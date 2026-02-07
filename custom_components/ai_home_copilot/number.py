from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_SEED_MAX_OFFERS_PER_HOUR,
    CONF_SEED_MAX_OFFERS_PER_UPDATE,
    CONF_SEED_MIN_SECONDS_BETWEEN_OFFERS,
    DEFAULT_SEED_MAX_OFFERS_PER_HOUR,
    DEFAULT_SEED_MAX_OFFERS_PER_UPDATE,
    DEFAULT_SEED_MIN_SECONDS_BETWEEN_OFFERS,
    DOMAIN,
)
from .entity import CopilotBaseEntity


class _BaseConfigNumber(CopilotBaseEntity, NumberEntity):
    _attr_has_entity_name = False
    _attr_mode = "box"
    # Advanced tuning: keep available but hidden by default.
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        *,
        key: str,
        name: str,
        unique_id: str,
        default: int,
        min_value: int,
        max_value: int,
    ):
        super().__init__(coordinator)
        self._entry = entry
        self._key = key
        self._default = default
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_native_min_value = float(min_value)
        self._attr_native_max_value = float(max_value)
        self._attr_native_step = 1.0

    @property
    def native_value(self) -> float | None:
        cfg = self._entry.data | self._entry.options
        v = cfg.get(self._key, self._default)
        try:
            return float(int(v))
        except Exception:  # noqa: BLE001
            return float(self._default)

    async def async_set_native_value(self, value: float) -> None:
        new_options = {**self._entry.options, self._key: int(value)}
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        self.async_write_ha_state()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities(
        [
            _BaseConfigNumber(
                coordinator,
                entry,
                key=CONF_SEED_MAX_OFFERS_PER_HOUR,
                name="AI Home CoPilot seed max offers per hour",
                unique_id="ai_home_copilot_seed_max_per_hour",
                default=DEFAULT_SEED_MAX_OFFERS_PER_HOUR,
                min_value=0,
                max_value=200,
            ),
            _BaseConfigNumber(
                coordinator,
                entry,
                key=CONF_SEED_MIN_SECONDS_BETWEEN_OFFERS,
                name="AI Home CoPilot seed min seconds between offers",
                unique_id="ai_home_copilot_seed_min_seconds_between",
                default=DEFAULT_SEED_MIN_SECONDS_BETWEEN_OFFERS,
                min_value=0,
                max_value=3600,
            ),
            _BaseConfigNumber(
                coordinator,
                entry,
                key=CONF_SEED_MAX_OFFERS_PER_UPDATE,
                name="AI Home CoPilot seed max offers per update",
                unique_id="ai_home_copilot_seed_max_per_update",
                default=DEFAULT_SEED_MAX_OFFERS_PER_UPDATE,
                min_value=1,
                max_value=50,
            ),
        ],
        True,
    )
