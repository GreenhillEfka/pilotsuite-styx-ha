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
from .tag_registry import (
    async_confirm_tag,
    async_set_assignment,
    async_sync_labels_now,
    async_upsert_tag,
)


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
    return runtime


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Install shipped blueprints (does not create automations).
    await async_install_blueprints(hass)

    runtime = _get_runtime(hass)
    await runtime.async_setup_entry(
        entry,
        modules=["legacy", "performance_scaling", "events_forwarder", "dev_surface", "habitus_miner", "ops_runbook"],
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime = _get_runtime(hass)
    return await runtime.async_unload_entry(
        entry,
        modules=["legacy", "performance_scaling", "events_forwarder", "dev_surface", "habitus_miner", "ops_runbook"],
    )
