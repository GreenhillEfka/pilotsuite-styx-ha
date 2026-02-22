"""Tests for stable PilotSuite device identity handling."""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components"))

from ai_home_copilot.const import DOMAIN, LEGACY_MAIN_DEVICE_IDENTIFIERS, MAIN_DEVICE_IDENTIFIER
from ai_home_copilot.debug import DebugModeSensor
from ai_home_copilot.entity import CopilotBaseEntity, build_main_device_identifiers


def test_build_main_device_identifiers_includes_canonical_and_legacy_ids() -> None:
    identifiers = build_main_device_identifiers({"host": "192.168.30.18", "port": 8909})

    assert (DOMAIN, MAIN_DEVICE_IDENTIFIER) in identifiers
    assert (DOMAIN, "192.168.30.18:8909") in identifiers
    for legacy in LEGACY_MAIN_DEVICE_IDENTIFIERS:
        assert (DOMAIN, legacy) in identifiers


def test_debug_mode_sensor_uses_main_device_identity() -> None:
    hass = SimpleNamespace(data={})
    entry = SimpleNamespace(data={"host": "homeassistant.local", "port": 8909}, options={})

    sensor = DebugModeSensor(hass, entry)
    identifiers = sensor._attr_device_info["identifiers"]

    assert (DOMAIN, MAIN_DEVICE_IDENTIFIER) in identifiers


def test_core_base_url_prefers_active_failover_endpoint() -> None:
    coordinator = SimpleNamespace(
        _config={"host": "homeassistant.local", "port": 8909, "token": "abc"},
        api=SimpleNamespace(_active_base_url="http://supervisor:8909"),
    )
    entity = object.__new__(CopilotBaseEntity)
    entity.coordinator = coordinator
    entity._host = "homeassistant.local"
    entity._port = 8909

    assert entity._core_base_url() == "http://supervisor:8909"


def test_core_headers_include_bearer_and_x_auth_token() -> None:
    coordinator = SimpleNamespace(
        _config={"host": "homeassistant.local", "port": 8909, "auth_token": "legacy"},
        api=SimpleNamespace(_active_base_url="http://localhost:8909"),
    )
    entity = object.__new__(CopilotBaseEntity)
    entity.coordinator = coordinator
    entity._host = "homeassistant.local"
    entity._port = 8909

    assert entity._core_headers() == {
        "Authorization": "Bearer legacy",
        "X-Auth-Token": "legacy",
    }
