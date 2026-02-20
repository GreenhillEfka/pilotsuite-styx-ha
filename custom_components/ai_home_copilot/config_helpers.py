"""Helpers and constants for config flow modules."""
from __future__ import annotations

import asyncio
import logging

import aiohttp

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Entity roles for zone configuration
ZONE_ENTITY_ROLES = {
    "motion": {"icon": "mdi:motion-sensor", "label": "Bewegung"},
    "lights": {"icon": "mdi:lightbulb", "label": "Lichter"},
    "sensors": {"icon": "mdi:thermometer", "label": "Sensoren"},
    "media": {"icon": "mdi:television", "label": "Media"},
    "climate": {"icon": "mdi:thermostat", "label": "Klima"},
    "covers": {"icon": "mdi:blinds", "label": "Jalousien"},
}

# Wizard step constants
STEP_DISCOVERY = "discovery"
STEP_ZONES = "zones"
STEP_ZONE_ENTITIES = "zone_entities"
STEP_ENTITIES = "entities"
STEP_FEATURES = "features"
STEP_NETWORK = "network"
STEP_REVIEW = "review"


def as_csv(value) -> str:
    """Convert a value to a comma-separated string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ",".join([v for v in value if isinstance(v, str)])
    return str(value)


def parse_csv(value: str) -> list[str]:
    """Parse a comma-separated string into a list of strings."""
    if not value:
        return []
    parts = [p.strip() for p in value.replace("\n", ",").split(",")]
    return [p for p in parts if p]


async def validate_input(hass: HomeAssistant, data: dict) -> None:
    """Validate config input: host, port, and critical numeric bounds."""
    from homeassistant.exceptions import HomeAssistantError

    host = data.get("host", "")
    if host and not isinstance(host, str):
        raise HomeAssistantError("host must be a string")

    port = data.get("port")
    if port is not None:
        try:
            port_int = int(port)
        except (TypeError, ValueError):
            raise HomeAssistantError("port must be an integer")
        if not (1 <= port_int <= 65535):
            raise HomeAssistantError(f"port must be 1-65535, got {port_int}")

    # Validate critical numeric bounds
    _bounds = {
        "seed_max_offers_per_hour": (1, 100),
        "seed_min_seconds_between_offers": (1, 3600),
        "seed_max_offers_per_update": (1, 50),
        "watchdog_interval_seconds": (30, 86400),
        "events_forwarder_flush_interval_seconds": (1, 300),
        "events_forwarder_max_batch": (1, 5000),
        "events_forwarder_idempotency_ttl_seconds": (10, 86400),
        "events_forwarder_persistent_queue_max_size": (10, 50000),
        "mupl_min_interactions": (1, 10000),
        "mupl_retention_days": (1, 3650),
    }
    for key, (lo, hi) in _bounds.items():
        val = data.get(key)
        if val is not None:
            try:
                val_int = int(val)
            except (TypeError, ValueError):
                continue
            if not (lo <= val_int <= hi):
                raise HomeAssistantError(f"{key} must be {lo}-{hi}, got {val_int}")

    # Test connectivity to Core Add-on (skip for zero-config with empty token)
    token = data.get("token", "")
    if host and port:
        from homeassistant.helpers.aiohttp_client import async_get_clientsession
        session = async_get_clientsession(hass)
        url = f"http://{host}:{int(port)}/api/v1/status"
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status >= 500:
                    raise HomeAssistantError(
                        f"Core Add-on returned server error ({resp.status})"
                    )
                _LOGGER.debug("Core Add-on reachable at %s:%s (status=%s)", host, port, resp.status)
        except asyncio.TimeoutError:
            raise HomeAssistantError(
                f"Core Add-on at {host}:{port} did not respond (timeout)"
            )
        except aiohttp.ClientError as err:
            raise HomeAssistantError(
                f"Cannot reach Core Add-on at {host}:{port}: {err}"
            )
