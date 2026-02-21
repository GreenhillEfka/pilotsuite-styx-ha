"""Unit tests for mood_store — HA Storage API persistence."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_hass():
    """Create a mock HA instance with empty data dict."""
    hass = MagicMock()
    hass.data = {}
    return hass


@pytest.fixture
def mock_store():
    """Create a mock Store instance."""
    store = MagicMock()
    store.async_load = AsyncMock(return_value=None)
    store.async_save = AsyncMock()
    return store


@pytest.mark.asyncio
async def test_get_store_creates_singleton(mock_hass, mock_store):
    """_get_store creates Store once and reuses it."""
    with patch(
        "custom_components.ai_home_copilot.mood_store.Store",
        return_value=mock_store,
    ):
        from custom_components.ai_home_copilot.mood_store import _get_store

        s1 = await _get_store(mock_hass)
        s2 = await _get_store(mock_hass)
        assert s1 is s2, "Store should be reused (singleton)"


@pytest.mark.asyncio
async def test_save_moods_persists_zones(mock_hass, mock_store):
    """async_save_moods writes zones + timestamp."""
    with patch(
        "custom_components.ai_home_copilot.mood_store.Store",
        return_value=mock_store,
    ):
        from custom_components.ai_home_copilot.mood_store import async_save_moods

        zones = {
            "living_room": {"comfort": 0.8, "joy": 0.7, "frugality": 0.3},
            "bedroom": {"comfort": 0.5, "joy": 0.2, "frugality": 0.6},
        }
        await async_save_moods(mock_hass, zones)

        mock_store.async_save.assert_called_once()
        saved = mock_store.async_save.call_args[0][0]
        assert "ts" in saved
        assert saved["zones"] == zones
        assert isinstance(saved["ts"], float)


@pytest.mark.asyncio
async def test_load_moods_returns_cached(mock_hass, mock_store):
    """async_load_moods returns zones when cache is fresh."""
    zones = {"kitchen": {"comfort": 0.6}}
    mock_store.async_load = AsyncMock(
        return_value={"ts": time.time(), "zones": zones}
    )

    with patch(
        "custom_components.ai_home_copilot.mood_store.Store",
        return_value=mock_store,
    ):
        from custom_components.ai_home_copilot.mood_store import async_load_moods

        result = await async_load_moods(mock_hass)
        assert result == zones


@pytest.mark.asyncio
async def test_load_moods_expired_returns_empty(mock_hass, mock_store):
    """async_load_moods returns {} when cache exceeds 24h TTL."""
    mock_store.async_load = AsyncMock(
        return_value={
            "ts": time.time() - 90000,  # 25 hours ago
            "zones": {"old": {"comfort": 0.1}},
        }
    )

    with patch(
        "custom_components.ai_home_copilot.mood_store.Store",
        return_value=mock_store,
    ):
        from custom_components.ai_home_copilot.mood_store import async_load_moods

        result = await async_load_moods(mock_hass)
        assert result == {}


@pytest.mark.asyncio
async def test_load_moods_no_data_returns_empty(mock_hass, mock_store):
    """async_load_moods returns {} when store has no data."""
    mock_store.async_load = AsyncMock(return_value=None)

    with patch(
        "custom_components.ai_home_copilot.mood_store.Store",
        return_value=mock_store,
    ):
        from custom_components.ai_home_copilot.mood_store import async_load_moods

        result = await async_load_moods(mock_hass)
        assert result == {}


@pytest.mark.asyncio
async def test_load_moods_invalid_data_returns_empty(mock_hass, mock_store):
    """async_load_moods returns {} for non-dict data."""
    mock_store.async_load = AsyncMock(return_value="invalid")

    with patch(
        "custom_components.ai_home_copilot.mood_store.Store",
        return_value=mock_store,
    ):
        from custom_components.ai_home_copilot.mood_store import async_load_moods

        result = await async_load_moods(mock_hass)
        assert result == {}


@pytest.mark.asyncio
async def test_load_moods_missing_ts_returns_empty(mock_hass, mock_store):
    """async_load_moods returns {} when ts field is 0 (epoch = stale)."""
    mock_store.async_load = AsyncMock(
        return_value={"zones": {"x": {}}}  # no "ts" key → defaults to 0
    )

    with patch(
        "custom_components.ai_home_copilot.mood_store.Store",
        return_value=mock_store,
    ):
        from custom_components.ai_home_copilot.mood_store import async_load_moods

        result = await async_load_moods(mock_hass)
        assert result == {}


@pytest.mark.asyncio
async def test_roundtrip_save_load(mock_hass):
    """Verify save → load roundtrip returns same data."""
    # Use a real-ish mock that stores data
    stored_data = {}

    async def fake_save(data):
        stored_data["payload"] = data

    async def fake_load():
        return stored_data.get("payload")

    store = MagicMock()
    store.async_save = AsyncMock(side_effect=fake_save)
    store.async_load = AsyncMock(side_effect=fake_load)

    with patch(
        "custom_components.ai_home_copilot.mood_store.Store",
        return_value=store,
    ):
        from custom_components.ai_home_copilot.mood_store import (
            async_load_moods,
            async_save_moods,
        )

        zones = {"office": {"comfort": 0.9, "joy": 0.4, "frugality": 0.7}}
        await async_save_moods(mock_hass, zones)
        result = await async_load_moods(mock_hass)
        assert result == zones
