# OliveVision AI - Usage Examples

This document provides practical examples for common use cases.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Image Analysis](#image-analysis)
3. [Video Analysis](#video-analysis)
4. [CLI Commands](#cli-commands)
5. [Programmatic Usage](#programmatic-usage)
6. [Configuration](#configuration)

---

## Basic Usage

### Command Line

```bash
# Analyze a single image
python olivevision.py image.jpg

# Analyze with tree ID
python olivevision.py image.jpg --tree-id "1-3"

# Launch GUI
python olivevision.py --gui

# Monitor mode
python olivevision.py --monitor --interval 60
```

### Output

```
outputs/
├── observations/
│   └── 2026-08-21_10-00-00.json    # Analysis result
├── preview/
│   └── annotated_image.jpg          # Annotated image
└── olivevision.db                   # SQLite database
```

---

## Image Analysis

### Example 1: Basic Analysis

```python
from src.runtime import Analyzer

analyzer = Analyzer()
result = analyzer.analyze("image.jpg")

print(f"Leaf count: {result['leaf_count']}")
print(f"Fruit count: {result['fruit_count']}")
print(f"Canopy coverage: {result['canopy_coverage']:.2%}")
```

### Example 2: Analysis with Tree ID

```python
from src.runtime import Analyzer

analyzer = Analyzer()
result = analyzer.analyze("image.jpg", tree_id="1-3")

print(f"Tree ID: {result['tree_id']}")
print(f"Leaf count: {result['leaf_count']}")
```

### Example 3: Custom Configuration

```python
from src.runtime import Analyzer

config = {
    "detection": {
        "fruit_min_area": 300,
        "leaf_min_area": 150,
    }
}

analyzer = Analyzer(config=config)
result = analyzer.analyze("image.jpg")
```

### Example 4: Accessing Analysis Details

```python
from src.runtime import Analyzer

analyzer = Analyzer()
result = analyzer.analyze("image.jpg")

details = result["analysis_details"]

# Leaf details
print(f"Leaf count: {details['leaf']['count']}")
print(f"Average area: {details['leaf']['avg_area']:.1f}")
print(f"Yellow leaves: {details['leaf']['yellow_count']}")

# Fruit details
print(f"Fruit count: {details['fruit']['count']}")
print(f"Average diameter: {details['fruit']['avg_diameter']:.1f}")
print(f"Maturity: {details['fruit']['maturity_avg']:.2%}")

# Stress indicators
print(f"Wrinkle score: {details['stress']['wrinkle_score']:.2f}")
print(f"Leaf curl: {details['stress']['leaf_curl_score']:.2f}")
print(f"Stress level: {details['stress']['level']}")
```

---

## Video Analysis

### Example 1: Basic Video Analysis

```python
from src.runtime import VideoAnalyzer

analyzer = VideoAnalyzer()
result = analyzer.analyze_video("video.mp4")

print(f"Frames analyzed: {result['frame_count']}")
print(f"Duration: {result['duration_seconds']:.1f}s")
print(f"Summary: {result['summary']}")
```

### Example 2: Video with DB Persistence

```python
from src.runtime import VideoAnalyzer, Store

store = Store()
analyzer = VideoAnalyzer(store=store, persist=True)

result = analyzer.analyze_video("video.mp4", tree_id="1-3")

# Results are now in the database
print(f"Saved {result['frame_count']} frames to database")
```

### Example 3: Custom Frame Interval

```python
from src.runtime import VideoAnalyzer

analyzer = VideoAnalyzer()

# Analyze every 2 seconds (at 30fps)
result = analyzer.analyze_video("video.mp4", interval=60)

# Analyze every frame (slow)
result = analyzer.analyze_video("video.mp4", interval=1)
```

---

## CLI Commands

### Status Command

```bash
# Show recent analyses
python olivevision.py status

# Filter by tree ID
python olivevision.py status --tree "1-3"

# Filter by source
python olivevision.py status --source video

# Limit results
python olivevision.py status --limit 20
```

### Trend Command

```bash
# Show trend analysis
python olivevision.py trend

# Filter by tree ID
python olivevision.py trend --tree "1-3"

# Filter by source
python olivevision.py trend --source image
```

### Trees Command

```bash
# List all tree IDs
python olivevision.py trees
```

### Export Command

```bash
# Export to CSV
python olivevision.py export --format csv

# Export specific tree
python olivevision.py export --tree "1-3" --format csv

# Export to JSON
python olivevision.py export --format json
```

---

## Programmatic Usage

### Example 1: Store Operations

```python
from src.runtime import Store

store = Store()

# Get recent results
results = store.recent(limit=10)
for r in results:
    print(f"{r['timestamp']}: {r['leaf_count']} leaves")

# Filter by tree
results = store.recent_by_tree("1-3")

# Filter by source
results = store.recent_by_source("video")

# Get all tree IDs
tree_ids = store.tree_ids()
print(f"Trees: {tree_ids}")

# Export to CSV
store.export_csv("output.csv", tree_id="1-3")
```

### Example 2: QR Code Detection

```python
import cv2
from src.runtime import Analyzer

analyzer = Analyzer()

# Load image
image = cv2.imread("image_with_qr.jpg")

# Detect QR code
tree_id = analyzer._detect_qr_tree_id(image)
print(f"Detected tree: {tree_id}")

# Analyze with detected ID
result = analyzer.analyze("image_with_qr.jpg")
print(f"Tree ID: {result['tree_id']}")
```

---

## Configuration

### Example 1: Runtime YAML

Edit `config/runtime.yaml`:

```yaml
detection:
  fruit_min_area: 250
  fruit_max_area: 50000
  leaf_min_area: 100
  leaf_max_area: 100000
  circle_dp: 1.2
  circle_min_dist: 30

analysis:
  curl_weights:
    tip_fraction: 0.4
    mid_fraction: 0.3
    base_fraction: 0.3
  curl_threshold: 0.35

stress:
  wrinkle_erosion: 3
  wrinkle_ridge_size: 5
  wrinkle_interior_frac: 0.1
```

### Example 2: Programmatic Configuration

```python
from src.runtime import Analyzer

config = {
    "detection": {
        "fruit_min_area": 300,
        "leaf_min_area": 150,
        "circle_dp": 1.5,
    },
    "analysis": {
        "curl_threshold": 0.4,
    }
}

analyzer = Analyzer(config=config)
result = analyzer.analyze("image.jpg")
```

---

## Troubleshooting

### No detections?

- Check lighting conditions
- Adjust `detection.fruit_min_area` in config
- Ensure QR code is clearly visible (if using tree IDs)

### Slow performance?

- Increase `detection.leaf_min_area`
- Use `interval=60` for video analysis
- Reduce image resolution

### QR code not detected?

- Ensure QR code is clearly visible
- Try different angles/lighting
- Check that QR code contains "第N試験樹" format

---

**Version**: 0.3.0
**Last Updated**: 2026-08-21
