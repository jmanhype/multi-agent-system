"""Contract tests for Planner components (T025-T026)."""

import pytest
from unittest.mock import Mock, patch
from lib.agents.data_agent.planner import (
    IntentParser,
    ParsedIntent,
    PlanBuilder,
    Plan,
    PlanStep,
    ToolType,
)


class TestIntentParserContract:
    """Validate IntentParser adheres to contract specifications."""
    
    @patch('lib.agents.data_agent.planner.intent_parser.Anthropic')
    def test_parse_returns_parsed_intent(self, mock_anthropic):
        """IntentParser.parse() must return ParsedIntent with required fields."""
        mock_response = Mock()
        mock_response.content = [Mock(text='{"objective": "test", "data_requirements": [], "operations": [], "deliverables": [], "constraints": []}')]
        mock_anthropic.return_value.messages.create.return_value = mock_response
        
        parser = IntentParser(api_key="test-key")
        result = parser.parse("Show me sales", ["sql_runner"], None)
        
        assert isinstance(result, ParsedIntent)
        assert hasattr(result, 'objective')
        assert hasattr(result, 'data_requirements')
        assert hasattr(result, 'operations')
        assert hasattr(result, 'deliverables')
        assert hasattr(result, 'constraints')
    
    @patch('lib.agents.data_agent.planner.intent_parser.Anthropic')
    def test_parse_with_schema_info(self, mock_anthropic):
        """IntentParser.parse() must accept optional schema_info parameter."""
        mock_response = Mock()
        mock_response.content = [Mock(text='{"objective": "test", "data_requirements": [], "operations": [], "deliverables": []}')]
        mock_anthropic.return_value.messages.create.return_value = mock_response
        
        parser = IntentParser(api_key="test-key")
        schema = {"fingerprint": "abc123", "columns": ["id", "name"]}
        result = parser.parse("Query customers", ["sql_runner"], schema)
        
        assert isinstance(result, ParsedIntent)


class TestPlanBuilderContract:
    """Validate PlanBuilder adheres to contract specifications."""
    
    def test_build_plan_returns_plan(self):
        """PlanBuilder.build_plan() must return Plan with required fields."""
        builder = PlanBuilder()
        plan = builder.build_plan(
            objective="Test analysis",
            operations=["query data", "aggregate"],
            deliverables=["table"],
            constraints=["row_limit=1000"],
        )
        
        assert isinstance(plan, Plan)
        assert hasattr(plan, 'plan_id')
        assert hasattr(plan, 'objective')
        assert hasattr(plan, 'steps')
        assert hasattr(plan, 'total_cost')
        assert hasattr(plan, 'deliverables')
        assert len(plan.steps) == 2
    
    def test_plan_steps_have_dependencies(self):
        """Plan steps must maintain dependency ordering."""
        builder = PlanBuilder()
        plan = builder.build_plan(
            objective="Multi-step",
            operations=["fetch data", "filter", "plot"],
            deliverables=["chart"],
            constraints=[],
        )
        
        assert plan.steps[0].dependencies == []
        assert len(plan.steps[1].dependencies) == 1
        assert plan.steps[1].dependencies[0] == plan.steps[0].step_id
    
    def test_plan_has_cost_estimate(self):
        """Plan must include total_cost as sum of step costs."""
        builder = PlanBuilder()
        plan = builder.build_plan(
            objective="Cost test",
            operations=["query", "plot"],
            deliverables=["chart"],
            constraints=[],
        )
        
        assert plan.total_cost > 0
        assert plan.total_cost == sum(step.estimated_cost for step in plan.steps)
    
    def test_dag_validation_rejects_invalid_dependencies(self):
        """PlanBuilder must reject plans with invalid dependencies."""
        builder = PlanBuilder()
        plan = builder.build_plan(
            objective="Base plan",
            operations=["step1"],
            deliverables=[],
            constraints=[],
        )
        
        with pytest.raises(ValueError, match="invalid dependency"):
            builder.add_step(
                plan,
                operation="invalid step",
                dependencies=["nonexistent-step-id"],
                constraints=[],
            )
    
    def test_tool_selection_logic(self):
        """PlanBuilder must select appropriate tools based on operations."""
        builder = PlanBuilder()
        plan = builder.build_plan(
            objective="Tool selection",
            operations=["query database", "filter rows", "plot bar chart", "profile schema"],
            deliverables=[],
            constraints=[],
        )
        
        assert plan.steps[0].tool == ToolType.SQL_RUNNER
        assert plan.steps[1].tool == ToolType.DF_OPERATIONS
        assert plan.steps[2].tool == ToolType.PLOTTER
        assert plan.steps[3].tool == ToolType.PROFILER
    
    def test_invariants_extracted_from_constraints(self):
        """PlanBuilder must extract and propagate invariants."""
        builder = PlanBuilder()
        plan = builder.build_plan(
            objective="Invariants test",
            operations=["filter data", "aggregate"],
            deliverables=[],
            constraints=["row_limit=5000", "enforce timeout"],
        )
        
        filter_step = plan.steps[0]
        assert any("filter_before_aggregate" in inv for inv in filter_step.invariants)
        assert any("row" in inv.lower() or "limit" in inv.lower() for inv in filter_step.invariants)


class TestPlanStepContract:
    """Validate PlanStep structure."""
    
    def test_plan_step_has_required_fields(self):
        """PlanStep must have all required fields."""
        step = PlanStep(
            step_id="test-123",
            operation="test operation",
            tool=ToolType.SQL_RUNNER,
            dependencies=[],
            estimated_cost=1.5,
            invariants=["constraint1"],
        )
        
        assert step.step_id == "test-123"
        assert step.operation == "test operation"
        assert step.tool == ToolType.SQL_RUNNER
        assert step.dependencies == []
        assert step.estimated_cost == 1.5
        assert step.invariants == ["constraint1"]