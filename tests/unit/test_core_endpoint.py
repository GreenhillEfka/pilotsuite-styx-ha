"""Unit tests for Core endpoint normalization/discovery helpers."""

from custom_components.ai_home_copilot.core_endpoint import (
    build_base_url,
    build_candidate_hosts,
    normalize_host_port,
)


def test_normalize_host_port_plain_host() -> None:
    host, port = normalize_host_port("homeassistant.local", 8909)
    assert host == "homeassistant.local"
    assert port == 8909


def test_normalize_host_port_embedded_port() -> None:
    host, port = normalize_host_port("192.168.30.18:8909", 1234)
    assert host == "192.168.30.18"
    assert port == 8909


def test_normalize_host_port_url() -> None:
    host, port = normalize_host_port("http://192.168.30.18:8909", 0)
    assert host == "192.168.30.18"
    assert port == 8909


def test_build_base_url() -> None:
    assert build_base_url("192.168.30.18", 8909) == "http://192.168.30.18:8909"


def test_build_candidate_hosts_includes_fallbacks() -> None:
    hosts = build_candidate_hosts(
        "192.168.30.18",
        internal_url="http://homeassistant.local:8123",
        external_url="https://ha.example.com",
    )
    assert hosts[0] == "192.168.30.18"
    assert "homeassistant.local" in hosts
    assert "homeassistant" in hosts
    assert "supervisor" in hosts
    assert "localhost" in hosts
    assert "127.0.0.1" in hosts
    assert "host.docker.internal" not in hosts
    assert "ha.example.com" in hosts


def test_build_candidate_hosts_can_include_docker_internal() -> None:
    hosts = build_candidate_hosts(
        "192.168.30.18",
        include_docker_internal=True,
    )
    assert "host.docker.internal" in hosts
