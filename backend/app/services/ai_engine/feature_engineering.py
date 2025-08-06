"""
Feature Engineering for AI Signal Generation

Advanced feature engineering pipeline for cryptocurrency trading signals.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import ta
from sklearn.preprocessing import StandardScaler, RobustScaler


class FeatureEngineer:
    """Feature engineering for cryptocurrency trading signals"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.robust_scaler = RobustScaler()
        
    def create_technical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create technical analysis features"""
        # Basic price features
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # Moving averages
        df['sma_20'] = ta.trend.sma_indicator(df['close'], window=20)
        df['ema_20'] = ta.trend.ema_indicator(df['close'], window=20)
        df['sma_50'] = ta.trend.sma_indicator(df['close'], window=50)
        
        # RSI
        df['rsi'] = ta.momentum.rsi(df['close'], window=14)
        
        # MACD
        macd = ta.trend.MACD(df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()
        
        # Bollinger Bands
        bollinger = ta.volatility.BollingerBands(df['close'])
        df['bb_upper'] = bollinger.bollinger_hband()
        df['bb_lower'] = bollinger.bollinger_lband()
        df['bb_middle'] = bollinger.bollinger_mavg()
        
        # Volume features
        df['volume_sma'] = ta.volume.volume_sma(df['close'], df['volume'], window=20)
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        return df
    
    def create_market_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create market structure features"""
        # Volatility
        df['volatility'] = df['returns'].rolling(window=20).std()
        
        # Price position in range
        df['price_position'] = (df['close'] - df['low'].rolling(20).min()) / (
            df['high'].rolling(20).max() - df['low'].rolling(20).min()
        )
        
        # Momentum
        df['momentum_5'] = df['close'] / df['close'].shift(5) - 1
        df['momentum_10'] = df['close'] / df['close'].shift(10) - 1
        
        return df
    
    def create_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create time-based features"""
        df['hour'] = pd.to_datetime(df.index).hour
        df['day_of_week'] = pd.to_datetime(df.index).dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        
        return df
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Main feature engineering pipeline"""
        df = self.create_technical_features(df)
        df = self.create_market_features(df)
        df = self.create_time_features(df)
        
        # Drop NaN values
        df = df.dropna()
        
        return df
    
    def scale_features(self, df: pd.DataFrame, feature_columns: List[str]) -> pd.DataFrame:
        """Scale features for ML models"""
        df_scaled = df.copy()
        df_scaled[feature_columns] = self.scaler.fit_transform(df[feature_columns])
        return df_scaled

