"""Tests for MoodContextModule cache integration (v4.3.0).

Tests the cache pre-load on startup and persist-on-fetch behavior
added in v4.3.0 (mood_store integration).
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def hass():
    hass = MagicMock()
    hass.data = {}
    return hass


@pytest.fixture
def module(hass):
    from custom_components.ai_home_copilot.core.modules.mood_context_module import (
        MoodContextModule,
    )

    return MoodContextModule(hass, "http://localhost:8909", "test_token")


# ---------- Pre-load from cache ----------


@pytest.mark.asyncio
async def test_start_preloads_from_cache(hass, module):
    """async_start should pre-load zone moods from HA cache."""
    cached = {"living": {"comfort": 0.6, "joy": 0.8, "frugality": 0.3}}

    with patch(
        "custom_components.ai_home_copilot.mood_store.async_load_moods",
        new_callable=AsyncMock,
        return_value=cached,
    ) as mock_load:
        # Patch the polling loop so it doesn't actually start
        with patch.object(module, "_polling_loop", new_callable=AsyncMock):
            await module.async_start()

        mock_load.assert_called_once_with(hass)
        assert module._zone_moods == cached
        assert module._using_cache is True


@pytest.mark.asyncio
async def test_start_no_cache_available(hass, module):
    """async_start should handle missing cache gracefully."""
    with patch(
        "custom_components.ai_home_copilot.mood_store.async_load_moods",
        new_callable=AsyncMock,
        return_value={},
    ):
        with patch.object(module, "_polling_loop", new_callable=AsyncMock):
            await module.async_start()

    assert module._zone_moods == {}
    assert module._using_cache is False


@pytest.mark.asyncio
async def test_start_cache_exception_handled(hass, module):
    """async_start should not crash if cache load raises."""
    with patch(
        "custom_components.ai_home_copilot.mood_store.async_load_moods",
        new_callable=AsyncMock,
        side_effect=Exception("storage corrupt"),
    ):
        with patch.object(module, "_polling_loop", new_callable=AsyncMock):
            # Should not raise
            await module.async_start()

    assert module._zone_moods == {}


# ---------- _using_cache flag ----------


def test_using_cache_flag_default(module):
    """_using_cache defaults to False."""
    assert module._using_cache is False


# ---------- Module initialisation ----------


def test_init_creates_empty_state(hass):
    from custom_components.ai_home_copilot.core.modules.mood_context_module import (
        MoodContextModule,
    )

    m = MoodContextModule(hass, "http://core:8909", "tok")
    assert m._zone_moods == {}
    assert m._last_update is None
    assert m._using_cache is False
    assert m._update_task is None


# ---------- start idempotence ----------


@pytest.mark.asyncio
async def test_start_is_idempotent(hass, module):
    """Calling async_start twice should not create two polling tasks."""
    with patch(
        "custom_components.ai_home_copilot.mood_store.async_load_moods",
        new_callable=AsyncMock,
        return_value={},
    ):
        with patch.object(module, "_polling_loop", new_callable=AsyncMock):
            await module.async_start()
            first_task = module._update_task
            await module.async_start()
            assert module._update_task is first_task
