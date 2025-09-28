"""Integration tests for memory layer components.

Tests recipe storage and retrieval end-to-end workflows.

NOTE: These tests require sentence-transformers model downloads and may have network dependencies.
Run with: pytest -m integration
Skip with: pytest -m "not integration"
"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from lib.agents.data_agent.memory import (
    compute_schema_fingerprint,
    RecipeStore,
)


pytestmark = pytest.mark.integration


class TestMemoryLayerIntegration:
    """Integration tests for complete memory workflows."""
    
    @pytest.fixture
    def temp_store(self):
        """Create temporary recipe store for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_recipes.db"
            store = RecipeStore(db_path=str(db_path))
            yield store
    
    @pytest.fixture
    def sample_dataframe(self):
        """Sample DataFrame for testing."""
        return pd.DataFrame({
            "date": pd.date_range("2025-01-01", periods=10),
            "sales": [100, 150, 200, 175, 225, 250, 300, 275, 350, 400],
            "region": ["AZ"] * 5 + ["CA"] * 5,
        })
    
    def test_end_to_end_recipe_storage_and_retrieval(
        self,
        temp_store,
        sample_dataframe,
    ):
        """Full workflow: compute fingerprint → save recipe → retrieve by similarity."""
        schema_fp = compute_schema_fingerprint(sample_dataframe)
        
        assert len(schema_fp) == 64, "Fingerprint should be SHA256"
        
        recipe_id = temp_store.save_recipe(
            schema_fingerprint=schema_fp,
            intent_template="Analyze {time_range} {location} sales trends",
            plan_structure={
                "subtasks": [
                    {
                        "task_id": "load_sales",
                        "tool_name": "sql.run",
                        "dependencies": [],
                    },
                    {
                        "task_id": "aggregate_monthly",
                        "tool_name": "df.transform",
                        "dependencies": ["load_sales"],
                    },
                    {
                        "task_id": "plot_trend",
                        "tool_name": "plot.render",
                        "dependencies": ["aggregate_monthly"],
                    },
                ]
            },
            tool_argument_templates=[
                {"query": "SELECT * FROM sales WHERE date BETWEEN {start} AND {end}"},
                {"operation": "groupby", "columns": ["month"], "aggregation": "sum"},
                {"type": "line", "x_col": "month", "y_col": "sales"},
            ],
        )
        
        assert recipe_id is not None
        
        retrieved_recipes = temp_store.retrieve_recipes(
            schema_fingerprint=schema_fp,
            intent="Show Arizona sales patterns over time",
            top_k=1,
        )
        
        assert len(retrieved_recipes) == 1
        assert retrieved_recipes[0].recipe_id == recipe_id
        assert "sales" in retrieved_recipes[0].intent_template.lower()
        assert "trends" in retrieved_recipes[0].intent_template.lower()
    
    def test_recipe_retrieval_with_multiple_candidates(
        self,
        temp_store,
        sample_dataframe,
    ):
        """Semantic ranking works when multiple recipes match schema."""
        schema_fp = compute_schema_fingerprint(sample_dataframe)
        
        temp_store.save_recipe(
            schema_fp,
            "Analyze quarterly sales revenue trends",
            {"subtasks": []},
            [],
        )
        temp_store.save_recipe(
            schema_fp,
            "Show regional distribution of orders",
            {"subtasks": []},
            [],
        )
        temp_store.save_recipe(
            schema_fp,
            "Calculate total revenue by product category",
            {"subtasks": []},
            [],
        )
        
        results = temp_store.retrieve_recipes(
            schema_fp,
            "Analyze sales revenue patterns",
            top_k=3,
        )
        
        assert len(results) == 3
        
        assert "sales" in results[0].intent_template.lower() or "revenue" in results[0].intent_template.lower()
    
    def test_schema_fingerprint_consistency_across_dataframes(self):
        """Same schema produces same fingerprint regardless of data."""
        df1 = pd.DataFrame({
            "date": pd.date_range("2025-01-01", periods=5),
            "sales": [100, 200, 300, 400, 500],
            "region": ["AZ", "CA", "TX", "NY", "FL"],
        })
        
        df2 = pd.DataFrame({
            "date": pd.date_range("2024-06-01", periods=10),
            "sales": [999, 888, 777, 666, 555, 444, 333, 222, 111, 0],
            "region": ["CA"] * 10,
        })
        
        fp1 = compute_schema_fingerprint(df1)
        fp2 = compute_schema_fingerprint(df2)
        
        assert fp1 == fp2, "Same schema should produce same fingerprint"
    
    def test_recipe_success_tracking(self, temp_store, sample_dataframe):
        """Recipe reuse increments success count and updates timestamp."""
        schema_fp = compute_schema_fingerprint(sample_dataframe)
        
        recipe_id = temp_store.save_recipe(
            schema_fp,
            "Test recipe for success tracking",
            {},
            [],
        )
        
        original = temp_store.get_recipe(recipe_id)
        assert original.success_count == 1
        
        temp_store.update_success_count(recipe_id)
        temp_store.update_success_count(recipe_id)
        
        updated = temp_store.get_recipe(recipe_id)
        assert updated.success_count == 3
        assert updated.last_used_at > original.last_used_at
    
    def test_no_recipes_for_unmatched_schema(self, temp_store):
        """Retrieval returns empty list when no recipes match schema."""
        temp_store.save_recipe(
            "schema_abc",
            "Test recipe",
            {},
            [],
        )
        
        results = temp_store.retrieve_recipes(
            "schema_xyz",
            "Any intent",
            top_k=5,
        )
        
        assert len(results) == 0
    
    def test_recipe_store_stats_accuracy(self, temp_store):
        """Store statistics reflect actual state."""
        temp_store.save_recipe("schema_a", "Intent 1", {}, [])
        temp_store.save_recipe("schema_a", "Intent 2", {}, [])
        temp_store.save_recipe("schema_b", "Intent 3", {}, [])
        
        recipes = temp_store.list_recipes()
        temp_store.update_success_count(recipes[0].recipe_id)
        temp_store.update_success_count(recipes[1].recipe_id)
        
        stats = temp_store.get_stats()
        
        assert stats["total_recipes"] == 3
        assert stats["unique_schemas"] == 2
        assert stats["total_success_count"] == 5
    
    def test_recipe_deletion_cleanup(self, temp_store, sample_dataframe):
        """Deleted recipes are removed from retrieval results."""
        schema_fp = compute_schema_fingerprint(sample_dataframe)
        
        r1_id = temp_store.save_recipe(schema_fp, "Recipe 1", {}, [])
        r2_id = temp_store.save_recipe(schema_fp, "Recipe 2", {}, [])
        
        results_before = temp_store.retrieve_recipes(schema_fp, "Test", top_k=10)
        assert len(results_before) == 2
        
        temp_store.delete_recipe(r1_id)
        
        results_after = temp_store.retrieve_recipes(schema_fp, "Test", top_k=10)
        assert len(results_after) == 1
        assert results_after[0].recipe_id == r2_id
    
    def test_parallel_schema_fingerprinting(self):
        """Schema fingerprinting works correctly for multiple DataFrames."""
        dataframes = [
            pd.DataFrame({"a": [1], "b": [2]}),
            pd.DataFrame({"x": [1], "y": [2]}),
            pd.DataFrame({"a": [999], "b": [888]}),
        ]
        
        fingerprints = [compute_schema_fingerprint(df) for df in dataframes]
        
        assert fingerprints[0] == fingerprints[2], "df[0] and df[2] have same schema"
        assert fingerprints[0] != fingerprints[1], "df[0] and df[1] have different schemas"
        assert all(len(fp) == 64 for fp in fingerprints), "All fingerprints are SHA256"
    
    def test_recipe_persistence_across_store_instances(self):
        """Recipes persist when store is reopened."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "persistent_test.db"
            
            store1 = RecipeStore(db_path=str(db_path))
            recipe_id = store1.save_recipe(
                "persistent_schema",
                "Persistent recipe",
                {"key": "value"},
                [],
            )
            
            del store1
            
            store2 = RecipeStore(db_path=str(db_path))
            retrieved = store2.get_recipe(recipe_id)
            
            assert retrieved is not None
            assert retrieved.recipe_id == recipe_id
            assert retrieved.intent_template == "Persistent recipe"