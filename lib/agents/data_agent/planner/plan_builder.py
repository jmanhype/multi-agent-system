"""Plan builder for DataAgent task orchestration.

Constructs validated DAGs from parsed intents with tool mapping and cost estimates.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Union
from enum import Enum
import uuid

from lib.agents.data_agent.planner.intent_parser import Operation


class ToolType(Enum):
    """Available tool types for plan steps."""
    SQL_RUNNER = "sql_runner"
    DF_OPERATIONS = "df_operations"
    PLOTTER = "plotter"
    PROFILER = "profiler"


@dataclass
class PlanStep:
    """Single step in execution plan.
    
    Attributes:
        step_id: Unique identifier
        operation: Logical operation description
        tool: Selected tool for execution
        dependencies: IDs of prerequisite steps
        estimated_cost: Estimated execution cost (seconds)
        invariants: Constraints that must hold (e.g., "row_count < 10000")
    """
    step_id: str
    operation: str
    tool: ToolType
    dependencies: List[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    invariants: List[str] = field(default_factory=list)


@dataclass
class Plan:
    """Complete analysis execution plan.
    
    Attributes:
        plan_id: Unique identifier
        objective: High-level goal
        steps: Ordered list of execution steps
        total_cost: Sum of step cost estimates
        deliverables: Expected output artifacts
    """
    plan_id: str
    objective: str
    steps: List[PlanStep]
    total_cost: float
    deliverables: List[str]


class PlanBuilder:
    """Build validated execution plans from parsed intents.
    
    Features:
    - Tool selection based on operation patterns
    - DAG validation (no cycles)
    - Cost estimation per FR-007 to FR-011
    - Invariant propagation
    """
    
    TOOL_COSTS = {
        ToolType.SQL_RUNNER: 2.0,
        ToolType.DF_OPERATIONS: 1.0,
        ToolType.PLOTTER: 1.5,
        ToolType.PROFILER: 0.5,
    }
    
    def build_plan(
        self,
        objective: str,
        operations: Union[List[str], List[Operation]],
        deliverables: List[str],
        constraints: List[str],
    ) -> Plan:
        """Build execution plan from parsed intent.
        
        Supports two modes:
        1. List[Operation]: Full DAG with explicit dependencies (recommended)
        2. List[str]: Legacy linear chain (each step depends on previous)
        
        Args:
            objective: Analysis goal
            operations: Either Operation objects with dependencies or simple string list
            deliverables: Expected outputs
            constraints: Safety constraints
        
        Returns:
            Validated Plan with DAG structure and cost estimates
        
        Raises:
            ValueError: If plan contains cycles or invalid dependencies
        
        Example (with dependencies):
            >>> from lib.agents.data_agent.planner import Operation
            >>> builder = PlanBuilder()
            >>> ops = [
            ...     Operation("op1", "Query sales", []),
            ...     Operation("op2", "Query customers", []),
            ...     Operation("op3", "Join data", ["op1", "op2"]),
            ... ]
            >>> plan = builder.build_plan("Join analysis", ops, ["table"], [])
            >>> len(plan.steps)
            3
        
        Example (legacy linear):
            >>> builder = PlanBuilder()
            >>> plan = builder.build_plan(
            ...     objective="Top customers by revenue",
            ...     operations=["query sales", "aggregate", "sort", "visualize"],
            ...     deliverables=["table", "chart"],
            ...     constraints=["row_limit=1000"]
            ... )
            >>> len(plan.steps)
            4
        """
        plan_id = str(uuid.uuid4())
        steps = []
        steps_map = {}
        
        if operations and isinstance(operations[0], Operation):
            # Two-pass approach: index operations, create steps, then resolve dependencies
            op_index: Dict[str, Operation] = {op.id: op for op in operations}
            step_index: Dict[str, PlanStep] = {}
            
            # Pass 1: Create all steps without dependencies
            for op in operations:
                step_id = f"{plan_id[:8]}-{op.id}"
                tool = self._select_tool(op.description)
                cost = self.TOOL_COSTS.get(tool, 1.0)
                invariants = self._extract_invariants(op.description, constraints)
                
                step = PlanStep(
                    step_id=step_id,
                    operation=op.description,
                    tool=tool,
                    dependencies=[],
                    estimated_cost=cost,
                    invariants=invariants,
                )
                steps.append(step)
                step_index[op.id] = step
            
            # Pass 2: Resolve dependencies with validation
            for op in operations:
                target_step = step_index[op.id]
                resolved_deps: List[str] = []
                for dep_id in op.dependencies or []:
                    if dep_id not in step_index:
                        raise ValueError(f"Operation '{op.id}' has invalid dependency reference '{dep_id}'")
                    resolved_deps.append(step_index[dep_id].step_id)
                target_step.dependencies = resolved_deps
        else:
            for i, operation in enumerate(operations):
                step_id = f"{plan_id[:8]}-step-{i}"
                tool = self._select_tool(operation)
                dependencies = [steps[i-1].step_id] if i > 0 else []
                cost = self.TOOL_COSTS.get(tool, 1.0)
                invariants = self._extract_invariants(operation, constraints)
                
                step = PlanStep(
                    step_id=step_id,
                    operation=operation,
                    tool=tool,
                    dependencies=dependencies,
                    estimated_cost=cost,
                    invariants=invariants,
                )
                steps.append(step)
        
        self._validate_dag(steps)
        
        total_cost = sum(step.estimated_cost for step in steps)
        
        return Plan(
            plan_id=plan_id,
            objective=objective,
            steps=steps,
            total_cost=total_cost,
            deliverables=deliverables,
        )
    
    def _select_tool(self, operation: str) -> ToolType:
        """Select appropriate tool for operation.
        
        Pattern matching on operation description to choose tool.
        """
        operation_lower = operation.lower()
        
        if any(kw in operation_lower for kw in ["query", "select", "fetch", "sql"]):
            return ToolType.SQL_RUNNER
        elif any(kw in operation_lower for kw in ["plot", "chart", "visualize", "graph"]):
            return ToolType.PLOTTER
        elif any(kw in operation_lower for kw in ["profile", "schema", "discover"]):
            return ToolType.PROFILER
        else:
            return ToolType.DF_OPERATIONS
    
    def _extract_invariants(
        self,
        operation: str,
        constraints: List[str],
    ) -> List[str]:
        """Extract invariants for operation from constraints."""
        invariants = []
        
        if "filter" in operation.lower() or "where" in operation.lower():
            invariants.append("filter_before_aggregate")
        
        for constraint in constraints:
            if "row" in constraint.lower() or "limit" in constraint.lower():
                invariants.append(constraint)
        
        return invariants
    
    def _validate_dag(self, steps: List[PlanStep]) -> None:
        """Validate that plan forms a directed acyclic graph.
        
        Raises:
            ValueError: If cycles detected or invalid dependencies
        """
        step_ids = {step.step_id for step in steps}
        
        for step in steps:
            for dep in step.dependencies:
                if dep not in step_ids:
                    raise ValueError(f"Step {step.step_id} has invalid dependency: {dep}")
        
        if self._has_cycle(steps):
            raise ValueError("Plan contains cycle - DAG validation failed")
    
    def _has_cycle(self, steps: List[PlanStep]) -> bool:
        """Check for cycles using DFS."""
        adj = {step.step_id: step.dependencies for step in steps}
        visited = set()
        rec_stack = set()
        
        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for step in steps:
            if step.step_id not in visited:
                if dfs(step.step_id):
                    return True
        
        return False
    
    def add_step(
        self,
        plan: Plan,
        operation: str,
        dependencies: List[str],
        constraints: Optional[List[str]] = None,
    ) -> Plan:
        """Add new step to existing plan.
        
        Args:
            plan: Existing plan to extend
            operation: New operation to add
            dependencies: IDs of prerequisite steps
            constraints: Optional constraints
        
        Returns:
            Updated plan with new step
        
        Raises:
            ValueError: If adding step creates cycle
        """
        step_id = str(uuid.uuid4())
        tool = self._select_tool(operation)
        cost = self.TOOL_COSTS.get(tool, 1.0)
        invariants = self._extract_invariants(operation, constraints or [])
        
        new_step = PlanStep(
            step_id=step_id,
            operation=operation,
            tool=tool,
            dependencies=dependencies,
            estimated_cost=cost,
            invariants=invariants,
        )
        
        updated_steps = plan.steps + [new_step]
        self._validate_dag(updated_steps)
        
        return Plan(
            plan_id=plan.plan_id,
            objective=plan.objective,
            steps=updated_steps,
            total_cost=plan.total_cost + cost,
            deliverables=plan.deliverables,
        )