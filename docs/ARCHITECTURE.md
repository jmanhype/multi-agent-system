# System Architecture - Quant LLM Research System

## Clean Architecture Overview

### 1. **Prompt Evolution (GEPA)**
- **Purpose**: Evolve prompts that generate better strategies
- **Location**: `lib/research/dspy_pipeline/dspy_gepa_integration.py`
- **When Used**: During research phase to learn HOW to generate strategies
- **Technology**: `dspy.GEPA` with reflection and feedback
- **Output**: Optimized prompts stored in `config/prompts/`

### 2. **Strategy Generation (DSPy)**
- **Purpose**: Generate trading strategy candidates
- **Location**: `lib/research/dspy_pipeline/proposer.py`
- **When Used**: After prompt optimization, generate actual strategies
- **Technology**: DSPy with Chain-of-Thought reasoning
- **Output**: Strategy configurations with parameters

### 3. **Parameter Optimization (Grid Search)**
- **Purpose**: Fine-tune strategy parameters
- **Location**: `lib/research/backtester_vbt.py`
- **When Used**: After strategy generation, optimize specific parameters
- **Technology**: VectorBT Pro grid search
- **Output**: Optimal parameters for each strategy

### 4. **Orchestration**
- **Purpose**: Coordinate the entire research pipeline
- **Location**: `lib/research/orchestrator.py`
- **Flow**:
  1. Initialize with GEPA optimizer
  2. Generate initial candidates
  3. Run GEPA prompt optimization
  4. Generate optimized strategies
  5. Run grid search for parameter tuning
  6. Evaluate and save winners

## Data Flow

```
1. Market Data → GEPA Training Examples
2. GEPA → Optimized Prompts
3. Optimized Prompts → Strategy Generation
4. Generated Strategies → Grid Search
5. Grid Search → Optimal Parameters
6. Backtest Results → Database Storage
7. Database → Cross-Asset Analysis
```

## Key Components

### Research Pipeline
- `orchestrator.py` - Main coordinator
- `dspy_gepa_integration.py` - GEPA prompt evolution
- `proposer.py` - Strategy generation
- `backtester_vbt.py` - Backtesting and grid search

### Storage & Analysis
- `lib/storage/db_manager.py` - SQLite database management
- `lib/analysis/trade_analytics.py` - Trade analysis tools
- `lib/utils/prompt_manager.py` - Centralized prompt management

### Configuration
- `config/prompts.yaml` - Centralized prompts
- `config/prompts/` - GEPA-optimized prompts
- `config/benchmarks.json` - Performance benchmarks
- `config/settings.local.json` - System settings

## Clean Separation of Concerns

1. **Prompt Optimization**: GEPA learns HOW to describe strategies
2. **Strategy Generation**: DSPy creates strategies from prompts
3. **Parameter Tuning**: Grid search finds optimal parameters
4. **Backtesting**: VectorBT Pro evaluates performance
5. **Storage**: SQLite tracks all results
6. **Analysis**: Tools for cross-asset comparison

## No Redundancy

- ✅ Single source for prompt evolution (GEPA)
- ✅ Single source for parameter optimization (Grid Search)
- ✅ Clear separation between prompt and parameter optimization
- ✅ No duplicate evolution mechanisms

## RiR/MENTAT Integration (Future)

While DSPy includes GEPA for prompt evolution, the full MENTAT system would add:
- Multi-rollout generation (K samples per prompt)
- MLP aggregator for combining rollouts
- CCC/NMSE metrics for regression tasks

Currently, we use the GEPA component which is the core of MENTAT's Phase 1.