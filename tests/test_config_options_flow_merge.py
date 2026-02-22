"""Tests for options-flow merge behavior (token/options persistence)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components"))

from ai_home_copilot.config_helpers import merge_config_data


def test_merge_config_data_keeps_existing_token_when_updates_omit_it() -> None:
    merged = merge_config_data(
        {"host": "192.168.30.18", "port": 8909, "token": "abc123"},
        {"media_music_players": ["media_player.living_room"]},
        {"media_tv_players": ["media_player.tv_lounge"]},
    )
    assert merged["token"] == "abc123"
    assert merged["host"] == "192.168.30.18"
    assert merged["media_music_players"] == ["media_player.living_room"]
    assert merged["media_tv_players"] == ["media_player.tv_lounge"]


def test_merge_config_data_applies_updates_and_preserves_unrelated_options() -> None:
    merged = merge_config_data(
        {"host": "homeassistant.local", "port": 8909, "token": "old"},
        {"watchdog_enabled": True, "events_forwarder_enabled": True},
        {"host": "192.168.30.18", "port": 8123},
    )
    assert merged["host"] == "192.168.30.18"
    assert merged["port"] == 8123
    assert merged["token"] == "old"
    assert merged["watchdog_enabled"] is True
    assert merged["events_forwarder_enabled"] is True
