from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_MEDIA_MUSIC_PLAYERS,
    CONF_MEDIA_TV_PLAYERS,
    CONF_SEED_ALLOWED_DOMAINS,
    CONF_SEED_BLOCKED_DOMAINS,
    CONF_SEED_MAX_OFFERS_PER_HOUR,
    CONF_SEED_MAX_OFFERS_PER_UPDATE,
    CONF_SEED_MIN_SECONDS_BETWEEN_OFFERS,
    CONF_SUGGESTION_SEED_ENTITIES,
    CONF_TEST_LIGHT,
    CONF_TOKEN,
    CONF_WEBHOOK_URL,
    CONF_WATCHDOG_ENABLED,
    CONF_WATCHDOG_INTERVAL_SECONDS,
    CONF_DEVLOG_PUSH_ENABLED,
    CONF_DEVLOG_PUSH_INTERVAL_SECONDS,
    CONF_DEVLOG_PUSH_PATH,
    CONF_DEVLOG_PUSH_MAX_LINES,
    CONF_DEVLOG_PUSH_MAX_CHARS,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_MEDIA_MUSIC_PLAYERS,
    DEFAULT_MEDIA_TV_PLAYERS,
    DEFAULT_SEED_ALLOWED_DOMAINS,
    DEFAULT_SEED_BLOCKED_DOMAINS,
    DEFAULT_SEED_MAX_OFFERS_PER_HOUR,
    DEFAULT_SEED_MAX_OFFERS_PER_UPDATE,
    DEFAULT_SEED_MIN_SECONDS_BETWEEN_OFFERS,
    DEFAULT_SUGGESTION_SEED_ENTITIES,
    DEFAULT_TEST_LIGHT,
    DEFAULT_WATCHDOG_ENABLED,
    DEFAULT_MEDIA_MUSIC_PLAYERS,
    DEFAULT_MEDIA_TV_PLAYERS,
    DEFAULT_WATCHDOG_INTERVAL_SECONDS,
    DEFAULT_DEVLOG_PUSH_ENABLED,
    DEFAULT_DEVLOG_PUSH_INTERVAL_SECONDS,
    DEFAULT_DEVLOG_PUSH_PATH,
    DEFAULT_DEVLOG_PUSH_MAX_LINES,
    DEFAULT_DEVLOG_PUSH_MAX_CHARS,
    DOMAIN,
)


def _as_csv(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ",".join([v for v in value if isinstance(v, str)])
    return str(value)


def _parse_csv(value: str) -> list[str]:
    if not value:
        return []
    parts = [p.strip() for p in value.replace("\n", ",").split(",")]
    return [p for p in parts if p]


async def _validate_input(hass: HomeAssistant, data: dict) -> None:
    # Keep validation light for MVP; coordinator will mark unavailable on failures.
    return


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await _validate_input(self.hass, user_input)
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                title = f"AI Home CoPilot ({user_input[CONF_HOST]}:{user_input[CONF_PORT]})"
                return self.async_create_entry(title=title, data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_TOKEN): str,
                # Use a plain string to maximize compatibility (no selector).
                vol.Optional(CONF_TEST_LIGHT, default=""): str,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, user_input: dict | None = None) -> FlowResult:
        return await self.async_step_user(user_input)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        # In newer HA versions, OptionsFlow has a read-only `config_entry` property.
        # Store the entry under our own attribute to stay compatible.
        self._entry = config_entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            # webhook_url is display-only; ignore if user edits it.
            user_input.pop(CONF_WEBHOOK_URL, None)

            # Normalize seed entities (comma-separated list -> list[str])
            seed_csv = user_input.get(CONF_SUGGESTION_SEED_ENTITIES)
            if isinstance(seed_csv, str):
                user_input[CONF_SUGGESTION_SEED_ENTITIES] = _parse_csv(seed_csv)

            # Normalize media players (comma-separated list -> list[str])
            music_csv = user_input.get(CONF_MEDIA_MUSIC_PLAYERS)
            if isinstance(music_csv, str):
                user_input[CONF_MEDIA_MUSIC_PLAYERS] = _parse_csv(music_csv)

            tv_csv = user_input.get(CONF_MEDIA_TV_PLAYERS)
            if isinstance(tv_csv, str):
                user_input[CONF_MEDIA_TV_PLAYERS] = _parse_csv(tv_csv)

            # Normalize media players (comma-separated list -> list[str])
            music_csv = user_input.get(CONF_MEDIA_MUSIC_PLAYERS)
            if isinstance(music_csv, str):
                user_input[CONF_MEDIA_MUSIC_PLAYERS] = _parse_csv(music_csv)

            tv_csv = user_input.get(CONF_MEDIA_TV_PLAYERS)
            if isinstance(tv_csv, str):
                user_input[CONF_MEDIA_TV_PLAYERS] = _parse_csv(tv_csv)

            # Keep allow/block domains as the raw string; seed adapter parses both list and str.
            return self.async_create_entry(title="", data=user_input)

        data = {**self._entry.data, **self._entry.options}

        webhook_id = data.get("webhook_id")
        base = self.hass.config.internal_url or self.hass.config.external_url or ""
        webhook_url = f"{base}/api/webhook/{webhook_id}" if webhook_id and base else (
            f"/api/webhook/{webhook_id}" if webhook_id else "(generated after first setup)"
        )

        schema = vol.Schema(
            {
                vol.Optional(CONF_WEBHOOK_URL, default=webhook_url): str,
                vol.Required(CONF_HOST, default=data.get(CONF_HOST, DEFAULT_HOST)): str,
                vol.Required(CONF_PORT, default=data.get(CONF_PORT, DEFAULT_PORT)): int,
                vol.Optional(CONF_TOKEN, default=data.get(CONF_TOKEN, "")): str,
                vol.Optional(
                    CONF_TEST_LIGHT,
                    default=data.get(CONF_TEST_LIGHT, ""),
                ): str,
                vol.Optional(
                    CONF_MEDIA_MUSIC_PLAYERS,
                    default=_as_csv(data.get(CONF_MEDIA_MUSIC_PLAYERS, DEFAULT_MEDIA_MUSIC_PLAYERS)),
                ): str,
                vol.Optional(
                    CONF_MEDIA_TV_PLAYERS,
                    default=_as_csv(data.get(CONF_MEDIA_TV_PLAYERS, DEFAULT_MEDIA_TV_PLAYERS)),
                ): str,
                # Comma-separated list of sensor entity_ids.
                vol.Optional(
                    CONF_SUGGESTION_SEED_ENTITIES,
                    default=_as_csv(
                        data.get(CONF_SUGGESTION_SEED_ENTITIES, DEFAULT_SUGGESTION_SEED_ENTITIES)
                    ),
                ): str,
                vol.Optional(
                    CONF_SEED_ALLOWED_DOMAINS,
                    default=_as_csv(data.get(CONF_SEED_ALLOWED_DOMAINS, DEFAULT_SEED_ALLOWED_DOMAINS)),
                ): str,
                vol.Optional(
                    CONF_SEED_BLOCKED_DOMAINS,
                    default=_as_csv(data.get(CONF_SEED_BLOCKED_DOMAINS, DEFAULT_SEED_BLOCKED_DOMAINS)),
                ): str,
                vol.Optional(
                    CONF_SEED_MAX_OFFERS_PER_HOUR,
                    default=data.get(
                        CONF_SEED_MAX_OFFERS_PER_HOUR, DEFAULT_SEED_MAX_OFFERS_PER_HOUR
                    ),
                ): int,
                vol.Optional(
                    CONF_SEED_MIN_SECONDS_BETWEEN_OFFERS,
                    default=data.get(
                        CONF_SEED_MIN_SECONDS_BETWEEN_OFFERS,
                        DEFAULT_SEED_MIN_SECONDS_BETWEEN_OFFERS,
                    ),
                ): int,
                vol.Optional(
                    CONF_SEED_MAX_OFFERS_PER_UPDATE,
                    default=data.get(
                        CONF_SEED_MAX_OFFERS_PER_UPDATE, DEFAULT_SEED_MAX_OFFERS_PER_UPDATE
                    ),
                ): int,
                vol.Optional(
                    CONF_WATCHDOG_ENABLED,
                    default=data.get(CONF_WATCHDOG_ENABLED, DEFAULT_WATCHDOG_ENABLED),
                ): bool,
                vol.Optional(
                    CONF_WATCHDOG_INTERVAL_SECONDS,
                    default=data.get(
                        CONF_WATCHDOG_INTERVAL_SECONDS, DEFAULT_WATCHDOG_INTERVAL_SECONDS
                    ),
                ): int,
                # Opt-in dev tool: push sanitized HA log snippets to Copilot-Core.
                vol.Optional(
                    CONF_DEVLOG_PUSH_ENABLED,
                    default=data.get(CONF_DEVLOG_PUSH_ENABLED, DEFAULT_DEVLOG_PUSH_ENABLED),
                ): bool,
                vol.Optional(
                    CONF_DEVLOG_PUSH_INTERVAL_SECONDS,
                    default=data.get(
                        CONF_DEVLOG_PUSH_INTERVAL_SECONDS,
                        DEFAULT_DEVLOG_PUSH_INTERVAL_SECONDS,
                    ),
                ): int,
                vol.Optional(
                    CONF_DEVLOG_PUSH_PATH,
                    default=data.get(CONF_DEVLOG_PUSH_PATH, DEFAULT_DEVLOG_PUSH_PATH),
                ): str,
                vol.Optional(
                    CONF_DEVLOG_PUSH_MAX_LINES,
                    default=data.get(CONF_DEVLOG_PUSH_MAX_LINES, DEFAULT_DEVLOG_PUSH_MAX_LINES),
                ): int,
                vol.Optional(
                    CONF_DEVLOG_PUSH_MAX_CHARS,
                    default=data.get(CONF_DEVLOG_PUSH_MAX_CHARS, DEFAULT_DEVLOG_PUSH_MAX_CHARS),
                ): int,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)


# Options flow is provided via ConfigFlow.async_get_options_flow
