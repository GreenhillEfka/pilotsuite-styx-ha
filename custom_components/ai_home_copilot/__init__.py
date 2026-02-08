from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

import voluptuous as vol

from .const import DOMAIN
from .blueprints import async_install_blueprints
from .core.runtime import CopilotRuntime
from .core.modules.legacy import LegacyModule
from .core.modules.events_forwarder import EventsForwarderModule
from .core.modules.dev_surface import DevSurfaceModule
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

    return True


def _get_runtime(hass: HomeAssistant) -> CopilotRuntime:
    runtime = CopilotRuntime.get(hass)
    # Register built-in modules (idempotent).
    if "legacy" not in runtime.registry.names():
        runtime.registry.register("legacy", LegacyModule)
    if "events_forwarder" not in runtime.registry.names():
        runtime.registry.register("events_forwarder", EventsForwarderModule)
    if "dev_surface" not in runtime.registry.names():
        runtime.registry.register("dev_surface", DevSurfaceModule)
    return runtime


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Install shipped blueprints (does not create automations).
    await async_install_blueprints(hass)

    runtime = _get_runtime(hass)
    await runtime.async_setup_entry(entry, modules=["legacy", "events_forwarder", "dev_surface"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime = _get_runtime(hass)
    return await runtime.async_unload_entry(entry, modules=["legacy", "events_forwarder", "dev_surface"])
