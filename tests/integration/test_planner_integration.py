"""Integration tests for Planner workflow (T025-T026)."""

import pytest
from unittest.mock import Mock, patch
from lib.agents.data_agent.planner import (
    IntentParser,
    PlanBuilder,
)


class TestPlannerIntegration:
    """End-to-end tests for intent parsing → plan building workflow."""
    
    @patch('lib.agents.data_agent.planner.intent_parser.Anthropic')
    def test_full_planner_workflow(self, mock_anthropic):
        """Test complete flow from natural language to validated plan."""
        mock_response = Mock()
        mock_response.content = [Mock(text='''{
            "objective": "Identify top revenue-generating regions",
            "data_requirements": ["sales table", "region column", "revenue column"],
            "operations": [
                "Query sales data for Q4",
                "Group by region",
                "Aggregate revenue sum",
                "Sort descending by revenue",
                "Take top 5 regions",
                "Visualize as bar chart"
            ],
            "deliverables": ["ranked table", "bar chart"],
            "constraints": ["enforce row limit", "no PII access"]
        }''')]
        mock_anthropic.return_value.messages.create.return_value = mock_response
        
        parser = IntentParser(api_key="test-key")
        builder = PlanBuilder()
        
        parsed = parser.parse(
            "Show me the top 5 revenue-generating regions in Q4",
            ["sql_runner", "df_operations", "plotter"],
            schema_info={"columns": ["region", "revenue", "date"]},
        )
        
        assert parsed.objective == "Identify top revenue-generating regions"
        assert len(parsed.operations) == 6
        
        plan = builder.build_plan(
            objective=parsed.objective,
            operations=parsed.operations,
            deliverables=parsed.deliverables,
            constraints=parsed.constraints,
        )
        
        assert len(plan.steps) == 6
        assert plan.steps[0].dependencies == []
        assert all(len(step.dependencies) == 1 for step in plan.steps[1:])
        assert plan.total_cost > 0
        assert "bar chart" in plan.deliverables
    
    @patch('lib.agents.data_agent.planner.intent_parser.Anthropic')
    def test_planner_with_complex_dag(self, mock_anthropic):
        """Test plan building with multiple dependency paths."""
        mock_response = Mock()
        mock_response.content = [Mock(text='''{
            "objective": "Compare metrics across dimensions",
            "data_requirements": ["sales", "customers"],
            "operations": [
                "Query sales data",
                "Profile sales schema",
                "Query customer data",
                "Join sales with customers",
                "Calculate metrics"
            ],
            "deliverables": ["summary table"],
            "constraints": ["row_limit=10000"]
        }''')]
        mock_anthropic.return_value.messages.create.return_value = mock_response
        
        parser = IntentParser(api_key="test-key")
        builder = PlanBuilder()
        
        parsed = parser.parse("Compare sales and customer metrics", ["sql_runner", "df_operations", "profiler"])
        plan = builder.build_plan(
            objective=parsed.objective,
            operations=parsed.operations,
            deliverables=parsed.deliverables,
            constraints=parsed.constraints,
        )
        
        assert len(plan.steps) == 5
        
        for step in plan.steps:
            assert step.tool in [
                builder._select_tool(op) for op in parsed.operations
            ]
    
    def test_plan_extension_preserves_validity(self):
        """Test that adding steps to existing plan maintains DAG validity."""
        builder = PlanBuilder()
        
        initial_plan = builder.build_plan(
            objective="Base analysis",
            operations=["query data", "filter rows"],
            deliverables=["table"],
            constraints=[],
        )
        
        extended_plan = builder.add_step(
            initial_plan,
            operation="visualize results",
            dependencies=[initial_plan.steps[-1].step_id],
            constraints=[],
        )
        
        assert len(extended_plan.steps) == 3
        assert extended_plan.steps[2].dependencies == [initial_plan.steps[1].step_id]
        assert extended_plan.total_cost == initial_plan.total_cost + builder.TOOL_COSTS[extended_plan.steps[2].tool]
    
    def test_planner_enforces_constraints(self):
        """Test that constraints are propagated through planning."""
        builder = PlanBuilder()
        
        plan = builder.build_plan(
            objective="Constrained analysis",
            operations=["filter sensitive data", "aggregate totals"],
            deliverables=["summary"],
            constraints=["no_pii_access", "row_limit=1000", "timeout=30s"],
        )
        
        has_row_constraint = any(
            any("row" in inv.lower() or "limit" in inv.lower() for inv in step.invariants)
            for step in plan.steps
        )
        assert has_row_constraint