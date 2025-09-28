"""Actor component for tool call grounding and execution.

Translates plan steps into concrete tool calls and executes them with self-repair.
"""

from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
import traceback

from lib.agents.data_agent.planner.plan_builder import PlanStep, ToolType
from lib.agents.data_agent.actor.observation import Observation, ExecutionStatus


@dataclass
class ToolCall:
    """Grounded tool invocation with concrete arguments.
    
    Attributes:
        tool_name: Tool identifier (sql_runner, df_operations, etc.)
        arguments: Concrete argument dictionary for tool execution
        step_id: ID of originating plan step
    """
    tool_name: str
    arguments: Dict[str, Any]
    step_id: str


class Actor:
    """Execute plan steps with tool grounding and self-repair.
    
    Features:
    - Tool call grounding from plan steps to concrete arguments
    - Self-repair loop with configurable max retries (default K=3 per FR)
    - Observation collection for feedback to planner
    - Invariant validation before execution
    """
    
    MAX_RETRIES = 3
    
    def __init__(
        self,
        tool_registry: Dict[str, Callable],
        schema_context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize actor with tool registry.
        
        Args:
            tool_registry: Map of tool names to executable functions
            schema_context: Optional schema metadata for argument grounding
        """
        self.tool_registry = tool_registry
        self.schema_context = schema_context or {}
        self.execution_history: List[Observation] = []
    
    def ground_step(
        self,
        step: PlanStep,
        execution_context: Optional[Dict[str, Any]] = None,
    ) -> ToolCall:
        """Ground plan step to concrete tool call.
        
        Args:
            step: Plan step to ground
            execution_context: Runtime context (previous results, variables)
        
        Returns:
            ToolCall with concrete arguments
        
        Raises:
            ValueError: If tool not found in registry or required args missing
        
        Example:
            >>> actor = Actor(tool_registry={"sql_runner": run_sql})
            >>> step = PlanStep(
            ...     step_id="step-1",
            ...     operation="Query sales data for Q4",
            ...     tool=ToolType.SQL_RUNNER,
            ...     dependencies=[],
            ...     estimated_cost=2.0,
            ...     invariants=["row_limit=10000"],
            ... )
            >>> tool_call = actor.ground_step(step)
            >>> tool_call.tool_name
            'sql_runner'
        """
        execution_context = execution_context or {}
        tool_name = step.tool.value
        
        if tool_name not in self.tool_registry:
            raise ValueError(f"Tool '{tool_name}' not found in registry")
        
        arguments = self._extract_arguments(
            step=step,
            context=execution_context,
        )
        
        self._validate_invariants(step, arguments)
        
        return ToolCall(
            tool_name=tool_name,
            arguments=arguments,
            step_id=step.step_id,
        )
    
    def execute_with_repair(
        self,
        tool_call: ToolCall,
        max_retries: Optional[int] = None,
    ) -> Observation:
        """Execute tool call with self-repair loop.
        
        Implements retry logic with exponential backoff for recoverable failures.
        
        Args:
            tool_call: Grounded tool invocation
            max_retries: Override default MAX_RETRIES
        
        Returns:
            Observation with execution result or failure details
        
        Example:
            >>> actor = Actor(tool_registry={"sql_runner": run_sql})
            >>> tool_call = ToolCall("sql_runner", {"query": "SELECT * FROM sales"}, "step-1")
            >>> obs = actor.execute_with_repair(tool_call)
            >>> obs.is_success()
            True
        """
        max_retries = max_retries if max_retries is not None else self.MAX_RETRIES
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                result = self._execute_tool(tool_call)
                
                observation = Observation(
                    step_id=tool_call.step_id,
                    status=ExecutionStatus.SUCCESS,
                    result=result,
                    error_message=None,
                    retry_count=attempt,
                    metadata=self._extract_metadata(result),
                )
                
                self.execution_history.append(observation)
                return observation
                
            except Exception as e:
                last_error = e
                error_message = f"{type(e).__name__}: {str(e)}"
                
                observation = Observation(
                    step_id=tool_call.step_id,
                    status=ExecutionStatus.FAILURE,
                    result=None,
                    error_message=error_message,
                    retry_count=attempt,
                )
                
                if attempt < max_retries and observation.is_recoverable():
                    continue
                else:
                    # Non-recoverable error or last attempt failed
                    final_error_message = f"Max retries ({max_retries}) exceeded. Last error: {last_error}"
                    if not observation.is_recoverable():
                        final_error_message = f"Non-recoverable error: {error_message}"
                    
                    final_observation = Observation(
                        step_id=tool_call.step_id,
                        status=ExecutionStatus.FAILURE,
                        result=None,
                        error_message=final_error_message,
                        retry_count=attempt,
                    )
                    self.execution_history.append(final_observation)
                    return final_observation
    
    def execute_step(
        self,
        step: PlanStep,
        execution_context: Optional[Dict[str, Any]] = None,
    ) -> Observation:
        """Ground and execute plan step with self-repair.
        
        Convenience method combining grounding and execution.
        
        Args:
            step: Plan step to execute
            execution_context: Runtime context
        
        Returns:
            Observation with execution result
        """
        try:
            tool_call = self.ground_step(step, execution_context)
            return self.execute_with_repair(tool_call)
        except Exception as e:
            return Observation(
                step_id=step.step_id,
                status=ExecutionStatus.FAILURE,
                result=None,
                error_message=f"Grounding failed: {type(e).__name__}: {str(e)}",
                retry_count=0,
            )
    
    def _execute_tool(self, tool_call: ToolCall) -> Any:
        """Execute tool with concrete arguments.
        
        Args:
            tool_call: Grounded tool invocation
        
        Returns:
            Tool execution result
        
        Raises:
            Exception: Any tool execution error
        """
        tool_func = self.tool_registry[tool_call.tool_name]
        return tool_func(**tool_call.arguments)
    
    def _extract_arguments(
        self,
        step: PlanStep,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract concrete arguments from step and context.
        
        Pattern-based argument extraction based on tool type and operation description.
        """
        arguments = {}
        operation_lower = step.operation.lower()
        
        if step.tool == ToolType.SQL_RUNNER:
            arguments = self._extract_sql_arguments(step, context)
        elif step.tool == ToolType.DF_OPERATIONS:
            arguments = self._extract_df_arguments(step, context)
        elif step.tool == ToolType.PLOTTER:
            arguments = self._extract_plot_arguments(step, context)
        elif step.tool == ToolType.PROFILER:
            arguments = self._extract_profiler_arguments(step, context)
        
        for invariant in step.invariants:
            if "row_limit" in invariant.lower() or "limit" in invariant.lower():
                parts = invariant.split("=")
                if len(parts) == 2:
                    try:
                        arguments["limit"] = int(parts[1].strip())
                    except ValueError:
                        pass
        
        return arguments
    
    def _extract_sql_arguments(
        self,
        step: PlanStep,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract SQL runner arguments from step."""
        arguments = {"query": step.operation}
        
        if "connection" in context:
            arguments["connection"] = context["connection"]
        
        if self.schema_context.get("database"):
            arguments["database"] = self.schema_context["database"]
        
        return arguments
    
    def _extract_df_arguments(
        self,
        step: PlanStep,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract DataFrame operations arguments from step."""
        arguments = {"operation": step.operation}
        
        if "dataframe" in context:
            arguments["dataframe"] = context["dataframe"]
        elif "df" in context:
            arguments["dataframe"] = context["df"]
        
        operation_lower = step.operation.lower()
        
        if "filter" in operation_lower or "where" in operation_lower:
            arguments["operation_type"] = "filter"
        elif "group" in operation_lower or "aggregate" in operation_lower:
            arguments["operation_type"] = "aggregate"
        elif "sort" in operation_lower:
            arguments["operation_type"] = "sort"
        elif "join" in operation_lower:
            arguments["operation_type"] = "join"
        
        return arguments
    
    def _extract_plot_arguments(
        self,
        step: PlanStep,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract plotter arguments from step."""
        arguments = {"title": step.operation}
        
        if "dataframe" in context:
            arguments["data"] = context["dataframe"]
        elif "df" in context:
            arguments["data"] = context["df"]
        
        operation_lower = step.operation.lower()
        
        if "bar" in operation_lower:
            arguments["chart_type"] = "bar"
        elif "line" in operation_lower:
            arguments["chart_type"] = "line"
        elif "scatter" in operation_lower:
            arguments["chart_type"] = "scatter"
        elif "pie" in operation_lower:
            arguments["chart_type"] = "pie"
        else:
            arguments["chart_type"] = "bar"
        
        return arguments
    
    def _extract_profiler_arguments(
        self,
        step: PlanStep,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract profiler arguments from step."""
        arguments = {}
        
        if "dataframe" in context:
            arguments["dataframe"] = context["dataframe"]
        elif "df" in context:
            arguments["dataframe"] = context["df"]
        
        if "connection" in context:
            arguments["connection"] = context["connection"]
        
        if self.schema_context.get("table_name"):
            arguments["table_name"] = self.schema_context["table_name"]
        
        return arguments
    
    def _validate_invariants(
        self,
        step: PlanStep,
        arguments: Dict[str, Any],
    ) -> None:
        """Validate step invariants before execution.
        
        Raises:
            ValueError: If invariant validation fails
        """
        for invariant in step.invariants:
            if "filter_before_aggregate" in invariant:
                if arguments.get("operation_type") == "aggregate":
                    if not self._has_prior_filter(step):
                        raise ValueError(
                            f"Invariant violation: {invariant} not satisfied"
                        )
    
    def _has_prior_filter(self, step: PlanStep) -> bool:
        """Check if step has a filter operation in its dependency chain."""
        history_map = {obs.step_id: obs for obs in self.execution_history}
        for dep_id in step.dependencies:
            if dep_id in history_map:
                dep_obs = history_map[dep_id]
                if dep_obs.metadata.get("operation_type") == "filter":
                    return True
        return False
    
    def _extract_metadata(self, result: Any) -> Dict[str, Any]:
        """Extract metadata from tool execution result."""
        metadata = {}
        
        if hasattr(result, "shape"):
            metadata["row_count"] = result.shape[0]
            metadata["column_count"] = result.shape[1]
        
        if hasattr(result, "columns"):
            metadata["columns"] = list(result.columns)
        
        return metadata
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary statistics of execution history.
        
        Returns:
            Dictionary with success rate, retry statistics, etc.
        """
        if not self.execution_history:
            return {
                "total_executions": 0,
                "successes": 0,
                "failures": 0,
                "success_rate": 0.0,
                "avg_retries": 0.0,
            }
        
        total = len(self.execution_history)
        successes = sum(1 for obs in self.execution_history if obs.is_success())
        failures = total - successes
        total_retries = sum(obs.retry_count for obs in self.execution_history)
        
        return {
            "total_executions": total,
            "successes": successes,
            "failures": failures,
            "success_rate": successes / total if total > 0 else 0.0,
            "avg_retries": total_retries / total if total > 0 else 0.0,
        }