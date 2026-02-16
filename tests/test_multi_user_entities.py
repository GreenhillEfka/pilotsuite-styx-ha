"""Tests fuer Multi-User Preference Entities (ActiveUsersSensor, UserMoodSensor).

Unit-Tests ohne Home Assistant Abhaengigkeit. MUPL-Modul wird gemockt.
"""
from __future__ import annotations

import sys
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# Mock HA modules before import
sys.modules.setdefault("homeassistant", MagicMock())
sys.modules.setdefault("homeassistant.components", MagicMock())
sys.modules.setdefault("homeassistant.components.sensor", MagicMock())
sys.modules.setdefault("homeassistant.helpers", MagicMock())
sys.modules.setdefault("homeassistant.helpers.entity", MagicMock())
sys.modules.setdefault("homeassistant.helpers.entity_platform", MagicMock())
sys.modules.setdefault("homeassistant.core", MagicMock())
sys.modules.setdefault("homeassistant.config_entries", MagicMock())

# Provide SensorEntity as a real base class for testing
from unittest.mock import MagicMock as _MM

class _FakeSensorEntity:
    _attr_native_value = None
    _attr_extra_state_attributes = {}
    _attr_name = ""
    _attr_icon = ""
    _attr_unique_id = ""

sys.modules["homeassistant.components.sensor"].SensorEntity = _FakeSensorEntity
sys.modules["homeassistant.components.sensor"].SensorDeviceClass = MagicMock()
sys.modules["homeassistant.helpers.entity"].EntityCategory = MagicMock()
sys.modules["homeassistant.helpers.entity"].EntityCategory.DIAGNOSTIC = "diagnostic"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_module():
    """Mock MultiUserPreferenceModule."""
    module = MagicMock()
    module.get_all_users.return_value = {
        "person.andreas": MagicMock(name="Andreas"),
        "person.steffi": MagicMock(name="Steffi"),
    }
    module.detect_active_users = AsyncMock(
        return_value=["person.andreas", "person.steffi"]
    )
    module.get_user_name.side_effect = lambda uid: {
        "person.andreas": "Andreas",
        "person.steffi": "Steffi",
    }.get(uid, "Unknown")
    module.get_user_preferences.return_value = {
        "mood_weights": {"comfort": 0.8, "frugality": 0.3, "joy": 0.6},
    }
    return module


# ---------------------------------------------------------------------------
# ActiveUsersSensor Tests
# ---------------------------------------------------------------------------

class TestActiveUsersSensor:

    def _make_sensor(self, module):
        # Import after mocks are set up
        from custom_components.ai_home_copilot.multi_user_preferences_entities import (
            ActiveUsersSensor,
        )
        return ActiveUsersSensor(module)

    @pytest.mark.asyncio
    async def test_update_count(self, mock_module):
        sensor = self._make_sensor(mock_module)
        await sensor.async_update()
        assert sensor._attr_native_value == 2

    @pytest.mark.asyncio
    async def test_update_attributes(self, mock_module):
        sensor = self._make_sensor(mock_module)
        await sensor.async_update()
        attrs = sensor._attr_extra_state_attributes
        assert "users" in attrs
        assert "user_names" in attrs
        assert "total_known_users" in attrs
        assert attrs["total_known_users"] == 2

    @pytest.mark.asyncio
    async def test_no_active_users(self, mock_module):
        mock_module.detect_active_users = AsyncMock(return_value=[])
        sensor = self._make_sensor(mock_module)
        await sensor.async_update()
        assert sensor._attr_native_value == 0

    def test_unique_id(self, mock_module):
        sensor = self._make_sensor(mock_module)
        assert "active_users" in sensor._attr_unique_id


# ---------------------------------------------------------------------------
# UserMoodSensor Tests
# ---------------------------------------------------------------------------

class TestUserMoodSensor:

    def _make_sensor(self, module, user_id="person.andreas", user_name="Andreas"):
        from custom_components.ai_home_copilot.multi_user_preferences_entities import (
            UserMoodSensor,
        )
        return UserMoodSensor(module, user_id, user_name)

    @pytest.mark.asyncio
    async def test_comfortable_mood(self, mock_module):
        mock_module.get_user_preferences.return_value = {
            "mood_weights": {"comfort": 0.8, "frugality": 0.3, "joy": 0.4},
        }
        sensor = self._make_sensor(mock_module)
        await sensor.async_update()
        assert sensor._attr_native_value == "comfortable"

    @pytest.mark.asyncio
    async def test_joyful_mood(self, mock_module):
        mock_module.get_user_preferences.return_value = {
            "mood_weights": {"comfort": 0.5, "frugality": 0.3, "joy": 0.9},
        }
        sensor = self._make_sensor(mock_module)
        await sensor.async_update()
        assert sensor._attr_native_value == "joyful"

    @pytest.mark.asyncio
    async def test_neutral_mood(self, mock_module):
        mock_module.get_user_preferences.return_value = {
            "mood_weights": {"comfort": 0.3, "frugality": 0.3, "joy": 0.3},
        }
        sensor = self._make_sensor(mock_module)
        await sensor.async_update()
        assert sensor._attr_native_value == "neutral"

    @pytest.mark.asyncio
    async def test_unknown_when_no_prefs(self, mock_module):
        mock_module.get_user_preferences.return_value = None
        sensor = self._make_sensor(mock_module)
        await sensor.async_update()
        assert sensor._attr_native_value == "unknown"

    @pytest.mark.asyncio
    async def test_attributes_include_user_info(self, mock_module):
        sensor = self._make_sensor(mock_module)
        await sensor.async_update()
        attrs = sensor._attr_extra_state_attributes
        assert attrs["user_id"] == "person.andreas"
        assert attrs["user_name"] == "Andreas"

    def test_unique_id_contains_user(self, mock_module):
        sensor = self._make_sensor(mock_module, "person.andreas", "Andreas")
        assert "mood" in sensor._attr_unique_id
        assert "andreas" in sensor._attr_unique_id

    def test_name_contains_user(self, mock_module):
        sensor = self._make_sensor(mock_module, "person.steffi", "Steffi")
        assert "Steffi" in sensor._attr_name
