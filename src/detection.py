"""
OliveVision AI - 葉・実検出モジュール
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple
from . import utils


class ObjectDetector:
    """
    オリーブの葉と実を検出するクラス
    """
    
    def __init__(self, config: Dict):
        """
        初期化
        
        Args:
            config: 設定辞書
        """
        self.config = config
        self.leaf_config = config['leaf_detection']
        self.fruit_config = config['fruit_detection']
    
    def detect_leaves(self, image: np.ndarray) -> Tuple[List[Dict], np.ndarray]:
        """
        葉を検出
        
        Args:
            image: BGR画像
        
        Returns:
            (葉の情報リスト, 可視化画像)
        """
        # HSV色空間に変換
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 葉領域をマスク
        mask = utils.create_mask_from_hsv_range(
            hsv_image,
            tuple(self.leaf_config['hue_range']),
            tuple(self.leaf_config['saturation_range']),
            tuple(self.leaf_config['value_range'])
        )
        
        # モルフォロジー処理
        mask = utils.apply_morphology(mask, 'open', 5)
        mask = utils.apply_morphology(mask, 'close', 5)
        
        # 輪郭抽出
        contours = utils.find_contours(mask)
        
        leaves = []
        for contour in contours:
            props = utils.get_contour_properties(contour)
            
            # フィルター条件
            if (self.leaf_config['min_area'] <= props['area'] <= self.leaf_config['max_area'] and
                props['circularity'] >= self.leaf_config['circularity_threshold'] and
                props['solidity'] >= self.leaf_config['solidity_threshold']):
                
                leaves.append(props)
        
        # 可視化
        vis_image = self._visualize_leaves(image, contours, leaves)
        
        return leaves, vis_image
    
    def detect_fruits(self, image: np.ndarray) -> Tuple[List[Dict], np.ndarray]:
        """
        実を検出
        
        Args:
            image: BGR画像
        
        Returns:
            (実の情報リスト, 可視化画像)
        """
        # HSV色空間に変換
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 実領域をマスク（config値を使用）
        fc = self.fruit_config
        masks = []
        
        # 緑色の実（configのhue_rangeを使用）
        mask_green = utils.create_mask_from_hsv_range(
            hsv_image,
            tuple(fc.get('hue_range', (30, 90))),
            tuple(fc.get('saturation_range', (40, 255))),
            tuple(fc.get('value_range', (40, 255)))
        )
        masks.append(mask_green)
        
        # 黄色の実
        yellow_hue = fc.get('yellow_hue_range', (15, 35))
        mask_yellow = utils.create_mask_from_hsv_range(
            hsv_image,
            yellow_hue,
            tuple(fc.get('saturation_range', (50, 255))),
            tuple(fc.get('value_range', (50, 255)))
        )
        masks.append(mask_yellow)
        
        # 紫色の実
        purple_hue = fc.get('purple_hue_range', (135, 170))
        mask_purple = utils.create_mask_from_hsv_range(
            hsv_image,
            purple_hue,
            tuple(fc.get('saturation_range', (50, 255))),
            tuple(fc.get('value_range', (50, 255)))
        )
        masks.append(mask_purple)
        
        # 黒色の実
        mask_black = utils.create_mask_from_hsv_range(
            hsv_image,
            (0, 180), (0, 255), (0, fc.get('black_value_max', 50))
        )
        masks.append(mask_black)
        
        # すべてのマスクを合成
        combined_mask = np.zeros_like(masks[0])
        for mask in masks:
            combined_mask = cv2.bitwise_or(combined_mask, mask)
        
        # モルフォロジー処理
        combined_mask = utils.apply_morphology(combined_mask, 'open', 3)
        combined_mask = utils.apply_morphology(combined_mask, 'close', 3)
        
        # 輪郭抽出
        contours = utils.find_contours(combined_mask)
        
        fruits = []
        for contour in contours:
            props = utils.get_contour_properties(contour)
            
            # フィルター条件
            if (self.fruit_config['min_area'] <= props['area'] <= self.fruit_config['max_area'] and
                props['circularity'] >= self.fruit_config['circularity_threshold']):
                
                fruits.append(props)
        
        # 可視化
        vis_image = self._visualize_fruits(image, contours, fruits)
        
        return fruits, vis_image
    
    def _visualize_leaves(self, image: np.ndarray, all_contours: List, 
                         valid_leaves: List[Dict]) -> np.ndarray:
        """
        検出された葉を可視化
        
        Args:
            image: 元画像
            all_contours: すべての輪郭
            valid_leaves: フィルター済みの葉
        
        Returns:
            可視化画像
        """
        vis = image.copy()
        
        for leaf in valid_leaves:
            x, y = int(leaf['x']), int(leaf['y'])
            w, h = int(leaf['width']), int(leaf['height'])
            cx, cy = int(leaf['center_x']), int(leaf['center_y'])
            
            # 外接矩形
            cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # 中心
            cv2.circle(vis, (cx, cy), 3, (0, 0, 255), -1)
        
        return vis
    
    def _visualize_fruits(self, image: np.ndarray, all_contours: List,
                         valid_fruits: List[Dict]) -> np.ndarray:
        """
        検出された実を可視化
        
        Args:
            image: 元画像
            all_contours: すべての輪郭
            valid_fruits: フィルター済みの実
        
        Returns:
            可視化画像
        """
        vis = image.copy()
        
        for fruit in valid_fruits:
            cx, cy = int(fruit['center_x']), int(fruit['center_y'])
            radius = int(fruit['radius'])
            
            # 円
            cv2.circle(vis, (cx, cy), radius, (0, 165, 255), 2)
            
            # 中心
            cv2.circle(vis, (cx, cy), 3, (0, 0, 255), -1)
        
        return vis
    
    def get_detection_summary(self, leaves: List[Dict], fruits: List[Dict]) -> Dict:
        """
        検出結果のサマリーを作成
        
        Args:
            leaves: 検出された葉のリスト
            fruits: 検出された実のリスト
        
        Returns:
            サマリー辞書
        """
        if len(leaves) == 0:
            leaf_avg_area = 0
            leaf_avg_circularity = 0
        else:
            leaf_avg_area = np.mean([l['area'] for l in leaves])
            leaf_avg_circularity = np.mean([l['circularity'] for l in leaves])
        
        if len(fruits) == 0:
            fruit_avg_area = 0
            fruit_avg_radius = 0
        else:
            fruit_avg_area = np.mean([f['area'] for f in fruits])
            fruit_avg_radius = np.mean([f['radius'] for f in fruits])
        
        return {
            'leaf_count': len(leaves),
            'leaf_avg_area': leaf_avg_area,
            'leaf_avg_circularity': leaf_avg_circularity,
            'fruit_count': len(fruits),
            'fruit_avg_area': fruit_avg_area,
            'fruit_avg_radius': fruit_avg_radius,
        }
