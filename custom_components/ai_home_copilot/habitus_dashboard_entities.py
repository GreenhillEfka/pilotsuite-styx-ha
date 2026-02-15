"""
Habitus Dashboard Card Entities
===============================

Sensor entities for Habitus Dashboard Cards:
- Zone Score Sensor (pro Zone)
- Zone Status Sensor
- Mood Distribution Sensor
- Zone Transition Event Sensor

These entities provide the data for the Habitus Dashboard Cards.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .entity import CopilotBaseEntity
# DEPRECATED: v1 - prefer v2
# from .habitus_zones_store import (
#     HabitusZone,
#     SIGNAL_HABITUS_ZONES_V2_UPDATED,
#     async_get_zones,
# )
from .habitus_zones_store_v2 import (
    HabitusZoneV2,
    SIGNAL_HABITUS_ZONES_V2_UPDATED,
    async_get_zones_v2,
)
from .habitus_dashboard_cards import (
    ZoneStatusData,
    ZoneTransitionData,
    MoodDistributionData,
    calculate_zone_score,
    aggregate_mood_distribution,
)

_LOGGER = logging.getLogger(__name__)


# ============================================================================
# Zone Score Sensor (per zone)
# ============================================================================

class HabitusZoneScoreSensor(CopilotBaseEntity, SensorEntity):
    """Sensor for individual zone activity score (0-100)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:chart-donut"
    _attr_native_unit_of_measurement = "%"

    def __init__(self, coordinator, entry: ConfigEntry, zone_id: str):
        super().__init__(coordinator)
        self._entry = entry
        self._zone_id = zone_id
        self._attr_unique_id = f"ai_home_copilot_zone_{zone_id}_score"
        self._attr_name = f"AI Home CoPilot Zone {zone_id} Score"

    @property
    def zone(self) -> HabitusZoneV2 | None:
        """Get the zone for this sensor."""
        # Will be set by async_added_to_hass or _reload_value
        return getattr(self, "_zone", None)

    @zone.setter
    def zone(self, value: HabitusZoneV2) -> None:
        self._zone = value

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self._reload_value()

    async def _reload_value(self) -> None:
        zones = await async_get_zones_v2(self.hass, self._entry.entry_id)
        zone = next((z for z in zones if z.zone_id == self._zone_id), None)

        if zone:
            self.zone = zone
            score = calculate_zone_score(zone, self.hass)
            self._attr_native_value = score
            self._attr_extra_state_attributes = {
                "zone_id": self._zone_id,
                "zone_name": zone.name,
                "entity_count": len(zone.entity_ids),
            }
        else:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {
                "zone_id": self._zone_id,
                "error": "Zone not found",
            }

        self.async_write_ha_state()


# ============================================================================
# Zone Status Sensor (combined)
# ============================================================================

class HabitusZoneStatusSensor(CopilotBaseEntity, SensorEntity):
    """Sensor for overall zone status (active zone, score, mood)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:home-circle"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = "ai_home_copilot_habitus_zone_status"
        self._attr_name = "AI Home CoPilot Habitus Zone Status"
        self._unsub = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub = async_dispatcher_connect(
            self.hass, SIGNAL_HABITUS_ZONES_V2_UPDATED, self._on_zones_updated
        )
        await self._refresh()

    async def async_will_remove_from_hass(self) -> None:
        if callable(self._unsub):
            self._unsub()
        self._unsub = None
        await super().async_will_remove_from_hass()

    async def _refresh(self) -> None:
        zones = await async_get_zones_v2(self.hass, self._entry.entry_id)

        # Find active zone (first with motion/presence)
        active_zone: HabitusZoneV2 | None = None
        active_score: float | None = None

        for z in zones:
            score = calculate_zone_score(z, self.hass)
            if score is not None:
                motion_entities = z.entities.get("motion") if z.entities else []
                for entity_id in motion_entities[:2]:
                    state = self.hass.states.get(entity_id)
                    if state and state.state == "on":
                        active_zone = z
                        active_score = score
                        break

            if active_zone:
                break

        if active_zone:
            self._attr_native_value = active_zone.name
            self._attr_extra_state_attributes = {
                "active_zone_id": active_zone.zone_id,
                "active_zone_name": active_zone.name,
                "score": active_score,
                "zone_count": len(zones),
            }
        else:
            self._attr_native_value = "Keine aktive Zone"
            self._attr_extra_state_attributes = {
                "active_zone_id": None,
                "active_zone_name": None,
                "score": None,
                "zone_count": len(zones),
            }

        self.async_write_ha_state()

    def _on_zones_updated(self, entry_id: str) -> None:
        if entry_id != self._entry.entry_id:
            return

        def _run() -> None:
            self.hass.async_create_task(self._refresh())

        self.hass.loop.call_soon_threadsafe(_run)


# ============================================================================
# Mood Distribution Sensor
# ============================================================================

class HabitusMoodDistributionSensor(CopilotBaseEntity, SensorEntity):
    """Sensor for mood distribution across zones."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:chart-pie"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = "ai_home_copilot_habitus_mood_distribution"
        self._attr_name = "AI Home CoPilot Habitus Mood Distribution"
        self._unsub = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub = async_dispatcher_connect(
            self.hass, SIGNAL_HABITUS_ZONES_V2_UPDATED, self._on_zones_updated
        )
        await self._refresh()

    async def async_will_remove_from_hass(self) -> None:
        if callable(self._unsub):
            self._unsub()
        self._unsub = None
        await super().async_will_remove_from_hass()

    async def _refresh(self) -> None:
        zones = await async_get_zones_v2(self.hass, self._entry.entry_id)

        # Simulate mood detection (would come from Core API in real implementation)
        zone_moods = self._detect_zone_moods(zones)
        mood_distribution = aggregate_mood_distribution(zones, zone_moods)

        # Format as JSON for state
        import json
        mood_data = [
            {"mood": m.mood, "count": m.count, "percentage": m.percentage, "zone_name": m.zone_name}
            for m in mood_distribution
        ]
        self._attr_native_value = json.dumps(mood_data)

        self._attr_extra_state_attributes = {
            "zone_count": len(zones),
            "mood_distribution": mood_data,
            "primary_mood": mood_distribution[0].mood if mood_distribution else None,
        }

        self.async_write_ha_state()

    def _detect_zone_moods(self, zones: list[HabitusZoneV2]) -> dict[str, str]:
        """Detect mood for each zone based on entity states.

        This is a simplified implementation. In production, this would
        call the Core API for mood inference.
        """
        moods: dict[str, str] = {}

        for z in zones:
            score = calculate_zone_score(z, self.hass)

            if score is None:
                moods[z.zone_id] = "unknown"
                continue

            # Simple mood detection based on activity
            if score > 70:
                moods[z.zone_id] = "active"
            elif score > 40:
                moods[z.zone_id] = "relax"
            else:
                moods[z.zone_id] = "quiet"

        return moods

    def _on_zones_updated(self, entry_id: str) -> None:
        if entry_id != self._entry.entry_id:
            return

        def _run() -> None:
            self.hass.async_create_task(self._refresh())

        self.hass.loop.call_soon_threadsafe(_run)


# ============================================================================
# Current Mood Sensor
# ============================================================================

class HabitusCurrentMoodSensor(CopilotBaseEntity, SensorEntity):
    """Sensor for the current overall mood of the home."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:emoticon-outline"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = "ai_home_copilot_habitus_current_mood"
        self._attr_name = "AI Home CoPilot Habitus Current Mood"
        self._unsub = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub = async_dispatcher_connect(
            self.hass, SIGNAL_HABITUS_ZONES_V2_UPDATED, self._on_zones_updated
        )
        await self._refresh()

    async def async_will_remove_from_hass(self) -> None:
        if callable(self._unsub):
            self._unsub()
        self._unsub = None
        await super().async_will_remove_from_hass()

    async def _refresh(self) -> None:
        zones = await async_get_zones_v2(self.hass, self._entry.entry_id)

        # Detect mood based on all zones
        zone_moods = self._detect_moods(zones)

        # Determine primary mood (most common)
        mood_counts: dict[str, int] = {}
        for mood in zone_moods.values():
            mood_counts[mood] = mood_counts.get(mood, 0) + 1

        if mood_counts:
            primary_mood = max(mood_counts.items(), key=lambda x: x[1])[0]
        else:
            primary_mood = "relax"

        self._attr_native_value = primary_mood
        self._attr_extra_state_attributes = {
            "zone_moods": zone_moods,
            "mood_counts": mood_counts,
            "zone_count": len(zones),
        }

        self.async_write_ha_state()

    def _detect_moods(self, zones: list[HabitusZoneV2]) -> dict[str, str]:
        """Detect mood for each zone."""
        moods: dict[str, str] = {}

        for z in zones:
            score = calculate_zone_score(z, self.hass)

            if score is None:
                moods[z.zone_id] = "relax"
                continue

            # Mood detection logic
            if score > 80:
                moods[z.zone_id] = "energy"
            elif score > 50:
                moods[z.zone_id] = "focus"
            elif score > 20:
                moods[z.zone_id] = "relax"
            else:
                moods[z.zone_id] = "sleep"

        return moods

    def _on_zones_updated(self, entry_id: str) -> None:
        if entry_id != self._entry.entry_id:
            return

        def _run() -> None:
            self.hass.async_create_task(self._refresh())

        self.hass.loop.call_soon_threadsafe(_run)


# ============================================================================
# Zone Transition Event Sensor (logbook-style)
# ============================================================================

class HabitusZoneTransitionLogSensor(CopilotBaseEntity, SensorEntity):
    """Sensor that stores zone transition history (JSON)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:timeline"
    _attr_available = False  # Text-based entity

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = "ai_home_copilot_habitus_transitions"
        self._attr_name = "AI Home CoPilot Habitus Zone Transitions"
        self._transitions: list[dict] = []
        self._unsub = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub = async_dispatcher_connect(
            self.hass, SIGNAL_HABITUS_ZONES_V2_UPDATED, self._on_zones_updated
        )
        await self._refresh()

    async def async_will_remove_from_hass(self) -> None:
        if callable(self._unsub):
            self._unsub()
        self._unsub = None
        await super().async_will_remove_from_hass()

    async def _refresh(self) -> None:
        import json

        # In a real implementation, this would track actual zone transitions
        # For now, return a snapshot of current zones
        zones = await async_get_zones_v2(self.hass, self._entry.entry_id)

        transitions = []
        for z in zones:
            transitions.append({
                "timestamp": datetime.now().isoformat(),
                "zone_id": z.zone_id,
                "zone_name": z.name,
                "entity_count": len(z.entity_ids),
            })

        self._transitions = transitions
        self._attr_native_value = json.dumps(transitions[-20:])  # Last 20 entries

        self._attr_extra_state_attributes = {
            "transition_count": len(transitions),
            "zones": [z.zone_id for z in zones],
        }

        self._attr_available = True
        self.async_write_ha_state()

    def add_transition(self, from_zone: str | None, to_zone: str, trigger: str | None) -> None:
        """Add a new transition to the log."""
        import json

        transition = {
            "timestamp": datetime.now().isoformat(),
            "from_zone": from_zone,
            "to_zone": to_zone,
            "trigger": trigger,
        }

        self._transitions.append(transition)
        # Keep only last 100 transitions
        if len(self._transitions) > 100:
            self._transitions = self._transitions[-100:]

        self._attr_native_value = json.dumps(self._transitions[-20:])
        self.async_write_ha_state()

    def _on_zones_updated(self, entry_id: str) -> None:
        if entry_id != self._entry.entry_id:
            return

        def _run() -> None:
            self.hass.async_create_task(self._refresh())

        self.hass.loop.call_soon_threadsafe(_run)


# ============================================================================
# Card Configuration Text Entity (for advanced users)
# ============================================================================

class HabitusCardsConfigText(CopilotBaseEntity, TextEntity):
    """Text entity with pre-generated YAML for all Habitus cards."""

    _attr_entity_registry_enabled_default = False
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot habitus cards YAML"
    _attr_unique_id = "ai_home_copilot_habitus_cards_yaml"
    _attr_icon = "mdi:card-text"
    _attr_mode = "text"  # multiline
    _attr_native_max = 65535

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        self._value: str = ""

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self._reload_value()

    async def _reload_value(self) -> None:
        zones = await async_get_zones_v2(self.hass, self._entry.entry_id)

        from .habitus_dashboard_cards import (
            generate_zone_status_card_simple,
            generate_zone_transitions_card_simple,
            generate_mood_distribution_card_simple,
        )

        yaml_content = f"""# AI Home CoPilot Habitus Dashboard Cards
# Generated: {datetime.now().isoformat()}

---
# Card 1: Zone Status
{generate_zone_status_card_yaml(zones=zones, active_zone_id=None)}

---
# Card 2: Zone Transitions
{generate_zone_transitions_card_yaml()}

---
# Card 3: Mood Distribution
{generate_mood_distribution_card_simple({}, len(zones))}
"""

        self._value = yaml_content
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        return self._value

    async def async_set_value(self, value: str) -> None:
        """Allow users to edit card configurations."""
        # In a real implementation, this would validate and apply changes
        self._value = value
        self.async_write_ha_state()
