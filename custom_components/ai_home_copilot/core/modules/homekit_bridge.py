"""HomeKit Bridge Module — expose Habitus Zone entities to Apple HomeKit.

v2.0 — by Styx

Features:
- Stores per-zone HomeKit toggle in HA Storage
- Calls `homekit.reload` after filter changes (preserves pairing)
- Auto-exposes new habitus zones to HomeKit on creation
- Fetches setup codes + QR URLs from Core Add-on
- Device info optimized for Apple Home ("by Styx")
- Dashboard shows QR code per zone for easy pairing
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

import aiohttp
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from ...connection_config import build_core_headers, resolve_core_connection
from .module import CopilotModule, ModuleContext

_LOGGER = logging.getLogger(__name__)

HOMEKIT_STORE_KEY = "ai_home_copilot.homekit_zones"
HOMEKIT_STORE_VERSION = 2

# Signal fired when zone HomeKit state changes
SIGNAL_HOMEKIT_ZONE_TOGGLED = "ai_home_copilot_homekit_zone_toggled"

# Domains that HomeKit understands
HOMEKIT_SUPPORTED_DOMAINS = {
    "light", "switch", "cover", "climate", "fan", "lock",
    "media_player", "sensor", "binary_sensor", "input_boolean",
}


class HomeKitBridgeModule(CopilotModule):
    """Module managing HomeKit exposure per habitus zone.

    On zone creation: auto-exposes compatible entities to HomeKit.
    Provides setup codes + QR URLs for Apple Home pairing.
    """

    @property
    def name(self) -> str:
        return "homekit_bridge"

    @property
    def version(self) -> str:
        return "2.0.0"

    def __init__(self):
        self._hass: Optional[HomeAssistant] = None
        self._entry_id: Optional[str] = None
        self._store: Optional[Store] = None
        # zone_id -> {"enabled", "entity_ids", "zone_name", "setup_info", "updated_at"}
        self._zone_config: dict[str, dict[str, Any]] = {}
        self._unsub_zones = None
        self._unsub_zone_state = None

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Load HomeKit zone config from storage and wire auto-expose."""
        self._hass = ctx.hass
        self._entry_id = ctx.entry_id
        self._store = Store(ctx.hass, HOMEKIT_STORE_VERSION, HOMEKIT_STORE_KEY)

        raw = await self._store.async_load()
        if raw and isinstance(raw, dict):
            self._zone_config = raw.get("zones", {})

        ctx.hass.data.setdefault("ai_home_copilot", {})
        ctx.hass.data["ai_home_copilot"].setdefault(ctx.entry_id, {})
        ctx.hass.data["ai_home_copilot"][ctx.entry_id]["homekit_bridge_module"] = self

        # Listen for zone creation/updates → auto-expose
        from ...habitus_zones_store_v2 import (
            SIGNAL_HABITUS_ZONES_V2_UPDATED,
            SIGNAL_HABITUS_ZONE_STATE_CHANGED,
        )
        self._unsub_zones = async_dispatcher_connect(
            ctx.hass, SIGNAL_HABITUS_ZONES_V2_UPDATED, self._on_zones_updated
        )
        self._unsub_zone_state = async_dispatcher_connect(
            ctx.hass, SIGNAL_HABITUS_ZONE_STATE_CHANGED, self._on_zone_state_changed
        )

        _LOGGER.info(
            "HomeKitBridgeModule v2.0 setup: %d zones configured, auto-expose active",
            sum(1 for z in self._zone_config.values() if z.get("enabled")),
        )

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        if callable(self._unsub_zones):
            self._unsub_zones()
        if callable(self._unsub_zone_state):
            self._unsub_zone_state()
        entry_store = ctx.hass.data.get("ai_home_copilot", {}).get(ctx.entry_id, {})
        if isinstance(entry_store, dict):
            entry_store.pop("homekit_bridge_module", None)
        return True

    # ------------------------------------------------------------------
    # Auto-expose: listen for zone creation/update
    # ------------------------------------------------------------------

    @callback
    def _on_zones_updated(self, entry_id: str) -> None:
        """When habitus zones change, auto-expose new zones to HomeKit."""
        if entry_id != self._entry_id:
            return
        if self._hass:
            self._hass.async_create_task(self._auto_expose_new_zones())

    @callback
    def _on_zone_state_changed(self, data: dict) -> None:
        """React to zone state changes (e.g. zone disabled → remove from HomeKit)."""
        if data.get("entry_id") != self._entry_id:
            return
        zone_id = data.get("zone_id", "")
        new_state = data.get("new_state", "")
        if new_state == "disabled" and self.is_zone_enabled(zone_id):
            if self._hass:
                self._hass.async_create_task(self.async_disable_zone(zone_id))

    async def _auto_expose_new_zones(self) -> None:
        """Auto-expose any new habitus zones that aren't yet HomeKit-configured."""
        if not self._hass or not self._entry_id:
            return

        try:
            from ...habitus_zones_store_v2 import async_get_zones_v2
            zones = await async_get_zones_v2(self._hass, self._entry_id)
        except Exception as exc:
            _LOGGER.debug("Could not get zones for auto-expose: %s", exc)
            return

        new_count = 0
        for zone in zones:
            if zone.zone_id in self._zone_config:
                continue  # Already configured
            if zone.current_state == "disabled":
                continue

            # Auto-expose: filter to supported entities
            entity_ids = list(zone.entity_ids) if zone.entity_ids else []
            supported = [
                eid for eid in entity_ids
                if eid.split(".", 1)[0] in HOMEKIT_SUPPORTED_DOMAINS
            ]
            if not supported:
                continue

            self._zone_config[zone.zone_id] = {
                "enabled": True,
                "zone_name": zone.name,
                "entity_ids": supported,
                "updated_at": time.time(),
                "auto_exposed": True,
            }
            new_count += 1
            _LOGGER.info(
                "HomeKit auto-exposed zone '%s' (%d entities)",
                zone.name, len(supported),
            )

        if new_count > 0:
            await self._save()
            await self._reload_homekit()
            # Fetch setup info from Core for new zones
            await self._fetch_setup_info_from_core()

    async def _fetch_setup_info_from_core(self) -> None:
        """Fetch HomeKit setup codes + QR URLs from Core Add-on."""
        if not self._hass or not self._entry_id:
            return

        try:
            from ...const import DOMAIN
            entries = self._hass.config_entries.async_entries(DOMAIN)
            if not entries:
                return
            entry = entries[0]
            host, port, token = resolve_core_connection(entry)

            import aiohttp
            headers = build_core_headers(token)
            url = f"http://{host}:{port}/api/v1/homekit/all-zones-info"

            session = async_get_clientsession(self._hass)
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for zone_info in data.get("zones", []):
                        zid = zone_info.get("zone_id", "")
                        if zid in self._zone_config:
                            self._zone_config[zid]["setup_info"] = {
                                "setup_code": zone_info.get("setup_code", ""),
                                "homekit_uri": zone_info.get("homekit_uri", ""),
                                "qr_svg_url": zone_info.get("qr_svg_url", ""),
                                "qr_png_url": zone_info.get("qr_png_url", ""),
                                "serial": zone_info.get("serial", ""),
                                "manufacturer": zone_info.get("manufacturer", "PilotSuite"),
                                "model": zone_info.get("model", "Styx HomeKit Bridge"),
                            }
                    await self._save()
                    _LOGGER.debug("Fetched HomeKit setup info from Core for %d zones", len(data.get("zones", [])))
        except Exception as exc:
            _LOGGER.debug("Could not fetch HomeKit setup info from Core: %s", exc)

    async def _save(self) -> None:
        if self._store:
            await self._store.async_save({"zones": self._zone_config})

    # ------------------------------------------------------------------
    # Zone HomeKit management
    # ------------------------------------------------------------------

    async def async_enable_zone(
        self,
        zone_id: str,
        zone_name: str,
        entity_ids: list[str],
    ) -> dict[str, Any]:
        """Enable HomeKit for a zone, exposing its entities."""
        if not self._hass:
            return {"error": "Module not initialized"}

        # Filter to HomeKit-supported entities
        supported = [
            eid for eid in entity_ids
            if eid.split(".", 1)[0] in HOMEKIT_SUPPORTED_DOMAINS
        ]

        if not supported:
            return {"error": f"Keine HomeKit-kompatiblen Entitäten in Zone '{zone_name}'"}

        self._zone_config[zone_id] = {
            "enabled": True,
            "zone_name": zone_name,
            "entity_ids": supported,
            "updated_at": time.time(),
        }
        await self._save()

        # Reload HomeKit integration to apply changes
        await self._reload_homekit()

        _LOGGER.info(
            "HomeKit enabled for zone %s (%d entities)",
            zone_name, len(supported),
        )
        return {
            "success": True,
            "zone_id": zone_id,
            "zone_name": zone_name,
            "entities_exposed": len(supported),
            "entity_ids": supported,
        }

    async def async_disable_zone(self, zone_id: str) -> dict[str, Any]:
        """Disable HomeKit for a zone."""
        config = self._zone_config.get(zone_id)
        if not config:
            return {"error": f"Zone '{zone_id}' nicht gefunden"}

        config["enabled"] = False
        config["updated_at"] = time.time()
        await self._save()
        await self._reload_homekit()

        _LOGGER.info("HomeKit disabled for zone %s", zone_id)
        return {"success": True, "zone_id": zone_id}

    async def async_update_zone_entities(
        self,
        zone_id: str,
        entity_ids: list[str],
    ) -> dict[str, Any]:
        """Update the entities for a HomeKit-enabled zone."""
        config = self._zone_config.get(zone_id)
        if not config or not config.get("enabled"):
            return {"error": f"Zone '{zone_id}' nicht für HomeKit aktiviert"}

        supported = [
            eid for eid in entity_ids
            if eid.split(".", 1)[0] in HOMEKIT_SUPPORTED_DOMAINS
        ]

        config["entity_ids"] = supported
        config["updated_at"] = time.time()
        await self._save()
        await self._reload_homekit()

        return {
            "success": True,
            "zone_id": zone_id,
            "entities_exposed": len(supported),
        }

    async def _reload_homekit(self) -> None:
        """Reload the HA HomeKit integration to apply filter changes.

        Uses homekit.reload service which preserves the pairing.
        """
        if not self._hass:
            return
        try:
            await self._hass.services.async_call(
                "homekit", "reload", blocking=True
            )
            _LOGGER.debug("HomeKit integration reloaded")
        except Exception as exc:
            _LOGGER.warning(
                "Could not reload HomeKit integration (may not be installed): %s", exc
            )

    # ------------------------------------------------------------------
    # Read API
    # ------------------------------------------------------------------

    def get_all_exposed_entities(self) -> list[str]:
        """Return all entity_ids currently exposed via HomeKit."""
        all_ids: list[str] = []
        for config in self._zone_config.values():
            if config.get("enabled"):
                all_ids.extend(config.get("entity_ids", []))
        return list(set(all_ids))

    def get_enabled_zones(self) -> list[dict[str, Any]]:
        """Return list of HomeKit-enabled zones."""
        return [
            {
                "zone_id": zid,
                "zone_name": cfg.get("zone_name", zid),
                "entity_count": len(cfg.get("entity_ids", [])),
                "enabled": cfg.get("enabled", False),
            }
            for zid, cfg in self._zone_config.items()
            if cfg.get("enabled")
        ]

    def is_zone_enabled(self, zone_id: str) -> bool:
        config = self._zone_config.get(zone_id, {})
        return config.get("enabled", False)

    def get_zone_count(self) -> int:
        return sum(1 for c in self._zone_config.values() if c.get("enabled"))

    def get_total_exposed(self) -> int:
        return len(self.get_all_exposed_entities())

    def get_summary(self) -> dict[str, Any]:
        """Structured summary for sensor attributes (incl. setup info + QR URLs)."""
        enabled_zones = self.get_enabled_zones()
        zones_with_info = []
        for z in enabled_zones:
            zid = z["zone_id"]
            cfg = self._zone_config.get(zid, {})
            setup = cfg.get("setup_info", {})
            entry = {
                "zone_id": zid,
                "zone_name": z["zone_name"],
                "entity_count": z["entity_count"],
                "setup_code": setup.get("setup_code", ""),
                "qr_svg_url": setup.get("qr_svg_url", ""),
                "serial": setup.get("serial", ""),
                "manufacturer": setup.get("manufacturer", "PilotSuite"),
                "model": setup.get("model", "Styx HomeKit Bridge"),
            }
            zones_with_info.append(entry)

        return {
            "enabled_zones": len(zones_with_info),
            "total_exposed_entities": self.get_total_exposed(),
            "zones": zones_with_info,
            "homekit_available": self._check_homekit_available(),
        }

    def get_zone_setup_info(self, zone_id: str) -> dict[str, Any]:
        """Get setup info (code, QR, serial) for a specific zone."""
        cfg = self._zone_config.get(zone_id, {})
        return cfg.get("setup_info", {})

    def _check_homekit_available(self) -> bool:
        """Check if the HA HomeKit integration is loaded."""
        if not self._hass:
            return False
        return "homekit" in self._hass.config.components

    # ------------------------------------------------------------------
    # LLM Context
    # ------------------------------------------------------------------

    def get_context_for_llm(self) -> str:
        """Inject HomeKit status into LLM system prompt."""
        enabled = self.get_enabled_zones()
        if not enabled:
            return ""
        total = self.get_total_exposed()
        zone_list = ", ".join(z["zone_name"] for z in enabled)
        return (
            f"HomeKit-Bridge: {len(enabled)} Zonen aktiv ({total} Entitäten) "
            f"— {zone_list}"
        )


def get_homekit_bridge(hass: HomeAssistant, entry_id: str) -> Optional[HomeKitBridgeModule]:
    """Return the HomeKitBridgeModule instance for a config entry, or None."""
    data = hass.data.get("ai_home_copilot", {}).get(entry_id, {})
    return data.get("homekit_bridge_module")
