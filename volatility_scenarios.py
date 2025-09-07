#!/usr/bin/env python
"""
Test how the GEPA system handles different volatility scenarios
Including the requested 10% daily volatility case
"""

import pandas as pd
import numpy as np
import json
import sys
sys.path.insert(0, '/Users/speed/Downloads/multi-agent-system')

from lib.data.dex_adapter import dex_adapter
from gepa_optimizer import create_enhanced_metric, TradingStrategyModule
import dspy
from dspy import Example
from dspy.teleprompt.gepa.gepa_utils import ScoreWithFeedback

# Create synthetic data with different volatility levels
def create_test_data(volatility_pct=10.0, periods=1000):
    """Create synthetic OHLCV data with specified daily volatility"""
    
    # Daily volatility as decimal
    daily_vol = volatility_pct / 100
    
    # Generate returns with specified volatility
    returns = np.random.normal(0, daily_vol, periods)
    
    # Create price series
    initial_price = 100
    prices = initial_price * np.exp(np.cumsum(returns))
    
    # Create OHLCV
    dates = pd.date_range(end=pd.Timestamp.now(), periods=periods, freq='5min')
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices * (1 + np.random.uniform(-0.005, 0.005, periods)),
        'high': prices * (1 + np.random.uniform(0, 0.01, periods)),
        'low': prices * (1 - np.random.uniform(0, 0.01, periods)),
        'close': prices,
        'volume': np.random.uniform(1000, 10000, periods)
    })
    
    df = df.set_index('timestamp')
    
    # Verify volatility
    actual_vol = df['close'].pct_change().std() * 100
    print(f"Created data with target {volatility_pct}% volatility, actual: {actual_vol:.2f}%")
    
    return df

def test_volatility_scenarios():
    """Test GEPA system with different volatility levels"""
    
    scenarios = [
        (0.7, "low"),      # Current system level
        (2.0, "moderate"), # Normal crypto
        (5.0, "high"),     # High volatility
        (10.0, "extreme"), # Requested 10% level
        (20.0, "crisis"),  # Extreme crisis
    ]
    
    # Simple backtest function for testing
    def mock_backtest(strategy, df):
        """Mock backtest that adjusts results based on volatility"""
        vol = df['close'].pct_change().std() * 100
        
        # Simulate worse performance in extreme volatility
        if vol > 10:
            sharpe = np.random.uniform(0.3, 0.8)
            win_rate = np.random.uniform(0.35, 0.45)
            max_dd = -np.random.uniform(0.3, 0.5)
        elif vol > 5:
            sharpe = np.random.uniform(0.8, 1.5)
            win_rate = np.random.uniform(0.4, 0.5)
            max_dd = -np.random.uniform(0.2, 0.35)
        else:
            sharpe = np.random.uniform(1.5, 2.5)
            win_rate = np.random.uniform(0.5, 0.6)
            max_dd = -np.random.uniform(0.1, 0.25)
        
        return {
            'sharpe_ratio': sharpe,
            'win_rate': win_rate,
            'max_drawdown': max_dd,
            'profit_factor': 1 + (sharpe * 0.2),
            'total_trades': 100
        }
    
    results = []
    
    for vol_pct, regime in scenarios:
        print(f"\n{'='*60}")
        print(f"Testing {regime} volatility: {vol_pct}%")
        print(f"{'='*60}")
        
        # Create test data
        df = create_test_data(vol_pct)
        
        # Create metric with this data
        metric = create_enhanced_metric(lambda s: mock_backtest(s, df))
        
        # Test different strategy responses
        test_strategies = [
            {
                "type": "momentum",
                "entry_conditions": {"rsi": 30, "volume_surge": 1.5},
                "exit_conditions": {"rsi": 70},
                "stop_loss_percentage": 2,
                "take_profit_percentage": 5
            },
            {
                "type": "mean_reversion",
                "entry_conditions": {"zscore": 2.0},
                "exit_conditions": {"zscore": 0.5},
                "stop_loss_percentage": 3,
                "take_profit_percentage": 3
            }
        ]
        
        for strategy in test_strategies:
            # Create mock prediction
            class MockPred:
                def __init__(self, s):
                    self.strategy = json.dumps(s)
                    self.reasoning = f"Strategy for {vol_pct}% volatility environment"
            
            pred = MockPred(strategy)
            
            # Evaluate
            result = metric(None, pred)
            
            print(f"\n{strategy['type'].upper()} Strategy:")
            print(f"  Score: {result.score:.3f}")
            print(f"  Feedback: {result.feedback[:200]}...")
            
            # Check for failures
            if result.score == 0.0:
                print("  ⚠️ COMPLETE FAILURE (0.0 score)")
            elif result.score < 0.1:
                print("  ⚠️ PARTIAL FAILURE (< 0.1 score)")
            
            results.append({
                'volatility': vol_pct,
                'regime': regime,
                'strategy': strategy['type'],
                'score': result.score,
                'failed': result.score < 0.1
            })
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY OF VOLATILITY HANDLING")
    print(f"{'='*60}")
    
    for r in results:
        status = "❌ FAILED" if r['failed'] else "✅ OK"
        print(f"{r['regime']:10} ({r['volatility']:4.1f}%) - {r['strategy']:15} - Score: {r['score']:.3f} {status}")
    
    # Check specific 10% case
    ten_pct_results = [r for r in results if r['volatility'] == 10.0]
    if any(r['failed'] for r in ten_pct_results):
        print("\n⚠️ WARNING: System struggles with 10% volatility!")
        print("Some strategies returned failure scores (< 0.1)")
    else:
        print("\n✅ System handles 10% volatility adequately")
        avg_score = sum(r['score'] for r in ten_pct_results) / len(ten_pct_results)
        print(f"Average score at 10% volatility: {avg_score:.3f}")

if __name__ == "__main__":
    test_volatility_scenarios()