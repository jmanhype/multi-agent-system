# Quickstart: DataAgent End-to-End Test

**Feature**: 001-build-an-autonomous  
**Date**: 2025-09-27  
**Purpose**: Validate user stories from spec.md through executable integration tests

---

## Prerequisites

- Python 3.11+
- pytest installed (`pip install pytest`)
- PostgreSQL database with sample sales data (or CSV files)
- Environment variables:
  - `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` (for Planner/Actor LLMs)
  - `DATABASE_URL` (for SQL data sources)

---

## Test Scenario 1: Basic Analysis with SQL Data Source

**User Story** (from spec.md lines 52-54):
> Given a user provides the intent "Analyze Q1 2021 Arizona sales; trends + charts"  
> When the DataAgent processes this request  
> Then the system returns monthly sales aggregates, a trend chart, a summary report, and a complete audit log

### Setup

```bash
# Create test database
createdb data_agent_test

# Load sample sales data
psql data_agent_test < tests/fixtures/sample_sales.sql
```

### Test Execution

```python
# tests/integration/test_basic_analysis.py
import pytest
import uuid
from lib.agents.data_agent import DataAgent
from lib.agents.data_agent.contracts.request import AnalysisRequest
import os

def test_q1_arizona_sales_analysis():
    """Test FR-001 through FR-006: Basic analysis workflow"""
    
    # Arrange
    agent = DataAgent()
    request_id = str(uuid.uuid4())
    
    request = AnalysisRequest(
        request_id=request_id,
        intent="Analyze Q1 2021 Arizona sales; trends + charts",
        data_sources=[{
            "type": "sql",
            "connection_string": os.getenv("DATABASE_URL"),
            "schema_fingerprint": "a3f5b8c9e7d2f1a4b6c8e0d3f5a7b9c1e3d5f7a9b1c3e5d7f9a1b3c5e7d9f1a3"
        }],
        deliverables=["tables", "charts", "summary"],
        constraints={
            "row_limit": 100000,
            "timeout_seconds": 30
        }
    )
    
    # Act
    response = agent.analyze(request)
    
    # Assert: FR-005 (returns artifacts)
    assert response.status == "completed"
    assert len(response.artifacts) >= 2  # At least table + chart
    
    # Assert: FR-006 (audit log exists)
    assert response.audit_log_ref.startswith("logs/data_agent_runs.jsonl")
    
    # Assert: Artifacts have correct types
    artifact_types = {a.artifact_type for a in response.artifacts}
    assert "table" in artifact_types
    assert "chart" in artifact_types
    
    # Assert: FR-043 (completes within 30 seconds)
    assert response.metrics.execution_time_seconds < 30
    
    # Assert: Summary contains key findings
    assert len(response.summary.key_findings) > 0
    assert "Q1 2021" in response.summary.insights
    
    # Assert: FR-036 (artifacts have SHA256 hashes)
    for artifact in response.artifacts:
        assert len(artifact.content_hash) == 64  # SHA256 hex
        assert all(c in "0123456789abcdef" for c in artifact.content_hash)
    
    print(f"✅ Test passed: {response.metrics.execution_time_seconds:.2f}s")
```

**Expected Output**:
```
✅ Test passed: 4.23s

Artifacts generated:
  - artifacts/tables/{request_id}/monthly_sales.csv (3 rows)
  - artifacts/charts/{request_id}/sales_trend.png (48 KB)

Summary:
  Key Findings:
    - Q1 2021 Arizona sales totaled $1.2M
    - March showed 15% growth over January
  
Audit Log: logs/data_agent_runs.jsonl#{request_id} (12 entries, chain valid)
```

---

## Test Scenario 2: Self-Repair on SQL Syntax Error

**User Story** (from spec.md lines 64-66):
> Given an analysis step fails (e.g., incorrect SQL syntax)  
> When the system encounters the error  
> Then the DataAgent automatically attempts to repair the query (up to K=3 attempts) and logs each attempt

### Test Execution

```python
# tests/integration/test_self_repair.py
def test_self_repair_sql_syntax():
    """Test FR-029, FR-030: Self-repair with K=3 attempts"""
    
    agent = DataAgent()
    request_id = str(uuid.uuid4())
    
    # This intent will likely cause initial SQL syntax error
    # (e.g., Planner forgets quotes around 'Arizona')
    request = AnalysisRequest(
        request_id=request_id,
        intent="Show sales for state Arizona in 2021",
        data_sources=[{
            "type": "sql",
            "connection_string": os.getenv("DATABASE_URL")
        }],
        deliverables=["tables"]
    )
    
    response = agent.analyze(request)
    
    # Assert: Either succeeds after retry OR fails after 3 attempts
    if response.status == "completed":
        # Success case: self-repair worked
        assert response.metrics.retries_count > 0, "Expected at least 1 retry"
        assert response.metrics.retries_count <= 6, "Max 6 retries (K=3 per tool call × 2 calls)"
    else:
        # Failure case: exhausted retries
        assert response.status == "failed"
        assert response.error.error_type == "grounding_error"
        
        # Check that 3 attempts were made per failing tool call
        for failed_call in response.error.failed_tool_calls:
            assert failed_call.attempts == 3, f"Expected 3 attempts, got {failed_call.attempts}"
    
    # Verify audit log contains retry entries
    audit_log = load_audit_log(response.audit_log_ref)
    retry_entries = [e for e in audit_log if e["event_type"] == "tool_called" and e["event_data"].get("attempt_number", 1) > 1]
    assert len(retry_entries) > 0, "Expected retry attempts in audit log"
```

---

## Test Scenario 3: Policy Guardrail Blocks PII Access

**User Story** (from spec.md lines 73-74):
> Given a request attempts to access sensitive data or perform unsafe operations  
> When the safety guardrails evaluate the planned operations  
> Then the system blocks the request and returns a clear explanation

### Test Execution

```python
# tests/integration/test_safety_guardrails.py
def test_pii_blocking():
    """Test FR-020: Detect and block PII column access"""
    
    agent = DataAgent()
    request_id = str(uuid.uuid4())
    
    request = AnalysisRequest(
        request_id=request_id,
        intent="Show customer names and emails from sales table",
        data_sources=[{
            "type": "sql",
            "connection_string": os.getenv("DATABASE_URL")
        }],
        deliverables=["tables"],
        policy={
            "blocked_patterns": ["email", "ssn", "phone"]
        }
    )
    
    response = agent.analyze(request)
    
    # Assert: Request blocked before execution
    assert response.status == "failed"
    assert response.error.error_type == "policy_violation"
    assert "email" in response.error.error_message.lower()
    
    # Assert: No artifacts generated
    assert len(response.artifacts) == 0
    
    # Assert: Execution time very short (no SQL executed)
    assert response.metrics.execution_time_seconds < 1.0
    
    # Assert: Audit log documents policy decision
    audit_log = load_audit_log(response.audit_log_ref)
    policy_entries = [e for e in audit_log if e["event_type"] == "policy_decision"]
    assert len(policy_entries) > 0
    assert policy_entries[0]["event_data"]["decision"] == "blocked"
```

---

## Test Scenario 4: Recipe Reuse

**User Story** (from spec.md lines 69-70):
> Given a similar analysis request has been successfully completed before  
> When the user submits a new request with the same data schema  
> Then the system retrieves the successful recipe from long-term memory and adapts it

### Test Execution

```python
# tests/integration/test_recipe_reuse.py
def test_recipe_storage_and_retrieval():
    """Test FR-031, FR-032, FR-033: Recipe memory"""
    
    agent = DataAgent()
    
    # First request: Creates new recipe
    request1 = AnalysisRequest(
        request_id=str(uuid.uuid4()),
        intent="Analyze Q1 2021 Arizona sales; trends + charts",
        data_sources=[{
            "type": "sql",
            "connection_string": os.getenv("DATABASE_URL"),
            "schema_fingerprint": "abc123..."  # Fixed fingerprint
        }],
        deliverables=["tables", "charts"]
    )
    
    response1 = agent.analyze(request1)
    assert response1.status == "completed"
    assert response1.metrics.recipe_used == False  # New recipe
    
    # Second request: Similar intent, same schema
    request2 = AnalysisRequest(
        request_id=str(uuid.uuid4()),
        intent="Analyze Q2 2021 Arizona sales; trends + charts",  # Similar pattern
        data_sources=[{
            "type": "sql",
            "connection_string": os.getenv("DATABASE_URL"),
            "schema_fingerprint": "abc123..."  # Same fingerprint
        }],
        deliverables=["tables", "charts"]
    )
    
    response2 = agent.analyze(request2)
    assert response2.status == "completed"
    assert response2.metrics.recipe_used == True  # Reused recipe
    
    # Assert: Second request faster due to recipe reuse
    assert response2.metrics.execution_time_seconds < response1.metrics.execution_time_seconds
```

---

## Running All Tests

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific scenario
pytest tests/integration/test_basic_analysis.py::test_q1_arizona_sales_analysis -v

# Run with coverage
pytest tests/integration/ --cov=lib/agents/data_agent --cov-report=html
```

---

## Validation Checklist

After running quickstart tests, verify:

- [ ] **FR-001 to FR-006**: Basic workflow completes successfully
- [ ] **FR-030**: Self-repair attempts up to K=3 retries
- [ ] **FR-020**: PII access blocked by policy guardrails
- [ ] **FR-033**: Recipe retrieval works for similar requests
- [ ] **FR-034**: Audit logs are Merkle-chained (verify with `verify_audit_chain()`)
- [ ] **FR-043**: Typical analyses complete within 30 seconds
- [ ] All generated artifacts have SHA256 hashes (FR-036)
- [ ] Contract schemas validate successfully (JSON Schema validation)

---

## Debugging

**Enable verbose logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Inspect audit log**:
```bash
# View audit trail for specific request
grep "request_id.*550e8400" logs/data_agent_runs.jsonl | jq .

# Verify Merkle chain
python -c "
from lib.agents.data_agent.audit.merkle_log import verify_chain
print('Chain valid:', verify_chain('logs/data_agent_runs.jsonl'))
"
```

**Check generated artifacts**:
```bash
ls -lh artifacts/tables/{request_id}/
ls -lh artifacts/charts/{request_id}/
```

---

## Next Steps

After quickstart tests pass:

1. Run contract tests: `pytest tests/contract/ -v`
2. Run unit tests: `pytest tests/unit/ -v`
3. Performance validation: Ensure 80%+ of requests complete <30s
4. Load testing: 10-20 concurrent analyses (per NFR-004)

---

**Version**: 1.0.0 | **Last Updated**: 2025-09-27