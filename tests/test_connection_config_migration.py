"""Regression tests for connection normalization and failover policy."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from custom_components.ai_home_copilot.api import CopilotApiError
from custom_components.ai_home_copilot.__init__ import _async_migrate_connection_config
from custom_components.ai_home_copilot.connection_config import (
    resolve_core_connection,
    resolve_core_connection_from_mapping,
)
from custom_components.ai_home_copilot.const import CONF_HOST, CONF_PORT, CONF_TOKEN
from custom_components.ai_home_copilot.coordinator import _should_failover
from custom_components.ai_home_copilot.core_endpoint import build_candidate_hosts


def test_resolve_core_connection_from_legacy_core_url_and_token() -> None:
    host, port, token = resolve_core_connection_from_mapping(
        {
            "core_url": "http://192.168.30.18:8909",
            "access_token": "abc123",
        }
    )
    assert host == "192.168.30.18"
    assert port == 8909
    assert token == "abc123"


def test_resolve_core_connection_prefers_options_token() -> None:
    entry = SimpleNamespace(
        data={"host": "192.168.30.18", "port": 8909, "token": ""},
        options={"token": "from_options"},
    )
    host, port, token = resolve_core_connection(entry)
    assert host == "192.168.30.18"
    assert port == 8909
    assert token == "from_options"


def test_candidate_hosts_skip_docker_internal_by_default() -> None:
    hosts = build_candidate_hosts("192.168.30.18")
    assert "host.docker.internal" not in hosts


def test_candidate_hosts_include_docker_internal_when_requested() -> None:
    hosts = build_candidate_hosts("192.168.30.18", include_docker_internal=True)
    assert "host.docker.internal" in hosts


def test_failover_does_not_trigger_for_auth_errors() -> None:
    assert _should_failover(CopilotApiError("HTTP 401 for http://x: nope")) is False
    assert _should_failover(CopilotApiError("HTTP 403 for http://x: nope")) is False


def test_failover_triggers_for_endpoint_or_transport_errors() -> None:
    assert _should_failover(CopilotApiError("HTTP 404 for http://x: nope")) is True
    assert _should_failover(CopilotApiError("HTTP 503 for http://x: nope")) is True
    assert _should_failover(CopilotApiError("Timeout calling http://x")) is True


@pytest.mark.asyncio
async def test_connection_migration_syncs_data_and_options() -> None:
    entry = SimpleNamespace(
        entry_id="entry_1",
        data={CONF_HOST: "192.168.30.18", CONF_PORT: 8909, CONF_TOKEN: "new_token"},
        options={CONF_HOST: "192.168.30.18", CONF_PORT: 8321, "auth_token": "legacy"},
    )
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_update_entry=MagicMock())
    )

    await _async_migrate_connection_config(hass, entry)

    hass.config_entries.async_update_entry.assert_called_once()
    _args, kwargs = hass.config_entries.async_update_entry.call_args
    updated_data = kwargs["data"]
    updated_options = kwargs["options"]

    assert updated_data[CONF_PORT] == 8909
    assert updated_options[CONF_PORT] == 8909
    assert updated_options[CONF_TOKEN] == "new_token"
    assert "auth_token" not in updated_options
