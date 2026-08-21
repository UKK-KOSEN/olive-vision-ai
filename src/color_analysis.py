"""
OliveVision AI - 色解析モジュール
"""

import cv2
import numpy as np
from typing import Dict


class ColorAnalyzer:
    """
    オリーブの色を分析するクラス
    """
    
    def __init__(self, config: Dict):
        """
        初期化
        
        Args:
            config: 設定辞書
        """
        self.config = config
    
    def analyze_leaf_color(self, image: np.ndarray, leaf_mask: np.ndarray) -> Dict:
        """
        葉の色を分析
        
        Args:
            image: BGR画像
            leaf_mask: 葉領域のマスク
        
        Returns:
            色解析結果の辞書
        """
        if np.sum(leaf_mask) == 0:
            return self._create_empty_color_dict()
        
        # HSV色空間での分析
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 平均Hue
        h_mean = cv2.mean(hsv_image[:,:,0], mask=leaf_mask)[0]
        s_mean = cv2.mean(hsv_image[:,:,1], mask=leaf_mask)[0]
        v_mean = cv2.mean(hsv_image[:,:,2], mask=leaf_mask)[0]
        
        # 色の判定
        color_stage = self._classify_leaf_color(h_mean)
        
        # 枯葉度合い
        senescence_degree = self._calculate_senescence_degree(h_mean, s_mean, v_mean)
        
        return {
            'mean_hue': h_mean,
            'mean_saturation': s_mean,
            'mean_value': v_mean,
            'color_stage': color_stage,
            'senescence_degree': senescence_degree,
        }
    
    def analyze_fruit_color(self, image: np.ndarray, fruit_mask: np.ndarray) -> Dict:
        """
        実の色を分析
        
        Args:
            image: BGR画像
            fruit_mask: 実領域のマスク
        
        Returns:
            色解析結果の辞書
        """
        if np.sum(fruit_mask) == 0:
            return self._create_empty_color_dict()
        
        # HSV色空間での分析
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 平均Hue
        h_mean = cv2.mean(hsv_image[:,:,0], mask=fruit_mask)[0]
        s_mean = cv2.mean(hsv_image[:,:,1], mask=fruit_mask)[0]
        v_mean = cv2.mean(hsv_image[:,:,2], mask=fruit_mask)[0]
        
        # 熟度判定
        maturity_stage = self._classify_fruit_maturity(h_mean)
        
        return {
            'mean_hue': h_mean,
            'mean_saturation': s_mean,
            'mean_value': v_mean,
            'maturity_stage': maturity_stage,
        }
    
    def _classify_leaf_color(self, hue: float) -> str:
        """
        Hue値から葉の色を分類
        
        Args:
            hue: Hue値（0-180 in OpenCV HSV）
        
        Returns:
            色ステージの名前
        """
        if hue > 70:  # 45-95の範囲の上部
            return 'healthy_green'
        elif hue > 50:
            return 'dark_green'
        elif hue > 35:
            return 'yellow_green'
        elif hue > 25:
            return 'yellow'
        elif hue > 15:
            return 'brown'
        else:
            return 'dead_brown'
    
    def _classify_fruit_maturity(self, hue: float) -> str:
        """
        Hue値から実の熟度を分類
        
        Args:
            hue: Hue値（0-180 in OpenCV HSV）
        
        Returns:
            熟度ステージの名前
        """
        if 30 <= hue <= 90:
            return 'green'
        elif 15 <= hue < 30:
            return 'yellow_green'
        elif 100 <= hue <= 135:
            return 'purple'
        elif hue < 15 or hue > 135:
            return 'black'
        else:
            return 'transitioning'
    
    def _calculate_senescence_degree(self, hue: float, saturation: float, 
                                    value: float) -> float:
        """
        枯葉度を計算（0-100%）
        
        Args:
            hue: Hue値
            saturation: Saturation値
            value: Value値
        
        Returns:
            枯葉度（%）
        """
        # Hueが低く、Saturationが低いほど枯葉率が高い
        hue_score = max(0, 1 - (hue / 90))  # 緑から遠いほど高い
        saturation_score = 1 - (saturation / 255)  # 彩度が低いほど高い
        
        degree = (hue_score * 0.6 + saturation_score * 0.4) * 100
        return min(100, max(0, degree))
    
    def _create_empty_color_dict(self) -> Dict:
        """
        空の色解析辞書を作成
        
        Returns:
            空の辞書
        """
        return {
            'mean_hue': 0,
            'mean_saturation': 0,
            'mean_value': 0,
            'color_stage': 'unknown',
        }
    
    def calculate_color_difference(self, image1: np.ndarray, image2: np.ndarray,
                                  region_mask: np.ndarray = None) -> float:
        """
        2つの画像間の色差（ΔE in Lab）を計算
        
        Args:
            image1: BGR画像1
            image2: BGR画像2
            region_mask: 対象領域のマスク
        
        Returns:
            色差
        """
        # Lab色空間に変換
        lab1 = cv2.cvtColor(cv2.cvtColor(image1, cv2.COLOR_BGR2RGB),
                           cv2.COLOR_RGB2LAB)
        lab2 = cv2.cvtColor(cv2.cvtColor(image2, cv2.COLOR_BGR2RGB),
                           cv2.COLOR_RGB2LAB)
        
        # 平均Lab値を計算
        l1_mean, a1_mean, b1_mean = cv2.mean(lab1, mask=region_mask)[:3]
        l2_mean, a2_mean, b2_mean = cv2.mean(lab2, mask=region_mask)[:3]
        
        # ΔEを計算
        delta_e = np.sqrt((l1_mean - l2_mean)**2 + 
                         (a1_mean - a2_mean)**2 + 
                         (b1_mean - b2_mean)**2)
        
        return delta_e
    
    def get_color_histogram(self, image: np.ndarray, mask: np.ndarray = None,
                           bins: int = 32) -> Dict:
        """
        Hue値のヒストグラムを計算
        
        Args:
            image: BGR画像
            mask: マスク（オプション）
            bins: ビン数
        
        Returns:
            ヒストグラム情報
        """
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h_channel = hsv_image[:,:,0]
        
        hist = cv2.calcHist([h_channel], [0], mask, [bins], [0, 180])
        
        # 正規化
        hist_norm = cv2.normalize(hist, hist).flatten()
        
        return {
            'histogram': hist_norm,
            'bins': bins,
            'peak_bin': np.argmax(hist_norm),
            'peak_value': np.max(hist_norm),
        }
