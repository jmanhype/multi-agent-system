#!/usr/bin/env python
"""
Features Extractor Agent - Real-time technical indicator calculation for trading execution
Specialized for winner strategy requirements: RSI(27/58 thresholds), EMA(10/58 regime)
Deterministic calculations only for live trading loop.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timezone
import warnings
warnings.filterwarnings('ignore')

# Import trading indicators
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'trading'))
from indicators import ema, rsi, atr


class FeatureExtractor:
    """
    Features Extractor Agent for Quantitative Trading System
    
    Specializes in:
    - Winner strategy RSI signals (27/58 thresholds)
    - EMA regime detection (10/58 periods) 
    - Volume analysis and price action
    - Real-time deterministic calculations
    - Feature vectors for strategy execution
    """
    
    def __init__(self, log_level: str = "INFO"):
        self.required_columns = ['open', 'high', 'low', 'close', 'volume']
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, log_level.upper()))
    
    def extract(self, df: pd.DataFrame, symbol: str = "BTC/USD", timeframe: str = "5m") -> Dict[str, Any]:
        """
        Main feature extraction pipeline for winner strategy
        
        Args:
            df: DataFrame with columns [timestamp, open, high, low, close, volume] 
            symbol: Trading symbol (default: "BTC/USD" per winner)
            timeframe: Timeframe (default: "5m" per winner)
        
        Returns:
            Dict with extracted features aligned to winner strategy requirements
        """
        start_time = datetime.now()
        
        if len(df) < 58:  # Need at least 58 periods for EMA(58)
            return self._default_features(symbol, timeframe)
        
        try:
            # Ensure proper columns and copy
            df_work = df.copy()
            if 'timestamp' in df_work.columns:
                df_work = df_work.drop('timestamp', axis=1)
            
            # Winner strategy core features
            features = self._extract_winner_features(df_work)
            
            # Volume analysis for confirmation
            features.update(self._extract_volume_analysis(df_work))
            
            # Price action patterns
            features.update(self._extract_price_action(df_work))
            
            # Regime classification
            features.update(self._extract_regime_state(df_work, features))
            
            # Generate execution signals
            signals = self._generate_winner_signals(features)
            
            # Build structured output
            computation_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "timeframe": timeframe,
                "features": {
                    "price": {
                        "close": float(df_work['close'].iloc[-1]),
                        "returns": features.get('return_1', 0.0),
                        "log_returns": features.get('log_return_1', 0.0)
                    },
                    "trend": {
                        "ema_10": features.get('ema_10', 0.0),
                        "ema_58": features.get('ema_58', 0.0), 
                        "regime_direction": features.get('regime_direction', 'neutral'),
                        "trend_strength": features.get('trend_strength', 0.0)
                    },
                    "momentum": {
                        "rsi_14": features.get('rsi_14', 50.0),
                        "rsi_entry_signal": features.get('rsi_entry_signal', False),
                        "rsi_exit_signal": features.get('rsi_exit_signal', False)
                    },
                    "volatility": {
                        "atr_14": features.get('atr_14', 0.0),
                        "atr_cap_pct": features.get('atr_cap_pct', 0.03),  # Per winner risk config
                        "realized_vol": features.get('realized_vol', 0.02)
                    },
                    "volume": {
                        "volume_ratio": features.get('volume_ratio', 1.0),
                        "volume_trend": features.get('volume_trend', 'neutral'),
                        "volume_confirmation": features.get('volume_confirmation', False)
                    },
                    "execution": {
                        "entry_conditions": features.get('entry_conditions', {}),
                        "exit_conditions": features.get('exit_conditions', {}),
                        "risk_metrics": features.get('risk_metrics', {})
                    }
                },
                "signals": signals,
                "metadata": {
                    "n_features": len(features),
                    "computation_time_ms": round(computation_time, 2),
                    "data_quality_score": self._calculate_quality_score(df_work),
                    "regime_state": features.get('regime_state', 'uncertain')
                }
            }
            
        except Exception as e:
            self.logger.error(f"Feature extraction failed: {str(e)}")
            return self._error_response(str(e), symbol, timeframe)
    
    def _default_features(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Return default feature values when insufficient data"""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": symbol,
            "timeframe": timeframe,
            "error": "Insufficient data for feature extraction",
            "features": {
                "price": {"close": 0.0, "returns": 0.0, "log_returns": 0.0},
                "trend": {"ema_10": 0.0, "ema_58": 0.0, "regime_direction": "neutral", "trend_strength": 0.0},
                "momentum": {"rsi_14": 50.0, "rsi_entry_signal": False, "rsi_exit_signal": False},
                "volatility": {"atr_14": 0.0, "atr_cap_pct": 0.03, "realized_vol": 0.02},
                "volume": {"volume_ratio": 1.0, "volume_trend": "neutral", "volume_confirmation": False},
                "execution": {"entry_conditions": {}, "exit_conditions": {}, "risk_metrics": {}}
            },
            "signals": {"entry_long": 0.0, "entry_short": 0.0, "exit_signal": 0.0},
            "metadata": {"n_features": 0, "computation_time_ms": 0.0, "data_quality_score": 0.0, "regime_state": "insufficient_data"}
        }
    
    def _extract_winner_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract core features for winner strategy execution"""
        features = {}
        
        close = df['close']
        high = df['high']
        low = df['low']
        
        # EMA regime detection (winner strategy: 10/58 periods)
        ema_10 = ema(close, 10)
        ema_58 = ema(close, 58)
        
        features['ema_10'] = float(ema_10.iloc[-1])
        features['ema_58'] = float(ema_58.iloc[-1])
        
        # Regime direction classification
        if ema_10.iloc[-1] > ema_58.iloc[-1]:
            features['regime_direction'] = 'up'
            features['trend_strength'] = float((ema_10.iloc[-1] - ema_58.iloc[-1]) / ema_58.iloc[-1])
        else:
            features['regime_direction'] = 'down' 
            features['trend_strength'] = float((ema_58.iloc[-1] - ema_10.iloc[-1]) / ema_58.iloc[-1])
        
        # RSI with winner thresholds (entry: below 27, exit: above 58)
        rsi_14 = rsi(close, 14)
        features['rsi_14'] = float(rsi_14.iloc[-1]) if not pd.isna(rsi_14.iloc[-1]) else 50.0
        
        # Winner strategy RSI signals
        features['rsi_entry_signal'] = features['rsi_14'] < 27  # Entry below 27
        features['rsi_exit_signal'] = features['rsi_14'] > 58   # Exit above 58
        
        # ATR for risk management (winner uses 3% cap)
        atr_14 = atr(high, low, close, 14)
        features['atr_14'] = float(atr_14.iloc[-1]) if not pd.isna(atr_14.iloc[-1]) else float(close.iloc[-1] * 0.02)
        features['atr_cap_pct'] = 0.03  # Per winner config
        
        # Returns calculation  
        returns = close.pct_change()
        features['return_1'] = float(returns.iloc[-1]) if not pd.isna(returns.iloc[-1]) else 0.0
        features['log_return_1'] = float(np.log(close.iloc[-1] / close.iloc[-2])) if len(close) > 1 else 0.0
        
        # Realized volatility (20-period)
        if len(returns) >= 20:
            features['realized_vol'] = float(returns.iloc[-20:].std() * np.sqrt(288))  # 5-min annualized
        else:
            features['realized_vol'] = 0.02
        
        return features
    
    def _extract_volume_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract volume features for trade confirmation"""
        features = {}
        volume = df['volume']
        close = df['close']
        
        # Volume ratio vs 20-period average
        volume_sma = volume.rolling(20).mean()
        features['volume_sma'] = float(volume_sma.iloc[-1]) if not pd.isna(volume_sma.iloc[-1]) else float(volume.mean())
        
        if features['volume_sma'] > 0:
            features['volume_ratio'] = float(volume.iloc[-1] / features['volume_sma'])
        else:
            features['volume_ratio'] = 1.0
        
        # Volume trend (increasing/decreasing/neutral)
        if len(volume) >= 5:
            recent_volume = volume.iloc[-5:].mean()
            prev_volume = volume.iloc[-10:-5].mean() if len(volume) >= 10 else recent_volume
            
            if recent_volume > prev_volume * 1.2:
                features['volume_trend'] = 'increasing'
            elif recent_volume < prev_volume * 0.8:
                features['volume_trend'] = 'decreasing'
            else:
                features['volume_trend'] = 'neutral'
        else:
            features['volume_trend'] = 'neutral'
        
        # Volume confirmation (high volume on breakouts)
        features['volume_confirmation'] = features['volume_ratio'] > 1.5
        
        return features
    
    def _extract_price_action(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract price action patterns and support/resistance"""
        features = {}
        high = df['high']
        low = df['low']
        close = df['close']
        open_price = df['open']
        
        # Support/resistance levels (20-period)
        if len(df) >= 20:
            features['support_level'] = float(low.iloc[-20:].min())
            features['resistance_level'] = float(high.iloc[-20:].max())
            
            # Distance from key levels
            current_price = close.iloc[-1]
            features['support_distance'] = float((current_price - features['support_level']) / current_price)
            features['resistance_distance'] = float((features['resistance_level'] - current_price) / current_price)
        else:
            features['support_level'] = float(low.min())
            features['resistance_level'] = float(high.max())
            features['support_distance'] = 0.0
            features['resistance_distance'] = 0.0
        
        # Price momentum (5 and 10 periods)
        if len(close) >= 5:
            features['momentum_5'] = float((close.iloc[-1] - close.iloc[-6]) / close.iloc[-6])
        else:
            features['momentum_5'] = 0.0
            
        if len(close) >= 10:
            features['momentum_10'] = float((close.iloc[-1] - close.iloc[-11]) / close.iloc[-11])
        else:
            features['momentum_10'] = 0.0
        
        return features
    
    def _extract_regime_state(self, df: pd.DataFrame, features: Dict[str, Any]) -> Dict[str, Any]:
        """Classify market regime based on winner strategy criteria"""
        regime_features = {}
        
        # EMA-based regime (winner strategy uses ema_cross type)
        ema_10 = features.get('ema_10', 0)
        ema_58 = features.get('ema_58', 0)
        
        if ema_10 > ema_58:
            # Uptrend regime
            if features.get('trend_strength', 0) > 0.02:  # Strong uptrend
                regime_features['regime_state'] = 'strong_uptrend'
            else:
                regime_features['regime_state'] = 'weak_uptrend'
        else:
            # Downtrend regime
            if features.get('trend_strength', 0) > 0.02:  # Strong downtrend
                regime_features['regime_state'] = 'strong_downtrend'  
            else:
                regime_features['regime_state'] = 'weak_downtrend'
        
        # Entry/exit conditions based on winner strategy
        rsi_val = features.get('rsi_14', 50)
        
        # Entry conditions (RSI below 27 AND uptrend regime)
        regime_features['entry_conditions'] = {
            'rsi_oversold': rsi_val < 27,
            'uptrend_regime': features.get('regime_direction') == 'up',
            'entry_signal': (rsi_val < 27) and (features.get('regime_direction') == 'up')
        }
        
        # Exit conditions (RSI above 58 OR regime change)
        regime_features['exit_conditions'] = {
            'rsi_overbought': rsi_val > 58,
            'regime_change': features.get('regime_direction') != 'up',
            'exit_signal': (rsi_val > 58) or (features.get('regime_direction') != 'up')
        }
        
        # Risk metrics from winner config
        regime_features['risk_metrics'] = {
            'take_profit': 0.0722576337714539,  # Winner TP
            'stop_loss': 0.042335733253338684,  # Winner SL
            'max_orders': 1,  # Winner max orders
            'atr_cap_pct': 0.03  # Winner ATR cap
        }
        
        return regime_features
    
    def _generate_winner_signals(self, features: Dict[str, Any]) -> Dict[str, float]:
        """Generate trading signals based on winner strategy logic"""
        signals = {'entry_long': 0.0, 'entry_short': 0.0, 'exit_signal': 0.0}
        
        try:
            # Winner strategy is long-only based on RSI + EMA regime
            rsi_val = features.get('rsi_14', 50)
            regime_direction = features.get('regime_direction', 'neutral')
            volume_confirmation = features.get('volume_confirmation', False)
            
            # Entry signal strength
            if regime_direction == 'up' and rsi_val < 27:
                # Strong entry signal
                entry_strength = 0.8
                
                # Volume confirmation boost
                if volume_confirmation:
                    entry_strength = min(1.0, entry_strength * 1.2)
                
                # Trend strength adjustment
                trend_strength = features.get('trend_strength', 0)
                if trend_strength > 0.05:  # Very strong trend
                    entry_strength = min(1.0, entry_strength * 1.1)
                
                signals['entry_long'] = entry_strength
            
            # Exit signal strength  
            if rsi_val > 58 or regime_direction != 'up':
                # Strong exit signal
                exit_strength = 0.8
                
                if rsi_val > 70:  # Very overbought
                    exit_strength = 1.0
                
                signals['exit_signal'] = exit_strength
            
            # Winner strategy doesn't use short positions
            signals['entry_short'] = 0.0
            
        except Exception as e:
            self.logger.error(f"Signal generation error: {e}")
        
        return signals
    
    def _calculate_quality_score(self, df: pd.DataFrame) -> float:
        """Calculate data quality score for features"""
        if df.empty:
            return 0.0
        
        # Check completeness
        missing_ratio = df.isnull().sum().sum() / (len(df) * len(df.columns))
        
        # Check for reasonable price data
        price_cols = ['open', 'high', 'low', 'close']
        price_valid = True
        
        for col in price_cols:
            if col in df.columns:
                if (df[col] <= 0).any() or df[col].isnull().any():
                    price_valid = False
                    break
        
        # Base score
        quality_score = 1.0 - missing_ratio
        
        if not price_valid:
            quality_score *= 0.5
        
        # Sufficient data penalty
        if len(df) < 58:
            quality_score *= 0.6
        
        return max(0.0, min(1.0, quality_score))
    
    def _error_response(self, error_msg: str, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Generate error response structure"""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": symbol,
            "timeframe": timeframe,
            "error": error_msg,
            "features": {},
            "signals": {"entry_long": 0.0, "entry_short": 0.0, "exit_signal": 0.0},
            "metadata": {
                "n_features": 0,
                "computation_time_ms": 0.0,
                "data_quality_score": 0.0,
                "regime_state": "error"
            }
        }
    
    def validate_signal(self, signal_data: Dict[str, Any]) -> bool:
        """
        Validate signal quality before execution
        
        Args:
            signal_data: Complete signal dictionary from extract()
            
        Returns:
            True if valid for trading execution
        """
        if 'error' in signal_data:
            return False
        
        required_fields = ['timestamp', 'symbol', 'features', 'signals']
        if not all(field in signal_data for field in required_fields):
            return False
        
        # Validate signals range
        signals = signal_data.get('signals', {})
        for signal_type in ['entry_long', 'entry_short', 'exit_signal']:
            if signal_type in signals:
                value = signals[signal_type]
                if not isinstance(value, (int, float)) or not (0 <= value <= 1):
                    return False
        
        # Check data freshness (max 5 minutes)
        try:
            timestamp = datetime.fromisoformat(signal_data['timestamp'].replace('Z', '+00:00'))
            age = datetime.now(timezone.utc) - timestamp
            if age.total_seconds() > 300:
                return False
        except:
            return False
        
        # Validate data quality
        quality_score = signal_data.get('metadata', {}).get('data_quality_score', 0.0)
        if quality_score < 0.7:  # Minimum quality threshold
            return False
        
        return True
    
    def get_feature_names(self) -> List[str]:
        """Get list of all feature names for winner strategy"""
        return [
            # Price features
            'close', 'return_1', 'log_return_1',
            # Trend features  
            'ema_10', 'ema_58', 'regime_direction', 'trend_strength',
            # Momentum features
            'rsi_14', 'rsi_entry_signal', 'rsi_exit_signal',
            # Volatility features
            'atr_14', 'atr_cap_pct', 'realized_vol',
            # Volume features
            'volume_ratio', 'volume_trend', 'volume_confirmation',
            # Price action features
            'support_level', 'resistance_level', 'support_distance', 'resistance_distance',
            'momentum_5', 'momentum_10',
            # Regime features
            'regime_state', 'entry_conditions', 'exit_conditions', 'risk_metrics'
        ]

def main():
    """
    Test the Winner Strategy Features Extractor with sample data
    """
    print("Testing Winner Strategy Features Extractor...")
    
    try:
        # Create sample OHLCV data
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=100, freq='5min')
        
        # Simulate realistic BTC price data
        base_price = 42000
        returns = np.random.normal(0, 0.002, 100)
        prices = base_price * (1 + returns).cumprod()
        
        # Create OHLCV with some realistic intrabar patterns
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.normal(0, 0.0005, 100)),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.001, 100))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.001, 100))),
            'close': prices,
            'volume': np.random.lognormal(10, 0.5, 100)  # Realistic volume distribution
        })
        
        # Initialize extractor
        extractor = FeatureExtractor(log_level="INFO")
        
        # Extract features
        result = extractor.extract(df, "BTC/USD", "5m")
        
        # Test results
        if 'error' not in result:
            print("✓ Feature extraction successful")
            print(f"✓ Symbol: {result['symbol']}")
            print(f"✓ Timeframe: {result['timeframe']}")
            print(f"✓ Features computed: {result['metadata']['n_features']}")
            print(f"✓ Data quality: {result['metadata']['data_quality_score']:.3f}")
            print(f"✓ Computation time: {result['metadata']['computation_time_ms']:.1f}ms")
            print(f"✓ Regime state: {result['metadata']['regime_state']}")
            
            # Print winner strategy specific features
            features = result['features']
            print("\n--- Winner Strategy Features ---")
            print(f"RSI(14): {features['momentum']['rsi_14']:.2f}")
            print(f"EMA(10): {features['trend']['ema_10']:.2f}")
            print(f"EMA(58): {features['trend']['ema_58']:.2f}")
            print(f"Regime: {features['trend']['regime_direction']}")
            print(f"Trend Strength: {features['trend']['trend_strength']:.4f}")
            print(f"ATR(14): {features['volatility']['atr_14']:.2f}")
            print(f"Volume Ratio: {features['volume']['volume_ratio']:.2f}")
            
            # Print signals
            signals = result['signals']
            print("\n--- Trading Signals ---")
            print(f"Entry Long: {signals['entry_long']:.3f}")
            print(f"Entry Short: {signals['entry_short']:.3f}")
            print(f"Exit Signal: {signals['exit_signal']:.3f}")
            
            # Print entry/exit conditions
            exec_features = features['execution']
            entry_cond = exec_features['entry_conditions']
            exit_cond = exec_features['exit_conditions']
            
            print("\n--- Winner Strategy Conditions ---")
            print(f"RSI Entry Signal (< 27): {entry_cond['rsi_oversold']}")
            print(f"Uptrend Regime: {entry_cond['uptrend_regime']}")
            print(f"Combined Entry: {entry_cond['entry_signal']}")
            print(f"RSI Exit Signal (> 58): {exit_cond['rsi_overbought']}")
            print(f"Regime Change: {exit_cond['regime_change']}")
            print(f"Combined Exit: {exit_cond['exit_signal']}")
            
            # Validate signal
            is_valid = extractor.validate_signal(result)
            print(f"\n✓ Signal validation: {'PASS' if is_valid else 'FAIL'}")
            
            # Print risk metrics
            risk_metrics = exec_features['risk_metrics']
            print("\n--- Risk Management (Winner Config) ---")
            print(f"Take Profit: {risk_metrics['take_profit']:.4f} ({risk_metrics['take_profit']*100:.2f}%)")
            print(f"Stop Loss: {risk_metrics['stop_loss']:.4f} ({risk_metrics['stop_loss']*100:.2f}%)")
            print(f"Max Orders: {risk_metrics['max_orders']}")
            print(f"ATR Cap: {risk_metrics['atr_cap_pct']*100:.1f}%")
            
        else:
            print(f"✗ Error: {result['error']}")
            
    except Exception as e:
        print(f"✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()