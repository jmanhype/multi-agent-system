#!/usr/bin/env python3
"""
Backtest wrapper that bridges GEPA strategy generation with signal generation
"""

import pandas as pd
import numpy as np
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class BacktestWrapper:
    """Wrapper to convert GEPA strategies to trading signals"""
    
    def __init__(self):
        pass
    
    def backtest_strategy(self, strategy: Dict, df: pd.DataFrame) -> Dict:
        """
        Backtest a strategy by first generating signals
        
        Args:
            strategy: Strategy dict with type and parameters
            df: OHLCV DataFrame
            
        Returns:
            Backtest results dict
        """
        # Generate signals from strategy
        df_with_signals = self._generate_signals(strategy, df)
        
        # Run backtest with signals
        from lib.research.backtester_vbt import run_backtest
        return run_backtest(df_with_signals)
    
    def _generate_signals(self, strategy: Dict, market_data: pd.DataFrame) -> pd.DataFrame:
        """Generate entry/exit signals from strategy configuration"""
        df = market_data.copy()
        
        # Initialize signal columns
        df['entries'] = False
        df['exits'] = False
        
        # Extract strategy type and parameters
        strategy_type = strategy.get('type', 'momentum')
        params = strategy.get('parameters', {})
        
        # Normalize strategy type
        if 'momentum' in strategy_type.lower():
            strategy_type = 'momentum'
        elif 'mean' in strategy_type.lower() or 'reversion' in strategy_type.lower():
            strategy_type = 'mean_reversion'
        elif 'breakout' in strategy_type.lower():
            strategy_type = 'breakout'
        elif 'ml' in strategy_type.lower():
            strategy_type = 'ml_based'
        elif 'volume' in strategy_type.lower():
            strategy_type = 'volume_based'
        
        # Generate signals based on strategy type
        if strategy_type == 'momentum':
            self._generate_momentum_signals(df, params)
        elif strategy_type == 'mean_reversion':
            self._generate_mean_reversion_signals(df, params)
        elif strategy_type == 'breakout':
            self._generate_breakout_signals(df, params)
        elif strategy_type == 'ml_based':
            self._generate_ml_signals(df, params)
        elif strategy_type == 'volume_based':
            self._generate_volume_signals(df, params)
        else:
            # Default to momentum
            self._generate_momentum_signals(df, params)
        
        return df
    
    def _calculate_rsi(self, prices, period=14):
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _generate_momentum_signals(self, df: pd.DataFrame, params: Dict):
        """Generate momentum-based signals optimized for DEX tokens"""
        # Parameters from GEPA strategy
        lookback = params.get('lookback', 10)
        entry_threshold = params.get('entry_threshold', 2.0)
        exit_threshold = params.get('exit_threshold', 0.5)
        stop_loss = params.get('stop_loss', 0.05)
        take_profit = params.get('take_profit', 0.15)
        
        # Calculate momentum indicators
        df['momentum'] = df['close'].pct_change(lookback)
        df['volume_ma'] = df['volume'].rolling(10).mean()
        df['volume_surge'] = df['volume'] / (df['volume_ma'] + 1e-9)
        
        # RSI for overbought/oversold
        df['rsi'] = self._calculate_rsi(df['close'], 14)
        
        # Z-score for extreme moves
        df['returns'] = df['close'].pct_change()
        df['zscore'] = (df['returns'] - df['returns'].rolling(20).mean()) / (df['returns'].rolling(20).std() + 1e-9)
        
        # Entry: momentum + volume confirmation
        df['entries'] = (
            (df['zscore'] > entry_threshold) &
            (df['volume_surge'] > 1.5) &
            (df['rsi'] < 70)
        ).fillna(False)
        
        # Exit: momentum reversal or targets
        df['exits'] = (
            (df['zscore'] < -exit_threshold) |
            (df['rsi'] > 85) |
            (df['returns'] < -stop_loss) |
            (df['returns'] > take_profit)
        ).fillna(False)
    
    def _generate_mean_reversion_signals(self, df: pd.DataFrame, params: Dict):
        """Generate mean reversion signals"""
        lookback = params.get('lookback', 20)
        entry_zscore = params.get('entry_threshold', 2.0)
        exit_zscore = params.get('exit_threshold', 0.5)
        
        # Bollinger Bands
        df['sma'] = df['close'].rolling(lookback).mean()
        df['std'] = df['close'].rolling(lookback).std()
        df['upper_band'] = df['sma'] + (df['std'] * 2)
        df['lower_band'] = df['sma'] - (df['std'] * 2)
        df['zscore'] = (df['close'] - df['sma']) / (df['std'] + 1e-9)
        
        # Volume filter
        df['volume_ma'] = df['volume'].rolling(10).mean()
        df['liquidity_ok'] = df['volume'] > df['volume_ma'] * 0.5
        
        # Entry: extreme deviation
        df['entries'] = (
            (abs(df['zscore']) > entry_zscore) &
            df['liquidity_ok']
        ).fillna(False)
        
        # Exit: mean reversion
        df['exits'] = (
            (abs(df['zscore']) < exit_zscore) |
            (abs(df['zscore']) > 3.5)
        ).fillna(False)
    
    def _generate_breakout_signals(self, df: pd.DataFrame, params: Dict):
        """Generate breakout signals"""
        lookback = params.get('lookback', 20)
        breakout_threshold = params.get('entry_threshold', 2.0) / 100  # Convert to percentage
        
        # Calculate channels
        df['high_channel'] = df['high'].rolling(lookback).max()
        df['low_channel'] = df['low'].rolling(lookback).min()
        df['channel_width'] = df['high_channel'] - df['low_channel']
        
        # Volume confirmation
        df['volume_ma'] = df['volume'].rolling(10).mean()
        df['volume_breakout'] = df['volume'] > df['volume_ma'] * 2
        
        # Entry: breakout with volume
        df['entries'] = (
            ((df['close'] > df['high_channel'] * (1 + breakout_threshold)) |
             (df['close'] < df['low_channel'] * (1 - breakout_threshold))) &
            df['volume_breakout']
        ).fillna(False)
        
        # Exit: return to channel
        middle = (df['high_channel'] + df['low_channel']) / 2
        df['exits'] = (
            (abs(df['close'] - middle) < df['channel_width'] * 0.2) |
            (df['close'].pct_change() < -0.05)
        ).fillna(False)
    
    def _generate_ml_signals(self, df: pd.DataFrame, params: Dict):
        """Generate ML-based pattern recognition signals"""
        # Simple ML-inspired pattern detection
        lookback = params.get('lookback', 20)
        
        # Feature engineering
        df['rsi'] = self._calculate_rsi(df['close'], 14)
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        df['price_position'] = (df['close'] - df['low'].rolling(20).min()) / (df['high'].rolling(20).max() - df['low'].rolling(20).min() + 1e-9)
        
        # Pattern: RSI divergence + volume surge
        df['bullish_pattern'] = (
            (df['rsi'] < 30) &
            (df['close'] > df['close'].shift(1)) &
            (df['volume_ratio'] > 1.5)
        )
        
        df['bearish_pattern'] = (
            (df['rsi'] > 70) &
            (df['close'] < df['close'].shift(1)) &
            (df['volume_ratio'] > 1.5)
        )
        
        # Entries and exits
        df['entries'] = df['bullish_pattern'].fillna(False)
        df['exits'] = df['bearish_pattern'].fillna(False) | (df['close'].pct_change(5) > 0.1)
    
    def _generate_volume_signals(self, df: pd.DataFrame, params: Dict):
        """Generate volume-based signals"""
        lookback = params.get('lookback', 20)
        volume_threshold = params.get('entry_threshold', 2.0)
        
        # Volume analysis
        df['volume_ma'] = df['volume'].rolling(lookback).mean()
        df['volume_std'] = df['volume'].rolling(lookback).std()
        df['volume_zscore'] = (df['volume'] - df['volume_ma']) / (df['volume_std'] + 1e-9)
        
        # Price-volume correlation
        df['price_change'] = df['close'].pct_change()
        df['volume_price_corr'] = df['price_change'].rolling(10).corr(df['volume'])
        
        # Entry: volume surge with price confirmation
        df['entries'] = (
            (df['volume_zscore'] > volume_threshold) &
            (df['price_change'] > 0.01) &
            (df['volume_price_corr'] > 0.3)
        ).fillna(False)
        
        # Exit: volume exhaustion
        df['exits'] = (
            (df['volume_zscore'] < -1) |
            (df['price_change'] < -0.03)
        ).fillna(False)


# Singleton instance
backtest_wrapper = BacktestWrapper()

def run_backtest(strategy: Dict, df: pd.DataFrame) -> Dict:
    """
    Main entry point for backtesting GEPA strategies
    
    Args:
        strategy: Strategy dict from GEPA with type and parameters
        df: OHLCV DataFrame
        
    Returns:
        Backtest results dict
    """
    return backtest_wrapper.backtest_strategy(strategy, df)