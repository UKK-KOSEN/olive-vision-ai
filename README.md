# OliveVision AI

> Raspberry Pi-friendly local olive monitoring system using classical computer vision

[![Tests](https://img.shields.io/badge/tests-24%20passing-brightgreen)](tests/test_runtime.py)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## Overview

OliveVision AI analyzes olive tree images and videos to detect leaves, fruits, and canopy, extract biological features, and track long-term trends. Everything runs locally on a Raspberry Pi with no GPU, cloud, or training required.

## Quick Start

```bash
git clone https://github.com/UKK-KOSEN/olive-vision-ai.git
cd olive-vision-ai
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac
pip install -r requirements.txt

python olivevision.py image.jpg
```

## Features

| Category | Features |
|----------|----------|
| **Image Analysis** | Leaf detection (HSV/LAB + watershed), Fruit detection (Hough circles + contours), QR code tree ID, Canopy analysis, Stress indicators (wrinkle, curl, yellowing) |
| **Video Analysis** | Frame-by-frame analysis, Trend tracking, Summary statistics, DB persistence |
| **Data Management** | SQLite storage, Time-series tracking, CSV/JSON export, Tree ID tracking |
| **CLI** | Status, Trend, Trees, Export, Monitor mode |
| **GUI** | Image selection, Camera capture, Annotated preview, History view |

## CLI Commands

| Command | Description |
|---------|-------------|
| `olivevision.py <image>` | Analyze a single image |
| `olivevision.py --gui` | Launch GUI mode |
| `olivevision.py --monitor --interval 60` | Continuous monitoring |
| `olivevision.py status` | Show recent analyses |
| `olivevision.py status --tree <ID>` | Filter by tree ID |
| `olivevision.py trend` | Show trend analysis |
| `olivevision.py trees` | List all tree IDs |
| `olivevision.py video <file>` | Analyze video file |
| `olivevision.py export --format csv` | Export data |

## Project Structure

```
olive-vision-ai/
├── olivevision.py          # Main CLI/GUI entry point
├── src/
│   ├── runtime.py          # Analysis engine, Store, VideoAnalyzer
│   ├── cli_ui.py           # ANSI color helpers, panels, spinners
│   └── ...                 # detection, preprocessing, color_analysis, etc.
├── config/
│   └── runtime.yaml        # All configurable parameters
├── tests/
│   └── test_runtime.py     # 24 tests
├── ml/                     # ML models (optional)
├── tools/                  # Evaluation & spec doc generators
├── docs/                   # Documentation
├── data/                   # Database storage
└── outputs/                # Analysis results
```

## Configuration

All parameters are configurable via `config/runtime.yaml`:

```yaml
detection:
  fruit_min_area: 250
  leaf_min_area: 100

analysis:
  curl_threshold: 0.35

stress:
  wrinkle_erosion: 3
```

## Requirements

- Python 3.10+
- OpenCV (headless)
- NumPy
- PyYAML

## Documentation

- [Quick Start](docs/QUICKSTART.md)
- [Operations Guide](docs/OPERATIONS.md) (Raspberry Pi setup)
- [API Reference](docs/API_REFERENCE.md)
- [Usage Examples](docs/USAGE_EXAMPLES.md)
- [Improvement Log](docs/IMPROVEMENTS.md)

## License

MIT License

## Acknowledgements

- [OpenCV](https://opencv.org/) for computer vision capabilities
- The open-source agricultural AI community

---

**Vision**: "Transforming long-term olive cultivation into a data-driven, AI-assisted, and scientifically measurable process."
