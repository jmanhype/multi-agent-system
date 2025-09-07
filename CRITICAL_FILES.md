# Critical Root Files Documentation

## Core Python Files (Root Level)

### 1. **run_gepa_trading.py** 
- **Purpose**: Main entry point for running GEPA optimization and trading system
- **Key Functions**: Runs complete pipeline (GEPA → Trading)
- **Dependencies**: All lib modules, DSPy, VectorBT

### 2. **test_gepa_enhanced.py**
- **Purpose**: Enhanced GEPA optimization with learned patterns
- **Key Features**: 
  - Auto budget calculation (light/medium/heavy)
  - Pareto optimization
  - Reflection with GPT-4o
- **Budget**: 396 metric calls (light), 710 (medium)

### 3. **test_gepa_three_gulfs.py**
- **Purpose**: GEPA with Three Gulfs Framework implementation
- **Key Components**:
  - GEPAComprehensionLogger
  - GEPASpecificationMetric
  - GEPAGeneralizationHandler
- **Volatility Testing**: Tests across 0.7% to 15% volatility

### 4. **test_10pct_volatility.py**
- **Purpose**: Direct test of 10% daily volatility scenario
- **Validates**: System handling of extreme volatility
- **Key Findings**: No JSON errors, handles extreme volatility correctly

### 5. **test_volatility_scenarios.py**
- **Purpose**: Test system across different volatility regimes
- **Scenarios**: Ultra-low (<1%), Low (1-2%), Medium (2-5%), High (5-10%), Extreme (>10%)

## Configuration Files

### 6. **.env**
- **Purpose**: Environment variables and API keys
- **Contains**: OpenAI API key, other service credentials
- **Security**: Should never be committed to git

### 7. **CLAUDE.md**
- **Purpose**: Operating guide for Claude Code
- **Key Principles**:
  - LLM offline only (research lane)
  - Black-box separation (.claude/ = control plane; lib/ = implementation)
  - Append-only evidence (logs/*.jsonl; db/metrics.db)

### 8. **README.md**
- **Purpose**: Project documentation and setup instructions
- **Contains**: Installation, usage, architecture overview

### 9. **requirements.txt**
- **Purpose**: Python package dependencies
- **Critical Packages**: dspy, vectorbtpro, pandas, numpy==1.23.5, numba==0.56.4

### 10. **.gitignore**
- **Purpose**: Git exclusion rules
- **Excludes**: .env, logs, data files, __pycache__

## Directory Structure

### Core Directories:
- **lib/** - Core implementation modules
  - evaluation/ - Three Gulfs implementation
  - research/ - Backtesting and strategy generation
  - data/ - DEX data adapters
  - execution/ - Trading execution
  
- **config/** - Configuration files
  - benchmarks.json - Performance benchmarks
  - best_strategy.json - Current best strategy
  - prompts/ - DSPy prompt templates

- **data/** - Data storage
  - models/ - Saved models and optimization results
  - gepa_logs/ - GEPA optimization logs

- **logs/** - Execution logs
  - runs.jsonl - Append-only run history
  - *.log - Various system logs

- **artifacts/** - Production artifacts
  - winner.json - Production strategy (PR gate)

- **docs/** - Documentation
  - GEPA_PATTERNS_LEARNED.md - Learned optimization patterns
  - Three Gulfs documentation

- **db/** - Database storage
  - metrics.db - Performance metrics database

- **.claude/** - Claude Code configuration
  - hooks/ - Automation hooks
  - mcp/ - MCP configuration
  - commands/ - Custom commands

## Log Files (Root Level)

### 11. **gepa_optimization.log**
- **Purpose**: Full GEPA optimization trace
- **Contains**: Iteration details, scores, prompt evolution

### 12. **gepa_monitoring.log**  
- **Purpose**: Real-time monitoring of GEPA execution
- **Tracks**: Failures, scores, NumPy/VectorBT issues

### 13. **trading_system.log**
- **Purpose**: Trading system execution log
- **Contains**: Trade signals, execution status

### 14. **gepa_auto_budget.log**
- **Purpose**: GEPA with auto budget calculation results
- **Shows**: 396 metric calls for light budget

## Critical Dependencies

### Python Environment:
- Python 3.10.14
- NumPy 1.23.5 (for VectorBT compatibility)
- Numba 0.56.4 (for VectorBT compatibility)
- VectorBT Pro 2025.7.27
- DSPy 3.0.3

### Key Integrations:
- OpenAI GPT-4o-mini (strategy generation)
- GPT-4o (reflection model)
- DEX data via pickle files
- VectorBT Pro for backtesting

## Workflow Files

### Research Lane (Offline):
1. test_gepa_enhanced.py → Optimize prompts
2. test_gepa_three_gulfs.py → Validate with Three Gulfs
3. test_10pct_volatility.py → Test extreme conditions

### Production Lane (Online):
1. run_gepa_trading.py → Full pipeline
2. artifacts/winner.json → Production strategy (PR gate)
3. config/benchmarks.json → Performance targets

## Critical File Relationships

```
.env → API Keys
    ↓
test_gepa_enhanced.py → GEPA Optimization
    ↓
lib/evaluation/* → Three Gulfs Framework
    ↓
lib/research/backtester_vbt.py → Backtesting
    ↓
config/best_strategy.json → Best Strategy
    ↓
artifacts/winner.json → Production (via PR)
```

## File Status Indicators

- ✅ **Working**: All test files, GEPA optimization
- ✅ **Fixed**: NumPy/VectorBT compatibility 
- ✅ **Updated**: Auto budget calculation
- ⚠️ **Monitor**: Disk space for logs
- 🔒 **Protected**: .env, artifacts/winner.json (PR gate)