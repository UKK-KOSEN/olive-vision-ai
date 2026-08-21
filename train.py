"""
OliveVision AI - LightGBM モデルトレーニング
"""

import logging
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import json
import pickle

import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from src import utils


class LightGBMTrainer:
    """
    LightGBMモデルのトレーニングクラス
    """
    
    def __init__(self, config: dict, logger: logging.Logger):
        """
        初期化
        
        Args:
            config: 設定辞書
            logger: ロガーオブジェクト
        """
        self.config = config
        self.logger = logger
        self.model = None
        self.feature_names = None
    
    def train_from_csv(self, csv_path: str, target_column: str,
                      test_size: float = 0.2) -> dict:
        """
        CSVファイルからモデルをトレーニング
        
        Args:
            csv_path: CSVファイルのパス
            target_column: ターゲット列の名前
            test_size: テスト集合の割合
        
        Returns:
            トレーニング結果
        """
        self.logger.info(f"CSVファイルを読み込み中: {csv_path}")
        
        # データを読み込み
        df = pd.read_csv(csv_path)
        self.logger.info(f"データサイズ: {df.shape}")
        
        # 欠損値を処理
        df = df.fillna(df.mean(numeric_only=True))
        
        # ターゲットと特徴量を分離
        if target_column not in df.columns:
            self.logger.error(f"ターゲット列が見つかりません: {target_column}")
            raise ValueError(f"ターゲット列が見つかりません: {target_column}")
        
        y = df[target_column].values
        X = df.drop(columns=[target_column])
        
        self.feature_names = X.columns.tolist()
        self.logger.info(f"特徴量数: {len(self.feature_names)}")
        
        # トレーニング・テスト分割
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
        
        self.logger.info(f"トレーニング: {len(X_train)}, テスト: {len(X_test)}")
        
        # モデルをトレーニング
        return self.train(X_train, X_test, y_train, y_test)
    
    def train(self, X_train: np.ndarray, X_test: np.ndarray,
             y_train: np.ndarray, y_test: np.ndarray) -> dict:
        """
        LightGBMモデルをトレーニング
        
        Args:
            X_train: トレーニング特徴量
            X_test: テスト特徴量
            y_train: トレーニングターゲット
            y_test: テストターゲット
        
        Returns:
            トレーニング結果
        """
        self.logger.info("LightGBMモデルをトレーニング中...")
        
        # LightGBMパラメータ
        params = {
            'objective': 'regression',
            'metric': 'rmse',
            'num_leaves': self.config['machine_learning'].get('num_leaves', 31),
            'learning_rate': self.config['machine_learning'].get('learning_rate', 0.1),
            'max_depth': self.config['machine_learning'].get('max_depth', 7),
            'verbose': 10,
        }
        
        # データセット
        train_data = lgb.Dataset(X_train, label=y_train, feature_names=self.feature_names)
        test_data = lgb.Dataset(X_test, label=y_test, feature_names=self.feature_names,
                               reference=train_data)
        
        # トレーニング
        self.model = lgb.train(
            params,
            train_data,
            num_boost_round=self.config['machine_learning'].get('n_estimators', 100),
            valid_sets=[test_data],
            callbacks=[lgb.log_evaluation(period=10)]
        )
        
        # 予測
        y_pred_train = self.model.predict(X_train)
        y_pred_test = self.model.predict(X_test)
        
        # 評価指標
        train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
        test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
        train_mae = mean_absolute_error(y_train, y_pred_train)
        test_mae = mean_absolute_error(y_test, y_pred_test)
        train_r2 = r2_score(y_train, y_pred_train)
        test_r2 = r2_score(y_test, y_pred_test)
        
        results = {
            'train_rmse': train_rmse,
            'test_rmse': test_rmse,
            'train_mae': train_mae,
            'test_mae': test_mae,
            'train_r2': train_r2,
            'test_r2': test_r2,
        }
        
        self.logger.info("トレーニング完了")
        self.logger.info(f"トレーニング RMSE: {train_rmse:.4f}")
        self.logger.info(f"テスト RMSE: {test_rmse:.4f}")
        self.logger.info(f"テスト R²: {test_r2:.4f}")
        
        return results
    
    def get_feature_importance(self, top_n: int = 20) -> dict:
        """
        特徴量の重要度を取得
        
        Args:
            top_n: 上位N件を返す
        
        Returns:
            特徴量重要度
        """
        if self.model is None:
            self.logger.warning("モデルがトレーニングされていません")
            return {}
        
        importance = self.model.feature_importance(importance_type='gain')
        
        # 特徴量名でソート
        feature_importance_dict = {
            name: imp for name, imp in zip(self.feature_names, importance)
        }
        
        # 上位N件をソート
        sorted_importance = sorted(feature_importance_dict.items(),
                                  key=lambda x: x[1], reverse=True)[:top_n]
        
        return dict(sorted_importance)
    
    def save_model(self, model_path: str) -> None:
        """
        モデルを保存
        
        Args:
            model_path: 保存先パス
        """
        if self.model is None:
            self.logger.warning("モデルがトレーニングされていません")
            return
        
        Path(model_path).parent.mkdir(parents=True, exist_ok=True)
        self.model.save_model(model_path)
        self.logger.info(f"モデルを保存: {model_path}")
    
    def load_model(self, model_path: str) -> None:
        """
        モデルを読み込み
        
        Args:
            model_path: モデルファイルのパス
        """
        self.model = lgb.Booster(model_file=model_path)
        self.logger.info(f"モデルを読み込み: {model_path}")


def generate_sample_data(output_path: str = "data/processed/sample_data.csv") -> None:
    """
    テスト用のサンプルデータを生成
    
    Args:
        output_path: 出力ファイルパス
    """
    np.random.seed(42)
    
    # 時系列データを生成
    n_samples = 365 * 24  # 1年分のデータ（1時間ごと）
    
    data = {
        'date': pd.date_range(start='2024-01-01', periods=n_samples, freq='H'),
        'hour': np.tile(np.arange(24), n_samples // 24 + 1)[:n_samples],
        'month': np.repeat(np.arange(1, 13), 30 * 24)[:n_samples],
        'leaf_count': np.random.normal(1000, 100, n_samples),
        'leaf_avg_area': np.random.normal(200, 30, n_samples),
        'fruit_count': np.random.normal(300, 50, n_samples),
        'color_mean_hue': np.random.normal(60, 10, n_samples),
    }
    
    # ターゲット（3日後の葉色）
    data['leaf_color_3days_ahead'] = np.roll(data['color_mean_hue'], -72) + \
                                     np.random.normal(0, 5, n_samples)
    
    df = pd.DataFrame(data)
    
    # 出力
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    
    print(f"サンプルデータを生成: {output_path}")
    print(f"データサイズ: {df.shape}")


def main():
    """
    メイン処理
    """
    # 設定読み込み
    config = utils.load_config("config/config.yaml")
    
    # ロガー設定
    logger = utils.setup_logger(config['logging']['file'])
    
    logger.info("=" * 60)
    logger.info("OliveVision AI - モデルトレーニング")
    logger.info("=" * 60)
    
    # サンプルデータを生成
    logger.info("サンプルデータを生成中...")
    generate_sample_data()
    
    # トレーナーを初期化
    trainer = LightGBMTrainer(config, logger)
    
    # モデルをトレーニング
    try:
        results = trainer.train_from_csv(
            "data/processed/sample_data.csv",
            target_column="leaf_color_3days_ahead"
        )
        
        # 結果表示
        print("\n" + "=" * 60)
        print("トレーニング結果")
        print("=" * 60)
        print(f"テスト RMSE: {results['test_rmse']:.4f}")
        print(f"テスト MAE: {results['test_mae']:.4f}")
        print(f"テスト R²: {results['test_r2']:.4f}")
        print("=" * 60 + "\n")
        
        # 特徴量重要度
        importance = trainer.get_feature_importance(top_n=10)
        print("特徴量重要度（上位10件）:")
        for rank, (name, imp) in enumerate(importance.items(), 1):
            print(f"  {rank}. {name}: {imp:.4f}")
        print()
        
        # モデルを保存
        model_path = f"models/olive_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        trainer.save_model(model_path)
        
        logger.info("トレーニング完了")
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        print(f"エラーが発生しました: {str(e)}")


if __name__ == '__main__':
    main()
