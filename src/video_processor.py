"""
OliveVision AI - 動画処理モジュール
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Generator, Optional
import logging


class VideoProcessor:
    """
    動画ファイルを処理するクラス
    """
    
    def __init__(self, video_path: str, logger: logging.Logger):
        """
        初期化
        
        Args:
            video_path: 動画ファイルのパス
            logger: ロガーオブジェクト
        """
        self.video_path = video_path
        self.logger = logger
        self.cap = None
        self.fps = None
        self.frame_count = None
        self.width = None
        self.height = None
        self._open_video()
    
    def _open_video(self) -> None:
        """
        動画ファイルを開く
        """
        if not Path(self.video_path).exists():
            raise FileNotFoundError(f"動画ファイルが見つかりません: {self.video_path}")
        
        self.cap = cv2.VideoCapture(self.video_path)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"動画を開けません: {self.video_path}")
        
        # 動画情報取得
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        self.logger.info(f"動画情報: {self.width}x{self.height} @ {self.fps}fps, {self.frame_count}フレーム")
    
    def get_frame_iterator(self, frame_interval: int = 1) -> Generator[Tuple[int, np.ndarray], None, None]:
        """
        フレームを取得するイテレータ
        
        Args:
            frame_interval: フレーム間隔（1=全フレーム、30=1秒ごと等）
        
        Yields:
            (フレーム番号, BGR画像)
        """
        frame_idx = 0
        
        while True:
            ret, frame = self.cap.read()
            
            if not ret:
                break
            
            if frame_idx % frame_interval == 0:
                yield frame_idx, frame
            
            frame_idx += 1
    
    def get_specific_frames(self, indices: List[int]) -> List[Tuple[int, np.ndarray]]:
        """
        指定されたフレーム番号のフレームを取得
        
        Args:
            indices: フレーム番号のリスト
        
        Returns:
            (フレーム番号, BGR画像)のリスト
        """
        frames = []
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        for target_idx in sorted(indices):
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_idx)
            ret, frame = self.cap.read()
            
            if ret:
                frames.append((target_idx, frame))
        
        return frames
    
    def extract_frames_to_disk(self, output_dir: str, frame_interval: int = 30) -> int:
        """
        フレームをディスクに保存
        
        Args:
            output_dir: 出力ディレクトリ
            frame_interval: フレーム間隔
        
        Returns:
            保存されたフレーム数
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        saved_count = 0
        
        for frame_idx, frame in self.get_frame_iterator(frame_interval):
            output_path = Path(output_dir) / f"frame_{frame_idx:06d}.jpg"
            cv2.imwrite(str(output_path), frame)
            saved_count += 1
        
        self.logger.info(f"{saved_count}フレームを保存しました")
        return saved_count
    
    def create_video_from_frames(self, input_dir: str, output_path: str,
                                fps: float = None, codec: str = 'mp4v') -> None:
        """
        フレーム画像から動画を作成
        
        Args:
            input_dir: フレーム画像のディレクトリ
            output_path: 出力動画ファイルパス
            fps: フレームレート
            codec: コーデック
        """
        if fps is None:
            fps = self.fps
        
        frame_files = sorted(Path(input_dir).glob("frame_*.jpg"))
        
        if not frame_files:
            self.logger.error("フレーム画像が見つかりません")
            return
        
        # 最初のフレームから出力サイズを決定
        first_frame = cv2.imread(str(frame_files[0]))
        height, width = first_frame.shape[:2]
        
        fourcc = cv2.VideoWriter_fourcc(*codec)
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frame_count = 0
        for frame_file in frame_files:
            frame = cv2.imread(str(frame_file))
            out.write(frame)
            frame_count += 1
        
        out.release()
        self.logger.info(f"動画を作成: {output_path} ({frame_count}フレーム)")
    
    def get_frame_at_time(self, time_seconds: float) -> Optional[np.ndarray]:
        """
        指定された時刻のフレームを取得
        
        Args:
            time_seconds: 時刻（秒）
        
        Returns:
            BGR画像またはNone
        """
        frame_idx = int(time_seconds * self.fps)
        
        if frame_idx < 0 or frame_idx >= self.frame_count:
            self.logger.warning(f"フレーム位置が範囲外: {frame_idx}")
            return None
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.cap.read()
        
        return frame if ret else None
    
    def get_statistics(self) -> Dict:
        """
        動画全体の統計情報を取得
        
        Returns:
            統計情報の辞書
        """
        return {
            'fps': self.fps,
            'frame_count': self.frame_count,
            'width': self.width,
            'height': self.height,
            'duration_seconds': self.frame_count / self.fps if self.fps > 0 else 0,
            'file_path': self.video_path,
        }
    
    def close(self) -> None:
        """
        動画ファイルを閉じる
        """
        if self.cap is not None:
            self.cap.release()
    
    def __del__(self):
        """
        デストラクタ
        """
        self.close()


class FrameSequenceAnalyzer:
    """
    フレームシーケンスを解析するクラス
    """
    
    def __init__(self, logger: logging.Logger):
        """
        初期化
        
        Args:
            logger: ロガーオブジェクト
        """
        self.logger = logger
        self.frame_sequence = []
    
    def add_frame_result(self, frame_idx: int, timestamp: float, result: Dict) -> None:
        """
        フレーム解析結果を追加
        
        Args:
            frame_idx: フレーム番号
            timestamp: タイムスタンプ（秒）
            result: 解析結果
        """
        self.frame_sequence.append({
            'frame_idx': frame_idx,
            'timestamp': timestamp,
            'result': result,
        })
    
    def get_trend(self, key: str) -> List[Tuple[int, float]]:
        """
        時系列のトレンドを取得
        
        Args:
            key: 追跡するキー（例: 'leaf_count'）
        
        Returns:
            (フレーム番号, 値)のリスト
        """
        trend = []
        
        for frame_data in self.frame_sequence:
            if key in frame_data['result']:
                trend.append((frame_data['frame_idx'], frame_data['result'][key]))
        
        return trend
    
    def calculate_change_rate(self, key: str) -> float:
        """
        値の変化率を計算
        
        Args:
            key: 追跡するキー
        
        Returns:
            変化率（%）
        """
        trend = self.get_trend(key)
        
        if len(trend) < 2:
            return 0
        
        first_value = trend[0][1]
        last_value = trend[-1][1]
        
        if first_value == 0:
            return 0
        
        change_rate = ((last_value - first_value) / first_value) * 100
        return change_rate
    
    def get_statistics(self) -> Dict:
        """
        シーケンス全体の統計情報を取得
        
        Returns:
            統計情報の辞書
        """
        if not self.frame_sequence:
            return {}
        
        stats = {
            'total_frames': len(self.frame_sequence),
            'start_timestamp': self.frame_sequence[0]['timestamp'],
            'end_timestamp': self.frame_sequence[-1]['timestamp'],
            'duration_seconds': self.frame_sequence[-1]['timestamp'] - self.frame_sequence[0]['timestamp'],
        }
        
        return stats
    
    def detect_anomalies(self, key: str, threshold: float = 2.0) -> List[int]:
        """
        異常値を検出（標準偏差ベース）
        
        Args:
            key: 追跡するキー
            threshold: 標準偏差の閾値（デフォルト: 2.0）
        
        Returns:
            異常が検出されたフレーム番号のリスト
        """
        import numpy as np
        
        trend = self.get_trend(key)
        
        if len(trend) < 3:
            return []
        
        values = np.array([v for _, v in trend])
        mean = np.mean(values)
        std = np.std(values)
        
        if std == 0:
            return []
        
        anomalies = []
        for frame_idx, value in trend:
            z_score = abs((value - mean) / std)
            if z_score > threshold:
                anomalies.append(frame_idx)
        
        return anomalies
