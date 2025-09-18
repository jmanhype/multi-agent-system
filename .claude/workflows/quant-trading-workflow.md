# Quant Trading Workflow

## Overview
Automated trading system with offline LLM research and deterministic execution

## Workflow Steps

### 1. Initial Setup
```bash
# Run setup helper
./.claude/helpers/quant-setup.sh

# Configure API keys
vim .env
```

### 2. Research Phase (Offline)
```bash
# Run full research pipeline
python -m lib.research.orchestrate --mode full

# Quick test with pretrained
python -m lib.research.orchestrate --seed-pretrained --mode quick
```

### 3. Backtest Validation
```bash
# Validate winning strategy
python -m lib.research.backtester_vbt \
  --strategy artifacts/winner.json \
  --data data/historical/*.parquet

# Check metrics
cat artifacts/winner.json | jq '.metrics'
```

### 4. Paper Trading
```bash
# Start paper trading
python -m lib.trading.orchestrator --mode paper

# Monitor performance
python -m lib.trading.monitor metrics --period 24h
```

### 5. Live Trading (PIN Required)
```bash
# Pre-flight checks
./.claude/hooks/circuit_breaker.sh

# Start live trading
python -m lib.trading.orchestrator --mode live --confirm
# Enter PIN when prompted
```

## Safety Checks

### Circuit Breaker
- Daily loss: -$100
- Max drawdown: -20%
- Consecutive losses: 5

### Risk Limits
- Position size: $62.50
- Bankroll percentage: 25%
- Symbol whitelist: BTC, ETH

### Time Restrictions
- No trading 3am-7am UTC
- No weekend trading

## Monitoring

### Real-time Metrics
```bash
# View positions
python -m lib.trading.monitor positions

# Check risk status
python -m lib.risk.manager status

# View trade journal
tail -f logs/trades.jsonl | jq
```

### Emergency Controls
```bash
# Kill switch
python -m lib.trading.orchestrator --kill

# Reset circuit breaker
rm .circuit_breaker_triggered
```

## Research Iteration

### Update Strategy
```bash
# Re-run research with new data
python -m lib.research.orchestrate \
  --start 2024-01-01 \
  --end 2024-12-31

# Compare strategies
python -m lib.research.compare \
  artifacts/winner.json \
  artifacts/strategy_*.json
```

### GEPA Evolution
```bash
# Evolve existing winner
python -m lib.research.evolve \
  --base artifacts/winner.json \
  --generations 10
```

## Audit Trail

### Verify Trades
```bash
# Check SHA256 proofs
python -m lib.audit.verify logs/trades.jsonl

# Export metrics
sqlite3 db/metrics.db ".mode csv" \
  "SELECT * FROM trades" > exports/trades.csv
```

## Troubleshooting

### Common Issues

1. **Circuit breaker triggered**
   ```bash
   # Check trigger reason
   cat .circuit_breaker_triggered
   # Reset after fixing
   rm .circuit_breaker_triggered
   ```

2. **API key errors**
   ```bash
   # Test exchange connection
   python -c "import ccxt; print(ccxt.binance().fetch_ticker('BTC/USDT'))"
   ```

3. **Backtest failures**
   ```bash
   # Run with debug
   python -m lib.research.backtester_vbt --debug
   ```

## Performance Optimization

### Parallel Backtesting
```bash
# Increase workers
export BACKTEST_WORKERS=8
python -m lib.research.orchestrate
```

### Cache Historical Data
```bash
# Pre-download data
python -m lib.data.download \
  --symbols BTC/USDT,ETH/USDT \
  --timeframe 5m \
  --days 365
```