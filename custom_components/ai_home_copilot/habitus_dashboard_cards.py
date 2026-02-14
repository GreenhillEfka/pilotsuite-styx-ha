"""
Habitus Dashboard Cards Module
=============================

Provides Lovelace UI card generators for:
- Habitus Zone Status Card (aktuelle Zone, Score)
- Zone Transitions Card (History der Zone-Änderungen)
- Mood Distribution Card (aktuelle Stimmungsverteilung)

These cards follow Lovelace UI patterns and integrate with the existing
habitus_dashboard.py infrastructure.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant

from .habitus_zones_store import HabitusZone, async_get_zones

_LOGGER = logging.getLogger(__name__)


# ============================================================================
# Card Configuration Data Classes
# ============================================================================

@dataclass(frozen=True, slots=True)
class ZoneStatusData:
    """Data for Zone Status Card."""
    zone_id: str
    zone_name: str
    score: float | None = None
    mood: str | None = None
    active_entities: int = 0
    last_activity: str | None = None


@dataclass(frozen=True, slots=True)
class ZoneTransitionData:
    """Data for Zone Transition Card."""
    timestamp: str
    from_zone: str | None
    to_zone: str
    trigger: str | None
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class MoodDistributionData:
    """Data for Mood Distribution Card."""
    mood: str
    count: int
    percentage: float
    zone_name: str


# ============================================================================
# Card YAML Generators
# ============================================================================

def _card_header(title: str, icon: str | None = None) -> str:
    """Generate card header YAML."""
    lines = [
        "    - type: custom:hui-card",
        f"      title: {title}",
    ]
    if icon:
        lines.append(f"      icon: {icon}")
    return "\n".join(lines)


def _gauge_card(entity_id: str, title: str, min_val: float = 0, max_val: float = 100) -> str:
    """Generate a gauge card YAML."""
    return f"""    - type: gauge
      entity: {entity_id}
      title: {title}
      min: {min_val}
      max: {max_val}
      severity:
        green: 70
        yellow: 40
        red: 20"""


def _stat_card(
    entity_id: str | None,
    title: str,
    value: str | None = None,
    icon: str | None = None,
    unit: str | None = None,
) -> str:
    """Generate a stat card YAML."""
    lines = [
        "    - type: statistic",
    ]
    if entity_id:
        lines.append(f"      entity: {entity_id}")
    lines.append(f"      title: {title}")
    if value:
        lines.append(f"      value: {value}")
    if icon:
        lines.append(f"      icon: {icon}")
    if unit:
        lines.append(f"      unit: {unit}")
    return "\n".join(lines)


def _entities_card(title: str, entities: list[str]) -> str:
    """Generate an entities card YAML."""
    lines = [
        "    - type: entities",
        f"      title: {title}",
        "      show_header_toggle: false",
        "      entities:",
    ]
    if not entities:
        lines.append("        - type: section")
        lines.append("          label: (keine)")
    else:
        for eid in entities:
            lines.append(f"        - entity: {eid}")
    return "\n".join(lines)


def _history_graph_card(title: str, entities: list[str], hours: int = 24) -> str:
    """Generate a history-graph card YAML."""
    lines = [
        "    - type: history-graph",
        f"      title: {title}",
        f"      hours_to_show: {hours}",
        "      entities:",
    ]
    if not entities:
        lines.append("        - sensor.time")
    else:
        for eid in entities[:12]:
            lines.append(f"        - {eid}")
    return "\n".join(lines)


def _markdown_card(title: str, content: str) -> str:
    """Generate a markdown card YAML."""
    lines = [
        "    - type: markdown",
        f"      title: {title}",
        "      content: |",
    ]
    for line in content.strip().splitlines():
        lines.append(f"        {line}")
    return "\n".join(lines)


def _vertical_stack_card(cards: list[str]) -> str:
    """Wrap cards in a vertical-stack."""
    return """    - type: vertical-stack
""" + "\n".join(cards)


def _grid_card(cards: list[str], columns: int = 2) -> str:
    """Generate a grid card with columns."""
    nested = []
    for card in cards:
        # Strip leading indentation and add proper grid nesting
        lines = card.strip().splitlines()
        if lines and lines[0].startswith("    - "):
            lines[0] = "      - " + lines[0][6:]
        nested.append("\n".join(lines))

    return f"""    - type: grid
      columns: {columns}
      square: false
      cards:
""" + "\n".join(nested)


# ============================================================================
# Habitus Zone Status Card
# ============================================================================

def generate_zone_status_card_yaml(
    zones: list[HabitusZone],
    active_zone_id: str | None = None,
    score_entity_id: str | None = None,
    mood_entity_id: str | None = None,
) -> str:
    """Generate Zone Status Card YAML.

    Args:
        zones: List of Habitus zones
        active_zone_id: Currently active zone ID
        score_entity_id: Entity ID for zone score sensor
        mood_entity_id: Entity ID for mood sensor

    Returns:
        YAML string for the card
    """
    cards: list[str] = []

    # Header with current status
    if active_zone_id:
        active_zone = next((z for z in zones if z.zone_id == active_zone_id), None)
        zone_name = active_zone.name if active_zone else active_zone_id
        status_content = f"**Aktive Zone:** {zone_name}"
    else:
        status_content = "**Keine aktive Zone**"

    cards.append(_markdown_card("Aktueller Status", status_content))

    # Zone selector (dropdown)
    zone_entities = [
        f"sensor.ai_home_copilot_zone_{z.zone_id}_status" for z in zones
    ]
    if zone_entities:
        cards.append(_entities_card("Zonen", zone_entities))

    # Score gauge (if available)
    if score_entity_id:
        cards.append(_gauge_card(score_entity_id, "Zone Score", 0, 100))

    # Current mood stat
    if mood_entity_id:
        cards.append(_stat_card(mood_entity_id, "Stimmung", icon="mdi:emoticon-outline"))

    # Grid of zone indicators
    zone_cards = []
    for z in zones:
        is_active = z.zone_id == active_zone_id
        state = "aktiv" if is_active else "inaktiv"
        icon = "mdi:home-circle" if is_active else "mdi:home-circle-outline"

        zone_card = _stat_card(
            entity_id=f"sensor.ai_home_copilot_zone_{z.zone_id}_score",
            title=z.name,
            value=state,
            icon=icon,
        )
        zone_cards.append(zone_card)

    if zone_cards:
        cards.append(_grid_card(zone_cards, columns=min(len(zone_cards), 4)))

    return _vertical_stack_card(cards)


def generate_zone_status_card_simple(active_zone: str, score: float | None = None) -> str:
    """Generate simple Zone Status Card YAML (standalone version).

    Args:
        active_zone: Name of the active zone
        score: Optional score value

    Returns:
        YAML string for the card
    """
    cards: list[str] = []

    # Header
    cards.append(_markdown_card("Habitus Zone", f"**Aktiv:** {active_zone}"))

    # Score if available
    if score is not None:
        cards.append(_gauge_card("sensor.ai_home_copilot_zone_score", "Zone Score", 0, 100))

    return _vertical_stack_card(cards)


# ============================================================================
# Zone Transitions Card
# ============================================================================

def generate_zone_transitions_card_yaml(
    transitions: list[ZoneTransitionData],
    max_entries: int = 10,
) -> str:
    """Generate Zone Transitions History Card YAML.

    Args:
        transitions: List of transition events
        max_entries: Maximum number of entries to show

    Returns:
        YAML string for the card
    """
    cards: list[str] = []

    # Header
    cards.append(_markdown_card("Zone Transitions", "**Letzte Zone-Änderungen**"))

    # Recent transitions timeline
    transition_lines = []
    for t in transitions[:max_entries]:
        from_str = t.from_zone or "unbekannt"
        to_str = t.to_zone
        time_str = t.timestamp.split("T")[1][:8] if "T" in t.timestamp else t.timestamp
        trigger_str = f" → *{t.trigger}*" if t.trigger else ""

        transition_lines.append(f"- *{time_str}*: {from_str} → {to_str}{trigger_str}")

    if not transition_lines:
        transition_lines.append("- Keine Übergänge aufgezeichnet")

    content = "\n".join(transition_lines)
    cards.append(_markdown_card("Verlauf (letzte 24h)", content))

    # History graph (if sensor entities exist)
    graph_entities = [f"sensor.ai_home_copilot_zone_{t.to_zone}" for t in transitions[:5]]
    if graph_entities:
        cards.append(_history_graph_card("Zone-Historie", graph_entities, hours=24))

    return _vertical_stack_card(cards)


def generate_zone_transitions_card_simple(last_transition: ZoneTransitionData | None = None) -> str:
    """Generate simple Zone Transitions Card YAML (standalone version).

    Args:
        last_transition: Last zone transition event

    Returns:
        YAML string for the card
    """
    cards: list[str] = []

    cards.append(_markdown_card("Zone Transition", "**Letzter Übergang:**"))

    if last_transition:
        from_str = last_transition.from_zone or "unbekannt"
        to_str = last_transition.to_zone
        content = f"""**Von:** {from_str}
**Nach:** {to_str}
**Zeit:** {last_transition.timestamp}
**Trigger:** {last_transition.trigger or "unbekannt"}"""
    else:
        content = "Keine Übergänge aufgezeichnet"

    cards.append(_markdown_card("Details", content))

    return _vertical_stack_card(cards)


# ============================================================================
# Mood Distribution Card
# ============================================================================

def generate_mood_distribution_card_yaml(
    mood_data: list[MoodDistributionData],
    current_mood_entity_id: str | None = None,
) -> str:
    """Generate Mood Distribution Card YAML.

    Args:
        mood_data: List of mood distribution data per zone
        current_mood_entity_id: Entity ID for current mood sensor

    Returns:
        YAML string for the card
    """
    cards: list[str] = []

    # Header
    cards.append(_markdown_card("Stimmungsverteilung", "**Aktuelle Mood-Verteilung nach Zone**"))

    # Mood breakdown table
    mood_lines = []
    for m in mood_data:
        bar = "█" * int(m.percentage / 10)
        mood_lines.append(f"- **{m.zone_name}:** {m.mood} ({m.percentage:.1f}%) {bar}")

    if not mood_lines:
        mood_lines.append("- Keine Daten verfügbar")

    content = "\n".join(mood_lines)
    cards.append(_markdown_card("Verteilung", content))

    # Pie chart-like visualization using bars
    pie_cards = []
    for m in mood_data:
        color_map = {
            "relax": "#4CAF50",
            "focus": "#2196F3",
            "energy": "#FF9800",
            "sleep": "#3F51B5",
            "party": "#E91E63",
            "default": "#9E9E9E",
        }
        color = color_map.get(m.mood.lower(), color_map["default"])

        bar_card = f"""        - type: custom:bar-card
          entity: sensor.ai_home_copilot_mood_{m.zone_id}
          title: {m.zone_name}
          direction: rtl
          value: {m.mood}
          min: 0
          max: 100
          card_style:
            background: {color}"""
        pie_cards.append(bar_card)

    if pie_cards:
        grid_content = "    - type: grid\n      columns: 2\n      square: false\n      cards:\n" + "\n".join(pie_cards)
        cards.append(grid_content)

    # Current mood stat
    if current_mood_entity_id:
        cards.append(_stat_card(current_mood_entity_id, "Aktuelle Stimmung", icon="mdi:emoticon-happy"))

    return _vertical_stack_card(cards)


def generate_mood_distribution_card_simple(
    mood_counts: dict[str, int],
    total_zones: int,
) -> str:
    """Generate simple Mood Distribution Card YAML (standalone version).

    Args:
        mood_counts: Dictionary of mood -> count
        total_zones: Total number of zones

    Returns:
        YAML string for the card
    """
    cards: list[str] = []

    cards.append(_markdown_card("Mood Verteilung", "**Stimmungsverteilung im Zuhause**"))

    mood_lines = []
    for mood, count in mood_counts.items():
        percentage = (count / total_zones * 100) if total_zones > 0 else 0
        bar = "█" * int(percentage / 5)
        mood_lines.append(f"- **{mood}:** {count} Zone(n) ({percentage:.0f}%) {bar}")

    if not mood_lines:
        mood_lines.append("- Keine Daten verfügbar")

    content = "\n".join(mood_lines)
    cards.append(_markdown_card("Übersicht", content))

    return _vertical_stack_card(cards)


# ============================================================================
# Combined Dashboard View Generator
# ============================================================================

def generate_habitus_dashboard_view(
    zones: list[HabitusZone],
    active_zone_id: str | None = None,
    transitions: list[ZoneTransitionData] | None = None,
    mood_data: list[MoodDistributionData] | None = None,
    score_entity_id: str | None = None,
    mood_entity_id: str | None = None,
) -> str:
    """Generate complete Habitus Dashboard view YAML.

    Args:
        zones: List of Habitus zones
        active_zone_id: Currently active zone
        transitions: List of recent transitions
        mood_data: Mood distribution data
        score_entity_id: Zone score sensor entity
        mood_entity_id: Current mood sensor entity

    Returns:
        YAML string for the complete dashboard view
    """
    view_cards: list[str] = []

    # Row 1: Status overview
    status_card = generate_zone_status_card_yaml(
        zones=zones,
        active_zone_id=active_zone_id,
        score_entity_id=score_entity_id,
        mood_entity_id=mood_entity_id,
    )
    view_cards.append(status_card)

    # Row 2: Transitions (if available)
    if transitions:
        transitions_card = generate_zone_transitions_card_yaml(transitions)
        view_cards.append(transitions_card)

    # Row 3: Mood distribution (if available)
    if mood_data:
        mood_card = generate_mood_distribution_card_yaml(
            mood_data=mood_data,
            current_mood_entity_id=mood_entity_id,
        )
        view_cards.append(mood_card)

    return _vertical_stack_card(view_cards)


# ============================================================================
# Helper Functions
# ============================================================================

async def get_active_zone_id(hass: HomeAssistant, entry_id: str) -> str | None:
    """Get the currently active Habitus zone."""
    zones = await async_get_zones(hass, entry_id)

    for z in zones:
        # Check for motion/presence activity in the zone
        motion_entities = z.entities.get("motion") if z.entities else []
        for entity_id in motion_entities[:3]:  # Check first 3 motion sensors
            state = hass.states.get(entity_id)
            if state and state.state == "on":
                return z.zone_id

    return None


def calculate_zone_score(z: HabitusZone, hass: HomeAssistant) -> float | None:
    """Calculate a simple zone score based on entity states.

    Args:
        z: Habitus zone
        hass: Home Assistant instance

    Returns:
        Score between 0-100 or None if not calculable
    """
    active_count = 0
    total_count = len(z.entity_ids)

    if total_count == 0:
        return None

    for entity_id in z.entity_ids:
        state = hass.states.get(entity_id)
        if state and state.state not in ("unavailable", "unknown", "off"):
            active_count += 1

    return round((active_count / total_count) * 100, 1)


def aggregate_mood_distribution(
    zones: list[HabitusZone],
    zone_moods: dict[str, str],
) -> list[MoodDistributionData]:
    """Aggregate mood distribution across zones.

    Args:
        zones: List of Habitus zones
        zone_moods: Dictionary mapping zone_id to mood

    Returns:
        List of MoodDistributionData sorted by percentage
    """
    mood_counts: dict[str, int] = {}
    zone_mood_map: dict[str, str] = {}

    for z in zones:
        mood = zone_moods.get(z.zone_id, "unknown")
        zone_mood_map[z.zone_id] = mood
        mood_counts[mood] = mood_counts.get(mood, 0) + 1

    total = len(zones)
    if total == 0:
        return []

    result: list[MoodDistributionData] = []
    for mood, count in mood_counts.items():
        percentage = (count / total) * 100
        # Get zone name for this mood (first zone with this mood)
        zone_name = next((z.name for z in zones if zone_moods.get(z.zone_id) == mood), mood)
        result.append(MoodDistributionData(
            mood=mood,
            count=count,
            percentage=percentage,
            zone_name=zone_name,
        ))

    return sorted(result, key=lambda x: x.percentage, reverse=True)
