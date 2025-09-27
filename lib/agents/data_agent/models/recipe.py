"""
Recipe entity: Stored successful analysis pattern for reuse.

Schema: recipe_id, schema_fingerprint, intent_template, intent_embedding, plan_structure, success_count
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class Recipe(BaseModel):
    """
    Analysis recipe: Stored successful plan pattern for similar future requests.
    
    Keyed by (schema_fingerprint, intent_embedding) for retrieval.
    """
    
    recipe_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schema_fingerprint: str = Field(..., description="SHA256 hash of sorted column names + types")
    intent_template: str = Field(..., description="Generalized intent pattern (e.g., 'Show <metric> trends by <dimension>')")
    intent_embedding: List[float] = Field(..., description="Sentence-transformers vector (768-dim)")
    plan_structure: Dict[str, Any] = Field(..., description="Serialized Plan object (subtasks, tools, ordering)")
    success_count: int = Field(default=1, ge=1, description="Number of times this recipe succeeded")
    last_used_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Performance metrics, user feedback")
    
    class Config:
        json_schema_extra = {
            "example": {
                "recipe_id": "recipe-550e8400-e29b-41d4-a716-446655440000",
                "schema_fingerprint": "sha256:abc123...",
                "intent_template": "Show quarterly <sales|revenue|volume> trends by <region|product|customer>",
                "intent_embedding": [0.123, -0.456, ...],  # 768 floats
                "plan_structure": {
                    "subtasks": [
                        {"tool": "sql", "pattern": "SELECT date_trunc('quarter', date_col) as qtr, SUM(metric_col) FROM table WHERE dim_col = $1 GROUP BY qtr"},
                        {"tool": "pandas", "pattern": "aggregate by quarter"},
                        {"tool": "plot", "pattern": "line chart with quarters on x-axis"}
                    ]
                },
                "success_count": 15,
                "last_used_at": "2025-09-27T12:00:00Z",
                "created_at": "2025-09-01T10:00:00Z",
                "metadata": {
                    "avg_execution_time_seconds": 4.2,
                    "schemas_applied_to": ["sales_db", "revenue_db"]
                }
            }
        }
    
    def increment_usage(self):
        """Update success count and last used timestamp."""
        self.success_count += 1
        self.last_used_at = datetime.utcnow()
    
    def get_avg_execution_time(self) -> Optional[float]:
        """Extract average execution time from metadata."""
        return self.metadata.get("avg_execution_time_seconds")