#!/usr/bin/env python
"""
Risk Management System - Comprehensive capital protection and position sizing
Provides Kelly Criterion sizing, multi-layer validation, and circuit breakers
"""

from .manager import RiskManager, PositionManager

# Version
__version__ = "1.0.0"

# Quick initialization function
def initialize_risk_system(config_path: str = None) -> RiskManager:
    """
    Initialize risk management system
    Returns: risk_manager
    """
    import json
    import os
    
    # Default configuration
    default_config = {
        'max_position_size': 62.50,
        'max_daily_loss': 100,
        'max_drawdown': 0.05,  # 5%
        'max_consecutive_losses': 3,
        'bankroll_percentage': 0.02,  # 2% per trade
        'max_leverage': 3.0,
        'symbol_whitelist': ['BTC/USDT', 'ETH/USDT'],
        'volatility_adjustment': True,
        'max_correlation': 0.7,
        'max_concentration': 0.25,
        'cb_daily_loss': -100,
        'cb_drawdown': 0.10,
        'cb_latency_ms': 1000,
        'cb_error_rate': 0.05,
        'cb_consecutive_errors': 3
    }
    
    # Load configuration
    config = default_config.copy()
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
        except Exception as e:
            print(f"Warning: Could not load config from {config_path}: {e}")
    
    # Initialize components
    risk_manager = RiskManager(config)
    
    return risk_manager

# Export main classes
__all__ = [
    'RiskManager',
    'PositionManager',
    'initialize_risk_system'
]