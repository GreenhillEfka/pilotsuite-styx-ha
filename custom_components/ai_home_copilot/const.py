DOMAIN = "ai_home_copilot"

# Internal hass.data keys (namespaced to avoid entry_id collisions).
DATA_CORE = "_core"
DATA_RUNTIME = "runtime"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_TOKEN = "token"
CONF_TEST_LIGHT = "test_light_entity_id"
CONF_WEBHOOK_ID = "webhook_id"
CONF_WEBHOOK_URL = "webhook_url"
CONF_WATCHDOG_ENABLED = "watchdog_enabled"
CONF_WATCHDOG_INTERVAL_SECONDS = "watchdog_interval_seconds"
CONF_ENABLE_USER_PREFERENCES = "enable_user_preferences"

# MediaContext (read-only signals)
CONF_MEDIA_MUSIC_PLAYERS = "media_music_players"
CONF_MEDIA_TV_PLAYERS = "media_tv_players"

# MediaContext v2 (zone mapping + volume control)
CONF_MEDIA_CONTEXT_V2_ENABLED = "media_context_v2_enabled"

# Dev/Debug: push sanitized HA log snippets to Copilot-Core (opt-in).
CONF_DEVLOG_PUSH_ENABLED = "devlog_push_enabled"

# Core API v1: capabilities ping + HA->Core event forwarder (opt-in).
CONF_EVENTS_FORWARDER_ENABLED = "events_forwarder_enabled"
CONF_EVENTS_FORWARDER_FLUSH_INTERVAL_SECONDS = "events_forwarder_flush_interval_seconds"
CONF_EVENTS_FORWARDER_MAX_BATCH = "events_forwarder_max_batch"
CONF_EVENTS_FORWARDER_FORWARD_CALL_SERVICE = "events_forwarder_forward_call_service"
CONF_EVENTS_FORWARDER_IDEMPOTENCY_TTL_SECONDS = "events_forwarder_idempotency_ttl_seconds"

# Core API v1: events forwarder persistent queue (optional).
CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_ENABLED = "events_forwarder_persistent_queue_enabled"
CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_MAX_SIZE = "events_forwarder_persistent_queue_max_size"
CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_FLUSH_INTERVAL_SECONDS = (
    "events_forwarder_persistent_queue_flush_interval_seconds"
)

# Core API v1: events forwarder entity allowlist
CONF_EVENTS_FORWARDER_INCLUDE_HABITUS_ZONES = "events_forwarder_include_habitus_zones"
CONF_EVENTS_FORWARDER_INCLUDE_MEDIA_PLAYERS = "events_forwarder_include_media_players"
CONF_EVENTS_FORWARDER_ADDITIONAL_ENTITIES = "events_forwarder_additional_entities"

# HA log digest (local): surface relevant errors/warnings in HA (opt-in).
CONF_HA_ERRORS_DIGEST_ENABLED = "ha_errors_digest_enabled"

# Debug Level: off, light (errors only), full (all logs)
CONF_DEBUG_LEVEL = "debug_level"
DEBUG_LEVEL_OFF = "off"
DEBUG_LEVEL_LIGHT = "light"
DEBUG_LEVEL_FULL = "full"
DEBUG_LEVELS = [DEBUG_LEVEL_OFF, DEBUG_LEVEL_LIGHT, DEBUG_LEVEL_FULL]

# PilotSuite / Dashboard UX
CONF_PILOTSUITE_SHOW_SAFETY_BACKUP_BUTTONS = "pilotsuite_show_safety_backup_buttons"
CONF_PILOTSUITE_SHOW_DEV_SURFACE_BUTTONS = "pilotsuite_show_dev_surface_buttons"
CONF_PILOTSUITE_SHOW_GRAPH_BRIDGE_BUTTONS = "pilotsuite_show_graph_bridge_buttons"
CONF_HA_ERRORS_DIGEST_INTERVAL_SECONDS = "ha_errors_digest_interval_seconds"
CONF_HA_ERRORS_DIGEST_MAX_LINES = "ha_errors_digest_max_lines"
CONF_DEVLOG_PUSH_INTERVAL_SECONDS = "devlog_push_interval_seconds"
CONF_DEVLOG_PUSH_PATH = "devlog_push_path"
CONF_DEVLOG_PUSH_MAX_LINES = "devlog_push_max_lines"
CONF_DEVLOG_PUSH_MAX_CHARS = "devlog_push_max_chars"

# Optional: entities that emit LLM-generated suggestions we want to treat as "seed" candidates.
# Example: sensor.ai_automation_suggestions_openai
CONF_SUGGESTION_SEED_ENTITIES = "suggestion_seed_entities"
CONF_SEED_ALLOWED_DOMAINS = "seed_allowed_domains"
CONF_SEED_BLOCKED_DOMAINS = "seed_blocked_domains"
CONF_SEED_MAX_OFFERS_PER_HOUR = "seed_max_offers_per_hour"
CONF_SEED_MIN_SECONDS_BETWEEN_OFFERS = "seed_min_seconds_between_offers"
CONF_SEED_MAX_OFFERS_PER_UPDATE = "seed_max_offers_per_update"

# Privacy-first defaults: no personal IPs/entities shipped.
# Tip: set this to your HA host IP (LAN) or a resolvable hostname.
DEFAULT_HOST = "homeassistant.local"
DEFAULT_PORT = 8909
DEFAULT_TEST_LIGHT = ""
DEFAULT_WATCHDOG_ENABLED = False
DEFAULT_WATCHDOG_INTERVAL_SECONDS = 1800
DEFAULT_ENABLE_USER_PREFERENCES = True

DEFAULT_MEDIA_MUSIC_PLAYERS: list[str] = []
DEFAULT_MEDIA_TV_PLAYERS: list[str] = []

DEFAULT_DEVLOG_PUSH_ENABLED = False
DEFAULT_DEVLOG_PUSH_INTERVAL_SECONDS = 60
DEFAULT_DEVLOG_PUSH_PATH = "/api/v1/dev/logs"
DEFAULT_DEVLOG_PUSH_MAX_LINES = 220
DEFAULT_DEVLOG_PUSH_MAX_CHARS = 6000

DEFAULT_EVENTS_FORWARDER_ENABLED = False
DEFAULT_EVENTS_FORWARDER_FLUSH_INTERVAL_SECONDS = 5
DEFAULT_EVENTS_FORWARDER_MAX_BATCH = 50
DEFAULT_EVENTS_FORWARDER_FORWARD_CALL_SERVICE = False
DEFAULT_EVENTS_FORWARDER_IDEMPOTENCY_TTL_SECONDS = 300

DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_ENABLED = False
DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_MAX_SIZE = 500
DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_FLUSH_INTERVAL_SECONDS = 5

DEFAULT_EVENTS_FORWARDER_INCLUDE_HABITUS_ZONES = True
DEFAULT_EVENTS_FORWARDER_INCLUDE_MEDIA_PLAYERS = True
DEFAULT_EVENTS_FORWARDER_ADDITIONAL_ENTITIES: list[str] = []

DEFAULT_HA_ERRORS_DIGEST_ENABLED = False
DEFAULT_DEBUG_LEVEL = DEBUG_LEVEL_OFF

DEFAULT_PILOTSUITE_SHOW_SAFETY_BACKUP_BUTTONS = False
DEFAULT_PILOTSUITE_SHOW_DEV_SURFACE_BUTTONS = False
DEFAULT_PILOTSUITE_SHOW_GRAPH_BRIDGE_BUTTONS = False
DEFAULT_HA_ERRORS_DIGEST_INTERVAL_SECONDS = 300
DEFAULT_HA_ERRORS_DIGEST_MAX_LINES = 800

DEFAULT_SUGGESTION_SEED_ENTITIES: list[str] = []
DEFAULT_SEED_ALLOWED_DOMAINS: list[str] = []
DEFAULT_SEED_BLOCKED_DOMAINS: list[str] = []
DEFAULT_SEED_MAX_OFFERS_PER_HOUR = 10
DEFAULT_SEED_MIN_SECONDS_BETWEEN_OFFERS = 30
DEFAULT_SEED_MAX_OFFERS_PER_UPDATE = 3

HEADER_AUTH = "X-Auth-Token"

# User Preference Module (Multi-user learning)
CONF_USER_PREFERENCE_ENABLED = "user_preference_enabled"
CONF_TRACKED_USERS = "tracked_users"
CONF_PRIMARY_USER = "primary_user"
CONF_USER_LEARNING_MODE = "user_learning_mode"

USER_LEARNING_MODE_OFF = "off"
USER_LEARNING_MODE_PASSIVE = "passive"
USER_LEARNING_MODE_ACTIVE = "active"
USER_LEARNING_MODES = [USER_LEARNING_MODE_OFF, USER_LEARNING_MODE_PASSIVE, USER_LEARNING_MODE_ACTIVE]

DEFAULT_USER_PREFERENCE_ENABLED = False
DEFAULT_TRACKED_USERS: list[str] = []
DEFAULT_PRIMARY_USER = None
DEFAULT_USER_LEARNING_MODE = USER_LEARNING_MODE_PASSIVE

# Multi-User Preference Learning (MUPL) Module
CONF_MUPL_ENABLED = "mupl_enabled"
CONF_MUPL_PRIVACY_MODE = "mupl_privacy_mode"
CONF_MUPL_MIN_INTERACTIONS = "mupl_min_interactions"
CONF_MUPL_RETENTION_DAYS = "mupl_retention_days"

MUPL_PRIVACY_MODE_OPT_IN = "opt-in"
MUPL_PRIVACY_MODE_OPT_OUT = "opt-out"
MUPL_PRIVACY_MODES = [MUPL_PRIVACY_MODE_OPT_IN, MUPL_PRIVACY_MODE_OPT_OUT]

DEFAULT_MUPL_ENABLED = False
DEFAULT_MUPL_PRIVACY_MODE = MUPL_PRIVACY_MODE_OPT_IN
DEFAULT_MUPL_MIN_INTERACTIONS = 5
DEFAULT_MUPL_RETENTION_DAYS = 90

# Preference learning constants
PREF_SMOOTHING_ALPHA = 0.3
PREF_MIN_INTERACTIONS = 5
PREF_RETENTION_DAYS = 90

# Neural System Configuration
CONF_NEURON_CONTEXT_ENTITIES = "neuron_context_entities"
CONF_NEURON_STATE_ENTITIES = "neuron_state_entities"
CONF_NEURON_MOOD_ENTITIES = "neuron_mood_entities"
CONF_NEURON_ENABLED = "neuron_enabled"
CONF_NEURON_EVALUATION_INTERVAL = "neuron_evaluation_interval"

# Default neuron config
DEFAULT_NEURON_ENABLED = True
DEFAULT_NEURON_EVALUATION_INTERVAL = 60  # seconds
DEFAULT_NEURON_CONTEXT_ENTITIES: list[str] = []
DEFAULT_NEURON_STATE_ENTITIES: list[str] = []
DEFAULT_NEURON_MOOD_ENTITIES: list[str] = []

# Neuron types for UI
NEURON_TYPE_CONTEXT = "context"
NEURON_TYPE_STATE = "state"
NEURON_TYPE_MOOD = "mood"
NEURON_TYPES = [NEURON_TYPE_CONTEXT, NEURON_TYPE_STATE, NEURON_TYPE_MOOD]

# Calendar Context Neuron
CONF_CALENDAR_CONTEXT_ENABLED = "calendar_context_enabled"
CONF_CALENDAR_ENTITIES = "calendar_entities"
CONF_CALENDAR_LOOKAHEAD_HOURS = "calendar_lookahead_hours"
CONF_CALENDAR_MEETING_SOON_MINUTES = "calendar_meeting_soon_minutes"

DEFAULT_CALENDAR_CONTEXT_ENABLED = False
DEFAULT_CALENDAR_ENTITIES: list[str] = []
DEFAULT_CALENDAR_LOOKAHEAD_HOURS = 24
DEFAULT_CALENDAR_MEETING_SOON_MINUTES = 30

# Suggestion Panel
CONF_SUGGESTION_PANEL_ENABLED = "suggestion_panel_enabled"
CONF_SUGGESTION_MAX_PENDING = "suggestion_max_pending"
CONF_SUGGESTION_MAX_HISTORY = "suggestion_max_history"
CONF_SUGGESTION_EXPIRY_HOURS = "suggestion_expiry_hours"

DEFAULT_SUGGESTION_PANEL_ENABLED = True
DEFAULT_SUGGESTION_MAX_PENDING = 50
DEFAULT_SUGGESTION_MAX_HISTORY = 200
DEFAULT_SUGGESTION_EXPIRY_HOURS = 72

# Mood Dashboard
CONF_MOOD_DASHBOARD_ENABLED = "mood_dashboard_enabled"
CONF_MOOD_HISTORY_MAX_ENTRIES = "mood_history_max_entries"

DEFAULT_MOOD_DASHBOARD_ENABLED = True
DEFAULT_MOOD_HISTORY_MAX_ENTRIES = 100

# Knowledge Graph Sync
CONF_KNOWLEDGE_GRAPH_ENABLED = "knowledge_graph_enabled"
CONF_KNOWLEDGE_GRAPH_SYNC_INTERVAL = "knowledge_graph_sync_interval"

DEFAULT_KNOWLEDGE_GRAPH_ENABLED = True
DEFAULT_KNOWLEDGE_GRAPH_SYNC_INTERVAL = 3600  # 1 hour

# ML Context Module
CONF_ML_ENABLED = "ml_enabled"
CONF_ML_ENTITIES = "ml_entities"
CONF_ML_ANOMALY_CONTAMINATION = "ml_anomaly_contamination"
CONF_ML_HABIT_WINDOW_SIZE = "ml_habit_window_size"

DEFAULT_ML_ENABLED = False
DEFAULT_ML_ENTITIES: list[str] = []
DEFAULT_ML_ANOMALY_CONTAMINATION = 0.1
DEFAULT_ML_HABIT_WINDOW_SIZE = 100

# Waste Collection Reminder Module
CONF_WASTE_ENABLED = "waste_enabled"
CONF_WASTE_ENTITIES = "waste_entities"
CONF_WASTE_TTS_ENABLED = "waste_tts_enabled"
CONF_WASTE_TTS_ENTITY = "waste_tts_entity"
CONF_WASTE_REMINDER_EVENING_HOUR = "waste_reminder_evening_hour"
CONF_WASTE_REMINDER_MORNING_HOUR = "waste_reminder_morning_hour"

DEFAULT_WASTE_ENABLED = False
DEFAULT_WASTE_ENTITIES: list[str] = []
DEFAULT_WASTE_TTS_ENABLED = True
DEFAULT_WASTE_TTS_ENTITY = ""
DEFAULT_WASTE_REMINDER_EVENING_HOUR = 19
DEFAULT_WASTE_REMINDER_MORNING_HOUR = 7

# Birthday Reminder Module
CONF_BIRTHDAY_ENABLED = "birthday_enabled"
CONF_BIRTHDAY_CALENDAR_ENTITIES = "birthday_calendar_entities"
CONF_BIRTHDAY_LOOKAHEAD_DAYS = "birthday_lookahead_days"
CONF_BIRTHDAY_TTS_ENABLED = "birthday_tts_enabled"
CONF_BIRTHDAY_TTS_ENTITY = "birthday_tts_entity"
CONF_BIRTHDAY_REMINDER_HOUR = "birthday_reminder_hour"

DEFAULT_BIRTHDAY_ENABLED = False
DEFAULT_BIRTHDAY_CALENDAR_ENTITIES: list[str] = []
DEFAULT_BIRTHDAY_LOOKAHEAD_DAYS = 14
DEFAULT_BIRTHDAY_TTS_ENABLED = True
DEFAULT_BIRTHDAY_TTS_ENTITY = ""
DEFAULT_BIRTHDAY_REMINDER_HOUR = 8

# Entity Tags (v3.2.2)
ENTITY_TAGS_STORE_KEY = "ai_home_copilot.entity_tags"
ENTITY_TAGS_STORE_VERSION = 1
