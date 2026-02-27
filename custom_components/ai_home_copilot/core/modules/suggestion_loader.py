"""Suggestion Loader Module — populates the SuggestionQueue from all sources.

Sources:
  1. data/initial_suggestions.json (loaded once, flagged)
  2. Event: ai_home_copilot_automation_analysis_complete
     → Converts ImprovementSuggestion → Suggestion → Queue
  3. Event: ai_home_copilot_proactive_suggestion (Webhook from Core)
     → Payload → Suggestion → Queue
  4. Event: ai_home_copilot_suggestion_received (Core polling)
     → Candidate → Suggestion → Queue

Deduplicates by suggestion pattern to avoid flooding the queue.

Path: custom_components/ai_home_copilot/core/modules/suggestion_loader.py
"""
from __future__ import annotations

import json
import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback

from ...const import DOMAIN
from ..module import CopilotModule, ModuleContext

_LOGGER = logging.getLogger(__name__)

_INITIAL_SUGGESTIONS_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "initial_suggestions.json"
)

# Priority mapping from severity strings
_SEVERITY_TO_PRIORITY = {
    "critical": "high",
    "high": "high",
    "warning": "medium",
    "medium": "medium",
    "info": "low",
    "low": "low",
}


class SuggestionLoaderModule(CopilotModule):
    """Loads suggestions from multiple sources into the SuggestionQueue."""

    @property
    def name(self) -> str:
        return "suggestion_loader"

    @property
    def version(self) -> str:
        return "1.0"

    def __init__(self) -> None:
        self._unsub_callbacks: list = []
        self._loaded_patterns: set[str] = set()

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        hass: HomeAssistant = ctx.hass
        entry: ConfigEntry = ctx.entry
        entry_id = entry.entry_id

        # 1. Load initial suggestions (once)
        entry_data = hass.data.setdefault(DOMAIN, {}).setdefault(entry_id, {})
        if not entry_data.get("_initial_suggestions_loaded"):
            count = await self._load_initial_suggestions(hass, entry_id)
            entry_data["_initial_suggestions_loaded"] = True
            if count:
                _LOGGER.info("Loaded %d initial suggestions into queue", count)

        # 2. Listen for automation analysis completion
        @callback
        def _on_analysis_complete(event: Event) -> None:
            evt_entry_id = event.data.get("entry_id", entry_id)
            if str(evt_entry_id) != entry_id:
                return
            hass.async_create_task(
                self._load_from_analysis(hass, entry_id)
            )

        unsub1 = hass.bus.async_listen(
            f"{DOMAIN}_automation_analysis_complete",
            _on_analysis_complete,
        )
        self._unsub_callbacks.append(unsub1)

        # 3. Listen for proactive suggestions from Core (webhook)
        @callback
        def _on_proactive_suggestion(event: Event) -> None:
            suggestion_data = event.data
            hass.async_create_task(
                self._load_proactive(hass, entry_id, suggestion_data)
            )

        unsub2 = hass.bus.async_listen(
            f"{DOMAIN}_proactive_suggestion",
            _on_proactive_suggestion,
        )
        self._unsub_callbacks.append(unsub2)

        # 4. Listen for suggestion_received from Core polling
        @callback
        def _on_suggestion_received(event: Event) -> None:
            suggestion_data = event.data
            hass.async_create_task(
                self._load_proactive(hass, entry_id, suggestion_data)
            )

        unsub3 = hass.bus.async_listen(
            f"{DOMAIN}_suggestion_received",
            _on_suggestion_received,
        )
        self._unsub_callbacks.append(unsub3)

        _LOGGER.info("SuggestionLoaderModule initialized (patterns tracked: %d)", len(self._loaded_patterns))

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        for unsub in self._unsub_callbacks:
            unsub()
        self._unsub_callbacks.clear()
        return True

    # ------------------------------------------------------------------
    # Source 1: initial_suggestions.json
    # ------------------------------------------------------------------

    async def _load_initial_suggestions(
        self, hass: HomeAssistant, entry_id: str,
    ) -> int:
        """Load initial suggestions from data/initial_suggestions.json."""
        try:
            raw = await hass.async_add_executor_job(self._read_initial_json)
        except Exception:
            _LOGGER.debug("Could not read initial_suggestions.json")
            return 0

        if not raw:
            return 0

        suggestions_raw = raw.get("suggestions", [])
        store = self._get_store(hass, entry_id)
        if not store:
            _LOGGER.debug("SuggestionStore not available yet, skipping initial load")
            return 0

        count = 0
        for item in suggestions_raw:
            suggestion = self._convert_initial_to_suggestion(item)
            if suggestion and self._is_new(suggestion):
                store.queue.add(suggestion)
                self._loaded_patterns.add(suggestion.get("pattern", ""))
                count += 1

        if count:
            await store.async_save()
        return count

    @staticmethod
    def _read_initial_json() -> dict[str, Any]:
        if not _INITIAL_SUGGESTIONS_PATH.exists():
            return {}
        return json.loads(_INITIAL_SUGGESTIONS_PATH.read_text(encoding="utf-8"))

    @staticmethod
    def _convert_initial_to_suggestion(item: dict[str, Any]) -> dict[str, Any] | None:
        """Convert an initial_suggestions.json entry to a Suggestion-compatible dict."""
        suggestion_id = item.get("id", "")
        if not suggestion_id:
            return None

        title = item.get("title", "")
        description = item.get("description", "")
        severity = item.get("severity", "medium")
        affected = item.get("affected_entities", [])
        example_yaml = item.get("example_yaml", "")
        suggestion_type = item.get("type", "general")

        return {
            "suggestion_id": f"initial_{suggestion_id}",
            "pattern": title,
            "confidence": 0.7 if severity in ("critical", "high") else 0.5,
            "lift": 1.0,
            "support": 1,
            "source": suggestion_type,
            "zone_entities": affected,
            "priority": _SEVERITY_TO_PRIORITY.get(severity, "medium"),
            "evidence": [{"yaml": example_yaml}] if example_yaml else [],
            "risk_level": "low",
        }

    # ------------------------------------------------------------------
    # Source 2: automation_analysis suggestions
    # ------------------------------------------------------------------

    async def _load_from_analysis(
        self, hass: HomeAssistant, entry_id: str,
    ) -> None:
        """Load improvement suggestions from automation analysis results."""
        entry_data = hass.data.get(DOMAIN, {}).get(entry_id, {})
        if not isinstance(entry_data, dict):
            return

        analysis = entry_data.get("automation_analysis", {})
        suggestions = analysis.get("suggestions", [])

        store = self._get_store(hass, entry_id)
        if not store:
            return

        count = 0
        for item in suggestions:
            suggestion = self._convert_analysis_to_suggestion(item)
            if suggestion and self._is_new(suggestion):
                store.queue.add(suggestion)
                self._loaded_patterns.add(suggestion.get("pattern", ""))
                count += 1

        if count:
            await store.async_save()
            _LOGGER.info("Loaded %d suggestions from automation analysis", count)

    @staticmethod
    def _convert_analysis_to_suggestion(item: dict[str, Any]) -> dict[str, Any] | None:
        """Convert an ImprovementSuggestion dict to Suggestion format."""
        title = item.get("title", "")
        if not title:
            return None

        zone_id = item.get("zone_id", "")
        return {
            "suggestion_id": f"analysis_{zone_id}_{item.get('suggestion_type', 'general')}",
            "pattern": title,
            "confidence": 0.6,
            "lift": 1.0,
            "support": 1,
            "source": "automation_analysis",
            "zone_id": zone_id,
            "priority": "medium",
            "evidence": [{"yaml": item.get("example_yaml", "")}],
            "risk_level": "low",
        }

    # ------------------------------------------------------------------
    # Source 3+4: proactive / webhook suggestions
    # ------------------------------------------------------------------

    async def _load_proactive(
        self, hass: HomeAssistant, entry_id: str, data: dict[str, Any],
    ) -> None:
        """Load a proactive suggestion from an event payload."""
        store = self._get_store(hass, entry_id)
        if not store:
            return

        suggestion = {
            "suggestion_id": data.get("suggestion_id", data.get("id", "")),
            "pattern": data.get("title", data.get("pattern", "")),
            "confidence": data.get("confidence", 0.5),
            "lift": data.get("lift", 1.0),
            "support": data.get("support", 1),
            "source": data.get("source", "core"),
            "zone_id": data.get("zone_id", ""),
            "priority": data.get("priority", "medium"),
            "evidence": data.get("evidence", []),
            "risk_level": data.get("risk_level", "medium"),
        }

        if suggestion["suggestion_id"] and self._is_new(suggestion):
            store.queue.add(suggestion)
            self._loaded_patterns.add(suggestion["pattern"])
            await store.async_save()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_new(self, suggestion: dict[str, Any]) -> bool:
        """Check if a suggestion pattern is new (dedup)."""
        pattern = suggestion.get("pattern", "")
        return bool(pattern and pattern not in self._loaded_patterns)

    @staticmethod
    def _get_store(hass: HomeAssistant, entry_id: str):
        """Get the SuggestionPanelStore from hass.data."""
        entry_data = hass.data.get(DOMAIN, {}).get(entry_id, {})
        if isinstance(entry_data, dict):
            return entry_data.get("suggestion_store")
        return None
