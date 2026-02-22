"""Tests for LLM provider model fallback behavior."""

from __future__ import annotations

from typing import Any

import pytest
import requests as http_requests

from copilot_core.llm_provider import LLMProvider


class _Resp:
    def __init__(self, status_code: int, text: str, data: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self.text = text
        self._data = data or {}

    def json(self) -> dict[str, Any]:
        return self._data


def test_requested_model_falls_back_to_configured_ollama_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_URL", "http://127.0.0.1:11435")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b")
    monkeypatch.delenv("CLOUD_API_URL", raising=False)
    monkeypatch.delenv("CLOUD_API_KEY", raising=False)

    calls: list[str] = []

    def _fake_post(url: str, json: dict[str, Any], timeout: int):  # noqa: A002
        calls.append(str(json.get("model")))
        model = json.get("model")
        if model == "gpt-4o-mini":
            return _Resp(404, '{"error":"model \\"gpt-4o-mini\\" not found"}')
        if model == "qwen3:4b":
            return _Resp(200, "", {"message": {"content": "ok from qwen"}})
        return _Resp(500, "unexpected")

    monkeypatch.setattr("copilot_core.llm_provider.http_requests.post", _fake_post)

    provider = LLMProvider()
    result = provider.chat(messages=[{"role": "user", "content": "hi"}], model="gpt-4o-mini")

    assert result["provider"] == "ollama"
    assert result["content"] == "ok from qwen"
    assert calls == ["gpt-4o-mini", "qwen3:4b"]


def test_offline_message_reports_missing_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_URL", "http://127.0.0.1:11435")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b")
    monkeypatch.delenv("CLOUD_API_URL", raising=False)
    monkeypatch.delenv("CLOUD_API_KEY", raising=False)

    def _fake_post(url: str, json: dict[str, Any], timeout: int):  # noqa: A002
        model = json.get("model")
        return _Resp(404, f'{{"error":"model \\"{model}\\" not found"}}')

    monkeypatch.setattr("copilot_core.llm_provider.http_requests.post", _fake_post)

    provider = LLMProvider()
    result = provider.chat(messages=[{"role": "user", "content": "hi"}], model="gpt-4o-mini")

    assert result["provider"] == "none"
    assert "Modell 'qwen3:4b' nicht installiert" in result["content"]


def test_cloud_used_for_explicit_external_model_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_URL", "http://127.0.0.1:11435")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b")
    monkeypatch.setenv("CLOUD_API_URL", "https://api.example.com/v1")
    monkeypatch.setenv("CLOUD_API_KEY", "sk-test")
    monkeypatch.setenv("CLOUD_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("PREFER_LOCAL", "true")

    ollama_models: list[str] = []
    cloud_calls: list[str] = []

    def _fake_post(url: str, json: dict[str, Any], timeout: int, headers=None):  # noqa: A002
        if url.endswith("/api/chat"):
            model = str(json.get("model", ""))
            ollama_models.append(model)
            return _Resp(404, f'{{"error":"model \\"{model}\\" not found"}}')
        if url.endswith("/chat/completions"):
            cloud_calls.append(str(json.get("model")))
            return _Resp(200, "", {"choices": [{"message": {"content": "ok from cloud"}}]})
        return _Resp(500, "unexpected")

    monkeypatch.setattr("copilot_core.llm_provider.http_requests.post", _fake_post)

    provider = LLMProvider()
    result = provider.chat(messages=[{"role": "user", "content": "hi"}], model="gpt-4o-mini")

    assert result["provider"] == "cloud"
    assert result["content"] == "ok from cloud"
    assert ollama_models == ["gpt-4o-mini"]
    assert cloud_calls == ["gpt-4o-mini"]


def test_cloud_url_without_key_returns_offline_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_URL", "http://127.0.0.1:11435")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b")
    monkeypatch.setenv("CLOUD_API_URL", "https://api.example.com/v1")
    monkeypatch.delenv("CLOUD_API_KEY", raising=False)
    monkeypatch.setenv("PREFER_LOCAL", "true")

    def _fake_post(url: str, json: dict[str, Any], timeout: int):  # noqa: A002
        raise http_requests.exceptions.ConnectionError("down")

    monkeypatch.setattr("copilot_core.llm_provider.http_requests.post", _fake_post)

    provider = LLMProvider()
    result = provider.chat(messages=[{"role": "user", "content": "hi"}], model="pilotsuite")

    assert isinstance(result, dict)
    assert result["provider"] == "none"
    assert "Cloud-API nicht konfiguriert" in result["content"]


def test_alias_model_maps_to_local_configured_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_URL", "http://127.0.0.1:11435")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b")
    monkeypatch.delenv("CLOUD_API_URL", raising=False)
    monkeypatch.delenv("CLOUD_API_KEY", raising=False)

    calls: list[str] = []

    def _fake_post(url: str, json: dict[str, Any], timeout: int):  # noqa: A002
        calls.append(str(json.get("model")))
        return _Resp(200, "", {"message": {"content": "ok"}})

    monkeypatch.setattr("copilot_core.llm_provider.http_requests.post", _fake_post)

    provider = LLMProvider()
    result = provider.chat(messages=[{"role": "user", "content": "hi"}], model="pilotsuite")

    assert result["provider"] == "ollama"
    assert result["content"] == "ok"
    assert calls == ["qwen3:4b"]
