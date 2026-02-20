"""Local user preference API endpoints for PilotSuite.

Privacy-first: user IDs remain local and are never forwarded to Core.
"""
from __future__ import annotations

import logging
from typing import Any

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class _UserPreferenceBaseView(HomeAssistantView):
    """Base view with shared helpers."""

    requires_auth = True

    def __init__(self, module) -> None:
        self._module = module

    def _json_response(self, payload: dict, status: int = 200) -> web.Response:
        return web.json_response(payload, status=status)


class UserPreferencesView(_UserPreferenceBaseView):
    """GET all preferences for a user."""

    url = "/api/v1/user/{user_id}/preferences"
    name = "api:ai_home_copilot:user_preferences"

    async def get(self, request: web.Request) -> web.Response:
        user_id = request.match_info.get("user_id", "")
        if not user_id:
            return self._json_response({"error": "user_id_required"}, status=400)

        prefs = self._module.get_user_preference(user_id)
        if prefs is None:
            return self._json_response({"user_id": user_id, "preferences": {}}, status=200)

        return self._json_response({"user_id": user_id, "preferences": prefs}, status=200)


class UserZonePreferenceView(_UserPreferenceBaseView):
    """GET preference for a user in a specific zone."""

    url = "/api/v1/user/{user_id}/zone/{zone_id}/preference"
    name = "api:ai_home_copilot:user_zone_preference"

    async def get(self, request: web.Request) -> web.Response:
        user_id = request.match_info.get("user_id", "")
        zone_id = request.match_info.get("zone_id", "")

        if not user_id or not zone_id:
            return self._json_response({"error": "user_id_and_zone_id_required"}, status=400)

        pref = self._module.get_user_preference(user_id, zone_id)
        if pref is None:
            return self._json_response({"user_id": user_id, "zone_id": zone_id, "preference": None}, status=200)

        return self._json_response({"user_id": user_id, "zone_id": zone_id, "preference": pref}, status=200)


class UserPreferenceUpdateView(_UserPreferenceBaseView):
    """POST to update a user's preference for a zone."""

    url = "/api/v1/user/{user_id}/preference"
    name = "api:ai_home_copilot:user_preference_update"

    async def post(self, request: web.Request) -> web.Response:
        user_id = request.match_info.get("user_id", "")
        if not user_id:
            return self._json_response({"error": "user_id_required"}, status=400)

        try:
            payload = await request.json()
        except Exception:  # noqa: BLE001
            return self._json_response({"error": "invalid_json"}, status=400)

        if not isinstance(payload, dict):
            return self._json_response({"error": "invalid_payload"}, status=400)

        zone_id = payload.get("zone_id")
        if not isinstance(zone_id, str) or not zone_id:
            return self._json_response({"error": "zone_id_required"}, status=400)

        def _as_float(val: Any, field: str) -> float | None:
            if val is None:
                return None
            try:
                return float(val)
            except (TypeError, ValueError) as exc:
                raise ValueError(field) from exc

        try:
            comfort_bias = _as_float(payload.get("comfort_bias"), "comfort_bias")
            frugality_bias = _as_float(payload.get("frugality_bias"), "frugality_bias")
            joy_bias = _as_float(payload.get("joy_bias"), "joy_bias")
        except ValueError as err:
            return self._json_response({"error": f"invalid_{err}"}, status=400)

        updated = await self._module.update_user_preference(
            user_id=user_id,
            zone_id=zone_id,
            comfort_bias=comfort_bias,
            frugality_bias=frugality_bias,
            joy_bias=joy_bias,
        )

        return self._json_response({"user_id": user_id, "zone_id": zone_id, "preference": updated}, status=200)


async def async_register_user_preference_api(
    hass: HomeAssistant,
    entry_id: str,
    module,
) -> None:
    """Register user preference API views.

    Only registers once per HA instance.
    """
    dom = hass.data.setdefault(DOMAIN, {})
    if dom.get("user_preference_api_registered"):
        return

    hass.http.register_view(UserPreferencesView(module))
    hass.http.register_view(UserZonePreferenceView(module))
    hass.http.register_view(UserPreferenceUpdateView(module))

    dom["user_preference_api_registered"] = True
    _LOGGER.info("User preference API registered for entry %s", entry_id)
