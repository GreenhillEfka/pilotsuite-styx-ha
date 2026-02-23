"""Styx Agent Auto-Config for Home Assistant (v5.21.0).

Automatically configures Styx as the default HA conversation agent,
verifies bidirectional communication, and provides setup services.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later

from .connection_config import build_core_headers
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# ── Auto-Config Service Names ────────────────────────────────────────────

SERVICE_SET_DEFAULT_AGENT = "set_default_agent"
SERVICE_VERIFY_AGENT = "verify_agent"
SERVICE_GET_AGENT_STATUS = "get_agent_status"
SERVICE_REPAIR_AGENT = "repair_agent"


async def async_verify_agent_connectivity(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Verify bidirectional connectivity between HA and Core.

    1. HA → Core: POST /api/v1/agent/verify
    2. Core → HA: responds with echo + status
    """
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = entry_data.get("coordinator")

    if coordinator is None:
        return {"ok": False, "error": "Coordinator not available"}

    host = coordinator._config.get("host", "homeassistant.local")
    port = coordinator._config.get("port", 8909)
    token = coordinator._config.get("token", "")

    session = async_get_clientsession(hass)
    verify_url = f"http://{host}:{port}/api/v1/agent/verify"
    status_url = f"http://{host}:{port}/chat/status"
    headers = build_core_headers(token)

    try:
        async with session.post(
            verify_url,
            json={"message": "ha_handshake", "source": "ha_integration"},
            headers=headers,
            timeout=10,
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("ok"):
                    _LOGGER.info(
                        "Agent connectivity verified: %s (%s)",
                        data.get("agent_name", "Styx"),
                        data.get("llm_model", "unknown"),
                    )
                    return {
                        "ok": True,
                        "agent_name": data.get("agent_name"),
                        "agent_ready": data.get("agent_ready"),
                        "llm_available": data.get("llm_available"),
                        "llm_model": data.get("llm_model"),
                        "features": data.get("features", []),
                    }
            if resp.status not in (404, 405):
                return {"ok": False, "error": f"Core returned status {resp.status}"}

        # Backward-compatible fallback for cores without /api/v1/agent/verify.
        async with session.get(status_url, headers=headers, timeout=10) as resp:
            if resp.status != 200:
                return {"ok": False, "error": f"Core returned status {resp.status}"}
            data = await resp.json()
            return {
                "ok": bool(data.get("available", False)),
                "agent_name": data.get("assistant_name", "Styx"),
                "agent_ready": bool(data.get("available", False)),
                "llm_available": bool(data.get("available", False)),
                "llm_model": data.get("model") or data.get("cloud_model"),
                "features": data.get("characters", []),
            }
    except TimeoutError:
        return {"ok": False, "error": "Connection to Core timed out"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def async_get_agent_status(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Get full agent status from Core."""
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = entry_data.get("coordinator")

    if coordinator is None:
        return {"ok": False, "error": "Coordinator not available"}

    host = coordinator._config.get("host", "homeassistant.local")
    port = coordinator._config.get("port", 8909)
    token = coordinator._config.get("token", "")

    session = async_get_clientsession(hass)
    url = f"http://{host}:{port}/api/v1/agent/status"
    fallback_url = f"http://{host}:{port}/chat/status"
    headers = build_core_headers(token)

    try:
        async with session.get(url, headers=headers, timeout=10) as resp:
            if resp.status == 200:
                return await resp.json()
            if resp.status not in (404, 405):
                return {"ok": False, "error": f"Core returned status {resp.status}"}

        # Backward-compatible fallback for cores without /api/v1/agent/status.
        async with session.get(fallback_url, headers=headers, timeout=10) as resp:
            if resp.status != 200:
                return {"ok": False, "error": f"Core returned status {resp.status}"}
            data = await resp.json()
            available = bool(data.get("available", False))
            llm_backend = str(data.get("active_provider", "none"))
            llm_model = data.get("model") or data.get("cloud_model") or ""
            return {
                "ok": True,
                "agent_name": data.get("assistant_name", "Styx"),
                "agent_version": data.get("version", "unknown"),
                "status": "ready" if available else "degraded",
                "llm_model": llm_model,
                "llm_backend": llm_backend,
                "character": data.get("character", "copilot"),
                "features": data.get("characters", []),
                "uptime_seconds": 0,
            }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def async_attempt_agent_self_heal(
    hass: HomeAssistant, entry: ConfigEntry, *, reason: str = "manual"
) -> dict[str, Any]:
    """Trigger Core-side self-heal flow (best effort)."""
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = entry_data.get("coordinator")

    if coordinator is None:
        return {"ok": False, "error": "Coordinator not available"}

    host = coordinator._config.get("host", "homeassistant.local")
    port = coordinator._config.get("port", 8909)
    token = coordinator._config.get("token", "")

    session = async_get_clientsession(hass)
    url = f"http://{host}:{port}/api/v1/agent/self-heal"
    headers = build_core_headers(token)

    try:
        async with session.post(
            url,
            json={"reason": reason, "source": "ha_integration"},
            headers=headers,
            timeout=20,
        ) as resp:
            if resp.status == 200:
                return await resp.json()
            return {"ok": False, "error": f"Core returned status {resp.status}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def async_set_default_conversation_agent(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Best-effort: keep Styx as active Assist conversation engine.

    Strategy:
    1) Ensure our conversation agent is registered.
    2) Update the preferred Assist pipeline to use this entry as conversation_engine.
       This survives restarts/updates because it writes pipeline storage.
    """
    try:
        # The agent_id for custom integrations is the config entry ID
        agent_id = entry.entry_id

        # Verify our agent is registered in conversation integration.
        from homeassistant.components.conversation import (
            async_get_agent_info,
        )

        agent_info = async_get_agent_info(hass, agent_id)
        if agent_info is None:
            _LOGGER.warning(
                "Styx conversation agent not found (entry_id=%s). "
                "Registration may not have completed yet.",
                agent_id,
            )
            return False

        # Persist as active engine for the preferred Assist pipeline.
        # This is what the Voice Assistants UI changes internally.
        try:
            from homeassistant.components import assist_pipeline

            pipeline = assist_pipeline.async_get_pipeline(hass)
            if pipeline.conversation_engine != agent_id:
                await assist_pipeline.async_update_pipeline(
                    hass,
                    pipeline,
                    conversation_engine=agent_id,
                )
                _LOGGER.info(
                    "Updated preferred Assist pipeline '%s' conversation_engine -> %s",
                    pipeline.id,
                    agent_id,
                )
            else:
                _LOGGER.debug(
                    "Preferred Assist pipeline '%s' already uses Styx agent",
                    pipeline.id,
                )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning(
                "Could not set preferred Assist pipeline conversation_engine to Styx: %s",
                exc,
            )

        # Fire event so automations/scripts can react
        hass.bus.async_fire(
            "pilotsuite_agent_ready",
            {
                "agent_id": agent_id,
                "agent_name": "Styx",
                "entry_id": entry.entry_id,
            },
        )

        _LOGGER.info(
            "Styx conversation agent is registered and ready (agent_id=%s).",
            agent_id,
        )
        return True

    except ImportError:
        _LOGGER.debug("async_get_agent_info not available in this HA version")
        # Conversation helpers not available in this HA version.
        # Still fire the event — agent was registered via async_set_agent.
        hass.bus.async_fire(
            "pilotsuite_agent_ready",
            {
                "agent_id": entry.entry_id,
                "agent_name": "Styx",
                "entry_id": entry.entry_id,
            },
        )
        return True

    except Exception as exc:
        _LOGGER.error("Failed to verify Styx as conversation agent: %s", exc)
        return False


async def async_setup_agent_auto_config(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Set up agent auto-config: verify connectivity, register services, set default."""

    # 1. Verify bidirectional connectivity
    connectivity = await async_verify_agent_connectivity(hass, entry)
    if connectivity.get("ok"):
        _LOGGER.info(
            "Styx agent bidirectional communication verified: %s (LLM: %s)",
            connectivity.get("agent_name", "Styx"),
            connectivity.get("llm_model", "n/a"),
        )
    else:
        _LOGGER.warning(
            "Styx agent connectivity check failed: %s. "
            "Agent will still be registered — verify Core Add-on is running.",
            connectivity.get("error", "unknown"),
        )
        repair = await async_attempt_agent_self_heal(
            hass, entry, reason="auto_setup_connectivity_failed"
        )
        if repair.get("ok"):
            _LOGGER.info(
                "Triggered Core self-heal after failed connectivity check (reason=%s)",
                "auto_setup_connectivity_failed",
            )
        else:
            _LOGGER.warning(
                "Core self-heal request failed after connectivity issue: %s",
                repair.get("error", "unknown"),
            )

    # 2. Set Styx as default conversation agent
    await async_set_default_conversation_agent(hass, entry)

    # 2b. If status says degraded/no provider, trigger one self-heal pass.
    status = await async_get_agent_status(hass, entry)
    if status.get("ok") and str(status.get("status", "")).lower() != "ready":
        repair = await async_attempt_agent_self_heal(
            hass, entry, reason="auto_setup_status_degraded"
        )
        if repair.get("ok"):
            _LOGGER.info("Triggered Core self-heal because agent status was degraded")
        else:
            _LOGGER.warning(
                "Core self-heal request failed for degraded status: %s",
                repair.get("error", "unknown"),
            )

    # 3. Register HA services
    async def handle_set_default(call: ServiceCall) -> None:
        """Service: ai_home_copilot.set_default_agent."""
        result = await async_set_default_conversation_agent(hass, entry)
        if result:
            from homeassistant.components.persistent_notification import async_create

            async_create(
                hass,
                title="Styx — Conversation Agent",
                message=(
                    "Styx ist als Gesprächsagent registriert und wurde als "
                    "Conversation-Engine in der bevorzugten Assist-Pipeline gesetzt.\n\n"
                    "Falls du mehrere Pipelines nutzt, kannst du dies in "
                    "**Einstellungen > Sprachassistenten** pro Pipeline anpassen."
                ),
                notification_id="pilotsuite_set_default_agent",
            )

    async def handle_verify(call: ServiceCall) -> None:
        """Service: ai_home_copilot.verify_agent."""
        result = await async_verify_agent_connectivity(hass, entry)

        from homeassistant.components.persistent_notification import async_create

        if result.get("ok"):
            async_create(
                hass,
                title="Styx — Agent Verified",
                message=(
                    f"Styx Agent ist erreichbar und bereit.\n\n"
                    f"**Agent:** {result.get('agent_name', 'Styx')}\n"
                    f"**LLM:** {result.get('llm_model', 'n/a')}\n"
                    f"**Features:** {', '.join(result.get('features', []))}"
                ),
                notification_id="pilotsuite_verify_agent",
            )
        else:
            async_create(
                hass,
                title="Styx — Agent Not Reachable",
                message=(
                    f"Styx Agent konnte nicht erreicht werden.\n\n"
                    f"**Fehler:** {result.get('error', 'unknown')}\n\n"
                    "Bitte prüfe ob der PilotSuite Core Add-on läuft."
                ),
                notification_id="pilotsuite_verify_agent",
            )

    async def handle_get_status(call: ServiceCall) -> None:
        """Service: ai_home_copilot.get_agent_status."""
        result = await async_get_agent_status(hass, entry)

        from homeassistant.components.persistent_notification import async_create

        if result.get("ok"):
            async_create(
                hass,
                title="Styx — Agent Status",
                message=(
                    f"**Agent:** {result.get('agent_name', 'Styx')} v{result.get('agent_version', '?')}\n"
                    f"**Status:** {result.get('status', 'unknown')}\n"
                    f"**LLM:** {result.get('llm_model', 'n/a')} ({result.get('llm_backend', 'n/a')})\n"
                    f"**Character:** {result.get('character', 'n/a')}\n"
                    f"**Uptime:** {int(result.get('uptime_seconds', 0))}s\n"
                    f"**Features:** {', '.join(result.get('features', []))}"
                ),
                notification_id="pilotsuite_agent_status",
            )
        else:
            async_create(
                hass,
                title="Styx — Agent Status Error",
                message=f"Could not retrieve agent status: {result.get('error', 'unknown')}",
                notification_id="pilotsuite_agent_status",
            )

    async def handle_repair(call: ServiceCall) -> None:
        """Service: ai_home_copilot.repair_agent."""
        result = await async_attempt_agent_self_heal(hass, entry, reason="manual_service")
        from homeassistant.components.persistent_notification import async_create

        if result.get("ok"):
            llm_backend = result.get("llm_backend", "unknown")
            llm_model = result.get("llm_model", "n/a")
            steps = result.get("steps", [])
            async_create(
                hass,
                title="Styx — Self-Repair Triggered",
                message=(
                    f"Self-repair wurde ausgelöst.\n\n"
                    f"**LLM:** {llm_model} ({llm_backend})\n"
                    f"**Schritte:** {len(steps)}\n"
                    "Hinweis: Modell-Downloads laufen ggf. im Hintergrund weiter."
                ),
                notification_id="pilotsuite_repair_agent",
            )
        else:
            async_create(
                hass,
                title="Styx — Self-Repair fehlgeschlagen",
                message=f"Self-repair konnte nicht gestartet werden: {result.get('error', 'unknown')}",
                notification_id="pilotsuite_repair_agent",
            )

    # Register services if not already registered
    if not hass.services.has_service(DOMAIN, SERVICE_SET_DEFAULT_AGENT):
        hass.services.async_register(DOMAIN, SERVICE_SET_DEFAULT_AGENT, handle_set_default)
    if not hass.services.has_service(DOMAIN, SERVICE_VERIFY_AGENT):
        hass.services.async_register(DOMAIN, SERVICE_VERIFY_AGENT, handle_verify)
    if not hass.services.has_service(DOMAIN, SERVICE_GET_AGENT_STATUS):
        hass.services.async_register(DOMAIN, SERVICE_GET_AGENT_STATUS, handle_get_status)
    if not hass.services.has_service(DOMAIN, SERVICE_REPAIR_AGENT):
        hass.services.async_register(DOMAIN, SERVICE_REPAIR_AGENT, handle_repair)

    # Delayed re-check: model pulls can take minutes; re-verify after startup.
    async def _delayed_health_check(_now) -> None:
        delayed_status = await async_get_agent_status(hass, entry)
        if delayed_status.get("ok") and str(delayed_status.get("status", "")).lower() == "ready":
            return
        await async_attempt_agent_self_heal(hass, entry, reason="delayed_post_setup")

    unsub_delayed = async_call_later(hass, 60, _delayed_health_check)
    entry_store = hass.data.setdefault(DOMAIN, {}).setdefault(entry.entry_id, {})
    if isinstance(entry_store, dict):
        entry_store["_agent_auto_config_unsub"] = unsub_delayed

    _LOGGER.info(
        "Agent auto-config complete: services registered "
        "(set_default_agent, verify_agent, get_agent_status, repair_agent)"
    )


async def async_unload_agent_auto_config(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Unload agent auto-config services."""
    entry_store = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    if isinstance(entry_store, dict):
        unsub = entry_store.pop("_agent_auto_config_unsub", None)
        if callable(unsub):
            unsub()

    for service in (
        SERVICE_SET_DEFAULT_AGENT,
        SERVICE_VERIFY_AGENT,
        SERVICE_GET_AGENT_STATUS,
        SERVICE_REPAIR_AGENT,
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
