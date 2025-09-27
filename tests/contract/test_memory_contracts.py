"""Contract tests for memory layer components.

Validates schema fingerprinting and recipe storage contracts.
"""

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from lib.agents.data_agent.memory import (
    compute_schema_fingerprint,
    schema_compatible,
    get_schema_summary,
    Recipe,
    RecipeStore,
)


class TestSchemaFingerprintContract:
    """Test schema fingerprinting contracts."""
    
    def test_fingerprint_is_deterministic(self):
        """Schema fingerprinting produces same hash for identical schemas."""
        df1 = pd.DataFrame({"sales": [100, 200], "region": ["AZ", "CA"]})
        df2 = pd.DataFrame({"sales": [999, 888], "region": ["TX", "NY"]})
        
        fp1 = compute_schema_fingerprint(df1)
        fp2 = compute_schema_fingerprint(df2)
        
        assert fp1 == fp2, "Same schema should produce same fingerprint"
        assert len(fp1) == 64, "Fingerprint should be 64-char SHA256 hex"
    
    def test_fingerprint_differs_for_different_schemas(self):
        """Different schemas produce different fingerprints."""
        df1 = pd.DataFrame({"sales": [100], "region": ["AZ"]})
        df2 = pd.DataFrame({"revenue": [100], "state": ["AZ"]})
        
        fp1 = compute_schema_fingerprint(df1)
        fp2 = compute_schema_fingerprint(df2)
        
        assert fp1 != fp2, "Different schemas should produce different fingerprints"
    
    def test_fingerprint_sensitive_to_dtype(self):
        """Schema fingerprinting distinguishes column types."""
        df1 = pd.DataFrame({"value": [1, 2, 3]})
        df2 = pd.DataFrame({"value": ["1", "2", "3"]})
        
        fp1 = compute_schema_fingerprint(df1)
        fp2 = compute_schema_fingerprint(df2)
        
        assert fp1 != fp2, "int64 vs object types should produce different fingerprints"
    
    def test_fingerprint_column_order_independent(self):
        """Column order doesn't affect fingerprint (sorted internally)."""
        df1 = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
        df2 = pd.DataFrame({"c": [3], "a": [1], "b": [2]})
        
        fp1 = compute_schema_fingerprint(df1)
        fp2 = compute_schema_fingerprint(df2)
        
        assert fp1 == fp2, "Column order shouldn't affect fingerprint"
    
    def test_schema_compatible(self):
        """Schema compatibility check works correctly."""
        fp1 = "abc123"
        fp2 = "abc123"
        fp3 = "def456"
        
        assert schema_compatible(fp1, fp2) is True
        assert schema_compatible(fp1, fp3) is False
    
    def test_get_schema_summary(self):
        """Schema summary extraction returns sorted tuples."""
        df = pd.DataFrame({"sales": [100], "region": ["AZ"], "count": [5]})
        
        summary = get_schema_summary(df)
        
        assert len(summary) == 3
        assert summary[0] == ("count", "int64")
        assert summary[1] == ("region", "object")
        assert summary[2] == ("sales", "int64")
        assert summary == sorted(summary), "Summary should be sorted by column name"


class TestRecipeStoreContract:
    """Test recipe storage and retrieval contracts."""
    
    @pytest.fixture
    def temp_store(self):
        """Create temporary recipe store for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_recipes.db"
            store = RecipeStore(db_path=str(db_path))
            yield store
    
    def test_save_and_retrieve_recipe(self, temp_store):
        """Recipe can be saved and retrieved by ID."""
        schema_fp = "abc123"
        intent = "Analyze Q1 sales trends"
        plan = {"subtasks": [{"task_id": "load", "tool": "sql.run"}]}
        args = [{"query": "SELECT * FROM sales"}]
        
        recipe_id = temp_store.save_recipe(schema_fp, intent, plan, args)
        
        assert recipe_id is not None
        assert len(recipe_id) == 36, "Recipe ID should be UUID format"
        
        retrieved = temp_store.get_recipe(recipe_id)
        
        assert retrieved is not None
        assert retrieved.recipe_id == recipe_id
        assert retrieved.schema_fingerprint == schema_fp
        assert retrieved.intent_template == intent
        assert json.loads(retrieved.plan_structure) == plan
        assert json.loads(retrieved.tool_argument_templates) == args
        assert retrieved.success_count == 1
    
    def test_retrieve_recipes_by_schema_and_similarity(self, temp_store):
        """Recipes retrieved by schema fingerprint + semantic similarity."""
        schema_fp = "xyz789"
        
        temp_store.save_recipe(
            schema_fp,
            "Analyze sales trends for Arizona",
            {"subtasks": []},
            [],
        )
        temp_store.save_recipe(
            schema_fp,
            "Show revenue patterns by region",
            {"subtasks": []},
            [],
        )
        temp_store.save_recipe(
            "different_schema",
            "Analyze sales trends for Texas",
            {"subtasks": []},
            [],
        )
        
        results = temp_store.retrieve_recipes(
            schema_fp,
            "Analyze Arizona sales data",
            top_k=2,
        )
        
        assert len(results) == 2, "Should return top-2 recipes"
        assert all(r.schema_fingerprint == schema_fp for r in results)
        assert "Arizona" in results[0].intent_template, "Most similar should rank first"
    
    def test_update_success_count(self, temp_store):
        """Success count increments on reuse."""
        recipe_id = temp_store.save_recipe(
            "abc",
            "Test intent",
            {},
            [],
        )
        
        original = temp_store.get_recipe(recipe_id)
        assert original.success_count == 1
        
        temp_store.update_success_count(recipe_id)
        
        updated = temp_store.get_recipe(recipe_id)
        assert updated.success_count == 2
        assert updated.last_used_at > original.last_used_at
    
    def test_delete_recipe(self, temp_store):
        """Recipe deletion works correctly."""
        recipe_id = temp_store.save_recipe("abc", "Test", {}, [])
        
        deleted = temp_store.delete_recipe(recipe_id)
        assert deleted is True
        
        retrieved = temp_store.get_recipe(recipe_id)
        assert retrieved is None
        
        deleted_again = temp_store.delete_recipe(recipe_id)
        assert deleted_again is False
    
    def test_list_recipes(self, temp_store):
        """Recipe listing with optional schema filter."""
        temp_store.save_recipe("schema_a", "Intent A", {}, [])
        temp_store.save_recipe("schema_a", "Intent B", {}, [])
        temp_store.save_recipe("schema_b", "Intent C", {}, [])
        
        all_recipes = temp_store.list_recipes()
        assert len(all_recipes) == 3
        
        schema_a_recipes = temp_store.list_recipes(schema_fingerprint="schema_a")
        assert len(schema_a_recipes) == 2
        assert all(r.schema_fingerprint == "schema_a" for r in schema_a_recipes)
        
        limited = temp_store.list_recipes(limit=1)
        assert len(limited) == 1
    
    def test_get_stats(self, temp_store):
        """Store statistics calculation works correctly."""
        temp_store.save_recipe("schema_a", "Intent 1", {}, [])
        temp_store.save_recipe("schema_a", "Intent 2", {}, [])
        temp_store.save_recipe("schema_b", "Intent 3", {}, [])
        
        r1_id = temp_store.list_recipes()[0].recipe_id
        temp_store.update_success_count(r1_id)
        
        stats = temp_store.get_stats()
        
        assert stats["total_recipes"] == 3
        assert stats["unique_schemas"] == 2
        assert stats["total_success_count"] == 4
    
    def test_recipe_validation(self, temp_store):
        """Recipe fields validate correctly."""
        recipe_id = temp_store.save_recipe(
            "a" * 64,
            "Test template with {placeholder}",
            {"key": "value"},
            [{"arg": "pattern"}],
        )
        
        recipe = temp_store.get_recipe(recipe_id)
        
        assert len(recipe.schema_fingerprint) == 64
        assert "{placeholder}" in recipe.intent_template
        assert recipe.success_count >= 1
        assert recipe.created_at == recipe.last_used_at
    
    def test_recipe_embedding_similarity_ranking(self, temp_store):
        """Recipes ranked by semantic similarity to query intent."""
        schema_fp = "shared"
        
        temp_store.save_recipe(
            schema_fp,
            "Calculate total revenue for Q1 fiscal year",
            {},
            [],
        )
        temp_store.save_recipe(
            schema_fp,
            "Show weather patterns by month",
            {},
            [],
        )
        
        results = temp_store.retrieve_recipes(
            schema_fp,
            "Compute Q1 revenue totals",
            top_k=2,
        )
        
        assert len(results) == 2
        assert "revenue" in results[0].intent_template.lower()
        assert "Q1" in results[0].intent_template or "fiscal" in results[0].intent_template