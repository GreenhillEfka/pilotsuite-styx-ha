"""Centralised service registration for PilotSuite.

Extracted from __init__.py to keep async_setup() lean.
"""
from __future__ import annotations

import logging

import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

from homeassistant.core import HomeAssistant, ServiceCall

from .connection_config import resolve_core_connection
from .const import DOMAIN
from .media_context_v2_setup import MediaContextV2ConfigManager
from .tag_registry import (
    async_confirm_tag,
    async_set_assignment,
    async_sync_labels_now,
    async_upsert_tag,
)
from .tag_sync import async_pull_tag_system_snapshot


# ---------------------------------------------------------------------------
# Installation Guide service
# ---------------------------------------------------------------------------

def _installation_guide_markdown(host: str, port: int, token_set: bool) -> str:
    token_note = "gesetzt" if token_set else "nicht gesetzt"
    return (
        "## PilotSuite Installationsanleitung (exakt)\n\n"
        "1. **Core Add-on installieren**\n"
        "   - Add-on: `PilotSuite Core`\n"
        "   - Starten und auf `running` warten\n"
        "   - Core API: `http://"
        + f"{host}:{port}`\n\n"
        "2. **Core Add-on konfigurieren**\n"
        "   - `conversation_ollama_model`: `qwen3:0.6b` (Default)\n"
        "   - Optional Cloud-Fallback: `conversation_cloud_api_url`, `conversation_cloud_api_key`, `conversation_cloud_model`\n"
        "   - `auth_token`: aktuell **"
        + token_note
        + "**\n\n"
        "3. **HA Integration konfigurieren**\n"
        "   - `Settings -> Devices & Services -> PilotSuite -> Configure`\n"
        "   - `Connection`: Host/Port/Token pruefen\n"
        "   - `Habitus Zones`: Zonen anlegen/bearbeiten\n\n"
        "4. **Dashboards in `configuration.yaml`**\n"
        "```yaml\n"
        "lovelace:\n"
        "  dashboards:\n"
        "    copilot-pilotsuite:\n"
        "      mode: yaml\n"
        "      title: \"PilotSuite - Styx\"\n"
        "      icon: mdi:robot-outline\n"
        "      show_in_sidebar: true\n"
        "      filename: \"pilotsuite-styx/pilotsuite_dashboard_latest.yaml\"\n"
        "    copilot-habitus-zones:\n"
        "      mode: yaml\n"
        "      title: \"PilotSuite - Habitus Zones\"\n"
        "      icon: mdi:layers-outline\n"
        "      show_in_sidebar: true\n"
        "      filename: \"pilotsuite-styx/habitus_zones_dashboard_latest.yaml\"\n"
        "```\n\n"
        "5. **Neustart + Smoke Test**\n"
        "   - Home Assistant neu starten\n"
        "   - `/chat/status` muss `available=true` zeigen\n"
        "   - Im Styx Dashboard eine Testnachricht senden\n"
    )


def _register_installation_guide_service(hass: HomeAssistant) -> None:
    """Register service that shows exact install/runbook steps in HA UI."""
    if hass.services.has_service(DOMAIN, "show_installation_guide"):
        return

    async def _handle_show_installation_guide(call: ServiceCall) -> None:
        from homeassistant.components import persistent_notification

        entry_id = str(call.data.get("entry_id") or "").strip()
        selected_entry = None
        if entry_id:
            selected_entry = hass.config_entries.async_get_entry(entry_id)
        if selected_entry is None:
            entries = hass.config_entries.async_entries(DOMAIN)
            selected_entry = entries[0] if entries else None

        host = "homeassistant.local"
        port = 8909
        token_set = False

        if selected_entry is not None:
            host, port, token = resolve_core_connection(selected_entry)
            token_set = bool(str(token or "").strip())

        persistent_notification.async_create(
            hass,
            _installation_guide_markdown(host, port, token_set),
            title="PilotSuite Installationsanleitung",
            notification_id="pilotsuite_installation_guide",
        )

    hass.services.async_register(
        DOMAIN,
        "show_installation_guide",
        _handle_show_installation_guide,
        schema=vol.Schema({vol.Optional("entry_id"): str}),
    )


# ---------------------------------------------------------------------------
# Tag Registry services
# ---------------------------------------------------------------------------

def _register_tag_registry_services(hass: HomeAssistant) -> None:
    """Register Tag Registry v0.1 governance services."""

    if not hass.services.has_service(DOMAIN, "tag_registry_upsert_tag"):

        async def _handle_upsert(call: ServiceCall) -> None:
            tag_key = str(call.data.get("tag_key") or "").strip()
            if not tag_key:
                return
            await async_upsert_tag(
                hass,
                tag_key,
                title=call.data.get("title"),
                icon=call.data.get("icon"),
                color=call.data.get("color"),
                status=call.data.get("status"),
            )

        hass.services.async_register(
            DOMAIN,
            "tag_registry_upsert_tag",
            _handle_upsert,
            schema=vol.Schema(
                {
                    vol.Required("tag_key"): str,
                    vol.Optional("title"): str,
                    vol.Optional("icon"): str,
                    vol.Optional("color"): str,
                    vol.Optional("status"): str,
                }
            ),
        )

    if not hass.services.has_service(DOMAIN, "tag_registry_set_assignment"):

        async def _handle_assign(call: ServiceCall) -> None:
            subject = str(call.data.get("subject") or "").strip()
            tag_keys = call.data.get("tag_keys")
            if not subject or not isinstance(tag_keys, list):
                return
            await async_set_assignment(hass, subject, [str(x) for x in tag_keys])

        hass.services.async_register(
            DOMAIN,
            "tag_registry_set_assignment",
            _handle_assign,
            schema=vol.Schema(
                {
                    vol.Required("subject"): str,
                    vol.Required("tag_keys"): [str],
                }
            ),
        )

    if not hass.services.has_service(DOMAIN, "tag_registry_confirm"):

        async def _handle_confirm(call: ServiceCall) -> None:
            tag_key = str(call.data.get("tag_key") or "").strip()
            if not tag_key:
                return
            await async_confirm_tag(hass, tag_key)

        hass.services.async_register(
            DOMAIN,
            "tag_registry_confirm",
            _handle_confirm,
            schema=vol.Schema({vol.Required("tag_key"): str}),
        )

    if not hass.services.has_service(DOMAIN, "tag_registry_sync_labels_now"):

        async def _handle_sync(_: ServiceCall) -> None:
            await async_sync_labels_now(hass)

        hass.services.async_register(
            DOMAIN,
            "tag_registry_sync_labels_now",
            _handle_sync,
        )

    if not hass.services.has_service(DOMAIN, "tag_registry_pull_from_core"):

        async def _handle_pull(call: ServiceCall) -> None:
            entry_id = call.data.get("entry_id")
            await async_pull_tag_system_snapshot(hass, entry_id=entry_id)

        hass.services.async_register(
            DOMAIN,
            "tag_registry_pull_from_core",
            _handle_pull,
            schema=vol.Schema({vol.Optional("entry_id"): str}),
        )


# ---------------------------------------------------------------------------
# Media Context v2 services
# ---------------------------------------------------------------------------

def _register_media_context_v2_services(hass: HomeAssistant) -> None:
    """Register Media Context v2 zone-mapping services."""

    if not hass.services.has_service(DOMAIN, "media_context_v2_suggest_zone_mapping"):

        async def _handle_suggest_zone_mapping(call: ServiceCall) -> None:
            entry_id = call.data.get("entry_id")
            if not entry_id:
                return
            for entry in hass.config_entries.async_entries(DOMAIN):
                if entry.entry_id == entry_id:
                    manager = MediaContextV2ConfigManager(hass, entry)
                    suggestions = await manager.async_get_zone_suggestions()
                    hass.bus.async_fire(
                        f"{DOMAIN}_media_context_v2_zone_suggestions",
                        {"entry_id": entry_id, "suggestions": suggestions},
                    )
                    break

        hass.services.async_register(
            DOMAIN,
            "media_context_v2_suggest_zone_mapping",
            _handle_suggest_zone_mapping,
            schema=vol.Schema({vol.Required("entry_id"): str}),
        )

    if not hass.services.has_service(DOMAIN, "media_context_v2_apply_zone_suggestions"):

        async def _handle_apply_zone_suggestions(call: ServiceCall) -> None:
            entry_id = call.data.get("entry_id")
            if not entry_id:
                return
            for entry in hass.config_entries.async_entries(DOMAIN):
                if entry.entry_id == entry_id:
                    manager = MediaContextV2ConfigManager(hass, entry)
                    await manager.async_apply_zone_suggestions()
                    break

        hass.services.async_register(
            DOMAIN,
            "media_context_v2_apply_zone_suggestions",
            _handle_apply_zone_suggestions,
            schema=vol.Schema({vol.Required("entry_id"): str}),
        )

    if not hass.services.has_service(DOMAIN, "media_context_v2_clear_overrides"):

        async def _handle_clear_overrides(call: ServiceCall) -> None:
            entry_id = call.data.get("entry_id")
            if not entry_id:
                return
            for entry in hass.config_entries.async_entries(DOMAIN):
                if entry.entry_id == entry_id:
                    manager = MediaContextV2ConfigManager(hass, entry)
                    coordinator_v2 = manager.coordinator_v2
                    if coordinator_v2:
                        coordinator_v2.clear_manual_overrides()
                    break

        hass.services.async_register(
            DOMAIN,
            "media_context_v2_clear_overrides",
            _handle_clear_overrides,
            schema=vol.Schema({vol.Required("entry_id"): str}),
        )


# ---------------------------------------------------------------------------
# N3 Forwarder services
# ---------------------------------------------------------------------------

def _register_forwarder_n3_services(hass: HomeAssistant) -> None:
    """Register N3 Event Forwarder services."""

    if not hass.services.has_service(DOMAIN, "forwarder_n3_start"):
        from .forwarder_n3 import N3EventForwarder

        async def _handle_forwarder_start(call: ServiceCall) -> None:
            entry_id = call.data.get("entry_id")
            if not entry_id:
                return
            for entry in hass.config_entries.async_entries(DOMAIN):
                if entry.entry_id == entry_id:
                    host, port, token = resolve_core_connection(entry)
                    config = {
                        "core_url": f"http://{host}:{port}",
                        "api_token": token,
                        "enabled_domains": [
                            "light", "climate", "media_player", "binary_sensor",
                            "sensor", "cover", "lock", "person", "device_tracker",
                            "weather",
                        ],
                        "batch_size": 50,
                        "flush_interval": 0.5,
                        "forward_call_service": True,
                    }
                    forwarder = N3EventForwarder(hass, config)
                    await forwarder.async_start()
                    hass.data.setdefault(DOMAIN, {})[f"n3_forwarder_{entry_id}"] = forwarder
                    break

        hass.services.async_register(
            DOMAIN,
            "forwarder_n3_start",
            _handle_forwarder_start,
            schema=vol.Schema({vol.Required("entry_id"): str}),
        )

    if not hass.services.has_service(DOMAIN, "forwarder_n3_stop"):

        async def _handle_forwarder_stop(call: ServiceCall) -> None:
            entry_id = call.data.get("entry_id")
            if not entry_id:
                return
            forwarder_key = f"n3_forwarder_{entry_id}"
            forwarder = hass.data.get(DOMAIN, {}).get(forwarder_key)
            if forwarder:
                await forwarder.async_stop()
                hass.data[DOMAIN].pop(forwarder_key, None)

        hass.services.async_register(
            DOMAIN,
            "forwarder_n3_stop",
            _handle_forwarder_stop,
            schema=vol.Schema({vol.Required("entry_id"): str}),
        )

    if not hass.services.has_service(DOMAIN, "forwarder_n3_stats"):

        async def _handle_forwarder_stats(call: ServiceCall) -> None:
            entry_id = call.data.get("entry_id")
            if not entry_id:
                return
            forwarder_key = f"n3_forwarder_{entry_id}"
            forwarder = hass.data.get(DOMAIN, {}).get(forwarder_key)
            if forwarder:
                stats = await forwarder.async_get_stats()
                hass.bus.async_fire(
                    f"{DOMAIN}_forwarder_n3_stats",
                    {"entry_id": entry_id, "stats": stats},
                )

        hass.services.async_register(
            DOMAIN,
            "forwarder_n3_stats",
            _handle_forwarder_stats,
            schema=vol.Schema({vol.Required("entry_id"): str}),
        )


# ---------------------------------------------------------------------------
# Ops Runbook services
# ---------------------------------------------------------------------------

def _register_ops_runbook_services(hass: HomeAssistant) -> None:
    """Register Ops Runbook v0.1 services."""

    if not hass.services.has_service(DOMAIN, "ops_runbook_preflight_check"):
        from .ops_runbook import async_run_preflight_check

        async def _handle_preflight_check(call: ServiceCall) -> None:
            await async_run_preflight_check(hass)

        hass.services.async_register(
            DOMAIN,
            "ops_runbook_preflight_check",
            _handle_preflight_check,
        )

    if not hass.services.has_service(DOMAIN, "ops_runbook_smoke_test"):
        from .ops_runbook import async_run_smoke_test

        async def _handle_smoke_test(call: ServiceCall) -> None:
            await async_run_smoke_test(hass)

        hass.services.async_register(
            DOMAIN,
            "ops_runbook_smoke_test",
            _handle_smoke_test,
        )

    if not hass.services.has_service(DOMAIN, "ops_runbook_execute_action"):
        from .ops_runbook import async_execute_runbook_action

        async def _handle_execute_action(call: ServiceCall) -> None:
            action = call.data.get("action")
            if not action:
                raise ValueError("Action parameter is required")
            await async_execute_runbook_action(hass, action)

        hass.services.async_register(
            DOMAIN,
            "ops_runbook_execute_action",
            _handle_execute_action,
            schema=vol.Schema({vol.Required("action"): str}),
        )

    if not hass.services.has_service(DOMAIN, "ops_runbook_run_checklist"):
        from .ops_runbook import async_run_checklist

        async def _handle_run_checklist(call: ServiceCall) -> None:
            checklist = call.data.get("checklist")
            if not checklist:
                raise ValueError("Checklist parameter is required")
            await async_run_checklist(hass, checklist)

        hass.services.async_register(
            DOMAIN,
            "ops_runbook_run_checklist",
            _handle_run_checklist,
            schema=vol.Schema({vol.Required("checklist"): str}),
        )


# ---------------------------------------------------------------------------
# Habitus Dashboard Cards services
# ---------------------------------------------------------------------------

def _register_habitus_dashboard_cards_services(hass: HomeAssistant) -> None:
    """Register Habitus Dashboard Cards v0.2 services."""

    if not hass.services.has_service(DOMAIN, "get_dashboard_patterns"):
        from .services.habitus_dashboard_cards_service import (
            async_setup_habitus_dashboard_cards_services,
        )
        hass.async_create_task(async_setup_habitus_dashboard_cards_services(hass))


# ---------------------------------------------------------------------------
# Multi-User Preference Learning (MUPL) services
# ---------------------------------------------------------------------------

def _register_mupl_services(hass: HomeAssistant) -> None:
    """Register Multi-User Preference Learning v0.8.0 services."""
    
    if not hass.services.has_service(DOMAIN, "mupl_learn_preference"):
        
        async def _handle_learn_preference(call: ServiceCall) -> None:
            from .multi_user_preferences import get_mupl_module
            mupl = get_mupl_module(hass)
            if not mupl:
                _LOGGER.warning("MUPL module not available — enable mupl_enabled in integration config")
                return
            user_id = call.data.get("user_id")
            pref_type = call.data.get("preference_type")
            value = call.data.get("value")
            zone = call.data.get("zone")
            await mupl.set_preference(user_id, pref_type, value, zone)
            
        hass.services.async_register(
            DOMAIN,
            "mupl_learn_preference",
            _handle_learn_preference,
            schema=vol.Schema(
                {
                    vol.Required("user_id"): str,
                    vol.Required("preference_type"): str,
                    vol.Required("value"): vol.Any(float, dict),
                    vol.Optional("zone"): str,
                }
            ),
        )
        
    if not hass.services.has_service(DOMAIN, "mupl_set_user_priority"):
        
        async def _handle_set_priority(call: ServiceCall) -> None:
            from .multi_user_preferences import get_mupl_module
            mupl = get_mupl_module(hass)
            if not mupl:
                _LOGGER.warning("MUPL module not available — enable mupl_enabled in integration config")
                return
            user_id = call.data.get("user_id")
            priority = float(call.data.get("priority", 0.5))
            await mupl.set_user_priority(user_id, priority)
            
        hass.services.async_register(
            DOMAIN,
            "mupl_set_user_priority",
            _handle_set_priority,
            schema=vol.Schema(
                {
                    vol.Required("user_id"): str,
                    vol.Required("priority"): vol.All(
                        vol.Coerce(float),
                        vol.Range(min=0.0, max=1.0),
                    ),
                }
            ),
        )
        
    if not hass.services.has_service(DOMAIN, "mupl_delete_user_data"):
        
        async def _handle_delete_data(call: ServiceCall) -> None:
            from .multi_user_preferences import get_mupl_module
            mupl = get_mupl_module(hass)
            if not mupl:
                _LOGGER.warning("MUPL module not available — enable mupl_enabled in integration config")
                return
            user_id = call.data.get("user_id")
            await mupl.delete_user_data(user_id)
            
        hass.services.async_register(
            DOMAIN,
            "mupl_delete_user_data",
            _handle_delete_data,
            schema=vol.Schema({vol.Required("user_id"): str}),
        )
        
    if not hass.services.has_service(DOMAIN, "mupl_export_user_data"):
        
        async def _handle_export_data(call: ServiceCall) -> None:
            from .multi_user_preferences import get_mupl_module
            mupl = get_mupl_module(hass)
            if not mupl:
                _LOGGER.warning("MUPL module not available — enable mupl_enabled in integration config")
                return
            user_id = call.data.get("user_id")
            data = await mupl.export_user_data(user_id)
            # Fire event with exported data
            hass.bus.async_fire(
                f"{DOMAIN}_mupl_user_data_exported",
                {"user_id": user_id, "data": data},
            )
            
        hass.services.async_register(
            DOMAIN,
            "mupl_export_user_data",
            _handle_export_data,
            schema=vol.Schema({vol.Required("user_id"): str}),
        )
        
    if not hass.services.has_service(DOMAIN, "mupl_detect_active_users"):
        
        async def _handle_detect_users(_: ServiceCall) -> None:
            from .multi_user_preferences import get_mupl_module
            mupl = get_mupl_module(hass)
            if not mupl:
                _LOGGER.warning("MUPL module not available — enable mupl_enabled in integration config")
                return
            active_users = await mupl.detect_active_users()
            # Fire event with results
            hass.bus.async_fire(
                f"{DOMAIN}_mupl_active_users_detected",
                {"users": active_users, "count": len(active_users)},
            )
            
        hass.services.async_register(
            DOMAIN,
            "mupl_detect_active_users",
            _handle_detect_users,
        )
        
    if not hass.services.has_service(DOMAIN, "mupl_get_aggregated_mood"):
        
        async def _handle_get_mood(call: ServiceCall) -> None:
            from .multi_user_preferences import get_mupl_module
            mupl = get_mupl_module(hass)
            if not mupl:
                _LOGGER.warning("MUPL module not available — enable mupl_enabled in integration config")
                return
            user_ids = call.data.get("user_ids")
            mood = mupl.get_aggregated_mood(user_ids)
            # Fire event with results
            hass.bus.async_fire(
                f"{DOMAIN}_mupl_aggregated_mood",
                {"mood": mood, "user_ids": user_ids},
            )
            
        hass.services.async_register(
            DOMAIN,
            "mupl_get_aggregated_mood",
            _handle_get_mood,
            schema=vol.Schema({vol.Optional("user_ids"): [str]}),
        )


# ---------------------------------------------------------------------------
# Camera Context Services
# ---------------------------------------------------------------------------

def _register_camera_context_services(hass: HomeAssistant) -> None:
    """Register Camera Context services for Habitus integration."""
    
    if not hass.services.has_service(DOMAIN, "camera_trigger_motion"):
        
        async def _handle_trigger_motion(call: ServiceCall) -> None:
            camera_id = call.data.get("camera_id", "")
            camera_name = call.data.get("camera_name", camera_id.split(".")[-1] if camera_id else "Unknown")
            confidence = call.data.get("confidence", 1.0)
            zone = call.data.get("zone")
            
            # Get coordinator and trigger motion
            for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
                coordinator = entry_data.get("coordinator")
                if coordinator:
                    coordinator.async_add_motion_event(
                        camera_id=camera_id,
                        camera_name=camera_name,
                        confidence=confidence,
                        zone=zone,
                    )
                    break
            
            # Fire event for other listeners
            hass.bus.async_fire(
                f"{DOMAIN}_camera_event",
                {
                    "type": "motion",
                    "camera_id": camera_id,
                    "camera_name": camera_name,
                    "action": "started",
                    "confidence": confidence,
                    "zone": zone,
                }
            )
        
        hass.services.async_register(
            DOMAIN,
            "camera_trigger_motion",
            _handle_trigger_motion,
            schema=vol.Schema({
                vol.Required("camera_id"): str,
                vol.Optional("camera_name"): str,
                vol.Optional("confidence"): vol.Coerce(float),
                vol.Optional("zone"): str,
            }),
        )
    
    if not hass.services.has_service(DOMAIN, "camera_trigger_presence"):
        
        async def _handle_trigger_presence(call: ServiceCall) -> None:
            camera_id = call.data.get("camera_id", "")
            camera_name = call.data.get("camera_name", camera_id.split(".")[-1] if camera_id else "Unknown")
            presence_type = call.data.get("presence_type", "person")
            person_name = call.data.get("person_name")
            confidence = call.data.get("confidence", 1.0)
            
            # Get coordinator and trigger presence
            for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
                coordinator = entry_data.get("coordinator")
                if coordinator:
                    coordinator.async_add_presence_event(
                        camera_id=camera_id,
                        camera_name=camera_name,
                        presence_type=presence_type,
                        person_name=person_name,
                        confidence=confidence,
                    )
                    break
            
            # Fire event
            hass.bus.async_fire(
                f"{DOMAIN}_camera_event",
                {
                    "type": "presence",
                    "camera_id": camera_id,
                    "camera_name": camera_name,
                    "presence_type": presence_type,
                    "person_name": person_name,
                }
            )
        
        hass.services.async_register(
            DOMAIN,
            "camera_trigger_presence",
            _handle_trigger_presence,
            schema=vol.Schema({
                vol.Required("camera_id"): str,
                vol.Optional("camera_name"): str,
                vol.Optional("presence_type"): str,
                vol.Optional("person_name"): str,
                vol.Optional("confidence"): vol.Coerce(float),
            }),
        )
    
    if not hass.services.has_service(DOMAIN, "camera_trigger_activity"):
        
        async def _handle_trigger_activity(call: ServiceCall) -> None:
            camera_id = call.data.get("camera_id", "")
            camera_name = call.data.get("camera_name", camera_id.split(".")[-1] if camera_id else "Unknown")
            activity_type = call.data.get("activity_type", "walking")
            duration = call.data.get("duration_seconds", 0)
            confidence = call.data.get("confidence", 1.0)
            
            # Get coordinator and trigger activity
            for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
                coordinator = entry_data.get("coordinator")
                if coordinator:
                    coordinator.async_add_activity_event(
                        camera_id=camera_id,
                        camera_name=camera_name,
                        activity_type=activity_type,
                        duration_seconds=duration,
                        confidence=confidence,
                    )
                    break
        
        hass.services.async_register(
            DOMAIN,
            "camera_trigger_activity",
            _handle_trigger_activity,
            schema=vol.Schema({
                vol.Required("camera_id"): str,
                vol.Optional("camera_name"): str,
                vol.Required("activity_type"): str,
                vol.Optional("duration_seconds"): int,
                vol.Optional("confidence"): vol.Coerce(float),
            }),
        )
    
    if not hass.services.has_service(DOMAIN, "camera_trigger_zone"):
        
        async def _handle_trigger_zone(call: ServiceCall) -> None:
            camera_id = call.data.get("camera_id", "")
            camera_name = call.data.get("camera_name", camera_id.split(".")[-1] if camera_id else "Unknown")
            zone_name = call.data.get("zone_name", "")
            event_type = call.data.get("event_type", "entered")
            object_type = call.data.get("object_type")
            
            # Get coordinator and trigger zone event
            for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
                coordinator = entry_data.get("coordinator")
                if coordinator:
                    coordinator.async_add_zone_event(
                        camera_id=camera_id,
                        camera_name=camera_name,
                        zone_name=zone_name,
                        event_type=event_type,
                        object_type=object_type,
                    )
                    break
        
        hass.services.async_register(
            DOMAIN,
            "camera_trigger_zone",
            _handle_trigger_zone,
            schema=vol.Schema({
                vol.Required("camera_id"): str,
                vol.Optional("camera_name"): str,
                vol.Required("zone_name"): str,
                vol.Optional("event_type"): str,
                vol.Optional("object_type"): str,
            }),
        )
    
    if not hass.services.has_service(DOMAIN, "camera_clear_motion"):
        
        async def _handle_clear_motion(call: ServiceCall) -> None:
            camera_id = call.data.get("camera_id", "")
            
            # Get coordinator and clear motion
            for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
                coordinator = entry_data.get("coordinator")
                if coordinator:
                    coordinator.async_clear_motion(camera_id)
                    break
        
        hass.services.async_register(
            DOMAIN,
            "camera_clear_motion",
            _handle_clear_motion,
            schema=vol.Schema({
                vol.Required("camera_id"): str,
            }),
        )
    
    if not hass.services.has_service(DOMAIN, "camera_set_retention"):
        
        async def _handle_set_retention(call: ServiceCall) -> None:
            camera_id = call.data.get("camera_id", "")
            hours = call.data.get("hours", 24)
            
            # Get coordinator and set retention
            for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
                coordinator = entry_data.get("coordinator")
                if coordinator:
                    coordinator.set_camera_retention(camera_id, hours)
                    break
        
        hass.services.async_register(
            DOMAIN,
            "camera_set_retention",
            _handle_set_retention,
            schema=vol.Schema({
                vol.Required("camera_id"): str,
                vol.Required("hours"): int,
            }),
        )


# ---------------------------------------------------------------------------
# Debug services (set_debug, disable_debug, clear_error_digest)
# ---------------------------------------------------------------------------

def _register_debug_services(hass: HomeAssistant) -> None:
    """Register debug-related services.

    Note: enable_debug, disable_debug, toggle_debug, clear_debug_buffer
    are registered by debug.py during async_setup_entry.
    Here we add set_debug (convenience wrapper) and clear_error_digest.
    """

    if not hass.services.has_service(DOMAIN, "set_debug"):

        async def _handle_set_debug(call: ServiceCall) -> None:
            enabled = call.data.get("enabled", False)
            target = "enable_debug" if enabled else "disable_debug"
            if hass.services.has_service(DOMAIN, target):
                await hass.services.async_call(DOMAIN, target, {})
            else:
                domain_data = hass.data.setdefault(DOMAIN, {})
                domain_data["debug_mode"] = enabled
                _LOGGER.info("Debug mode set to %s (fallback)", enabled)

        hass.services.async_register(
            DOMAIN,
            "set_debug",
            _handle_set_debug,
            schema=vol.Schema({vol.Required("enabled"): bool}),
        )

    # disable_debug is registered by debug.py — only add fallback
    # if it hasn't been registered yet (pre-setup race).

    if not hass.services.has_service(DOMAIN, "clear_error_digest"):

        async def _handle_clear_error_digest(_: ServiceCall) -> None:
            for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
                if not isinstance(entry_data, dict):
                    continue
                digest = entry_data.get("error_digest")
                if digest and hasattr(digest, "clear"):
                    digest.clear()
            _LOGGER.info("Error digest cleared")

        hass.services.async_register(
            DOMAIN, "clear_error_digest", _handle_clear_error_digest
        )


# ---------------------------------------------------------------------------
# UniFi services
# ---------------------------------------------------------------------------

def _register_unifi_services(hass: HomeAssistant) -> None:
    """Register UniFi network diagnostic services."""

    if not hass.services.has_service(DOMAIN, "ai_home_copilot_unifi_run_diagnostics"):

        async def _handle_unifi_diagnostics(_: ServiceCall) -> None:
            for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
                if not isinstance(entry_data, dict):
                    continue
                runtime = entry_data.get("runtime")
                if runtime and hasattr(runtime, "registry"):
                    mod = runtime.registry.get("network")
                    if mod and hasattr(mod, "run_diagnostics"):
                        result = await mod.run_diagnostics()
                        hass.bus.async_fire(
                            f"{DOMAIN}_unifi_diagnostics",
                            {"entry_id": entry_id, "result": result},
                        )
                        return
            _LOGGER.warning("UniFi module not available for diagnostics")

        hass.services.async_register(
            DOMAIN, "ai_home_copilot_unifi_run_diagnostics", _handle_unifi_diagnostics
        )

    if not hass.services.has_service(DOMAIN, "ai_home_copilot_unifi_get_report"):

        async def _handle_unifi_report(_: ServiceCall) -> None:
            for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
                if not isinstance(entry_data, dict):
                    continue
                runtime = entry_data.get("runtime")
                if runtime and hasattr(runtime, "registry"):
                    mod = runtime.registry.get("network")
                    if mod and hasattr(mod, "get_report"):
                        report = await mod.get_report()
                        hass.bus.async_fire(
                            f"{DOMAIN}_unifi_report",
                            {"entry_id": entry_id, "report": report},
                        )
                        return
            _LOGGER.warning("UniFi module not available for report")

        hass.services.async_register(
            DOMAIN, "ai_home_copilot_unifi_get_report", _handle_unifi_report
        )


# ---------------------------------------------------------------------------
# Predictive Automation service
# ---------------------------------------------------------------------------

def _register_predictive_services(hass: HomeAssistant) -> None:
    """Register predictive automation services."""

    if not hass.services.has_service(DOMAIN, "predictive_automation_suggest_automation"):

        async def _handle_suggest_automation(call: ServiceCall) -> None:
            pattern = call.data.get("pattern", "")
            confidence = call.data.get("confidence", 0.5)
            zone = call.data.get("zone")

            for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
                if not isinstance(entry_data, dict):
                    continue
                coordinator = entry_data.get("coordinator")
                if not coordinator:
                    continue

                # Build suggestion from pattern
                suggestion = {
                    "pattern": pattern,
                    "confidence": confidence,
                    "zone": zone,
                    "source": "user_service_call",
                }

                hass.bus.async_fire(
                    f"{DOMAIN}_predictive_suggestion",
                    {"entry_id": entry_id, "suggestion": suggestion},
                )
                _LOGGER.info("Predictive automation suggestion: %s (conf=%.2f)", pattern, confidence)
                return

        hass.services.async_register(
            DOMAIN,
            "predictive_automation_suggest_automation",
            _handle_suggest_automation,
            schema=vol.Schema({
                vol.Required("pattern"): str,
                vol.Optional("confidence"): vol.Coerce(float),
                vol.Optional("zone"): str,
            }),
        )


# ---------------------------------------------------------------------------
# Anomaly Alert services
# ---------------------------------------------------------------------------

def _register_anomaly_services(hass: HomeAssistant) -> None:
    """Register anomaly detection services."""

    if not hass.services.has_service(DOMAIN, "anomaly_alert_check_and_alert"):

        async def _handle_check_anomaly(call: ServiceCall) -> None:
            device_id = call.data.get("device_id", "")
            threshold = call.data.get("threshold", 0.7)

            state = hass.states.get(device_id)
            if state is None:
                _LOGGER.warning("Anomaly check: entity %s not found", device_id)
                return

            # Basic anomaly detection: check if value is unusually high/low
            try:
                value = float(state.state)
            except (ValueError, TypeError):
                _LOGGER.debug("Entity %s has non-numeric state, skipping anomaly check", device_id)
                return

            hass.bus.async_fire(
                f"{DOMAIN}_anomaly_check",
                {
                    "device_id": device_id,
                    "value": value,
                    "threshold": threshold,
                    "state": state.state,
                    "attributes": dict(state.attributes),
                },
            )

        hass.services.async_register(
            DOMAIN,
            "anomaly_alert_check_and_alert",
            _handle_check_anomaly,
            schema=vol.Schema({
                vol.Required("device_id"): str,
                vol.Optional("threshold"): vol.Coerce(float),
            }),
        )

    if not hass.services.has_service(DOMAIN, "anomaly_alert_clear_history"):

        async def _handle_clear_anomaly(_: ServiceCall) -> None:
            for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
                if not isinstance(entry_data, dict):
                    continue
                anomaly_store = entry_data.get("anomaly_history")
                if anomaly_store and hasattr(anomaly_store, "clear"):
                    anomaly_store.clear()
            _LOGGER.info("Anomaly history cleared")

        hass.services.async_register(
            DOMAIN, "anomaly_alert_clear_history", _handle_clear_anomaly
        )


# ---------------------------------------------------------------------------
# Energy Insights service
# ---------------------------------------------------------------------------

def _register_energy_services(hass: HomeAssistant) -> None:
    """Register energy insights services."""

    if not hass.services.has_service(DOMAIN, "energy_insights_get"):

        async def _handle_energy_insights(call: ServiceCall) -> None:
            device_id = call.data.get("device_id")
            hours = call.data.get("hours", 24)

            insights = {
                "device_id": device_id,
                "hours": hours,
                "recommendations": [],
            }

            # Collect energy data from HA
            energy_entities = [
                s for s in hass.states.async_entity_ids("sensor")
                if "energy" in s.lower() or "power" in s.lower()
            ]

            if device_id:
                energy_entities = [e for e in energy_entities if device_id in e]

            for eid in energy_entities[:20]:
                state = hass.states.get(eid)
                if state and state.state not in ("unknown", "unavailable"):
                    try:
                        val = float(state.state)
                        insights["recommendations"].append({
                            "entity": eid,
                            "value": val,
                            "unit": state.attributes.get("unit_of_measurement", ""),
                        })
                    except (ValueError, TypeError):
                        pass

            hass.bus.async_fire(
                f"{DOMAIN}_energy_insights",
                insights,
            )

        hass.services.async_register(
            DOMAIN,
            "energy_insights_get",
            _handle_energy_insights,
            schema=vol.Schema({
                vol.Optional("device_id"): str,
                vol.Optional("hours"): int,
            }),
        )


# ---------------------------------------------------------------------------
# Habit Learning services
# ---------------------------------------------------------------------------

def _register_habit_learning_services(hass: HomeAssistant) -> None:
    """Register habit learning services."""

    if not hass.services.has_service(DOMAIN, "habit_learning_learn"):

        async def _handle_learn(call: ServiceCall) -> None:
            device_id = call.data.get("device_id", "")
            event_type = call.data.get("event_type", "")
            device_chain = call.data.get("device_chain")

            import time
            event = {
                "device_id": device_id,
                "event_type": event_type,
                "timestamp": time.time(),
                "device_chain": device_chain,
            }

            # Store in hass.data for the habit learning module
            domain_data = hass.data.setdefault(DOMAIN, {})
            habit_buffer = domain_data.setdefault("_habit_learning_buffer", [])
            habit_buffer.append(event)

            # Trim buffer
            max_size = 1000
            if len(habit_buffer) > max_size:
                del habit_buffer[:len(habit_buffer) - max_size]

            hass.bus.async_fire(
                f"{DOMAIN}_habit_learned",
                event,
            )
            _LOGGER.debug("Habit learned: %s %s", device_id, event_type)

        hass.services.async_register(
            DOMAIN,
            "habit_learning_learn",
            _handle_learn,
            schema=vol.Schema({
                vol.Required("device_id"): str,
                vol.Required("event_type"): str,
                vol.Optional("device_chain"): list,
            }),
        )

    if not hass.services.has_service(DOMAIN, "habit_learning_predict"):

        async def _handle_predict(call: ServiceCall) -> None:
            device_id = call.data.get("device_id", "")
            event_type = call.data.get("event_type", "")
            start_device = call.data.get("start_device")

            # Simple frequency-based prediction from buffer
            domain_data = hass.data.get(DOMAIN, {})
            buffer = domain_data.get("_habit_learning_buffer", [])

            matching = [
                e for e in buffer
                if e.get("device_id") == device_id and e.get("event_type") == event_type
            ]

            prediction = {
                "device_id": device_id,
                "event_type": event_type,
                "confidence": min(len(matching) / max(len(buffer), 1), 1.0) if buffer else 0.0,
                "occurrences": len(matching),
                "total_events": len(buffer),
                "start_device": start_device,
            }

            hass.bus.async_fire(
                f"{DOMAIN}_habit_prediction",
                prediction,
            )

        hass.services.async_register(
            DOMAIN,
            "habit_learning_predict",
            _handle_predict,
            schema=vol.Schema({
                vol.Required("device_id"): str,
                vol.Required("event_type"): str,
                vol.Optional("start_device"): str,
            }),
        )


# ---------------------------------------------------------------------------
# HomeKit Bridge services (per-zone toggle)
# ---------------------------------------------------------------------------

def _register_homekit_services(hass: HomeAssistant) -> None:
    """Register HomeKit bridge per-zone services."""

    if not hass.services.has_service(DOMAIN, "homekit_enable_zone"):

        async def _handle_enable_zone(call: ServiceCall) -> None:
            zone_id = call.data.get("zone_id", "")
            zone_name = call.data.get("zone_name", zone_id)
            if not zone_id:
                return
            for entry in hass.config_entries.async_entries(DOMAIN):
                from .core.modules.homekit_bridge import get_homekit_bridge
                bridge = get_homekit_bridge(hass, entry.entry_id)
                if not bridge:
                    continue
                # Get zone entities
                try:
                    from .habitus_zones_store_v2 import async_get_zones_v2
                    zones = await async_get_zones_v2(hass, entry.entry_id)
                    zone = next((z for z in zones if z.zone_id == zone_id), None)
                    if zone:
                        entity_ids = list(zone.entity_ids) if zone.entity_ids else []
                        result = await bridge.async_enable_zone(zone_id, zone_name or zone.name, entity_ids)
                        hass.bus.async_fire(
                            f"{DOMAIN}_homekit_zone_toggled",
                            {"zone_id": zone_id, "enabled": True, **result},
                        )
                except Exception as exc:
                    _LOGGER.warning("HomeKit enable zone failed: %s", exc)
                break

        hass.services.async_register(
            DOMAIN,
            "homekit_enable_zone",
            _handle_enable_zone,
            schema=vol.Schema({
                vol.Required("zone_id"): str,
                vol.Optional("zone_name"): str,
            }),
        )

    if not hass.services.has_service(DOMAIN, "homekit_disable_zone"):

        async def _handle_disable_zone(call: ServiceCall) -> None:
            zone_id = call.data.get("zone_id", "")
            if not zone_id:
                return
            for entry in hass.config_entries.async_entries(DOMAIN):
                from .core.modules.homekit_bridge import get_homekit_bridge
                bridge = get_homekit_bridge(hass, entry.entry_id)
                if not bridge:
                    continue
                result = await bridge.async_disable_zone(zone_id)
                hass.bus.async_fire(
                    f"{DOMAIN}_homekit_zone_toggled",
                    {"zone_id": zone_id, "enabled": False, **result},
                )
                break

        hass.services.async_register(
            DOMAIN,
            "homekit_disable_zone",
            _handle_disable_zone,
            schema=vol.Schema({vol.Required("zone_id"): str}),
        )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def async_register_all_services(hass: HomeAssistant) -> None:
    """Register all domain-level services (called from async_setup)."""
    _register_installation_guide_service(hass)
    _register_tag_registry_services(hass)
    _register_media_context_v2_services(hass)
    _register_forwarder_n3_services(hass)
    _register_ops_runbook_services(hass)
    _register_habitus_dashboard_cards_services(hass)
    _register_mupl_services(hass)
    _register_camera_context_services(hass)
    _register_debug_services(hass)
    _register_unifi_services(hass)
    _register_predictive_services(hass)
    _register_anomaly_services(hass)
    _register_energy_services(hass)
    _register_habit_learning_services(hass)
    _register_homekit_services(hass)
