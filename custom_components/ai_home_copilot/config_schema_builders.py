"""Schema builder functions for the settings options flow."""
from __future__ import annotations

import voluptuous as vol

from .config_helpers import as_csv
from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_TOKEN,
    CONF_TEST_LIGHT,
    CONF_WEBHOOK_URL,
    CONF_MEDIA_MUSIC_PLAYERS,
    CONF_MEDIA_TV_PLAYERS,
    CONF_SUGGESTION_SEED_ENTITIES,
    CONF_SEED_ALLOWED_DOMAINS,
    CONF_SEED_BLOCKED_DOMAINS,
    CONF_SEED_MAX_OFFERS_PER_HOUR,
    CONF_SEED_MIN_SECONDS_BETWEEN_OFFERS,
    CONF_SEED_MAX_OFFERS_PER_UPDATE,
    CONF_WATCHDOG_ENABLED,
    CONF_WATCHDOG_INTERVAL_SECONDS,
    CONF_ENABLE_USER_PREFERENCES,
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
    CONF_PILOTSUITE_SHOW_SAFETY_BACKUP_BUTTONS,
    CONF_PILOTSUITE_SHOW_DEV_SURFACE_BUTTONS,
    CONF_PILOTSUITE_SHOW_GRAPH_BRIDGE_BUTTONS,
    CONF_HA_ERRORS_DIGEST_ENABLED,
    CONF_HA_ERRORS_DIGEST_INTERVAL_SECONDS,
    CONF_HA_ERRORS_DIGEST_MAX_LINES,
    CONF_DEVLOG_PUSH_ENABLED,
    CONF_DEVLOG_PUSH_INTERVAL_SECONDS,
    CONF_DEVLOG_PUSH_PATH,
    CONF_DEVLOG_PUSH_MAX_LINES,
    CONF_DEVLOG_PUSH_MAX_CHARS,
    CONF_USER_PREFERENCE_ENABLED,
    CONF_TRACKED_USERS,
    CONF_PRIMARY_USER,
    CONF_USER_LEARNING_MODE,
    CONF_MUPL_ENABLED,
    CONF_MUPL_PRIVACY_MODE,
    CONF_MUPL_MIN_INTERACTIONS,
    CONF_MUPL_RETENTION_DAYS,
    CONF_NEURON_ENABLED,
    CONF_NEURON_EVALUATION_INTERVAL,
    CONF_NEURON_CONTEXT_ENTITIES,
    CONF_NEURON_STATE_ENTITIES,
    CONF_NEURON_MOOD_ENTITIES,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_MEDIA_MUSIC_PLAYERS,
    DEFAULT_MEDIA_TV_PLAYERS,
    DEFAULT_SUGGESTION_SEED_ENTITIES,
    DEFAULT_SEED_ALLOWED_DOMAINS,
    DEFAULT_SEED_BLOCKED_DOMAINS,
    DEFAULT_SEED_MAX_OFFERS_PER_HOUR,
    DEFAULT_SEED_MIN_SECONDS_BETWEEN_OFFERS,
    DEFAULT_SEED_MAX_OFFERS_PER_UPDATE,
    DEFAULT_WATCHDOG_ENABLED,
    DEFAULT_WATCHDOG_INTERVAL_SECONDS,
    DEFAULT_ENABLE_USER_PREFERENCES,
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
    DEFAULT_PILOTSUITE_SHOW_SAFETY_BACKUP_BUTTONS,
    DEFAULT_PILOTSUITE_SHOW_DEV_SURFACE_BUTTONS,
    DEFAULT_PILOTSUITE_SHOW_GRAPH_BRIDGE_BUTTONS,
    DEFAULT_HA_ERRORS_DIGEST_ENABLED,
    DEFAULT_HA_ERRORS_DIGEST_INTERVAL_SECONDS,
    DEFAULT_HA_ERRORS_DIGEST_MAX_LINES,
    DEFAULT_DEVLOG_PUSH_ENABLED,
    DEFAULT_DEVLOG_PUSH_INTERVAL_SECONDS,
    DEFAULT_DEVLOG_PUSH_PATH,
    DEFAULT_DEVLOG_PUSH_MAX_LINES,
    DEFAULT_DEVLOG_PUSH_MAX_CHARS,
    DEFAULT_USER_PREFERENCE_ENABLED,
    DEFAULT_TRACKED_USERS,
    DEFAULT_PRIMARY_USER,
    DEFAULT_USER_LEARNING_MODE,
    USER_LEARNING_MODES,
    DEFAULT_MUPL_ENABLED,
    DEFAULT_MUPL_PRIVACY_MODE,
    DEFAULT_MUPL_MIN_INTERACTIONS,
    DEFAULT_MUPL_RETENTION_DAYS,
    MUPL_PRIVACY_MODES,
    DEFAULT_NEURON_ENABLED,
    DEFAULT_NEURON_EVALUATION_INTERVAL,
    DEFAULT_NEURON_CONTEXT_ENTITIES,
    DEFAULT_NEURON_STATE_ENTITIES,
    DEFAULT_NEURON_MOOD_ENTITIES,
    CONF_WASTE_ENABLED,
    CONF_WASTE_ENTITIES,
    CONF_WASTE_TTS_ENABLED,
    CONF_WASTE_TTS_ENTITY,
    CONF_WASTE_REMINDER_EVENING_HOUR,
    CONF_WASTE_REMINDER_MORNING_HOUR,
    DEFAULT_WASTE_ENABLED,
    DEFAULT_WASTE_ENTITIES,
    DEFAULT_WASTE_TTS_ENABLED,
    DEFAULT_WASTE_TTS_ENTITY,
    DEFAULT_WASTE_REMINDER_EVENING_HOUR,
    DEFAULT_WASTE_REMINDER_MORNING_HOUR,
    CONF_BIRTHDAY_ENABLED,
    CONF_BIRTHDAY_CALENDAR_ENTITIES,
    CONF_BIRTHDAY_LOOKAHEAD_DAYS,
    CONF_BIRTHDAY_TTS_ENABLED,
    CONF_BIRTHDAY_TTS_ENTITY,
    CONF_BIRTHDAY_REMINDER_HOUR,
    DEFAULT_BIRTHDAY_ENABLED,
    DEFAULT_BIRTHDAY_CALENDAR_ENTITIES,
    DEFAULT_BIRTHDAY_LOOKAHEAD_DAYS,
    DEFAULT_BIRTHDAY_TTS_ENABLED,
    DEFAULT_BIRTHDAY_TTS_ENTITY,
    DEFAULT_BIRTHDAY_REMINDER_HOUR,
)


def build_network_schema(data: dict, webhook_url: str, token_hint: str) -> dict:
    """Build schema fields for network settings (HOST, PORT, TOKEN)."""
    return {
        vol.Optional(CONF_WEBHOOK_URL, default=webhook_url): str,
        vol.Required(CONF_HOST, default=data.get(CONF_HOST, DEFAULT_HOST)): str,
        vol.Required(CONF_PORT, default=data.get(CONF_PORT, DEFAULT_PORT)): int,
        vol.Optional(CONF_TOKEN, default="", description={"suggested_value": token_hint}): str,
        vol.Optional("_clear_token"): bool,
        vol.Optional(CONF_TEST_LIGHT, default=data.get(CONF_TEST_LIGHT, "")): str,
    }


def build_media_schema(data: dict) -> dict:
    """Build schema fields for media player settings."""
    return {
        vol.Optional(
            CONF_MEDIA_MUSIC_PLAYERS,
            default=as_csv(data.get(CONF_MEDIA_MUSIC_PLAYERS, DEFAULT_MEDIA_MUSIC_PLAYERS)),
        ): str,
        vol.Optional(
            CONF_MEDIA_TV_PLAYERS,
            default=as_csv(data.get(CONF_MEDIA_TV_PLAYERS, DEFAULT_MEDIA_TV_PLAYERS)),
        ): str,
    }


def build_seed_schema(data: dict) -> dict:
    """Build schema fields for suggestion seed settings."""
    return {
        vol.Optional(
            CONF_SUGGESTION_SEED_ENTITIES,
            default=as_csv(data.get(CONF_SUGGESTION_SEED_ENTITIES, DEFAULT_SUGGESTION_SEED_ENTITIES)),
        ): str,
        vol.Optional(
            CONF_SEED_ALLOWED_DOMAINS,
            default=as_csv(data.get(CONF_SEED_ALLOWED_DOMAINS, DEFAULT_SEED_ALLOWED_DOMAINS)),
        ): str,
        vol.Optional(
            CONF_SEED_BLOCKED_DOMAINS,
            default=as_csv(data.get(CONF_SEED_BLOCKED_DOMAINS, DEFAULT_SEED_BLOCKED_DOMAINS)),
        ): str,
        vol.Optional(
            CONF_SEED_MAX_OFFERS_PER_HOUR,
            default=data.get(CONF_SEED_MAX_OFFERS_PER_HOUR, DEFAULT_SEED_MAX_OFFERS_PER_HOUR),
        ): int,
        vol.Optional(
            CONF_SEED_MIN_SECONDS_BETWEEN_OFFERS,
            default=data.get(CONF_SEED_MIN_SECONDS_BETWEEN_OFFERS, DEFAULT_SEED_MIN_SECONDS_BETWEEN_OFFERS),
        ): int,
        vol.Optional(
            CONF_SEED_MAX_OFFERS_PER_UPDATE,
            default=data.get(CONF_SEED_MAX_OFFERS_PER_UPDATE, DEFAULT_SEED_MAX_OFFERS_PER_UPDATE),
        ): int,
    }


def build_watchdog_schema(data: dict) -> dict:
    """Build schema fields for watchdog settings."""
    return {
        vol.Optional(
            CONF_WATCHDOG_ENABLED,
            default=data.get(CONF_WATCHDOG_ENABLED, DEFAULT_WATCHDOG_ENABLED),
        ): bool,
        vol.Optional(
            CONF_WATCHDOG_INTERVAL_SECONDS,
            default=data.get(CONF_WATCHDOG_INTERVAL_SECONDS, DEFAULT_WATCHDOG_INTERVAL_SECONDS),
        ): int,
        vol.Optional(
            CONF_ENABLE_USER_PREFERENCES,
            default=data.get(CONF_ENABLE_USER_PREFERENCES, DEFAULT_ENABLE_USER_PREFERENCES),
        ): bool,
    }


def build_forwarder_schema(data: dict) -> dict:
    """Build schema fields for events forwarder settings."""
    return {
        vol.Optional(
            CONF_EVENTS_FORWARDER_ENABLED,
            default=data.get(CONF_EVENTS_FORWARDER_ENABLED, DEFAULT_EVENTS_FORWARDER_ENABLED),
        ): bool,
        vol.Optional(
            CONF_EVENTS_FORWARDER_FLUSH_INTERVAL_SECONDS,
            default=data.get(CONF_EVENTS_FORWARDER_FLUSH_INTERVAL_SECONDS, DEFAULT_EVENTS_FORWARDER_FLUSH_INTERVAL_SECONDS),
        ): int,
        vol.Optional(
            CONF_EVENTS_FORWARDER_MAX_BATCH,
            default=data.get(CONF_EVENTS_FORWARDER_MAX_BATCH, DEFAULT_EVENTS_FORWARDER_MAX_BATCH),
        ): int,
        vol.Optional(
            CONF_EVENTS_FORWARDER_FORWARD_CALL_SERVICE,
            default=data.get(CONF_EVENTS_FORWARDER_FORWARD_CALL_SERVICE, DEFAULT_EVENTS_FORWARDER_FORWARD_CALL_SERVICE),
        ): bool,
        vol.Optional(
            CONF_EVENTS_FORWARDER_IDEMPOTENCY_TTL_SECONDS,
            default=data.get(CONF_EVENTS_FORWARDER_IDEMPOTENCY_TTL_SECONDS, DEFAULT_EVENTS_FORWARDER_IDEMPOTENCY_TTL_SECONDS),
        ): int,
        vol.Optional(
            CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_ENABLED,
            default=data.get(CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_ENABLED, DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_ENABLED),
        ): bool,
        vol.Optional(
            CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_MAX_SIZE,
            default=data.get(CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_MAX_SIZE, DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_MAX_SIZE),
        ): int,
        vol.Optional(
            CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_FLUSH_INTERVAL_SECONDS,
            default=data.get(CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_FLUSH_INTERVAL_SECONDS, DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_FLUSH_INTERVAL_SECONDS),
        ): int,
        vol.Optional(
            CONF_EVENTS_FORWARDER_INCLUDE_HABITUS_ZONES,
            default=data.get(CONF_EVENTS_FORWARDER_INCLUDE_HABITUS_ZONES, DEFAULT_EVENTS_FORWARDER_INCLUDE_HABITUS_ZONES),
        ): bool,
        vol.Optional(
            CONF_EVENTS_FORWARDER_INCLUDE_MEDIA_PLAYERS,
            default=data.get(CONF_EVENTS_FORWARDER_INCLUDE_MEDIA_PLAYERS, DEFAULT_EVENTS_FORWARDER_INCLUDE_MEDIA_PLAYERS),
        ): bool,
        vol.Optional(
            CONF_EVENTS_FORWARDER_ADDITIONAL_ENTITIES,
            default=as_csv(data.get(CONF_EVENTS_FORWARDER_ADDITIONAL_ENTITIES, DEFAULT_EVENTS_FORWARDER_ADDITIONAL_ENTITIES)),
        ): str,
    }


def build_pilotsuite_schema(data: dict) -> dict:
    """Build schema fields for PilotSuite UX settings."""
    return {
        vol.Optional(
            CONF_PILOTSUITE_SHOW_SAFETY_BACKUP_BUTTONS,
            default=data.get(CONF_PILOTSUITE_SHOW_SAFETY_BACKUP_BUTTONS, DEFAULT_PILOTSUITE_SHOW_SAFETY_BACKUP_BUTTONS),
        ): bool,
        vol.Optional(
            CONF_PILOTSUITE_SHOW_DEV_SURFACE_BUTTONS,
            default=data.get(CONF_PILOTSUITE_SHOW_DEV_SURFACE_BUTTONS, DEFAULT_PILOTSUITE_SHOW_DEV_SURFACE_BUTTONS),
        ): bool,
        vol.Optional(
            CONF_PILOTSUITE_SHOW_GRAPH_BRIDGE_BUTTONS,
            default=data.get(CONF_PILOTSUITE_SHOW_GRAPH_BRIDGE_BUTTONS, DEFAULT_PILOTSUITE_SHOW_GRAPH_BRIDGE_BUTTONS),
        ): bool,
    }


def build_ha_errors_schema(data: dict) -> dict:
    """Build schema fields for HA errors digest settings."""
    return {
        vol.Optional(
            CONF_HA_ERRORS_DIGEST_ENABLED,
            default=data.get(CONF_HA_ERRORS_DIGEST_ENABLED, DEFAULT_HA_ERRORS_DIGEST_ENABLED),
        ): bool,
        vol.Optional(
            CONF_HA_ERRORS_DIGEST_INTERVAL_SECONDS,
            default=data.get(CONF_HA_ERRORS_DIGEST_INTERVAL_SECONDS, DEFAULT_HA_ERRORS_DIGEST_INTERVAL_SECONDS),
        ): int,
        vol.Optional(
            CONF_HA_ERRORS_DIGEST_MAX_LINES,
            default=data.get(CONF_HA_ERRORS_DIGEST_MAX_LINES, DEFAULT_HA_ERRORS_DIGEST_MAX_LINES),
        ): int,
    }


def build_devlog_schema(data: dict) -> dict:
    """Build schema fields for devlog push settings."""
    return {
        vol.Optional(
            CONF_DEVLOG_PUSH_ENABLED,
            default=data.get(CONF_DEVLOG_PUSH_ENABLED, DEFAULT_DEVLOG_PUSH_ENABLED),
        ): bool,
        vol.Optional(
            CONF_DEVLOG_PUSH_INTERVAL_SECONDS,
            default=data.get(CONF_DEVLOG_PUSH_INTERVAL_SECONDS, DEFAULT_DEVLOG_PUSH_INTERVAL_SECONDS),
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


def build_user_prefs_schema(data: dict) -> dict:
    """Build schema fields for user preference settings."""
    return {
        vol.Optional(
            CONF_USER_PREFERENCE_ENABLED,
            default=data.get(CONF_USER_PREFERENCE_ENABLED, DEFAULT_USER_PREFERENCE_ENABLED),
        ): bool,
        vol.Optional(
            CONF_TRACKED_USERS,
            default=as_csv(data.get(CONF_TRACKED_USERS, DEFAULT_TRACKED_USERS)),
        ): str,
        vol.Optional(
            CONF_PRIMARY_USER,
            default=data.get(CONF_PRIMARY_USER, DEFAULT_PRIMARY_USER or ""),
        ): str,
        vol.Optional(
            CONF_USER_LEARNING_MODE,
            default=data.get(CONF_USER_LEARNING_MODE, DEFAULT_USER_LEARNING_MODE),
        ): vol.In(USER_LEARNING_MODES),
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


def build_neuron_schema(data: dict) -> dict:
    """Build schema fields for neural system settings."""
    return {
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
            default=as_csv(data.get(CONF_NEURON_CONTEXT_ENTITIES, DEFAULT_NEURON_CONTEXT_ENTITIES)),
        ): str,
        vol.Optional(
            CONF_NEURON_STATE_ENTITIES,
            default=as_csv(data.get(CONF_NEURON_STATE_ENTITIES, DEFAULT_NEURON_STATE_ENTITIES)),
        ): str,
        vol.Optional(
            CONF_NEURON_MOOD_ENTITIES,
            default=as_csv(data.get(CONF_NEURON_MOOD_ENTITIES, DEFAULT_NEURON_MOOD_ENTITIES)),
        ): str,
    }


def build_waste_schema(data: dict) -> dict:
    """Build schema fields for waste collection reminder settings."""
    return {
        vol.Optional(
            CONF_WASTE_ENABLED,
            default=data.get(CONF_WASTE_ENABLED, DEFAULT_WASTE_ENABLED),
        ): bool,
        vol.Optional(
            CONF_WASTE_ENTITIES,
            default=as_csv(data.get(CONF_WASTE_ENTITIES, DEFAULT_WASTE_ENTITIES)),
        ): str,
        vol.Optional(
            CONF_WASTE_TTS_ENABLED,
            default=data.get(CONF_WASTE_TTS_ENABLED, DEFAULT_WASTE_TTS_ENABLED),
        ): bool,
        vol.Optional(
            CONF_WASTE_TTS_ENTITY,
            default=data.get(CONF_WASTE_TTS_ENTITY, DEFAULT_WASTE_TTS_ENTITY),
        ): str,
        vol.Optional(
            CONF_WASTE_REMINDER_EVENING_HOUR,
            default=data.get(CONF_WASTE_REMINDER_EVENING_HOUR, DEFAULT_WASTE_REMINDER_EVENING_HOUR),
        ): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
        vol.Optional(
            CONF_WASTE_REMINDER_MORNING_HOUR,
            default=data.get(CONF_WASTE_REMINDER_MORNING_HOUR, DEFAULT_WASTE_REMINDER_MORNING_HOUR),
        ): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
    }


def build_birthday_schema(data: dict) -> dict:
    """Build schema fields for birthday reminder settings."""
    return {
        vol.Optional(
            CONF_BIRTHDAY_ENABLED,
            default=data.get(CONF_BIRTHDAY_ENABLED, DEFAULT_BIRTHDAY_ENABLED),
        ): bool,
        vol.Optional(
            CONF_BIRTHDAY_CALENDAR_ENTITIES,
            default=as_csv(data.get(CONF_BIRTHDAY_CALENDAR_ENTITIES, DEFAULT_BIRTHDAY_CALENDAR_ENTITIES)),
        ): str,
        vol.Optional(
            CONF_BIRTHDAY_LOOKAHEAD_DAYS,
            default=data.get(CONF_BIRTHDAY_LOOKAHEAD_DAYS, DEFAULT_BIRTHDAY_LOOKAHEAD_DAYS),
        ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
        vol.Optional(
            CONF_BIRTHDAY_TTS_ENABLED,
            default=data.get(CONF_BIRTHDAY_TTS_ENABLED, DEFAULT_BIRTHDAY_TTS_ENABLED),
        ): bool,
        vol.Optional(
            CONF_BIRTHDAY_TTS_ENTITY,
            default=data.get(CONF_BIRTHDAY_TTS_ENTITY, DEFAULT_BIRTHDAY_TTS_ENTITY),
        ): str,
        vol.Optional(
            CONF_BIRTHDAY_REMINDER_HOUR,
            default=data.get(CONF_BIRTHDAY_REMINDER_HOUR, DEFAULT_BIRTHDAY_REMINDER_HOUR),
        ): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
    }


def build_settings_schema(data: dict, webhook_url: str, token_hint: str) -> vol.Schema:
    """Build the complete settings schema from all builder functions."""
    fields: dict = {}
    fields.update(build_network_schema(data, webhook_url, token_hint))
    fields.update(build_media_schema(data))
    fields.update(build_seed_schema(data))
    fields.update(build_watchdog_schema(data))
    fields.update(build_forwarder_schema(data))
    fields.update(build_pilotsuite_schema(data))
    fields.update(build_ha_errors_schema(data))
    fields.update(build_devlog_schema(data))
    fields.update(build_user_prefs_schema(data))
    fields.update(build_waste_schema(data))
    fields.update(build_birthday_schema(data))
    return vol.Schema(fields)
