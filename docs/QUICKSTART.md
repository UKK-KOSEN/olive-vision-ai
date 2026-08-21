# OliveVision AI - Quick Start Guide

## Installation

```bash
# Clone the repository
git clone https://github.com/UKK-KOSEN/olive-vision-ai.git
cd olive-vision-ai

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

## Basic Usage

### Image Analysis

```bash
# Analyze a single image
python olivevision.py image.jpg

# Analyze with specific tree ID
python olivevision.py image.jpg --tree-id "1-3"

# Save annotated image
python olivevision.py image.jpg --save-image
```

### GUI Mode

```bash
# Launch GUI
python olivevision.py --gui

# GUI with specific image
python olivevision.py --gui --input image.jpg
```

### Monitoring Mode

```bash
# Monitor every 60 seconds
python olivevision.py --monitor --interval 60

# Monitor specific tree
python olivevision.py --monitor --tree-id "1-3" --interval 120
```

### CLI Commands

```bash
# Show recent analysis history
python olivevision.py status

# Filter by tree ID
python olivevision.py status --tree "1-3"

# Show trend analysis
python olivevision.py trend

# List all tree IDs
python olivevision.py trees

# Analyze video
python olivevision.py video sample.mp4

# Export data
python olivevision.py export --format csv
```

## Configuration

Edit `config/runtime.yaml` to customize parameters:

```yaml
detection:
  fruit_min_area: 250
  leaf_min_area: 100

analysis:
  curl_weights:
    tip_fraction: 0.4
    mid_fraction: 0.3
    base_fraction: 0.3
```

## Output Files

- `outputs/observations/` - Analysis results (JSON)
- `data/database/olivevision.db` - SQLite database
- `outputs/preview/` - Annotated images

## Troubleshooting

**No detections?**
- Check lighting conditions
- Adjust `detection.fruit_min_area` in config

**QR code not detected?**
- Ensure QR code is clearly visible
- Try different angles/lighting

**Slow performance?**
- Reduce image resolution
- Increase `detection.leaf_min_area`

## Next Steps

1. Read [OPERATIONS.md](OPERATIONS.md) for Raspberry Pi setup
2. Check [API_REFERENCE.md](API_REFERENCE.md) for programmatic use
3. See [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) for examples
