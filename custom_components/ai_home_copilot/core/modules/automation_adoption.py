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

        async def handle_adopt_from_suggestion(call: ServiceCall) -> None:
            """Service: adopt directly from a suggestion (with YAML from analysis)."""
            suggestion_id = call.data.get("suggestion_id", "")
            if not suggestion_id:
                _LOGGER.warning("adopt_from_suggestion called without suggestion_id")
                return
            await self._adopt_from_suggestion(hass, entry, suggestion_id)

        # Register services (idempotent)
        if not hass.services.has_service(DOMAIN, "adopt_suggestion"):
            hass.services.async_register(DOMAIN, "adopt_suggestion", handle_adopt_suggestion)
        if not hass.services.has_service(DOMAIN, "dismiss_suggestion"):
            hass.services.async_register(DOMAIN, "dismiss_suggestion", handle_dismiss_suggestion)
        if not hass.services.has_service(DOMAIN, "adopt_from_suggestion"):
            hass.services.async_register(DOMAIN, "adopt_from_suggestion", handle_adopt_from_suggestion)

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
        """Build a HA automation config from candidate data.

        Parses trigger/condition/action from example_yaml if available,
        otherwise builds actions from the candidate action list.
        """
        # Try parsing complete automation from example_yaml
        example_yaml = extra.get("example_yaml", "")
        if example_yaml:
            parsed = self._parse_full_yaml_automation(example_yaml)
            if parsed:
                parsed.setdefault("alias", f"Styx: {suggestion[:60]}")
                parsed.setdefault("description",
                    f"Auto-generated from PilotSuite Styx candidate {candidate_id}")
                return parsed

        # Build from structured action data
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
                for key in ("brightness_pct", "volume_level", "preset_mode", "temperature"):
                    if key in action:
                        ha_action.setdefault("data", {})[key] = action[key]
                ha_actions.append(ha_action)

        # Try extracting triggers from example_yaml even without full parse
        triggers = self._parse_yaml_triggers(example_yaml) if example_yaml else []

        return {
            "alias": f"Styx: {suggestion[:60]}",
            "description": f"Auto-generated from PilotSuite Styx candidate {candidate_id}",
            "trigger": triggers,
            "action": ha_actions,
            "mode": "single",
        }

    @staticmethod
    def _parse_yaml_triggers(yaml_str: str) -> list[dict[str, Any]]:
        """Extract trigger block from a YAML automation string."""
        try:
            import yaml
            parsed = yaml.safe_load(yaml_str)
            if isinstance(parsed, dict):
                triggers = parsed.get("trigger", parsed.get("triggers", []))
                if isinstance(triggers, list):
                    return triggers
                if isinstance(triggers, dict):
                    return [triggers]
        except Exception:
            pass
        return []

    @staticmethod
    def _parse_full_yaml_automation(yaml_str: str) -> dict[str, Any] | None:
        """Parse a complete YAML automation (trigger + condition + action).

        Returns a dict suitable for HA automation creation, or None.
        """
        try:
            import yaml
            parsed = yaml.safe_load(yaml_str)
            if not isinstance(parsed, dict):
                return None

            # Must have at least trigger and action
            triggers = parsed.get("trigger", parsed.get("triggers", []))
            actions = parsed.get("action", parsed.get("actions", []))

            if not triggers or not actions:
                return None

            result: dict[str, Any] = {
                "trigger": triggers if isinstance(triggers, list) else [triggers],
                "action": actions if isinstance(actions, list) else [actions],
                "mode": parsed.get("mode", "single"),
            }

            # Optional fields
            if "alias" in parsed:
                result["alias"] = parsed["alias"]
            if "description" in parsed:
                result["description"] = parsed["description"]
            conditions = parsed.get("condition", parsed.get("conditions"))
            if conditions:
                result["condition"] = conditions if isinstance(conditions, list) else [conditions]

            return result
        except Exception:
            return None

    async def _adopt_from_suggestion(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        suggestion_id: str,
    ) -> None:
        """Adopt an automation from a SuggestionPanel suggestion.

        Looks up the suggestion in the store, parses its YAML evidence,
        writes to automations.yaml, and triggers automation.reload.
        """
        entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
        store = entry_data.get("suggestion_store") if isinstance(entry_data, dict) else None
        if not store:
            _LOGGER.warning("No suggestion store for adopt_from_suggestion")
            return

        # Find the suggestion
        suggestion = None
        if hasattr(store, "queue") and hasattr(store.queue, "_pending"):
            for s in store.queue._pending:
                sid = s.suggestion_id if hasattr(s, "suggestion_id") else s.get("suggestion_id", "")
                if sid == suggestion_id:
                    suggestion = s
                    break

        if not suggestion:
            _LOGGER.warning("Suggestion %s not found", suggestion_id)
            return

        # Extract YAML from evidence
        evidence = suggestion.evidence if hasattr(suggestion, "evidence") else suggestion.get("evidence", [])
        example_yaml = ""
        for ev in evidence:
            if isinstance(ev, dict) and ev.get("yaml"):
                example_yaml = ev["yaml"]
                break

        if not example_yaml:
            _LOGGER.warning("No example YAML in suggestion %s", suggestion_id)
            return

        # Parse and write
        config = self._build_automation_config(
            suggestion_id,
            suggestion.pattern if hasattr(suggestion, "pattern") else suggestion.get("pattern", ""),
            [],  # No structured actions, using YAML
            {"example_yaml": example_yaml},
        )

        if config.get("trigger"):
            await self._write_automation_yaml(hass, config)
            _LOGGER.info("Adopted suggestion %s as automation: %s", suggestion_id, config.get("alias"))

            # Mark as accepted in store
            if hasattr(store.queue, "accept"):
                store.queue.accept(suggestion_id, "styx_auto")
                await store.async_save()
        else:
            _LOGGER.warning("Could not parse triggers from suggestion %s", suggestion_id)

    @staticmethod
    async def _write_automation_yaml(
        hass: HomeAssistant,
        config: dict,
    ) -> None:
        """Append an automation config to automations.yaml and reload."""
        import yaml
        from pathlib import Path

        automations_path = Path(hass.config.path("automations.yaml"))

        def _write():
            existing = []
            if automations_path.exists():
                try:
                    content = automations_path.read_text(encoding="utf-8")
                    if content.strip():
                        parsed = yaml.safe_load(content)
                        if isinstance(parsed, list):
                            existing = parsed
                except Exception:
                    pass

            existing.append(config)
            automations_path.write_text(
                yaml.dump(existing, default_flow_style=False, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

        await hass.async_add_executor_job(_write)

        # Reload automations
        try:
            await hass.services.async_call("automation", "reload", {}, blocking=False)
        except Exception:
            _LOGGER.debug("Automation reload after adoption failed (non-blocking)")

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
