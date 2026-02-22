"""Helpers and constants for config flow modules."""
from __future__ import annotations

import asyncio
import logging

import aiohttp

from homeassistant.core import HomeAssistant

from .const import DEFAULT_HOST, DEFAULT_PORT
from .core_endpoint import build_base_url, build_candidate_hosts, normalize_host_port

_LOGGER = logging.getLogger(__name__)

# Entity roles for zone configuration
ZONE_ENTITY_ROLES = {
    "motion": {"icon": "mdi:motion-sensor", "label": "Bewegung", "domain": ["binary_sensor", "sensor"]},
    "lights": {"icon": "mdi:lightbulb", "label": "Lichter", "domain": ["light"]},
    "sensors": {"icon": "mdi:thermometer", "label": "Sensoren", "domain": ["sensor"]},
    "media": {"icon": "mdi:television", "label": "Media", "domain": ["media_player"]},
    "climate": {"icon": "mdi:thermostat", "label": "Klima", "domain": ["climate"]},
    "covers": {"icon": "mdi:blinds", "label": "Jalousien", "domain": ["cover"]},
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

    host_raw = data.get("host", "")
    if host_raw and not isinstance(host_raw, str):
        raise HomeAssistantError("host must be a string")

    port_raw = data.get("port")
    if port_raw is not None:
        try:
            port_int = int(port_raw)
        except (TypeError, ValueError):
            raise HomeAssistantError("port must be an integer")
        if not (1 <= port_int <= 65535):
            raise HomeAssistantError(f"port must be 1-65535, got {port_int}")

    host, port = normalize_host_port(host_raw, port_raw, default_port=DEFAULT_PORT)
    if host:
        # Keep normalized values for downstream consumers in the same flow.
        data["host"] = host
        data["port"] = port

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
        url = f"{build_base_url(host, port)}/api/v1/status"
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status < 200 or resp.status >= 300:
                    raise HomeAssistantError(
                        f"Core Add-on at {host}:{port} returned HTTP {resp.status} for /api/v1/status"
                    )
                ctype = (resp.headers.get("Content-Type", "") or "").lower()
                if "json" not in ctype:
                    preview = (await resp.text())[:120]
                    raise HomeAssistantError(
                        f"Endpoint {host}:{port} is not PilotSuite Core (unexpected response): {preview}"
                    )
                payload = await resp.json()
                if not isinstance(payload, dict) or payload.get("ok") is not True:
                    raise HomeAssistantError(
                        f"Endpoint {host}:{port} does not expose a valid PilotSuite status API"
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


async def discover_reachable_core_endpoint(
    hass: HomeAssistant,
    *,
    preferred_host: str = DEFAULT_HOST,
    preferred_port: int = DEFAULT_PORT,
    timeout_s: float = 2.5,
) -> tuple[str, int] | None:
    """Try multiple host candidates and return the first reachable Core endpoint."""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    host, port = normalize_host_port(preferred_host, preferred_port, default_port=DEFAULT_PORT)
    candidates = build_candidate_hosts(
        host or DEFAULT_HOST,
        internal_url=getattr(hass.config, "internal_url", None),
        external_url=getattr(hass.config, "external_url", None),
    )
    session = async_get_clientsession(hass)
    port_candidates = [port]
    if DEFAULT_PORT not in port_candidates:
        port_candidates.append(DEFAULT_PORT)

    for candidate_host in candidates:
        for candidate_port in port_candidates:
            base = build_base_url(candidate_host, candidate_port)
            try:
                async with session.get(
                    f"{base}/api/v1/status",
                    timeout=aiohttp.ClientTimeout(total=timeout_s),
                ) as resp:
                    if resp.status != 200:
                        continue
                    ctype = (resp.headers.get("Content-Type", "") or "").lower()
                    if "json" not in ctype:
                        continue
                    payload = await resp.json()
                    if isinstance(payload, dict) and payload.get("ok") is True:
                        _LOGGER.info(
                            "Discovered reachable PilotSuite Core endpoint at %s:%s",
                            candidate_host,
                            candidate_port,
                        )
                        return candidate_host, candidate_port
            except (aiohttp.ClientError, asyncio.TimeoutError):
                continue
            except Exception:
                continue

    return None
