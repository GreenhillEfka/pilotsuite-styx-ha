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

# Dev/Debug: push sanitized HA log snippets to Copilot-Core (opt-in).
CONF_DEVLOG_PUSH_ENABLED = "devlog_push_enabled"

# Core API v1: capabilities ping + HA->Core event forwarder (opt-in).
CONF_EVENTS_FORWARDER_ENABLED = "events_forwarder_enabled"
CONF_EVENTS_FORWARDER_FLUSH_INTERVAL_SECONDS = "events_forwarder_flush_interval_seconds"
CONF_EVENTS_FORWARDER_MAX_BATCH = "events_forwarder_max_batch"

# HA log digest (local): surface relevant errors/warnings in HA (opt-in).
CONF_HA_ERRORS_DIGEST_ENABLED = "ha_errors_digest_enabled"
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

DEFAULT_HA_ERRORS_DIGEST_ENABLED = False
DEFAULT_HA_ERRORS_DIGEST_INTERVAL_SECONDS = 300
DEFAULT_HA_ERRORS_DIGEST_MAX_LINES = 800

DEFAULT_SUGGESTION_SEED_ENTITIES: list[str] = []
DEFAULT_SEED_ALLOWED_DOMAINS: list[str] = []
DEFAULT_SEED_BLOCKED_DOMAINS: list[str] = []
DEFAULT_SEED_MAX_OFFERS_PER_HOUR = 10
DEFAULT_SEED_MIN_SECONDS_BETWEEN_OFFERS = 30
DEFAULT_SEED_MAX_OFFERS_PER_UPDATE = 3

HEADER_AUTH = "X-Auth-Token"
