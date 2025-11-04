import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass
import json
import logging

try:
    import vectorbtpro as vbt
    # Configure VBT Pro for maximum performance
    vbt.settings.set_theme('dark')
    vbt.settings['caching'] = {
        'disable': False,
        'disable_whitelist': False,
        'disable_machinery': False,
        'silence_warnings': False,
        'register_lazily': True,
        'ignore_args': ['jitted', 'chunked'],
        'use_cached_accessors': True
    }
    vbt.settings['numba']['parallel'] = True
    # Note: 'cache' setting doesn't exist in this VBT version
    HAS_VBT = True
    print(f"VectorBT Pro {vbt.__version__} loaded successfully")
except Exception as e:
    vbt = None
    HAS_VBT = False
    print(f"VectorBT Pro not available: {e}")

logger = logging.getLogger(__name__)

@dataclass
class BacktestResult:
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    trades: List[Dict]
    equity_curve: pd.Series
    metrics: Dict

def _fallback_backtest(df: pd.DataFrame, position_size: float = 0.25, initial_cash: float = 10000) -> dict:
    # Enhanced fallback with trade memory
    prices = df["close"] if "close" in df.columns else df["Close"]
    entries = df["entries"].fillna(False) if "entries" in df.columns else pd.Series(False, index=df.index)
    exits = df["exits"].fillna(False) if "exits" in df.columns else pd.Series(False, index=df.index)
    
    position = 0
    cash = initial_cash
    equity = [initial_cash]
    trades = []
    rets = []
    
    for i in range(1, len(df)):
        try:
            entry_signal = entries.iloc[i-1] if i-1 < len(entries) else False
            exit_signal = exits.iloc[i-1] if i-1 < len(exits) else False
            current_price = prices.iloc[i]
            
            if position == 0 and entry_signal:
                # Entry
                position_value = cash * position_size
                position = position_value / current_price
                cash -= position_value
                trades.append({
                    'entry_time': df.index[i],
                    'entry_price': current_price,
                    'size': position,
                    'entry_reason': 'signal_triggered'
                })
            elif position > 0 and exit_signal and trades:
                # Exit
                exit_value = position * current_price
                pnl = exit_value - (trades[-1]['entry_price'] * position)
                cash += exit_value
                equity.append(cash)
                
                # Update trade record
                trades[-1].update({
                    'exit_time': df.index[i],
                    'exit_price': current_price,
                    'pnl': pnl,
                    'return': pnl / (trades[-1]['entry_price'] * position),
                    'exit_reason': 'signal_exit'
                })
                
                rets.append(trades[-1]['return'])
                position = 0
            else:
                # Hold or no position
                current_equity = cash + (position * current_price if position > 0 else 0)
                equity.append(current_equity)
                
        except (IndexError, KeyError) as e:
            # Skip problematic rows
            continue
    
    # Calculate metrics
    equity_series = pd.Series(equity[:len(df)], index=df.index[:len(equity)])
    returns = equity_series.pct_change().dropna()
    
    total_return = (equity[-1] - initial_cash) / initial_cash
    sharpe = returns.mean() / returns.std() * np.sqrt(252 * 288) if returns.std() > 0 else 0
    max_dd = (equity_series / equity_series.cummax() - 1).min()
    win_rate = len([t for t in trades if t.get('pnl', 0) > 0]) / len(trades) if trades else 0
    
    # Profit factor
    wins = sum([t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0])
    losses = abs(sum([t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0]))
    profit_factor = wins / losses if losses > 0 else 0
    
    sortino = (np.mean(rets) / (np.std([r for r in rets if r < 0]) + 1e-9)) if rets else 0.0
    
    return {
        "total_return": float(total_return),
        "trades": int(len(trades)),
        "sortino": float(sortino),
        "sharpe_ratio": float(sharpe),
        "max_drawdown": float(max_dd),
        "win_rate": float(win_rate),
        "profit_factor": float(profit_factor),
        "trade_records": trades,
        "equity_curve": equity_series.to_dict()
    }

def run_backtest(df: pd.DataFrame, exec_cfg: dict | None = None, 
                position_size: float = 0.25, initial_cash: float = 10000,
                fee: float = 0.001, advanced_metrics: bool = True,
                save_returns: bool = True, save_state: bool = True) -> dict:
    """
    Enhanced VectorBT Pro backtesting with trade memory and advanced metrics
    
    Args:
        df: OHLCV data with entries/exits columns
        exec_cfg: Execution configuration
        position_size: Fraction of portfolio per trade
        initial_cash: Starting capital
        fee: Trading fee percentage
        advanced_metrics: Include advanced metrics
    """
    if not HAS_VBT:
        return _fallback_backtest(df, position_size, initial_cash)
    
    # Enhanced VBT backtesting
    entries = df["entries"].fillna(False)
    exits = df["exits"].fillna(False)
    close = df["close"] if "close" in df.columns else df["Close"]
    
    # Configure portfolio with VectorBT Pro advanced settings
    # Calculate size as percentage of available cash
    size_value = position_size * initial_cash
    
    pf = vbt.Portfolio.from_signals(
        close=close,
        entries=entries,
        exits=exits,
        size=size_value,
        size_type='value',  # Use value-based sizing instead of target percent
        init_cash=initial_cash,
        fees=fee,
        freq='5min',  # Use 'min' instead of deprecated 'T'
        call_seq='auto',
        save_returns=save_returns,  # Pre-compute returns for performance
        save_state=save_state,  # Save execution state for analysis
        fill_pos_info=True,  # Track detailed position information
        cash_sharing=False,  # Independent positions per asset
        update_value=True  # Update portfolio value after each order
    )
    
    # Extract trade records with memory  
    trades = []
    try:
        if pf.trades.count() > 0:
            trade_records = pf.trades.records_readable
            
            # Debug: check available columns (commented out)
            # print(f"Trade record columns: {trade_records.columns.tolist()}")
            
            for idx, trade in trade_records.iterrows():
                try:
                    # Use actual timestamp columns if available
                    entry_time = trade.get('Entry Timestamp', trade.get('Entry Index'))
                    exit_time = trade.get('Exit Timestamp', trade.get('Exit Index'))
                    
                    # Calculate duration
                    if hasattr(entry_time, 'total_seconds') and hasattr(exit_time, 'total_seconds'):
                        duration = (exit_time - entry_time).total_seconds() / 60
                    else:
                        duration = 0
                    
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': exit_time,
                        'entry_price': trade.get('Avg Entry Price', trade.get('Entry Price', 0)),
                        'exit_price': trade.get('Avg Exit Price', trade.get('Exit Price', 0)),
                        'size': trade.get('Size', 0),
                        'pnl': trade.get('PnL', 0),
                        'return': trade.get('Return', 0),
                        'duration': duration,
                        'direction': trade.get('Direction', 'Long'),
                        'status': trade.get('Status', 'Closed')
                    })
                except Exception as e:
                    # Skip problematic trades
                    continue
    except Exception as e:
        # If trade extraction fails, continue with empty trades
        print(f"Trade extraction failed: {e}")
        trades = []
    
    # Get comprehensive stats - handle different VectorBT versions
    try:
        stats = pf.stats()
    except (AttributeError, TypeError, ValueError) as e:
        logger.debug(f"Could not extract portfolio stats: {e}")
        stats = {}
    
    # Build result dictionary - handle callable vs property differences
    def safe_extract(obj, default=0.0):
        """Safely extract value from VectorBT object (callable or property)"""
        try:
            if callable(obj):
                return float(obj())
            else:
                return float(obj)
        except (TypeError, ValueError, AttributeError) as e:
            return default
    
    result = {
        "total_return": safe_extract(pf.total_return if hasattr(pf, 'total_return') else 0),
        "trades": int(pf.trades.count() if hasattr(pf.trades, 'count') else len(trades)),
        "sortino": float(stats.get("Sortino Ratio", 0.0)),
        "sharpe_ratio": safe_extract(pf.sharpe_ratio if hasattr(pf, 'sharpe_ratio') else 0),
        "max_drawdown": safe_extract(pf.max_drawdown if hasattr(pf, 'max_drawdown') else 0),
        "win_rate": safe_extract(pf.trades.win_rate if hasattr(pf.trades, 'win_rate') else 0),
        "profit_factor": safe_extract(pf.trades.profit_factor if hasattr(pf.trades, 'profit_factor') else 0)
    }
    
    if advanced_metrics:
        # Add VectorBT Pro advanced metrics
        # Calculate average trade duration from our trade records
        avg_duration = np.mean([t['duration'] for t in trades]) if trades else 0
        
        # Safe calculations
        max_dd = safe_extract(pf.max_drawdown if hasattr(pf, 'max_drawdown') else 0)
        calmar_ratio = 0
        if max_dd != 0:
            ann_ret = safe_extract(pf.annualized_return if hasattr(pf, 'annualized_return') else 0)
            calmar_ratio = ann_ret / abs(max_dd)
        
        try:
            equity_curve = pf.cumulative_returns().to_dict() if hasattr(pf, 'cumulative_returns') else {}
        except (AttributeError, TypeError, ValueError) as e:
            equity_curve = {}
            
        # Trade-based metrics
        best_trade = 0
        worst_trade = 0
        consecutive_wins = 0
        consecutive_losses = 0
        
        try:
            if hasattr(pf.trades, 'returns') and pf.trades.count() > 0:
                returns_series = pf.trades.returns
                best_trade = float(returns_series.max())
                worst_trade = float(returns_series.min())
                consecutive_wins = _max_consecutive(returns_series > 0)
                consecutive_losses = _max_consecutive(returns_series < 0)
        except (AttributeError, TypeError, ValueError) as e:
            pass  # Use default values if trade analysis fails
        
        result.update({
            "calmar_ratio": calmar_ratio,
            "omega_ratio": safe_extract(pf.omega_ratio if hasattr(pf, 'omega_ratio') else 0),
            "avg_trade_duration": float(avg_duration),
            "best_trade": best_trade,
            "worst_trade": worst_trade,
            "consecutive_wins": consecutive_wins,
            "consecutive_losses": consecutive_losses,
            "trade_records": trades,
            "equity_curve": equity_curve,
            # VectorBT Pro specific metrics
            "tail_ratio": safe_extract(pf.tail_ratio if hasattr(pf, 'tail_ratio') else 0),
            "expectancy": safe_extract(pf.trades.expectancy if hasattr(pf.trades, 'expectancy') else 0),
            "kelly_criterion": _calculate_kelly(pf) if len(trades) > 0 else 0,
            "memory_usage_mb": safe_extract(pf.getsize if hasattr(pf, 'getsize') else 0) / 1024 / 1024
        })
    
    return result

def _max_consecutive(series):
    """Calculate maximum consecutive True values"""
    if len(series) == 0:
        return 0
    groups = (series != series.shift()).cumsum()
    return series.groupby(groups).sum().max()

def _calculate_kelly(pf):
    """Calculate Kelly Criterion from portfolio"""
    try:
        if not hasattr(pf.trades, 'count') or pf.trades.count() <= 0:
            return 0.0
            
        # Use safe_extract for win_rate
        def safe_extract(obj, default=0.0):
            try:
                if callable(obj):
                    return float(obj())
                else:
                    return float(obj)
            except (TypeError, ValueError, AttributeError):
                return default
        
        win_rate = safe_extract(pf.trades.win_rate if hasattr(pf.trades, 'win_rate') else 0)
        
        if not hasattr(pf.trades, 'returns'):
            return 0.0
            
        returns = pf.trades.returns
        avg_win = returns[returns > 0].mean() if (returns > 0).any() else 0
        avg_loss = abs(returns[returns < 0].mean()) if (returns < 0).any() else 1
        
        if avg_loss == 0 or avg_win == 0:
            return 0.0
        return (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
    except (ZeroDivisionError, ValueError, TypeError) as e:
        return 0.0

def analyze_trades(trades: List[Dict]) -> Dict:
    """Deep analysis of trade patterns"""
    if not trades:
        return {}
    
    trades_df = pd.DataFrame(trades)
    
    analysis = {
        'trade_count': len(trades),
        'profitable_trades': len([t for t in trades if t.get('pnl', 0) > 0]),
        'losing_trades': len([t for t in trades if t.get('pnl', 0) < 0]),
        'avg_pnl': trades_df['pnl'].mean() if 'pnl' in trades_df else 0,
        'total_pnl': trades_df['pnl'].sum() if 'pnl' in trades_df else 0,
        'best_trade_pnl': trades_df['pnl'].max() if 'pnl' in trades_df else 0,
        'worst_trade_pnl': trades_df['pnl'].min() if 'pnl' in trades_df else 0,
        'avg_duration': trades_df['duration'].mean() if 'duration' in trades_df else 0
    }
    
    # Risk metrics
    if 'return' in trades_df:
        returns = trades_df['return'].dropna()
        if len(returns) > 0:
            analysis['var_95'] = np.percentile(returns, 5)
            analysis['cvar_95'] = returns[returns <= analysis['var_95']].mean()
    
    return analysis


def run_grid_search(data: Dict[str, pd.DataFrame], param_grid: Dict, 
                   initial_cash: float = 10000, n_jobs: int = -1) -> pd.DataFrame:
    """
    Run VectorBT Pro grid search across multiple assets and parameters
    
    Args:
        data: Dictionary of {symbol: DataFrame} with OHLCV data
        param_grid: Parameter grid for optimization
        initial_cash: Starting capital
        n_jobs: Number of parallel jobs (-1 for all cores)
    
    Returns:
        DataFrame with grid search results
    """
    if not HAS_VBT:
        logger.error("VectorBT Pro required for grid search")
        return pd.DataFrame()
    
    # Setup parameter combinations using VBT's Param
    param_product = vbt.Param(
        param_grid,
        product=True  # Create all combinations
    )
    
    results = []
    
    # Run grid search for each asset
    for symbol, df in data.items():
        logger.info(f"Grid search for {symbol} with {len(param_product)} combinations")
        
        # Generate signals for each parameter combination
        entries_list = []
        exits_list = []
        param_names = []
        
        for params in param_product:
            # Generate signals based on parameters
            entries, exits = generate_signals_from_params(df, params)
            entries_list.append(entries)
            exits_list.append(exits)
            param_names.append(str(params))
        
        # Batch backtest all combinations using VBT Pro
        close = df['close'] if 'close' in df.columns else df['Close']
        
        # Stack signals for batch processing
        entries_stack = pd.concat(entries_list, axis=1, keys=param_names)
        exits_stack = pd.concat(exits_list, axis=1, keys=param_names)
        
        # Run batch backtest
        pf = vbt.Portfolio.from_signals(
            close=close,
            entries=entries_stack,
            exits=exits_stack,
            size=initial_cash * 0.1,  # 10% per position
            size_type='value',
            init_cash=initial_cash,
            fees=0.001,
            freq='5min',
            n_jobs=n_jobs,  # Parallel processing
            chunk_len=100  # Process in chunks
        )
        
        # Extract metrics for each combination
        for i, params in enumerate(param_product):
            col = param_names[i]
            
            # Safe metric extraction
            def safe_get(func, default=0):
                try:
                    val = func[col] if hasattr(func, '__getitem__') else func
                    return float(val) if not pd.isna(val) else default
                except (KeyError, TypeError, ValueError, AttributeError):
                    return default
            
            result = {
                'symbol': symbol,
                'params': params,
                'total_return': safe_get(pf.total_return),
                'sharpe_ratio': safe_get(pf.sharpe_ratio),
                'sortino_ratio': safe_get(pf.sortino_ratio),
                'max_drawdown': safe_get(pf.max_drawdown),
                'win_rate': safe_get(pf.trades.win_rate),
                'num_trades': safe_get(pf.trades.count),
                'profit_factor': safe_get(pf.trades.profit_factor)
            }
            results.append(result)
    
    return pd.DataFrame(results)


def generate_signals_from_params(df: pd.DataFrame, params: Dict) -> Tuple[pd.Series, pd.Series]:
    """Generate entry/exit signals from parameters"""
    
    # RSI signals
    rsi_period = params.get('rsi_period', 14)
    rsi_oversold = params.get('rsi_oversold', 30)
    rsi_overbought = params.get('rsi_overbought', 70)
    
    # EMA signals
    ema_fast = params.get('ema_fast', 20)
    ema_slow = params.get('ema_slow', 50)
    
    # Calculate indicators using VBT
    close = df['close'] if 'close' in df.columns else df['Close']
    
    rsi = vbt.RSI.run(close, window=rsi_period).rsi
    ema_f = vbt.MA.run(close, window=ema_fast, ma_type='ema').ma
    ema_s = vbt.MA.run(close, window=ema_slow, ma_type='ema').ma
    
    # Generate signals
    entries = (rsi < rsi_oversold) & (ema_f > ema_s)
    exits = (rsi > rsi_overbought) | (ema_f < ema_s)
    
    return entries, exits


def run_multi_asset_portfolio(data: Dict[str, pd.DataFrame], strategies: Dict[str, Dict],
                             initial_cash: float = 100000, 
                             rebalance_freq: str = 'daily') -> Dict:
    """
    Run portfolio backtest across multiple assets with different strategies
    
    Args:
        data: Dictionary of {symbol: DataFrame} with OHLCV data
        strategies: Dictionary of {symbol: strategy_params}
        initial_cash: Starting capital
        rebalance_freq: Rebalancing frequency
    
    Returns:
        Portfolio performance metrics
    """
    if not HAS_VBT:
        logger.error("VectorBT Pro required for multi-asset portfolio")
        return {}
    
    # Prepare data for all assets
    close_data = {}
    entries_data = {}
    exits_data = {}
    
    for symbol in strategies.keys():
        if symbol not in data:
            logger.warning(f"No data for {symbol}, skipping")
            continue
            
        df = data[symbol]
        params = strategies[symbol]
        
        # Generate signals
        entries, exits = generate_signals_from_params(df, params)
        
        close_data[symbol] = df['close'] if 'close' in df.columns else df['Close']
        entries_data[symbol] = entries
        exits_data[symbol] = exits
    
    # Align data to same index
    close_df = pd.DataFrame(close_data)
    entries_df = pd.DataFrame(entries_data)
    exits_df = pd.DataFrame(exits_data)
    
    # Forward fill for missing data
    close_df = close_df.fillna(method='ffill')
    entries_df = entries_df.fillna(False)
    exits_df = exits_df.fillna(False)
    
    # Calculate position sizes (risk parity)
    volatilities = close_df.pct_change().std()
    inv_vol = 1 / volatilities
    weights = inv_vol / inv_vol.sum()
    
    # Run portfolio backtest
    pf = vbt.Portfolio.from_signals(
        close=close_df,
        entries=entries_df,
        exits=exits_df,
        size=weights * initial_cash * 0.95,  # 95% invested, 5% cash buffer
        size_type='value',
        init_cash=initial_cash,
        fees=0.001,
        freq='5min',
        group_by=True,  # Treat as single portfolio
        cash_sharing=True,  # Share cash across assets
        call_seq='auto'
    )
    
    # Calculate portfolio metrics
    metrics = {
        'total_return': float(pf.total_return()),
        'annualized_return': float(pf.annualized_return()),
        'sharpe_ratio': float(pf.sharpe_ratio()),
        'sortino_ratio': float(pf.sortino_ratio()),
        'max_drawdown': float(pf.max_drawdown()),
        'calmar_ratio': float(pf.calmar_ratio()),
        'num_trades': int(pf.trades.count()),
        'win_rate': float(pf.trades.win_rate()),
        'profit_factor': float(pf.trades.profit_factor()),
        'assets_traded': len(close_df.columns),
        'portfolio_value': float(pf.value()[-1]),
        'weights': weights.to_dict()
    }
    
    # Asset contribution analysis
    asset_returns = {}
    for col in close_df.columns:
        if col in pf.wrapper.columns:
            asset_pf = pf[col]
            asset_returns[col] = float(asset_pf.total_return())
    
    metrics['asset_returns'] = asset_returns
    
    return metrics