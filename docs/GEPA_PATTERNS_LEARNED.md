# GEPA (Gradient-free Evolution via Prompt Adjustment) - Key Patterns Learned

## Core Concepts

### 1. GEPA Overview
- **Purpose**: Reflective prompt optimization that evolves prompts based on feedback
- **Mechanism**: Uses LLM reflection to identify why prompts fail and proposes improvements
- **Evolution**: Iteratively mutates prompts based on performance feedback

### 2. Metric Requirements (Critical)
The metric function MUST:
- Accept 5 parameters: `(gold, pred, trace=None, pred_name=None, pred_trace=None)`
- Return `ScoreWithFeedback` object (not tuple!)
- Provide actionable feedback explaining failures

```python
from dspy.teleprompt.gepa.gepa_utils import ScoreWithFeedback

def metric(gold: Example, pred, trace=None, pred_name=None, pred_trace=None):
    # Calculate score
    score = evaluate_performance(pred)
    
    # Generate feedback
    feedback = "Specific feedback about what went wrong and how to improve"
    
    return ScoreWithFeedback(
        score=score,  # float between 0 and 1
        feedback=feedback  # string with actionable insights
    )
```

### 3. Reflection Mechanism
- Uses a separate LLM (reflection_lm) to analyze failures
- Reflection LLM needs higher temperature (0.9-1.0) for creative mutations
- Reflects on batches of failures to identify patterns

### 4. Prompt Evolution Examples

#### From AIME Math Tutorial:
- **Initial**: Basic instruction to solve problem
- **Evolved**: Detailed step-by-step reasoning with specific strategies
- **Result**: 46.7% → 53.3% accuracy improvement

#### From Structured Information Tutorial:
- **Initial**: Simple extraction instructions
- **Evolved**: Detailed categorization rules with edge cases
- **Result**: 72.1% → 84.7% accuracy improvement

#### From Our Trading Strategy:
- **Initial**: "Generate trading strategy based on market conditions"
- **Evolved**: Comprehensive instructions with JSON format requirements, performance metrics, and complexity handling
- **Result**: 50% → 100% validation success rate

## Key Implementation Patterns

### 1. Apple Silicon Compatibility
```python
# CRITICAL: Set before any imports using multiprocessing
import multiprocessing
multiprocessing.set_start_method('fork', force=True)
```

### 2. GEPA Configuration
```python
from dspy import GEPA

optimizer = GEPA(
    metric=metric_with_feedback,  # Must return ScoreWithFeedback
    max_metric_calls=50,           # Budget for optimization
    reflection_lm=reflection_lm,   # Separate LLM for reflection
    reflection_minibatch_size=2,   # Batch size for reflection
    candidate_selection_strategy="pareto",  # Multi-objective optimization
    use_merge=False,              # Disable on Apple Silicon (LLVM issues)
    num_threads=1,                # Single thread for Apple Silicon
    track_stats=True,             # Enable tracking
    seed=42                       # Reproducibility
)
```

### 3. Feedback Generation Pattern
Effective feedback should:
- Be specific about what failed
- Suggest concrete improvements
- Include performance metrics
- Focus on actionable changes

Example:
```python
if sharpe < 0.3:
    feedback += "Poor Sharpe ratio - consider more conservative thresholds"
if win_rate < 0.4:
    feedback += "Low win rate - improve entry timing"
if max_dd > 0.3:
    feedback += "Excessive drawdowns - need stronger risk controls"
```

### 4. Module Structure
```python
class TradingStrategyModule(dspy.Module):
    def __init__(self):
        super().__init__()
        # Use ChainOfThought for reasoning
        self.generate_strategy = dspy.ChainOfThought(StrategySignature)
    
    def forward(self, market_context: str):
        return self.generate_strategy(market_context=market_context)
```

## Optimization Process

### 1. Iteration Flow
1. Evaluate base program
2. Select candidate from Pareto front
3. Reflect on failures with feedback
4. Propose prompt mutations
5. Evaluate mutated program
6. Update Pareto front if improved
7. Repeat until budget exhausted

### 2. Pareto Front Optimization
- Tracks multiple objectives simultaneously
- Maintains set of non-dominated solutions
- Allows exploration of diverse strategies
- Prevents premature convergence

### 3. Reflection Prompts
GEPA generates reflection prompts like:
```
"The prompt [current prompt] led to failures with feedback:
- Example 1: [feedback]
- Example 2: [feedback]
Propose an improved prompt that addresses these issues."
```

## Best Practices

### 1. Training Data
- Provide diverse examples covering edge cases
- Include both successful and challenging scenarios
- Balance dataset to avoid bias

### 2. Metric Design
- Score should reflect true performance
- Feedback should be educational, not just evaluative
- Consider multiple objectives (Sharpe, drawdown, win rate)

### 3. Optimization Budget
- Start small (50-100 calls) for testing
- Scale up (500-1000) for production optimization
- Monitor convergence to avoid overfitting

### 4. Prompt Evolution Tracking
```python
# Extract and save optimized prompts
prompts = {}
for name, predictor in optimized_module.named_predictors():
    if hasattr(predictor, 'signature'):
        prompts[name] = str(predictor.signature)

# Save for analysis
with open('optimized_prompts.json', 'w') as f:
    json.dump(prompts, f, indent=2)
```

## Common Pitfalls and Solutions

### 1. Metric Return Type Error
**Problem**: Returning tuple instead of ScoreWithFeedback
**Solution**: Always use `ScoreWithFeedback(score=..., feedback=...)`

### 2. Apple Silicon LLVM Crash
**Problem**: RuntimeDyldMachOAArch64.h assertion failure
**Solution**: Set multiprocessing to 'fork' before imports

### 3. No Prompt Evolution
**Problem**: Prompts don't evolve beyond base
**Solution**: Ensure feedback is specific and actionable

### 4. Import Errors
**Problem**: Can't import GEPA from dspy.teleprompt
**Solution**: Ensure DSPy 3.0.3+ is properly installed

## Results Achieved

### Our Trading Strategy Optimization:
- **Validation Success**: 50% → 100%
- **Prompt Complexity**: Simple instruction → Comprehensive JSON specification
- **Key Addition**: Domain-specific requirements (Sharpe > 1.5, win rate > 50%, drawdown < 8%)

### Key Improvements in Evolved Prompts:
1. Added specific JSON formatting requirements
2. Included performance metric targets
3. Added complexity handling for extreme volatility
4. Specified exact output structure with all required fields
5. Added validation rules for strategy parameters

## Next Steps for Trading System

1. **Increase optimization budget** to 500+ metric calls
2. **Add more diverse market conditions** to training set
3. **Implement multi-objective feedback** (Sharpe, Sortino, Calmar ratios)
4. **Track prompt evolution** across different market regimes
5. **Create domain-specific reflection prompts** for trading strategies
6. **Test on out-of-sample data** to verify generalization