from __future__ import annotations

import json
import logging

from aiohttp.web import Response

from homeassistant.core import HomeAssistant
from homeassistant.components import webhook

from .api import CopilotStatus
from .const import CONF_TOKEN, CONF_WEBHOOK_ID, DOMAIN, HEADER_AUTH

_LOGGER = logging.getLogger(__name__)

# Event types the add-on can push via webhook
EVENT_TYPE_STATUS = "status"
EVENT_TYPE_MOOD = "mood_changed"
EVENT_TYPE_SUGGESTION = "suggestion_new"
EVENT_TYPE_NEURON = "neuron_update"


def _make_webhook_url(hass: HomeAssistant, webhook_id: str) -> str:
    # Public base url or internal depending on HA config.
    return webhook.async_generate_url(hass, webhook_id)


async def async_ensure_webhook(hass: HomeAssistant, entry) -> str:
    webhook_id = entry.data.get(CONF_WEBHOOK_ID)
    if webhook_id:
        return webhook_id

    webhook_id = webhook.async_generate_id()
    hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_WEBHOOK_ID: webhook_id})
    return webhook_id


def _merge_coordinator_data(coordinator, updates: dict) -> dict:
    """Merge partial updates into existing coordinator data dict."""
    current = coordinator.data if isinstance(coordinator.data, dict) else {}
    merged = {**current, **updates}
    return merged


async def async_register_webhook(hass: HomeAssistant, entry, coordinator) -> str:
    webhook_id = await async_ensure_webhook(hass, entry)

    async def _handle(hass: HomeAssistant, webhook_id: str, request):
        token_expected = (entry.data | entry.options).get(CONF_TOKEN)
        token_got = request.headers.get(HEADER_AUTH)

        if token_expected and token_got != token_expected:
            _LOGGER.warning("Rejected webhook: invalid token")
            return Response(status=401)

        try:
            payload = await request.json()
        except Exception:  # noqa: BLE001
            return Response(status=400)

        if not isinstance(payload, dict):
            return Response(status=400)

        # Typed envelope: {"type": "mood_changed", "data": {...}}
        event_type = payload.get("type", EVENT_TYPE_STATUS)
        data = payload.get("data") if payload.get("data") else payload

        if event_type == EVENT_TYPE_MOOD:
            # Add-on pushes mood change: merge into coordinator data
            updates = {
                "mood": data,
                "dominant_mood": data.get("mood", "unknown"),
                "mood_confidence": data.get("confidence", 0.0),
            }
            merged = _merge_coordinator_data(coordinator, updates)
            coordinator.async_set_updated_data(merged)
            _LOGGER.debug("Webhook: mood push received – %s", data.get("mood"))

        elif event_type == EVENT_TYPE_NEURON:
            # Add-on pushes neuron state update
            updates = {"neurons": data.get("neurons", {})}
            merged = _merge_coordinator_data(coordinator, updates)
            coordinator.async_set_updated_data(merged)
            _LOGGER.debug("Webhook: neuron update received")

        elif event_type == EVENT_TYPE_SUGGESTION:
            # Add-on pushes new suggestion – fire HA event for suggestion panel
            hass.bus.async_fire(
                f"{DOMAIN}_suggestion_received",
                {"suggestion": data},
            )
            _LOGGER.debug("Webhook: suggestion push received")

        else:
            # Legacy status push (online/version)
            online = data.get("online")
            version = data.get("version")

            updates = {}
            if online is not None:
                updates["ok"] = bool(online)
            if isinstance(version, str):
                updates["version"] = version

            if updates:
                merged = _merge_coordinator_data(coordinator, updates)
                coordinator.async_set_updated_data(merged)

        return Response(
            status=200,
            text=json.dumps({"ok": True}),
            content_type="application/json",
        )

    webhook.async_register(
        hass,
        DOMAIN,
        f"PilotSuite webhook ({entry.entry_id})",
        webhook_id,
        _handle,
    )

    return webhook_id


async def async_unregister_webhook(hass: HomeAssistant, webhook_id: str) -> None:
    webhook.async_unregister(hass, webhook_id)
