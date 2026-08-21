"""OliveVision AI - 技術仕様書 (DOCX) と 技術解説 (PowerPoint) を同時に生成"""
import os, sys
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
# DOCX 生成
# ═══════════════════════════════════════════════════════════════
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

doc = Document()
style = doc.styles["Normal"]
style.font.name = "Yu Gothic"
style.font.size = Pt(10)
for lv in range(1, 4):
    hs = doc.styles[f"Heading {lv}"]
    hs.font.color.rgb = RGBColor(0x1B, 0x5E, 0x20)
    hs.font.bold = True
    hs.font.size = Pt(16 - lv * 2)

def code_block(text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.8)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(text)
    r.font.name = "Consolas"
    r.font.size = Pt(8.5)
    r.font.color.rgb = RGBColor(0x21, 0x21, 0x21)

def tbl(headers, rows):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]; c.text = h
        for p in c.paragraphs:
            for r in p.runs: r.bold = True; r.font.size = Pt(8.5)
    for rd in rows:
        row = t.add_row()
        for i, v in enumerate(rd):
            c = row.cells[i]; c.text = str(v)
            for p in c.paragraphs:
                for r in p.runs: r.font.size = Pt(8.5)
    doc.add_paragraph()

def add_page():
    doc.add_page_break()

# ═══════════════════════════════════════════════════════════════
# DOCX: タイトル
# ═══════════════════════════════════════════════════════════════
doc.add_paragraph(); doc.add_paragraph()
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("OliveVision AI 技術仕様書"); r.font.size = Pt(26); r.bold = True; r.font.color.rgb = RGBColor(0x1B,0x5E,0x20)
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("AI搭載 オリーブ樹長期モニタリングシステム\nアーキテクチャ / 検出アルゴリズム / パラメータ仕様"); r.font.size = Pt(11); r.font.color.rgb = RGBColor(0x75,0x75,0x75)
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("バージョン: 3.0 | 最終更新: 2026年8月17日 | 対象: src/runtime.py (2,800行)"); r.font.size = Pt(9); r.font.color.rgb = RGBColor(0x9E,0x9E,0x9E)
add_page()

# ═══════════════════════════════════════════════════════════════
# 1. プロジェクト概要
# ═══════════════════════════════════════════════════════════════
doc.add_heading("1. プロジェクト概要", level=1)
doc.add_heading("1.1 システム目的", level=2)
doc.add_paragraph(
    "OliveVision AI は Raspberry Pi 4 上のカメラ模倣装置を用いて、"
    "農家の代わりにオリーブ樹を定期的に撮影し、AI画像解析で農業指標を自動算出する。"
    "本番ランタイムは ML/クラウド依存なしで常時動作する。")
for item in [
    "葉数・実数カウント / 葉面被覆率 (green_coverage %) / 実面被覆率 (fruit_cover_pct %)",
    "葉色ステージ (healthy_green / dark_green / yellow_green / yellow / brown / dead_brown)",
    "葉枯れ度合い (leaf_senescence 0-100)",
    "実熟度 (green / yellow_green / purple / black / transitioning)",
    "シワ検出 (smooth / slightly_wrinkled / wrinkled / heavily_wrinkled)",
    "葉巻き込み (flat / slight_curl / curled / heavily_curled)",
    "ぼけレベル (blur_level 0.0-1.0) / QRコード木番号検出",
    "ヘルストレンド (stable / maturing / declining / mixed / insufficient)",
]: doc.add_paragraph(item, style="List Bullet")

doc.add_heading("1.2 依存関係", level=2)
doc.add_paragraph("本番ランタイム (requirements.txt):")
tbl(["パッケージ","バージョン","用途"],[
    ["numpy",">=1.23, <3","配列計算・画像配列操作"],
    ["opencv-python-headless",">=4.7, <5","画像処理・検出・変換"],
    ["PyYAML",">=6, <7","runtime.yaml 読み込み"],
])
doc.add_paragraph("ML研究用 (requirements-ml.txt):")
tbl(["パッケージ","バージョン","用途"],[
    ["lightgbm","4.1.0","Histogram-based GBDT"],
    ["pandas","2.2.2","時系列データ操作"],
    ["scikit-learn","1.5.1","交差検証・特徴量選択"],
    ["scikit-image","0.23.2","GLCM / LBP"],
    ["matplotlib","3.9.1","グラフ・可視化"],
    ["openpyxl","3.1.2","Excel出力"],
    ["scipy","1.14.0","統計解析"],
])

# ═══════════════════════════════════════════════════════════════
# 2. ファイル構成
# ═══════════════════════════════════════════════════════════════
add_page()
doc.add_heading("2. ファイル構成と更新履歴", level=1)
code_block(
    "olive-p/\n"
    "  src/runtime.py              # コア検出エンジン (2,800行)\n"
    "  src/cli_ui.py               # ANSI CLI UI ヘルパー\n"
    "  src/detection.py            # レガシー検出モジュール (238行)\n"
    "  src/color_analysis.py       # 色解析モジュール (228行)\n"
    "  src/feature_extraction.py   # 特徴量抽出モジュール (345行)\n"
    "  src/advanced_detection.py   # マルチスケール検出\n"
    "  src/background_removal.py   # 5方式背景除去\n"
    "  src/video_processor.py      # 動画処理\n"
    "  src/texture_analysis.py     # GLCM/LBP\n"
    "  src/optical_flow_analysis.py # オプティカルフロー\n"
    "  config/runtime.yaml         # 本番パラメータ (132行)\n"
    "  config/config.yaml          # レガシー設定\n"
    "  tools/check_hough.py        # Hough円デバッグ\n"
    "  tools/check_cur.py          # シワ/巻き込みデバッグ\n"
    "  tests/test_runtime.py       # 回帰テスト (7件)\n"
    "  data/database/olivevision.db # SQLite DB\n"
    "  outputs/observations/       # JSON出力\n"
    "  olivevision.py              # CLI/GUIエントリポイント\n"
    "  analyze.py / train.py / predict.py\n"
    "  requirements.txt / requirements-ml.txt")

doc.add_heading("2.1 最近更新ファイル (2026/08/17)", level=2)
tbl(["ファイル","更新時刻","変更内容"],[
    ["tools/check_hough.py","12:27","シグナルエビデンス可視化ツール"],
    ["src/runtime.py","12:20","blur-aware 閾値, rescue ロジック, analysis/stress/trend セクション追加"],
    ["config/runtime.yaml","12:19","fruit_no_circle_min_area, curl/wrinkle/trend パラメータ追加"],
    ["tools/check_cur.py","12:17","シワ/巻き込みデバッグ拡充"],
    ["tests/test_runtime.py","11:20","回帰テスト 7 件"],
    ["olivevision.py","11:24","GUI タブ追加, スライダー拡充"],
])

# ═══════════════════════════════════════════════════════════════
# 3. モジュール構成
# ═══════════════════════════════════════════════════════════════
add_page()
doc.add_heading("3. src/runtime.py モジュール構成 (2,800行)", level=1)
doc.add_heading("3.1 グローバル定数 (runtime.py:20-138)", level=2)
doc.add_paragraph(
    "DEFAULTS 辞書は 5 セクション (runtime, detection, analysis, stress, trend, video) を含む。"
    "load_runtime_config() (runtime.py:163) が yaml 内容で上書きする。")
tbl(["セクション","主なキー","行"],[
    ["runtime","max_width=1280, jpeg_quality=90, camera_warmup_frames=8","21"],
    ["detection","leaf_hue=[30,95], leaf_saturation_min=35, leaf_value_min=25","22-76"],
    ["detection","leaf_min_area=350, leaf_max_area=30000, leaf_min_aspect=1.0, leaf_max_aspect=12.0","24-25"],
    ["detection","leaf_min_solidity=0.58, excess_green_min=12","26,38"],
    ["detection","fruit_hue_yellow=[18,45], fruit_hue_ripe=[105,179]","27"],
    ["detection","fruit_saturation_min=55, fruit_value_min=65, fruit_lab_b_min=145","28-29"],
    ["detection","fruit_min_area=250, fruit_max_area=18000, fruit_min_aspect=0.45, fruit_max_aspect=2.4","29"],
    ["detection","fruit_min_circularity=0.50, fruit_min_solidity=0.72, fruit_max_ellipse_ratio=3.5","30-32"],
    ["detection","fruit_no_circle_min_area=1400, fruit_no_circle_min_circularity=0.65, fruit_no_circle_min_solidity=0.88","33-35"],
    ["detection","fruit_no_circle_max_std=45.0, fruit_no_circle_max_area=4000","36-37"],
    ["detection","multiscale_scales=[0.75,1.0,1.3], watershed_mindist=20","40-41"],
    ["detection","detect_mode=multi_signal, edge_refine=True","44-45"],
    ["detection","wrinkle_ridge_weight=3.0, wrinkle_texture_base=18.0, wrinkle_texture_scale=80.0","51-53"],
    ["detection","wrinkle_smooth_max=0.25, wrinkle_slightly_wrinkled_max=0.45, wrinkle_wrinkled_max=0.70","54-56"],
    ["detection","wrinkle_erosion_scale=0.25, wrinkle_min_interior_pixels=60, wrinkle_min_valid_pixels=30","57-58"],
    ["detection","curl_weight_solidity=0.30, curl_weight_defect=0.30, curl_weight_elongation=0.40","65-67"],
    ["detection","curl_defect_radius_scale=0.5, curl_elongation_baseline=1.2, curl_elongation_scale=4.0","68-70"],
    ["detection","curl_threshold_flat=0.10, curl_threshold_slight=0.25, curl_threshold_curled=0.50","71-73"],
    ["detection","qr_detection=True","75"],
    ["analysis","leaf_hue_green_low=35, leaf_hue_green_high=85, leaf_hue_yellow_high=95, leaf_hue_dark_high=150","79-82"],
    ["analysis","leaf_size_small_max=2000, leaf_size_medium_max=6000","84-85"],
    ["analysis","drooping_angle_low=45, drooping_angle_high=135","87-88"],
    ["analysis","leaf_low_confidence_threshold=0.5, fruit_low_confidence_threshold=0.5","90,94"],
    ["stress","weight_curl=0.5, weight_wrinkle=0.5","98-99"],
    ["stress","green_coverage_max=50.0, curl_saturation=3.0, wrinkle_saturation=2.0","101-103"],
    ["stress","weight_green=0.30, weight_health_curl=0.25, weight_health_wrinkle=0.25, weight_saturation=0.20","106-109"],
    ["trend","min_green_coverage=10.0","112"],
    ["trend","dehydration_wrinkle_scale=0.5, dehydration_wrinkle_weight=0.6, dehydration_shrink_weight=0.4","114-116"],
    ["trend","flag_ripeness_threshold=0.15, flag_wrinkle_threshold=0.2, flag_dehydration_threshold=0.30","118-120"],
    ["trend","note_ripeness_rise=0.05, note_wrinkle_increase=0.05, note_green_decline=-2.0","122-124"],
    ["trend","note_fruit_count_decline=-0.5, note_leaf_count_decline=-1.0, dropout_green_tolerance=1.0","126-129"],
    ["video","frame_interval=10, max_frames=500, output_fps=5, track_max_age=30, track_iou_threshold=0.3","131-137"],
])

doc.add_paragraph("FRUIT_SIGNAL_THRESHOLDS (runtime.py:144-149):")
tbl(["キー","閾値","意味"],[
    ["yellow_green","0.35","黄色緑シグナルが blob 面積の 35% 以上"],
    ["ripe","0.25","熟紫シグナルが blob 面積の 25% 以上"],
    ["dark","0.25","暗熟シグナルが blob 面積の 25% 以上"],
    ["hough_circle","0.20","Hough 円マスクが blob 面積の 20% 以上"],
])

# ═══════════════════════════════════════════════════════════════
# 4. Store クラス
# ═══════════════════════════════════════════════════════════════
add_page()
doc.add_heading("4. Store クラス (runtime.py:213-344)", level=1)
doc.add_heading("4.1 テーブルスキーマ (runtime.py:219-224)", level=2)
code_block(
    "CREATE TABLE IF NOT EXISTS observations (\n"
    "    id              INTEGER PRIMARY KEY,\n"
    "    observed_at     TEXT NOT NULL,\n"
    "    source          TEXT NOT NULL,\n"
    "    image_path      TEXT,\n"
    "    leaf_count      INTEGER NOT NULL,\n"
    "    fruit_count     INTEGER NOT NULL,\n"
    "    green_coverage  REAL NOT NULL,\n"
    "    image_width     INTEGER NOT NULL,\n"
    "    image_height    INTEGER NOT NULL,\n"
    "    result_json     TEXT NOT NULL,\n"
    "    tree_id         TEXT\n"
    ")")
doc.add_paragraph(
    "tree_id カラムは ALTER TABLE でマイグレーション (runtime.py:226-229)。"
    "add() は _sanitize_for_json() (runtime.py:238-251) で ndarray を安全にシリアライズする。")

doc.add_heading("4.2 メソッド", level=2)
tbl(["メソッド","行","説明"],[
    ["__init__","213","DB + テーブル自動生成 + tree_id マイグレーション"],
    ["add","253","_sanitize_for_json -> INSERT INTO observations"],
    ["recent","271","直近 N 件を降順取得"],
    ["recent_by_tree","281","tree_id でフィルタして取得"],
    ["recent_by_source","292","source プレフィックス + オプション tree_id でフィルタ"],
    ["tree_ids","312"," DISTINCT tree_id のリストを取得"],
    ["export_csv","323","全観測を CSV エクスポート (件数返却)"],
    ["clear","335","全削除 (削除件数返却)"],
])

# ═══════════════════════════════════════════════════════════════
# 5. ヘルパー関数
# ═══════════════════════════════════════════════════════════════
add_page()
doc.add_heading("5. ヘルパー関数群", level=1)
tbl(["関数","行","説明"],[
    ["now()","159","ISO8601 タイムスタンプ生成"],
    ["load_runtime_config()","163","DEFAULTS + yaml 上書き"],
    ["build_logger()","176","logging.Logger 生成"],
    ["_detect_qr_tree_id()","191","QR コードから第 N 試験樹を抽出"],
    ["_ripeness_ratio()","347","ripe + dark の signal_ratios 合計"],
    ["_linear_slope_per_day()","356","最小二乗法で日あたりスロープ"],
    ["analyze_health_trend()","378","ヘルストレンド分析レポート生成"],
    ["_estimate_blur()","615","Laplacian 分散 (鮮明=高, ぼけ=低)"],
    ["_local_sharpness_map()","621","48x48 ブロックの Laplacian 分散 [0,1]"],
    ["_unsharp_mask()","639","アンシャープマスク"],
    ["_is_mixed_focus()","650","混合フォーカス検出 (変動係数 > 1.0)"],
    ["_deblur_adaptive()","674","領域別デブラ (sharp/blur 重み付け)"],
    ["_adaptive_preprocess()","697","バイラテラル + CLAHE + ガウシアン + シャープニング"],
    ["_compute_vegetation_index()","717","ExG: (2G-R-B)/(R+G+B+1)*128+128"],
    ["_compute_cgi()","723","arctan2(G-R, G+R)"],
    ["_compute_edge_density()","729","mask 境界と画像エッジの重なり率"],
    ["_compute_internal_texture()","741","mask 内部の gray std (erode 後)"],
    ["_compute_wrinkle_score()","755","Sobel -> Otsu -> 4方向リッジ -> 0-1 スコア"],
    ["_grabcut_refine()","851","GrabCut でマスク境界を洗練"],
    ["_edge_refine_mask()","882","Canny エッジへマスクをスナップ"],
    ["_adaptive_canny()","895","Otsu 自動閾値で Canny"],
    ["_snap_contour_to_edges()","908","輪郭頂点を勾配中心に最大 4px 移動"],
    ["_compute_shape_descriptors()","953","area, circularity, solidity, hu_moments, defects"],
    ["_compute_leaf_curl_score()","1003","solidity_gap + defect_ratio + elongation"],
    ["_curl_label()","1031","0-1 -> flat/slight_curl/curled/heavily_curled"],
    ["_watershed_split()","1044","距离変換 watershed で接触 blob を分離"],
    ["_hough_circles_fruit()","1068","Hough 円検出 (dp=1.2, param1=80, param2=40)"],
    ["_fg_mask_kmeans()","1092","K-means で前景クラスタ抽出"],
    ["_fg_mask_grabcut()","1119","GrabCut で前景抽出"],
    ["_fg_mask_hsv_bgsub()","1146","HSV 背景除去"],
    ["_fg_mask_edge_flood()","1165","Canny + FloodFill 前景"],
    ["_adaptive_fg_mask()","1189","画像特性で最適前景方式を選択"],
    ["_CentroidTracker","1210","重心ベースマルチオブジェクト追跡"],
    ["save_observation()","(後半)","ndarray 除外 -> JSON/DB 保存"],
    ["explain_detection()","(後半)","検出結果のテキスト説明を構築"],
    ["capture_camera()","(後半)","USB/PiCamera2 からフレーム取得"],
])

# ═══════════════════════════════════════════════════════════════
# 6. analyze() パイプライン
# ═══════════════════════════════════════════════════════════════
add_page()
doc.add_heading("6. Analyzer.analyze() パイプライン (runtime.py:1662-2099)", level=1)
doc.add_heading("6.1 シグネチャ", level=2)
code_block(
    "class Analyzer:\n"
    "    def __init__(self, config: dict):\n"
    "    def analyze(self, image: np.ndarray, source: str,\n"
    "                image_path: Optional[str] = None) -> Tuple[dict, np.ndarray]:")
doc.add_heading("6.2 処理ステップ", level=2)
tbl(["行","処理","詳細"],[
    ["1664","_resize","max_width=1280 でアスペクト比保持リサイズ"],
    ["1665","blur_raw","Laplacian 分散を算出"],
    ["1669","blur_level","min(1.0, max(0.0, (180-blur_raw)/160))"],
    ["1673","edge_refine","blur_level < 0.75 のみ有効"],
    ["1674","sharp_map","_local_sharpness_map(image, block=48)"],
    ["1677-1678","uniform_blurry","blur_level>0.15 AND blur_raw>=5.0 AND NOT mixed_focus"],
    ["1679-1680","processed","_adaptive_preprocess(image, blur_k, deblur=uniform_blurry)"],
    ["1683","processed","_deblur_adaptive(processed, blur_level, sharp_map)"],
    ["1684-1685","hsv, lab","BGR->HSV, BGR->LAB 変換"],
    ["1688-1699","fg_mask","detect_mode に応じて前景マスク生成 (6方式)"],
    ["1701-1706","leaf_mask","_build_leaf_mask -> _split_large_components"],
    ["1707-1718","leaf_contours","multiscale_scales で各倍率の輪郭を _merge_multiscale"],
    ["1719-1720","leaf_descs","_filter_contours(leaf_contours, 'leaf', ...)"],
    ["1724-1734","葉色","各葉の HSV Hue 平均 -> _classify_leaf_color"],
    ["1737-1742","巻き込み","各葉の _compute_leaf_curl_score -> curl_label"],
    ["1745-1746","fruit_mask","_build_fruit_mask -> _watershed_split"],
    ["1751-1752","fruit_descs","_filter_contours(all_fruit_contours, 'fruit', ...)"],
    ["1759-1762","fruit_det_mask","accept された実輪郭を個別に描画したマスク"],
    ["1766-1783","シグナル再生成","ev_yellow/ripe/dark/circles (エビデンス割り当て用)"],
    ["1785-1836","各実のループ","色, 熟度, シワ, signal_ratios, detect_evidence, low_signal"],
    ["1840-1847","leaf_roughness","全葉マスクの Laplacian std"],
    ["1849-1881","アノテーション","エッジスナップ付きの可視化画像を生成"],
    ["1897-2099","result 辞書","全フィールドを構築して返す"],
])

doc.add_heading("6.3 result 辞書の主なフィールド (runtime.py:1897-2099)", level=2)
tbl(["フィールド","型","算出元"],[
    ["observed_at","str","now() (ISO8601)"],
    ["leaf_count","int","len(leaf_descs)"],
    ["fruit_count","int","len(fruit_descs)"],
    ["green_coverage","float","leaf_mask nonzero / total * 100"],
    ["leaf_color_stage","str","_classify_leaf_color(avg_lh)"],
    ["leaf_senescence","float","_calculate_senescence(avg_lh, avg_ls)"],
    ["leaf_avg_hue / leaf_avg_saturation / leaf_avg_area","float","各葉の平均"],
    ["leaf_confidence","float","全葉の confidence 平均"],
    ["fruit_maturity","str","_classify_fruit_maturity(avg_fh)"],
    ["fruit_maturity_breakdown","dict","熟度ラベルごとのカウント"],
    ["wrinkled_fruit_count","int","wrinkle_score >= 0.45 の実数"],
    ["fruit_wrinkle_summary","dict","smooth/slightly/wrinkled/heavily のカウント"],
    ["fruit_avg_hue / fruit_avg_area / fruit_confidence","float","各実の平均"],
    ["fruit_cover_pct","float","fruit_det_mask nonzero / total * 100"],
    ["leaf_roughness","float","全葉マスクの Laplacian std"],
    ["leaf_curl_index","float","全葉の curl_score 平均"],
    ["curled_leaf_pct","float","curl_score >= 0.25 の葉割合 (%)"],
    ["detect_mode","str","spec['detect_mode']"],
    ["blur_score","float","blur_raw (Laplacian 分散)"],
    ["blur_level","float","正規化ぼけレベル (0-1)"],
    ["leaf_objects","list","各葉の全情報 (confidence, area, aspect, solidity, curl_score, ...)"],
    ["fruit_objects","list","各実の全情報 (confidence, area, maturity, wrinkle_score, signal_ratios, ...)"],
    ["fruit_thresholds","dict","フィルタ閾値のスナップショット"],
    ["signal_thresholds","dict","FRUIT_SIGNAL_THRESHOLDS のコピー"],
    ["pipeline_diagnostics","dict","除外統計・シグナルカバレッジ"],
])

# ═══════════════════════════════════════════════════════════════
# 7. 葉マスク
# ═══════════════════════════════════════════════════════════════
add_page()
doc.add_heading("7. _build_leaf_mask (runtime.py:1347-1415)", level=1)
doc.add_paragraph("6 カラースペースから同時に検証し、HSV を必須条件として融合する。")
doc.add_heading("7.1 カラースペース定義", level=2)
tbl(["#","カラースペース","変換式/閾値","行"],[
    ["1","HSV","Hue=[30,95], Sat>=sat_floor, Val>=25","1357-1359"],
    ["2","Excess Green","(2G-R-B)/(R+G+B+1)*128+128 >= 12","1361-1362"],
    ["3","CGI","arctan2(G-R, G+R) >= 165","1364-1365"],
    ["4","LAB a-channel","a < 118","1367"],
    ["5","YCrCb","Cr < 130","1369-1370"],
])
doc.add_heading("7.2 融合ロジック", level=2)
code_block(
    "relax = max(0.0, (blur_level - 0.5) * 2.0)          # 0..1 for blur>=0.5\n"
    "sat_floor = int(max(25, leaf_saturation_min - relax * 25))\n"
    "required_signals = 2 if blur_level < 0.75 else 1     # 1374\n"
    "signals = exg + cgi + lab + ycrcb                     # 1377-1381\n"
    "multi_signal = cv2.inRange(signals, required_signals, 255)\n"
    "combined = HSV_mask AND (multi_signal OR vegetation_union)  # 1384")
doc.add_heading("7.3 後処理", level=2)
tbl(["ステップ","行","詳細"],[
    ["Dilate + Open + Close","1389-1391","楕円カーネル edge_k (blur で縮小)"],
    ["Scale-aware Open + Close","1395-1398","mk_size = min(7, min(h,w)/150)"],
    ["暗画素抑制","1401","V >= 15 の画素のみ残す"],
    ["前景制約","1405-1406","fg_mask がある場合 AND"],
    ["Edge refine","1409-1410","blur_level < 0.75 のみ"],
    ["Hole fill","1413-1414","MORPH_CLOSE (7x7 楕円)"],
])

# ═══════════════════════════════════════════════════════════════
# 8. 実マスク
# ═══════════════════════════════════════════════════════════════
add_page()
doc.add_heading("8. _build_fruit_mask (runtime.py:1417-1499)", level=1)
doc.add_heading("8.1 色帯定義", level=2)
tbl(["色帯","HSV Hue","Sat","Val","LAB b","行"],[
    ["黄色緑","[18, 45]",">= sat_floor",">= 65",">= lab_b_floor","1427-1431"],
    ["熟紫","[105, 179]",">= max(60, ripe_sat)","[55, 220]","-","1433-1434"],
    ["暗熟","[105, 175]",">= 85-relax*20","[25, 55]","-","1435"],
])
doc.add_paragraph(
    "sat_floor = max(50, fruit_saturation_min - relax*25)    # 1425\n"
    "lab_b_floor = max(110, fruit_lab_b_min - relax*30)      # 1426\n"
    "ripe_sat = 110 - int(relax * 25)                        # 1432")
doc.add_heading("8.2 Hough 円検証", level=2)
code_block(
    "circles = _hough_circles_fruit(gray, dp=1.2, minDist=25, param1=80, param2=40)\n"
    "if circles:\n"
    "    circle_fruit = fruit AND circle_mask               # 1454\n"
    "    near_circle = fruit AND dilated_circles            # 1456\n"
    "    if blur_level < 0.5:                               # 1459\n"
    "        # rescue: far_fruit から条件を満たす blob を救済\n"
    "        # area [1400, 4000], circ >= 0.65 OR solid >= 0.88, gstd <= 45.0\n"
    "        fruit = near_circle OR se                       # 1481\n"
    "    else: fruit = near_circle                          # 1483")

# ═══════════════════════════════════════════════════════════════
# 9. フィルタ
# ═══════════════════════════════════════════════════════════════
add_page()
doc.add_heading("9. _filter_contours (runtime.py:1501-1610)", level=1)
doc.add_heading("9.1 葉フィルタ", level=2)
tbl(["パラメータ","条件","値"],[
    ["area","leaf_min_area <= area <= leaf_max_area","350-30000"],
    ["aspect","leaf_min_aspect <= aspect <= leaf_max_aspect","1.0-12.0"],
    ["solidity","solidity >= leaf_min_solidity",">= 0.58"],
])
doc.add_heading("9.2 実フィルタ", level=2)
tbl(["パラメータ","条件","値"],[
    ["area","fruit_min_area <= area <= fruit_max_area","250-18000"],
    ["aspect","fruit_min_aspect <= aspect <= fruit_max_aspect","0.45-2.4"],
    ["solidity","solidity >= fruit_min_solidity",">= 0.72"],
    ["circularity","circularity >= fruit_min_circularity",">= 0.50"],
    ["ellipse_axis_ratio","<= fruit_max_ellipse_ratio","<= 3.5"],
    ["internal_texture","std <= fruit_max_internal_std","<= 40.0"],
])
doc.add_heading("9.3 信頼度算出 (_detection_confidence, runtime.py:1332-1343)", level=2)
code_block(
    "circ_s = min(1.0, circularity / 0.8)\n"
    "sol_s  = min(1.0, solidity / 0.9)\n"
    "# 葉: ar_s = 1.0 - min(0.5, abs(aspect-2.5)/4.0)\n"
    "#      base = circ_s*0.25 + sol_s*0.35 + ar_s*0.25\n"
    "# 実: ar_s = 1.0 - min(0.5, abs(aspect-1.2)/2.0)\n"
    "#      base = circ_s*0.35 + sol_s*0.35 + ar_s*0.15\n"
    "# 後処理:\n"
    "# 葉: conf = base*(0.50+obj_blur*0.10) + color_consistency*0.25 + edge_density*edge_weight\n"
    "# 実: conf = base*(0.45+obj_blur*0.10) + color_consistency*0.25 + edge_density*min(ew+0.05, 0.30)\n"
    "# edge_weight = max(0.0, 0.25 - obj_blur * 0.15)")

# ═══════════════════════════════════════════════════════════════
# 10. シワ/巻き込み
# ═══════════════════════════════════════════════════════════════
add_page()
doc.add_heading("10. シワ/巻き込みスコアリング", level=1)
doc.add_heading("10.1 _compute_wrinkle_score (runtime.py:755-848)", level=2)
code_block(
    "# 1. インテリアマスク生成\n"
    "radius = max(1.0, (area / pi) ** 0.5)\n"
    "ksize = max(3, min(11, int(2 * radius * erosion_scale)))  # erosion_scale=0.25\n"
    "interior = erode(mask, kernel=ksize)\n"
    "interior_fraction = interior_px / area\n"
    "# interior_px < 60 で unreliable=True, full mask にフォールバック\n"
    "\n"
    "# 2. Sobel 勾配\n"
    "gx = Sobel(gray, CV_32F, 1, 0, ksize=3)\n"
    "gy = Sobel(gray, CV_32F, 0, 1, ksize=3)\n"
    "mag = magnitude(gx, gy)\n"
    "\n"
    "# 3. 閾値\n"
    "otsu_thr = Otsu(mag)\n"
    "thr = max(otsu_thr, mean*1.4, 20.0)  # ridge_mean_multiplier=1.4, ridge_min_threshold=20.0\n"
    "\n"
    "# 4. 4方向カーネル (1x7, 7x1, diag, fliplr(diag))\n"
    "thin = max(open(ridge,k)|close(ridge,k) for k in line_kernels)\n"
    "\n"
    "# 5. スコア\n"
    "density = thin_count / interior_count\n"
    "texture = std(gray[interior > 0])\n"
    "score = min(1.0, density*ridge_weight + max(0,texture-texture_base)/texture_scale)\n"
    "\n"
    "# 6. ディスカウント (interior_fraction < 0.30 OR area < 350)\n"
    "if area < 350: discount = min(1.0, area/350 * interior_fraction/0.30)\n"
    "else:          discount = min(1.0, interior_fraction / 0.30)\n"
    "score *= discount")
tbl(["スコア範囲","ラベル"],[
    ["< 0.25","smooth"],
    ["0.25 - 0.45","slightly_wrinkled"],
    ["0.45 - 0.70","wrinkled"],
    [">= 0.70","heavily_wrinkled"],
])

doc.add_heading("10.2 _compute_leaf_curl_score (runtime.py:1003-1028)", level=2)
code_block(
    "solidity_gap = 1.0 - solidity\n"
    "defect_ratio = min(1.0, defect_depth / radius * curl_defect_radius_scale)\n"
    "elongation = min(1.0, max(0.0, aspect - curl_elongation_baseline) / curl_elongation_scale)\n"
    "score = ws*solidity_gap + wd*defect_ratio + we*elongation\n"
    "# ws=0.30, wd=0.30, we=0.40\n"
    "# curl_defect_radius_scale=0.5, curl_elongation_baseline=1.2, curl_elongation_scale=4.0")
tbl(["スコア範囲","ラベル"],[
    ["< 0.10","flat"],
    ["0.10 - 0.25","slight_curl"],
    ["0.25 - 0.50","curled"],
    [">= 0.50","heavily_curled"],
])

# ═══════════════════════════════════════════════════════════════
# 11. 追跡
# ═══════════════════════════════════════════════════════════════
add_page()
doc.add_heading("11. _CentroidTracker (runtime.py:1210-1282)", level=1)
doc.add_paragraph("重心ベースのマルチオブジェクト追跡。葉と実で個別インスタンスを使用。")
code_block(
    "class _CentroidTracker:\n"
    "    max_age: int = 30\n"
    "    def update(detections: List[Tuple[int,int,int,int]]) -> Dict[int, Tuple]:\n"
    "        # 1. 入力 bbox から重心を算出                      # 1229-1231\n"
    "        # 2. 既存トラックとの距離行列 D[i,j] を構築         # 1246-1249\n"
    "        # 3. D を平坦化 -> min(axis=1) でソート            # 1251-1252\n"
    "        # 4. D[row,col] <= 80px のペアをマッチング         # 1259\n"
    "        # 5. マッチしなかった新規 -> 新規登録              # 1276-1280\n"
    "        # 6. age > max_age のトラックを削除                # 1271-1274")

# ═══════════════════════════════════════════════════════════════
# 12. ヘルストレンド
# ═══════════════════════════════════════════════════════════════
add_page()
doc.add_heading("12. analyze_health_trend (runtime.py:378-608)", level=1)
doc.add_heading("12.1 前処理", level=2)
tbl(["行","処理"],[
    ["415-417","observed_at でソート"],
    ["422-427","green_coverage < min_green_coverage (10.0%) を除外"],
    ["429-437","重複観測の削除: (date, source, leaf_count, fruit_count, round(green,2))"],
])
doc.add_heading("12.2 時系列スロープ (runtime.py:356-375)", level=2)
code_block(
    "xs = [(d - start).total_seconds() / 3600.0 for d in dates]  # 時間 (hour)\n"
    "denom = n*sum(x^2) - sum(x)^2\n"
    "slope_per_hour = (n*sum(x*y) - sum(x)*sum(y)) / denom\n"
    "return slope_per_hour * 24.0  # 日あたりの変化量")
doc.add_heading("12.3 実追跡とフラグ (runtime.py:472-542)", level=2)
code_block(
    "# 跨日マッチング (match_radius=60px)\n"
    "d_rip = rip_last - rip_first   # flag_ripeness_threshold=0.15\n"
    "d_wrk = wrk_last - wrk_first   # flag_wrinkle_threshold=0.2\n"
    "shrink = area_last / area_first\n"
    "dehydration = wrk_contribution*0.6 + shrink_contribution*0.4\n"
    "# flag_dehydration_threshold=0.30\n"
    "# d_rip>=0.15 AND d_wrk>=0.2 -> \"deteriorating\"")
doc.add_heading("12.4 ヘルス判定 (runtime.py:578-588)", level=2)
tbl(["判定","条件"],[
    ["insufficient","追跡実が 0 個"],
    ["declining","wrinkling >= max(1, n/2) OR dehydrating >= max(1, n/2)"],
    ["maturing","ripening >= max(1, n/2)"],
    ["mixed","任意のフラグがあるが一方的でない"],
    ["stable","フラグなし"],
])

# ═══════════════════════════════════════════════════════════════
# 13. config/runtime.yaml
# ═══════════════════════════════════════════════════════════════
add_page()
doc.add_heading("13. config/runtime.yaml パラメータ仕様 (132行)", level=1)
doc.add_paragraph(
    "load_runtime_config() (runtime.py:163-173) が DEFAULTS を基盤として yaml で上書き。"
    "yaml にないキーは DEFAULTS の値がそのまま使われる。")
tbl(["セクション","主なパラメータ"],[
    ["runtime (3キー)","max_width=1280, jpeg_quality=90, camera_warmup_frames=8"],
    ["detection (45+キー)","leaf/fruit/wrinkle/curl/multiscale/watershed/fg/detect_mode"],
    ["analysis (10キー)","leaf_hue_bands, leaf/fruit_size_buckets, drooping_angles, confidence_thresholds"],
    ["stress (7キー)","weight_curl/wrinkle, green_coverage_max, saturation thresholds, weights"],
    ["trend (14キー)","min_green_coverage, dehydration_*, flag_*, note_*, dropout_green_tolerance"],
    ["video (5キー)","frame_interval=10, max_frames=500, output_fps=5, track_max_age=30, track_iou_threshold=0.3"],
])

# ═══════════════════════════════════════════════════════════════
# 14. olivevision.py
# ═══════════════════════════════════════════════════════════════
add_page()
doc.add_heading("14. olivevision.py CLI/GUI アーキテクチャ", level=1)
doc.add_heading("14.1 CLI コマンド", level=2)
tbl(["コマンド","説明"],[
    ["analyze","画像/動画解析 -> アノテーション + JSON + SQLite"],
    ["capture","カメラ 1 枚撮影 -> 解析"],
    ["monitor","定期撮影・解析 (Ctrl+C で停止)"],
    ["status","SQLite 直近観測を表示"],
    ["export","SQLite -> CSV エクスポート"],
    ["trend","ヘルストレンド分析レポート表示"],
    ["video","動画フレーム解析"],
    ["gui","Tkinter GUI 起動"],
])
doc.add_heading("14.2 GUI 構成", level=2)
doc.add_paragraph(
    "カラーパレット: Catppuccin Mocha (#1e1e2e / #a6e3a1 / #cdd6f4 / #313244)\n"
    "ツールバー: Open Image / Capture / Open Video / History / Trend / Settings\n"
    "タブ: Log / History / Hue Histogram / Timeline / Why? / Diagnostics\n"
    "パラメータスライダー: 葉 Hue Min/Max, Sat/Val Min, 実 Hue Min/Max\n"
    "検出モード選択: multi_signal / kmeans / grabcut / adaptive\n"
    "統計カード: LEAVES / FRUITS / GREEN% を大文字テキストで表示")

# ═══════════════════════════════════════════════════════════════
# 15. 出力仕様
# ═══════════════════════════════════════════════════════════════
add_page()
doc.add_heading("15. 出力仕様", level=1)
doc.add_heading("15.1 leaf_objects[] のフィールド", level=2)
tbl(["フィールド","型","説明"],[
    ["confidence","float","検出信頼度"],
    ["area","int","面積 (px)"],
    ["aspect","float","アスペクト比"],
    ["solidity","float","凸包充填率"],
    ["ellipse_axis_ratio","float","楕円軸比"],
    ["num_defects","int","convexity defect 数"],
    ["mean_defect_depth","float","平均 defect 深度"],
    ["curl_score","float","巻き込みスコア (0-1)"],
    ["curl_label","str","flat/slight_curl/curled/heavily_curled"],
    ["color_consistency","float","1.0 - min(1.0, hue_std/50.0)"],
    ["edge_density","float","mask 境界と画像エッジの重なり率"],
    ["blur_level","float","ローカルぼけレベル"],
    ["center_x / center_y","float","重心座標"],
])
doc.add_heading("15.2 fruit_objects[] のフィールド", level=2)
tbl(["フィールド","型","説明"],[
    ["confidence","float","検出信頼度"],
    ["area","int","面積 (px)"],
    ["circularity","float","円形度"],
    ["solidity","float","凸包充填率"],
    ["ellipse_axis_ratio","float","楕円軸比"],
    ["hue / saturation / lab_b","float","平均色"],
    ["maturity","str","green/yellow_green/purple/black/transitioning"],
    ["wrinkle_score","float","シワスコア (0-1)"],
    ["wrinkle_label","str","smooth/slightly_wrinkled/wrinkled/heavily_wrinkled"],
    ["wrinkle_reliable","bool","シワ検出の信頼性"],
    ["ridge_density","float","リッジ密度"],
    ["detect_evidence","list","検出シグナル名のリスト"],
    ["signal_ratios","dict","各シグナルの overlap ratio"],
    ["edge_touch","bool","画像エッジに接触"],
    ["low_signal","bool","シグナル強度が弱い"],
    ["center_x / center_y","float","重心座標"],
])

# ═══════════════════════════════════════════════════════════════
# 16. テスト
# ═══════════════════════════════════════════════════════════════
add_page()
doc.add_heading("16. tests/test_runtime.py 回帰テスト (7件)", level=1)
tbl(["テスト名","概要","検証内容"],[
    ["test_analysis_persists_result_and_export","黒画像に緑矩形 -> 解析 -> DB 保存","green_coverage > 0, CSV エクスポート成功"],
    ["test_colour_and_shape_filters_reject_non_olive_regions","茶色土壌 + 肌色 -> 検出なし","leaf_count == 0, fruit_count == 0"],
    ["test_result_includes_maturity_breakdown_and_cover","緑実 + 黄緑実 -> 熟度分析","maturity_breakdown 合計 == fruit_count"],
    ["test_watershed_splits_touching_fruits","2つの接触する円 -> watershed 分割",">= 2 個に分割"],
    ["test_health_trend_tracks_fruits_and_detects_changes","3日間シーケンス -> ヘルストレンド","ripening, wrinkling, deteriorating フラグ"],
    ["test_gt_6497_fruit_detection_recall","IMG_6497.jpg + GT JSON -> 検出率","recall == 1.0, precision == 1.0"],
])
doc.add_paragraph("テストは ML 依存 (lightgbm, pandas 等) を使用しない。runtime.py のみで完結。")

# ═══════════════════════════════════════════════════════════════
# 17. デバッグツール
# ═══════════════════════════════════════════════════════════════
doc.add_heading("17. デバッグツール群", level=1)
doc.add_paragraph(
    "tools/check_hough.py: Hough 円検出のシグナルエビデンスを可視化・統計\n"
    "tools/check_cur.py: シワ/巻き込みのスコアリング結果をデバッグ表示")

# DOCX 保存
docx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "OliveVision_AI_技術仕様書_v3.docx")
doc.save(docx_path)
print(f"DOCX saved: {docx_path}")


# ═══════════════════════════════════════════════════════════════
# PowerPoint 生成
# ═══════════════════════════════════════════════════════════════
from pptx import Presentation
from pptx.util import Inches, Pt as PptPt
from pptx.dml.color import RGBColor as PptRGB
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

G = PptRGB(0x1B,0x5E,0x20)
GL = PptRGB(0x4C,0xAF,0x50)
O = PptRGB(0xE6,0x51,0x00)
DB = PptRGB(0x1A,0x1A,0x2E)
W = PptRGB(0xFF,0xFF,0xFF)
BK = PptRGB(0x21,0x21,0x21)
GY = PptRGB(0x61,0x61,0x61)

def slide_bg(slide, color):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = color

def title_slide(title, sub):
    s = prs.slides.add_slide(prs.slide_layouts[6]); slide_bg(s, DB)
    tb = s.shapes.add_textbox(Inches(1), Inches(2.2), Inches(11.333), Inches(1.2))
    tf = tb.text_frame; tf.word_wrap = True; p = tf.paragraphs[0]
    p.text = title; p.font.size = PptPt(44); p.font.bold = True; p.font.color.rgb = GL; p.alignment = PP_ALIGN.CENTER
    tb2 = s.shapes.add_textbox(Inches(1), Inches(3.6), Inches(11.333), Inches(1.5))
    tf2 = tb2.text_frame; tf2.word_wrap = True; p2 = tf2.paragraphs[0]
    p2.text = sub; p2.font.size = PptPt(16); p2.font.color.rgb = PptRGB(0xBD,0xBD,0xBD); p2.alignment = PP_ALIGN.CENTER

def section_slide(title, num=None):
    s = prs.slides.add_slide(prs.slide_layouts[6]); slide_bg(s, DB)
    if num:
        tn = s.shapes.add_textbox(Inches(1), Inches(2.0), Inches(11.333), Inches(0.7))
        tnf = tn.text_frame; pn = tnf.paragraphs[0]; pn.text = num; pn.font.size = PptPt(20); pn.font.color.rgb = PptRGB(0x75,0x75,0x75); pn.alignment = PP_ALIGN.CENTER
    tb = s.shapes.add_textbox(Inches(1), Inches(2.8), Inches(11.333), Inches(1.5))
    tf = tb.text_frame; tf.word_wrap = True; p = tf.paragraphs[0]
    p.text = title; p.font.size = PptPt(36); p.font.bold = True; p.font.color.rgb = W; p.alignment = PP_ALIGN.CENTER

def content_slide(title, bullets_left, bullets_right=None, note=None):
    s = prs.slides.add_slide(prs.slide_layouts[6]); slide_bg(s, W)
    sh = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), prs.slide_width, Inches(0.9))
    sh.fill.solid(); sh.fill.fore_color.rgb = G; sh.line.fill.background()
    tb = s.shapes.add_textbox(Inches(0.5), Inches(0.12), Inches(12.333), Inches(0.7))
    p = tb.text_frame.paragraphs[0]; p.text = title; p.font.size = PptPt(24); p.font.bold = True; p.font.color.rgb = W

    left_w = Inches(5.8) if bullets_right else Inches(12.1)
    tbL = s.shapes.add_textbox(Inches(0.6), Inches(1.1), left_w, Inches(6.0))
    tfL = tbL.text_frame; tfL.word_wrap = True; first = True
    for b in bullets_left:
        p = tfL.paragraphs[0] if first else tfL.add_paragraph(); first = False
        p.text = b; p.font.size = PptPt(13); p.font.color.rgb = BK; p.space_after = Pt(3)

    if bullets_right:
        tbR = s.shapes.add_textbox(Inches(6.8), Inches(1.1), Inches(5.8), Inches(6.0))
        tfR = tbR.text_frame; tfR.word_wrap = True; first = True
        for b in bullets_right:
            p = tfR.paragraphs[0] if first else tfR.add_paragraph(); first = False
            p.text = b; p.font.size = PptPt(13); p.font.color.rgb = BK; p.space_after = Pt(3)

    if note:
        tn = s.shapes.add_textbox(Inches(0.6), Inches(6.9), Inches(12.1), Inches(0.4))
        pn = tn.text_frame.paragraphs[0]; pn.text = note; pn.font.size = PptPt(9); pn.font.color.rgb = GY

def two_col_table_slide(title, headers, rows):
    s = prs.slides.add_slide(prs.slide_layouts[6]); slide_bg(s, W)
    sh = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), prs.slide_width, Inches(0.9))
    sh.fill.solid(); sh.fill.fore_color.rgb = G; sh.line.fill.background()
    tb = s.shapes.add_textbox(Inches(0.5), Inches(0.12), Inches(12.333), Inches(0.7))
    p = tb.text_frame.paragraphs[0]; p.text = title; p.font.size = PptPt(24); p.font.bold = True; p.font.color.rgb = W

    cols = len(headers)
    tbl_shape = s.shapes.add_table(min(len(rows)+1, 25), cols, Inches(0.5), Inches(1.1), Inches(12.333), Inches(6.0))
    tbl = tbl_shape.table
    for i, h in enumerate(headers):
        c = tbl.cell(0, i); c.text = h; c.fill.solid(); c.fill.fore_color.rgb = G
        p = c.text_frame.paragraphs[0]; p.font.size = PptPt(11); p.font.bold = True; p.font.color.rgb = W; p.alignment = PP_ALIGN.CENTER
    for r, rd in enumerate(rows[:24]):
        for c, v in enumerate(rd):
            cell = tbl.cell(r+1, c); cell.text = str(v)
            cell.fill.solid(); cell.fill.fore_color.rgb = PptRGB(0xF5,0xF5,0xF5) if r%2==0 else W
            p = cell.text_frame.paragraphs[0]; p.font.size = PptPt(10); p.font.color.rgb = BK

def code_slide(title, code_text, caption=None):
    s = prs.slides.add_slide(prs.slide_layouts[6]); slide_bg(s, W)
    sh = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), prs.slide_width, Inches(0.9))
    sh.fill.solid(); sh.fill.fore_color.rgb = G; sh.line.fill.background()
    tb = s.shapes.add_textbox(Inches(0.5), Inches(0.12), Inches(12.333), Inches(0.7))
    p = tb.text_frame.paragraphs[0]; p.text = title; p.font.size = PptPt(24); p.font.bold = True; p.font.color.rgb = W

    cb = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.5), Inches(1.1), Inches(12.333), Inches(5.8))
    cb.fill.solid(); cb.fill.fore_color.rgb = PptRGB(0x26,0x32,0x38); cb.line.fill.background()
    tc = s.shapes.add_textbox(Inches(0.7), Inches(1.2), Inches(11.9), Inches(5.5))
    tf = tc.text_frame; tf.word_wrap = True; lines = code_text.strip().split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i==0 else tf.add_paragraph()
        p.text = line; p.font.size = PptPt(10); p.font.name = "Consolas"
        p.font.color.rgb = PptRGB(0xA5,0xD6,0xA7); p.space_after = Pt(1)
    if caption:
        tn = s.shapes.add_textbox(Inches(0.6), Inches(7.0), Inches(12.1), Inches(0.3))
        pn = tn.text_frame.paragraphs[0]; pn.text = caption; pn.font.size = PptPt(9); pn.font.color.rgb = GY


# ═══════════════════════════════════════════════════════════════
# PowerPoint: スライド生成
# ═══════════════════════════════════════════════════════════════

title_slide("OliveVision AI 技術解説",
    "AI搭載 オリーブ樹長期モニタリングシステム\n"
    "src/runtime.py (2,800行) のアーキテクチャと検出アルゴリズム\n\n2026年8月")

two_col_table_slide("目次",
    ["章","内容","ページ"],
    [
        ["1","プロジェクト概要","2"],
        ["2","最近作業ファイル","3"],
        ["3","モジュール構成 (DEFAULTS, 5セクション)","4"],
        ["4","Store クラス (SQLite)","5"],
        ["5","ヘルパー関数群","6"],
        ["6","analyze() パイプライン","7"],
        ["7","葉マスク (6カラースペース融合)","8"],
        ["8","実マスク (3色帯 + Hough円)","9"],
        ["9","フィルタと信頼度","10"],
        ["10","シワ/巻き込み","11"],
        ["11","追跡とヘルストレンド","12"],
        ["12","runtime.yaml / CLI/GUI","13"],
        ["13","出力仕様","14"],
    ])

section_slide("プロジェクト概要", "Part 1")

content_slide("システム目的", [
    "Raspberry Pi 4 上で常時動作",
    "ML/クラウド依存なし",
    "",
    "自動算出する指標:",
    "  - 葉数 / 実数 / 葉面被覆率 / 実面被覆率",
    "  - 葉色ステージ (6段階)",
    "  - 実熟度 (5段階)",
    "  - シワ検出 (4段階)",
    "  - 葉巻き込み (4段階)",
    "  - ぼけレベル (0-1)",
    "  - QRコード木番号検出",
    "  - ヘルストレンド (5段階)",
], [
    "依存関係 (本番):",
    "  numpy >=1.23, <3",
    "  opencv-python-headless >=4.7, <5",
    "  PyYAML >=6, <7",
    "",
    "依存関係 (ML研究用):",
    "  lightgbm==4.1.0",
    "  pandas==2.2.2",
    "  scikit-learn==1.5.1",
    "  scikit-image==0.23.2",
    "  matplotlib==3.9.1",
    "  openpyxl==3.1.2",
    "  scipy==1.14.0",
], note="requirements.txt / requirements-ml.txt 参照")

two_col_table_slide("最近作業ファイル (2026/08/17)",
    ["ファイル","時刻","変更内容"],
    [
        ["tools/check_hough.py","12:27","シグナルエビデンス可視化"],
        ["src/runtime.py","12:20","analysis/stress/trend追加, rescue拡充"],
        ["config/runtime.yaml","12:19","curl/wrinkle/trend パラメータ"],
        ["tools/check_cur.py","12:17","シワ/巻き込みデバッグ"],
        ["tests/test_runtime.py","11:20","回帰テスト 7 件"],
        ["olivevision.py","11:24","GUI タブ追加"],
    ])

section_slide("モジュール構成", "Part 2")

content_slide("DEFAULTS 辞書の5セクション (runtime.py:20-138)", [
    "runtime (3キー):",
    "  max_width=1280, jpeg_quality=90, camera_warmup_frames=8",
    "",
    "detection (45+キー):",
    "  leaf_hue=[30,95], leaf_saturation_min=35, leaf_value_min=25",
    "  leaf_min_area=350, leaf_max_area=30000",
    "  fruit_hue_yellow=[18,45], fruit_hue_ripe=[105,179]",
    "  fruit_saturation_min=55, fruit_value_min=65, fruit_lab_b_min=145",
    "  fruit_min_area=250, fruit_max_area=18000",
    "  fruit_min_circularity=0.50, fruit_min_solidity=0.72",
    "  fruit_max_ellipse_ratio=3.5, fruit_max_internal_std=40.0",
    "  fruit_no_circle_min_area=1400, fruit_no_circle_min_circularity=0.65",
    "  multiscale_scales=[0.75,1.0,1.3], watershed_mindist=20",
    "  detect_mode=multi_signal, edge_refine=True",
], [
    "wrinkle (10キー):",
    "  ridge_weight=3.0, texture_base=18.0, texture_scale=80.0",
    "  smooth_max=0.25, slightly=0.45, wrinkled=0.70",
    "  erosion_scale=0.25, min_interior_pixels=60",
    "",
    "curl (7キー):",
    "  weight_solidity=0.30, weight_defect=0.30, weight_elongation=0.40",
    "  defect_radius_scale=0.5, elongation_baseline=1.2, scale=4.0",
    "  thresholds: 0.10 / 0.25 / 0.50",
    "",
    "analysis (10キー): hue_bands, size_buckets, drooping_angles",
    "stress (7キー): weight_curl=0.5, weight_wrinkle=0.5, weights",
    "trend (14キー): dehydration, flag, note thresholds",
    "video (5キー): interval=10, max_frames=500, fps=5",
], note="runtime.yaml で上書き可能。yaml にないキーは DEFAULTS がそのまま使用される")

content_slide("Store クラス (runtime.py:213-344)", [
    "テーブルスキーマ:",
    "  id INTEGER PRIMARY KEY",
    "  observed_at TEXT NOT NULL",
    "  source TEXT NOT NULL",
    "  image_path TEXT",
    "  leaf_count INTEGER NOT NULL",
    "  fruit_count INTEGER NOT NULL",
    "  green_coverage REAL NOT NULL",
    "  image_width INTEGER NOT NULL",
    "  image_height INTEGER NOT NULL",
    "  result_json TEXT NOT NULL",
    "  tree_id TEXT",
], [
    "メソッド:",
    "  __init__(): DB + テーブル自動生成 + tree_id マイグレーション",
    "  add(): _sanitize_for_json -> INSERT",
    "  recent(): 直近 N 件を降順取得",
    "  recent_by_tree(): tree_id でフィルタ",
    "  recent_by_source(): source プレフィックスでフィルタ",
    "  tree_ids(): DISTINCT tree_id リスト",
    "  export_csv(): CSV エクスポート",
    "  clear(): 全削除",
    "",
    "_sanitize_for_json(): ndarray/list/int/float を安全に変換",
])

content_slide("ヘルパー関数群 (主要20関数)", [
    "ぼけ検出:",
    "  _estimate_blur(): Laplacian 分散",
    "  _local_sharpness_map(): 48x48ブロック Laplacian [0,1]",
    "  _is_mixed_focus(): 変動係数 > 1.0 で判定",
    "",
    "前処理:",
    "  _unsharp_mask(): sigma=2.0, amount=1.6",
    "  _adaptive_preprocess(): バイラテラル+CLAHE+ガウシアン",
    "  _deblur_adaptive(): sharp/blur 重み付けデブラ",
    "  _adaptive_canny(): Otsu 自動閾値 Canny",
    "",
    "植被指数:",
    "  _compute_vegetation_index(): (2G-R-B)/(R+G+B+1)*128+128",
    "  _compute_cgi(): arctan2(G-R, G+R)",
], [
    "検出支援:",
    "  _compute_edge_density(): mask境界とエッジの重なり率",
    "  _compute_internal_texture(): mask内 gray std",
    "  _snap_contour_to_edges(): 輪郭をエッジに最大4px移動",
    "  _compute_shape_descriptors(): area/circularity/solidity/hu",
    "",
    "シワ/巻き込み:",
    "  _compute_wrinkle_score(): Sobel→Otsu→4方向リッジ",
    "  _compute_leaf_curl_score(): solidity+defect+aspect",
    "",
    "前景除去 (6方式):",
    "  _fg_mask_kmeans/grabcut/hsv_bgsub/edge_flood/adaptive",
    "",
    "その他:",
    "  _watershed_split(): 距離変換 watershed",
    "  _hough_circles_fruit(): dp=1.2, param1=80, param2=40",
    "  _detect_qr_tree_id(): QR から第N試験樹を抽出",
])

section_slide("検出パイプライン", "Part 3")

content_slide("Analyzer.analyze() パイプライン (runtime.py:1662)", [
    "Step 1:  _resize (max_width=1280)",
    "Step 2:  blur_raw = Laplacian分散",
    "Step 3:  blur_level = (180-blur_raw)/160",
    "Step 4:  sharp_map = _local_sharpness_map(block=48)",
    "Step 5:  uniform_blurry 判定",
    "Step 6:  _adaptive_preprocess (バイラテラル+CLAHE+ガウシアン)",
    "Step 7:  _deblur_adaptive (領域別デブラ)",
    "Step 8:  hsv, lab 変換",
    "Step 9:  fg_mask 生成 (detect_mode に応じて)",
    "Step 10: _build_leaf_mask (6カラースペース融合)",
], [
    "Step 11: _split_large_components (大型blob分割)",
    "Step 12: multiscale 検出 (0.75x, 1.0x, 1.3x)",
    "Step 13: _merge_multiscale (IoU>0.35 で重複除去)",
    "Step 14: _filter_contours (leaf)",
    "Step 15: 葉色分類 + 巻き込みスコア",
    "Step 16: _build_fruit_mask (3色帯+Hough円)",
    "Step 17: _watershed_split (接触実分離)",
    "Step 18: _filter_contours (fruit)",
    "Step 19: シグナル再生成 + detect_evidence 割り当て",
    "Step 20: アノテーション画像生成 (エッジスナップ付き)",
    "Step 21: result 辞書構築 → 返却",
], note="処理時間: Raspberry Pi 4 で約 0.5-2.0 秒/画像")

code_slide("_build_leaf_mask 融合ロジック (runtime.py:1347)",
    "relax = max(0.0, (blur_level - 0.5) * 2.0)\n"
    "sat_floor = int(max(25, leaf_saturation_min - relax * 25))\n"
    "\n"
    "# HSV必須 + 4シグナルのうち N 個以上一致\n"
    "required_signals = 2 if blur_level < 0.75 else 1\n"
    "signals = exg + cgi + lab + ycrcb\n"
    "multi_signal = inRange(signals, required_signals, 255)\n"
    "\n"
    "combined = HSV_mask AND (multi_signal OR vegetation_union)\n"
    "\n"
    "# 後処理: Dilate→Open→Close→Scale-aware→暗画素抑制→前景→Edge→Hole fill",
    caption="6カラースペース: HSV(Hue 30-95) + ExG(>=12) + CGI(>=165) + LAB(a<118) + YCrCb(Cr<130)")

code_slide("_build_fruit_mask 検証フロー (runtime.py:1417)",
    "# 3色帯のOR統合\n"
    "fruit = _clean(yellow_green | ripe | dark_ripe)\n"
    "safe_leaf = leaf_mask AND NOT yellow_green\n"
    "fruit = fruit AND NOT safe_leaf\n"
    "\n"
    "# Hough 円検証\n"
    "circles = _hough_circles_fruit(gray, dp=1.2, minDist=25, param1=80, param2=40)\n"
    "if circles:\n"
    "    near_circle = fruit AND dilated_circles\n"
    "    if blur_level < 0.5:\n"
    "        # rescue: area[1400,4000], circ>=0.65 OR solid>=0.88, gstd<=45.0\n"
    "        fruit = near_circle OR self_evident_rescue\n"
    "    else:\n"
    "        fruit = near_circle",
    caption="rescue ロジック: Hough 円に検出されなかった blob を丸くて滑らかな形状で救済")

content_slide("シワスコアリング (runtime.py:755-848)", [
    "アルゴリズム:",
    "1. erode(mask) でインテリアマスク生成",
    "   radius = sqrt(area/pi), ksize = 2*radius*0.25",
    "2. Sobel 勾配マップ",
    "   gx = Sobel(gray, CV_32F, 1, 0, ksize=3)",
    "   gy = Sobel(gray, CV_32F, 0, 1, ksize=3)",
    "   mag = magnitude(gx, gy)",
    "3. 閾値: max(otsu, mean*1.4, 20.0)",
    "4. 4方向カーネル (1x7, 7x1, diag, fliplr)",
    "   thin = max(open|close for k in kernels)",
    "5. density = thin_count / interior_count",
    "6. texture = std(gray[interior])",
    "7. score = min(1.0, density*3.0 + max(0,texture-18.0)/80.0)",
], [
    "ディスカウント:",
    "  interior_fraction < 0.30 → discount",
    "  area < 350 → aggressive discount",
    "  unreliable=True → score *= discount",
    "",
    "ラベルリング:",
    "  < 0.25 → smooth",
    "  0.25-0.45 → slightly_wrinkled",
    "  0.45-0.70 → wrinkled",
    "  >= 0.70 → heavily_wrinkled",
    "",
    "信頼性:",
    "  unreliable=True は health verdict で",
    "  信頼性が下がる",
], note="config: wrinkle_ridge_weight=3.0, texture_base=18.0, texture_scale=80.0")

content_slide("葉巻き込みスコア (runtime.py:1003-1028)", [
    "3つの形状ヒントから 0-1 スコアを算出:",
    "",
    "solidity_gap = 1.0 - solidity",
    "  (0=凸, 1=非常に凹む)",
    "",
    "defect_ratio = min(1.0, defect_depth / radius * 0.5)",
    "  (convexity defect 深度 / 葉半径)",
    "",
    "elongation = min(1.0, max(0, aspect-1.2) / 4.0)",
    "  (アスペクト比が高い=巻き込み)",
    "",
    "score = 0.30*gap + 0.30*defect + 0.40*elongation",
], [
    "ラベルリング:",
    "  < 0.10 → flat",
    "  0.10-0.25 → slight_curl",
    "  0.25-0.50 → curled",
    "  >= 0.50 → heavily_curled",
    "",
    "出力例:",
    '  leaf_curl_index: 0.203',
    '  curled_leaf_pct: 0.0%',
    "",
    "config で全パラメータを調整可能:",
    "  curl_weight_solidity=0.30",
    "  curl_weight_defect=0.30",
    "  curl_weight_elongation=0.40",
])

content_slide("フィルタと信頼度 (_filter_contours)", [
    "葉フィルタ条件:",
    "  area: 350-30000",
    "  aspect: 1.0-12.0",
    "  solidity >= 0.58",
    "",
    "実フィルタ条件:",
    "  area: 250-18000",
    "  aspect: 0.45-2.4",
    "  solidity >= 0.72",
    "  circularity >= 0.50",
    "  ellipse_axis_ratio <= 3.5",
    "  internal_texture <= 40.0",
], [
    "信頼度算出:",
    "  circ_s = min(1.0, circularity/0.8)",
    "  sol_s = min(1.0, solidity/0.9)",
    "",
    "  葉: base = circ_s*0.25 + sol_s*0.35 + ar_s*0.25",
    "  実: base = circ_s*0.35 + sol_s*0.35 + ar_s*0.15",
    "",
    "  conf = base*base_w + color*0.25 + edge*ew",
    "",
    "  葉: base_w = 0.50 + obj_blur*0.10",
    "  実: base_w = 0.45 + obj_blur*0.10",
    "  ew = max(0, 0.25 - obj_blur*0.15)",
], note="ローカルぼけ推定: band_w = max(15, min(45, 2*sqrt(area/pi))) のバンドから peak を取得")

content_slide("ヘルストレンド分析 (runtime.py:378-608)", [
    "前処理:",
    "  - green_coverage < 10% を除外",
    "  - 重複観測の削除 (date+source+counts+coverage)",
    "",
    "時系列スロープ:",
    "  xs = 時間(hour), ys = 値",
    "  slope = (n*sum(xy)-sum(x)*sum(y)) / (n*sum(x^2)-sum(x)^2) * 24",
    "",
    "実追跡 (match_radius=60px):",
    "  d_rip = rip_last - rip_first (threshold=0.15)",
    "  d_wrk = wrk_last - wrk_first (threshold=0.2)",
    "  dehydration = wrk*0.6 + shrink*0.4 (threshold=0.30)",
], [
    "ヘルス判定:",
    "  insufficient: 追跡実が 0 個",
    "  declining: wrinkling >= n/2 OR dehydrating >= n/2",
    "  maturing: ripening >= n/2",
    "  mixed: フラグがあるが一方的でない",
    "  stable: フラグなし",
    "",
    "ノート生成:",
    "  - ripeness 上昇/低下",
    "  - wrinkling 増加",
    "  - green 減少",
    "  - fruit_count 減少",
    "  - leaf_count 減少",
    "  - dropout 検出",
], note="config/trend セクションで全閾値を調整可能")

content_slide("config/runtime.yaml パラメータ (132行)", [
    "runtime (3キー):",
    "  max_width, jpeg_quality, camera_warmup_frames",
    "",
    "detection (45+キー):",
    "  leaf_hue=[30,95], leaf_saturation_min=35",
    "  fruit_hue_yellow=[18,45], fruit_hue_ripe=[105,179]",
    "  fruit_min_circularity=0.50, fruit_min_solidity=0.72",
    "  detect_mode=multi_signal",
    "  wrinkle_ridge_weight=3.0, texture_base=18.0",
    "  curl_weight_solidity=0.30, curl_weight_defect=0.30",
    "",
    "analysis (10キー):",
    "  leaf_hue_green_low=35, green_high=85, yellow_high=95",
    "  leaf_size_small_max=2000, medium_max=6000",
    "  drooping_angle_low=45, high=135",
], [
    "stress (7キー):",
    "  weight_curl=0.5, weight_wrinkle=0.5",
    "  green_coverage_max=50.0",
    "  curl_saturation=3.0, wrinkle_saturation=2.0",
    "  weight_green=0.30, weight_health_curl=0.25",
    "  weight_health_wrinkle=0.25, weight_saturation=0.20",
    "",
    "trend (14キー):",
    "  min_green_coverage=10.0",
    "  dehydration_wrinkle_scale=0.5",
    "  flag_ripeness_threshold=0.15",
    "  note_green_decline=-2.0",
    "",
    "video (5キー):",
    "  frame_interval=10, max_frames=500",
    "  output_fps=5, track_max_age=30",
])

content_slide("出力仕様 (leaf_objects / fruit_objects)", [
    "leaf_objects[]:",
    "  confidence, area, aspect, solidity",
    "  ellipse_axis_ratio, num_defects, mean_defect_depth",
    "  curl_score, curl_label",
    "  color_consistency, edge_density, blur_level",
    "  center_x, center_y",
    "",
    "fruit_objects[]:",
    "  confidence, area, circularity, solidity",
    "  ellipse_axis_ratio, hue, saturation, lab_b",
    "  maturity, wrinkle_score, wrinkle_label",
    "  wrinkle_reliable, ridge_density",
    "  detect_evidence, signal_ratios",
    "  edge_touch, low_signal",
    "  center_x, center_y",
], [
    "pipeline_diagnostics:",
    "  leaves: {candidates, accepted, rejected_by}",
    "  fruits: {candidates, accepted, rejected_by}",
    "  signals: {yellow_green_mask, ripe_mask,",
    "            dark_mask, hough_circle_mask}",
    "  accepted_fruit_mask_pct",
    "",
    "fruit_thresholds:",
    "  min_area, max_area, min_aspect, max_aspect",
    "  min_solidity, min_circularity",
    "  max_ellipse_ratio, max_internal_std",
    "",
    "signal_thresholds:",
    "  yellow_green=0.35, ripe=0.25",
    "  dark=0.25, hough_circle=0.20",
])

content_slide("テスト (tests/test_runtime.py - 7件)", [
    "1. test_analysis_persists_result_and_export:",
    "   黒画像に緑矩形 → 解析 → DB 保存, CSV エクスポート",
    "",
    "2. test_colour_and_shape_filters_reject_non_olive_regions:",
    "   茶色土壌 + 肌色 → 検出なし",
    "",
    "3. test_result_includes_maturity_breakdown_and_cover:",
    "   緑実 + 黄緑実 → 熟度分析",
    "",
    "4. test_watershed_splits_touching_fruits:",
    "   2つの接触する円 → >= 2 個に分割",
], [
    "5. test_health_trend_tracks_fruits_and_detects_changes:",
    "   3日間シーケンス → ヘルストレンド",
    "   ripening, wrinkling, deteriorating フラグ",
    "",
    "6. test_gt_6497_fruit_detection_recall:",
    "   IMG_6497.jpg + GT JSON → recall=1.0, precision=1.0",
    "",
    "テスト環境:",
    "  - ML 依存なし (numpy + opencv のみ)",
    "  - PiCamera2 不要",
    "  - OpenCV headless で実行可能",
])

title_slide("まとめ",
    "src/runtime.py (2,800行) が検出エンジンの全容を担い、\n"
    "マルチカラースペース融合、Hough円検出、シワ/巻き込みスコアリング、\n"
    "アダプティブデブラ、マルチスケール検出、ヘルストレンド分析を統合。\n\n"
    "config/runtime.yaml でパラメータを外部化し、\n"
    "tests/test_runtime.py で回帰ガードを確保。\n\n"
    "Raspberry Pi 上でもML依存なしで動作する軽量ランタイムを実現。")

pptx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "OliveVision_AI_技術解説_v3.pptx")
prs.save(pptx_path)
print(f"PPTX saved: {pptx_path}")
