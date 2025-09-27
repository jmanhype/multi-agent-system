"""Contract tests for AnalysisRequest schema validation.

Tests FR-038, FR-039: Stable JSON Request contract validation.
"""

import json
import uuid
from pathlib import Path

import jsonschema
import pytest
from pydantic import ValidationError

from lib.agents.data_agent.contracts.request import AnalysisRequest


def load_request_schema():
    """Load AnalysisRequest JSON schema from specs."""
    schema_path = Path(__file__).parents[2] / "specs" / "001-build-an-autonomous" / "contracts" / "request.json"
    with open(schema_path) as f:
        return json.load(f)


class TestRequestSchemaValidation:
    """Test AnalysisRequest schema validation against JSON Schema spec."""

    @pytest.fixture
    def schema(self):
        return load_request_schema()

    def test_valid_basic_request(self, schema):
        """Test valid basic AnalysisRequest passes JSON schema validation."""
        request = {
            "request_id": str(uuid.uuid4()),
            "intent": "Analyze Q1 2021 Arizona sales; trends + charts",
            "data_sources": [
                {
                    "type": "sql",
                    "connection_string": "postgresql://localhost/test"
                }
            ],
            "deliverables": ["tables", "charts", "summary"]
        }
        
        jsonschema.validate(instance=request, schema=schema)

    def test_valid_request_with_constraints(self, schema):
        """Test valid AnalysisRequest with constraints passes validation."""
        request = {
            "request_id": str(uuid.uuid4()),
            "intent": "Analyze sales data",
            "data_sources": [{"type": "sql", "connection_string": "postgresql://localhost/test"}],
            "deliverables": ["tables"],
            "constraints": {
                "row_limit": 10000,
                "timeout_seconds": 60
            }
        }
        
        jsonschema.validate(instance=request, schema=schema)

    def test_valid_request_with_policy(self, schema):
        """Test valid AnalysisRequest with policy passes validation."""
        request = {
            "request_id": str(uuid.uuid4()),
            "intent": "Analyze user behavior",
            "data_sources": [{"type": "csv", "file_path": "/data/users.csv"}],
            "deliverables": ["summary"],
            "policy": {
                "allowed_columns": ["user_id", "purchase_amount", "date"],
                "blocked_patterns": ["ssn", "email", "phone"]
            }
        }
        
        jsonschema.validate(instance=request, schema=schema)

    def test_missing_required_fields_fails(self, schema):
        """Test AnalysisRequest missing required fields fails validation."""
        request = {
            "intent": "Analyze data"
        }
        
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=request, schema=schema)

    def test_invalid_intent_length_fails(self, schema):
        """Test AnalysisRequest with empty intent fails validation."""
        request = {
            "request_id": str(uuid.uuid4()),
            "intent": "",
            "data_sources": [{"type": "sql", "connection_string": "test"}],
            "deliverables": ["tables"]
        }
        
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=request, schema=schema)

    def test_invalid_row_limit_fails(self, schema):
        """Test AnalysisRequest with out-of-bounds row_limit fails validation (FR-022)."""
        request = {
            "request_id": str(uuid.uuid4()),
            "intent": "Analyze data",
            "data_sources": [{"type": "sql", "connection_string": "test"}],
            "deliverables": ["tables"],
            "constraints": {
                "row_limit": 300000
            }
        }
        
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=request, schema=schema)

    def test_invalid_timeout_fails(self, schema):
        """Test AnalysisRequest with out-of-bounds timeout fails validation (FR-023)."""
        request = {
            "request_id": str(uuid.uuid4()),
            "intent": "Analyze data",
            "data_sources": [{"type": "sql", "connection_string": "test"}],
            "deliverables": ["tables"],
            "constraints": {
                "timeout_seconds": 200
            }
        }
        
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=request, schema=schema)


class TestRequestPydanticModel:
    """Test AnalysisRequest Pydantic model matches JSON schema contract."""

    def test_pydantic_model_with_valid_data(self):
        """Test Pydantic AnalysisRequest model accepts valid data."""
        request = AnalysisRequest(
            request_id=str(uuid.uuid4()),
            intent="Analyze Q1 2021 Arizona sales; trends + charts",
            data_sources=[
                {"type": "sql", "connection_string": "postgresql://localhost/test"}
            ],
            deliverables=["tables", "charts", "summary"]
        )
        
        assert request.intent == "Analyze Q1 2021 Arizona sales; trends + charts"
        assert len(request.data_sources) == 1
        assert "tables" in request.deliverables

    def test_pydantic_model_rejects_invalid_data(self):
        """Test Pydantic AnalysisRequest model rejects invalid data."""
        with pytest.raises(ValidationError):
            AnalysisRequest(
                request_id="invalid",
                intent="",
                data_sources=[],
                deliverables=[]
            )

    def test_pydantic_model_enforces_row_limit(self):
        """Test Pydantic model enforces row_limit constraint (FR-022)."""
        with pytest.raises(ValidationError):
            AnalysisRequest(
                request_id=str(uuid.uuid4()),
                intent="Test",
                data_sources=[{"type": "sql", "connection_string": "test"}],
                deliverables=["tables"],
                constraints={"row_limit": 300000}
            )

    def test_pydantic_model_enforces_timeout(self):
        """Test Pydantic model enforces timeout constraint (FR-023)."""
        with pytest.raises(ValidationError):
            AnalysisRequest(
                request_id=str(uuid.uuid4()),
                intent="Test",
                data_sources=[{"type": "sql", "connection_string": "test"}],
                deliverables=["tables"],
                constraints={"timeout_seconds": 200}
            )