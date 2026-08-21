# OliveVision AI - Usage Examples

本ドキュメントは実際のユースケースと詳細なサンプルコードを提供します。

---

## 目次

1. [基本的な使用方法](#基本的な使用方法)
2. [単一画像の解析](#単一画像の解析)
3. [動画ファイルの解析](#動画ファイルの解析)
4. [バッチ処理](#バッチ処理)
5. [カスタム検出パラメータ](#カスタム検出パラメータ)
6. [結果の後処理](#結果の後処理)
7. [時系列データの処理](#時系列データの処理)

---

## 基本的な使用方法

### コマンドライン

```bash
# 単一画像を解析
python analyze.py path/to/image.jpg

# 単一画像を解析（可視化パスを指定）
python analyze.py data/raw_images/sample.jpg

# 動画を解析（1秒ごと = フレーム間隔30）
python analyze.py path/to/video.mp4 --frame-interval 30

# 動画を解析（全フレーム）
python analyze.py path/to/video.mp4 --frame-interval 1
```

### 出力

```
outputs/
├── analysis_20260719_120530.json    # 解析結果
├── visualization_20260719_120530.jpg # 検出可視化
└── olive_analysis.log               # ログファイル
```

---

## 単一画像の解析

### 例1: シンプルな葉検出

```python
from src.utils import load_config, setup_logger, load_image
from src.preprocessing import ImagePreprocessor
from src.detection import ObjectDetector

# 初期化
config = load_config('config/config.yaml')
logger = setup_logger()

# 画像読み込み
image = load_image('data/raw_images/sample.jpg')

# 前処理
preprocessor = ImagePreprocessor(config)
preprocessed = preprocessor.preprocess(image)

# 葉検出
detector = ObjectDetector(config)
leaves, vis_image = detector.detect_leaves(preprocessed)

# 結果確認
print(f"検出された葉: {len(leaves)}個")
for i, leaf in enumerate(leaves):
    print(f"  葉{i}: 面積={leaf['area']:.1f}, 円形度={leaf['circularity']:.2f}")
```

### 例2: 高度な検出（信頼度フィルタ付き）

```python
from src.advanced_detection import AdvancedDetector

# マルチスケール検出
advanced_detector = AdvancedDetector(config)
leaves = advanced_detector.detect_leaves_multiscale(
    image,
    scales=[0.8, 1.0, 1.2]
)

# 信頼度でフィルタリング
high_confidence_leaves = [
    leaf for leaf in leaves 
    if advanced_detector.calculate_detection_confidence(leaf) > 0.5
]

print(f"高信頼度葉: {len(high_confidence_leaves)}個")
```

### 例3: 色解析

```python
from src.color_analysis import ColorAnalyzer
from src.preprocessing import ColorSpaceConverter

# 色空間変換
converter = ColorSpaceConverter()
color_spaces = converter.get_color_spaces(image)

# 色解析
analyzer = ColorAnalyzer()
leaf_colors = []

for leaf in leaves:
    # マスク作成
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    cv2.drawContours(mask, [leaf['contour']], 0, 255, -1)
    
    # 色解析
    color_info = analyzer.analyze_leaf_color(image, mask)
    leaf_colors.append(color_info)
    
    print(f"葉色: {color_info['color_stage']}")
    print(f"  Hue={color_info['mean_hue']:.1f}")
    print(f"   枯葉度: {color_info['senescence_degree']:.1f}%")
```

### 例4: テクスチャ解析

```python
from src.texture_analysis import TextureAnalyzer

analyzer = TextureAnalyzer(logger)

for leaf in leaves:
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    cv2.drawContours(mask, [leaf['contour']], 0, 255, -1)
    
    texture = analyzer.analyze_object_texture(image, mask)
    smoothness = analyzer.calculate_leaf_smoothness(image, mask)
    
    print(f"テクスチャ解析:")
    print(f"  GLCM対比度: {texture['glcm_contrast']:.2f}")
    print(f"   滑らかさ: {smoothness:.2f}")
```

---

## 動画ファイルの解析

### 例1: 基本的な動画処理

```python
from src.video_processor import VideoProcessor, FrameSequenceAnalyzer
from src.detection import ObjectDetector
from src.preprocessing import ImagePreprocessor

config = load_config('config/config.yaml')
logger = setup_logger()

# 動画読み込み
video = VideoProcessor('data/raw_videos/sample.mp4', logger)
print(f"動画情報: {video.width}x{video.height}, {video.fps}fps, {video.frame_count}フレーム")

# フレーム処理
preprocessor = ImagePreprocessor(config)
detector = ObjectDetector(config)
analyzer = FrameSequenceAnalyzer()

for frame_idx, frame in video.get_frame_iterator(frame_interval=30):
    preprocessed = preprocessor.preprocess(frame)
    leaves, _ = detector.detect_leaves(preprocessed)
    
    # 結果を時系列に追加
    result = {'leaf_count': len(leaves)}
    analyzer.add_frame_result(frame_idx, frame_idx / video.fps, result)
    
    print(f"フレーム {frame_idx}: 葉数 = {len(leaves)}")

# トレンド分析
leaf_trend = analyzer.get_trend('leaf_count')
print(f"葉数トレンド: {leaf_trend}")
```

### 例2: 異常検出

```python
# 異常フレームの検出
anomaly_frames = analyzer.detect_anomalies('leaf_count', threshold=2.0)
print(f"異常が検出されたフレーム: {anomaly_frames}")

for frame_idx in anomaly_frames:
    print(f"  フレーム {frame_idx}: 異常な葉数")
```

### 例3: 成長速度の計算

```python
from src.optical_flow_analysis import OpticalFlowAnalyzer

flow_analyzer = OpticalFlowAnalyzer(logger)

for frame_idx, frame in video.get_frame_iterator(frame_interval=1):
    preprocessed = preprocessor.preprocess(frame)
    
    # オプティカルフロー計算
    flow_x, flow_y = flow_analyzer.calculate_lucas_kanade_flow(preprocessed)
    metrics = flow_analyzer.calculate_growth_metrics(flow_x, flow_y)
    
    expansion_rate = flow_analyzer.calculate_expansion_rate(flow_x, flow_y)
    
    print(f"フレーム {frame_idx}:")
    print(f"  平均フロー大きさ: {metrics['avg_flow_magnitude']:.2f} px/frame")
    print(f"  領域拡大率: {expansion_rate:.3f}")
```

---

## バッチ処理

### 例1: 複数画像の処理

```python
from pathlib import Path
import json
from datetime import datetime

image_dir = Path('data/raw_images')
results = []

config = load_config('config/config.yaml')
logger = setup_logger()

for image_path in sorted(image_dir.glob('*.jpg')):
    logger.info(f"処理中: {image_path.name}")
    
    image = load_image(str(image_path))
    preprocessor = ImagePreprocessor(config)
    preprocessed = preprocessor.preprocess(image)
    
    detector = ObjectDetector(config)
    leaves, _ = detector.detect_leaves(preprocessed)
    fruits, _ = detector.detect_fruits(preprocessed)
    
    result = {
        'image': image_path.name,
        'leaf_count': len(leaves),
        'fruit_count': len(fruits),
        'timestamp': datetime.now().isoformat(),
    }
    results.append(result)
    print(f"  葉: {len(leaves)}, 実: {len(fruits)}")

# CSV保存
import pandas as pd
df = pd.DataFrame(results)
df.to_csv('outputs/batch_results.csv', index=False)
print(f"結果を保存: outputs/batch_results.csv")
```

### 例2: 複数動画の処理

```python
video_dir = Path('data/raw_videos')
video_results = []

for video_path in sorted(video_dir.glob('*.mp4')):
    logger.info(f"処理中: {video_path.name}")
    
    video = VideoProcessor(str(video_path), logger)
    
    preprocessor = ImagePreprocessor(config)
    detector = ObjectDetector(config)
    analyzer = FrameSequenceAnalyzer()
    
    frame_count = 0
    for frame_idx, frame in video.get_frame_iterator(frame_interval=30):
        preprocessed = preprocessor.preprocess(frame)
        leaves, _ = detector.detect_leaves(preprocessed)
        analyzer.add_frame_result(frame_idx, frame_idx / video.fps, 
                                 {'leaf_count': len(leaves)})
        frame_count += 1
    
    stats = analyzer.get_statistics()
    leaf_trend = analyzer.get_trend('leaf_count')
    
    video_result = {
        'video': video_path.name,
        'frames_analyzed': frame_count,
        'leaf_count_avg': np.mean([v[1] for v in leaf_trend]),
        'leaf_count_std': np.std([v[1] for v in leaf_trend]),
    }
    video_results.append(video_result)

df_video = pd.DataFrame(video_results)
df_video.to_csv('outputs/video_batch_results.csv', index=False)
```

---

## カスタム検出パラメータ

### 例1: 設定ファイルの編集

`config/config.yaml` を編集：

```yaml
leaf_detection:
  hue_range: [35, 95]         # より狭く: [40, 80]
  saturation: [30, 255]       # より厳しく: [50, 255]
  value: [30, 255]            # より明るく: [80, 255]
  min_area: 50                # より大きく: 100
  max_area: 50000             # より小さく: 20000
  circularity: 0.3            # より円形: 0.5
  solidity: 0.5               # より凸: 0.6
```

### 例2: 動的パラメータ調整

```python
# 設定をコピーしてカスタマイズ
custom_config = config.copy()
custom_config['leaf_detection']['min_area'] = 200
custom_config['leaf_detection']['circularity'] = 0.6

detector = ObjectDetector(custom_config)
leaves, _ = detector.detect_leaves(image)
print(f"カスタムパラメータで検出: {len(leaves)}個")
```

### 例3: HSV範囲の自動最適化

```python
from src.advanced_detection import ColorRangeOptimizer

optimizer = ColorRangeOptimizer()

# 前景マスクを作成（必須）
preprocessor = ImagePreprocessor(config)
preprocessed = preprocessor.preprocess(image)

# 背景除去
from src.background_removal import BackgroundRemover
bg_remover = BackgroundRemover(logger)
fg_mask = bg_remover.adaptive_background_removal(preprocessed, config)

# 最適HSV範囲を自動計算
optimal_ranges = optimizer.optimize_hsv_range(
    preprocessed, 
    fg_mask,
    percentile=95
)

print(f"最適HSV範囲:")
print(f"  Hue: {optimal_ranges['hue_range']}")
print(f"  Saturation: {optimal_ranges['saturation_range']}")
print(f"  Value: {optimal_ranges['value_range']}")
```

---

## 結果の後処理

### 例1: JSON結果の読み込み

```python
import json

with open('outputs/analysis_20260719_120530.json', 'r') as f:
    results = json.load(f)

print(f"葉数: {results['detection']['leaf_count']}")
print(f"実数: {results['detection']['fruit_count']}")
print(f"検出精度: {results['detection']['detection_confidence']:.1%}")

# 個別の葉情報
for i, leaf in enumerate(results['detection']['leaves']):
    print(f"葉{i}: 面積={leaf['area']:.0f}, Hue={leaf['hue']:.1f}")
```

### 例2: Pandasでの統計処理

```python
import pandas as pd

# 複数の結果を集計
results_df = pd.read_csv('outputs/batch_results.csv')

print(f"平均葉数: {results_df['leaf_count'].mean():.1f}")
print(f"標準偏差: {results_df['leaf_count'].std():.1f}")
print(f"最大値: {results_df['leaf_count'].max()}")
print(f"最小値: {results_df['leaf_count'].min()}")

# グループ分析
results_df['date'] = pd.to_datetime(results_df['timestamp']).dt.date
daily_stats = results_df.groupby('date')['leaf_count'].agg(['mean', 'std', 'count'])
print(daily_stats)
```

### 例3: 可視化画像の生成

```python
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# 元画像を読み込み
image = load_image('data/raw_images/sample.jpg')

# 検出結果を読み込み
with open('outputs/analysis_20260719_120530.json', 'r') as f:
    results = json.load(f)

# 検出結果を描画
fig, ax = plt.subplots(figsize=(12, 8))
ax.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

# 葉を描画
for leaf in results['detection']['leaves']:
    rect = Rectangle((leaf['x'], leaf['y']), leaf['width'], leaf['height'],
                     linewidth=2, edgecolor='green', facecolor='none')
    ax.add_patch(rect)

# 実を描画
for fruit in results['detection']['fruits']:
    rect = Rectangle((fruit['x'], fruit['y']), fruit['width'], fruit['height'],
                     linewidth=2, edgecolor='red', facecolor='none')
    ax.add_patch(rect)

ax.set_title(f"葉: {len(results['detection']['leaves'])} | 実: {len(results['detection']['fruits'])}")
plt.tight_layout()
plt.savefig('outputs/visualization_custom.png', dpi=150, bbox_inches='tight')
```

---

## 時系列データの処理

### 例1: 特徴量の時系列生成

```python
from src.feature_extraction import TimeSeriesFeatureExtractor
import pandas as pd

# 特徴量データフレームを作成
data = {
    'timestamp': pd.date_range('2026-01-01', periods=100, freq='D'),
    'leaf_count': np.random.randint(20, 50, 100),
    'leaf_area': np.random.randint(1000, 3000, 100),
    'fruit_count': np.random.randint(5, 20, 100),
}
df = pd.DataFrame(data)

# 時系列特徴量を生成
ts_extractor = TimeSeriesFeatureExtractor()
df_with_lags = ts_extractor.create_lag_features(df, lags=[1, 2, 7])
df_with_lags = ts_extractor.create_moving_average_features(df_with_lags, windows=[3, 7])
df_with_lags = ts_extractor.create_diff_features(df_with_lags, diffs=[1, 7])

print(df_with_lags.head())
print(f"特徴量数: {len(df_with_lags.columns)}")
```

### 例2: 予測モデルの学習

```python
from src.train import LightGBMTrainer

trainer = LightGBMTrainer(logger)

# 学習データを準備
X = df_with_lags.drop('leaf_count', axis=1).dropna()
y = df_with_lags.loc[X.index, 'leaf_count']

# モデルを学習
trainer.train(X, y)

# 特徴量の重要度
importance = trainer.get_feature_importance()
print("トップ10重要特徴量:")
for feature, score in importance[:10]:
    print(f"  {feature}: {score:.4f}")

# モデルを保存
trainer.save_model('models/olive_model.txt')
```

### 例3: 将来予測

```python
from src.predict import OliveForecast

forecast = OliveForecast('models/olive_model.txt', logger)

# 最新特徴量を取得
current_features = df_with_lags.iloc[-1].to_dict()

# 3日先、7日先、30日先を予測
predictions = {
    '3days': forecast.predict_future(current_features, days_ahead=3),
    '7days': forecast.predict_future(current_features, days_ahead=7),
    '30days': forecast.predict_future(current_features, days_ahead=30),
}

for period, pred in predictions.items():
    print(f"{period}: 葉数予測 = {pred:.1f}個")

# レポート生成
report = forecast.generate_report(current_features, days_ahead=7)
print(report)
```

---

## トラブルシューティング

### Q: 葉が過度に検出される

**原因:** HSV範囲が広すぎる、または背景も検出されている

**解決:**
```python
# 1. 背景除去を有効化
bg_remover = BackgroundRemover(logger)
fg_mask = bg_remover.adaptive_background_removal(image, config)

# 2. HSV範囲を最適化
optimizer = ColorRangeOptimizer()
optimal_ranges = optimizer.optimize_hsv_range(image, fg_mask, percentile=90)

# 3. 最小面積を増やす
custom_config = config.copy()
custom_config['leaf_detection']['min_area'] = 200

detector = ObjectDetector(custom_config)
leaves, _ = detector.detect_leaves(image)
```

### Q: 葉が検出されない

**原因:** HSV範囲が狭すぎる、またはノイズが多い

**解決:**
```python
# 1. 画像前処理を改善
preprocessor = ImagePreprocessor(config)
preprocessed = preprocessor.preprocess(image)

# 2. HSV範囲を広げる
custom_config = config.copy()
custom_config['leaf_detection']['hue_range'] = [30, 100]
custom_config['leaf_detection']['saturation'] = [20, 255]

# 3. 最小面積を減らす
custom_config['leaf_detection']['min_area'] = 30
```

---

## パフォーマンス最適化

### 動画処理の高速化

```python
# 重いフレーム間隔を使用（精度は低下）
for frame_idx, frame in video.get_frame_iterator(frame_interval=60):  # 2秒ごと
    # 処理
    pass

# または並列処理を使用
from concurrent.futures import ThreadPoolExecutor

def process_frame(frame):
    preprocessed = preprocessor.preprocess(frame)
    return detector.detect_leaves(preprocessed)

with ThreadPoolExecutor(max_workers=4) as executor:
    for frame_idx, frame in video.get_frame_iterator(30):
        executor.submit(process_frame, frame)
```

---

## バージョン

- **版**: 0.2.0
- **最終更新**: 2026-07-19
