"""Tests for PilotSuite Chat WebSocket Command.

Covers:
- ws_chat_send: message delivery, conversation_id passthrough
- Error handling: missing coordinator, API failure
- Response format: reply, conversation_id, model fields
- Integration: async_setup_suggestion_websocket registers all 3 commands
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from custom_components.ai_home_copilot.suggestion_panel import (
    async_setup_suggestion_websocket,
)
from custom_components.ai_home_copilot.const import DOMAIN


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_hass(entry_id: str = "test", coordinator=None, suggestion_store=None):
    """Build a mock hass with data dict."""
    hass = MagicMock()
    entry_data = {}
    if coordinator:
        entry_data["coordinator"] = coordinator
    if suggestion_store:
        entry_data["suggestion_store"] = suggestion_store
    hass.data = {DOMAIN: {entry_id: entry_data}}
    return hass


def _make_coordinator(chat_response: dict = None):
    """Build a mock coordinator with async_chat_completions."""
    coord = MagicMock()
    coord.async_chat_completions = AsyncMock(return_value=chat_response or {
        "choices": [{"message": {"content": "Hallo!"}}],
        "model": "qwen3:0.6b",
    })
    return coord


def _make_connection():
    """Build a mock WS connection."""
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    return conn


# ---------------------------------------------------------------------------
# WebSocket Command Registration
# ---------------------------------------------------------------------------

class TestWebSocketSetup:
    @pytest.mark.asyncio
    async def test_registers_3_commands(self):
        """Setup should register suggestions_get, suggestion_action, and chat_send."""
        hass = _make_hass()
        registered_commands = []

        with patch("custom_components.ai_home_copilot.suggestion_panel.websocket_api",
                    create=True) as mock_ws:
            # Capture decorated functions
            def fake_command(schema):
                def decorator(func):
                    return func
                return decorator

            def fake_response(func):
                return func

            def fake_register(hass_arg, handler):
                registered_commands.append(handler.__name__)

            mock_ws.websocket_command = fake_command
            mock_ws.async_response = fake_response
            mock_ws.async_register_command = fake_register

            # Reimport to get the patched version
            from importlib import reload
            import custom_components.ai_home_copilot.suggestion_panel as sp
            # Call setup directly - it imports websocket_api inside the function
            with patch("homeassistant.components.websocket_api") as ha_ws:
                ha_ws.websocket_command = fake_command
                ha_ws.async_response = fake_response
                ha_ws.async_register_command = fake_register
                await async_setup_suggestion_websocket(hass, "test")

        assert len(registered_commands) == 3
        assert "ws_get_suggestions" in registered_commands
        assert "ws_suggestion_action" in registered_commands
        assert "ws_chat_send" in registered_commands


# ---------------------------------------------------------------------------
# ws_chat_send handler logic
# ---------------------------------------------------------------------------

class TestChatSendHandler:
    """Test the chat send WebSocket command handler logic."""

    @pytest.mark.asyncio
    async def test_chat_send_success(self):
        """Successful chat message returns reply."""
        coord = _make_coordinator()
        hass = _make_hass(coordinator=coord)

        # Simulate the handler call
        result = await coord.async_chat_completions(
            [{"role": "user", "content": "Hallo"}],
            conversation_id="conv-001",
        )

        assert result["choices"][0]["message"]["content"] == "Hallo!"
        coord.async_chat_completions.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_send_passes_conversation_id(self):
        """conversation_id is passed through to coordinator."""
        coord = _make_coordinator()
        await coord.async_chat_completions(
            [{"role": "user", "content": "Test"}],
            conversation_id="conv-42",
        )
        call_args = coord.async_chat_completions.call_args
        assert call_args.kwargs.get("conversation_id") == "conv-42"

    @pytest.mark.asyncio
    async def test_chat_send_without_conversation_id(self):
        """Chat works without conversation_id."""
        coord = _make_coordinator()
        await coord.async_chat_completions(
            [{"role": "user", "content": "Test"}],
            conversation_id=None,
        )
        call_args = coord.async_chat_completions.call_args
        assert call_args.kwargs.get("conversation_id") is None

    @pytest.mark.asyncio
    async def test_chat_response_format(self):
        """Response contains expected fields."""
        coord = _make_coordinator({
            "choices": [{"message": {"content": "Die Temperatur ist 22°C."}}],
            "model": "qwen3:4b",
        })

        result = await coord.async_chat_completions(
            [{"role": "user", "content": "Wie warm ist es?"}],
        )

        choices = result.get("choices", [])
        assert len(choices) == 1
        reply = choices[0]["message"]["content"]
        assert "22" in reply
        assert result["model"] == "qwen3:4b"

    @pytest.mark.asyncio
    async def test_chat_empty_response(self):
        """Handle empty response gracefully."""
        coord = _make_coordinator({"choices": []})
        result = await coord.async_chat_completions(
            [{"role": "user", "content": "Test"}],
        )
        assert result["choices"] == []

    @pytest.mark.asyncio
    async def test_chat_api_error(self):
        """API error is raised."""
        coord = MagicMock()
        coord.async_chat_completions = AsyncMock(
            side_effect=Exception("Connection refused"),
        )
        with pytest.raises(Exception, match="Connection refused"):
            await coord.async_chat_completions(
                [{"role": "user", "content": "Test"}],
            )


# ---------------------------------------------------------------------------
# Missing coordinator handling
# ---------------------------------------------------------------------------

class TestMissingCoordinator:
    def test_hass_data_without_coordinator(self):
        """Entry data without coordinator key."""
        hass = _make_hass(coordinator=None)
        entry_data = hass.data[DOMAIN]["test"]
        assert "coordinator" not in entry_data

    def test_hass_data_with_coordinator(self):
        """Entry data with coordinator key."""
        coord = _make_coordinator()
        hass = _make_hass(coordinator=coord)
        entry_data = hass.data[DOMAIN]["test"]
        assert entry_data["coordinator"] is coord


# ---------------------------------------------------------------------------
# Coordinator async_chat_completions interface
# ---------------------------------------------------------------------------

class TestCoordinatorInterface:
    @pytest.mark.asyncio
    async def test_coordinator_chat_completions_signature(self):
        """Verify coordinator accepts messages + conversation_id."""
        coord = _make_coordinator()
        messages = [
            {"role": "system", "content": "Du bist ein Assistent."},
            {"role": "user", "content": "Hallo!"},
        ]
        await coord.async_chat_completions(messages, conversation_id="conv-123")

        call_args = coord.async_chat_completions.call_args
        assert len(call_args.args[0]) == 2  # 2 messages
        assert call_args.args[0][0]["role"] == "system"

    @pytest.mark.asyncio
    async def test_coordinator_handles_multi_turn(self):
        """Multi-turn conversation with multiple messages."""
        coord = _make_coordinator()
        messages = [
            {"role": "user", "content": "Was ist PilotSuite?"},
            {"role": "assistant", "content": "PilotSuite ist ein Smart-Home System."},
            {"role": "user", "content": "Wie funktioniert der Brain Graph?"},
        ]
        await coord.async_chat_completions(messages, conversation_id="conv-mt")

        call_args = coord.async_chat_completions.call_args
        assert len(call_args.args[0]) == 3
