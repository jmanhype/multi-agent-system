"""AnalysisRequest Pydantic model for DataAgent input contract.

Implements FR-038, FR-039: Stable JSON Request contract with semantic versioning.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class DataSource(BaseModel):
    """Data source configuration for analysis."""
    
    type: str = Field(..., description="Data source type: 'sql' or 'csv'")
    connection_string: Optional[str] = Field(None, description="Database connection string (for SQL sources)")
    file_path: Optional[str] = Field(None, description="File path (for CSV sources)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional source metadata")
    
    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate data source type is supported."""
        if v not in ["sql", "csv"]:
            raise ValueError(f"Unsupported data source type: {v}. Must be 'sql' or 'csv'")
        return v


class Constraints(BaseModel):
    """Resource constraints for analysis execution."""
    
    row_limit: Optional[int] = Field(
        default=200000,
        ge=1,
        le=200000,
        description="Maximum rows to process (FR-022)"
    )
    timeout_seconds: Optional[int] = Field(
        default=30,
        ge=1,
        le=180,
        description="Maximum execution time in seconds (FR-023)"
    )


class Policy(BaseModel):
    """Safety policy configuration for analysis."""
    
    allowed_columns: Optional[List[str]] = Field(
        default=None,
        description="Whitelist of allowed column names (FR-019)"
    )
    blocked_patterns: Optional[List[str]] = Field(
        default_factory=lambda: ["ssn", "email", "phone"],
        description="PII patterns to block (FR-020)"
    )


class AnalysisRequest(BaseModel):
    """Input contract for DataAgent analysis workflow.
    
    Implements FR-038, FR-039: Stable JSON Request contract.
    Version: 1.0.0
    """
    
    request_id: str = Field(..., description="Unique request identifier (UUID)")
    intent: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language analysis intent (FR-001)"
    )
    data_sources: List[DataSource] = Field(
        ...,
        min_length=1,
        description="List of data sources for analysis (FR-012, FR-013, FR-014)"
    )
    deliverables: List[str] = Field(
        ...,
        min_length=1,
        description="Requested output artifacts: 'tables', 'charts', 'reports', 'summary'"
    )
    constraints: Optional[Constraints] = Field(
        default_factory=Constraints,
        description="Resource constraints (FR-022, FR-023)"
    )
    policy: Optional[Policy] = Field(
        default_factory=Policy,
        description="Safety policy configuration (FR-016 through FR-021)"
    )
    
    @field_validator("deliverables")
    @classmethod
    def validate_deliverables(cls, v: List[str]) -> List[str]:
        """Validate deliverables contain supported artifact types."""
        valid_types = {"tables", "charts", "reports", "summary"}
        for deliverable in v:
            if deliverable not in valid_types:
                raise ValueError(
                    f"Invalid deliverable: {deliverable}. Must be one of {valid_types}"
                )
        return v
    
    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "intent": "Analyze Q1 2021 Arizona sales; trends + charts",
                "data_sources": [
                    {
                        "type": "sql",
                        "connection_string": "postgresql://localhost/sales_db"
                    }
                ],
                "deliverables": ["tables", "charts", "summary"],
                "constraints": {
                    "row_limit": 200000,
                    "timeout_seconds": 30
                },
                "policy": {
                    "blocked_patterns": ["ssn", "email", "phone"]
                }
            }
        }