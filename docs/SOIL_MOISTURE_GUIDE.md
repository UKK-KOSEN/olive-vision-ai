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
api_base_url: "https://soil-moisture-pages-ddl.pages.dev"

# APIキー（必要な場合のみ）
api_key: ""

# デフォルトのキットID
# 登録済み: shodoshima-field-01 (処理区/常時冠水), shodoshima-field-02 (未処理区/冠水無し)
default_kit_id: "shodoshima-field-01"
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

## 評価基準

### 土壌水分の状態判定

画像解析時に拍照時刻と同じ時間帯の土壌水分を取得し、以下の基準で判定する。

| 状態 | 平均水分 (%) | 色 | 説明 |
|------|-------------|-----|------|
| **DRY** | < 30 | 赤 | 水分不足。灌水が必要 |
| **OPTIMAL** | 30 - 70 | 緑 | 適切な水分状態 |
| **WET** | > 70 | 黄 | 過湿。排水・通気を確認 |

### 健康リスク評価

土壌水分から算出するリスクレベル。視覚的解析（葉の色・シワ・巻き込み等）と組み合わせて総合判定する。

| リスク | 平均水分 (%) | 温度条件 | スコア | 緩和策 |
|--------|-------------|---------|--------|--------|
| **critical** | < 20 | — | 0.1 | 直ちに灌水。日陰への移動を検討 |
| **high** | 20-30 | — | 0.3 | 灌水計画の見直し |
| **high** | > 75 | — | 0.3 | 排水確認、灌水量の削減 |
| **moderate** | 30-40 | — | 0.6 | 状態の継続モニタリング |
| **moderate** | 65-75 | — | 0.7 | 灌水頻度の調整 |
| **normal** | 40-65 | — | 1.0 | この状態を維持 |

**温度による追加ペナルティ:**

| 条件 | スコア乗数 | 説明 |
|------|-----------|------|
| 気温 > 35°C | ×0.8 | 高温ストレス |
| 気温 < 5°C | ×0.7 | 低温ストレス |

### 総合スコアの算出

```
総合スコア = 視覚スコア × (1 - 土壌水分重み) + 土壌水分スコア × 土壌水分重み
```

- **視覚スコア**: 既存の健康評価（葉の色、シワ、巻き込み、樹冠密度等）
- **土壌水分スコア**: 上記リスクテーブルから算出
- **重み**: リスクレベルに応じて自動調整

| リスクレベル | 土壌水分重み | 視覚重み |
|-------------|------------|---------|
| normal | 10% | 90% |
| moderate | 30% | 70% |
| high | 30% | 70% |
| critical | 30% | 70% |

**例:**
- 視覚スコア=0.8, 土壌水分スコア=0.3 (high risk), 重み=30%
- 総合スコア = 0.8 × 0.7 + 0.3 × 0.3 = **0.65**

### 出力される評価結果

CLI/GUIの解析結果に以下のフィールドが追加される:

```json
{
  "health_assessment": {
    "visual_health_score": 0.800,      // 視覚的健康スコア
    "moisture_health_score": 1.000,     // 土壌水分スコア
    "moisture_weight": 0.10,            // 土壌水分の重み
    "combined_health_score": 0.820,     // 総合スコア
    "moisture_risk": "normal",          // リスクレベル
    "moisture_message": "適切な水分 (avg 52%)",  // メッセージ
    "flags": []                         // フラグ (soil_moisture_high等)
  },
  "soil_moisture": {
    "available": true,
    "status": "optimal",
    "average_percent": 52.0,
    "sensor1_percent": 50.0,
    "sensor2_percent": 54.0,
    "temperature": 25.0,
    "humidity": 60.0
  }
}
```

### フラグ一覧

| フラグ | 意味 | 対応 |
|--------|------|------|
| `soil_moisture_critical` | 深刻な水分不足 | 直ちに灌水 |
| `soil_moisture_high` | 水分不足/過湿のリスク | 灌水計画の見直し |
| `soil_moisture_moderate` | やや水分不足/過湿 | 状態の継続モニタリング |

### API エンドポイント

| エンドポイント | 説明 | パラメータ |
|---------------|------|-----------|
| `/api/sensor/latest` | 最新の測定値 | `kit_id` |
| `/api/sensor/history` | 過去の測定履歴 | `kit_id`, `hours`, `limit` |
| `/api/sensor/stats` | 統計情報 | `kit_id`, `hours` |
| `/api/sensor/calibration` | キャリブレーション値 | `kit_id` |

**使用例:**
```
https://soil-moisture-pages-ddl.pages.dev/api/sensor/latest?kit_id=shodoshima-field-01
https://soil-moisture-pages-ddl.pages.dev/api/sensor/history?kit_id=shodoshima-field-01&hours=24
https://soil-moisture-pages-ddl.pages.dev/api/sensor/stats?kit_id=shodoshima-field-01&hours=24
```

**登録済みキット:**
| キットID | 名前 | 説明 |
|---------|------|------|
| `shodoshima-field-01` | １ 処理区（常時冠水） | 常時灌水されている区画 |
| `shodoshima-field-02` | ２ 未処理区（冠水無し） | 灌水されていない区画 |

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
