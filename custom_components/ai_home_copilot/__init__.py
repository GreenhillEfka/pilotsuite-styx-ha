from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

import voluptuous as vol

from .const import DOMAIN
from .media_context_v2_setup import MediaContextV2ConfigManager
from .blueprints import async_install_blueprints
from .core.runtime import CopilotRuntime
from .core.modules.legacy import LegacyModule
from .core.modules.events_forwarder import EventsForwarderModule
from .core.modules.dev_surface import DevSurfaceModule
from .core.modules.performance_scaling import PerformanceScalingModule
from .core.modules.habitus_miner import HabitusMinerModule
from .core.modules.ops_runbook import OpsRunbookModule
from .core.modules.unifi_module import UniFiModule
from .core.modules.brain_graph_sync import BrainGraphSyncModule
from .tag_registry import (
    async_confirm_tag,
    async_set_assignment,
    async_sync_labels_now,
    async_upsert_tag,
)
from .tag_sync import async_pull_tag_system_snapshot


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})

    # Minimal Tag Registry v0.1 services (governance-first):
    # - confirm_tag: manual confirmation gate for learned.* / candidate.*
    # - sync_labels_now: apply confirmed tags to HA labels + assignments
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

    # Media Context v2 services
    if not hass.services.has_service(DOMAIN, "media_context_v2_suggest_zone_mapping"):

        async def _handle_suggest_zone_mapping(call: ServiceCall) -> None:
            entry_id = call.data.get("entry_id")
            if not entry_id:
                return
            
            for entry in hass.config_entries.async_entries(DOMAIN):
                if entry.entry_id == entry_id:
                    manager = MediaContextV2ConfigManager(hass, entry)
                    suggestions = await manager.async_get_zone_suggestions()
                    # Could store suggestions in a sensor or fire an event
                    hass.bus.async_fire(
                        f"{DOMAIN}_media_context_v2_zone_suggestions",
                        {
                            "entry_id": entry_id,
                            "suggestions": suggestions,
                        }
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

    # N3 Forwarder services
    if not hass.services.has_service(DOMAIN, "forwarder_n3_start"):
        from .forwarder_n3 import N3EventForwarder

        async def _handle_forwarder_start(call: ServiceCall) -> None:
            entry_id = call.data.get("entry_id")
            if not entry_id:
                return
            
            # Get core URL and token from config entry
            for entry in hass.config_entries.async_entries(DOMAIN):
                if entry.entry_id == entry_id:
                    config = {
                        "core_url": entry.data.get("core_url", "http://localhost:8099"),
                        "api_token": entry.data.get("api_token", ""),
                        "enabled_domains": ["light", "climate", "media_player", "binary_sensor", "sensor", "cover", "lock", "person", "device_tracker", "weather"],
                        "batch_size": 50,
                        "flush_interval": 0.5,
                        "forward_call_service": True,
                    }
                    
                    # Create and start forwarder
                    forwarder = N3EventForwarder(hass, config)
                    await forwarder.async_start()
                    
                    # Store in hass data for later access
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
                    {"entry_id": entry_id, "stats": stats}
                )

        hass.services.async_register(
            DOMAIN,
            "forwarder_n3_stats",
            _handle_forwarder_stats,
            schema=vol.Schema({vol.Required("entry_id"): str}),
        )

    # Ops Runbook v0.1 services
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

    return True


def _get_runtime(hass: HomeAssistant) -> CopilotRuntime:
    runtime = CopilotRuntime.get(hass)
    # Register built-in modules (idempotent).
    if "legacy" not in runtime.registry.names():
        runtime.registry.register("legacy", LegacyModule)
    if "performance_scaling" not in runtime.registry.names():
        runtime.registry.register("performance_scaling", PerformanceScalingModule)
    if "events_forwarder" not in runtime.registry.names():
        runtime.registry.register("events_forwarder", EventsForwarderModule)
    if "dev_surface" not in runtime.registry.names():
        runtime.registry.register("dev_surface", DevSurfaceModule)
    if "habitus_miner" not in runtime.registry.names():
        runtime.registry.register("habitus_miner", HabitusMinerModule)
    if "ops_runbook" not in runtime.registry.names():
        runtime.registry.register("ops_runbook", OpsRunbookModule)
    if "unifi_module" not in runtime.registry.names():
        runtime.registry.register("unifi_module", UniFiModule)
    if "brain_graph_sync" not in runtime.registry.names():
        runtime.registry.register("brain_graph_sync", BrainGraphSyncModule)
    return runtime


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Install shipped blueprints (does not create automations).
    await async_install_blueprints(hass)

    runtime = _get_runtime(hass)
    await runtime.async_setup_entry(
        entry,
        modules=["legacy", "performance_scaling", "events_forwarder", "dev_surface", "habitus_miner", "ops_runbook", "unifi_module", "brain_graph_sync"],
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime = _get_runtime(hass)
    return await runtime.async_unload_entry(
        entry,
        modules=["legacy", "performance_scaling", "events_forwarder", "dev_surface", "habitus_miner", "ops_runbook", "unifi_module", "brain_graph_sync"],
    )
