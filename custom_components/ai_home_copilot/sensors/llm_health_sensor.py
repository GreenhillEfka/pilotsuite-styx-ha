"""LLM Health Sensor — Circuit breaker, usage tracking, provider status.

Exposes detailed LLM provider health including:
- Per-provider circuit breaker state (closed/open/half_open)
- Usage statistics (requests + tokens per provider)
- Provider timeouts and routing info
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class LlmHealthSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing LLM provider health and circuit breaker status."""

    _attr_name = "Styx LLM Health"
    _attr_unique_id = "ai_home_copilot_llm_health"
    _attr_icon = "mdi:brain"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._data: dict[str, Any] = {}

    @property
    def native_value(self) -> str | None:
        provider = self._data.get("active_provider", "none")
        model = self._data.get("primary_model", "")
        if provider == "none":
            return "Offline"
        return f"{provider}: {model}" if model else provider

    @property
    def icon(self) -> str:
        provider = self._data.get("active_provider", "none")
        breakers = self._data.get("circuit_breakers", {})
        # Check if any breaker is open
        for cb in breakers.values():
            if isinstance(cb, dict) and cb.get("state") == "open":
                return "mdi:brain-off"
        if provider == "ollama":
            return "mdi:server"
        if provider == "cloud":
            return "mdi:cloud"
        return "mdi:brain-off"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        breakers = self._data.get("circuit_breakers", {})
        usage = self._data.get("usage", {})
        ollama_cb = breakers.get("ollama", {})
        cloud_cb = breakers.get("cloud", {})
        offline_usage = usage.get("offline", {})
        cloud_usage = usage.get("cloud", {})

        return {
            "active_provider": self._data.get("active_provider", "none"),
            "primary_provider": self._data.get("primary_provider", "offline"),
            "secondary_provider": self._data.get("secondary_provider", "cloud"),
            "primary_model": self._data.get("primary_model", ""),
            "secondary_model": self._data.get("secondary_model", ""),
            "ollama_available": self._data.get("ollama_available", False),
            "cloud_configured": self._data.get("cloud_configured", False),
            "offline_timeout": self._data.get("offline_timeout", 120),
            "cloud_timeout": self._data.get("cloud_timeout", 60),
            # Circuit breakers
            "ollama_circuit_state": ollama_cb.get("state", "unknown"),
            "ollama_circuit_failures": ollama_cb.get("failure_count", 0),
            "cloud_circuit_state": cloud_cb.get("state", "unknown"),
            "cloud_circuit_failures": cloud_cb.get("failure_count", 0),
            # Usage
            "offline_requests": offline_usage.get("requests", 0),
            "offline_tokens": offline_usage.get("tokens", 0),
            "cloud_requests": cloud_usage.get("requests", 0),
            "cloud_tokens": cloud_usage.get("tokens", 0),
        }

    async def async_update(self) -> None:
        session = async_get_clientsession(self.hass)
        base = f"{self._core_base_url()}/chat"
        headers = self._core_headers()

        try:
            async with session.get(
                f"{base}/status", headers=headers, timeout=10
            ) as resp:
                if resp.status == 200:
                    self._data = await resp.json()
                else:
                    self._data["active_provider"] = "none"
        except Exception as exc:
            _LOGGER.debug("Failed to fetch LLM health: %s", exc)
            self._data["active_provider"] = "none"
