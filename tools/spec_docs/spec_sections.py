"""spec_sections.py - 各セクションのビルド関数"""


def build_all(doc, code, tbl):
    _s1_overview(doc, code, tbl)
    _s2_files(doc, code, tbl)
    _s3_constants(doc, code, tbl)
    _s4_store(doc, code, tbl)
    _s5_helpers(doc, code, tbl)
    _s6_analyze(doc, code, tbl)
    _s7_leaf_mask(doc, code, tbl)
    _s8_fruit_mask(doc, code, tbl)
    _s9_contour_filter(doc, code, tbl)
    _s10_wrinkle_curl(doc, code, tbl)
    _s11_tracker(doc, code, tbl)
    _s12_health_trend(doc, code, tbl)
    _s13_yaml(doc, code, tbl)
    _s14_cli(doc, code, tbl)
    _s15_output(doc, code, tbl)
    _s16_tests(doc, code, tbl)
    _s17_tools(doc, code, tbl)
    _s18_legacy(doc, code, tbl)


def _s1_overview(doc, code, tbl):
    doc.add_heading("1. プロジェクト概要", level=1)
    doc.add_heading("1.1 システム目的", level=2)
    doc.add_paragraph(
        "OliveVision AI は、Raspberry Pi 4 上のカメラ模倣装置を用いて、"
        "農家の代わりにオリーブ樹を定期的に撮影し、AI画像解析で"
        "農業指標を自動算出するシステムである。"
        "本番ランタイムは ML/クラウド依存なしで動作する。"
    )
    for item in [
        "葉数・実数カウント",
        "葉面被覆率 (green_coverage %) / 実面被覆率 (fruit_cover_pct %)",
        "葉色ステージ (healthy_green / dark_green / yellow_green / yellow / brown / dead_brown)",
        "葉枯れ度合い (leaf_senescence 0-100)",
        "実熟度 (green / yellow_green / purple / black / transitioning)",
        "シワ検出 (smooth / slightly_wrinkled / wrinkled / heavily_wrinkled)",
        "葉巻き込み (flat / slight_curl / curled / heavily_curled)",
        "ぼけレベル (blur_level 0.0-1.0)",
        "ヘルストレンド (stable / maturing / declining / mixed / insufficient)",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    doc.add_heading("1.2 依存関係", level=2)
    doc.add_paragraph("本番ランタイム (requirements.txt):")
    tbl(["パッケージ", "バージョン", "用途"], [
        ["numpy", ">=1.23, <3", "配列計算・画像配列操作"],
        ["opencv-python-headless", ">=4.7, <5", "画像処理・検出・変換"],
        ["PyYAML", ">=6, <7", "runtime.yaml 読み込み"],
    ])
    doc.add_paragraph("ML研究用 (requirements-ml.txt):")
    tbl(["パッケージ", "バージョン", "用途"], [
        ["lightgbm", "4.1.0", "Histogram-based GBDT"],
        ["pandas", "2.2.2", "時系列データ操作"],
        ["scikit-learn", "1.5.1", "交差検証・特徴量選択"],
        ["scikit-image", "0.23.2", "GLCM / LBP"],
        ["matplotlib", "3.9.1", "グラフ・可視化"],
        ["openpyxl", "3.1.2", "Excel出力"],
        ["scipy", "1.14.0", "統計解析"],
    ])


def _s2_files(doc, code, tbl):
    from docx.shared import Pt as _Pt
    doc.add_page_break()
    doc.add_heading("2. ファイル構成と更新履歴", level=1)
    doc.add_heading("2.1 ディレクトリツリー", level=2)
    code(
        "olive-p/\n"
        "  src/\n"
        "    runtime.py              # コア検出エンジン (2,222行)\n"
        "    cli_ui.py               # ANSI CLI UI ヘルパー\n"
        "    detection.py            # レガシー検出モジュール\n"
        "    color_analysis.py       # 色解析モジュール\n"
        "    feature_extraction.py   # 特徴量抽出モジュール\n"
        "    advanced_detection.py   # マルチスケール検出\n"
        "    background_removal.py   # 5方式背景除去\n"
        "    video_processor.py      # 動画処理\n"
        "    texture_analysis.py     # GLCM/LBP\n"
        "    optical_flow_analysis.py # オプティカルフロー\n"
        "  config/\n"
        "    runtime.yaml            # 本番パラメータ\n"
        "    config.yaml             # レガシー設定\n"
        "  tools/\n"
        "    check_hough.py          # Hough円デバッグ\n"
        "    check_cur.py            # シワ/巻き込みデバッグ\n"
        "  tests/\n"
        "    test_runtime.py         # 回帰テスト\n"
        "  data/database/\n"
        "    olivevision.db          # SQLite DB\n"
        "    gui_settings.json       # GUI設定\n"
        "  outputs/observations/     # JSON出力\n"
        "  olivevision.py            # CLI/GUI入口\n"
        "  analyze.py / train.py / predict.py\n"
        "  requirements.txt / requirements-ml.txt\n"
        "  docs/ (API_REFERENCE.md / OPERATIONS.md / USAGE_EXAMPLES.md)"
    )
    doc.add_heading("2.2 最近更新ファイル (2026/08/17)", level=2)
    tbl(["ファイル", "更新時刻", "変更内容"], [
        ["tools/check_hough.py", "12:27", "シグナルエビデンス可視化ツール"],
        ["src/runtime.py", "12:20", "blur-aware 閾値, rescue ロジック, シグナル閾値表示"],
        ["config/runtime.yaml", "12:19", "fruit_no_circle_min_area 追加"],
        ["tools/check_cur.py", "12:17", "シワ/巻き込みデバッグ拡充"],
        ["data/database/olivevision.db", "12:06", "observations テーブル書き込み"],
        ["tests/test_runtime.py", "11:20", "回帰テスト 7 件"],
        ["olivevision.py", "11:24", "GUI タブ追加, スライダー拡充"],
    ])


def _s3_constants(doc, code, tbl):
    doc.add_page_break()
    doc.add_heading("3. src/runtime.py -- モジュールグローバル定数", level=1)
    doc.add_heading("3.1 DEFAULTS 辞書 (runtime.py:20-64)", level=2)
    doc.add_paragraph(
        "runtime.yaml が未指定のパラメータのフォールバック値。"
        "load_runtime_config() (runtime.py:89) で yaml 内容を上書きする。"
    )
    tbl(["セクション", "キー", "デフォルト値", "説明"], [
        ["runtime", "max_width", "1280", "リサイズ上限 (px)"],
        ["runtime", "jpeg_quality", "90", "JPEG 品質"],
        ["runtime", "camera_warmup_frames", "8", "スキップフレーム数"],
        ["detection", "leaf_hue", "[30, 95]", "HSV Hue"],
        ["detection", "leaf_saturation_min", "35", "彩度下限"],
        ["detection", "leaf_value_min", "25", "明度下限"],
        ["detection", "leaf_min_area", "350", "最小面積"],
        ["detection", "leaf_max_area", "30000", "最大面積"],
        ["detection", "leaf_min_aspect", "1.0", "最小アスペクト比"],
        ["detection", "leaf_max_aspect", "12.0", "最大アスペクト比"],
        ["detection", "leaf_min_solidity", "0.58", "凸包充填率下限"],
        ["detection", "excess_green_min", "12", "ExG 閾値"],
        ["detection", "fruit_hue_yellow", "[18, 45]", "黄色緑帯"],
        ["detection", "fruit_hue_ripe", "[105, 179]", "熟紫帯"],
        ["detection", "fruit_saturation_min", "55", "彩度下限"],
        ["detection", "fruit_value_min", "65", "明度下限"],
        ["detection", "fruit_lab_b_min", "145", "LAB b 下限"],
        ["detection", "fruit_min_area", "250", "最小面積"],
        ["detection", "fruit_max_area", "18000", "最大面積"],
        ["detection", "fruit_min_aspect", "0.45", "最小アスペクト比"],
        ["detection", "fruit_max_aspect", "2.4", "最大アスペクト比"],
        ["detection", "fruit_min_circularity", "0.50", "円形度下限"],
        ["detection", "fruit_min_solidity", "0.72", "凸包充填率下限"],
        ["detection", "fruit_max_ellipse_ratio", "3.5", "楕円軸比上限"],
        ["detection", "fruit_max_internal_std", "40.0", "内部テクスチャ上限"],
        ["detection", "fruit_no_circle_min_area", "1400", "rescue 最小面積"],
        ["detection", "fruit_no_circle_min_circularity", "0.65", "rescue 円形度下限"],
        ["detection", "fruit_no_circle_min_solidity", "0.88", "rescue 凸包充填率下限"],
        ["detection", "fruit_no_circle_max_std", "45.0", "rescue テクスチャ上限"],
        ["detection", "fruit_no_circle_max_area", "4000", "rescue 最大面积"],
        ["detection", "multiscale_scales", "[0.75, 1.0, 1.3]", "マルチスケール"],
        ["detection", "watershed_mindist", "20", "Watershed 最小距離"],
        ["detection", "deblur_min_blur_raw", "5.0", "デブラ開始 Laplacian 分散"],
        ["detection", "detect_mode", "multi_signal", "検出モード"],
        ["detection", "wrinkle_ridge_weight", "3.0", "リッジ重み"],
        ["detection", "wrinkle_texture_base", "18.0", "テクスチャ基準値"],
        ["detection", "wrinkle_texture_scale", "80.0", "テクスチャ正規化"],
        ["detection", "wrinkle_smooth_max", "0.25", "smooth 上限"],
        ["detection", "wrinkle_slightly_wrinkled_max", "0.45", "slightly_wrinkled 上限"],
        ["detection", "wrinkle_wrinkled_max", "0.70", "wrinkled 上限"],
        ["video", "frame_interval", "10", "間引き間隔"],
        ["video", "max_frames", "500", "最大フレーム数"],
        ["video", "output_fps", "5", "出力 FPS"],
        ["video", "track_max_age", "30", "追跡 ID 保持"],
        ["video", "track_iou_threshold", "0.3", "IoU 閾値"],
    ])

    doc.add_heading("3.2 FRUIT_SIGNAL_THRESHOLDS (runtime.py:70-75)", level=2)
    doc.add_paragraph(
        "各果実候補が「シグナルで裏付けられている」と見なすための"
        " minimum per-pixel overlap ratio。analyze() 内のエビデンス割り当てと "
        " explain_detection() の人間可読説明で共用。"
    )
    tbl(["キー", "閾値", "意味"], [
        ["yellow_green", "0.35", "黄色緑シグナルが blob 面積の 35% 以上"],
        ["ripe", "0.25", "熟紫シグナルが blob 面積の 25% 以上"],
        ["dark", "0.25", "暗熟シグナルが blob 面積の 25% 以上"],
        ["hough_circle", "0.20", "Hough 円マスクが blob 面積の 20% 以上"],
    ])
    doc.add_paragraph(
        "FRUIT_SIGNAL_LABELS (runtime.py:77-82): "
        "\"yellow-green colour\", \"ripe colour\", \"dark/over-ripe colour\", "
        "\"round Hough circle\""
    )


def _s4_store(doc, code, tbl):
    doc.add_page_break()
    doc.add_heading("4. Store クラス (runtime.py:112-176)", level=1)
    doc.add_heading("4.1 テーブルスキーマ", level=2)
    code(
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
        "    result_json     TEXT NOT NULL\n"
        ")"
    )
    doc.add_heading("4.2 メソッド", level=2)
    tbl(["メソッド", "行", "シグネチャ", "説明"], [
        ["__init__", "113", "(db_path: str|Path)", "DB + テーブル自動生成"],
        ["add", "130", "(result: dict) -> None", "result_json に全結果を格納"],
        ["recent", "145", "(limit=20) -> list[dict]", "直近 N 件を降順取得"],
        ["export_csv", "155", "(destination) -> int", "CSV エクスポート (件数返却)"],
        ["clear", "167", "() -> int", "全削除 (削除件数返却)"],
    ])
    doc.add_paragraph(
        "add() は result を json.dumps(result, ensure_ascii=False) で "
        "文字列化して result_json に格納。ndarray はシリアライズ不可のため、"
        "save_observation() (runtime.py:1811) で np.ndarray フィールドを除外してから呼び出す。"
    )


def _s5_helpers(doc, code, tbl):
    doc.add_page_break()
    doc.add_heading("5. ヘルパー関数群", level=1)

    doc.add_heading("5.1 ぼけ検出", level=2)
    doc.add_paragraph("_estimate_blur (runtime.py:431-434):")
    code(
        "def _estimate_blur(image_bgr: np.ndarray) -> float:\n"
        "    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)\n"
        "    return float(cv2.Laplacian(gray, cv2.CV_64F).var())"
    )
    doc.add_paragraph(
        "Laplacian 分散。>=180 で鮮明、20 で blur_level ~1.0。"
        "blur_level = min(1.0, max(0.0, (180.0 - blur_raw) / 160.0)) (runtime.py:1470)"
    )
    doc.add_paragraph("_local_sharpness_map (runtime.py:437-452):")
    code(
        "def _local_sharpness_map(image_bgr, block=32) -> np.ndarray:\n"
        "    # block=48 で呼び出される\n"
        "    # 各ブロックの Laplacian 分散を [0,1] に正規化\n"
        "    # vmax > 0 のとき sharp /= vmax"
    )
    doc.add_paragraph("_is_mixed_focus (runtime.py:466-487):")
    code(
        "def _is_mixed_focus(image_bgr, block=64) -> bool:\n"
        "    # 64x64 ブロックごとの Laplacian 分散を算出\n"
        "    # cv_ = arr.std() / arr.mean() > 1.0 で混合フォーカス\n"
        "    # mean <= 1.0 なら False (全体的にノイズが少ない)"
    )
    doc.add_paragraph("_unsharp_mask (runtime.py:455-463):")
    code(
        "def _unsharp_mask(image_bgr, sigma=2.0, amount=1.6, threshold=0):\n"
        "    blurred = cv2.GaussianBlur(image_bgr, (0, 0), sigma)\n"
        "    sharpened = cv2.addWeighted(image_bgr, 1.0+amount, blurred, -amount, 0)\n"
        "    if threshold > 0:\n"
        "        low_contrast = np.all(np.abs(image - blurred) < threshold, axis=2)\n"
        "        sharpened[low_contrast] = image[low_contrast]"
    )
    doc.add_paragraph("_adaptive_canny (runtime.py:704-714):")
    code(
        "def _adaptive_canny(gray):\n"
        "    grad8 = cv2.convertScaleAbs(cv2.Laplacian(gray, cv2.CV_64F))\n"
        "    t, _ = cv2.threshold(grad8, 0, 255, THRESH_BINARY + THRESH_OTSU)\n"
        "    hi = max(35, min(200, int(round(t * 1.6))))\n"
        "    lo = max(8, int(round(t * 0.5)))\n"
        "    return cv2.Canny(gray, lo, hi)"
    )

    doc.add_heading("5.2 アダプティブ前処理 (_adaptive_preprocess, runtime.py:513-530)", level=2)
    code(
        "1. バイラテラルフィルタ (d=9, sigmaColor=75, sigmaSpace=75)\n"
        "2. LAB 変換 -> L チャンネルに CLAHE (clipLimit=2.5, tileGridSize=8x8)\n"
        "3. ガウシアンブラー (k=blur_k, 默认 5, 奇数に調整)\n"
        "4. blur_score (= blur_raw) < 180 のとき unsharp_mask(sigma=2.5, amount=1.8)"
    )

    doc.add_heading("5.3 領域別デブラ (_deblur_adaptive, runtime.py:490-510)", level=2)
    code(
        "実行条件:\n"
        "  sharp_map = _local_sharpness_map(image_bgr, block=48)\n"
        "  sharp_frac = (sharp_map > 0.6).mean()  # sharp ピクセル割合\n"
        "  blur_frac  = (sharp_map < 0.3).mean()   # blur ピクセル割合\n"
        "  sharp_frac >= 0.15 AND blur_frac >= 0.3 のとき実行\n"
        "\n"
        "アプローチ:\n"
        "  strong = _unsharp_mask(image_bgr, sigma=3.0, amount=1.8)\n"
        "  mild   = _unsharp_mask(image_bgr, sigma=1.2, amount=0.6)\n"
        "  weight = (1.0 - sharp_map)[:, :, None]  # ぼけているほど strong\n"
        "  weight = cv2.GaussianBlur(weight, (0,0), 4)\n"
        "  out = strong * weight + mild * (1 - weight)"
    )

    doc.add_heading("5.4 その他のヘルパー", level=2)
    tbl(["関数", "行", "説明"], [
        ["_compute_vegetation_index", "533", "(2G-R-B)/(R+G+B+1)*128+128"],
        ["_compute_cgi", "539", "arctan2(G-R, G+R)"],
        ["_compute_edge_density", "545", "mask 境界のうち画像エッジと重なる割合"],
        ["_compute_internal_texture", "557", "mask 内部の gray std (erode 後)"],
        ["_snap_contour_to_edges", "717", "輪郭頂点を勾配中心に最大 4px 移動"],
        ["_compute_shape_descriptors", "762", "area, circularity, solidity, aspect, hu_moments, defects"],
        ["_circles_to_mask", "885", "(cx,cy,r) リスト -> 二値マスク"],
        ["_fg_mask_kmeans", "893", "K-means で前景クラスタ抽出"],
        ["_fg_mask_grabcut", "920", "GrabCut で前景抽出"],
        ["_fg_mask_hsv_bgsub", "947", "HSV で暗い/低彩度背景を除去"],
        ["_fg_mask_edge_flood", "966", "Canny + FloodFill で前景"],
        ["_adaptive_fg_mask", "990", "画像特性で最適前景方式を選択"],
        ["save_observation", "1811", "ndarray除外 -> analyze -> JSON/DB 保存"],
        ["explain_detection", "1908", "検出結果のテキスト説明を構築"],
        ["capture_camera", "2033", "USB/PiCamera2 からフレーム取得"],
    ])


def _s6_analyze(doc, code, tbl):
    doc.add_page_break()
    doc.add_heading("6. Analyzer.analyze() パイプライン (runtime.py:1463-1771)", level=1)

    doc.add_heading("6.1 シグネチャと返り値", level=2)
    code(
        "class Analyzer:\n"
        "    def __init__(self, config: dict):  # runtime.yaml の内容\n"
        "\n"
        "    def analyze(self, image: np.ndarray, source: str,\n"
        "                image_path: Optional[str] = None) -> Tuple[dict, np.ndarray]:\n"
        "        # 返り値: (result_dict, annotated_image)"
    )

    doc.add_heading("6.2 処理ステップ (runtime.py 行号付き)", level=2)
    steps = [
        ("1465", "_resize", "max_width=1280 でアスペクト比保持リサイズ。scale = maximum / width。"),
        ("1466", "blur_raw = _estimate_blur(image)", "Laplacian 分散を算出。"),
        ("1470", "blur_level", "min(1.0, max(0.0, (180.0 - blur_raw) / 160.0))"),
        ("1474", "edge_refine", "blur_level < 0.75 のときのみ有効。"),
        ("1475", "sharp_map", "_local_sharpness_map(image, block=48)"),
        ("1478-1479", "uniform_blurry", "blur_level > 0.15 AND blur_raw >= 5.0 AND NOT mixed_focus"),
        ("1480-1481", "processed", "_adaptive_preprocess(image, blur_k, deblur=uniform_blurry)"),
        ("1484", "processed", "_deblur_adaptive(processed, blur_level, sharp_map)"),
        ("1485-1486", "hsv, lab", "processed から BGR->HSV, BGR->LAB 変換"),
        ("1489-1502", "fg_mask", "detect_mode に応じて前景マスク生成"),
        ("1505-1506", "leaf_mask", "_build_leaf_mask(processed, hsv, lab, spec, fg_mask, ...)"),
        ("1509-1510", "leaf_mask", "_split_large_components(leaf_mask, processed, leaf_max_area)"),
        ("1511-1522", "leaf_contours", "multiscale_scales で各倍率の輪郭を抽出し _merge_multiscale"),
        ("1523-1524", "leaf_descs", "_filter_contours(leaf_contours, 'leaf', spec, hsv, image, blur, sharp_map)"),
        ("1528-1538", "葉色", "各葉の HSV Hue 平均 -> _classify_leaf_color -> leaf_stage"),
        ("1542-1548", "巻き込み", "各葉の _compute_leaf_curl_score -> curl_label"),
        ("1551-1552", "fruit_mask", "_build_fruit_mask(processed, hsv, lab, leaf_mask, spec, fg_mask, ...)"),
        ("1553-1554", "fruit_masks_ind", "_watershed_split(processed, fruit_mask, min_dist=20)"),
        ("1559-1560", "fruit_descs", "_filter_contours(all_fruit_contours, 'fruit', spec, hsv, ...)"),
        ("1565-1568", "fruit_det_mask", "accept された実輪郭を個別に描画したマスク"),
        ("1576-1585", "ev_yellow/ripe/dark/circles", "シグナル再生成 (エビデンス割り当て用)"),
        ("1587-1638", "各実のループ", "色, 熟度, シワ, signal_ratios, detect_evidence, low_signal"),
        ("1644-1651", "leaf_roughness", "全葉マスクの Laplacian std"),
        ("1653-1685", "アノテーション", "エッジスナップ付きの可視化画像を生成"),
        ("1723-1768", "result 辞書", "全フィールドを構築して返す"),
    ]
    tbl(["行", "処理", "詳細"], [[r, n, d] for r, n, d in steps])

    doc.add_heading("6.3 result 辞書の全フィールド (runtime.py:1723-1768)", level=2)
    tbl(["フィールド", "型", "算出元"], [
        ["observed_at", "str", "now() (ISO8601)"],
        ["source", "str", "引数"],
        ["image_path", "str|None", "引数"],
        ["leaf_count", "int", "len(leaf_descs)"],
        ["fruit_count", "int", "len(fruit_descs)"],
        ["green_coverage", "float", "leaf_mask の nonzero / total * 100"],
        ["image_width", "int", "リサイズ後の幅"],
        ["image_height", "int", "リサイズ後の高さ"],
        ["leaf_color_stage", "str", "_classify_leaf_color(avg_lh)"],
        ["leaf_senescence", "float", "_calculate_senescence(avg_lh, avg_ls)"],
        ["leaf_avg_hue", "float", "全葉の HSV Hue 平均"],
        ["leaf_avg_saturation", "float", "全葉の HSV Saturation 平均"],
        ["leaf_avg_area", "float", "全葉の area 平均"],
        ["leaf_confidence", "float", "全葉の confidence 平均"],
        ["fruit_maturity", "str", "_classify_fruit_maturity(avg_fh)"],
        ["fruit_maturity_breakdown", "dict", "熟度ラベルごとのカウント"],
        ["wrinkled_fruit_count", "int", "wrinkle_score >= 0.45 の実数"],
        ["unreliable_wrinkle_count", "int", "wrinkle_reliable=False の実数"],
        ["fruit_wrinkle_summary", "dict", "smooth/slightly/wrinkled/heavily のカウント"],
        ["fruit_avg_hue", "float", "全実の Hue 平均"],
        ["fruit_avg_area", "float", "全実の area 平均"],
        ["fruit_confidence", "float", "全実の confidence 平均"],
        ["leaf_total_area", "int", "leaf_mask nonzero"],
        ["fruit_total_area", "int", "fruit_det_mask nonzero"],
        ["fruit_cover_pct", "float", "fruit_det_mask nonzero / total * 100"],
        ["leaf_roughness", "float", "全葉マスクの Laplacian std"],
        ["leaf_curl_index", "float", "全葉の curl_score 平均"],
        ["curled_leaf_pct", "float", "curl_score >= 0.25 の葉割合 (%)"],
        ["detect_mode", "str", "spec['detect_mode']"],
        ["blur_score", "float", "blur_raw (Laplacian 分散)"],
        ["blur_level", "float", "正規化ぼけレベル (0-1)"],
        ["leaf_objects", "list", "各葉の全情報"],
        ["fruit_objects", "list", "各実の全情報"],
        ["leaf_boxes", "list", "(x,y,w,h) リスト"],
        ["fruit_boxes", "list", "(x,y,w,h) リスト"],
        ["fruit_thresholds", "dict", "フィルタ閾値のスナップショット"],
        ["signal_thresholds", "dict", "FRUIT_SIGNAL_THRESHOLDS のコピー"],
        ["pipeline_diagnostics", "dict", "除外統計・シグナルカバレッジ"],
    ])


def _s7_leaf_mask(doc, code, tbl):
    doc.add_page_break()
    doc.add_heading("7. _build_leaf_mask (runtime.py:1148-1216)", level=1)
    doc.add_paragraph(
        "6 カラースペースから同時に検証し、HSV を必須条件として融合する。"
        "ぼけレベルに応じて required_signals を緩和するアダプティブ機構を持つ。"
    )
    doc.add_heading("7.1 カラースペース定義", level=2)
    tbl(["#", "カラースペース", "変換式/閾値", "行"], [
        ["1", "HSV", "Hue=[30,95], Sat>=sat_floor, Val>=leaf_value_min", "1158-1160"],
        ["2", "Excess Green", "(2G-R-B)/(R+G+B+1)*128+128 -> >=12", "1162-1163"],
        ["3", "CGI", "arctan2(G-R, G+R) -> >=165", "1165-1166"],
        ["4", "LAB a-channel", "a < 118", "1168"],
        ["5", "YCrCb", "Cr < 130", "1170-1171"],
    ])
    doc.add_heading("7.2 融合ロジック", level=2)
    code(
        "relax = max(0.0, (blur_level - 0.5) * 2.0)          # 0..1 for blur>=0.5\n"
        "sat_floor = int(max(25, spec['leaf_saturation_min'] - relax * 25))\n"
        "\n"
        "required_signals = 2 if blur_level < 0.75 else 1     # 1175行\n"
        "signals = exg + cgi + lab + ycrcb                     # 1178-1182\n"
        "multi_signal = cv2.inRange(signals, required_signals, 255)  # 1183\n"
        "\n"
        "combined = HSV_mask AND (multi_signal OR vegetation_union)  # 1185"
    )
    doc.add_heading("7.3 後処理", level=2)
    tbl(["ステップ", "行", "詳細"], [
        ["Dilate + Open + Close", "1191-1192", "楕円カーネル edge_k (blur で縮小)"],
        ["Scale-aware Open + Close", "1196-1199", "mk_size = min(7, min(h,w)/150)"],
        ["暗画素抑制", "1202", "V >= 15 の画素のみ残す"],
        ["前景制約", "1206-1207", "fg_mask がある場合 AND"],
        ["Edge refine", "1210-1211", "blur_level < 0.75 のみ"],
        ["Hole fill", "1214-1215", "MORPH_CLOSE (7x7 楕円)"],
    ])


def _s8_fruit_mask(doc, code, tbl):
    doc.add_page_break()
    doc.add_heading("8. _build_fruit_mask (runtime.py:1218-1300)", level=1)
    doc.add_heading("8.1 色帯定義", level=2)
    tbl(["色帯", "HSV Hue", "Sat", "Val", "LAB b", "行"], [
        ["黄色緑", "[18, 45]", ">= sat_floor", ">= 65", ">= lab_b_floor", "1228-1232"],
        ["熟紫", "[105, 179]", ">= max(60, ripe_sat)", ">= 55", "—", "1234-1235"],
        ["暗熟", "[105, 175]", ">= 85-relax*20", "[25, 55]", "—", "1236"],
    ])
    doc.add_paragraph(
        "sat_floor = max(50, fruit_saturation_min - relax*25)  # 1226行\n"
        "lab_b_floor = max(110, fruit_lab_b_min - relax*30)     # 1227行\n"
        "ripe_sat = 110 - int(relax * 25)                       # 1233行"
    )
    doc.add_heading("8.2 後処理と Hough 円検証", level=2)
    code(
        "fruit = _clean(yellow_green | ripe | dark_ripe)       # 1238\n"
        "safe_leaf = leaf_mask AND NOT yellow_green             # 1239\n"
        "fruit = fruit AND NOT safe_leaf                        # 1240\n"
        "\n"
        "# Hough 円検証\n"
        "circles = _hough_circles_fruit(gray, dp=1.2, minDist=25, param1=80, param2=40)\n"
        "if circles:\n"
        "    circle_fruit = fruit AND circle_mask               # 1255\n"
        "    near_circle = fruit AND dilated_circles            # 1257\n"
        "    if blur_level < 0.5:                               # 1260\n"
        "        # rescue: far_fruit から条件を満たす blob を救済\n"
        "        # area ∈ [1400, 4000], circularity >= 0.65 OR solidity >= 0.88,\n"
        "        # gstd <= 45.0                                   # 1267-1280\n"
        "        fruit = near_circle OR se                       # 1282\n"
        "    else:\n"
        "        fruit = near_circle                             # 1284\n"
        "\n"
        "# 面積フィルタ\n"
        "area < fruit_min_area * 0.5 -> 除外                   # 1296\n"
        "area > img_area * 0.30 -> 除外                         # 1298"
    )


def _s9_contour_filter(doc, code, tbl):
    doc.add_page_break()
    doc.add_heading("9. _filter_contours (runtime.py:1302-1411)", level=1)
    doc.add_paragraph(
        "輪郭をサイズ・形状・エッジ密度・色一貫性でフィルタし、"
        "各候補の confidence を算出する。"
    )
    doc.add_heading("9.1 葉フィルタ条件", level=2)
    tbl(["パラメータ", "条件", "runtime.yaml キー"], [
        ["area", "leaf_min_area <= area <= leaf_max_area", "350-30000"],
        ["aspect", "leaf_min_aspect <= aspect <= leaf_max_aspect", "1.0-12.0"],
        ["solidity", "solidity >= leaf_min_solidity", ">= 0.58"],
    ])
    doc.add_heading("9.2 実フィルタ条件", level=2)
    tbl(["パラメータ", "条件", "runtime.yaml キー"], [
        ["area", "fruit_min_area <= area <= fruit_max_area", "250-18000"],
        ["aspect", "fruit_min_aspect <= aspect <= fruit_max_aspect", "0.45-2.4"],
        ["solidity", "solidity >= fruit_min_solidity", ">= 0.72"],
        ["circularity", "circularity >= fruit_min_circularity", ">= 0.50"],
        ["ellipse_axis_ratio", "<= fruit_max_ellipse_ratio", "<= 3.5"],
        ["internal_texture", "std <= fruit_max_internal_std", "<= 40.0"],
    ])
    doc.add_heading("9.3 信頼度算出 (_detection_confidence, runtime.py:1134-1144)", level=2)
    code(
        "# 基本スコア\n"
        "circ_s = min(1.0, circularity / 0.8)\n"
        "sol_s  = min(1.0, solidity / 0.9)\n"
        "\n"
        "# 葉の場合\n"
        "ar_s = 1.0 - min(0.5, abs(aspect - 2.5) / 4.0)\n"
        "base = circ_s * 0.25 + sol_s * 0.35 + ar_s * 0.25\n"
        "\n"
        "# 実の場合\n"
        "ar_s = 1.0 - min(0.5, abs(aspect - 1.2) / 2.0)\n"
        "base = circ_s * 0.35 + sol_s * 0.35 + ar_s * 0.15\n"
        "\n"
        "# 後処理 (runtime.py:1393-1404)\n"
        "# 葉: confidence = base * (0.50 + obj_blur*0.10) + color_consistency*0.25 + edge_density*edge_weight\n"
        "# 実: confidence = base * (0.45 + obj_blur*0.10) + color_consistency*0.25 + edge_density*min(edge_weight+0.05, 0.30)\n"
        "# edge_weight = max(0.0, 0.25 - obj_blur * 0.15)"
    )
    doc.add_heading("9.4 ローカルぼけ推定 (runtime.py:1362-1371)", level=2)
    doc.add_paragraph(
        "blur_level >= 0.5 かつ sharp_map がある場合、"
        "各オブジェクトの周辺バンド (band_w = max(15, min(45, 2*sqrt(area/pi)))) "
        "からローカルな sharpness peak を取得し、obj_blur を算出。"
        "obj_blur = min(1.0, max(blur_level, 1.0 - peak))"
    )


def _s10_wrinkle_curl(doc, code, tbl):
    doc.add_page_break()
    doc.add_heading("10. シワ/巻き込みスコアリング", level=1)

    doc.add_heading("10.1 _compute_wrinkle_score (runtime.py:571-657)", level=2)
    code(
        "# 1. インテリアマスク生成\n"
        "radius = max(1.0, (area / pi) ** 0.5)\n"
        "ksize = max(3, min(11, int(2 * radius * 0.25)))       # 593行\n"
        "interior = erode(mask, kernel=ksize)                    # 596行\n"
        "interior_fraction = interior_px / area                  # 602行\n"
        "\n"
        "# interior_px < 60 で unreliable=True, full mask にフォールバック  # 604-609\n"
        "\n"
        "# 2. Sobel 勾配マップ\n"
        "gx = Sobel(gray, CV_32F, 1, 0, ksize=3)\n"
        "gy = Sobel(gray, CV_32F, 0, 1, ksize=3)\n"
        "mag = magnitude(gx, gy)                                # 616行\n"
        "\n"
        "# 3. 閾値\n"
        "otsu_thr, _ = threshold(mag.astype(uint8), 0, 255, THRESH_BINARY+THRESH_OTSU)\n"
        "thr = max(otsu_thr, mean*1.4, 20.0)                   # 621行\n"
        "\n"
        "# 4. 4方向カーネルで morphological open/close\n"
        "kernels = [ones(1,7), ones(7,1), diag([1]*7), fliplr(diag([1]*7))]\n"
        "thin = max(open(ridge, k) | close(ridge, k) for k in kernels)  # 629-632\n"
        "\n"
        "# 5. スコア\n"
        "density = thin_count / interior_count                   # 633行\n"
        "texture = std(gray[interior > 0])                       # 634行\n"
        "score = min(1.0, density*3.0 + max(0, texture-18.0)/80.0)  # 635行\n"
        "\n"
        "# 6. ディスカウント\n"
        "if unreliable or interior_fraction < 0.30 or area < 350:\n"
        "    if area < 350:\n"
        "        discount = min(1.0, area/350.0 * interior_fraction/0.30)\n"
        "    else:\n"
        "        discount = min(1.0, interior_fraction / 0.30)\n"
        "    score *= discount                                   # 646行"
    )
    tbl(["スコア範囲", "ラベル"], [
        ["< 0.25", "smooth"],
        ["0.25 - 0.45", "slightly_wrinkled"],
        ["0.45 - 0.70", "wrinkled"],
        [">= 0.70", "heavily_wrinkled"],
    ])

    doc.add_heading("10.2 _compute_leaf_curl_score (runtime.py:812-832)", level=2)
    code(
        "solidity_gap = 1.0 - solidity                          # 0=凸, 1=凹\n"
        "defect_depth = desc['mean_defect_depth']\n"
        "radius = max(1.0, (area / 3.14159) ** 0.5)\n"
        "defect_ratio = min(1.0, defect_depth / radius * 0.5)   # 828行\n"
        "elongation = min(1.0, max(0.0, aspect - 1.2) / 4.0)    # 830行\n"
        "score = 0.30*solidity_gap + 0.30*defect_ratio + 0.40*elongation  # 831行"
    )
    tbl(["スコア範囲", "ラベル"], [
        ["< 0.10", "flat"],
        ["0.10 - 0.25", "slight_curl"],
        ["0.25 - 0.50", "curled"],
        [">= 0.50", "heavily_curled"],
    ])


def _s11_tracker(doc, code, tbl):
    doc.add_page_break()
    doc.add_heading("11. _CentroidTracker (runtime.py:1011-1083)", level=1)
    doc.add_paragraph("重心ベースのマルチオブジェクト追跡。葉と実で個別インスタンスを使用。")
    code(
        "class _CentroidTracker:\n"
        "    max_age: int = 30  # フレーム未検出で削除\n"
        "\n"
        "    update(detections: List[Tuple[int,int,int,int]]) -> Dict[int, Tuple]:\n"
        "        # 1. 入力 bbox から重心を算出                       # 1031-1032\n"
        "        # 2. 既存トラックとの距離行列 D[i,j] を構築          # 1047-1050\n"
        "        # 3. D を平坦化 -> min(axis=1) でソート             # 1052-1053\n"
        "        # 4. D[row,col] <= 80px のペアをマッチング          # 1060\n"
        "        # 5. マッチしなかった新規 -> 新規トラック登録        # 1077-1081\n"
        "        # 6. age > max_age のトラックを削除                 # 1072-1075\n"
        "        # 返り値: {track_id: (x,y,w,h)}"
    )
    doc.add_paragraph(
        "VideoAnalyzer (runtime.py:2064) で self.tracker_leaves と "
        "self.tracker_fruits を使い分け、各フレームで update() を呼び出す。"
        "追跡結果は timeline エントリに tracked_leaves / tracked_fruits として記録。"
    )


def _s12_health_trend(doc, code, tbl):
    doc.add_page_break()
    doc.add_heading("12. analyze_health_trend (runtime.py:210-424)", level=1)
    doc.add_heading("12.1 入出力", level=2)
    code(
        "def analyze_health_trend(observations: list[dict],\n"
        "                         match_radius: float = 60.0,\n"
        "                         min_observations: int = 2) -> dict:\n"
        "    # 返り値: {ok, period, count, series, trends, fruit_tracks, health}"
    )
    doc.add_heading("12.2 前処理 (runtime.py:225-253)", level=2)
    steps = [
        ("231-233", "observed_at でソート"),
        ("238-243", "green_coverage < 10.0% を除外"),
        ("245-253", "重複�測の削除: (date, source, leaf_count, fruit_count, round(green,2)) でユニーク化"),
    ]
    tbl(["行", "処理"], steps)

    doc.add_heading("12.3 時系列スロープ (_linear_slope_per_day, runtime.py:188-207)", level=2)
    code(
        "xs = [(d - start).total_seconds() / 3600.0 for d in dates]  # 時間 (hour)\n"
        "ys = values\n"
        "denom = n*sum(x^2) - sum(x)^2\n"
        "slope_per_hour = (n*sum(x*y) - sum(x)*sum(y)) / denom\n"
        "return slope_per_hour * 24.0  # 日あたりの変化量"
    )

    doc.add_heading("12.4 実追跡とマッチング (runtime.py:288-358)", level=2)
    code(
        "# 各観測の fruit_objects から中心座標で跨日マッチング\n"
        "d2 = (cx - lx)^2 + (cy - ly)^2\n"
        "if d2 < match_radius^2 (default 60px): -> マッチ\n"
        "\n"
        "# マッチした実の変化を追跡:\n"
        "rip_first/last = ripe + dark の signal_ratios 合計             # 320-321\n"
        "d_rip = rip_last - rip_first                                   # 325\n"
        "d_wrk = wrk_last - wrk_first                                  # 326\n"
        "shrink = area_last / area_first                                # 327\n"
        "\n"
        "# dehydration = wrinkle_contribution*0.6 + shrink_contribution*0.4  # 330-332\n"
        "# wrinkle_contrib = min(1.0, max(0, d_wrk) / 0.5) * 0.6\n"
        "# shrink_contrib = (1.0 - min(1.0, max(0, shrink))) * 0.4\n"
        "\n"
        "# フラグ生成\n"
        "# d_rip >= 0.15 -> \"ripening\"                                # 334\n"
        "# d_wrk >= 0.2  -> \"wrinkling\"                               # 336\n"
        "# dehydration >= 0.30 -> \"dehydration\"                        # 338\n"
        "# d_rip>=0.15 AND d_wrk>=0.2 -> \"deteriorating\"              # 340"
    )

    doc.add_heading("12.5 ヘルス判定 (runtime.py:387-404)", level=2)
    tbl(["判定", "条件"], [
        ["insufficient", "追跡実が 0 個"],
        ["declining", "wrinkling >= max(1, n/2) OR dehydrating >= max(1, n/2)"],
        ["maturing", "ripening >= max(1, n/2)"],
        ["mixed", "任意のフラグがあるが一方的でない"],
        ["stable", "フラグなし"],
    ])
    doc.add_paragraph(
        "加えて、notes リストに個別のアラートテキストを追加 (runtime.py:361-385): "
        "ripeness 上昇、wrinkling 増加、green_coverage 減少、fruit_count 減少、"
        "leaf_count 減少、一時的 dropout 検出。"
    )


def _s13_yaml(doc, code, tbl):
    doc.add_page_break()
    doc.add_heading("13. config/runtime.yaml パラメータ仕様", level=1)
    doc.add_paragraph(
        "load_runtime_config() (runtime.py:89-99) が "
        "DEFAULTS 辞書を基盤として、yaml の内容で上書きする。"
        "yaml にないキーはデフォルト値がそのまま使われる。"
    )
    doc.add_heading("13.1 runtime セクション", level=2)
    tbl(["キー", "デフォルト", "説明"], [
        ["max_width", "1280", "リサイズ上限 (px)"],
        ["jpeg_quality", "90", "JPEG 品質"],
        ["camera_warmup_frames", "8", "スキップフレーム数"],
    ])
    doc.add_heading("13.2 detection セクション", level=2)
    doc.add_paragraph(
        "本番 runtime.yaml の全パラメータは Section 3.1 の DEFAULTS 表に記載済み。"
        "runtime.yaml はそれらを上書きする目的でのみ使用される。"
        "runtime.yaml に記載がないパラメータは DEFAULTS の値が適用される。"
    )
    doc.add_heading("13.3 video セクション", level=2)
    tbl(["キー", "デフォルト", "説明"], [
        ["frame_interval", "10", "フレーム間引き間隔"],
        ["max_frames", "500", "最大解析フレーム数"],
        ["output_fps", "5", "出力動画 FPS"],
        ["track_max_age", "30", "追跡 ID 保持フレーム数"],
        ["track_iou_threshold", "0.3", "IoU マッチング閾値"],
    ])


def _s14_cli(doc, code, tbl):
    doc.add_page_break()
    doc.add_heading("14. olivevision.py CLI/GUI アーキテクチャ", level=1)
    doc.add_heading("14.1 CLI コマンド", level=2)
    tbl(["コマンド", "説明"], [
        ["analyze", "画像/動画解析 -> アノテーション + JSON + SQLite 保存"],
        ["capture", "カメラ 1 枚撮影 -> 解析"],
        ["monitor", "定期撮影・解析 (Ctrl+C で停止)"],
        ["status", "SQLite 直近観測を表示"],
        ["export", "SQLite -> CSV エクスポート"],
        ["trend", "ヘルストレンド分析レポート表示"],
        ["video", "動画フレーム解析"],
        ["gui", "Tkinter GUI 起動"],
    ])
    doc.add_heading("14.2 GUI 構成 (Tkinter ダークテーマ)", level=2)
    doc.add_paragraph("カラーパレット: Catppuccin Mocha")
    tbl(["用途", "HEX"], [
        ["背景", "#1e1e2e"],
        ["アクセント", "#a6e3a1"],
        ["テキスト", "#cdd6f4"],
        ["カード背景", "#313244"],
    ])
    doc.add_paragraph(
        "ツールバー: Open Image / Capture / Open Video / History / Trend / Settings\n"
        "タブ: Log / History / Hue Histogram / Timeline / Why? / Diagnostics\n"
        "パラメータスライダー: 葉 Hue Min/Max, Sat/Val Min, 実 Hue Min/Max 等\n"
        "検出モード選択: multi_signal / kmeans / grabcut / adaptive\n"
        "統計カード: LEAVES / FRUITS / GREEN% を大文字テキストで表示"
    )


def _s15_output(doc, code, tbl):
    doc.add_page_break()
    doc.add_heading("15. 出力仕様", level=1)

    doc.add_heading("15.1 JSON 出力 (outputs/observations/)", level=2)
    doc.add_paragraph(
        "save_observation() (runtime.py:1811) が生成。"
        "ファイル名: observation_{YYYYMMDD_HHMMSS_ffffff}.json"
    )
    doc.add_heading("15.1.1 leaf_objects[] のフィールド (runtime.py:1689-1701)", level=2)
    tbl(["フィールド", "型", "説明"], [
        ["confidence", "float", "検出信頼度"],
        ["area", "int", "面積 (px)"],
        ["aspect", "float", "アスペクト比"],
        ["solidity", "float", "凸包充填率"],
        ["ellipse_axis_ratio", "float", "楕円軸比"],
        ["num_defects", "int", "convexity defect 数"],
        ["mean_defect_depth", "float", "平均 defect 深度"],
        ["curl_score", "float", "巻き込みスコア (0-1)"],
        ["curl_label", "str", "flat/slight_curl/curled/heavily_curled"],
        ["color_consistency", "float", "1.0 - min(1.0, hue_std/50.0)"],
        ["edge_density", "float", "mask 境界と画像エッジの重なり率"],
        ["blur_level", "float", "ローカルぼけレベル"],
        ["center_x", "float", "重心 X"],
        ["center_y", "float", "重心 Y"],
    ])

    doc.add_heading("15.1.2 fruit_objects[] のフィールド (runtime.py:1702-1722)", level=2)
    tbl(["フィールド", "型", "説明"], [
        ["confidence", "float", "検出信頼度"],
        ["area", "int", "面積 (px)"],
        ["aspect", "float", "アスペクト比"],
        ["solidity", "float", "凸包充填率"],
        ["circularity", "float", "円形度"],
        ["ellipse_axis_ratio", "float", "楕円軸比"],
        ["color_consistency", "float", "色の一貫性"],
        ["edge_density", "float", "エッジ密度"],
        ["blur_level", "float", "ローカルぼけレベル"],
        ["internal_texture", "float", "内部テクスチャ (gray std)"],
        ["hue", "float", "平均 Hue"],
        ["saturation", "float", "平均彩度"],
        ["lab_b", "float", "LAB b-channel"],
        ["maturity", "str", "green/yellow_green/purple/black/transitioning"],
        ["center_x", "float", "重心 X"],
        ["center_y", "float", "重心 Y"],
        ["wrinkle_score", "float", "シワスコア (0-1)"],
        ["wrinkle_label", "str", "smooth/slightly_wrinkled/wrinkled/heavily_wrinkled"],
        ["wrinkle_reliable", "bool", "シワ検出の信頼性"],
        ["ridge_density", "float", "リッジ密度"],
        ["detect_evidence", "list", "検出シグナル名のリスト"],
        ["signal_ratios", "dict", "各シグナルの overlap ratio"],
        ["edge_touch", "bool", "画像エッジに接触"],
        ["low_signal", "bool", "シグナル強度が弱い"],
    ])

    doc.add_heading("15.1.3 pipeline_diagnostics (runtime.py:1774-1808)", level=2)
    code(
        "{\n"
        "  \"leaves\": {\n"
        "    \"candidates\": 57,       # フィルタ前候補数\n"
        "    \"accepted\": 2,          # フィルタ通過数\n"
        "    \"rejected\": 55,         # 除外数\n"
        "    \"rejected_by\": {        # 除外理由別カウント\n"
        "      \"area\": 52,\n"
        "      \"aspect\": 3\n"
        "    }\n"
        "  },\n"
        "  \"fruits\": {\n"
        "    \"candidates\": 3,\n"
        "    \"accepted\": 1,\n"
        "    \"rejected\": 2,\n"
        "    \"rejected_by\": { \"circularity\": 2 }\n"
        "  },\n"
        "  \"signals\": {\n"
        "    \"yellow_green_mask\": { \"pixels\": 1234, \"pct\": 2.5 },\n"
        "    \"ripe_mask\": { \"pixels\": 567, \"pct\": 1.1 },\n"
        "    \"dark_mask\": { \"pixels\": 89, \"pct\": 0.2 },\n"
        "    \"hough_circle_mask\": { \"pixels\": 200, \"pct\": 0.4 }\n"
        "  },\n"
        "  \"accepted_fruit_mask_pct\": 1.23\n"
        "}"
    )

    doc.add_heading("15.2 アノテーション画像", level=2)
    doc.add_paragraph(
        "_snap_contour_to_edges (runtime.py:717) で輪郭をエッジにスナップしてから描画。"
        "葉は緑 (50,220,50)、実はオレンジ (0,150,255)。"
        "各オブジェクトに confidence ラベル、フレーム左上に Leaves/Fruits カウント、"
        "Green%/Leaf Stage/Fruit Maturity を描画。"
    )


def _s16_tests(doc, code, tbl):
    doc.add_page_break()
    doc.add_heading("16. tests/test_runtime.py 回帰テスト (7件)", level=1)
    tbl(["テスト名", "概要", "検証内容"], [
        ["test_analysis_persists_result_and_export",
         "黒画像に緑矩形 -> 解析 -> DB 保存",
         "green_coverage > 0, CSV エクスポート成功"],
        ["test_colour_and_shape_filters_reject_non_olive_regions",
         "茶色土壌 + 肌色 -> 検出なし",
         "leaf_count == 0, fruit_count == 0"],
        ["test_result_includes_maturity_breakdown_and_cover",
         "緑実 + 黄緑実 -> 熟度分析",
         "maturity_breakdown 合計 == fruit_count"],
        ["test_watershed_splits_touching_fruits",
         "2つの接触する円 -> watershed 分割",
         ">= 2 個に分割"],
        ["test_health_trend_tracks_fruits_and_detects_changes",
         "3日間シーケンス -> ヘルストレンド",
         "ripening, wrinkling, deteriorating フラグ"],
        ["test_gt_6497_fruit_detection_recall",
         "IMG_6497.jpg + GT JSON -> 検出率",
         "recall == 1.0, precision == 1.0"],
    ])
    doc.add_paragraph(
        "テストは ML 依存 (lightgbm, pandas 等) を使用しない。"
        "runtime.py のみで完結するオフラインテスト。"
    )


def _s17_tools(doc, code, tbl):
    doc.add_heading("17. デバッグツール群", level=1)
    doc.add_heading("17.1 tools/check_hough.py", level=2)
    doc.add_paragraph(
        "Hough 円検出のシグナルエビデンスを可視化・統計。"
        "各色帯の画素数・割合・Hough 円の検出状況を出力。"
    )
    doc.add_heading("17.2 tools/check_cur.py", level=2)
    doc.add_paragraph(
        "シワ/巻き込みのスコアリング結果をデバッグ表示。"
        "各オブジェクトの wrinkle_score, curl_score, リッジ密度, "
        "convexity defect 詳細を出力。"
    )


def _s18_legacy(doc, code, tbl):
    doc.add_heading("18. レガシーモジュール", level=1)
    doc.add_heading("18.1 src/detection.py (238行)", level=2)
    doc.add_paragraph(
        "ObjectDetector クラス。config.yaml の HSV パラメータを使用。"
        "runtime.py の _build_leaf_mask / _build_fruit_mask とは独立実装。"
    )
    doc.add_heading("18.2 src/color_analysis.py (228行)", level=2)
    doc.add_paragraph(
        "ColorAnalyzer クラス。HSV 平均から葉色/実熟度を分類。"
        "runtime.py の _classify_leaf_color / _classify_fruit_maturity と同様のロジック。"
    )
    doc.add_heading("18.3 src/feature_extraction.py (345行)", level=2)
    doc.add_paragraph(
        "FeatureExtractor クラス。ML 学習用の特徴量抽出。"
        "時間的/葉/実/色/画像全体の特徴量を生成。"
    )
    doc.add_heading("18.4 config/config.yaml", level=2)
    doc.add_paragraph(
        "レガシー設定。runtime.yaml を使用する runtime.py とは独立。"
        "preprocessing, leaf_detection, fruit_detection, machine_learning, output, database, logging のセクションを持つ。"
    )
