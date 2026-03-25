# multi-agent-system

A trading strategy optimizer that uses DSPy's GEPA (Gradient-free Evolution via Prompt Adjustment) to generate and backtest trading strategies across different volatility regimes. Validates strategies using the Three Gulfs Framework.

## What it does

1. Feeds market context to an LLM via a DSPy `ChainOfThought` module
2. LLM generates a JSON trading strategy (entry/exit rules, stops, position sizing)
3. Strategy is backtested with VectorBT against historical data
4. GEPA evolves the prompt over 33-66+ iterations to maximize a composite score (Sharpe, win rate, drawdown)
5. Three Gulfs analysis validates the result

```bash
make setup-uv && make fix-numpy && make optimize
```

## GEPA budget tiers

| Budget | LLM calls | Full evaluations | Typical runtime |
|--------|-----------|-----------------|-----------------|
| Light | ~396 | 33 | ~5 min |
| Medium | ~710 | 59 | ~15 min |
| Heavy | 800+ | 66+ | ~30 min |

## Volatility adaptation

The system adjusts strategy parameters based on market conditions:

| Regime | Daily range | Strategy type | Stop loss | Take profit |
|--------|------------|---------------|-----------|-------------|
| Ultra low | <1% | Mean reversion | 0.5-1.5% | 1-3% |
| Low | 1-2% | Mean rev/breakout | 1-2% | 2-5% |
| Medium | 2-5% | Momentum/breakout | 2-5% | 3-8% |
| High | 5-10% | Momentum | 3-7% | 5-12% |
| Extreme | 10-20% | Momentum/ML | 5-10% | 8-20% |
| Crisis | >20% | ML-based | 8-10% | 15-20% |

## Three Gulfs Framework

Adapted from Hamel Husain and Shreya Shankar's evaluation framework:

| Gulf | Gap | Implementation |
|------|-----|----------------|
| Comprehension | Developer vs. data | Append-only logs of every evaluation |
| Specification | Developer vs. LLM | Explicit scoring criteria in DSPy signatures |
| Generalization | Data vs. LLM | Testing across 6 volatility regimes |

## Score interpretation

| Range | Meaning |
|-------|---------|
| 0.80+ | Strategy passes backtesting validation |
| 0.60-0.79 | Functional, needs refinement |
| 0.40-0.59 | Suboptimal |
| 0.25 | Backtest failure (usually VectorBT/NumPy issue) |
| 0.00 | JSON structure error from LLM |

## Performance targets

| Metric | Target | Typical result |
|--------|--------|---------------|
| Sharpe ratio | >1.0 | 1.5-2.0 |
| Win rate | >45% | 55-60% |
| Max drawdown | <25% | 15-25% |
| Risk/reward | >1.5 | 2.0-3.0 |

These numbers come from backtests on historical data. Live trading performance will differ.

## Requirements

```bash
# .env
OPENAI_API_KEY=sk-...       # Required (GPT-4o-mini for strategy generation)
ANTHROPIC_API_KEY=...        # Optional
VECTOR_BT_KEY=...            # VectorBT Pro license (optional)
```

NumPy must be pinned to 1.23.5 for VectorBT compatibility. `make fix-numpy` handles this.

## Commands

```bash
make optimize          # Light budget
make optimize-medium   # Medium budget
make optimize-heavy    # Heavy budget
make volatility        # Test 10% daily volatility scenario
make scenarios         # Test all 6 volatility regimes
make three-gulfs       # Run Three Gulfs analysis
make pipeline          # Full optimization + trading flow
```

## Project layout

```
gepa_optimizer.py           # Main GEPA optimization loop
gepa_three_gulfs.py         # Three Gulfs validation
volatility_analyzer.py      # Stress testing
volatility_scenarios.py     # All volatility regime tests
main.py                     # Trading pipeline entry point
lib/
  evaluation/               # Three Gulfs implementations
  research/                 # Backtest wrapper
  data/                     # Market data adapters (DEX)
config/                     # Strategy configurations
artifacts/                  # Production strategies (PR-gated)
logs/                       # Append-only evaluation logs
```

## Production safety

Strategies only reach production through a PR gate:
`config/best_strategy.json` -> PR review -> `artifacts/winner.json`

Additional safeguards: circuit breaker on high risk/latency, kill switch, paper trading by default, PIN required for live trading.

## Limitations

- This is a research system. Backtested returns do not predict live performance.
- GEPA optimization requires an OpenAI API key and generates hundreds of LLM calls per run.
- VectorBT Pro compatibility issues with modern NumPy versions require pinning to 1.23.5.
- The `.claude/` directory contains 50+ agent configuration files for an optional multi-agent framework (Claude-Flow) that is not required for core functionality.
- Market data adapter currently supports DEX sources only.
- No automated test suite.

## License

MIT
