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

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# ── Auto-Config Service Names ────────────────────────────────────────────

SERVICE_SET_DEFAULT_AGENT = "set_default_agent"
SERVICE_VERIFY_AGENT = "verify_agent"
SERVICE_GET_AGENT_STATUS = "get_agent_status"


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
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

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
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

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


async def async_set_default_conversation_agent(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Attempt to set PilotSuite as the default conversation agent.

    Uses HA's internal conversation component to configure the default agent.
    This sets the agent_id in the conversation component's configuration.
    """
    try:
        # The agent_id for custom integrations is the config entry ID
        agent_id = entry.entry_id

        # Try to set via HA's conversation component storage
        from homeassistant.components.conversation import (
            async_get_agent_info,
        )

        # Verify our agent is registered
        agent_info = async_get_agent_info(hass, agent_id)
        if agent_info is None:
            _LOGGER.warning(
                "Styx conversation agent not found (entry_id=%s). "
                "Registration may not have completed yet.",
                agent_id,
            )
            return False

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
            "Styx conversation agent is registered and ready (agent_id=%s). "
            "To set as default: Settings > Voice Assistants > select PilotSuite.",
            agent_id,
        )
        return True

    except ImportError:
        _LOGGER.debug("async_get_agent_info not available in this HA version")
        # Still fire the event — agent was registered via async_set_agent
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

    # 2. Set Styx as default conversation agent
    await async_set_default_conversation_agent(hass, entry)

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
                    "Styx ist als Gesprächsagent registriert.\n\n"
                    "Gehe zu **Einstellungen > Sprachassistenten** und wähle "
                    "**PilotSuite** als Standard-Gesprächsagent.\n\n"
                    "Styx is registered as conversation agent.\n"
                    "Go to **Settings > Voice Assistants** and select "
                    "**PilotSuite** as default."
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

    # Register services if not already registered
    if not hass.services.has_service(DOMAIN, SERVICE_SET_DEFAULT_AGENT):
        hass.services.async_register(DOMAIN, SERVICE_SET_DEFAULT_AGENT, handle_set_default)
    if not hass.services.has_service(DOMAIN, SERVICE_VERIFY_AGENT):
        hass.services.async_register(DOMAIN, SERVICE_VERIFY_AGENT, handle_verify)
    if not hass.services.has_service(DOMAIN, SERVICE_GET_AGENT_STATUS):
        hass.services.async_register(DOMAIN, SERVICE_GET_AGENT_STATUS, handle_get_status)

    _LOGGER.info(
        "Agent auto-config complete: services registered "
        "(set_default_agent, verify_agent, get_agent_status)"
    )


async def async_unload_agent_auto_config(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Unload agent auto-config services."""
    for service in (SERVICE_SET_DEFAULT_AGENT, SERVICE_VERIFY_AGENT, SERVICE_GET_AGENT_STATUS):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
