"""Recipe storage and retrieval for analysis pattern reuse.

Stores successful analysis workflows indexed by schema fingerprint and
semantic intent embedding. Enables zero-shot reuse of proven patterns.
"""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import uuid

import numpy as np
from sentence_transformers import SentenceTransformer


@dataclass
class Recipe:
    """Successful analysis pattern for reuse.
    
    Attributes:
        recipe_id: Unique identifier
        schema_fingerprint: SHA256 hash of data source schema
        intent_template: Generalized intent pattern with {placeholders}
        intent_embedding: Semantic vector for similarity matching
        plan_structure: Reusable plan template (JSON-serialized)
        tool_argument_templates: Argument patterns for tool calls (JSON-serialized)
        success_count: Number of successful reuses
        created_at: First successful use timestamp
        last_used_at: Most recent reuse timestamp
    """
    recipe_id: str
    schema_fingerprint: str
    intent_template: str
    intent_embedding: np.ndarray
    plan_structure: str
    tool_argument_templates: str
    success_count: int
    created_at: str
    last_used_at: str


class RecipeStore:
    """Recipe storage with semantic retrieval.
    
    Features:
    - SQLite/Postgres storage with schema fingerprint indexing
    - Sentence-transformer embeddings for semantic search
    - Top-K retrieval by cosine similarity
    - Success tracking and recency scoring
    """
    
    def __init__(
        self,
        db_path: str = "db/recipe_memory.db",
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        """Initialize recipe store.
        
        Args:
            db_path: Path to SQLite database
            embedding_model: Sentence-transformer model name
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._embedding_model_name = embedding_model
        self._embedding_model = None
        
        self._init_db()
    
    @property
    def embedding_model(self):
        """Lazy-load the sentence transformer model."""
        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer(self._embedding_model_name)
        return self._embedding_model
    
    def _init_db(self) -> None:
        """Initialize database schema if not exists."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recipes (
                    recipe_id TEXT PRIMARY KEY,
                    schema_fingerprint TEXT NOT NULL,
                    intent_template TEXT NOT NULL,
                    intent_embedding BLOB NOT NULL,
                    plan_structure TEXT NOT NULL,
                    tool_argument_templates TEXT NOT NULL,
                    success_count INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    last_used_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_schema_fp 
                ON recipes(schema_fingerprint)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_used 
                ON recipes(last_used_at DESC)
            """)
            
            conn.commit()
        finally:
            conn.close()
    
    def save_recipe(
        self,
        schema_fingerprint: str,
        intent_template: str,
        plan_structure: dict,
        tool_argument_templates: List[dict],
    ) -> str:
        """Save new recipe to storage.
        
        Args:
            schema_fingerprint: SHA256 hash of data schema
            intent_template: Generalized intent with {placeholders}
            plan_structure: Reusable plan template
            tool_argument_templates: Tool call argument patterns
        
        Returns:
            Recipe ID (UUID)
        """
        recipe_id = str(uuid.uuid4())
        
        intent_embedding = self.embedding_model.encode(intent_template).astype(np.float32)
        
        now_iso = datetime.now(timezone.utc).isoformat()
        
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO recipes (
                    recipe_id, schema_fingerprint, intent_template, 
                    intent_embedding, plan_structure, tool_argument_templates,
                    success_count, created_at, last_used_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    recipe_id,
                    schema_fingerprint,
                    intent_template,
                    intent_embedding.tobytes(),
                    json.dumps(plan_structure),
                    json.dumps(tool_argument_templates),
                    1,
                    now_iso,
                    now_iso,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        
        return recipe_id
    
    def retrieve_recipes(
        self,
        schema_fingerprint: str,
        intent: str,
        top_k: int = 3,
    ) -> List[Recipe]:
        """Retrieve top-K recipes by schema + semantic similarity.
        
        Retrieval strategy (per FR-031, FR-033):
        1. Filter recipes matching schema_fingerprint
        2. Compute cosine similarity between intent and recipe embeddings
        3. Rank by similarity score
        4. Return top-K recipes
        
        Args:
            schema_fingerprint: SHA256 hash of current data schema
            intent: Current natural language intent
            top_k: Number of recipes to return
        
        Returns:
            List of Recipe objects sorted by relevance
        """
        intent_embedding = self.embedding_model.encode(intent)
        
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT recipe_id, schema_fingerprint, intent_template,
                       intent_embedding, plan_structure, tool_argument_templates,
                       success_count, created_at, last_used_at
                FROM recipes
                WHERE schema_fingerprint = ?
                """,
                (schema_fingerprint,),
            )
            
            candidates = []
            for row in cursor.fetchall():
                recipe_embedding = np.frombuffer(row[3], dtype=np.float32)
                
                similarity = self._cosine_similarity(intent_embedding, recipe_embedding)
                
                candidates.append((similarity, row))
            
            candidates.sort(reverse=True, key=lambda x: x[0])
            
            results = []
            for _, row in candidates[:top_k]:
                recipe = Recipe(
                    recipe_id=row[0],
                    schema_fingerprint=row[1],
                    intent_template=row[2],
                    intent_embedding=np.frombuffer(row[3], dtype=np.float32),
                    plan_structure=row[4],
                    tool_argument_templates=row[5],
                    success_count=row[6],
                    created_at=row[7],
                    last_used_at=row[8],
                )
                results.append(recipe)
            
            return results
        finally:
            conn.close()
    
    def update_success_count(self, recipe_id: str) -> None:
        """Increment success count and update last_used timestamp.
        
        Args:
            recipe_id: Recipe to update
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                UPDATE recipes
                SET success_count = success_count + 1,
                    last_used_at = ?
                WHERE recipe_id = ?
                """,
                (now_iso, recipe_id),
            )
            conn.commit()
        finally:
            conn.close()
    
    def get_recipe(self, recipe_id: str) -> Optional[Recipe]:
        """Retrieve recipe by ID.
        
        Args:
            recipe_id: Recipe UUID
        
        Returns:
            Recipe object or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT recipe_id, schema_fingerprint, intent_template,
                       intent_embedding, plan_structure, tool_argument_templates,
                       success_count, created_at, last_used_at
                FROM recipes
                WHERE recipe_id = ?
                """,
                (recipe_id,),
            )
            
            row = cursor.fetchone()
            if row is None:
                return None
            
            return Recipe(
                recipe_id=row[0],
                schema_fingerprint=row[1],
                intent_template=row[2],
                intent_embedding=np.frombuffer(row[3], dtype=np.float32),
                plan_structure=row[4],
                tool_argument_templates=row[5],
                success_count=row[6],
                created_at=row[7],
                last_used_at=row[8],
            )
        finally:
            conn.close()
    
    def delete_recipe(self, recipe_id: str) -> bool:
        """Delete recipe by ID.
        
        Args:
            recipe_id: Recipe UUID
        
        Returns:
            True if recipe was deleted, False if not found
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "DELETE FROM recipes WHERE recipe_id = ?",
                (recipe_id,),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def list_recipes(
        self,
        schema_fingerprint: Optional[str] = None,
        limit: int = 50,
    ) -> List[Recipe]:
        """List recipes, optionally filtered by schema.
        
        Args:
            schema_fingerprint: Optional schema filter
            limit: Maximum recipes to return
        
        Returns:
            List of Recipe objects sorted by last_used_at DESC
        """
        conn = sqlite3.connect(self.db_path)
        try:
            if schema_fingerprint:
                cursor = conn.execute(
                    """
                    SELECT recipe_id, schema_fingerprint, intent_template,
                           intent_embedding, plan_structure, tool_argument_templates,
                           success_count, created_at, last_used_at
                    FROM recipes
                    WHERE schema_fingerprint = ?
                    ORDER BY last_used_at DESC
                    LIMIT ?
                    """,
                    (schema_fingerprint, limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT recipe_id, schema_fingerprint, intent_template,
                           intent_embedding, plan_structure, tool_argument_templates,
                           success_count, created_at, last_used_at
                    FROM recipes
                    ORDER BY last_used_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
            
            recipes = []
            for row in cursor.fetchall():
                recipe = Recipe(
                    recipe_id=row[0],
                    schema_fingerprint=row[1],
                    intent_template=row[2],
                    intent_embedding=np.frombuffer(row[3], dtype=np.float32),
                    plan_structure=row[4],
                    tool_argument_templates=row[5],
                    success_count=row[6],
                    created_at=row[7],
                    last_used_at=row[8],
                )
                recipes.append(recipe)
            
            return recipes
        finally:
            conn.close()
    
    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between vectors.
        
        Args:
            a: First embedding vector
            b: Second embedding vector
        
        Returns:
            Cosine similarity score (-1 to 1)
        """
        a = a.astype(np.float32)
        b = b.astype(np.float32)
        
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(np.dot(a, b) / (norm_a * norm_b))
    
    def get_stats(self) -> dict:
        """Get recipe store statistics.
        
        Returns:
            Dictionary with total_recipes, unique_schemas, total_success_count
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_recipes,
                    COUNT(DISTINCT schema_fingerprint) as unique_schemas,
                    SUM(success_count) as total_success_count
                FROM recipes
            """)
            
            row = cursor.fetchone()
            return {
                "total_recipes": row[0],
                "unique_schemas": row[1],
                "total_success_count": row[2] or 0,
            }
        finally:
            conn.close()