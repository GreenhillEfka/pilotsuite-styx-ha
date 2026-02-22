"""Regression tests for connection normalization and failover policy."""
from __future__ import annotations

from types import SimpleNamespace

from custom_components.ai_home_copilot.api import CopilotApiError
from custom_components.ai_home_copilot.connection_config import (
    resolve_core_connection,
    resolve_core_connection_from_mapping,
)
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

