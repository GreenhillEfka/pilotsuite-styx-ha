"""Tests for Collective Intelligence module."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestCollectiveIntelligence:
    """Test federated learning and collective intelligence."""
    
    def test_initialization(self):
        """Test Collective Intelligence initialization."""
        from custom_components.ai_home_copilot.collective_intelligence import (
            CollectiveIntelligence,
        )
        
        hass = MagicMock()
        hass.data = {}
        
        collective = CollectiveIntelligence(
            hass=hass,
            home_id="home_test",
            home_name="Test Home",
            privacy_epsilon=1.0,
        )
        
        assert collective.home_id == "home_test"
        assert collective.home_name == "Test Home"
        assert collective.privacy_epsilon == 1.0
        assert collective.local_models == {}
        assert collective.shared_patterns == {}
        
    @pytest.mark.asyncio
    async def test_register_model(self):
        """Test registering a local model."""
        from custom_components.ai_home_copilot.collective_intelligence import (
            CollectiveIntelligence,
            LocalModel,
        )
        
        hass = MagicMock()
        hass.data = {}
        
        # Mock the store
        mock_store = AsyncMock()
        mock_store.async_load = AsyncMock(return_value=None)
        mock_store.async_save = AsyncMock()
        
        with patch(
            "custom_components.ai_home_copilot.collective_intelligence.Store",
            return_value=mock_store,
        ):
            collective = CollectiveIntelligence(
                hass=hass,
                home_id="home_test",
                home_name="Test Home",
            )
            await collective.async_initialize()
            
            model = await collective.async_register_model(
                model_id="habit_model",
                model_type="habit",
                parameters={"learning_rate": 0.01},
            )
            
            assert model.model_id == "habit_model"
            assert model.model_type == "habit"
            assert model.version == 1
            assert model.sample_count == 0
            assert "habit_model" in collective.local_models
            
    @pytest.mark.asyncio
    async def test_update_model(self):
        """Test updating a local model."""
        from custom_components.ai_home_copilot.collective_intelligence import (
            CollectiveIntelligence,
        )
        
        hass = MagicMock()
        hass.data = {}
        
        mock_store = AsyncMock()
        mock_store.async_load = AsyncMock(return_value=None)
        mock_store.async_save = AsyncMock()
        
        with patch(
            "custom_components.ai_home_copilot.collective_intelligence.Store",
            return_value=mock_store,
        ):
            collective = CollectiveIntelligence(
                hass=hass,
                home_id="home_test",
                home_name="Test Home",
            )
            await collective.async_initialize()
            
            # Register first
            await collective.async_register_model(
                model_id="habit_model",
                model_type="habit",
                parameters={"learning_rate": 0.01},
            )
            
            # Update
            updated = await collective.async_update_model(
                model_id="habit_model",
                parameters={"learning_rate": 0.02, "epochs": 100},
                accuracy=0.85,
                sample_count=50,
            )
            
            assert updated.version == 2
            assert updated.accuracy == 0.85
            assert updated.sample_count == 50
            
    def test_differential_privacy(self):
        """Test differential privacy noise application."""
        from custom_components.ai_home_copilot.collective_intelligence import (
            CollectiveIntelligence,
        )
        
        hass = MagicMock()
        
        collective = CollectiveIntelligence(
            hass=hass,
            home_id="home_test",
            home_name="Test Home",
            privacy_epsilon=1.0,
        )
        
        weights = {"light_on": 0.8, "temperature": 0.6, "time_morning": 0.7}
        
        # Apply multiple times - should get different results
        result1 = collective._apply_differential_privacy(weights.copy())
        result2 = collective._apply_differential_privacy(weights.copy())
        
        # Results should be different due to noise
        assert result1 != result2
        
        # But values should be in reasonable range (allowing for noise)
        for key in weights:
            assert -3.0 <= result1[key] <= 3.0
            
    @pytest.mark.asyncio
    async def test_create_pattern_below_threshold(self):
        """Test pattern creation below contribution threshold."""
        from custom_components.ai_home_copilot.collective_intelligence import (
            CollectiveIntelligence,
        )
        
        hass = MagicMock()
        hass.data = {}
        
        mock_store = AsyncMock()
        mock_store.async_load = AsyncMock(return_value=None)
        mock_store.async_save = AsyncMock()
        
        with patch(
            "custom_components.ai_home_copilot.collective_intelligence.Store",
            return_value=mock_store,
        ):
            collective = CollectiveIntelligence(
                hass=hass,
                home_id="home_test",
                home_name="Test Home",
                min_contribution_score=0.5,
            )
            await collective.async_initialize()
            
            pattern = await collective.async_create_pattern(
                model_id="habit_model",
                pattern_type="habit",
                category="lighting",
                weights={"light_on": 0.8},
                metadata={"zone": "living_room"},
                confidence=0.3,  # Below threshold
            )
            
            assert pattern is None
            
    @pytest.mark.asyncio
    async def test_create_pattern_above_threshold(self):
        """Test pattern creation above contribution threshold."""
        from custom_components.ai_home_copilot.collective_intelligence import (
            CollectiveIntelligence,
        )
        
        hass = MagicMock()
        hass.data = {}
        
        mock_store = AsyncMock()
        mock_store.async_load = AsyncMock(return_value=None)
        mock_store.async_save = AsyncMock()
        
        with patch(
            "custom_components.ai_home_copilot.collective_intelligence.Store",
            return_value=mock_store,
        ):
            collective = CollectiveIntelligence(
                hass=hass,
                home_id="home_test",
                home_name="Test Home",
                min_contribution_score=0.5,
            )
            await collective.async_initialize()
            
            pattern = await collective.async_create_pattern(
                model_id="habit_model",
                pattern_type="habit",
                category="lighting",
                weights={"light_on": 0.8, "time_evening": 0.6},
                metadata={"zone": "living_room"},
                confidence=0.8,  # Above threshold
            )
            
            assert pattern is not None
            assert pattern.pattern_type == "habit"
            assert pattern.category == "lighting"
            assert pattern.confidence == 0.8
            assert pattern.contributed_by == "home_test"
            
    @pytest.mark.asyncio
    async def test_receive_patterns(self):
        """Test receiving patterns from other homes."""
        from custom_components.ai_home_copilot.collective_intelligence import (
            CollectiveIntelligence,
            SharedPattern,
        )
        
        hass = MagicMock()
        hass.data = {}
        
        mock_store = AsyncMock()
        mock_store.async_load = AsyncMock(return_value=None)
        mock_store.async_save = AsyncMock()
        
        with patch(
            "custom_components.ai_home_copilot.collective_intelligence.Store",
            return_value=mock_store,
        ):
            collective = CollectiveIntelligence(
                hass=hass,
                home_id="home_test",
                home_name="Test Home",
            )
            await collective.async_initialize()
            
            import time
            
            # Create pattern from another home
            pattern = SharedPattern(
                pattern_id="pattern_123",
                pattern_type="habit",
                category="lighting",
                anonymized_weights={"light_on": 0.7},
                metadata={"zone": "bedroom"},
                contributed_by="home_other",
                confidence=0.8,
                created_at=time.time(),
                expires_at=time.time() + 86400,
            )
            
            added = await collective.async_receive_patterns([pattern])
            
            assert added == 1
            assert "pattern_123" in collective.shared_patterns
            
    @pytest.mark.asyncio
    async def test_receive_own_pattern_ignored(self):
        """Test that own patterns are ignored."""
        from custom_components.ai_home_copilot.collective_intelligence import (
            CollectiveIntelligence,
            SharedPattern,
        )
        
        hass = MagicMock()
        hass.data = {}
        
        mock_store = AsyncMock()
        mock_store.async_load = AsyncMock(return_value=None)
        mock_store.async_save = AsyncMock()
        
        with patch(
            "custom_components.ai_home_copilot.collective_intelligence.Store",
            return_value=mock_store,
        ):
            collective = CollectiveIntelligence(
                hass=hass,
                home_id="home_test",
                home_name="Test Home",
            )
            await collective.async_initialize()
            
            import time
            
            # Create pattern from same home
            pattern = SharedPattern(
                pattern_id="pattern_own",
                pattern_type="habit",
                category="lighting",
                anonymized_weights={"light_on": 0.7},
                metadata={},
                contributed_by="home_test",  # Same as collective.home_id
                confidence=0.8,
                created_at=time.time(),
                expires_at=time.time() + 86400,
            )
            
            added = await collective.async_receive_patterns([pattern])
            
            assert added == 0
            
    def test_get_patterns_by_type(self):
        """Test filtering patterns by type."""
        from custom_components.ai_home_copilot.collective_intelligence import (
            CollectiveIntelligence,
            SharedPattern,
        )
        
        hass = MagicMock()
        
        collective = CollectiveIntelligence(
            hass=hass,
            home_id="home_test",
            home_name="Test Home",
        )
        
        import time
        
        # Add test patterns
        patterns = [
            SharedPattern(
                pattern_id="p1",
                pattern_type="habit",
                category="lighting",
                anonymized_weights={},
                metadata={},
                contributed_by="home_other",
                confidence=0.8,
                created_at=time.time(),
                expires_at=time.time() + 86400,
            ),
            SharedPattern(
                pattern_id="p2",
                pattern_type="habit",
                category="climate",
                anonymized_weights={},
                metadata={},
                contributed_by="home_other",
                confidence=0.7,
                created_at=time.time(),
                expires_at=time.time() + 86400,
            ),
            SharedPattern(
                pattern_id="p3",
                pattern_type="energy",
                category="usage",
                anonymized_weights={},
                metadata={},
                contributed_by="home_other",
                confidence=0.9,
                created_at=time.time(),
                expires_at=time.time() + 86400,
            ),
        ]
        
        collective.shared_patterns = {p.pattern_id: p for p in patterns}
        
        # Filter by type
        habit_patterns = collective.get_patterns_by_type("habit")
        assert len(habit_patterns) == 2
        
        # Filter by type and category
        lighting_patterns = collective.get_patterns_by_type("habit", "lighting")
        assert len(lighting_patterns) == 1
        assert lighting_patterns[0].category == "lighting"
        
    def test_get_aggregate_for_type(self):
        """Test aggregation of patterns."""
        from custom_components.ai_home_copilot.collective_intelligence import (
            CollectiveIntelligence,
            SharedPattern,
        )
        
        hass = MagicMock()
        
        collective = CollectiveIntelligence(
            hass=hass,
            home_id="home_test",
            home_name="Test Home",
        )
        
        import time
        
        # Add test patterns
        patterns = [
            SharedPattern(
                pattern_id="p1",
                pattern_type="habit",
                category="lighting",
                anonymized_weights={"light_on": 0.8, "time_evening": 0.6},
                metadata={},
                contributed_by="home_a",
                confidence=0.8,
                created_at=time.time(),
                expires_at=time.time() + 86400,
            ),
            SharedPattern(
                pattern_id="p2",
                pattern_type="habit",
                category="lighting",
                anonymized_weights={"light_on": 0.6, "time_evening": 0.8},
                metadata={},
                contributed_by="home_b",
                confidence=0.6,
                created_at=time.time(),
                expires_at=time.time() + 86400,
            ),
        ]
        
        collective.shared_patterns = {p.pattern_id: p for p in patterns}
        
        aggregate = collective.get_aggregate_for_type("habit")
        
        assert aggregate["count"] == 2
        assert aggregate["pattern_type"] == "habit"
        assert "light_on" in aggregate["aggregated_weights"]
        assert "time_evening" in aggregate["aggregated_weights"]
        
    def test_get_stats(self):
        """Test getting statistics."""
        from custom_components.ai_home_copilot.collective_intelligence import (
            CollectiveIntelligence,
        )
        
        hass = MagicMock()
        
        collective = CollectiveIntelligence(
            hass=hass,
            home_id="home_test",
            home_name="Test Home",
            privacy_epsilon=0.5,
        )
        
        stats = collective.get_stats()
        
        assert stats["home_id"] == "home_test"
        assert stats["local_models"] == 0
        assert stats["shared_patterns"] == 0
        assert stats["privacy_epsilon"] == 0.5
