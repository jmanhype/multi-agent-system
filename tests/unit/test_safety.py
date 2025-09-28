"""Unit tests for safety guardrails."""

import pytest
from lib.agents.data_agent.safety.policy import (
    SQLPolicyChecker,
    PIIDetector,
    ColumnAccessControl,
    PolicyEnforcer,
    PolicyResult,
    PIIMatch,
)
from lib.agents.data_agent.safety.sandbox import (
    SandboxExecutor,
    ResourceQuota,
    SandboxTimeoutError,
)


class TestSQLPolicyChecker:
    """Unit tests for SQL policy checker."""
    
    def test_allow_safe_query(self):
        checker = SQLPolicyChecker()
        result = checker.check_query("SELECT id, name FROM users WHERE age > 18")
        
        assert result.allowed is True
        assert len(result.violations) == 0
        assert result.severity == "none"
    
    def test_block_ddl_create(self):
        checker = SQLPolicyChecker()
        result = checker.check_query("CREATE TABLE users (id INT)")
        
        assert result.allowed is False
        assert any("DDL" in v for v in result.violations)
        assert result.severity == "critical"
    
    def test_block_ddl_drop(self):
        checker = SQLPolicyChecker()
        result = checker.check_query("DROP TABLE users")
        
        assert result.allowed is False
        assert any("DDL" in v for v in result.violations)
        assert result.severity == "critical"
    
    def test_block_ddl_alter(self):
        checker = SQLPolicyChecker()
        result = checker.check_query("ALTER TABLE users ADD COLUMN email VARCHAR(255)")
        
        assert result.allowed is False
        assert any("DDL" in v for v in result.violations)
        assert result.severity == "critical"
    
    def test_block_dml_insert(self):
        checker = SQLPolicyChecker()
        result = checker.check_query("INSERT INTO users (name) VALUES ('Alice')")
        
        assert result.allowed is False
        assert any("DML" in v for v in result.violations)
        assert result.severity == "critical"
    
    def test_block_dml_update(self):
        checker = SQLPolicyChecker()
        result = checker.check_query("UPDATE users SET name = 'Bob' WHERE id = 1")
        
        assert result.allowed is False
        assert any("DML" in v for v in result.violations)
        assert result.severity == "critical"
    
    def test_block_dml_delete(self):
        checker = SQLPolicyChecker()
        result = checker.check_query("DELETE FROM users WHERE id = 1")
        
        assert result.allowed is False
        assert any("DML" in v for v in result.violations)
        assert result.severity == "critical"
    
    def test_block_dangerous_exec(self):
        checker = SQLPolicyChecker()
        result = checker.check_query("EXEC sp_executesql @sql")
        
        assert result.allowed is False
        assert any("Dangerous" in v for v in result.violations)
        assert result.severity == "critical"
    
    def test_detect_sql_comment_injection(self):
        checker = SQLPolicyChecker()
        result = checker.check_query("SELECT * FROM users WHERE id = 1 -- DROP TABLE users")
        
        assert result.allowed is False
        assert any("comment" in v.lower() for v in result.violations)
    
    def test_detect_multiple_statements(self):
        checker = SQLPolicyChecker()
        result = checker.check_query("SELECT * FROM users; DROP TABLE users;")
        
        assert result.allowed is False
        assert any("Multiple statements" in v for v in result.violations)


class TestPIIDetector:
    """Unit tests for PII detector."""
    
    def test_detect_ssn(self):
        detector = PIIDetector()
        matches = detector.detect_pii("My SSN is 123-45-6789", "test")
        
        assert len(matches) == 1
        assert matches[0].pii_type == "ssn"
        assert matches[0].value == "123-45-6789"
        assert matches[0].confidence > 0.9
    
    def test_detect_email(self):
        detector = PIIDetector()
        matches = detector.detect_pii("Contact me at alice@example.com", "test")
        
        assert len(matches) == 1
        assert matches[0].pii_type == "email"
        assert matches[0].value == "alice@example.com"
    
    def test_detect_phone(self):
        detector = PIIDetector()
        matches = detector.detect_pii("Call me at (555) 123-4567", "test")
        
        assert len(matches) == 1
        assert matches[0].pii_type == "phone"
        assert "555" in matches[0].value
    
    def test_detect_credit_card_valid(self):
        detector = PIIDetector()
        matches = detector.detect_pii("Card: 4532015112830366", "test")
        
        assert len(matches) == 1
        assert matches[0].pii_type == "credit_card"
    
    def test_detect_credit_card_invalid_luhn(self):
        detector = PIIDetector()
        matches = detector.detect_pii("Card: 1234-5678-9012-3456", "test")
        
        assert len(matches) == 0
    
    def test_detect_multiple_pii(self):
        detector = PIIDetector()
        text = "Contact alice@example.com or call (555) 123-4567. SSN: 123-45-6789"
        matches = detector.detect_pii(text, "test")
        
        assert len(matches) >= 3
        types = {m.pii_type for m in matches}
        assert "email" in types
        assert "phone" in types
        assert "ssn" in types
    
    def test_no_pii_in_clean_text(self):
        detector = PIIDetector()
        matches = detector.detect_pii("The quick brown fox jumps over the lazy dog", "test")
        
        assert len(matches) == 0


class TestColumnAccessControl:
    """Unit tests for column access control."""
    
    def test_allow_all_by_default(self):
        control = ColumnAccessControl()
        result = control.check_column_access("users", "name")
        
        assert result.allowed is True
        assert len(result.violations) == 0
    
    def test_block_blacklisted_column(self):
        control = ColumnAccessControl(blocked_patterns=["*.password"])
        result = control.check_column_access("users", "password")
        
        assert result.allowed is False
        assert any("password" in v for v in result.violations)
        assert result.severity == "high"
    
    def test_block_blacklisted_table_wildcard(self):
        control = ColumnAccessControl(blocked_patterns=["sensitive.*"])
        result = control.check_column_access("sensitive", "data")
        
        assert result.allowed is False
    
    def test_allow_whitelisted_column(self):
        control = ColumnAccessControl(allowed_patterns=["users.name", "users.email"])
        result = control.check_column_access("users", "name")
        
        assert result.allowed is True
    
    def test_block_non_whitelisted_column(self):
        control = ColumnAccessControl(allowed_patterns=["users.name"])
        result = control.check_column_access("users", "email")
        
        assert result.allowed is False
        assert result.severity == "medium"
    
    def test_blacklist_overrides_whitelist(self):
        control = ColumnAccessControl(
            allowed_patterns=["users.*"],
            blocked_patterns=["*.password"],
        )
        result = control.check_column_access("users", "password")
        
        assert result.allowed is False
        assert result.severity == "high"
    
    def test_wildcard_patterns(self):
        control = ColumnAccessControl(blocked_patterns=["*.ssn", "*.credit_card"])
        
        assert control.check_column_access("users", "ssn").allowed is False
        assert control.check_column_access("customers", "credit_card").allowed is False
        assert control.check_column_access("users", "name").allowed is True


class TestPolicyEnforcer:
    """Unit tests for policy enforcer."""
    
    def test_validate_safe_query(self):
        enforcer = PolicyEnforcer()
        result = enforcer.validate_query("SELECT * FROM users WHERE age > 18")
        
        assert result.allowed is True
    
    def test_validate_dangerous_query(self):
        enforcer = PolicyEnforcer()
        result = enforcer.validate_query("DROP TABLE users")
        
        assert result.allowed is False
        assert result.severity == "critical"
    
    def test_scan_data_for_pii(self):
        enforcer = PolicyEnforcer()
        data = [
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Bob", "email": "bob@example.com"},
        ]
        matches = enforcer.scan_data_for_pii(data, "users")
        
        assert len(matches) == 2
        assert all(m.pii_type == "email" for m in matches)
    
    def test_validate_column_access_allowed(self):
        enforcer = PolicyEnforcer()
        result = enforcer.validate_column_access("users", ["id", "name", "email"])
        
        assert result.allowed is True
    
    def test_validate_column_access_blocked(self):
        enforcer = PolicyEnforcer()
        result = enforcer.validate_column_access("users", ["name", "password"])
        
        assert result.allowed is False
        assert any("password" in v for v in result.violations)
    
    def test_validate_multiple_violations(self):
        enforcer = PolicyEnforcer()
        result = enforcer.validate_column_access(
            "users",
            ["password", "ssn", "credit_card"],
        )
        
        assert result.allowed is False
        assert len(result.violations) == 3
        assert result.severity == "high"


class TestSandboxExecutor:
    """Unit tests for sandbox executor."""
    
    def test_execute_simple_function(self):
        quota = ResourceQuota(max_execution_seconds=5.0)
        sandbox = SandboxExecutor(quota)
        
        def simple_func(x, y):
            return x + y
        
        result = sandbox.execute_in_sandbox(simple_func, 2, 3)
        
        assert result.success is True
        assert result.result == 5
        assert result.error is None
        assert result.execution_time_seconds < 5.0
    
    def test_execute_with_timeout(self):
        import sys
        if sys.platform != "linux":
            pytest.skip("SIGALRM not available on non-Linux platforms")
        
        quota = ResourceQuota(max_execution_seconds=0.1)
        sandbox = SandboxExecutor(quota)
        
        def slow_func():
            import time
            time.sleep(1.0)
            return "done"
        
        result = sandbox.execute_in_sandbox(slow_func)
        
        assert result.success is False
        assert "timeout" in result.error.lower()
        assert len(result.violations) > 0
    
    def test_execute_with_exception(self):
        quota = ResourceQuota()
        sandbox = SandboxExecutor(quota)
        
        def error_func():
            raise ValueError("Test error")
        
        result = sandbox.execute_in_sandbox(error_func)
        
        assert result.success is False
        assert "Test error" in result.error
    
    def test_monitor_resources(self):
        quota = ResourceQuota()
        sandbox = SandboxExecutor(quota)
        
        metrics = sandbox.monitor_resources()
        
        assert "memory_mb" in metrics
        assert "cpu_percent" in metrics
        assert metrics["memory_mb"] >= 0
        assert metrics["cpu_percent"] >= 0
    
    def test_memory_tracking(self):
        quota = ResourceQuota(max_memory_mb=100)
        sandbox = SandboxExecutor(quota)
        
        def memory_func():
            data = [0] * 1000
            return len(data)
        
        result = sandbox.execute_in_sandbox(memory_func)
        
        assert result.success is True
        assert result.peak_memory_mb >= 0
    
    def test_cpu_tracking(self):
        quota = ResourceQuota()
        sandbox = SandboxExecutor(quota)
        
        def cpu_func():
            total = 0
            for i in range(10000):
                total += i
            return total
        
        result = sandbox.execute_in_sandbox(cpu_func)
        
        assert result.success is True
        assert result.avg_cpu_percent >= 0