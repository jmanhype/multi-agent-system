"""AnalysisResponse Pydantic model for DataAgent output contract.

Implements FR-038, FR-040: Stable JSON Response contract with semantic versioning.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class Summary(BaseModel):
    """High-level analysis summary."""
    
    key_findings: List[str] = Field(..., description="Bullet points of main discoveries")
    insights: str = Field(..., description="Narrative summary of analysis")
    warnings: Optional[List[str]] = Field(default_factory=list, description="Data quality issues or analysis limitations")


class Artifact(BaseModel):
    """Analysis artifact output."""
    
    artifact_id: str = Field(..., description="Unique artifact identifier (UUID)")
    artifact_type: str = Field(..., description="Artifact type: 'table', 'chart', 'report', 'summary'")
    content_ref: str = Field(..., description="URI reference to artifact content")
    content_hash: str = Field(..., description="SHA256 hash of artifact for audit trail")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Type-specific metadata")
    size_bytes: Optional[int] = Field(default=None, ge=0, description="Artifact file size")
    created_at: Optional[str] = Field(default=None, description="ISO 8601 timestamp")
    
    @field_validator("artifact_type")
    @classmethod
    def validate_artifact_type(cls, v: str) -> str:
        """Validate artifact type is supported."""
        if v not in ["table", "chart", "report", "summary"]:
            raise ValueError(f"Unsupported artifact type: {v}. Must be 'table', 'chart', 'report', or 'summary'")
        return v


class ErrorDetail(BaseModel):
    """Error details for failed analysis."""
    
    error_type: str = Field(..., description="Error type: timeout, resource_limit, policy_violation, grounding_error, tool_failure")
    error_message: str = Field(..., description="Human-readable error message")
    failed_tool_calls: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Details of failed tool calls")


class Metrics(BaseModel):
    """Analysis execution metrics."""
    
    execution_time_seconds: float = Field(..., description="Total execution time (FR-043: target <30s)")
    tool_calls_count: int = Field(..., ge=0, description="Number of tool calls executed")
    retries_count: Optional[int] = Field(default=0, ge=0, le=6, description="Self-repair attempts (FR-030: max K=3 per tool call)")
    rows_processed: Optional[int] = Field(default=0, ge=0, description="Total rows processed across all data sources")
    recipe_used: Optional[bool] = Field(default=False, description="Whether a stored recipe was retrieved and adapted")


class AnalysisResponse(BaseModel):
    """Output contract for DataAgent analysis workflow.
    
    Implements FR-038, FR-040: Stable JSON Response contract.
    Version: 1.0.0
    """
    
    request_id: str = Field(..., description="Original request identifier")
    status: str = Field(..., description="Analysis status: 'completed', 'failed', 'partial_success'")
    artifacts: List[Artifact] = Field(
        default_factory=list,
        description="Generated artifacts (FR-005) - required for 'completed' status"
    )
    summary: Summary = Field(..., description="High-level analysis summary (FR-005)")
    metrics: Metrics = Field(..., description="Execution metrics and performance data")
    audit_log_ref: str = Field(..., description="URI reference to audit log entries (FR-034, FR-037)")
    plan_ref: Optional[str] = Field(default=None, description="URI reference to execution plan")
    error: Optional[ErrorDetail] = Field(default=None, description="Error details - required for 'failed' status")
    data_sources_accessed: Optional[List[str]] = Field(
        default=None,
        description="List of data sources actually accessed during analysis"
    )
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status is supported."""
        if v not in ["completed", "failed", "partial_success"]:
            raise ValueError(f"Invalid status: {v}. Must be 'completed', 'failed', or 'partial_success'")
        return v
    
    @model_validator(mode="after")
    def validate_status_fields(self) -> "AnalysisResponse":
        """Validate required fields based on status.
        
        - 'completed' requires at least one artifact
        - 'failed' or 'partial_success' requires error field
        """
        if self.status == "completed" and len(self.artifacts) == 0:
            raise ValueError("Status 'completed' requires at least one artifact")
        
        if self.status in ["failed", "partial_success"] and self.error is None:
            raise ValueError(f"Status '{self.status}' requires error field")
        
        return self
    
    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example_completed": {
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "artifacts": [
                    {
                        "artifact_id": "660e8400-e29b-41d4-a716-446655440001",
                        "artifact_type": "table",
                        "content_ref": "file:///data/results_q1_arizona.csv",
                        "content_hash": "d3f5a7b9c1e3d5f7a9b1c3e5d7f9a1b3c5e7d9f1a3b5c7d9e1f3a5b7c9d1e3f5",
                        "metadata": {
                            "rows": 1234,
                            "columns": ["month", "sales", "region"]
                        },
                        "size_bytes": 256,
                        "created_at": "2025-09-27T10:15:30Z"
                    },
                    {
                        "artifact_id": "660e8400-e29b-41d4-a716-446655440002",
                        "artifact_type": "chart",
                        "content_ref": "file:///data/trends_q1_arizona.png",
                        "content_hash": "e4g6b8c0d2f4a6b8c0d2f4a6b8c0d2f4a6b8c0d2f4a6b8c0d2f4a6b8c0d2f4a6",
                        "metadata": {
                            "chart_type": "line",
                            "title": "Q1 2021 Arizona Sales Trends"
                        },
                        "size_bytes": 48392,
                        "created_at": "2025-09-27T10:15:32Z"
                    }
                ],
                "summary": {
                    "key_findings": [
                        "Total revenue: $1.2M",
                        "15% increase over Q4 2020",
                        "Peak sales in March"
                    ],
                    "insights": "Q1 2021 Arizona sales showed strong growth with consistent upward trend.",
                    "warnings": []
                },
                "metrics": {
                    "execution_time_seconds": 12.5,
                    "tool_calls_count": 3,
                    "retries_count": 0,
                    "rows_processed": 5000,
                    "recipe_used": False
                },
                "audit_log_ref": "file:///logs/data_agent_runs.jsonl#line-1234",
                "plan_ref": "file:///logs/plans/550e8400-e29b-41d4-a716-446655440000.json",
                "data_sources_accessed": ["postgresql://localhost/sales_db"]
            },
            "example_failed": {
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "failed",
                "artifacts": [],
                "error": {
                    "error_type": "grounding_error",
                    "error_message": "Failed to resolve column 'salez' after 3 repair attempts",
                    "failed_tool_calls": [
                        {
                            "call_id": "call-001",
                            "tool_name": "sql_runner",
                            "error_category": "missing_column",
                            "attempts": 3
                        }
                    ]
                },
                "summary": {
                    "key_findings": [],
                    "insights": "Analysis failed due to invalid column reference after exhausting repair attempts.",
                    "warnings": ["Column 'salez' not found after 3 repair attempts"]
                },
                "metrics": {
                    "execution_time_seconds": 8.2,
                    "tool_calls_count": 4,
                    "retries_count": 3,
                    "rows_processed": 0,
                    "recipe_used": False
                },
                "audit_log_ref": "file:///logs/data_agent_runs.jsonl#line-1235"
            }
        }