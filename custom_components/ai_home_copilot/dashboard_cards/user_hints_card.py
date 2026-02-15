"""User Hints Dashboard Card for Home Assistant."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class HintCardConfig:
    """Configuration for user hints card."""
    title: str = "💡 Automation Hints"
    show_pending: bool = True
    show_accepted: bool = False
    show_rejected: bool = False
    max_hints: int = 10
    show_confidence: bool = True
    show_entities: bool = True


def generate_hints_card(config: Optional[HintCardConfig] = None) -> Dict[str, Any]:
    """Generate a Lovelace card for user hints."""
    if config is None:
        config = HintCardConfig()
    
    return {
        "type": "custom:user-hints-card",
        "title": config.title,
        "show_pending": config.show_pending,
        "show_accepted": config.show_accepted,
        "show_rejected": config.show_rejected,
        "max_hints": config.max_hints,
        "show_confidence": config.show_confidence,
        "show_entities": config.show_entities,
    }


def generate_hints_panel() -> Dict[str, Any]:
    """Generate a full panel for managing user hints."""
    return {
        "type": "panel",
        "title": "💡 Automation Hints",
        "cards": [
            # Input card for new hints
            {
                "type": "custom:user-hints-input-card",
                "title": "Neuen Hinweis eingeben",
                "placeholder": "z.B. Schalte das Licht im Wohnzimmer an, wenn die Sonne untergeht",
            },
            # Pending hints
            {
                "type": "custom:user-hints-list-card",
                "title": "Offene Vorschläge",
                "filter": "pending",
                "show_actions": True,
            },
            # Accepted hints
            {
                "type": "custom:user-hints-list-card",
                "title": "Aktivierte Automatisierungen",
                "filter": "accepted",
                "show_actions": False,
            },
        ],
    }


def generate_hint_entity_card(hint_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a card for a single hint."""
    confidence = hint_data.get("confidence", 0)
    confidence_color = "green" if confidence >= 0.8 else "yellow" if confidence >= 0.5 else "red"
    
    return {
        "type": "entities",
        "title": f"💡 {hint_data.get('text', 'Hint')[:50]}...",
        "entities": [
            {
                "entity": "sensor.ai_home_copilot_hint_confidence",
                "name": "Confidence",
                "icon": f"mdi:check-circle" if confidence >= 0.8 else "mdi:alert-circle",
                "attribute": None,
            },
        ],
        "footer": {
            "type": "buttons",
            "entities": [
                {
                    "name": "✓ Aktivieren",
                    "service": "ai_home_copilot.accept_hint",
                    "service_data": {"hint_id": hint_data.get("id")},
                },
                {
                    "name": "✗ Ablehnen",
                    "service": "ai_home_copilot.reject_hint",
                    "service_data": {"hint_id": hint_data.get("id")},
                },
            ],
        },
    }


# Lovelace card YAML templates
HINTS_CARD_YAML = """
type: custom:button-card
entity: sensor.ai_home_copilot_hints_pending
name: 💡 Hints
icon: mdi:lightbulb-on
show_state: true
show_name: true
tap_action:
  action: fire-dom-event
  browser_mod:
    service: browser_mod.popup
    data:
      title: Automation Hints
      content:
        type: custom:user-hints-list
        show_pending: true
styles:
  card:
    - background-color: |
        [[[
          if (entity.state > 0) {
            return 'var(--paper-item-icon-active-color, #fdd835)';
          }
          return 'var(--paper-card-background-color)';
        ]]]
"""

HINT_INPUT_YAML = """
type: custom:user-hints-input
title: Was soll automatisiert werden?
placeholder: z.B. Schalte die Kaffeemühle, wenn die Kaffeemaschine an geht
submit_text: Vorschlag erstellen
"""