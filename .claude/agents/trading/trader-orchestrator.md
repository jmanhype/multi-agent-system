# Trader Orchestrator (deterministic 5m loop)
Inputs: config/settings.local.json, artifacts/winner.json

Steps:
1. ccxt-exchange.fetchOHLCV(symbol, timeframe, limit=N)
2. features-extractor (or compiler computes features)
3. Load DSL → lib.research.strategy_compiler.compile_strategy(dsl)(df)
4. ccxt-exchange.fetchTicker(symbol) for mid/best price
5. risk-manager → enforce per_trade_cap_usd + atr_cap_pct + whitelist
6. If mode=live → hooks/guard_approve.sh (PIN)
7. ccxt-exchange.createOrder (or paper)
8. journal.append → logs/trades.jsonl
9. metrics.write → db/metrics.db