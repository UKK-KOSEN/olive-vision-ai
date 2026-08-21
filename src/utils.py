"""
OliveVision AI - ユーティリティ関数
"""

import cv2
import numpy as np
import yaml
import logging
from pathlib import Path
from typing import Dict, Tuple, List


def load_config(config_path: str = "config/config.yaml") -> Dict:
    """
    YAML設定ファイルを読み込む
    
    Args:
        config_path: 設定ファイルのパス
    
    Returns:
        設定辞書
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config


def setup_logger(log_path: str = "outputs/olive_analysis.log") -> logging.Logger:
    """
    ロガーを設定
    
    Args:
        log_path: ログファイルのパス
    
    Returns:
        ロガーオブジェクト
    """
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("OliveVisionAI")
    logger.setLevel(logging.INFO)
    
    # ファイルハンドラ
    fh = logging.FileHandler(log_path, encoding='utf-8')
    fh.setLevel(logging.INFO)
    
    # コンソールハンドラ
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # フォーマッタ
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger


def load_image(image_path: str) -> np.ndarray:
    """
    画像ファイルを読み込む
    
    Args:
        image_path: 画像ファイルのパス
    
    Returns:
        BGR形式のnumpy配列
    """
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"画像ファイルが読み込めません: {image_path}")
    return image


def save_image(image: np.ndarray, output_path: str) -> None:
    """
    画像をファイルに保存
    
    Args:
        image: numpy配列の画像
        output_path: 出力ファイルのパス
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(output_path, image)


def rgb_to_hsv(image_bgr: np.ndarray) -> np.ndarray:
    """
    BGR画像をHSV色空間に変換
    
    Args:
        image_bgr: BGR形式の画像
    
    Returns:
        HSV形式の画像
    """
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)


def rgb_to_lab(image_bgr: np.ndarray) -> np.ndarray:
    """
    BGR画像をLab色空間に変換
    
    Args:
        image_bgr: BGR形式の画像
    
    Returns:
        Lab形式の画像
    """
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    return cv2.cvtColor(image_rgb, cv2.COLOR_RGB2LAB)


def apply_gaussian_blur(image: np.ndarray, kernel_size: int = 5) -> np.ndarray:
    """
    ガウシアンフィルターを適用
    
    Args:
        image: 入力画像
        kernel_size: カーネルサイズ（奇数）
    
    Returns:
        フィルター後の画像
    """
    if kernel_size % 2 == 0:
        kernel_size += 1
    return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)


def apply_clahe(image_gray: np.ndarray, clip_limit: float = 2.0, 
                grid_size: int = 8) -> np.ndarray:
    """
    CLAHE（局所コントラスト強調）を適用
    
    Args:
        image_gray: グレースケール画像
        clip_limit: コントラスト制限値
        grid_size: グリッドサイズ
    
    Returns:
        CLAHE適用後の画像
    """
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid_size, grid_size))
    return clahe.apply(image_gray)


def find_contours(binary_image: np.ndarray) -> List[np.ndarray]:
    """
    二値画像から輪郭を検出
    
    Args:
        binary_image: 二値化された画像
    
    Returns:
        輪郭のリスト
    """
    contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, 
                                    cv2.CHAIN_APPROX_SIMPLE)
    return contours


def draw_contours(image: np.ndarray, contours: List[np.ndarray], 
                  color: Tuple = (0, 255, 0), thickness: int = 2) -> np.ndarray:
    """
    輪郭を画像に描画
    
    Args:
        image: 入力画像
        contours: 輪郭のリスト
        color: 色（BGR）
        thickness: 線の太さ
    
    Returns:
        輪郭が描画された画像
    """
    return cv2.drawContours(image.copy(), contours, -1, color, thickness)


def calculate_circularity(area: float, perimeter: float) -> float:
    """
    円形度を計算
    
    円形度 = 4πA / P²
    
    Args:
        area: 領域の面積
        perimeter: 領域の周囲長
    
    Returns:
        円形度（0-1）
    """
    if perimeter == 0:
        return 0
    return 4 * np.pi * area / (perimeter ** 2)


def calculate_solidity(area: float, convex_area: float) -> float:
    """
    Solidityを計算
    
    Solidity = Area / Convex Hull Area
    
    Args:
        area: 領域の面積
        convex_area: 凸包の面積
    
    Returns:
        Solidity（0-1）
    """
    if convex_area == 0:
        return 0
    return area / convex_area


def get_contour_properties(contour: np.ndarray) -> Dict:
    """
    輪郭から複数のプロパティを計算
    
    Args:
        contour: 輪郭
    
    Returns:
        プロパティの辞書
    """
    area = cv2.contourArea(contour)
    perimeter = cv2.arcLength(contour, True)
    
    # 外接矩形
    x, y, w, h = cv2.boundingRect(contour)
    
    # 最小外接円
    (cx, cy), radius = cv2.minEnclosingCircle(contour)
    
    # 凸包
    hull = cv2.convexHull(contour)
    convex_area = cv2.contourArea(hull)
    
    # 円形度とSolidity
    circularity = calculate_circularity(area, perimeter)
    solidity = calculate_solidity(area, convex_area)
    
    return {
        'area': area,
        'perimeter': perimeter,
        'x': x,
        'y': y,
        'width': w,
        'height': h,
        'center_x': cx,
        'center_y': cy,
        'radius': radius,
        'circularity': circularity,
        'solidity': solidity,
        'aspect_ratio': float(w) / h if h != 0 else 0,
        'extent': area / (w * h) if (w * h) != 0 else 0
    }


def color_difference_lab(lab1: np.ndarray, lab2: np.ndarray) -> float:
    """
    Lab色空間での色差（ΔE）を計算
    
    ΔE = √((L1-L2)² + (a1-a2)² + (b1-b2)²)
    
    Args:
        lab1: Lab色1
        lab2: Lab色2
    
    Returns:
        色差
    """
    return np.sqrt(np.sum((lab1 - lab2) ** 2))


def create_mask_from_hsv_range(hsv_image: np.ndarray, 
                               hue_range: Tuple, 
                               sat_range: Tuple, 
                               val_range: Tuple) -> np.ndarray:
    """
    HSV範囲からマスクを作成
    
    Args:
        hsv_image: HSV画像
        hue_range: Hue範囲 [min, max]
        sat_range: Saturation範囲 [min, max]
        val_range: Value範囲 [min, max]
    
    Returns:
        二値マスク
    """
    lower = np.array([hue_range[0], sat_range[0], val_range[0]])
    upper = np.array([hue_range[1], sat_range[1], val_range[1]])
    return cv2.inRange(hsv_image, lower, upper)


def apply_morphology(binary_image: np.ndarray, operation: str = 'close',
                     kernel_size: int = 5) -> np.ndarray:
    """
    モルフォロジー処理を適用
    
    Args:
        binary_image: 二値画像
        operation: 処理の種類 ('open', 'close', 'erode', 'dilate')
        kernel_size: カーネルサイズ
    
    Returns:
        処理後の画像
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    
    if operation == 'open':
        return cv2.morphologyEx(binary_image, cv2.MORPH_OPEN, kernel)
    elif operation == 'close':
        return cv2.morphologyEx(binary_image, cv2.MORPH_CLOSE, kernel)
    elif operation == 'erode':
        return cv2.erode(binary_image, kernel, iterations=1)
    elif operation == 'dilate':
        return cv2.dilate(binary_image, kernel, iterations=1)
    else:
        raise ValueError(f"Unknown operation: {operation}")
