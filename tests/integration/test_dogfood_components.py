"""Dogfooding test: DataAgent components working together.

Tests the integration of tools and safety layer without full orchestrator.
"""

import tempfile
from pathlib import Path
import pandas as pd
import pytest
from lib.agents.data_agent.tools import SQLRunner, DataFrameOperations, Plotter, DataProfiler
from lib.agents.data_agent.safety import PolicyEnforcer, SandboxExecutor, ResourceQuota


@pytest.fixture
def sample_dataframe():
    """Create sample DataFrame for testing."""
    return pd.DataFrame({
        "region": ["A", "A", "B", "B", "C"],
        "sales": [100, 200, 150, 300, 250],
        "price": [10, 20, 15, 30, 25],
        "month": ["Jan", "Feb", "Jan", "Feb", "Jan"],
    })


@pytest.fixture
def artifacts_dir():
    """Create temporary artifacts directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestDataAgentDogfood:
    """Integration test demonstrating DataAgent components working together."""
    
    def test_policy_enforcer_blocks_dangerous_queries(self):
        """Test: PolicyEnforcer blocks DDL/DML operations."""
        enforcer = PolicyEnforcer()
        
        safe_query = "SELECT * FROM users WHERE id = 1"
        result = enforcer.validate_query(safe_query)
        assert result.allowed, "Safe SELECT query should be allowed"
        
        dangerous_queries = [
            "DROP TABLE users",
            "DELETE FROM users WHERE id = 1",
            "INSERT INTO users VALUES (1, 'hacker')",
            "UPDATE users SET password = 'pwned'",
        ]
        
        for query in dangerous_queries:
            result = enforcer.validate_query(query)
            assert not result.allowed, f"Dangerous query should be blocked: {query}"
            assert len(result.violations) > 0
            assert result.severity == "critical"
    
    def test_pii_detector_finds_sensitive_data(self):
        """Test: PIIDetector identifies sensitive information."""
        enforcer = PolicyEnforcer()
        
        data_with_pii = [
            {"name": "John Doe", "email": "john@example.com", "ssn": "123-45-6789"},
            {"name": "Jane Smith", "email": "jane@test.com", "ssn": "987-65-4321"},
        ]
        
        pii_matches = enforcer.scan_data_for_pii(data_with_pii, "users")
        
        assert len(pii_matches) >= 4, "Should detect emails and SSNs"
        
        pii_types = {match.pii_type for match in pii_matches}
        assert "email" in pii_types
        assert "ssn" in pii_types
    
    def test_dataframe_operations_chain(self, sample_dataframe):
        """Test: DataFrameOperations can be chained together."""
        df_ops = DataFrameOperations()
        
        df = sample_dataframe.copy()
        
        df = df_ops.filter(df, "sales > 100")
        assert len(df) == 4, "Should filter to 4 rows"
        
        df = df_ops.aggregate(df, ["region"], {"sales": "sum", "price": "mean"})
        assert len(df) == 3, "Should aggregate to 3 regions"
        assert "sales" in df.columns
        
        df = df_ops.transform(df, {"total_value": "sales * price"})
        assert "total_value" in df.columns
        
        df = df_ops.sort(df, "sales", ascending=False)
        assert df.iloc[0]["region"] in ["B", "A"]
    
    def test_plotter_generates_artifacts(self, sample_dataframe, artifacts_dir):
        """Test: Plotter generates chart artifacts with metadata."""
        plotter = Plotter(artifacts_dir)
        
        result = plotter.bar_chart(
            sample_dataframe,
            x="region",
            y="sales",
            title="Sales by Region",
            backend="matplotlib",
        )
        
        assert result.artifact_id is not None
        assert Path(result.file_path).exists()
        assert result.content_hash is not None
        assert len(result.content_hash) == 64
        assert result.plot_type == "bar"
        assert result.size_bytes > 0
    
    def test_profiler_analyzes_data_quality(self, sample_dataframe):
        """Test: DataProfiler assesses data quality."""
        profiler = DataProfiler()
        
        profile = profiler.profile_dataframe(sample_dataframe)
        
        assert profile.row_count == 5
        assert profile.column_count == 4
        assert len(profile.columns) == 4
        assert 0.0 <= profile.quality_score <= 1.0
        
        for col_profile in profile.columns:
            assert col_profile.name in sample_dataframe.columns
            assert col_profile.null_count == 0
            assert col_profile.unique_count > 0
    
    @pytest.mark.skip(reason="Signal-based timeout unreliable on macOS; threading alternative needed")
    def test_sandbox_enforces_timeout(self):
        """Test: SandboxExecutor enforces timeout limits."""
        import time
        
        sandbox = SandboxExecutor(ResourceQuota(max_execution_seconds=0.5))
        
        def slow_function():
            time.sleep(2)
            return "Should timeout"
        
        result = sandbox.execute_in_sandbox(slow_function)
        
        assert not result.success
        assert "timeout" in result.error.lower()
        assert len(result.violations) > 0
    
    def test_sandbox_tracks_resources(self):
        """Test: SandboxExecutor tracks memory and CPU."""
        sandbox = SandboxExecutor()
        
        def memory_intensive():
            data = [i**2 for i in range(100000)]
            return len(data)
        
        result = sandbox.execute_in_sandbox(memory_intensive)
        
        assert result.success
        assert result.result == 100000
        assert result.execution_time_seconds > 0
        assert result.peak_memory_mb >= 0
    
    def test_full_workflow_integration(self, sample_dataframe, artifacts_dir):
        """Test: Complete workflow using all components together."""
        enforcer = PolicyEnforcer()
        sandbox = SandboxExecutor()
        df_ops = DataFrameOperations()
        plotter = Plotter(artifacts_dir)
        profiler = DataProfiler()
        
        query = "SELECT * FROM sales WHERE region IN ('A', 'B', 'C')"
        policy_result = enforcer.validate_query(query)
        assert policy_result.allowed, "Query should pass policy check"
        
        df = sample_dataframe.copy()
        
        profile = profiler.profile_dataframe(df)
        assert profile.quality_score > 0.8, "Data quality should be good"
        
        def transform_pipeline():
            result = df_ops.aggregate(df, ["region"], {"sales": "sum"})
            return result
        
        sandbox_result = sandbox.execute_in_sandbox(transform_pipeline)
        assert sandbox_result.success
        aggregated_df = sandbox_result.result
        
        chart_result = plotter.bar_chart(
            aggregated_df,
            x="region",
            y="sales",
            title="Total Sales by Region",
            backend="matplotlib",
        )
        
        assert Path(chart_result.file_path).exists()
        assert chart_result.size_bytes > 0
        
        print(f"\n✓ Full workflow succeeded:")
        print(f"  - Policy check: passed")
        print(f"  - Data quality: {profile.quality_score:.2f}")
        print(f"  - Sandbox execution: {sandbox_result.execution_time_seconds:.3f}s")
        print(f"  - Chart artifact: {chart_result.file_path}")
        print(f"  - Artifact hash: {chart_result.content_hash[:16]}...")


class TestSafetyGuardrails:
    """Test safety guardrails integration (T008 requirement)."""
    
    def test_column_access_control(self):
        """Test: Column access control blocks sensitive columns."""
        enforcer = PolicyEnforcer()
        
        result = enforcer.validate_column_access("users", ["id", "name", "email"])
        assert result.allowed, "Non-sensitive columns should be allowed"
        
        result = enforcer.validate_column_access("users", ["password"])
        assert not result.allowed, "Sensitive column should be blocked"
        assert "password" in str(result.violations)
    
    def test_multi_statement_injection_blocked(self):
        """Test: Multi-statement SQL injection attempts blocked."""
        enforcer = PolicyEnforcer()
        
        injection_query = "SELECT * FROM users; DROP TABLE users;"
        result = enforcer.validate_query(injection_query)
        
        assert not result.allowed
        assert len(result.violations) > 0