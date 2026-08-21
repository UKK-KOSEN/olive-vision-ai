# 土壌水分統合ガイド

OliveVision AI に UKK-KOSEN 土壌水分監視システムを統合する方法。

## クイックスタート

### 1. 設定ファイルを編集

```bash
# config/soil_moisture.yaml を開く
nano config/soil_moisture.yaml
```

```yaml
# API エンドポイント（Cloudflare Pages）
api_base_url: "https://soil-moisture-final.pages.dev"

# APIキー（必要な場合のみ）
api_key: ""

# デフォルトのキットID
default_kit_id: "default"
```

### 2. CLI で土壌水分を確認

```bash
# 最新の土壌水分を表示
python olivevision.py soil latest

# 過去24時間の履歴を表示
python olivevision.py soil history

# 統計情報を表示
python olivevision.py soil stats

# 簡易ステータス表示
python olivevision.py soil status
```

### 3. 画像解析に土壌水分を統合

```bash
# 土壌水分を自動統合（デフォルト）
python olivevision.py analyze photo.jpg

# 土壌水分を無効にして解析
python olivevision.py analyze photo.jpg --no-soil-moisture
```

## CLI コマンドリファレンス

### `soil` サブコマンド

| サブコマンド | 説明 | オプション |
|-------------|------|-----------|
| `latest` | 最新の土壌水分データを表示 | — |
| `history` | 過去の履歴を表示 | `--hours N` |
| `stats` | 統計情報を表示 | `--hours N` |
| `status` | 簡易ステータスを表示 | — |

**例:**
```bash
# 過去48時間の履歴
python olivevision.py soil history --hours 48

# 過去72時間の統計
python olivevision.py soil stats --hours 72
```

### `analyze` / `capture` コマンド

| フラグ | 説明 |
|--------|------|
| `--no-soil-moisture` | 土壌水分統合をスキップ |

**例:**
```bash
# 土壌水分を統合して画像を解析
python olivevision.py analyze IMG_6497.jpg

# カメラからキャプチャ（土壌水分統合なし）
python olivevision.py capture --camera 0 --no-soil-moisture
```

### `status` コマンド

土壌水分データは `status` コマンドの各行に表示されます。

```
  2026-08-21 10:00  IMG  第1試験樹  L= 25  F= 3  G=45.2%  OPTIMAL=52%
```

## GUI 使い方

### 土壌水分タブ

GUI を起動すると、Notebook に「Soil Moisture」タブが追加されています。

```bash
python olivevision.py gui
```

タブには以下が表示されます:
- **Status**: 土壌水分の状態（DRY/OPTIMAL/WET）
- **Moisture Levels**: センサー1/2の値と平均
- **Environment**: 温度・湿度
- **Health Assessment**: 健康リスク評価
- **24h Statistics**: 過去24時間の統計

### オン/オフトグル

ツールバーの「Soil Moisture」チェックボックスで、解析時の土壌水分統合をON/OFFできます。

- **ON**: 画像解析時に土壌水分データを自動取得し、健康評価に統合
- **OFF**: 画像解析のみ実行（土壌水分データなし）

## 健康評価への統合

### 仕組み

1. 画像解析時に拍照時刻を取得
2. 同じ時間帯の土壌水分データをAPIから取得
3. 土壌水分のリスクレベルを判定
4. 既存の視覚的健康スコアと組み合わせて総合スコアを算出

### リスクレベル

| レベル | 土壌水分 (avg) | スコア | 説明 |
|--------|---------------|--------|------|
| critical | < 20% | 0.1 | 深刻な水分不足 |
| high | 20-30% または > 75% | 0.3 | 水分不足/過湿のリスク |
| moderate | 30-40% または 65-75% | 0.6-0.7 | やや水分不足/過湿 |
| normal | 40-65% | 1.0 | 適切な水分 |

### 総合スコアの算出

```
総合スコア = 視覚スコア × (1 - 土壌水分重み) + 土壌水分スコア × 土壌水分重み
```

- 視覚スコア: 既存の健康評価（葉の色、シワ、巻き込み等）
- 土壌水分スコア: 土壌水分の状態から算出
- 重み: リスクレベルに応じて自動調整（0-30%）

## Python API

### 基本的な使い方

```python
from src.soil_moisture import SoilMoistureClient, get_moisture_for_olive_analysis

# クライアント作成
client = SoilMoistureClient()

# 最新データ取得
latest = client.get_latest()
print(f"水分: {latest['sensor1_moisture_percent']}%")

# 時刻指定でデータ取得
from datetime import datetime
target = datetime(2026, 8, 21, 10, 0, 0)
data = client.get_moisture_at_time(target, window_hours=2.0)

# オリーブ解析統合用データ
result = get_moisture_for_olive_analysis(client, target_time=target)
print(result["soil_moisture"]["status"])  # "dry"/"optimal"/"wet"
print(result["soil_moisture"]["health"]["risk"])  # "critical"/"high"/"moderate"/"normal"
```

### 健康評価の統合

```python
from src.runtime import integrate_soil_moisture
from src.soil_moisture import get_moisture_for_olive_analysis

# 画像解析の結果に土壌水分を統合
result = analyzer.analyze(image, "file")
soil_data = get_moisture_for_olive_analysis(target_time=obs_time)
result = integrate_soil_moisture(result, soil_data)

# 結果を確認
print(result["health_assessment"]["combined_health_score"])
print(result["health_assessment"]["moisture_risk"])
```

## トラブルシューティング

### データが取得できない

1. ネットワーク接続を確認
2. `config/soil_moisture.yaml` の `api_base_url` を確認
3. `python olivevision.py soil latest` で直接テスト

### 健康評価に土壌水分が反映されない

1. GUI: ツールバーの「Soil Moisture」チェックボックスがONか確認
2. CLI: `--no-soil-moisture` フラグが付いていないか確認
3. 土壌水分システムが稼働しているか確認

### API エラー

```bash
# API の接続テスト
python olivevision.py soil latest --verbose
```

## 設定項目リファレンス

`config/soil_moisture.yaml`:

| 項目 | デフォルト | 説明 |
|------|-----------|------|
| `api_base_url` | — | Cloudflare Pages のURL |
| `api_key` | `""` | 認証キー（必要な場合のみ） |
| `default_kit_id` | `"default"` | デフォルトのキットID |
| `timeout` | `10` | ネットワークタイムアウト（秒） |
| `cache_ttl` | `60` | キャッシュ有効期間（秒） |
| `olive_integration.weight` | `0.3` | 健康評価での土壌水分の重み |
| `olive_integration.thresholds.dry` | `20` | 水分不足のしきい値（%） |
| `olive_integration.thresholds.wet` | `70` | 過湿のしきい値（%） |
