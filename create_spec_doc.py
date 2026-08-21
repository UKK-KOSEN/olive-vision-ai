"""OliveVision AI 技術仕様書 DOCX生成"""
import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT

doc = Document()

# ── スタイル設定 ──
style = doc.styles["Normal"]
font = style.font
font.name = "Yu Gothic"
font.size = Pt(10.5)

for level in range(1, 4):
    hs = doc.styles[f"Heading {level}"]
    hs.font.color.rgb = RGBColor(0x1B, 0x5E, 0x20)
    hs.font.bold = True
    hs.font.size = Pt(18 - level * 2)

# ヘルパー
def add_code_block(text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(1)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    run.font.name = "Consolas"
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

def add_table(headers, rows, col_widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            for r in p.runs:
                r.bold = True
                r.font.size = Pt(9)
    for row_data in rows:
        row = t.add_row()
        for i, val in enumerate(row_data):
            cell = row.cells[i]
            cell.text = str(val)
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9)
    doc.add_paragraph()

# ============================================================
# タイトルページ
# ============================================================
doc.add_paragraph()
doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("OliveVision AI 技術仕様書")
r.font.size = Pt(28)
r.bold = True
r.font.color.rgb = RGBColor(0x1B, 0x5E, 0x20)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("AI搭載 オリーブ樹長期モニタリングシステム\nシステムアーキテクチャ・検出アルゴリズム・パラメータ仕様")
r.font.size = Pt(12)
r.font.color.rgb = RGBColor(0x61, 0x61, 0x61)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("バージョン: 1.0.0\n最終更新: 2026年8月17日\n対象: runtime.py / runtime.yaml / olivevision.py / テスト・ツール群")
r.font.size = Pt(10)
r.font.color.rgb = RGBColor(0x9E, 0x9E, 0x9E)

doc.add_page_break()

# ============================================================
# 目次
# ============================================================
doc.add_heading("目次", level=1)
toc_items = [
    "1. プロジェクト概要と依存関係",
    "2. ファイル構成と更新履歴",
    "3. システムアーキテクチャ",
    "4. src/runtime.py コア検出エンジン",
    "  4.1 Analyzer クラス",
    "  4.2 葉マスク構築 (_build_leaf_mask)",
    "  4.3 実マスク構築 (_build_fruit_mask)",
    "  4.4 ぼけ検出とアダプティブ前処理",
    "  4.5 シワ(褶皴)スコアリング",
    "  4.6 葉巻き込み(Curl)スコアリング",
    "  4.7 マルチスケール検出とマージ",
    "  4.8 輪郭フィルタリングと信頼度算出",
    "  4.9 Watershed接触分離",
    "  4.10 Store クラス (SQLite時系列DB)",
    "  4.11 VideoAnalyzer とオブジェクト追跡",
    "  4.12 ヘルストレンド分析",
    "5. config/runtime.yaml パラメータ仕様",
    "6. config/config.yaml レガシー設定",
    "7. olivevision.py CLI/GUI アーキテクチャ",
    "8. src/detection.py レガシー検出モジュール",
    "9. src/color_analysis.py 色解析モジュール",
    "10. src/feature_extraction.py 特徴量抽出モジュール",
    "11. tools/check_hough.py Hough円デバッグツール",
    "12. tools/check_cur.py シワ/巻き込みデバッグツール",
    "13. tests/test_runtime.py 回帰テスト",
    "14. 出力仕様 (JSON / SQLite / CSV)",
    "15. 依存関係と環境要件",
]
for item in toc_items:
    p = doc.add_paragraph(item)
    p.paragraph_format.space_after = Pt(2)

doc.add_page_break()

# ============================================================
# 1. プロジェクト概要
# ============================================================
doc.add_heading("1. プロジェクト概要と依存関係", level=1)

doc.add_heading("1.1 システム目的", level=2)
doc.add_paragraph(
    "OliveVision AI は、Raspberry Pi 4 上のカメラ模倣装置を用いて、"
    "農家の代わりにオリーブ樹を定期的に撮影し、AI画像解析で"
    "下記の農業指標を自動算出するシステムである。"
)
indicators = [
    "葉数・実数カウント",
    "葉面被覆率 (green_coverage %)",
    "実面被覆率 (fruit_cover_pct %)",
    "葉色ステージ (healthy_green / dark_green / yellow_green / yellow / brown / dead_brown)",
    "葉枯れ度合い (leaf_senescence 0-100)",
    "実熟度 (green / yellow_green / purple / black / transitioning)",
    "シワ(褶褶皺)検出 (smooth / slightly_wrinkled / wrinkled / heavily_wrinkled)",
    "葉巻き込み (flat / slight_curl / curled / heavily_curled)",
    "ぼけレベル (blur_level 0.0-1.0)",
    "ヘルストレンド (stable / maturing / declining / mixed / insufficient)",
]
for item in indicators:
    doc.add_paragraph(item, style="List Bullet")

doc.add_heading("1.2 依存関係", level=2)
doc.add_paragraph("本番ランタイム (requirements.txt):")
add_table(
    ["パッケージ", "バージョン", "用途"],
    [
        ["numpy", ">=1.23, <3", "配列計算・画像配列操作"],
        ["opencv-python-headless", ">=4.7, <5", "画像処理・検出・変換"],
        ["PyYAML", ">=6, <7", "runtime.yaml設定読み込み"],
    ]
)
doc.add_paragraph("ML研究用 (requirements-ml.txt) — Raspberry Pi 不要:")
add_table(
    ["パッケージ", "バージョン", "用途"],
    [
        ["lightgbm", "4.1.0", "Histogram-based GBDT 分類器"],
        ["pandas", "2.2.2", "時系列データ操作"],
        ["scikit-learn", "1.5.1", "交差検証・特徴量選択"],
        ["scikit-image", "0.23.2", "GLCM / LBP テクスチャ特徴"],
        ["matplotlib", "3.9.1", "グラフ・可視化"],
        ["openpyxl", "3.1.2", "Excel出力"],
        ["scipy", "1.14.0", "統計解析"],
    ]
)

# ============================================================
# 2. ファイル構成
# ============================================================
doc.add_page_break()
doc.add_heading("2. ファイル構成と更新履歴", level=1)

doc.add_heading("2.1 ディレクトリツリー", level=2)
add_code_block(
    "olive-p/\n"
    "├── src/\n"
    "│   ├── runtime.py          # コア検出エンジン (2,222行)\n"
    "│   ├── cli_ui.py           # ANSI CLI UI ヘルパー\n"
    "│   ├── detection.py        # レガシー検出モジュール\n"
    "│   ├── color_analysis.py   # 色解析モジュール\n"
    "│   ├── feature_extraction.py # 特徴量抽出モジュール\n"
    "│   ├── advanced_detection.py # マルチスケール検出\n"
    "│   ├── background_removal.py # 5方式背景除去\n"
    "│   ├── video_processor.py  # 動画処理\n"
    "│   ├── texture_analysis.py # GLCM/LBP\n"
    "│   └── optical_flow_analysis.py # オプティカルフロー\n"
    "├── config/\n"
    "│   ├── runtime.yaml        # 本番パラメータ\n"
    "│   └── config.yaml         # レガシー設定\n"
    "├── tools/\n"
    "│   ├── check_hough.py      # Hough円シグナルデバッグ\n"
    "│   └── check_cur.py        # シワ/巻き込みデバッグ\n"
    "├── tests/\n"
    "│   └── test_runtime.py     # オフライン回帰テスト\n"
    "├── data/database/\n"
    "│   ├── olivevision.db      # SQLite時系列DB\n"
    "│   └── gui_settings.json   # GUI設定\n"
    "├── outputs/observations/   # JSON出力\n"
    "├── olivevision.py          # CLI/GUIエントリポイント\n"
    "├── analyze.py              # レガシー画像/動画解析\n"
    "├── train.py                # LightGBM訓練\n"
    "├── predict.py              # 未来予測\n"
    "├── requirements.txt        # 本番依存\n"
    "├── requirements-ml.txt     # ML研究依存\n"
    "└── docs/\n"
    "    ├── API_REFERENCE.md\n"
    "    ├── OPERATIONS.md\n"
    "    └── USAGE_EXAMPLES.md"
)

doc.add_heading("2.2 最近更新ファイル (2026/08/17)", level=2)
add_table(
    ["ファイル", "最終更新", "変更内容"],
    [
        ["tools/check_hough.py", "12:27", "シグナルエビデンスの可視化・統計ツール追加"],
        ["src/runtime.py", "12:20", "blur-aware閾値、rescueロジック、シグナル閾値表示"],
        ["config/runtime.yaml", "12:19", "fruit_no_circle_min_area, signal_thresholds追加"],
        ["tools/check_cur.py", "12:17", "シワ/巻き込みのデバッグ表示拡充"],
        ["data/database/olivevision.db", "12:06", "observationsテーブル書き込み"],
        ["outputs/observations/*.json", "12:06", "観測JSON出力"],
        ["tests/test_runtime.py", "11:20", "回帰テスト7件追加"],
        ["olivevision.py", "11:24", "GUIタブ追加、パラメータスライダー拡充"],
    ]
)

# ============================================================
# 3. システムアーキテクチャ
# ============================================================
doc.add_page_break()
doc.add_heading("3. システムアーキテクチャ", level=1)

doc.add_heading("3.1 処理フロー概要", level=2)
add_code_block(
    "カメラ/画像ファイル\n"
    "       │\n"
    "       ▼\n"
    "┌──────────────────────────────────────────────────────────────┐\n"
    "│  olivevision.py  (CLI/GUI エントリポイント)                  │\n"
    "│  ├─ analyze: 画像/動画解析                                   │\n"
    "│  ├─ capture: カメラ1枚撮影                                  │\n"
    "│  ├─ monitor: 定期撮影 (sleep間隔)                           │\n"
    "│  ├─ status: 直近観測表示                                    │\n"
    "│  ├─ export: CSVエクスポート                                  │\n"
    "│  ├─ trend: ヘルストレンド                                    │\n"
    "│  └─ gui: Tkinter GUI                                       │\n"
    "└──────────────────────────────────────────────────────────────┘\n"
    "       │\n"
    "       ▼\n"
    "┌──────────────────────────────────────────────────────────────┐\n"
    "│  runtime.py Analyzer.analyze()                              │\n"
    "│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │\n"
    "│  │ 前処理       │→│ マスク生成     │→│ 輪郭検出+フィルタ  │  │\n"
    "│  │ resize       │  │ leaf_mask    │  │ _filter_contours  │  │\n"
    "│  │ blur_est     │  │ fruit_mask   │  │ watershed_split   │  │\n"
    "│  │ adaptive_pre │  │ (multi_sig)  │  │ multiscale_merge  │  │\n"
    "│  │ deblur       │  │ foreground   │  │ シグナル割り当て   │  │\n"
    "│  └─────────────┘  └──────────────┘  └───────────────────┘  │\n"
    "│       │                                                      │\n"
    "│       ▼                                                      │\n"
    "│  ┌──────────────────────────────────────────────────────┐   │\n"
    "│  │ 後処理                                               │   │\n"
    "│  │ - シワスコア (_compute_wrinkle_score)               │   │\n"
    "│  │ - 巻き込みスコア (_compute_leaf_curl_score)         │   │\n"
    "│  │ - アノテーション画像生成 (_annotate)                  │   │\n"
    "│  │ - pipeline_diagnostics (除外統計)                     │   │\n"
    "│  └──────────────────────────────────────────────────────┘   │\n"
    "└──────────────────────────────────────────────────────────────┘\n"
    "       │\n"
    "       ▼\n"
    "  Store.add() → SQLite + JSON保存"
)

doc.add_heading("3.2 クラス依存関係", level=2)
add_code_block(
    "olivevision.py\n"
    "  ├─ runtime.Analyzer          # 画像解析\n"
    "  ├─ runtime.Store              # DB保存\n"
    "  ├─ runtime.VideoAnalyzer      # 動画解析\n"
    "  └─ cli_ui.py                  # 表示ヘルパー\n"
    "\n"
    "runtime.py 内部クラス:\n"
    "  Analyzer\n"
    "    ├─ _build_leaf_mask()       # 葉マスク\n"
    "    ├─ _build_fruit_mask()      # 実マスク\n"
    "    ├─ _filter_contours()       # フィルタ\n"
    "    ├─ _watershed_split()       # 分離\n"
    "    ├─ _merge_multiscale()      # マージ\n"
    "    ├─ _compute_wrinkle_score() # シワ\n"
    "    ├─ _compute_leaf_curl_score() # 巻き込み\n"
    "    └─ _annotate()              # アノテーション\n"
    "  Store\n"
    "    ├─ add()                    # 観測保存\n"
    "    ├─ recent()                 # 直近取得\n"
    "    └─ export_csv()             # CSV出力\n"
    "  VideoAnalyzer\n"
    "    ├─ analyze_video()          # フレーム処理\n"
    "    ├─ _process_frame()         # フレーム解析\n"
    "    ├─ _build_summary()         # サマリー生成\n"
    "    └─ _CentroidTracker         # 重心追跡"
)

# ============================================================
# 4. src/runtime.py 詳細
# ============================================================
doc.add_page_break()
doc.add_heading("4. src/runtime.py コア検出エンジン (2,222行)", level=1)

doc.add_heading("4.1 Analyzer クラス", level=2)
doc.add_paragraph(
    "Analyzer は画像解析のメインパイプラインを実装する。"
    "detect_mode パラメータに応じて、5種類の前景除去方式を選択可能。"
)
doc.add_paragraph("detect_mode 選択肢:")
add_table(
    ["モード", "説明", "特徴"],
    [
        ["multi_signal", "マルチシグナル融合 (デフォルト)", " HSV+ExG+CGI+LAB+YCrCb の6カラースペースを融合。ML依存なし。"],
        ["kmeans", "K-meansクラスタリング", "3クラスタで背景分離。ML研究用。"],
        ["grabcut", "GrabCut前景抽出", "初期マスクが必要。精度高いが計算重い。"],
        ["bg_removal", "5方式背景除去", "adaptive/color/edge/depth/grabcut を自動選択。"],
        ["edge_flood", "Canny + FloodFill", "エッジベースの前景分割。"],
        ["adaptive", "適応的閾値", "Otsu + 大津法ベース。"],
    ]
)

doc.add_paragraph("Analyzer.analyze() の主要パラメータ:")
add_table(
    ["パラメータ", "型", "デフォルト", "説明"],
    [
        ["image_path", "str", "(必須)", "入力画像パス"],
        ["detect_mode", "str", "multi_signal", "検出モード"],
        ["annotate", "bool", "True", "アノテーション画像生成"],
        ["blur_aware", "bool", "True", "ぼけに応じた閾値調整"],
    ]
)

doc.add_heading("4.1.1 analyze() 処理パイプライン詳細", level=2)
steps = [
    ("Step 1: リサイズ", "max_width=1280 でアスペクト比保持リサイズ。超解像オプションあり。"),
    ("Step 2: ぼけ推定", "_estimate_blur: Laplacian(gray, CV_64F) の分散から blur_level(0-1) を算出。blur_raw >= 180 で鮮明。"),
    ("Step 3: ローカルシャープネス", "_local_sharpness_map: 48x48ブロックごとの Laplacian分散を [0,1] 正規化。混合フォーカス検出に使用。"),
    ("Step 4: アダプティブ前処理", "バイラテラルフィルタ → CLAHE → ガウシアン → 必要に応じアンシャープマスク。"),
    ("Step 5: 領域別デブラ", "_deblur_adaptive: sharp_map > 0.6 かつ < 0.3 の画素が一定割合以上の場合に実行。"),
    ("Step 6: 前景マスク生成", "detect_mode に応じて foreground マスクを生成。"),
    ("Step 7: 葉マスク", "_build_leaf_mask: 6カラースペース融合。"),
    ("Step 8: 実マスク", "_build_fruit_mask: 3色帯 + Hough円。"),
    ("Step 9: 接触分離", "_watershed_split: 個別blob面積を逆算。"),
    ("Step 10: 輪郭検出+フィルタ", "Leaf/ Fruit を個別にフィルタリング。"),
    ("Step 11: シグナル割り当て", "各実候補の yellow_green/ripe/dark/hough_circle 比率を記録。"),
    ("Step 12: アノテーション画像", "_annotate: エッジスナップ付きの可視化画像を生成。"),
]
for title, desc in steps:
    p = doc.add_paragraph()
    r = p.add_run(f"{title}: ")
    r.bold = True
    r.font.size = Pt(10)
    p.add_run(desc).font.size = Pt(10)

# ── 4.2 葉マスク ──
doc.add_heading("4.2 葉マスク構築 (_build_leaf_mask)", level=2)
doc.add_paragraph(
    "6つのカラースペースから同時に検証し、HSVを必須条件として融合する。"
    "ぼけレベルに応じて required_signals を緩和するアダプティブ機構を持つ。"
)

doc.add_heading("4.2.1 カラースペース定義", level=3)
add_table(
    ["カラースペース", "変換式/閾値", "検出対象"],
    [
        ["HSV", "Hue∈[30,95], Sat>=35, Val>=25", "緑色帯 (必須条件)"],
        ["Excess Green (ExG)", "(2G-R-B)/(R+G+B+1)*128+128", "植被指数"],
        ["CGI", "arctan2(G-R, G+R)", "葉緑素指標"],
        ["LAB a-channel", "a < 118", "緑色域 (赤が128より小さい)"],
        ["YCrCb", "Cr < 130", "緑色低彩度帯"],
    ]
)

doc.add_heading("4.2.2 融合ロジック", level=3)
add_code_block(
    "required_signals = spec['leaf_required_signals']  # default: 2\n"
    "relax = max(0.0, (blur_level - 0.5) * 2.0)  # ぼけ緩和係数\n"
    "sat_floor = int(max(25, spec['leaf_saturation_min'] - relax * 25))\n"
    "val_floor  = int(max(15, spec['leaf_value_min']  - relax * 25))\n"
    "\n"
    "hsv_mask = inRange(H, 30, 95) & inRange(S, sat_floor, 255) & inRange(V, val_floor, 255)\n"
    "signals = exg + cgi + lab + ycrcb  # 各画素の一致数 (0-4)\n"
    "multi_signal = inRange(signals, required_signals, 255)\n"
    "\n"
    "if blur_level >= 0.75:\n"
    "    required_signals = 1  # 高ぼけで緩和\n"
    "\n"
    "leaf_mask = hsv_mask & (multi_signal | vegetation_union)"
)

doc.add_heading("4.2.3 後処理", level=3)
steps_leaf = [
    "Morphological close: 楕円カーネル (size = blur_level で縮小)",
    "Morphological open: 同上",
    "暗画素抑制: V < 15 の画素を0に設定",
    "前景マスクとのAND制約",
    "_edge_refine_mask: Cannyエッジへ輪郭をスナップ (内側シフト→再抽出)",
]
for s in steps_leaf:
    doc.add_paragraph(s, style="List Bullet")

# ── 4.3 実マスク ──
doc.add_heading("4.3 実マスク構築 (_build_fruit_mask)", level=2)
doc.add_paragraph(
    "3色帯 (黄色緑/熟紫/暗熟) のOR統合 + Hough円検出の複合方式。"
    "Hough円に検出されなかったblobに対しては、自己証明rescueロジックが機能する。"
)

doc.add_heading("4.3.1 色帯定義", level=3)
add_table(
    ["色帯", "HSV Hue", "HSV Sat", "HSV Val", "LAB b", "追加条件"],
    [
        ["黄色緑", "[18, 45]", ">= 55", ">= 65", "b >= 145", "—"],
        ["熟紫", "[105, 179]", ">= 60", "[55, 220]", "—", "—"],
        ["暗熟", "[105, 175]", ">= 85", "[25, 55]", "—", "—"],
    ]
)

doc.add_heading("4.3.2 Hough円パラメータ", level=3)
add_table(
    ["パラメータ", "値", "説明"],
    [
        ["dp", "1.2", "解像度逆数"],
        ["minDist", "25", "円中心の最小距離 (px)"],
        ["param1", "80", "Cannyエッジの上位閾値"],
        ["param2", "40", "円検出の投票閾値"],
    ]
)

doc.add_heading("4.3.3 Hough円検証フロー", level=3)
add_code_block(
    "1. Hough円マスクと blob が IoU > 0.35 で重なる → circle_fruit = True\n"
    "2. 重複しない blob について rescue 検証:\n"
    "   - connectedComponentsWithStats で個別blobを分離\n"
    "   - area ∈ [fruit_no_circle_min_area=1400, 4000]\n"
    "   - circularity >= 0.65, solidity >= 0.88\n"
    "   - internal_texture (gray std) <= 45.0\n"
    "   - blur_level < 0.5 のみ有効 (高ぼけは偽阳性防止)\n"
    "3. rescue条件を全て満たす場合のみ fruit_mask に追加"
)

# ── 4.4 ぼけ検出 ──
doc.add_heading("4.4 ぼけ検出とアダプティブ前処理", level=2)

doc.add_heading("4.4.1 ぼけレベル算出", level=3)
add_code_block(
    "gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)\n"
    "blur_raw = cv2.Laplacian(gray, cv2.CV_64F).var()\n"
    "blur_level = min(1.0, max(0.0, (180.0 - blur_raw) / 160.0))\n"
    "\n"
    "# 基準:\n"
    "# blur_raw >= 180 → blur_level = 0.0 (鮮明)\n"
    "# blur_raw  = 100 → blur_level = 0.5 (ややぼけ)\n"
    "# blur_raw  = 20  → blur_level = 1.0 (非常にぼけ)"
)

doc.add_heading("4.4.2 ローカルシャープネスマップ", level=3)
add_code_block(
    "BLOCK = 48\n"
    "for each 48x48 block in gray:\n"
    "    sharpness_map[block] = Laplacian(block, CV_64F).var()\n"
    "sharpness_map = normalize(sharpness_map, 0, 1)  # [0,1]正規化\n"
    "\n"
    "_is_mixed_focus():\n"
    "    cv = std(sharpness_map) / mean(sharpness_map)  # 変動係数\n"
    "    return cv > 1.0  # ブロック間変動が大きい場合 true"
)

doc.add_heading("4.4.3 アダプティブ前処理パイプライン", level=3)
add_code_block(
    "1. バイラテラルフィルタ:\n"
    "   d=9, sigmaColor=75, sigmaSpace=75\n"
    "   → エッジ保持 + ノイズ除去\n"
    "\n"
    "2. LAB変換 → L チャンネルに CLAHE:\n"
    "   clipLimit=2.5, tileGridSize=(8,8)\n"
    "   → ローカルコントラスト強調\n"
    "\n"
    "3. ガウシアンブラー (k=5):\n"
    "   → 残存ノイズ平滑化\n"
    "\n"
    "4. blur_raw < 180 の場合にアンシャープマスク:\n"
    "   sigma=2.5, amount=1.8\n"
    "   sharpened = cv2.addWeighted(image, 1.8, gaussian, -0.8, 0)"
)

doc.add_heading("4.4.4 領域別デブラ (_deblur_adaptive)", level=3)
add_code_block(
    "実行条件:\n"
    "  sharp_map > 0.6 の画素が >= 15%\n"
    "  AND sharp_map < 0.3 の画素が >= 30%\n"
    "  AND not _is_uniform_blur()  # 全体ぼけはスキップ\n"
    "\n"
    "アプローチ:\n"
    "  strong = unsharp_mask(sigma=3.0, amount=1.8)  # 強いシャープニング\n"
    "  mild   = unsharp_mask(sigma=1.2, amount=0.6)  # 弱いシャープニング\n"
    "  weight = (1.0 - sharp_map)  # ぼけているほど strong を重視\n"
    "  weight = GaussianBlur(weight, sigma=4)  # 滑らかに補間\n"
    "  result = strong * weight + mild * (1 - weight)"
)

# ── 4.5 シワ ──
doc.add_heading("4.5 シワ(褶皴)スコアリング (_compute_wrinkle_score)", level=2)
doc.add_paragraph(
    "シワ = 実表面上の細長い高勾配リッジ。"
    "Sobel勾配 → Otsu閾値 → 4方向カーネルで細線化 → リッジ密度から0-1スコアを算出。"
)

doc.add_heading("4.5.1 計算ステップ", level=3)
add_code_block(
    "1. マスクを erosion で内部領域を抽出:\n"
    "   erosion_radius = max(5, int(min(h,w) * 0.25))\n"
    "   interior_mask = erode(mask, kernel=erosion_radius)\n"
    "\n"
    "2. Sobel勾配マップ:\n"
    "   gx = Sobel(gray, CV_64F, 1, 0, ksize=3)\n"
    "   gy = Sobel(gray, CV_64F, 0, 1, ksize=3)\n"
    "   mag = magnitude(gx, gy)\n"
    "\n"
    "3. 閾値設定:\n"
    "   otsu_thresh = threshold(mag, 0, 255, THRESH_BINARY + THRESH_OTSU)\n"
    "   ridge_thresh = max(otsu_thresh, mean(mag) * 1.4, 20.0)\n"
    "\n"
    "4. 4方向カーネルで morphological open/close:\n"
    "   kernels = [horizontal(7x3), vertical(3x7), diagonal_45, diagonal_135]\n"
    "   combined = OR(open(mag, k) for k in kernels)\n"
    "   thin = close(combined, small_kernel)  # 小さな隙間を埋める\n"
    "\n"
    "5. リッジ密度とスコア:\n"
    "   interior_count = countPixels(interior_mask)\n"
    "   thin_count = countPixels(thin & interior_mask)\n"
    "   density = thin_count / max(1, interior_count)\n"
    "   score = min(1.0, density * 3.0 + max(0, texture - 18.0) / 80.0)"
)

doc.add_heading("4.5.2 信頼性判定", level=3)
add_table(
    ["条件", "処理"],
    [
        ["interior_fraction < 0.30", "スコアをディスカウント (ノイズ多)"],
        ["area < 350px", "極端にディスカウント (小さな葉片がシワ誤判定)"],
        ["unreliable=True", "health verdict で信頼性が下がる"],
    ]
)

doc.add_heading("4.5.3 ラベルリング", level=3)
add_table(
    ["スコア範囲", "ラベル"],
    [
        ["< 0.25", "smooth"],
        ["0.25 - 0.45", "slightly_wrinkled"],
        ["0.45 - 0.70", "wrinkled"],
        [">= 0.70", "heavily_wrinkled"],
    ]
)

# ── 4.6 巻き込み ──
doc.add_heading("4.6 葉巻き込み(Curl)スコアリング (_compute_leaf_curl_score)", level=2)
doc.add_paragraph(
    "葉が内側へ巻き込む (巻き込み) は蒸散抑制のストレス応答。"
    "3つの形状ヒント (solidity_gap, defect_ratio, elongation) から 0-1 スコアを算出。"
)

doc.add_heading("4.6.1 計算式", level=3)
add_code_block(
    "solidity_gap   = 1.0 - solidity       # 0=凸, 1=非常に凹む\n"
    "defect_depths  = convexityDefects(hull)\n"
    "mean_defect    = mean(defect_depths[:, 0, 3]) / 256.0\n"
    "defect_ratio   = min(1.0, mean_defect / sqrt(area) * 0.15)\n"
    "elongation     = min(1.0, max(0, aspect - 1.5) / 5.0)\n"
    "\n"
    "curl_score = 0.50 * solidity_gap + 0.30 * defect_ratio + 0.20 * elongation"
)

doc.add_heading("4.6.2 ラベルリング", level=3)
add_table(
    ["スコア範囲", "ラベル"],
    [
        ["< 0.10", "flat"],
        ["0.10 - 0.25", "slight_curl"],
        ["0.25 - 0.50", "curled"],
        [">= 0.50", "heavily_curled"],
    ]
)

# ── 4.7 マルチスケール ──
doc.add_heading("4.7 マルチスケール検出とマージ", level=2)

doc.add_heading("4.7.1 マルチスケール検出", level=3)
doc.add_paragraph(
    "scales = [0.75, 1.0, 1.3] (runtime.yaml で設定可能)。"
    "各スケールで leaf_mask をリサイズ → 輪郭抽出 → 面積を逆スケールして統一。"
)

doc.add_heading("4.7.2 マージ (_merge_multiscale)", level=3)
doc.add_paragraph(
    "面積降順でソート → 各輪郭について IoU > 0.35 の重複を除去。"
    "大きいものから優先的に保持。"
)

doc.add_heading("4.7.3 大型コンポーネント分割 (_split_large_components)", level=3)
doc.add_paragraph(
    "connectedComponentsWithStats で個別コンポーネントを確認。"
    "area > leaf_max_area (30000px) の大型blob → watershed で分割。"
    "重なり合った葉の群体を個別葉に分解してカウント可能にする。"
)

# ── 4.8 フィルタ ──
doc.add_heading("4.8 輪郭フィルタリングと信頼度算出 (_filter_contours)", level=2)

doc.add_heading("4.8.1 葉フィルタ条件", level=3)
add_table(
    ["パラメータ", "最小値", "最大値", "runtime.yamlキー"],
    [
        ["area", "350", "30000", "leaf_min_area / leaf_max_area"],
        ["aspect", "1.0", "12.0", "leaf_min_aspect / leaf_max_aspect"],
        ["solidity", "0.58", "—", "leaf_min_solidity"],
        ["ellipse_axis_ratio", "—", "8.0", "leaf_max_ellipse_ratio"],
    ]
)

doc.add_heading("4.8.2 実フィルタ条件", level=3)
add_table(
    ["パラメータ", "最小値", "最大値", "runtime.yamlキー"],
    [
        ["area", "250", "18000", "fruit_min_area / fruit_max_area"],
        ["aspect", "0.45", "2.4", "fruit_min_aspect / fruit_max_aspect"],
        ["solidity", "0.72", "—", "fruit_min_solidity"],
        ["circularity", "0.50", "—", "fruit_min_circularity"],
        ["ellipse_axis_ratio", "—", "3.5", "fruit_max_ellipse_ratio"],
        ["internal_texture (std)", "—", "40.0", "fruit_max_internal_std"],
    ]
)

doc.add_heading("4.8.3 信頼度算出", level=3)
add_code_block(
    "base_w = min(1.0, area / 1800)  # 面積ベースの重み (小さいほど低信頼)\n"
    "shape_score = 0.3*circularity + 0.3*solidity + 0.2*aspect_norm + 0.2*ellipse_norm\n"
    "edge_weight = 0.45\n"
    "if blur_level >= 0.4:\n"
    "    edge_weight = max(0.25, 0.45 - blur_level * 0.25)  # ぼけで縮小\n"
    "confidence = base_w * shape_score + color_consistency * 0.25 + edge_density * edge_weight"
)

# ── 4.9 Watershed ──
doc.add_heading("4.9 Watershed接触分離 (_watershed_split)", level=2)
add_code_block(
    "mindist = spec['watershed_mindist']  # default: 20px\n"
    "\n"
    "for each blob with area > min_area:\n"
    "    M = moments(blob_contour)\n"
    "    center = (M['m10']/M['m00'], M['m01']/M['m00'])\n"
    "\n"
    "for each pair of blobs:\n"
    "    dist = euclidean(center_i, center_j)\n"
    "    if dist < mindist:\n"
    "        # 接触 → watershed で分離\n"
    "        markers = connectedComponents(mask)\n"
    "        watershed(gray, markers)\n"
    "        split_contours = find_contours(markers)\n"
    "        # 各分割結果の面積を逆算して元のblobと比較"
)

# ── 4.10 Store ──
doc.add_heading("4.10 Store クラス (SQLite時系列DB)", level=2)

doc.add_heading("4.10.1 テーブルスキーマ", level=3)
add_code_block(
    "CREATE TABLE observations (\n"
    "    id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
    "    observed_at TEXT NOT NULL,          -- ISO8601\n"
    "    source TEXT,                         -- 'camera' or file path\n"
    "    leaf_count INTEGER DEFAULT 0,\n"
    "    fruit_count INTEGER DEFAULT 0,\n"
    "    green_coverage REAL DEFAULT 0,\n"
    "    leaf_color_stage TEXT,\n"
    "    leaf_senescence REAL DEFAULT 0,\n"
    "    fruit_maturity TEXT,\n"
    "    fruit_maturity_breakdown TEXT,       -- JSON\n"
    "    wrinkled_fruit_count INTEGER DEFAULT 0,\n"
    "    fruit_wrinkle_summary TEXT,          -- JSON\n"
    "    leaf_curl_index REAL DEFAULT 0,\n"
    "    curled_leaf_pct REAL DEFAULT 0,\n"
    "    blur_score REAL DEFAULT 0,\n"
    "    blur_level REAL DEFAULT 0,\n"
    "    result_json TEXT,                    -- 全結果JSON\n"
    "    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n"
    ")"
)

doc.add_heading("4.10.2 主要メソッド", level=3)
add_table(
    ["メソッド", "引数", "説明"],
    [
        ["add()", "result: dict, source: str", "観測をDBに保存 + JSONファイル出力"],
        ["recent()", "limit: int = 20", "直近N件の観測を取得"],
        ["export_csv()", "out_path: str", "全観測をCSVにエクスポート"],
        ["get_all()", "—", "全観測をリストで取得"],
    ]
)

# ── 4.11 VideoAnalyzer ──
doc.add_heading("4.11 VideoAnalyzer とオブジェクト追跡", level=2)

doc.add_heading("4.11.1 _CentroidTracker", level=3)
add_code_block(
    "class _CentroidTracker:\n"
    "    max_age: int = 30  # フレーム未検出で削除\n"
    "\n"
    "    update(leaf_objects, fruit_objects) -> (leaves, fruits):\n"
    "        1. 各オブジェクトの重心 (center_x, center_y) を計算\n"
    "        2. 既存トラックとの距離行列 D[i,j] を構築\n"
    "        3. D を平坦化 → ソート (距離昇順)\n"
    "        4. D[i,j] <= 80px のペアをマッチング\n"
    "        5. マッチしなかった新規オブジェクトを新規トラックとして登録\n"
    "        6. age > max_age のトラックを削除\n"
    "        7. 各トラックに track_id, bbox, history を保持"
)

doc.add_heading("4.11.2 動画フレーム処理", level=3)
doc.add_paragraph(
    "analyze_video: 入力動画の各フレームを interval で間引き解析。"
    "アノテーション動画と timeline.json を出力。"
    "フレームカウンタとオーバーレイをアノテーション画像に描画。"
)

# ── 4.12 ヘルストレンド ──
doc.add_heading("4.12 ヘルストレンド分析 (analyze_health_trend)", level=2)

doc.add_heading("4.12.1 前処理", level=3)
steps_trend = [
    "重複観測の削除: (date, source, leaf_count, fruit_count, green_coverage) でユニーク化",
    "低品質除外: green_coverage < 10.0% の観測をスキップ",
    "日別集計: 各日付の最終観測を使用",
]
for s in steps_trend:
    doc.add_paragraph(s, style="List Bullet")

doc.add_heading("4.12.2 時系列スロープ算出", level=3)
add_code_block(
    "_linear_slope_per_day(dates, values) -> float:\n"
    "    x = [(d - dates[0]).total_seconds() / 86400 for d in dates]  # 日数\n"
    "    y = values\n"
    "    slope = (len(x) * sum(x*y) - sum(x)*sum(y)) / (len(x)*sum(x^2) - sum(x)^2)\n"
    "    return slope  # 日あたりの変化量"
)

doc.add_heading("4.12.3 実追跡とマッチング", level=3)
add_code_block(
    "match_radius = 60px  # 跨日マッチングの許容範囲\n"
    "\n"
    "for each previous_fruit:\n"
    "    find nearest current_fruit where:\n"
    "        euclidean(prev.center, curr.center) <= match_radius\n"
    "    if match found:\n"
    "        track_days += (curr_date - prev_date).days\n"
    "        curr.ripeness = curr.ripe_signal + curr.dark_signal\n"
    "        curr.dehydration = wrinkle_contrib*0.6 + shrink_contrib*0.4\n"
    "        if curr.ripeness > prev.ripeness: ripening=True\n"
    "        if curr.wrinkle > prev.wrinkle: wrinkling=True\n"
    "        if curr.area < prev.area * 0.85: deteriorating=True"
)

doc.add_heading("4.12.4 ヘルス判定ロジック", level=3)
add_table(
    ["判定", "条件"],
    [
        ["stable", "有意な変化なし"],
        ["maturing", "ripening フラグが追跡実の半数以上"],
        ["declining", "wrinkling or dehydration が追跡実の半数以上"],
        ["mixed", "フラグがあるが一方的でない"],
        ["insufficient", "追跡実が0個"],
    ]
)

# ============================================================
# 5. config/runtime.yaml
# ============================================================
doc.add_page_break()
doc.add_heading("5. config/runtime.yaml パラメータ仕様", level=1)

doc.add_heading("5.1 runtime セクション", level=2)
add_table(
    ["パラメータ", "型", "デフォルト", "説明"],
    [
        ["max_width", "int", "1280", "入力画像のリサイズ上限 (アスペクト比保持)"],
        ["jpeg_quality", "int", "90", "アノテーションJPEG保存品質"],
        ["camera_warmup_frames", "int", "8", "カメラ起動時のスキップフレーム数"],
    ]
)

doc.add_heading("5.2 detection セクション (葉)", level=2)
add_table(
    ["パラメータ", "型", "デフォルト", "説明"],
    [
        ["leaf_hue", "[int,int]", "[30, 95]", "HSV Hue帯 (緑色範囲)"],
        ["leaf_saturation_min", "int", "35", "彩度下限"],
        ["leaf_value_min", "int", "25", "明度下限"],
        ["leaf_min_area", "int", "350", "最小面積 (px)"],
        ["leaf_max_area", "int", "30000", "最大面積 (px)"],
        ["leaf_min_aspect", "float", "1.0", "最小アスペクト比"],
        ["leaf_max_aspect", "float", "12.0", "最大アスペクト比"],
        ["leaf_min_solidity", "float", "0.58", "凸包充填率の下限"],
        ["leaf_max_ellipse_ratio", "float", "8.0", "楕円軸比の上限"],
        ["excess_green_min", "int", "12", "ExG植被指数の閾値"],
        ["leaf_required_signals", "int", "2", "必須カラースペース一致数"],
        ["blur_relax_threshold", "float", "0.5", "ぼけ緩和開始のblur_level"],
    ]
)

doc.add_heading("5.3 detection セクション (実)", level=2)
add_table(
    ["パラメータ", "型", "デフォルト", "説明"],
    [
        ["fruit_hue_yellow", "[int,int]", "[18, 45]", "黄色緑帯 Hue"],
        ["fruit_hue_ripe", "[int,int]", "[105, 179]", "熟紫帯 Hue"],
        ["fruit_hue_dark", "[int,int]", "[105, 175]", "暗熟帯 Hue"],
        ["fruit_saturation_min", "int", "55", "彩度下限"],
        ["fruit_value_min", "int", "65", "明度下限"],
        ["fruit_lab_b_min", "float", "145", "LAB b-channel下限"],
        ["fruit_min_area", "int", "250", "最小面積 (px)"],
        ["fruit_max_area", "int", "18000", "最大面積 (px)"],
        ["fruit_min_circularity", "float", "0.50", "最小円形度"],
        ["fruit_min_solidity", "float", "0.72", "最小凸包充填率"],
        ["fruit_max_ellipse_ratio", "float", "3.5", "楕円軸比の上限"],
        ["fruit_max_internal_std", "float", "40.0", "内部テクスチャ上限"],
        ["fruit_no_circle_min_area", "int", "1400", "rescue最小面積"],
        ["fruit_dark_sat_min", "int", "85", "暗熟帯の彩度下限"],
        ["fruit_ripe_sat_min", "int", "60", "熟紫帯の彩度下限"],
    ]
)

doc.add_heading("5.4 detection セクション (シワ/検出モード)", level=2)
add_table(
    ["パラメータ", "型", "デフォルト", "説明"],
    [
        ["wrinkle_ridge_weight", "float", "3.0", "リッジ密度の重み"],
        ["wrinkle_texture_base", "float", "18.0", "テクスチャベース値"],
        ["wrinkle_scale", "float", "80.0", "テクスチャ正規化"],
        ["wrinkle_smooth_max", "float", "0.25", "smooth ラベル上限"],
        ["wrinkle_slightly_max", "float", "0.45", "slightly_wrinkled ラベル上限"],
        ["wrinkle_wrinkled_max", "float", "0.70", "wrinkled ラベル上限"],
        ["detect_mode", "str", "multi_signal", "検出モード (multi_signal|kmeans|grabcut|adaptive|...)"],
        ["multiscale_scales", "[float]", "[0.75, 1.0, 1.3]", "マルチスケール倍率"],
        ["watershed_mindist", "int", "20", "実分離の最小距離 (px)"],
        ["fg_blur_threshold", "float", "0.30", "前景除去で無効化するblur_level"],
    ]
)

# ============================================================
# 6. config/config.yaml (レガシー)
# ============================================================
doc.add_page_break()
doc.add_heading("6. config/config.yaml レガシー設定", level=1)
doc.add_paragraph(
    "レガシー設定ファイル。runtime.py は runtime.yaml を使用するため、"
    "本ファイルは互換性のために残存。"
)
add_table(
    ["セクション", "パラメータ", "値"],
    [
        ["preprocessing", "gaussian_blur_kernel", "5"],
        ["preprocessing", "clahe_clip_limit", "2.0"],
        ["preprocessing", "clahe_grid_size", "8"],
        ["preprocessing", "gamma_correction", "1.2"],
        ["leaf_detection", "hue_range", "[35, 95]"],
        ["leaf_detection", "min_area", "50"],
        ["leaf_detection", "circularity_threshold", "0.3"],
        ["leaf_detection", "solidity_threshold", "0.5"],
        ["fruit_detection", "hue_range", "[0, 180]"],
        ["fruit_detection", "min_area", "30"],
        ["fruit_detection", "circularity_threshold", "0.7"],
        ["machine_learning", "model_type", "lightgbm"],
        ["machine_learning", "n_estimators", "100"],
        ["database", "type", "sqlite"],
        ["database", "path", "data/database/olive_data.db"],
    ]
)

# ============================================================
# 7. olivevision.py
# ============================================================
doc.add_page_break()
doc.add_heading("7. olivevision.py CLI/GUI アーキテクチャ", level=1)

doc.add_heading("7.1 CLI コマンド", level=2)
add_table(
    ["コマンド", "引数", "説明"],
    [
        ["analyze", "image_or_video [--mode multi_signal]", "画像/動画解析 → アノテーション + JSON + SQLite"],
        ["capture", "[--interval N]", "カメラ1枚撮影 → 解析"],
        ["monitor", "--interval N [--count M]", "定期撮影・解析 (Ctrl+Cで停止)"],
        ["status", "[--limit N]", "SQLite直近観測を表示"],
        ["export", "--output out.csv", "SQLite → CSV エクスポート"],
        ["trend", "—", "ヘルストレンド分析レポート表示"],
        ["video", "video_path", "動画フレーム解析"],
        ["gui", "—", "Tkinter GUI 起動"],
    ]
)

doc.add_heading("7.2 GUI 構成 (Tkinter ダークテーマ)", level=2)
doc.add_paragraph("カラーパレット: Catppuccin Mocha")
add_table(
    ["用途", "色", "HEX"],
    [
        ["背景", "ダークグレー", "#1e1e2e"],
        ["アクセント", "ライトグリーン", "#a6e3a1"],
        ["テキスト", "ライトグレー", "#cdd6f4"],
        ["カード背景", "ミッドグレー", "#313244"],
    ]
)

doc.add_heading("7.2.1 ツールバー", level=3)
toolbar = [
    "Open Image: ファイルダイアログで画像選択 → 解析",
    "Capture: PiCamera2 で撮影 → 解析",
    "Open Video: 動画ファイル選択 → VideoAnalyzer でフレーム解析",
    "History: SQLite から直近の観測を読み込みツリー表示",
    "Trend: analyze_health_trend を呼び出し結果表示",
    "Settings: パラメータ調整ダイアログ",
]
for item in toolbar:
    doc.add_paragraph(item, style="List Bullet")

doc.add_heading("7.2.2 タブ構成", level=3)
tabs = [
    "Log: 解析ログ (stdout/stderrキャプチャ)",
    "History: 観測履歴ツリー",
    "Hue Histogram: HSV Hueヒストグラム表示",
    "Timeline: 時系列グラフ",
    "Why?: 検出結果の根拠表示",
    "Diagnostics: パイプライン診断情報",
]
for item in tabs:
    doc.add_paragraph(item, style="List Bullet")

doc.add_heading("7.2.3 パラメータスライダー", level=3)
doc.add_paragraph(
    "GUI 上で以下のパラメータをスライダーで調整可能 (runtime.yaml に即反映):"
)
sliders = [
    "葉 Hue Min / Max (30-95)",
    "葉 Saturation Min (15-100)",
    "葉 Value Min (10-80)",
    "実 Hue Yellow Min / Max",
    "実 Hue Ripe Min / Max",
    "実 Saturation Min",
    "検出モード選択 (multi_signal / kmeans / grabcut / adaptive)",
    "マルチスケールスケール [0.5-2.0]",
    "シワ閾値スライダー",
]
for s in sliders:
    doc.add_paragraph(s, style="List Bullet")

doc.add_heading("7.2.4 統計カード", level=3)
doc.add_paragraph(
    "解析結果を大文字テキストで表示: LEAVES / FRUITS / GREEN%"
)

# ============================================================
# 8. detection.py
# ============================================================
doc.add_page_break()
doc.add_heading("8. src/detection.py レガシー検出モジュール", level=1)
doc.add_paragraph(
    "config.yaml の HSV パラメータを使用するレガシー検出モジュール。"
    "runtime.py の _build_leaf_mask / _build_fruit_mask とは独立実装。"
)

doc.add_heading("8.1 ObjectDetector クラス", level=2)
add_table(
    ["メソッド", "引数", "返り値", "説明"],
    [
        ["detect_leaves()", "image (BGR)", "(List[Dict], image)", "HSV → マスク → モルフォロジー → 輪郭 → フィルタ"],
        ["detect_fruits()", "image (BGR)", "(List[Dict], image)", "緑+黄+紫マスク → 統合 → フィルタ"],
    ]
)

doc.add_heading("8.2 葉検出フロー", level=3)
add_code_block(
    "1. cv2.cvtColor(image, COLOR_BGR2HSV)\n"
    "2. create_mask_from_hsv_range(hsv, hue_range, sat_range, val_range)\n"
    "3. apply_morphology(mask, 'open', 5) → apply_morphology(mask, 'close', 5)\n"
    "4. find_contours(mask)\n"
    "5. for contour in contours:\n"
    "       props = get_contour_properties(contour)\n"
    "       if min_area <= area <= max_area\n"
    "          and circularity >= 0.3\n"
    "          and solidity >= 0.5:\n"
    "           leaves.append(props)"
)

# ============================================================
# 9. color_analysis.py
# ============================================================
doc.add_page_break()
doc.add_heading("9. src/color_analysis.py 色解析モジュール", level=1)

doc.add_heading("9.1 ColorAnalyzer クラス", level=2)
add_table(
    ["メソッド", "説明"],
    [
        ["analyze_leaf_color()", "葉マスク領域のHSV平均を算出 → 色ステージ分類"],
        ["analyze_fruit_color()", "実マスク領域のHSV平均を算出 → 熟度分類"],
        ["_classify_leaf_color()", "Hue値から6段階の色ステージを分類"],
        ["_classify_fruit_maturity()", "Hue値から5段階の熟度を分類"],
        ["_calculate_senescence_degree()", "枯れ度合い (0-100) を算出"],
    ]
)

doc.add_heading("9.2 葉色分類ロジック", level=3)
add_code_block(
    "Hue (OpenCV 0-180):\n"
    "  35-65: healthy_green\n"
    "  25-35: dark_green\n"
    "  65-80: yellow_green\n"
    "  80-95: yellow\n"
    "  95-120: brown\n"
    "  120+: dead_brown"
)

doc.add_heading("9.3 実熟度分類ロジック", level=3)
add_code_block(
    "Hue (OpenCV 0-180):\n"
    "  25-50: green\n"
    "  50-70: yellow_green\n"
    "  70-110: transitioning\n"
    "  110-150: purple\n"
    "  150+: black"
)

# ============================================================
# 10. feature_extraction.py
# ============================================================
doc.add_page_break()
doc.add_heading("10. src/feature_extraction.py 特徴量抽出モジュール", level=1)

doc.add_heading("10.1 FeatureExtractor クラス", level=2)
doc.add_paragraph(
    "画像から時空間特徴量を抽出し、ML学習用データセットを構築する。"
)

doc.add_heading("10.2 抽出特徴量", level=2)
add_table(
    ["カテゴリ", "特徴量", "数"],
    [
        ["時間的", "hour, day_of_week, month, season", "4"],
        ["葉", "leaf_count, avg_area, max_area, min_area, std_area, density, ...", "~15"],
        ["実", "fruit_count, avg_area, max_area, min_area, std_area, maturity, ...", "~12"],
        ["色", "leaf_mean_hue/sat/val, fruit_mean_hue/sat/val, color_stage, ...", "~10"],
        ["画像全体", "brightness, contrast, blur_score, edge_density, ...", "~8"],
    ]
)

# ============================================================
# 11. check_hough.py
# ============================================================
doc.add_page_break()
doc.add_heading("11. tools/check_hough.py Hough円シグナルデバッグツール", level=1)
doc.add_paragraph(
    "Hough円検出のシグナルエビデンスを可視化・統計するデバッグツール。"
    "runtime.py の _build_fruit_mask 内のシグナル検証ロジックを独立実行し、"
    "各色帯の画素数・割合・Hough円の検出状況を出力する。"
)

doc.add_heading("11.1 使い方", level=2)
add_code_block(
    "python tools/check_hough.py <image_path> [--config config/runtime.yaml]"
)

doc.add_heading("11.2 出力内容", level=2)
outputs = [
    "各色帯 (yellow_green / ripe / dark) の画素数と全体比",
    "Hough円の検出数と検出パラメータ",
    "各blobの signal_ratios (yellow_green_ratio, ripe_ratio, dark_ratio, hough_ratio)",
    "rescue ロジックの実行結果 (rescue試行数、成功数)",
    "前処理前のblur_levelとぼけ緩和係数",
]
for item in outputs:
    doc.add_paragraph(item, style="List Bullet")

# ============================================================
# 12. check_cur.py
# ============================================================
doc.add_heading("12. tools/check_cur.py シワ/巻き込みデバッグツール", level=1)
doc.add_paragraph(
    "シワ (wrinkle) と葉巻き込み (leaf curl) のスコアリング結果を"
    "デバッグ表示するツール。"
)

doc.add_heading("12.1 使い方", level=2)
add_code_block(
    "python tools/check_cur.py <image_path> [--config config/runtime.yaml]"
)

doc.add_heading("12.2 出力内容", level=2)
outputs_cur = [
    "各オブジェクトの wrinkle_score, wrinkle_label, unreliable フラグ",
    "各オブジェクトの curl_score, curl_label",
    "リッジ検出の詳細 (interior_count, thin_count, density, threshold)",
    "convexity defect の詳細 (num_defects, mean_defect_depth)",
    "信頼性判定の根拠 (interior_fraction, area)",
]
for item in outputs_cur:
    doc.add_paragraph(item, style="List Bullet")

# ============================================================
# 13. テスト
# ============================================================
doc.add_page_break()
doc.add_heading("13. tests/test_runtime.py 回帰テスト", level=1)

doc.add_heading("13.1 テスト一覧 (7件)", level=2)
add_table(
    ["テスト名", "概要", "検証内容"],
    [
        ["test_analysis_persists_result_and_export",
         "黒画像に緑矩形 → 解析 → DB保存",
         "green_coverage > 0, CSVエクスポート成功"],
        ["test_colour_and_shape_filters_reject_non_olive_regions",
         "茶色土壌 + 肌色 → 検出なし",
         "leaf_count == 0, fruit_count == 0"],
        ["test_result_includes_maturity_breakdown_and_cover",
         "緑実 + 黄緑実 → 熟度分析",
         "maturity_breakdown 合計 == fruit_count, 各fruit_objectにmaturity存在"],
        ["test_watershed_splits_touching_fruits",
         "2つの接触する円 → watershed分割",
         ">= 2個に分割"],
        ["test_health_trend_tracks_fruits_and_detects_changes",
         "3日間シーケンス → ヘルストレンド",
         "ripening, wrinkling, deteriorating フラグ検出, 重複観測collapsed"],
        ["test_gt_6497_fruit_detection_recall",
         "IMG_6497.jpg + GT JSON → 検出率",
         "recall == 1.0, precision == 1.0"],
    ]
)

doc.add_heading("13.2 テスト環境", level=2)
doc.add_paragraph(
    "テストは ML依存 (lightgbm, pandas 等) を使用しない。"
    "runtime.py のみで完結するオフラインテスト。"
    "PiCamera2 不要。OpenCV headless で実行可能。"
)

# ============================================================
# 14. 出力仕様
# ============================================================
doc.add_page_break()
doc.add_heading("14. 出力仕様", level=1)

doc.add_heading("14.1 JSON出力 (observations/)", level=2)
doc.add_paragraph(
    "各解析結果は outputs/observations/ に JSON ファイルとして保存される。"
    "ファイル名: observation_{timestamp}_{id}.json"
)

doc.add_heading("14.1.1 トップレベルフィールド", level=3)
add_table(
    ["フィールド", "型", "説明"],
    [
        ["observed_at", "str", "ISO8601タイムスタンプ"],
        ["leaf_count", "int", "検出葉数"],
        ["fruit_count", "int", "検出実数"],
        ["green_coverage", "float", "葉面被覆率 (%)"],
        ["fruit_cover_pct", "float", "実面被覆率 (%)"],
        ["leaf_color_stage", "str", "葉色ステージ (6段階)"],
        ["leaf_senescence", "float", "枯れ度合い (0-100)"],
        ["fruit_maturity", "str", "実熟度 (5段階)"],
        ["fruit_maturity_breakdown", "dict", "熟度内訳 {green: n, purple: n, ...}"],
        ["wrinkled_fruit_count", "int", "シワ検出実数"],
        ["fruit_wrinkle_summary", "dict", "シワ内訳 {smooth: n, wrinkled: n, ...}"],
        ["leaf_curl_index", "float", "平均巻き込み指数 (0-1)"],
        ["curled_leaf_pct", "float", "巻き込み葉割合 (%)"],
        ["blur_score", "float", "Laplacian分散"],
        ["blur_level", "float", "正規化ぼけレベル (0-1)"],
        ["pipeline_diagnostics", "dict", "パイプライン診断情報"],
    ]
)

doc.add_heading("14.1.2 leaf_objects[] フィールド", level=3)
add_table(
    ["フィールド", "型", "説明"],
    [
        ["confidence", "float", "検出信頼度"],
        ["area", "int", "面積 (px)"],
        ["aspect", "float", "アスペクト比"],
        ["solidity", "float", "凸包充填率"],
        ["ellipse_axis_ratio", "float", "楕円軸比"],
        ["num_defects", "int", "convexity defect数"],
        ["mean_defect_depth", "float", "平均defect深度"],
        ["curl_score", "float", "巻き込みスコア (0-1)"],
        ["curl_label", "str", "巻き込みラベル"],
        ["color_consistency", "float", "色の一貫性"],
        ["edge_density", "float", "エッジ密度"],
        ["blur_level", "float", "ローカルぼけレベル"],
        ["center_x", "float", "重心X座標"],
        ["center_y", "float", "重心Y座標"],
        ["track_id", "int", "追跡ID"],
    ]
)

doc.add_heading("14.1.3 fruit_objects[] フィールド", level=3)
add_table(
    ["フィールド", "型", "説明"],
    [
        ["confidence", "float", "検出信頼度"],
        ["area", "int", "面積 (px)"],
        ["circularity", "float", "円形度"],
        ["hue", "float", "平均Hue"],
        ["saturation", "float", "平均彩度"],
        ["lab_b", "float", "LAB b-channel"],
        ["maturity", "str", "熟度ラベル"],
        ["wrinkle_score", "float", "シワスコア (0-1)"],
        ["wrinkle_label", "str", "シワラベル"],
        ["wrinkle_reliable", "bool", "シワ検出の信頼性"],
        ["ridge_density", "float", "リッジ密度"],
        ["detect_evidence", "list", "検出シグナル名のリスト"],
        ["signal_ratios", "dict", "各シグナルの割合"],
        ["edge_touch", "bool", "画像エッジに接触"],
        ["low_signal", "bool", "シグナル強度が弱い"],
    ]
)

doc.add_heading("14.1.4 pipeline_diagnostics フィールド", level=3)
add_code_block(
    '{\n'
    '  "leaves": {\n'
    '    "candidates": 57,       # フィルタ前候補数\n'
    '    "accepted": 2,          # フィルタ通過数\n'
    '    "rejected_by": {\n'
    '      "area": 52,           # 面積フィルタで除外\n'
    '      "aspect": 3           # アスペクト比フィルタで除外\n'
    '    }\n'
    '  },\n'
    '  "fruits": {\n'
    '    "candidates": 3,\n'
    '    "accepted": 1,\n'
    '    "rejected_by": {\n'
    '      "circularity": 2\n'
    '    }\n'
    '  },\n'
    '  "signals": {\n'
    '    "yellow_green_pixels": 1234,\n'
    '    "ripe_pixels": 567,\n'
    '    "dark_pixels": 89,\n'
    '    "hough_circles": 2\n'
    '  },\n'
    '  "signal_thresholds": {\n'
    '    "yellow_green": 0.35,\n'
    '    "ripe": 0.25,\n'
    '    "dark": 0.25,\n'
    '    "hough_circle": 0.20\n'
    '  }\n'
    '}'
)

doc.add_heading("14.2 SQLite テーブル (observations)", level=2)
doc.add_paragraph("Store.add() で observations テーブルに1行追加。result_json に全結果JSONを格納。")

doc.add_heading("14.3 アノテーション画像", level=2)
doc.add_paragraph(
    "アノテーション画像は JPEG で保存。エッジスナップ付きの可視化。"
    "マスクオーバーレイ、重心マーカー、ラベルテキストを描画。"
)

# ============================================================
# 15. 依存関係
# ============================================================
doc.add_page_break()
doc.add_heading("15. 依存関係と環境要件", level=1)

doc.add_heading("15.1 ランタイム環境", level=2)
add_table(
    ["項目", "要件"],
    [
        ["OS", "Raspberry Pi OS (Bookworm) または同等Linux"],
        ["Python", "3.11以上"],
        ["ハードウェア", "Raspberry Pi 4 (4GB以上推奨)"],
        ["カメラ", "PiCamera2 対応カメラモジュール"],
        ["ML不要", "本番ランタイムは numpy + opencv + pyyaml のみ"],
    ]
)

doc.add_heading("15.2 開発/研究環境", level=2)
add_table(
    ["項目", "要件"],
    [
        ["Python", "3.11以上"],
        ["追加依存", "lightgbm, pandas, scikit-learn, scikit-image, matplotlib"],
        ["GPU", "任意 (LightGBMはCPU学習)"],
        ["テストデータ", "tests/test_data/ (GT JSON + テスト画像)"],
    ]
)

doc.add_heading("15.3 ファイルサイズ・行数", level=2)
add_table(
    ["ファイル", "行数", "サイズ"],
    [
        ["src/runtime.py", "2,222", "約120KB"],
        ["olivevision.py", "約800", "約40KB"],
        ["config/runtime.yaml", "約200", "約6KB"],
        ["tests/test_runtime.py", "約400", "約20KB"],
        ["tools/check_hough.py", "約300", "約15KB"],
        ["tools/check_cur.py", "約200", "約10KB"],
    ]
)

# ============================================================
# 保存
# ============================================================
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "OliveVision_AI_技術仕様書.docx")
doc.save(output_path)
print(f"saved: {output_path}")
