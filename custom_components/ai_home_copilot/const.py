DOMAIN = "ai_home_copilot"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_TOKEN = "token"
CONF_TEST_LIGHT = "test_light_entity_id"
CONF_WEBHOOK_ID = "webhook_id"
CONF_WEBHOOK_URL = "webhook_url"
CONF_WATCHDOG_ENABLED = "watchdog_enabled"
CONF_WATCHDOG_INTERVAL_SECONDS = "watchdog_interval_seconds"

# Privacy-first defaults: no personal IPs/entities shipped.
# Tip: set this to your HA host IP (LAN) or a resolvable hostname.
DEFAULT_HOST = "homeassistant.local"
DEFAULT_PORT = 8909
DEFAULT_TEST_LIGHT = ""
DEFAULT_WATCHDOG_ENABLED = False
DEFAULT_WATCHDOG_INTERVAL_SECONDS = 1800

HEADER_AUTH = "X-Auth-Token"
