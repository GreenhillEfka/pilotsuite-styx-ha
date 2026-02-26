"""Habitus Zone Dashboard Card - Combines zone overview, mood, and news.

Generates a comprehensive Lovelace dashboard view for each Habitus zone,
including:
  - Zone status and entity summary
  - Current mood per zone (comfort/joy/frugality gauges)
  - Recent patterns and suggestions for the zone
  - Relevant news and warnings
  - Quick actions per zone

This card is the main "Habituszonen-Dashboard" for the HA Frontend,
as opposed to the Core backend dashboard.
"""
from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


def generate_zone_dashboard_view(
    zones: list[dict[str, Any]],
    mood_data: dict[str, Any] | None = None,
    news_items: list[dict[str, Any]] | None = None,
    suggestions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Generate a complete dashboard view with zone cards.

    Args:
        zones: List of zone dicts from habitus_zones_store_v2
        mood_data: Per-zone mood snapshots from Core
        news_items: Regional news/warnings
        suggestions: Active automation suggestions

    Returns:
        Lovelace view configuration dict
    """
    cards: list[dict[str, Any]] = []

    # Overview header
    cards.append(_create_overview_header(zones, mood_data))

    # Zone cards (one per zone)
    for zone in zones:
        zone_id = zone.get("zone_id", "")
        zone_mood = (mood_data or {}).get(zone_id, {})
        zone_suggestions = [
            s for s in (suggestions or [])
            if s.get("zone") == zone_id or s.get("zone_id") == zone_id
        ]
        cards.append(_create_zone_card(zone, zone_mood, zone_suggestions))

    # News and warnings section
    if news_items:
        cards.append(_create_news_card(news_items))

    # Household quick actions
    cards.append(_create_household_actions_card())

    return {
        "title": "Habituszonen",
        "path": "habituszonen",
        "icon": "mdi:home-map-marker",
        "badges": [],
        "cards": cards,
    }


def _create_overview_header(
    zones: list[dict[str, Any]],
    mood_data: dict[str, Any] | None,
) -> dict[str, Any]:
    """Create the overview header card with summary stats."""
    total_entities = sum(len(z.get("entity_ids", [])) for z in zones)
    active_count = sum(1 for z in zones if z.get("current_state") == "active")

    # Overall mood summary
    mood_summary = ""
    if mood_data:
        avg_comfort = 0.0
        avg_joy = 0.0
        count = 0
        for zone_mood in mood_data.values():
            if isinstance(zone_mood, dict):
                avg_comfort += zone_mood.get("comfort", 0)
                avg_joy += zone_mood.get("joy", 0)
                count += 1
        if count > 0:
            mood_summary = (
                f"Komfort: {avg_comfort / count:.0%} | "
                f"Freude: {avg_joy / count:.0%}"
            )

    content = (
        f"## Uebersicht\n\n"
        f"**{len(zones)} Zonen** | {total_entities} Entitaeten | "
        f"{active_count} aktiv\n\n"
    )
    if mood_summary:
        content += f"Stimmung: {mood_summary}\n"

    return {
        "type": "markdown",
        "content": content,
    }


def _create_zone_card(
    zone: dict[str, Any],
    mood: dict[str, Any],
    suggestions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create a card for a single Habitus zone."""
    zone_id = zone.get("zone_id", "?")
    name = zone.get("name", zone_id)
    zone_type = zone.get("zone_type", "room")
    entity_ids = zone.get("entity_ids", [])
    entities_by_role = zone.get("entities", {})
    state = zone.get("current_state", "idle")

    # State icon
    state_icons = {
        "active": "mdi:checkbox-marked-circle",
        "idle": "mdi:sleep",
        "transitioning": "mdi:sync",
        "disabled": "mdi:cancel",
    }

    # Build entity rows (grouped by role)
    entity_rows = []
    for role, role_entities in entities_by_role.items():
        if role_entities:
            for eid in role_entities[:3]:  # Limit to 3 per role
                entity_rows.append({"entity": eid})

    # Fallback: flat entity list
    if not entity_rows and entity_ids:
        for eid in entity_ids[:6]:
            entity_rows.append({"entity": eid})

    # Build the zone card
    zone_cards: list[dict[str, Any]] = []

    # Zone header with mood gauges
    mood_content = f"### {name}\n"
    mood_content += f"Typ: {zone_type} | Status: {state}\n\n"

    if mood:
        comfort = mood.get("comfort", 0)
        joy = mood.get("joy", 0)
        frugality = mood.get("frugality", 0)
        mood_content += (
            f"Komfort: {'█' * int(comfort * 10)}{'░' * (10 - int(comfort * 10))} {comfort:.0%}\n\n"
            f"Freude: {'█' * int(joy * 10)}{'░' * (10 - int(joy * 10))} {joy:.0%}\n\n"
            f"Sparsamkeit: {'█' * int(frugality * 10)}{'░' * (10 - int(frugality * 10))} {frugality:.0%}\n"
        )

    zone_cards.append({"type": "markdown", "content": mood_content})

    # Entity list
    if entity_rows:
        zone_cards.append({
            "type": "entities",
            "entities": entity_rows[:8],
            "show_header_toggle": False,
        })

    # Suggestions for this zone
    if suggestions:
        sugg_content = "#### Vorschlaege\n\n"
        for s in suggestions[:3]:
            sugg_text = s.get("suggestion", "?")
            confidence = s.get("confidence", 0)
            sugg_content += f"- {sugg_text} ({confidence:.0%})\n"
        zone_cards.append({"type": "markdown", "content": sugg_content})

    return {
        "type": "vertical-stack",
        "cards": zone_cards,
    }


def _create_news_card(news_items: list[dict[str, Any]]) -> dict[str, Any]:
    """Create a news/warnings card."""
    content = "## Nachrichten & Warnungen\n\n"
    for item in news_items[:5]:
        title = item.get("title", item.get("headline", ""))
        severity = item.get("severity", "info")
        icon = {"warning": "⚠️", "critical": "🔴", "info": "ℹ️"}.get(severity, "📰")
        content += f"{icon} **{title}**\n\n"
        desc = item.get("description", item.get("text", ""))
        if desc:
            content += f"{desc[:120]}...\n\n"

    return {"type": "markdown", "content": content}


def _create_household_actions_card() -> dict[str, Any]:
    """Create household quick actions card."""
    return {
        "type": "horizontal-stack",
        "cards": [
            {
                "type": "button",
                "name": "Alle Lichter aus",
                "icon": "mdi:lightbulb-off",
                "tap_action": {
                    "action": "call-service",
                    "service": "light.turn_off",
                    "target": {"entity_id": "all"},
                },
            },
            {
                "type": "button",
                "name": "Alles sichern",
                "icon": "mdi:shield-lock",
                "tap_action": {
                    "action": "call-service",
                    "service": "lock.lock",
                    "target": {"entity_id": "all"},
                },
            },
            {
                "type": "button",
                "name": "Gute Nacht",
                "icon": "mdi:weather-night",
                "tap_action": {
                    "action": "call-service",
                    "service": "scene.turn_on",
                    "data": {"entity_id": "scene.gute_nacht"},
                },
            },
        ],
    }
