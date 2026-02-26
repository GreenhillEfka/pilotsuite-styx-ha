"""Coordinator Module - Clean replacement for legacy coordinator setup.

Replaces the monolithic legacy.py with focused responsibilities:
  - Creates and initializes CopilotDataUpdateCoordinator
  - Registers webhook for real-time Core pushes
  - Fetches Core API capabilities
  - No platform forwarding (handled by legacy.py still for entity setup)

This module runs first and makes the coordinator available for all other modules.
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ...const import DOMAIN
from ...coordinator import CopilotDataUpdateCoordinator
from ...core_v1 import async_fetch_core_capabilities
from ...webhook import async_register_webhook, async_unregister_webhook
from ..module import ModuleContext

_LOGGER = logging.getLogger(__name__)


class CoordinatorModule:
    """Dedicated module for coordinator lifecycle management."""

    name = "coordinator"

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        hass: HomeAssistant = ctx.hass
        entry: ConfigEntry = ctx.entry

        # Check if coordinator already exists (set up by legacy module)
        data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if isinstance(data, dict) and data.get("coordinator"):
            _LOGGER.debug("Coordinator already initialized by legacy module — skipping")
            return

        coordinator = CopilotDataUpdateCoordinator(hass, entry.data | entry.options)

        # Best-effort first refresh
        try:
            await coordinator.async_config_entry_first_refresh()
        except Exception:  # noqa: BLE001
            _LOGGER.warning(
                "PilotSuite Core not reachable at startup — "
                "entities will update automatically when Core comes online"
            )
            coordinator.data = {
                "ok": False,
                "version": "unknown",
                "mood": {"mood": "unknown", "confidence": 0.0},
                "neurons": {},
                "dominant_mood": "unknown",
                "mood_confidence": 0.0,
                "habit_summary": {},
                "predictions": [],
                "sequences": [],
                "core_modules": {},
                "brain_summary": {},
                "habitus_rules": {},
            }

        # Register webhook
        webhook_id = None
        try:
            webhook_id = await async_register_webhook(hass, entry, coordinator)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Failed to register webhook")

        # Store coordinator data
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN].setdefault(entry.entry_id, {})
        hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator
        hass.data[DOMAIN][entry.entry_id]["webhook_id"] = webhook_id

        # Fetch Core capabilities (best-effort)
        try:
            await async_fetch_core_capabilities(hass, entry, api=coordinator.api)
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Core API capabilities fetch failed (non-blocking)")

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        hass: HomeAssistant = ctx.hass
        entry: ConfigEntry = ctx.entry

        data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if isinstance(data, dict):
            webhook_id = data.get("webhook_id")
            if webhook_id:
                await async_unregister_webhook(hass, webhook_id)

        return True
