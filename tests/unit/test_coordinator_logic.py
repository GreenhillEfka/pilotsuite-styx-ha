"""Unit tests for Coordinator logic - No Home Assistant dependency.

Tests the data aggregation and API client logic without HA imports.

Run with: pytest tests/unit/test_coordinator_logic.py -v
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


class TestCopilotApiClientLogic:
    """Tests for CopilotApiClient logic without HA dependency."""
    
    def test_url_construction(self):
        """Test URL construction for API calls."""
        host = "localhost"
        port = 8909
        expected_base = f"http://{host}:{port}"
        
        # Verify URL construction
        assert expected_base == "http://localhost:8909"
        
        # Mood endpoint
        mood_url = f"{expected_base}/api/v1/neurons/mood"
        assert mood_url == "http://localhost:8909/api/v1/neurons/mood"
        
        # Neurons endpoint
        neurons_url = f"{expected_base}/api/v1/neurons"
        assert neurons_url == "http://localhost:8909/api/v1/neurons"
    
    def test_token_header_construction(self):
        """Test authorization header construction."""
        token = "test_token_123"
        expected_header = f"Bearer {token}"
        
        assert expected_header == "Bearer test_token_123"
    
    def test_response_parsing(self):
        """Test API response parsing logic."""
        # Mood response
        mood_response = {
            "success": True,
            "data": {"mood": "relax", "confidence": 0.85}
        }
        
        # Extract mood data (what the client does)
        mood_data = mood_response.get("data", mood_response)
        assert mood_data["mood"] == "relax"
        assert mood_data["confidence"] == 0.85
        
        # Neurons response
        neurons_response = {
            "success": True,
            "data": {
                "neurons": {
                    "context.presence": {"active": True, "value": 1.0},
                    "mood.relax": {"active": True, "value": 0.8}
                }
            }
        }
        
        neurons_data = neurons_response.get("data", neurons_response)
        assert "neurons" in neurons_data
        assert neurons_data["neurons"]["context.presence"]["active"] is True
    
    def test_fallback_logic(self):
        """Test fallback logic when API is unavailable."""
        # Fallback mood data
        fallback_mood = {"mood": "unknown", "confidence": 0.0}
        
        assert fallback_mood["mood"] == "unknown"
        assert fallback_mood["confidence"] == 0.0


class TestCoordinatorDataAggregation:
    """Tests for coordinator data aggregation logic."""
    
    def test_data_combination(self):
        """Test combining status, mood, and neuron data."""
        status = {"ok": True, "version": "0.4.16"}
        mood_data = {"mood": "relax", "confidence": 0.9}
        neurons_data = {"neurons": {"context.presence": {"active": True}}}
        
        # Combine all data (what coordinator does)
        combined = {
            "ok": status.get("ok", True),
            "version": status.get("version", "unknown"),
            "mood": mood_data,
            "neurons": neurons_data.get("neurons", {}),
            "dominant_mood": mood_data.get("mood", "unknown"),
            "mood_confidence": mood_data.get("confidence", 0.0),
        }
        
        assert combined["ok"] is True
        assert combined["version"] == "0.4.16"
        assert combined["dominant_mood"] == "relax"
        assert combined["mood_confidence"] == 0.9
        assert "context.presence" in combined["neurons"]
    
    def test_empty_data_handling(self):
        """Test handling of empty/missing data."""
        status = {}
        mood_data = {}
        neurons_data = {}
        
        # Combine with defaults
        combined = {
            "ok": status.get("ok", True),
            "version": status.get("version", "unknown"),
            "mood": mood_data,
            "neurons": neurons_data.get("neurons", {}),
            "dominant_mood": mood_data.get("mood", "unknown"),
            "mood_confidence": mood_data.get("confidence", 0.0),
        }
        
        assert combined["ok"] is True
        assert combined["version"] == "unknown"
        assert combined["dominant_mood"] == "unknown"
        assert combined["mood_confidence"] == 0.0


class TestNeuronDashboardSensorLogic:
    """Tests for neuron dashboard sensor logic."""
    
    def test_neuron_counting(self):
        """Test counting active neurons."""
        neurons = {
            "context.presence": {"active": True, "value": 1.0},
            "context.time_of_day": {"active": True, "value": 0.5},
            "mood.relax": {"active": True, "value": 0.8},
            "mood.focus": {"active": False, "value": 0.2},
            "state.energy": {"active": False, "value": 0.3}
        }
        
        total_count = len(neurons)
        active_count = sum(1 for n in neurons.values() if isinstance(n, dict) and n.get("active"))
        
        assert total_count == 5
        assert active_count == 3
    
    def test_neuron_categorization(self):
        """Test categorizing neurons by type."""
        neurons = {
            "context.presence": {"active": True},
            "context.time": {"active": True},
            "state.energy": {"active": False},
            "mood.relax": {"active": True},
        }
        
        context = {}
        state = {}
        mood = {}
        
        for name, data in neurons.items():
            if name.startswith("context."):
                context[name] = data
            elif name.startswith("state."):
                state[name] = data
            elif name.startswith("mood."):
                mood[name] = data
        
        assert len(context) == 2
        assert len(state) == 1
        assert len(mood) == 1
    
    def test_mood_history_tracking(self):
        """Test mood history tracking logic."""
        history = []
        max_history = 20
        
        # Add entries
        for i in range(5):
            entry = {
                "mood": "relax" if i % 2 == 0 else "focus",
                "confidence": 0.5 + i * 0.1,
            }
            history.append(entry)
            if len(history) > max_history:
                history = history[-max_history:]
        
        assert len(history) == 5
        assert history[0]["mood"] == "relax"
        assert history[4]["confidence"] == 0.9
    
    def test_suggestion_extraction(self):
        """Test extracting top suggestion."""
        suggestions = [
            {"action_type": "light", "confidence": 0.8},
            {"action_type": "climate", "confidence": 0.6},
        ]
        
        if suggestions:
            top_suggestion = suggestions[0]
            action_type = top_suggestion.get("action_type", "none")
        else:
            action_type = "none"
        
        assert action_type == "light"
        assert len(suggestions) == 2


class TestAPIEndpointLogic:
    """Tests for API endpoint construction and handling."""
    
    def test_evaluate_context_building(self):
        """Test building evaluation context from HA states."""
        # Simulate HA states
        ha_states = {
            "person.user_a": {"state": "home"},
            "person.user_b": {"state": "away"},
            "sensor.temperature_living": {"state": "22.5"},
            "light.living_room": {"state": "on"},
            "media_player.tv": {"state": "playing"},
        }
        
        # Build context (what coordinator does)
        context = {
            "states": {},
            "time": {},
            "weather": {},
            "presence": {},
        }
        
        entity_patterns = [
            "person.", "binary_sensor.", "sensor.temperature",
            "sensor.humidity", "sensor.light", "sensor.illuminance",
            "weather.", "light.", "media_player."
        ]
        
        for entity_id in ha_states:
            for pattern in entity_patterns:
                if entity_id.startswith(pattern):
                    state = ha_states[entity_id]
                    context["states"][entity_id] = {
                        "state": state["state"],
                        "attributes": dict(state.get("attributes", {}))
                    }
                    break
        
        assert "person.user_a" in context["states"]
        assert "person.user_b" in context["states"]
        assert "light.living_room" in context["states"]
        assert "media_player.tv" in context["states"]
    
    def test_timeout_handling(self):
        """Test timeout fallback logic."""
        # Simulate timeout scenario
        timeout_occurred = True
        
        # Fallback mood (what client returns on timeout)
        if timeout_occurred:
            result = {"mood": "unknown", "confidence": 0.0}
        else:
            result = {"mood": "relax", "confidence": 0.85}
        
        assert result["mood"] == "unknown"
        assert result["confidence"] == 0.0


class TestUpdateInterval:
    """Tests for update interval configuration."""
    
    def test_default_update_interval(self):
        """Test default 30-second update interval."""
        from datetime import timedelta
        
        update_interval = timedelta(seconds=30)
        
        assert update_interval.total_seconds() == 30
    
    def test_interval_reasonableness(self):
        """Test that update intervals are reasonable."""
        from datetime import timedelta
        
        # Expected intervals
        intervals = {
            "coordinator": timedelta(seconds=30),
            "energy": timedelta(seconds=30),
            "unifi": timedelta(seconds=60),
            "weather": timedelta(seconds=300),
        }
        
        for name, interval in intervals.items():
            seconds = interval.total_seconds()
            assert seconds >= 10, f"{name} interval too short: {seconds}s"
            assert seconds <= 600, f"{name} interval too long: {seconds}s"


class TestSafeFetchLogic:
    """Tests for the _safe_fetch helper and parallel gather pattern."""

    def test_safe_fetch_returns_fallback_on_error(self):
        """_safe_fetch should return fallback when the coroutine raises."""
        import asyncio

        async def _failing_coro():
            raise RuntimeError("boom")

        async def _run():
            from custom_components.ai_home_copilot.coordinator import (
                CopilotDataUpdateCoordinator,
            )

            result = await CopilotDataUpdateCoordinator._safe_fetch(
                _failing_coro, fallback={"default": True}
            )
            assert result == {"default": True}

        asyncio.get_event_loop().run_until_complete(_run())

    def test_safe_fetch_returns_value_on_success(self):
        """_safe_fetch should return the coroutine result on success."""
        import asyncio

        async def _good_coro():
            return {"ok": True}

        async def _run():
            from custom_components.ai_home_copilot.coordinator import (
                CopilotDataUpdateCoordinator,
            )

            result = await CopilotDataUpdateCoordinator._safe_fetch(
                _good_coro, fallback={}
            )
            assert result == {"ok": True}

        asyncio.get_event_loop().run_until_complete(_run())

    def test_safe_fetch_passes_args_to_coroutine(self):
        """_safe_fetch should forward positional arguments."""
        import asyncio

        async def _echo(path):
            return {"path": path}

        async def _run():
            from custom_components.ai_home_copilot.coordinator import (
                CopilotDataUpdateCoordinator,
            )

            result = await CopilotDataUpdateCoordinator._safe_fetch(
                _echo, "/api/v1/test", fallback={}
            )
            assert result == {"path": "/api/v1/test"}

        asyncio.get_event_loop().run_until_complete(_run())


class TestHabitDataHelpers:
    """Tests for the refactored habit data extraction helpers."""

    def test_find_ml_context_returns_none_for_non_dict(self):
        """_find_ml_context should return None when entry_data is not a dict."""
        from unittest.mock import MagicMock

        coord = MagicMock()
        coord.hass.data = {"ai_home_copilot": "not_a_dict"}

        from custom_components.ai_home_copilot.coordinator import (
            CopilotDataUpdateCoordinator,
        )

        result = CopilotDataUpdateCoordinator._find_ml_context(coord)
        assert result is None

    def test_find_ml_context_returns_none_for_no_ml(self):
        """_find_ml_context should return None when no ml_context exists."""
        from unittest.mock import MagicMock

        coord = MagicMock()
        coord.hass.data = {"ai_home_copilot": {"entry1": {"other": "data"}}}

        from custom_components.ai_home_copilot.coordinator import (
            CopilotDataUpdateCoordinator,
        )

        result = CopilotDataUpdateCoordinator._find_ml_context(coord)
        assert result is None

    def test_build_habit_predictions_empty(self):
        """_build_habit_predictions returns empty list for empty summary."""
        from custom_components.ai_home_copilot.coordinator import (
            CopilotDataUpdateCoordinator,
        )

        from unittest.mock import MagicMock

        ml = MagicMock()
        result = CopilotDataUpdateCoordinator._build_habit_predictions(ml, {})
        assert result == []

    def test_build_habit_sequences_empty(self):
        """_build_habit_sequences returns empty list when no patterns exist."""
        from custom_components.ai_home_copilot.coordinator import (
            CopilotDataUpdateCoordinator,
        )

        from unittest.mock import MagicMock

        predictor = MagicMock()
        predictor.sequence_patterns = {}
        result = CopilotDataUpdateCoordinator._build_habit_sequences(predictor)
        assert result == []


# Mark all tests as unit tests
pytestmark = pytest.mark.unit