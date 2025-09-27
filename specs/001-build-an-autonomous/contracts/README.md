# DataAgent JSON Contracts

**Feature**: 001-build-an-autonomous  
**Date**: 2025-09-27  
**Contract Version**: 1.0.0

---

## Overview

This directory contains the stable JSON contracts for the DataAgent black-box module per Constitutional Principles II (Black-Box Separation) and VI (Format-First Contracts).

**Contract Files**:
- `request.json`: AnalysisRequest schema (input to DataAgent)
- `response.json`: AnalysisResponse schema (output from DataAgent)

**Contract Guarantee**: These schemas define the public API. Internal implementation (Planner/Actor loop, tools, memory) can evolve freely as long as these contracts remain stable.

---

## Semantic Versioning

Contract versions follow semantic versioning (MAJOR.MINOR.PATCH per FR-042):

- **MAJOR**: Breaking changes (field removal, type changes, new required fields)
- **MINOR**: Backward-compatible additions (new optional fields, new enum values)
- **PATCH**: Clarifications, documentation updates, non-semantic fixes

**Current Version**: 1.0.0

---

## Usage

### Python (Pydantic)

```python
from pydantic import BaseModel, Field
import json

# Load schemas
with open("contracts/request.json") as f:
    request_schema = json.load(f)

with open("contracts/response.json") as f:
    response_schema = json.load(f)

# Generate Pydantic models (automated in lib/agents/data_agent/contracts/)
class AnalysisRequest(BaseModel):
    request_id: str
    intent: str
    data_sources: list
    # ... (full model in lib/agents/data_agent/contracts/request.py)

# Validate incoming request
def invoke_data_agent(request_data: dict) -> dict:
    request = AnalysisRequest(**request_data)  # Raises ValidationError if invalid
    response = data_agent.analyze(request)
    return response.dict()
```

### Contract Testing

Contract tests MUST be written before implementation (Constitutional Principle VIII: TDD):

```python
# tests/contract/test_request_schema.py
import jsonschema
import pytest

def test_request_schema_valid():
    with open("specs/001-build-an-autonomous/contracts/request.json") as f:
        schema = json.load(f)
    
    # Valid request
    valid_request = {
        "request_id": "550e8400-e29b-41d4-a716-446655440000",
        "intent": "Analyze Q1 2021 Arizona sales",
        "data_sources": [{"type": "sql", "connection_string": "postgresql://..."}],
        "deliverables": ["tables"]
    }
    jsonschema.validate(instance=valid_request, schema=schema)  # Should pass

def test_request_schema_rejects_invalid():
    # Missing required field
    invalid_request = {
        "request_id": "550e8400-e29b-41d4-a716-446655440000",
        # Missing "intent"
        "data_sources": [{"type": "sql"}],
        "deliverables": ["tables"]
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid_request, schema=schema)
```

---

## Integration Points

**GEPA Trading System** (per FR-041):
The DataAgent exposes this contract to the GEPA research-execution pipeline as a pluggable sub-agent:

```python
# GEPA research loop integration
from lib.agents.data_agent import DataAgent

agent = DataAgent()

# Research phase: Analyze historical trading data
request = {
    "request_id": str(uuid.uuid4()),
    "intent": "Analyze volatility patterns in BTC-USD hourly candles for last 90 days",
    "data_sources": [{
        "type": "sql",
        "connection_string": "postgresql://trading_db/market_data"
    }],
    "deliverables": ["tables", "charts", "summary"]
}

response = agent.analyze(request)

# Use response.summary.insights to inform strategy generation
if response["status"] == "completed":
    strategy_context = response["summary"]["insights"]
    # Feed to GEPA Generator...
```

---

## Contract Evolution

**Adding New Fields** (MINOR version bump):
```json
// OK: Add optional field
{
  "properties": {
    "priority": {
      "type": "string",
      "enum": ["low", "medium", "high"],
      "default": "medium",
      "description": "NEW in v1.1.0: Analysis priority for queue scheduling"
    }
  }
}
```

**Breaking Changes** (MAJOR version bump):
```json
// NOT OK: Remove required field → v2.0.0
{
  "required": ["request_id", "intent", "data_sources"]
  // Removed "deliverables" - BREAKING
}
```

**Migration Guide** (for breaking changes):
When bumping to v2.0.0, provide migration script:
```python
# migrate_v1_to_v2.py
def migrate_request(v1_request: dict) -> dict:
    v2_request = v1_request.copy()
    # Example: deliverables now inferred from intent
    del v2_request["deliverables"]
    return v2_request
```

---

## Validation Tools

**JSON Schema Validator**:
```bash
# Install validator
pip install jsonschema

# Validate example requests
python -c "
import json, jsonschema
schema = json.load(open('specs/001-build-an-autonomous/contracts/request.json'))
example = schema['examples'][0]
jsonschema.validate(instance=example, schema=schema)
print('✅ Schema valid')
"
```

**OpenAPI Spec Generation** (optional):
Convert JSON schemas to OpenAPI 3.0 for REST API exposure:
```bash
# Generate OpenAPI spec
python scripts/generate_openapi.py --input contracts/ --output openapi.yaml
```

---

## Constitutional Compliance

**Principle II (Black-Box Separation)**: ✅
- Contracts define stable public API
- Implementation in `lib/agents/data_agent/` is private
- Control plane (`.claude/`) cannot reach into internal logic

**Principle VI (Format-First Contracts)**: ✅
- Explicit JSON schemas for all interactions
- Pydantic models generated from schemas
- Semantic versioning enforced

**Principle VIII (TDD)**: ✅
- Contract tests written before implementation
- Tests MUST fail until DataAgent is built

---

**Version**: 1.0.0 | **Last Updated**: 2025-09-27