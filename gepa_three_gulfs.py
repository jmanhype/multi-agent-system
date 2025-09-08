#!/usr/bin/env python
"""
GEPA Optimization with Three Gulfs Framework
Implements comprehensive evaluation following Hamel Husain & Shreya Shankar's framework

Key Improvements:
1. Gulf of Comprehension - Full logging and analysis of every evaluation
2. Gulf of Specification - Precise, explicit evaluation criteria  
3. Gulf of Generalization - Robust handling across volatility regimes
"""

import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import multiprocessing
import argparse

# Fix for Apple Silicon
multiprocessing.set_start_method('fork', force=True)

sys.path.insert(0, '/Users/speed/Downloads/multi-agent-system')

import dspy
from dspy import Example
from dspy.teleprompt import GEPA
from dspy.teleprompt.gepa.gepa_utils import ScoreWithFeedback

# Import Three Gulfs components
from lib.evaluation.gepa_comprehension_logger import GEPAComprehensionLogger
from lib.evaluation.gepa_specification_metric import GEPASpecificationMetric
from lib.evaluation.gepa_generalization_handler import GEPAGeneralizationHandler

# Import system components
from lib.data.dex_adapter import dex_adapter
from lib.research.backtest_wrapper import run_backtest

class ThreeGulfsTradingModule(dspy.Module):
    """
    Trading strategy generator with Three Gulfs improvements
    """
    
    def __init__(self):
        super().__init__()
        
        # Initialize Three Gulfs components
        self.generalization_handler = GEPAGeneralizationHandler()
        
        # Enhanced signature with precise specifications
        self.strategy_generator = dspy.ChainOfThought(
            """
            market_context -> strategy, reasoning
            
            You are an expert DEX trading strategist implementing the Three Gulfs Framework.
            
            CRITICAL REQUIREMENTS (Gulf of Specification):
            
            1. OUTPUT FORMAT - Must be EXACT JSON with these fields:
               {
                 "type": "momentum" | "mean_reversion" | "breakout" | "ml_based" | "volume_based",
                 "entry_conditions": {<dict with at least 2 conditions>},
                 "exit_conditions": {<dict with at least 2 conditions>},
                 "stop_loss_percentage": <number between 0.5 and 10.0>,
                 "take_profit_percentage": <number between 1.0 and 20.0>
               }
            
            2. VOLATILITY ADAPTATION (Gulf of Generalization):
               - Ultra Low (<1% daily): mean_reversion, SL: 0.5-1.5%, TP: 1-3%
               - Low (1-2% daily): mean_reversion/breakout, SL: 1-2%, TP: 2-5%
               - Medium (2-5% daily): momentum/breakout, SL: 2-5%, TP: 3-8%
               - High (5-10% daily): momentum, SL: 3-7%, TP: 5-12%
               - Extreme (10-20% daily): momentum/ml_based, SL: 5-10%, TP: 8-20%
               - Crisis (>20% daily): ml_based, SL: 8-10%, TP: 15-20%
            
            3. STRATEGY-SPECIFIC REQUIREMENTS:
               
               MOMENTUM:
               - entry_conditions MUST include: "rsi", "volume_surge", "zscore"
               - exit_conditions MUST include: "rsi", "zscore" or "trailing_stop"
               - RSI entry must be < RSI exit
               
               MEAN_REVERSION:
               - entry_conditions MUST include: "zscore" or "bollinger"
               - exit_conditions MUST include: "zscore" or "mean_target"
               - Z-score thresholds must be symmetric
               
               BREAKOUT:
               - entry_conditions MUST include: "channel_break", "volume"
               - exit_conditions MUST include: "channel_return" or "trailing_stop"
               
            4. RISK MANAGEMENT:
               - Risk/Reward ratio MUST be > 1.0 and < 10.0
               - Stop loss MUST scale with volatility
               - Position sizing implicit in stop loss
            
            5. REASONING:
               - Explain WHY this strategy fits the market conditions
               - Reference specific volatility level and trend
               - Justify parameter choices
            
            NEVER generate strategies outside these specifications.
            ALWAYS validate JSON structure before returning.
            """
        )
    
    def forward(self, market_context):
        # Use generalization handler to adapt to market
        market_data = self._parse_market_context(market_context)
        
        # Retrieve similar successful strategies (RAG)
        similar_strategies = self.generalization_handler.retrieve_similar_strategies(market_data)
        
        # Enhance context with examples
        enhanced_context = market_context
        if similar_strategies:
            enhanced_context += f"\n\nSimilar successful strategy: {json.dumps(similar_strategies[0]['strategy'])}"
        
        # Generate strategy
        result = self.strategy_generator(market_context=enhanced_context)
        
        return result
    
    def _parse_market_context(self, context: str) -> dict:
        """Extract market metrics from context"""
        data = {"volatility": 5.0, "trend": "unknown"}
        
        # Parse volatility
        if "volatility" in context.lower():
            import re
            vol_match = re.search(r'(\d+\.?\d*)\s*%?\s*(?:daily\s+)?volatility', context.lower())
            if vol_match:
                data["volatility"] = float(vol_match.group(1))
        
        # Parse trend
        if "trending" in context.lower():
            data["trend"] = "trending"
        elif "ranging" in context.lower():
            data["trend"] = "ranging"
        
        return data


def create_three_gulfs_metric(backtester_func):
    """
    Create comprehensive metric using Three Gulfs Framework
    """
    
    # Initialize components
    comprehension_logger = GEPAComprehensionLogger()
    specification_metric = GEPASpecificationMetric(backtester=backtester_func)
    generalization_handler = GEPAGeneralizationHandler()
    
    iteration_counter = [0]  # Mutable counter
    
    def metric(example, pred) -> ScoreWithFeedback:
        iteration_counter[0] += 1
        
        # Parse market context
        market_context = example.market_context if hasattr(example, 'market_context') else str(example)
        
        # Extract volatility
        volatility = 5.0  # Default
        if "volatility" in market_context.lower():
            import re
            vol_match = re.search(r'(\d+\.?\d*)\s*%?\s*(?:daily\s+)?volatility', market_context.lower())
            if vol_match:
                volatility = float(vol_match.group(1))
        
        market_data = {
            'volatility': volatility,
            'df': dex_adapter.get_candles('BTC/USDT', '5m', 1000)
        }
        
        # Evaluate with specification metric
        result = specification_metric.evaluate(market_data, pred)
        
        # Log for comprehension analysis
        try:
            strategy = json.loads(pred.strategy) if hasattr(pred, 'strategy') else {}
        except:
            strategy = {}
        
        error_type = None
        if result.score == 0.0:
            if "JSON" in result.feedback:
                error_type = "json_error"
            elif "Missing" in result.feedback:
                error_type = "validation_error"
            else:
                error_type = "unknown_error"
        elif result.score < 0.5:
            error_type = "performance_issue"
        
        comprehension_logger.log_evaluation(
            iteration=iteration_counter[0],
            market_context=market_context,
            prediction=pred,
            score=result.score,
            feedback=result.feedback,
            error_type=error_type
        )
        
        # Add generalization insights to feedback
        if result.score < 0.5 and volatility > 10:
            result = ScoreWithFeedback(
                score=result.score,
                feedback=result.feedback + " | HIGH VOL: Consider using fallback strategy for extreme conditions"
            )
        
        return result
    
    # Store logger reference for reporting
    metric.comprehension_logger = comprehension_logger
    
    return metric


def test_with_volatility_scenarios(iterations=10):
    """
    Test GEPA optimization across different volatility scenarios
    """
    
    print("\n" + "="*80)
    print("GEPA OPTIMIZATION WITH THREE GULFS FRAMEWORK")
    print("Testing across volatility scenarios including 10% daily")
    print("="*80)
    
    # Initialize DSPy
    lm = dspy.LM(
        model="openai/gpt-4o-mini",
        max_tokens=1000,
        temperature=0.7
    )
    dspy.settings.configure(lm=lm)
    
    # Create test scenarios with different volatility levels
    scenarios = [
        ("Low Volatility (0.7%)", 0.7),
        ("Medium Volatility (3%)", 3.0),
        ("High Volatility (7%)", 7.0),
        ("EXTREME Volatility (10%)", 10.0),  # Requested case
        ("CRISIS Volatility (15%)", 15.0),
    ]
    
    all_results = {}
    
    for scenario_name, volatility in scenarios:
        print(f"\n{'='*60}")
        print(f"Testing: {scenario_name}")
        print(f"{'='*60}")
        
        # Create examples for this volatility level
        examples = []
        for i in range(5):
            context = f"""
Market Analysis for DEX Token:

CURRENT CONDITIONS:
- Volatility: {volatility}% daily
- Trend Direction: {'trending' if i % 2 == 0 else 'ranging'}
- 24h Volume: ${100000 * (1 + volatility/10):.0f}

Generate a trading strategy optimized for these conditions.
"""
            examples.append(Example(market_context=context))
        
        # Create module and metric
        module = ThreeGulfsTradingModule()
        metric = create_three_gulfs_metric(run_backtest)
        
        # Run GEPA optimization with auto budget
        # Use auto budget for proper calculation based on dataset size
        optimizer = GEPA(
            auto='light',  # Will calculate ~404 metric calls for 6 examples
            metric=metric,
            verbose=True,
            init_temperature=0.7,
            track_heritage=True
        )
        
        print(f"\nOptimizing for {scenario_name}...")
        optimized_module = optimizer.compile(
            module,
            trainset=examples[:3],
            valset=examples[3:]
        )
        
        # Get final prompts
        final_prompts = {}
        for name, param in optimized_module.named_parameters():
            if hasattr(param, 'instructions'):
                final_prompts[name] = param.instructions
        
        # Generate comprehension report
        if hasattr(metric, 'comprehension_logger'):
            report = metric.comprehension_logger.generate_comprehension_report()
            
            all_results[scenario_name] = {
                "volatility": volatility,
                "failure_rate": report['overview']['failure_rate'],
                "average_score": report['overview']['average_score'],
                "gulf_analysis": report['gulf_analysis'],
                "top_failures": list(report.get('failure_patterns', {}).keys())[:3],
                "optimized_prompts": final_prompts
            }
            
            # Display summary
            print(f"\nRESULTS for {scenario_name}:")
            print(f"  Failure Rate: {report['overview']['failure_rate']:.1%}")
            print(f"  Average Score: {report['overview']['average_score']:.3f}")
            print(f"  Gulf Distribution:")
            for gulf, count in report['gulf_analysis'].items():
                if count > 0:
                    print(f"    {gulf}: {count}")
    
    # Final summary
    print("\n" + "="*80)
    print("FINAL SUMMARY - VOLATILITY HANDLING")
    print("="*80)
    
    for scenario, results in all_results.items():
        print(f"\n{scenario}:")
        print(f"  Success Rate: {(1 - results['failure_rate']):.1%}")
        print(f"  Average Score: {results['average_score']:.3f}")
        
        # Check 10% volatility specifically
        if results['volatility'] == 10.0:
            print(f"\n  ⚠️ 10% VOLATILITY ANALYSIS:")
            if results['failure_rate'] > 0.3:
                print(f"    ❌ High failure rate: {results['failure_rate']:.1%}")
                print(f"    Main issues: {', '.join(results['top_failures'])}")
            else:
                print(f"    ✅ Acceptable performance: {(1-results['failure_rate']):.1%} success rate")
    
    # Save results
    output_file = Path("data/gepa_logs/three_gulfs_results.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")
    
    return all_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test GEPA with Three Gulfs Framework')
    parser.add_argument('--iterations', type=int, default=10, help='Number of GEPA iterations')
    parser.add_argument('--test-volatility', action='store_true', help='Test across volatility scenarios')
    
    args = parser.parse_args()
    
    if args.test_volatility:
        results = test_with_volatility_scenarios(args.iterations)
    else:
        # Run standard test
        print("Running standard GEPA optimization with Three Gulfs improvements...")
        
        # Initialize DSPy
        lm = dspy.OpenAI(
            model="gpt-4o-mini",
            max_tokens=1000,
            temperature=0.7
        )
        dspy.settings.configure(lm=lm)
        
        # Create training examples
        examples = []
        volatilities = [0.7, 2.0, 5.0, 10.0, 15.0]  # Include 10% case
        
        for vol in volatilities:
            context = f"""
Market Analysis for DEX Token:

CURRENT CONDITIONS:
- Volatility: {vol}% daily
- Trend Direction: {'trending' if vol > 5 else 'ranging'}
- 24h Volume: ${100000 * (1 + vol/10):.0f}

Generate a trading strategy optimized for these conditions.
"""
            examples.append(Example(market_context=context))
        
        # Create module and metric
        module = ThreeGulfsTradingModule()
        metric = create_three_gulfs_metric(run_backtest)
        
        # Run optimization with auto budget
        budget_mode = os.getenv('GEPA_BUDGET', 'light')
        print(f"\nUsing budget mode: {budget_mode}")
        
        optimizer = GEPA(
            auto=budget_mode,  # Let DSPy calculate optimal budget
            metric=metric,
            verbose=True,
            init_temperature=0.7
        )
        
        optimized_module = optimizer.compile(
            module,
            trainset=examples[:3],
            valset=examples[3:]
        )
        
        # Generate final report
        metric.comprehension_logger.display_summary()
        
        print("\n✅ GEPA optimization with Three Gulfs Framework complete!")