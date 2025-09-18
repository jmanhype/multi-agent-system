# Research Workflow

## DSPy/GEPA Strategy Evolution Pipeline

### Phase 1: Data Preparation
```bash
# Download historical data
python -m lib.data.download --symbols BTC/USDT --days 365

# Convert to parquet
python -m lib.data.convert --format parquet
```

### Phase 2: Initial Generation
```bash
# Generate candidates with DSPy
python -m lib.research.dspy_pipeline.proposer \
  --n-candidates 20 \
  --config config/settings.local.json
```

### Phase 3: Parallel Backtesting
```bash
# Run backtests
python -m lib.research.parallel_backtest \
  --strategies data/strategies/candidates.json \
  --workers 4
```

### Phase 4: GEPA Evolution
```bash
# Evolve strategies
python -m lib.research.dspy_pipeline.evolver \
  --population data/strategies/candidates.json \
  --generations 5 \
  --mutation-rate 0.1
```

### Phase 5: Winner Selection
```bash
# Select best strategy
python -m lib.research.select_winner \
  --results data/strategies/evolved.json \
  --output artifacts/winner.json
```

## Using Pretrained Models

### Load Optimization Bundle
```bash
python scripts/load_pretrained.py
```

### Seed DSPy with Pretrained
```bash
python -m lib.research.orchestrate \
  --seed-pretrained \
  --pretrained-count 10
```

## Advanced Research

### Market Regime Analysis
```bash
python -m lib.research.regime_analysis \
  --data data/historical/*.parquet \
  --output artifacts/regimes.json
```

### Strategy Comparison
```bash
python -m lib.research.compare_strategies \
  artifacts/winner.json \
  data/strategies/pretrained_dspy.json
```

### Performance Attribution
```bash
python -m lib.research.attribution \
  --strategy artifacts/winner.json \
  --trades logs/trades.jsonl
```