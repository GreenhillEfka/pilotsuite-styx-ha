"""Conversation Context Builder for Styx.

Builds a context-rich system prompt from live HA data so the
conversation agent has full awareness of the home state.

Max ~2000 characters to stay within LLM context budgets.

Path: custom_components/ai_home_copilot/conversation_context.py
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

_MAX_PROMPT_CHARS = 2000


async def async_build_system_prompt(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    language: str = "de",
) -> str:
    """Build a context-rich system prompt for the Styx conversation agent.

    Sections:
      1. Identity + personality
      2. Live mood summary
      3. Zone overview (temperatures, humidity)
      4. Person states
      5. Weather
      6. Pending suggestions (top 3)
      7. Automation analysis summary

    Returns a prompt string, max ~2000 chars.
    """
    parts: list[str] = []

    # 1. Identity
    assistant_name = _get_config(hass, entry, "assistant_name", "Styx")
    home_name = _get_home_name(hass)
    parts.append(
        f"Du bist {assistant_name}, der lokale KI-Assistent fuer SmartHome \"{home_name}\". "
        f"Antworte auf Deutsch, kurz und hilfreich."
    )

    # 2. Live Mood
    mood_str = _build_mood_section(hass, entry)
    if mood_str:
        parts.append(mood_str)

    # 3. Zones
    zone_str = _build_zones_section(hass, entry)
    if zone_str:
        parts.append(zone_str)

    # 4. Persons
    person_str = _build_persons_section(hass)
    if person_str:
        parts.append(person_str)

    # 5. Weather
    weather_str = _build_weather_section(hass)
    if weather_str:
        parts.append(weather_str)

    # 6. Suggestions
    suggestions_str = _build_suggestions_section(hass, entry)
    if suggestions_str:
        parts.append(suggestions_str)

    # 7. Automation analysis
    analysis_str = _build_analysis_section(hass, entry)
    if analysis_str:
        parts.append(analysis_str)

    prompt = "\n".join(parts)

    # Truncate if needed
    if len(prompt) > _MAX_PROMPT_CHARS:
        prompt = prompt[:_MAX_PROMPT_CHARS - 3] + "..."

    return prompt


def _get_config(hass: HomeAssistant, entry: ConfigEntry, key: str, default: str) -> str:
    """Get a config value from entry options or data."""
    val = entry.options.get(key, entry.data.get(key, default))
    return str(val) if val else default


def _get_home_name(hass: HomeAssistant) -> str:
    """Get the home name from HA config."""
    return getattr(hass.config, "location_name", "Zuhause") or "Zuhause"


def _build_mood_section(hass: HomeAssistant, entry: ConfigEntry) -> str:
    """Build mood summary from live_mood data."""
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    if not isinstance(entry_data, dict):
        return ""

    live_mood = entry_data.get("live_mood", {})
    if not live_mood:
        # Fall back to coordinator mood
        coordinator = entry_data.get("coordinator")
        if coordinator and hasattr(coordinator, "data") and coordinator.data:
            mood_data = coordinator.data.get("mood", {})
            if isinstance(mood_data, dict):
                mood = mood_data.get("mood", "unknown")
                conf = mood_data.get("confidence", 0)
                dims = mood_data.get("dimensions", {})
                parts = [f"Stimmung: {mood} ({int(float(conf) * 100)}%)"]
                if isinstance(dims, dict):
                    for k, v in dims.items():
                        parts.append(f"{k}: {int(float(v) * 100)}%")
                return "=== Stimmung === " + " | ".join(parts)
        return ""

    # Aggregate live mood across zones
    comfort_vals = []
    joy_vals = []
    frugality_vals = []
    for zone_data in live_mood.values():
        if isinstance(zone_data, dict):
            comfort_vals.append(zone_data.get("comfort", 0.5))
            joy_vals.append(zone_data.get("joy", 0.5))
            frugality_vals.append(zone_data.get("frugality", 0.5))

    def _avg(vals: list) -> int:
        return int(sum(vals) / len(vals) * 100) if vals else 50

    return (
        f"=== Stimmung === "
        f"Komfort: {_avg(comfort_vals)}% | "
        f"Freude: {_avg(joy_vals)}% | "
        f"Sparsamkeit: {_avg(frugality_vals)}%"
    )


def _build_zones_section(hass: HomeAssistant, entry: ConfigEntry) -> str:
    """Build zone summary with current temperatures."""
    import json
    from pathlib import Path

    # Load zone config
    zones_path = Path(__file__).resolve().parent / "data" / "zones_config.json"
    try:
        raw = json.loads(zones_path.read_text(encoding="utf-8"))
        zones = raw.get("zones", [])
    except Exception:
        return ""

    if not zones:
        return ""

    zone_parts: list[str] = []
    for zone in zones[:12]:
        name = zone.get("name", zone.get("zone_id", "?"))
        entities = zone.get("entities", {})

        temp_eids = entities.get("temperature", [])
        humid_eids = entities.get("humidity", [])

        temp_str = _state_val(hass, temp_eids[0]) if temp_eids else ""
        humid_str = _state_val(hass, humid_eids[0]) if humid_eids else ""

        parts = [name]
        if temp_str:
            parts.append(f"{temp_str}°C")
        if humid_str:
            parts.append(f"{humid_str}%")
        zone_parts.append(", ".join(parts))

    return f"=== Zonen ({len(zones)}) === " + " | ".join(zone_parts)


def _build_persons_section(hass: HomeAssistant) -> str:
    """Build persons summary from person.* entities."""
    persons = []
    for state in hass.states.async_all("person"):
        name = state.attributes.get("friendly_name", state.entity_id.split(".")[-1])
        status = "zuhause" if state.state == "home" else state.state
        persons.append(f"{name}: {status}")
    if not persons:
        return ""
    return "=== Personen === " + " | ".join(persons)


def _build_weather_section(hass: HomeAssistant) -> str:
    """Build weather summary from first weather.* entity."""
    for state in hass.states.async_all("weather"):
        condition = state.state
        temp = state.attributes.get("temperature", "")
        name = state.attributes.get("friendly_name", "Wetter")
        if temp:
            return f"=== Wetter === {condition}, {temp}°C"
        return f"=== Wetter === {condition}"
    return ""


def _build_suggestions_section(hass: HomeAssistant, entry: ConfigEntry) -> str:
    """Build top-3 pending suggestions summary."""
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    if not isinstance(entry_data, dict):
        return ""

    # Try suggestion store / queue
    store = entry_data.get("suggestion_store")
    if store and hasattr(store, "get_pending"):
        pending = store.get_pending()[:3]
        if pending:
            titles = [s.get("title", "?") if isinstance(s, dict) else str(s) for s in pending]
            return f"=== Vorschlaege ({len(pending)}) === " + " | ".join(titles)

    # Fall back to automation analysis suggestions
    analysis = entry_data.get("automation_analysis", {})
    suggestions = analysis.get("suggestions", [])[:3]
    if suggestions:
        titles = [s.get("title", "?") if isinstance(s, dict) else "?" for s in suggestions]
        return f"=== Vorschlaege ({len(suggestions)}) === " + " | ".join(titles)

    return ""


def _build_analysis_section(hass: HomeAssistant, entry: ConfigEntry) -> str:
    """Build automation analysis summary."""
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    if not isinstance(entry_data, dict):
        return ""

    analysis = entry_data.get("automation_analysis", {})
    if not analysis:
        return ""

    total = analysis.get("automation_count", 0)
    hints = len(analysis.get("repair_hints", []))
    if total:
        return f"=== Automationen === {total} gesamt, {hints} Reparatur-Hinweise"
    return ""


def _state_val(hass: HomeAssistant, entity_id: str) -> str:
    """Get a state value, return empty string if unavailable."""
    state = hass.states.get(entity_id)
    if state is None or state.state in ("unknown", "unavailable", ""):
        return ""
    return state.state
