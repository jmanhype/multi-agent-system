#!/usr/bin/env python
"""
Gulf of Generalization Bridge for GEPA Evaluations
Based on Three Gulfs Framework by Hamel Husain & Shreya Shankar

Key Principle: "Even with a crystal-clear prompt, the model can fail to apply it across diverse inputs"
Solution: Architectural changes like retrieval, multi-step decomposition, and fallback logic
"""

import json
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
import logging
from pathlib import Path

class GEPAGeneralizationHandler:
    """
    Handles model generalization across diverse market conditions
    
    Core Solutions:
    1. Task Decomposition - Break complex strategy generation into steps
    2. Retrieval Augmentation - Provide relevant examples for edge cases  
    3. Ensemble/Fallback - Multiple attempts with different approaches
    4. Adaptive Prompting - Adjust prompt based on market regime
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Load historical successful strategies for different regimes
        self.strategy_library = self._build_strategy_library()
        
        # Define volatility regime boundaries
        self.volatility_regimes = {
            "ultra_low": (0, 1),      # < 1% daily
            "low": (1, 2),            # 1-2% daily
            "medium": (2, 5),         # 2-5% daily  
            "high": (5, 10),          # 5-10% daily
            "extreme": (10, 20),      # 10-20% daily
            "crisis": (20, float('inf'))  # > 20% daily
        }
        
        # Fallback strategies for edge cases
        self.fallback_strategies = {
            "extreme": {
                "type": "momentum",
                "entry_conditions": {
                    "rsi": 20,
                    "volume_surge": 3.0,
                    "zscore": 3.0
                },
                "exit_conditions": {
                    "rsi": 80,
                    "trailing_stop": 0.1
                },
                "stop_loss_percentage": 8.0,
                "take_profit_percentage": 15.0
            },
            "crisis": {
                "type": "ml_based",
                "entry_conditions": {
                    "pattern": "extreme_oversold",
                    "volume_spike": 5.0
                },
                "exit_conditions": {
                    "pattern": "exhaustion",
                    "time_limit": 4  # hours
                },
                "stop_loss_percentage": 10.0,
                "take_profit_percentage": 20.0
            }
        }
    
    def _build_strategy_library(self) -> Dict:
        """Build library of successful strategies for retrieval"""
        
        return {
            "low_volatility_winners": [
                {
                    "context": "0.5% daily volatility, ranging market",
                    "strategy": {
                        "type": "mean_reversion",
                        "entry_conditions": {"zscore": 2.0, "bollinger_touch": True},
                        "exit_conditions": {"zscore": 0.5, "mean_target": True},
                        "stop_loss_percentage": 1.5,
                        "take_profit_percentage": 3.0
                    },
                    "performance": {"sharpe": 2.1, "win_rate": 0.62}
                }
            ],
            "high_volatility_winners": [
                {
                    "context": "8% daily volatility, trending market",
                    "strategy": {
                        "type": "momentum",
                        "entry_conditions": {"rsi": 25, "volume_surge": 2.5, "zscore": 2.5},
                        "exit_conditions": {"rsi": 75, "zscore": -1.0},
                        "stop_loss_percentage": 5.0,
                        "take_profit_percentage": 12.0
                    },
                    "performance": {"sharpe": 1.8, "win_rate": 0.54}
                }
            ],
            "extreme_volatility_winners": [
                {
                    "context": "15% daily volatility, crisis conditions",
                    "strategy": {
                        "type": "momentum",
                        "entry_conditions": {"rsi": 15, "volume_surge": 4.0, "zscore": 3.5},
                        "exit_conditions": {"time_stop": 2, "trailing_stop": 0.15},
                        "stop_loss_percentage": 10.0,
                        "take_profit_percentage": 20.0
                    },
                    "performance": {"sharpe": 1.2, "win_rate": 0.48}
                }
            ]
        }
    
    def decompose_strategy_generation(self, market_context: Dict) -> Dict:
        """
        Task Decomposition: Break strategy generation into manageable steps
        Following Three Gulfs principle of handling complex tasks
        """
        
        steps = {
            "step1_analyze_regime": self._analyze_market_regime(market_context),
            "step2_select_approach": None,
            "step3_tune_parameters": None,
            "step4_validate_coherence": None,
            "step5_final_strategy": None
        }
        
        # Step 2: Select strategy approach based on regime
        regime_info = steps["step1_analyze_regime"]
        steps["step2_select_approach"] = self._select_strategy_approach(regime_info)
        
        # Step 3: Tune parameters for conditions
        steps["step3_tune_parameters"] = self._tune_parameters(
            steps["step2_select_approach"],
            regime_info
        )
        
        # Step 4: Validate coherence
        steps["step4_validate_coherence"] = self._validate_strategy_coherence(
            steps["step3_tune_parameters"]
        )
        
        # Step 5: Finalize strategy
        if steps["step4_validate_coherence"]["is_valid"]:
            steps["step5_final_strategy"] = steps["step3_tune_parameters"]
        else:
            # Use fallback if validation fails
            steps["step5_final_strategy"] = self._get_fallback_strategy(regime_info)
        
        return steps
    
    def _analyze_market_regime(self, market_context: Dict) -> Dict:
        """Analyze current market regime"""
        
        volatility = market_context.get('volatility', 5.0)
        
        # Determine regime
        regime = "medium"
        for name, (low, high) in self.volatility_regimes.items():
            if low <= volatility < high:
                regime = name
                break
        
        # Analyze additional factors
        trend = market_context.get('trend', 'unknown')
        volume_profile = market_context.get('volume_profile', 'normal')
        
        return {
            "volatility": volatility,
            "regime": regime,
            "trend": trend,
            "volume_profile": volume_profile,
            "requires_special_handling": regime in ["extreme", "crisis"],
            "confidence": 0.8 if regime in ["low", "medium", "high"] else 0.5
        }
    
    def _select_strategy_approach(self, regime_info: Dict) -> Dict:
        """Select appropriate strategy type for regime"""
        
        regime = regime_info["regime"]
        trend = regime_info["trend"]
        
        # Strategy selection matrix
        selection_matrix = {
            ("ultra_low", "ranging"): "mean_reversion",
            ("ultra_low", "trending"): "breakout",
            ("low", "ranging"): "mean_reversion",
            ("low", "trending"): "breakout",
            ("medium", "ranging"): "mean_reversion",
            ("medium", "trending"): "momentum",
            ("high", "ranging"): "volume_based",
            ("high", "trending"): "momentum",
            ("extreme", "any"): "momentum",
            ("crisis", "any"): "ml_based"
        }
        
        # Get strategy type
        key = (regime, trend if trend != "unknown" else "any")
        if key not in selection_matrix:
            key = (regime, "any")
        
        strategy_type = selection_matrix.get(key, "momentum")
        
        return {
            "type": strategy_type,
            "reasoning": f"Selected {strategy_type} for {regime} volatility and {trend} trend",
            "confidence": regime_info["confidence"]
        }
    
    def _tune_parameters(self, approach: Dict, regime_info: Dict) -> Dict:
        """Tune strategy parameters for specific conditions"""
        
        volatility = regime_info["volatility"]
        regime = regime_info["regime"]
        strategy_type = approach["type"]
        
        # Base parameters
        strategy = {
            "type": strategy_type,
            "entry_conditions": {},
            "exit_conditions": {},
            "stop_loss_percentage": 2.0,
            "take_profit_percentage": 5.0
        }
        
        # Volatility-adaptive parameter scaling
        vol_multiplier = max(1.0, volatility / 2.0)  # Scale with volatility
        
        # Set stop loss and take profit based on volatility
        strategy["stop_loss_percentage"] = min(10.0, 1.0 * vol_multiplier)
        strategy["take_profit_percentage"] = min(20.0, 2.5 * vol_multiplier)
        
        # Type-specific parameters
        if strategy_type == "momentum":
            strategy["entry_conditions"] = {
                "rsi": max(20, 30 - volatility),  # More extreme RSI in high vol
                "volume_surge": 1.5 + (volatility / 10),  # Higher volume requirement
                "zscore": min(3.5, 2.0 + (volatility / 10))  # Wider bands in high vol
            }
            strategy["exit_conditions"] = {
                "rsi": min(80, 70 + volatility),
                "zscore": max(-2.0, -0.5 - (volatility / 10))
            }
            
        elif strategy_type == "mean_reversion":
            strategy["entry_conditions"] = {
                "zscore": min(3.0, 2.0 + (volatility / 20)),
                "bollinger_bands": 2.0,
                "volume_check": True
            }
            strategy["exit_conditions"] = {
                "zscore": 0.5,
                "mean_target": True,
                "time_limit": max(4, 24 / vol_multiplier)  # Shorter holding in high vol
            }
            
        elif strategy_type == "breakout":
            strategy["entry_conditions"] = {
                "channel_break": 1.0 + (volatility / 100),
                "volume_confirmation": 2.0,
                "atr_filter": True
            }
            strategy["exit_conditions"] = {
                "channel_return": True,
                "trailing_stop": 0.05 * vol_multiplier,
                "time_stop": 8
            }
            
        elif strategy_type == "volume_based":
            strategy["entry_conditions"] = {
                "volume_zscore": 2.0,
                "price_confirmation": 0.01 * vol_multiplier,
                "correlation_threshold": 0.3
            }
            strategy["exit_conditions"] = {
                "volume_exhaustion": -1.0,
                "price_reversal": -0.03 * vol_multiplier
            }
            
        elif strategy_type == "ml_based":
            strategy["entry_conditions"] = {
                "pattern": "bullish_divergence",
                "confidence_threshold": 0.7,
                "volume_spike": 3.0
            }
            strategy["exit_conditions"] = {
                "pattern": "bearish_divergence",
                "time_limit": 4,
                "trailing_stop": 0.1 * vol_multiplier
            }
        
        return strategy
    
    def _validate_strategy_coherence(self, strategy: Dict) -> Dict:
        """Validate strategy makes logical sense"""
        
        issues = []
        is_valid = True
        
        # Check risk/reward ratio
        sl = strategy.get("stop_loss_percentage", 0)
        tp = strategy.get("take_profit_percentage", 0)
        
        if sl > 0 and tp > 0:
            risk_reward = tp / sl
            if risk_reward < 1.0:
                issues.append(f"Poor risk/reward ratio: {risk_reward:.2f}")
                is_valid = False
            elif risk_reward > 10.0:
                issues.append(f"Unrealistic risk/reward ratio: {risk_reward:.2f}")
                is_valid = False
        
        # Check entry/exit logic
        entry = strategy.get("entry_conditions", {})
        exit = strategy.get("exit_conditions", {})
        
        if not entry:
            issues.append("No entry conditions")
            is_valid = False
        if not exit:
            issues.append("No exit conditions")
            is_valid = False
        
        # Type-specific validation
        if strategy.get("type") == "momentum":
            if "rsi" in entry and "rsi" in exit:
                entry_rsi = entry.get("rsi", 50)
                exit_rsi = exit.get("rsi", 50)
                if entry_rsi >= exit_rsi:
                    issues.append("Contradictory RSI levels for momentum")
                    is_valid = False
        
        return {
            "is_valid": is_valid,
            "issues": issues,
            "confidence": 0.9 if is_valid else 0.3
        }
    
    def _get_fallback_strategy(self, regime_info: Dict) -> Dict:
        """Get fallback strategy for edge cases"""
        
        regime = regime_info["regime"]
        
        # Use predefined fallback for extreme regimes
        if regime in ["extreme", "crisis"]:
            return self.fallback_strategies.get(regime, self.fallback_strategies["extreme"])
        
        # Generic safe fallback
        return {
            "type": "momentum",
            "entry_conditions": {
                "rsi": 30,
                "volume_surge": 2.0,
                "zscore": 2.0
            },
            "exit_conditions": {
                "rsi": 70,
                "zscore": -0.5,
                "trailing_stop": 0.05
            },
            "stop_loss_percentage": 3.0,
            "take_profit_percentage": 6.0
        }
    
    def retrieve_similar_strategies(self, market_context: Dict, k: int = 3) -> List[Dict]:
        """
        Retrieval Augmentation: Find similar successful strategies
        Following Three Gulfs RAG principle
        """
        
        volatility = market_context.get('volatility', 5.0)
        
        # Determine which library to search
        if volatility < 2:
            library = self.strategy_library.get("low_volatility_winners", [])
        elif volatility < 10:
            library = self.strategy_library.get("high_volatility_winners", [])
        else:
            library = self.strategy_library.get("extreme_volatility_winners", [])
        
        # Return top k strategies
        return library[:k]
    
    def ensemble_generation(self, market_context: Dict, n_attempts: int = 3) -> Dict:
        """
        Ensemble/Fallback: Multiple generation attempts
        Following Three Gulfs ensemble principle
        """
        
        strategies = []
        
        for i in range(n_attempts):
            # Try different approaches
            if i == 0:
                # Decomposition approach
                result = self.decompose_strategy_generation(market_context)
                strategies.append(result["step5_final_strategy"])
            elif i == 1:
                # Retrieval-based approach
                similar = self.retrieve_similar_strategies(market_context, k=1)
                if similar:
                    strategies.append(similar[0]["strategy"])
            else:
                # Fallback approach
                regime_info = self._analyze_market_regime(market_context)
                strategies.append(self._get_fallback_strategy(regime_info))
        
        # Select best or merge strategies
        # For now, return the first valid one
        for strategy in strategies:
            validation = self._validate_strategy_coherence(strategy)
            if validation["is_valid"]:
                return strategy
        
        # If all fail, return safest fallback
        return strategies[-1]
    
    def adapt_to_edge_cases(self, market_context: Dict, previous_failures: List[str]) -> Dict:
        """
        Adapt strategy generation based on previous failures
        Learning from errors to improve generalization
        """
        
        # Analyze failure patterns
        failure_patterns = {
            "json_errors": any("json" in f.lower() for f in previous_failures),
            "performance_issues": any("sharpe" in f.lower() or "drawdown" in f.lower() for f in previous_failures),
            "validation_errors": any("missing" in f.lower() or "invalid" in f.lower() for f in previous_failures)
        }
        
        # Use different approach based on failures
        if failure_patterns["json_errors"]:
            # Use structured template
            return self._get_fallback_strategy(self._analyze_market_regime(market_context))
        elif failure_patterns["performance_issues"]:
            # Use more conservative parameters
            strategy = self.decompose_strategy_generation(market_context)["step5_final_strategy"]
            strategy["stop_loss_percentage"] *= 0.7  # Tighter stop
            strategy["take_profit_percentage"] *= 1.2  # Higher target
            return strategy
        else:
            # Standard generation with ensemble
            return self.ensemble_generation(market_context)


# Test the handler
if __name__ == "__main__":
    handler = GEPAGeneralizationHandler()
    
    # Test different volatility scenarios
    test_scenarios = [
        {"volatility": 0.7, "trend": "ranging"},     # Low vol
        {"volatility": 5.0, "trend": "trending"},     # Medium vol
        {"volatility": 10.0, "trend": "trending"},    # High vol (requested case)
        {"volatility": 15.0, "trend": "unknown"},     # Extreme vol
        {"volatility": 25.0, "trend": "crashing"}     # Crisis vol
    ]
    
    for scenario in test_scenarios:
        print(f"\n{'='*60}")
        print(f"Testing {scenario['volatility']}% volatility, {scenario['trend']} market")
        print(f"{'='*60}")
        
        # Decomposition approach
        result = handler.decompose_strategy_generation(scenario)
        strategy = result["step5_final_strategy"]
        
        print(f"Regime: {result['step1_analyze_regime']['regime']}")
        print(f"Strategy Type: {strategy['type']}")
        print(f"Stop Loss: {strategy['stop_loss_percentage']:.1f}%")
        print(f"Take Profit: {strategy['take_profit_percentage']:.1f}%")
        print(f"Entry Conditions: {strategy['entry_conditions']}")
        print(f"Exit Conditions: {strategy['exit_conditions']}")
        
        # Validate
        validation = handler._validate_strategy_coherence(strategy)
        print(f"Valid: {validation['is_valid']}")
        if validation['issues']:
            print(f"Issues: {validation['issues']}")