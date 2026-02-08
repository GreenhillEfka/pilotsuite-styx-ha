from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ...blueprints import async_install_blueprints
from ...const import DOMAIN
from ...coordinator import CopilotDataUpdateCoordinator
from ...devlog_push import async_setup_devlog_push
from ...ha_errors_digest import async_setup_ha_errors_digest
from ...seed_adapter import async_setup_seed_adapter
from ...media_setup import async_setup_media_context, async_unload_media_context
from ...webhook import async_register_webhook, async_unregister_webhook
from ...core_v1 import async_fetch_core_capabilities
from ..module import ModuleContext


PLATFORMS: list[str] = ["binary_sensor", "sensor", "button", "text", "number"]


class LegacyModule:
    """Preserves the existing single-module integration behavior."""

    name = "legacy"

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        hass: HomeAssistant = ctx.hass
        entry: ConfigEntry = ctx.entry

        coordinator = CopilotDataUpdateCoordinator(hass, entry.data | entry.options)

        # Ship blueprints with the integration (no automations are created).
        await async_install_blueprints(hass)

        # Webhook push mode (primary). We still do one initial refresh for baseline state.
        await coordinator.async_config_entry_first_refresh()

        webhook_id = await async_register_webhook(hass, entry, coordinator)

        # Optional dev tool: push sanitized HA log snippets to Copilot-Core.
        unsub_devlog_push = await async_setup_devlog_push(
            hass, entry, coordinator_api=coordinator.api
        )

        # Local HA log digest (opt-in): surfaces relevant warnings/errors via notifications.
        unsub_ha_errors = await async_setup_ha_errors_digest(hass, entry)

        hass.data[DOMAIN][entry.entry_id] = {
            "coordinator": coordinator,
            "webhook_id": webhook_id,
            "unsub_devlog_push": unsub_devlog_push,
            "unsub_ha_errors": unsub_ha_errors,
        }

        # Core API v1: capabilities ping (best-effort, read-only).
        # Old cores will return 404; this is expected and shown in the sensor.
        await async_fetch_core_capabilities(hass, entry, api=coordinator.api)

        # Read-only media context (music vs TV/other).
        await async_setup_media_context(hass, entry)

        # Optional: ingest suggestion seeds from other sensor entities.
        await async_setup_seed_adapter(hass, entry)

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        hass: HomeAssistant = ctx.hass
        entry: ConfigEntry = ctx.entry

        data = hass.data[DOMAIN].get(entry.entry_id)
        webhook_id = None
        if isinstance(data, dict):
            webhook_id = data.get("webhook_id")

        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        if unload_ok:
            if webhook_id:
                await async_unregister_webhook(hass, webhook_id)

            data = hass.data[DOMAIN].get(entry.entry_id)

            unsub = data.get("unsub_seed_adapter") if isinstance(data, dict) else None
            if callable(unsub):
                unsub()

            unsub_devlog = data.get("unsub_devlog_push") if isinstance(data, dict) else None
            if callable(unsub_devlog):
                unsub_devlog()

            unsub_ha_errors = data.get("unsub_ha_errors") if isinstance(data, dict) else None
            if callable(unsub_ha_errors):
                unsub_ha_errors()

            await async_unload_media_context(hass, entry)

            hass.data[DOMAIN].pop(entry.entry_id, None)

        return unload_ok
