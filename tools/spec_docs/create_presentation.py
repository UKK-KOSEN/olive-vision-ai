"""OliveVision AI 解説用PowerPointスライド - 最近作業ファイル中心・技術詳細版"""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
import os

# カラーパレット
GREEN = RGBColor(0x2E, 0x7D, 0x32)
GREEN_LIGHT = RGBColor(0x4C, 0xAF, 0x50)
ORANGE = RGBColor(0xE6, 0x51, 0x00)
BLUE = RGBColor(0x15, 0x65, 0xC0)
RED = RGBColor(0xC6, 0x28, 0x28)
DARK_BG = RGBColor(0x1A, 0x1A, 0x2E)
CARD_BG = RGBColor(0xF5, 0xF5, 0xF5)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BLACK = RGBColor(0x21, 0x21, 0x21)
GRAY = RGBColor(0x61, 0x61, 0x61)
LIGHT_GREEN_BG = RGBColor(0xE8, 0xF5, 0xE9)
LIGHT_BLUE_BG = RGBColor(0xE3, 0xF2, 0xFD)
LIGHT_ORANGE_BG = RGBColor(0xFF, 0xF3, 0xE0)
LIGHT_RED_BG = RGBColor(0xFF, 0xEB, 0xEE)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

def set_slide_bg(slide, color):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color

def add_title_slide(title, subtitle, bg_color=DARK_BG):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, bg_color)
    txBox = slide.shapes.add_textbox(Inches(1), Inches(2.0), Inches(11.333), Inches(1.5))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(48)
    p.font.bold = True
    p.font.color.rgb = GREEN_LIGHT
    p.alignment = PP_ALIGN.CENTER
    txBox2 = slide.shapes.add_textbox(Inches(1), Inches(3.6), Inches(11.333), Inches(1.2))
    tf2 = txBox2.text_frame
    tf2.word_wrap = True
    p2 = tf2.paragraphs[0]
    p2.text = subtitle
    p2.font.size = Pt(20)
    p2.font.color.rgb = RGBColor(0xBD, 0xBD, 0xBD)
    p2.alignment = PP_ALIGN.CENTER
    return slide

def add_section_slide(title, number=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, DARK_BG)
    if number:
        txN = slide.shapes.add_textbox(Inches(1), Inches(2.0), Inches(11.333), Inches(0.8))
        tfN = txN.text_frame
        pN = tfN.paragraphs[0]
        pN.text = number
        pN.font.size = Pt(24)
        pN.font.color.rgb = RGBColor(0x75, 0x75, 0x75)
        pN.alignment = PP_ALIGN.CENTER
    txBox = slide.shapes.add_textbox(Inches(1), Inches(2.8), Inches(11.333), Inches(1.5))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(40)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.alignment = PP_ALIGN.CENTER
    return slide

def add_content_slide(title, sections, bg_color=WHITE):
    """sections: list of (subtitle_or_None, bullets)"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, bg_color)
    # Title bar
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), prs.slide_width, Inches(1.0)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = GREEN
    shape.line.fill.background()
    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.12), Inches(12.333), Inches(0.75))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(26)
    p.font.bold = True
    p.font.color.rgb = WHITE

    txBox2 = slide.shapes.add_textbox(Inches(0.6), Inches(1.2), Inches(12.1), Inches(5.8))
    tf2 = txBox2.text_frame
    tf2.word_wrap = True
    first = True
    for subtitle, bullets in sections:
        if subtitle:
            if first:
                p = tf2.paragraphs[0]
                first = False
            else:
                p = tf2.add_paragraph()
                p.space_before = Pt(10)
            p.text = subtitle
            p.font.size = Pt(18)
            p.font.bold = True
            p.font.color.rgb = GREEN
            p.space_after = Pt(4)
        for b in bullets:
            if first:
                p = tf2.paragraphs[0]
                first = False
            else:
                p = tf2.add_paragraph()
            p.text = f"  {b}"
            p.font.size = Pt(14)
            p.font.color.rgb = BLACK
            p.space_after = Pt(2)
    return slide

def add_code_slide(title, code, caption=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, WHITE)
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), prs.slide_width, Inches(1.0)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = GREEN
    shape.line.fill.background()
    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.12), Inches(12.333), Inches(0.75))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(26)
    p.font.bold = True
    p.font.color.rgb = WHITE

    # Code block
    code_card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.5), Inches(1.2), Inches(12.333), Inches(5.5)
    )
    code_card.fill.solid()
    code_card.fill.fore_color.rgb = RGBColor(0x26, 0x32, 0x38)
    code_card.line.fill.background()

    txCode = slide.shapes.add_textbox(Inches(0.7), Inches(1.35), Inches(11.9), Inches(5.2))
    tfCode = txCode.text_frame
    tfCode.word_wrap = True
    lines = code.strip().split("\n")
    for i, line in enumerate(lines):
        if i == 0:
            p = tfCode.paragraphs[0]
        else:
            p = tfCode.add_paragraph()
        p.text = line
        p.font.size = Pt(11)
        p.font.name = "Consolas"
        p.font.color.rgb = RGBColor(0xA5, 0xD6, 0xA7)
        p.space_after = Pt(1)

    if caption:
        txCap = slide.shapes.add_textbox(Inches(0.6), Inches(6.85), Inches(12.1), Inches(0.5))
        tfCap = txCap.text_frame
        pCap = tfCap.paragraphs[0]
        pCap.text = caption
        pCap.font.size = Pt(11)
        pCap.font.color.rgb = GRAY
    return slide

def add_table_slide(title, headers, rows):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, WHITE)
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), prs.slide_width, Inches(1.0)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = GREEN
    shape.line.fill.background()
    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.12), Inches(12.333), Inches(0.75))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(26)
    p.font.bold = True
    p.font.color.rgb = WHITE

    cols = len(headers)
    table_shape = slide.shapes.add_table(
        len(rows) + 1, cols, Inches(0.5), Inches(1.2), Inches(12.333), Inches(5.8)
    )
    table = table_shape.table
    for i, h in enumerate(headers):
        cell = table.cell(0, i)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = GREEN
        p = cell.text_frame.paragraphs[0]
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = WHITE
        p.alignment = PP_ALIGN.CENTER
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            cell = table.cell(r + 1, c)
            cell.text = str(val)
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(0xF5, 0xF5, 0xF5) if r % 2 == 0 else WHITE
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(12)
            p.font.color.rgb = BLACK
    return slide


# ============================================================
# SLIDES
# ============================================================

add_title_slide(
    "OliveVision AI",
    "AI搭載 オリーブ樹長期モニタリングシステム\n"
    "解説スライド (技術詳細版)\n\n"
    "2026年8月"
)

add_content_slide("目次", [
    ("1. プロジェクト全体像とファイル構成", []),
    ("2. 最近作業しているファイル一覧", []),
    ("3. src/runtime.py - コア検出エンジン", []),
    ("4. 葉マスク構築: マルチカラースペース融合", []),
    ("5. 実マスク構築: シグナルベース検出", []),
    ("6. ぼけ検出とアダプティブ前処理", []),
    ("7. シワ(褶皴)スコアリング", []),
    ("8. 葉巻き込み(Curl)スコアリング", []),
    ("9. マルチスケール検出とマージ", []),
    ("10. オブジェクト追跡とヘルストレンド", []),
    ("11. config/runtime.yaml - パラメータ仕様", []),
    ("12. olivevision.py - CLI/GUIアーキテクチャ", []),
    ("13. テストと回帰ガード", []),
    ("14. 実行結果の出力仕様", []),
])

# 2. 最近作業ファイル
add_table_slide("最近作業しているファイル (2026/08/17 更新順)",
    ["ファイル", "最終更新", "主な役割"],
    [
        ["src/runtime.py", "12:20", "検出エンジン本体 (Analyzer, Store, 健康トレンド)"],
        ["config/runtime.yaml", "12:19", "検出パラメータ (HSV, 面積, シワ閾値等)"],
        ["tools/check_hough.py", "12:27", "シグナルエビデンスのデバッグツール"],
        ["tools/check_cur.py", "12:17", "シワ/巻き込みのデバッグツール"],
        ["tests/test_runtime.py", "11:20", "オフラインスモークテスト (7テスト)"],
        ["olivevision.py", "11:24", "CLI/GUI (Tkinter, ダークテーマ)"],
        ["outputs/observations/*.json", "12:06", "実行結果のJSON出力"],
        ["data/database/olivevision.db", "12:06", "SQLite時系列データベース"],
    ]
)

# 3. runtime.py概要
add_section_slide("src/runtime.py\nコア検出エンジン", "Part 1")

add_content_slide("src/runtime.py - モジュール構成 (2,200行超)", [
    ("主要クラス", [
        "Analyzer: 画像解析のメインパイプライン (analyzeメソッド)",
        "Store: SQLite時系列データベース (add, recent, export_csv)",
        "VideoAnalyzer: 動画フレーム解析 + マルチターゲット追跡",
        "_CentroidTracker: 重心ベースのマルチオブジェクトトラッカー",
    ]),
    ("主要ヘルパー関数 (検出)", [
        "_build_leaf_mask: マルチカラースペース葉マスク構築",
        "_build_fruit_mask: シグナルベース実マスク構築",
        "_filter_contours: 面積・形状・エッジ密度フィルタリング",
        "_watershed_split: 接触blob分離 (Watershed変換)",
        "_hough_circles_fruit: Hough円検出による実候補検出",
    ]),
    ("前処理・補正", [
        "_adaptive_preprocess: バイラテラルフィルタ + CLAHE + ガウシアン",
        "_unsharp_mask: アンシャープマスクによるシャープニング",
        "_deblur_adaptive: ローカルシャープネスマップベースの領域別デブラ",
        "_adaptive_canny: Otsu自動閾値によるCannyエッジ検出",
    ]),
])

add_content_slide("src/runtime.py - Analyzer.analyze() パイプライン", [
    ("処理フロー (analyzeメソッド内)", [
        "1. _resize: max_width=1280でアスペクト比保持リサイズ",
        "2. _estimate_blur: Laplacian分散でぼけレベル算出 (0=鮮明, 1=非常にぼけ)",
        "3. _local_sharpness_map: 48x48ブロックごとのシャープネスマップ生成",
        "4. _adaptive_preprocess: バイラテラル + CLAHE + 必要に応じデブラ",
        "5. _deblur_adaptive: 混合フォーカス時のみ領域別強調",
        "6. detect_modeに応じて前景マスク生成 (multi_signal/kmeans/grabcut/adaptive)",
        "7. _build_leaf_mask: HSV + ExG + CGI + LAB + YCrCb 融合マスク",
        "8. _build_fruit_mask: 黄緑 + 紫 + 暗熟 + Hough円マスク",
        "9. _watershed_split: 接触実の分離",
        "10. _filter_contours: 面積/アスペクト比/solidity/circularity/テクスチャ",
        "11. シグナル割り当て: 各実候補のyellow_green/ripe/dark/hough_circle比率",
        "12. アノテーション画像生成 (エッジスナップ付き)",
    ]),
])

# 4. 葉マスク
add_content_slide("葉マスク構築: _build_leaf_mask (マルチカラースペース融合)", [
    ("6つのカラースペースから同時検証", [
        "HSV: Hue 30-95, Saturation >= 35, Value >= 25 → 緑色帯マスク",
        "Excess Green (ExG): (2G-R-B)/(R+G+B+1) * 128 + 128 → 植生指数",
        "CGI (Chlorophyll Green-Red): arctan2(G-R, G+R) → 葉緑素指標",
        "LAB a-channel: a < 118 → 緑色域 (赤が128より小さい)",
        "YCrCb: Cr < 130 → 緑色低彩度帯",
    ]),
    ("融合ロジック", [
        "HSV マスクが必須条件",
        "ExG, CGI, LAB, YCrCb のうち required_signals (1-2個) 以上が一致する必要あり",
        "ぼけレベル >= 0.75 の場合、required_signals を 1 に緩和",
        "最終マスク = HSV ∩ (multi_signal ∨ vegetation_union)",
    ]),
    ("後処理", [
        "Morphological close/open (楕円カーネル, ぼけでカーネル縮小)",
        "暗い画素 (V < 15) の抑制",
        "前景マスクとのAND制約",
        "_edge_refine_mask: Cannyエッジへ輪郭をスナップ",
    ]),
    ("コード例", [
        "relax = max(0.0, (blur_level - 0.5) * 2.0)  # ぼけ緩和係数",
        "sat_floor = int(max(25, spec['leaf_saturation_min'] - relax * 25))",
        "signals = exg + cgi + lab + ycrcb  # 各画素の一致数",
        "multi_signal = inRange(signals, required_signals, 255)",
    ]),
])

# 5. 実マスク
add_content_slide("実マスク構築: _build_fruit_mask (シグナルベース)", [
    ("3色帯 + Hough円の複合検出", [
        "黄色緑帯: HSV Hue 18-45, Sat >= 55, Val >= 65 + LAB b >= 145",
        "熟紫帯: HSV Hue 105-179, Sat >= 60, Val 55-220",
        "暗熟帯: HSV Hue 105-175, Sat >= 85, Val 25-55",
        "Hough円: dp=1.2, minDist=25, param1=80, param2=40",
    ]),
    ("検証フロー", [
        "1. 3色帯のOR統合 → 形態学処理",
        "2. 葉マスクの safe_leaf 領域を除外 (葉からの誤検出防止)",
        "3. 前景マスクとのAND制約",
        "4. Hough円マスクとの重複検証:",
        "   - 円と重なるblob → ブースト (circle_fruit)",
        "   - 円と離れたblob → 丸くて滑らかで実サイズなら rescue",
        "   - rescue条件: area 1400-4000, circularity >= 0.65, solidity >= 0.88, std <= 45",
    ]),
    ("自己証明rescueロジック", [
        "Hough円に検出されなかった実候補に対して:",
        "connectedComponentsWithStats で個別blobを検証",
        "内部テクスチャ (gray std) が低く、円形度・solidity が高い場合のみ救済",
        "blur_level >= 0.5 の場合、rescueは無効 (ぼけで平滑化が偽阳性を生む)",
    ]),
])

# 6. ぼけ検出
add_content_slide("ぼけ検出とアダプティブ前処理", [
    ("ぼけレベル算出", [
        "_estimate_blur: Laplacian(gray, CV_64F) の分散",
        "blur_level = min(1.0, max(0.0, (180.0 - blur_raw) / 160.0))",
        "blur_raw >= 180 → 0 (鮮明),  blur_raw = 20 → ~1.0 (非常にぼけ)",
    ]),
    ("ローカルシャープネスマップ", [
        "_local_sharpness_map: 48x48ブロックごとの Laplacian 分散を [0,1] 正規化",
        "_is_mixed_focus: ブロック間の変動係数 (CV > 1.0 で混合フォーカス判定)",
    ]),
    ("アダプティブ前処理パイプライン", [
        "1. バイラテラルフィルタ (d=9, sigmaColor=75, sigmaSpace=75) → エッジ保持ノイズ除去",
        "2. LAB変換 → L チャンネルに CLAHE (clipLimit=2.5, 8x8グリッド)",
        "3. ガウシアンブラー (k=5) → ノイズ平滑化",
        "4. blur_raw < 180 の場合 → _unsharp_mask (sigma=2.5, amount=1.8)",
    ]),
    ("領域別デブラ (_deblur_adaptive)", [
        "sharp_map > 0.6 の画素が15%以上 AND sharp_map < 0.3 の画素が30%以上 → 実行",
        "strong = unsharp(sigma=3.0, amount=1.8) / mild = unsharp(sigma=1.2, amount=0.6)",
        "weight = 1.0 - sharp_map (ぼけているほど strong を重視)",
        "GaussianBlur(weight, sigma=4) で滑らかに補間",
        "uniformBlur (全体ぼけ) は _adaptive_preprocess で処理済みなのでスキップ",
    ]),
])

# 7. シワスコア
add_content_slide("シワ(褶皴)スコアリング: _compute_wrinkle_score", [
    ("アルゴリズム概要", [
        "シワ = 実表面上の細長い高勾配リッジ (Sobel → 閾値処理 → 形態学)",
        "新鮮な実は滑らか (リッジ密度=0)、脱水したオリーブはリッジネットワークを生成",
    ]),
    ("計算ステップ", [
        "1. マスクを erosion で内部領域を抽出 (半径の25%カーネル)",
        "2. Sobel(gx, gy) → cv2.magnitude で勾配マップ",
        "3. Otsu閾値 + max(otsu, mean*1.4, 20.0) でリッジ閾値",
        "4. 4方向カーネル (横/縦/対角2本) で morphological open/close → 細線化",
        "5. density = thin_count / interior_count",
        "6. score = min(1.0, density * 3.0 + max(0, texture - 18.0) / 80.0)",
    ]),
    ("信頼性判定", [
        "interior_fraction < 0.30 → スコアをディスカウント",
        "area < 350px → 極端にディスカウント (小さな葉片がシワ誤判定されるのを防止)",
        "unreliable=True のオブジェクトは health verdict で信頼性が下がる",
    ]),
    ("ラベルリング", [
        "score < 0.25 → smooth",
        "0.25-0.45 → slightly_wrinkled",
        "0.45-0.70 → wrinkled",
        ">= 0.70 → heavily_wrinkled",
    ]),
])

# 8. 葉巻き込み
add_content_slide("葉巻き込み(Curl)スコアリング: _compute_leaf_curl_score", [
    ("生物学的背景", [
        "葉が内側へ巻き込む (巻き込み) は蒸散抑制のストレス応答",
        "平坦な葉は convex hull をよく埋める (solidity ≈ 1)",
        "巻き込んだ葉は細長いプロフィール + 深い凹みを示す",
    ]),
    ("3つの形状ヒントから 0-1 スコアを算出", [
        "solidity_gap = 1.0 - solidity (0=凸, 1=非常に凹む) → 重み 0.50",
        "defect_ratio = min(1.0, mean_defect_depth / sqrt(area) * 0.15) → 重み 0.30",
        "elongation = min(1.0, max(0, aspect - 1.5) / 5.0) → 重み 0.20",
        "score = 0.50 * gap + 0.30 * defect_ratio + 0.20 * elongation",
    ]),
    ("ラベルリング", [
        "score < 0.10 → flat",
        "0.10-0.25 → slight_curl",
        "0.25-0.50 → curled",
        ">= 0.50 → heavily_curled",
    ]),
    ("出力例 (observation JSON)", [
        '"leaf_curl_index": 0.203,  "curled_leaf_pct": 0.0',
        "→ 平均巻き込み=0.203 (slight_curl)、巻き込み葉割合=0.0%",
    ]),
])

# 9. マルチスケール
add_content_slide("マルチスケール検出とマージ: _merge_multiscale", [
    ("マルチスケール検出", [
        "scales = [0.75, 1.0, 1.3] (runtime.yaml で設定可能)",
        "各スケールで leaf_mask をリサイズ → 輪郭抽出 → 面積を逆スケール",
        "→ 小さい葉 (0.75x) 〜 大きい葉 (1.3x) を網羅的に検出",
    ]),
    ("マージ (_merge_multiscale)", [
        "面積降順でソート → 各輪郭について IoU > 0.35 の重複を除去",
        "大きいものから優先的に保持 → 小さい重複候補は削除",
    ]),
    ("大型コンポーネント分割 (_split_large_components)", [
        "connectedComponentsWithStats で個別コンポーネントを確認",
        "area > leaf_max_area (30000px) の大型blob → watershed で分割",
        "→ 重なり合った葉の群体を個別葉に分解してカウント可能に",
    ]),
    ("フィルタリング (_filter_contours)", [
        "葉: area 350-30000, aspect 1.0-12.0, solidity >= 0.58",
        "実: area 250-18000, aspect 0.45-2.4, solidity >= 0.72, circularity >= 0.50",
        "実: ellipse_axis_ratio <= 3.5 (細長い葉片の除外)",
        "実: internal_texture (gray std) <= 40.0 (滑らかさ検証)",
        "信頼度 = base_w * shape_score + color_consistency * 0.25 + edge_density * edge_weight",
        "ぼけオブジェクトの edge_weight を自動縮小 (0.25 - obj_blur * 0.15)",
    ]),
])

# 10. トラッキング
add_content_slide("オブジェクト追跡とヘルストレンド分析", [
    ("_CentroidTracker (重心ベース追跡)", [
        "D[i,j] = 重心間のユークリッド距離",
        "距離行列をグリーディにソート → D > 80px で未マッチは新規登録",
        "max_age=30 フレーム未検出で削除",
        "track_id → bounding box (x,y,w,h) とヒストリー (重心リスト) を管理",
    ]),
    ("analyze_health_trend (ヘルストレンド)", [
        "重複観測の削除: (date, source, leaf_count, fruit_count, green_coverage) でユニーク化",
        "低品質除外: green_coverage < 10.0% の観測をスキップ",
        "時系列スロープ: _linear_slope_per_day (最小二乗法, 24hあたりの変化量)",
        "実追跡: 位置 (center_x, center_y) で跨日マッチング (match_radius=60px)",
        "ripeness = ripe_signal + dark_signal の合計比率",
        "dehydration = wrinkle_contribution * 0.6 + shrink_contribution * 0.4",
    ]),
    ("ヘルス判定ロジック", [
        "stable: 有意な変化なし",
        "maturing: ripeningフラグが追跡実の半数以上",
        "declining: wrinkling or dehydration が追跡実の半数以上",
        "mixed: フラグがあるが一方的でない",
        "insufficient: 追跡実が0個",
    ]),
])

# 11. config
add_content_slide("config/runtime.yaml - 主要パラメータ仕様", [
    ("runtime セクション", [
        "max_width: 1280 — 入力画像のリサイズ上限 (アスペクト比保持)",
        "jpeg_quality: 90 — アノテーションJPEG保存品質",
        "camera_warmup_frames: 8 — カメラ起動時のスキップフレーム数",
    ]),
    ("detection セクション (葉)", [
        "leaf_hue: [30, 95] — HSV Hue帯 (緑色範囲)",
        "leaf_saturation_min: 35 / leaf_value_min: 25 — 彩度・明度下限",
        "leaf_min_area: 350 / leaf_max_area: 30000 — 面積フィルタ (px)",
        "leaf_min_aspect: 1.0 / leaf_max_aspect: 12.0 — アスペクト比フィルタ",
        "leaf_min_solidity: 0.58 — 凸包充填率の下限",
        "excess_green_min: 12 — ExG植被指数の閾値",
    ]),
    ("detection セクション (実)", [
        "fruit_hue_yellow: [18, 45] / fruit_hue_ripe: [105, 179]",
        "fruit_saturation_min: 55 / fruit_value_min: 65 / fruit_lab_b_min: 145",
        "fruit_min_area: 250 / fruit_max_area: 18000",
        "fruit_min_circularity: 0.50 / fruit_min_solidity: 0.72",
        "fruit_max_ellipse_ratio: 3.5 — 細長 blob の除外",
        "fruit_max_internal_std: 40.0 — 内部テクスチャ (滑らかさ) の上限",
        "fruit_no_circle_min_area: 1400 — Hough円なしでもrescueする最小面積",
    ]),
    ("シワ/検出モード", [
        "wrinkle_ridge_weight: 3.0 / wrinkle_texture_base: 18.0 / scale: 80.0",
        "wrinkle_smooth_max: 0.25 / slightly: 0.45 / wrinkled: 0.70",
        "detect_mode: multi_signal (kmeans|grabcut|bg_removal|edge_flood|adaptive)",
        "multiscale_scales: [0.75, 1.0, 1.3]",
        "watershed_mindist: 20 — 実分離の最小距離 (px)",
    ]),
])

# 12. olivevision.py
add_content_slide("olivevision.py - CLI/GUI アーキテクチャ", [
    ("CLIコマンド", [
        "analyze: 画像/動画を解析 → アノテーション + JSON + SQLite保存",
        "capture: カメラ1枚撮影 → 解析",
        "monitor: 指定間隔で繰り返し撮影・解析 (Ctrl+Cで停止)",
        "status: SQLite の直近観測を表示",
        "export: SQLite → CSV エクスポート",
        "trend: ヘルストレンド分析レポート表示",
        "video: 動画ファイルのフレーム解析",
        "gui: Tkinter GUI 起動",
    ]),
    ("GUI 特徴 (Tkinter ダークテーマ)", [
        "Catppuccin Mocha カラーパレット (BG=#1e1e2e, ACCENT=#a6e3a1)",
        "ツールバー: Open Image / Capture / Open Video / History / Trend / Settings",
        "タブ: Log / History / Hue Histogram / Timeline / Why? / Diagnostics",
        "パラメータスライダー: 葉Hue Min/Max, Sat/Val Min, 実Hue Min/Max 等",
        "検出モード選択: multi_signal / kmeans / grabcut / adaptive 等",
        "マスク表示トグル: Leaf / Fruit / FG マスクのオーバーレイ",
        "統計カード: LEAVES / FRUITS / GREEN% を大文字で表示",
    ]),
    ("GUI検出結果パネルの表示フィールド", [
        "leaf_count, fruit_count, green_coverage, fruit_cover_pct",
        "leaf_color_stage, leaf_senescence, leaf_avg_hue, leaf_confidence",
        "fruit_maturity, fruit_maturity_breakdown, wrinkled_fruit_count",
        "fruit_wrinkle_summary, fruit_avg_hue, fruit_avg_area, fruit_confidence",
        "leaf_roughness — 各フィールドは検出結果JSONから自動マッピング",
    ]),
])

# 13. テスト
add_content_slide("tests/test_runtime.py - オフラインテスト (7テスト)", [
    ("テスト一覧", [
        "test_analysis_persists_result_and_export:",
        "  → 黒画像に緑矩形を描画 → 解析 → green_coverage > 0, CSVエクスポート検証",
        "",
        "test_colour_and_shape_filters_reject_non_olive_regions:",
        "  → 茶色土壌 (BGR 35,80,130) + 肌色 (BGR 80,135,185) → 葉0, 実0",
        "",
        "test_result_includes_maturity_breakdown_and_cover:",
        "  → 緑実 + 黄緑実 → fruit_maturity_breakdown 合計 == fruit_count",
        "  → 各fruit_object に maturity, hue, ellipse_axis_ratio, wrinkle_* が存在",
        "",
        "test_watershed_splits_touching_fruits:",
        "  → 半径22の2円 (接触) → >= 2個に分割",
        "",
        "test_health_trend_tracks_fruits_and_detects_changes:",
        "  → 3日間のシーケンス → fruit #536 に ripening + wrinkling + deteriorating",
        "  → 重複観測 collapsed → unique=3",
        "",
        "test_gt_6497_fruit_detection_recall (回帰ガード):",
        "  → IMG_6497.jpg + GT JSON → recall=1.0, precision=1.0",
    ]),
])

# 14. 出力仕様
add_content_slide("出力仕様 (observation JSON)", [
    ("トップレベルフィールド (最近の実行結果より)", [
        "observed_at: ISO8601タイムスタンプ",
        "leaf_count / fruit_count / green_coverage",
        "leaf_color_stage (healthy_green/dark_green/yellow_green/yellow/brown/dead_brown)",
        "leaf_senescence: 0-100の枯れ具合",
        "fruit_maturity (green/yellow_green/purple/black/transitioning)",
        "fruit_maturity_breakdown: {purple: 1} 等",
        "wrinkled_fruit_count / fruit_wrinkle_summary: {smooth: n, slightly_wrinkled: n, ...}",
        "blur_score (Laplacian分散) / blur_level (0-1正規化値)",
        "leaf_curl_index / curled_leaf_pct",
    ]),
    ("個別オブジェクト情報", [
        "leaf_objects[]: confidence, area, aspect, solidity, ellipse_axis_ratio,",
        "  num_defects, mean_defect_depth, curl_score, curl_label,",
        "  color_consistency, edge_density, blur_level, center_x/y",
        "",
        "fruit_objects[]: confidence, area, aspect, solidity, circularity,",
        "  ellipse_axis_ratio, hue, saturation, lab_b, maturity,",
        "  wrinkle_score, wrinkle_label, wrinkle_reliable, ridge_density,",
        "  detect_evidence[], signal_ratios{}, edge_touch, low_signal",
    ]),
    ("パイプライン診断", [
        "pipeline_diagnostics.leaves: candidates=57, accepted=2, rejected_by={area:52, aspect:3}",
        "pipeline_diagnostics.fruits: candidates=3, accepted=1, rejected_by={circularity:2}",
        "pipeline_diagnostics.signals: 各色帯の画素数と割合",
        "signal_thresholds: {yellow_green:0.35, ripe:0.25, dark:0.25, hough_circle:0.20}",
    ]),
])

add_title_slide(
    "まとめ",
    "src/runtime.py (2,200行) が検出エンジンのほぼ全容を担い、\n"
    "マルチカラースペース融合、Hough円検出、シワ/巻き込みスコアリング、\n"
    "アダプティブデブラ、マルチスケール検出を統合。\n\n"
    "config/runtime.yaml でパラメータを外部化し、\n"
    "tests/test_runtime.py で回帰ガードを確保。\n\n"
    "olivevision.py がCLI/GUIを提供し、\n"
    "Raspberry Pi上でもML依存なしで動作する軽量ランタイムを実現。"
)

# 保存
output_path = os.path.join(os.path.dirname(__file__), "OliveVision_AI_技術解説.pptx")
prs.save(output_path)
print(f"saved: {output_path}")
