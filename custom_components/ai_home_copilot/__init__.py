from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .blueprints import async_install_blueprints
from .const import CONF_WEBHOOK_ID, DOMAIN
from .coordinator import CopilotDataUpdateCoordinator
from .webhook import async_register_webhook, async_unregister_webhook

PLATFORMS: list[str] = ["binary_sensor", "sensor", "button"]


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

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "webhook_id": webhook_id,
    }

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
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
