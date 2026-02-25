"""Config flow for PilotSuite integration.

This is the thin coordinator module. Heavy logic lives in:
- config_helpers.py         - CSV utils, constants
- config_schema_builders.py - All schema builder functions
- config_wizard_steps.py    - Wizard step handlers
- config_zones_flow.py      - Zone management + helpers
- config_options_flow.py    - OptionsFlowHandler
"""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .config_helpers import (
    STEP_DISCOVERY,
    STEP_ZONES,
    STEP_ZONE_ENTITIES,
    STEP_ENTITIES,
    STEP_FEATURES,
    STEP_NETWORK,
    STEP_REVIEW,
    validate_input,
    discover_reachable_core_endpoint,
)
from .config_options_flow import OptionsFlowHandler  # noqa: F401 - used by HA via async_get_options_flow
from .config_wizard_steps import (
    build_discovery_form,
    build_zones_form,
    build_zone_entities_form,
    build_entities_form,
    build_features_form,
    build_network_form,
    build_review_form,
    process_discovery_input,
    process_zones_input,
    process_zone_entities_input,
    process_entities_input,
    process_features_input,
    process_network_input,
    build_final_config,
)
from .config_zones_flow import get_zone_entity_suggestions
from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_TEST_LIGHT,
    CONF_TOKEN,
    CONF_ENTITY_PROFILE,
    DEFAULT_ENTITY_PROFILE,
    ENTITY_PROFILES,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DOMAIN,
    INTEGRATION_UNIQUE_ID,
)
from .setup_wizard import SetupWizard

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def get_zone_entity_suggestions(self, zone_name: str) -> dict:
        """Get entity suggestions for a zone."""
        return await get_zone_entity_suggestions(self.hass, zone_name)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Initial step - show main menu with Zero Config, Quick Start, or Manual."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_show_menu(
            step_id="user",
            menu_options=["zero_config", "quick_start", "manual_setup"],
            description_placeholders={
                "description": "PilotSuite Setup\n\n"
                "Choose your setup method:\n\n"
                "Zero Config: Install and start immediately with smart defaults. "
                "PilotSuite discovers your devices automatically and asks for "
                "improvements later through conversation.\n\n"
                "Quick Start: Guided wizard to configure zones and devices (~2 min).\n\n"
                "Manual Setup: Expert configuration with full control.\n"
            },
        )

    async def async_step_zero_config(self, user_input: dict | None = None) -> FlowResult:
        """Zero Config - instant start with Styx defaults.

        Tries Core connectivity first; if unreachable, creates the entry
        anyway (governance-first: the user can reconfigure later) but
        logs a clear warning so it shows up in the system log.
        """
        resolved = await discover_reachable_core_endpoint(
            self.hass,
            preferred_host=DEFAULT_HOST,
            preferred_port=DEFAULT_PORT,
        )
        host, port = resolved if resolved else (DEFAULT_HOST, DEFAULT_PORT)
        if resolved is None:
            _LOGGER.warning(
                "Zero-config: no reachable Core endpoint auto-detected; using defaults %s:%s",
                DEFAULT_HOST,
                DEFAULT_PORT,
            )

        config = {
            CONF_HOST: host,
            CONF_PORT: port,
            CONF_TOKEN: "",
            CONF_ENTITY_PROFILE: DEFAULT_ENTITY_PROFILE,
            "assistant_name": "Styx",
        }

        # Best-effort connectivity check (non-blocking)
        try:
            await validate_input(self.hass, config)
            _LOGGER.info("Zero-config: Core reachable at %s:%s", host, port)
        except Exception:
            _LOGGER.warning(
                "Zero-config: Core Add-on not reachable at %s:%s — "
                "integration will start anyway. Reconfigure via "
                "Settings > Integrations > PilotSuite > Configure",
                host,
                port,
            )

        await self.async_set_unique_id(INTEGRATION_UNIQUE_ID)
        self._abort_if_unique_id_configured()

        title = "Styx — PilotSuite"
        return self.async_create_entry(title=title, data=config)

    async def async_step_quick_start(self, user_input: dict | None = None) -> FlowResult:
        """Quick Start - guided wizard with smart defaults."""
        return await self.async_step_wizard(user_input)

    async def async_step_manual_setup(self, user_input: dict | None = None) -> FlowResult:
        """Manual setup - direct configuration form."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Best-effort connectivity check — warn but always create entry
            try:
                await validate_input(self.hass, user_input)
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning(
                    "Core not reachable at %s:%s (%s) — "
                    "creating entry anyway, will retry automatically",
                    user_input.get(CONF_HOST),
                    user_input.get(CONF_PORT),
                    err,
                )

            if self.source == config_entries.SOURCE_REAUTH:
                reauth_entry = self.hass.config_entries.async_get_entry(self.context.get("entry_id"))
                if reauth_entry is not None:
                    updated = {**reauth_entry.data, **user_input}
                    updated.setdefault(CONF_ENTITY_PROFILE, DEFAULT_ENTITY_PROFILE)
                    self.hass.config_entries.async_update_entry(reauth_entry, data=updated)
                    await self.hass.config_entries.async_reload(reauth_entry.entry_id)
                    return self.async_abort(reason="reauth_successful")

            name = user_input.get("assistant_name", "Styx")
            title = f"{name} — PilotSuite ({user_input[CONF_HOST]}:{user_input[CONF_PORT]})"
            user_input.setdefault(CONF_ENTITY_PROFILE, DEFAULT_ENTITY_PROFILE)
            await self.async_set_unique_id(INTEGRATION_UNIQUE_ID)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=title, data=user_input)

        discovered = await discover_reachable_core_endpoint(
            self.hass,
            preferred_host=DEFAULT_HOST,
            preferred_port=DEFAULT_PORT,
        )
        default_host, default_port = discovered if discovered else (DEFAULT_HOST, DEFAULT_PORT)

        schema = vol.Schema(
            {
                vol.Optional("assistant_name", default="Styx"): str,
                vol.Required(CONF_HOST, default=default_host): str,
                vol.Required(CONF_PORT, default=default_port): int,
                vol.Optional(CONF_TOKEN): str,
                vol.Optional(CONF_ENTITY_PROFILE, default=DEFAULT_ENTITY_PROFILE): vol.In(ENTITY_PROFILES),
                vol.Optional(CONF_TEST_LIGHT, default=None): vol.Any(
                    None,
                    selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="light", multiple=False),
                    ),
                ),
            }
        )

        return self.async_show_form(
            step_id="manual_setup",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "description": "Enter your PilotSuite Core Add-on connection details."
            },
        )

    async def async_step_reauth(self, user_input: dict | None = None) -> FlowResult:
        return await self.async_step_manual_setup(user_input)

    # ── Wizard dispatcher ────────────────────────────────────────────

    async def async_step_wizard(self, user_input: dict | None = None) -> FlowResult:
        """Setup wizard - multi-step guided configuration."""
        if not hasattr(self, "_wizard"):
            self._wizard = SetupWizard(self.hass)
            self._data: dict = {}

        wizard = self._wizard
        wizard_step = getattr(self, "_wizard_step", STEP_DISCOVERY)

        # Show form for current step (no user input yet)
        if user_input is None:
            return self._show_wizard_step(wizard_step, wizard)

        # Process input and advance to next step
        next_step = self._process_wizard_input(wizard_step, user_input, wizard)

        # Handle async discovery if flagged
        if self._data.pop("_auto_discover", False):
            discovered = await wizard.discover_entities()
            self._data["discovery"] = discovered

        # Final step: create entry
        if next_step is None:
            final_config, title = build_final_config(self._data)
            final_config.setdefault(CONF_ENTITY_PROFILE, DEFAULT_ENTITY_PROFILE)
            try:
                preferred_port = int(final_config.get(CONF_PORT, DEFAULT_PORT))
            except (TypeError, ValueError):
                preferred_port = DEFAULT_PORT
            resolved = await discover_reachable_core_endpoint(
                self.hass,
                preferred_host=str(final_config.get(CONF_HOST, DEFAULT_HOST)),
                preferred_port=preferred_port,
            )
            if resolved is not None:
                final_config[CONF_HOST], final_config[CONF_PORT] = resolved
            await self.async_set_unique_id(INTEGRATION_UNIQUE_ID)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=title, data=final_config)

        self._wizard_step = next_step
        return await self.async_step_wizard(None)

    def _show_wizard_step(self, step: str, wizard) -> FlowResult:
        """Show the form for a wizard step."""
        builders = {
            STEP_DISCOVERY: lambda: build_discovery_form(),
            STEP_ZONES: lambda: build_zones_form(wizard),
            STEP_ZONE_ENTITIES: lambda: self._build_zone_entities(wizard),
            STEP_ENTITIES: lambda: build_entities_form(wizard),
            STEP_FEATURES: lambda: build_features_form(),
            STEP_NETWORK: lambda: build_network_form(),
            STEP_REVIEW: lambda: build_review_form(self._data),
        }

        step_id, data_schema, desc = builders[step]()
        kwargs: dict = {"step_id": step_id, "data_schema": data_schema}
        if desc:
            kwargs["description_placeholders"] = desc
        return self.async_show_form(**kwargs)

    def _build_zone_entities(self, wizard):
        """Build zone entities form, or skip if no zones selected."""
        selected_zones = self._data.get("selected_zones", [])
        if not selected_zones:
            # No zones selected, skip to entities
            self._wizard_step = STEP_ENTITIES
            return build_entities_form(wizard)
        return build_zone_entities_form(wizard, selected_zones)

    def _process_wizard_input(self, step: str, user_input: dict, wizard) -> str | None:
        """Process wizard step input. Returns next step name or None for final."""
        processors = {
            STEP_DISCOVERY: lambda ui: process_discovery_input(ui, wizard, self._data),
            STEP_ZONES: lambda ui: process_zones_input(ui, self._data),
            STEP_ZONE_ENTITIES: lambda ui: process_zone_entities_input(ui, self._data),
            STEP_ENTITIES: lambda ui: process_entities_input(ui, self._data),
            STEP_FEATURES: lambda ui: process_features_input(ui, self._data),
            STEP_NETWORK: lambda ui: process_network_input(ui, self._data),
            STEP_REVIEW: lambda ui: None,  # Final step
        }
        return processors[step](user_input)
