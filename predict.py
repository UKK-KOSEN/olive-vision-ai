"""
OliveVision AI - 将来予測スクリプト
"""

import logging
import pandas as pd
import numpy as np
from pathlib import Path
import json

import lightgbm as lgb

from src import utils


class OliveForecast:
    """
    オリーブの将来状態を予測するクラス
    """
    
    def __init__(self, model_path: str, logger: logging.Logger):
        """
        初期化
        
        Args:
            model_path: 学習済みモデルのパス
            logger: ロガーオブジェクト
        """
        self.logger = logger
        self.model = None
        self.load_model(model_path)
    
    def load_model(self, model_path: str) -> None:
        """
        学習済みモデルを読み込み
        
        Args:
            model_path: モデルファイルのパス
        """
        try:
            self.model = lgb.Booster(model_file=model_path)
            self.logger.info(f"モデルを読み込み: {model_path}")
        except Exception as e:
            self.logger.error(f"モデルの読み込みに失敗: {str(e)}")
            raise
    
    def predict_future(self, current_features: dict, days_ahead: int = 3) -> dict:
        """
        将来のオリーブ状態を予測
        
        Args:
            current_features: 現在の特徴量
            days_ahead: 予測対象日数
        
        Returns:
            予測結果
        """
        if self.model is None:
            self.logger.error("モデルがロードされていません")
            raise RuntimeError("モデルがロードされていません")
        
        self.logger.info(f"{days_ahead}日後の状態を予測中...")
        
        # 特徴量をDataFrameに変換
        features_df = pd.DataFrame([current_features])
        
        # 予測
        prediction = self.model.predict(features_df)[0]
        
        # 予測結果を解釈
        interpretation = self._interpret_prediction(prediction, days_ahead)
        
        result = {
            'days_ahead': days_ahead,
            'predicted_value': float(prediction),
            'interpretation': interpretation,
            'confidence': self._estimate_confidence(prediction),
        }
        
        return result
    
    def _interpret_prediction(self, value: float, days_ahead: int) -> str:
        """
        予測値を解釈
        
        Args:
            value: 予測値
            days_ahead: 予測対象日数
        
        Returns:
            解釈文
        """
        if value > 80:
            return f"{days_ahead}日以内に健康な緑色が保たれる見込みです。"
        elif value > 60:
            return f"{days_ahead}日以内に若干の黄変が見られる可能性があります。"
        elif value > 40:
            return f"{days_ahead}日以内に黄変が進む見込みです。注意が必要です。"
        elif value > 20:
            return f"{days_ahead}日以内に褐変が始まる可能性があります。"
        else:
            return f"{days_ahead}日以内に枯変が進む可能性があります。対応が必要です。"
    
    def _estimate_confidence(self, prediction: float) -> float:
        """
        予測信頼度を推定
        
        Args:
            prediction: 予測値
        
        Returns:
            信頼度（0-1）
        """
        # 簡易的な信頼度計算
        # 予測値が極端でない場合、信頼度が高い
        if 20 <= prediction <= 80:
            return 0.85
        elif 10 <= prediction <= 90:
            return 0.70
        else:
            return 0.50


class AnalysisReport:
    """
    解析レポートを生成するクラス
    """
    
    def __init__(self, logger: logging.Logger):
        """
        初期化
        
        Args:
            logger: ロガーオブジェクト
        """
        self.logger = logger
    
    def generate_report(self, analysis_results: dict, forecasts: list) -> str:
        """
        解析レポートを生成
        
        Args:
            analysis_results: 画像解析結果
            forecasts: 予測結果のリスト
        
        Returns:
            レポートテキスト
        """
        report = []
        report.append("=" * 70)
        report.append("OliveVision AI - 解析レポート")
        report.append("=" * 70)
        report.append("")
        
        # 現在の状態
        report.append("【現在の状態】")
        report.append("-" * 70)
        
        detection = analysis_results.get('detection', {})
        report.append(f"葉の個数: {detection.get('leaf_count', 0)}")
        report.append(f"実の個数: {detection.get('fruit_count', 0)}")
        
        color = analysis_results.get('color', {})
        leaf_color = color.get('leaf', {})
        report.append(f"葉の色: {leaf_color.get('color_stage', '不明')}")
        report.append(f"  - 平均Hue: {leaf_color.get('mean_hue', 0):.1f}")
        report.append(f"  - 枯葉度: {leaf_color.get('senescence_degree', 0):.1f}%")
        
        report.append("")
        
        # 将来予測
        report.append("【将来予測】")
        report.append("-" * 70)
        
        for forecast in forecasts:
            report.append(f"{forecast['days_ahead']}日後:")
            report.append(f"  {forecast['interpretation']}")
            report.append(f"  信頼度: {forecast['confidence']*100:.1f}%")
            report.append("")
        
        # 推奨事項
        report.append("【推奨事項】")
        report.append("-" * 70)
        
        if leaf_color.get('senescence_degree', 0) > 20:
            report.append("・枯葉率が高い可能性があります。")
            report.append("・樹勢の確認をお勧めします。")
            report.append("・灌水や施肥の検討をしてください。")
        
        if detection.get('fruit_count', 0) < 100:
            report.append("・実の個数が少ないようです。")
            report.append("・着果状況の確認をお勧めします。")
        
        report.append("")
        report.append("=" * 70)
        
        return "\n".join(report)
    
    def save_report(self, report_text: str, output_path: str) -> None:
        """
        レポートをファイルに保存
        
        Args:
            report_text: レポートテキスト
            output_path: 出力ファイルパス
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        self.logger.info(f"レポートを保存: {output_path}")


def main():
    """
    メイン処理
    """
    # 設定読み込み
    config = utils.load_config("config/config.yaml")
    
    # ロガー設定
    logger = utils.setup_logger(config['logging']['file'])
    
    logger.info("=" * 60)
    logger.info("OliveVision AI - 将来予測")
    logger.info("=" * 60)
    
    # サンプル特徴量（実際にはanalyze.pyの出力から取得）
    sample_features = {
        'hour': 12,
        'month': 6,
        'leaf_count': 950,
        'leaf_avg_area': 195,
        'fruit_count': 280,
        'color_mean_hue': 65,
        'avg_brightness': 128,
        'contrast': 35,
        'edge_density': 0.15,
    }
    
    # モデルパス（最新のモデルを使用）
    model_dir = Path("models")
    if not model_dir.exists():
        logger.warning("modelsディレクトリが見つかりません")
        print("使用方法: まずtrain.pyを実行してモデルを作成してください")
        return
    
    model_files = list(model_dir.glob("*.txt"))
    if not model_files:
        logger.warning("学習済みモデルが見つかりません")
        print("使用方法: まずtrain.pyを実行してモデルを作成してください")
        return
    
    model_path = sorted(model_files)[-1]
    logger.info(f"使用するモデル: {model_path}")
    
    try:
        # 予測
        forecaster = OliveForecast(str(model_path), logger)
        
        # 複数の予測日数
        forecast_days = [3, 7, 14, 30]
        forecasts = []
        
        print("\n" + "=" * 60)
        print("将来予測結果")
        print("=" * 60)
        
        for days in forecast_days:
            forecast = forecaster.predict_future(sample_features, days)
            forecasts.append(forecast)
            
            print(f"\n{days}日後:")
            print(f"  予測値: {forecast['predicted_value']:.2f}")
            print(f"  {forecast['interpretation']}")
        
        print("\n" + "=" * 60 + "\n")
        
        # レポート生成
        analysis_results = {
            'detection': {
                'leaf_count': sample_features['leaf_count'],
                'fruit_count': sample_features['fruit_count'],
            },
            'color': {
                'leaf': {
                    'mean_hue': sample_features['color_mean_hue'],
                    'senescence_degree': 15,
                    'color_stage': 'healthy_green',
                }
            }
        }
        
        reporter = AnalysisReport(logger)
        report = reporter.generate_report(analysis_results, forecasts)
        
        print(report)
        
        # レポート保存
        report_path = f"outputs/forecast_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.txt"
        reporter.save_report(report, report_path)
        
        logger.info("予測完了")
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        print(f"エラーが発生しました: {str(e)}")


if __name__ == '__main__':
    main()
