"""PilotSuite Conversation Agent for Home Assistant.

Proxies user utterances to the PilotSuite Core Add-on via the
OpenAI-compatible /v1/chat/completions endpoint and returns the
assistant reply as a ConversationResult.

Follows the HA 2024.x+ conversation agent pattern.
"""

from __future__ import annotations

import logging
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

_LOGGER = logging.getLogger(__name__)


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

        if coordinator is None:
            return self._error_result(
                user_input, "PilotSuite coordinator not available."
            )

        api = coordinator.api

        payload: dict[str, Any] = {
            "model": "pilotsuite",
            "messages": [
                {"role": "user", "content": user_input.text},
            ],
        }

        if user_input.conversation_id:
            payload["conversation_id"] = user_input.conversation_id

        try:
            url = f"{api._base_url}/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api._token}"}

            async with api._session.post(
                url, json=payload, headers=headers, timeout=30
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    _LOGGER.error(
                        "PilotSuite API error %s: %s", resp.status, body[:200]
                    )
                    return self._error_result(
                        user_input,
                        f"Core returned status {resp.status}.",
                    )

                data = await resp.json()

        except Exception as err:
            _LOGGER.error("PilotSuite conversation request failed: %s", err)
            return self._error_result(
                user_input, "Could not reach PilotSuite Core."
            )

        # Extract assistant message from OpenAI-compatible response
        choices = data.get("choices", [])
        reply = ""
        if choices:
            message = choices[0].get("message", {})
            reply = message.get("content", "")

        response = intent.IntentResponse(language=user_input.language)
        response.async_set_speech(reply or "No response from PilotSuite.")
        return ConversationResult(response=response, conversation_id=user_input.conversation_id)

    @staticmethod
    def _error_result(
        user_input: ConversationInput, message: str
    ) -> ConversationResult:
        """Build a ConversationResult for error cases."""
        response = intent.IntentResponse(language=user_input.language)
        response.async_set_speech(message)
        return ConversationResult(response=response, conversation_id=user_input.conversation_id)


async def async_setup_conversation(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Register the PilotSuite conversation agent."""
    from homeassistant.components.conversation import async_set_agent

    agent = StyxConversationAgent(hass, entry)
    async_set_agent(hass, entry, agent)
    _LOGGER.info("PilotSuite conversation agent registered")
