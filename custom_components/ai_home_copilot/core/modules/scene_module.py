"""Scene Module — Habitus Zone scene management.

Allows saving current zone conditions as HA scenes, with learning,
suggestions, and built-in presets. Integrates with the Habitus system
for intelligent scene recommendations.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Optional

from homeassistant.core import HomeAssistant

from .module import CopilotModule, ModuleContext

_LOGGER = logging.getLogger(__name__)

# Domains whose entities can be captured in scenes
CAPTURABLE_DOMAINS = {
    "light", "switch", "cover", "climate", "fan", "media_player",
    "input_boolean", "input_number", "input_select",
}

# Attribute keys to capture per domain
DOMAIN_CAPTURE_ATTRS = {
    "light": ["brightness", "color_temp_kelvin", "rgb_color", "hs_color", "effect"],
    "cover": ["current_position", "current_tilt_position"],
    "climate": ["temperature", "target_temp_high", "target_temp_low", "hvac_mode", "fan_mode"],
    "fan": ["percentage", "preset_mode"],
    "media_player": ["volume_level", "is_volume_muted", "source"],
}


class SceneModule(CopilotModule):
    """Module managing zone scenes — save, apply, learn, and suggest."""

    @property
    def name(self) -> str:
        return "scene_module"

    @property
    def version(self) -> str:
        return "0.1.0"

    def __init__(self):
        self._hass: Optional[HomeAssistant] = None
        self._entry_id: Optional[str] = None
        self._scenes: dict = {}  # scene_id -> ZoneScene

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Load scenes and register in hass.data."""
        self._hass = ctx.hass
        self._entry_id = ctx.entry_id

        from ...scene_store import async_get_scenes
        self._scenes = await async_get_scenes(ctx.hass)

        ctx.hass.data.setdefault("ai_home_copilot", {})
        ctx.hass.data["ai_home_copilot"].setdefault(ctx.entry_id, {})
        ctx.hass.data["ai_home_copilot"][ctx.entry_id]["scene_module"] = self

        _LOGGER.info(
            "SceneModule setup: %d scenes loaded",
            len(self._scenes),
        )

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        entry_store = ctx.hass.data.get("ai_home_copilot", {}).get(ctx.entry_id, {})
        if isinstance(entry_store, dict):
            entry_store.pop("scene_module", None)
        return True

    # ------------------------------------------------------------------
    # Scene capture — snapshot current zone entity states
    # ------------------------------------------------------------------

    async def async_capture_zone_scene(
        self,
        zone_id: str,
        zone_name: str,
        entity_ids: list[str],
        scene_name: str | None = None,
        source: str = "manual",
    ) -> dict[str, Any]:
        """Capture current states of zone entities as a new scene.

        Returns the scene dict or error dict.
        """
        if not self._hass:
            return {"error": "Module not initialized"}

        # Filter to capturable entities
        capturable = [
            eid for eid in entity_ids
            if eid.split(".", 1)[0] in CAPTURABLE_DOMAINS
        ]
        if not capturable:
            return {"error": "Keine steuerbaren Entitäten in der Zone gefunden"}

        # Snapshot current states
        entity_states: dict[str, dict[str, Any]] = {}
        for eid in capturable:
            state = self._hass.states.get(eid)
            if state is None:
                continue
            domain = eid.split(".", 1)[0]
            snapshot: dict[str, Any] = {"state": state.state}

            # Capture relevant attributes
            for attr_key in DOMAIN_CAPTURE_ATTRS.get(domain, []):
                val = state.attributes.get(attr_key)
                if val is not None:
                    snapshot[attr_key] = val

            entity_states[eid] = snapshot

        if not entity_states:
            return {"error": "Keine aktiven Entitäten zum Speichern gefunden"}

        # Create scene
        scene_id = f"zone_scene_{uuid.uuid4().hex[:12]}"
        name = scene_name or f"{zone_name} — {time.strftime('%d.%m %H:%M')}"

        from ...scene_store import ZoneScene, async_upsert_scene
        scene = ZoneScene(
            scene_id=scene_id,
            zone_id=zone_id,
            zone_name=zone_name,
            name=name,
            entity_states=entity_states,
            source=source,
        )
        await async_upsert_scene(self._hass, scene)
        self._scenes[scene_id] = scene

        # Also create a matching HA scene entity
        ha_scene_id = await self._create_ha_scene(scene)
        if ha_scene_id:
            scene.ha_scene_entity_id = ha_scene_id
            await async_upsert_scene(self._hass, scene)

        _LOGGER.info("Scene captured: %s (%s) for zone %s", scene_id, name, zone_id)
        return scene.to_dict()

    async def _create_ha_scene(self, scene) -> str | None:
        """Create a Home Assistant scene entity from a ZoneScene."""
        if not self._hass:
            return None
        try:
            # Build HA scene entity data
            entities_data = {}
            for eid, state_data in scene.entity_states.items():
                entity_scene_data: dict[str, Any] = {"state": state_data.get("state", "on")}
                for k, v in state_data.items():
                    if k != "state":
                        entity_scene_data[k] = v
                entities_data[eid] = entity_scene_data

            # Use scene.create service
            await self._hass.services.async_call(
                "scene",
                "create",
                {
                    "scene_id": scene.scene_id,
                    "snapshot_entities": list(scene.entity_states.keys()),
                },
                blocking=True,
            )
            return f"scene.{scene.scene_id}"
        except Exception as exc:
            _LOGGER.warning("Failed to create HA scene for %s: %s", scene.scene_id, exc)
            return None

    # ------------------------------------------------------------------
    # Scene application
    # ------------------------------------------------------------------

    async def async_apply_scene(self, scene_id: str) -> dict[str, Any]:
        """Apply a saved scene to its zone entities."""
        if not self._hass:
            return {"error": "Module not initialized"}

        scene = self._scenes.get(scene_id)
        if not scene:
            return {"error": f"Szene '{scene_id}' nicht gefunden"}

        errors = []
        for eid, state_data in scene.entity_states.items():
            try:
                await self._apply_entity_state(eid, state_data)
            except Exception as exc:
                errors.append(f"{eid}: {exc}")

        # Update apply count
        from ...scene_store import async_increment_apply_count
        await async_increment_apply_count(self._hass, scene_id)
        scene.applied_count += 1
        scene.last_applied = time.time()

        if errors:
            return {"success": True, "warnings": errors, "scene": scene.to_dict()}
        return {"success": True, "scene": scene.to_dict()}

    async def _apply_entity_state(self, entity_id: str, state_data: dict) -> None:
        """Apply a specific state to an entity."""
        domain = entity_id.split(".", 1)[0]
        target_state = state_data.get("state", "")

        if domain == "light":
            if target_state == "off":
                await self._hass.services.async_call(
                    "light", "turn_off", {"entity_id": entity_id}, blocking=True
                )
            else:
                service_data: dict[str, Any] = {"entity_id": entity_id}
                if "brightness" in state_data:
                    service_data["brightness"] = state_data["brightness"]
                if "color_temp_kelvin" in state_data:
                    service_data["color_temp_kelvin"] = state_data["color_temp_kelvin"]
                if "rgb_color" in state_data:
                    service_data["rgb_color"] = state_data["rgb_color"]
                await self._hass.services.async_call(
                    "light", "turn_on", service_data, blocking=True
                )

        elif domain == "switch" or domain == "input_boolean":
            service = "turn_on" if target_state == "on" else "turn_off"
            await self._hass.services.async_call(
                domain, service, {"entity_id": entity_id}, blocking=True
            )

        elif domain == "cover":
            pos = state_data.get("current_position")
            if pos is not None:
                await self._hass.services.async_call(
                    "cover", "set_cover_position",
                    {"entity_id": entity_id, "position": pos}, blocking=True
                )

        elif domain == "climate":
            service_data = {"entity_id": entity_id}
            if "hvac_mode" in state_data:
                service_data["hvac_mode"] = state_data["hvac_mode"]
            if "temperature" in state_data:
                service_data["temperature"] = state_data["temperature"]
            await self._hass.services.async_call(
                "climate", "set_hvac_mode" if "hvac_mode" in service_data else "set_temperature",
                service_data, blocking=True
            )

        elif domain == "fan":
            if target_state == "off":
                await self._hass.services.async_call(
                    "fan", "turn_off", {"entity_id": entity_id}, blocking=True
                )
            else:
                service_data = {"entity_id": entity_id}
                if "percentage" in state_data:
                    service_data["percentage"] = state_data["percentage"]
                await self._hass.services.async_call(
                    "fan", "turn_on", service_data, blocking=True
                )

        elif domain == "media_player":
            if target_state in ("off", "idle", "standby"):
                await self._hass.services.async_call(
                    "media_player", "turn_off",
                    {"entity_id": entity_id}, blocking=True
                )

    # ------------------------------------------------------------------
    # Scene deletion
    # ------------------------------------------------------------------

    async def async_delete_scene(self, scene_id: str) -> bool:
        """Delete a scene."""
        if not self._hass:
            return False
        from ...scene_store import async_delete_scene
        ok = await async_delete_scene(self._hass, scene_id)
        self._scenes.pop(scene_id, None)
        return ok

    # ------------------------------------------------------------------
    # Read API (sync — safe for sensors)
    # ------------------------------------------------------------------

    def get_all_scenes(self) -> list[dict]:
        """Return all scenes as dicts."""
        return [s.to_dict() for s in self._scenes.values()]

    def get_scenes_for_zone(self, zone_id: str) -> list[dict]:
        """Return scenes for a specific zone."""
        return [
            s.to_dict() for s in self._scenes.values()
            if s.zone_id == zone_id
        ]

    def get_scene_count(self) -> int:
        return len(self._scenes)

    def get_zone_scene_count(self, zone_id: str) -> int:
        return sum(1 for s in self._scenes.values() if s.zone_id == zone_id)

    def get_presets(self) -> list[dict]:
        """Return built-in scene presets."""
        from ...scene_store import SCENE_PRESETS
        return SCENE_PRESETS

    def get_popular_scenes(self, limit: int = 5) -> list[dict]:
        """Return the most frequently applied scenes."""
        sorted_scenes = sorted(
            self._scenes.values(),
            key=lambda s: s.applied_count,
            reverse=True,
        )
        return [s.to_dict() for s in sorted_scenes[:limit]]

    def get_summary(self) -> dict[str, Any]:
        """Structured summary for sensor attributes."""
        zone_counts: dict[str, int] = {}
        for s in self._scenes.values():
            zone_counts[s.zone_id] = zone_counts.get(s.zone_id, 0) + 1
        return {
            "scene_count": len(self._scenes),
            "zones_with_scenes": len(zone_counts),
            "zone_counts": zone_counts,
            "manual_count": sum(1 for s in self._scenes.values() if s.source == "manual"),
            "learned_count": sum(1 for s in self._scenes.values() if s.source == "learned"),
            "preset_count": sum(1 for s in self._scenes.values() if s.source == "preset"),
        }

    # ------------------------------------------------------------------
    # Reload
    # ------------------------------------------------------------------

    async def reload_from_storage(self) -> None:
        """Re-read scenes from HA Storage."""
        if self._hass:
            from ...scene_store import async_get_scenes
            self._scenes = await async_get_scenes(self._hass)
            _LOGGER.debug("SceneModule reloaded: %d scenes", len(self._scenes))

    # ------------------------------------------------------------------
    # LLM Context
    # ------------------------------------------------------------------

    def get_context_for_llm(self) -> str:
        """Inject scene info into LLM system prompt."""
        if not self._scenes:
            return ""
        lines = [f"Gespeicherte Habituszonen-Szenen ({len(self._scenes)} total):"]
        zone_scenes: dict[str, list] = {}
        for s in self._scenes.values():
            zone_scenes.setdefault(s.zone_name or s.zone_id, []).append(s)
        for zone_name, scenes in zone_scenes.items():
            names = [s.name for s in scenes[:5]]
            suffix = f" (+{len(scenes)-5})" if len(scenes) > 5 else ""
            lines.append(f"  {zone_name}: {', '.join(names)}{suffix}")
        return "\n".join(lines) if len(lines) > 1 else ""


def get_scene_module(hass: HomeAssistant, entry_id: str) -> Optional[SceneModule]:
    """Return the SceneModule instance for a config entry, or None."""
    data = hass.data.get("ai_home_copilot", {}).get(entry_id, {})
    return data.get("scene_module")
