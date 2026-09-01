"""
AI Image Upscaling Module for OliveVision AI.

Wraps the realesrgan-ncnn-vulkan CLI tool to upscale low-resolution
drone/aerial images before detection. The upscaler is called as a
subprocess, so no extra Python dependencies are required.

The tool binary should be installed at tools/realesrgan-ncnn-vulkan/
(see README for setup instructions). If the tool is not found, upscaling
is gracefully skipped.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

DEFAULT_TOOL_DIR = Path(__file__).resolve().parent.parent / "tools" / "realesrgan-ncnn-vulkan"
DEFAULT_MODEL = "realesrgan-x4plus"
DEFAULT_SCALE = 2
DEFAULT_THRESHOLD = 900


class ImageUpscaler:
    """Wraps the realesrgan-ncnn-vulkan CLI for programmatic upscaling.

    Upscaling is only triggered when an image is below the configured
    resolution threshold. The tool is invoked as an external subprocess
    so it works from both the CLI and the GUI without duplicating logic.
    """

    def __init__(self, tool_dir: Optional[Path] = None,
                 model: str = DEFAULT_MODEL,
                 scale: int = DEFAULT_SCALE,
                 threshold: int = DEFAULT_THRESHOLD,
                 enabled: bool = True):
        """
        Args:
            tool_dir: Directory containing realesrgan-ncnn-vulkan.exe.
                      Defaults to tools/realesrgan-ncnn-vulkan.
            model:   ncnn model name (realesrgan-x4plus, realesr-animevideov3, ...).
            scale:   Upscale ratio (2, 3, or 4).
            threshold: Minimum (shorter) image side in px; images below this
                      are upscaled.
            enabled: If False, upscaling is a no-op (returns original image).
        """
        self.tool_dir = Path(tool_dir) if tool_dir else DEFAULT_TOOL_DIR
        self.model = model
        self.scale = max(2, min(4, int(scale)))
        self.threshold = int(threshold)
        self.enabled = enabled
        self.exe = self.tool_dir / "realesrgan-ncnn-vulkan.exe"
        self.models_dir = self.tool_dir / "models"

        # Map fuzzy model names (with _x4 suffix etc.) to official ncnn names.
        self._normalized_model = self._normalize_model(model)

        self.available = self._check_available()

    @staticmethod
    def _normalize_model(model: str) -> str:
        """Map common model names/aliases to the official ncnn model names."""
        m = model.strip().lower()
        aliases = {
            "x4plus": "realesrgan-x4plus",
            "realesrgan": "realesrgan-x4plus",
            "realesrgan-x4": "realesrgan-x4plus",
            "anime": "realesr-animevideov3",
            "animevideo": "realesr-animevideov3",
            "realesr-animevideov3": "realesr-animevideov3",
            "realesrnet-x4plus": "realesrnet-x4plus",
        }
        return aliases.get(m, m)

    def _check_available(self) -> bool:
        """Return True if the upscaler binary and models are present."""
        if not self.exe.exists():
            return False
        # Model pair (.param + .bin) must exist for the chosen model.
        param = self.models_dir / f"{self._normalized_model}.param"
        bin_ = self.models_dir / f"{self._normalized_model}.bin"
        return param.exists() and bin_.exists()

    @property
    def resolution_mode(self) -> str:
        """Return a short string describing the upscaler state."""
        if not self.enabled:
            return "disabled"
        if not self.available:
            return "unavailable"
        return f"{self.model} x{self.scale}"

    def needs_upscale(self, image: np.ndarray) -> bool:
        """Return True if the image should be upscaled."""
        if not self.enabled or not self.available:
            return False
        h, w = image.shape[:2]
        return min(w, h) < self.threshold

    def upscale_image(self, image: np.ndarray) -> np.ndarray:
        """Upscale a low-res image and return the enlarged BGR image.

        If upscaling is disabled, unavailable, or the image is already
        large enough, the original image is returned unchanged.
        """
        if not self.enabled or not self.available:
            return image
        if not self.needs_upscale(image):
            return image

        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            input_path = temp_dir / "input.png"
            output_path = temp_dir / "output.png"
            cv2.imwrite(str(input_path), image)

            cmd = [
                str(self.exe),
                "-i", str(input_path),
                "-o", str(output_path),
                "-n", self._normalized_model,
                "-s", str(self.scale),
                "-m", str(self.models_dir),
                "-f", "png",
            ]
            try:
                proc = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=120)
                if proc.returncode != 0 or not output_path.exists():
                    return image
            except (subprocess.TimeoutExpired, OSError):
                return image

            upscaled = cv2.imread(str(output_path))
            if upscaled is None:
                return image
            return upscaled

    def upscale_file(self, input_path, output_path) -> bool:
        """Upscale a file directly with the CLI (bypasses img array).

        Returns True on success, False if the tool is unavailable or failed.
        """
        if not self.enabled or not self.available:
            return False
        cmd = [
            str(self.exe),
            "-i", str(input_path),
            "-o", str(output_path),
            "-n", self._normalized_model,
            "-s", str(self.scale),
            "-m", str(self.models_dir),
            "-f", "png",
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return proc.returncode == 0 and Path(output_path).exists()
        except (subprocess.TimeoutExpired, OSError):
            return False
