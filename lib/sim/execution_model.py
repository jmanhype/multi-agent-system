from typing import NamedTuple

class ExecutionConfig(NamedTuple):
    fees_maker_bps: float
    fees_taker_bps: float
    slippage_k: float
    latency_ms: int
    min_qty: float
    tick: float

def apply_execution(price_series, orders, cfg: ExecutionConfig):
    # Placeholder; extend with fills, partials, and rounding.
    return orders