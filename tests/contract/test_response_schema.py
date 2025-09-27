"""Contract tests for AnalysisResponse schema validation.

Tests FR-038, FR-040: Stable JSON Response contract validation.
"""

import json
import uuid
from pathlib import Path

import jsonschema
import pytest
from pydantic import ValidationError

from lib.agents.data_agent.contracts.response import AnalysisResponse


def load_response_schema():
    """Load AnalysisResponse JSON schema from specs."""
    schema_path = Path(__file__).parents[2] / "specs" / "001-build-an-autonomous" / "contracts" / "response.json"
    with open(schema_path) as f:
        return json.load(f)


class TestResponseSchemaValidation:
    """Test AnalysisResponse schema validation against JSON Schema spec."""

    @pytest.fixture
    def schema(self):
        return load_response_schema()

    def test_valid_completed_response(self, schema):
        """Test valid completed AnalysisResponse passes JSON schema validation."""
        response = {
            "request_id": str(uuid.uuid4()),
            "status": "completed",
            "artifacts": [
                {
                    "artifact_id": str(uuid.uuid4()),
                    "artifact_type": "table",
                    "content_ref": "file:///data/results.csv",
                    "content_hash": "d3f5a7b9c1e3d5f7a9b1c3e5d7f9a1b3c5e7d9f1a3b5c7d9e1f3a5b7c9d1e3f5",
                    "metadata": {
                        "rows": 100,
                        "columns": ["date", "sales", "region"]
                    }
                }
            ],
            "summary": {
                "key_findings": [
                    "Total revenue: $1.2M",
                    "15% increase over Q4 2020"
                ],
                "insights": "Q1 2021 Arizona sales showed strong growth.",
                "warnings": []
            },
            "metrics": {
                "execution_time_seconds": 12.5,
                "tool_calls_count": 3
            },
            "audit_log_ref": "file:///logs/data_agent_runs.jsonl#line-1234",
            "plan_ref": "file:///logs/plans/plan-uuid.json"
        }
        
        jsonschema.validate(instance=response, schema=schema)

    def test_valid_failed_response(self, schema):
        """Test valid failed AnalysisResponse passes validation."""
        response = {
            "request_id": str(uuid.uuid4()),
            "status": "failed",
            "artifacts": [],
            "error": {
                "error_type": "grounding_error",
                "error_message": "Failed to resolve column 'salez' after 3 repair attempts",
                "failed_tool_calls": []
            },
            "summary": {
                "key_findings": [],
                "insights": "Analysis failed due to invalid column reference.",
                "warnings": ["Column 'salez' not found after 3 repair attempts"]
            },
            "metrics": {
                "execution_time_seconds": 8.2,
                "tool_calls_count": 4
            },
            "audit_log_ref": "file:///logs/data_agent_runs.jsonl#line-1235"
        }
        
        jsonschema.validate(instance=response, schema=schema)

    def test_missing_required_fields_fails(self, schema):
        """Test AnalysisResponse missing required fields fails validation."""
        response = {
            "status": "completed"
        }
        
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=response, schema=schema)

    def test_invalid_status_fails(self, schema):
        """Test AnalysisResponse with invalid status fails validation."""
        response = {
            "request_id": str(uuid.uuid4()),
            "status": "invalid_status",
            "summary": {
                "key_findings": [],
                "insights": "Test",
                "warnings": []
            },
            "metrics": {
                "execution_time_seconds": 1.0,
                "tool_calls_count": 1
            },
            "audit_log_ref": "test"
        }
        
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=response, schema=schema)

    def test_completed_without_artifacts_fails(self, schema):
        """Test completed AnalysisResponse without artifacts fails validation."""
        response = {
            "request_id": str(uuid.uuid4()),
            "status": "completed",
            "summary": {
                "key_findings": [],
                "insights": "Test",
                "warnings": []
            },
            "metrics": {
                "execution_time_seconds": 1.0,
                "tool_calls_count": 1
            },
            "audit_log_ref": "test"
        }
        
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=response, schema=schema)

    def test_failed_without_error_fails(self, schema):
        """Test failed AnalysisResponse without error field fails validation."""
        response = {
            "request_id": str(uuid.uuid4()),
            "status": "failed",
            "summary": {
                "key_findings": [],
                "insights": "Test",
                "warnings": []
            },
            "metrics": {
                "execution_time_seconds": 1.0,
                "tool_calls_count": 1
            },
            "audit_log_ref": "test"
        }
        
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=response, schema=schema)

    def test_performance_constraint_validation(self, schema):
        """Test response metrics validate performance requirements (FR-043)."""
        response = {
            "request_id": str(uuid.uuid4()),
            "status": "completed",
            "artifacts": [{"artifact_id": str(uuid.uuid4()), "artifact_type": "table", "content_ref": "test", "content_hash": "d3f5a7b9c1e3d5f7a9b1c3e5d7f9a1b3c5e7d9f1a3b5c7d9e1f3a5b7c9d1e3f5"}],
            "summary": {
                "key_findings": [],
                "insights": "Test",
                "warnings": []
            },
            "metrics": {
                "execution_time_seconds": 29.5,
                "tool_calls_count": 5
            },
            "audit_log_ref": "test"
        }
        
        jsonschema.validate(instance=response, schema=schema)
        assert response["metrics"]["execution_time_seconds"] < 30


class TestResponsePydanticModel:
    """Test AnalysisResponse Pydantic model matches JSON schema contract."""

    def test_pydantic_model_with_valid_completed_response(self):
        """Test Pydantic AnalysisResponse model accepts valid completed response."""
        response = AnalysisResponse(
            request_id=str(uuid.uuid4()),
            status="completed",
            artifacts=[
                {
                    "artifact_id": str(uuid.uuid4()),
                    "artifact_type": "table",
                    "content_ref": "file:///data/results.csv",
                    "content_hash": "d3f5a7b9c1e3d5f7a9b1c3e5d7f9a1b3c5e7d9f1a3b5c7d9e1f3a5b7c9d1e3f5"
                }
            ],
            summary={
                "key_findings": ["Analysis completed"],
                "insights": "Analysis completed successfully.",
                "warnings": []
            },
            metrics={
                "execution_time_seconds": 12.5,
                "tool_calls_count": 3
            },
            audit_log_ref="file:///logs/data_agent_runs.jsonl#line-1234"
        )
        
        assert response.status == "completed"
        assert len(response.artifacts) == 1
        assert response.metrics.tool_calls_count == 3

    def test_pydantic_model_with_valid_failed_response(self):
        """Test Pydantic AnalysisResponse model accepts valid failed response."""
        response = AnalysisResponse(
            request_id=str(uuid.uuid4()),
            status="failed",
            error={
                "error_type": "timeout",
                "error_message": "Analysis exceeded 30 second timeout",
                "failed_tool_calls": []
            },
            summary={
                "key_findings": [],
                "insights": "Analysis failed due to timeout.",
                "warnings": ["Exceeded 30 second timeout"]
            },
            metrics={
                "execution_time_seconds": 30.1,
                "tool_calls_count": 2
            },
            audit_log_ref="file:///logs/data_agent_runs.jsonl#line-1236"
        )
        
        assert response.status == "failed"
        assert response.error.error_type == "timeout"

    def test_pydantic_model_rejects_invalid_status(self):
        """Test Pydantic AnalysisResponse model rejects invalid status."""
        with pytest.raises(ValidationError):
            AnalysisResponse(
                request_id=str(uuid.uuid4()),
                status="invalid",
                summary={
                    "key_findings": [],
                    "insights": "Test",
                    "warnings": []
                },
                metrics={
                    "execution_time_seconds": 1.0,
                    "tool_calls_count": 1,
                    "data_rows_processed": 0
                },
                audit_log_ref="test"
            )

    def test_pydantic_model_enforces_completed_artifacts(self):
        """Test Pydantic model enforces artifacts for completed responses."""
        with pytest.raises(ValidationError):
            AnalysisResponse(
                request_id=str(uuid.uuid4()),
                status="completed",
                summary={
                    "key_findings": [],
                    "insights": "Test",
                    "warnings": []
                },
                metrics={
                    "execution_time_seconds": 1.0,
                    "tool_calls_count": 1,
                    "data_rows_processed": 0
                },
                audit_log_ref="test"
            )

    def test_pydantic_model_enforces_failed_error(self):
        """Test Pydantic model enforces error field for failed responses."""
        with pytest.raises(ValidationError):
            AnalysisResponse(
                request_id=str(uuid.uuid4()),
                status="failed",
                summary={
                    "key_findings": [],
                    "insights": "Test",
                    "warnings": []
                },
                metrics={
                    "execution_time_seconds": 1.0,
                    "tool_calls_count": 1,
                    "data_rows_processed": 0
                },
                audit_log_ref="test"
            )