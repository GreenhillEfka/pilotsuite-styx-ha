from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .blueprints import async_install_blueprints
from .const import CONF_WEBHOOK_ID, DOMAIN
from .coordinator import CopilotDataUpdateCoordinator
from .seed_adapter import async_setup_seed_adapter
from .devlog_push import async_setup_devlog_push
from .webhook import async_register_webhook, async_unregister_webhook

PLATFORMS: list[str] = ["binary_sensor", "sensor", "button", "text", "number"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = CopilotDataUpdateCoordinator(hass, entry.data | entry.options)

    # Ship blueprints with the integration (no automations are created).
    await async_install_blueprints(hass)

    # Webhook push mode (primary). We still do one initial refresh for baseline state.
    await coordinator.async_config_entry_first_refresh()

    webhook_id = await async_register_webhook(hass, entry, coordinator)

    # Optional dev tool: push sanitized HA log snippets to Copilot-Core.
    unsub_devlog_push = await async_setup_devlog_push(hass, entry, coordinator_api=coordinator.api)

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "webhook_id": webhook_id,
        "unsub_devlog_push": unsub_devlog_push,
    }

    # Optional: ingest suggestion seeds from other sensor entities.
    await async_setup_seed_adapter(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
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

        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
