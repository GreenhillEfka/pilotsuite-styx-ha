"""
Camera Dashboard Cards for AI Home CoPilot.

Provides dashboard cards for:
- Camera Status Card
- Motion History Card
- Zone Activity Card
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .habitus_dashboard_store import HabitusDashboardState, async_get_state, async_set_state
from .habitus_zones_store import async_get_zones, HabitusZone

_LOGGER = logging.getLogger(__name__)


def _camera_status_card_yaml(cameras: List[str]) -> str:
    """Create a camera status card."""
    if not cameras:
        return ""
    
    lines = [
        "      - type: vertical-stack",
        "        title: Kameras",
        "        cards:",
    ]
    
    for cam in cameras[:6]:  # Max 6 cameras
        lines.extend([
            f"          - type: entity",
            f"            entity: {cam}",
            f"            name: {cam.split('.')[-1].replace('_', ' ').title()}",
        ])
    
    return "\n".join(lines)


def _motion_history_card_yaml(sensors: List[str]) -> str:
    """Create a motion history card."""
    lines = [
        "      - type: gauge",
        "        title: Bewegungserkennung (24h)",
        "        entity: sensor.ai_home_copilot_camera_motion_history",
        "        min: 0",
        "        max: 100",
        "        severity:",
        "          green: 0",
        "          yellow: 20",
        "          red: 50",
    ]
    return "\n".join(lines)


def _presence_history_card_yaml() -> str:
    """Create a presence history card."""
    lines = [
        "      - type: gauge",
        "        title: Präsenz-Erkennungen (24h)",
        "        entity: sensor.ai_home_copilot_camera_presence_history",
        "        min: 0",
        "        max: 50",
        "        severity:",
        "          green: 0",
        "          yellow: 10",
        "          red: 30",
    ]
    return "\n".join(lines)


def _activity_history_card_yaml() -> str:
    """Create an activity history card."""
    lines = [
        "      - type: gauge",
        "        title: Aktivitäten (24h)",
        "        entity: sensor.ai_home_copilot_camera_activity_history",
        "        min: 0",
        "        max: 100",
        "        severity:",
        "          green: 0",
        "          yellow: 30",
        "          red: 70",
    ]
    return "\n".join(lines)


def _zone_activity_card_yaml() -> str:
    """Create a zone activity card."""
    lines = [
        "      - type: gauge",
        "        title: Zonen-Aktivität (24h)",
        "        entity: sensor.ai_home_copilot_camera_zone_activity",
        "        min: 0",
        "        max: 50",
        "        severity:",
        "          green: 0",
        "          yellow: 15",
        "          red: 40",
    ]
    return "\n".join(lines)


def _camera_entities_yaml(cameras: List[str]) -> str:
    """Create an entities card showing all camera sensors."""
    if not cameras:
        return ""
    
    lines = [
        "      - type: entities",
        "        title: Kamera-Sensoren",
        "        show_header_toggle: false",
        "        entities:",
    ]
    
    for cam in cameras[:8]:
        cam_id = cam.split(".")[-1]
        lines.extend([
            f"          - entity: binary_sensor.ai_home_copilot_motion_{cam_id}",
            f"            name: Bewegung {cam.split('.')[-1].replace('_', ' ').title()}",
            f"          - entity: binary_sensor.ai_home_copilot_presence_{cam_id}",
            f"            name: Präsenz {cam.split('.')[-1].replace('_', ' ').title()}",
        ])
    
    return "\n".join(lines)


def _camera_summary_yaml(motion_count: int, presence_count: int, activity_count: int, zone_count: int) -> str:
    """Create a summary card for camera stats."""
    lines = [
        "      - type: markdown",
        "        title: Kamera-Übersicht",
        "        content: |",
        f"          ## 📷 Kamera-Übersicht",
        f"",
        f"          - **Bewegungen (24h):** {motion_count}",
        f"          - **Präsenzen (24h):** {presence_count}",
        f"          - **Aktivitäten (24h):** {activity_count}",
        f"          - **Zonen-Events (24h):** {zone_count}",
    ]
    return "\n".join(lines)


async def generate_camera_dashboard_yaml(
    hass: HomeAssistant,
    entry_id: str,
) -> str:
    """Generate complete camera dashboard YAML."""
    
    # Get camera sensors
    camera_sensors = [
        "sensor.ai_home_copilot_camera_motion_history",
        "sensor.ai_home_copilot_camera_presence_history", 
        "sensor.ai_home_copilot_camera_activity_history",
        "sensor.ai_home_copilot_camera_zone_activity",
    ]
    
    # Get motion cameras
    motion_cameras = [
        eid for eid in hass.states.async_entity_ids("binary_sensor")
        if "ai_home_copilot_motion" in eid
    ]
    
    # Get camera entities
    camera_entities = [
        eid for eid in hass.states.async_entity_ids("camera")
    ]
    
    # Try to get counts from sensors
    motion_count = 0
    presence_count = 0
    activity_count = 0
    zone_count = 0
    
    motion_state = hass.states.get("sensor.ai_home_copilot_camera_motion_history")
    if motion_state and motion_state.state.isdigit():
        motion_count = int(motion_state.state)
    
    presence_state = hass.states.get("sensor.ai_home_copilot_camera_presence_history")
    if presence_state and presence_state.state.isdigit():
        presence_count = int(presence_state.state)
        
    activity_state = hass.states.get("sensor.ai_home_copilot_camera_activity_history")
    if activity_state and activity_state.state.isdigit():
        activity_count = int(activity_state.state)
        
    zone_state = hass.states.get("sensor.ai_home_copilot_camera_zone_activity")
    if zone_state and zone_state.state.isdigit():
        zone_count = int(zone_state.state)
    
    yaml_content = f"""title: AI Home CoPilot Kamera
path: ai-home-copilot-camera
icon: mdi:cctv

cards:
  - type: vertical-stack
    title: 📷 Kamera-Status
    cards:
{y _camera_summary_yaml(motion_count, presence_count, activity_count, zone_count)}

  - type: horizontal-stack
    cards:
{motion_history_card_yaml()}
      - type: vertical-stack
{presence_history_card_yaml()}

  - type: horizontal-stack
    cards:
{activity_history_card_yaml()}
      - type: vertical-stack
{zone_activity_card_yaml()}

  - type: entities
    title: Bewegungserkennung
    entities:
"""
    
    # Add motion cameras
    for cam in motion_cameras[:6]:
        yaml_content += f"      - {cam}\n"
    
    if not motion_cameras:
        yaml_content += "      - type: section\n        label: Keine Kameras konfiguriert\n"
    
    yaml_content += """
  - type: entities
    title: Kamera-Übersicht
    entities:
"""
    
    # Add all camera entities
    for cam in camera_entities[:8]:
        yaml_content += f"      - {cam}\n"
    
    if not camera_entities:
        yaml_content += "      - type: section\n        label: Keine Kameras verfügbar\n"
    
    return yaml_content


# Helper functions need to be defined before use
def motion_history_card_yaml() -> str:
    return _motion_history_card_yaml([])


# Fix the import issue - generate inline
async def generate_camera_dashboard_v2_yaml(
    hass: HomeAssistant,
    entry_id: str,
) -> str:
    """Generate camera dashboard YAML (v2 with inline helpers)."""
    
    # Get camera sensors
    camera_entities = [
        eid for eid in hass.states.async_entity_ids("camera")
    ]
    
    motion_cameras = [
        eid for eid in hass.states.async_entity_ids("binary_sensor")
        if "ai_home_copilot_motion" in eid
    ]
    
    # Get counts
    def get_sensor_count(sensor_id: str) -> int:
        state = hass.states.get(sensor_id)
        if state and state.state.isdigit():
            return int(state.state)
        return 0
    
    motion_count = get_sensor_count("sensor.ai_home_copilot_camera_motion_history")
    presence_count = get_sensor_count("sensor.ai_home_copilot_camera_presence_history")
    activity_count = get_sensor_count("sensor.ai_home_copilot_camera_activity_history")
    zone_count = get_sensor_count("sensor.ai_home_copilot_camera_zone_activity")
    
    yaml_content = f"""title: AI Home CoPilot Kamera
path: ai-home-copilot-camera
icon: mdi:cctv

cards:
  - type: markdown
    title: 📷 Kamera-Übersicht
    content: |
      ## 📷 Kamera-Übersicht
      
      - **Bewegungen (24h):** {motion_count}
      - **Präsenzen (24h):** {presence_count}
      - **Aktivitäten (24h):** {activity_count}
      - **Zonen-Events (24h):** {zone_count}

  - type: horizontal-stack
    cards:
      - type: gauge
        title: Bewegung (24h)
        entity: sensor.ai_home_copilot_camera_motion_history
        min: 0
        max: 100
        severity:
          green: 0
          yellow: 20
          red: 50

      - type: gauge
        title: Präsenz (24h)
        entity: sensor.ai_home_copilot_camera_presence_history
        min: 0
        max: 50
        severity:
          green: 0
          yellow: 10
          red: 30

  - type: horizontal-stack
    cards:
      - type: gauge
        title: Aktivität (24h)
        entity: sensor.ai_home_copilot_camera_activity_history
        min: 0
        max: 100
        severity:
          green: 0
          yellow: 30
          red: 70

      - type: gauge
        title: Zonen (24h)
        entity: sensor.ai_home_copilot_camera_zone_activity
        min: 0
        max: 50
        severity:
          green: 0
          yellow: 15
          red: 40

  - type: entities
    title: Bewegungserkennung
    show_header_toggle: false
    entities:
"""
    
    for cam in motion_cameras[:6]:
        yaml_content += f"      - {cam}\n"
    
    if not motion_cameras:
        yaml_content += "      - type: section\n        label: Keine Bewegungskameras konfiguriert\n"
    
    yaml_content += """
  - type: entities
    title: Kameras
    show_header_toggle: false
    entities:
"""
    
    for cam in camera_entities[:8]:
        yaml_content += f"      - {cam}\n"
    
    if not camera_entities:
        yaml_content += "      - type: section\n        label: Keine Kameras verfügbar\n"
    
    return yaml_content


__all__ = [
    "generate_camera_dashboard_yaml",
    "generate_camera_dashboard_v2_yaml",
]
