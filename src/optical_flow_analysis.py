"""
OliveVision AI - オプティカルフロー解析モジュール（成長速度・動き追跡）
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging


class OpticalFlowAnalyzer:
    """
    オプティカルフローで成長速度や動きを追跡するクラス
    """
    
    def __init__(self, logger: logging.Logger = None):
        """
        初期化
        
        Args:
            logger: ロガーオブジェクト
        """
        self.logger = logger or logging.getLogger(__name__)
        self.prev_gray = None
    
    def calculate_lucas_kanade_flow(self, image: np.ndarray,
                                   mask: np.ndarray = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Lucas-Kanadeオプティカルフローを計算
        
        Args:
            image: 現在フレームの画像
            mask: 対象領域のマスク
        
        Returns:
            (flow_x, flow_y) - フロー成分
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        if self.prev_gray is None:
            self.prev_gray = gray
            return np.zeros_like(gray), np.zeros_like(gray)
        
        # Lucas-Kanade
        flow = cv2.calcOpticalFlowFarneback(
            self.prev_gray, gray,
            pyr_scale=0.5,
            levels=3,
            winsize=15,
            iterations=3,
            n8=False,
            poly_n=5,
            poly_sigma=1.2,
            flags=0
        )
        
        flow_x = flow[:, :, 0]
        flow_y = flow[:, :, 1]
        
        if mask is not None:
            flow_x[mask == 0] = 0
            flow_y[mask == 0] = 0
        
        self.prev_gray = gray
        
        return flow_x, flow_y
    
    def calculate_growth_metrics(self, flow_x: np.ndarray,
                                flow_y: np.ndarray) -> Dict:
        """
        フローから成長メトリクスを計算
        
        Args:
            flow_x: X方向フロー
            flow_y: Y方向フロー
        
        Returns:
            成長メトリクス
        """
        # フロー大きさ
        magnitude = np.sqrt(flow_x ** 2 + flow_y ** 2)
        
        metrics = {
            'avg_flow_magnitude': np.mean(magnitude),
            'max_flow_magnitude': np.max(magnitude),
            'std_flow_magnitude': np.std(magnitude),
            'avg_flow_x': np.mean(flow_x),
            'avg_flow_y': np.mean(flow_y),
        }
        
        return metrics
    
    def calculate_expansion_rate(self, flow_x: np.ndarray,
                                flow_y: np.ndarray) -> float:
        """
        領域の拡大率を計算（発散）
        
        Args:
            flow_x: X方向フロー
            flow_y: Y方向フロー
        
        Returns:
            拡大率（正値＝成長）
        """
        # 発散（divergence）= ∂u/∂x + ∂v/∂y
        # 数値微分で計算
        dux = np.diff(flow_x, axis=1)
        dvy = np.diff(flow_y, axis=0)
        
        # サイズを合わせる
        min_h = min(dux.shape[0], dvy.shape[0])
        min_w = min(dux.shape[1], dvy.shape[1])
        
        divergence = dux[:min_h, :min_w] + dvy[:min_h, :min_w]
        
        expansion_rate = np.mean(divergence)
        
        return expansion_rate
    
    def track_feature_points(self, image: np.ndarray,
                            max_points: int = 100) -> List[Tuple[float, float]]:
        """
        特徴点を検出して追跡
        
        Args:
            image: RGB画像
            max_points: 最大検出点数
        
        Returns:
            特徴点の座標リスト
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Shi-Tomasi コーナー検出
        corners = cv2.goodFeaturesToTrack(
            gray,
            maxCorners=max_points,
            qualityLevel=0.01,
            minDistance=10
        )
        
        if corners is None:
            return []
        
        return [(x, y) for x, y in corners.reshape(-1, 2)]
    
    def visualize_optical_flow(self, image: np.ndarray,
                              flow_x: np.ndarray,
                              flow_y: np.ndarray,
                              step: int = 15) -> np.ndarray:
        """
        オプティカルフローを可視化
        
        Args:
            image: 背景画像
            flow_x: X方向フロー
            flow_y: Y方向フロー
            step: 矢印の間隔
        
        Returns:
            フロー可視化画像
        """
        vis = image.copy()
        h, w = image.shape[:2]
        
        for y in range(0, h, step):
            for x in range(0, w, step):
                fx = int(flow_x[y, x])
                fy = int(flow_y[y, x])
                
                if abs(fx) > 0.1 or abs(fy) > 0.1:
                    # 矢印を描画
                    cv2.arrowedLine(vis, (x, y), (x + fx, y + fy),
                                   (0, 255, 0), 1, tipLength=0.2)
        
        return vis
    
    def visualize_magnitude(self, flow_x: np.ndarray,
                           flow_y: np.ndarray) -> np.ndarray:
        """
        フロー大きさをヒートマップで可視化
        
        Args:
            flow_x: X方向フロー
            flow_y: Y方向フロー
        
        Returns:
            ヒートマップ画像
        """
        magnitude = np.sqrt(flow_x ** 2 + flow_y ** 2)
        
        # 正規化
        magnitude = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX)
        magnitude = np.uint8(magnitude)
        
        # カラーマップを適用
        heatmap = cv2.applyColorMap(magnitude, cv2.COLORMAP_JET)
        
        return heatmap


class ObjectTracker:
    """
    オブジェクト追跡を行うクラス
    """
    
    def __init__(self, logger: logging.Logger = None):
        """
        初期化
        
        Args:
            logger: ロガーオブジェクト
        """
        self.logger = logger or logging.getLogger(__name__)
        self.tracks = {}  # ID -> 位置履歴
        self.next_id = 0
    
    def update(self, detections: List[Dict]) -> Dict[int, Dict]:
        """
        検出結果から追跡を更新
        
        Args:
            detections: 検出結果のリスト（中心座標を含む）
        
        Returns:
            ID -> 更新された検出結果の辞書
        """
        updated_tracks = {}
        
        # 既存の追跡と新規検出のマッチング
        matched = self._match_detections(detections)
        
        for track_id, detection in matched.items():
            if track_id not in self.tracks:
                self.tracks[track_id] = {
                    'history': [],
                    'creation_frame': 0,
                }
            
            # 履歴を記録
            self.tracks[track_id]['history'].append((
                detection['center_x'],
                detection['center_y']
            ))
            
            # 履歴を制限（最新100フレーム）
            if len(self.tracks[track_id]['history']) > 100:
                self.tracks[track_id]['history'].pop(0)
            
            detection['track_id'] = track_id
            detection['track_history'] = self.tracks[track_id]['history']
            updated_tracks[track_id] = detection
        
        # 新規追跡
        for detection in detections:
            if 'track_id' not in detection:
                track_id = self.next_id
                self.next_id += 1
                
                self.tracks[track_id] = {
                    'history': [(detection['center_x'], detection['center_y'])],
                    'creation_frame': 0,
                }
                
                detection['track_id'] = track_id
                detection['track_history'] = self.tracks[track_id]['history']
                updated_tracks[track_id] = detection
        
        return updated_tracks
    
    def _match_detections(self, detections: List[Dict],
                         distance_threshold: float = 50) -> Dict[int, Dict]:
        """
        既存追跡と新規検出をマッチング
        
        Args:
            detections: 検出結果
            distance_threshold: マッチング距離の閾値
        
        Returns:
            ID -> 検出結果のマッピング
        """
        matched = {}
        used_detection_indices = set()
        
        # 既存の追跡ごとに最も近い検出を探す
        for track_id, track_data in self.tracks.items():
            if not track_data['history']:
                continue
            
            last_pos = track_data['history'][-1]
            
            # 最も近い検出を探す
            best_dist = distance_threshold
            best_idx = -1
            
            for i, detection in enumerate(detections):
                if i in used_detection_indices:
                    continue
                
                dist = np.sqrt((detection['center_x'] - last_pos[0]) ** 2 +
                             (detection['center_y'] - last_pos[1]) ** 2)
                
                if dist < best_dist:
                    best_dist = dist
                    best_idx = i
            
            if best_idx >= 0:
                matched[track_id] = detections[best_idx]
                used_detection_indices.add(best_idx)
        
        return matched
    
    def get_track_velocity(self, track_id: int, 
                          window_size: int = 5) -> Tuple[float, float]:
        """
        追跡オブジェクトの速度を計算
        
        Args:
            track_id: 追跡ID
            window_size: 速度計算用のウィンドウサイズ
        
        Returns:
            (vx, vy) - X,Y方向の速度
        """
        if track_id not in self.tracks:
            return (0, 0)
        
        history = self.tracks[track_id]['history']
        
        if len(history) < window_size:
            if len(history) < 2:
                return (0, 0)
            window_size = len(history)
        
        # 最新のwindow_sizeフレームから速度を計算
        recent_positions = history[-window_size:]
        
        first_pos = recent_positions[0]
        last_pos = recent_positions[-1]
        
        vx = (last_pos[0] - first_pos[0]) / (window_size - 1)
        vy = (last_pos[1] - first_pos[1]) / (window_size - 1)
        
        return (vx, vy)
    
    def get_track_acceleration(self, track_id: int,
                             window_size: int = 5) -> Tuple[float, float]:
        """
        追跡オブジェクトの加速度を計算
        
        Args:
            track_id: 追跡ID
            window_size: 加速度計算用のウィンドウサイズ
        
        Returns:
            (ax, ay) - X,Y方向の加速度
        """
        if track_id not in self.tracks:
            return (0, 0)
        
        history = self.tracks[track_id]['history']
        
        if len(history) < window_size + 1:
            return (0, 0)
        
        # 速度の変化から加速度を計算
        v1 = self.get_track_velocity(track_id, window_size)
        
        # 前のウィンドウでの速度
        temp_history = self.tracks[track_id]['history']
        self.tracks[track_id]['history'] = history[:-1]
        v2 = self.get_track_velocity(track_id, window_size)
        self.tracks[track_id]['history'] = temp_history
        
        ax = v1[0] - v2[0]
        ay = v1[1] - v2[1]
        
        return (ax, ay)
