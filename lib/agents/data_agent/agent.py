"""Main DataAgent orchestrator.

Coordinates Planner→Actor loop with audit logging and recipe reuse.
"""

import dataclasses
import hashlib
import re
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

from lib.agents.data_agent.planner import IntentParser, PlanBuilder, Plan
from lib.agents.data_agent.actor import Actor, ExecutionStatus
from lib.agents.data_agent.memory import RecipeStore, SchemaFingerprinter
from lib.agents.data_agent.audit import AuditTracer


class AnalysisStatus(Enum):
    """Overall analysis completion status."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"


@dataclass
class AnalysisRequest:
    """Input request for data analysis.
    
    Attributes:
        request_id: Unique request identifier
        intent: Natural language analysis intent
        data_sources: List of data source identifiers
        constraints: Optional constraints (row limits, timeouts)
        deliverables: Requested output types (tables, charts, reports)
        policy: Optional policy overrides
    """
    request_id: str
    intent: str
    data_sources: List[Union[Any, str, Dict[str, Any]]]  # Can be DataSource objects, dicts, or strings
    constraints: Optional[Dict[str, Any]] = None
    deliverables: Optional[List[str]] = None
    policy: Optional[Dict[str, Any]] = None


@dataclass
class AnalysisResponse:
    """Output response from data analysis.
    
    Attributes:
        request_id: Request this response belongs to
        status: Overall analysis status
        artifacts: Generated artifacts (tables, charts, reports)
        summary: Human-readable summary of results
        metrics: Performance metrics (duration, steps, retries)
        audit_log_ref: Reference to audit log entries
        plan_ref: Reference to execution plan
        error_message: Error details if status is not SUCCESS
    """
    request_id: str
    status: AnalysisStatus
    artifacts: List[Dict[str, Any]]
    summary: str
    metrics: Dict[str, Any]
    audit_log_ref: str
    plan_ref: Optional[str] = None
    error_message: Optional[str] = None


class DataAgent:
    """Autonomous data analysis agent.
    
    Orchestrates Planner→Actor loop with:
    - Natural language intent parsing
    - Plan generation and execution
    - Self-repair on failures
    - Recipe memory for pattern reuse
    - Merkle-chained audit logging
    """
    
    # Sensitive keys to redact in audit logs (normalized without separators)
    SENSITIVE_KEYS = {
        'password', 'passwd', 'pwd', 'token', 'apikey', 'secret',
        'credential', 'auth', 'privatekey', 'publickey',
        'accesstoken', 'refreshtoken', 'bearer', 'connectionstring',
        'clientsecret', 'clientid', 'sessionid', 'sessiontoken'
    }
    
    def __init__(
        self,
        tool_registry: Dict[str, Callable],
        anthropic_api_key: Optional[str] = None,
        recipe_store_path: str = "db/recipe_memory.db",
        audit_log_path: str = "logs/data_agent_runs.jsonl",
    ):
        """Initialize DataAgent.
        
        Args:
            tool_registry: Map of tool names to callable functions
            anthropic_api_key: API key for LLM calls (Planner)
            recipe_store_path: Path to recipe storage database
            audit_log_path: Path to audit log file
        """
        self.tool_registry = tool_registry
        
        # Initialize components
        self.intent_parser = IntentParser(api_key=anthropic_api_key) if anthropic_api_key else None
        self.plan_builder = PlanBuilder()
        self.actor = Actor(tool_registry=tool_registry)
        self.recipe_store = RecipeStore(db_path=recipe_store_path)
        self.schema_fingerprinter = SchemaFingerprinter()
        self.audit_tracer = AuditTracer(log_path=audit_log_path)
        
        # Progress callback
        self._progress_callback: Optional[Callable[[str, float], None]] = None
    
    def set_progress_callback(self, callback: Callable[[str, float], None]) -> None:
        """Set callback for progress updates.
        
        Args:
            callback: Function(message: str, progress: float) called during analysis
        """
        self._progress_callback = callback
    
    def _redact_sensitive_data(self, obj: Any) -> Any:
        """Recursively redact sensitive data from objects before logging.
        
        Args:
            obj: Object to redact (dict, list, or primitive)
            
        Returns:
            Redacted copy of the object
        """
        def _normalize_key(key: Any) -> str:
            """Normalize key for comparison by removing non-alphanumeric chars and lowercasing."""
            return re.sub(r'[^a-z0-9]', '', str(key).lower())
        
        if isinstance(obj, dict):
            redacted = {}
            for key, value in obj.items():
                # Normalize key for comparison
                key_normalized = _normalize_key(key)
                is_sensitive = any(
                    sensitive in key_normalized 
                    for sensitive in self.SENSITIVE_KEYS
                )
                
                if is_sensitive:
                    redacted[key] = "***REDACTED***"
                else:
                    redacted[key] = self._redact_sensitive_data(value)
            return redacted
        elif isinstance(obj, list):
            return [self._redact_sensitive_data(item) for item in obj]
        elif isinstance(obj, str):
            # Improved patterns for detecting credentials in string values
            credential_patterns = [
                # Bearer tokens
                r'(?i)\b(bearer)\s+[A-Za-z0-9\-\._~\+\/]+=*',
                # Key-value assignments with various formats
                r'(?i)\b(password|passwd|pwd|token|access[_\-]?token|refresh[_\-]?token|'
                r'api[_\-]?key|secret|private[_\-]?key|connection[_\-]?string|'
                r'client[_\-]?secret|session[_\-]?id|session[_\-]?token)\b\s*[:=]\s*'
                r'("[^"]+"|\'[^\']+\'|[^\s,;]+)',
                # High-entropy strings that look like tokens (32+ chars)
                r'\b[A-Za-z0-9+/]{32,}={0,2}\b',
                # AWS-style keys
                r'(?i)\b(AKIA|A3T|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}\b',
            ]
            
            for pattern in credential_patterns:
                if re.search(pattern, obj):
                    return "***REDACTED***"
            return obj
        else:
            return obj
    
    def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        """Execute end-to-end data analysis.
        
        Main orchestration method:
        1. Log request submission
        2. Attempt recipe retrieval (if schema known)
        3. Parse intent → generate plan
        4. Execute plan steps with Actor
        5. Collect artifacts and observations
        6. Log completion with audit trail
        7. Store successful recipe for reuse
        
        Args:
            request: Analysis request with intent and data sources
        
        Returns:
            AnalysisResponse with artifacts, summary, and audit reference
        """
        start_time = time.time()
        
        # Log request submission with proper serialization and redaction
        serialized_data_sources = []
        for ds in request.data_sources:
            if hasattr(ds, 'model_dump'):
                serialized_data_sources.append(ds.model_dump())
            elif dataclasses.is_dataclass(ds) and not isinstance(ds, type):
                serialized_data_sources.append(dataclasses.asdict(ds))
            else:
                serialized_data_sources.append(ds)
        
        # Redact sensitive information before logging
        redacted_data_sources = self._redact_sensitive_data(serialized_data_sources)
        
        self.audit_tracer.log_request(
            request_id=request.request_id,
            intent=request.intent,
            data_sources=redacted_data_sources,
        )
        
        self._report_progress("Analyzing request", 0.0)
        
        try:
            # Try recipe retrieval (if schema known)
            plan = None
            recipe_used = None
            
            if request.data_sources:
                # Generate composite fingerprint from all data sources
                fingerprints = []
                for ds in request.data_sources:
                    fp = self._get_schema_fingerprint(ds)
                    if fp:
                        fingerprints.append(fp)
                
                if fingerprints:
                    # Combine fingerprints with sorted concatenation for deterministic result
                    schema_fp = hashlib.sha256(
                        "-".join(sorted(fingerprints)).encode('utf-8')
                    ).hexdigest()
                    
                    recipes = self.recipe_store.retrieve_recipes(
                        schema_fingerprint=schema_fp,
                        intent_query=request.intent,
                        top_k=1,
                    )
                    if recipes:
                        recipe_used = recipes[0]
                        self.audit_tracer.log_recipe_retrieval(
                            recipe_id=recipe_used["recipe_id"],
                            schema_fingerprint=schema_fp,
                            similarity_score=recipe_used["similarity_score"],
                        )
                        self._report_progress("Using similar recipe", 0.1)
            
            # Parse intent and build plan
            self._report_progress("Planning analysis", 0.2)
            
            if self.intent_parser:
                parsed_intent = self.intent_parser.parse(
                    intent=request.intent,
                    data_sources=request.data_sources,
                )
                
                plan = self.plan_builder.build_plan(
                    objective=parsed_intent.objective,
                    operations=parsed_intent.operations,
                    deliverables=request.deliverables or parsed_intent.deliverables,
                    constraints=request.constraints or [],
                )
            else:
                # Fallback for testing without LLM
                # Create steps that map to different tools based on deliverables
                operations = ["Query data"]  # SQL runner
                if request.deliverables and "chart" in request.deliverables:
                    operations.extend(["Aggregate data", "Create chart"])  # DF ops, plotter
                else:
                    operations.extend(["Transform data", "Generate output"])  # DF ops, DF ops
                
                plan = self.plan_builder.build_plan(
                    objective=request.intent,
                    operations=operations,
                    deliverables=request.deliverables or ["table"],
                    constraints=request.constraints or [],
                )
            
            self.audit_tracer.log_plan(
                request_id=request.request_id,
                plan_id=plan.plan_id,
                subtask_count=len(plan.steps),
                estimated_seconds=plan.total_cost,
            )
            
            # Execute plan steps
            self._report_progress("Executing analysis", 0.3)
            
            artifacts = []
            execution_context = {}
            failed_steps = []
            
            for i, step in enumerate(plan.steps):
                step_progress = 0.3 + (0.6 * (i / len(plan.steps)))
                self._report_progress(f"Step {i+1}/{len(plan.steps)}: {step.operation[:50]}", step_progress)
                
                observation = self.actor.execute_step(step, execution_context)
                
                self.audit_tracer.log_observation(
                    observation_id=str(uuid.uuid4()),
                    call_id=f"{step.step_id}-call",
                    status=observation.status.value,
                    execution_time_seconds=observation.metadata.get("execution_time", 0.0),
                    error_message=observation.error_message,
                )
                
                if observation.is_success():
                    # Update execution context with result
                    execution_context[f"step_{step.step_id}_result"] = observation.result
                    
                    # Collect artifacts
                    if observation.result is not None:
                        artifact = self._create_artifact(
                            request_id=request.request_id,
                            step_id=step.step_id,
                            result=observation.result,
                        )
                        if artifact:
                            artifacts.append(artifact)
                else:
                    failed_steps.append({
                        "step_id": step.step_id,
                        "operation": step.operation,
                        "error": observation.error_message,
                        "retry_count": observation.retry_count,
                    })
            
            # Determine overall status
            total_steps = len(plan.steps)
            failed_count = len(failed_steps)
            
            if failed_count == 0:
                status = AnalysisStatus.SUCCESS
            elif failed_count < total_steps:
                status = AnalysisStatus.PARTIAL
            else:
                status = AnalysisStatus.FAILURE
            
            # Store successful recipe
            if status == AnalysisStatus.SUCCESS and request.data_sources:
                schema_fp = self._get_schema_fingerprint(request.data_sources[0])
                if schema_fp:
                    recipe_id = self.recipe_store.save_recipe(
                        schema_fingerprint=schema_fp,
                        intent_template=request.intent,
                        plan_structure={"steps": [s.operation for s in plan.steps]},
                        tool_argument_templates=[],
                    )
                    self.audit_tracer.log_recipe_storage(
                        recipe_id=recipe_id,
                        schema_fingerprint=schema_fp,
                        plan_id=plan.plan_id,
                    )
            
            # Generate summary
            duration = time.time() - start_time
            summary = self._generate_summary(
                status=status,
                total_steps=total_steps,
                artifacts=artifacts,
                failed_steps=failed_steps,
                duration=duration,
            )
            
            # Collect metrics
            metrics = {
                "total_duration_seconds": duration,
                "total_steps": total_steps,
                "successful_steps": total_steps - failed_count,
                "failed_steps": failed_count,
                "artifact_count": len(artifacts),
                "recipe_used": recipe_used["recipe_id"] if recipe_used else None,
            }
            
            # Log completion
            self.audit_tracer.log_completion(
                request_id=request.request_id,
                status=status.value,
                total_duration_seconds=duration,
                artifact_count=len(artifacts),
            )
            
            self._report_progress("Analysis complete", 1.0)
            
            return AnalysisResponse(
                request_id=request.request_id,
                status=status,
                artifacts=artifacts,
                summary=summary,
                metrics=metrics,
                audit_log_ref=f"logs:{request.request_id}",
                plan_ref=plan.plan_id if plan else None,
                error_message=self._format_errors(failed_steps) if failed_steps else None,
            )
        
        except Exception as e:
            # Catch-all error handling
            duration = time.time() - start_time
            error_id = str(uuid.uuid4())
            
            self.audit_tracer.log_error(
                error_id=error_id,
                error_type="orchestration_error",
                error_message=str(e),
                context={"request_id": request.request_id},
            )
            
            self._report_progress("Analysis failed", 1.0)
            
            return AnalysisResponse(
                request_id=request.request_id,
                status=AnalysisStatus.FAILURE,
                artifacts=[],
                summary=f"Analysis failed: {str(e)}",
                metrics={
                    "total_duration_seconds": duration,
                    "error_id": error_id,
                    "total_steps": 0,
                    "successful_steps": 0,
                    "failed_steps": 0,
                    "artifact_count": 0,
                },
                audit_log_ref=f"logs:{request.request_id}",
                error_message=str(e),
            )
    
    def _get_schema_fingerprint(self, data_source: str) -> Optional[str]:
        """Get schema fingerprint for data source.
        
        Args:
            data_source: Data source identifier
        
        Returns:
            Schema fingerprint or None if unable to determine
        """
        # TODO: Implement schema discovery
        # For now, return None (no recipe reuse)
        return None
    
    def _create_artifact(
        self,
        request_id: str,
        step_id: str,
        result: Any,
    ) -> Optional[Dict[str, Any]]:
        """Create artifact from step result.
        
        Args:
            request_id: Request ID
            step_id: Step ID that produced result
            result: Step execution result
        
        Returns:
            Artifact dictionary or None
        """
        if result is None:
            return None
        
        artifact_id = f"{request_id}-{step_id}-artifact"
        
        # Determine artifact type
        artifact_type = "data"
        if hasattr(result, "to_csv"):
            artifact_type = "table"
        elif isinstance(result, dict) and "chart_path" in result:
            artifact_type = "chart"
        
        return {
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "step_id": step_id,
            "metadata": {"result_type": str(type(result).__name__)},
        }
    
    def _generate_summary(
        self,
        status: AnalysisStatus,
        total_steps: int,
        artifacts: List[Dict[str, Any]],
        failed_steps: List[Dict[str, str]],
        duration: float,
    ) -> str:
        """Generate human-readable summary.
        
        Args:
            status: Overall analysis status
            total_steps: Total steps executed
            artifacts: Generated artifacts
            failed_steps: Failed step details
            duration: Total duration in seconds
        
        Returns:
            Summary string
        """
        if status == AnalysisStatus.SUCCESS:
            return (
                f"Analysis completed successfully in {duration:.1f}s. "
                f"Executed {total_steps} steps and generated {len(artifacts)} artifacts."
            )
        elif status == AnalysisStatus.PARTIAL:
            return (
                f"Analysis partially completed in {duration:.1f}s. "
                f"{total_steps - len(failed_steps)}/{total_steps} steps succeeded. "
                f"Generated {len(artifacts)} artifacts. "
                f"{len(failed_steps)} steps failed."
            )
        else:
            return (
                f"Analysis failed after {duration:.1f}s. "
                f"All {total_steps} steps failed."
            )
    
    def _format_errors(self, failed_steps: List[Dict[str, str]]) -> str:
        """Format failed steps into error message.
        
        Args:
            failed_steps: List of failed step details
        
        Returns:
            Formatted error string
        """
        lines = [f"{len(failed_steps)} step(s) failed:"]
        for step in failed_steps[:5]:  # Limit to first 5
            lines.append(f"- {step['operation'][:60]}: {step['error'][:100]}")
        
        if len(failed_steps) > 5:
            lines.append(f"... and {len(failed_steps) - 5} more")
        
        return "\n".join(lines)
    
    def _report_progress(self, message: str, progress: float) -> None:
        """Report progress to callback if set.
        
        Args:
            message: Progress message
            progress: Progress value (0.0-1.0)
        """
        if self._progress_callback:
            self._progress_callback(message, progress)
    
    def verify_audit_integrity(self) -> tuple[bool, Optional[str]]:
        """Verify audit log integrity.
        
        Returns:
            (is_valid, error_message)
        """
        return self.audit_tracer.verify_integrity()
    
    def get_request_trace(self, request_id: str) -> list:
        """Get complete audit trace for a request.
        
        Args:
            request_id: Request to trace
        
        Returns:
            List of audit log entries
        """
        return self.audit_tracer.get_request_trace(request_id)