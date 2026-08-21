# OliveVision AI

**Raspberry Pi-friendly local olive monitoring system using classical computer vision**

[![Tests](https://img.shields.io/badge/tests-24%20passing-brightgreen)](tests/test_runtime.py)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![GitHub](https://img.shields.io/github/stars/UKK-KOSEN/olive-vision-ai)](https://github.com/UKK-KOSEN/olive-vision-ai)

## Overview

OliveVision AI analyzes olive tree images and videos to detect leaves, fruits, and canopy, extract biological features, and track long-term trends. Everything runs locally on a Raspberry Pi with **no GPU, cloud, or training required**.

```
Camera → Image → OpenCV Analysis → SQLite Database → Trend Reports
```

## Features

### Image Analysis
- **Leaf detection**: HSV/LAB thresholds + watershed segmentation + shape gates
- **Fruit detection**: Hough circles + contour analysis + color classification
- **QR code detection**: Automatic tree ID from QR codes
- **Canopy analysis**: Coverage, density, greenness metrics
- **Stress indicators**: Wrinkle, leaf curl, yellowing detection

### Video Analysis
- Frame-by-frame analysis with configurable intervals
- Trend tracking across video duration
- Summary statistics with per-tree aggregation

### Data Management
- SQLite storage with automatic schema migration
- Time-series trend analysis (linear regression)
- CSV/JSON export for external analysis
- Tree ID tracking via QR codes

## Quick Start

```bash
# Clone and setup
git clone https://github.com/UKK-KOSEN/olive-vision-ai.git
cd olive-vision-ai
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac
pip install -r requirements.txt

# Analyze an image
python olivevision.py image.jpg

# Launch GUI
python olivevision.py --gui

# Monitor mode (capture every 60s)
python olivevision.py --monitor --interval 60
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `olivevision.py <image>` | Analyze a single image |
| `olivevision.py --gui` | Launch GUI mode |
| `olivevision.py --monitor --interval N` | Continuous monitoring (N seconds) |
| `olivevision.py status` | Show recent analyses |
| `olivevision.py status --tree <ID>` | Filter by tree ID |
| `olivevision.py trend` | Show trend analysis |
| `olivevision.py trees` | List all tree IDs |
| `olivevision.py video <file>` | Analyze video file |
| `olivevision.py export --format csv` | Export data to CSV |

## Configuration

All parameters are configurable via `config/runtime.yaml`:

```yaml
detection:
  fruit_min_area: 250      # Minimum fruit area (pixels)
  leaf_min_area: 100       # Minimum leaf area (pixels)
  circle_dp: 1.2           # Hough circle dp

analysis:
  curl_threshold: 0.35     # Leaf curl detection threshold

stress:
  wrinkle_erosion: 3       # Wrinkle detection erosion iterations
```

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

## Requirements

- Python 3.10+
- OpenCV (headless)
- NumPy
- PyYAML

Optional (for ML features):
- scikit-learn
- LightGBM
- pandas

## Documentation

| Document | Description |
|----------|-------------|
| [Quick Start](docs/QUICKSTART.md) | Getting started guide |
| [Operations Guide](docs/OPERATIONS.md) | Raspberry Pi setup & systemd service |
| [API Reference](docs/API_REFERENCE.md) | Programmatic interface documentation |
| [Usage Examples](docs/USAGE_EXAMPLES.md) | Practical code examples |
| [Improvement Log](docs/IMPROVEMENTS.md) | Version history & changes |

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Run tests: `python -m unittest tests.test_runtime -v`
4. Submit a pull request

## License

MIT License

## Acknowledgements

- [OpenCV](https://opencv.org/) for computer vision capabilities
- The open-source agricultural AI community

---

**Vision**: "Transforming long-term olive cultivation into a data-driven, AI-assisted, and scientifically measurable process."
