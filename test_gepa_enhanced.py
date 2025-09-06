#!/usr/bin/env python
"""
Enhanced GEPA implementation for trading strategies
Applying patterns learned from DSPy tutorials
"""

import logging
import sys
import os
from pathlib import Path
import json
from dotenv import load_dotenv
import dspy
from dspy import Example
from dspy.teleprompt import GEPA
from dspy.teleprompt.gepa.gepa_utils import ScoreWithFeedback

# CRITICAL FIX FOR APPLE SILICON
import multiprocessing
multiprocessing.set_start_method('fork', force=True)

# Add project root to path
sys.path.insert(0, '/Users/speed/Downloads/multi-agent-system')
from lib.data.dex_adapter import dex_adapter
from lib.research.backtest_wrapper import run_backtest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()


class StrategyGenerator(dspy.Signature):
    """Generate advanced trading strategy with comprehensive requirements"""
    market_context: str = dspy.InputField(desc="Market conditions, volatility, and requirements")
    reasoning: str = dspy.OutputField(desc="Step-by-step reasoning for strategy selection")
    strategy: str = dspy.OutputField(desc="JSON trading strategy with complete parameters")


class TradingStrategyModule(dspy.Module):
    """Enhanced module with multi-stage reasoning"""
    
    def __init__(self):
        super().__init__()
        self.generate_strategy = dspy.ChainOfThought(StrategyGenerator)
    
    def forward(self, market_context: str):
        return self.generate_strategy(market_context=market_context)


def create_enhanced_metric(backtest_func):
    """
    Enhanced metric with detailed, actionable feedback
    Applies patterns from GEPA tutorials
    """
    
    def metric(gold: Example, pred, trace=None, pred_name=None, pred_trace=None):
        """
        Comprehensive evaluation with multi-objective feedback
        Returns: ScoreWithFeedback with actionable insights
        """
        
        # Parse strategy
        try:
            strategy_text = pred.strategy if hasattr(pred, 'strategy') else str(pred)
            reasoning = pred.reasoning if hasattr(pred, 'reasoning') else ""
            
            # Clean JSON
            if strategy_text.startswith('```json'):
                strategy_text = strategy_text[7:]
            if strategy_text.endswith('```'):
                strategy_text = strategy_text[:-3]
            
            strategy = json.loads(strategy_text.strip())
            
        except (json.JSONDecodeError, AttributeError) as e:
            # Detailed parse error feedback
            feedback = f"JSON parsing failed: {str(e)[:100]}. "
            feedback += "Ensure output is valid JSON with all required fields: "
            feedback += "type, entry_conditions, exit_conditions, stop_loss_percentage, take_profit_percentage. "
            feedback += "Use double quotes for all strings and proper JSON formatting."
            
            return ScoreWithFeedback(score=0.0, feedback=feedback)
        
        # Validate required fields
        required_fields = ['type', 'entry_conditions', 'exit_conditions', 
                          'stop_loss_percentage', 'take_profit_percentage']
        missing_fields = [f for f in required_fields if f not in strategy]
        
        if missing_fields:
            feedback = f"Missing required fields: {missing_fields}. "
            feedback += "Every strategy must include all required fields with appropriate values."
            return ScoreWithFeedback(score=0.1, feedback=feedback)
        
        # Run backtest
        try:
            results = backtest_func(strategy)
        except Exception as e:
            feedback = f"Backtest failed: {str(e)[:100]}. "
            feedback += "Check that entry/exit conditions use valid indicators and thresholds. "
            feedback += "Ensure stop_loss and take_profit are positive percentages."
            return ScoreWithFeedback(score=0.05, feedback=feedback)
        
        # Multi-objective evaluation
        sharpe = results.get('sharpe_ratio', 0)
        win_rate = results.get('win_rate', 0.5)
        max_dd = abs(results.get('max_drawdown', -1))
        profit_factor = results.get('profit_factor', 1)
        total_trades = results.get('total_trades', 0)
        
        # Calculate composite score
        score_components = {
            'sharpe': min(sharpe / 2.0, 1.0) * 0.35,  # Target Sharpe > 2
            'win_rate': win_rate * 0.25,
            'drawdown': (1 - min(max_dd * 2, 1)) * 0.25,  # Target DD < 50%
            'profit_factor': min(profit_factor / 2, 1) * 0.15
        }
        
        score = sum(score_components.values())
        
        # Generate detailed, actionable feedback
        feedback_parts = []
        
        # Sharpe ratio feedback
        if sharpe < 0.5:
            feedback_parts.append(
                f"Critical: Sharpe ratio {sharpe:.2f} is too low. "
                "Consider tighter entry conditions or adjusting position sizing. "
                "Try momentum strategies in trending markets or mean reversion in ranging markets."
            )
        elif sharpe < 1.0:
            feedback_parts.append(
                f"Sharpe ratio {sharpe:.2f} needs improvement. "
                "Fine-tune entry/exit thresholds. Consider adding filters for market regime."
            )
        elif sharpe > 1.5:
            feedback_parts.append(f"Excellent Sharpe ratio {sharpe:.2f}")
        
        # Win rate feedback
        if win_rate < 0.35:
            feedback_parts.append(
                f"Win rate {win_rate:.1%} is concerning. "
                "Entry conditions may be too aggressive. "
                "Consider waiting for stronger confirmation signals."
            )
        elif win_rate < 0.45:
            feedback_parts.append(
                f"Win rate {win_rate:.1%} could be better. "
                "Try adjusting entry timing or adding trend filters."
            )
        
        # Drawdown feedback
        if max_dd > 0.5:
            feedback_parts.append(
                f"Severe drawdown {max_dd:.1%}! "
                "Implement tighter stop losses or reduce position size. "
                "Consider adding volatility-based position sizing."
            )
        elif max_dd > 0.3:
            feedback_parts.append(
                f"High drawdown {max_dd:.1%}. "
                "Review risk management. Consider trailing stops."
            )
        
        # Trade frequency feedback
        if total_trades < 10:
            feedback_parts.append(
                "Too few trades for reliable statistics. "
                "Consider relaxing entry conditions slightly."
            )
        elif total_trades > 1000:
            feedback_parts.append(
                "Very high trade frequency may indicate overtrading. "
                "Consider adding minimum profit targets."
            )
        
        # Strategy-specific recommendations
        if strategy.get('type') == 'momentum' and sharpe < 1:
            feedback_parts.append(
                "Momentum strategy underperforming. "
                "Try stronger trend filters or wait for breakout confirmation."
            )
        elif strategy.get('type') == 'mean_reversion' and win_rate < 0.5:
            feedback_parts.append(
                "Mean reversion struggling. "
                "Consider wider bands or stronger oversold/overbought thresholds."
            )
        
        # Reasoning quality feedback
        if reasoning and len(reasoning) < 50:
            feedback_parts.append(
                "Reasoning too brief. Explain WHY this strategy fits the market conditions."
            )
        
        # Combine feedback
        if not feedback_parts:
            feedback_parts.append("Strong performance across all metrics!")
        
        feedback = " | ".join(feedback_parts[:3])  # Top 3 most important
        
        # Add metrics summary
        feedback += f" [Sharpe={sharpe:.2f}, WR={win_rate:.1%}, DD={max_dd:.1%}, PF={profit_factor:.2f}]"
        
        return ScoreWithFeedback(
            score=min(1.0, max(0.0, score)),
            feedback=feedback
        )
    
    return metric


def create_diverse_training_examples():
    """
    Create diverse training examples covering various market conditions
    Based on patterns from tutorials
    """
    
    examples = []
    
    # Market scenarios with increasing complexity
    scenarios = [
        # Basic scenarios
        ("moderate (50% daily swings)", "bullish", "momentum", 1.2, "stable"),
        ("low (20% swings)", "ranging", "mean reversion", 1.0, "quiet"),
        ("high (100% swings)", "bearish", "short momentum", 1.3, "declining"),
        
        # Complex scenarios
        ("extreme (200%+ swings)", "parabolic", "breakout capture", 1.5, "explosive"),
        ("very high (150% swings)", "whipsaw", "volatility arbitrage", 1.4, "chaotic"),
        ("extreme (300% swings)", "crash", "defensive hedging", 1.0, "crisis"),
        
        # Edge cases
        ("minimal (10% swings)", "flat", "scalping", 0.8, "dormant"),
        ("extreme (500% swings)", "manipulation", "liquidity provision", 1.8, "irregular"),
        ("high (80% swings)", "recovery", "trend following", 1.3, "recovering"),
        
        # Regime changes
        ("increasing (20% to 100%)", "transitioning", "adaptive", 1.2, "changing"),
        ("decreasing (100% to 20%)", "stabilizing", "risk reduction", 1.1, "calming"),
        ("cyclic (20%-100%-20%)", "seasonal", "regime switching", 1.3, "cyclical"),
    ]
    
    for i, (volatility, trend, focus, target_sharpe, regime) in enumerate(scenarios):
        context = f"""
Market Analysis for DEX Token (Scenario {i+1}):

CURRENT CONDITIONS:
- Volatility: {volatility}
- Trend Direction: {trend}
- Market Regime: {regime}
- Recommended Strategy: {focus}

PERFORMANCE REQUIREMENTS:
- Target Sharpe Ratio: > {target_sharpe}
- Minimum Win Rate: > 45%
- Maximum Drawdown: < 25%
- Risk-Reward Ratio: > 1.5

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
6. "position_sizing": Optional risk-based sizing rules
7. "filters": Optional market regime filters

IMPORTANT CONSIDERATIONS:
- In {regime} markets, {focus} strategies typically perform best
- Adjust parameters for {volatility} volatility environment
- Account for {trend} trend direction in entry/exit logic
- Ensure all JSON is properly formatted with double quotes
"""
        
        example = Example(
            market_context=context
        ).with_inputs('market_context')
        
        examples.append(example)
    
    return examples


def main():
    """Run enhanced GEPA optimization with learned patterns"""
    
    logger.info("="*80)
    logger.info("ENHANCED GEPA OPTIMIZATION WITH LEARNED PATTERNS")
    logger.info("="*80)
    
    # Configure DSPy with appropriate models
    if os.getenv('OPENAI_API_KEY'):
        # Main model for strategy generation
        lm = dspy.LM(
            model="gpt-4o-mini",
            api_key=os.getenv('OPENAI_API_KEY'),
            temperature=0.7,  # Balanced creativity
            max_tokens=1500
        )
        
        # Reflection model with higher temperature for creative mutations
        reflection_lm = dspy.LM(
            model="gpt-4o",  # More powerful model for reflection
            api_key=os.getenv('OPENAI_API_KEY'),
            temperature=1.0,  # High temperature for diverse mutations
            max_tokens=3000
        )
    else:
        lm = dspy.LM(
            model="claude-3-haiku-20240307",
            api_key=os.getenv('ANTHROPIC_API_KEY'),
            temperature=0.7
        )
        reflection_lm = dspy.LM(
            model="claude-3-sonnet-20240229",
            api_key=os.getenv('ANTHROPIC_API_KEY'),
            temperature=1.0,
            max_tokens=3000
        )
    
    dspy.configure(lm=lm)
    
    # Load DEX data
    logger.info("Loading DEX data...")
    df = dex_adapter.get_features_compatible_data()
    logger.info(f"Loaded {len(df)} data points")
    
    # Create backtest function
    backtest_func = lambda s: run_backtest(s, df)
    
    # Create diverse training examples
    logger.info("Creating diverse training examples...")
    examples = create_diverse_training_examples()
    
    # Split data (70/30 for more training)
    split_idx = int(len(examples) * 0.7)
    train_examples = examples[:split_idx]
    val_examples = examples[split_idx:]
    
    logger.info(f"Training examples: {len(train_examples)}")
    logger.info(f"Validation examples: {len(val_examples)}")
    
    # Create enhanced module
    module = TradingStrategyModule()
    
    # Create enhanced metric
    metric = create_enhanced_metric(backtest_func)
    
    # Configure GEPA with learned patterns
    logger.info("\nConfiguring enhanced GEPA optimizer...")
    optimizer = GEPA(
        metric=metric,
        max_metric_calls=200,  # Increased budget for better optimization
        reflection_lm=reflection_lm,
        reflection_minibatch_size=3,  # Larger batches for pattern recognition
        candidate_selection_strategy="pareto",  # Multi-objective optimization
        use_merge=False,  # Disabled for Apple Silicon
        max_merge_invocations=0,
        failure_score=0.0,
        perfect_score=1.0,
        num_threads=1,  # Single thread for Apple Silicon
        log_dir="data/gepa_logs/enhanced/",
        track_stats=True,
        seed=42
    )
    
    logger.info("Running enhanced GEPA optimization...")
    logger.info("This will evolve prompts based on detailed feedback...")
    
    try:
        # Run optimization
        optimized_module = optimizer.compile(
            student=module,
            trainset=train_examples,
            valset=val_examples
        )
        
        logger.info("\n" + "="*80)
        logger.info("OPTIMIZATION COMPLETE!")
        logger.info("="*80)
        
        # Test on challenging scenario
        test_context = """
Market Analysis for DEX Token (EXTREME TEST):

CURRENT CONDITIONS:
- Volatility: EXTREME (1000% daily swings)
- Trend Direction: Manipulation-driven spikes
- Market Regime: Highly irregular with coordinated pump-and-dump
- Liquidity: Thin with large gaps

PERFORMANCE REQUIREMENTS:
- Target Sharpe Ratio: > 2.0
- Minimum Win Rate: > 60%
- Maximum Drawdown: < 15%
- Risk-Reward Ratio: > 3.0

CRITICAL: This is an extreme market requiring sophisticated risk management.
Generate a defensive strategy that can survive and profit in these conditions.
"""
        
        logger.info("\nTesting optimized module on extreme scenario...")
        result = optimized_module(market_context=test_context)
        
        logger.info("\nGenerated Strategy:")
        logger.info(f"Reasoning: {result.reasoning[:200]}...")
        logger.info(f"Strategy: {result.strategy[:300]}...")
        
        # Parse and evaluate the test strategy
        try:
            strategy_json = result.strategy
            if strategy_json.startswith('```json'):
                strategy_json = strategy_json[7:-3]
            test_strategy = json.loads(strategy_json)
            
            logger.info("\nBacktesting generated strategy...")
            test_results = backtest_func(test_strategy)
            
            logger.info("\nTest Strategy Performance:")
            logger.info(f"Sharpe Ratio: {test_results.get('sharpe_ratio', 0):.3f}")
            logger.info(f"Win Rate: {test_results.get('win_rate', 0):.1%}")
            logger.info(f"Max Drawdown: {test_results.get('max_drawdown', 0):.1%}")
            logger.info(f"Profit Factor: {test_results.get('profit_factor', 0):.2f}")
            
        except Exception as e:
            logger.error(f"Failed to evaluate test strategy: {e}")
        
        # Extract and save evolved prompts
        logger.info("\nExtracting optimized prompts...")
        prompts = {}
        for name, predictor in optimized_module.named_predictors():
            if hasattr(predictor, 'signature'):
                prompts[name] = str(predictor.signature)
                
                # Show prompt evolution
                logger.info(f"\n{name} prompt evolved to:")
                logger.info(f"{str(predictor.signature)[:500]}...")
        
        # Save prompts and stats
        output_dir = Path("data/gepa_logs/enhanced")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        with open(output_dir / "optimized_prompts.json", 'w') as f:
            json.dump(prompts, f, indent=2)
        
        logger.info(f"\nOptimized prompts saved to {output_dir}/optimized_prompts.json")
        
        # Save optimization stats if available
        if hasattr(optimizer, 'get_stats'):
            stats = optimizer.get_stats()
            with open(output_dir / "optimization_stats.json", 'w') as f:
                json.dump(stats, f, indent=2)
            logger.info(f"Optimization stats saved to {output_dir}/optimization_stats.json")
        
        return True
        
    except Exception as e:
        logger.error(f"GEPA optimization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)