"""
Integration test for recipe storage and retrieval functionality.

Tests FR-031 to FR-033: Recipe memory for successful analysis patterns.
"""

import pytest
from lib.agents.data_agent.agent import DataAgent
from lib.agents.data_agent.contracts.request import AnalysisRequest


@pytest.fixture
def data_agent():
    """Create DataAgent instance for testing."""
    return DataAgent()


@pytest.fixture
def sample_request():
    """Create sample analysis request."""
    return AnalysisRequest(
        request_id="test-recipe-001",
        intent="Show quarterly sales trends by region",
        data_sources=[
            {"type": "sql", "connection_string": "postgresql://localhost/test_db"}
        ],
        deliverables=["tables", "charts"],
        constraints={"row_limit": 10000, "timeout_seconds": 30},
    )


class TestRecipeReuse:
    """Test recipe memory storage and retrieval."""

    def test_recipe_storage_on_success(self, data_agent, sample_request):
        """FR-031: Store successful analysis as recipe."""
        # Execute analysis (should succeed)
        response = data_agent.analyze(sample_request)
        
        assert response.status == "completed"
        assert response.recipe_id is not None, "Recipe should be stored on success"

    def test_recipe_retrieval_by_schema_and_intent(self, data_agent, sample_request):
        """FR-032: Retrieve recipe by schema fingerprint + intent similarity."""
        # First request: establish recipe
        response1 = data_agent.analyze(sample_request)
        recipe_id_1 = response1.recipe_id
        
        # Second request: similar intent, same schema (should reuse recipe)
        sample_request.request_id = "test-recipe-002"
        sample_request.intent = "Display regional sales by quarter"  # Similar intent
        response2 = data_agent.analyze(sample_request)
        
        assert response2.recipe_id == recipe_id_1, "Should reuse existing recipe"
        assert response2.metrics.recipe_reused is True

    def test_recipe_adaptation_to_new_context(self, data_agent, sample_request):
        """FR-033: Adapt stored recipe to current request context."""
        # First request: sales analysis
        response1 = data_agent.analyze(sample_request)
        
        # Second request: similar structure, different columns
        sample_request.request_id = "test-recipe-003"
        sample_request.intent = "Show quarterly revenue trends by region"  # Revenue vs Sales
        response2 = data_agent.analyze(sample_request)
        
        # Should adapt recipe (column name change: sales → revenue)
        assert response2.status == "completed"
        assert response2.recipe_id == response1.recipe_id  # Same base recipe
        assert "revenue" in str(response2.summary).lower(), "Should adapt to 'revenue' column"

    def test_no_recipe_reuse_for_different_schema(self, data_agent, sample_request):
        """Verify recipes are schema-specific (no cross-schema reuse)."""
        # First request: sales database
        response1 = data_agent.analyze(sample_request)
        
        # Second request: different database schema
        sample_request.request_id = "test-recipe-004"
        sample_request.data_sources = [
            {"type": "sql", "connection_string": "postgresql://localhost/inventory_db"}
        ]
        response2 = data_agent.analyze(sample_request)
        
        assert response2.recipe_id != response1.recipe_id, "Different schemas should use different recipes"
        assert response2.metrics.recipe_reused is False