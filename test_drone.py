"""Diagnostic script to compare normal vs drone mode detection."""
import cv2
import numpy as np
from pathlib import Path
from src.runtime import Analyzer, load_runtime_config

config = load_runtime_config(Path('config/runtime.yaml'))

for img_name in [
    'outputs/observations/observation_20260826_180914_329093.jpg',
    'outputs/observations/observation_20260826_175813_978478.jpg',
    'outputs/observations/observation_20260826_181427_194681.jpg',
]:
    img_path = Path(img_name)
    img = cv2.imread(str(img_path))
    if img is None:
        continue
    h, w = img.shape[:2]
    print(f'\n{"="*60}')
    print(f'{img_path.name} ({w}x{h})')
    print(f'{"="*60}')

    # Normal mode
    analyzer_n = Analyzer(config, resolution_mode='auto', drone_mode=False)
    result_n, _ = analyzer_n.analyze(img, source='test')
    print(f'[Normal]  leaves={result_n["leaf_count"]:3d}  fruits={result_n["fruit_count"]:3d}  '
          f'green={result_n["green_coverage"]:5.1f}%  stage={result_n["leaf_color_stage"]:15s}  '
          f'maturity={result_n["fruit_maturity"]}')

    # Drone mode
    analyzer_d = Analyzer(config, resolution_mode='auto', drone_mode=True)
    result_d, _ = analyzer_d.analyze(img, source='test')
    print(f'[Drone]   leaves={result_d["leaf_count"]:3d}  fruits={result_d["fruit_count"]:3d}  '
          f'green={result_d["green_coverage"]:5.1f}%  stage={result_d["leaf_color_stage"]:15s}  '
          f'maturity={result_d["fruit_maturity"]}')
