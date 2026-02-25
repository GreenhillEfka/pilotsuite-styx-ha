"""Coordinator API client compatibility tests."""

from unittest.mock import MagicMock

from custom_components.ai_home_copilot.api import CopilotApiClient as SharedCopilotApiClient
from custom_components.ai_home_copilot.coordinator import CopilotApiClient


def test_coordinator_api_client_is_shared_subclass() -> None:
    assert issubclass(CopilotApiClient, SharedCopilotApiClient)


def test_coordinator_api_path_normalization() -> None:
    assert CopilotApiClient._normalize_v1_path("habitus/rules") == "/api/v1/habitus/rules"
    assert CopilotApiClient._normalize_v1_path("/api/v1/status") == "/api/v1/status"
    assert CopilotApiClient._normalize_v1_path("v1/chat/completions") == "/v1/chat/completions"


def test_coordinator_api_client_construction() -> None:
    api = CopilotApiClient(
        MagicMock(),
        base_urls=["http://localhost:8909", "http://127.0.0.1:8909"],
        token="test-token",
    )
    assert hasattr(api, "async_get")
    assert hasattr(api, "get_with_auth")
