# Operating Guide (Claude Code)

## Principles
- **LLM offline only** (research lane). Live loop is deterministic.
- **Black-box separation**: .claude/ = control plane; lib/ = implementation.
- **Append-only evidence**: logs/*.jsonl; db/metrics.db.
- **PR gate**: promotion to `artifacts/winner.json` only via PR.

## Daily Ops (TL;DR)
- 06:00 research-loop.md → new candidates; deterministic eval; proof → logs/runs.jsonl
- If winner beats `config/benchmarks.json`, merge PR (updates `artifacts/winner.json`).
- crypto-trader.md runs each 5m (paper or live). Live requires PIN via `hooks/guard_approve.sh`.

## Safety
- `hooks/circuit_breaker.sh` flips to paper on risk/latency errors.
- `hooks/kill_switch.sh` hard stops.

---

## DataAgent Usage

### Basic Analysis
```python
from lib.agents.data_agent import DataAgent
from lib.agents.data_agent.contracts.request import AnalysisRequest
import uuid

agent = DataAgent()
request = AnalysisRequest(
    request_id=str(uuid.uuid4()),
    intent="Analyze Q1 2021 Arizona sales; trends + charts",
    data_sources=[{
        "type": "sql",
        "connection_string": "postgresql://localhost/sales_db"
    }],
    deliverables=["tables", "charts", "summary"],
    constraints={"row_limit": 100000, "timeout_seconds": 30}
)

response = agent.analyze(request)
print(f"Status: {response.status}")
print(f"Artifacts: {len(response.artifacts)}")
print(f"Time: {response.metrics.execution_time_seconds:.2f}s")
```

### Safety Guardrails
```python
request = AnalysisRequest(
    request_id=str(uuid.uuid4()),
    intent="Show customer contact information",
    data_sources=[{"type": "sql", "connection_string": "..."}],
    deliverables=["tables"],
    policy={"blocked_patterns": ["*.email", "*.phone", "*.ssn"]}
)

response = agent.analyze(request)
if response.status == "failed" and response.error.error_type == "policy_violation":
    print(f"Blocked: {response.error.error_message}")
```

### Recipe Reuse
```python
request1 = AnalysisRequest(
    request_id=str(uuid.uuid4()),
    intent="Analyze Q1 sales trends",
    data_sources=[{"type": "sql", "schema_fingerprint": "abc123..."}]
)
response1 = agent.analyze(request1)

request2 = AnalysisRequest(
    request_id=str(uuid.uuid4()),
    intent="Analyze Q2 sales trends",
    data_sources=[{"type": "sql", "schema_fingerprint": "abc123..."}]
)
response2 = agent.analyze(request2)
print(f"Recipe reused: {response2.metrics.recipe_used}")
```

### Audit Trail
```bash
grep "request_id.*550e8400" logs/data_agent_runs.jsonl | jq .

python -c "
from lib.agents.data_agent.audit.merkle_log import verify_chain
print('Chain valid:', verify_chain('logs/data_agent_runs.jsonl'))
"
```

### Performance Validation
Run integration tests with target <30s completion:
```bash
pytest tests/integration/test_basic_analysis.py -v
pytest tests/integration/test_orchestrator_integration.py -v
```
