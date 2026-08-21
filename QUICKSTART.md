# OliveVision AI - クイックスタートガイド

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. 設定ファイルの確認

`config/config.yaml`で各種パラメータを設定できます。

## 使用方法

### 1. 画像解析

単一の画像を解析：

```bash
python analyze.py path/to/image.jpg
```

結果は`outputs/`ディレクトリにJSON形式で保存されます。

**出力内容：**
- 葉の個数・面積・特性（高度な検出で信頼度も含む）
- 実の個数・面積・熟度
- 色解析結果（Hue値など）
- テクスチャ解析（GLCM, LBP特徴）
- 葉の滑らかさ、実の光沢度
- 画像全体の統計情報

### 1b. 動画解析

動画ファイルを解析（フレーム間隔指定可能）：

```bash
# 1秒ごと（フレームレート30fpsの場合）
python analyze.py path/to/video.mp4 --frame-interval 30

# 全フレーム解析（重い処理）
python analyze.py path/to/video.mp4 --frame-interval 1
```

**出力内容：**
- 各フレームの葉数・実数変化
- 葉色の時系列トレンド
- オプティカルフロー（成長速度）
- 拡大率（領域の成長）
- 異常フレーム検出
- トレンド分析（変化率計算）

### 2. モデルトレーニング

LightGBMモデルをトレーニング：

```bash
python train.py
```

自動的にサンプルデータを生成してトレーニングします。

**出力内容：**
- トレーニング済みモデル（models/）
- 精度指標（RMSE, MAE, R²）
- 特徴量重要度

### 3. 将来予測

オリーブの将来状態を予測：

```bash
python predict.py
```

3日後、7日後、14日後、30日後の状態を予測します。

**出力内容：**
- 予測値
- 解釈テキスト
- 信頼度
- レポート（outputs/）

## プロジェクト構成

```
olive-p/
├── README.md              # プロジェクト説明
├── QUICKSTART.md          # このファイル
├── requirements.txt       # Python依存パッケージ
├── config/
│   └── config.yaml        # 設定ファイル
├── src/
│   ├── __init__.py
│   ├── utils.py           # ユーティリティ関数
│   ├── preprocessing.py   # 画像前処理
│   ├── detection.py       # 葉・実検出
│   ├── color_analysis.py  # 色解析
│   └── feature_extraction.py  # 特徴量抽出
├── analyze.py             # 画像解析メインスクリプト
├── train.py               # モデルトレーニング
├── predict.py             # 予測スクリプト
├── data/
│   ├── raw_images/        # 入力画像
│   ├── processed/         # 処理済みデータ
│   └── database/          # データベース
├── models/                # 学習済みモデル
└── outputs/               # 解析結果
```

## 主なモジュール

### preprocessing.py
- `ImagePreprocessor`: ノイズ除去、白バランス補正、ガンマ補正
- `ColorSpaceConverter`: 複数色空間への変換

### detection.py
- `ObjectDetector`: 葉・実の自動検出

### color_analysis.py
- `ColorAnalyzer`: 複数色空間での色解析、枯葉度計算

### feature_extraction.py
- `FeatureExtractor`: 時系列特徴量の抽出
- `TimeSeriesFeatureExtractor`: 遅延特徴量、移動平均、差分特徴量
- `FeatureScaler`: 特徴量正規化

## サンプル実行フロー

```bash
# 1. 環境構築
pip install -r requirements.txt

# 2. テスト画像を用意（data/raw_images/に配置）

# 3. 画像を解析（高度な検出＋テクスチャ解析付き）
python analyze.py data/raw_images/sample.jpg

# 3b. 動画を解析（オプション）
python analyze.py data/raw_images/sample.mp4 --frame-interval 30

# 4. モデルをトレーニング（サンプルデータで学習）
python train.py

# 5. 将来状態を予測
python predict.py
```

## 新機能（v0.2.0）

### 動画対応
- 複数フレームの時系列解析
- オプティカルフロー追跡
- 成長速度の自動計算
- 異常フレーム検出

### 精度向上
- マルチスケール葉検出
- 背景除去の複数手法
- HSV範囲の自動最適化
- テクスチャ解析（GLCM/LBP）
- 検出信頼度スコア
- 後処理フィルタリング

### 新しい特徴量
- 葉の滑らかさ（surface roughness）
- 実の光沢度（shine/reflection）
- オプティカルフロー指標
- テクスチャエネルギー
- GLCM特徴（対比度、均質性など）

## 特徴量

### 抽出される特徴量の例（100+種類）

**葉関連:**
- 葉の個数、平均面積・最大面積・最小面積
- 平均Hue（色）
- 枯葉度合い
- 形状特性（円形度、Solidity、アスペクト比）
- テクスチャ特性（エネルギー、粗さ）
- GLCM特徴（対比度、相関性など）
- LBP特徴（均一性、エントロピー）
- 表面の滑らかさ

**実関連:**
- 実の個数
- 平均直径・面積
- 熟度ステージ
- 円形度
- 光沢度（brightness ratio）

**色解析:**
- RGB値
- HSV値
- Lab値
- 色差（ΔE）
- 色相トレンド

**テクスチャ:**
- 表面粗さ
- エッジ密度
- LBPヒストグラム特徴
- GLCM統計量

**動き・成長:**
- オプティカルフロー大きさ
- 領域拡大率（divergence）
- 特徴点速度
- 加速度（追跡ベース）

**画像全体:**
- 画像サイズ
- エッジ密度
- 平均輝度
- 対比度

## 予測対象

モデルは以下を予測できます：

- 3日後の葉色
- 7日後の実の熟度
- 14日後の枯葉率
- 30日後の樹勢

## カスタマイズ

### 葉検出のパラメータ調整

`config/config.yaml`の`leaf_detection`セクション：

```yaml
leaf_detection:
  hue_range: [35, 95]        # Hue範囲（環境に応じて調整）
  saturation_range: [30, 255]
  value_range: [30, 255]
  min_area: 50               # 最小ピクセル数
  circularity_threshold: 0.3 # 円形度閾値
```

### 機械学習パラメータ

`config/config.yaml`の`machine_learning`セクション：

```yaml
machine_learning:
  n_estimators: 100
  max_depth: 7
  learning_rate: 0.1
```

## トラブルシューティング

### 画像が読み込めない場合

- ファイルパスが正しいか確認
- サポート形式（JPG, PNG, BMP, TIFF）か確認

### 葉・実が検出されない場合

- 照明条件が悪い場合、`config.yaml`のパラメータを調整
- 画像の前処理（ガウシアンフィルタ、CLAHEなど）を確認

### モデルトレーニング時のエラー

- データファイルが存在するか確認
- 依存パッケージがインストールされているか確認

## 次のステップ

1. **時系列解析の構築**
   - `data/processed/`に複数の日時の特徴量を保存
   - TimeSeriesFeatureExtractorで時系列特徴を作成

2. **モデルの改善**
   - より多くのトレーニングデータを集める
   - 異なるML手法（XGBoost、CatBoost、LSTM）を試す

3. **ダッシュボード開発**
   - 結果を視覚化するWebインターフェース

4. **IoT統合**
   - Raspberry Pi等で自動撮影・解析を実装

## ライセンス

MIT License

## 参考文献

- OpenCV Documentation: https://docs.opencv.org/
- LightGBM Documentation: https://lightgbm.readthedocs.io/
- scikit-learn: https://scikit-learn.org/

---

質問や問題がある場合は、GitHubのIssuesでお知らせください。
