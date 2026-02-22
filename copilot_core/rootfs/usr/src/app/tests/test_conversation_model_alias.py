"""Tests for OpenAI conversation model alias normalization."""

from __future__ import annotations

import pytest

from copilot_core.api.v1.conversation import _normalize_requested_model


def test_model_alias_pilotsuite_maps_to_configured_ollama_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b")
    assert _normalize_requested_model("pilotsuite") == "qwen3:4b"


def test_model_alias_local_maps_to_default_when_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    assert _normalize_requested_model("local") == "qwen3:4b"


def test_non_alias_model_is_preserved() -> None:
    assert _normalize_requested_model("gpt-4o-mini") == "gpt-4o-mini"
