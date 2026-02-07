from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .habitus_zones_store import async_get_zones, async_set_zones_from_raw
from .config_snapshot_store import (
    async_get_state,
    async_set_last_generated,
    async_set_last_published,
)


EXPORT_DIR = "/config/ai_home_copilot/exports"
PUBLISH_DIR = "/config/www/ai_home_copilot"


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _redact_options(opts: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(opts)
    # Never export secrets by default.
    for key in ("token", "auth_token"):
        if key in redacted and redacted.get(key):
            redacted[key] = "<redacted>"
    return redacted


async def async_generate_config_snapshot(hass: HomeAssistant, entry: ConfigEntry) -> str:
    """Generate a local JSON snapshot of the integration configuration.

    Governance/privacy-first: secrets are redacted; file is written locally under /config.
    """

    os.makedirs(EXPORT_DIR, exist_ok=True)

    zones = await async_get_zones(hass, entry.entry_id)
    zones_raw = [{"id": z.zone_id, "name": z.name, "entity_ids": list(z.entity_ids)} for z in zones]

    # Options contain host/port/media lists/forwarder settings; entry.data contains original setup.
    options = dict(entry.options)
    data = dict(entry.data)

    snapshot: dict[str, Any] = {
        "schema": "ai_home_copilot_config_snapshot",
        "version": 1,
        "generated": datetime.now(timezone.utc).isoformat(),
        "entry": {
            "title": entry.title,
            "entry_id": entry.entry_id,
        },
        "data": _redact_options(data),
        "options": _redact_options(options),
        "habitus_zones": zones_raw,
        "notes": {
            "secrets": "Tokens are redacted by default. Re-enter them manually after import if needed.",
        },
    }

    fname = f"ai_home_copilot_snapshot_{_now_stamp()}.json"
    path = os.path.join(EXPORT_DIR, fname)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, ensure_ascii=False, indent=2)

    await async_set_last_generated(hass, path)

    persistent_notification.async_create(
        hass,
        f"Generated config snapshot:\n{path}",
        title="AI Home CoPilot config snapshot",
        notification_id="ai_home_copilot_config_snapshot",
    )

    return path


async def async_publish_last_config_snapshot(hass: HomeAssistant) -> str:
    state = await async_get_state(hass)
    src = state.last_generated_path
    if not src:
        raise ValueError("No snapshot generated yet. Click 'generate config snapshot' first.")

    os.makedirs(PUBLISH_DIR, exist_ok=True)
    base = os.path.basename(src)
    dst = os.path.join(PUBLISH_DIR, base)
    shutil.copyfile(src, dst)

    await async_set_last_published(hass, dst)

    url = f"/local/ai_home_copilot/{base}"
    persistent_notification.async_create(
        hass,
        f"Published snapshot for download:\n{url}",
        title="AI Home CoPilot config snapshot",
        notification_id="ai_home_copilot_config_snapshot",
    )
    return url


def _strip_redacted(opts: dict[str, Any], *, keep_existing: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for k, v in opts.items():
        if v == "<redacted>":
            # keep existing secret
            if k in keep_existing:
                cleaned[k] = keep_existing[k]
            continue
        cleaned[k] = v
    return cleaned


async def async_apply_config_snapshot(
    hass: HomeAssistant,
    entry: ConfigEntry,
    snapshot: dict[str, Any],
) -> None:
    """Apply snapshot to HA storage/options (no silent actions beyond config storage).

    - Habitus zones are written to our store.
    - Options are updated (secrets remain unchanged if redacted).
    - Finally reload config entry.
    """

    zones = snapshot.get("habitus_zones")
    if zones is None:
        zones = []

    if not isinstance(zones, list):
        raise ValueError("Snapshot habitus_zones must be a list")

    await async_set_zones_from_raw(hass, entry.entry_id, zones)

    snap_opts = snapshot.get("options")
    if isinstance(snap_opts, dict):
        # Preserve current secrets when snapshot has redacted values.
        merged = _strip_redacted(dict(snap_opts), keep_existing=dict(entry.options))
        hass.config_entries.async_update_entry(entry, options=merged)

    # entry.data is treated as setup-time config; we generally do not overwrite it.
    await hass.config_entries.async_reload(entry.entry_id)
