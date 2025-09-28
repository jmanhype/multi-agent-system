"""Contract tests for Actor components.

Validates Actor interfaces and behavior contracts per TDD principles.
"""

import pytest
from unittest.mock import Mock

from lib.agents.data_agent.actor import Actor, ToolCall, Observation, ExecutionStatus
from lib.agents.data_agent.planner import PlanStep, ToolType


class TestObservationContracts:
    """Contract tests for Observation dataclass."""
    
    def test_observation_has_required_fields(self):
        """Observation must have step_id, status, result, error_message fields."""
        obs = Observation(
            step_id="step-1",
            status=ExecutionStatus.SUCCESS,
            result={"data": "test"},
            error_message=None,
            retry_count=0,
        )
        
        assert hasattr(obs, 'step_id')
        assert hasattr(obs, 'status')
        assert hasattr(obs, 'result')
        assert hasattr(obs, 'error_message')
        assert hasattr(obs, 'retry_count')
        assert hasattr(obs, 'metadata')
    
    def test_observation_is_success_method(self):
        """Observation.is_success() must return bool based on status."""
        success_obs = Observation(
            step_id="step-1",
            status=ExecutionStatus.SUCCESS,
        )
        failure_obs = Observation(
            step_id="step-2",
            status=ExecutionStatus.FAILURE,
            error_message="test error",
        )
        
        assert success_obs.is_success() is True
        assert failure_obs.is_success() is False
    
    def test_observation_is_recoverable_method(self):
        """Observation.is_recoverable() must detect transient failures."""
        timeout_obs = Observation(
            step_id="step-1",
            status=ExecutionStatus.FAILURE,
            error_message="Connection timeout",
        )
        permanent_obs = Observation(
            step_id="step-2",
            status=ExecutionStatus.FAILURE,
            error_message="Invalid syntax",
        )
        success_obs = Observation(
            step_id="step-3",
            status=ExecutionStatus.SUCCESS,
        )
        
        assert timeout_obs.is_recoverable() is True
        assert permanent_obs.is_recoverable() is False
        assert success_obs.is_recoverable() is False


class TestToolCallContracts:
    """Contract tests for ToolCall dataclass."""
    
    def test_toolcall_has_required_fields(self):
        """ToolCall must have tool_name, arguments, step_id fields."""
        tool_call = ToolCall(
            tool_name="sql_runner",
            arguments={"query": "SELECT * FROM test"},
            step_id="step-1",
        )
        
        assert hasattr(tool_call, 'tool_name')
        assert hasattr(tool_call, 'arguments')
        assert hasattr(tool_call, 'step_id')
        assert isinstance(tool_call.arguments, dict)


class TestActorContracts:
    """Contract tests for Actor class."""
    
    def test_actor_initialization(self):
        """Actor must accept tool_registry and optional schema_context."""
        tool_registry = {"sql_runner": Mock()}
        schema_context = {"database": "test_db"}
        
        actor = Actor(
            tool_registry=tool_registry,
            schema_context=schema_context,
        )
        
        assert actor.tool_registry == tool_registry
        assert actor.schema_context == schema_context
        assert hasattr(actor, 'execution_history')
        assert isinstance(actor.execution_history, list)
    
    def test_actor_ground_step_returns_toolcall(self):
        """Actor.ground_step() must return ToolCall object."""
        tool_registry = {"sql_runner": Mock()}
        actor = Actor(tool_registry=tool_registry)
        
        step = PlanStep(
            step_id="step-1",
            operation="Query sales data",
            tool=ToolType.SQL_RUNNER,
            dependencies=[],
            estimated_cost=2.0,
            invariants=[],
        )
        
        tool_call = actor.ground_step(step)
        
        assert isinstance(tool_call, ToolCall)
        assert tool_call.tool_name == "sql_runner"
        assert tool_call.step_id == "step-1"
        assert isinstance(tool_call.arguments, dict)
    
    def test_actor_ground_step_raises_on_missing_tool(self):
        """Actor.ground_step() must raise ValueError if tool not in registry."""
        tool_registry = {"sql_runner": Mock()}
        actor = Actor(tool_registry=tool_registry)
        
        step = PlanStep(
            step_id="step-1",
            operation="Plot data",
            tool=ToolType.PLOTTER,
            dependencies=[],
            estimated_cost=1.5,
            invariants=[],
        )
        
        with pytest.raises(ValueError, match="Tool .* not found in registry"):
            actor.ground_step(step)
    
    def test_actor_execute_with_repair_returns_observation(self):
        """Actor.execute_with_repair() must return Observation."""
        mock_tool = Mock(return_value={"result": "success"})
        tool_registry = {"sql_runner": mock_tool}
        actor = Actor(tool_registry=tool_registry)
        
        tool_call = ToolCall(
            tool_name="sql_runner",
            arguments={"query": "SELECT 1"},
            step_id="step-1",
        )
        
        obs = actor.execute_with_repair(tool_call)
        
        assert isinstance(obs, Observation)
        assert obs.step_id == "step-1"
        assert hasattr(obs, 'status')
        assert hasattr(obs, 'retry_count')
    
    def test_actor_execute_with_repair_success(self):
        """Actor.execute_with_repair() must return SUCCESS on successful execution."""
        mock_tool = Mock(return_value={"data": "test"})
        tool_registry = {"sql_runner": mock_tool}
        actor = Actor(tool_registry=tool_registry)
        
        tool_call = ToolCall(
            tool_name="sql_runner",
            arguments={"query": "SELECT 1"},
            step_id="step-1",
        )
        
        obs = actor.execute_with_repair(tool_call)
        
        assert obs.status == ExecutionStatus.SUCCESS
        assert obs.error_message is None
        assert obs.result is not None
        assert obs.retry_count == 0
        mock_tool.assert_called_once_with(query="SELECT 1")
    
    def test_actor_execute_with_repair_failure(self):
        """Actor.execute_with_repair() must return FAILURE and retry on errors."""
        mock_tool = Mock(side_effect=ValueError("Invalid query"))
        tool_registry = {"sql_runner": mock_tool}
        actor = Actor(tool_registry=tool_registry)
        
        tool_call = ToolCall(
            tool_name="sql_runner",
            arguments={"query": "INVALID"},
            step_id="step-1",
        )
        
        obs = actor.execute_with_repair(tool_call, max_retries=2)
        
        assert obs.status == ExecutionStatus.FAILURE
        assert obs.error_message is not None
        assert "ValueError" in obs.error_message
        assert obs.result is None
    
    def test_actor_execute_with_repair_retry_logic(self):
        """Actor.execute_with_repair() must retry recoverable failures."""
        mock_tool = Mock(side_effect=ConnectionError("Timeout"))
        tool_registry = {"sql_runner": mock_tool}
        actor = Actor(tool_registry=tool_registry)
        
        tool_call = ToolCall(
            tool_name="sql_runner",
            arguments={"query": "SELECT 1"},
            step_id="step-1",
        )
        
        obs = actor.execute_with_repair(tool_call, max_retries=3)
        
        assert obs.status == ExecutionStatus.FAILURE
        assert obs.retry_count == 3
        assert mock_tool.call_count > 1
    
    def test_actor_execute_step_convenience_method(self):
        """Actor.execute_step() must combine grounding and execution."""
        mock_tool = Mock(return_value={"result": "test"})
        tool_registry = {"sql_runner": mock_tool}
        actor = Actor(tool_registry=tool_registry)
        
        step = PlanStep(
            step_id="step-1",
            operation="Query test data",
            tool=ToolType.SQL_RUNNER,
            dependencies=[],
            estimated_cost=2.0,
            invariants=[],
        )
        
        obs = actor.execute_step(step)
        
        assert isinstance(obs, Observation)
        assert obs.step_id == "step-1"
        mock_tool.assert_called_once()
    
    def test_actor_tracks_execution_history(self):
        """Actor must maintain execution_history of Observations."""
        mock_tool = Mock(return_value={"result": "test"})
        tool_registry = {"sql_runner": mock_tool}
        actor = Actor(tool_registry=tool_registry)
        
        tool_call1 = ToolCall("sql_runner", {"query": "SELECT 1"}, "step-1")
        tool_call2 = ToolCall("sql_runner", {"query": "SELECT 2"}, "step-2")
        
        actor.execute_with_repair(tool_call1)
        actor.execute_with_repair(tool_call2)
        
        assert len(actor.execution_history) == 2
        assert all(isinstance(obs, Observation) for obs in actor.execution_history)
    
    def test_actor_get_execution_summary(self):
        """Actor.get_execution_summary() must return statistics dict."""
        mock_tool = Mock(return_value={"result": "test"})
        tool_registry = {"sql_runner": mock_tool}
        actor = Actor(tool_registry=tool_registry)
        
        summary = actor.get_execution_summary()
        
        assert isinstance(summary, dict)
        assert "total_executions" in summary
        assert "successes" in summary
        assert "failures" in summary
        assert "success_rate" in summary
        assert "avg_retries" in summary