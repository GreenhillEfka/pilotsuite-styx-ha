from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_MEDIA_MUSIC_PLAYERS,
    CONF_MEDIA_TV_PLAYERS,
    CONF_SEED_ALLOWED_DOMAINS,
    CONF_SEED_BLOCKED_DOMAINS,
    CONF_SUGGESTION_SEED_ENTITIES,
    CONF_TEST_LIGHT,
    DOMAIN,
)
from .entity import CopilotBaseEntity
from .habitus_zones_entities import HabitusZonesJsonText


def _as_csv(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ",".join([v for v in value if isinstance(v, str)])
    return str(value)


class _BaseConfigText(CopilotBaseEntity, TextEntity):
    _attr_has_entity_name = False
    _attr_mode = "text"
    # Advanced config surface: keep available but hidden by default to reduce entity clutter.
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, entry: ConfigEntry, *, key: str, name: str, unique_id: str):
        super().__init__(coordinator)
        self._entry = entry
        self._key = key
        self._attr_name = name
        self._attr_unique_id = unique_id

    @property
    def native_value(self) -> str | None:
        cfg = self._entry.data | self._entry.options
        return _as_csv(cfg.get(self._key, ""))

    async def async_set_value(self, value: str) -> None:
        # Persist in entry.options so it survives restarts.
        new_options = {**self._entry.options, self._key: value}
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        self.async_write_ha_state()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities(
        [
            HabitusZonesJsonText(coordinator, entry),
            _BaseConfigText(
                coordinator,
                entry,
                key=CONF_SUGGESTION_SEED_ENTITIES,
                name="AI Home CoPilot seed sensors (csv)",
                unique_id="ai_home_copilot_seed_sensors_csv",
            ),
            _BaseConfigText(
                coordinator,
                entry,
                key=CONF_SEED_ALLOWED_DOMAINS,
                name="AI Home CoPilot seed allow domains (csv)",
                unique_id="ai_home_copilot_seed_allow_domains_csv",
            ),
            _BaseConfigText(
                coordinator,
                entry,
                key=CONF_SEED_BLOCKED_DOMAINS,
                name="AI Home CoPilot seed block domains (csv)",
                unique_id="ai_home_copilot_seed_block_domains_csv",
            ),
            _BaseConfigText(
                coordinator,
                entry,
                key=CONF_TEST_LIGHT,
                name="AI Home CoPilot test light entity_id",
                unique_id="ai_home_copilot_test_light_entity_id",
            ),
            _BaseConfigText(
                coordinator,
                entry,
                key=CONF_MEDIA_MUSIC_PLAYERS,
                name="AI Home CoPilot media music players (csv)",
                unique_id="ai_home_copilot_media_music_players_csv",
            ),
            _BaseConfigText(
                coordinator,
                entry,
                key=CONF_MEDIA_TV_PLAYERS,
                name="AI Home CoPilot media TV players (csv)",
                unique_id="ai_home_copilot_media_tv_players_csv",
            ),
        ],
        True,
    )
