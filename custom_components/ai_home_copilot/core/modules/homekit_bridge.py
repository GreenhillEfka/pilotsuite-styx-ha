"""HomeKit Bridge Module — expose Habitus Zone entities to Apple HomeKit.

Optionally turns each habitus zone into a HomeKit-compatible bridge by
managing the HA HomeKit integration's entity filter.

Approach:
- Stores per-zone HomeKit toggle in HA Storage
- Calls `homekit.reload` after filter changes (preserves pairing)
- Dashboard shows "Add to HomeKit" button per zone
- LLM context reports HomeKit-enabled zones
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .module import CopilotModule, ModuleContext

_LOGGER = logging.getLogger(__name__)

HOMEKIT_STORE_KEY = "ai_home_copilot.homekit_zones"
HOMEKIT_STORE_VERSION = 1

# Domains that HomeKit understands
HOMEKIT_SUPPORTED_DOMAINS = {
    "light", "switch", "cover", "climate", "fan", "lock",
    "media_player", "sensor", "binary_sensor", "input_boolean",
}


class HomeKitBridgeModule(CopilotModule):
    """Module managing HomeKit exposure per habitus zone."""

    @property
    def name(self) -> str:
        return "homekit_bridge"

    @property
    def version(self) -> str:
        return "0.1.0"

    def __init__(self):
        self._hass: Optional[HomeAssistant] = None
        self._entry_id: Optional[str] = None
        self._store: Optional[Store] = None
        # zone_id -> {"enabled": bool, "entity_ids": [...], "updated_at": float}
        self._zone_config: dict[str, dict[str, Any]] = {}

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Load HomeKit zone config from storage."""
        self._hass = ctx.hass
        self._entry_id = ctx.entry_id
        self._store = Store(ctx.hass, HOMEKIT_STORE_VERSION, HOMEKIT_STORE_KEY)

        raw = await self._store.async_load()
        if raw and isinstance(raw, dict):
            self._zone_config = raw.get("zones", {})

        ctx.hass.data.setdefault("ai_home_copilot", {})
        ctx.hass.data["ai_home_copilot"].setdefault(ctx.entry_id, {})
        ctx.hass.data["ai_home_copilot"][ctx.entry_id]["homekit_bridge_module"] = self

        _LOGGER.info(
            "HomeKitBridgeModule setup: %d zones configured",
            sum(1 for z in self._zone_config.values() if z.get("enabled")),
        )

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        entry_store = ctx.hass.data.get("ai_home_copilot", {}).get(ctx.entry_id, {})
        if isinstance(entry_store, dict):
            entry_store.pop("homekit_bridge_module", None)
        return True

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
        """Structured summary for sensor attributes."""
        enabled_zones = self.get_enabled_zones()
        return {
            "enabled_zones": len(enabled_zones),
            "total_exposed_entities": self.get_total_exposed(),
            "zones": [
                {"zone_name": z["zone_name"], "entity_count": z["entity_count"]}
                for z in enabled_zones
            ],
            "homekit_available": self._check_homekit_available(),
        }

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
