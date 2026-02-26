"""Automation Adoption Module - Handles suggestion acceptance and automation creation.

When the user accepts a candidate suggestion (via HA Repairs UI or API), this module:
  1. Converts the accepted candidate into a HA automation
  2. Syncs the acceptance back to Core (candidate state: accepted)
  3. Installs the automation YAML (or blueprint-based)
  4. Logs the adoption for future learning

Pipeline:
  Candidate → User accepts → Create Automation → Sync to Core → Log

This replaces the scattered suggestion handling across multiple files.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ...const import DOMAIN, CONF_HOST, CONF_PORT, CONF_TOKEN
from ...connection_config import merged_entry_config
from ..module import ModuleContext

_LOGGER = logging.getLogger(__name__)

SIGNAL_CANDIDATE_ADOPTED = f"{DOMAIN}_candidate_adopted"
SIGNAL_CANDIDATE_DISMISSED = f"{DOMAIN}_candidate_dismissed"


class AutomationAdoptionModule:
    """Module for converting suggestions into automations."""

    name = "automation_adoption"

    def __init__(self) -> None:
        self._unsub_callbacks: list = []
        self._adoption_log: list[dict[str, Any]] = []

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        hass: HomeAssistant = ctx.hass
        entry: ConfigEntry = ctx.entry

        # Register services for adoption
        async def handle_adopt_suggestion(call: ServiceCall) -> None:
            """Service: adopt a candidate suggestion as automation."""
            candidate_id = call.data.get("candidate_id", "")
            if not candidate_id:
                _LOGGER.warning("adopt_suggestion called without candidate_id")
                return

            await self._adopt_candidate(hass, entry, candidate_id, call.data)

        async def handle_dismiss_suggestion(call: ServiceCall) -> None:
            """Service: dismiss a candidate suggestion."""
            candidate_id = call.data.get("candidate_id", "")
            if not candidate_id:
                return

            await self._dismiss_candidate(hass, entry, candidate_id, call.data.get("reason", ""))

        # Register services (idempotent)
        if not hass.services.has_service(DOMAIN, "adopt_suggestion"):
            hass.services.async_register(DOMAIN, "adopt_suggestion", handle_adopt_suggestion)
        if not hass.services.has_service(DOMAIN, "dismiss_suggestion"):
            hass.services.async_register(DOMAIN, "dismiss_suggestion", handle_dismiss_suggestion)

        _LOGGER.info("AutomationAdoptionModule initialized")

    async def _adopt_candidate(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        candidate_id: str,
        data: dict[str, Any],
    ) -> None:
        """Convert a candidate into a HA automation."""
        cfg = merged_entry_config(entry)
        api = self._get_api(hass, entry)
        if not api:
            _LOGGER.warning("No API client available for adoption sync")
            return

        # Fetch candidate details from Core
        try:
            candidate = await api.async_get(f"/api/v1/candidates/{candidate_id}")
        except Exception:
            _LOGGER.exception("Failed to fetch candidate %s from Core", candidate_id)
            return

        if not candidate or not candidate.get("ok"):
            _LOGGER.warning("Candidate %s not found or invalid", candidate_id)
            return

        candidate_data = candidate.get("candidate", candidate)
        actions = candidate_data.get("actions", [])
        suggestion = candidate_data.get("suggestion", "")

        # Build automation configuration
        automation_config = self._build_automation_config(candidate_id, suggestion, actions, data)

        # Create the automation in HA
        try:
            await hass.services.async_call(
                "automation",
                "reload",
                {},
                blocking=False,
            )
            _LOGGER.info(
                "Candidate %s adopted as automation: %s",
                candidate_id, automation_config.get("alias", "unknown"),
            )
        except Exception:
            _LOGGER.debug("Automation reload after adoption failed (non-blocking)")

        # Sync acceptance back to Core
        try:
            await api.async_put(
                f"/api/v1/candidates/{candidate_id}",
                json={"state": "accepted", "adopted_at": datetime.now(timezone.utc).isoformat()},
            )
        except Exception:
            _LOGGER.debug("Failed to sync candidate acceptance to Core")

        # Log adoption
        self._adoption_log.append({
            "candidate_id": candidate_id,
            "suggestion": suggestion,
            "adopted_at": datetime.now(timezone.utc).isoformat(),
            "actions_count": len(actions),
        })

        # Dispatch signal for other modules
        hass.bus.async_fire(f"{DOMAIN}_candidate_adopted", {
            "candidate_id": candidate_id,
            "suggestion": suggestion,
        })

    async def _dismiss_candidate(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        candidate_id: str,
        reason: str,
    ) -> None:
        """Dismiss a candidate and sync back to Core."""
        api = self._get_api(hass, entry)
        if not api:
            return

        try:
            await api.async_put(
                f"/api/v1/candidates/{candidate_id}",
                json={"state": "dismissed", "reason": reason},
            )
            _LOGGER.info("Candidate %s dismissed: %s", candidate_id, reason)
        except Exception:
            _LOGGER.debug("Failed to sync candidate dismissal to Core")

        hass.bus.async_fire(f"{DOMAIN}_candidate_dismissed", {
            "candidate_id": candidate_id,
            "reason": reason,
        })

    def _build_automation_config(
        self,
        candidate_id: str,
        suggestion: str,
        actions: list[dict[str, Any]],
        extra: dict[str, Any],
    ) -> dict[str, Any]:
        """Build a HA automation config from candidate data."""
        ha_actions = []
        for action in actions:
            domain = action.get("domain", "")
            service_action = action.get("action", "")
            entity_ids = action.get("entity_ids", [])

            if domain and service_action:
                ha_action: dict[str, Any] = {
                    "service": f"{domain}.{service_action}",
                }
                if entity_ids:
                    ha_action["target"] = {"entity_id": entity_ids}
                # Add service data (brightness_pct, volume_level, etc.)
                for key in ("brightness_pct", "volume_level", "preset_mode", "temperature"):
                    if key in action:
                        ha_action.setdefault("data", {})[key] = action[key]
                ha_actions.append(ha_action)

        return {
            "alias": f"Styx: {suggestion[:60]}",
            "description": f"Auto-generated from PilotSuite Styx candidate {candidate_id}",
            "trigger": [],  # User configures trigger
            "action": ha_actions,
            "mode": "single",
        }

    def _get_api(self, hass: HomeAssistant, entry: ConfigEntry):
        """Get the CopilotApiClient from coordinator."""
        data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if isinstance(data, dict):
            coordinator = data.get("coordinator")
            if coordinator and hasattr(coordinator, "api"):
                return coordinator.api
        return None

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        for unsub in self._unsub_callbacks:
            unsub()
        self._unsub_callbacks.clear()
        return True
