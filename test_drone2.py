import cv2
from pathlib import Path
from src.runtime import Analyzer, load_runtime_config

config = load_runtime_config(Path('config/runtime.yaml'))

for name in [
    'outputs/observations/observation_20260826_180914_329093.jpg',
    'outputs/observations/observation_20260826_175813_978478.jpg',
    'outputs/observations/observation_20260826_181427_194681.jpg',
]:
    img = cv2.imread(name)
    if img is None:
        continue
    h, w = img.shape[:2]

    a_n = Analyzer(config, resolution_mode='auto', drone_mode=False)
    r_n, _ = a_n.analyze(img, source='test')

    a_d = Analyzer(config, resolution_mode='auto', drone_mode=True)
    r_d, _ = a_d.analyze(img, source='test')

    print(f'{Path(name).name} ({w}x{h})')
    print(f'  Normal: leaves={r_n["leaf_count"]:3d}  fruits={r_n["fruit_count"]:3d}  green={r_n["green_coverage"]:5.1f}%')
    print(f'  Drone:  leaves={r_d["leaf_count"]:3d}  fruits={r_d["fruit_count"]:3d}  green={r_d["green_coverage"]:5.1f}%')
    print()
