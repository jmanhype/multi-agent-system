#!/usr/bin/env python
"""
Gulf of Specification Bridge for GEPA Evaluations
Based on Three Gulfs Framework by Hamel Husain & Shreya Shankar

Key Principle: "Any lack of clarity in the prompt = room for error"
Solution: Precise, explicit evaluation criteria with clear pass/fail conditions
"""

import json
import numpy as np
from typing import Dict, Any, Tuple, List
from dspy.teleprompt.gepa.gepa_utils import ScoreWithFeedback

class GEPASpecificationMetric:
    """
    Precise evaluation metric following Three Gulfs Specification principles
    
    Instead of vague "good strategy" criteria, we define EXACT requirements:
    1. STRUCTURE: Must be valid JSON with required fields
    2. PARAMETERS: Must have specific numeric ranges  
    3. LOGIC: Must have coherent entry/exit conditions
    4. ADAPTATION: Must match market volatility regime
    5. RISK: Must have appropriate risk controls
    """
    
    def __init__(self, backtester=None):
        self.backtester = backtester
        
        # EXPLICIT SPECIFICATIONS (not vague guidelines)
        self.specifications = {
            "required_fields": {
                "type": ["momentum", "mean_reversion", "breakout", "ml_based", "volume_based"],
                "entry_conditions": dict,  # Must be dict
                "exit_conditions": dict,   # Must be dict
                "stop_loss_percentage": (0.5, 10.0),  # Min, max range
                "take_profit_percentage": (1.0, 20.0)  # Min, max range
            },
            
            "volatility_adaptations": {
                "low": {  # < 2% daily vol
                    "preferred_types": ["mean_reversion", "breakout"],
                    "stop_loss_range": (1.0, 3.0),
                    "take_profit_range": (2.0, 5.0)
                },
                "medium": {  # 2-5% daily vol
                    "preferred_types": ["momentum", "breakout"],
                    "stop_loss_range": (2.0, 5.0),
                    "take_profit_range": (3.0, 8.0)
                },
                "high": {  # 5-10% daily vol
                    "preferred_types": ["momentum", "volume_based"],
                    "stop_loss_range": (3.0, 7.0),
                    "take_profit_range": (5.0, 12.0)
                },
                "extreme": {  # > 10% daily vol
                    "preferred_types": ["momentum", "ml_based"],
                    "stop_loss_range": (5.0, 10.0),
                    "take_profit_range": (8.0, 20.0)
                }
            },
            
            "coherence_rules": {
                "momentum": {
                    "required_entry": ["rsi", "volume_surge", "zscore"],
                    "required_exit": ["rsi", "zscore"]
                },
                "mean_reversion": {
                    "required_entry": ["zscore", "bollinger"],
                    "required_exit": ["zscore", "mean_target"]
                },
                "breakout": {
                    "required_entry": ["channel_break", "volume"],
                    "required_exit": ["channel_return", "trailing_stop"]
                }
            }
        }
    
    def evaluate(self, market_data: Dict, prediction: Any) -> ScoreWithFeedback:
        """
        Evaluate with PRECISE specifications, not vague criteria
        
        Following Three Gulfs principle:
        "Decompose the task thoroughly - assume nothing is obvious"
        """
        
        # Initialize scoring components
        scores = {
            "structure": 0.0,      # 20% - Valid JSON structure
            "parameters": 0.0,     # 20% - Parameter validation
            "coherence": 0.0,      # 20% - Logical coherence
            "adaptation": 0.0,     # 20% - Market adaptation
            "performance": 0.0     # 20% - Backtest performance
        }
        
        feedback_parts = []
        
        # 1. STRUCTURE CHECK (Explicit, not assumed)
        structure_result = self._check_structure(prediction)
        scores["structure"] = structure_result[0]
        feedback_parts.append(f"Structure: {structure_result[1]}")
        
        if scores["structure"] == 0:
            # Complete structural failure - return early
            return ScoreWithFeedback(
                score=0.0,
                feedback=f"SPECIFICATION FAILURE: {structure_result[1]}. "
                        "The output must be valid JSON with ALL required fields."
            )
        
        # Parse strategy
        try:
            strategy = json.loads(prediction.strategy)
        except (json.JSONDecodeError, TypeError, AttributeError) as e:
            strategy = prediction.strategy if isinstance(prediction.strategy, dict) else {}
        
        # 2. PARAMETER VALIDATION (Precise ranges, not "reasonable")
        param_result = self._check_parameters(strategy)
        scores["parameters"] = param_result[0]
        feedback_parts.append(f"Parameters: {param_result[1]}")
        
        # 3. COHERENCE CHECK (Logical consistency)
        coherence_result = self._check_coherence(strategy)
        scores["coherence"] = coherence_result[0]
        feedback_parts.append(f"Coherence: {coherence_result[1]}")
        
        # 4. MARKET ADAPTATION (Match volatility regime)
        volatility = market_data.get('volatility', 2.0)
        adaptation_result = self._check_adaptation(strategy, volatility)
        scores["adaptation"] = adaptation_result[0]
        feedback_parts.append(f"Adaptation: {adaptation_result[1]}")
        
        # 5. PERFORMANCE (If structure is valid)
        if scores["structure"] > 0.5 and self.backtester:
            perf_result = self._check_performance(strategy, market_data)
            scores["performance"] = perf_result[0]
            feedback_parts.append(f"Performance: {perf_result[1]}")
        else:
            scores["performance"] = 0.0
            feedback_parts.append("Performance: Not evaluated due to structural issues")
        
        # Calculate weighted score
        weights = {
            "structure": 0.2,
            "parameters": 0.2,
            "coherence": 0.2,
            "adaptation": 0.2,
            "performance": 0.2
        }
        
        final_score = sum(scores[k] * weights[k] for k in scores)
        
        # Generate actionable feedback
        feedback = " | ".join(feedback_parts)
        
        # Add specific improvement suggestions
        if final_score < 0.5:
            feedback += " | IMPROVE: " + self._suggest_improvements(scores, strategy, volatility)
        
        return ScoreWithFeedback(score=final_score, feedback=feedback)
    
    def _check_structure(self, prediction) -> Tuple[float, str]:
        """Check if output has valid structure with ALL required fields"""
        
        try:
            # Must be able to extract strategy
            if hasattr(prediction, 'strategy'):
                strategy_str = prediction.strategy
            else:
                return (0.0, "Missing strategy attribute")
            
            # Must be valid JSON
            strategy = json.loads(strategy_str) if isinstance(strategy_str, str) else strategy_str
            
            # Check ALL required fields explicitly
            missing = []
            for field in ["type", "entry_conditions", "exit_conditions", 
                         "stop_loss_percentage", "take_profit_percentage"]:
                if field not in strategy:
                    missing.append(field)
            
            if missing:
                return (0.0, f"Missing required fields: {', '.join(missing)}")
            
            # Validate field types
            if not isinstance(strategy["entry_conditions"], dict):
                return (0.3, "entry_conditions must be a dictionary")
            if not isinstance(strategy["exit_conditions"], dict):
                return (0.3, "exit_conditions must be a dictionary")
            
            return (1.0, "Valid structure")
            
        except json.JSONDecodeError as e:
            return (0.0, f"Invalid JSON: {str(e)[:50]}")
        except Exception as e:
            return (0.0, f"Structure error: {str(e)[:50]}")
    
    def _check_parameters(self, strategy: Dict) -> Tuple[float, str]:
        """Validate parameters are within specified ranges"""
        
        issues = []
        score = 1.0
        
        # Check stop loss
        sl = strategy.get("stop_loss_percentage", 0)
        if not (0.5 <= sl <= 10.0):
            issues.append(f"stop_loss {sl}% outside range [0.5-10%]")
            score -= 0.3
        
        # Check take profit
        tp = strategy.get("take_profit_percentage", 0)
        if not (1.0 <= tp <= 20.0):
            issues.append(f"take_profit {tp}% outside range [1-20%]")
            score -= 0.3
        
        # Check risk/reward ratio
        if sl > 0 and tp > 0:
            risk_reward = tp / sl
            if risk_reward < 1.0:
                issues.append(f"Poor risk/reward ratio: {risk_reward:.1f}")
                score -= 0.2
        
        # Strategy type validation
        strategy_type = strategy.get("type", "")
        valid_types = self.specifications["required_fields"]["type"]
        if strategy_type not in valid_types:
            issues.append(f"Invalid type '{strategy_type}'")
            score -= 0.2
        
        if issues:
            return (max(0, score), f"Issues: {'; '.join(issues)}")
        return (1.0, "Parameters valid")
    
    def _check_coherence(self, strategy: Dict) -> Tuple[float, str]:
        """Check logical coherence of entry/exit conditions"""
        
        strategy_type = strategy.get("type", "momentum")
        entry = strategy.get("entry_conditions", {})
        exit = strategy.get("exit_conditions", {})
        
        score = 1.0
        issues = []
        
        # Check for empty conditions
        if not entry:
            issues.append("Empty entry conditions")
            score -= 0.5
        if not exit:
            issues.append("Empty exit conditions")
            score -= 0.5
        
        # Type-specific coherence checks
        if strategy_type in self.specifications["coherence_rules"]:
            rules = self.specifications["coherence_rules"][strategy_type]
            
            # Check required entry conditions
            required_entry = rules.get("required_entry", [])
            missing_entry = [r for r in required_entry if not any(r in str(entry).lower() for r in required_entry)]
            if missing_entry:
                issues.append(f"Missing entry indicators for {strategy_type}")
                score -= 0.2
            
            # Check required exit conditions  
            required_exit = rules.get("required_exit", [])
            missing_exit = [r for r in required_exit if not any(r in str(exit).lower() for r in required_exit)]
            if missing_exit:
                issues.append(f"Missing exit indicators for {strategy_type}")
                score -= 0.2
        
        # Check for contradictions
        if "rsi" in str(entry) and "rsi" in str(exit):
            # Make sure RSI values make sense
            try:
                entry_rsi = entry.get("rsi", 0)
                exit_rsi = exit.get("rsi", 0)
                if strategy_type == "momentum" and entry_rsi > exit_rsi:
                    issues.append("Contradictory RSI levels")
                    score -= 0.2
            except (KeyError, TypeError, AttributeError):
                pass  # Skip coherence check if data structure is unexpected
        
        if issues:
            return (max(0, score), f"Coherence issues: {'; '.join(issues)}")
        return (1.0, "Logically coherent")
    
    def _check_adaptation(self, strategy: Dict, volatility: float) -> Tuple[float, str]:
        """Check if strategy adapts to market volatility"""
        
        # Determine volatility regime
        if volatility < 2:
            regime = "low"
        elif volatility < 5:
            regime = "medium"
        elif volatility < 10:
            regime = "high"
        else:
            regime = "extreme"
        
        spec = self.specifications["volatility_adaptations"][regime]
        
        score = 1.0
        feedback = []
        
        # Check strategy type fitness
        strategy_type = strategy.get("type", "")
        if strategy_type in spec["preferred_types"]:
            feedback.append(f"Good type for {regime} vol")
        else:
            score -= 0.3
            feedback.append(f"Type '{strategy_type}' suboptimal for {regime} vol")
        
        # Check stop loss adaptation
        sl = strategy.get("stop_loss_percentage", 0)
        sl_range = spec["stop_loss_range"]
        if not (sl_range[0] <= sl <= sl_range[1]):
            score -= 0.3
            feedback.append(f"SL {sl}% not adapted for {regime} vol")
        
        # Check take profit adaptation
        tp = strategy.get("take_profit_percentage", 0)
        tp_range = spec["take_profit_range"]
        if not (tp_range[0] <= tp <= tp_range[1]):
            score -= 0.3
            feedback.append(f"TP {tp}% not adapted for {regime} vol")
        
        return (max(0, score), f"{regime} vol ({volatility:.1f}%): {'; '.join(feedback)}")
    
    def _check_performance(self, strategy: Dict, market_data: Dict) -> Tuple[float, str]:
        """Evaluate backtest performance"""
        
        try:
            results = self.backtester(strategy, market_data.get('df'))
            
            sharpe = results.get('sharpe_ratio', 0)
            win_rate = results.get('win_rate', 0)
            max_dd = results.get('max_drawdown', 0)
            
            # Score based on performance thresholds
            score = 0.0
            
            if sharpe > 1.5:
                score += 0.4
            elif sharpe > 1.0:
                score += 0.2
            elif sharpe > 0.5:
                score += 0.1
            
            if win_rate > 0.55:
                score += 0.3
            elif win_rate > 0.50:
                score += 0.2
            elif win_rate > 0.45:
                score += 0.1
            
            if max_dd > -0.15:
                score += 0.3
            elif max_dd > -0.25:
                score += 0.2
            elif max_dd > -0.35:
                score += 0.1
            
            feedback = f"Sharpe:{sharpe:.2f}, WR:{win_rate:.1%}, DD:{max_dd:.1%}"
            return (min(1.0, score), feedback)
            
        except Exception as e:
            return (0.0, f"Backtest failed: {str(e)[:30]}")
    
    def _suggest_improvements(self, scores: Dict, strategy: Dict, volatility: float) -> str:
        """Generate specific improvement suggestions"""
        
        suggestions = []
        
        # Find weakest component
        weakest = min(scores, key=scores.get)
        
        if weakest == "structure":
            suggestions.append("Ensure ALL required fields present with correct types")
        elif weakest == "parameters":
            sl = strategy.get("stop_loss_percentage", 0)
            tp = strategy.get("take_profit_percentage", 0)
            suggestions.append(f"Adjust SL to 2-5% and TP to 5-10% for {volatility:.1f}% volatility")
        elif weakest == "coherence":
            suggestions.append(f"Add required indicators for {strategy.get('type', 'unknown')} strategy")
        elif weakest == "adaptation":
            if volatility > 10:
                suggestions.append("Use momentum strategy with wider stops for extreme volatility")
            elif volatility < 2:
                suggestions.append("Use mean reversion with tighter stops for low volatility")
        elif weakest == "performance":
            suggestions.append("Review entry/exit logic or consider different strategy type")
        
        return suggestions[0] if suggestions else "Review overall strategy design"


# Example usage
if __name__ == "__main__":
    
    # Create metric
    def mock_backtest(strategy, df):
        """Mock backtest for testing"""
        return {
            'sharpe_ratio': np.random.uniform(0.5, 2.5),
            'win_rate': np.random.uniform(0.4, 0.6),
            'max_drawdown': -np.random.uniform(0.1, 0.3)
        }
    
    metric = GEPASpecificationMetric(backtester=mock_backtest)
    
    # Test with good strategy
    class GoodPred:
        strategy = json.dumps({
            "type": "momentum",
            "entry_conditions": {"rsi": 30, "volume_surge": 2.0, "zscore": 2.0},
            "exit_conditions": {"rsi": 70, "zscore": -0.5},
            "stop_loss_percentage": 3.0,
            "take_profit_percentage": 8.0
        })
        reasoning = "Momentum strategy for medium volatility"
    
    # Test with bad strategy
    class BadPred:
        strategy = json.dumps({
            "type": "invalid_type",
            "entry_conditions": {},  # Empty
            "stop_loss_percentage": 50.0  # Way too high
            # Missing required fields
        })
        reasoning = "Poor strategy"
    
    # Evaluate
    market_data = {'volatility': 5.0}  # 5% daily vol
    
    print("GOOD STRATEGY:")
    result = metric.evaluate(market_data, GoodPred())
    print(f"Score: {result.score:.3f}")
    print(f"Feedback: {result.feedback}\n")
    
    print("BAD STRATEGY:")
    result = metric.evaluate(market_data, BadPred())
    print(f"Score: {result.score:.3f}")
    print(f"Feedback: {result.feedback}")