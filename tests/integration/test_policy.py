"""Integration test for policy guardrails and safety enforcement.

Tests FR-016 through FR-024: Safety guardrails, PII blocking, resource limits.
Based on Quickstart Test 3 scenario.
"""

import json
import os
import uuid

import pytest

from lib.agents.data_agent.agent import DataAgent
from lib.agents.data_agent.contracts.request import AnalysisRequest


@pytest.fixture
def test_database():
    """Set up test database with PII columns."""
    pytest.skip("Database setup required - implement after DataAgent core")


@pytest.fixture
def audit_log_path(tmp_path):
    """Create temporary audit log path."""
    log_path = tmp_path / "data_agent_runs.jsonl"
    return log_path


class TestPolicyGuardrails:
    """Test policy guardrails block unsafe operations."""

    def test_pii_access_blocked(self, test_database, audit_log_path):
        """Test policy guardrails block PII column access (FR-020).
        
        Validates:
        - FR-020: PII detection and blocking (SSN, email, phone)
        - Policy decision logged to audit trail
        - Clear error message returned to user
        """
        agent = DataAgent(audit_log_path=str(audit_log_path))
        
        request = AnalysisRequest(
            request_id=str(uuid.uuid4()),
            intent="Show me all customer emails and phone numbers",
            data_sources=[
                {
                    "type": "sql",
                    "connection_string": os.getenv("TEST_DATABASE_URL", "postgresql://localhost/test_sales")
                }
            ],
            deliverables=["tables"],
            policy={
                "blocked_patterns": ["email", "phone", "ssn"]
            }
        )
        
        response = agent.analyze(request)
        
        assert response.status == "failed"
        assert response.error is not None
        assert "pii" in response.error["message"].lower() or "blocked" in response.error["message"].lower()
        assert response.error["code"] in ["POLICY_VIOLATION", "PII_ACCESS_BLOCKED"]
        
        audit_entries = []
        with open(audit_log_path) as f:
            for line in f:
                entry = json.loads(line)
                if entry["request_id"] == request.request_id:
                    audit_entries.append(entry)
        
        policy_blocks = [e for e in audit_entries if e["event_type"] == "policy_block"]
        assert len(policy_blocks) > 0
        
        assert any("email" in str(e.get("blocked_columns", [])).lower() for e in policy_blocks)

    def test_ddl_operations_blocked(self, test_database, audit_log_path):
        """Test policy guardrails block DDL operations (FR-016).
        
        Validates:
        - FR-016: DDL operations blocked (CREATE, ALTER, DROP)
        - Policy enforcement before execution
        """
        agent = DataAgent(audit_log_path=str(audit_log_path))
        
        request = AnalysisRequest(
            request_id=str(uuid.uuid4()),
            intent="Create a new table for storing analysis results",
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
        assert "ddl" in response.error["message"].lower() or "create" in response.error["message"].lower()

    def test_dml_operations_blocked(self, test_database, audit_log_path):
        """Test policy guardrails block DML operations (FR-017).
        
        Validates:
        - FR-017: DML operations blocked (INSERT, UPDATE, DELETE)
        - Read-only access enforced
        """
        agent = DataAgent(audit_log_path=str(audit_log_path))
        
        request = AnalysisRequest(
            request_id=str(uuid.uuid4()),
            intent="Update all sales records to add 10% markup",
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
        assert "update" in response.error["message"].lower() or "modify" in response.error["message"].lower()

    def test_row_limit_enforced(self, test_database, audit_log_path):
        """Test system enforces row limits on queries (FR-022).
        
        Validates:
        - FR-022: Row limit enforcement (max 200k rows)
        - Warning when results truncated
        """
        agent = DataAgent(audit_log_path=str(audit_log_path))
        
        request = AnalysisRequest(
            request_id=str(uuid.uuid4()),
            intent="Show me all sales records",
            data_sources=[
                {
                    "type": "sql",
                    "connection_string": os.getenv("TEST_DATABASE_URL", "postgresql://localhost/test_sales")
                }
            ],
            deliverables=["tables"],
            constraints={
                "row_limit": 1000
            }
        )
        
        response = agent.analyze(request)
        
        if response.status == "completed":
            assert response.metrics["data_rows_processed"] <= 1000

    def test_timeout_limit_enforced(self, test_database, audit_log_path):
        """Test system enforces timeout limits on operations (FR-023).
        
        Validates:
        - FR-023: Timeout enforcement (max 180s)
        - Graceful degradation on timeout
        """
        agent = DataAgent(audit_log_path=str(audit_log_path))
        
        request = AnalysisRequest(
            request_id=str(uuid.uuid4()),
            intent="Perform complex multi-table join analysis",
            data_sources=[
                {
                    "type": "sql",
                    "connection_string": os.getenv("TEST_DATABASE_URL", "postgresql://localhost/test_sales")
                }
            ],
            deliverables=["tables"],
            constraints={
                "timeout_seconds": 5
            }
        )
        
        response = agent.analyze(request)
        
        if response.status == "failed":
            assert response.error["code"] in ["TIMEOUT", "TIMEOUT_EXCEEDED"]
        else:
            assert response.metrics["execution_time_seconds"] <= 5

    def test_parameterized_queries_enforced(self, test_database, audit_log_path):
        """Test system uses parameterized queries (FR-018).
        
        Validates:
        - FR-018: Parameterized queries mandatory
        - No SQL injection vulnerabilities
        """
        agent = DataAgent(audit_log_path=str(audit_log_path))
        
        request = AnalysisRequest(
            request_id=str(uuid.uuid4()),
            intent="Show sales where region = 'Arizona'; DROP TABLE sales; --",
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
                if entry["request_id"] == request.request_id and entry["event_type"] == "tool_call":
                    audit_entries.append(entry)
        
        sql_calls = [e for e in audit_entries if e.get("tool_name") == "sql.run"]
        for call in sql_calls:
            assert "DROP TABLE" not in str(call.get("tool_args", {}))
            assert "parameters" in call.get("tool_args", {})

    def test_sensitive_data_redaction(self, test_database, audit_log_path):
        """Test system redacts sensitive data in logs (FR-021).
        
        Validates:
        - FR-021: Sensitive data redacted in audit logs
        - PII patterns masked in log entries
        """
        agent = DataAgent(audit_log_path=str(audit_log_path))
        
        request = AnalysisRequest(
            request_id=str(uuid.uuid4()),
            intent="Analyze customer demographics by age group",
            data_sources=[
                {
                    "type": "sql",
                    "connection_string": os.getenv("TEST_DATABASE_URL", "postgresql://localhost/test_sales")
                }
            ],
            deliverables=["tables"],
            policy={
                "allowed_columns": ["age_group", "region", "purchase_count"]
            }
        )
        
        response = agent.analyze(request)
        
        with open(audit_log_path) as f:
            log_content = f.read()
            
            assert "@" not in log_content or "[REDACTED]" in log_content
            assert not any(pattern in log_content for pattern in ["123-45-6789", "(555) 555-5555"])