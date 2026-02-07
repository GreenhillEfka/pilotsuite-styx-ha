from __future__ import annotations

import json
import logging

from aiohttp.web import Response

from homeassistant.core import HomeAssistant
from homeassistant.components import webhook

from .api import CopilotStatus
from .const import CONF_TOKEN, CONF_WEBHOOK_ID, DOMAIN, HEADER_AUTH

_LOGGER = logging.getLogger(__name__)


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

        # Accept either direct {online/version} or typed envelope.
        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, dict):
            payload = data

        online = payload.get("online")
        version = payload.get("version")

        status = CopilotStatus(
            ok=bool(online) if online is not None else None,
            version=version if isinstance(version, str) else None,
        )

        coordinator.async_set_updated_data(status)
        return Response(
            status=200,
            text=json.dumps({"ok": True}),
            content_type="application/json",
        )

    webhook.async_register(
        hass,
        DOMAIN,
        f"AI Home CoPilot webhook ({entry.entry_id})",
        webhook_id,
        _handle,
    )

    return webhook_id


async def async_unregister_webhook(hass: HomeAssistant, webhook_id: str) -> None:
    webhook.async_unregister(hass, webhook_id)
