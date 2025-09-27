"""
Artifact entity: Generated output file (CSV, plot, summary).

Schema: artifact_id, request_id, artifact_type, content_ref, content_hash, metadata, size_bytes
"""

from typing import Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class ArtifactType(str, Enum):
    """Types of artifacts DataAgent can generate."""
    TABLE = "table"  # CSV or Parquet file
    CHART = "chart"  # PNG/SVG plot
    SUMMARY = "summary"  # Text summary
    PROFILE = "profile"  # Data quality report


class Artifact(BaseModel):
    """
    Generated artifact: File output from analysis (table, chart, summary).
    
    References content by file path or object storage URI.
    """
    
    artifact_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = Field(..., description="Parent analysis request ID")
    artifact_type: ArtifactType = Field(..., description="Type of generated content")
    content_ref: str = Field(..., description="File path or URI (file:///path, s3://bucket/key)")
    content_hash: str = Field(..., description="SHA256 hash of content for integrity")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Type-specific metadata (shape, encoding, format)")
    size_bytes: int = Field(..., ge=0, description="File size in bytes")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "artifact_id": "art-550e8400-e29b-41d4-a716-446655440000",
                    "request_id": "req-001",
                    "artifact_type": "table",
                    "content_ref": "file:///data/artifacts/results_20250927_120000.csv",
                    "content_hash": "sha256:def456...",
                    "metadata": {
                        "rows": 12,
                        "columns": ["month", "total"],
                        "format": "csv",
                        "encoding": "utf-8"
                    },
                    "size_bytes": 1024,
                    "created_at": "2025-09-27T12:00:00Z"
                },
                {
                    "artifact_id": "art-550e8400-e29b-41d4-a716-446655440001",
                    "request_id": "req-001",
                    "artifact_type": "chart",
                    "content_ref": "file:///data/artifacts/trend_plot_20250927_120000.png",
                    "content_hash": "sha256:ghi789...",
                    "metadata": {
                        "width": 800,
                        "height": 600,
                        "format": "png",
                        "dpi": 100,
                        "chart_type": "line"
                    },
                    "size_bytes": 45312,
                    "created_at": "2025-09-27T12:00:01Z"
                }
            ]
        }
    
    def is_table(self) -> bool:
        """Check if artifact is a data table."""
        return self.artifact_type == ArtifactType.TABLE
    
    def is_chart(self) -> bool:
        """Check if artifact is a visualization."""
        return self.artifact_type == ArtifactType.CHART
    
    def get_file_path(self) -> str:
        """Extract local file path from content_ref (handles file:// URIs)."""
        if self.content_ref.startswith("file://"):
            return self.content_ref[7:]  # Remove file:// prefix
        return self.content_ref