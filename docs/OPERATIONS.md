# Raspberry Pi 運用ガイド / Raspberry Pi operations guide

`olivevision.py` is the production entry point. It performs local image analysis,
saves an annotated JPEG and JSON result, and appends a row to SQLite. It does not
need a training dataset, a model file, network access, or cloud credentials.

## Recommended hardware

The supported baseline is Raspberry Pi 4 (4 GB RAM), Raspberry Pi OS Bookworm
64-bit (Python 3.11), a reliable 5 V / 3 A power supply, and a USB camera or Raspberry Pi
Camera Module. Raspberry Pi 5 (4 GB+) is recommended for higher-resolution
images or shorter capture intervals. A Pi Zero is not a supported production
target. Use a high-endurance microSD card or an SSD; keep sufficient free space
for `outputs/observations/`.

## Install

On Raspberry Pi OS, install the camera/OpenCV/Tk packages supplied by the OS
first. They avoid compiling OpenCV on the device.

```bash
sudo apt update
sudo apt install -y python3-venv python3-opencv python3-tk python3-picamera2
cd /path/to/olive-p
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 olivevision.py --help
```

`python3-tk` is only required for the GUI. If pip's OpenCV wheel conflicts with
the OS package, keep `python3-opencv` and install only `numpy` and `PyYAML` in
the venv. The original research/training stack is intentionally optional:
`pip install -r requirements-ml.txt`.

Before deployment, run the offline smoke test (it creates its own artificial
image and does not require a camera or environmental data):

```bash
python3 -m unittest tests/test_runtime.py
```

## Daily operation

Every command shows progress and reports output locations. All paths can be
overridden with `--database`, `--output`, and `--config`.

```bash
# Test with a captured image; creates an annotation, JSON record and SQLite row.
python3 olivevision.py analyze /home/pi/sample.jpg

# Test the first camera once.
python3 olivevision.py capture --camera 0

# Show the most recent measurements or export them for spreadsheet use.
python3 olivevision.py status --limit 20
python3 olivevision.py export outputs/olivevision-export.csv

# Desktop GUI: select an image, capture a frame, inspect the annotated preview,
# and inspect recent activity.
python3 olivevision.py gui --camera 0

# Headless continuous monitoring, one capture each hour.
python3 olivevision.py monitor --camera 0 --interval 3600
```

The green boxes are leaf regions and orange boxes are possible fruit regions.
The runtime combines HSV and Lab colour spaces, an excess-green vegetation
index, and contour shape tests (leaf elongation; fruit oval/roundness and
solidity). This substantially suppresses soil, branches, highlights, and other
colour-only false positives while retaining the low Raspberry Pi resource use.
Counts are still classical CV measurements, not a trained object detector.

For reliable site-specific figures, take 10–20 representative daytime images
and tune `config/runtime.yaml`: raise `*_min_area` to suppress tiny false
positives; narrow `fruit_hue` if soil is detected; lower `leaf_saturation_min`
slightly if shade loses olive leaves. Re-run `analyze` after every change and
visually inspect the annotation before relying on a threshold for operations.
Always tune and analyse the original camera image, not a previously annotated
output from `outputs/observations/`: its green/orange overlay boxes can be
mistaken for image content by any colour-based analyser.

## Reliable unattended operation

First run `capture` interactively and verify the annotation and `status` output.
For a USB camera, make sure the service user can read `/dev/video0` (normally by
being in the `video` group). For a CSI camera, the runtime automatically falls
back to Picamera2 when OpenCV cannot open a V4L device; ensure
`python3-picamera2` is installed and test `capture` before enabling a service.

Create `/etc/systemd/system/olivevision.service` (replace paths and user):

```ini
[Unit]
Description=OliveVision local camera monitor
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/olive-p
ExecStart=/home/pi/olive-p/.venv/bin/python olivevision.py monitor --camera 0 --interval 3600
Restart=always
RestartSec=15
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Then enable it and watch live progress:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now olivevision
journalctl -u olivevision -f
```

Stop it safely with `sudo systemctl stop olivevision`. The monitor catches a
temporary camera failure, logs it, and retries on the next interval; systemd
restarts the process if it terminates unexpectedly.

## Verification performed in this repository

The included offline test creates a synthetic image containing one green leaf
region and one fruit-coloured region. The test verifies annotation output,
SQLite persistence, and CSV export. The CLI was also checked end-to-end with
that image (`analyze`, `status`, and `export`) and the camera-unavailable path
was checked for a clear error message. A real camera must still be checked on
the target Raspberry Pi with `capture --camera 0`, because this development
machine has no attached Pi camera.

## Storage and backup

SQLite history is `data/database/olivevision.db`; annotations and per-run JSON
are `outputs/observations/`. Back these up regularly. Output pruning is a local
operations decision and is intentionally not automatic, so evidence is never
silently deleted.
