"""
OliveVision AI - 画像前処理モジュール
"""

import cv2
import numpy as np
from typing import Dict, Tuple
from . import utils


class ImagePreprocessor:
    """
    画像前処理を行うクラス
    """
    
    def __init__(self, config: Dict):
        """
        初期化
        
        Args:
            config: 設定辞書
        """
        self.config = config['preprocessing']
        self.gaussian_blur_kernel = self.config.get('gaussian_blur_kernel', 5)
        self.clahe_clip_limit = self.config.get('clahe_clip_limit', 2.0)
        self.clahe_grid_size = self.config.get('clahe_grid_size', 8)
        self.gamma = self.config.get('gamma_correction', 1.2)
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        画像を前処理
        
        Args:
            image: 入力画像（BGR）
        
        Returns:
            前処理済み画像
        """
        # ノイズ除去
        image = self._denoise(image)
        
        # ホワイトバランス補正
        image = self._white_balance(image)
        
        # ガンマ補正
        image = self._gamma_correction(image)
        
        return image
    
    def _denoise(self, image: np.ndarray) -> np.ndarray:
        """
        ノイズ除去
        
        Args:
            image: 入力画像
        
        Returns:
            ノイズ除去済み画像
        """
        # ガウシアンフィルタ
        image = utils.apply_gaussian_blur(image, self.gaussian_blur_kernel)
        return image
    
    def _white_balance(self, image: np.ndarray) -> np.ndarray:
        """
        ホワイトバランス補正（Gray World Assumption）
        
        Args:
            image: 入力画像
        
        Returns:
            補正済み画像
        """
        result = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(result)
        
        l_avg = cv2.mean(l)[0]
        a_avg = cv2.mean(a)[0]
        b_avg = cv2.mean(b)[0]
        
        # 補正
        l = np.clip(l - (l_avg - 50), 0, 255).astype(np.uint8)
        a = np.clip(a - (a_avg - 128), 0, 255).astype(np.uint8)
        b = np.clip(b - (b_avg - 128), 0, 255).astype(np.uint8)
        
        result = cv2.merge([l, a, b])
        result = cv2.cvtColor(result, cv2.COLOR_LAB2BGR)
        
        return result
    
    def _gamma_correction(self, image: np.ndarray) -> np.ndarray:
        """
        ガンマ補正
        
        Args:
            image: 入力画像
        
        Returns:
            補正済み画像
        """
        inv_gamma = 1.0 / self.gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 
                         for i in np.arange(0, 256)]).astype("uint8")
        return cv2.LUT(image, table)


class ColorSpaceConverter:
    """
    色空間変換を行うクラス
    """
    
    @staticmethod
    def get_color_spaces(image: np.ndarray) -> Dict[str, np.ndarray]:
        """
        複数の色空間に変換
        
        Args:
            image: BGR画像
        
        Returns:
            各色空間の画像辞書
        """
        return {
            'bgr': image,
            'hsv': cv2.cvtColor(image, cv2.COLOR_BGR2HSV),
            'lab': cv2.cvtColor(cv2.cvtColor(image, cv2.COLOR_BGR2RGB), 
                               cv2.COLOR_RGB2LAB),
            'gray': cv2.cvtColor(image, cv2.COLOR_BGR2GRAY),
        }
    
    @staticmethod
    def get_mean_color(image: np.ndarray, mask: np.ndarray = None) -> Dict[str, float]:
        """
        領域の平均色を複数の色空間で取得
        
        Args:
            image: BGR画像
            mask: マスク（Noneの場合は画像全体）
        
        Returns:
            各色空間の平均色
        """
        if mask is not None and np.sum(mask) == 0:
            return {'r': 0, 'g': 0, 'b': 0, 'h': 0, 's': 0, 'v': 0}
        
        # BGR平均
        b_mean, g_mean, r_mean = cv2.mean(image, mask=mask)[:3]
        
        # HSV平均
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h_mean, s_mean, v_mean = cv2.mean(hsv_image, mask=mask)[:3]
        
        return {
            'r': r_mean,
            'g': g_mean,
            'b': b_mean,
            'h': h_mean,
            's': s_mean,
            'v': v_mean,
        }
