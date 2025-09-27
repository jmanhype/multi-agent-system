"""Integration test for self-repair with K=3 attempts.

Tests FR-029, FR-030: Self-repair and error recovery mechanisms.
Based on Quickstart Test 2 scenario.
"""

import json
import os
import uuid

import pytest

from lib.agents.data_agent.agent import DataAgent
from lib.agents.data_agent.contracts.request import AnalysisRequest


@pytest.fixture
def test_database():
    """Set up test database with sample data."""
    pytest.skip("Database setup required - implement after DataAgent core")


@pytest.fixture
def audit_log_path(tmp_path):
    """Create temporary audit log path."""
    log_path = tmp_path / "data_agent_runs.jsonl"
    return log_path


class TestSelfRepairMechanism:
    """Test self-repair with K=3 attempts for grounding errors."""

    def test_self_repair_typo_column_name(self, test_database, audit_log_path):
        """Test self-repair recovers from typo in column name (FR-029, FR-030).
        
        Validates:
        - FR-029: Grounding error detection
        - FR-030: K=3 self-repair attempts (initial + 2 retries)
        - Error classification and adaptive repair
        - Audit log includes all repair attempts
        """
        agent = DataAgent(audit_log_path=str(audit_log_path))
        
        request = AnalysisRequest(
            request_id=str(uuid.uuid4()),
            intent="Show me average salez by region",
            data_sources=[
                {
                    "type": "sql",
                    "connection_string": os.getenv("TEST_DATABASE_URL", "postgresql://localhost/test_sales")
                }
            ],
            deliverables=["tables"]
        )
        
        response = agent.analyze(request)
        
        assert response.status == "completed"
        
        audit_entries = []
        with open(audit_log_path) as f:
            for line in f:
                entry = json.loads(line)
                if entry["request_id"] == request.request_id:
                    audit_entries.append(entry)
        
        repair_attempts = [e for e in audit_entries if e["event_type"] == "repair_attempt"]
        assert len(repair_attempts) >= 1
        assert len(repair_attempts) <= 3
        
        assert any("salez" in str(e.get("original_error", "")) for e in repair_attempts)
        assert any("sales" in str(e.get("repair_strategy", "")) for e in repair_attempts)

    def test_self_repair_exhausts_attempts(self, test_database, audit_log_path):
        """Test self-repair fails after K=3 attempts for unrecoverable error (FR-030).
        
        Validates:
        - Maximum 3 repair attempts (initial + 2 retries)
        - System returns failure with all attempts documented
        - Audit log contains error details and repair strategies
        """
        agent = DataAgent(audit_log_path=str(audit_log_path))
        
        request = AnalysisRequest(
            request_id=str(uuid.uuid4()),
            intent="Show me data from nonexistent_table",
            data_sources=[
                {
                    "type": "sql",
                    "connection_string": os.getenv("TEST_DATABASE_URL", "postgresql://localhost/test_sales")
                }
            ],
            deliverables=["tables"]
        )
        
        response = agent.analyze(request)
        
        assert response.status == "failed"
        assert response.error is not None
        assert "repair attempts" in response.error["message"].lower()
        
        audit_entries = []
        with open(audit_log_path) as f:
            for line in f:
                entry = json.loads(line)
                if entry["request_id"] == request.request_id:
                    audit_entries.append(entry)
        
        repair_attempts = [e for e in audit_entries if e["event_type"] == "repair_attempt"]
        assert len(repair_attempts) == 3

    def test_self_repair_type_mismatch(self, test_database, audit_log_path):
        """Test self-repair recovers from type mismatch errors (FR-029)."""
        agent = DataAgent(audit_log_path=str(audit_log_path))
        
        request = AnalysisRequest(
            request_id=str(uuid.uuid4()),
            intent="Filter sales where date > 'invalid_date_format'",
            data_sources=[
                {
                    "type": "sql",
                    "connection_string": os.getenv("TEST_DATABASE_URL", "postgresql://localhost/test_sales")
                }
            ],
            deliverables=["tables"]
        )
        
        response = agent.analyze(request)
        
        audit_entries = []
        with open(audit_log_path) as f:
            for line in f:
                entry = json.loads(line)
                if entry["request_id"] == request.request_id:
                    audit_entries.append(entry)
        
        repair_attempts = [e for e in audit_entries if e["event_type"] == "repair_attempt"]
        
        if response.status == "completed":
            assert len(repair_attempts) >= 1
        else:
            assert len(repair_attempts) == 3

    def test_self_repair_missing_column(self, test_database, audit_log_path):
        """Test self-repair attempts column name suggestions for missing columns."""
        agent = DataAgent(audit_log_path=str(audit_log_path))
        
        request = AnalysisRequest(
            request_id=str(uuid.uuid4()),
            intent="Show me customer_naem grouped by region",
            data_sources=[
                {
                    "type": "sql",
                    "connection_string": os.getenv("TEST_DATABASE_URL", "postgresql://localhost/test_sales")
                }
            ],
            deliverables=["tables"]
        )
        
        response = agent.analyze(request)
        
        audit_entries = []
        with open(audit_log_path) as f:
            for line in f:
                entry = json.loads(line)
                if entry["request_id"] == request.request_id:
                    audit_entries.append(entry)
        
        repair_attempts = [e for e in audit_entries if e["event_type"] == "repair_attempt"]
        assert len(repair_attempts) > 0
        
        assert any("customer_name" in str(e.get("repair_strategy", "")).lower() for e in repair_attempts)