# Risk Manager
- Deny if symbol ∉ whitelist.
- Deny if ATR% > config/risk.json.atr_cap_pct.
- Clamp notional to per_trade_cap_usd.
- Emit {allowed: bool, qty_usd, reason?}.