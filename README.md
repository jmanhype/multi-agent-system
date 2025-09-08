# GEPA Multi-Agent Trading System

> Advanced trading system using DSPy's GEPA (Gradient-free Evolution via Prompt Adjustment) optimization with the Three Gulfs Framework for robust strategy generation across volatile markets.

## 🚀 Quick Start

```bash
# Clone and setup
git clone <repo>
cd multi-agent-system

# Install with uv (recommended)
make setup-uv
make fix-numpy  # Fix VectorBT compatibility

# Or traditional pip
make install
make fix-numpy

# Run optimization
make optimize  # Light budget (396 calls, ~5 min)
```

## 📖 Overview

This system implements a sophisticated trading strategy optimizer that:
- **Learns** from market conditions using GEPA's reflective prompt evolution
- **Adapts** to volatility regimes from 0.7% to 20% daily movement
- **Validates** strategies using the Three Gulfs Framework
- **Backtests** with VectorBT Pro for realistic performance metrics

### Key Innovation: Three Gulfs Framework

Based on Hamel Husain & Shreya Shankar's framework, we bridge three critical gaps:

1. **Gulf of Comprehension** (Developer ↔ Data): Comprehensive logging of every evaluation
2. **Gulf of Specification** (Developer ↔ LLM): Precise, explicit evaluation criteria
3. **Gulf of Generalization** (Data ↔ LLM): Robust handling across volatility regimes

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│           RESEARCH LANE (Offline)           │
├─────────────────────────────────────────────┤
│  gepa_optimizer.py                          │
│    ↓ GEPA Evolution (396-800+ calls)        │
│  gepa_three_gulfs.py                        │
│    ↓ Validation & Analysis                  │
│  volatility_analyzer.py                     │
│    ↓ Stress Testing (10% daily vol)         │
├─────────────────────────────────────────────┤
│          PRODUCTION LANE (Online)           │
├─────────────────────────────────────────────┤
│  main.py → artifacts/winner.json            │
│    ↓ (PR Gate Required)                     │
│  Live Trading System                        │
└─────────────────────────────────────────────┘
```

## 💡 Core Concepts

### GEPA Optimization
- **Auto Budget**: Calculates optimal iterations based on dataset size
  - Light: ~396 calls (33 full evals) - Quick experiments
  - Medium: ~710 calls (59 full evals) - Balanced optimization
  - Heavy: ~800+ calls (66+ full evals) - Thorough optimization

### Volatility Adaptation
The system automatically adjusts strategies for different market conditions:

| Volatility | Range | Strategy Type | Stop Loss | Take Profit |
|------------|-------|--------------|-----------|-------------|
| Ultra Low | <1% | Mean Reversion | 0.5-1.5% | 1-3% |
| Low | 1-2% | Mean Rev/Breakout | 1-2% | 2-5% |
| Medium | 2-5% | Momentum/Breakout | 2-5% | 3-8% |
| High | 5-10% | Momentum | 3-7% | 5-12% |
| Extreme | 10-20% | Momentum/ML | 5-10% | 8-20% |
| Crisis | >20% | ML-based | 8-10% | 15-20% |

## 📚 Usage Guide

### Basic Operations

```bash
# Run GEPA optimization with different budgets
make optimize          # Light budget (fastest)
make optimize-medium   # Balanced
make optimize-heavy    # Most thorough

# Test specific scenarios
make volatility       # Test 10% daily volatility
make scenarios        # Test all volatility regimes
make three-gulfs      # Run Three Gulfs analysis

# Full pipeline
make pipeline         # Complete optimization → trading flow
```

### Environment Variables

```bash
# Required in .env
OPENAI_API_KEY=sk-...       # For GPT-4o-mini generation
ANTHROPIC_API_KEY=...        # Optional: For Claude models

# Optional overrides
GEPA_BUDGET=medium           # Control optimization budget
VECTOR_BT_KEY=...            # VectorBT Pro license
```

### Advanced Usage

```python
# Custom optimization with specific volatility
from gepa_optimizer import create_enhanced_metric
from lib.data.dex_adapter import dex_adapter

# Load your data
df = dex_adapter.get_candles('BTC/USDT', '5m', 1000)

# Create metric with custom backtest
metric = create_enhanced_metric(your_backtest_func)

# Run GEPA with custom settings
optimizer = GEPA(
    auto='medium',
    metric=metric,
    reflection_lm=your_model
)
```

## 🛠️ Development

### File Structure

```
.
├── Core Files
│   ├── gepa_optimizer.py      # Main GEPA optimization
│   ├── gepa_three_gulfs.py    # Three Gulfs validation
│   ├── volatility_analyzer.py # 10% volatility test
│   ├── volatility_scenarios.py # All volatility regimes
│   └── main.py                 # Trading pipeline
│
├── lib/
│   ├── evaluation/       # Three Gulfs implementation
│   │   ├── gepa_comprehension_logger.py
│   │   ├── gepa_specification_metric.py
│   │   └── gepa_generalization_handler.py
│   ├── research/         # Backtesting & generation
│   └── data/            # Market data adapters
│
├── config/              # Configurations
├── artifacts/           # Production strategies (PR-gated)
├── logs/               # Append-only evidence
└── .claude/            # Multi-agent framework (optional)
```

### Common Issues & Solutions

#### NumPy/VectorBT Compatibility
```bash
# If you see: "AttributeError: _ARRAY_API not found"
make fix-numpy  # Downgrades to compatible versions
```

#### Disk Space Issues
```bash
# GEPA logs can grow large
make clean-logs  # Archive old logs
```

#### Low Scores (0.25)
This usually indicates backtest failures. Check:
1. VectorBT is properly installed
2. NumPy version is 1.23.5
3. Market data is loading correctly

## 🎯 Tips for Success

### 1. Start with Light Budget
```bash
GEPA_BUDGET=light make optimize  # ~5 minutes
```
Validate your setup works before running longer optimizations.

### 2. Monitor in Real-Time
```bash
make monitor  # Watch scores and iterations
```

### 3. Understand Your Scores

- **0.80+**: Excellent strategy, ready for validation
- **0.60-0.79**: Good baseline, may need refinement
- **0.40-0.59**: Functional but suboptimal
- **0.25**: Backtest failure (check VectorBT)
- **0.00**: JSON structure error

### 4. Use Three Gulfs for Debugging
```bash
make three-gulfs  # Comprehensive analysis
```
This shows exactly where strategies fail: structure, parameters, coherence, adaptation, or performance.

### 5. Test Extreme Conditions
```bash
make volatility  # Always test 10% volatility
```
If your strategy survives 10% daily volatility, it's robust.

## 📊 Performance Benchmarks

Current best results (as of last run):
- **Sharpe Ratio**: 1.5-2.0 (target: >1.0)
- **Win Rate**: 55-60% (target: >45%)
- **Max Drawdown**: 15-25% (target: <25%)
- **Risk/Reward**: 2.0-3.0 (target: >1.5)

## 🔒 Security & Production

### PR Gate for Production
Strategies only reach production through:
```
config/best_strategy.json → PR Review → artifacts/winner.json
```

### Safety Mechanisms
- Circuit breaker on high risk/latency
- Kill switch for emergency stops
- Paper trading mode by default
- PIN required for live trading

## 🤖 Multi-Agent Framework (Optional)

This system can be enhanced with Claude-Flow's multi-agent orchestration for:
- **Swarm Intelligence**: 64 specialized AI agents across 16 categories
- **Consensus Protocols**: Raft, Byzantine, CRDT, Gossip implementations
- **GitHub Integration**: PR management, issue tracking, release automation
- **Performance Monitoring**: Real-time metrics and bottleneck analysis

See `.claude/` directory for advanced multi-agent configurations.

### Activating Multi-Agent System

```bash
# Install Claude-Flow Alpha globally
npm install -g claude-flow@alpha

# Initialize in your project
npx claude-flow@alpha init --force

# Quick AI coordination
npx claude-flow@alpha swarm "optimize trading strategy" --claude

# Full hive-mind system (complex projects)
npx claude-flow@alpha hive-mind wizard
```

## 🤝 Contributing

1. Run optimizations locally: `make optimize`
2. Validate with Three Gulfs: `make three-gulfs`
3. Test extreme volatility: `make volatility`
4. Submit PR with evidence in logs/

## 📝 License

MIT - See LICENSE file

## 🙏 Acknowledgments

- DSPy team for GEPA optimizer
- Hamel Husain & Shreya Shankar for Three Gulfs Framework
- VectorBT Pro for backtesting engine
- Claude-Flow v2.0.0 Alpha for multi-agent orchestration capabilities

---

**Note**: This is a research system. Always validate strategies thoroughly before live trading. The system is designed for safety-first operation with multiple validation gates.