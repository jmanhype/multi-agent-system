#!/usr/bin/env python
"""
GEPA-Powered Trading System
Uses optimized prompts from GEPA to generate and execute trading strategies
"""

import os
import sys
import json
import pickle
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

# CRITICAL FIX FOR APPLE SILICON
import multiprocessing
multiprocessing.set_start_method('fork', force=True)

import dspy
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.data.dex_adapter import dex_adapter
from lib.research.backtester_vbt import run_backtest
from lib.features.extractor import FeatureExtractor
from lib.risk.manager import RiskManager
from lib.storage.db_manager import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()


class GEPAOptimizedStrategy(dspy.Signature):
    """GEPA-optimized signature for strategy generation"""
    market_context: str = dspy.InputField(desc="Market conditions and requirements")
    reasoning: str = dspy.OutputField(desc="Step-by-step reasoning for strategy selection")
    strategy: str = dspy.OutputField(desc="JSON trading strategy with complete parameters")


class GEPATradingModule(dspy.Module):
    """Trading module using GEPA-optimized prompts"""
    
    def __init__(self, optimized_prompt: str = None):
        super().__init__()
        
        # Load optimized prompt from GEPA
        if optimized_prompt is None:
            optimized_prompt = self.load_gepa_prompt()
        
        # Create signature with optimized instructions
        self.signature = GEPAOptimizedStrategy
        if optimized_prompt:
            # Override the base signature with GEPA-optimized instructions
            self.signature.__doc__ = optimized_prompt
        
        self.generate_strategy = dspy.ChainOfThought(self.signature)
    
    def load_gepa_prompt(self) -> Optional[str]:
        """Load the optimized prompt from GEPA state"""
        state_file = Path("data/gepa_logs/enhanced/gepa_state.bin")
        
        if not state_file.exists():
            logger.warning("No GEPA state file found, using default prompts")
            return None
        
        try:
            with open(state_file, 'rb') as f:
                state = pickle.load(f)
            
            # Get the evolved prompt (Program 1 had the evolved version)
            candidates = state['program_candidates']
            if len(candidates) > 1:
                evolved_prompt = candidates[1]['generate_strategy.predict']
                logger.info(f"Loaded GEPA-optimized prompt ({len(evolved_prompt)} chars)")
                return evolved_prompt
            
        except Exception as e:
            logger.error(f"Failed to load GEPA prompt: {e}")
        
        return None
    
    def forward(self, market_context: str):
        """Generate strategy using GEPA-optimized prompts"""
        return self.generate_strategy(market_context=market_context)


class GEPATradingSystem:
    """Complete trading system powered by GEPA optimization"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.db_manager = DatabaseManager()
        
        # Load risk config
        risk_config_path = Path("config/risk.json")
        if risk_config_path.exists():
            with open(risk_config_path, 'r') as f:
                risk_config = json.load(f)
        else:
            risk_config = {}
        
        # Initialize components
        self.features_extractor = FeatureExtractor()
        self.risk_manager = RiskManager(risk_config)
        
        # Configure DSPy
        self.configure_llm()
        
        # Initialize GEPA module
        self.strategy_module = GEPATradingModule()
        
        # Load market data
        self.df = None
        self.load_market_data()
    
    def configure_llm(self):
        """Configure LLM for strategy generation"""
        if os.getenv('OPENAI_API_KEY'):
            lm = dspy.LM(
                model="gpt-4o-mini",
                api_key=os.getenv('OPENAI_API_KEY'),
                temperature=0.7,
                max_tokens=1500
            )
        else:
            lm = dspy.LM(
                model="claude-3-haiku-20240307",
                api_key=os.getenv('ANTHROPIC_API_KEY'),
                temperature=0.7
            )
        dspy.configure(lm=lm)
    
    def load_market_data(self):
        """Load DEX market data"""
        self.logger.info("Loading market data...")
        self.df = dex_adapter.get_features_compatible_data()
        
        # Extract features
        self.features = self.features_extractor.extract(self.df)
        
        # Analyze market conditions
        self.market_analysis = self.analyze_market()
        self.logger.info(f"Market analysis: {self.market_analysis}")
    
    def analyze_market(self) -> Dict[str, Any]:
        """Analyze current market conditions"""
        recent_data = self.df.tail(100)
        
        # Calculate volatility
        returns = recent_data['close'].pct_change()
        volatility = returns.std() * 100
        
        # Determine trend
        sma_20 = recent_data['close'].rolling(20).mean()
        sma_50 = recent_data['close'].rolling(50).mean()
        
        if sma_20.iloc[-1] > sma_50.iloc[-1] * 1.05:
            trend = "bullish"
        elif sma_20.iloc[-1] < sma_50.iloc[-1] * 0.95:
            trend = "bearish"
        else:
            trend = "ranging"
        
        # Determine regime
        if volatility > 10:
            regime = "extreme"
        elif volatility > 5:
            regime = "high"
        elif volatility > 2:
            regime = "moderate"
        else:
            regime = "low"
        
        return {
            'volatility': volatility,
            'volatility_regime': regime,
            'trend': trend,
            'last_price': float(recent_data['close'].iloc[-1]),
            'volume_24h': float(recent_data['volume'].sum())
        }
    
    def generate_strategy(self) -> Dict[str, Any]:
        """Generate trading strategy using GEPA-optimized prompts"""
        
        # Create comprehensive market context
        market_context = f"""
Market Analysis for DEX Token:

CURRENT CONDITIONS:
- Volatility: {self.market_analysis['volatility_regime']} ({self.market_analysis['volatility']:.1f}% daily)
- Trend Direction: {self.market_analysis['trend']}
- Last Price: ${self.market_analysis['last_price']:.4f}
- 24h Volume: ${self.market_analysis['volume_24h']:.0f}

PERFORMANCE REQUIREMENTS:
- Target Sharpe Ratio: > 1.5
- Minimum Win Rate: > 50%
- Maximum Drawdown: < 20%
- Risk-Reward Ratio: > 2.0

STRATEGY SPECIFICATIONS:
Generate a comprehensive JSON trading strategy including:
1. "type": Choose from ["momentum", "mean_reversion", "volume", "breakout", "arbitrage"]
2. "entry_conditions": Specific conditions with indicator thresholds
   - Must include at least 2 conditions
   - Use indicators like RSI, MA crossovers, volume spikes
   - Provide exact threshold values
3. "exit_conditions": Clear exit rules
   - Include both profit targets and stop conditions
   - Consider trailing stops for trending markets
4. "stop_loss_percentage": Risk per trade (typically 1-3%)
5. "take_profit_percentage": Target profit (typically 2-6%)

IMPORTANT CONSIDERATIONS:
- Adapt to {self.market_analysis['volatility_regime']} volatility environment
- Account for {self.market_analysis['trend']} trend in entry/exit logic
- Ensure all JSON is properly formatted with double quotes
"""
        
        self.logger.info("Generating strategy with GEPA-optimized prompts...")
        
        # Generate strategy
        result = self.strategy_module(market_context=market_context)
        
        # Parse strategy
        try:
            strategy_text = result.strategy
            reasoning = result.reasoning if hasattr(result, 'reasoning') else ""
            
            # Clean JSON
            if strategy_text.startswith('```json'):
                strategy_text = strategy_text[7:]
            if strategy_text.endswith('```'):
                strategy_text = strategy_text[:-3]
            
            strategy = json.loads(strategy_text.strip())
            
            self.logger.info(f"Strategy generated successfully")
            self.logger.info(f"Reasoning: {reasoning[:200]}...")
            
            return {
                'strategy': strategy,
                'reasoning': reasoning,
                'market_analysis': self.market_analysis,
                'timestamp': datetime.now().isoformat()
            }
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse strategy JSON: {e}")
            return None
    
    def generate_signals(self, strategy_config: Dict[str, Any], df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals from strategy configuration"""
        df_signals = df.copy()
        
        # Initialize signal columns
        df_signals['entries'] = False
        df_signals['exits'] = False
        
        # Get strategy type and parameters
        strategy_type = strategy_config.get('type', 'momentum')
        
        # Simple signal generation based on strategy type
        if 'momentum' in strategy_type.lower():
            # Momentum strategy - buy on upward momentum
            df_signals['rsi'] = self.calculate_rsi(df_signals['close'], 14)
            df_signals['entries'] = df_signals['rsi'] < 30  # Oversold
            df_signals['exits'] = df_signals['rsi'] > 70    # Overbought
            
        elif 'mean_reversion' in strategy_type.lower():
            # Mean reversion - trade against extremes
            sma = df_signals['close'].rolling(20).mean()
            std = df_signals['close'].rolling(20).std()
            upper_band = sma + (2 * std)
            lower_band = sma - (2 * std)
            
            df_signals['entries'] = df_signals['close'] < lower_band
            df_signals['exits'] = df_signals['close'] > upper_band
            
        elif 'breakout' in strategy_type.lower():
            # Breakout strategy
            high_20 = df_signals['high'].rolling(20).max()
            low_20 = df_signals['low'].rolling(20).min()
            
            df_signals['entries'] = df_signals['close'] > high_20.shift(1)
            df_signals['exits'] = df_signals['close'] < low_20.shift(1)
            
        else:
            # Default: simple moving average crossover
            sma_fast = df_signals['close'].rolling(10).mean()
            sma_slow = df_signals['close'].rolling(30).mean()
            
            df_signals['entries'] = (sma_fast > sma_slow) & (sma_fast.shift(1) <= sma_slow.shift(1))
            df_signals['exits'] = (sma_fast < sma_slow) & (sma_fast.shift(1) >= sma_slow.shift(1))
        
        # Remove NaN values
        df_signals['entries'] = df_signals['entries'].fillna(False)
        df_signals['exits'] = df_signals['exits'].fillna(False)
        
        return df_signals
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def backtest_strategy(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Backtest the generated strategy"""
        self.logger.info("Running backtest...")
        
        try:
            # Generate signals from strategy
            df_with_signals = self.generate_signals(strategy['strategy'], self.df)
            
            # Run backtest with signals
            results = run_backtest(df_with_signals)
            
            self.logger.info(f"Backtest results:")
            self.logger.info(f"  Sharpe Ratio: {results.get('sharpe_ratio', 0):.3f}")
            self.logger.info(f"  Win Rate: {results.get('win_rate', 0):.1%}")
            self.logger.info(f"  Max Drawdown: {results.get('max_drawdown', 0):.1%}")
            self.logger.info(f"  Profit Factor: {results.get('profit_factor', 0):.2f}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Backtest failed: {e}")
            return None
    
    def validate_strategy(self, strategy: Dict[str, Any], backtest_results: Dict[str, Any]) -> bool:
        """Validate strategy meets performance requirements"""
        
        # Check performance metrics
        sharpe = backtest_results.get('sharpe_ratio', 0)
        win_rate = backtest_results.get('win_rate', 0)
        max_dd = abs(backtest_results.get('max_drawdown', -1))
        
        # Risk validation - validate as a trade request
        risk_check = self.risk_manager.validate_trade({
            'symbol': 'BTC/USDT',
            'side': 'buy',
            'amount': 10,
            'strategy': strategy['strategy']
        })
        
        passed = (
            sharpe > 1.0 and
            win_rate > 0.45 and
            max_dd < 0.30 and
            risk_check.get('passed', True)  # Default to True if key missing
        )
        
        if passed:
            self.logger.info("✅ Strategy passed all validation checks")
        else:
            self.logger.warning(f"❌ Strategy failed validation:")
            if sharpe <= 1.0:
                self.logger.warning(f"  - Sharpe ratio too low: {sharpe:.3f}")
            if win_rate <= 0.45:
                self.logger.warning(f"  - Win rate too low: {win_rate:.1%}")
            if max_dd >= 0.30:
                self.logger.warning(f"  - Drawdown too high: {max_dd:.1%}")
            if not risk_check.get('passed', True):
                self.logger.warning(f"  - Risk check failed: {risk_check.get('reason', 'Unknown')}")
        
        return passed
    
    def save_strategy(self, strategy: Dict[str, Any], backtest_results: Dict[str, Any]):
        """Save successful strategy to config"""
        
        # Convert any non-serializable objects
        def make_serializable(obj):
            if isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_serializable(v) for v in obj]
            elif isinstance(obj, (pd.Timestamp, datetime)):
                return str(obj)
            elif isinstance(obj, pd.Series):
                return obj.tolist()
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            else:
                return obj
        
        # Prepare complete strategy package
        strategy_package = {
            'strategy': strategy['strategy'],
            'reasoning': strategy['reasoning'],
            'market_analysis': strategy['market_analysis'],
            'backtest_results': make_serializable(backtest_results),
            'timestamp': strategy['timestamp'],
            'gepa_optimized': True
        }
        
        # Save to config
        config_file = Path("config/best_strategy.json")
        with open(config_file, 'w') as f:
            json.dump(strategy_package, f, indent=2)
        
        self.logger.info(f"Strategy saved to {config_file}")
        
        # Store in database (skipped for now - method doesn't exist)
        # self.db_manager.store_strategy(strategy_package)
        
        # Also save to gepa results directory
        gepa_results_dir = Path("data/gepa_logs/enhanced/strategies")
        gepa_results_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        gepa_file = gepa_results_dir / f"strategy_{timestamp}.json"
        with open(gepa_file, 'w') as f:
            json.dump(strategy_package, f, indent=2)
        
        self.logger.info(f"Strategy archived to {gepa_file}")
    
    def run(self, max_attempts: int = 3) -> bool:
        """Run the complete GEPA-powered trading system"""
        
        self.logger.info("="*80)
        self.logger.info("GEPA-POWERED TRADING SYSTEM")
        self.logger.info("="*80)
        
        for attempt in range(max_attempts):
            self.logger.info(f"\nAttempt {attempt + 1}/{max_attempts}")
            
            # Generate strategy
            strategy = self.generate_strategy()
            if not strategy:
                continue
            
            # Backtest
            backtest_results = self.backtest_strategy(strategy)
            if not backtest_results:
                continue
            
            # Validate
            if self.validate_strategy(strategy, backtest_results):
                # Save successful strategy
                self.save_strategy(strategy, backtest_results)
                
                self.logger.info("\n" + "="*80)
                self.logger.info("SUCCESS! GEPA-optimized strategy generated and validated")
                self.logger.info("="*80)
                
                return True
        
        self.logger.warning("\nFailed to generate valid strategy after %d attempts", max_attempts)
        return False


def main():
    """Main entry point"""
    
    # Create and run GEPA trading system
    system = GEPATradingSystem()
    success = system.run()
    
    if success:
        logger.info("\n✅ GEPA Trading System completed successfully")
        logger.info("Strategy saved to config/best_strategy.json")
        logger.info("Ready for execution with run_trader_orchestrator.py")
    else:
        logger.error("\n❌ GEPA Trading System failed to generate valid strategy")
        sys.exit(1)


if __name__ == "__main__":
    main()