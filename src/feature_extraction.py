"""
OliveVision AI - 特徴量抽出モジュール
"""

import cv2
import numpy as np
import pandas as pd
from typing import Dict, List
from datetime import datetime
from . import utils


class FeatureExtractor:
    """
    画像から特徴量を抽出するクラス
    """
    
    def __init__(self, config: Dict):
        """
        初期化
        
        Args:
            config: 設定辞書
        """
        self.config = config
    
    def extract_features(self, image_path: str, detection_results: Dict,
                        color_analysis: Dict, timestamp: datetime = None) -> Dict:
        """
        画像から全特徴量を抽出
        
        Args:
            image_path: 画像ファイルパス
            detection_results: 検出結果（葉・実）
            color_analysis: 色解析結果
            timestamp: タイムスタンプ
        
        Returns:
            全特徴量の辞書
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        features = {}
        
        # タイムスタンプ特徴量
        features.update(self._extract_temporal_features(timestamp))
        
        # 葉の特徴量
        features.update(self._extract_leaf_features(detection_results.get('leaves', [])))
        
        # 実の特徴量
        features.update(self._extract_fruit_features(detection_results.get('fruits', [])))
        
        # 色特徴量
        features.update(self._extract_color_features(color_analysis))
        
        # 画像全体の特徴量
        image = utils.load_image(image_path)
        features.update(self._extract_image_features(image))
        
        return features
    
    def _extract_temporal_features(self, timestamp: datetime) -> Dict:
        """
        時間的特徴量を抽出
        
        Args:
            timestamp: タイムスタンプ
        
        Returns:
            時間特徴量
        """
        return {
            'date': timestamp.strftime('%Y-%m-%d'),
            'time': timestamp.strftime('%H:%M:%S'),
            'hour': timestamp.hour,
            'day_of_week': timestamp.weekday(),
            'month': timestamp.month,
            'season': self._get_season(timestamp.month),
        }
    
    def _extract_leaf_features(self, leaves: List[Dict]) -> Dict:
        """
        葉の特徴量を抽出
        
        Args:
            leaves: 検出された葉のリスト
        
        Returns:
            葉の特徴量
        """
        if len(leaves) == 0:
            return {
                'leaf_count': 0,
                'leaf_avg_area': 0,
                'leaf_max_area': 0,
                'leaf_min_area': 0,
                'leaf_std_area': 0,
                'leaf_density': 0,
                'leaf_avg_aspect_ratio': 0,
                'leaf_avg_solidity': 0,
            }
        
        areas = [l['area'] for l in leaves]
        aspect_ratios = [l['aspect_ratio'] for l in leaves]
        solidities = [l['solidity'] for l in leaves]
        
        return {
            'leaf_count': len(leaves),
            'leaf_avg_area': np.mean(areas),
            'leaf_max_area': np.max(areas),
            'leaf_min_area': np.min(areas),
            'leaf_std_area': np.std(areas),
            'leaf_avg_aspect_ratio': np.mean(aspect_ratios),
            'leaf_avg_solidity': np.mean(solidities),
        }
    
    def _extract_fruit_features(self, fruits: List[Dict]) -> Dict:
        """
        実の特徴量を抽出
        
        Args:
            fruits: 検出された実のリスト
        
        Returns:
            実の特徴量
        """
        if len(fruits) == 0:
            return {
                'fruit_count': 0,
                'fruit_avg_area': 0,
                'fruit_max_area': 0,
                'fruit_min_area': 0,
                'fruit_avg_radius': 0,
                'fruit_avg_circularity': 0,
            }
        
        areas = [f['area'] for f in fruits]
        radii = [f['radius'] for f in fruits]
        circularities = [f['circularity'] for f in fruits]
        
        return {
            'fruit_count': len(fruits),
            'fruit_avg_area': np.mean(areas),
            'fruit_max_area': np.max(areas),
            'fruit_min_area': np.min(areas),
            'fruit_avg_radius': np.mean(radii),
            'fruit_avg_circularity': np.mean(circularities),
        }
    
    def _extract_color_features(self, color_analysis: Dict) -> Dict:
        """
        色特徴量を抽出
        
        Args:
            color_analysis: 色解析結果
        
        Returns:
            色特徴量
        """
        features = {}
        
        for key, value in color_analysis.items():
            if isinstance(value, (int, float)):
                features[f'color_{key}'] = value
        
        return features
    
    def _extract_image_features(self, image: np.ndarray) -> Dict:
        """
        画像全体の特徴量を抽出
        
        Args:
            image: BGR画像
        
        Returns:
            画像特徴量
        """
        height, width = image.shape[:2]
        
        # グレースケール化
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # エッジ検出
        edges = cv2.Canny(gray, 100, 200)
        edge_density = np.sum(edges > 0) / (height * width)
        
        # 平均輝度
        avg_brightness = np.mean(gray)
        
        # 対比度
        contrast = np.std(gray)
        
        return {
            'image_width': width,
            'image_height': height,
            'image_area': width * height,
            'edge_density': edge_density,
            'avg_brightness': avg_brightness,
            'contrast': contrast,
        }
    
    @staticmethod
    def _get_season(month: int) -> str:
        """
        月から季節を判定
        
        Args:
            month: 月（1-12）
        
        Returns:
            季節の名前
        """
        if month in [12, 1, 2]:
            return 'winter'
        elif month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        else:
            return 'autumn'


class TimeSeriesFeatureExtractor:
    """
    時系列データから特徴量を抽出するクラス
    """
    
    @staticmethod
    def create_lag_features(df: pd.DataFrame, lags: List[int] = None) -> pd.DataFrame:
        """
        遅延特徴量を作成
        
        Args:
            df: 時系列データフレーム
            lags: 遅延ステップのリスト
        
        Returns:
            遅延特徴量が追加されたデータフレーム
        """
        if lags is None:
            lags = [1, 2, 6, 12, 24]
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for lag in lags:
            for col in numeric_cols:
                df[f'{col}_lag{lag}'] = df[col].shift(lag)
        
        return df
    
    @staticmethod
    def create_moving_average_features(df: pd.DataFrame, 
                                      windows: List[int] = None) -> pd.DataFrame:
        """
        移動平均特徴量を作成
        
        Args:
            df: 時系列データフレーム
            windows: ウィンドウサイズのリスト
        
        Returns:
            移動平均特徴量が追加されたデータフレーム
        """
        if windows is None:
            windows = [3, 6, 12, 24]
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for window in windows:
            for col in numeric_cols:
                df[f'{col}_ma{window}'] = df[col].rolling(window=window).mean()
        
        return df
    
    @staticmethod
    def create_diff_features(df: pd.DataFrame, diffs: List[int] = None) -> pd.DataFrame:
        """
        差分特徴量を作成
        
        Args:
            df: 時系列データフレーム
            diffs: 差分ステップのリスト
        
        Returns:
            差分特徴量が追加されたデータフレーム
        """
        if diffs is None:
            diffs = [1, 24]
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for diff in diffs:
            for col in numeric_cols:
                df[f'{col}_diff{diff}'] = df[col].diff(diff)
        
        return df


class FeatureScaler:
    """
    特徴量を正規化するクラス
    """
    
    @staticmethod
    def normalize_minmax(data: np.ndarray, min_val: float = 0, 
                        max_val: float = 1) -> np.ndarray:
        """
        Min-Max正規化
        
        Args:
            data: 入力データ
            min_val: 最小値
            max_val: 最大値
        
        Returns:
            正規化されたデータ
        """
        data_min = np.min(data)
        data_max = np.max(data)
        
        if data_max == data_min:
            return np.full_like(data, (min_val + max_val) / 2, dtype=float)
        
        return (data - data_min) / (data_max - data_min) * (max_val - min_val) + min_val
    
    @staticmethod
    def normalize_zscore(data: np.ndarray) -> np.ndarray:
        """
        Z-score正規化
        
        Args:
            data: 入力データ
        
        Returns:
            正規化されたデータ
        """
        mean = np.mean(data)
        std = np.std(data)
        
        if std == 0:
            return np.zeros_like(data, dtype=float)
        
        return (data - mean) / std
