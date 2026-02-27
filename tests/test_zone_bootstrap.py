"""Tests for ZoneBootstrapModule -- loads zones_config.json into HabitusZoneStore V2.

Covers:
- Initial load when store is empty
- Skip when store already has zones
- Reload service re-loads zones (forced)
- zones_config.json is valid JSON with 9 zones
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

DOMAIN = "ai_home_copilot"

# Path to the real zones_config.json bundled with the integration
_ZONES_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "ai_home_copilot"
    / "data"
    / "zones_config.json"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ctx(hass=None, entry=None):
    """Build a minimal ModuleContext mock."""
    from custom_components.ai_home_copilot.core.module import ModuleContext

    if hass is None:
        hass = MagicMock()
        hass.services = MagicMock()
        hass.async_add_executor_job = AsyncMock()
    if entry is None:
        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.domain = DOMAIN
    return ModuleContext(hass=hass, entry=entry)


# ---------------------------------------------------------------------------
# Tests: zones_config.json integrity
# ---------------------------------------------------------------------------

class TestZonesConfigFile:
    """Validate the bundled zones_config.json."""

    def test_file_exists(self):
        assert _ZONES_CONFIG_PATH.exists(), f"zones_config.json not found at {_ZONES_CONFIG_PATH}"

    def test_valid_json(self):
        with open(_ZONES_CONFIG_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        assert isinstance(data, dict)

    def test_has_9_zones(self):
        with open(_ZONES_CONFIG_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        zones = data.get("zones", [])
        assert len(zones) == 9, f"Expected 9 zones, got {len(zones)}"

    def test_each_zone_has_required_keys(self):
        with open(_ZONES_CONFIG_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        for zone in data["zones"]:
            assert "zone_id" in zone, f"Zone missing zone_id: {zone}"
            assert "name" in zone, f"Zone missing name: {zone}"
            assert "entities" in zone, f"Zone missing entities: {zone}"


# ---------------------------------------------------------------------------
# Tests: ZoneBootstrapModule lifecycle
# ---------------------------------------------------------------------------

class TestZoneBootstrapSetup:
    """Test async_setup_entry behaviour."""

    @pytest.mark.asyncio
    async def test_loads_zones_when_store_empty(self):
        """When no zones exist in store, module should load from file."""
        from custom_components.ai_home_copilot.core.modules.zone_bootstrap import (
            ZoneBootstrapModule,
        )

        ctx = _make_ctx()

        with patch(
            "custom_components.ai_home_copilot.core.modules.zone_bootstrap.async_get_zones_v2",
            new_callable=AsyncMock,
            return_value=[],  # store is empty
        ) as mock_get, patch(
            "custom_components.ai_home_copilot.core.modules.zone_bootstrap.async_set_zones_v2_from_raw",
            new_callable=AsyncMock,
            return_value=[MagicMock()] * 9,
        ) as mock_set, patch(
            "custom_components.ai_home_copilot.core.modules.zone_bootstrap.async_dispatcher_send",
        ):
            # async_add_executor_job should call the function synchronously for our test
            ctx.hass.async_add_executor_job = AsyncMock(
                side_effect=lambda fn, *a: fn(*a) if callable(fn) else None
            )
            module = ZoneBootstrapModule()
            await module.async_setup_entry(ctx)

            mock_get.assert_awaited_once()
            mock_set.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_skips_when_store_has_zones(self):
        """When zones already exist, module should NOT reload from file."""
        from custom_components.ai_home_copilot.core.modules.zone_bootstrap import (
            ZoneBootstrapModule,
        )

        ctx = _make_ctx()
        existing_zones = [MagicMock()] * 5

        with patch(
            "custom_components.ai_home_copilot.core.modules.zone_bootstrap.async_get_zones_v2",
            new_callable=AsyncMock,
            return_value=existing_zones,
        ), patch(
            "custom_components.ai_home_copilot.core.modules.zone_bootstrap.async_set_zones_v2_from_raw",
            new_callable=AsyncMock,
        ) as mock_set:
            module = ZoneBootstrapModule()
            await module.async_setup_entry(ctx)

            mock_set.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_reload_service_registered(self):
        """The reload service should be registered on setup."""
        from custom_components.ai_home_copilot.core.modules.zone_bootstrap import (
            SERVICE_RELOAD,
            ZoneBootstrapModule,
        )

        ctx = _make_ctx()

        with patch(
            "custom_components.ai_home_copilot.core.modules.zone_bootstrap.async_get_zones_v2",
            new_callable=AsyncMock,
            return_value=[MagicMock()],
        ):
            module = ZoneBootstrapModule()
            await module.async_setup_entry(ctx)

        ctx.hass.services.async_register.assert_called_once()
        call_args = ctx.hass.services.async_register.call_args
        assert call_args[0][0] == DOMAIN
        assert call_args[0][1] == SERVICE_RELOAD

    @pytest.mark.asyncio
    async def test_reload_service_forces_load(self):
        """Calling the reload service handler should force-load zones."""
        from custom_components.ai_home_copilot.core.modules.zone_bootstrap import (
            ZoneBootstrapModule,
        )

        ctx = _make_ctx()
        ctx.hass.async_add_executor_job = AsyncMock(
            side_effect=lambda fn, *a: fn(*a) if callable(fn) else None
        )

        with patch(
            "custom_components.ai_home_copilot.core.modules.zone_bootstrap.async_get_zones_v2",
            new_callable=AsyncMock,
            return_value=[MagicMock()],
        ), patch(
            "custom_components.ai_home_copilot.core.modules.zone_bootstrap.async_set_zones_v2_from_raw",
            new_callable=AsyncMock,
            return_value=[MagicMock()] * 9,
        ) as mock_set, patch(
            "custom_components.ai_home_copilot.core.modules.zone_bootstrap.async_dispatcher_send",
        ):
            module = ZoneBootstrapModule()
            await module.async_setup_entry(ctx)

            # Extract the reload handler
            handler = ctx.hass.services.async_register.call_args[0][2]
            mock_set.reset_mock()
            await handler(MagicMock())

            mock_set.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unload_removes_service(self):
        """Unloading the module should remove the reload service."""
        from custom_components.ai_home_copilot.core.modules.zone_bootstrap import (
            SERVICE_RELOAD,
            ZoneBootstrapModule,
        )

        ctx = _make_ctx()

        with patch(
            "custom_components.ai_home_copilot.core.modules.zone_bootstrap.async_get_zones_v2",
            new_callable=AsyncMock,
            return_value=[MagicMock()],
        ):
            module = ZoneBootstrapModule()
            await module.async_setup_entry(ctx)
            result = await module.async_unload_entry(ctx)

        assert result is True
        ctx.hass.services.async_remove.assert_called_once_with(DOMAIN, SERVICE_RELOAD)
