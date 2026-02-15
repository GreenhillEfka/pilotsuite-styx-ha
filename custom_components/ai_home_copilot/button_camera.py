"""
Camera Dashboard Button for AI Home CoPilot.

Provides a button to generate the camera dashboard.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import CopilotDataUpdateCoordinator
from .camera_dashboard import generate_camera_dashboard_v2_yaml

_LOGGER = logging.getLogger(__name__)


class CopilotGenerateCameraDashboardButton(ButtonEntity):
    """Button to generate camera dashboard YAML."""

    _attr_name = "Generate Camera Dashboard"
    _attr_unique_id = "ai_home_copilot_generate_camera_dashboard"
    _attr_icon = "mdi:cctv"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        self._hass = hass
        self._entry = entry

    async def async_press(self) -> None:
        """Generate camera dashboard."""
        _LOGGER.info("Generating camera dashboard")
        
        try:
            yaml_content = await generate_camera_dashboard_v2_yaml(
                self._hass,
                self._entry.entry_id,
            )
            
            now = dt_util.now()
            ts = now.strftime("%Y%m%d_%H%M%S")
            
            out_dir = Path(self._hass.config.path("ai_home_copilot"))
            out_dir.mkdir(parents=True, exist_ok=True)
            
            out_path = out_dir / f"camera_dashboard_{ts}.yaml"
            latest_path = out_dir / "camera_dashboard_latest.yaml"
            
            out_path.write_text(yaml_content, encoding="utf-8")
            latest_path.write_text(yaml_content, encoding="utf-8")
            
            from homeassistant.components import persistent_notification
            persistent_notification.async_create(
                self._hass,
                (
                    f"Generated camera dashboard YAML at:\n{out_path}\n\n"
                    f"Latest (stable):\n{latest_path}"
                ),
                title="AI Home CoPilot Camera Dashboard",
                notification_id="ai_home_copilot_camera_dashboard",
            )
            
            _LOGGER.info("Generated camera dashboard at %s", out_path)
            
        except Exception as e:
            _LOGGER.error("Failed to generate camera dashboard: %s", e)
            from homeassistant.components import persistent_notification
            persistent_notification.async_create(
                self._hass,
                f"Failed to generate camera dashboard: {e}",
                title="AI Home CoPilot Camera Dashboard Error",
                notification_id="ai_home_copilot_camera_dashboard_error",
            )


class CopilotDownloadCameraDashboardButton(ButtonEntity):
    """Button to download camera dashboard YAML."""

    _attr_name = "Download Camera Dashboard"
    _attr_unique_id = "ai_home_copilot_download_camera_dashboard"
    _attr_icon = "mdi:download"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        self._hass = hass
        self._entry = entry

    async def async_press(self) -> None:
        """Download camera dashboard YAML."""
        _LOGGER.info("Downloading camera dashboard")
        
        from homeassistant.components import persistent_notification
        
        out_dir = Path(self._hass.config.path("ai_home_copilot"))
        latest_path = out_dir / "camera_dashboard_latest.yaml"
        
        if not latest_path.exists():
            persistent_notification.async_create(
                self._hass,
                "No camera dashboard generated yet. Click 'Generate Camera Dashboard' first.",
                title="AI Home CoPilot Camera Dashboard",
                notification_id="ai_home_copilot_camera_dashboard_download",
            )
            return
        
        persistent_notification.async_create(
            self._hass,
            f"Camera dashboard YAML available at:\n{latest_path}",
            title="AI Home CoPilot Camera Dashboard",
            notification_id="ai_home_copilot_camera_dashboard_download",
        )


__all__ = [
    "CopilotGenerateCameraDashboardButton",
    "CopilotDownloadCameraDashboardButton",
]
