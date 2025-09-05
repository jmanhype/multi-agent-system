import pandas as pd
import numpy as np

try:
    import vectorbtpro as vbt  # optional
except Exception:
    vbt = None

from ..sim.execution_model import ExecutionConfig, apply_execution

def _fallback_backtest(df: pd.DataFrame) -> dict:
    # Naive PnL: buy at next close on entries, sell on next close on exits; TP/SL if provided
    prices = df["close"] if "close" in df.columns else df["Close"]
    entries = df["entries"].fillna(False)
    exits = df["exits"].fillna(False)
    pos = 0
    equity = 1.0
    last_entry_price = None
    rets = []
    for i in range(1, len(df)):
        if pos == 0 and entries.iat[i-1]:
            pos = 1
            last_entry_price = prices.iat[i]
        elif pos == 1 and exits.iat[i-1]:
            r = (prices.iat[i] / last_entry_price) - 1.0
            equity *= (1 + r)
            rets.append(r)
            pos = 0
            last_entry_price = None
    total_return = equity - 1.0
    trades = len(rets)
    sortino = (np.mean(rets) / (np.std([r for r in rets if r < 0]) + 1e-9)) if rets else 0.0
    return {"total_return": float(total_return), "trades": int(trades), "sortino": float(sortino)}

def run_backtest(df: pd.DataFrame, exec_cfg: dict | None = None) -> dict:
    if vbt is None:
        return _fallback_backtest(df)
    # Minimal vbtpro wrapper (user can extend)
    entries = df["entries"].fillna(False)
    exits = df["exits"].fillna(False)
    close = df["close"] if "close" in df.columns else df["Close"]
    pf = vbt.Portfolio.from_signals(close, entries, exits)
    stats = pf.stats()
    return {
        "total_return": float(stats.get("Total Return [%]", 0.0) / 100.0),
        "trades": int(pf.trades.count()),
        "sortino": float(stats.get("Sortino Ratio", 0.0))
    }