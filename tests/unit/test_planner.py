"""Unit tests for planner components."""

import pytest
from lib.agents.data_agent.planner.plan_builder import (
    PlanBuilder,
    PlanStep,
    Plan,
    ToolType,
)
from lib.agents.data_agent.planner.intent_parser import Operation


class TestPlanBuilder:
    """Unit tests for PlanBuilder."""
    
    def test_build_plan_with_operations_list(self):
        builder = PlanBuilder()
        
        operations = [
            Operation("op1", "Query sales data", []),
            Operation("op2", "Filter results", ["op1"]),
            Operation("op3", "Aggregate totals", ["op2"]),
        ]
        
        plan = builder.build_plan(
            objective="Calculate sales totals",
            operations=operations,
            deliverables=["table"],
            constraints=["row_limit=1000"],
        )
        
        assert plan.objective == "Calculate sales totals"
        assert len(plan.steps) == 3
        assert plan.deliverables == ["table"]
        assert plan.total_cost > 0
        
        assert plan.steps[0].operation == "Query sales data"
        assert plan.steps[0].tool == ToolType.SQL_RUNNER
        assert plan.steps[0].dependencies == []
        
        assert plan.steps[1].operation == "Filter results"
        assert plan.steps[1].dependencies == [plan.steps[0].step_id]
        
        assert plan.steps[2].dependencies == [plan.steps[1].step_id]
    
    def test_build_plan_with_string_list_legacy(self):
        builder = PlanBuilder()
        
        operations = ["query sales", "aggregate", "sort", "visualize"]
        
        plan = builder.build_plan(
            objective="Top customers by revenue",
            operations=operations,
            deliverables=["table", "chart"],
            constraints=["row_limit=1000"],
        )
        
        assert len(plan.steps) == 4
        assert plan.steps[0].dependencies == []
        assert plan.steps[1].dependencies == [plan.steps[0].step_id]
        assert plan.steps[2].dependencies == [plan.steps[1].step_id]
        assert plan.steps[3].dependencies == [plan.steps[2].step_id]
    
    def test_tool_selection_sql(self):
        builder = PlanBuilder()
        
        assert builder._select_tool("Query sales data") == ToolType.SQL_RUNNER
        assert builder._select_tool("SELECT * FROM users") == ToolType.SQL_RUNNER
        assert builder._select_tool("Fetch records") == ToolType.SQL_RUNNER
    
    def test_tool_selection_plotter(self):
        builder = PlanBuilder()
        
        assert builder._select_tool("Create bar chart") == ToolType.PLOTTER
        assert builder._select_tool("Visualize trends") == ToolType.PLOTTER
        assert builder._select_tool("Plot distribution") == ToolType.PLOTTER
    
    def test_tool_selection_profiler(self):
        builder = PlanBuilder()
        
        assert builder._select_tool("Profile dataset") == ToolType.PROFILER
        assert builder._select_tool("Discover schema") == ToolType.PROFILER
    
    def test_tool_selection_df_operations(self):
        builder = PlanBuilder()
        
        assert builder._select_tool("Aggregate values") == ToolType.DF_OPERATIONS
        assert builder._select_tool("Join tables") == ToolType.DF_OPERATIONS
        assert builder._select_tool("Transform data") == ToolType.DF_OPERATIONS
    
    def test_extract_invariants(self):
        builder = PlanBuilder()
        
        invariants = builder._extract_invariants(
            "Filter WHERE age > 18",
            ["row_limit=1000", "no_pii=true"],
        )
        
        assert "filter_before_aggregate" in invariants
        assert "row_limit=1000" in invariants
    
    def test_dag_validation_no_cycles(self):
        builder = PlanBuilder()
        
        operations = [
            Operation("op1", "Step 1", []),
            Operation("op2", "Step 2", ["op1"]),
            Operation("op3", "Step 3", ["op2"]),
        ]
        
        plan = builder.build_plan(
            objective="Test",
            operations=operations,
            deliverables=["table"],
            constraints=[],
        )
        
        assert len(plan.steps) == 3
    
    def test_dag_validation_detects_cycle(self):
        builder = PlanBuilder()
        plan_id = "test"
        
        steps = [
            PlanStep(
                step_id=f"{plan_id}-1",
                operation="Step 1",
                tool=ToolType.SQL_RUNNER,
                dependencies=[f"{plan_id}-2"],
            ),
            PlanStep(
                step_id=f"{plan_id}-2",
                operation="Step 2",
                tool=ToolType.SQL_RUNNER,
                dependencies=[f"{plan_id}-1"],
            ),
        ]
        
        with pytest.raises(ValueError, match="cycle"):
            builder._validate_dag(steps)
    
    def test_dag_validation_invalid_dependency(self):
        builder = PlanBuilder()
        
        operations = [
            Operation("op1", "Step 1", []),
            Operation("op2", "Step 2", ["op_nonexistent"]),
        ]
        
        with pytest.raises(ValueError, match="invalid dependency"):
            builder.build_plan(
                objective="Test",
                operations=operations,
                deliverables=["table"],
                constraints=[],
            )
    
    def test_parallel_operations(self):
        builder = PlanBuilder()
        
        operations = [
            Operation("op1", "Query sales", []),
            Operation("op2", "Query customers", []),
            Operation("op3", "Join data", ["op1", "op2"]),
        ]
        
        plan = builder.build_plan(
            objective="Join analysis",
            operations=operations,
            deliverables=["table"],
            constraints=[],
        )
        
        assert len(plan.steps) == 3
        assert len(plan.steps[2].dependencies) == 2
        assert plan.steps[0].step_id in plan.steps[2].dependencies
        assert plan.steps[1].step_id in plan.steps[2].dependencies
    
    def test_add_step_to_plan(self):
        builder = PlanBuilder()
        
        operations = [Operation("op1", "Query data", [])]
        
        plan = builder.build_plan(
            objective="Initial",
            operations=operations,
            deliverables=["table"],
            constraints=[],
        )
        
        updated_plan = builder.add_step(
            plan,
            operation="Visualize results",
            dependencies=[plan.steps[0].step_id],
            constraints=[],
        )
        
        assert len(updated_plan.steps) == 2
        assert updated_plan.steps[1].operation == "Visualize results"
        assert updated_plan.steps[1].tool == ToolType.PLOTTER
        assert updated_plan.total_cost == plan.total_cost + builder.TOOL_COSTS[ToolType.PLOTTER]
    
    def test_add_step_invalid_dependency(self):
        builder = PlanBuilder()
        
        operations = [
            Operation("op1", "Step 1", []),
            Operation("op2", "Step 2", ["op1"]),
        ]
        
        plan = builder.build_plan(
            objective="Test",
            operations=operations,
            deliverables=["table"],
            constraints=[],
        )
        
        with pytest.raises(ValueError, match="invalid dependency"):
            builder.add_step(
                plan,
                operation="Step 3",
                dependencies=["invalid_new_step"],
                constraints=[],
            )
    
    def test_cost_estimation(self):
        builder = PlanBuilder()
        
        operations = [
            Operation("op1", "Query data", []),
            Operation("op2", "Aggregate values", ["op1"]),
            Operation("op3", "Create chart", ["op2"]),
        ]
        
        plan = builder.build_plan(
            objective="Analysis",
            operations=operations,
            deliverables=["chart"],
            constraints=[],
        )
        
        expected_cost = (
            builder.TOOL_COSTS[ToolType.SQL_RUNNER] +
            builder.TOOL_COSTS[ToolType.DF_OPERATIONS] +
            builder.TOOL_COSTS[ToolType.PLOTTER]
        )
        
        assert plan.total_cost == expected_cost