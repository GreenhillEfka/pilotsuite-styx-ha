from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

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
    CONF_ENABLE_USER_PREFERENCES,
    CONF_DEVLOG_PUSH_ENABLED,
    CONF_DEVLOG_PUSH_INTERVAL_SECONDS,
    CONF_DEVLOG_PUSH_PATH,
    CONF_DEVLOG_PUSH_MAX_LINES,
    CONF_DEVLOG_PUSH_MAX_CHARS,
    CONF_EVENTS_FORWARDER_ENABLED,
    CONF_EVENTS_FORWARDER_FLUSH_INTERVAL_SECONDS,
    CONF_EVENTS_FORWARDER_MAX_BATCH,
    CONF_EVENTS_FORWARDER_FORWARD_CALL_SERVICE,
    CONF_EVENTS_FORWARDER_IDEMPOTENCY_TTL_SECONDS,
    CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_ENABLED,
    CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_MAX_SIZE,
    CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_FLUSH_INTERVAL_SECONDS,
    CONF_EVENTS_FORWARDER_INCLUDE_HABITUS_ZONES,
    CONF_EVENTS_FORWARDER_INCLUDE_MEDIA_PLAYERS,
    CONF_EVENTS_FORWARDER_ADDITIONAL_ENTITIES,
    CONF_HA_ERRORS_DIGEST_ENABLED,
    CONF_HA_ERRORS_DIGEST_INTERVAL_SECONDS,
    CONF_HA_ERRORS_DIGEST_MAX_LINES,
    CONF_PILOTSUITE_SHOW_SAFETY_BACKUP_BUTTONS,
    CONF_PILOTSUITE_SHOW_DEV_SURFACE_BUTTONS,
    CONF_PILOTSUITE_SHOW_GRAPH_BRIDGE_BUTTONS,
    # User Preference Module
    CONF_USER_PREFERENCE_ENABLED,
    CONF_TRACKED_USERS,
    CONF_PRIMARY_USER,
    CONF_USER_LEARNING_MODE,
    DEFAULT_USER_PREFERENCE_ENABLED,
    DEFAULT_TRACKED_USERS,
    DEFAULT_PRIMARY_USER,
    DEFAULT_USER_LEARNING_MODE,
    USER_LEARNING_MODES,
    # Multi-User Preference Learning (MUPL) Module v0.8.0
    CONF_MUPL_ENABLED,
    CONF_MUPL_PRIVACY_MODE,
    CONF_MUPL_MIN_INTERACTIONS,
    CONF_MUPL_RETENTION_DAYS,
    DEFAULT_MUPL_ENABLED,
    DEFAULT_MUPL_PRIVACY_MODE,
    DEFAULT_MUPL_MIN_INTERACTIONS,
    DEFAULT_MUPL_RETENTION_DAYS,
    MUPL_PRIVACY_MODES,
    # Neural System Configuration
    CONF_NEURON_ENABLED,
    CONF_NEURON_EVALUATION_INTERVAL,
    CONF_NEURON_CONTEXT_ENTITIES,
    CONF_NEURON_STATE_ENTITIES,
    CONF_NEURON_MOOD_ENTITIES,
    DEFAULT_NEURON_ENABLED,
    DEFAULT_NEURON_EVALUATION_INTERVAL,
    DEFAULT_NEURON_CONTEXT_ENTITIES,
    DEFAULT_NEURON_STATE_ENTITIES,
    DEFAULT_NEURON_MOOD_ENTITIES,
    NEURON_TYPES,
    # Other defaults
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
    DEFAULT_ENABLE_USER_PREFERENCES,
    DEFAULT_DEVLOG_PUSH_ENABLED,
    DEFAULT_DEVLOG_PUSH_INTERVAL_SECONDS,
    DEFAULT_DEVLOG_PUSH_PATH,
    DEFAULT_DEVLOG_PUSH_MAX_LINES,
    DEFAULT_DEVLOG_PUSH_MAX_CHARS,
    DEFAULT_EVENTS_FORWARDER_ENABLED,
    DEFAULT_EVENTS_FORWARDER_FLUSH_INTERVAL_SECONDS,
    DEFAULT_EVENTS_FORWARDER_MAX_BATCH,
    DEFAULT_EVENTS_FORWARDER_FORWARD_CALL_SERVICE,
    DEFAULT_EVENTS_FORWARDER_IDEMPOTENCY_TTL_SECONDS,
    DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_ENABLED,
    DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_MAX_SIZE,
    DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_FLUSH_INTERVAL_SECONDS,
    DEFAULT_EVENTS_FORWARDER_INCLUDE_HABITUS_ZONES,
    DEFAULT_EVENTS_FORWARDER_INCLUDE_MEDIA_PLAYERS,
    DEFAULT_EVENTS_FORWARDER_ADDITIONAL_ENTITIES,
    DEFAULT_HA_ERRORS_DIGEST_ENABLED,
    DEFAULT_HA_ERRORS_DIGEST_INTERVAL_SECONDS,
    DEFAULT_HA_ERRORS_DIGEST_MAX_LINES,
    DEFAULT_PILOTSUITE_SHOW_SAFETY_BACKUP_BUTTONS,
    DEFAULT_PILOTSUITE_SHOW_DEV_SURFACE_BUTTONS,
    DEFAULT_PILOTSUITE_SHOW_GRAPH_BRIDGE_BUTTONS,
    DOMAIN,
)

# Import from setup_wizard
from .setup_wizard import (
    SetupWizard,
    SCHEMA_FEATURES,
    SCHEMA_NETWORK,
    SCHEMA_REVIEW,
)

# Wizard step constants
STEP_DISCOVERY = "discovery"
STEP_ZONES = "zones"
STEP_ENTITIES = "entities"
STEP_FEATURES = "features"
STEP_NETWORK = "network"
STEP_REVIEW = "review"


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
        """Initial step - show main menu with Quick Start vs Manual Setup."""
        # Show main menu: Quick Start vs Manual Setup
        return self.async_show_menu(
            step_id="user",
            menu_options=["quick_start", "manual_setup"],
            description_placeholders={
                "description": "🏠 **AI Home CoPilot Setup**\n\n"
                "Choose your setup method:\n\n"
                "⚡ **Quick Start**: Auto-configure with smart defaults\n"
                "   - Auto-discovers your devices\n"
                "   - Configures media players automatically\n"
                "   - Ready in under 2 minutes\n\n"
                "⚙️ **Manual Setup**: Expert configuration\n"
                "   - Full control over all options\n"
                "   - Advanced networking settings\n"
            }
        )

    async def async_step_quick_start(self, user_input: dict | None = None) -> FlowResult:
        """Quick Start - guided wizard with smart defaults."""
        return await self.async_step_wizard(user_input)

    async def async_step_manual_setup(self, user_input: dict | None = None) -> FlowResult:
        """Manual setup - direct configuration form."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await _validate_input(self.hass, user_input)
            except Exception as err:  # noqa: BLE001
                import logging
                _LOGGER = logging.getLogger(__name__)
                _LOGGER.error("Config validation failed for %s:%s - %s", 
                             user_input.get(CONF_HOST), user_input.get(CONF_PORT), str(err))
                _LOGGER.debug("Config validation error details", exc_info=True)
                errors["base"] = "cannot_connect"
            else:
                title = f"AI Home CoPilot ({user_input[CONF_HOST]}:{user_input[CONF_PORT]})"
                return self.async_create_entry(title=title, data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_TOKEN): str,
                vol.Optional(CONF_TEST_LIGHT, default=""): str,
            }
        )

        return self.async_show_form(
            step_id="manual_setup", 
            data_schema=schema, 
            errors=errors,
            description_placeholders={
                "description": "Enter your OpenClaw Gateway connection details."
            }
        )

    async def async_step_reauth(self, user_input: dict | None = None) -> FlowResult:
        return await self.async_step_manual_setup(user_input)

    async def async_step_wizard(self, user_input: dict | None = None) -> FlowResult:
        """Setup wizard - guided configuration for new users.
        
        Multi-step wizard:
        1. Quick Start - auto-discovery with defaults
        2. Zone selection (full wizard)
        3. Entity selection
        4. Feature selection
        5. Network configuration
        6. Review & confirm
        """
        # Initialize wizard and data storage
        if not hasattr(self, "_wizard"):
            self._wizard = SetupWizard(self.hass)
            self._data = {}
        
        wizard = self._wizard
        
        # Handle wizard flow state
        wizard_step = getattr(self, "_wizard_step", STEP_DISCOVERY)
        
        if user_input is None:
            # Show current step
            if wizard_step == STEP_DISCOVERY:
                return self.async_show_form(
                    step_id="wizard_discovery",
                    data_schema=vol.Schema({
                        vol.Optional("quick_start", default=True): bool,
                        vol.Optional("auto_discover", default=True): bool,
                    }),
                    description_placeholders={
                        "description": "Quick Start uses intelligent defaults based on your HA setup. "
                        "Auto-discovery will scan for compatible devices.\n\n"
                        "Skip advanced configuration if you're experienced with OpenClaw."
                    }
                )
            elif wizard_step == STEP_ZONES:
                zone_suggestions = wizard.get_zone_suggestions()
                zone_options = [(z["area_id"], f"{z['name']} ({z['entity_count']} entities)") for z in zone_suggestions]
                
                if zone_options:
                    zone_schema = vol.Schema({
                        vol.Optional("selected_zones"): selector({
                            "select": {
                                "options": zone_options,
                                "multiple": True,
                                "mode": "list",
                            }
                        }),
                    })
                else:
                    zone_schema = vol.Schema({
                        vol.Optional("selected_zones"): str,
                    })
                    
                return self.async_show_form(
                    step_id="wizard_zones",
                    data_schema=zone_schema,
                    description_placeholders={
                        "found_zones": str(len(zone_suggestions)),
                        "hint": "Select zones or skip with empty selection."
                    }
                )
            elif wizard_step == STEP_ENTITIES:
                suggestions = wizard.suggest_media_players()
                return self.async_show_form(
                    step_id="wizard_entities",
                    data_schema=vol.Schema({
                        vol.Optional("music_players", default=suggestions["music"]): selector({
                            "entity": {
                                "filter": [{"domain": "media_player"}],
                                "multiple": True,
                            }
                        }),
                        vol.Optional("tv_players", default=suggestions["tv"]): selector({
                            "entity": {
                                "filter": [{"domain": "media_player", "device_class": "tv"}],
                                "multiple": True,
                            }
                        }),
                    }),
                )
            elif wizard_step == STEP_FEATURES:
                return self.async_show_form(
                    step_id="wizard_features",
                    data_schema=SCHEMA_FEATURES,
                )
            elif wizard_step == STEP_NETWORK:
                return self.async_show_form(
                    step_id="wizard_network",
                    data_schema=SCHEMA_NETWORK,
                )
            elif wizard_step == STEP_REVIEW:
                # Generate summary
                network = self._data.get("network", {})
                entities = self._data.get("entities", {})
                features = self._data.get("features", [])
                zones = self._data.get("selected_zones", [])
                
                music_count = len(entities.get("music_players", [])) if isinstance(entities.get("music_players"), list) else 0
                tv_count = len(entities.get("tv_players", [])) if isinstance(entities.get("tv_players"), list) else 0
                
                summary = f"""
**Configuration Summary:**

**Network:**
- Host: {network.get(CONF_HOST, DEFAULT_HOST)}
- Port: {network.get(CONF_PORT, DEFAULT_PORT)}

**Selected Zones:** {len(zones) if zones else 'Auto-detected'}

**Media Players:**
- Music: {music_count} players
- TV: {tv_count} players

**Features:** {', '.join(features) if features else 'Basic'}
                """
                
                return self.async_show_form(
                    step_id="wizard_review",
                    data_schema=SCHEMA_REVIEW,
                    description_placeholders={"summary": summary}
                )
        
        # Process user input based on current step
        if wizard_step == STEP_DISCOVERY:
            quick_start = user_input.get("quick_start", True)
            auto_discover = user_input.get("auto_discover", True)
            self._data["quick_start"] = quick_start
            
            if auto_discover:
                # Perform discovery
                discovered = await wizard.discover_entities()
                self._data["discovery"] = discovered
            
            if quick_start:
                # Quick Start mode - use smart defaults
                suggestions = wizard.suggest_media_players()
                self._data["entities"] = {
                    "music_players": suggestions.get("music", []),
                    "tv_players": suggestions.get("tv", []),
                }
                self._data["features"] = ["basic", "media_control"]
                self._data["selected_zones"] = []
                self._data["network"] = {
                    CONF_HOST: DEFAULT_HOST,
                    CONF_PORT: DEFAULT_PORT,
                    CONF_TOKEN: "",
                }
                # Skip to review
                self._wizard_step = STEP_REVIEW
            else:
                # Full wizard - continue to zones
                self._wizard_step = STEP_ZONES
            
            return await self.async_step_wizard(None)
            
        elif wizard_step == STEP_ZONES:
            self._data["selected_zones"] = user_input.get("selected_zones", [])
            self._wizard_step = STEP_ENTITIES
            return await self.async_step_wizard(None)
            
        elif wizard_step == STEP_ENTITIES:
            self._data["entities"] = user_input
            self._wizard_step = STEP_FEATURES
            return await self.async_step_wizard(None)
            
        elif wizard_step == STEP_FEATURES:
            self._data["features"] = user_input.get("features", [])
            self._wizard_step = STEP_NETWORK
            return await self.async_step_wizard(None)
            
        elif wizard_step == STEP_NETWORK:
            self._data["network"] = user_input
            self._wizard_step = STEP_REVIEW
            return await self.async_step_wizard(None)
            
        elif wizard_step == STEP_REVIEW:
            # Generate final configuration
            final_config = {
                **self._data.get("network", {}),
                **self._data.get("entities", {}),
                "selected_zones": self._data.get("selected_zones", []),
                "features": self._data.get("features", []),
                CONF_WATCHDOG_ENABLED: DEFAULT_WATCHDOG_ENABLED,
                CONF_EVENTS_FORWARDER_ENABLED: DEFAULT_EVENTS_FORWARDER_ENABLED,
            }
            
            title = "AI Home CoPilot (Quick Start)" if self._data.get("quick_start") else "AI Home CoPilot"
            return self.async_create_entry(title=title, data=final_config)


from .config_snapshot_flow import ConfigSnapshotOptionsFlow


class OptionsFlowHandler(config_entries.OptionsFlow, ConfigSnapshotOptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        # In newer HA versions, OptionsFlow has a read-only `config_entry` property.
        # Store the entry under our own attribute to stay compatible.
        self._entry = config_entry
        ConfigSnapshotOptionsFlow.__init__(self, config_entry)

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        # Top-level menu: keep settings form, add Habitus zones wizard.
        return self.async_show_menu(
            step_id="init",
            menu_options=["settings", "habitus_zones", "neurons", "backup_restore"],
        )

    async def async_step_settings(self, user_input: dict | None = None) -> FlowResult:
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

            # Normalize additional forwarder entities (comma-separated list -> list[str])
            additional_entities_csv = user_input.get(CONF_EVENTS_FORWARDER_ADDITIONAL_ENTITIES)
            if isinstance(additional_entities_csv, str):
                user_input[CONF_EVENTS_FORWARDER_ADDITIONAL_ENTITIES] = _parse_csv(additional_entities_csv)

            # Normalize tracked users (comma-separated list -> list[str])
            tracked_users_csv = user_input.get(CONF_TRACKED_USERS)
            if isinstance(tracked_users_csv, str):
                user_input[CONF_TRACKED_USERS] = _parse_csv(tracked_users_csv)

            # Token handling: if empty string provided, explicitly remove token
            if CONF_TOKEN in user_input:
                token = user_input.get(CONF_TOKEN, "").strip()
                if not token:  # Empty or whitespace-only = clear token
                    user_input[CONF_TOKEN] = ""

            # Keep allow/block domains as the raw string; seed adapter parses both list and str.
            return self.async_create_entry(title="", data=user_input)

        data = {**self._entry.data, **self._entry.options}

        webhook_id = data.get("webhook_id")
        base = self.hass.config.internal_url or self.hass.config.external_url or ""
        webhook_url = f"{base}/api/webhook/{webhook_id}" if webhook_id and base else (
            f"/api/webhook/{webhook_id}" if webhook_id else "(generated after first setup)"
        )

        # Token helper text
        current_token = data.get(CONF_TOKEN, "")
        token_hint = "** AKTUELL GESETZT **" if current_token else "Leer lassen um Token zu löschen"
        
        schema = vol.Schema(
            {
                vol.Optional(CONF_WEBHOOK_URL, default=webhook_url): str,
                vol.Required(CONF_HOST, default=data.get(CONF_HOST, DEFAULT_HOST)): str,
                vol.Required(CONF_PORT, default=data.get(CONF_PORT, DEFAULT_PORT)): int,
                vol.Optional(CONF_TOKEN, default="", description={"suggested_value": token_hint}): str,
                vol.Optional(CONF_TEST_LIGHT, default=data.get(CONF_TEST_LIGHT, "")): str,
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
                vol.Optional(
                    CONF_ENABLE_USER_PREFERENCES,
                    default=data.get(
                        CONF_ENABLE_USER_PREFERENCES, DEFAULT_ENABLE_USER_PREFERENCES
                    ),
                ): bool,
                # Core API v1: HA -> Core event forwarder (opt-in, allowlist=Habitus zones).
                vol.Optional(
                    CONF_EVENTS_FORWARDER_ENABLED,
                    default=data.get(CONF_EVENTS_FORWARDER_ENABLED, DEFAULT_EVENTS_FORWARDER_ENABLED),
                ): bool,
                vol.Optional(
                    CONF_EVENTS_FORWARDER_FLUSH_INTERVAL_SECONDS,
                    default=data.get(
                        CONF_EVENTS_FORWARDER_FLUSH_INTERVAL_SECONDS,
                        DEFAULT_EVENTS_FORWARDER_FLUSH_INTERVAL_SECONDS,
                    ),
                ): int,
                vol.Optional(
                    CONF_EVENTS_FORWARDER_MAX_BATCH,
                    default=data.get(
                        CONF_EVENTS_FORWARDER_MAX_BATCH,
                        DEFAULT_EVENTS_FORWARDER_MAX_BATCH,
                    ),
                ): int,
                vol.Optional(
                    CONF_EVENTS_FORWARDER_FORWARD_CALL_SERVICE,
                    default=data.get(
                        CONF_EVENTS_FORWARDER_FORWARD_CALL_SERVICE,
                        DEFAULT_EVENTS_FORWARDER_FORWARD_CALL_SERVICE,
                    ),
                ): bool,
                vol.Optional(
                    CONF_EVENTS_FORWARDER_IDEMPOTENCY_TTL_SECONDS,
                    default=data.get(
                        CONF_EVENTS_FORWARDER_IDEMPOTENCY_TTL_SECONDS,
                        DEFAULT_EVENTS_FORWARDER_IDEMPOTENCY_TTL_SECONDS,
                    ),
                ): int,

                # Events forwarder persistent queue (optional): store unsent events across HA restarts.
                vol.Optional(
                    CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_ENABLED,
                    default=data.get(
                        CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_ENABLED,
                        DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_ENABLED,
                    ),
                ): bool,
                vol.Optional(
                    CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_MAX_SIZE,
                    default=data.get(
                        CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_MAX_SIZE,
                        DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_MAX_SIZE,
                    ),
                ): int,
                vol.Optional(
                    CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_FLUSH_INTERVAL_SECONDS,
                    default=data.get(
                        CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_FLUSH_INTERVAL_SECONDS,
                        DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_FLUSH_INTERVAL_SECONDS,
                    ),
                ): int,
                # Entity allowlist options for events forwarder
                vol.Optional(
                    CONF_EVENTS_FORWARDER_INCLUDE_HABITUS_ZONES,
                    default=data.get(
                        CONF_EVENTS_FORWARDER_INCLUDE_HABITUS_ZONES,
                        DEFAULT_EVENTS_FORWARDER_INCLUDE_HABITUS_ZONES,
                    ),
                ): bool,
                vol.Optional(
                    CONF_EVENTS_FORWARDER_INCLUDE_MEDIA_PLAYERS,
                    default=data.get(
                        CONF_EVENTS_FORWARDER_INCLUDE_MEDIA_PLAYERS,
                        DEFAULT_EVENTS_FORWARDER_INCLUDE_MEDIA_PLAYERS,
                    ),
                ): bool,
                vol.Optional(
                    CONF_EVENTS_FORWARDER_ADDITIONAL_ENTITIES,
                    default=_as_csv(data.get(
                        CONF_EVENTS_FORWARDER_ADDITIONAL_ENTITIES,
                        DEFAULT_EVENTS_FORWARDER_ADDITIONAL_ENTITIES,
                    )),
                ): str,

                # PilotSuite UX knobs (safe defaults).
                vol.Optional(
                    CONF_PILOTSUITE_SHOW_SAFETY_BACKUP_BUTTONS,
                    default=data.get(
                        CONF_PILOTSUITE_SHOW_SAFETY_BACKUP_BUTTONS,
                        DEFAULT_PILOTSUITE_SHOW_SAFETY_BACKUP_BUTTONS,
                    ),
                ): bool,
                vol.Optional(
                    CONF_PILOTSUITE_SHOW_DEV_SURFACE_BUTTONS,
                    default=data.get(
                        CONF_PILOTSUITE_SHOW_DEV_SURFACE_BUTTONS,
                        DEFAULT_PILOTSUITE_SHOW_DEV_SURFACE_BUTTONS,
                    ),
                ): bool,
                vol.Optional(
                    CONF_PILOTSUITE_SHOW_GRAPH_BRIDGE_BUTTONS,
                    default=data.get(
                        CONF_PILOTSUITE_SHOW_GRAPH_BRIDGE_BUTTONS,
                        DEFAULT_PILOTSUITE_SHOW_GRAPH_BRIDGE_BUTTONS,
                    ),
                ): bool,

                # Local HA log digest (opt-in): show relevant warnings/errors as notifications.
                vol.Optional(
                    CONF_HA_ERRORS_DIGEST_ENABLED,
                    default=data.get(CONF_HA_ERRORS_DIGEST_ENABLED, DEFAULT_HA_ERRORS_DIGEST_ENABLED),
                ): bool,
                vol.Optional(
                    CONF_HA_ERRORS_DIGEST_INTERVAL_SECONDS,
                    default=data.get(
                        CONF_HA_ERRORS_DIGEST_INTERVAL_SECONDS,
                        DEFAULT_HA_ERRORS_DIGEST_INTERVAL_SECONDS,
                    ),
                ): int,
                vol.Optional(
                    CONF_HA_ERRORS_DIGEST_MAX_LINES,
                    default=data.get(
                        CONF_HA_ERRORS_DIGEST_MAX_LINES,
                        DEFAULT_HA_ERRORS_DIGEST_MAX_LINES,
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

                # User Preference Module (Multi-user learning)
                vol.Optional(
                    CONF_USER_PREFERENCE_ENABLED,
                    default=data.get(CONF_USER_PREFERENCE_ENABLED, DEFAULT_USER_PREFERENCE_ENABLED),
                ): bool,
                vol.Optional(
                    CONF_TRACKED_USERS,
                    default=_as_csv(data.get(CONF_TRACKED_USERS, DEFAULT_TRACKED_USERS)),
                ): str,
                vol.Optional(
                    CONF_PRIMARY_USER,
                    default=data.get(CONF_PRIMARY_USER, DEFAULT_PRIMARY_USER or ""),
                ): str,
                vol.Optional(
                    CONF_USER_LEARNING_MODE,
                    default=data.get(CONF_USER_LEARNING_MODE, DEFAULT_USER_LEARNING_MODE),
                ): vol.In(USER_LEARNING_MODES),

                # Multi-User Preference Learning (MUPL) Module v0.8.0
                vol.Optional(
                    CONF_MUPL_ENABLED,
                    default=data.get(CONF_MUPL_ENABLED, DEFAULT_MUPL_ENABLED),
                ): bool,
                vol.Optional(
                    CONF_MUPL_PRIVACY_MODE,
                    default=data.get(CONF_MUPL_PRIVACY_MODE, DEFAULT_MUPL_PRIVACY_MODE),
                ): vol.In(MUPL_PRIVACY_MODES),
                vol.Optional(
                    CONF_MUPL_MIN_INTERACTIONS,
                    default=data.get(CONF_MUPL_MIN_INTERACTIONS, DEFAULT_MUPL_MIN_INTERACTIONS),
                ): int,
                vol.Optional(
                    CONF_MUPL_RETENTION_DAYS,
                    default=data.get(CONF_MUPL_RETENTION_DAYS, DEFAULT_MUPL_RETENTION_DAYS),
                ): int,
            }
        )

        return self.async_show_form(step_id="settings", data_schema=schema)

    async def async_step_habitus_zones(self, user_input: dict | None = None) -> FlowResult:
        return self.async_show_menu(
            step_id="habitus_zones",
            menu_options=[
                "create_zone",
                "edit_zone",
                "delete_zone",
                "generate_dashboard",
                "publish_dashboard",
                "bulk_edit",
                "back",
            ],
        )

    async def async_step_back(self, user_input: dict | None = None) -> FlowResult:
        return await self.async_step_init()

    async def async_step_create_zone(self, user_input: dict | None = None) -> FlowResult:
        return await self._async_step_zone_form(mode="create", user_input=user_input)

    async def async_step_edit_zone(self, user_input: dict | None = None) -> FlowResult:
        # DEPRECATED: v1 - prefer v2
        # from .habitus_zones_store import async_get_zones
        from .habitus_zones_store_v2 import async_get_zones_v2

        zones = await async_get_zones_v2(self.hass, self._entry.entry_id)
        ids = [z.zone_id for z in zones]
        if not ids:
            return self.async_abort(reason="no_zones")

        if user_input is None:
            schema = vol.Schema({vol.Required("zone_id"): vol.In(ids)})
            return self.async_show_form(step_id="edit_zone", data_schema=schema)

        zid = str(user_input.get("zone_id", ""))
        return await self._async_step_zone_form(mode="edit", user_input=None, zone_id=zid)

    async def async_step_delete_zone(self, user_input: dict | None = None) -> FlowResult:
        # DEPRECATED: v1 - prefer v2
        # from .habitus_zones_store import async_get_zones, async_set_zones
        from .habitus_zones_store_v2 import async_get_zones_v2, async_set_zones_v2

        zones = await async_get_zones_v2(self.hass, self._entry.entry_id)
        ids = [z.zone_id for z in zones]
        if not ids:
            return self.async_abort(reason="no_zones")

        if user_input is None:
            schema = vol.Schema({vol.Required("zone_id"): vol.In(ids)})
            return self.async_show_form(step_id="delete_zone", data_schema=schema)

        zid = str(user_input.get("zone_id", ""))
        remain = [z for z in zones if z.zone_id != zid]
        await async_set_zones_v2(self.hass, self._entry.entry_id, remain)
        return await self.async_step_habitus_zones()

    async def async_step_bulk_edit(self, user_input: dict | None = None) -> FlowResult:
        """Bulk editor to paste YAML/JSON (no 255-char limit) with validation."""
        from homeassistant.helpers import selector
        import yaml
        import json

        # DEPRECATED: v1 - prefer v2
        # from .habitus_zones_store import async_get_zones, async_set_zones_from_raw
        from .habitus_zones_store_v2 import async_get_zones_v2, async_set_zones_v2_from_raw

        zones = await async_get_zones_v2(self.hass, self._entry.entry_id)
        current = []
        for z in zones:
            # UX: if a zone has structured `entities`, prefer emitting that only.
            # Emitting both `entity_ids` + `entities` leads to confusion and duplicates.
            item = {"id": z.zone_id, "name": z.name}
            if isinstance(getattr(z, "entities", None), dict) and z.entities:
                item["entities"] = z.entities
            else:
                item["entity_ids"] = z.entity_ids
            current.append(item)

        if user_input is not None:
            raw_text = str(user_input.get("zones") or "").strip()
            if not raw_text:
                raw_text = "[]"

            try:
                try:
                    raw = json.loads(raw_text)
                except Exception:  # noqa: BLE001
                    raw = yaml.safe_load(raw_text)

                await async_set_zones_v2_from_raw(self.hass, self._entry.entry_id, raw)
            except Exception as err:  # noqa: BLE001
                return self.async_show_form(
                    step_id="bulk_edit",
                    data_schema=vol.Schema(
                        {
                            vol.Required(
                                "zones",
                                default=raw_text,
                            ): selector.TextSelector(
                                selector.TextSelectorConfig(multiline=True)
                            )
                        }
                    ),
                    errors={"base": "invalid_json"},
                    description_placeholders={"hint": f"Parse/validation error: {err}"},
                )

            return await self.async_step_habitus_zones()

        default = yaml.safe_dump(current, allow_unicode=True, sort_keys=False)
        schema = vol.Schema(
            {
                vol.Required("zones", default=default): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=True)
                )
            }
        )

        return self.async_show_form(
            step_id="bulk_edit",
            data_schema=schema,
            description_placeholders={
                "hint": (
                    "Paste a YAML/JSON list of zones (or {zones:[...]}). Each zone requires motion/presence + light.\n\n"
                    "Optional: use a categorized structure via `entities:` (role -> list of entity_ids), e.g.\n"
                    "- entities: {motion: [...], lights: [...], brightness: [...], heating: [...], humidity: [...], co2: [...], cover: [...], door: [...], window: [...], lock: [...], media: [...], other: [...]}"
                ),
            },
        )

    async def async_step_generate_dashboard(self, user_input: dict | None = None) -> FlowResult:
        """Generate Lovelace dashboard YAML for all Habitus zones."""
        from .habitus_dashboard import async_generate_habitus_zones_dashboard

        if user_input is not None:
            try:
                path = await async_generate_habitus_zones_dashboard(self.hass, self._entry.entry_id)
                return self.async_abort(
                    reason="dashboard_generated",
                    description_placeholders={"path": str(path)},
                )
            except Exception as err:  # noqa: BLE001
                return self.async_show_form(
                    step_id="generate_dashboard",
                    errors={"base": "generation_failed"},
                    description_placeholders={"error": str(err)},
                )

        schema = vol.Schema({vol.Optional("confirm", default=True): bool})
        return self.async_show_form(
            step_id="generate_dashboard",
            data_schema=schema,
            description_placeholders={
                "description": "Creates a Lovelace YAML dashboard file for all Habitus zones. "
                "The file is saved in the `ai_home_copilot/` configuration folder."
            },
        )

    async def async_step_publish_dashboard(self, user_input: dict | None = None) -> FlowResult:
        """Publish the latest generated dashboard to www folder."""
        from .habitus_dashboard import async_publish_last_habitus_dashboard

        if user_input is not None:
            try:
                url = await async_publish_last_habitus_dashboard(self.hass)
                return self.async_abort(
                    reason="dashboard_published",
                    description_placeholders={"url": url},
                )
            except FileNotFoundError:
                return self.async_show_form(
                    step_id="publish_dashboard",
                    errors={"base": "no_dashboard_generated"},
                    description_placeholders={
                        "hint": "Generate a dashboard first using 'Generate dashboard YAML'."
                    },
                )
            except Exception as err:  # noqa: BLE001
                return self.async_show_form(
                    step_id="publish_dashboard",
                    errors={"base": "publish_failed"},
                    description_placeholders={"error": str(err)},
                )

        schema = vol.Schema({vol.Optional("confirm", default=True): bool})
        return self.async_show_form(
            step_id="publish_dashboard",
            data_schema=schema,
            description_placeholders={
                "description": "Copies the latest generated dashboard to the `www/ai_home_copilot/` folder "
                "for easy download. This creates a stable URL for the dashboard YAML."
            },
        )

    async def _async_step_zone_form(
        self,
        *,
        mode: str,
        user_input: dict | None,
        zone_id: str | None = None,
    ) -> FlowResult:
        from homeassistant.helpers import selector
        # DEPRECATED: v1 - prefer v2
        # from .habitus_zones_store import HabitusZone, async_get_zones, async_set_zones
        from .habitus_zones_store_v2 import HabitusZoneV2, async_get_zones_v2, async_set_zones_v2

        zones = await async_get_zones_v2(self.hass, self._entry.entry_id)
        existing = {z.zone_id: z for z in zones}

        if zone_id and zone_id in existing:
            z = existing[zone_id]
        else:
            # v2: HabitusZoneV2 uses tuples instead of lists
            z = HabitusZoneV2(zone_id="", name="", entity_ids=(), entities=None)

        if user_input is not None:
            zid = str(user_input.get("zone_id") or "").strip()
            name = str(user_input.get("name") or zid).strip()
            motion = str(user_input.get("motion_entity_id") or "").strip()
            lights = user_input.get("light_entity_ids") or []
            optional = user_input.get("optional_entity_ids") or []

            if not isinstance(lights, list):
                lights = [lights]
            if not isinstance(optional, list):
                optional = [optional]

            entity_ids = [motion] + [str(x).strip() for x in lights] + [str(x).strip() for x in optional]
            entity_ids = [e for e in entity_ids if e]

            # De-dupe
            seen = set()
            uniq = []
            for e in entity_ids:
                if e in seen:
                    continue
                seen.add(e)
                uniq.append(e)

            ent_map = {
                "motion": [motion] if motion else [],
                "lights": [str(x).strip() for x in lights if str(x).strip()],
                "other": [str(x).strip() for x in optional if str(x).strip()],
            }
            # drop empty roles
            ent_map = {k: v for k, v in ent_map.items() if v}

            new_zone = HabitusZoneV2(zone_id=zid, name=name or zid, entity_ids=tuple(uniq), entities=ent_map or None)

            # Replace / insert
            new_list = [zz for zz in zones if zz.zone_id != zid]
            new_list.append(new_zone)
            # Persist (store enforces requirements)
            await async_set_zones_v2(self.hass, self._entry.entry_id, new_list)

            return await self.async_step_habitus_zones()

        default_motion = None
        default_lights: list[str] = []
        default_optional: list[str] = []

        # Best-effort prefill from existing zone.
        ent_map = getattr(z, "entities", None)
        if isinstance(ent_map, dict):
            motion_list = ent_map.get("motion") or []
            lights_list = ent_map.get("lights") or []
            other_list = ent_map.get("other") or []

            if motion_list:
                default_motion = str(motion_list[0])
            default_lights = [str(x) for x in lights_list]
            default_optional = [str(x) for x in other_list]
        else:
            for eid in z.entity_ids:
                if eid.startswith("light."):
                    default_lights.append(eid)
                elif eid.startswith("binary_sensor.") and default_motion is None:
                    default_motion = eid
                else:
                    default_optional.append(eid)

        schema = vol.Schema(
            {
                vol.Required("zone_id", default=(z.zone_id if mode == "edit" else "")): str,
                vol.Optional("name", default=(z.name if z.name else "")): str,
                vol.Required(
                    "motion_entity_id",
                    default=default_motion or "",
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["binary_sensor", "sensor"], multiple=False)
                ),
                vol.Required(
                    "light_entity_ids",
                    default=default_lights,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="light", multiple=True)
                ),
                vol.Optional(
                    "optional_entity_ids",
                    default=default_optional,
                ): selector.EntitySelector(selector.EntitySelectorConfig(multiple=True)),
            }
        )

        step_id = "create_zone" if mode == "create" else "edit_zone_form"
        return self.async_show_form(step_id=step_id, data_schema=schema)

    async def async_step_neurons(self, user_input: dict | None = None) -> FlowResult:
        """Configure neural system entities."""
        if user_input is not None:
            # Normalize entity lists
            context_csv = user_input.get(CONF_NEURON_CONTEXT_ENTITIES, "")
            if isinstance(context_csv, str):
                user_input[CONF_NEURON_CONTEXT_ENTITIES] = _parse_csv(context_csv)
            
            state_csv = user_input.get(CONF_NEURON_STATE_ENTITIES, "")
            if isinstance(state_csv, str):
                user_input[CONF_NEURON_STATE_ENTITIES] = _parse_csv(state_csv)
            
            mood_csv = user_input.get(CONF_NEURON_MOOD_ENTITIES, "")
            if isinstance(mood_csv, str):
                user_input[CONF_NEURON_MOOD_ENTITIES] = _parse_csv(mood_csv)
            
            return self.async_create_entry(title="", data=user_input)
        
        data = {**self._entry.data, **self._entry.options}
        
        schema = vol.Schema({
            vol.Optional(
                CONF_NEURON_ENABLED,
                default=data.get(CONF_NEURON_ENABLED, DEFAULT_NEURON_ENABLED),
            ): bool,
            vol.Optional(
                CONF_NEURON_EVALUATION_INTERVAL,
                default=data.get(CONF_NEURON_EVALUATION_INTERVAL, DEFAULT_NEURON_EVALUATION_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
            vol.Optional(
                CONF_NEURON_CONTEXT_ENTITIES,
                default=_as_csv(data.get(CONF_NEURON_CONTEXT_ENTITIES, DEFAULT_NEURON_CONTEXT_ENTITIES)),
            ): str,  # Comma-separated context entity IDs
            vol.Optional(
                CONF_NEURON_STATE_ENTITIES,
                default=_as_csv(data.get(CONF_NEURON_STATE_ENTITIES, DEFAULT_NEURON_STATE_ENTITIES)),
            ): str,  # Comma-separated state entity IDs
            vol.Optional(
                CONF_NEURON_MOOD_ENTITIES,
                default=_as_csv(data.get(CONF_NEURON_MOOD_ENTITIES, DEFAULT_NEURON_MOOD_ENTITIES)),
            ): str,  # Comma-separated mood entity IDs
        })
        
        return self.async_show_form(step_id="neurons", data_schema=schema)


# Options flow is provided via ConfigFlow.async_get_options_flow
