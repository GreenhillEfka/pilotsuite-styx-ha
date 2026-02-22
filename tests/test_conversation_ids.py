"""Unit tests for conversation ID helpers."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components"))

from ai_home_copilot.conversation_ids import generate_ulid, is_valid_conversation_id, normalize_conversation_id


def test_generate_ulid_shape() -> None:
    value = generate_ulid()
    assert len(value) == 26
    assert is_valid_conversation_id(value)


def test_normalize_conversation_id_keeps_valid_ulid() -> None:
    ulid = generate_ulid()
    assert normalize_conversation_id(ulid) == ulid


def test_normalize_conversation_id_replaces_invalid_value() -> None:
    normalized = normalize_conversation_id("not_valid")
    assert len(normalized) == 26
    assert is_valid_conversation_id(normalized)
