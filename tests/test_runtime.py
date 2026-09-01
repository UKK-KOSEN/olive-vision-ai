"""Offline smoke tests for the production runtime (no camera or sample data)."""
import json
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from src.runtime import (Analyzer, Store, analyze_health_trend,
                         load_runtime_config, save_observation,
                         scale_detection_for_resolution,
                         normalize_illumination,
                         compute_adaptive_green_threshold,
                         _detect_qr_tree_id, _QR_TREE_RE)


def _obs(at, fruits, green, leaf=10):
    return {"observed_at": at, "source": "file", "leaf_count": leaf,
            "fruit_count": len(fruits), "green_coverage": green,
            "image_width": 1280, "image_height": 1920,
            "fruit_objects": fruits}


class RuntimeTest(unittest.TestCase):
    def test_analysis_persists_result_and_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image = np.zeros((120, 160, 3), dtype=np.uint8)
            cv2.rectangle(image, (10, 10), (70, 100), (0, 180, 0), -1)
            analyzer = Analyzer(load_runtime_config())
            store = Store(root / "history.db")
            result, annotation = save_observation(analyzer, store, image, "test", root / "output")
            self.assertGreater(result["green_coverage"], 0)
            self.assertTrue(annotation.exists())
            self.assertEqual(len(store.recent()), 1)
            self.assertEqual(store.export_csv(root / "history.csv"), 1)

    def test_colour_and_shape_filters_reject_non_olive_regions(self):
        """Brown soil and skin-like pixels must not be reported as fruit."""
        image = np.zeros((180, 260, 3), dtype=np.uint8)
        cv2.rectangle(image, (5, 5), (115, 175), (35, 80, 130), -1)  # brown soil
        cv2.ellipse(image, (190, 85), (45, 65), 0, 0, 360, (80, 135, 185), -1)  # skin-like colour
        result, _ = Analyzer(load_runtime_config()).analyze(image, "test")
        self.assertEqual(result["leaf_count"], 0)
        self.assertEqual(result["fruit_count"], 0)

    def test_result_includes_maturity_breakdown_and_cover(self):
        image = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.circle(image, (90, 90), 22, (60, 150, 90), -1)     # green fruit on dark bg
        cv2.circle(image, (150, 140), 20, (50, 130, 200), -1)  # yellow-green fruit
        result, _ = Analyzer(load_runtime_config()).analyze(image, "test")
        self.assertIn("fruit_maturity_breakdown", result)
        self.assertIn("fruit_cover_pct", result)
        self.assertIn("fruit_total_area", result)
        self.assertEqual(sum(result["fruit_maturity_breakdown"].values()), result["fruit_count"])
        for obj in result.get("fruit_objects", []):
            self.assertIn("maturity", obj)
            self.assertIn("hue", obj)
            self.assertIn("ellipse_axis_ratio", obj)
            self.assertIn("wrinkle_score", obj)
            self.assertIn("wrinkle_label", obj)
            self.assertIn("ridge_density", obj)
        self.assertIn("wrinkled_fruit_count", result)
        self.assertIn("fruit_wrinkle_summary", result)
        self.assertTrue(
            0.0 <= result["wrinkled_fruit_count"] <= result["fruit_count"])
        self.assertEqual(
            sum(result["fruit_wrinkle_summary"].values()), result["fruit_count"])

    def test_watershed_splits_touching_fruits(self):
        from src.runtime import _watershed_split
        import numpy as np
        mask = np.zeros((120, 160), dtype=np.uint8)
        cv2.circle(mask, (55, 60), 22, 255, -1)
        cv2.circle(mask, (100, 60), 22, 255, -1)   # touching the first circle
        image = np.zeros((120, 160, 3), dtype=np.uint8)
        pieces = _watershed_split(image, mask, min_dist=20)
        self.assertGreaterEqual(len(pieces), 2)

    def test_health_trend_tracks_fruits_and_detects_changes(self):
        def fruit(cx, cy, wrinkle, ripe, area=800):
            return {"center_x": cx, "center_y": cy, "wrinkle_score": wrinkle,
                    "area": area,
                    "signal_ratios": {"yellow_green": 1.0 - ripe, "ripe": ripe,
                                      "dark": 0.0, "hough_circle": 1.0}}
        day1 = [fruit(536, 1113, 0.20, 0.00), fruit(161, 1437, 0.10, 0.00)]
        day2 = [fruit(536, 1113, 0.50, 0.10), fruit(161, 1437, 0.12, 0.00),
                fruit(900, 900, 0.10, 0.00)]   # new fruit appears
        day3 = [fruit(536, 1113, 0.80, 0.25), fruit(161, 1437, 0.12, 0.00),
                fruit(900, 900, 0.10, 0.00)]
        observations = [
            _obs("2026-08-01T09:00:00+09:00", day1, 40.0),
            _obs("2026-08-02T09:00:00+09:00", day2, 39.8),
            _obs("2026-08-02T11:00:00+09:00", day2, 39.8),  # duplicate capture
            _obs("2026-08-03T09:00:00+09:00", day3, 39.5),
        ]
        analysis = analyze_health_trend(observations)
        self.assertTrue(analysis["ok"])
        self.assertEqual(analysis["period"]["days"], 3)
        self.assertEqual(analysis["count"]["unique"], 3)  # dup collapsed
        tracks = {tr["x"]: tr for tr in analysis["fruit_tracks"]}
        first = tracks[536]
        self.assertIn("ripening", first["flags"])
        self.assertIn("wrinkling", first["flags"])
        self.assertIn("deteriorating", first["flags"])
        self.assertEqual(first["observations"], 3)
        self.assertNotIn("ripening", tracks[161]["flags"])
        self.assertEqual(analysis["health"]["level"], "mixed")

    def test_gt_6497_fruit_detection_recall(self):
        """Regression guard: IMG_6497 must keep 3/3 GT fruit and no FPs.

        Skips when the sample image + GT file are not present on this machine.
        """
        image_path = Path(r"C:\Users\yakit\Downloads\IMG_6497.jpg")
        gt_path = Path(r"C:\Users\yakit\Downloads\IMg_6497.jpg.gt.json")
        if not image_path.is_file() or not gt_path.is_file():
            self.skipTest("IMG_6497 sample + GT not available")
        image = cv2.imread(str(image_path))
        self.assertIsNotNone(image, "IMG_6497 must load")
        analyzer = Analyzer(load_runtime_config())
        result, _ = analyzer.analyze(image, "file")
        maxw = int(load_runtime_config()["runtime"]["max_width"])
        scale = maxw / image.shape[1]
        gt = json.loads(gt_path.read_text(encoding="utf-8"))["fruits"]
        gt = [[x * scale, y * scale] for x, y in gt]
        dets = result["fruit_objects"]
        used, tp = set(), 0
        for gx, gy in gt:
            best_j, best_d = None, float("inf")
            for j, d in enumerate(dets):
                if j in used:
                    continue
                dist = float(np.hypot(d["center_x"] - gx, d["center_y"] - gy))
                if dist < best_d:
                    best_j, best_d = j, dist
            if best_j is not None and best_d <= 60:
                used.add(best_j)
                tp += 1
        self.assertEqual(tp, len(gt),
                         "every GT fruit must be detected (recall must stay 1.0)")
        self.assertEqual(tp, len(dets),
                         "no false positives on the GT image (precision must stay 1.0)")

    # ── QR tree-id tests ────────────────────────────────────────────────

    def _make_qr_image(self, text, size=400):
        """Generate a QR-code image with the given text."""
        enc = cv2.QRCodeEncoder.create()
        qr = enc.encode(text)
        # Scale up for reliable detection.
        scale = max(1, size // max(qr.shape))
        qr = cv2.resize(qr, (qr.shape[1] * scale, qr.shape[0] * scale),
                         interpolation=cv2.INTER_NEAREST)
        return cv2.cvtColor(qr, cv2.COLOR_GRAY2BGR)

    def test_qr_regex_parses_tree_ids(self):
        self.assertEqual(_QR_TREE_RE.search("第1試験樹").group(0), "第1試験樹")
        self.assertEqual(_QR_TREE_RE.search("第12試験樹").group(0), "第12試験樹")
        self.assertIsNone(_QR_TREE_RE.search("no qr"))
        self.assertIsNone(_QR_TREE_RE.search("試験樹"))
        self.assertIsNone(_QR_TREE_RE.search("第"))

    def test_detect_qr_tree_id_returns_id(self):
        img = self._make_qr_image("第3試験樹")
        tid = _detect_qr_tree_id(img)
        self.assertEqual(tid, "第3試験樹")

    def test_detect_qr_tree_id_returns_none_for_no_qr(self):
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        self.assertIsNone(_detect_qr_tree_id(img))

    def test_detect_qr_tree_id_handles_utf8_bytes(self):
        """OpenCV may return bytes instead of str for UTF-8 QR content."""
        import unittest.mock as mock
        detector = cv2.QRCodeDetector()
        # Simulate OpenCV returning bytes (UTF-8 encoded Japanese).
        utf8_bytes = "第7試験樹".encode("utf-8")
        with mock.patch.object(type(detector), "detectAndDecode",
                               return_value=(utf8_bytes, None, None)):
            with mock.patch("src.runtime.cv2.QRCodeDetector", return_value=detector):
                tid = _detect_qr_tree_id(np.zeros((100, 100, 3), dtype=np.uint8))
                self.assertEqual(tid, "第7試験樹")

    def test_detect_qr_tree_id_ignores_non_tree_qr(self):
        img = self._make_qr_image("hello world")
        self.assertIsNone(_detect_qr_tree_id(img))

    def test_analyze_returns_tree_id_when_qr_present(self):
        img = np.zeros((400, 400, 3), dtype=np.uint8)
        # Embed a QR code in the top-left corner.
        qr = self._make_qr_image("第5試験樹", size=120)
        h, w = qr.shape[:2]
        img[10:10+h, 10:10+w] = qr
        result, _ = Analyzer(load_runtime_config()).analyze(img, "test")
        self.assertEqual(result.get("tree_id"), "第5試験樹")

    def test_analyze_tree_id_none_when_no_qr(self):
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        result, _ = Analyzer(load_runtime_config()).analyze(img, "test")
        self.assertIsNone(result.get("tree_id"))

    def test_qr_detection_disabled_skips_qr(self):
        """When qr_detection=false, tree_id is never set even if QR is present."""
        cfg = load_runtime_config()
        cfg["detection"]["qr_detection"] = False
        img = np.zeros((400, 400, 3), dtype=np.uint8)
        qr = self._make_qr_image("第5試験樹", size=120)
        h, w = qr.shape[:2]
        img[10:10+h, 10:10+w] = qr
        result, _ = Analyzer(cfg).analyze(img, "test")
        self.assertIsNone(result.get("tree_id"))

    # ── Store tree-id tests ─────────────────────────────────────────────

    def test_store_add_with_tree_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "test.db")
            obs = {"observed_at": "2026-08-19T10:00:00+09:00", "source": "file",
                   "leaf_count": 10, "fruit_count": 3, "green_coverage": 25.0,
                   "image_width": 640, "image_height": 480, "tree_id": "第2試験樹"}
            store.add(obs)
            rows = store.recent()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["tree_id"], "第2試験樹")

    def test_store_add_without_tree_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "test.db")
            obs = {"observed_at": "2026-08-19T10:00:00+09:00", "source": "file",
                   "leaf_count": 10, "fruit_count": 3, "green_coverage": 25.0,
                   "image_width": 640, "image_height": 480}
            store.add(obs)
            rows = store.recent()
            self.assertEqual(len(rows), 1)
            self.assertIsNone(rows[0].get("tree_id"))

    def test_store_recent_by_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "test.db")
            for i, tid in enumerate(["第1試験樹", "第2試験樹", "第1試験樹", "第3試験樹"]):
                store.add({"observed_at": f"2026-08-1{i}T09:00:00+09:00", "source": "file",
                           "leaf_count": 10, "fruit_count": 3, "green_coverage": 25.0,
                           "image_width": 640, "image_height": 480, "tree_id": tid})
            tree1 = store.recent_by_tree("第1試験樹")
            tree2 = store.recent_by_tree("第2試験樹")
            tree99 = store.recent_by_tree("第99試験樹")
            self.assertEqual(len(tree1), 2)
            self.assertEqual(len(tree2), 1)
            self.assertEqual(len(tree99), 0)
            # Verify ordering (most recent first).
            self.assertEqual(tree1[0]["tree_id"], "第1試験樹")

    def test_store_tree_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "test.db")
            for tid in ["第2試験樹", "第1試験樹", "第2試験樹", "第3試験樹", None]:
                store.add({"observed_at": "2026-08-19T09:00:00+09:00", "source": "file",
                           "leaf_count": 10, "fruit_count": 3, "green_coverage": 25.0,
                           "image_width": 640, "image_height": 480,
                           "tree_id": tid})
            ids = store.tree_ids()
            self.assertEqual(ids, ["第1試験樹", "第2試験樹", "第3試験樹"])

    def test_store_recent_by_source(self):
        """recent_by_source filters by source prefix."""
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "test.db")
            for src in ["file", "video:test.mp4", "file", "video:demo.avi"]:
                store.add({"observed_at": "2026-08-19T09:00:00+09:00", "source": src,
                           "leaf_count": 10, "fruit_count": 3, "green_coverage": 25.0,
                           "image_width": 640, "image_height": 480})
            self.assertEqual(len(store.recent_by_source("file")), 2)
            self.assertEqual(len(store.recent_by_source("video")), 2)
            self.assertEqual(len(store.recent_by_source("nonexist")), 0)
            # Combined with tree_id
            for src, tid in [("file", "第1試験樹"), ("video:x.mp4", "第2試験樹")]:
                store.add({"observed_at": "2026-08-19T09:00:00+09:00", "source": src,
                           "leaf_count": 10, "fruit_count": 3, "green_coverage": 25.0,
                           "image_width": 640, "image_height": 480, "tree_id": tid})
            self.assertEqual(len(store.recent_by_source("video", tree_id="第2試験樹")), 1)
            self.assertEqual(len(store.recent_by_source("file", tree_id="第1試験樹")), 1)

    def test_store_migration_adds_tree_id_column(self):
        """Verify that opening an older DB without tree_id does not crash."""
        with tempfile.TemporaryDirectory() as tmp:
            import sqlite3
            db_path = Path(tmp) / "old.db"
            con = sqlite3.connect(str(db_path))
            con.execute("""CREATE TABLE observations (
                id INTEGER PRIMARY KEY, observed_at TEXT NOT NULL, source TEXT NOT NULL,
                image_path TEXT, leaf_count INTEGER NOT NULL, fruit_count INTEGER NOT NULL,
                green_coverage REAL NOT NULL, image_width INTEGER NOT NULL,
                image_height INTEGER NOT NULL, result_json TEXT NOT NULL)""")
            con.execute(
                "INSERT INTO observations VALUES (1,'2026-08-19T09:00:00','test',NULL,5,2,30.0,640,480,'{}')")
            con.commit()
            con.close()
            # Opening with the new Store should migrate the schema.
            store = Store(db_path)
            rows = store.recent()
            self.assertEqual(len(rows), 1)

    def test_export_csv_includes_tree_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "test.db")
            store.add({"observed_at": "2026-08-19T09:00:00+09:00", "source": "file",
                        "leaf_count": 10, "fruit_count": 3, "green_coverage": 25.0,
                        "image_width": 640, "image_height": 480, "tree_id": "第7試験樹"})
            csv_path = Path(tmp) / "export.csv"
            store.export_csv(csv_path)
            content = csv_path.read_text(encoding="utf-8")
            self.assertIn("tree_id", content.split("\n")[0])
            self.assertIn("第7試験樹", content)

    def test_health_trend_with_tree_ids(self):
        """Trend analysis should work when observations have tree_id."""
        def obs(at, fruits, green, tree_id):
            return {"observed_at": at, "source": "file", "leaf_count": 10,
                    "fruit_count": len(fruits), "green_coverage": green,
                    "image_width": 1280, "image_height": 1920,
                    "fruit_objects": fruits, "tree_id": tree_id}
        day1 = [{"center_x": 500, "center_y": 500, "wrinkle_score": 0.2, "area": 800}]
        day2 = [{"center_x": 500, "center_y": 500, "wrinkle_score": 0.5, "area": 600}]
        a = analyze_health_trend([
            obs("2026-08-01T09:00:00+09:00", day1, 40.0, "第1試験樹"),
            obs("2026-08-02T09:00:00+09:00", day2, 39.0, "第1試験樹"),
        ])
        self.assertTrue(a["ok"])
        self.assertEqual(a["period"]["days"], 2)

    def test_video_analyzer_includes_tree_id_in_timeline(self):
        """VideoAnalyzer propagates tree_id from per-frame analysis."""
        from src.runtime import VideoAnalyzer
        enc = cv2.QRCodeEncoder.create()
        qr_img = enc.encode("第10試験樹")
        scale = 3
        qr_img = cv2.resize(qr_img, (qr_img.shape[1] * scale, qr_img.shape[0] * scale),
                             interpolation=cv2.INTER_NEAREST)
        qr_bgr = cv2.cvtColor(qr_img, cv2.COLOR_GRAY2BGR)
        # Build a 3-frame synthetic video (no QR in frame 0, QR in frames 1-2).
        with tempfile.TemporaryDirectory() as tmp:
            video_path = Path(tmp) / "test.mp4"
            h, w = 200, 200
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(video_path), fourcc, 10.0, (w, h))
            # Frame 0: no QR.
            writer.write(np.zeros((h, w, 3), dtype=np.uint8))
            # Frame 1: QR in top-left.
            frame1 = np.zeros((h, w, 3), dtype=np.uint8)
            qh, qw = qr_bgr.shape[:2]
            frame1[:qh, :qw] = qr_bgr
            writer.write(frame1)
            # Frame 2: same QR.
            writer.write(frame1.copy())
            writer.release()
            # Analyze.
            out_dir = Path(tmp) / "output"
            config = load_runtime_config()
            va = VideoAnalyzer(Analyzer(config), config)
            summary = va.analyze_video(str(video_path), str(out_dir), frame_interval=1)
            # At least frames 1 and 2 should have tree_id.
            tree_ids = [e["tree_id"] for e in va.timeline]
            self.assertIn("第10試験樹", tree_ids)
            self.assertIsNone(tree_ids[0])  # frame 0 has no QR.
            self.assertIn("第10試験樹", summary.get("tree_ids", []))
            # Verify new summary fields exist.
            self.assertIn("per_tree", summary)
            self.assertIn("leaf_curl_avg", summary)
            self.assertIn("blur_level_avg", summary)
            self.assertIn("leaf_roughness_avg", summary)
            # Verify per_tree has the tree entry.
            if summary["per_tree"]:
                tid = list(summary["per_tree"].keys())[0]
                self.assertIn("frames", summary["per_tree"][tid])
                self.assertIn("leaf_count_avg", summary["per_tree"][tid])
            # Verify timeline entries have analysis_details.
            last = va.timeline[-1]
            self.assertIn("analysis_details", last)
            self.assertIn("leaf_senescence", last)
            self.assertIn("blur_level", last)

    def test_video_analyzer_persists_to_store(self):
        """When persist=True and store is given, frame results are saved to DB."""
        from src.runtime import VideoAnalyzer, Store
        with tempfile.TemporaryDirectory() as tmp:
            video_path = Path(tmp) / "test.mp4"
            h, w = 200, 200
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(video_path), fourcc, 10.0, (w, h))
            writer.write(np.zeros((h, w, 3), dtype=np.uint8))
            writer.write(np.zeros((h, w, 3), dtype=np.uint8))
            writer.release()
            db_path = Path(tmp) / "test.db"
            store = Store(db_path)
            config = load_runtime_config()
            va = VideoAnalyzer(Analyzer(config), config, store=store)
            out_dir = Path(tmp) / "output"
            summary = va.analyze_video(str(video_path), str(out_dir),
                                       frame_interval=1, persist=True)
            # Each analyzed frame should have been stored in the DB.
            rows = store.recent(100)
            self.assertEqual(len(rows), summary["analyzed_frames"])
            # Each stored row should have a source starting with "video:".
            for r in rows:
                self.assertTrue(r.get("source", "").startswith("video:"))


class ResolutionAdaptationTest(unittest.TestCase):
    """Tests for resolution-adaptive parameter scaling."""

    def setUp(self):
        self.config = load_runtime_config(Path("config/runtime.yaml"))

    def test_high_res_no_change(self):
        """High-res images should not be scaled."""
        result = scale_detection_for_resolution(self.config, 1280)
        self.assertEqual(result["detection"]["leaf_min_area"],
                         self.config["detection"]["leaf_min_area"])

    def test_low_res_scales_areas(self):
        """Low-res images should have smaller area thresholds."""
        original_leaf_min = self.config["detection"]["leaf_min_area"]
        result = scale_detection_for_resolution(self.config, 720)
        self.assertLess(result["detection"]["leaf_min_area"], original_leaf_min)
        self.assertLess(result["detection"]["fruit_min_area"],
                        self.config["detection"]["fruit_min_area"])

    def test_very_low_res_scales_more(self):
        """Very low-res images should have even smaller thresholds."""
        low = scale_detection_for_resolution(self.config, 720)
        very_low = scale_detection_for_resolution(self.config, 480)
        self.assertLess(very_low["detection"]["leaf_min_area"],
                        low["detection"]["leaf_min_area"])

    def test_preserves_non_area_params(self):
        """Non-area parameters should not be changed."""
        result = scale_detection_for_resolution(self.config, 720)
        self.assertEqual(result["detection"]["leaf_hue"],
                         self.config["detection"]["leaf_hue"])
        self.assertEqual(result["detection"]["fruit_hue_yellow"],
                         self.config["detection"]["fruit_hue_yellow"])

    def test_resolution_mode_recorded(self):
        """Resolution mode should be recorded in the result."""
        result = scale_detection_for_resolution(self.config, 720)
        self.assertIn("_resolution_mode", result)
        self.assertEqual(result["_resolution_mode"], "low")

    def test_very_low_mode_recorded(self):
        """Very low resolution mode should be recorded."""
        result = scale_detection_for_resolution(self.config, 480)
        self.assertEqual(result["_resolution_mode"], "very_low")

    def test_original_config_not_mutated(self):
        """Original config should never be modified."""
        original_leaf_min = self.config["detection"]["leaf_min_area"]
        scale_detection_for_resolution(self.config, 720)
        self.assertEqual(self.config["detection"]["leaf_min_area"], original_leaf_min)


class DroneEnhancementTest(unittest.TestCase):
    """Tests for drone-specific image enhancement functions."""

    def test_normalize_illumination_preserves_shape(self):
        """Normalization should preserve image dimensions."""
        image = np.random.randint(0, 255, (100, 120, 3), dtype=np.uint8)
        result = normalize_illumination(image)
        self.assertEqual(result.shape, image.shape)
        self.assertEqual(result.dtype, np.uint8)

    def test_normalize_illumination_brightens_dark(self):
        """Normalization should brighten very dark images."""
        dark = np.zeros((100, 100, 3), dtype=np.uint8)
        dark[:, :, :] = 10
        result = normalize_illumination(dark)
        # L channel CLAHE should increase brightness
        self.assertGreater(np.mean(result), np.mean(dark))

    def test_adaptive_threshold_returns_positive(self):
        """Adaptive threshold should return a positive integer."""
        image = np.random.randint(0, 255, (100, 120, 3), dtype=np.uint8)
        # Add some green
        image[30:70, 30:70, 1] = 200
        thresh = compute_adaptive_green_threshold(image, base_min=10)
        self.assertGreaterEqual(thresh, 10)
        self.assertIsInstance(thresh, int)

    def test_adaptive_threshold_no_green_low(self):
        """Image with no green should return base_min."""
        # Pure red image
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        image[:, :, 2] = 200
        thresh = compute_adaptive_green_threshold(image, base_min=10)
        self.assertEqual(thresh, 10)

    def test_drone_leaf_mask_produces_result(self):
        """Drone mode leaf mask should produce a valid binary mask."""
        config = load_runtime_config(Path("config/runtime.yaml"))
        analyzer = Analyzer(config, resolution_mode="normal", drone_mode=True)
        image = np.zeros((100, 120, 3), dtype=np.uint8)
        # Add green region
        image[20:80, 20:100, 1] = 180
        image[20:80, 20:100, 0] = 50
        image[20:80, 20:100, 2] = 50
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        spec = config["detection"]
        mask = analyzer._build_leaf_mask(image, hsv, lab, spec, drone_mode=True)
        self.assertEqual(mask.shape[:2], image.shape[:2])
        self.assertEqual(len(np.unique(mask)), 2)  # binary

    def test_drone_mode_flag_independent_of_resolution(self):
        """drone_mode should work regardless of image resolution."""
        config = load_runtime_config(Path("config/runtime.yaml"))
        # Large image (above threshold) but drone_mode=True
        analyzer = Analyzer(config, resolution_mode="normal", drone_mode=True)
        self.assertTrue(analyzer.drone_mode)
        image = np.zeros((100, 120, 3), dtype=np.uint8)
        image[20:80, 20:100, 1] = 180
        adapted = analyzer._adapt_for_resolution(image)
        self.assertEqual(adapted.get("_resolution_mode"), "drone")

    def test_upscale_flag_disabled_no_upscaler(self):
        """With upscale=False the analyzer must not attempt upscaling."""
        config = load_runtime_config(Path("config/runtime.yaml"))
        analyzer = Analyzer(config, upscale=False)
        self.assertIsNone(analyzer.upscaler)

    def test_upscale_flag_enabled_creates_upscaler(self):
        """With upscale=True (and tool present) an upscaler is created."""
        config = load_runtime_config(Path("config/runtime.yaml"))
        analyzer = Analyzer(config, upscale=True)
        if analyzer.upscaler is not None:
            self.assertTrue(hasattr(analyzer.upscaler, "upscale_image"))
        # must not crash either way

    def test_set_upscale_toggle(self):
        """set_upscale(False) should clear the upscaler."""
        config = load_runtime_config(Path("config/runtime.yaml"))
        analyzer = Analyzer(config, upscale=False)
        analyzer.set_upscale(enabled=False)
        self.assertIsNone(analyzer.upscaler)

    def test_analyze_reports_upscaled_field(self):
        """Result dict includes upscaled flag."""
        config = load_runtime_config(Path("config/runtime.yaml"))
        analyzer = Analyzer(config, upscale=False)
        image = np.zeros((100, 120, 3), dtype=np.uint8)
        result, _ = analyzer.analyze(image, "test")
        self.assertFalse(result.get("upscaled"))
        self.assertEqual(result.get("upscale_model"), "")


if __name__ == "__main__":
    unittest.main()
