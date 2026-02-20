"""HomeKit per-zone entities: toggle button, QR sensor, setup info.

Creates entities that allow enabling/disabling HomeKit per Habitus zone
and display the QR code + setup code for Apple Home pairing.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_HOST, CONF_PORT
from .coordinator import CopilotDataUpdateCoordinator
from .entity import CopilotBaseEntity
from .core.modules.homekit_bridge import (
    SIGNAL_HOMEKIT_ZONE_TOGGLED,
    get_homekit_bridge,
)

_LOGGER = logging.getLogger(__name__)


class HomeKitZoneToggleButton(CopilotBaseEntity, ButtonEntity):
    """Button to toggle HomeKit exposure for a Habitus zone."""

    _attr_icon = "mdi:apple"

    def __init__(
        self,
        coordinator: CopilotDataUpdateCoordinator,
        entry: ConfigEntry,
        zone_id: str,
        zone_name: str,
        entity_ids: list[str],
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._zone_id = zone_id
        self._zone_name = zone_name
        self._entity_ids = entity_ids
        self._attr_has_entity_name = False
        self._attr_name = f"PilotSuite HomeKit — {zone_name}"
        self._attr_unique_id = f"ai_home_copilot_homekit_toggle_{zone_id}"

    async def async_press(self) -> None:
        """Toggle HomeKit for this zone."""
        bridge = get_homekit_bridge(self.hass, self._entry.entry_id)
        if not bridge:
            _LOGGER.warning("HomeKit bridge module not available")
            return

        if bridge.is_zone_enabled(self._zone_id):
            await bridge.async_disable_zone(self._zone_id)
            _LOGGER.info("HomeKit disabled for zone %s", self._zone_name)
        else:
            await bridge.async_enable_zone(
                self._zone_id, self._zone_name, self._entity_ids
            )
            _LOGGER.info("HomeKit enabled for zone %s", self._zone_name)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        bridge = get_homekit_bridge(self.hass, self._entry.entry_id)
        if not bridge:
            return {"homekit_enabled": False}

        enabled = bridge.is_zone_enabled(self._zone_id)
        setup_info = bridge.get_zone_setup_info(self._zone_id)
        host = self._entry.data.get(CONF_HOST, "homeassistant.local")
        port = self._entry.data.get(CONF_PORT, 8909)

        attrs: dict[str, Any] = {
            "homekit_enabled": enabled,
            "zone_id": self._zone_id,
            "zone_name": self._zone_name,
            "entity_count": len(self._entity_ids),
        }

        if enabled and setup_info:
            attrs["setup_code"] = setup_info.get("setup_code", "")
            attrs["serial"] = setup_info.get("serial", "")
            attrs["manufacturer"] = setup_info.get("manufacturer", "PilotSuite")
            attrs["model"] = setup_info.get("model", "Styx HomeKit Bridge")
            attrs["qr_svg_url"] = f"http://{host}:{port}/api/v1/homekit/qr/{self._zone_id}.svg"
            attrs["qr_png_url"] = f"http://{host}:{port}/api/v1/homekit/qr/{self._zone_id}.png"

        return attrs


class HomeKitZoneQRSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing HomeKit setup code + QR URL for a zone.

    The state is the setup code (XXX-XX-XXX).
    Attributes contain QR image URLs and device info.
    """

    _attr_icon = "mdi:qrcode"

    def __init__(
        self,
        coordinator: CopilotDataUpdateCoordinator,
        entry: ConfigEntry,
        zone_id: str,
        zone_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._zone_id = zone_id
        self._zone_name = zone_name
        self._attr_has_entity_name = False
        self._attr_name = f"PilotSuite HomeKit QR — {zone_name}"
        self._attr_unique_id = f"ai_home_copilot_homekit_qr_{zone_id}"

    @property
    def native_value(self) -> str:
        """Return the setup code as state."""
        bridge = get_homekit_bridge(self.hass, self._entry.entry_id)
        if not bridge or not bridge.is_zone_enabled(self._zone_id):
            return "nicht aktiv"

        setup_info = bridge.get_zone_setup_info(self._zone_id)
        return setup_info.get("setup_code", "---")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        bridge = get_homekit_bridge(self.hass, self._entry.entry_id)
        if not bridge:
            return {}

        enabled = bridge.is_zone_enabled(self._zone_id)
        setup_info = bridge.get_zone_setup_info(self._zone_id)
        host = self._entry.data.get(CONF_HOST, "homeassistant.local")
        port = self._entry.data.get(CONF_PORT, 8909)

        attrs: dict[str, Any] = {
            "homekit_enabled": enabled,
            "zone_id": self._zone_id,
            "zone_name": self._zone_name,
        }

        if enabled:
            attrs["setup_code"] = setup_info.get("setup_code", "")
            attrs["homekit_uri"] = setup_info.get("homekit_uri", "")
            attrs["qr_svg_url"] = f"http://{host}:{port}/api/v1/homekit/qr/{self._zone_id}.svg"
            attrs["qr_png_url"] = f"http://{host}:{port}/api/v1/homekit/qr/{self._zone_id}.png"
            attrs["serial"] = setup_info.get("serial", "")
            attrs["manufacturer"] = setup_info.get("manufacturer", "PilotSuite")
            attrs["model"] = setup_info.get("model", "Styx HomeKit Bridge")
            # Apple Home display name
            attrs["apple_home_name"] = f"{self._zone_name} by Styx"

        return attrs


async def async_create_homekit_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: CopilotDataUpdateCoordinator,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create HomeKit toggle + QR entities for each habitus zone.

    Called from sensor.py async_setup_entry.
    """
    try:
        from .habitus_zones_store_v2 import async_get_zones_v2
        zones = await async_get_zones_v2(hass, entry.entry_id)
    except Exception:
        _LOGGER.debug("Could not load zones for HomeKit entities")
        return

    entities: list = []
    for zone in zones:
        if zone.current_state == "disabled":
            continue
        entity_ids = list(zone.entity_ids) if zone.entity_ids else []

        entities.append(
            HomeKitZoneToggleButton(
                coordinator, entry,
                zone.zone_id, zone.name, entity_ids,
            )
        )
        entities.append(
            HomeKitZoneQRSensor(
                coordinator, entry,
                zone.zone_id, zone.name,
            )
        )

    if entities:
        async_add_entities(entities, update_before_add=False)
        _LOGGER.info("Created %d HomeKit entities for %d zones", len(entities), len(entities) // 2)
