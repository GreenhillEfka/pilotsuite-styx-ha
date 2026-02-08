"""Ops Runbook – HA integration (v0.1 kernel).

Fetches preflight check results from Copilot Core and exposes them
as a sensor + button in Home Assistant.

Privacy-first: no secrets or entity-IDs are transmitted.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_run_preflight(
    hass: HomeAssistant,
    entry: ConfigEntry | None = None,
    *,
    api=None,
) -> dict:
    """Call Core /api/v1/ops/runbook/preflight and return the result dict.

    Returns a dict with keys: ok (bool), checks (list), time (str), error (str|None).
    """
    if api is None:
        if entry is None:
            return {"ok": False, "checks": [], "time": "", "error": "no entry/api"}
        data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if isinstance(data, dict):
            api = data.get("coordinator", None)
            if api is not None:
                api = getattr(api, "api", None)
        if api is None:
            return {"ok": False, "checks": [], "time": "", "error": "no api available"}

    try:
        result = await api.async_get("/api/v1/ops/runbook/preflight")
        if not isinstance(result, dict):
            return {"ok": False, "checks": [], "time": "", "error": "unexpected response"}
        return {
            "ok": bool(result.get("ok", False)),
            "checks": result.get("checks", []),
            "time": str(result.get("time", "")),
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("ops_runbook preflight failed: %s", exc)
        return {"ok": False, "checks": [], "time": "", "error": str(exc)}


async def async_show_preflight_notification(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Run preflight and display results as a persistent notification."""
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    api = None
    if isinstance(data, dict):
        coord = data.get("coordinator")
        if coord is not None:
            api = getattr(coord, "api", None)

    result = await async_run_preflight(hass, entry, api=api)

    if result.get("error"):
        persistent_notification.async_create(
            hass,
            f"Preflight check failed: {result['error']}",
            title="AI Home CoPilot Ops Runbook – Preflight",
            notification_id="ai_home_copilot_ops_preflight",
        )
        return

    lines: list[str] = []
    lines.append(f"Overall: {'✅ OK' if result['ok'] else '❌ ISSUES FOUND'}")
    lines.append(f"Time: {result.get('time', '?')}")
    lines.append("")

    checks = result.get("checks", [])
    for chk in checks:
        if not isinstance(chk, dict):
            continue
        icon = "✅" if chk.get("ok") else "❌"
        title = chk.get("title", "?")
        detail = chk.get("detail", "")
        lines.append(f"{icon} **{title}**: {detail}")

    persistent_notification.async_create(
        hass,
        "\n".join(lines),
        title="AI Home CoPilot Ops Runbook – Preflight",
        notification_id="ai_home_copilot_ops_preflight",
    )
