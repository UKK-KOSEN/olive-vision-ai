"""
OliveVision AI - テクスチャ解析モジュール
"""

import cv2
import numpy as np
from typing import Dict
import logging

try:
    from skimage.feature import graycomatrix, graycoprops
    HAS_SKIMAGE = True
except ImportError:
    try:
        from skimage.feature import greycomatrix as graycomatrix, greycoprops as graycoprops
        HAS_SKIMAGE = True
    except ImportError:
        HAS_SKIMAGE = False


class TextureAnalyzer:

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)

    def analyze_object_texture(self, image: np.ndarray, mask: np.ndarray) -> Dict:
        if np.sum(mask) == 0:
            return {}

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        features = {}

        # Masked region in 2D (preserving spatial structure)
        masked_2d = gray.copy()
        masked_2d[mask == 0] = 0

        # Bounding-box crop of the masked area for efficiency
        ys, xs = np.where(mask > 0)
        if len(ys) == 0:
            return {}
        y0, y1 = max(0, ys.min() - 1), min(gray.shape[0], ys.max() + 2)
        x0, x1 = max(0, xs.min() - 1), min(gray.shape[1], xs.max() + 2)
        roi = masked_2d[y0:y1, x0:x1]
        roi_mask = mask[y0:y1, x0:x1]
        roi_pixels = roi[roi_mask > 0]

        # Basic stats
        features['texture_mean'] = float(np.mean(roi_pixels))
        features['texture_std'] = float(np.std(roi_pixels))
        features['texture_min'] = int(np.min(roi_pixels))
        features['texture_max'] = int(np.max(roi_pixels))
        features['texture_median'] = float(np.median(roi_pixels))
        features['texture_contrast'] = features['texture_max'] - features['texture_min']
        features['texture_energy'] = self._calculate_energy(roi_pixels)

        # GLCM
        glcm_features = self._calculate_glcm_features(roi, roi_mask)
        features.update(glcm_features)

        # LBP
        lbp_features = self._calculate_lbp_features(roi, roi_mask)
        features.update(lbp_features)

        return features

    @staticmethod
    def _calculate_energy(data: np.ndarray) -> float:
        mn, mx = np.min(data), np.max(data)
        normalized = (data - mn) / (mx - mn + 1e-8)
        return float(np.sum(normalized ** 2) / len(normalized))

    @staticmethod
    def _calculate_glcm_features(roi_2d: np.ndarray, roi_mask: np.ndarray,
                                  distances=None) -> Dict:
        if distances is None:
            distances = [1]
        features = {}
        if not HAS_SKIMAGE:
            return features

        # Use the bounding-box roi directly (already 2D spatial)
        h, w = roi_2d.shape
        if h < 5 or w < 5:
            return features

        # Resize to max 128x128 for speed
        max_dim = 128
        scale = min(max_dim / h, max_dim / w, 1.0)
        if scale < 1.0:
            rh, rw = max(5, int(h * scale)), max(5, int(w * scale))
            small = cv2.resize(roi_2d, (rw, rh), interpolation=cv2.INTER_AREA)
            small_mask = cv2.resize(roi_mask, (rw, rh), interpolation=cv2.INTER_NEAREST)
        else:
            small = roi_2d
            small_mask = roi_mask

        # Zero out non-mask pixels and shift to uint8 0-255
        work = small.copy()
        work[small_mask == 0] = 0
        work = work.astype(np.uint8)

        try:
            glcm = graycomatrix(work, distances=distances, angles=[0],
                                levels=256, symmetric=True, normed=True)
            features['glcm_contrast'] = float(graycoprops(glcm, 'contrast')[0][0])
            features['glcm_dissimilarity'] = float(graycoprops(glcm, 'dissimilarity')[0][0])
            features['glcm_homogeneity'] = float(graycoprops(glcm, 'homogeneity')[0][0])
            features['glcm_energy'] = float(graycoprops(glcm, 'energy')[0][0])
            features['glcm_correlation'] = float(graycoprops(glcm, 'correlation')[0][0])
            features['glcm_asm'] = float(graycoprops(glcm, 'asm')[0][0])
        except Exception:
            pass

        return features

    @staticmethod
    def _calculate_lbp_features(roi_2d: np.ndarray, roi_mask: np.ndarray) -> Dict:
        features = {}
        h, w = roi_2d.shape
        if h < 3 or w < 3:
            return features

        # Vectorised LBP (8-neighbour, clockwise from top-left)
        padded = np.pad(roi_2d.astype(np.int16), 1, mode='constant', constant_values=0)
        center = padded[1:-1, 1:-1]
        neighbors = [
            padded[0:-2, 0:-2], padded[0:-2, 1:-1], padded[0:-2, 2:],
            padded[1:-1, 2:],
            padded[2:, 2:], padded[2:, 1:-1], padded[2:, 0:-2],
            padded[1:-1, 0:-2],
        ]
        lbp = np.zeros((h, w), dtype=np.uint8)
        for k, nb in enumerate(neighbors):
            lbp |= ((nb >= center).astype(np.uint8) << k)

        # Only consider masked pixels
        masked_lbp = lbp[roi_mask > 0]
        if len(masked_lbp) == 0:
            return features

        hist, _ = np.histogram(masked_lbp, bins=256, range=(0, 256))
        hist = hist.astype(np.float64)
        total = hist.sum()
        if total > 0:
            hist /= total

        features['lbp_energy'] = float(np.sum(hist ** 2))
        features['lbp_entropy'] = float(-np.sum(hist[hist > 0] * np.log2(hist[hist > 0])))
        features['lbp_uniformity'] = float(np.max(hist))

        return features

    def analyze_surface_roughness(self, image: np.ndarray, mask: np.ndarray) -> float:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        if np.sum(mask) == 0:
            return 0.0
        gray_masked = gray.copy()
        gray_masked[mask == 0] = 0
        laplacian = cv2.Laplacian(gray_masked, cv2.CV_64F)
        return float(np.std(laplacian[mask > 0]))

    def detect_surface_defects(self, image: np.ndarray, mask: np.ndarray,
                               threshold: float = 2.0) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        mean = cv2.blur(gray, (7, 7))
        sqr = cv2.blur(gray.astype(np.float64) ** 2, (7, 7))
        std = np.sqrt(np.maximum(sqr - mean.astype(np.float64) ** 2, 0))
        diff = np.abs(gray.astype(np.float32) - mean.astype(np.float32))
        defects = (diff > threshold * (std.astype(np.float32) + 1)).astype(np.uint8) * mask
        return defects

    def calculate_leaf_smoothness(self, image: np.ndarray, mask: np.ndarray) -> float:
        roughness = self.analyze_surface_roughness(image, mask)
        max_roughness = 50.0
        smoothness = max(0, 1.0 - (roughness / max_roughness))
        return min(1.0, smoothness)

    def calculate_fruit_shine(self, image: np.ndarray, mask: np.ndarray) -> float:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        masked = gray[mask > 0]
        if len(masked) == 0:
            return 0.0
        return float(np.sum(masked > 200) / len(masked))
