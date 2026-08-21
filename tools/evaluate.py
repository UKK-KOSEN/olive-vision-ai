"""Precision/recall evaluation for the fruit detector using ground-truth points.

Usage:
    python tools/evaluate.py <image> [--gt-file path.json]

GT file format (original image pixel coordinates, 0-indexed):
    {"fruits": [[x, y], ...]}

The detector analyses the image at `runtime.max_width` (isotropic), so the GT
is scaled by the same factor before matching. A detection matches a GT fruit
when its centre lies within `radius` pixels of the scaled GT point.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.runtime import Analyzer, load_runtime_config


def match(detections, gt_points, radius=60.0):
    """Greedy matching: each GT point binds to its nearest unused detection."""
    used = set()
    tp = 0
    matches = []                      # (gt_idx, det_idx, distance)
    for i, (gx, gy) in enumerate(gt_points):
        best_j, best_d = None, float("inf")
        for j, det in enumerate(detections):
            if j in used:
                continue
            d = float(np.hypot(det["center_x"] - gx, det["center_y"] - gy))
            if d < best_d:
                best_j, best_d = j, d
        if best_j is not None and best_d <= radius:
            used.add(best_j)
            tp += 1
            matches.append((i, best_j, round(best_d, 1)))
    return tp, matches


def evaluate(args):
    image = cv2.imread(str(args.image))
    if image is None:
        raise SystemExit(f"ERROR: cannot read {args.image}")

    config = load_runtime_config(args.config)
    analyzer = Analyzer(config)
    result, _ = analyzer.analyze(image, "eval")

    # Scale factor used inside the pipeline (isotropic to max_width).
    maxw = int(config["runtime"]["max_width"])
    scale = 1.0 if image.shape[1] <= maxw else maxw / image.shape[1]

    with open(args.gt_file, "r", encoding="utf-8") as f:
        gt_raw = json.load(f)
    gt = [[x * scale, y * scale] for x, y in gt_raw["fruits"]]

    detections = result["fruit_objects"]
    tp, matches = match(detections, gt, radius=args.radius)
    n_gt = len(gt)
    n_det = len(detections)
    precision = tp / n_det if n_det else 0.0
    recall = tp / n_gt if n_gt else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    print(f"Image         : {args.image.name}")
    print(f"Scale         : {scale:.4f}  (analysis {result['image_width']}x{result['image_height']})")
    print(f"Ground truth  : {n_gt} fruit(s)")
    print(f"Detected      : {n_det} fruit(s)")
    print(f"Match radius  : {args.radius}px")
    print("-" * 40)
    print(f"True positives: {tp}")
    print(f"Precision     : {precision:.3f}  ({tp}/{n_det})")
    print(f"Recall        : {recall:.3f}  ({tp}/{n_gt})")
    print(f"F1            : {f1:.3f}")
    if args.show_matches:
        print("-" * 40)
        det = detections
        for i, (gx, gy) in enumerate(gt):
            hit = next((d for d in matches if d[0] == i), None)
            if hit:
                d = detections[hit[1]]
                print(f"  GT#{i} ({gx:.0f},{gy:.0f}) -> det ({d['center_x']:.0f},{d['center_y']:.0f}) "
                      f"dist {hit[2]}px conf {d['confidence']:.0%}")
            else:
                print(f"  GT#{i} ({gx:.0f},{gy:.0f}) -> MISSED")
        print("-" * 40)
        for j, d in enumerate(detections):
            hit = next((m for m in matches if m[1] == j), None)
            if not hit:
                print(f"  det#{j} ({d['center_x']:.0f},{d['center_y']:.0f}) -> NO MATCH (FP)")
    return f1


def main():
    p = argparse.ArgumentParser(description="Evaluate fruit detection precision/recall vs GT.")
    p.add_argument("image", type=Path)
    p.add_argument("--gt-file", type=Path, default=None,
                   help="JSON with {\"fruits\": [[x,y],...]} in original coords. "
                        "Defaults to <image>.gt.json beside the image.")
    p.add_argument("--radius", type=float, default=60.0,
                   help="match radius in analysis-pixel units")
    p.add_argument("--config", default="config/runtime.yaml")
    p.add_argument("--show-matches", action="store_true")
    args = p.parse_args()
    args.gt_file = args.gt_file or args.image.with_suffix(args.image.suffix + ".gt.json")
    if not args.gt_file.is_file():
        raise SystemExit(f"ERROR: no GT file found: {args.gt_file}")
    f1 = evaluate(args)
    sys.exit(0 if f1 > 0 else 1)


if __name__ == "__main__":
    main()
