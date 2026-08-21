# OliveVision AI - API Reference

本ドキュメントは各モジュールの詳細なAPI仕様書です。

---

## 目次

1. [utils](#utils)
2. [preprocessing](#preprocessing)
3. [detection](#detection)
4. [color_analysis](#color_analysis)
5. [feature_extraction](#feature_extraction)
6. [video_processor](#video_processor)
7. [background_removal](#background_removal)
8. [advanced_detection](#advanced_detection)
9. [texture_analysis](#texture_analysis)
10. [optical_flow_analysis](#optical_flow_analysis)

---

## utils

### load_config(config_path: str) → Dict

設定ファイルを読み込む。

**パラメータ:**
- `config_path` (str): YAML設定ファイルのパス（デフォルト: `config/config.yaml`）

**戻り値:** 設定辞書

**例:**
```python
from src import utils
config = utils.load_config('config/config.yaml')
print(config['leaf_detection']['hue_range'])  # [35, 95]
```

---

### setup_logger(log_path: str) → logging.Logger

ロガーを設定してインスタンスを作成。

**パラメータ:**
- `log_path` (str): ログファイルのパス（デフォルト: `outputs/olive_analysis.log`）

**戻り値:** ロガーオブジェクト

**例:**
```python
logger = utils.setup_logger('outputs/custom.log')
logger.info('処理開始')
```

---

### load_image(image_path: str) → np.ndarray

画像ファイルを読み込む。

**パラメータ:**
- `image_path` (str): 画像ファイルのパス

**戻り値:** BGR形式のnumpy配列 (shape: [H, W, 3])

**例外:**
- `ValueError`: ファイルが読み込めない場合

---

### save_image(image: np.ndarray, output_path: str) → None

画像をファイルに保存。

**パラメータ:**
- `image` (np.ndarray): 画像配列
- `output_path` (str): 出力パス

---

### calculate_circularity(area: float, perimeter: float) → float

円形度を計算。

**式:** `4πA / P²`

**戻り値:** 円形度（0-1、1に近いほど円形）

---

### get_contour_properties(contour: np.ndarray) → Dict

輪郭から複数のプロパティを計算。

**戻り値:**
```python
{
    'area': float,              # 面積
    'perimeter': float,         # 周囲長
    'x': int, 'y': int,        # 左上座標
    'width': int, 'height': int, # 幅・高さ
    'center_x': float,          # 中心X
    'center_y': float,          # 中心Y
    'radius': float,            # 最小外接円の半径
    'circularity': float,       # 円形度
    'solidity': float,          # Solidity
    'aspect_ratio': float,      # 幅/高さ
    'extent': float,            # 面積/外接矩形面積
}
```

---

### create_mask_from_hsv_range(...) → np.ndarray

HSV範囲からマスクを作成。

**パラメータ:**
- `hsv_image` (np.ndarray): HSV画像
- `hue_range` (tuple): [min, max]
- `sat_range` (tuple): [min, max]
- `val_range` (tuple): [min, max]

**戻り値:** 二値マスク（255: 範囲内、0: 範囲外）

---

## preprocessing

### ImagePreprocessor

画像の前処理を行うクラス。

#### __init__(config: Dict)

**パラメータ:**
- `config` (dict): 設定辞書

```python
preprocessor = ImagePreprocessor(config)
```

#### preprocess(image: np.ndarray) → np.ndarray

画像を前処理（ノイズ除去→白バランス→ガンマ補正）。

**パラメータ:**
- `image` (np.ndarray): BGR画像

**戻り値:** 前処理済み画像

---

### ColorSpaceConverter

#### get_color_spaces(image: np.ndarray) → Dict

複数の色空間に変換。

**戻り値:**
```python
{
    'bgr': np.ndarray,   # 元の画像
    'hsv': np.ndarray,   # HSV色空間
    'lab': np.ndarray,   # Lab色空間
    'gray': np.ndarray,  # グレースケール
}
```

---

## detection

### ObjectDetector

葉・実を検出するクラス。

#### __init__(config: Dict)

#### detect_leaves(image: np.ndarray) → Tuple[List[Dict], np.ndarray]

葉を検出。

**戻り値:** (葉情報のリスト, 可視化画像)

**葉情報:**
```python
{
    'area': float,
    'perimeter': float,
    'x': int, 'y': int,
    'width': int, 'height': int,
    'circularity': float,
    'solidity': float,
    ...
}
```

#### detect_fruits(image: np.ndarray) → Tuple[List[Dict], np.ndarray]

実を検出。

---

## color_analysis

### ColorAnalyzer

色を分析するクラス。

#### analyze_leaf_color(image: np.ndarray, mask: np.ndarray) → Dict

葉の色を分析。

**戻り値:**
```python
{
    'mean_hue': float,              # 平均Hue値
    'mean_saturation': float,       # 平均Saturation
    'mean_value': float,            # 平均Value
    'color_stage': str,             # 'healthy_green', 'yellow', 'brown', etc.
    'senescence_degree': float,     # 枯葉度（0-100%）
}
```

#### calculate_color_difference(image1: np.ndarray, image2: np.ndarray, ...) → float

Lab色空間での色差（ΔE）を計算。

---

## feature_extraction

### FeatureExtractor

特徴量を抽出するクラス。

#### extract_features(image_path: str, detection_results: Dict, ...) → Dict

画像から全特徴量を抽出（100+種類）。

**戻り値:** 特徴量の辞書

---

### TimeSeriesFeatureExtractor

#### create_lag_features(df: pd.DataFrame, lags: List[int]) → pd.DataFrame

遅延特徴量を作成（デフォルト: [1, 2, 6, 12, 24]）。

#### create_moving_average_features(df: pd.DataFrame, windows: List[int]) → pd.DataFrame

移動平均特徴量を作成（デフォルト: [3, 6, 12, 24]）。

#### create_diff_features(df: pd.DataFrame, diffs: List[int]) → pd.DataFrame

差分特徴量を作成（デフォルト: [1, 24]）。

---

## video_processor

### VideoProcessor

動画ファイルを処理するクラス。

#### __init__(video_path: str, logger: logging.Logger)

#### get_frame_iterator(frame_interval: int) → Generator[Tuple[int, np.ndarray], None, None]

フレームを取得するイテレータ。

**パラメータ:**
- `frame_interval` (int): フレーム間隔（1=全フレーム、30=1秒ごと）

**Yields:** (フレーム番号, BGR画像)

```python
video = VideoProcessor('video.mp4', logger)
for frame_idx, frame in video.get_frame_iterator(30):
    print(f"Frame {frame_idx}")
```

#### get_frame_at_time(time_seconds: float) → Optional[np.ndarray]

指定された時刻のフレームを取得。

#### extract_frames_to_disk(output_dir: str, frame_interval: int) → int

フレームをディスクに保存。

**戻り値:** 保存されたフレーム数

#### get_statistics() → Dict

動画全体の統計情報。

**戻り値:**
```python
{
    'fps': float,
    'frame_count': int,
    'width': int,
    'height': int,
    'duration_seconds': float,
    'file_path': str,
}
```

---

### FrameSequenceAnalyzer

時系列フレームを解析するクラス。

#### add_frame_result(frame_idx: int, timestamp: float, result: Dict) → None

フレーム解析結果を追加。

#### get_trend(key: str) → List[Tuple[int, float]]

時系列のトレンドを取得。

#### calculate_change_rate(key: str) → float

値の変化率を計算（%）。

#### detect_anomalies(key: str, threshold: float = 2.0) → List[int]

異常フレームを検出（標準偏差ベース）。

---

## background_removal

### BackgroundRemover

背景を除去するクラス（複数の手法）。

#### remove_by_hsv(...) → np.ndarray

HSV値で背景（暗色）を除去。

#### remove_by_grabcut(image: np.ndarray, rect: Tuple = None, ...) → Tuple[np.ndarray, np.ndarray]

GrabCutアルゴリズムで背景を除去。

**戻り値:** (マスク, 前景画像)

#### remove_by_canny(image: np.ndarray, ...) → np.ndarray

Cannyエッジ検出で背景を除去。

#### remove_by_kmeans(image: np.ndarray, k: int = 3) → np.ndarray

K-meansクラスタリングで背景を除去。

#### adaptive_background_removal(image: np.ndarray, config: Dict) → np.ndarray

環境に応じて最適な背景除去方法を自動選択。

**アルゴリズム選択:**
- コントラスト > 50 → Cannyを使用
- 彩度 < 80 → HSVを使用
- その他 → K-meansを使用

#### apply_morphological_cleanup(mask: np.ndarray, ...) → np.ndarray

モルフォロジー処理でマスクをクリーンアップ。

---

## advanced_detection

### AdvancedDetector

より精密な検出を行うクラス。

#### detect_leaves_multiscale(image: np.ndarray, scales: List[float] = None) → List[Dict]

マルチスケール葉検出。

**パラメータ:**
- `scales` (list): スケールファクター（デフォルト: [1.0, 0.8, 1.2]）

**処理フロー:**
1. 複数スケールで並列検出
2. 検出結果をスケールバック
3. 重複検出を統合

#### post_process_detections(detections: List[Dict], image: np.ndarray) → List[Dict]

検出結果の後処理（画像範囲外を除外）。

#### calculate_detection_confidence(detection: Dict) → float

検出の信頼度を計算（0-1）。

**計算式:**
```
confidence = 0.4 * circularity_score 
           + 0.4 * solidity_score 
           + 0.2 * aspect_ratio_score
```

---

### ColorRangeOptimizer

#### optimize_hsv_range(image: np.ndarray, foreground_mask: np.ndarray = None, ...) → Dict

画像から最適なHSV範囲を推定。

**パラメータ:**
- `percentile` (float): パーセンタイル値（デフォルト: 95）

**戻り値:**
```python
{
    'hue_range': tuple,        # (min, max)
    'saturation_range': tuple,
    'value_range': tuple,
}
```

---

## texture_analysis

### TextureAnalyzer

画像テクスチャを解析するクラス。

#### analyze_object_texture(image: np.ndarray, mask: np.ndarray) → Dict

マスク領域のテクスチャを解析。

**戻り値:**
```python
{
    'texture_mean': float,
    'texture_std': float,
    'texture_contrast': float,
    'texture_energy': float,
    'glcm_contrast': float,
    'glcm_dissimilarity': float,
    'glcm_homogeneity': float,
    'glcm_energy': float,
    'glcm_correlation': float,
    'glcm_asm': float,
    'lbp_energy': float,
    'lbp_entropy': float,
    'lbp_uniformity': float,
}
```

#### calculate_leaf_smoothness(image: np.ndarray, mask: np.ndarray) → float

葉の表面の滑らかさを計算（0-1、1が最も滑らか）。

#### calculate_fruit_shine(image: np.ndarray, mask: np.ndarray) → float

実の光沢度を計算（0-1）。

#### detect_surface_defects(image: np.ndarray, mask: np.ndarray, ...) → np.ndarray

表面の欠陥を検出。

---

## optical_flow_analysis

### OpticalFlowAnalyzer

オプティカルフローで成長速度や動きを追跡。

#### calculate_lucas_kanade_flow(image: np.ndarray, mask: np.ndarray = None) → Tuple[np.ndarray, np.ndarray]

Lucas-Kanadeオプティカルフローを計算。

**戻り値:** (flow_x, flow_y)

#### calculate_growth_metrics(flow_x: np.ndarray, flow_y: np.ndarray) → Dict

フローから成長メトリクスを計算。

**戻り値:**
```python
{
    'avg_flow_magnitude': float,      # 平均フロー大きさ
    'max_flow_magnitude': float,
    'std_flow_magnitude': float,
    'avg_flow_x': float,
    'avg_flow_y': float,
}
```

#### calculate_expansion_rate(flow_x: np.ndarray, flow_y: np.ndarray) → float

領域の拡大率を計算（発散）。

**式:** `divergence = ∂u/∂x + ∂v/∂y`

---

### ObjectTracker

マルチターゲット追跡を行うクラス。

#### update(detections: List[Dict]) → Dict[int, Dict]

検出結果から追跡を更新。

**戻り値:** ID → 更新された検出結果

```python
tracker = ObjectTracker(logger)
for frame_idx, frame in video.get_frame_iterator():
    detections = detector.detect_leaves(frame)
    tracked = tracker.update(detections)
    for track_id, detection in tracked.items():
        print(f"Leaf {track_id}: {detection['track_history']}")
```

#### get_track_velocity(track_id: int, window_size: int = 5) → Tuple[float, float]

追跡オブジェクトの速度を計算（ピクセル/フレーム）。

#### get_track_acceleration(track_id: int, window_size: int = 5) → Tuple[float, float]

追跡オブジェクトの加速度を計算。

---

## 共通パターン

### エラーハンドリング

すべてのモジュールは詳細なロギングを行います：

```python
import logging
logger = logging.getLogger(__name__)

try:
    result = processor.process(image)
    logger.info(f"処理成功: {len(result)}個のオブジェクト")
except Exception as e:
    logger.error(f"処理失敗: {str(e)}", exc_info=True)
```

### メモリ効率

大規模動画処理の場合、フレーム間隔を調整：

```python
# 推奨: 30 (30fps動画で1秒ごと)
video = VideoProcessor('large_video.mp4', logger)
for frame_idx, frame in video.get_frame_iterator(frame_interval=30):
    # 処理
    pass
```

---

## バージョン

- **版**: 0.2.0
- **最終更新**: 2026-07-19
