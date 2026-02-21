"""Zone Energy Device Discovery & Auto-Association (v5.1.0).

Discovers energy-related entities (power sensors, energy meters) and
auto-associates them with Habituszones based on:
1. Shared device_id (same physical device)
2. Area matching (same HA area)
3. Entity name heuristics (matching zone name patterns)

Also provides per-zone energy aggregation and tagging.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Set

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import area_registry as ar

_LOGGER = logging.getLogger(__name__)

# Energy-related device classes
ENERGY_DEVICE_CLASSES = {"power", "energy", "current", "voltage"}

# Entity domain patterns that indicate energy measurement
ENERGY_DOMAINS = {"sensor"}

# Entity name patterns that indicate energy measurement
ENERGY_NAME_PATTERNS = [
    "power", "energy", "consumption", "watt", "kwh",
    "strom", "leistung", "verbrauch", "energie",
    "current", "voltage", "ampere", "volt",
]


@dataclass
class ZoneEnergyDevice:
    """An energy device associated with a zone."""

    entity_id: str
    device_class: str  # power, energy, current, voltage
    device_id: Optional[str]
    area_id: Optional[str]
    friendly_name: str
    unit: str
    related_entities: List[str]  # Non-energy entities sharing same device
    association_method: str  # "device", "area", "name", "manual"
    tags: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ZoneEnergyDiscovery:
    """Discovers and auto-associates energy entities with zones."""

    def __init__(self, hass: HomeAssistant):
        self._hass = hass

    def discover_all_energy_entities(self) -> List[Dict[str, Any]]:
        """Find all energy-related entities in HA.

        Returns list of dicts with entity info suitable for zone assignment.
        """
        ent_reg = er.async_get(self._hass)
        dev_reg = dr.async_get(self._hass)

        energy_entities = []
        for entry in ent_reg.entities.values():
            if not self._is_energy_entity(entry):
                continue

            device = None
            device_id = None
            area_id = entry.area_id

            if entry.device_id:
                device = dev_reg.async_get(entry.device_id)
                device_id = entry.device_id
                if device and not area_id:
                    area_id = device.area_id

            state = self._hass.states.get(entry.entity_id)
            friendly_name = (
                state.attributes.get("friendly_name", entry.entity_id)
                if state
                else entry.entity_id
            )
            unit = (
                state.attributes.get("unit_of_measurement", "")
                if state
                else ""
            )

            energy_entities.append({
                "entity_id": entry.entity_id,
                "device_class": entry.device_class or entry.original_device_class or "unknown",
                "device_id": device_id,
                "area_id": area_id,
                "friendly_name": friendly_name,
                "unit": unit,
                "device_name": device.name if device else None,
            })

        _LOGGER.info(
            "Discovered %d energy entities", len(energy_entities)
        )
        return energy_entities

    def discover_for_zone(
        self,
        zone_entity_ids: List[str],
        zone_name: str = "",
    ) -> List[ZoneEnergyDevice]:
        """Auto-discover energy devices related to a zone's entities.

        Uses 3 strategies:
        1. Device-based: Energy sensors sharing a device_id with zone entities
        2. Area-based: Energy sensors in the same HA area as zone entities
        3. Name-based: Energy sensors with names matching zone entities/zone name
        """
        ent_reg = er.async_get(self._hass)
        dev_reg = dr.async_get(self._hass)

        # Collect device_ids and area_ids from zone entities
        zone_device_ids: Set[str] = set()
        zone_area_ids: Set[str] = set()
        zone_entity_names: Set[str] = set()

        for eid in zone_entity_ids:
            entry = ent_reg.async_get(eid)
            if not entry:
                continue
            if entry.device_id:
                zone_device_ids.add(entry.device_id)
            if entry.area_id:
                zone_area_ids.add(entry.area_id)
            elif entry.device_id:
                device = dev_reg.async_get(entry.device_id)
                if device and device.area_id:
                    zone_area_ids.add(device.area_id)

            # Extract name for matching
            name_parts = eid.split(".")[-1].lower().replace("_", " ").split()
            zone_entity_names.update(name_parts)

        if zone_name:
            zone_entity_names.update(zone_name.lower().split())

        all_energy = self.discover_all_energy_entities()
        results: List[ZoneEnergyDevice] = []
        seen: Set[str] = set()

        for e in all_energy:
            eid = e["entity_id"]
            if eid in seen or eid in zone_entity_ids:
                continue

            method = None
            related = []

            # Strategy 1: Same device
            if e["device_id"] and e["device_id"] in zone_device_ids:
                method = "device"
                # Find which zone entities share this device
                for zeid in zone_entity_ids:
                    ze = ent_reg.async_get(zeid)
                    if ze and ze.device_id == e["device_id"]:
                        related.append(zeid)

            # Strategy 2: Same area
            elif e["area_id"] and e["area_id"] in zone_area_ids:
                method = "area"

            # Strategy 3: Name matching
            elif zone_entity_names:
                e_name = e["friendly_name"].lower()
                if any(n in e_name for n in zone_entity_names if len(n) > 3):
                    method = "name"

            if method:
                results.append(ZoneEnergyDevice(
                    entity_id=eid,
                    device_class=e["device_class"],
                    device_id=e["device_id"],
                    area_id=e["area_id"],
                    friendly_name=e["friendly_name"],
                    unit=e["unit"],
                    related_entities=related,
                    association_method=method,
                    tags=["auto-discovered", f"zone:{zone_name}"] if zone_name else ["auto-discovered"],
                ))
                seen.add(eid)

        # Sort: device matches first, then area, then name
        priority = {"device": 0, "area": 1, "name": 2, "manual": 3}
        results.sort(key=lambda x: priority.get(x.association_method, 9))

        _LOGGER.info(
            "Discovered %d energy devices for zone '%s' "
            "(device=%d, area=%d, name=%d)",
            len(results),
            zone_name,
            sum(1 for r in results if r.association_method == "device"),
            sum(1 for r in results if r.association_method == "area"),
            sum(1 for r in results if r.association_method == "name"),
        )
        return results

    def get_zone_power_total(
        self,
        energy_entity_ids: List[str],
    ) -> Dict[str, Any]:
        """Aggregate current power for a set of energy entities.

        Returns dict with total power, per-entity breakdown, and metadata.
        """
        total_watts = 0.0
        breakdown = []

        for eid in energy_entity_ids:
            state = self._hass.states.get(eid)
            if not state or state.state in ("unavailable", "unknown"):
                breakdown.append({
                    "entity_id": eid,
                    "value": None,
                    "unit": "",
                    "status": "unavailable",
                })
                continue

            try:
                value = float(state.state)
                unit = state.attributes.get("unit_of_measurement", "")

                # Convert to Watts if needed
                watts = value
                if unit in ("kW", "KW"):
                    watts = value * 1000
                elif unit in ("mW",):
                    watts = value / 1000

                total_watts += watts
                breakdown.append({
                    "entity_id": eid,
                    "value": round(value, 2),
                    "unit": unit,
                    "watts": round(watts, 2),
                    "status": "ok",
                })
            except (ValueError, TypeError):
                breakdown.append({
                    "entity_id": eid,
                    "value": state.state,
                    "unit": "",
                    "status": "non_numeric",
                })

        return {
            "total_watts": round(total_watts, 2),
            "entity_count": len(energy_entity_ids),
            "active_count": sum(1 for b in breakdown if b["status"] == "ok"),
            "breakdown": breakdown,
        }

    @staticmethod
    def _is_energy_entity(entry: er.RegistryEntry) -> bool:
        """Check if a registry entry is an energy-related entity."""
        if entry.domain not in ENERGY_DOMAINS:
            return False

        # Check device_class
        dc = entry.device_class or entry.original_device_class or ""
        if dc in ENERGY_DEVICE_CLASSES:
            return True

        # Check entity_id patterns
        eid_lower = entry.entity_id.lower()
        for pattern in ENERGY_NAME_PATTERNS:
            if pattern in eid_lower:
                return True

        return False
