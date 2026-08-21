"""
OliveVision AI - メイン画像/動画解析スクリプト
"""

import cv2
import sys
import logging
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, List
import numpy as np

from src import (
    utils, ImagePreprocessor, ObjectDetector, ColorAnalyzer, FeatureExtractor,
    VideoProcessor, FrameSequenceAnalyzer, BackgroundRemover, AdvancedDetector,
    TextureAnalyzer, OpticalFlowAnalyzer, ObjectTracker, ColorRangeOptimizer
)


def analyze_image(image_path: str, config: Dict, logger: logging.Logger,
                 use_advanced_detection: bool = True) -> Dict:
    """
    単一の画像を解析（高度な検出版）
    
    Args:
        image_path: 画像ファイルのパス
        config: 設定辞書
        logger: ロガーオブジェクト
        use_advanced_detection: 高度な検出を使用
    
    Returns:
        解析結果の辞書
    """
    logger.info(f"解析開始: {image_path}")
    
    # 画像読み込み
    image = utils.load_image(image_path)
    logger.info(f"画像サイズ: {image.shape}")
    
    # 前処理
    logger.info("画像を前処理中...")
    preprocessor = ImagePreprocessor(config)
    preprocessed_image = preprocessor.preprocess(image)
    
    # 背景除去
    logger.info("背景を除去中...")
    bg_remover = BackgroundRemover(logger)
    fg_mask = bg_remover.adaptive_background_removal(preprocessed_image)
    fg_mask = bg_remover.apply_morphological_cleanup(fg_mask)
    
    # 色範囲最適化
    logger.info("HSV範囲を最適化中...")
    color_optimizer = ColorRangeOptimizer(logger)
    optimized_ranges = color_optimizer.optimize_hsv_range(preprocessed_image, fg_mask)
    logger.debug(f"最適化されたHue範囲: {optimized_ranges['hue_range']}")
    
    # 検出
    logger.info("葉と実を検出中...")
    if use_advanced_detection:
        advanced_detector = AdvancedDetector(config, logger)
        leaves = advanced_detector.detect_leaves_multiscale(preprocessed_image)
        leaves = advanced_detector.post_process_detections(leaves, preprocessed_image)
        
        # 信頼度を計算
        for leaf in leaves:
            leaf['confidence'] = advanced_detector.calculate_detection_confidence(leaf)
        
        # フィルター処理
        leaves = [l for l in leaves if l.get('confidence', 0) > 0.5]
        
        logger.info(f"高度な検出: {len(leaves)}個の葉を検出")
    else:
        detector = ObjectDetector(config)
        leaves, _ = detector.detect_leaves(preprocessed_image)
    
    fruits, _ = ObjectDetector(config).detect_fruits(preprocessed_image)
    logger.info(f"検出結果 - 葉: {len(leaves)}個, 実: {len(fruits)}個")
    
    # 色解析
    logger.info("色を解析中...")
    color_analyzer = ColorAnalyzer(config)
    
    # 葉マスクを作成
    hsv = cv2.cvtColor(preprocessed_image, cv2.COLOR_BGR2HSV)
    leaf_mask = utils.create_mask_from_hsv_range(
        hsv,
        tuple(optimized_ranges.get('hue_range', config['leaf_detection']['hue_range'])),
        tuple(optimized_ranges.get('saturation_range', config['leaf_detection']['saturation_range'])),
        tuple(optimized_ranges.get('value_range', config['leaf_detection']['value_range']))
    )
    
    # 実マスクを作成
    fruit_mask = utils.create_mask_from_hsv_range(
        hsv,
        (15, 170), (40, 255), (30, 255)
    )
    
    leaf_colors = color_analyzer.analyze_leaf_color(preprocessed_image, leaf_mask)
    fruit_colors = color_analyzer.analyze_fruit_color(preprocessed_image, fruit_mask)
    
    # テクスチャ解析
    logger.info("テクスチャを解析中...")
    texture_analyzer = TextureAnalyzer(logger)
    leaf_texture = texture_analyzer.analyze_object_texture(preprocessed_image, leaf_mask)
    fruit_texture = texture_analyzer.analyze_object_texture(preprocessed_image, fruit_mask)
    leaf_smoothness = texture_analyzer.calculate_leaf_smoothness(preprocessed_image, leaf_mask)
    fruit_shine = texture_analyzer.calculate_fruit_shine(preprocessed_image, fruit_mask)
    
    logger.info(f"葉の平均Hue: {leaf_colors['mean_hue']:.2f}")
    logger.info(f"葉の滑らかさ: {leaf_smoothness:.2f}")
    logger.info(f"実の光沢度: {fruit_shine:.2f}")
    
    # 特徴量抽出
    logger.info("特徴量を抽出中...")
    feature_extractor = FeatureExtractor(config)
    
    detection_results = {
        'leaves': leaves,
        'fruits': fruits,
    }
    
    color_analysis_results = {
        'leaf_colors': leaf_colors,
        'fruit_colors': fruit_colors,
        'leaf_texture': leaf_texture,
        'fruit_texture': fruit_texture,
        'leaf_smoothness': leaf_smoothness,
        'fruit_shine': fruit_shine,
    }
    
    features = feature_extractor.extract_features(
        image_path,
        detection_results,
        color_analysis_results,
        timestamp=datetime.now()
    )
    
    # 結果をまとめる
    results = {
        'image_path': image_path,
        'timestamp': datetime.now().isoformat(),
        'detection': {
            'leaf_count': len(leaves),
            'fruit_count': len(fruits),
            'leaves': leaves,
            'fruits': fruits,
            'summary': ObjectDetector(config).get_detection_summary(leaves, fruits),
        },
        'color': {
            'leaf': leaf_colors,
            'fruit': fruit_colors,
        },
        'texture': {
            'leaf': leaf_texture,
            'fruit': fruit_texture,
        },
        'analysis': {
            'leaf_smoothness': leaf_smoothness,
            'fruit_shine': fruit_shine,
        },
        'features': features,
    }
    
    logger.info("解析完了")
    
    return results


def save_results(results: Dict, output_dir: str, logger: logging.Logger) -> None:
    """
    解析結果をファイルに保存
    
    Args:
        results: 解析結果
        output_dir: 出力ディレクトリ
        logger: ロガーオブジェクト
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # JSON形式で保存
    json_path = output_path / f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    logger.info(f"結果を保存: {json_path}")


def analyze_video(video_path: str, config: Dict, logger: logging.Logger,
                 frame_interval: int = 30) -> Dict:
    """
    動画ファイルを解析
    
    Args:
        video_path: 動画ファイルのパス
        config: 設定辞書
        logger: ロガーオブジェクト
        frame_interval: フレーム間隔（1=全フレーム、30=1秒ごと）
    
    Returns:
        解析結果の辞書
    """
    logger.info(f"動画解析開始: {video_path}")
    logger.info(f"フレーム間隔: {frame_interval}")
    
    # ビデオプロセッサを初期化
    video_proc = VideoProcessor(video_path, logger)
    stats = video_proc.get_statistics()
    logger.info(f"動画情報: {stats['width']}x{stats['height']} @ {stats['fps']}fps, {stats['frame_count']}フレーム")
    
    # フレームシーケンス解析器
    seq_analyzer = FrameSequenceAnalyzer(logger)
    
    # 前処理・検出用のインスタンス
    preprocessor = ImagePreprocessor(config)
    tracker = ObjectTracker(logger)
    flow_analyzer = OpticalFlowAnalyzer(logger)
    
    # 結果を保存
    frame_results = []
    
    logger.info("フレーム解析中...")
    frame_count = 0
    
    for frame_idx, frame in video_proc.get_frame_iterator(frame_interval):
        # タイムスタンプ計算
        timestamp = frame_idx / stats['fps']
        
        # 前処理
        preprocessed = preprocessor.preprocess(frame)
        
        # 検出
        detector = ObjectDetector(config)
        leaves, _ = detector.detect_leaves(preprocessed)
        fruits, _ = detector.detect_fruits(preprocessed)
        
        # 追跡
        tracked_leaves = tracker.update(leaves)
        
        # オプティカルフロー
        flow_x, flow_y = flow_analyzer.calculate_lucas_kanade_flow(preprocessed)
        flow_metrics = flow_analyzer.calculate_growth_metrics(flow_x, flow_y)
        expansion = flow_analyzer.calculate_expansion_rate(flow_x, flow_y)
        
        # 色解析
        color_analyzer = ColorAnalyzer(config)
        hsv = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2HSV)
        leaf_mask = utils.create_mask_from_hsv_range(
            hsv,
            tuple(config['leaf_detection']['hue_range']),
            tuple(config['leaf_detection']['saturation_range']),
            tuple(config['leaf_detection']['value_range'])
        )
        leaf_colors = color_analyzer.analyze_leaf_color(preprocessed, leaf_mask)
        
        # 結果を集計
        frame_data = {
            'frame_idx': frame_idx,
            'timestamp': timestamp,
            'leaf_count': len(leaves),
            'fruit_count': len(fruits),
            'leaf_color_hue': leaf_colors.get('mean_hue', 0),
            'flow_magnitude': flow_metrics.get('avg_flow_magnitude', 0),
            'expansion_rate': expansion,
        }
        
        frame_results.append(frame_data)
        seq_analyzer.add_frame_result(frame_idx, timestamp, frame_data)
        
        frame_count += 1
        if frame_count % 10 == 0:
            logger.info(f"処理済み: {frame_count}フレーム")
    
    video_proc.close()
    
    # 統計情報を計算
    seq_stats = seq_analyzer.get_statistics()
    
    # トレンド分析
    leaf_count_trend = seq_analyzer.get_trend('leaf_count')
    hue_trend = seq_analyzer.get_trend('leaf_color_hue')
    expansion_trend = seq_analyzer.get_trend('expansion_rate')
    
    # 変化率計算
    leaf_count_change = seq_analyzer.calculate_change_rate('leaf_count')
    hue_change = seq_analyzer.calculate_change_rate('leaf_color_hue')
    
    # 異常検出
    anomalies = seq_analyzer.detect_anomalies('leaf_count', threshold=2.0)
    
    results = {
        'video_path': video_path,
        'timestamp': datetime.now().isoformat(),
        'video_info': stats,
        'analysis_summary': {
            'total_frames_analyzed': frame_count,
            'duration_seconds': seq_stats.get('duration_seconds', 0),
            'avg_leaf_count': np.mean([f['leaf_count'] for f in frame_results]),
            'avg_fruit_count': np.mean([f['fruit_count'] for f in frame_results]),
            'leaf_count_change_percent': leaf_count_change,
            'hue_change_percent': hue_change,
        },
        'trends': {
            'leaf_count': leaf_count_trend,
            'leaf_color_hue': hue_trend,
            'expansion_rate': expansion_trend,
        },
        'anomalies': {
            'detected_frames': anomalies,
            'count': len(anomalies),
        },
        'frame_results': frame_results,
    }
    
    logger.info(f"動画解析完了: {frame_count}フレーム処理")
    
    return results


def main():
    """
    メイン処理（画像/動画自動判別）
    """
    # 設定読み込み
    config = utils.load_config("config/config.yaml")
    
    # ロガー設定
    logger = utils.setup_logger(config['logging']['file'])
    
    logger.info("=" * 60)
    logger.info("OliveVision AI - 画像/動画解析")
    logger.info("=" * 60)
    
    # コマンドライン引数チェック
    if len(sys.argv) < 2:
        logger.error("使用方法: python analyze.py <ファイルパス> [--frame-interval N]")
        print("使用方法: python analyze.py <ファイルパス> [--frame-interval N]")
        print("  ファイルパス: 画像ファイル（jpg, png等）または動画ファイル（mp4, avi等）")
        print("  --frame-interval: 動画の場合、このフレーム間隔で解析（デフォルト: 30）")
        sys.exit(1)
    
    file_path = sys.argv[1]
    frame_interval = 30
    
    # frame-interval パラメータ
    if len(sys.argv) >= 4 and sys.argv[2] == '--frame-interval':
        try:
            frame_interval = int(sys.argv[3])
        except ValueError:
            logger.warning("frame-intervalは整数である必要があります。デフォルト値を使用します。")
    
    # ファイル存在確認
    if not Path(file_path).exists():
        logger.error(f"ファイルが見つかりません: {file_path}")
        print(f"ファイルが見つかりません: {file_path}")
        sys.exit(1)
    
    # ファイル形式判定
    file_ext = Path(file_path).suffix.lower()
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
    
    is_video = file_ext in video_extensions
    is_image = file_ext in image_extensions
    
    if not is_video and not is_image:
        logger.error(f"サポートされていないファイル形式: {file_ext}")
        print(f"サポートされていないファイル形式: {file_ext}")
        print(f"画像形式: {', '.join(image_extensions)}")
        print(f"動画形式: {', '.join(video_extensions)}")
        sys.exit(1)
    
    # 解析実行
    try:
        if is_image:
            logger.info(f"画像ファイルを解析: {file_path}")
            results = analyze_image(file_path, config, logger, use_advanced_detection=True)
            
            # 結果表示
            print("\n" + "=" * 60)
            print("画像解析結果")
            print("=" * 60)
            print(f"葉の個数: {results['detection']['leaf_count']}")
            print(f"実の個数: {results['detection']['fruit_count']}")
            print(f"葉の平均面積: {results['detection']['summary']['leaf_avg_area']:.2f} px²")
            print(f"実の平均面積: {results['detection']['summary']['fruit_avg_area']:.2f} px²")
            print(f"葉の平均Hue: {results['color']['leaf']['mean_hue']:.2f}")
            print(f"実の平均Hue: {results['color']['fruit']['mean_hue']:.2f}")
            print(f"葉の滑らかさ: {results['analysis'].get('leaf_smoothness', 0):.3f}")
            print(f"実の光沢度: {results['analysis'].get('fruit_shine', 0):.3f}")
            print("=" * 60 + "\n")
            
        else:  # is_video
            logger.info(f"動画ファイルを解析: {file_path}")
            results = analyze_video(file_path, config, logger, frame_interval=frame_interval)
            
            # 結果表示
            print("\n" + "=" * 60)
            print("動画解析結果")
            print("=" * 60)
            print(f"解析フレーム数: {results['analysis_summary']['total_frames_analyzed']}")
            print(f"動画時間: {results['analysis_summary']['duration_seconds']:.2f}秒")
            print(f"平均葉数: {results['analysis_summary']['avg_leaf_count']:.1f}")
            print(f"平均実数: {results['analysis_summary']['avg_fruit_count']:.1f}")
            print(f"葉数変化率: {results['analysis_summary']['leaf_count_change_percent']:.2f}%")
            print(f"色相変化率: {results['analysis_summary']['hue_change_percent']:.2f}%")
            print(f"異常フレーム: {results['anomalies']['count']}")
            print("=" * 60 + "\n")
        
        # 結果を保存
        save_results(results, "outputs", logger)
        
        logger.info("処理完了")
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}", exc_info=True)
        print(f"エラーが発生しました: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
