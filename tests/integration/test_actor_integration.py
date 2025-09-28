"""Integration tests for Actor component.

Tests end-to-end workflows including plan execution and self-repair.
"""

import pytest
from unittest.mock import Mock
import pandas as pd

from lib.agents.data_agent.actor import Actor, ExecutionStatus
from lib.agents.data_agent.planner import PlanBuilder, ToolType, PlanStep


class TestActorPlanExecution:
    """Integration tests for Actor executing complete plans."""
    
    def test_single_step_execution_success(self):
        """Actor must successfully execute single-step plan."""
        mock_sql = Mock(return_value=pd.DataFrame({"id": [1, 2], "value": [10, 20]}))
        tool_registry = {"sql_runner": mock_sql}
        actor = Actor(tool_registry=tool_registry)
        
        step = PlanStep(
            step_id="step-1",
            operation="Query sales data",
            tool=ToolType.SQL_RUNNER,
            dependencies=[],
            estimated_cost=2.0,
            invariants=[],
        )
        
        obs = actor.execute_step(step)
        
        assert obs.is_success()
        assert obs.result is not None
        assert mock_sql.called
    
    def test_multi_step_sequential_execution(self):
        """Actor must execute multi-step plan with sequential dependencies."""
        query_result = pd.DataFrame({"region": ["A", "B", "C"], "revenue": [100, 200, 150]})
        mock_sql = Mock(return_value=query_result)
        
        def mock_df_op(dataframe=None, operation=None, operation_type=None, **kwargs):
            if operation_type == "sort":
                return dataframe.sort_values("revenue", ascending=False)
            return dataframe
        
        def mock_plotter(data=None, title=None, chart_type=None, **kwargs):
            return {"chart_path": f"/tmp/chart_{chart_type}.png"}
        
        tool_registry = {
            "sql_runner": mock_sql,
            "df_operations": mock_df_op,
            "plotter": mock_plotter,
        }
        actor = Actor(tool_registry=tool_registry)
        
        steps = [
            PlanStep(
                step_id="step-1",
                operation="Query revenue by region",
                tool=ToolType.SQL_RUNNER,
                dependencies=[],
                estimated_cost=2.0,
                invariants=[],
            ),
            PlanStep(
                step_id="step-2",
                operation="Sort by revenue descending",
                tool=ToolType.DF_OPERATIONS,
                dependencies=["step-1"],
                estimated_cost=1.0,
                invariants=[],
            ),
            PlanStep(
                step_id="step-3",
                operation="Plot top regions as bar chart",
                tool=ToolType.PLOTTER,
                dependencies=["step-2"],
                estimated_cost=1.5,
                invariants=[],
            ),
        ]
        
        execution_context = {}
        observations = []
        
        for step in steps:
            if step.step_id == "step-2":
                execution_context["dataframe"] = query_result
            elif step.step_id == "step-3":
                execution_context["dataframe"] = query_result
            
            obs = actor.execute_step(step, execution_context)
            observations.append(obs)
        
        assert all(obs.is_success() for obs in observations)
        assert len(actor.execution_history) == 3
        assert observations[2].result["chart_path"].endswith(".png")
    
    def test_self_repair_success_after_retry(self):
        """Actor must successfully recover from transient failures."""
        call_count = 0
        
        def flaky_tool(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary connection timeout")
            return {"result": "success"}
        
        tool_registry = {"sql_runner": flaky_tool}
        actor = Actor(tool_registry=tool_registry)
        
        step = PlanStep(
            step_id="step-1",
            operation="Query with flaky connection",
            tool=ToolType.SQL_RUNNER,
            dependencies=[],
            estimated_cost=2.0,
            invariants=[],
        )
        
        obs = actor.execute_step(step)
        
        assert obs.is_success()
        assert obs.retry_count == 2
        assert call_count == 3
    
    def test_self_repair_max_retries_exceeded(self):
        """Actor must fail gracefully after max retries exceeded."""
        mock_tool = Mock(side_effect=ConnectionError("Persistent timeout"))
        tool_registry = {"sql_runner": mock_tool}
        actor = Actor(tool_registry=tool_registry)
        
        step = PlanStep(
            step_id="step-1",
            operation="Query with persistent failure",
            tool=ToolType.SQL_RUNNER,
            dependencies=[],
            estimated_cost=2.0,
            invariants=[],
        )
        
        obs = actor.execute_step(step)
        
        assert obs.status == ExecutionStatus.FAILURE
        assert obs.retry_count == 3
        assert "Max retries" in obs.error_message or obs.retry_count == 3
        assert mock_tool.call_count == 4
    
    def test_invariant_validation_enforcement(self):
        """Actor must enforce invariants before execution."""
        mock_tool = Mock(return_value=pd.DataFrame())
        tool_registry = {"df_operations": mock_tool}
        actor = Actor(tool_registry=tool_registry)
        
        step = PlanStep(
            step_id="step-1",
            operation="Aggregate revenue by region",
            tool=ToolType.DF_OPERATIONS,
            dependencies=[],
            estimated_cost=1.0,
            invariants=["filter_before_aggregate"],
        )
        
        obs = actor.execute_step(step)
        
        assert obs.status == ExecutionStatus.FAILURE
        assert "Invariant violation" in obs.error_message or "filter_before_aggregate" in obs.error_message
    
    def test_execution_summary_statistics(self):
        """Actor must track execution statistics accurately."""
        success_tool = Mock(return_value={"result": "ok"})
        failure_tool = Mock(side_effect=ValueError("Invalid"))
        
        call_count = 0
        def retry_tool(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Timeout")
            return {"result": "ok"}
        
        tool_registry = {
            "sql_runner": success_tool,
            "df_operations": failure_tool,
            "plotter": retry_tool,
        }
        actor = Actor(tool_registry=tool_registry)
        
        steps = [
            PlanStep("s1", "query", ToolType.SQL_RUNNER, [], 2.0, []),
            PlanStep("s2", "transform", ToolType.DF_OPERATIONS, [], 1.0, []),
            PlanStep("s3", "plot", ToolType.PLOTTER, [], 1.5, []),
        ]
        
        for step in steps:
            actor.execute_step(step)
        
        summary = actor.get_execution_summary()
        
        assert summary["total_executions"] == 3
        assert summary["successes"] == 2
        assert summary["failures"] == 1
        assert 0.0 <= summary["success_rate"] <= 1.0
        assert summary["avg_retries"] >= 0.0
    
    def test_tool_argument_extraction_sql(self):
        """Actor must correctly extract SQL runner arguments."""
        mock_sql = Mock(return_value=pd.DataFrame())
        tool_registry = {"sql_runner": mock_sql}
        schema_context = {"database": "test_db"}
        actor = Actor(tool_registry=tool_registry, schema_context=schema_context)
        
        step = PlanStep(
            step_id="step-1",
            operation="SELECT * FROM sales WHERE region = 'US'",
            tool=ToolType.SQL_RUNNER,
            dependencies=[],
            estimated_cost=2.0,
            invariants=["row_limit=5000"],
        )
        
        tool_call = actor.ground_step(step)
        
        assert "query" in tool_call.arguments
        assert tool_call.arguments["query"] == step.operation
        assert "database" in tool_call.arguments
        assert tool_call.arguments["database"] == "test_db"
        assert tool_call.arguments.get("limit") == 5000
    
    def test_tool_argument_extraction_dataframe_ops(self):
        """Actor must correctly extract DataFrame operations arguments."""
        mock_df_op = Mock(return_value=pd.DataFrame())
        tool_registry = {"df_operations": mock_df_op}
        actor = Actor(tool_registry=tool_registry)
        
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        context = {"dataframe": df}
        
        step = PlanStep(
            step_id="step-1",
            operation="Filter rows where revenue > 1000",
            tool=ToolType.DF_OPERATIONS,
            dependencies=[],
            estimated_cost=1.0,
            invariants=[],
        )
        
        tool_call = actor.ground_step(step, context)
        
        assert "operation" in tool_call.arguments
        assert "dataframe" in tool_call.arguments
        assert tool_call.arguments["operation_type"] == "filter"
    
    def test_tool_argument_extraction_plotter(self):
        """Actor must correctly extract plotter arguments."""
        mock_plotter = Mock(return_value={"chart_path": "/tmp/chart.png"})
        tool_registry = {"plotter": mock_plotter}
        actor = Actor(tool_registry=tool_registry)
        
        df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        context = {"dataframe": df}
        
        step = PlanStep(
            step_id="step-1",
            operation="Create bar chart of revenue by region",
            tool=ToolType.PLOTTER,
            dependencies=[],
            estimated_cost=1.5,
            invariants=[],
        )
        
        tool_call = actor.ground_step(step, context)
        
        assert "title" in tool_call.arguments
        assert "data" in tool_call.arguments
        assert tool_call.arguments["chart_type"] == "bar"