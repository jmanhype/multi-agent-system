"""Integration tests for DataAgent orchestrator."""

import pytest
from unittest.mock import Mock, MagicMock
import pandas as pd
import tempfile
from pathlib import Path

from lib.agents.data_agent.agent import DataAgent, AnalysisRequest, AnalysisStatus


class TestDataAgentOrchestration:
    """Integration tests for end-to-end DataAgent workflows."""
    
    def test_successful_analysis_workflow(self):
        """DataAgent must complete full analysis workflow successfully."""
        # Mock tools
        mock_sql = Mock(return_value=pd.DataFrame({"id": [1, 2], "value": [10, 20]}))
        mock_df_ops = Mock(return_value=pd.DataFrame({"id": [1, 2], "value": [10, 20]}))
        mock_plotter = Mock(return_value={"chart_path": "/tmp/chart.png"})
        
        tool_registry = {
            "sql_runner": mock_sql,
            "df_operations": mock_df_ops,
            "plotter": mock_plotter,
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = DataAgent(
                tool_registry=tool_registry,
                recipe_store_path=str(Path(tmpdir) / "recipes.db"),
                audit_log_path=str(Path(tmpdir) / "audit.jsonl"),
            )
            
            request = AnalysisRequest(
                request_id="test-req-1",
                intent="Analyze sales data and create visualization",
                data_sources=["sales_db"],
                deliverables=["table", "chart"],
            )
            
            response = agent.analyze(request)
            
            assert response.status == AnalysisStatus.SUCCESS
            assert response.request_id == "test-req-1"
            assert len(response.artifacts) > 0
            assert response.plan_ref is not None
            assert response.metrics["total_steps"] > 0
            assert response.metrics["failed_steps"] == 0
    
    def test_partial_success_with_failed_steps(self):
        """DataAgent must handle partial success when some steps fail."""
        # Mock tools - second tool fails
        mock_sql = Mock(return_value=pd.DataFrame({"id": [1], "value": [10]}))
        mock_df_ops = Mock(side_effect=ValueError("Invalid operation"))
        mock_plotter = Mock(return_value={"chart_path": "/tmp/chart.png"})
        
        tool_registry = {
            "sql_runner": mock_sql,
            "df_operations": mock_df_ops,
            "plotter": mock_plotter,
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = DataAgent(
                tool_registry=tool_registry,
                recipe_store_path=str(Path(tmpdir) / "recipes.db"),
                audit_log_path=str(Path(tmpdir) / "audit.jsonl"),
            )
            
            request = AnalysisRequest(
                request_id="test-req-2",
                intent="Process data with transformations",
                data_sources=["data_db"],
            )
            
            response = agent.analyze(request)
            
            # Should be partial success (some steps worked)
            assert response.status in [AnalysisStatus.PARTIAL, AnalysisStatus.FAILURE]
            assert response.error_message is not None
            assert "Invalid operation" in response.error_message or response.metrics["failed_steps"] > 0
    
    def test_progress_callback_invoked(self):
        """DataAgent must invoke progress callback during analysis."""
        mock_tool = Mock(return_value=pd.DataFrame({"x": [1]}))
        tool_registry = {"sql_runner": mock_tool}
        
        progress_calls = []
        
        def progress_callback(message: str, progress: float):
            progress_calls.append((message, progress))
        
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = DataAgent(
                tool_registry=tool_registry,
                recipe_store_path=str(Path(tmpdir) / "recipes.db"),
                audit_log_path=str(Path(tmpdir) / "audit.jsonl"),
            )
            
            agent.set_progress_callback(progress_callback)
            
            request = AnalysisRequest(
                request_id="test-req-3",
                intent="Quick query",
                data_sources=["db"],
            )
            
            agent.analyze(request)
            
            assert len(progress_calls) > 0
            # First call should be 0.0, last should be 1.0
            assert progress_calls[0][1] == 0.0
            assert progress_calls[-1][1] == 1.0
    
    def test_audit_trail_completeness(self):
        """DataAgent must log all events to audit trail."""
        mock_tool = Mock(return_value=pd.DataFrame({"x": [1]}))
        tool_registry = {"sql_runner": mock_tool}
        
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = DataAgent(
                tool_registry=tool_registry,
                recipe_store_path=str(Path(tmpdir) / "recipes.db"),
                audit_log_path=str(Path(tmpdir) / "audit.jsonl"),
            )
            
            request = AnalysisRequest(
                request_id="test-req-4",
                intent="Test audit trail",
                data_sources=["db"],
            )
            
            agent.analyze(request)
            
            # Verify audit log has entries
            trace = agent.get_request_trace("test-req-4")
            
            assert len(trace) > 0
            
            # Should have at least: request, plan, completion
            event_types = {entry.event_type for entry in trace}
            assert "request_submitted" in event_types
            assert "analysis_completed" in event_types
    
    def test_error_handling_for_orchestration_failure(self):
        """DataAgent must handle catastrophic failures gracefully."""
        # Tool that raises during execution
        mock_tool = Mock(side_effect=RuntimeError("Database connection lost"))
        tool_registry = {"sql_runner": mock_tool}
        
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = DataAgent(
                tool_registry=tool_registry,
                recipe_store_path=str(Path(tmpdir) / "recipes.db"),
                audit_log_path=str(Path(tmpdir) / "audit.jsonl"),
            )
            
            request = AnalysisRequest(
                request_id="test-req-5",
                intent="This will fail",
                data_sources=["db"],
            )
            
            response = agent.analyze(request)
            
            assert response.status == AnalysisStatus.FAILURE
            assert response.error_message is not None
            assert "Database connection lost" in response.error_message or response.metrics.get("error_id")
    
    def test_metrics_collection(self):
        """DataAgent must collect performance metrics."""
        mock_tool = Mock(return_value=pd.DataFrame({"x": [1, 2, 3]}))
        tool_registry = {"sql_runner": mock_tool}
        
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = DataAgent(
                tool_registry=tool_registry,
                recipe_store_path=str(Path(tmpdir) / "recipes.db"),
                audit_log_path=str(Path(tmpdir) / "audit.jsonl"),
            )
            
            request = AnalysisRequest(
                request_id="test-req-6",
                intent="Collect metrics",
                data_sources=["db"],
            )
            
            response = agent.analyze(request)
            
            assert "total_duration_seconds" in response.metrics
            assert response.metrics["total_duration_seconds"] > 0
            assert "total_steps" in response.metrics
            assert "successful_steps" in response.metrics
            assert "failed_steps" in response.metrics
            assert "artifact_count" in response.metrics
    
    def test_verify_audit_integrity(self):
        """DataAgent must allow audit integrity verification."""
        mock_tool = Mock(return_value=pd.DataFrame({"x": [1]}))
        tool_registry = {"sql_runner": mock_tool}
        
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = DataAgent(
                tool_registry=tool_registry,
                recipe_store_path=str(Path(tmpdir) / "recipes.db"),
                audit_log_path=str(Path(tmpdir) / "audit.jsonl"),
            )
            
            request = AnalysisRequest(
                request_id="test-req-7",
                intent="Test integrity",
                data_sources=["db"],
            )
            
            agent.analyze(request)
            
            is_valid, error = agent.verify_audit_integrity()
            
            assert is_valid is True
            assert error is None