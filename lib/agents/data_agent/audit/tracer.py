"""AuditTrace event logging for workflow observability.

Logs all significant events in the DataAgent workflow to Merkle-chained log.
"""

from enum import Enum
from typing import Any, Dict, Optional
import uuid

from lib.agents.data_agent.audit.merkle_log import MerkleLog


class EventType(Enum):
    """Types of events tracked in audit trail."""
    REQUEST_SUBMITTED = "request_submitted"
    PLAN_CREATED = "plan_created"
    TOOL_CALLED = "tool_called"
    OBSERVATION_RECORDED = "observation_recorded"
    ARTIFACT_GENERATED = "artifact_generated"
    POLICY_DECISION = "policy_decision"
    ERROR_OCCURRED = "error_occurred"
    RECIPE_RETRIEVED = "recipe_retrieved"
    RECIPE_STORED = "recipe_stored"
    ANALYSIS_COMPLETED = "analysis_completed"


class AuditTracer:
    """High-level API for logging workflow events.
    
    Wraps MerkleLog with event-specific methods for common logging patterns.
    """
    
    def __init__(self, log_path: str = "logs/data_agent_runs.jsonl"):
        """Initialize audit tracer.
        
        Args:
            log_path: Path to JSONL audit log
        """
        self.log = MerkleLog(log_path)
    
    def log_request(self, request_id: str, intent: str, data_sources: list) -> None:
        """Log analysis request submission.
        
        Args:
            request_id: Unique request identifier
            intent: Natural language intent
            data_sources: List of data source names
        """
        self.log.append(
            entry_id=f"{request_id}-request",
            event_type=EventType.REQUEST_SUBMITTED.value,
            data={
                "request_id": request_id,
                "intent": intent,
                "data_sources": data_sources,
            },
        )
    
    def log_plan(
        self,
        request_id: str,
        plan_id: str,
        subtask_count: int,
        estimated_seconds: float,
    ) -> None:
        """Log plan creation.
        
        Args:
            request_id: Request this plan belongs to
            plan_id: Unique plan identifier
            subtask_count: Number of subtasks in plan
            estimated_seconds: Total estimated execution time
        """
        self.log.append(
            entry_id=f"{request_id}-plan-{plan_id}",
            event_type=EventType.PLAN_CREATED.value,
            data={
                "request_id": request_id,
                "plan_id": plan_id,
                "subtask_count": subtask_count,
                "estimated_seconds": estimated_seconds,
            },
        )
    
    def log_tool_call(
        self,
        call_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        attempt_number: int = 1,
    ) -> None:
        """Log tool invocation.
        
        Args:
            call_id: Unique call identifier
            tool_name: Name of tool being invoked
            arguments: Tool arguments (sensitive data redacted)
            attempt_number: Retry attempt number (1 for first attempt)
        """
        self.log.append(
            entry_id=f"{call_id}-call",
            event_type=EventType.TOOL_CALLED.value,
            data={
                "call_id": call_id,
                "tool_name": tool_name,
                "arguments": arguments,
                "attempt_number": attempt_number,
            },
        )
    
    def log_observation(
        self,
        observation_id: str,
        call_id: str,
        status: str,
        execution_time_seconds: float,
        error_message: Optional[str] = None,
    ) -> None:
        """Log tool execution observation.
        
        Args:
            observation_id: Unique observation identifier
            call_id: Tool call this observation belongs to
            status: Execution status (success/failure)
            execution_time_seconds: Execution duration
            error_message: Error details if status is failure
        """
        data = {
            "observation_id": observation_id,
            "call_id": call_id,
            "status": status,
            "execution_time_seconds": execution_time_seconds,
        }
        
        if error_message:
            data["error_message"] = error_message
        
        self.log.append(
            entry_id=f"{observation_id}-obs",
            event_type=EventType.OBSERVATION_RECORDED.value,
            data=data,
        )
    
    def log_artifact(
        self,
        artifact_id: str,
        request_id: str,
        artifact_type: str,
        content_hash: str,
        size_bytes: int,
    ) -> None:
        """Log artifact generation.
        
        Args:
            artifact_id: Unique artifact identifier
            request_id: Request this artifact belongs to
            artifact_type: Type of artifact (table, chart, report)
            content_hash: SHA256 hash of artifact content
            size_bytes: Artifact size in bytes
        """
        self.log.append(
            entry_id=f"{artifact_id}-artifact",
            event_type=EventType.ARTIFACT_GENERATED.value,
            data={
                "artifact_id": artifact_id,
                "request_id": request_id,
                "artifact_type": artifact_type,
                "content_hash": content_hash,
                "size_bytes": size_bytes,
            },
        )
    
    def log_policy_decision(
        self,
        decision_id: str,
        policy_name: str,
        decision: str,
        reason: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log safety policy enforcement decision.
        
        Args:
            decision_id: Unique decision identifier
            policy_name: Name of policy (e.g., "pii_blocking", "ddl_prevention")
            decision: Decision outcome (allow/block)
            reason: Human-readable explanation
            context: Additional decision context
        """
        data = {
            "decision_id": decision_id,
            "policy_name": policy_name,
            "decision": decision,
            "reason": reason,
        }
        
        if context:
            data["context"] = context
        
        self.log.append(
            entry_id=f"{decision_id}-policy",
            event_type=EventType.POLICY_DECISION.value,
            data=data,
        )
    
    def log_error(
        self,
        error_id: str,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log error occurrence.
        
        Args:
            error_id: Unique error identifier
            error_type: Error category (grounding_error, timeout, etc.)
            error_message: Error details
            context: Additional error context
        """
        data = {
            "error_id": error_id,
            "error_type": error_type,
            "error_message": error_message,
        }
        
        if context:
            data["context"] = context
        
        self.log.append(
            entry_id=f"{error_id}-error",
            event_type=EventType.ERROR_OCCURRED.value,
            data=data,
        )
    
    def log_recipe_retrieval(
        self,
        recipe_id: str,
        schema_fingerprint: str,
        similarity_score: float,
    ) -> None:
        """Log recipe retrieval from memory.
        
        Args:
            recipe_id: ID of retrieved recipe
            schema_fingerprint: Schema fingerprint used for retrieval
            similarity_score: Intent similarity score (0-1)
        """
        self.log.append(
            entry_id=f"{recipe_id}-retrieve",
            event_type=EventType.RECIPE_RETRIEVED.value,
            data={
                "recipe_id": recipe_id,
                "schema_fingerprint": schema_fingerprint,
                "similarity_score": similarity_score,
            },
        )
    
    def log_recipe_storage(
        self,
        recipe_id: str,
        schema_fingerprint: str,
        plan_id: str,
    ) -> None:
        """Log successful recipe storage.
        
        Args:
            recipe_id: ID of stored recipe
            schema_fingerprint: Schema fingerprint for retrieval
            plan_id: Plan structure stored in recipe
        """
        self.log.append(
            entry_id=f"{recipe_id}-store",
            event_type=EventType.RECIPE_STORED.value,
            data={
                "recipe_id": recipe_id,
                "schema_fingerprint": schema_fingerprint,
                "plan_id": plan_id,
            },
        )
    
    def log_completion(
        self,
        request_id: str,
        status: str,
        total_duration_seconds: float,
        artifact_count: int,
    ) -> None:
        """Log analysis completion.
        
        Args:
            request_id: Completed request ID
            status: Final status (success/partial/failure)
            total_duration_seconds: Total analysis duration
            artifact_count: Number of artifacts generated
        """
        self.log.append(
            entry_id=f"{request_id}-complete",
            event_type=EventType.ANALYSIS_COMPLETED.value,
            data={
                "request_id": request_id,
                "status": status,
                "total_duration_seconds": total_duration_seconds,
                "artifact_count": artifact_count,
            },
        )
    
    def verify_integrity(self) -> tuple[bool, Optional[str]]:
        """Verify Merkle chain integrity.
        
        Returns:
            (is_valid, error_message)
        """
        return self.log.verify_chain()
    
    def get_request_trace(self, request_id: str) -> list:
        """Get all events for a specific request.
        
        Args:
            request_id: Request to trace
        
        Returns:
            List of LogEntry objects for this request
        """
        return self.log.get_entries(entry_id_prefix=request_id)