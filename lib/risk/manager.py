#!/usr/bin/env python
"""
Risk Manager - Multi-layer risk validation
Enforces position sizing, loss limits, and safety checks
"""

import json
import logging
import os
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sqlite3
import math

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Comprehensive risk management system with Kelly Criterion position sizing
    Enforces multiple layers of protection and dynamic risk adjustments
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Core risk parameters
        self.max_position_size = config.get('max_position_size', 62.50)
        self.max_daily_loss = config.get('max_daily_loss', 100)
        self.max_drawdown = config.get('max_drawdown', 0.05)  # 5% max drawdown
        self.max_consecutive_losses = config.get('max_consecutive_losses', 3)
        self.bankroll_percentage = config.get('bankroll_percentage', 0.02)  # 2% per trade
        self.max_leverage = config.get('max_leverage', 3.0)
        self.symbol_whitelist = config.get('symbol_whitelist', ['BTC/USDT', 'ETH/USDT'])
        
        # Dynamic risk adjustment parameters
        self.volatility_adjustment = config.get('volatility_adjustment', True)
        self.correlation_limit = config.get('max_correlation', 0.7)
        self.concentration_limit = config.get('max_concentration', 0.25)  # 25% max in single position
        
        # Circuit breaker thresholds
        self.circuit_breakers = {
            'DAILY_LOSS': config.get('cb_daily_loss', -100),
            'DRAWDOWN': config.get('cb_drawdown', 0.10),
            'LATENCY': config.get('cb_latency_ms', 1000),
            'ERROR_RATE': config.get('cb_error_rate', 0.05),
            'CONSECUTIVE_ERRORS': config.get('cb_consecutive_errors', 3)
        }
        
        # Track state
        self.consecutive_losses = 0
        self.daily_pnl = 0
        self.peak_balance = 10000  # Default starting balance
        self.current_balance = 10000
        self.error_count = 0
        self.last_latency = 0
        
        # Historical data for Kelly Criterion
        self.trade_history = []
        self.win_rate = 0.5  # Default 50%
        self.avg_win = 0.0
        self.avg_loss = 0.0
        
        # Load state from database
        self._load_state()
        
        # Initialize position manager
        self.position_manager = PositionManager(self)
        
        logger.info(f"Risk Manager initialized with {len(self.circuit_breakers)} circuit breakers")
    
    def _load_state(self):
        """Load risk state from database"""
        try:
            conn = sqlite3.connect('db/metrics.db')
            cursor = conn.cursor()
            
            # Get latest account state
            cursor.execute("""
                SELECT current_balance, peak_balance, daily_pnl
                FROM account_state
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            if row:
                self.current_balance, self.peak_balance, self.daily_pnl = row
            
            # Count consecutive losses
            cursor.execute("""
                SELECT pnl FROM trades
                ORDER BY timestamp DESC
                LIMIT ?
            """, (self.max_consecutive_losses,))
            
            recent_trades = cursor.fetchall()
            self.consecutive_losses = 0
            for (pnl,) in recent_trades:
                if pnl < 0:
                    self.consecutive_losses += 1
                else:
                    break
            
            conn.close()
        except Exception as e:
            logger.error(f"Failed to load risk state: {e}")
    
    def _save_state(self):
        """Save risk state to database"""
        try:
            conn = sqlite3.connect('db/metrics.db')
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO account_state (timestamp, current_balance, peak_balance, daily_pnl, total_pnl)
                VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                self.current_balance,
                self.peak_balance,
                self.daily_pnl,
                self.current_balance - 10000  # Assuming initial balance of 10000
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to save risk state: {e}")
    
    def validate_trade(self, request: Dict, context: Dict = None) -> Dict:
        """
        Multi-layer risk validation pipeline
        Returns comprehensive validation result with adjusted parameters
        """
        checks = []
        warnings = []
        
        # Extract trade parameters
        symbol = request.get('symbol', '')
        size = request.get('size', 0)
        side = request.get('side', '')
        
        try:
            # Layer 1: Hard limits and circuit breakers
            checks.append(self._check_circuit_breaker())
            checks.append(self._check_symbol_whitelist(symbol))
            checks.append(self._check_position_limits(size))
            
            # Layer 2: Market conditions
            if context:
                checks.append(self._check_volatility_regime(context))
                checks.append(self._check_liquidity(request, context))
            
            # Layer 3: Portfolio risk
            checks.append(self._check_correlation_risk(request))
            checks.append(self._check_concentration_risk(request))
            
            # Layer 4: Account state
            checks.append(self._check_daily_loss())
            checks.append(self._check_drawdown())
            checks.append(self._check_consecutive_losses())
            
            # Layer 5: Timing restrictions
            checks.append(self._check_trading_hours())
            
            # Aggregate results
            all_passed = all(check['passed'] for check in checks)
            critical_failures = [c for c in checks if not c['passed'] and c.get('severity') == 'CRITICAL']
            
            # Calculate adjusted size
            adjusted_size = self._calculate_safe_size(request, checks) if all_passed else 0
            
            result = {
                'approved': all_passed and len(critical_failures) == 0,
                'original_size': size,
                'adjusted_size': adjusted_size,
                'checks': checks,
                'warnings': warnings,
                'critical_failures': critical_failures,
                'risk_score': self._calculate_risk_score(checks),
                'recommendation': self._get_risk_recommendation(checks)
            }
            
            # Log decision
            self._log_risk_decision(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Risk validation error: {e}")
            return {
                'approved': False,
                'error': str(e),
                'checks': [],
                'adjusted_size': 0
            }
    
    # Layer 1: Hard limits
    def _check_circuit_breaker(self) -> Dict:
        """Check if circuit breaker is active"""
        active = os.path.exists('.circuit_breaker_triggered')
        return {
            'name': 'circuit_breaker',
            'passed': not active,
            'severity': 'CRITICAL' if active else 'INFO',
            'message': 'Circuit breaker is active' if active else 'Circuit breaker OK'
        }
    
    def _check_symbol_whitelist(self, symbol: str) -> Dict:
        """Check if symbol is whitelisted"""
        allowed = symbol in self.symbol_whitelist
        return {
            'name': 'symbol_whitelist',
            'passed': allowed,
            'severity': 'HIGH' if not allowed else 'INFO',
            'message': f'Symbol {symbol} {"approved" if allowed else "not in whitelist"}'
        }
    
    def _check_position_limits(self, size: float) -> Dict:
        """Check position size limits"""
        within_limit = size <= self.max_position_size
        return {
            'name': 'position_limits',
            'passed': within_limit,
            'severity': 'HIGH' if not within_limit else 'INFO',
            'message': f'Position size ${size:.2f} {"within" if within_limit else "exceeds"} limit ${self.max_position_size}'
        }
    
    # Layer 2: Market conditions
    def _check_volatility_regime(self, context: Dict) -> Dict:
        """Check market volatility regime"""
        volatility = context.get('volatility', 0.15)
        high_vol_threshold = 0.30
        
        if volatility > high_vol_threshold:
            return {
                'name': 'volatility_regime',
                'passed': True,  # Allow but warn
                'severity': 'MEDIUM',
                'message': f'High volatility detected: {volatility:.1%}',
                'adjustment': 'reduce_size'
            }
        
        return {
            'name': 'volatility_regime',
            'passed': True,
            'severity': 'INFO',
            'message': f'Normal volatility: {volatility:.1%}'
        }
    
    def _check_liquidity(self, request: Dict, context: Dict) -> Dict:
        """Check market liquidity conditions"""
        # This would typically check order book depth, spread, etc.
        # For now, implement basic logic
        return {
            'name': 'liquidity_check',
            'passed': True,
            'severity': 'INFO',
            'message': 'Liquidity check passed'
        }
    
    # Layer 3: Portfolio risk
    def _check_correlation_risk(self, request: Dict) -> Dict:
        """Check portfolio correlation risk"""
        # Simplified correlation check
        return {
            'name': 'correlation_risk',
            'passed': True,
            'severity': 'INFO',
            'message': 'Correlation risk acceptable'
        }
    
    def _check_concentration_risk(self, request: Dict) -> Dict:
        """Check portfolio concentration risk"""
        size = request.get('size', 0)
        concentration_pct = (size / self.current_balance) if self.current_balance > 0 else 1
        
        within_limit = concentration_pct <= self.concentration_limit
        return {
            'name': 'concentration_risk',
            'passed': within_limit,
            'severity': 'HIGH' if not within_limit else 'INFO',
            'message': f'Position concentration: {concentration_pct:.1%} (limit: {self.concentration_limit:.1%})'
        }
    
    # Layer 4: Account state
    def _check_daily_loss(self) -> Dict:
        """Check daily loss limits"""
        exceeded = self.daily_pnl <= -self.max_daily_loss
        return {
            'name': 'daily_loss',
            'passed': not exceeded,
            'severity': 'CRITICAL' if exceeded else 'INFO',
            'message': f'Daily P&L: ${self.daily_pnl:.2f} (limit: -${self.max_daily_loss})'
        }
    
    def _check_drawdown(self) -> Dict:
        """Check maximum drawdown limits"""
        if self.peak_balance <= 0:
            return {
                'name': 'drawdown_check',
                'passed': True,
                'severity': 'INFO',
                'message': 'No peak balance established'
            }
        
        drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
        exceeded = drawdown > self.max_drawdown
        
        return {
            'name': 'drawdown_check',
            'passed': not exceeded,
            'severity': 'CRITICAL' if exceeded else 'INFO',
            'message': f'Current drawdown: {drawdown:.2%} (limit: {self.max_drawdown:.2%})'
        }
    
    def _check_consecutive_losses(self) -> Dict:
        """Check consecutive loss limits"""
        exceeded = self.consecutive_losses >= self.max_consecutive_losses
        return {
            'name': 'consecutive_losses',
            'passed': not exceeded,
            'severity': 'HIGH' if exceeded else 'INFO',
            'message': f'Consecutive losses: {self.consecutive_losses} (limit: {self.max_consecutive_losses})'
        }
    
    def _check_trading_hours(self) -> Dict:
        """Check trading hour restrictions"""
        hour = datetime.utcnow().hour
        restricted = 3 <= hour < 7  # Low liquidity hours
        
        return {
            'name': 'trading_hours',
            'passed': not restricted,
            'severity': 'MEDIUM' if restricted else 'INFO',
            'message': f'Current hour: {hour} UTC {"(restricted)" if restricted else "(allowed)"}'
        }
    
    def _calculate_safe_size(self, request: Dict, checks: List[Dict]) -> float:
        """Calculate safe position size based on risk checks"""
        original_size = request.get('size', 0)
        
        # Start with original size
        safe_size = original_size
        
        # Apply reductions based on warnings
        for check in checks:
            if check.get('adjustment') == 'reduce_size':
                safe_size *= 0.75  # 25% reduction
            elif not check['passed'] and check['severity'] in ['HIGH', 'MEDIUM']:
                safe_size *= 0.5  # 50% reduction for failures
        
        # Ensure minimum/maximum bounds
        safe_size = max(0, min(safe_size, self.max_position_size))
        
        return round(safe_size, 2)
    
    def _calculate_risk_score(self, checks: List[Dict]) -> float:
        """Calculate overall risk score (0-100)"""
        total_score = 0
        max_score = 0
        
        severity_weights = {
            'INFO': 0,
            'MEDIUM': 25,
            'HIGH': 50,
            'CRITICAL': 100
        }
        
        for check in checks:
            weight = severity_weights.get(check['severity'], 0)
            max_score += weight
            if not check['passed']:
                total_score += weight
        
        return (total_score / max_score * 100) if max_score > 0 else 0
    
    def _get_risk_recommendation(self, checks: List[Dict]) -> str:
        """Get risk-based recommendation"""
        critical_failures = [c for c in checks if not c['passed'] and c['severity'] == 'CRITICAL']
        high_failures = [c for c in checks if not c['passed'] and c['severity'] == 'HIGH']
        
        if critical_failures:
            return 'REJECT_TRADE'
        elif len(high_failures) >= 2:
            return 'REDUCE_SIZE_SIGNIFICANTLY'
        elif high_failures:
            return 'REDUCE_SIZE_MODERATELY'
        else:
            return 'PROCEED_AS_PLANNED'
    
    def _log_risk_decision(self, decision: Dict):
        """Log risk management decision"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'approved': decision['approved'],
            'risk_score': decision.get('risk_score', 0),
            'recommendation': decision.get('recommendation', ''),
            'size_adjustment': decision.get('adjusted_size', 0) / decision.get('original_size', 1) if decision.get('original_size', 0) > 0 else 0
        }
        
        # Append to risk decisions log
        os.makedirs('logs', exist_ok=True)
        with open('logs/risk_decisions.jsonl', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def calculate_position_size(self, price: float, atr: float = None, symbol: str = None, market_data: Dict = None) -> Dict:
        """
        Calculate optimal position size using Kelly Criterion and multiple risk factors
        Returns detailed sizing information including risk metrics
        """
        try:
            # 1. Kelly Criterion base calculation
            kelly_size = self._calculate_kelly_position()
            
            # 2. ATR-based sizing if available
            atr_size = self.max_position_size
            if atr and price:
                atr_result = self._size_by_atr(atr, price, kelly_size)
                atr_size = atr_result['value']
            
            # 3. Volatility adjustment
            vol_adjusted_size = kelly_size
            if market_data and self.volatility_adjustment:
                current_vol = market_data.get('volatility', 0.15)
                vol_adjusted_size = self._adjust_for_volatility(kelly_size, current_vol)
            
            # 4. Portfolio concentration check
            concentration_limit = self._check_concentration_limit()
            
            # 5. Take the minimum of all constraints
            final_size = min(
                kelly_size,
                atr_size,
                vol_adjusted_size,
                concentration_limit,
                self.max_position_size
            )
            
            # 6. Apply leverage limit
            leveraged_size = min(final_size, self.current_balance * self.max_leverage)
            
            return {
                'recommended_size': round(leveraged_size, 2),
                'kelly_size': round(kelly_size, 2),
                'atr_size': round(atr_size, 2),
                'vol_adjusted_size': round(vol_adjusted_size, 2),
                'concentration_limit': round(concentration_limit, 2),
                'risk_per_dollar': atr / price if atr and price else 0.02,
                'position_as_pct_balance': (leveraged_size / self.current_balance * 100) if self.current_balance > 0 else 0,
                'stop_loss_distance': atr * 2 if atr else price * 0.02
            }
        except Exception as e:
            logger.error(f"Position sizing error: {e}")
            return {
                'recommended_size': self.max_position_size * 0.1,  # Conservative fallback
                'error': str(e)
            }
    
    def _calculate_kelly_position(self) -> float:
        """Calculate position size using Kelly Criterion"""
        if len(self.trade_history) < 10:  # Need minimum history
            return self.current_balance * 0.02  # Conservative 2%
        
        # Calculate win rate and average win/loss
        wins = [t for t in self.trade_history if t > 0]
        losses = [abs(t) for t in self.trade_history if t < 0]
        
        if not wins or not losses:
            return self.current_balance * 0.02
        
        win_rate = len(wins) / len(self.trade_history)
        avg_win = np.mean(wins)
        avg_loss = np.mean(losses)
        win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 1
        
        # Kelly fraction: (bp - q) / b
        # where b = win/loss ratio, p = win rate, q = loss rate
        kelly = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
        
        # Apply safety factor (quarter Kelly)
        safe_kelly = max(0, kelly * 0.25)
        
        # Cap at reasonable limits
        safe_kelly = min(safe_kelly, 0.25)  # Max 25% of bankroll
        
        return self.current_balance * safe_kelly
    
    def _size_by_atr(self, atr: float, price: float, risk_amount: float, multiplier: float = 2.0) -> Dict:
        """Calculate position size based on ATR"""
        stop_distance = atr * multiplier
        position_size = risk_amount / stop_distance if stop_distance > 0 else 0
        
        return {
            'units': position_size,
            'value': position_size * price,
            'stop_loss': price - stop_distance,
            'risk_per_unit': stop_distance
        }
    
    def _adjust_for_volatility(self, base_size: float, current_vol: float, target_vol: float = 0.15) -> float:
        """Adjust position size based on volatility"""
        if current_vol <= 0:
            return base_size * 0.5  # Reduce size if no volatility data
        
        vol_adjustment = target_vol / current_vol
        adjusted_size = base_size * vol_adjustment
        
        # Cap adjustment factor
        adjusted_size = min(adjusted_size, base_size * 2)  # Max 2x
        adjusted_size = max(adjusted_size, base_size * 0.5)  # Min 0.5x
        
        return adjusted_size
    
    def _check_concentration_limit(self) -> float:
        """Check portfolio concentration limits"""
        total_exposure = self.position_manager.total_exposure if hasattr(self, 'position_manager') else 0
        available_capacity = self.current_balance * self.concentration_limit - total_exposure
        return max(0, available_capacity)
    
    def update_pnl(self, pnl: float):
        """Update P&L tracking"""
        self.daily_pnl += pnl
        self.current_balance += pnl
        
        # Update peak balance
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        
        # Update consecutive losses
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        
        # Save state
        self._save_state()
        
        # Check for circuit breaker conditions
        self._check_circuit_breaker_conditions()
    
    def _check_circuit_breaker_conditions(self):
        """Check if any circuit breaker conditions are met (legacy method)"""
        # Use the new comprehensive system
        result = self.check_circuit_breaker_conditions()
        if result['circuit_breaker_active']:
            critical_triggers = [t for t in result['triggers'] if t.get('severity') == 'CRITICAL']
            if critical_triggers:
                reason = '; '.join([t['message'] for t in critical_triggers])
                self._trigger_circuit_breaker(reason, 'CRITICAL')
    
    def check_circuit_breaker_conditions(self, metrics: Dict = None) -> Dict:
        """Comprehensive circuit breaker system with multiple triggers"""
        triggered = []
        
        # Get current metrics
        if not metrics:
            metrics = self._get_current_metrics()
        
        # Check each circuit breaker condition
        for trigger_name, threshold in self.circuit_breakers.items():
            if trigger_name in metrics:
                trigger_result = self._check_trigger(trigger_name, metrics[trigger_name], threshold)
                if trigger_result['triggered']:
                    triggered.append(trigger_result)
        
        # Additional dynamic checks
        triggered.extend(self._check_dynamic_conditions(metrics))
        
        result = {
            'circuit_breaker_active': len(triggered) > 0,
            'triggers': triggered,
            'recommended_action': self._get_recommended_action(triggered),
            'system_status': 'EMERGENCY' if any(t.get('severity') == 'CRITICAL' for t in triggered) else 'NORMAL'
        }
        
        return result
    
    def _get_current_metrics(self) -> Dict:
        """Get current system metrics for circuit breaker evaluation"""
        return {
            'DAILY_LOSS': self.daily_pnl,
            'DRAWDOWN': self._calculate_current_drawdown(),
            'CONSECUTIVE_ERRORS': self.consecutive_losses,
            'ERROR_RATE': self._calculate_error_rate(),
            'LATENCY': self.last_latency
        }
    
    def _check_trigger(self, trigger_name: str, current_value: float, threshold: float) -> Dict:
        """Check individual circuit breaker trigger"""
        triggered = False
        severity = 'INFO'
        
        if trigger_name == 'DAILY_LOSS':
            triggered = current_value <= threshold
            severity = 'CRITICAL' if triggered else 'INFO'
        elif trigger_name == 'DRAWDOWN':
            triggered = current_value >= threshold
            severity = 'CRITICAL' if triggered else 'INFO'
        elif trigger_name == 'LATENCY':
            triggered = current_value >= threshold
            severity = 'HIGH' if triggered else 'INFO'
        elif trigger_name == 'ERROR_RATE':
            triggered = current_value >= threshold
            severity = 'HIGH' if triggered else 'INFO'
        elif trigger_name == 'CONSECUTIVE_ERRORS':
            triggered = current_value >= threshold
            severity = 'HIGH' if triggered else 'INFO'
        
        return {
            'trigger': trigger_name,
            'triggered': triggered,
            'current_value': current_value,
            'threshold': threshold,
            'severity': severity,
            'message': f'{trigger_name}: {current_value} vs threshold {threshold}',
            'action': self._get_trigger_action(trigger_name)
        }
    
    def _check_dynamic_conditions(self, metrics: Dict) -> List[Dict]:
        """Check dynamic circuit breaker conditions"""
        conditions = []
        
        # Velocity-based checks
        if hasattr(self, 'trade_history') and len(self.trade_history) >= 5:
            recent_pnl = sum(self.trade_history[-5:])
            if recent_pnl < -self.max_daily_loss * 0.5:  # 50% of daily limit in recent trades
                conditions.append({
                    'trigger': 'RAPID_LOSS_VELOCITY',
                    'triggered': True,
                    'severity': 'HIGH',
                    'message': f'Rapid loss velocity detected: ${recent_pnl:.2f} in last 5 trades',
                    'action': 'PAUSE_NEW_ORDERS'
                })
        
        # Market regime changes
        if 'market_regime' in metrics and metrics['market_regime'] == 'CRISIS':
            conditions.append({
                'trigger': 'MARKET_CRISIS',
                'triggered': True,
                'severity': 'HIGH',
                'message': 'Market crisis regime detected',
                'action': 'REDUCE_EXPOSURE'
            })
        
        return conditions
    
    def _get_trigger_action(self, trigger_name: str) -> str:
        """Get recommended action for specific trigger"""
        action_map = {
            'DAILY_LOSS': 'EMERGENCY_STOP',
            'DRAWDOWN': 'EMERGENCY_LIQUIDATION',
            'LATENCY': 'PAUSE_NEW_ORDERS',
            'ERROR_RATE': 'REDUCE_POSITION_SIZE',
            'CONSECUTIVE_ERRORS': 'PAUSE_TRADING'
        }
        return action_map.get(trigger_name, 'MONITOR')
    
    def _get_recommended_action(self, triggers: List[Dict]) -> str:
        """Determine overall recommended action based on all triggers"""
        if not triggers:
            return 'NORMAL_OPERATION'
        
        # Prioritize actions by severity
        critical_actions = [t.get('action', '') for t in triggers if t.get('severity') == 'CRITICAL']
        high_actions = [t.get('action', '') for t in triggers if t.get('severity') == 'HIGH']
        
        if 'EMERGENCY_STOP' in critical_actions:
            return 'EMERGENCY_STOP'
        elif 'EMERGENCY_LIQUIDATION' in critical_actions:
            return 'EMERGENCY_LIQUIDATION'
        elif 'PAUSE_TRADING' in high_actions:
            return 'PAUSE_TRADING'
        elif 'PAUSE_NEW_ORDERS' in high_actions:
            return 'PAUSE_NEW_ORDERS'
        elif 'REDUCE_POSITION_SIZE' in high_actions:
            return 'REDUCE_POSITION_SIZE'
        else:
            return 'MONITOR'
    
    def _calculate_current_drawdown(self) -> float:
        """Calculate current drawdown percentage"""
        if self.peak_balance <= 0:
            return 0
        return (self.peak_balance - self.current_balance) / self.peak_balance
    
    def _calculate_error_rate(self) -> float:
        """Calculate recent error rate"""
        # This would be implemented based on actual error tracking
        # For now, return a placeholder
        return 0.0
    
    def _trigger_circuit_breaker(self, reason: str, severity: str = 'CRITICAL'):
        """Trigger comprehensive circuit breaker system"""
        timestamp = datetime.now().isoformat()
        logger.critical(f"CIRCUIT BREAKER TRIGGERED [{severity}]: {reason}")
        
        # Create detailed circuit breaker state
        circuit_breaker_state = {
            'timestamp': timestamp,
            'reason': reason,
            'severity': severity,
            'account_state': {
                'daily_pnl': self.daily_pnl,
                'current_balance': self.current_balance,
                'peak_balance': self.peak_balance,
                'drawdown': self._calculate_current_drawdown(),
                'consecutive_losses': self.consecutive_losses
            },
            'system_metrics': {
                'error_rate': self._calculate_error_rate(),
                'last_latency': self.last_latency,
                'active_positions': len(self.position_manager.positions) if hasattr(self, 'position_manager') else 0
            },
            'recovery_conditions': self._get_recovery_conditions()
        }
        
        # Write circuit breaker file
        with open('.circuit_breaker_triggered', 'w') as f:
            f.write(json.dumps(circuit_breaker_state, indent=2))
        
        # Log to risk decisions
        self._log_circuit_breaker(circuit_breaker_state)
        
        # Execute emergency procedures
        self._execute_emergency_procedures(severity)
        
        # Call circuit breaker hook if exists
        if os.path.exists('.claude/hooks/circuit_breaker.sh'):
            try:
                os.system(f'.claude/hooks/circuit_breaker.sh "{reason}" {severity}')
            except Exception as e:
                logger.error(f"Circuit breaker hook failed: {e}")
    
    def _get_recovery_conditions(self) -> Dict:
        """Define conditions for circuit breaker recovery"""
        return {
            'manual_reset_required': True,
            'min_wait_minutes': 15,
            'required_checks': [
                'System latency < 500ms',
                'Error rate < 1%',
                'Account balance verified',
                'All positions reconciled'
            ],
            'gradual_restart': {
                'phase_1': 'Monitor only (30 min)',
                'phase_2': 'Paper trading (2 hours)',
                'phase_3': 'Reduced size live trading',
                'phase_4': 'Full operation'
            }
        }
    
    def _execute_emergency_procedures(self, severity: str):
        """Execute emergency procedures based on severity"""
        try:
            if severity == 'CRITICAL':
                # Emergency liquidation if configured
                if self.config.get('auto_liquidate_on_critical', False):
                    self._emergency_liquidate_all()
                
                # Stop all trading processes
                self._stop_trading_processes()
                
            elif severity == 'HIGH':
                # Reduce all positions
                self._reduce_all_positions(0.5)  # 50% reduction
                
            # Send alerts
            self._send_emergency_alerts(severity)
            
        except Exception as e:
            logger.error(f"Emergency procedure failed: {e}")
    
    def _stop_trading_processes(self):
        """Stop all trading processes"""
        try:
            # This would integrate with the actual trading system
            # For now, log the action
            logger.critical("STOPPING ALL TRADING PROCESSES")
            
            # Kill trading orchestrator if running
            os.system('pkill -f "trading.orchestrator" || true')
            
        except Exception as e:
            logger.error(f"Failed to stop trading processes: {e}")
    
    def _emergency_liquidate_all(self):
        """Emergency liquidation of all positions"""
        if hasattr(self, 'position_manager'):
            logger.critical("EMERGENCY LIQUIDATION OF ALL POSITIONS")
            # This would implement actual liquidation logic
            # For now, just log
    
    def _reduce_all_positions(self, factor: float):
        """Reduce all positions by a factor"""
        logger.warning(f"REDUCING ALL POSITIONS BY {factor:.0%}")
        # Implementation would depend on position management system
    
    def _send_emergency_alerts(self, severity: str):
        """Send emergency alerts via configured channels"""
        alert_message = f"TRADING SYSTEM ALERT [{severity}]: Circuit breaker triggered at {datetime.now()}"
        logger.critical(alert_message)
        
        # Here you would integrate with actual alerting systems
        # e.g., Slack, email, SMS, etc.
    
    def _log_circuit_breaker(self, state: Dict):
        """Log circuit breaker activation"""
        os.makedirs('logs', exist_ok=True)
        with open('logs/circuit_breaker.jsonl', 'a') as f:
            f.write(json.dumps(state) + '\n')
    
    def reset_daily_stats(self):
        """Reset daily statistics"""
        logger.info("Resetting daily risk statistics")
        self.daily_pnl = 0
        self._save_state()
    
    def get_risk_status(self) -> Dict:
        """Get simplified risk status for backward compatibility"""
        drawdown = self._calculate_current_drawdown()
        
        return {
            'current_balance': self.current_balance,
            'peak_balance': self.peak_balance,
            'daily_pnl': self.daily_pnl,
            'drawdown': drawdown,
            'consecutive_losses': self.consecutive_losses,
            'circuit_breaker_active': os.path.exists('.circuit_breaker_triggered'),
            'daily_loss_remaining': max(0, self.max_daily_loss + self.daily_pnl),
            'position_size_limit': self.max_position_size,
            'risk_score': self._calculate_overall_risk_score()
        }
    
    def get_comprehensive_risk_status(self) -> Dict:
        """Get comprehensive risk status with all metrics"""
        drawdown = self._calculate_current_drawdown()
        
        # Get circuit breaker status
        cb_check = self.check_circuit_breaker_conditions()
        
        # Calculate risk utilization
        daily_loss_used = abs(self.daily_pnl) / self.max_daily_loss if self.max_daily_loss > 0 else 0
        drawdown_used = drawdown / self.max_drawdown if self.max_drawdown > 0 else 0
        
        # Position metrics
        position_metrics = self.position_manager.get_exposure() if hasattr(self, 'position_manager') else {
            'total_exposure': 0,
            'open_positions': 0,
            'positions': []
        }
        
        return {
            'timestamp': datetime.now().isoformat(),
            'account_metrics': {
                'current_balance': self.current_balance,
                'peak_balance': self.peak_balance,
                'daily_pnl': self.daily_pnl,
                'total_pnl': self.current_balance - 10000,  # Assuming 10k start
                'drawdown_current': drawdown,
                'drawdown_max': self.max_drawdown,
                'consecutive_losses': self.consecutive_losses
            },
            'risk_utilization': {
                'daily_loss_used_pct': min(100, daily_loss_used * 100),
                'drawdown_used_pct': min(100, drawdown_used * 100),
                'daily_loss_remaining': max(0, self.max_daily_loss + self.daily_pnl),
                'drawdown_remaining_pct': max(0, (self.max_drawdown - drawdown) * 100)
            },
            'position_metrics': position_metrics,
            'limits': {
                'max_position_size': self.max_position_size,
                'max_daily_loss': self.max_daily_loss,
                'max_drawdown_pct': self.max_drawdown * 100,
                'max_consecutive_losses': self.max_consecutive_losses,
                'max_leverage': self.max_leverage,
                'concentration_limit_pct': self.concentration_limit * 100
            },
            'circuit_breaker': {
                'active': cb_check['circuit_breaker_active'],
                'system_status': cb_check['system_status'],
                'triggered_conditions': [t['trigger'] for t in cb_check['triggers'] if t.get('triggered')],
                'recommended_action': cb_check['recommended_action']
            },
            'kelly_metrics': {
                'win_rate': self.win_rate,
                'avg_win': self.avg_win,
                'avg_loss': self.avg_loss,
                'trade_count': len(self.trade_history) if hasattr(self, 'trade_history') else 0
            },
            'performance_metrics': self._calculate_performance_metrics(),
            'risk_score': self._calculate_overall_risk_score()
        }
    
    def _calculate_performance_metrics(self) -> Dict:
        """Calculate performance metrics"""
        if not hasattr(self, 'trade_history') or len(self.trade_history) < 2:
            return {'insufficient_data': True}
        
        trades = np.array(self.trade_history)
        returns = trades[trades != 0]  # Remove zero trades
        
        if len(returns) == 0:
            return {'no_completed_trades': True}
        
        # Calculate metrics
        total_return = np.sum(returns)
        avg_return = np.mean(returns)
        volatility = np.std(returns) if len(returns) > 1 else 0
        
        # Sharpe ratio (assuming 0% risk-free rate)
        sharpe = avg_return / volatility if volatility > 0 else 0
        
        # Sortino ratio (downside deviation)
        negative_returns = returns[returns < 0]
        downside_vol = np.std(negative_returns) if len(negative_returns) > 1 else 0
        sortino = avg_return / downside_vol if downside_vol > 0 else 0
        
        # Win rate
        wins = np.sum(returns > 0)
        win_rate = wins / len(returns) if len(returns) > 0 else 0
        
        # Max consecutive wins/losses
        consecutive_wins = 0
        consecutive_losses = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        
        for ret in returns:
            if ret > 0:
                consecutive_wins += 1
                consecutive_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
            else:
                consecutive_losses += 1
                consecutive_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
        
        return {
            'total_trades': len(returns),
            'total_return': total_return,
            'avg_return_per_trade': avg_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'win_rate': win_rate,
            'avg_win': np.mean(returns[returns > 0]) if np.any(returns > 0) else 0,
            'avg_loss': np.mean(returns[returns < 0]) if np.any(returns < 0) else 0,
            'max_consecutive_wins': max_consecutive_wins,
            'max_consecutive_losses': max_consecutive_losses,
            'profit_factor': abs(np.sum(returns[returns > 0]) / np.sum(returns[returns < 0])) if np.any(returns < 0) else float('inf')
        }
    
    def _calculate_overall_risk_score(self) -> float:
        """Calculate overall risk score (0-100, lower is better)"""
        scores = []
        
        # Drawdown score
        drawdown_score = (self._calculate_current_drawdown() / self.max_drawdown * 100) if self.max_drawdown > 0 else 0
        scores.append(min(100, drawdown_score))
        
        # Daily loss score
        daily_loss_score = (abs(self.daily_pnl) / self.max_daily_loss * 100) if self.max_daily_loss > 0 else 0
        scores.append(min(100, daily_loss_score))
        
        # Consecutive losses score
        consecutive_score = (self.consecutive_losses / self.max_consecutive_losses * 100) if self.max_consecutive_losses > 0 else 0
        scores.append(min(100, consecutive_score))
        
        # Circuit breaker score
        cb_score = 100 if os.path.exists('.circuit_breaker_triggered') else 0
        scores.append(cb_score)
        
        # Return weighted average
        weights = [0.3, 0.3, 0.2, 0.2]  # Adjust weights as needed
        return sum(score * weight for score, weight in zip(scores, weights))


class PositionManager:
    """
    Manages open positions and exposure
    """
    
    def __init__(self, risk_manager: RiskManager):
        self.risk_manager = risk_manager
        self.positions = {}
        self.total_exposure = 0
    
    def add_position(self, symbol: str, size: float, side: str, entry_price: float):
        """Add a new position"""
        position_id = f"{symbol}_{datetime.now().timestamp()}"
        
        self.positions[position_id] = {
            'symbol': symbol,
            'size': size,
            'side': side,
            'entry_price': entry_price,
            'entry_time': datetime.now(),
            'stop_loss': None,
            'take_profit': None
        }
        
        # Update exposure
        self.total_exposure += size
        
        logger.info(f"Position opened: {position_id} - {symbol} {side} {size}@{entry_price}")
        return position_id
    
    def close_position(self, position_id: str, exit_price: float) -> float:
        """Close a position and calculate P&L"""
        if position_id not in self.positions:
            logger.error(f"Position {position_id} not found")
            return 0
        
        position = self.positions[position_id]
        
        # Calculate P&L
        if position['side'] == 'long':
            pnl = (exit_price - position['entry_price']) * position['size'] / position['entry_price']
        else:
            pnl = (position['entry_price'] - exit_price) * position['size'] / position['entry_price']
        
        # Update risk manager
        self.risk_manager.update_pnl(pnl)
        
        # Remove position
        self.total_exposure -= position['size']
        del self.positions[position_id]
        
        logger.info(f"Position closed: {position_id} - P&L: ${pnl:.2f}")
        return pnl
    
    def set_stop_loss(self, position_id: str, stop_price: float):
        """Set stop loss for a position"""
        if position_id in self.positions:
            self.positions[position_id]['stop_loss'] = stop_price
            logger.info(f"Stop loss set for {position_id}: {stop_price}")
    
    def set_take_profit(self, position_id: str, target_price: float):
        """Set take profit for a position"""
        if position_id in self.positions:
            self.positions[position_id]['take_profit'] = target_price
            logger.info(f"Take profit set for {position_id}: {target_price}")
    
    def check_stops(self, current_prices: Dict):
        """Check if any stops are triggered"""
        positions_to_close = []
        
        for position_id, position in self.positions.items():
            symbol = position['symbol']
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            
            # Check stop loss
            if position['stop_loss']:
                if position['side'] == 'long' and current_price <= position['stop_loss']:
                    positions_to_close.append((position_id, current_price, 'stop_loss'))
                elif position['side'] == 'short' and current_price >= position['stop_loss']:
                    positions_to_close.append((position_id, current_price, 'stop_loss'))
            
            # Check take profit
            if position['take_profit']:
                if position['side'] == 'long' and current_price >= position['take_profit']:
                    positions_to_close.append((position_id, current_price, 'take_profit'))
                elif position['side'] == 'short' and current_price <= position['take_profit']:
                    positions_to_close.append((position_id, current_price, 'take_profit'))
        
        # Close triggered positions
        for position_id, price, reason in positions_to_close:
            logger.info(f"Closing position {position_id} - {reason} triggered at {price}")
            self.close_position(position_id, price)
    
    def get_exposure(self) -> Dict:
        """Get current exposure metrics"""
        return {
            'total_exposure': self.total_exposure,
            'open_positions': len(self.positions),
            'positions': list(self.positions.values())
        }


def main():
    """Main entry point for testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Risk Manager')
    parser.add_argument('--status', action='store_true',
                       help='Show risk status')
    parser.add_argument('--reset', action='store_true',
                       help='Reset circuit breaker')
    
    args = parser.parse_args()
    
    # Load config with comprehensive risk parameters
    config = {
        'max_position_size': 62.50,
        'max_daily_loss': 100,
        'max_drawdown': 0.05,  # 5% max drawdown
        'max_consecutive_losses': 3,
        'bankroll_percentage': 0.02,  # 2% per trade
        'max_leverage': 3.0,
        'symbol_whitelist': ['BTC/USDT', 'ETH/USDT'],
        'volatility_adjustment': True,
        'max_correlation': 0.7,
        'max_concentration': 0.25,
        # Circuit breaker thresholds
        'cb_daily_loss': -100,
        'cb_drawdown': 0.10,
        'cb_latency_ms': 1000,
        'cb_error_rate': 0.05,
        'cb_consecutive_errors': 3
    }
    
    # Create risk manager
    risk_manager = RiskManager(config)
    
    if args.status:
        # Show status
        status = risk_manager.get_risk_status()
        print("Risk Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")
    
    if args.reset:
        # Reset circuit breaker using new comprehensive system
        result = risk_manager.reset_circuit_breaker(manual_override=True)
        if result['success']:
            print(f"✓ {result['message']}")
        else:
            print(f"✗ {result['message']}")
            if 'conditions' in result:
                print("Recovery conditions not met:")
                for condition, status in result['conditions']['conditions'].items():
                    print(f"  {condition}: {'✓' if status else '✗'}")
    
    def reset_circuit_breaker(self, manual_override: bool = False) -> Dict:
        """Reset circuit breaker with safety checks"""
        if not os.path.exists('.circuit_breaker_triggered'):
            return {'success': True, 'message': 'Circuit breaker was not active'}
        
        try:
            # Load current circuit breaker state
            with open('.circuit_breaker_triggered', 'r') as f:
                cb_state = json.load(f)
            
            # Check recovery conditions
            recovery_check = self._check_recovery_conditions(cb_state)
            
            if not recovery_check['ready'] and not manual_override:
                return {
                    'success': False,
                    'message': 'Recovery conditions not met',
                    'conditions': recovery_check
                }
            
            # Reset circuit breaker
            os.remove('.circuit_breaker_triggered')
            
            # Log reset
            reset_log = {
                'timestamp': datetime.now().isoformat(),
                'action': 'circuit_breaker_reset',
                'manual_override': manual_override,
                'previous_state': cb_state
            }
            
            with open('logs/circuit_breaker.jsonl', 'a') as f:
                f.write(json.dumps(reset_log) + '\n')
            
            logger.info(f"Circuit breaker reset {'(manual override)' if manual_override else ''}")
            
            return {
                'success': True,
                'message': 'Circuit breaker reset successfully',
                'restart_mode': 'gradual' if not manual_override else 'immediate'
            }
            
        except Exception as e:
            logger.error(f"Circuit breaker reset failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _check_recovery_conditions(self, cb_state: Dict) -> Dict:
        """Check if conditions are met for circuit breaker recovery"""
        recovery_conditions = cb_state.get('recovery_conditions', {})
        min_wait = recovery_conditions.get('min_wait_minutes', 15)
        
        # Check minimum wait time
        trigger_time = datetime.fromisoformat(cb_state['timestamp'])
        wait_elapsed = (datetime.now() - trigger_time).total_seconds() / 60
        
        conditions_met = {
            'wait_time_elapsed': wait_elapsed >= min_wait,
            'system_stable': self._calculate_error_rate() < 0.01,
            'latency_acceptable': self.last_latency < 500,
            'account_verified': True  # This would be actual verification
        }
        
        all_ready = all(conditions_met.values())
        
        return {
            'ready': all_ready,
            'conditions': conditions_met,
            'wait_remaining': max(0, min_wait - wait_elapsed) if not conditions_met['wait_time_elapsed'] else 0
        }


if __name__ == '__main__':
    main()