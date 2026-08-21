# OliveVision AI

> AI-Powered Long-Term Olive Tree Monitoring System using Computer Vision and Machine Learning

## Production Raspberry Pi runtime

The original code remains available for research and model experiments. For
actual local operation on Raspberry Pi or a desktop, use the lightweight
`olivevision.py` CLI/GUI: it needs no environmental data, trained model, or
network connection; shows each processing step; stores annotated images, JSON,
and a local SQLite history. See [the operations guide](docs/OPERATIONS.md) for
Pi 4/Pi 5 requirements, installation, GUI, CLI, camera monitoring, and the
systemd service configuration.

---

# 日本語

## 🌳 OliveVision AIとは

OliveVision AIは、オリーブ樹の長期観測を目的としたAI画像解析システムです。

定点カメラやスマートフォンなどで1時間ごとに撮影された画像・動画を入力すると、

- オリーブの葉
- オリーブの実
- 枝
- 樹冠

を自動認識し、

- 色
- 形状
- 大きさ
- 成長速度
- 枯葉率
- 熟成度
- 葉数
- 実数

など多数の特徴量を抽出します。

さらに、取得した時系列データをLightGBMへ入力し、

数日後〜数週間後のオリーブの状態変化を予測します。

本プロジェクトは農業DX・スマート農業・植物フェノタイピング・研究用途を想定しています。

---

# English

## 🌳 What is OliveVision AI?

OliveVision AI is an AI-powered computer vision system designed for long-term olive tree monitoring.

Images and videos captured periodically (e.g., every hour) are automatically analyzed to detect

- Olive fruits
- Olive leaves
- Branches
- Tree canopy

The system extracts numerous biological features including

- Color
- Shape
- Size
- Growth rate
- Leaf aging
- Fruit maturity
- Number of fruits
- Number of leaves

The extracted time-series data are then used to train a LightGBM model for predicting future changes in olive tree conditions.

This project is intended for Smart Agriculture, Agricultural AI, Plant Phenotyping and Research.

---

# 🎯 Project Objectives

本プロジェクトでは画像解析だけではなく、

「未来予測」

を最終目標としています。

例えば、

- この葉は3日後に黄変するか？
- この実は5日後に成熟するか？
- 樹勢が低下していないか？
- 生理落下が発生しそうか？
- 水不足の兆候はあるか？

などをAIが予測します。

---

# 🚀 Main Features

## OpenCV Image Analysis

- Leaf Detection
- Fruit Detection
- Branch Detection
- Canopy Detection
- Background Removal
- Color Extraction
- Shape Analysis
- Object Tracking
- Time Series Analysis

---

## Machine Learning

- LightGBM
- Feature Engineering
- Time-series Prediction
- Growth Prediction
- Color Prediction
- Stress Detection
- Early Warning System

---

## Visualization

- Growth Graph
- Color Transition
- Fruit Count
- Leaf Count
- Heatmap
- Daily Report
- Weekly Report
- Monthly Report

---

# 📈 Overall Workflow

```text
Image / Video
      │
      ▼
OpenCV
      │
      ▼
Object Detection
      │
      ▼
Leaf Detection
Fruit Detection
Branch Detection
      │
      ▼
Feature Extraction
      │
      ▼
Color Analysis
Shape Analysis
Texture Analysis
Growth Analysis
      │
      ▼
Database
      │
      ▼
LightGBM
      │
      ▼
Future Prediction
      │
      ▼
Dashboard
```

---

# 🧠 System Architecture

```text
Camera
   │
   ▼

Image Collection
   │

Pre-processing
   │

OpenCV Analysis
   │

Object Detection
   │

Feature Extraction
   │

Database
   │

Machine Learning
   │

Prediction Engine
   │

Visualization
```

---

# 📷 Supported Inputs

## Images

- JPG
- PNG
- BMP
- TIFF

---

## Videos

- MP4
- AVI
- MOV
- MKV

---

## Live Camera

- USB Camera
- Raspberry Pi Camera
- IP Camera
- RTSP Stream

---

# 🔬 Core Technologies

| Technology | Purpose |
|------------|----------|
| OpenCV | Image Processing |
| NumPy | Numerical Computing |
| Pandas | Data Analysis |
| LightGBM | Machine Learning |
| Matplotlib | Visualization |
| Scikit-learn | Feature Processing |
| OpenPyXL | Excel Export |
| SQLite | Local Database |
| YOLO (Optional) | Object Detection |
| Segment Anything (Future) | Segmentation |

---

# 💡 Why OpenCV?

OpenCV provides robust and fast image processing capabilities suitable for agricultural monitoring.

It enables:

- Edge Detection
- Morphological Processing
- Contour Analysis
- Color Space Conversion
- Optical Flow
- Object Tracking
- Background Subtraction

allowing the system to operate even on low-power devices such as Raspberry Pi.

---

# 🎨 Color Spaces Used

Instead of relying only on RGB values, the project utilizes multiple color spaces for more accurate biological analysis.

| Color Space | Purpose |
|-------------|----------|
| RGB | Original Image |
| HSV | Leaf/Fruit Color |
| LAB | Color Difference |
| YCrCb | Brightness Robustness |
| Gray | Shape Detection |

Using multiple color spaces improves robustness against:

- Shadows
- Cloudy weather
- Direct sunlight
- Seasonal illumination changes

---

# 🔍 Main Analysis Targets

The system continuously observes:

- Leaf color
- Fruit color
- Leaf shape
- Fruit size
- Number of fruits
- Number of leaves
- Growth speed
- Tree vigor
- Health condition
- Canopy density
- Branch visibility
- Disease symptoms (future)
- Pest symptoms (future)

---

# 📊 Long-term Monitoring

Unlike ordinary image classification projects, OliveVision AI performs continuous monitoring.

Example:

```

2026/01/01 10:00

↓

2026/01/01 11:00

↓

2026/01/01 12:00

↓

...

↓

2027/01/01

↓

2028/01/01

```

The accumulated time-series data enable advanced prediction of growth trends and environmental responses.

---

# ⭐ Future Vision

Ultimately, OliveVision AI aims to become an autonomous agricultural AI platform capable of:

- Monitoring orchard health
- Predicting fruit maturity
- Detecting abnormal growth
- Estimating harvest timing
- Providing cultivation recommendations
- Supporting agricultural research

# 🌿 Part 2 - Image Analysis (OpenCV)

---

# 日本語

## 🌿 葉検出（Leaf Detection）

葉の検出は本システムの最も重要な解析の一つです。

一般的な植物画像解析では色だけで葉を検出することが多いですが、本プロジェクトでは以下の複数の特徴量を組み合わせて高精度に検出します。

### 使用する特徴

- HSV色空間
- Lab色空間
- RGB
- 輪郭形状（Contour）
- 面積
- 周囲長
- 円形度
- アスペクト比
- Hu Moments
- Convex Hull
- Solidity
- Extent

---

## 前処理

画像はまずノイズを除去します。

### 1. Gaussian Blur

細かなノイズを除去します。

```text
Input
↓

Gaussian Blur
↓

Smooth Image
```

---

### 2. CLAHE

局所コントラストを改善します。

これにより

- 曇り
- 夕方
- 逆光

でも認識率が向上します。

---

### 3. White Balance

ホワイトバランス補正を行い、

時間帯による色変化を軽減します。

---

### 4. Gamma Correction

暗い画像でも色の判定精度を維持します。

---

# 🌿 葉領域抽出

RGBではなくHSVを利用します。

```text
RGB

↓

HSV

↓

Green Mask

↓

Morphology

↓

Contours

↓

Leaf Candidates
```

---

### HSV範囲（例）

```text
Hue
35〜95

Saturation
30〜255

Value
30〜255
```

※実際には固定値ではなく自動調整します。

---

## Morphology

ノイズ除去のため

- Opening
- Closing
- Erosion
- Dilation

を組み合わせます。

```text
Mask

↓

Opening

↓

Closing

↓

Clean Mask
```

---

## Contour解析

各輪郭について

```python
Area

Perimeter

Bounding Box

Convex Hull

Solidity

Circularity
```

を計算します。

---

### 円形度

```
Circularity

= 4πA / P²
```

葉は極端な円形にならないため、

この値を利用して雑草やノイズを除外します。

---

### Solidity

```
Area

/

Convex Hull Area
```

葉は比較的Solidityが高い特徴があります。

---

### Hu Moments

Hu Momentsを利用して

葉の形状特徴を学習します。

これにより

- 回転
- 拡大
- 縮小

に対して頑健になります。

---

# 🫒 オリーブ実検出

実の検出では

色だけではなく

- 円形度
- テクスチャ
- 大きさ

も利用します。

---

## 実検出フロー

```text
Input

↓

HSV

↓

Fruit Color Mask

↓

Morphology

↓

Circle Candidate

↓

Contour Analysis

↓

Fruit Detection
```

---

## 実の特徴

抽出する特徴

- Area
- Radius
- Diameter
- Major Axis
- Minor Axis
- Circularity
- Mean Color
- Texture

---

### 円形判定

```
Circularity

> 0.7
```

などの条件を利用します。

---

### 実サイズ

算出項目

- 最大径
- 最小径
- 面積
- 推定体積

---

# 🎨 色解析

色解析は本プロジェクトの中心となる解析です。

RGBのみでは

照明条件によって変化してしまいます。

そこで

複数色空間を利用します。

---

## RGB

取得値

```
Mean R

Mean G

Mean B
```

---

## HSV

取得値

```
Mean Hue

Mean Saturation

Mean Value
```

特に

Hue

が重要になります。

---

### Hueによる葉色判定

例

```text
H=45

濃い緑

H=60

健康

H=75

若葉

H=25

黄化

H=15

枯れ始め

H<10

褐変
```

※栽培品種や撮影条件に応じて補正が必要です。

---

## Lab色空間

Labでは

色差ΔEを利用できます。

これにより

昨日

↓

今日

↓

明日

の変化量を定量化できます。

---

### 色差

```
ΔE

=
√((L1-L2)²

+(a1-a2)²

+(b1-b2)²)
```

利用用途

- 黄化
- 褐変
- 熟成
- 劣化

---

# 🍃 枯葉率

葉ごとに

Healthy

Yellow

Brown

Dead

へ分類します。

---

例

```
Healthy

850枚

Yellow

90枚

Brown

40枚

Dead

20枚
```

---

枯葉率

```
(Dead

+

Brown)

/

Total Leaves
```

例えば

```
60

/

1000

=

6%
```

---

# 🫒 実の成熟度

色から

成熟段階を推定します。

例

```
Stage1

Bright Green

Stage2

Dark Green

Stage3

Yellow Green

Stage4

Purple

Stage5

Black
```

成熟割合を算出します。

---

# 📈 成長速度

長期観測データから

面積変化を計算します。

```
Today's Area

Yesterday's Area

Difference

Growth Rate
```

例えば

```
昨日

420px²

今日

445px²

増加

25px²
```

時間当たりの増加量を算出します。

---

# 🌳 樹勢評価

以下を総合評価します。

- 葉数
- 葉色
- 実数
- 成熟率
- 枯葉率
- 樹冠面積
- 成長速度

これらをスコア化し、

```
Excellent

Good

Normal

Warning

Critical
```

の5段階で樹勢を評価します。

---

# 📊 OpenCVで取得する全特徴量

## 葉

- 面積
- 周囲長
- 重心
- 重心移動量
- 傾き
- 外接矩形
- 最小外接円
- Hu Moments
- Solidity
- Extent
- Circularity
- RGB平均
- HSV平均
- Lab平均
- テクスチャ特徴
- エッジ密度

---

## 実

- 面積
- 半径
- 直径
- 円形度
- 重心
- 色平均
- テクスチャ
- エッジ密度
- 成熟度
- 推定体積

---

## 樹木全体

- 樹冠面積
- 葉密度
- 実密度
- 葉枚数
- 実数
- 枯葉率
- 平均葉色
- 平均実色
- 生育指数
- 樹勢指数
- 被覆率（Canopy Coverage）

---

# 🎯 Part 2 Summary

OpenCVでは単なる物体検出ではなく、

- 葉の検出
- 実の検出
- 色解析
- 形状解析
- テクスチャ解析
- 成長解析
- 樹勢解析

を統合し、数百種類以上の特徴量を抽出します。

これらの特徴量は次章でLightGBMへ入力され、将来の色変化・成長速度・異常兆候を予測するための教師データとして利用されます。

# 🤖 Part 3 - Machine Learning & Future Prediction (LightGBM)

---

# 日本語

## 🤖 機械学習による将来予測

OpenCVによる画像解析だけでは、「現在の状態」を把握することしかできません。

本プロジェクトでは、長期間蓄積された時系列データを機械学習モデルへ入力することで、

**「未来の状態」を予測するAIシステム**を構築します。

解析対象は以下のような変化です。

- 葉色の変化
- 実色の変化
- 枯葉率
- 葉数
- 実数
- 成長速度
- 樹勢
- 異常兆候
- 水不足
- 生理落下
- 収穫適期

---

# なぜLightGBMなのか

本プロジェクトでは深層学習（LSTMやTransformer）ではなく、

まずLightGBMを採用します。

理由は以下の通りです。

- 学習速度が非常に速い
- 少量データでも高精度
- 特徴量の重要度を確認できる
- 欠損値に強い
- 過学習しにくい
- Raspberry Piでも推論可能
- 時系列特徴量との相性が良い

---

# 学習フロー

```text
OpenCV

↓

特徴量抽出

↓

CSV / SQLite

↓

特徴量生成

↓

LightGBM

↓

予測モデル

↓

未来予測
```

---

# 時系列データ

本システムは

**1時間ごと**

にデータを保存します。

例

| 時刻 | 葉数 | 実数 | 平均Hue | 枯葉率 |
|------|------|------|----------|---------|
|10:00|1023|215|57|3.2%|
|11:00|1021|215|56|3.2%|
|12:00|1020|216|56|3.3%|
|13:00|1017|216|55|3.4%|

これを数か月～数年間蓄積します。

---

# 特徴量（Features）

LightGBMへ入力する特徴量は100項目以上を想定しています。

## 基本情報

- 撮影日時
- 曜日
- 月
- 季節
- 撮影時刻

---

## 葉情報

- 葉数
- 平均面積
- 最大面積
- 最小面積
- 平均Hue
- 平均Saturation
- 平均Brightness
- 平均Lab
- 枯葉率
- 黄葉率
- 葉密度
- 葉重心
- 葉形状特徴量

---

## 実情報

- 実数
- 平均直径
- 最大直径
- 最小直径
- 平均色
- 成熟率
- 紫色割合
- 黒色割合
- 緑色割合

---

## 樹木全体

- 樹冠面積
- 被覆率
- 樹勢スコア
- 総葉面積
- 総実面積

---

## 気象情報（任意）

より高精度な予測を行うため、外部センサーデータや気象データを特徴量として利用できます。

- 気温
- 湿度
- 気圧
- 日照時間
- 降水量
- 風速
- 土壌水分
- 土壌温度
- CO₂濃度
- 光量（Lux）

---

# ラグ特徴量（Lag Features）

過去の状態を特徴量として利用します。

例

```text
現在

↓

1時間前

↓

2時間前

↓

6時間前

↓

12時間前

↓

24時間前

↓

48時間前

↓

72時間前
```

これにより、

「昨日から葉色が徐々に黄色くなっている」

といった変化を学習できます。

---

# 移動平均特徴量

短期的な変化だけではなく、

長期傾向も学習します。

例

- 3時間平均
- 6時間平均
- 12時間平均
- 24時間平均
- 7日平均
- 30日平均

---

# 差分特徴量

変化量も重要な特徴です。

例

```text
現在Hue

-

1日前Hue

=

色変化量
```

同様に、

- 葉数差分
- 実数差分
- 成長量
- 枯葉率変化

も特徴量になります。

---

# 教師データ（Target）

LightGBMでは目的変数を複数作成できます。

例

## 回帰問題

- 3日後の平均Hue
- 7日後の実色
- 5日後の葉数
- 7日後の枯葉率
- 10日後の樹勢スコア

---

## 分類問題

- 黄変するか
- 枯れるか
- 実が成熟するか
- 生理落下が起こるか
- 異常発生するか

---

# 予測例

入力

```text
現在

平均Hue = 56

枯葉率 = 3%

葉数 = 1050
```

↓

AI

```text
3日後

平均Hue = 52

枯葉率 = 5%

葉数 = 1015
```

---

# 成長速度予測

OpenCVで計算した成長速度を学習します。

例

```text
Day1

0.45%

Day2

0.43%

Day3

0.40%

Day4

0.36%
```

AIは

「成長速度が低下している」

ことを検出できます。

---

# 色変化予測

例えば

```text
Green

↓

Dark Green

↓

Yellow Green

↓

Purple

↓

Black
```

という成熟パターンを学習します。

これにより

収穫適期を推定できます。

---

# 異常検知

以下のような異常を早期検出します。

- 急激な黄化
- 葉の大量落下
- 成長停止
- 果実の異常着色
- 樹冠縮小
- 実数減少
- 葉密度低下

---

# 特徴量重要度

LightGBMでは

各特徴量が予測へどれだけ影響したか確認できます。

例

|順位|特徴量|重要度|
|----|-------|------|
|1|平均Hue|1245|
|2|土壌水分|1102|
|3|気温|1034|
|4|枯葉率|956|
|5|樹冠面積|892|

これにより、

オリーブの成長に最も影響する要因を分析できます。

---

# モデル更新

AIは定期的に再学習します。

例

```text
毎日

↓

新しいデータ追加

↓

モデル再学習

↓

精度向上
```

---

# 評価指標

## 回帰モデル

- RMSE
- MAE
- MSE
- R² Score
- MAPE

---

## 分類モデル

- Accuracy
- Precision
- Recall
- F1 Score
- ROC-AUC
- Confusion Matrix

---

# 推論結果

AIは単なる数値だけでなく、

解釈しやすい文章も生成します。

例

```text
現在の葉色は健康状態です。

3日以内に黄変率が
約4%増加する可能性があります。

成長速度は平均より
12%低下しています。

水不足の可能性があります。
```

---

# 将来的なAI拡張

LightGBMに加えて、

以下のモデルも比較・検証予定です。

- CatBoost
- XGBoost
- Random Forest
- Extra Trees
- LSTM
- GRU
- Temporal Fusion Transformer (TFT)
- Transformer
- TabNet
- NGBoost

---

# AIパイプライン

```text
Camera

↓

OpenCV

↓

画像解析

↓

特徴量抽出

↓

SQLite / CSV

↓

特徴量生成

↓

LightGBM

↓

予測

↓

異常検知

↓

ダッシュボード

↓

通知システム
```

---

# 🎯 Part 3 Summary

本システムでは、OpenCVで取得した数百種類の特徴量と長期間蓄積した時系列データを活用し、LightGBMによってオリーブ樹の将来状態を予測します。

予測対象は単なる色の変化だけでなく、葉や果実の成長速度、枯葉率、成熟度、樹勢、水不足の兆候、生理落下の可能性、さらには収穫適期まで多岐にわたります。

画像解析と機械学習を統合することで、「現在を観測するシステム」から「未来を予測するシステム」へ発展させることを目指します。

---

# English (Summary)

OliveVision AI combines advanced computer vision with LightGBM-based machine learning to predict future olive tree conditions from long-term time-series observations.

The prediction targets include:

- Leaf color transition
- Fruit maturation
- Growth rate
- Leaf aging
- Tree vigor
- Water stress
- Fruit drop risk
- Harvest timing

By continuously learning from accumulated observations, the system evolves into an intelligent decision-support platform for smart agriculture, precision farming, and plant phenotyping research.

# 📦 Part 4 - Installation, Project Structure, Roadmap & License

---

# 日本語

# 📂 ディレクトリ構成

プロジェクトは以下のような構成を想定しています。

```text
OliveVision-AI/
│
├── README.md
├── README_EN.md
├── LICENSE
├── requirements.txt
├── pyproject.toml
├── .gitignore
│
├── config/
│   ├── config.yaml
│   ├── camera.yaml
│   └── model.yaml
│
├── data/
│   ├── raw_images/
│   ├── raw_videos/
│   ├── processed/
│   ├── dataset/
│   └── database/
│
├── models/
│   ├── lightgbm/
│   ├── yolo/
│   ├── sam/
│   └── checkpoints/
│
├── src/
│   ├── preprocessing/
│   ├── detection/
│   ├── segmentation/
│   ├── tracking/
│   ├── color_analysis/
│   ├── feature_extraction/
│   ├── ml/
│   ├── visualization/
│   └── utils/
│
├── dashboard/
│
├── notebooks/
│
├── docs/
│
├── tests/
│
└── outputs/
```

---

# 💻 推奨環境

## OS

- Windows 11
- Ubuntu 22.04+
- Debian
- Raspberry Pi OS
- macOS

---

## Python

```
Python 3.12+
```

---

## 推奨スペック

最低

- CPU 4コア
- RAM 8GB

推奨

- CPU 8コア以上
- RAM 16GB以上
- CUDA対応GPU

---

# 📥 インストール

Clone

```bash
git clone https://github.com/yourname/OliveVision-AI.git
```

移動

```bash
cd OliveVision-AI
```

仮想環境

```bash
python -m venv .venv
```

Windows

```bash
.venv\Scripts\activate
```

Linux

```bash
source .venv/bin/activate
```

インストール

```bash
pip install -r requirements.txt
```

---

# ▶ 実行

画像解析

```bash
python analyze.py image.jpg
```

動画解析

```bash
python analyze.py movie.mp4
```

ディレクトリ解析

```bash
python analyze.py dataset/
```

学習

```bash
python train.py
```

未来予測

```bash
python predict.py
```

---

# 📄 出力ファイル

解析後

```
outputs/

├── result.jpg
├── result.mp4
├── report.csv
├── report.xlsx
├── features.csv
├── prediction.csv
└── graphs/
```

---

# 📊 出力される情報

葉

- 葉数
- 平均面積
- 色
- 枯葉率
- 黄葉率

---

実

- 実数
- 成熟率
- 色
- 面積
- 推定体積

---

樹木

- 樹勢
- 被覆率
- 成長速度
- 健康状態

---

AI予測

- 3日後
- 5日後
- 7日後
- 14日後
- 30日後

---

# 📈 ダッシュボード

Web Dashboardでは

- リアルタイム画像
- 色変化
- 成長速度
- AI予測
- グラフ
- ヒートマップ
- カメラ状態

などを表示します。

---

# 📡 長期観測

想定する運用

```
1時間ごと

↓

画像取得

↓

解析

↓

データ保存

↓

AI更新

↓

レポート生成
```

365日連続運転を前提としています。

---

# 🔔 通知機能（予定）

以下の異常を検出すると通知できます。

- 枯葉率増加
- 黄化
- 急激な色変化
- 成長停止
- 実落下
- カメラ異常
- 通信異常

通知先

- Discord
- LINE
- Slack
- E-mail
- Webhook

---

# 🌱 将来の拡張予定

## Computer Vision

- YOLOv11
- YOLOv12
- Segment Anything Model 2
- Detectron2
- OpenVINO
- TensorRT

---

## AI

- XGBoost
- CatBoost
- Random Forest
- LSTM
- Transformer
- TFT
- TabNet
- AutoML

---

## IoT

- Raspberry Pi
- NVIDIA Jetson
- ESP32
- Arduino
- LoRaWAN
- LTE
- 5G

---

## センサー

- 土壌水分
- 気温
- 湿度
- 気圧
- 雨量
- CO₂
- 照度
- 紫外線
- 土壌EC
- 土壌pH

---

## 将来的な研究テーマ

- 病害虫の早期発見
- 水ストレス推定
- 栄養不足推定
- 収穫量予測
- 剪定支援
- 自動灌水
- 気候変動解析
- 植物フェノタイピング
- デジタルツイン農園

---

# 📚 学術利用

本プロジェクトは以下の用途を想定しています。

- 大学研究
- 高専研究
- 農業研究
- スマート農業
- AI教育
- 機械学習教材
- OpenCV教材
- 植物解析

---

# 🤝 コントリビューション

Pull Requestは歓迎します。

改善例

- 新しい特徴量
- 新しいAIモデル
- 新しいセンサー
- 高速化
- GUI改善
- バグ修正
- ドキュメント改善

---

# 📜 ライセンス

本プロジェクトでは、利用するライブラリや学習モデルごとにライセンスが異なります。

主な例：

| コンポーネント | ライセンス |
|--------------|-----------|
| Python | PSF License |
| OpenCV | Apache License 2.0 |
| NumPy | BSD 3-Clause License |
| Pandas | BSD 3-Clause License |
| scikit-learn | BSD 3-Clause License |
| LightGBM | MIT License |
| Matplotlib | PSF-based License |

**注意:** YOLO系モデルや学習済み重み、外部データセットを利用する場合は、それぞれのライセンス（例: AGPL、GPL、CC BYなど）を必ず確認してください。

---

# ⭐ Star History

もしこのプロジェクトが役に立ったら

GitHub Star ⭐ をお願いします！

---

# English

## Overview

OliveVision AI is an open-source long-term olive tree monitoring platform that integrates:

- OpenCV
- Machine Learning
- Time-series Analysis
- Smart Agriculture
- Computer Vision

The system continuously observes olive trees, extracts hundreds of biological features, predicts future growth, and visualizes long-term trends.

---

## Main Features

- Automatic leaf detection
- Automatic fruit detection
- Color analysis
- Shape analysis
- Time-series monitoring
- Growth prediction
- Stress detection
- LightGBM forecasting
- Dashboard visualization
- CSV / Excel export

---

## Installation

```bash
git clone https://github.com/yourname/OliveVision-AI.git

cd OliveVision-AI

pip install -r requirements.txt
```

---

## Run

```bash
python analyze.py image.jpg

python train.py

python predict.py
```

---

## Future Goals

- Autonomous orchard monitoring
- Harvest prediction
- Disease detection
- Water stress estimation
- Smart irrigation support
- Digital twin orchard
- AI-assisted agriculture

---

## Contributing

Contributions are always welcome!

You can contribute by:

- Improving image processing
- Adding new ML models
- Optimizing performance
- Improving documentation
- Fixing bugs
- Supporting new sensors
- Developing the web dashboard

---

## License

This project is distributed under the **MIT License** unless otherwise specified.

Please note that third-party libraries, pretrained models, and datasets may have different licenses. Always verify and comply with the original license terms before redistribution or commercial use.

---

# 🎯 Project Vision

> **"Transforming long-term olive cultivation into a data-driven, AI-assisted, and scientifically measurable process."**

OliveVision AI aims to bridge computer vision, machine learning, and precision agriculture to support researchers, farmers, and engineers in understanding and predicting olive tree growth over months and years.

---

# Acknowledgements

This project would not be possible without the amazing open-source community behind:

- OpenCV
- LightGBM
- NumPy
- Pandas
- Scikit-learn
- Matplotlib
- Python

Special thanks to all researchers and contributors advancing precision agriculture, plant phenotyping, and AI for sustainable farming.