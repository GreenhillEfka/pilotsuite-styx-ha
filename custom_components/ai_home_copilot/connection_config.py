"""Helpers for resolving Core connection config from config entries."""
from __future__ import annotations

from typing import Any, Mapping

from homeassistant.config_entries import ConfigEntry

from .const import CONF_HOST, CONF_PORT, CONF_TOKEN, DEFAULT_HOST, DEFAULT_PORT
from .core_endpoint import build_base_url, normalize_host_port

_LEGACY_TOKEN_KEYS = ("auth_token", "access_token", "api_token")


def merged_entry_config(entry: ConfigEntry) -> dict[str, Any]:
    """Return merged entry config with options overriding data."""
    merged: dict[str, Any] = {}
    if isinstance(entry.data, Mapping):
        merged.update(entry.data)
    if isinstance(entry.options, Mapping):
        merged.update(entry.options)
    return merged


def resolve_core_connection_from_mapping(config: Mapping[str, Any]) -> tuple[str, int, str]:
    """Resolve normalized ``(host, port, token)`` from mixed config mappings."""
    host_raw: object = config.get(CONF_HOST)
    port_raw: object = config.get(CONF_PORT)
    legacy_url = config.get("core_url")

    # Backward compatibility: parse host/port from legacy core_url if needed.
    if legacy_url:
        legacy_host, legacy_port = normalize_host_port(legacy_url, port_raw, default_port=DEFAULT_PORT)
        if not str(host_raw or "").strip():
            host_raw = legacy_host
        if port_raw in (None, "", 0):
            port_raw = legacy_port

    host, port = normalize_host_port(host_raw, port_raw, default_port=DEFAULT_PORT)
    if not host:
        host = DEFAULT_HOST

    token = str(config.get(CONF_TOKEN) or "").strip()
    if not token:
        for key in _LEGACY_TOKEN_KEYS:
            legacy_token = str(config.get(key) or "").strip()
            if legacy_token:
                token = legacy_token
                break

    return host, port, token


def resolve_core_connection(entry: ConfigEntry) -> tuple[str, int, str]:
    """Resolve normalized ``(host, port, token)`` from a config entry."""
    return resolve_core_connection_from_mapping(merged_entry_config(entry))


def build_core_base_url(entry: ConfigEntry) -> str:
    """Return normalized Core base URL from entry settings."""
    host, port, _token = resolve_core_connection(entry)
    return build_base_url(host, port)


def build_core_headers(
    token: str | None,
    *,
    content_type: str | None = None,
) -> dict[str, str]:
    """Build auth headers compatible with both legacy and current Core endpoints."""
    headers: dict[str, str] = {}
    token_clean = str(token or "").strip()
    if token_clean:
        headers["Authorization"] = f"Bearer {token_clean}"
        headers["X-Auth-Token"] = token_clean
    if content_type:
        headers["Content-Type"] = content_type
    return headers

