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
