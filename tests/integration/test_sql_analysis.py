"""Integration test for SQL-based data analysis workflow.

Tests FR-001 through FR-006, FR-043: End-to-end SQL analysis with artifacts and audit logs.
Based on Quickstart Test 1 scenario.
"""

import json
import os
import uuid
from pathlib import Path

import pytest

from lib.agents.data_agent.agent import DataAgent
from lib.agents.data_agent.contracts.request import AnalysisRequest


@pytest.fixture
def test_database():
    """Set up test database with sample sales data."""
    pytest.skip("Database setup required - implement after DataAgent core")


@pytest.fixture
def audit_log_path(tmp_path):
    """Create temporary audit log path."""
    log_path = tmp_path / "data_agent_runs.jsonl"
    return log_path


class TestSQLAnalysisWorkflow:
    """Test SQL-based analysis end-to-end workflow."""

    def test_q1_arizona_sales_analysis(self, test_database, audit_log_path):
        """Test Q1 2021 Arizona sales analysis with trends and charts (FR-001 to FR-006).
        
        This test validates:
        - FR-001: Natural language intent processing
        - FR-002: Autonomous task decomposition
        - FR-003: Structured operation generation
        - FR-004: Sandboxed execution
        - FR-005: Artifact generation (tables, charts, reports)
        - FR-006: Complete audit trail
        - FR-043: <30s completion time
        """
        agent = DataAgent(audit_log_path=str(audit_log_path))
        
        request = AnalysisRequest(
            request_id=str(uuid.uuid4()),
            intent="Analyze Q1 2021 Arizona sales; trends + charts",
            data_sources=[
                {
                    "type": "sql",
                    "connection_string": os.getenv("TEST_DATABASE_URL", "postgresql://localhost/test_sales")
                }
            ],
            deliverables=["tables", "charts", "summary"],
            constraints={
                "row_limit": 200000,
                "timeout_seconds": 30
            }
        )
        
        response = agent.analyze(request)
        
        assert response.status == "completed"
        
        assert len(response.artifacts) >= 2
        
        artifact_types = {a["type"] for a in response.artifacts}
        assert "table" in artifact_types
        assert "chart" in artifact_types
        
        assert response.summary is not None
        assert len(response.summary) > 0
        
        assert response.metrics["execution_time_seconds"] < 30
        assert response.metrics["tool_calls_count"] >= 2
        assert response.metrics["data_rows_processed"] > 0
        
        assert response.audit_log_ref is not None
        
        audit_entries = []
        with open(audit_log_path) as f:
            for line in f:
                entry = json.loads(line)
                if entry["request_id"] == request.request_id:
                    audit_entries.append(entry)
        
        assert len(audit_entries) > 0
        assert any(e["event_type"] == "plan_generated" for e in audit_entries)
        assert any(e["event_type"] == "tool_call" for e in audit_entries)
        assert any(e["event_type"] == "artifact_created" for e in audit_entries)
        
        for i in range(1, len(audit_entries)):
            assert "parent_hash" in audit_entries[i]
            assert audit_entries[i]["parent_hash"] == audit_entries[i-1]["trace_hash"]

    def test_multi_source_analysis(self, test_database, audit_log_path):
        """Test analysis spanning SQL database and CSV file (FR-014).
        
        Validates:
        - FR-012: SQL database support
        - FR-013: CSV file support
        - FR-014: Multiple heterogeneous data sources
        """
        agent = DataAgent(audit_log_path=str(audit_log_path))
        
        request = AnalysisRequest(
            request_id=str(uuid.uuid4()),
            intent="Join customer database with product catalog CSV; analyze purchase patterns",
            data_sources=[
                {
                    "type": "sql",
                    "connection_string": os.getenv("TEST_DATABASE_URL", "postgresql://localhost/test_sales")
                },
                {
                    "type": "csv",
                    "file_path": str(Path(__file__).parent / "fixtures" / "products.csv")
                }
            ],
            deliverables=["tables", "summary"]
        )
        
        response = agent.analyze(request)
        
        assert response.status == "completed"
        assert len(response.data_sources_accessed) == 2

    def test_performance_within_30_seconds(self, test_database, audit_log_path):
        """Test typical analysis completes within 30 seconds (FR-043)."""
        agent = DataAgent(audit_log_path=str(audit_log_path))
        
        request = AnalysisRequest(
            request_id=str(uuid.uuid4()),
            intent="Calculate monthly sales averages for 2021",
            data_sources=[
                {
                    "type": "sql",
                    "connection_string": os.getenv("TEST_DATABASE_URL", "postgresql://localhost/test_sales")
                }
            ],
            deliverables=["tables", "summary"]
        )
        
        response = agent.analyze(request)
        
        assert response.status == "completed"
        assert response.metrics["execution_time_seconds"] < 30

    def test_progress_indicator_after_10_seconds(self, test_database, audit_log_path):
        """Test progress indicator appears for analyses exceeding 10 seconds (FR-045)."""
        pytest.skip("Progress indicator implementation pending")