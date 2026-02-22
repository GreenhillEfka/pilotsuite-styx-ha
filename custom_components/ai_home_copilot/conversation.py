"""PilotSuite Conversation Agent for Home Assistant.

Proxies user utterances to the PilotSuite Core Add-on via the
OpenAI-compatible /v1/chat/completions endpoint and returns the
assistant reply as a ConversationResult.

Follows the HA 2024.x+ conversation agent pattern.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from homeassistant.components.conversation import (
    AbstractConversationAgent,
    ConversationInput,
    ConversationResult,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent

from .const import DOMAIN
from .coordinator import CopilotApiError

_LOGGER = logging.getLogger(__name__)
_CONVERSATION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _normalize_conversation_id(value: Any) -> str:
    """Return a safe conversation id that satisfies frontend/API expectations."""
    if isinstance(value, str):
        candidate = value.strip()
        if _CONVERSATION_ID_RE.fullmatch(candidate):
            return candidate
    # 26 chars to align with common ULID-like conversation ids.
    return uuid.uuid4().hex[:26]


class StyxConversationAgent(AbstractConversationAgent):
    """Conversation agent that proxies to PilotSuite Core."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.entry = entry

    @property
    def supported_languages(self) -> list[str]:
        """Return supported languages."""
        return ["de", "en"]

    async def async_process(
        self, user_input: ConversationInput
    ) -> ConversationResult:
        """Process a user utterance via PilotSuite Core."""
        entry_data = self.hass.data.get(DOMAIN, {}).get(self.entry.entry_id, {})
        coordinator = entry_data.get("coordinator")
        conversation_id = _normalize_conversation_id(user_input.conversation_id)

        if coordinator is None:
            return self._error_result(
                user_input, "PilotSuite coordinator not available.", conversation_id
            )

        messages = [{"role": "user", "content": user_input.text}]

        try:
            result = await coordinator.api.async_chat_completions(
                messages=messages,
                conversation_id=conversation_id,
            )
        except CopilotApiError as err:
            _LOGGER.error("PilotSuite API error: %s", err)
            return self._error_result(
                user_input, f"Core returned an error: {err}", conversation_id
            )
        except TimeoutError:
            _LOGGER.error("PilotSuite conversation request timed out")
            return self._error_result(
                user_input, "Request to PilotSuite Core timed out.", conversation_id
            )
        except Exception as err:
            _LOGGER.error("PilotSuite conversation request failed: %s", err)
            return self._error_result(
                user_input, "Could not reach PilotSuite Core.", conversation_id
            )

        reply = result.get("content", "")
        response = intent.IntentResponse(language=user_input.language)
        response.async_set_speech(reply or "No response from PilotSuite.")
        return ConversationResult(
            response=response,
            conversation_id=conversation_id,
        )

    @staticmethod
    def _error_result(
        user_input: ConversationInput,
        message: str,
        conversation_id: str,
    ) -> ConversationResult:
        """Build a ConversationResult for error cases."""
        response = intent.IntentResponse(language=user_input.language)
        response.async_set_speech(message)
        return ConversationResult(
            response=response,
            conversation_id=conversation_id,
        )


async def async_setup_conversation(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Register the PilotSuite conversation agent."""
    from homeassistant.components.conversation import async_set_agent

    agent = StyxConversationAgent(hass, entry)
    async_set_agent(hass, entry, agent)
    _LOGGER.info("PilotSuite conversation agent registered")


async def async_unload_conversation(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Unregister the PilotSuite conversation agent."""
    from homeassistant.components.conversation import async_unset_agent

    async_unset_agent(hass, entry)
    _LOGGER.info("PilotSuite conversation agent unregistered")
