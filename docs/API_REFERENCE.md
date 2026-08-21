# OliveVision AI - API Reference

This document describes the API for the main modules.

## Table of Contents

1. [runtime](#runtime) - Main analysis engine
2. [cli_ui](#cli_ui) - CLI UI helpers
3. [video_processor](#video_processor) - Video processing

---

## runtime

### Analyzer

Main analysis class for image processing.

#### `__init__(config: dict = None)`

Initialize analyzer with optional config override.

```python
from src.runtime import Analyzer
analyzer = Analyzer()
result = analyzer.analyze("image.jpg")
```

#### `analyze(path: str, tree_id: str = None) -> dict`

Analyze an image file.

**Parameters:**
- `path` (str): Path to image file
- `tree_id` (str, optional): Tree ID from QR code

**Returns:**
```python
{
    "timestamp": "2026-08-21T10:00:00",
    "source": "image",
    "tree_id": "1-3",
    "image_path": "path/to/image.jpg",
    "leaf_count": 39,
    "fruit_count": 3,
    "canopy_coverage": 0.45,
    "leaf_color_avg": {"hue": 56.2, "saturation": 120.5, "value": 89.3},
    "fruit_color_avg": {"hue": 45.0, "saturation": 150.0, "value": 100.0},
    "maturity_avg": 0.72,
    "yellow_leaf_ratio": 0.05,
    "wrinkle_score": 0.23,
    "leaf_curl_score": 0.15,
    "stress_level": "low",
    "analysis_details": {...}
}
```

#### `_detect_qr_tree_id(image) -> str | None`

Detect QR code and extract tree ID.

**Returns:**
- Tree ID string (e.g., "1-3") or None

#### `_compute_leaf_curl_score(leaf_contours, gray) -> float`

Compute leaf curl score (0-1).

**Parameters:**
- `leaf_contours`: List of leaf contours
- `gray`: Grayscale image

**Returns:**
- Curl score (0 = no curl, 1 = severe curl)

#### `_compute_wrinkle_score(image, mask) -> float`

Compute wrinkle score (0-1).

**Parameters:**
- `image`: BGR image
- `mask`: Leaf mask

**Returns:**
- Wrinkle score and reliability flag

#### `_compute_analysis_details(result, image) -> dict`

Compute detailed analysis for all sections.

**Returns:**
```python
{
    "leaf": {
        "count": 39,
        "avg_area": 1250.5,
        "total_area": 48769.5,
        "avg_circularity": 0.65,
        "avg_solidity": 0.82,
        "yellow_count": 2,
        "brown_count": 1
    },
    "fruit": {
        "count": 3,
        "avg_diameter": 15.2,
        "maturity_avg": 0.72,
        "color_classes": {"green": 1, "purple": 2}
    },
    "canopy": {
        "coverage": 0.45,
        "density": 0.78,
        "greenness": 0.85
    },
    "stress": {
        "wrinkle_score": 0.23,
        "leaf_curl_score": 0.15,
        "yellow_leaf_ratio": 0.05,
        "level": "low"
    }
}
```

---

### VideoAnalyzer

Video analysis class with DB persistence.

#### `__init__(config: dict = None, store: Store = None, persist: bool = False)`

**Parameters:**
- `config`: Configuration dict
- `store`: Store instance for DB persistence
- `persist`: Whether to persist results to DB

#### `analyze_video(path: str, tree_id: str = None, interval: int = 30) -> dict`

Analyze video file.

**Parameters:**
- `path`: Path to video file
- `tree_id`: Tree ID from QR code
- `interval`: Frame interval (default: 30 = 1 sec at 30fps)

**Returns:**
```python
{
    "timestamp": "2026-08-21T10:00:00",
    "source": "video",
    "video_path": "path/to/video.mp4",
    "tree_id": "1-3",
    "frame_count": 150,
    "duration_seconds": 5.0,
    "fps": 30.0,
    "frames": [
        {"frame_idx": 0, "leaf_count": 39, "fruit_count": 3, ...},
        {"frame_idx": 30, "leaf_count": 40, "fruit_count": 3, ...},
        ...
    ],
    "summary": {
        "leaf_count_avg": 39.5,
        "fruit_count_avg": 3.0,
        "leaf_curl_avg": 0.15,
        "maturity_avg": 0.72,
        ...
    },
    "trend": {
        "leaf_count_trend": "stable",
        "fruit_count_trend": "stable",
        "maturity_trend": "increasing"
    }
}
```

---

### Store

SQLite storage for analysis results.

#### `__init__(db_path: str = None)`

**Parameters:**
- `db_path`: Path to SQLite database (default: `data/database/olivevision.db`)

#### `save(result: dict) -> None`

Save analysis result to database.

#### `recent(limit: int = 10) -> list`

Get recent analysis results.

#### `recent_by_tree(tree_id: str, limit: int = 10) -> list`

Get recent results filtered by tree ID.

#### `recent_by_source(source: str, limit: int = 10) -> list`

Get recent results filtered by source (image/video).

#### `tree_ids() -> list`

Get all unique tree IDs.

#### `export_csv(output_path: str, tree_id: str = None, source: str = None) -> str`

Export data to CSV file.

**Returns:**
- Path to exported CSV file

---

### DEFAULTS

Default configuration values.

```python
DEFAULTS = {
    "detection": {
        "fruit_min_area": 250,
        "fruit_max_area": 50000,
        "leaf_min_area": 100,
        "leaf_max_area": 100000,
        "circle_dp": 1.2,
        "circle_min_dist": 30,
        "circle_param1": 100,
        "circle_param2": 30,
        "circle_min_radius": 5,
        "circle_max_radius": 50,
    },
    "analysis": {
        "curl_weights": {
            "tip_fraction": 0.4,
            "mid_fraction": 0.3,
            "base_fraction": 0.3,
        },
        "curl_threshold": 0.35,
        "wrinkle_discount": 0.5,
    },
    "stress": {
        "wrinkle_erosion": 3,
        "wrinkle_ridge_size": 5,
        "wrinkle_interior_frac": 0.1,
        "wrinkle_reliable_threshold": 0.3,
    },
    "trend": {
        "min_samples": 3,
        "window_size": 5,
    },
}
```

---

## cli_ui

### Color Helpers

```python
from src.cli_ui import bold, dim, cyan, green, yellow, red, magenta
```

- `bold(text)`: Bold text
- `dim(text)`: Dimmed text
- `cyan(text)`: Cyan text
- `green(text)`: Green text
- `yellow(text)`: Yellow text
- `red(text)`: Red text
- `magenta(text)`: Magenta text

### UI Components

```python
from src.cli_ui import panel, rule, Spinner, ProgressBar
```

- `panel(title, content)`: Create a panel with title
- `rule()`: Create a horizontal rule
- `Spinner(message)`: Context manager for spinner
- `ProgressBar(total)`: Progress bar

---

## video_processor

### VideoProcessor

Video file processing class.

#### `__init__(video_path: str)`

#### `get_frame_iterator(interval: int = 30) -> Generator`

Yield frames at specified interval.

```python
video = VideoProcessor("video.mp4")
for frame_idx, frame in video.get_frame_iterator(30):
    print(f"Frame {frame_idx}: {frame.shape}")
```

#### `get_statistics() -> dict`

Get video metadata.

**Returns:**
```python
{
    "fps": 30.0,
    "frame_count": 150,
    "width": 1920,
    "height": 1080,
    "duration_seconds": 5.0,
    "file_path": "path/to/video.mp4"
}
```

---

## Configuration

All parameters can be configured via `config/runtime.yaml`:

```yaml
detection:
  fruit_min_area: 250
  fruit_max_area: 50000
  leaf_min_area: 100
  leaf_max_area: 100000
  circle_dp: 1.2
  circle_min_dist: 30
  circle_param1: 100
  circle_param2: 30
  circle_min_radius: 5
  circle_max_radius: 50

analysis:
  curl_weights:
    tip_fraction: 0.4
    mid_fraction: 0.3
    base_fraction: 0.3
  curl_threshold: 0.35
  wrinkle_discount: 0.5

stress:
  wrinkle_erosion: 3
  wrinkle_ridge_size: 5
  wrinkle_interior_frac: 0.1
  wrinkle_reliable_threshold: 0.3

trend:
  min_samples: 3
  window_size: 5
```

---

## Error Handling

All modules use consistent error handling with `_error()` helper:

```python
from olivevision import _error

try:
    result = analyzer.analyze("image.jpg")
except Exception as e:
    _error("Analysis failed", detail=str(e), hint="Check file path")
```

---

**Version**: 0.3.0
**Last Updated**: 2026-08-21
