"""Observation types for Actor execution feedback.

Captures tool execution results and status for self-repair loop.
"""

from dataclasses import dataclass
from typing import Any, Optional
from enum import Enum


class ExecutionStatus(Enum):
    """Status of tool execution attempt."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


@dataclass
class Observation:
    """Execution observation for self-repair feedback.
    
    Attributes:
        step_id: ID of executed plan step
        status: Execution outcome status
        result: Tool execution result (DataFrame, plot path, etc.)
        error_message: Error details if status is FAILURE
        retry_count: Number of retry attempts made
        metadata: Additional execution context (row counts, timing, etc.)
    """
    step_id: str
    status: ExecutionStatus
    result: Optional[Any] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def is_success(self) -> bool:
        """Check if execution succeeded."""
        return self.status == ExecutionStatus.SUCCESS
    
    def is_recoverable(self) -> bool:
        """Check if failure is potentially recoverable with retry."""
        if self.status != ExecutionStatus.FAILURE:
            return False
        
        recoverable_patterns = [
            "timeout",
            "connection",
            "temporary",
            "rate limit",
            "retry",
        ]
        
        if self.error_message:
            error_lower = self.error_message.lower()
            return any(pattern in error_lower for pattern in recoverable_patterns)
        
        return False