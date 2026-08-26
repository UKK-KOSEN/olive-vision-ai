"""Small, dependable runtime used by the OliveVision CLI and desktop GUI.

The module deliberately has no ML or cloud dependency: it is intended to run
continuously on a Raspberry Pi and to keep every measurement locally.
"""
from __future__ import annotations

import csv
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple, List, Dict

import cv2
import numpy as np
import yaml

DEFAULTS = {
    "runtime": {"max_width": 1280, "jpeg_quality": 90, "camera_warmup_frames": 8},
    "detection": {
        "leaf_hue": [30, 95], "leaf_saturation_min": 35, "leaf_value_min": 25,
        "leaf_min_area": 350, "leaf_max_area": 30000, "leaf_min_aspect": 1.0,
        "leaf_max_aspect": 12.0, "leaf_min_solidity": 0.58,
        "fruit_hue_yellow": [18, 45], "fruit_hue_ripe": [105, 179],
        "fruit_saturation_min": 55, "fruit_value_min": 65,
        "fruit_lab_b_min": 145,
        "fruit_min_area": 250, "fruit_max_area": 18000, "fruit_min_aspect": 0.45,
        "fruit_max_aspect": 2.4, "fruit_min_circularity": 0.50,
        "fruit_min_solidity": 0.72,
        "fruit_max_ellipse_ratio": 3.5,
        "fruit_no_circle_min_area": 1400,
        "fruit_no_circle_min_circularity": 0.65,
        "fruit_no_circle_min_solidity": 0.88,
        "fruit_no_circle_max_std": 45.0,
        "fruit_no_circle_max_area": 4000,
        "excess_green_min": 12,
        "adaptive_blur": 5,
        "multiscale_scales": [0.75, 1.0, 1.3],
        "watershed_mindist": 20,
        "edge_close_kernel": 5,
        "grabcut_iter": 3,
        "edge_refine": True,
        "detect_mode": "multi_signal",
        "fg_kmeans_clusters": 3,
        "fg_grabcut_iter": 5,
        "fg_min_area_ratio": 0.005,
        "fg_morph_kernel": 7,
        # Wrinkle scoring
        "wrinkle_ridge_weight": 3.0,
        "wrinkle_texture_base": 18.0,
        "wrinkle_texture_scale": 80.0,
        "wrinkle_smooth_max": 0.25,
        "wrinkle_slightly_wrinkled_max": 0.45,
        "wrinkle_wrinkled_max": 0.70,
        "wrinkle_erosion_scale": 0.25,
        "wrinkle_min_interior_pixels": 60,
        "wrinkle_min_valid_pixels": 30,
        "wrinkle_ridge_mean_multiplier": 1.4,
        "wrinkle_ridge_min_threshold": 20.0,
        "wrinkle_interior_fraction_min": 0.30,
        "wrinkle_min_reliable_area": 350,
        # Leaf curl scoring
        "curl_weight_solidity": 0.30,
        "curl_weight_defect": 0.30,
        "curl_weight_elongation": 0.40,
        "curl_defect_radius_scale": 0.5,
        "curl_elongation_baseline": 1.2,
        "curl_elongation_scale": 4.0,
        "curl_threshold_flat": 0.10,
        "curl_threshold_slight": 0.25,
        "curl_threshold_curled": 0.50,
        # QR code tree-id detection.
        "qr_detection": True,
    },
    "analysis": {
        # Leaf colour hue bands
        "leaf_hue_green_low": 35,
        "leaf_hue_green_high": 85,
        "leaf_hue_yellow_high": 95,
        "leaf_hue_dark_high": 150,
        # Leaf size buckets (px²)
        "leaf_size_small_max": 2000,
        "leaf_size_medium_max": 6000,
        # Drooping angle (degrees from horizontal)
        "drooping_angle_low": 45,
        "drooping_angle_high": 135,
        # Confidence threshold
        "leaf_low_confidence_threshold": 0.5,
        # Fruit size buckets (px²)
        "fruit_size_small_max": 400,
        "fruit_size_medium_max": 800,
        "fruit_low_confidence_threshold": 0.5,
    },
    "stress": {
        # Water stress
        "weight_curl": 0.5,
        "weight_wrinkle": 0.5,
        # Overall health score normalisation
        "green_coverage_max": 50.0,
        "curl_saturation": 3.0,
        "wrinkle_saturation": 2.0,
        "saturation_max": 120.0,
        # Overall health score weights
        "weight_green": 0.30,
        "weight_health_curl": 0.25,
        "weight_health_wrinkle": 0.25,
        "weight_saturation": 0.20,
    },
    "trend": {
        "min_green_coverage": 10.0,
        # Dehydration scoring
        "dehydration_wrinkle_scale": 0.5,
        "dehydration_wrinkle_weight": 0.6,
        "dehydration_shrink_weight": 0.4,
        # Per-fruit track flag thresholds
        "flag_ripeness_threshold": 0.15,
        "flag_wrinkle_threshold": 0.2,
        "flag_dehydration_threshold": 0.30,
        # Trend note thresholds (per-day slopes)
        "note_ripeness_rise": 0.05,
        "note_ripeness_fall": -0.05,
        "note_wrinkle_increase": 0.05,
        "note_green_decline": -2.0,
        "note_fruit_count_decline": -0.5,
        "note_leaf_count_decline": -1.0,
        # Dropout detection
        "dropout_green_tolerance": 1.0,
    },
    "video": {
        "frame_interval": 10,
        "max_frames": 500,
        "output_fps": 5,
        "track_max_age": 30,
        "track_iou_threshold": 0.3,
    },
}

# Minimum per-pixel overlap ratio (fraction of the object mask covered by a
# signal) before that signal counts as evidence for a fruit. Shared by the
# evidence attribution in analyze() and the human-readable explanation, so the
# two can never drift apart.
FRUIT_SIGNAL_THRESHOLDS = {
    "yellow_green": 0.35,
    "ripe": 0.25,
    "dark": 0.25,
    "hough_circle": 0.20,
}

FRUIT_SIGNAL_LABELS = {
    "yellow_green": "yellow-green colour",
    "ripe": "ripe colour",
    "dark": "dark/over-ripe colour",
    "hough_circle": "round Hough circle",
}


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_runtime_config(path: Optional[Path] = None) -> dict:
    config = json.loads(json.dumps(DEFAULTS))
    if path and Path(path).exists():
        with Path(path).open(encoding="utf-8") as handle:
            supplied = yaml.safe_load(handle) or {}
        for section, values in supplied.items():
            if isinstance(values, dict) and isinstance(config.get(section), dict):
                config[section].update(values)
            else:
                config[section] = values
    return config


def scale_detection_for_resolution(config: dict, image_width: int) -> dict:
    """Scale detection parameters based on image resolution.

    For low-resolution images (e.g. drone captures), area-based thresholds
    and other size-dependent parameters are scaled down proportionally.
    This function returns a NEW config dict with scaled values; the
    original config is never mutated.

    Args:
        config: Runtime configuration dict
        image_width: Width of the input image in pixels

    Returns:
        Config dict with resolution-scaled detection parameters
    """
    import copy
    presets = config.get("resolution_presets", {})
    base = presets.get("base_resolution", 1280)
    low_thr = presets.get("low_res_threshold", 900)

    if image_width >= low_thr:
        return config

    factor = image_width / base
    is_very_low = image_width < (low_thr * 0.6)

    if is_very_low:
        scale = presets.get("very_low_res", presets.get("low_res", {}))
    else:
        scale = presets.get("low_res", {})

    if not scale:
        return config

    scaled = copy.deepcopy(config)
    det = scaled.get("detection", {})

    area_keys = [
        "leaf_min_area", "leaf_max_area",
        "fruit_min_area", "fruit_max_area",
        "fruit_no_circle_min_area", "fruit_no_circle_max_area",
        "wrinkle_min_reliable_area",
    ]
    for key in area_keys:
        if key in det and key in scale:
            multiplier = scale[key]
            det[key] = max(10, int(det[key] * multiplier))

    float_keys = [
        "leaf_min_solidity", "fruit_min_solidity",
        "fruit_min_circularity", "fg_min_area_ratio",
    ]
    for key in float_keys:
        if key in det and key in scale:
            det[key] = scale[key]

    if "watershed_mindist" in det and "watershed_mindist" in scale:
        det["watershed_mindist"] = max(5, int(det["watershed_mindist"] * scale["watershed_mindist"]))

    if "multiscale_scales" in scale:
        det["multiscale_scales"] = scale["multiscale_scales"]

    scaled["detection"] = det
    scaled["_resolution_scale"] = round(factor, 3)
    scaled["_resolution_mode"] = "very_low" if is_very_low else "low"
    return scaled


# --- Drone / aerial image enhancement helpers ---

def normalize_illumination(image):
    """Color-normalize an image to reduce lighting variation.

    Uses LAB color space to normalize L channel while preserving A/B.
    This helps drone images taken under different lighting conditions.
    """
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    # CLAHE on L channel: adaptive histogram equalization
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    # Gentle white balance: shift A/B channels toward mean
    a_mean, b_mean = np.mean(a), np.mean(b)
    a = cv2.addWeighted(a, 0.85, np.full_like(a, a_mean), 0.15, 0)
    b = cv2.addWeighted(b, 0.85, np.full_like(b, b_mean), 0.15, 0)
    lab = cv2.merge([l, a, b])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def compute_adaptive_green_threshold(image, base_min=10, percentile=5):
    """Compute adaptive ExG threshold from image statistics.

    Returns a threshold higher than base_min based on the image's
    actual green distribution, reducing false positives in noisy images.
    """
    exg = _compute_vegetation_index(image)
    nonzero = exg[exg > 0]
    if len(nonzero) < 100:
        return base_min
    # Use percentile as floor, but at least base_min
    adaptive = max(base_min, int(np.percentile(nonzero, percentile)))
    return min(adaptive, 30)  # cap at 30 to avoid over-tightening


def build_logger(verbose: bool = False) -> logging.Logger:
    logger = logging.getLogger("olivevision.runtime")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
    return logger


import re as _re

_QR_TREE_RE = _re.compile(r"第(\d+)試験樹")


def _detect_qr_tree_id(image_bgr: np.ndarray) -> str | None:
    """Detect a QR code in the image and extract the tree trial ID.

    Expects QR content matching the pattern ``第N試験樹`` (e.g. 第1試験樹).
    Returns the full matched string (e.g. "第1試験樹") or None if no match.
    """
    try:
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(image_bgr)
        if not data:
            return None
        # OpenCV may return bytes (UTF-8 encoded) instead of str.
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")
        m = _QR_TREE_RE.search(data)
        if m:
            return m.group(0)
        return None
    except Exception:
        return None


class Store:
    def __init__(self, db_path: str | Path):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        con = self._connect()
        try:
            con.execute("""CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY, observed_at TEXT NOT NULL, source TEXT NOT NULL,
                image_path TEXT, leaf_count INTEGER NOT NULL, fruit_count INTEGER NOT NULL,
                green_coverage REAL NOT NULL, image_width INTEGER NOT NULL,
                image_height INTEGER NOT NULL, result_json TEXT NOT NULL,
                tree_id TEXT)""")
            # Migrate older databases that lack the tree_id column.
            try:
                con.execute("SELECT tree_id FROM observations LIMIT 1")
            except sqlite3.OperationalError:
                con.execute("ALTER TABLE observations ADD COLUMN tree_id TEXT")
            con.commit()
        finally:
            con.close()

    def _connect(self):
        return sqlite3.connect(self.path, timeout=15)

    @staticmethod
    def _sanitize_for_json(obj):
        """Recursively convert numpy arrays and similar objects for JSON serialization."""
        import numpy as _np
        if isinstance(obj, dict):
            return {k: Store._sanitize_for_json(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [Store._sanitize_for_json(v) for v in obj]
        if isinstance(obj, _np.ndarray):
            return obj.tolist()
        if isinstance(obj, (_np.integer,)):
            return int(obj)
        if isinstance(obj, (_np.floating,)):
            return float(obj)
        return obj

    def add(self, result: dict) -> None:
        con = self._connect()
        try:
            clean = Store._sanitize_for_json(result)
            con.execute(
                "INSERT INTO observations (observed_at,source,image_path,leaf_count,"
                "fruit_count,green_coverage,image_width,image_height,result_json,"
                "tree_id) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (clean["observed_at"], clean["source"], clean.get("image_path"),
                 clean["leaf_count"], clean["fruit_count"], clean["green_coverage"],
                 clean["image_width"], clean["image_height"],
                 json.dumps(clean, ensure_ascii=False),
                 clean.get("tree_id")))
            con.commit()
        finally:
            con.close()

    def recent(self, limit: int = 20) -> list[dict]:
        con = self._connect()
        try:
            rows = con.execute(
                "SELECT result_json FROM observations ORDER BY id DESC LIMIT ?",
                (limit,)).fetchall()
        finally:
            con.close()
        return [json.loads(row[0]) for row in rows]

    def recent_by_tree(self, tree_id: str, limit: int = 1_000_000) -> list[dict]:
        con = self._connect()
        try:
            rows = con.execute(
                "SELECT result_json FROM observations WHERE tree_id = ? "
                "ORDER BY id DESC LIMIT ?",
                (tree_id, limit)).fetchall()
        finally:
            con.close()
        return [json.loads(row[0]) for row in rows]

    def recent_by_source(self, source_prefix: str, tree_id: str = None,
                         limit: int = 1_000_000) -> list[dict]:
        con = self._connect()
        try:
            if tree_id:
                rows = con.execute(
                    "SELECT result_json FROM observations "
                    "WHERE source LIKE ? AND tree_id = ? "
                    "ORDER BY id DESC LIMIT ?",
                    (f"{source_prefix}%", tree_id, limit)).fetchall()
            else:
                rows = con.execute(
                    "SELECT result_json FROM observations "
                    "WHERE source LIKE ? "
                    "ORDER BY id DESC LIMIT ?",
                    (f"{source_prefix}%", limit)).fetchall()
        finally:
            con.close()
        return [json.loads(row[0]) for row in rows]

    def tree_ids(self) -> list[str]:
        con = self._connect()
        try:
            rows = con.execute(
                "SELECT DISTINCT tree_id FROM observations "
                "WHERE tree_id IS NOT NULL AND tree_id != '' "
                "ORDER BY tree_id").fetchall()
        finally:
            con.close()
        return [row[0] for row in rows]

    def export_csv(self, destination: str | Path) -> int:
        records = list(reversed(self.recent(1_000_000)))
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        fields = ["observed_at", "source", "image_path", "leaf_count", "fruit_count",
                  "green_coverage", "image_width", "image_height", "tree_id"]
        with destination.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows({key: row.get(key) for key in fields} for row in records)
        return len(records)

    def clear(self) -> int:
        """Delete all observations and return how many were removed."""
        con = self._connect()
        try:
            count = con.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
            con.execute("DELETE FROM observations")
            con.commit()
            return count
        finally:
            con.close()


def _ripeness_ratio(fruit: dict) -> Optional[float]:
    """Fraction of a fruit's signal pixels already in the ripe/dark bands.
    Returns None when the fruit was recorded without signal ratios."""
    ratios = fruit.get("signal_ratios")
    if not isinstance(ratios, dict):
        return None
    return float(ratios.get("ripe", 0.0) or 0.0) + float(ratios.get("dark", 0.0) or 0.0)


def _linear_slope_per_day(hours: list[float], values: list) -> Optional[float]:
    """Least-squares slope of ``values`` vs hours since the first capture,
    expressed as change per 24 h. Returns None when not enough spread."""
    xs, ys = [], []
    for x, y in zip(hours, values):
        if y is None:
            continue
        xs.append(x)
        ys.append(y)
    if len(xs) < 2:
        return None
    n = len(xs)
    sx = sum(xs)
    sy = sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-9:
        return None
    return (n * sxy - sx * sy) / denom * 24.0


def analyze_health_trend(observations: list[dict], match_radius: float = 60.0,
                         min_observations: int = 2, cfg: dict | None = None) -> dict:
    """Turn stored observations into a health-change report.

    Repeated analyses of the same picture are collapsed, low-quality captures
    are skipped, and individual fruits are tracked across captures by position
    so that colour (ripeness) and wrinkle changes can be measured over time.

    Returns a dict with:
      period/count        observation timeline information
      series              one row per unique capture
      trends              per-day slopes for fruit_count/green/ripeness/wrinkle
      fruit_tracks        persistent fruits with first/last colour & wrinkle
      health              overall verdict (stable/maturing/declining/mixed/insufficient)
    """
    cfg = cfg or {}
    trend_cfg = cfg.get("trend", {})
    min_green_cov = trend_cfg.get("min_green_coverage", 10.0)
    dehy_wr_scale = trend_cfg.get("dehydration_wrinkle_scale", 0.5)
    dehy_wr_weight = trend_cfg.get("dehydration_wrinkle_weight", 0.6)
    dehy_sh_weight = trend_cfg.get("dehydration_shrink_weight", 0.4)
    flag_rip_thr = trend_cfg.get("flag_ripeness_threshold", 0.15)
    flag_wrk_thr = trend_cfg.get("flag_wrinkle_threshold", 0.2)
    flag_dehy_thr = trend_cfg.get("flag_dehydration_threshold", 0.30)
    note_rip_rise = trend_cfg.get("note_ripeness_rise", 0.05)
    note_rip_fall = trend_cfg.get("note_ripeness_fall", -0.05)
    note_wrk_inc = trend_cfg.get("note_wrinkle_increase", 0.05)
    note_green_dec = trend_cfg.get("note_green_decline", -2.0)
    note_fruit_dec = trend_cfg.get("note_fruit_count_decline", -0.5)
    note_leaf_dec = trend_cfg.get("note_leaf_count_decline", -1.0)
    dropout_green_tol = trend_cfg.get("dropout_green_tolerance", 1.0)
    def _ts(o):
        try:
            return datetime.fromisoformat(o["observed_at"])
        except (KeyError, TypeError, ValueError):
            return None

    timed = [(o, _ts(o)) for o in observations if _ts(o) is not None]
    timed.sort(key=lambda pair: pair[1])
    obs = [o for o, _ in timed]
    if not obs:
        return {"ok": False, "error": "no observations with valid timestamps"}
    start, end = timed[0][1], timed[-1][1]

    good, bad = [], 0
    for o in obs:
        if float(o.get("green_coverage", 0.0)) >= min_green_cov:
            good.append(o)
        else:
            bad += 1

    unique, seen = [], set()
    for o in good:
        ts = _ts(o)
        key = (ts.date(), o.get("source"), o.get("leaf_count"), o.get("fruit_count"),
               round(float(o.get("green_coverage", 0.0)), 2))
        if key in seen:
            continue
        seen.add(key)
        unique.append(o)

    def _avg(fruits, key):
        vals = [f.get(key) for f in fruits if f.get(key) is not None]
        return (sum(vals) / len(vals)) if vals else None

    series = []
    for o in unique:
        fruits = o.get("fruit_objects") or []
        rip = [v for v in (_ripeness_ratio(f) for f in fruits) if v is not None]
        avg_rip = (sum(rip) / len(rip)) if rip else None
        avg_hue = _avg(fruits, "hue")
        avg_wrinkle = _avg(fruits, "wrinkle_score")
        series.append({
            "observed_at": o["observed_at"],
            "source": o.get("source", "file"),
            "leaves": o.get("leaf_count", 0),
            "fruits": o.get("fruit_count", 0),
            "green": round(float(o.get("green_coverage", 0.0)), 2),
            "avg_hue": round(avg_hue, 1) if avg_hue is not None else None,
            "avg_ripeness": round(avg_rip, 3) if avg_rip is not None else None,
            "avg_wrinkle": round(avg_wrinkle, 3) if avg_wrinkle is not None else None,
        })

    hours = []
    for o in unique:
        hours.append((_ts(o) - start).total_seconds() / 3600.0)
    trends = {
        "fruit_count_per_day": _linear_slope_per_day(hours, [r["fruits"] for r in series]),
        "leaf_count_per_day": _linear_slope_per_day(hours, [r["leaves"] for r in series]),
        "green_per_day": _linear_slope_per_day(hours, [r["green"] for r in series]),
        "ripeness_per_day": _linear_slope_per_day(hours, [r["avg_ripeness"] for r in series]),
        "wrinkle_per_day": _linear_slope_per_day(hours, [r["avg_wrinkle"] for r in series]),
    }

    tracks = []
    for o in unique:
        ts = _ts(o)
        used = set()
        for f in o.get("fruit_objects") or []:
            if "center_x" not in f or "center_y" not in f:
                continue
            cx, cy = float(f.get("center_x", 0)), float(f.get("center_y", 0))
            best_idx, best_d2 = -1, match_radius ** 2
            for ti, t in enumerate(tracks):
                if ti in used:
                    continue
                lx, ly = t["points"][-1]
                d2 = (cx - lx) ** 2 + (cy - ly) ** 2
                if d2 < best_d2:
                    best_d2, best_idx = d2, ti
            if best_idx >= 0:
                t = tracks[best_idx]
                t["points"].append((cx, cy))
                t["fruits"].append(f)
                t["times"].append(ts)
                used.add(best_idx)
            else:
                tracks.append({"points": [(cx, cy)], "fruits": [f], "times": [ts]})

    fruit_tracks = []
    for ti, t in enumerate(tracks, 1):
        if len(t["fruits"]) < min_observations:
            continue
        first, last = t["fruits"][0], t["fruits"][-1]
        if t["times"][-1].date() == t["times"][0].date():
            continue
        rip_first, rip_last = _ripeness_ratio(first), _ripeness_ratio(last)
        wrk_first = first.get("wrinkle_score")
        wrk_last = last.get("wrinkle_score")
        area_first = first.get("area")
        area_last = last.get("area")
        d_rip = rip_last - rip_first if (rip_first is not None and rip_last is not None) else None
        d_wrk = wrk_last - wrk_first if (wrk_first is not None and wrk_last is not None) else None
        shrink = (area_last / area_first) if (area_first and area_last and area_first > 0) else None
        # Dehydration: combined effect of surface wrinkling + fruit shrinkage.
        # Wrinkle contribution (0..1) scaled by 0.6, shrinkage (0..1) by 0.4.
        wrk_contribution = (min(1.0, max(0.0, d_wrk) / dehy_wr_scale) * dehy_wr_weight) if d_wrk is not None else 0.0
        shrink_contribution = ((1.0 - min(1.0, max(0.0, shrink))) * dehy_sh_weight) if shrink is not None else 0.0
        dehydration = round(wrk_contribution + shrink_contribution, 3)
        flags = []
        if d_rip is not None and d_rip >= flag_rip_thr:
            flags.append("ripening")
        if d_wrk is not None and d_wrk >= flag_wrk_thr:
            flags.append("wrinkling")
        if dehydration >= flag_dehy_thr:
            flags.append("dehydration")
        if d_rip is not None and d_wrk is not None and d_rip >= flag_rip_thr and d_wrk >= flag_wrk_thr:
            flags.append("deteriorating")
        fruit_tracks.append({
            "id": ti,
            "observations": len(t["fruits"]),
            "first": t["times"][0].isoformat(),
            "last": t["times"][-1].isoformat(),
            "x": round(t["points"][-1][0]),
            "y": round(t["points"][-1][1]),
            "ripeness_first": round(rip_first, 3) if rip_first is not None else None,
            "ripeness_last": round(rip_last, 3) if rip_last is not None else None,
            "wrinkle_first": round(wrk_first, 3) if wrk_first is not None else None,
            "wrinkle_last": round(wrk_last, 3) if wrk_last is not None else None,
            "area_first": area_first,
            "area_last": area_last,
            "shrink_ratio": round(shrink, 3) if shrink is not None else None,
            "dehydration": dehydration,
            "flags": flags,
        })

    notes = []
    r = trends["ripeness_per_day"]
    w = trends["wrinkle_per_day"]
    g = trends["green_per_day"]
    c = trends["fruit_count_per_day"]
    if r is not None and r >= note_rip_rise:
        notes.append(f"fruit colour is drifting towards ripe/dark (ripeness {r:+.3f}/day)")
    elif r is not None and r <= note_rip_fall:
        notes.append(f"fruit colour is shifting back towards unripe ({r:+.3f}/day)")
    if w is not None and w >= note_wrk_inc:
        notes.append(f"fruit surface wrinkling is increasing (possible dehydration {w:+.3f}/day)")
    if g is not None and g <= note_green_dec:
        notes.append(f"foliage coverage is declining ({g:+.1f}%/day)")
    if c is not None and c <= note_fruit_dec:
        notes.append(f"detected fruit count is falling ({c:+.1f}/day; check camera angle / detection)")
    lc = trends["leaf_count_per_day"]
    if lc is not None and lc <= note_leaf_dec:
        notes.append(f"leaf count is declining ({lc:+.1f}/day; possible leaf drop)")

    for i in range(1, len(series) - 1):
        prev, cur, nxt = series[i - 1], series[i], series[i + 1]
        if cur["fruits"] == 0 and prev["fruits"] > 0 and nxt["fruits"] > 0 \
                and abs(cur["green"] - prev["green"]) <= dropout_green_tol:
            notes.append(f"{cur['observed_at']}: temporary fruit-count dropout detected "
                         f"(likely a detection failure, not fruit loss)")
            break

    ripening = sum(1 for t in fruit_tracks if "ripening" in t["flags"])
    wrinkling = sum(1 for t in fruit_tracks if "wrinkling" in t["flags"])
    dehydrating = sum(1 for t in fruit_tracks if "dehydration" in t["flags"])
    n_fruit = len(fruit_tracks)
    if dehydrating and dehydrating >= max(1, n_fruit / 2):
        notes.append(f"dehydration detected in {dehydrating}/{n_fruit} tracked fruits "
                     f"(wrinkle + area shrinkage)")
    if n_fruit == 0:
        level = "insufficient"
    elif (wrinkling and wrinkling >= max(1, n_fruit / 2)) or \
         (dehydrating and dehydrating >= max(1, n_fruit / 2)):
        level = "declining"
    elif ripening and ripening >= max(1, n_fruit / 2):
        level = "maturing"
    elif any(t["flags"] for t in fruit_tracks):
        level = "mixed"
    else:
        level = "stable"

    return {
        "ok": True,
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": len({t.date() for _, t in timed}),
        },
        "count": {
            "total": len(observations),
            "good": len(good),
            "bad_dropped": bad,
            "redundant_dropped": len(good) - len(unique),
            "unique": len(unique),
        },
        "series": series,
        "trends": trends,
        "fruit_tracks": fruit_tracks,
        "health": {"level": level, "notes": notes},
    }


# ===================================================================
#  Detection helpers
# ===================================================================

def _estimate_blur(image_bgr: np.ndarray) -> float:
    """Variance of Laplacian: high = sharp, low = blurry (image-level metric)."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _local_sharpness_map(image_bgr: np.ndarray, block: int = 32) -> np.ndarray:
    """Per-block Laplacian variance, normalised to [0,1]. 1 = sharp, 0 = blurry."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    sharp = np.zeros((h, w), np.float32)
    for y in range(0, h, block):
        for x in range(0, w, block):
            tile = gray[y:y + block, x:x + block]
            if tile.size < 9:
                continue
            var = float(cv2.Laplacian(tile, cv2.CV_64F).var())
            sharp[y:y + block, x:x + block] = var
    vmax = float(sharp.max())
    if vmax > 0:
        sharp /= vmax
    return sharp


def _unsharp_mask(image_bgr: np.ndarray, sigma: float = 2.0,
                  amount: float = 1.6, threshold: int = 0) -> np.ndarray:
    """Unsharp masking: sharpen edges while leaving flat areas intact."""
    blurred = cv2.GaussianBlur(image_bgr, (0, 0), sigma)
    sharpened = cv2.addWeighted(image_bgr, 1.0 + amount, blurred, -amount, 0)
    if threshold > 0:
        low_contrast = np.all(np.abs(image_bgr.astype(np.int16) - blurred.astype(np.int16)) < threshold, axis=2)
        sharpened[low_contrast] = image_bgr[low_contrast]
    return sharpened


def _is_mixed_focus(image_bgr: np.ndarray, block: int = 64) -> bool:
    """Detect shallow-depth-of-field / partly-blurred frames.

    Computes the Laplacian variance per tile; a frame mixing sharp and blurry
    regions has high dispersion (coefficient of variation) of tile sharpness,
    while a uniformly blurry or uniformly sharp frame is relatively flat.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    vals = []
    for y in range(0, h - block + 1, block):
        for x in range(0, w - block + 1, block):
            vals.append(float(cv2.Laplacian(gray[y:y + block, x:x + block],
                                            cv2.CV_64F).var()))
    if not vals:
        return False
    arr = np.asarray(vals)
    mean = float(arr.mean())
    if mean <= 1.0:
        return False
    cv_ = float(arr.std()) / mean
    return cv_ > 1.0


def _deblur_adaptive(image_bgr: np.ndarray, blur_level: float,
                     sharp_map: Optional[np.ndarray] = None) -> np.ndarray:
    """Region-aware deblur for locally out-of-focus (mixed) photos.

    Only runs when the frame mixes sharp and blurry regions (shallow depth of
    field / partial motion blur). Uniformly blurry frames are already handled by
    the global deblur inside _adaptive_preprocess, and uniformly smooth matte
    frames are left alone to avoid halo artifacts.
    """
    if sharp_map is None:
        sharp_map = _local_sharpness_map(image_bgr, block=48)
    sharp_frac = float((sharp_map > 0.6).mean())
    blur_frac = float((sharp_map < 0.3).mean())
    if not (sharp_frac >= 0.15 and blur_frac >= 0.3):
        return image_bgr
    strong = _unsharp_mask(image_bgr, sigma=3.0, amount=1.8)
    mild = _unsharp_mask(image_bgr, sigma=1.2, amount=0.6)
    weight = 1.0 - sharp_map.astype(np.float32)          # 0 = sharp, 1 = blurry
    weight = cv2.GaussianBlur(weight, (0, 0), 4)[..., None]
    out = strong.astype(np.float32) * weight + mild.astype(np.float32) * (1.0 - weight)
    return np.clip(out, 0, 255).astype(np.uint8)


def _adaptive_preprocess(image: np.ndarray, blur_k: int = 5,
                         deblur: bool = True, blur_score: Optional[float] = None) -> np.ndarray:
    """Adaptive preprocessing: denoise, enhance contrast, deblur, preserve detail."""
    if blur_score is None:
        blur_score = _estimate_blur(image)
    denoised = cv2.bilateralFilter(image, 9, 75, 75)
    lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    l = clahe.apply(l)
    enhanced = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
    if blur_k > 1:
        k = blur_k if blur_k % 2 == 1 else blur_k + 1
        enhanced = cv2.GaussianBlur(enhanced, (k, k), 0)
    # Blurry frames benefit from unsharp masking before thresholding.
    if deblur and blur_score < 180:
        enhanced = _unsharp_mask(enhanced, sigma=2.5, amount=1.8)
    return enhanced


def _compute_vegetation_index(image: np.ndarray) -> np.ndarray:
    b, g, r = cv2.split(image.astype(np.int16))
    denom = (r + g + b + 1).astype(np.float32)
    return np.clip((2.0 * g - r - b) / denom * 128 + 128, 0, 255).astype(np.uint8)


def _compute_cgi(image: np.ndarray) -> np.ndarray:
    b, g, r = cv2.split(image.astype(np.float32) + 1.0)
    cgi = np.arctan2(g - r, g + r)
    return cv2.normalize(cgi, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)


def _compute_edge_density(image_bgr: np.ndarray, mask: np.ndarray) -> float:
    """Fraction of mask boundary pixels that coincide with image edges."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    edges = _adaptive_canny(gray)
    kernel = np.ones((3, 3), np.uint8)
    boundary = cv2.subtract(mask, cv2.erode(mask, kernel))
    if cv2.countNonZero(boundary) == 0:
        return 0.0
    overlap = cv2.bitwise_and(boundary, edges)
    return cv2.countNonZero(overlap) / max(1, cv2.countNonZero(boundary))


def _compute_internal_texture(gray: np.ndarray, mask: np.ndarray) -> float:
    """Std dev of gray values inside a mask (eroded to ignore the boundary).

    Real fruit surfaces are smooth (low value); foliage regions contain veins
    and leaf edges (high value). Used to reject foliage leaks from the fruit
    mask on sharp photos.
    """
    eroded = cv2.erode(mask, np.ones((5, 5), np.uint8), iterations=1)
    if cv2.countNonZero(eroded) < 16:
        eroded = mask
    vals = gray[eroded > 0]
    return float(np.std(vals)) if vals.size else 0.0


def _compute_wrinkle_score(gray: np.ndarray, mask: np.ndarray,
                           cfg: dict | None = None) -> dict:
    """Estimate fruit wrinkling / shrivelling from internal ridge structure.

    Wrinkles are thin, elongated, high-gradient ridges on the fruit surface.
    Fresh, smooth fruit show almost none; dehydrated / shrivelled olives show
    a network of them. Combined with the interior texture (std of gray) this
    gives a 0..1 score:

      inner 0.00-smooth_max: smooth, smooth_max-slightly_wrinkled_max: slightly_wrinkled,
      slightly_wrinkled_max-wrinkled_max: wrinkled, >=wrinkled_max: heavily_wrinkled
    """
    cfg = cfg or {}
    ridge_weight = cfg.get("wrinkle_ridge_weight", 3.0)
    texture_base = cfg.get("wrinkle_texture_base", 18.0)
    texture_scale = cfg.get("wrinkle_texture_scale", 80.0)
    thr_smooth = cfg.get("wrinkle_smooth_max", 0.25)
    thr_slight = cfg.get("wrinkle_slightly_wrinkled_max", 0.45)
    thr_wrinkled = cfg.get("wrinkle_wrinkled_max", 0.70)
    erosion_scale = cfg.get("wrinkle_erosion_scale", 0.25)
    min_interior_px = cfg.get("wrinkle_min_interior_pixels", 60)
    min_valid_px = cfg.get("wrinkle_min_valid_pixels", 30)
    ridge_mean_mult = cfg.get("wrinkle_ridge_mean_multiplier", 1.4)
    ridge_min_thr = cfg.get("wrinkle_ridge_min_threshold", 20.0)
    int_frac_min = cfg.get("wrinkle_interior_fraction_min", 0.30)
    min_reliable_area = cfg.get("wrinkle_min_reliable_area", 350)
    area = cv2.countNonZero(mask)
    # Scale erosion kernel with object size so small fruit keep a usable interior.
    radius = max(1.0, (area / np.pi) ** 0.5)
    ksize = max(3, min(11, int(2 * radius * erosion_scale)))
    if ksize % 2 == 0:
        ksize += 1
    interior = cv2.erode(mask, np.ones((ksize, ksize), np.uint8), iterations=1)
    interior_px = cv2.countNonZero(interior)
    # For very small objects the erosion consumes nearly the whole mask; analysing
    # the full boundary ring would produce artefactual heavily-wrinkled labels.
    # Fall back to the full mask only when a usable interior fraction remains;
    # otherwise flag the result as unreliable.
    interior_fraction = interior_px / max(1, area)
    unreliable = False
    if interior_px < min_interior_px:
        # Too few interior pixels for meaningful analysis — mark unreliable
        # but still compute the score from whatever survives (may be the full
        # mask boundary).  A discount factor is applied below.
        interior = mask
        unreliable = True
    vals = gray[interior > 0]
    if vals.size < min_valid_px:
        return {"wrinkle_score": 0.0, "ridge_density": 0.0,
                "wrinkle_label": "smooth", "wrinkle_reliable": True}
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)
    interior_mag = mag[interior > 0]
    otsu_thr, _ = cv2.threshold(mag.astype(np.uint8), 0, 255,
                                cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mean = float(interior_mag.mean())
    thr = max(float(otsu_thr), mean * ridge_mean_mult, ridge_min_thr)
    ridge = ((mag > thr) & (interior > 0)).astype(np.uint8) * 255
    line_kernels = (
        np.ones((1, 7), np.uint8),
        np.ones((7, 1), np.uint8),
        np.diag([1, 1, 1, 1, 1, 1, 1]).astype(np.uint8),
        np.fliplr(np.diag([1, 1, 1, 1, 1, 1, 1]).astype(np.uint8)),
    )
    thin = np.zeros_like(ridge)
    for k in line_kernels:
        thin = np.maximum(thin, cv2.morphologyEx(ridge, cv2.MORPH_OPEN, k))
        thin = np.maximum(thin, cv2.morphologyEx(ridge, cv2.MORPH_CLOSE, k))
    density = cv2.countNonZero(thin) / max(1, cv2.countNonZero(interior))
    texture = float(np.std(vals))
    score = float(min(1.0, density * ridge_weight + max(0.0, texture - texture_base) / texture_scale))
    # Discount score when the object is too small for reliable interior analysis.
    # A fruit with 30% interior fraction is fully trusted; below that, the score
    # is scaled down linearly to avoid labelling edge artefacts as wrinkles.
    # Objects below 350px area almost never have a usable interior; cap score
    # aggressively so tiny leaf fragments are not mislabelled as wrinkled fruit.
    if unreliable or interior_fraction < int_frac_min or area < min_reliable_area:
        if area < min_reliable_area:
            discount = min(1.0, area / float(min_reliable_area) * interior_fraction / int_frac_min)
        else:
            discount = min(1.0, interior_fraction / int_frac_min)
        score *= discount
        unreliable = True
    if score < thr_smooth:
        label = "smooth"
    elif score < thr_slight:
        label = "slightly_wrinkled"
    elif score < thr_wrinkled:
        label = "wrinkled"
    else:
        label = "heavily_wrinkled"
    return {"wrinkle_score": round(score, 3), "ridge_density": round(density, 4),
            "wrinkle_label": label, "wrinkle_reliable": not unreliable}


def _grabcut_refine(image_bgr: np.ndarray, mask: np.ndarray, iterations: int = 3) -> np.ndarray:
    """Refine mask boundary using GrabCut."""
    h, w = mask.shape[:2]
    if cv2.countNonZero(mask) < 200:
        return mask
    coords = cv2.findNonZero(mask)
    if coords is None or len(coords) < 10:
        return mask
    x, y, bw, bh = cv2.boundingRect(coords)
    pad = 10
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1, y1 = min(w, x + bw + pad), min(h, y + bh + pad)
    rect = (x0, y0, x1 - x0, y1 - y0)

    gc_mask = np.full((h, w), cv2.GC_BGD, np.uint8)
    gc_mask[mask > 0] = cv2.GC_PR_FGD
    kernel = np.ones((5, 5), np.uint8)
    eroded = cv2.erode(mask, kernel, iterations=2)
    gc_mask[eroded > 0] = cv2.GC_FGD

    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(image_bgr, gc_mask, rect, bgd_model, fgd_model, iterations,
                    cv2.GC_INIT_WITH_MASK)
    except cv2.error:
        return mask
    result = np.where((gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    return result


def _edge_refine_mask(image_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Snap mask edges to real image edges via Canny."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    edges = _adaptive_canny(gray)
    ek = np.ones((3, 3), np.uint8)
    edge_band = cv2.dilate(edges, ek, iterations=2)
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    interior = cv2.inRange(dist, 3, 255)
    refined = cv2.bitwise_or(interior, cv2.bitwise_and(mask, edge_band))
    refined = cv2.morphologyEx(refined, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    return refined


def _adaptive_canny(gray: np.ndarray) -> np.ndarray:
    """Canny with thresholds derived from the frame's own gradient statistics.

    Otsu's method picks the gradient threshold, so low-contrast foliage edges
    are not lost to a fixed (50, 150) band.
    """
    grad8 = cv2.convertScaleAbs(cv2.Laplacian(gray, cv2.CV_64F))
    t, _ = cv2.threshold(grad8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    hi = max(35, min(200, int(round(t * 1.6))))
    lo = max(8, int(round(t * 0.5)))
    return cv2.Canny(gray, lo, hi)


def _snap_contour_to_edges(contour, gray: np.ndarray,
                           win: int = 3, min_grad: int = 80) -> np.ndarray:
    """Pull contour vertices toward strong image gradients (edge snapping).

    Each vertex is moved (at most 4 px) toward the gradient-weighted centroid
    of its neighbourhood, so the drawn outline follows the real object
    boundary instead of the puffy morphology mask edge. Only strong gradients
    are trusted, so smooth (no-edge) regions keep the original boundary.
    """
    sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad = cv2.magnitude(sobel_x, sobel_y)
    h, w = gray.shape
    pts = contour.reshape(-1, 2).astype(np.float32)
    snapped = []
    for (x, y) in pts:
        x0, y0 = int(round(x)), int(round(y))
        xs = slice(max(0, x0 - win), min(w, x0 + win + 1))
        ys = slice(max(0, y0 - win), min(h, y0 + win + 1))
        band = grad[ys, xs]
        peak = float(band.max()) if band.size else 0.0
        if peak > min_grad:
            weight = np.maximum(band - min_grad, 0).astype(np.float32)
            s = float(weight.sum())
            if s > 0:
                yy, xx = np.mgrid[ys.start:ys.stop, xs.start:xs.stop]
                nx = float((xx.astype(np.float32) * weight).sum() / s)
                ny = float((yy.astype(np.float32) * weight).sum() / s)
                dx, dy = nx - x, ny - y
                if dx * dx + dy * dy <= 16.0:
                    snapped.append((nx, ny))
                    continue
        snapped.append((x, y))
    out = np.asarray(snapped, dtype=np.float32).reshape(-1, 1, 2)
    # Light moving-average smoothing to remove per-vertex jitter.
    if out.shape[0] >= 6:
        k = 3
        smooth = out.reshape(-1, 2).copy()
        for i in range(out.shape[0]):
            idx = [(i + d) % out.shape[0] for d in (-k, 0, k)]
            smooth[i] = np.mean(out.reshape(-1, 2)[idx], axis=0)
        out = smooth.reshape(-1, 1, 2)
    return np.ascontiguousarray(out).astype(np.int32)


def _compute_shape_descriptors(contour) -> dict:
    """Hu moments, convexity defects, and extent."""
    area = cv2.contourArea(contour)
    perimeter = cv2.arcLength(contour, True)
    hull = cv2.convexHull(contour, returnPoints=False)
    hull_area = cv2.contourArea(cv2.convexHull(contour))
    x, y, w, h = cv2.boundingRect(contour)
    circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
    solidity = area / hull_area if hull_area > 0 else 0
    extent = area / (w * h) if (w * h) > 0 else 0
    hu = cv2.HuMoments(cv2.moments(contour)).flatten()
    hu_log = -np.sign(hu) * np.log10(np.abs(hu) + 1e-10)
    m = cv2.moments(contour)
    cx = m["m10"] / m["m00"] if m["m00"] > 0 else x + w / 2.0
    cy = m["m01"] / m["m00"] if m["m00"] > 0 else y + h / 2.0

    ellipse_ratio = 1.0
    if len(contour) >= 5:
        try:
            (_, _), (ma, mi), _ = cv2.fitEllipse(contour)
            lo, hi = min(ma, mi), max(ma, mi)
            if lo > 1e-3 and hi > 0:
                ellipse_ratio = round(float(hi / lo), 3)
        except cv2.error:
            pass

    defects = []
    if len(contour) > 5 and hull is not None and len(hull) > 3:
        try:
            defects_raw = cv2.convexityDefects(contour, hull)
            if defects_raw is not None:
                for i in range(defects_raw.shape[0]):
                    s, e, f, d = defects_raw[i, 0]
                    if d > 1000:
                        defects.append(d / 256.0)
        except Exception:
            pass

    return {
        "area": area, "perimeter": perimeter, "circularity": circularity,
        "solidity": solidity, "extent": extent, "aspect": w / max(1, h),
        "ellipse_axis_ratio": ellipse_ratio,
        "hu_moments": hu_log.tolist(),
        "mean_defect_depth": float(np.mean(defects)) if defects else 0.0,
        "num_defects": len(defects),
        "x": x, "y": y, "width": w, "height": h,
        "center_x": round(float(cx), 1), "center_y": round(float(cy), 1),
    }


def _compute_leaf_curl_score(desc: dict, cfg: dict) -> float:
    """Estimate leaf inward-curling (巻き込み) from contour geometry.

    A flat leaf fills its convex hull (solidity ~1) with few deep
    concavities. A curled leaf shows a narrow profile (high aspect ratio)
    and pronounced concavities where the blade rolls inward. The score
    combines three shape cues into a 0..1 value:

      0.00-0.09: flat,   0.10-0.24: slight_curl,
      0.25-0.49: curled, 0.50-1.00: heavily_curled
    """
    solidity = desc.get("solidity", 1.0)
    solidity_gap = 1.0 - solidity                                    # 0 = convex, 1 = very concave
    defect_depth = desc.get("mean_defect_depth", 0.0)
    area = max(1.0, desc.get("area", 1.0))
    radius = max(1.0, (area / 3.14159) ** 0.5)
    defect_ratio = min(1.0, defect_depth / radius * cfg.get("curl_defect_radius_scale", 0.5))
    aspect = desc.get("aspect", 1.0)
    baseline = cfg.get("curl_elongation_baseline", 1.2)
    scale = cfg.get("curl_elongation_scale", 4.0)
    elongation = min(1.0, max(0.0, aspect - baseline) / scale)
    ws = cfg.get("curl_weight_solidity", 0.30)
    wd = cfg.get("curl_weight_defect", 0.30)
    we = cfg.get("curl_weight_elongation", 0.40)
    score = ws * solidity_gap + wd * defect_ratio + we * elongation
    return round(min(1.0, score), 3)


def _curl_label(score: float, cfg: dict) -> str:
    flat = cfg.get("curl_threshold_flat", 0.10)
    slight = cfg.get("curl_threshold_slight", 0.25)
    curled = cfg.get("curl_threshold_curled", 0.50)
    if score < flat:
        return "flat"
    if score < slight:
        return "slight_curl"
    if score < curled:
        return "curled"
    return "heavily_curled"


def _watershed_split(image_bgr: np.ndarray, mask: np.ndarray,
                     min_dist: int = 20, fg_scale: float = 0.35) -> list:
    """Split touching blobs (e.g. clustered fruit) via the watershed transform."""
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    _, fg = cv2.threshold(dist, fg_scale * max(dist.max(), 1), 255, 0)
    fg = fg.astype(np.uint8)
    kernel = np.ones((3, 3), np.uint8)
    bg = cv2.dilate(mask, kernel, iterations=3)
    bg = cv2.subtract(bg, fg)
    _, markers = cv2.connectedComponents(fg)
    markers = markers + 1
    markers[bg == 255] = 0
    gray3 = cv2.cvtColor(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    markers = cv2.watershed(gray3, markers)
    masks = []
    for uid in np.unique(markers):
        if uid <= 1:
            continue
        m = (markers == uid).astype(np.uint8) * 255
        if cv2.countNonZero(m) >= 50:
            masks.append(m)
    return masks if masks else [mask]


def _hough_circles_fruit(gray: np.ndarray, min_radius: int = 8, max_radius: int = 80) -> list:
    """Detect circular fruit candidates via Hough Circle Transform."""
    blurred = cv2.medianBlur(gray, 5)
    circles = cv2.HoughCircles(
        blurred, cv2.HOUGH_GRADIENT, dp=1.2, minDist=25,
        param1=80, param2=40,
        minRadius=min_radius, maxRadius=max_radius)
    if circles is None:
        return []
    results = []
    for c in np.uint16(np.around(circles[0, :])):
        cx, cy, r = int(c[0]), int(c[1]), int(c[2])
        results.append((cx, cy, r))
    return results


def _circles_to_mask(circles: list, h: int, w: int) -> np.ndarray:
    """Convert list of (cx, cy, r) circles to a binary mask."""
    mask = np.zeros((h, w), np.uint8)
    for cx, cy, r in circles:
        cv2.circle(mask, (cx, cy), r, 255, -1)
    return mask


def _fg_mask_kmeans(image: np.ndarray, k: int = 3,
                    min_area_ratio: float = 0.005) -> np.ndarray:
    """K-means foreground mask: largest non-background cluster = foreground."""
    h, w = image.shape[:2]
    small = cv2.resize(image, (min(320, w), min(240, h)))
    pixels = small.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.2)
    _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 8, cv2.KMEANS_PP_CENTERS)
    label_map = labels.reshape(small.shape[:2])
    mean_bgr = np.mean(small.reshape((-1, 3)).astype(np.float64), axis=0)
    dists = [np.sqrt(np.sum((centers[i] - mean_bgr) ** 2)) for i in range(k)]
    fg_label = int(np.argmax(dists))
    fg_small = ((label_map == fg_label).astype(np.uint8)) * 255
    fg = cv2.resize(fg_small, (w, h), interpolation=cv2.INTER_NEAREST)
    min_area = h * w * min_area_ratio
    contours, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cleaned = np.zeros_like(fg)
    for c in contours:
        if cv2.contourArea(c) >= min_area:
            cv2.drawContours(cleaned, [c], -1, 255, -1)
    k_size = max(3, min(9, min(h, w) // 80))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_size, k_size))
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel, iterations=2)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel, iterations=1)
    return cleaned


def _fg_mask_grabcut(image: np.ndarray, iterations: int = 5,
                     min_area_ratio: float = 0.005) -> np.ndarray:
    """GrabCut foreground mask: segment the dominant foreground object."""
    h, w = image.shape[:2]
    margin = max(5, min(30, min(h, w) // 20))
    rect = (margin, margin, w - 2 * margin, h - 2 * margin)
    gc_mask = np.full((h, w), cv2.GC_BGD, np.uint8)
    bg_model = np.zeros((1, 65), np.float64)
    fg_model = np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(image, gc_mask, rect, bg_model, fg_model, iterations,
                    cv2.GC_INIT_WITH_RECT)
    except cv2.error:
        return np.zeros((h, w), np.uint8)
    fg = np.where((gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    min_area = h * w * min_area_ratio
    contours, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cleaned = np.zeros_like(fg)
    for c in contours:
        if cv2.contourArea(c) >= min_area:
            cv2.drawContours(cleaned, [c], -1, 255, -1)
    k_size = max(3, min(7, min(h, w) // 100))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_size, k_size))
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel, iterations=2)
    return cleaned


def _fg_mask_hsv_bgsub(image: np.ndarray, min_area_ratio: float = 0.005) -> np.ndarray:
    """HSV-based background subtraction: remove dark/desaturated background."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, w = image.shape[:2]
    bg_mask = cv2.inRange(hsv, (0, 0, 0), (180, 60, 80))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    bg_mask = cv2.morphologyEx(bg_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    bg_mask = cv2.morphologyEx(bg_mask, cv2.MORPH_OPEN, kernel, iterations=1)
    fg = cv2.bitwise_not(bg_mask)
    min_area = h * w * min_area_ratio
    contours, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cleaned = np.zeros_like(fg)
    for c in contours:
        if cv2.contourArea(c) >= min_area:
            cv2.drawContours(cleaned, [c], -1, 255, -1)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel, iterations=1)
    return cleaned


def _fg_mask_edge_flood(image: np.ndarray, min_area_ratio: float = 0.005) -> np.ndarray:
    """Edge-based flood fill: Canny edges + flood fill from center."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    edges = cv2.dilate(edges, k, iterations=2)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, k, iterations=3)
    h, w = edges.shape
    flood = edges.copy()
    mask = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(flood, mask, (w // 2, h // 2), 128)
    fg = ((flood != 128) & (flood != 255)).astype(np.uint8) * 255
    min_area = h * w * min_area_ratio
    contours, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cleaned = np.zeros_like(fg)
    for c in contours:
        if cv2.contourArea(c) >= min_area:
            cv2.drawContours(cleaned, [c], -1, 255, -1)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, k, iterations=2)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, k, iterations=1)
    return cleaned


def _adaptive_fg_mask(image: np.ndarray, spec: dict) -> np.ndarray:
    """Auto-select the best foreground mask based on image characteristics."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    contrast = float(np.std(gray))
    s_mean = float(np.mean(hsv[:, :, 1]))
    v_mean = float(np.mean(hsv[:, :, 2]))
    min_area = spec.get("fg_min_area_ratio", 0.005)

    if contrast > 55 and s_mean > 60:
        return _fg_mask_edge_flood(image, min_area)
    elif s_mean < 50 or v_mean < 80:
        return _fg_mask_hsv_bgsub(image, min_area)
    else:
        return _fg_mask_kmeans(image, k=3, min_area_ratio=min_area)


# ===================================================================
#  Simple centroid-based multi-object tracker
# ===================================================================

class _CentroidTracker:
    def __init__(self, max_age: int = 30):
        self.next_id = 1
        self.objects: Dict[int, np.ndarray] = {}
        self.disappeared: Dict[int, int] = {}
        self.max_age = max_age
        self.history: Dict[int, list] = {}

    def update(self, detections: List[Tuple[int, int, int, int]]) -> Dict[int, Tuple[int, int, int, int]]:
        """Register/deregister objects. Returns {track_id: (x,y,w,h)}."""
        if len(detections) == 0:
            for oid in list(self.disappeared.keys()):
                self.disappeared[oid] += 1
                if self.disappeared[oid] > self.max_age:
                    del self.objects[oid]
                    del self.disappeared[oid]
                    self.history.pop(oid, None)
            return self.objects.copy()

        input_centroids = []
        for (x, y, w, h) in detections:
            input_centroids.append((x + w // 2, y + h // 2))

        if len(self.objects) == 0:
            for i, det in enumerate(detections):
                self.objects[self.next_id] = det
                self.disappeared[self.next_id] = 0
                self.history[self.next_id] = [input_centroids[i]]
                self.next_id += 1
        else:
            track_ids = list(self.objects.keys())
            track_centroids = []
            for tid in track_ids:
                obj = self.objects[tid]
                track_centroids.append((obj[0] + obj[2] // 2, obj[1] + obj[3] // 2))

            D = np.zeros((len(track_ids), len(input_centroids)))
            for i, tc in enumerate(track_centroids):
                for j, ic in enumerate(input_centroids):
                    D[i, j] = np.sqrt((tc[0] - ic[0]) ** 2 + (tc[1] - ic[1]) ** 2)

            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]

            used_rows = set()
            used_cols = set()
            for (row, col) in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue
                if D[row, col] > 80:
                    continue
                tid = track_ids[row]
                self.objects[tid] = detections[col]
                self.disappeared[tid] = 0
                self.history[tid].append(input_centroids[col])
                used_rows.add(row)
                used_cols.add(col)

            for row in set(range(len(track_ids))) - used_rows:
                tid = track_ids[row]
                self.disappeared[tid] += 1
                if self.disappeared[tid] > self.max_age:
                    del self.objects[tid]
                    del self.disappeared[tid]
                    self.history.pop(tid, None)

            for col in set(range(len(input_centroids))) - used_cols:
                self.objects[self.next_id] = detections[col]
                self.disappeared[self.next_id] = 0
                self.history[self.next_id] = [input_centroids[col]]
                self.next_id += 1

        return self.objects.copy()


# ===================================================================
#  Analyzer
# ===================================================================

class Analyzer:
    def __init__(self, config: dict, resolution_mode: str = "auto"):
        """Initialize the analyzer.

        Args:
            config: Runtime configuration dict
            resolution_mode: "auto" (scale based on image width),
                           "normal" (no scaling),
                           "low" (force low-res scaling),
                           "very_low" (force very-low-res scaling)
        """
        self.config = config
        self.resolution_mode = resolution_mode

    def _adapt_for_resolution(self, image: np.ndarray) -> dict:
        """Return config scaled for the input image resolution."""
        if self.resolution_mode == "normal":
            return self.config
        w = image.shape[1]
        return scale_detection_for_resolution(self.config, w)

    def _resize(self, image: np.ndarray) -> np.ndarray:
        maximum = int(self.config["runtime"]["max_width"])
        if image.shape[1] <= maximum:
            return image
        # Isotropic scale so circles stay circular; otherwise a portrait
        # frame (e.g. 2160x2880) is squashed and Hough/circularity tests break.
        scale = maximum / image.shape[1]
        return cv2.resize(image, None, fx=scale, fy=scale,
                          interpolation=cv2.INTER_AREA)

    @staticmethod
    def _clean(mask: np.ndarray, size: int = 3) -> np.ndarray:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
        return cv2.morphologyEx(
            cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel), cv2.MORPH_CLOSE, kernel)

    @staticmethod
    def _classify_leaf_color(hue: float) -> str:
        if hue > 70: return "healthy_green"
        if hue > 50: return "dark_green"
        if hue > 35: return "yellow_green"
        if hue > 25: return "yellow"
        if hue > 15: return "brown"
        return "dead_brown"

    @staticmethod
    def _calculate_senescence(hue: float, saturation: float) -> float:
        hue_score = max(0.0, 1.0 - (hue / 90.0))
        sat_score = 1.0 - (saturation / 255.0)
        return round(min(100.0, max(0.0, (hue_score * 0.6 + sat_score * 0.4) * 100.0)), 1)

    @staticmethod
    def _classify_fruit_maturity(hue: float) -> str:
        if 30 <= hue <= 90: return "green"
        if 15 <= hue < 30: return "yellow_green"
        if 100 <= hue <= 135: return "purple"
        if hue < 15 or hue > 135: return "black"
        return "transitioning"

    @staticmethod
    def _detection_confidence(desc: dict, kind: str) -> float:
        circ = desc.get("circularity", 0)
        sol = desc.get("solidity", 0)
        aspect = desc.get("aspect", 1)
        circ_s = min(1.0, circ / 0.8)
        sol_s = min(1.0, sol / 0.9)
        if kind == "leaf":
            ar_s = 1.0 - min(0.5, abs(aspect - 2.5) / 4.0)
            return round(circ_s * 0.25 + sol_s * 0.35 + ar_s * 0.25, 3)
        ar_s = 1.0 - min(0.5, abs(aspect - 1.2) / 2.0)
        return round(circ_s * 0.35 + sol_s * 0.35 + ar_s * 0.15, 3)

    # ---- mask builders ----

    def _build_leaf_mask(self, image, hsv, lab, spec, fg_mask=None, edge_refine=True,
                         blur_level=0.0, drone_mode=False):
        """Multi-colorspace leaf mask: HSV + ExG + CGI + LAB + edge guidance.

        blur_level relaxes signal requirements in blurry frames where colour
        discrimination is weaker (fewer agreement signals + lower saturation floor).
        drone_mode enables aerial-specific enhancements: color normalization,
        adaptive thresholds, wider HSV ranges.
        """
        # --- Drone-specific preprocessing ---
        if drone_mode:
            # Color-normalize to reduce lighting variation
            image_norm = normalize_illumination(image)
            hsv = cv2.cvtColor(image_norm, cv2.COLOR_BGR2HSV)
            lab = cv2.cvtColor(image_norm, cv2.COLOR_BGR2LAB)
            # Wider HSV green range for aerial views (lighting varies more)
            hue_lo = max(25, spec["leaf_hue"][0] - 8)
            hue_hi = min(100, spec["leaf_hue"][1] + 8)
            sat_floor_val = max(18, spec["leaf_saturation_min"] - 12)
            val_floor = max(18, spec["leaf_value_min"] - 10)
        else:
            hue_lo, hue_hi = spec["leaf_hue"]
            sat_floor_val = spec["leaf_saturation_min"]
            val_floor = spec["leaf_value_min"]

        # 1. HSV green range. Saturation floor drops only in very blurry frames.
        relax = max(0.0, (blur_level - 0.5) * 2.0)          # 0..1 for blur>=0.5
        sat_floor = int(max(25 if not drone_mode else sat_floor_val,
                            sat_floor_val - relax * 25))
        hsv_mask = cv2.inRange(hsv,
                               (hue_lo, max(sat_floor, 25 if not drone_mode else 18), val_floor),
                               (hue_hi, 255, 255))
        # 2. Excess Green index (adaptive threshold for drone)
        exg = _compute_vegetation_index(image)
        if drone_mode:
            exg_thresh = compute_adaptive_green_threshold(
                image, base_min=spec.get("excess_green_min", 12), percentile=3)
        else:
            exg_thresh = spec.get("excess_green_min", 12)
        exg_mask = cv2.inRange(exg, exg_thresh, 255)
        # 3. CGI (Chlorophyll Green-Red Index)
        cgi = _compute_cgi(image)
        cgi_thresh = 155 if drone_mode else 165
        cgi_mask = cv2.inRange(cgi, cgi_thresh, 255)
        # 4. LAB a-channel (green<128<red) — wider range for drone
        lab_hi = 125 if drone_mode else 118
        lab_green = cv2.inRange(lab[:, :, 1], 0, lab_hi)
        # 5. YCrCb: green has low Cr
        ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
        ycrcb_hi = 140 if drone_mode else 130
        ycrcb_green = cv2.inRange(ycrcb[:, :, 1], 0, ycrcb_hi)

        # Fuse: HSV is required, at least N of {ExG, CGI, LAB, YCrCb} must agree.
        # Very blurry frames lose colour discrimination, so require fewer signals.
        # Drone mode: also relaxed signal count due to aerial noise.
        if drone_mode:
            required_signals = 1 if blur_level >= 0.5 else 2
        else:
            required_signals = 2 if blur_level < 0.75 else 1
        vegetation = cv2.bitwise_or(cv2.bitwise_or(exg_mask, cgi_mask),
                                    cv2.bitwise_or(lab_green, ycrcb_green))
        signals = np.zeros(hsv.shape[:2], np.uint8)
        signals = cv2.add(signals, (exg_mask > 0).astype(np.uint8))
        signals = cv2.add(signals, (cgi_mask > 0).astype(np.uint8))
        signals = cv2.add(signals, (lab_green > 0).astype(np.uint8))
        signals = cv2.add(signals, (ycrcb_green > 0).astype(np.uint8))
        multi_signal = cv2.inRange(signals, required_signals, 255)

        combined = cv2.bitwise_and(hsv_mask, cv2.bitwise_or(multi_signal, vegetation))

        # Morphological cleanup with elliptical kernel (smaller when blurry so
        # softened details survive)
        edge_k = max(3, spec.get("edge_close_kernel", 5) - (1 if blur_level >= 0.5 else 0))
        ekernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (edge_k, edge_k))
        combined = cv2.morphologyEx(combined, cv2.MORPH_DILATE, ekernel)
        clean_size = max(3, spec.get("adaptive_blur", 5))
        if drone_mode:
            clean_size = min(7, clean_size + 2)
        combined = self._clean(combined, size=clean_size)

        # Scale-aware secondary cleanup
        h, w = image.shape[:2]
        mk_size = max(3, min(7, int(min(h, w) / 150)))
        mk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (mk_size, mk_size))
        combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, mk)
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, mk)

        # Suppress very dark pixels (likely noise/shadow)
        v_floor = 10 if drone_mode else 15
        v_suppress = cv2.inRange(hsv[:, :, 2], v_floor, 255)
        combined = cv2.bitwise_and(combined, v_suppress)

        # Foreground constraint: if fg_mask provided, only keep leaf within foreground
        if fg_mask is not None:
            combined = cv2.bitwise_and(combined, fg_mask)

        # Edge-guided refinement (skipped in blurry frames to preserve soft edges)
        if edge_refine and spec.get("edge_refine", True):
            combined = _edge_refine_mask(image, combined)

        # Fill small holes (larger kernel for drone to merge fragmented regions)
        fill_k = 9 if drone_mode else 7
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE,
                                     cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (fill_k, fill_k)))
        return combined

    def _build_fruit_mask(self, image, hsv, lab, leaf_mask, spec, fg_mask=None,
                          blur_level=0.0, drone_mode=False):
        """Multi-signal fruit mask: HSV yellow-green + ripe + Hough circles.

        blur_level lowers the saturation/LAB floors so desaturated, blurred
        fruit still registers (only for genuinely blurry frames).
        drone_mode relaxes thresholds for aerial images.
        """
        relax = max(0.0, (blur_level - 0.5) * 2.0)          # 0..1 for blur>=0.5
        sat_relax = 15 if drone_mode else 0
        lab_relax = 20 if drone_mode else 0
        sat_floor = int(max(35 if drone_mode else 50,
                            spec["fruit_saturation_min"] - relax * 25 - sat_relax))
        lab_b_floor = int(max(90 if drone_mode else 110,
                              spec.get("fruit_lab_b_min", 145) - relax * 30 - lab_relax))
        yellow_green = cv2.inRange(hsv,
                                   (spec["fruit_hue_yellow"][0], sat_floor, spec["fruit_value_min"]),
                                   (spec["fruit_hue_yellow"][1], 255, 255))
        yellow_green = cv2.bitwise_and(yellow_green, cv2.inRange(hsv[:, :, 1], 70 - int(relax * 20), 255))
        yellow_green = cv2.bitwise_and(yellow_green, cv2.inRange(lab[:, :, 2], lab_b_floor, 255))
        ripe_sat = 110 - int(relax * 25)
        ripe = cv2.inRange(hsv, (spec["fruit_hue_ripe"][0], max(60, ripe_sat), 55),
                           (spec["fruit_hue_ripe"][1], 255, 220))
        dark_ripe = cv2.inRange(hsv, (105, 85 - int(relax * 20), 25), (175, 255, 55))

        fruit = self._clean(yellow_green | ripe | dark_ripe)
        safe_leaf = cv2.bitwise_and(leaf_mask, cv2.bitwise_not(yellow_green))
        fruit = cv2.bitwise_and(fruit, cv2.bitwise_not(safe_leaf))

        # Foreground constraint: if fg_mask provided, only keep fruit within foreground
        if fg_mask is not None:
            fruit = cv2.bitwise_and(fruit, fg_mask)

        # Hough circle mask overlay: boost fruit regions that contain circles.
        # Foliage blobs without circle evidence are dropped, EXCEPT for blobs
        # that are self-evidently fruit (round + smooth). Without this, real
        # fruit whose circle was missed (clipped by the frame edge, partial
        # shadow) would be erased along with the foliage.
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        circles = _hough_circles_fruit(gray)
        if circles:
            circle_mask = _circles_to_mask(circles, image.shape[0], image.shape[1])
            circle_fruit = cv2.bitwise_and(fruit, circle_mask)
            dilated_circles = cv2.dilate(circle_mask, np.ones((5, 5), np.uint8))
            near_circle = cv2.bitwise_and(fruit, dilated_circles)
            # Blur hides texture and invents smoothness, so the self-evident
            # rescue (smoothness + convexity) is only trusted on sharp frames.
            if blur_level < 0.5:
                se = np.zeros_like(fruit)
                if cv2.countNonZero(near_circle) > 0:
                    far_fruit = cv2.bitwise_and(fruit, cv2.bitwise_not(dilated_circles))
                    nf, labels, stats, _ = cv2.connectedComponentsWithStats(far_fruit)
                    for i in range(1, nf):
                        x, y, w, h, area = stats[i]
                        if area < spec.get("fruit_no_circle_min_area", 200):
                            continue
                        if area > spec.get("fruit_no_circle_max_area", 4000):
                            continue
                        blob = (labels == i).astype(np.uint8) * 255
                        cts, _ = cv2.findContours(blob, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        c = max(cts, key=cv2.contourArea)
                        per = cv2.arcLength(c, True)
                        circ = 4 * np.pi * area / max(1.0, per * per)
                        solid = area / max(1.0, cv2.contourArea(cv2.convexHull(c)))
                        gstd = _compute_internal_texture(gray, blob)
                        if (gstd <= spec.get("fruit_no_circle_max_std", 45.0)
                                and (circ >= spec.get("fruit_no_circle_min_circularity", 0.65)
                                     or solid >= spec.get("fruit_no_circle_min_solidity", 0.88))):
                            se[blob > 0] = 255
                fruit = cv2.bitwise_or(near_circle, se)
            else:
                fruit = near_circle

        h, w = image.shape[:2]
        mk_size = max(3, min(5, int(min(h, w) / 200)))
        mk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (mk_size, mk_size))
        fruit = cv2.morphologyEx(fruit, cv2.MORPH_OPEN, mk)
        fruit = cv2.morphologyEx(fruit, cv2.MORPH_CLOSE, mk)

        contours_f, _ = cv2.findContours(fruit, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        img_area = h * w
        for c in contours_f:
            area = cv2.contourArea(c)
            if area < spec.get("fruit_min_area", 120) * 0.5:
                cv2.drawContours(fruit, [c], -1, 0, -1)
            elif area > img_area * 0.30:
                cv2.drawContours(fruit, [c], -1, 0, -1)
        return fruit

    def _filter_contours(self, contours, kind, spec, hsv_img=None, image_bgr=None,
                         blur_level=0.0, sharp_map=None):
        """Filter contours by size, shape, edge density, and colour consistency.

        blur_level in [0,1]: 1 = very blurry. When blurry, edge evidence is
        unreliable, so edge_density weight is reduced in the confidence score.
        Per-object blur is measured on the contour's boundary gradient, scaled
        against the sharpest edges in the same frame, and floored by the global
        blur_level (so fully-blurry frames are not fooled by self-scaling).

        Returns (accepted, trace) where trace records every candidate considered
        and, if rejected, the specific test-category name that failed.
        """
        accepted = []
        trace = []                      # per-candidate: accepted or (reason)
        edge_weight = max(0.0, 0.25 - blur_level * 0.15)
        gray_ftr = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY) if image_bgr is not None else None
        for c in contours:
            desc = _compute_shape_descriptors(c)
            area = desc["area"]
            reject = None               # set to the first failing criterion name
            if kind == "leaf":
                if area < spec["leaf_min_area"] or area > spec["leaf_max_area"]:
                    reject = "area"
                elif not spec["leaf_min_aspect"] <= desc["aspect"] <= spec["leaf_max_aspect"]:
                    reject = "aspect"
                elif desc["solidity"] < spec["leaf_min_solidity"]:
                    reject = "solidity"
            else:
                if area < spec["fruit_min_area"] or area > spec["fruit_max_area"]:
                    reject = "area"
                elif not spec["fruit_min_aspect"] <= desc["aspect"] <= spec["fruit_max_aspect"]:
                    reject = "aspect"
                elif desc["solidity"] < spec["fruit_min_solidity"]:
                    reject = "solidity"
                elif desc["circularity"] < spec["fruit_min_circularity"]:
                    reject = "circularity"
                # Real olives are near-round; elongated leaf clusters and stems
                # masquerading as fruit are rejected by the fitted-ellipse ratio.
                if reject is None and desc["ellipse_axis_ratio"] > spec.get("fruit_max_ellipse_ratio", 1.5):
                    reject = "ellipse_ratio"
                # Fruit surfaces are smooth; textured foliage blobs are rejected.
                # (Blurred frames are uniformly smooth, so this is inert there.)
                if reject is None and gray_ftr is not None and area > 100:
                    m = np.zeros(gray_ftr.shape[:2], np.uint8)
                    cv2.drawContours(m, [c], -1, 255, -1)
                    gstd = _compute_internal_texture(gray_ftr, m)
                    desc["internal_texture"] = round(gstd, 1)
                    if gstd > spec.get("fruit_max_internal_std", 40.0):
                        reject = "internal_texture"
            if reject is not None:
                trace.append({"x": desc["center_x"], "y": desc["center_y"],
                              "area": int(area), "rejected": True, "reason": reject})
                continue
            desc["confidence"] = self._detection_confidence(desc, kind)
            # Per-object blur: if the band around the contour touches a sharp
            # block of the sharpness map, the object is in focus. The band is
            # sized to absorb the mask dilation offset. The local estimate only
            # contributes when the frame is genuinely blurry; typical photos keep
            # the global (≈0) value so confidence scoring is unchanged.
            obj_blur = blur_level
            if blur_level >= 0.5 and sharp_map is not None and area > 100:
                m = np.zeros(sharp_map.shape[:2], np.uint8)
                cv2.drawContours(m, [c], -1, 255, -1)
                band_w = max(15, min(45, int(2 * np.sqrt(area / np.pi))))
                band = cv2.subtract(cv2.dilate(m, np.ones((band_w, band_w), np.uint8)), m)
                vals = sharp_map[band > 0]
                if vals.size > 8:
                    peak = float(np.max(vals))
                    obj_blur = round(min(1.0, max(blur_level, 1.0 - peak)), 3)
            edge_weight = max(0.0, 0.25 - obj_blur * 0.15)
            if hsv_img is not None and area > 100:
                m = np.zeros(hsv_img.shape[:2], np.uint8)
                cv2.drawContours(m, [c], -1, 255, -1)
                hue_vals = hsv_img[:, :, 0][m > 0]
                if len(hue_vals) > 10:
                    hue_std = float(np.std(hue_vals))
                    desc["color_consistency"] = round(1.0 - min(1.0, hue_std / 50.0), 3)
                else:
                    desc["color_consistency"] = 0.0
            else:
                desc["color_consistency"] = 0.0
            # Edge density: higher means the contour aligns with real image edges
            if image_bgr is not None and area > 200:
                m = np.zeros(image_bgr.shape[:2], np.uint8)
                cv2.drawContours(m, [c], -1, 255, -1)
                desc["edge_density"] = round(_compute_edge_density(image_bgr, m), 3)
            else:
                desc["edge_density"] = 0.0
            # Adjust confidence with edge density and colour consistency.
            # Edge weight drops in blurry regions where edges are unreliable.
            if kind == "leaf":
                base_w = 0.5 + obj_blur * 0.10
                desc["confidence"] = round(min(1.0,
                    desc["confidence"] * base_w
                    + desc.get("color_consistency", 0) * 0.25
                    + desc.get("edge_density", 0) * edge_weight), 3)
            else:
                base_w = 0.45 + obj_blur * 0.10
                desc["confidence"] = round(min(1.0,
                    desc["confidence"] * base_w
                    + desc.get("color_consistency", 0) * 0.25
                    + desc.get("edge_density", 0) * min(edge_weight + 0.05, 0.30)), 3)
            desc["blur_level"] = round(obj_blur, 3)
            desc["contour"] = c
            trace.append({"kind": kind, "area": int(area),
                          "x": desc["center_x"], "y": desc["center_y"],
                          "rejected": None, "reason": None})
            accepted.append(desc)
        return accepted, trace

    def _split_large_components(self, mask: np.ndarray, image_bgr: np.ndarray,
                                max_area: int) -> np.ndarray:
        """Decompose oversized mask components (dense foliage canopy) into
        leaf-sized clusters so the area gate can count them instead of
        rejecting the whole region.

        A canopy of overlapping leaves often forms one connected blob of
        0.4-1.3M px that exceeds leaf_max_area and is discarded wholesale.
        Splitting such blobs with the distance-transform watershed yields
        distinct leaf-like clusters; small components pass through untouched.
        """
        n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
        if n <= 1:
            return mask
        out = np.zeros_like(mask)
        for lab in range(1, n):
            area = stats[lab, cv2.CC_STAT_AREA]
            if area > max_area:
                comp = ((labels == lab).astype(np.uint8)) * 255
                for piece in _watershed_split(image_bgr, comp):
                    out[piece > 0] = 255
            else:
                out[labels == lab] = 255
        return out

    @staticmethod
    def _merge_multiscale(contour_area_pairs, iou_threshold=0.35):
        if not contour_area_pairs:
            return []
        pairs = sorted(contour_area_pairs, key=lambda p: p[1], reverse=True)
        keep, used = [], set()
        for i, (c_i, a_i) in enumerate(pairs):
            if i in used:
                continue
            xi, yi, wi, hi = cv2.boundingRect(c_i)
            keep.append(c_i)
            for j, (c_j, _) in enumerate(pairs[i + 1:], start=i + 1):
                if j in used:
                    continue
                xj, yj, wj, hj = cv2.boundingRect(c_j)
                xa, ya = max(xi, xj), max(yi, yj)
                xb, yb = min(xi + wi, xj + wj), min(yi + hi, yj + hj)
                inter = max(0, xb - xa) * max(0, yb - ya)
                union = wi * hi + wj * hj - inter
                if union > 0 and inter / union > iou_threshold:
                    used.add(j)
        return keep

    # ---- main analyze ----

    def analyze(self, image: np.ndarray, source: str,
                image_path: Optional[str] = None) -> Tuple[dict, np.ndarray]:
        image = self._resize(image)
        adapted = self._adapt_for_resolution(image)
        spec = adapted["detection"]
        blur_raw = _estimate_blur(image)
        # Laplacian variance is low for smooth matte foliage even when in focus,
        # so only genuinely blurry frames should be treated as blurry.
        # blur_raw >= 180 -> 0 (sharp/typical), 20 -> ~1.0 (very blurry).
        blur_level = round(min(1.0, max(0.0, (180.0 - blur_raw) / 160.0)), 3)
        # In blurry frames, skip the aggressive edge-snapping refinement so
        # soft boundaries of blurred objects are not eroded away.
        edge_refine = spec.get("edge_refine", True) and blur_level < 0.75
        sharp_map = _local_sharpness_map(image, block=48)
        # Global deblur only when the whole frame is uniformly blurry; a mixed
        # (partly sharp) frame would get its sharp regions degraded by halos.
        uniform_blurry = (blur_level > 0.15 and blur_raw >= spec.get("deblur_min_blur_raw", 5.0)
                          and not _is_mixed_focus(image))
        processed = _adaptive_preprocess(image, spec.get("adaptive_blur", 5),
                                         deblur=uniform_blurry, blur_score=blur_raw)
        # Region-aware deblur: locally out-of-focus parts get strong sharpening,
        # sharp parts are left untouched. Runs only for mixed-focus frames.
        processed = _deblur_adaptive(processed, blur_level, sharp_map)
        hsv = cv2.cvtColor(processed, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(processed, cv2.COLOR_BGR2LAB)

        # === FOREGROUND MASK (optional, based on detect_mode) ===
        detect_mode = spec.get("detect_mode", "multi_signal")
        fg_mask = None
        if detect_mode == "kmeans":
            fg_mask = _fg_mask_kmeans(processed, k=spec.get("fg_kmeans_clusters", 3),
                                       min_area_ratio=spec.get("fg_min_area_ratio", 0.005))
        elif detect_mode == "grabcut":
            fg_mask = _fg_mask_grabcut(processed, iterations=spec.get("fg_grabcut_iter", 5),
                                        min_area_ratio=spec.get("fg_min_area_ratio", 0.005))
        elif detect_mode == "bg_removal":
            fg_mask = _fg_mask_hsv_bgsub(processed, min_area_ratio=spec.get("fg_min_area_ratio", 0.005))
        elif detect_mode == "edge_flood":
            fg_mask = _fg_mask_edge_flood(processed, min_area_ratio=spec.get("fg_min_area_ratio", 0.005))
        elif detect_mode == "adaptive":
            fg_mask = _adaptive_fg_mask(processed, spec)

        # === LEAF ===
        is_drone = adapted.get("_resolution_mode", "normal") in ("low", "very_low")
        leaf_mask = self._build_leaf_mask(processed, hsv, lab, spec, fg_mask,
                                          edge_refine=edge_refine, blur_level=blur_level,
                                          drone_mode=is_drone)
        # A dense canopy is one giant component far above leaf_max_area; split
        # it into leaf-sized clusters before contour extraction.
        leaf_mask = self._split_large_components(
            leaf_mask, processed, spec.get("leaf_max_area", 30000))
        scales = spec.get("multiscale_scales", [0.75, 1.0, 1.3])
        all_leaf = []
        for scale in scales:
            sf = 1.0 / scale if abs(scale - 1.0) > 0.01 else 1.0
            scaled = leaf_mask if sf == 1.0 else cv2.resize(leaf_mask, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
            _, scaled = cv2.threshold(scaled, 127, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(scaled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in contours:
                a = cv2.contourArea(c) * (scale ** 2)
                c_s = (c.astype(np.float64) * (1.0 / scale)).astype(np.int32)
                all_leaf.append((c_s, a))
        leaf_contours = self._merge_multiscale(all_leaf)
        leaf_descs, leaf_trace = self._filter_contours(leaf_contours, "leaf", spec, hsv, image,
                                            blur_level, sharp_map)
        leaf_boxes = [(d["x"], d["y"], d["width"], d["height"]) for d in leaf_descs]
        leaf_count = len(leaf_descs)

        leaf_hues, leaf_sats = [], []
        for d in leaf_descs:
            m = np.zeros(leaf_mask.shape, np.uint8)
            cv2.drawContours(m, [d["contour"]], -1, 255, -1)
            hue_val = float(cv2.mean(hsv[:, :, 0], mask=m)[0])
            sat_val = float(cv2.mean(hsv[:, :, 1], mask=m)[0])
            leaf_hues.append(hue_val)
            leaf_sats.append(sat_val)
            d["hue"] = round(hue_val, 1)
            d["saturation"] = round(sat_val, 1)
        avg_lh = float(np.mean(leaf_hues)) if leaf_hues else 0.0
        avg_ls = float(np.mean(leaf_sats)) if leaf_sats else 0.0
        avg_lc = float(np.mean([d["confidence"] for d in leaf_descs])) if leaf_descs else 0.0
        leaf_stage = self._classify_leaf_color(avg_lh)
        leaf_senes = self._calculate_senescence(avg_lh, avg_ls)

        # Leaf curling (巻き込み): roll inward to reduce transpiration.
        # Computed from contour shape (solidity gap + convexity defects + aspect).
        for d in leaf_descs:
            d["curl_score"] = _compute_leaf_curl_score(d, adapted["detection"])
            d["curl_label"] = _curl_label(d["curl_score"], adapted["detection"])
        curl_scores = [d["curl_score"] for d in leaf_descs] if leaf_descs else []
        avg_curl = float(np.mean(curl_scores)) if curl_scores else 0.0
        # Fraction of leaves exhibiting significant curling (score >= 0.25).
        curled_pct = round(float(sum(1 for c in curl_scores if c >= 0.25) / max(1, len(curl_scores)) * 100), 1)

        # === FRUIT ===
        fruit_mask = self._build_fruit_mask(processed, hsv, lab, leaf_mask, spec, fg_mask,
                                            blur_level=blur_level, drone_mode=is_drone)
        fruit_masks_ind = _watershed_split(processed, fruit_mask,
                                           min_dist=spec.get("watershed_mindist", 20))
        all_fruit_contours = []
        for fm in fruit_masks_ind:
            sub_c, _ = cv2.findContours(fm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            all_fruit_contours.extend(sub_c)
        fruit_descs, fruit_trace = self._filter_contours(all_fruit_contours, "fruit", spec, hsv, image,
                                            blur_level, sharp_map)
        fruit_boxes = [(d["x"], d["y"], d["width"], d["height"]) for d in fruit_descs]
        fruit_count = len(fruit_descs)

        # Coverage of the *accepted* fruit regions (drawn masks), not the raw mask.
        fruit_det_mask = np.zeros(fruit_mask.shape, np.uint8)
        for d in fruit_descs:
            cv2.drawContours(fruit_det_mask, [d["contour"]], -1, 255, -1)

        fruit_hues, fruit_sats, fruit_b = [], [], []
        fruit_maturity_counts = {}
        fruit_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        wrinkled_fruit_count = 0
        unreliable_wrinkle_count = 0
        # Re-derive the raw colour bands and circle mask purely to attribute
        # each accepted fruit to the signal that proved it (for explanations).
        relax = max(0.0, (blur_level - 0.5) * 2.0)
        sat_floor = int(max(50, spec["fruit_saturation_min"] - relax * 25))
        lab_b_floor = int(max(110, spec.get("fruit_lab_b_min", 145) - relax * 30))
        ev_yellow = cv2.inRange(hsv, (spec["fruit_hue_yellow"][0], sat_floor, spec["fruit_value_min"]),
                                (spec["fruit_hue_yellow"][1], 255, 255))
        ev_ripe = cv2.inRange(hsv, (spec["fruit_hue_ripe"][0], max(60, 110 - int(relax * 25)), 55),
                              (spec["fruit_hue_ripe"][1], 255, 220))
        ev_dark = cv2.inRange(hsv, (105, 85 - int(relax * 20), 25), (175, 255, 55))
        ev_circles = _hough_circles_fruit(fruit_gray)
        ev_circle_mask = _circles_to_mask(ev_circles, fruit_mask.shape[0], fruit_mask.shape[1])

        for d in fruit_descs:
            m = np.zeros(fruit_mask.shape, np.uint8)
            cv2.drawContours(m, [d["contour"]], -1, 255, -1)
            x0, y0, w0, h0 = cv2.boundingRect(d["contour"])
            d["edge_touch"] = (x0 <= 0 or y0 <= 0
                               or x0 + w0 >= fruit_mask.shape[1] - 1
                               or y0 + h0 >= fruit_mask.shape[0] - 1)
            hue = float(cv2.mean(hsv[:, :, 0], mask=m)[0])
            sat = float(cv2.mean(hsv[:, :, 1], mask=m)[0])
            bval = float(cv2.mean(lab[:, :, 2], mask=m)[0])
            fruit_hues.append(hue)
            fruit_sats.append(sat)
            fruit_b.append(bval)
            stage = self._classify_fruit_maturity(hue)
            d["maturity"] = stage
            d["hue"] = round(hue, 1)
            d["saturation"] = round(sat, 1)
            d["lab_b"] = round(bval, 1)
            wr = _compute_wrinkle_score(fruit_gray, m, cfg=adapted.get("detection", {}))
            d["wrinkle_score"] = wr["wrinkle_score"]
            d["wrinkle_label"] = wr["wrinkle_label"]
            d["wrinkle_reliable"] = wr.get("wrinkle_reliable", True)
            d["ridge_density"] = wr["ridge_density"]
            if wr["wrinkle_score"] >= 0.45:
                wrinkled_fruit_count += 1
                if not wr.get("wrinkle_reliable", True):
                    unreliable_wrinkle_count += 1
            fruit_maturity_counts[stage] = fruit_maturity_counts.get(stage, 0) + 1

            # Attribute signals that overlap this fruit, with measurable ratios.
            npx = max(1, cv2.countNonZero(m))
            ratios = {
                "yellow_green": round(cv2.countNonZero(cv2.bitwise_and(m, ev_yellow)) / npx, 3),
                "ripe": round(cv2.countNonZero(cv2.bitwise_and(m, ev_ripe)) / npx, 3),
                "dark": round(cv2.countNonZero(cv2.bitwise_and(m, ev_dark)) / npx, 3),
                "hough_circle": round(cv2.countNonZero(cv2.bitwise_and(m, ev_circle_mask)) / npx, 3),
            }
            d["signal_ratios"] = ratios
            evidence = []
            for key, label in FRUIT_SIGNAL_LABELS.items():
                if ratios[key] > FRUIT_SIGNAL_THRESHOLDS[key]:
                    evidence.append(label)
            d["detect_evidence"] = evidence if evidence else ["nearest colour-run"]
            # Fruits backed by no strong signal are false-positive candidates:
            # a blob can slip through the shape tests on colour alone. Keep it in
            # the report (so nothing is silently hidden) but drop its confidence
            # so the health verdict does not over-count weak detections.
            if not evidence:
                d["confidence"] = round(d["confidence"] * 0.5, 3)
                d["low_signal"] = True
            else:
                d["low_signal"] = False
        avg_fh = float(np.mean(fruit_hues)) if fruit_hues else 0.0
        avg_fc = float(np.mean([d["confidence"] for d in fruit_descs])) if fruit_descs else 0.0
        fruit_mat = self._classify_fruit_maturity(avg_fh)

        # === TEXTURE ===
        leaf_roughness = 0.0
        if leaf_descs:
            lm = np.zeros(image.shape[:2], np.uint8)
            for d in leaf_descs:
                cv2.drawContours(lm, [d["contour"]], -1, 255, -1)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            lap = cv2.Laplacian(gray, cv2.CV_64F)
            leaf_roughness = round(float(np.std(lap[lm > 0])), 2) if np.any(lm > 0) else 0.0

        # === ANNOTATE ===
        annotated = image.copy()
        gray_ann = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        def _draw_object(d, color, tag, snap):
            """Fill the object's precise (edge-snapped) contour, outline it, and
            draw a small label. Snapping only affects the drawing; the mask-based
            metrics and counts are unchanged."""
            contour = _snap_contour_to_edges(d["contour"], gray_ann) if snap else d["contour"]
            m = np.zeros(image.shape[:2], np.uint8)
            cv2.drawContours(m, [contour], -1, 255, -1)
            overlay = annotated.copy()
            cv2.drawContours(overlay, [contour], -1, color, -1)
            annotated[...] = cv2.addWeighted(overlay, 0.35, annotated, 0.65, 0)[...]
            cv2.drawContours(annotated, [contour], -1, color, 1, cv2.LINE_AA)
            x, y, w, h = cv2.boundingRect(contour)
            label = f"{tag}{d['confidence']:.0%}"
            cv2.putText(annotated, label, (x, max(14, y - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)

        for d in leaf_descs:
            _draw_object(d, (50, 220, 50), "L", snap=True)
        for d in fruit_descs:
            _draw_object(d, (0, 150, 255), "F", snap=True)

        label = f"Leaves:{leaf_count}  Fruits:{fruit_count}"
        cv2.putText(annotated, label, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(annotated, label, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 30, 30), 1)
        gp = round(float(np.count_nonzero(leaf_mask)) / leaf_mask.size * 100, 1)
        mode_label = detect_mode.replace("_", " ").title()
        sub = f"Green:{gp}%  Leaf:{leaf_stage}  Fruit:{fruit_mat}  Mode:{mode_label}"
        cv2.putText(annotated, sub, (12, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        cv2.putText(annotated, sub, (12, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (30, 30, 30), 1)
        # QR tree ID annotation.
        if spec.get("qr_detection", True):
            tree_id = _detect_qr_tree_id(image)
        else:
            tree_id = None
        if tree_id:
            qr_label = f"Tree: {tree_id}"
            cv2.putText(annotated, qr_label, (12, 76), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(annotated, qr_label, (12, 76), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 1)

        green_pct = round(float(np.count_nonzero(leaf_mask)) / leaf_mask.size * 100, 2)
        fruit_pct = round(float(np.count_nonzero(fruit_det_mask)) / fruit_det_mask.size * 100, 2)
        leaf_objects = [{
            "confidence": d["confidence"], "area": int(d["area"]),
            "aspect": round(d.get("aspect", 0), 2), "solidity": round(d.get("solidity", 0), 2),
            "ellipse_axis_ratio": round(d.get("ellipse_axis_ratio", 1.0), 2),
            "num_defects": d.get("num_defects", 0),
            "mean_defect_depth": round(d.get("mean_defect_depth", 0.0), 1),
            "curl_score": d.get("curl_score", 0.0),
            "curl_label": d.get("curl_label", "flat"),
            "hue": d.get("hue", 0.0), "saturation": d.get("saturation", 0.0),
            "color_consistency": d.get("color_consistency", 0.0),
            "edge_density": d.get("edge_density", 0.0), "blur_level": d.get("blur_level", 0.0),
            "center_x": round(d.get("center_x", 0.0), 1),
            "center_y": round(d.get("center_y", 0.0), 1),
            "_contour": d["contour"],
        } for d in leaf_descs]
        fruit_objects = [{
            "confidence": d["confidence"], "area": int(d["area"]),
            "aspect": round(d.get("aspect", 0), 2), "solidity": round(d.get("solidity", 0), 2),
            "circularity": round(d.get("circularity", 0), 2),
            "ellipse_axis_ratio": round(d.get("ellipse_axis_ratio", 1.0), 2),
            "color_consistency": d.get("color_consistency", 0.0),
            "edge_density": d.get("edge_density", 0.0), "blur_level": d.get("blur_level", 0.0),
            "internal_texture": d.get("internal_texture", 0.0),
            "hue": round(d.get("hue", 0.0), 1), "saturation": d.get("saturation", 0.0),
            "lab_b": d.get("lab_b", 0.0), "maturity": d.get("maturity", "unknown"),
            "center_x": round(d.get("center_x", 0.0), 1),
            "center_y": round(d.get("center_y", 0.0), 1),
            "wrinkle_score": d.get("wrinkle_score", 0.0),
            "wrinkle_label": d.get("wrinkle_label", "smooth"),
            "wrinkle_reliable": d.get("wrinkle_reliable", True),
            "ridge_density": d.get("ridge_density", 0.0),
            "detect_evidence": d.get("detect_evidence", []),
            "signal_ratios": d.get("signal_ratios", {}),
            "edge_touch": bool(d.get("edge_touch", False)),
            "low_signal": bool(d.get("low_signal", False)),
        } for d in fruit_descs]
        result = {
            "observed_at": now(), "source": source, "image_path": image_path,
            "tree_id": tree_id,
            "resolution_mode": adapted.get("_resolution_mode", "normal"),
            "resolution_scale": adapted.get("_resolution_scale", 1.0),
            "leaf_count": leaf_count, "fruit_count": fruit_count, "green_coverage": green_pct,
            "image_width": int(image.shape[1]), "image_height": int(image.shape[0]),
            "leaf_color_stage": leaf_stage, "leaf_senescence": leaf_senes,
            "leaf_avg_hue": round(avg_lh, 1), "leaf_avg_saturation": round(avg_ls, 1),
            "leaf_avg_area": round(float(np.mean([d["area"] for d in leaf_descs])), 1) if leaf_descs else 0.0,
            "leaf_confidence": round(avg_lc, 3),
            "fruit_maturity": fruit_mat, "fruit_maturity_breakdown": fruit_maturity_counts,
            "wrinkled_fruit_count": wrinkled_fruit_count,
            "unreliable_wrinkle_count": unreliable_wrinkle_count,
            "fruit_wrinkle_summary": {
                "smooth": sum(1 for d in fruit_descs if d.get("wrinkle_label") == "smooth"),
                "slightly_wrinkled": sum(1 for d in fruit_descs if d.get("wrinkle_label") == "slightly_wrinkled"),
                "wrinkled": sum(1 for d in fruit_descs if d.get("wrinkle_label") == "wrinkled"),
                "heavily_wrinkled": sum(1 for d in fruit_descs if d.get("wrinkle_label") == "heavily_wrinkled"),
            },
            "fruit_avg_hue": round(avg_fh, 1),
            "fruit_avg_area": round(float(np.mean([d["area"] for d in fruit_descs])), 1) if fruit_descs else 0.0,
            "fruit_confidence": round(avg_fc, 3),
            "leaf_total_area": int(np.count_nonzero(leaf_mask)),
            "fruit_total_area": int(np.count_nonzero(fruit_det_mask)),
            "fruit_cover_pct": fruit_pct,
            "leaf_roughness": leaf_roughness,
            "leaf_curl_index": round(avg_curl, 3),
            "curled_leaf_pct": curled_pct,
            "detect_mode": detect_mode,
            "blur_score": round(blur_raw, 1), "blur_level": blur_level,
            "leaf_objects": leaf_objects, "fruit_objects": fruit_objects,
            "leaf_boxes": leaf_boxes, "fruit_boxes": fruit_boxes,
            "leaf_mask": leaf_mask, "fruit_mask": fruit_mask,
            "fruit_thresholds": {
                "min_area": spec.get("fruit_min_area", 120),
                "max_area": spec.get("fruit_max_area", 18000),
                "min_aspect": spec.get("fruit_min_aspect", 0.45),
                "max_aspect": spec.get("fruit_max_aspect", 2.4),
                "min_solidity": spec.get("fruit_min_solidity", 0.72),
                "min_circularity": spec.get("fruit_min_circularity", 0.50),
                "max_ellipse_ratio": spec.get("fruit_max_ellipse_ratio", 3.5),
                "max_internal_std": spec.get("fruit_max_internal_std", 40.0),
            },
            "signal_thresholds": dict(FRUIT_SIGNAL_THRESHOLDS),
            "pipeline_diagnostics": _pipeline_diagnostics(
                leaf_trace, fruit_trace, fruit_det_mask,
                ev_yellow, ev_ripe, ev_dark, ev_circle_mask),
            "analysis_details": _compute_analysis_details(
                leaf_objects, fruit_objects, image, leaf_mask, fruit_det_mask,
                leaf_senes, fruit_maturity_counts, avg_curl, curled_pct,
                leaf_roughness, avg_ls, blur_level, cfg=adapted),
        }
        # Strip internal contours (numpy arrays) that are not JSON-serializable.
        for lo in result.get("leaf_objects", []):
            lo.pop("_contour", None)
        if fg_mask is not None:
            result["fg_mask"] = fg_mask
        return result, annotated


def _compute_analysis_details(leaf_objects, fruit_objects, image_bgr,
                              leaf_mask, fruit_mask,
                              leaf_senes, fruit_maturity_counts,
                              avg_curl, curled_pct, leaf_roughness,
                              avg_leaf_sat, blur_level, cfg=None):
    """Compute fine-grained analysis metrics from existing detection results.

    This function adds depth to the standard detection output without
    modifying the detection pipeline itself.  All metrics are derived from
    the already-computed leaf/fruit objects and masks.
    """
    cfg = cfg or {}
    acfg = cfg.get("analysis", {})
    scfg = cfg.get("stress", {})
    h, w = image_bgr.shape[:2]
    img_area = max(1, h * w)
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    # Leaf colour hue bands
    hue_green_lo = acfg.get("leaf_hue_green_low", 35)
    hue_green_hi = acfg.get("leaf_hue_green_high", 85)
    hue_yellow_hi = acfg.get("leaf_hue_yellow_high", 95)
    hue_dark_hi = acfg.get("leaf_hue_dark_high", 150)
    # Leaf size buckets
    leaf_sm_max = acfg.get("leaf_size_small_max", 2000)
    leaf_md_max = acfg.get("leaf_size_medium_max", 6000)
    # Drooping angle
    drop_lo = acfg.get("drooping_angle_low", 45)
    drop_hi = acfg.get("drooping_angle_high", 135)
    # Confidence
    leaf_conf_thr = acfg.get("leaf_low_confidence_threshold", 0.5)
    # Fruit size buckets
    fruit_sm_max = acfg.get("fruit_size_small_max", 400)
    fruit_md_max = acfg.get("fruit_size_medium_max", 800)
    fruit_conf_thr = acfg.get("fruit_low_confidence_threshold", 0.5)
    # Stress weights
    ws_curl = scfg.get("weight_curl", 0.5)
    ws_wrinkle = scfg.get("weight_wrinkle", 0.5)
    green_cov_max = scfg.get("green_coverage_max", 50.0)
    curl_sat = scfg.get("curl_saturation", 3.0)
    wrk_sat = scfg.get("wrinkle_saturation", 2.0)
    sat_max = scfg.get("saturation_max", 120.0)
    hw_green = scfg.get("weight_green", 0.30)
    hw_curl = scfg.get("weight_health_curl", 0.25)
    hw_wrinkle = scfg.get("weight_health_wrinkle", 0.25)
    hw_sat = scfg.get("weight_saturation", 0.20)

    # ── Leaf analysis ───────────────────────────────────────────────────
    leaf_areas = [d["area"] for d in leaf_objects] if leaf_objects else []
    leaf_hues = [d.get("hue", 0) for d in leaf_objects] if leaf_objects else []
    leaf_aspects = [d.get("aspect", 1.0) for d in leaf_objects] if leaf_objects else []
    leaf_solidities = [d.get("solidity", 0.8) for d in leaf_objects] if leaf_objects else []
    leaf_confidences = [d.get("confidence", 0.5) for d in leaf_objects] if leaf_objects else []

    # Colour distribution: classify each leaf by hue band.
    green_leaves = sum(1 for h_ in leaf_hues if hue_green_lo <= h_ <= hue_green_hi)
    yellow_leaves = sum(1 for h_ in leaf_hues if (h_ < hue_green_lo or hue_green_hi < h_ <= hue_yellow_hi))
    dark_leaves = sum(1 for h_ in leaf_hues if h_ < hue_green_lo or h_ > hue_dark_hi)
    nl = max(1, len(leaf_hues))

    # Size distribution buckets.
    small_leaves = sum(1 for a in leaf_areas if a < leaf_sm_max)
    medium_leaves = sum(1 for a in leaf_areas if leaf_sm_max <= a < leaf_md_max)
    large_leaves = sum(1 for a in leaf_areas if a >= leaf_md_max)

    # Orientation: ellipse angle from contours (via fitted ellipse).
    leaf_angles = []
    for d in leaf_objects:
        cnt = d.get("_contour")
        if cnt is not None and len(cnt) >= 5:
            _, (ma, MA), angle = cv2.fitEllipse(cnt)
            leaf_angles.append(round(angle, 1))
    mean_angle = round(float(np.mean(leaf_angles)), 1) if leaf_angles else 0.0
    std_angle = round(float(np.std(leaf_angles)), 1) if leaf_angles else 0.0
    # Drooping: leaves tilted from horizontal may indicate wilt.
    drooping = sum(1 for a in leaf_angles if (a % 180) > drop_lo and (a % 180) < drop_hi)
    drooping_pct = round(drooping / max(1, len(leaf_angles)) * 100, 1)

    # Confidence stats.
    mean_leaf_conf = round(float(np.mean(leaf_confidences)), 3) if leaf_confidences else 0.0
    low_conf_leaves = sum(1 for c in leaf_confidences if c < leaf_conf_thr)

    leaf_detail = {
        "count": len(leaf_objects),
        "color_distribution": {
            "green_pct": round(green_leaves / nl * 100, 1),
            "yellow_pct": round(yellow_leaves / nl * 100, 1),
            "dark_pct": round(dark_leaves / nl * 100, 1),
            "mean_hue": round(float(np.mean(leaf_hues)), 1) if leaf_hues else 0.0,
            "std_hue": round(float(np.std(leaf_hues)), 1) if leaf_hues else 0.0,
        },
        "size_distribution": {
            "small_lt2k": small_leaves,
            "medium_2k_6k": medium_leaves,
            "large_gt6k": large_leaves,
            "mean_area": round(float(np.mean(leaf_areas)), 1) if leaf_areas else 0.0,
            "std_area": round(float(np.std(leaf_areas)), 1) if leaf_areas else 0.0,
            "median_area": round(float(np.median(leaf_areas)), 1) if leaf_areas else 0.0,
        },
        "orientation": {
            "mean_angle": mean_angle,
            "std_angle": std_angle,
            "drooping_pct": drooping_pct,
        },
        "health": {
            "senescence": leaf_senes,
            "curl_index": round(avg_curl, 3),
            "curled_leaf_pct": curled_pct,
            "roughness": leaf_roughness,
            "mean_saturation": round(avg_leaf_sat, 1),
        },
        "confidence": {
            "mean": mean_leaf_conf,
            "low_confidence_count": low_conf_leaves,
        },
    }

    # ── Fruit analysis ──────────────────────────────────────────────────
    fruit_areas = [d["area"] for d in fruit_objects] if fruit_objects else []
    fruit_hues = [d.get("hue", 0) for d in fruit_objects] if fruit_objects else []
    fruit_sats = [d.get("saturation", 0) for d in fruit_objects] if fruit_objects else []
    fruit_wrinkle_scores = [d.get("wrinkle_score", 0) for d in fruit_objects] if fruit_objects else []
    fruit_confidences = [d.get("confidence", 0.5) for d in fruit_objects] if fruit_objects else []
    nf = max(1, len(fruit_objects))

    # Size buckets.
    small_fruit = sum(1 for a in fruit_areas if a < fruit_sm_max)
    medium_fruit = sum(1 for a in fruit_areas if fruit_sm_max <= a < fruit_md_max)
    large_fruit = sum(1 for a in fruit_areas if a >= fruit_md_max)

    # Maturity breakdown with percentages.
    maturity_pct = {}
    for stage, count in fruit_maturity_counts.items():
        maturity_pct[stage] = round(count / nf * 100, 1)

    # Wrinkle breakdown with percentages.
    wrinkle_labels = [d.get("wrinkle_label", "smooth") for d in fruit_objects]
    wrinkle_pct = {}
    for label in ("smooth", "slightly_wrinkled", "wrinkled", "heavily_wrinkled"):
        cnt = sum(1 for l in wrinkle_labels if l == label)
        wrinkle_pct[label] = round(cnt / nf * 100, 1)

    # Color uniformity: how similar are the detected fruits in color?
    hue_std = round(float(np.std(fruit_hues)), 1) if fruit_hues else 0.0
    sat_std = round(float(np.std(fruit_sats)), 1) if fruit_sats else 0.0

    # Per-fruit color variance (average internal color consistency).
    mean_color_consistency = round(float(np.mean(
        [d.get("color_consistency", 0) for d in fruit_objects])), 3) if fruit_objects else 0.0

    mean_fruit_conf = round(float(np.mean(fruit_confidences)), 3) if fruit_confidences else 0.0
    low_conf_fruit = sum(1 for c in fruit_confidences if c < fruit_conf_thr)

    fruit_detail = {
        "count": len(fruit_objects),
        "size_distribution": {
            "small_lt400": small_fruit,
            "medium_400_800": medium_fruit,
            "large_gt800": large_fruit,
            "mean_area": round(float(np.mean(fruit_areas)), 1) if fruit_areas else 0.0,
            "std_area": round(float(np.std(fruit_areas)), 1) if fruit_areas else 0.0,
            "median_area": round(float(np.median(fruit_areas)), 1) if fruit_areas else 0.0,
        },
        "color": {
            "mean_hue": round(float(np.mean(fruit_hues)), 1) if fruit_hues else 0.0,
            "std_hue": hue_std,
            "mean_saturation": round(float(np.mean(fruit_sats)), 1) if fruit_sats else 0.0,
            "std_saturation": sat_std,
            "maturity_pct": maturity_pct,
            "mean_color_consistency": mean_color_consistency,
        },
        "quality": {
            "wrinkle_pct": wrinkle_pct,
            "mean_wrinkle_score": round(float(np.mean(fruit_wrinkle_scores)), 3) if fruit_wrinkle_scores else 0.0,
            "std_wrinkle_score": round(float(np.std(fruit_wrinkle_scores)), 3) if fruit_wrinkle_scores else 0.0,
            "unreliable_wrinkle_count": sum(1 for d in fruit_objects if not d.get("wrinkle_reliable", True)),
        },
        "confidence": {
            "mean": mean_fruit_conf,
            "low_confidence_count": low_conf_fruit,
        },
    }

    # ── Canopy / spatial analysis ───────────────────────────────────────
    # Divide the frame into vertical thirds and measure leaf density.
    third_h = max(1, h // 3)
    zones = {"top": (0, third_h), "mid": (third_h, 2 * third_h), "bottom": (2 * third_h, h)}
    zone_density = {}
    leaf_total = max(1, cv2.countNonZero(leaf_mask))
    for name, (y0, y1) in zones.items():
        strip = leaf_mask[y0:y1, :]
        zone_density[name] = round(cv2.countNonZero(strip) / leaf_total * 100, 1)

    # Light penetration: mean brightness in leaf regions vs overall.
    leaf_brightness = float(np.mean(gray[leaf_mask > 0])) if cv2.countNonZero(leaf_mask) > 0 else 0.0
    overall_brightness = float(np.mean(gray))
    light_ratio = round(leaf_brightness / max(1.0, overall_brightness), 3)

    # Canopy fullness: leaf coverage as percentage of frame.
    fullness = round(cv2.countNonZero(leaf_mask) / img_area * 100, 2)

    canopy_detail = {
        "spatial_density": zone_density,
        "leaf_brightness": round(leaf_brightness, 1),
        "overall_brightness": round(overall_brightness, 1),
        "light_penetration_ratio": light_ratio,
        "fullness_pct": fullness,
    }

    # ── Stress indicators ───────────────────────────────────────────────
    # Chlorophyll proxy: high green saturation + green hue = healthy.
    chlorophyll_simple = round(avg_leaf_sat / 255.0, 3)

    # Water stress: combined curl + wrinkle signals.
    mean_wrinkle = float(np.mean(fruit_wrinkle_scores)) if fruit_wrinkle_scores else 0.0
    water_stress = round(min(1.0, avg_curl * ws_curl + mean_wrinkle * ws_wrinkle), 3)

    # Overall health: weighted combination of indicators.
    # Healthy: high green coverage, low curl, low wrinkle, high saturation.
    green_factor = min(1.0, fullness / green_cov_max)
    curl_factor = 1.0 - min(1.0, avg_curl * curl_sat)
    wrinkle_factor = 1.0 - min(1.0, mean_wrinkle * wrk_sat)
    saturation_factor = min(1.0, avg_leaf_sat / sat_max)
    overall_health = round(hw_green * green_factor + hw_curl * curl_factor +
                           hw_wrinkle * wrinkle_factor + hw_sat * saturation_factor, 3)

    stress_detail = {
        "chlorophyll_proxy": chlorophyll_simple,
        "water_stress": water_stress,
        "overall_health_score": overall_health,
        "components": {
            "green_coverage_factor": round(green_factor, 3),
            "curl_factor": round(curl_factor, 3),
            "wrinkle_factor": round(wrinkle_factor, 3),
            "saturation_factor": round(saturation_factor, 3),
        },
    }

    return {
        "leaf": leaf_detail,
        "fruit": fruit_detail,
        "canopy": canopy_detail,
        "stress": stress_detail,
    }


def integrate_soil_moisture(result: dict, soil_data: dict) -> dict:
    """Add soil moisture data to an analysis result and update health assessment.

    Args:
        result: Analysis result dict from Analyzer.analyze()
        soil_data: Soil moisture data from get_moisture_for_olive_analysis()

    Returns:
        Updated result dict with soil_moisture and health_assessment fields
    """
    sm = soil_data.get("soil_moisture", {})
    result["soil_moisture"] = sm
    health = sm.get("health", {})
    ad = result.get("analysis_details", {})
    stress = ad.get("stress", {})
    visual_score = stress.get("overall_health_score", 0.5)
    moisture_score = health.get("score", 0.5)
    moisture_weight = health.get("weight", 0.0)
    combined = round(visual_score * (1.0 - moisture_weight) + moisture_score * moisture_weight, 3)
    risk = health.get("risk", "unknown")
    flags = []
    if risk in ("critical", "high"):
        flags.append(f"soil_moisture_{risk}")
    if risk == "moderate":
        flags.append("soil_moisture_moderate")
    result["health_assessment"] = {
        "visual_health_score": visual_score,
        "moisture_health_score": moisture_score,
        "moisture_weight": moisture_weight,
        "combined_health_score": combined,
        "moisture_risk": risk,
        "moisture_message": health.get("message", ""),
        "flags": flags,
    }
    return result


def _avg_leaf_hue_norm(hues):
    """Normalise average leaf hue to a green-centred0..1 range.

    Olive-leaf green is around hue 35-85.  Centred at 60, spread ~25.
    Returns 0 when hue is perfectly green, positive when yellowish,
    negative when dark/reddish.
    """
    if not hues:
        return 0.0
    mean_h = float(np.mean(hues))
    return (mean_h - 60.0) / 30.0


def _pipeline_diagnostics(leaf_trace, fruit_trace, accepted_fruit_mask,
                          ev_yellow, ev_ripe, ev_dark, ev_circle_mask):
    """Summarise the detection pipeline's internal decisions for transparency.

    Reports how many candidate blobs each class considered and, for rejected
    ones, which test category failed. Also reports the raw colour-band signal
    coverage so a user can see how strongly each fruit cue was present.
    """
    def _tally(trace):
        total = len(trace)
        accepted = sum(1 for t in trace if not t.get("rejected"))
        rejected = [t.get("reason") for t in trace if t.get("rejected")]
        reasons: dict = {}
        for r in rejected:
            reasons[r] = reasons.get(r, 0) + 1
        return {"candidates": total, "accepted": accepted, "rejected": len(rejected),
                "rejected_by": reasons}

    def _coverage(mask):
        n = int(np.count_nonzero(mask)) if mask is not None else 0
        total = int(mask.size) if mask is not None else 1
        return {"pixels": n, "pct": round(n / max(1, total) * 100, 2)}

    return {
        "leaves": _tally(leaf_trace),
        "fruits": _tally(fruit_trace),
        "signals": {
            "yellow_green_mask": _coverage(ev_yellow),
            "ripe_mask": _coverage(ev_ripe),
            "dark_mask": _coverage(ev_dark),
            "hough_circle_mask": _coverage(ev_circle_mask),
        },
        "accepted_fruit_mask_pct": round(
            np.count_nonzero(accepted_fruit_mask) / max(1, accepted_fruit_mask.size) * 100, 2),
    }


def save_observation(analyzer, store, image, source, output_dir, image_path=None,
                      persist=True):
    """Analyse ``image``, write the annotated frame + JSON and - when ``store``
    is given and ``persist`` is true - add the result to the observation DB.
    ``persist=False`` (single-shot analysis) never touches the DB."""
    result, annotated = analyzer.analyze(image, source, image_path)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    annotated_path = output / f"observation_{stamp}.jpg"
    cv2.imwrite(str(annotated_path), annotated, [cv2.IMWRITE_JPEG_QUALITY, analyzer.config["runtime"]["jpeg_quality"]])
    result["annotated_path"] = str(annotated_path)
    # Strip non-serializable ndarray fields before persistence
    serializable_result = {k: v for k, v in result.items() if not isinstance(v, np.ndarray)}
    if store is not None and persist:
        store.add(serializable_result)
    (output / f"observation_{stamp}.json").write_text(
        json.dumps(serializable_result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result, annotated_path


def _confidence_label(conf: float) -> str:
    if conf >= 0.75:
        return "high"
    if conf >= 0.5:
        return "moderate"
    return "low"


def _frame_position(obj: dict, width: int, height: int) -> str:
    """Human-readable location of a detected object within the frame."""
    cx = float(obj.get("center_x", 0.0))
    cy = float(obj.get("center_y", 0.0))
    if width <= 0 or height <= 0 or (cx == 0 and cy == 0):
        return "position unknown"
    xf = cx / width
    yf = cy / height
    hz = "left" if xf < 0.34 else ("right" if xf > 0.66 else "centre")
    vz = "top" if yf < 0.34 else ("bottom" if yf > 0.66 else "middle")
    zone = f"{vz} {hz}" if hz == "centre" else f"{vz}-{hz}"
    edge = " (touches the frame edge -> partially clipped fruit)" if obj.get("edge_touch") else ""
    return f"{zone} of the frame (x {xf * 100:.0f}%, y {yf * 100:.0f}%){edge}"


def _signal_strength(v: float) -> str:
    if v >= 0.8:
        return "strong"
    if v >= 0.5:
        return "moderate"
    return "weak"


def _fruit_why(obj: dict, fruit_thr: dict, sig_thr: dict) -> list:
    """Lines explaining why a region was classified as a fruit."""
    ratios = obj.get("signal_ratios") or {}
    lines = []
    signals = []
    for key, label in FRUIT_SIGNAL_LABELS.items():
        v = ratios.get(key, 0.0)
        thr = sig_thr.get(key, 0.2)
        if v > thr:
            signals.append(f"{label} {v:.2f} (threshold {thr:.2f}) -> {_signal_strength(v)}")
        else:
            signals.append(f"{label} {v:.2f} (below threshold {thr:.2f})")
    lines.append("signals: " + "; ".join(signals))

    circ = float(obj.get("circularity", 0.0))
    solid = float(obj.get("solidity", 0.0))
    aspect = float(obj.get("aspect", 0.0))
    ear = float(obj.get("ellipse_axis_ratio", 1.0))
    area = float(obj.get("area", 0.0))
    tex = float(obj.get("internal_texture", 0.0))
    checks = []
    checks.append(f"size {area:.0f}px (allowed {fruit_thr.get('min_area', 120)}-"
                  f"{fruit_thr.get('max_area', 18000)})")
    checks.append(f"circularity {circ:.2f} (need >= {fruit_thr.get('min_circularity', 0.5):.2f})"
                  + ("" if circ >= fruit_thr.get("min_circularity", 0.5) else " - MARGINAL"))
    checks.append(f"solidity {solid:.2f} (need >= {fruit_thr.get('min_solidity', 0.72):.2f})")
    checks.append(f"ellipse axis ratio {ear:.2f} (need <= {fruit_thr.get('max_ellipse_ratio', 3.5):.1f})")
    if fruit_thr.get("max_internal_std"):
        checks.append(f"surface smoothness {tex:.1f} (need <= "
                      f"{fruit_thr['max_internal_std']:.0f}, lower is smoother)")
    lines.append("shape/surface tests passed: " + "; ".join(checks))

    circle = ratios.get("hough_circle", 0.0) > sig_thr.get("hough_circle", 0.2)
    rescue = not circle
    if obj.get("low_signal"):
        lines.append("caution: no strong signal backed this blob, so its confidence was halved")
    elif rescue:
        lines.append("detection path: no Hough circle overlapped it, so it was kept only by its "
                     "round, smooth, fruit-sized shape (self-evident rescue)")
    else:
        lines.append("detection path: a Hough circle overlapped the blob, so it was boosted as a "
                     "round fruit even where foliage surrounds it")
    return lines


def explain_detection(result: dict) -> str:
    """Build a human-readable text explaining how the detection result was reached."""
    lines: list[str] = []
    mode = result.get("detect_mode", "multi_signal")
    blur = float(result.get("blur_level", 0.0))
    blur_score = float(result.get("blur_score", 0.0))
    lines.append("DETECTION EXPLANATION")
    lines.append("=" * 60)
    lines.append(
        f"Analysed a {result.get('image_width')}x{result.get('image_height')} image using the "
        f"'{mode}' pipeline.")
    if blur >= 0.75:
        lines.append(
            f"WARNING: the frame is very blurry (Laplacian variance {blur_score:.0f}). "
            "Blur weakens edge evidence, so the pipeline applied unsharp-mask deblurring, "
            "skipped edge-snapping refinement, and relied more on colour consistency than edges.")
    elif blur >= 0.4:
        lines.append(
            f"NOTE: the frame is moderately blurry (Laplacian variance {blur_score:.0f}). "
            "Edge evidence was down-weighted in confidence scoring.")
    else:
        lines.append(
            f"The frame is sharp (Laplacian variance {blur_score:.0f}), so edge alignment "
            "was a trusted signal for confidence.")

    def describe(kind: str, objects: list, threshold_note: str, count: int) -> list:
        block = []
        block.append(f"- {kind}: {count} object(s) detected ({threshold_note}).")
        if not objects:
            block.append(f"  No {kind.lower()} passed the minimum area/shape/colour tests, "
                         "so the mask had nothing to report.")
        for i, obj in enumerate(objects, start=1):
            conf = float(obj.get("confidence", 0.0))
            is_fruit = kind.lower().startswith("fruit")
            w, h = result.get("image_width", 0), result.get("image_height", 0)
            where = _frame_position(obj, w, h)
            cx = obj.get("center_x", 0.0)
            cy = obj.get("center_y", 0.0)
            loc = f" at ({cx:.0f},{cy:.0f})" if (cx or cy) else ""
            block.append(f"  #{i}{loc}  {where}.")
            block.append(f"      area={obj.get('area', 0)}px, confidence {conf:.0%} "
                         f"({_confidence_label(conf)}).")
            if is_fruit:
                block.extend("      " + line for line in _fruit_why(
                    obj, result.get("fruit_thresholds") or {},
                    result.get("signal_thresholds") or FRUIT_SIGNAL_THRESHOLDS))
                maturity = obj.get("maturity", "")
                if maturity and maturity != "unknown":
                    block.append(f"      colour classified as a {maturity} fruit "
                                 f"(hue {obj.get('hue', '?')}).")
                wl = obj.get("wrinkle_label", "smooth")
                if wl != "smooth":
                    block.append(f"      surface shows {wl} texture "
                                 f"(wrinkle score {obj.get('wrinkle_score', 0.0):.2f}).")
            else:
                reasons = []
                cc = float(obj.get("color_consistency", 0.0))
                ed = float(obj.get("edge_density", 0.0))
                if cc >= 0.6:
                    reasons.append(f"colour is uniform within the region (consistency {cc:.2f})")
                elif cc >= 0.35:
                    reasons.append(f"colour is somewhat uniform (consistency {cc:.2f})")
                if ed >= 0.4:
                    reasons.append(f"boundary aligns with real image edges (edge density {ed:.2f})")
                elif ed >= 0.2:
                    reasons.append(f"boundary partially follows image edges (edge density {ed:.2f})")
                if obj.get("aspect", 0) >= 1.5:
                    reasons.append(f"shape is elongated like a leaf (aspect {obj['aspect']:.2f})")
                block.append("      why: " + "; ".join(reasons) + "." if reasons
                             else "      why: matched the leaf colour/vegetation-index bands.")
        return block

    lines.extend(describe(
        "Leaves", result.get("leaf_objects", []),
        "leaf hue/saturation range + vegetation-index agreement + size/shape tests",
        result.get("leaf_count", 0)))
    lines.extend(describe(
        "Fruits", result.get("fruit_objects", []),
        "yellow-green/ripe HSV bands + LAB b-channel + size/shape/circularity tests",
        result.get("fruit_count", 0)))

    gcov = float(result.get("green_coverage", 0.0))
    stage = result.get("leaf_color_stage", "unknown")
    sens = result.get("leaf_senescence", "unknown")
    mat = result.get("fruit_maturity", "unknown")
    lines.append("SUMMARY")
    lines.append(
        f"  Green coverage is {gcov:.1f}% of the frame; leaf colour classified as '{stage}' "
        f"(senescence '{sens}') and fruit maturity as '{mat}'.")
    breakdown = result.get("fruit_maturity_breakdown") or {}
    if breakdown:
        parts = [f"{v} {k}" for k, v in sorted(breakdown.items()) if v > 0]
        if parts:
            lines.append("  Fruit maturity breakdown: " + ", ".join(parts) + ".")
    ftot = int(result.get("fruit_total_area", 0))
    fcov = float(result.get("fruit_cover_pct", 0.0))
    if ftot:
        lines.append(f"  Fruit mask covers {fcov:.2f}% of the frame ({ftot} px in total).")
    wrinkle_sum = result.get("fruit_wrinkle_summary") or {}
    if wrinkle_sum:
        parts = [f"{v} {k}" for k, v in wrinkle_sum.items() if v > 0]
        if parts:
            lines.append("  Fruit wrinkle breakdown: " + ", ".join(parts) + ".")
    uw = result.get("unreliable_wrinkle_count", 0)
    if uw:
        lines.append(f"  ({uw} wrinkle label(s) unreliable due to small object size)")
    curl_idx = result.get("leaf_curl_index")
    curled_pct = result.get("curled_leaf_pct")
    if curl_idx is not None:
        lines.append(f"  Leaf curl index: {curl_idx:.3f}  "
                     f"({curled_pct:.1f}% of leaves curled ≥0.25)")
    # Detailed analysis section
    details = result.get("analysis_details")
    if details:
        lines.append("")
        lines.append("DETAILED ANALYSIS")
        ld = details.get("leaf", {})
        if ld:
            cd = ld.get("color_distribution", {})
            sd = ld.get("size_distribution", {})
            od = ld.get("orientation", {})
            lines.append(f"  Leaves: {cd.get('green_pct',0):.0f}% green, "
                         f"{cd.get('yellow_pct',0):.0f}% yellow  "
                         f"(hue μ={cd.get('mean_hue',0):.1f} σ={cd.get('std_hue',0):.1f})")
            lines.append(f"    size: {sd.get('small_lt2k',0)} small, "
                         f"{sd.get('medium_2k_6k',0)} medium, {sd.get('large_gt6k',0)} large  "
                         f"(area μ={sd.get('mean_area',0):.0f} median={sd.get('median_area',0):.0f})")
            lines.append(f"    orientation: angle μ={od.get('mean_angle',0):.1f}° "
                         f"σ={od.get('std_angle',0):.1f}°  drooping={od.get('drooping_pct',0):.1f}%")
        fd = details.get("fruit", {})
        if fd:
            fsd = fd.get("size_distribution", {})
            fcol = fd.get("color", {})
            fqual = fd.get("quality", {})
            maturity_parts = [f"{v:.0f}% {k}" for k, v in fcol.get("maturity_pct", {}).items() if v > 0]
            lines.append(f"  Fruits: {fsd.get('small_lt400',0)} small, "
                         f"{fsd.get('medium_400_800',0)} medium, {fsd.get('large_gt800',0)} large  "
                         f"(area μ={fsd.get('mean_area',0):.0f} σ={fsd.get('std_area',0):.0f})")
            if maturity_parts:
                lines.append(f"    maturity: {', '.join(maturity_parts)}")
            wrinkle_parts = [f"{v:.0f}% {k}" for k, v in fqual.get("wrinkle_pct", {}).items() if v > 0]
            if wrinkle_parts:
                lines.append(f"    wrinkle: {', '.join(wrinkle_parts)}")
        cdet = details.get("canopy", {})
        if cdet:
            sdens = cdet.get("spatial_density", {})
            lines.append(f"  Canopy: {cdet.get('fullness_pct',0):.1f}% full  "
                         f"distribution: top={sdens.get('top',0):.0f}% "
                         f"mid={sdens.get('mid',0):.0f}% bottom={sdens.get('bottom',0):.0f}%")
            lines.append(f"    light penetration: {cdet.get('light_penetration_ratio',0):.3f}  "
                         f"leaf brightness: {cdet.get('leaf_brightness',0):.1f}")
        stress = details.get("stress", {})
        if stress:
            comp = stress.get("components", {})
            lines.append(f"  Health: overall={stress.get('overall_health_score',0):.3f}  "
                         f"water_stress={stress.get('water_stress',0):.3f}  "
                         f"chlorophyll={stress.get('chlorophyll_proxy',0):.3f}")
            lines.append(f"    factors: green={comp.get('green_coverage_factor',0):.3f} "
                         f"curl={comp.get('curl_factor',0):.3f} "
                         f"wrinkle={comp.get('wrinkle_factor',0):.3f} "
                         f"saturation={comp.get('saturation_factor',0):.3f}")
    leaf_avg = float(result.get("leaf_confidence", 0.0))
    fruit_avg = float(result.get("fruit_confidence", 0.0))
    if result.get("leaf_count", 0) and leaf_avg < 0.5:
        lines.append("  Leaf detections are low-confidence: try brighter or sharper images, "
                     "or a foreground-aware mode (kmeans/grabcut) to remove background.")
    if result.get("fruit_count", 0) and fruit_avg < 0.5:
        lines.append("  Fruit detections are low-confidence: consider more zoom, better focus, "
                     "or switching the detection mode.")
    if not result.get("leaf_count", 0) and not result.get("fruit_count", 0):
        lines.append("  Nothing was detected. Common causes: very blurry frame, low contrast, "
                     "background masking too aggressive, or thresholds mismatched to this camera.")
    return "\n".join(lines)


def capture_camera(index: int, warmup: int) -> np.ndarray:
    camera = cv2.VideoCapture(index)
    if not camera.isOpened():
        camera.release()
        try:
            from picamera2 import Picamera2
            pi = Picamera2()
            pi.configure(pi.create_still_configuration())
            pi.start()
            try:
                frame = pi.capture_array("main")
            finally:
                pi.stop(); pi.close()
            return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        except ImportError as exc:
            raise RuntimeError(f"Camera {index} cannot be opened.") from exc
    try:
        frame = None
        for _ in range(max(1, warmup)):
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError("Camera returned no frame.")
        return frame
    finally:
        camera.release()


# ===================================================================
#  Video analyzer
# ===================================================================

class VideoAnalyzer:
    """Frame-by-frame analysis with multi-object tracking."""

    def __init__(self, analyzer: Analyzer, config: dict, logger=None, store=None):
        self.analyzer = analyzer
        self.video_cfg = config.get("video", DEFAULTS["video"])
        self.logger = logger or logging.getLogger("olivevision.video")
        self.store = store
        self.tracker_leaves = _CentroidTracker(max_age=self.video_cfg.get("track_max_age", 30))
        self.tracker_fruits = _CentroidTracker(max_age=self.video_cfg.get("track_max_age", 30))
        self.timeline: List[dict] = []

    def analyze_video(self, video_path: str, output_dir: str,
                      frame_interval: Optional[int] = None,
                      progress_callback=None, persist: bool = False) -> dict:
        """Analyze an mp4/avi video. Returns summary dict."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        interval = frame_interval or self.video_cfg.get("frame_interval", 10)
        max_frames = self.video_cfg.get("max_frames", 500)

        self.logger.info("Video: %dx%d @ %.1f fps, %d frames, interval=%d",
                         width, height, fps, total_frames, interval)

        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        frame_dir = out_dir / "frames"
        frame_dir.mkdir(exist_ok=True)

        # Output annotated video
        out_fps = self.video_cfg.get("output_fps", 5)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        ann_path = out_dir / "annotated.mp4"
        writer = cv2.VideoWriter(str(ann_path), fourcc, out_fps, (width, height))

        self.tracker_leaves = _CentroidTracker(self.video_cfg.get("track_max_age", 30))
        self.tracker_fruits = _CentroidTracker(self.video_cfg.get("track_max_age", 30))
        self.timeline = []

        frame_idx = 0
        analyzed_count = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_idx % interval != 0:
                frame_idx += 1
                continue
            if analyzed_count >= max_frames:
                self.logger.info("Reached max_frames=%d, stopping.", max_frames)
                break

            result, annotated = self.analyzer.analyze(frame, f"video:{Path(video_path).name}")

            # Save frame result
            frame_path = frame_dir / f"frame_{frame_idx:06d}.jpg"
            cv2.imwrite(str(frame_path), annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])

            # Update trackers with actual bounding boxes
            leaf_boxes = result.get("leaf_boxes", [])
            fruit_boxes = result.get("fruit_boxes", [])
            tracked_leaves = self.tracker_leaves.update(leaf_boxes)
            tracked_fruits = self.tracker_fruits.update(fruit_boxes)

            # Draw track IDs on annotated frame
            for tid, (x, y, w, h) in tracked_leaves.items():
                cv2.putText(annotated, f"L#{tid}", (x + w + 2, y + 12),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (50, 220, 50), 1, cv2.LINE_AA)
            for tid, (x, y, w, h) in tracked_fruits.items():
                cv2.putText(annotated, f"F#{tid}", (x + w + 2, y + 12),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 150, 255), 1, cv2.LINE_AA)

            timestamp_sec = frame_idx / fps
            entry = {
                "frame": frame_idx, "timestamp_sec": round(timestamp_sec, 2),
                "tree_id": result.get("tree_id"),
                "leaf_count": result["leaf_count"], "fruit_count": result["fruit_count"],
                "green_coverage": result["green_coverage"],
                "fruit_cover_pct": result.get("fruit_cover_pct", 0.0),
                "leaf_color_stage": result["leaf_color_stage"],
                "leaf_senescence": result.get("leaf_senescence"),
                "leaf_avg_hue": result.get("leaf_avg_hue", 0.0),
                "leaf_avg_saturation": result.get("leaf_avg_saturation", 0.0),
                "leaf_avg_area": result.get("leaf_avg_area", 0.0),
                "leaf_confidence": result["leaf_confidence"],
                "leaf_roughness": result.get("leaf_roughness", 0.0),
                "leaf_curl_index": result.get("leaf_curl_index", 0.0),
                "curled_leaf_pct": result.get("curled_leaf_pct", 0.0),
                "fruit_maturity": result["fruit_maturity"],
                "fruit_maturity_breakdown": result.get("fruit_maturity_breakdown", {}),
                "wrinkled_fruit_count": result.get("wrinkled_fruit_count", 0),
                "unreliable_wrinkle_count": result.get("unreliable_wrinkle_count", 0),
                "fruit_wrinkle_summary": result.get("fruit_wrinkle_summary", {}),
                "fruit_avg_hue": result.get("fruit_avg_hue", 0.0),
                "fruit_avg_area": result.get("fruit_avg_area", 0.0),
                "fruit_confidence": result["fruit_confidence"],
                "blur_level": result.get("blur_level", 0.0),
                "analysis_details": result.get("analysis_details"),
                "tracked_leaves": len(tracked_leaves),
                "tracked_fruits": len(tracked_fruits),
            }
            self.timeline.append(entry)

            # Persist frame result to DB if store is available.
            if persist and self.store is not None:
                try:
                    self.store.add(result)
                except Exception as exc:
                    self.logger.warning("Failed to store frame %d: %s", frame_idx, exc)

            # Draw frame counter on annotated
            info = f"Frame {frame_idx} | T={timestamp_sec:.1f}s | L:{result['leaf_count']} F:{result['fruit_count']}"
            cv2.putText(annotated, info, (12, height - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
            cv2.putText(annotated, info, (12, height - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 30, 30), 1)
            writer.write(annotated)

            analyzed_count += 1
            if progress_callback:
                progress_callback(analyzed_count, max(1, total_frames // interval), result)
            if analyzed_count % 20 == 0:
                self.logger.info("  processed %d frames...", analyzed_count)

            frame_idx += 1

        cap.release()
        writer.release()

        # Save timeline JSON
        timeline_path = out_dir / "timeline.json"
        summary = self._build_summary(width, height, fps, total_frames, video_path)
        summary["timeline"] = self.timeline
        timeline_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

        self.logger.info("Video analysis complete: %d frames analyzed, output=%s", analyzed_count, ann_path)
        return summary

    def _build_summary(self, w, h, fps, total_frames, path) -> dict:
        if not self.timeline:
            return {"total_frames": total_frames, "analyzed_frames": 0}
        leaves = [t["leaf_count"] for t in self.timeline]
        fruits = [t["fruit_count"] for t in self.timeline]
        greens = [t["green_coverage"] for t in self.timeline]
        tracked_leaves = [t.get("tracked_leaves", 0) for t in self.timeline]
        tracked_fruits = [t.get("tracked_fruits", 0) for t in self.timeline]
        fruit_covers = [t.get("fruit_cover_pct", 0.0) for t in self.timeline]
        maturity_tally: Dict[str, int] = {}
        for t in self.timeline:
            for stage, count in (t.get("fruit_maturity_breakdown") or {}).items():
                maturity_tally[stage] = maturity_tally.get(stage, 0) + count
        wrinkle_tally: Dict[str, int] = {}
        for t in self.timeline:
            for label, count in (t.get("fruit_wrinkle_summary") or {}).items():
                wrinkle_tally[label] = wrinkle_tally.get(label, 0) + count
        wrinkled = [t.get("wrinkled_fruit_count", 0) for t in self.timeline]
        curl_vals = [t.get("leaf_curl_index", 0.0) for t in self.timeline]
        leaf_hues = [t.get("leaf_avg_hue", 0.0) for t in self.timeline]
        fruit_hues = [t.get("fruit_avg_hue", 0.0) for t in self.timeline]
        blur_vals = [t.get("blur_level", 0.0) for t in self.timeline]
        # Per-tree grouping: compute averages for each detected tree_id.
        tree_groups: Dict[str, list] = {}
        for t in self.timeline:
            tid = t.get("tree_id")
            if tid:
                tree_groups.setdefault(tid, []).append(t)
        per_tree = {}
        for tid, frames in tree_groups.items():
            per_tree[tid] = {
                "frames": len(frames),
                "leaf_count_avg": round(float(np.mean([f["leaf_count"] for f in frames])), 1),
                "fruit_count_avg": round(float(np.mean([f["fruit_count"] for f in frames])), 1),
                "green_coverage_avg": round(float(np.mean([f["green_coverage"] for f in frames])), 2),
                "fruit_cover_avg": round(float(np.mean([f.get("fruit_cover_pct", 0.0) for f in frames])), 2),
                "leaf_curl_avg": round(float(np.mean([f.get("leaf_curl_index", 0.0) for f in frames])), 3),
            }
        return {
            "source_video": path,
            "video_width": w, "video_height": h, "video_fps": round(fps, 1),
            "total_frames": total_frames,
            "analyzed_frames": len(self.timeline),
            "tree_ids": sorted({t["tree_id"] for t in self.timeline if t.get("tree_id")}),
            "per_tree": per_tree,
            "leaf_count_min": min(leaves), "leaf_count_max": max(leaves),
            "leaf_count_avg": round(float(np.mean(leaves)), 1),
            "fruit_count_min": min(fruits), "fruit_count_max": max(fruits),
            "fruit_count_avg": round(float(np.mean(fruits)), 1),
            "green_coverage_avg": round(float(np.mean(greens)), 2),
            "fruit_cover_avg": round(float(np.mean(fruit_covers)), 2) if fruit_covers else 0.0,
            "leaf_curl_avg": round(float(np.mean(curl_vals)), 3),
            "curled_leaf_pct_avg": round(float(np.mean([t.get("curled_leaf_pct", 0.0) for t in self.timeline])), 1),
            "leaf_roughness_avg": round(float(np.mean([t.get("leaf_roughness", 0.0) for t in self.timeline])), 3),
            "leaf_avg_hue_avg": round(float(np.mean(leaf_hues)), 1),
            "fruit_avg_hue_avg": round(float(np.mean(fruit_hues)), 1),
            "blur_level_avg": round(float(np.mean(blur_vals)), 3),
            "fruit_maturity_total": dict(sorted(maturity_tally.items())),
            "wrinkled_fruit_avg": round(float(np.mean(wrinkled)), 1),
            "fruit_wrinkle_total": dict(sorted(wrinkle_tally.items())),
            "tracked_leaves_max": max(tracked_leaves),
            "tracked_fruits_max": max(tracked_fruits),
            "duration_sec": round(self.timeline[-1]["timestamp_sec"], 1) if self.timeline else 0,
        }