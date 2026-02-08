from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event

from .entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class _AggregateSpec:
    key: str
    label: str
    device_class: SensorDeviceClass | None


_AGGREGATES: list[_AggregateSpec] = [
    _AggregateSpec(
        key="temperature",
        label="Temperatur Ø",
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    _AggregateSpec(
        key="humidity",
        label="Luftfeuchte Ø",
        device_class=SensorDeviceClass.HUMIDITY,
    ),
]


def _as_float(state: str) -> float | None:
    try:
        return float(state)
    except Exception:  # noqa: BLE001
        return None


class HabitusZoneAverageSensor(CopilotBaseEntity, SensorEntity):
    """Average sensor over a list of source sensors.

    This is intentionally simple and local-only.
    """

    _attr_has_entity_name = False
    _attr_icon = "mdi:calculator-variant"

    def __init__(
        self,
        coordinator,
        *,
        hass: HomeAssistant,
        zone_id: str,
        zone_name: str,
        spec: _AggregateSpec,
        sources: list[str],
    ) -> None:
        super().__init__(coordinator)
        self.hass = hass
        self._zone_id = zone_id
        self._zone_name = zone_name
        self._spec = spec
        self._sources = [s for s in sources if isinstance(s, str) and s]

        self._attr_unique_id = f"ai_home_copilot_hz_{zone_id}_{spec.key}_avg"
        # Stable entity_id for dashboards.
        self.entity_id = f"sensor.ai_home_copilot_hz_{zone_id}_{spec.key}_avg"
        self._attr_name = f"{zone_name} {spec.label}"

        self._attr_device_class = spec.device_class
        self._attr_state_class = "measurement"

        # Default units (best effort, updated on first calculation)
        if spec.key == "temperature":
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        elif spec.key == "humidity":
            self._attr_native_unit_of_measurement = PERCENTAGE

        self._value: float | None = None
        self._unsub = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._sources:
            self._unsub = async_track_state_change_event(
                self.hass, self._sources, self._on_source_change
            )
        await self._recalc()

    async def async_will_remove_from_hass(self) -> None:
        if callable(self._unsub):
            self._unsub()
        self._unsub = None
        await super().async_will_remove_from_hass()

    @property
    def native_value(self) -> float | None:
        return self._value

    async def _on_source_change(self, _event: Event) -> None:
        await self._recalc()

    async def _recalc(self) -> None:
        vals: list[float] = []
        unit = None

        for eid in self._sources:
            st = self.hass.states.get(eid)
            if st is None:
                continue
            v = _as_float(st.state)
            if v is None:
                continue
            vals.append(v)
            if unit is None:
                unit = st.attributes.get("unit_of_measurement")

        if not vals:
            self._value = None
        else:
            self._value = round(sum(vals) / len(vals), 2)

        if unit:
            self._attr_native_unit_of_measurement = unit

        self.async_write_ha_state()


def build_zone_average_sensors(
    *,
    hass: HomeAssistant,
    coordinator,
    zone_id: str,
    zone_name: str,
    entities_by_role: dict[str, list[str]] | None,
) -> list[HabitusZoneAverageSensor]:
    """Create average sensors for a zone.

    Policy: only create an average sensor when there are >2 source entities.
    """

    if not isinstance(entities_by_role, dict):
        return []

    out: list[HabitusZoneAverageSensor] = []
    for spec in _AGGREGATES:
        sources = entities_by_role.get(spec.key) or []
        if len(sources) <= 2:
            continue
        out.append(
            HabitusZoneAverageSensor(
                coordinator,
                hass=hass,
                zone_id=zone_id,
                zone_name=zone_name,
                spec=spec,
                sources=[str(x) for x in sources],
            )
        )

    return out
