"""Automation Suggestion Sensor for PilotSuite (v5.9.0).

Exposes automation suggestions count and top recommendations as a HA sensor.
"""
from __future__ import annotations

import logging
from typing import Any

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class AutomationSuggestionSensor(CopilotBaseEntity):
    """Sensor exposing automation suggestions from Core."""

    _attr_name = "Automation Suggestions"
    _attr_icon = "mdi:robot"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "copilot_automation_suggestions"
        self._suggestion_data: dict[str, Any] | None = None

    @property
    def native_value(self) -> str | None:
        """Return suggestion count as state."""
        if self._suggestion_data and self._suggestion_data.get("ok"):
            count = self._suggestion_data.get("count", 0)
            return f"{count} suggestions" if count > 0 else "no suggestions"
        return "unavailable"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return suggestion details."""
        attrs: dict[str, Any] = {
            "suggestions_url": (
                f"{self._core_base_url()}"
                "/api/v1/automations/suggestions"
            ),
        }

        if self._suggestion_data and self._suggestion_data.get("ok"):
            suggestions = self._suggestion_data.get("suggestions", [])
            attrs["total_count"] = self._suggestion_data.get("count", 0)

            # Category breakdown
            categories: dict[str, int] = {}
            for s in suggestions:
                cat = s.get("category", "other")
                categories[cat] = categories.get(cat, 0) + 1
            attrs["by_category"] = categories

            # Top 3 suggestions
            attrs["top_suggestions"] = [
                {
                    "id": s["id"],
                    "title": s["title"],
                    "category": s["category"],
                    "confidence": s["confidence"],
                    "savings_eur": s.get("estimated_savings_eur"),
                }
                for s in suggestions[:3]
            ]

            # Total potential savings
            total_savings = sum(
                s.get("estimated_savings_eur") or 0.0
                for s in suggestions
            )
            attrs["total_potential_savings_eur"] = round(total_savings, 2)

        return attrs

    async def async_update(self) -> None:
        """Fetch suggestions from Core API."""
        try:
            session = self.coordinator._session
            if session is None:
                return

            url = (
                f"{self._core_base_url()}"
                "/api/v1/automations/suggestions"
            )
            headers = self._core_headers()

            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    self._suggestion_data = await resp.json()
                else:
                    _LOGGER.debug("Automation API returned %s", resp.status)
        except Exception as e:
            _LOGGER.debug("Failed to fetch suggestions: %s", e)
