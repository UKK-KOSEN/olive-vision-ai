"""
OliveVision AI - 高度な検出・精度向上モジュール
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple
import logging


class AdvancedDetector:
    """
    より精密な葉・実検出を行うクラス
    """
    
    def __init__(self, config: Dict, logger: logging.Logger = None):
        """
        初期化
        
        Args:
            config: 設定辞書
            logger: ロガーオブジェクト
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
    
    def detect_leaves_multiscale(self, image: np.ndarray, 
                                 scales: List[float] = None) -> List[Dict]:
        """
        マルチスケール葉検出（複数スケールで検出後に統合）
        
        Args:
            image: BGR画像
            scales: スケールファクターのリスト
        
        Returns:
            葉の情報リスト
        """
        if scales is None:
            scales = [1.0, 0.8, 1.2]
        
        all_leaves = []
        
        for scale in scales:
            # 画像をリサイズ
            h, w = image.shape[:2]
            scaled_image = cv2.resize(image, (int(w * scale), int(h * scale)))
            
            # 検出
            leaves = self._detect_leaves_single_scale(scaled_image)
            
            # スケール値を戻す
            for leaf in leaves:
                leaf['area'] /= (scale ** 2)
                leaf['x'] /= scale
                leaf['y'] /= scale
                leaf['width'] /= scale
                leaf['height'] /= scale
                leaf['center_x'] /= scale
                leaf['center_y'] /= scale
                leaf['radius'] /= scale
            
            all_leaves.extend(leaves)
        
        # 重複する検出を統合
        return self._merge_detections(all_leaves)
    
    def _detect_leaves_single_scale(self, image: np.ndarray) -> List[Dict]:
        """
        単一スケールでの葉検出
        
        Args:
            image: BGR画像
        
        Returns:
            葉の情報リスト
        """
        # HSV変換
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 複数のHSV範囲で検出
        masks = []
        
        # 濃い緑
        mask1 = cv2.inRange(hsv, np.array([25, 40, 40]), np.array([90, 255, 255]))
        masks.append(mask1)
        
        # 薄い緑
        mask2 = cv2.inRange(hsv, np.array([30, 20, 50]), np.array([85, 150, 200]))
        masks.append(mask2)
        
        # マスクを統合
        combined_mask = cv2.bitwise_or(masks[0], masks[1])
        
        # ノイズ除去
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        cleaned = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)
        
        # 輪郭抽出
        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        leaves = []
        config = self.config['leaf_detection']
        
        for contour in contours:
            props = self._calculate_advanced_properties(contour)
            
            # より厳密なフィルタリング
            if (config['min_area'] <= props['area'] <= config['max_area'] and
                props['circularity'] >= config.get('circularity_threshold', 0.3) and
                props['solidity'] >= config.get('solidity_threshold', 0.5) and
                0.2 <= props['aspect_ratio'] <= 5.0):  # アスペクト比チェック
                
                leaves.append(props)
        
        return leaves
    
    def _calculate_advanced_properties(self, contour: np.ndarray) -> Dict:
        """
        輪郭から詳細なプロパティを計算
        
        Args:
            contour: 輪郭
        
        Returns:
            プロパティの辞書
        """
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        
        x, y, w, h = cv2.boundingRect(contour)
        (cx, cy), radius = cv2.minEnclosingCircle(contour)
        
        hull = cv2.convexHull(contour)
        convex_area = cv2.contourArea(hull)
        
        # Hu Moments
        hu_moments = cv2.HuMoments(contour).flatten()
        
        # 円形度
        circularity = 4 * np.pi * area / (perimeter ** 2) if perimeter > 0 else 0
        
        # Solidity
        solidity = area / convex_area if convex_area > 0 else 0
        
        # エッジの数
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approximation = cv2.approxPolyDP(contour, epsilon, True)
        edge_count = len(approximation)
        
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
            'extent': area / (w * h) if (w * h) != 0 else 0,
            'edge_count': edge_count,
            'hu_moments': hu_moments,
        }
    
    def _merge_detections(self, detections: List[Dict],
                         distance_threshold: float = 30) -> List[Dict]:
        """
        重複する検出を統合
        
        Args:
            detections: 検出結果のリスト
            distance_threshold: 統合する最大距離
        
        Returns:
            統合された検出結果
        """
        if not detections:
            return []
        
        # 面積でソート
        detections = sorted(detections, key=lambda x: x['area'], reverse=True)
        
        merged = []
        used_indices = set()
        
        for i, detection in enumerate(detections):
            if i in used_indices:
                continue
            
            # 同じグループの検出を集める
            group = [detection]
            
            for j, other in enumerate(detections[i+1:], start=i+1):
                if j in used_indices:
                    continue
                
                # 距離計算
                dist = np.sqrt((detection['center_x'] - other['center_x'])**2 +
                             (detection['center_y'] - other['center_y'])**2)
                
                if dist < distance_threshold:
                    group.append(other)
                    used_indices.add(j)
            
            # グループの平均を取る
            merged_detection = self._average_detections(group)
            merged.append(merged_detection)
        
        return merged
    
    def _average_detections(self, detections: List[Dict]) -> Dict:
        """
        複数の検出を平均化
        
        Args:
            detections: 検出結果のリスト
        
        Returns:
            平均化された検出結果
        """
        averaged = {}
        
        numeric_keys = ['area', 'perimeter', 'x', 'y', 'width', 'height',
                       'center_x', 'center_y', 'radius', 'circularity',
                       'solidity', 'aspect_ratio', 'extent', 'edge_count']
        
        for key in numeric_keys:
            values = [d.get(key, 0) for d in detections]
            averaged[key] = np.mean(values)
        
        return averaged
    
    def detect_with_filtering(self, image: np.ndarray, 
                             detections: List[Dict],
                             filter_type: str = 'bilateral') -> Tuple[np.ndarray, List[Dict]]:
        """
        フィルターを適用してから検出
        
        Args:
            image: BGR画像
            detections: 検出結果
            filter_type: フィルター種類 ('bilateral', 'morphology', 'nlm')
        
        Returns:
            (フィルター済み画像, 検出結果)
        """
        if filter_type == 'bilateral':
            # バイラテラルフィルター（エッジ保存）
            filtered = cv2.bilateralFilter(image, 9, 75, 75)
        elif filter_type == 'morphology':
            # モルフォロジー
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            filtered = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
            filtered = cv2.morphologyEx(filtered, cv2.MORPH_CLOSE, kernel)
        elif filter_type == 'nlm':
            # ノンローカルミーンズ
            filtered = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
        else:
            filtered = image
        
        return filtered, detections
    
    def post_process_detections(self, detections: List[Dict],
                               image: np.ndarray) -> List[Dict]:
        """
        検出結果の後処理（フィルタリング＆検証）
        
        Args:
            detections: 検出結果
            image: 元の画像
        
        Returns:
            フィルター済み検出結果
        """
        h, w = image.shape[:2]
        processed = []
        
        for detection in detections:
            # 画像外の検出を除外
            if (detection['x'] < 0 or detection['y'] < 0 or
                detection['x'] + detection['width'] > w or
                detection['y'] + detection['height'] > h):
                continue
            
            # 中心が画像内か確認
            if not (0 < detection['center_x'] < w and 0 < detection['center_y'] < h):
                continue
            
            processed.append(detection)
        
        return processed
    
    def calculate_detection_confidence(self, detection: Dict) -> float:
        """
        検出の信頼度を計算
        
        Args:
            detection: 検出結果
        
        Returns:
            信頼度（0-1）
        """
        # 複数の要因から信頼度を計算
        circularity_score = min(1.0, detection.get('circularity', 0) / 0.8)
        solidity_score = min(1.0, detection.get('solidity', 0) / 0.9)
        aspect_ratio = detection.get('aspect_ratio', 1.0)
        aspect_ratio_score = 1.0 - min(0.5, abs(aspect_ratio - 1.0) / 2.0)
        
        # 総合スコア
        confidence = (circularity_score * 0.4 + solidity_score * 0.4 + 
                     aspect_ratio_score * 0.2)
        
        return min(1.0, max(0.0, confidence))


class ColorRangeOptimizer:
    """
    HSV範囲を画像から自動最適化するクラス
    """
    
    def __init__(self, logger: logging.Logger = None):
        """
        初期化
        
        Args:
            logger: ロガーオブジェクト
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def optimize_hsv_range(self, image: np.ndarray,
                          foreground_mask: np.ndarray = None,
                          percentile: float = 95) -> Dict:
        """
        画像から最適なHSV範囲を推定
        
        Args:
            image: BGR画像
            foreground_mask: 前景マスク（指定時は前景から統計を計算）
            percentile: パーセンタイル値
        
        Returns:
            最適なHSV範囲の辞書
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        if foreground_mask is not None:
            h_data = hsv[:, :, 0][foreground_mask > 0]
            s_data = hsv[:, :, 1][foreground_mask > 0]
            v_data = hsv[:, :, 2][foreground_mask > 0]
        else:
            h_data = hsv[:, :, 0].flatten()
            s_data = hsv[:, :, 1].flatten()
            v_data = hsv[:, :, 2].flatten()
        
        # パーセンタイルから範囲を計算
        h_range = (int(np.percentile(h_data, 5)), int(np.percentile(h_data, percentile)))
        s_range = (int(np.percentile(s_data, 5)), int(np.percentile(s_data, percentile)))
        v_range = (int(np.percentile(v_data, 5)), int(np.percentile(v_data, percentile)))
        
        return {
            'hue_range': h_range,
            'saturation_range': s_range,
            'value_range': v_range,
        }
