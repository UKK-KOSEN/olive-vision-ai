"""
OliveVision AI - 背景除去モジュール
"""

import cv2
import numpy as np
from typing import Tuple, Dict
import logging


class BackgroundRemover:
    """
    背景を除去するクラス（複数の手法）
    """
    
    def __init__(self, logger: logging.Logger = None):
        """
        初期化
        
        Args:
            logger: ロガーオブジェクト
        """
        self.logger = logger
    
    def remove_by_hsv(self, image: np.ndarray, 
                     hue_range: Tuple = (0, 180),
                     sat_range: Tuple = (0, 50),
                     val_range: Tuple = (0, 50)) -> np.ndarray:
        """
        HSV値で背景（暗色）を除去
        
        Args:
            image: BGR画像
            hue_range: Hue範囲
            sat_range: Saturation範囲
            val_range: Value範囲（低い値が背景）
        
        Returns:
            背景を除去したマスク
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        lower = np.array([hue_range[0], sat_range[0], val_range[0]])
        upper = np.array([hue_range[1], sat_range[1], val_range[1]])
        
        # 背景マスク
        bg_mask = cv2.inRange(hsv, lower, upper)
        
        # 反転して前景マスク
        fg_mask = cv2.bitwise_not(bg_mask)
        
        return fg_mask
    
    def remove_by_grabcut(self, image: np.ndarray, rect: Tuple = None,
                         iterations: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """
        GrabCutアルゴリズムで背景を除去
        
        Args:
            image: BGR画像
            rect: 対象領域 (x, y, width, height)。Noneの場合は全体
            iterations: イテレーション数
        
        Returns:
            (マスク, 前景画像)
        """
        if rect is None:
            # 画像全体を対象
            h, w = image.shape[:2]
            rect = (10, 10, w-20, h-20)
        
        # マスク初期化
        mask = np.zeros(image.shape[:2], np.uint8)
        
        # 背景・前景の初期値
        bg_model = np.zeros((1, 65), np.float64)
        fg_model = np.zeros((1, 65), np.float64)
        
        # GrabCut実行
        cv2.grabCut(image, mask, rect, bg_model, fg_model, iterations,
                   cv2.GC_INIT_WITH_RECT)
        
        # マスクを2値化（前景のみ）
        mask = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype('uint8')
        
        # 前景画像
        fg_image = cv2.bitwise_and(image, image, mask=mask)
        
        return mask, fg_image
    
    def remove_by_canny(self, image: np.ndarray, 
                       threshold1: int = 50, threshold2: int = 150) -> np.ndarray:
        """
        Cannyエッジ検出と膨張で背景を除去
        
        Args:
            image: BGR画像
            threshold1: Canny下限値
            threshold2: Canny上限値
        
        Returns:
            背景を除去したマスク
        """
        # グレースケール化
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # エッジ検出
        edges = cv2.Canny(gray, threshold1, threshold2)
        
        # 膨張処理で領域を拡張
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        dilated = cv2.dilate(edges, kernel, iterations=3)
        
        # 閉じる処理で穴を埋める
        closed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel, iterations=3)
        
        return closed
    
    def remove_by_contour_analysis(self, image: np.ndarray,
                                   min_area: int = 100) -> np.ndarray:
        """
        輪郭解析で背景を除去
        
        Args:
            image: BGR画像
            min_area: 最小領域面積
        
        Returns:
            背景を除去したマスク
        """
        # グレースケール化と二値化
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 輪郭抽出
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # マスク作成
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        
        # 大きい輪郭のみを描画
        for contour in contours:
            if cv2.contourArea(contour) > min_area:
                cv2.drawContours(mask, [contour], 0, 255, -1)
        
        return mask
    
    def remove_by_kmeans(self, image: np.ndarray, k: int = 3) -> np.ndarray:
        """
        K-meansクラスタリングで背景を除去
        
        Args:
            image: BGR画像
            k: クラスタ数
        
        Returns:
            背景を除去したマスク
        """
        # ピクセルをベクトル化
        pixel_values = image.reshape((-1, 3))
        pixel_values = np.float32(pixel_values)
        
        # K-means
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        _, labels, centers = cv2.kmeans(pixel_values, k, None, criteria, 10,
                                       cv2.KMEANS_RANDOM_CENTERS)
        
        # 背景は通常最も大きなクラスター
        unique, counts = np.unique(labels, return_counts=True)
        bg_label = unique[np.argmax(counts)]
        
        # マスク作成
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        mask[labels.reshape(image.shape[:2]) != bg_label] = 255
        
        return mask
    
    def adaptive_background_removal(self, image: np.ndarray,
                                   config: Dict = None) -> np.ndarray:
        """
        環境に応じて最適な背景除去方法を自動選択
        
        Args:
            image: BGR画像
            config: 設定辞書
        
        Returns:
            背景を除去したマスク
        """
        # 画像の特性を分析
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # コントラスト計算
        contrast = np.std(gray)
        
        # 動的範囲計算
        dynamic_range = np.max(gray) - np.min(gray)
        
        if self.logger:
            self.logger.debug(f"コントラスト: {contrast:.2f}, 動的範囲: {dynamic_range}")
        
        # 背景色の判定
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        s_mean = np.mean(hsv[:, :, 1])
        
        # コントラストが高い場合: Cannyを使用
        if contrast > 50:
            mask = self.remove_by_canny(image, 30, 100)
        # 彩度が低い（灰色背景）場合: HSVを使用
        elif s_mean < 80:
            mask = self.remove_by_hsv(image, (0, 180), (0, 80), (0, 100))
        # その他: K-meansを使用
        else:
            mask = self.remove_by_kmeans(image, k=3)
        
        return mask
    
    def apply_morphological_cleanup(self, mask: np.ndarray,
                                   kernel_size: int = 5,
                                   iterations: int = 2) -> np.ndarray:
        """
        モルフォロジー処理でマスクをクリーンアップ
        
        Args:
            mask: 入力マスク
            kernel_size: カーネルサイズ
            iterations: イテレーション数
        
        Returns:
            クリーンアップされたマスク
        """
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, 
                                          (kernel_size, kernel_size))
        
        # オープニング（小さなノイズを除去）
        opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=iterations)
        
        # クロージング（穴を埋める）
        cleaned = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel, iterations=iterations)
        
        return cleaned
