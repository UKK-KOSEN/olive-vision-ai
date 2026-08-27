import cv2
from pathlib import Path
from src.runtime import Analyzer, load_runtime_config

config = load_runtime_config(Path('config/runtime.yaml'))
for name in [
    'drone.png',
    'outputs/observations/observation_20260826_180914_329093.jpg',
    'outputs/observations/observation_20260826_175813_978478.jpg',
    'outputs/observations/observation_20260826_181427_194681.jpg',
]:
    img = cv2.imread(name)
    if img is None:
        continue
    h, w = img.shape[:2]
    an = Analyzer(config, resolution_mode='auto', drone_mode=False)
    rn, _ = an.analyze(img, source='test')
    ad = Analyzer(config, resolution_mode='auto', drone_mode=True)
    rd, _ = ad.analyze(img, source='test')
    n = Path(name).name
    print(f'{n} ({w}x{h})')
    print(f'  Normal: leaves={rn["leaf_count"]:3d} fruits={rn["fruit_count"]:3d} green={rn["green_coverage"]:5.1f}%')
    print(f'  Drone:  leaves={rd["leaf_count"]:3d} fruits={rd["fruit_count"]:3d} green={rd["green_coverage"]:5.1f}%')
    print()
