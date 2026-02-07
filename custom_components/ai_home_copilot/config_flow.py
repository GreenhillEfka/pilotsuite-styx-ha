from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_TEST_LIGHT,
    CONF_TOKEN,
    CONF_WEBHOOK_URL,
    CONF_WATCHDOG_ENABLED,
    CONF_WATCHDOG_INTERVAL_SECONDS,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_TEST_LIGHT,
    DEFAULT_WATCHDOG_ENABLED,
    DEFAULT_WATCHDOG_INTERVAL_SECONDS,
    DOMAIN,
)


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
                vol.Optional(CONF_TEST_LIGHT): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="light")
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, user_input: dict | None = None) -> FlowResult:
        return await self.async_step_user(user_input)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            # webhook_url is display-only; ignore if user edits it.
            user_input.pop(CONF_WEBHOOK_URL, None)
            return self.async_create_entry(title="", data=user_input)

        data = {**self.config_entry.data, **self.config_entry.options}

        webhook_id = data.get("webhook_id")
        base = self.hass.config.internal_url or self.hass.config.external_url or ""
        webhook_url = f"{base}/api/webhook/{webhook_id}" if webhook_id and base else (
            f"/api/webhook/{webhook_id}" if webhook_id else "(generated after first setup)"
        )

        schema = vol.Schema(
            {
                vol.Optional(CONF_WEBHOOK_URL, default=webhook_url): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=False)
                ),
                vol.Required(CONF_HOST, default=data.get(CONF_HOST, DEFAULT_HOST)): str,
                vol.Required(CONF_PORT, default=data.get(CONF_PORT, DEFAULT_PORT)): int,
                vol.Optional(CONF_TOKEN, default=data.get(CONF_TOKEN, "")): str,
                vol.Optional(
                    CONF_TEST_LIGHT,
                    default=data.get(CONF_TEST_LIGHT, ""),
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="light")),
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
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)


# Options flow is provided via ConfigFlow.async_get_options_flow
