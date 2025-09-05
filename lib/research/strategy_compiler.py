import pandas as pd
from ..trading.indicators import ema, rsi

def compile_strategy(dsl: dict):
    reg = dsl.get("regime", {})
    ent = dsl.get("entry", {})
    ext = dsl.get("exit", {})
    tp = dsl.get("risk", {}).get("tp", None)
    sl = dsl.get("risk", {}).get("sl", None)

    fast = int(reg.get("fast", 20)); slow = int(reg.get("slow", 50))
    ent_th = float(ent.get("threshold", 30)); ex_th = float(ext.get("threshold", 70))

    def _ensure_close(df: pd.DataFrame):
        for k in ("close","Close","c","dex_price"): 
            if k in df.columns: return df[k]
        raise ValueError("No close price column present")

    def fn(df: pd.DataFrame) -> pd.DataFrame:
        c = _ensure_close(df)
        efast, eslow = ema(c, fast), ema(c, slow)
        rrsi = rsi(c, 14)
        regime_up = efast > eslow if reg.get("direction","up") == "up" else efast < eslow
        entries = regime_up & (rrsi < ent_th)
        exits = (rrsi > ex_th)
        out = df.copy()
        out["entries"] = entries.fillna(False)
        out["exits"] = exits.fillna(False)
        if tp is not None: out["tp"] = float(tp)
        if sl is not None: out["sl"] = float(sl)
        return out

    return fn