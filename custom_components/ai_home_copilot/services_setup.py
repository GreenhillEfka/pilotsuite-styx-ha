"""Centralised service registration for AI Home CoPilot.

Extracted from __init__.py (v0.5.3) to keep async_setup() lean.
Pure refactor – no behaviour change.
"""
from __future__ import annotations

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall

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
                    config = {
                        "core_url": entry.data.get("core_url", "http://localhost:8909"),
                        "api_token": entry.data.get("api_token", ""),
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
# Public entry point
# ---------------------------------------------------------------------------

def async_register_all_services(hass: HomeAssistant) -> None:
    """Register all domain-level services (called from async_setup)."""
    _register_tag_registry_services(hass)
    _register_media_context_v2_services(hass)
    _register_forwarder_n3_services(hass)
    _register_ops_runbook_services(hass)
    _register_habitus_dashboard_cards_services(hass)
    _register_mupl_services(hass)
    _register_camera_context_services(hass)
