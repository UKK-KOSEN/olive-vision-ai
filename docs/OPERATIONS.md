# Raspberry Pi Operations Guide

`olivevision.py` is the production entry point. It performs local image/video analysis,
saves annotated results, and stores data in SQLite. No training, no network, no cloud required.

## Recommended Hardware

- **Raspberry Pi 4** (4 GB RAM) or **Pi 5** (4 GB+)
- **Raspberry Pi OS Bookworm** 64-bit (Python 3.11)
- **USB camera** or **Raspberry Pi Camera Module**
- **5V / 3A power supply**
- **High-endurance microSD** or SSD

Pi Zero is not supported. Ensure sufficient free space for `outputs/observations/`.

## Installation

```bash
# Install system packages
sudo apt update
sudo apt install -y python3-venv python3-opencv python3-tk python3-picamera2

# Clone and setup
git clone https://github.com/UKK-KOSEN/olive-vision-ai.git
cd olive-vision-ai
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements.txt

# Verify installation
python3 olivevision.py --help
```

For GUI, install `python3-tk`. For ML features, optionally install `pip install -r ml/requirements-ml.txt`.

## Basic Commands

### Image Analysis

```bash
# Analyze single image
python3 olivevision.py image.jpg

# Analyze with tree ID
python3 olivevision.py image.jpg --tree-id "1-3"

# Save annotated image
python3 olivevision.py image.jpg --save-image
```

### Video Analysis

```bash
# Analyze video file
python3 olivevision.py video sample.mp4

# Analyze with tree ID
python3 olivevision.py video sample.mp4 --tree-id "1-3"

# Custom frame interval
python3 olivevision.py video sample.mp4 --interval 60
```

### CLI Commands

```bash
# Show recent analyses
python3 olivevision.py status

# Filter by tree ID
python3 olivevision.py status --tree "1-3"

# Show trend analysis
python3 olivevision.py trend

# List all tree IDs
python3 olivevision.py trees

# Export data
python3 olivevision.py export --format csv
```

### GUI Mode

```bash
# Launch GUI
python3 olivevision.py --gui

# GUI with camera
python3 olivevision.py --gui --camera 0
```

### Monitoring Mode

```bash
# Continuous monitoring (every 60 seconds)
python3 olivevision.py --monitor --interval 60

# Monitor specific tree
python3 olivevision.py --monitor --tree-id "1-3" --interval 120
```

## Configuration

Edit `config/runtime.yaml` to customize parameters:

```yaml
detection:
  fruit_min_area: 250
  leaf_min_area: 100
  circle_dp: 1.2

analysis:
  curl_weights:
    tip_fraction: 0.4
    mid_fraction: 0.3
    base_fraction: 0.3
  curl_threshold: 0.35

stress:
  wrinkle_erosion: 3
  wrinkle_ridge_size: 5
```

## QR Code Tree IDs

The system can detect QR codes in images to identify tree IDs:

- QR codes should contain text like "第1試験樹" (Tree #1)
- Tree IDs are stored in the database
- Filter analyses by tree ID using `--tree` flag

## Systemd Service

Create `/etc/systemd/system/olivevision.service`:

```ini
[Unit]
Description=OliveVision local camera monitor
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/olive-vision-ai
ExecStart=/home/pi/olive-vision-ai/.venv/bin/python olivevision.py --monitor --camera 0 --interval 3600
Restart=always
RestartSec=15
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now olivevision
journalctl -u olivevision -f
```

## Storage

- **Database**: `data/database/olivevision.db`
- **Observations**: `outputs/observations/`
- **Annotated images**: `outputs/preview/`

Back up regularly. Output pruning is intentionally manual.

## Troubleshooting

### No detections?
- Check lighting conditions
- Adjust `detection.fruit_min_area` in config
- Ensure QR code is clearly visible (if using tree IDs)

### Camera not working?
- Verify `/dev/video0` is accessible
- Check user is in `video` group
- Test with `python3 olivevision.py --capture --camera 0`

### Slow performance?
- Increase `detection.leaf_min_area`
- Use `--interval 60` for monitoring
- Reduce image resolution

## Verification

Run offline tests before deployment:

```bash
python3 -m pytest tests/test_runtime.py -v
```

All 24 tests should pass.

---

**Version**: 0.3.0
**Last Updated**: 2026-08-21
