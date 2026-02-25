"""Helpers for entity profile selection (core vs full)."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry

from .const import (
    CONF_ENTITY_PROFILE,
    DEFAULT_ENTITY_PROFILE,
    ENTITY_PROFILE_FULL,
    ENTITY_PROFILES,
)


def get_entity_profile(entry: ConfigEntry) -> str:
    """Return normalized entity profile for a config entry."""
    options = entry.options if isinstance(entry.options, dict) else {}
    data = entry.data if isinstance(entry.data, dict) else {}
    profile = options.get(CONF_ENTITY_PROFILE, data.get(CONF_ENTITY_PROFILE, DEFAULT_ENTITY_PROFILE))
    if profile not in ENTITY_PROFILES:
        return DEFAULT_ENTITY_PROFILE
    return str(profile)


def is_full_entity_profile(entry: ConfigEntry) -> bool:
    """Return True if the entry is configured for the full entity surface."""
    return get_entity_profile(entry) == ENTITY_PROFILE_FULL
