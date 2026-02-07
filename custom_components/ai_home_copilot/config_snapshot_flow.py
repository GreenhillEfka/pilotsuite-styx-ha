from __future__ import annotations

import json
import os
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .config_snapshot import (
    EXPORT_DIR,
    async_apply_config_snapshot,
)


STEP_IMPORT_SOURCE = vol.Schema(
    {
        vol.Required("source", default="path"): vol.In(
            {
                "path": "Import from local file path",
                "paste": "Paste JSON",
            }
        )
    }
)

STEP_IMPORT_PATH = vol.Schema(
    {
        vol.Required("path"): str,
    }
)

STEP_IMPORT_PASTE = vol.Schema(
    {
        vol.Required("json"): str,
    }
)

STEP_CONFIRM = vol.Schema(
    {
        vol.Required("confirm", default=False): bool,
    }
)


def _load_json_path(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, dict):
        raise ValueError("Snapshot must be a JSON object")
    return raw


class ConfigSnapshotOptionsFlow:
    """Mixin-like helper for OptionsFlowHandler (kept separate to keep config_flow.py small)."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry
        self._snapshot: dict[str, Any] | None = None

    async def async_step_backup_restore(self, user_input: dict | None = None) -> FlowResult:
        return self.async_show_menu(
            step_id="backup_restore",
            menu_options=["import_snapshot", "back"],
        )

    async def async_step_import_snapshot(self, user_input: dict | None = None) -> FlowResult:
        if user_input is None:
            return self.async_show_form(step_id="import_snapshot", data_schema=STEP_IMPORT_SOURCE)

        src = user_input.get("source")
        if src == "paste":
            return await self.async_step_import_snapshot_paste()
        return await self.async_step_import_snapshot_path()

    async def async_step_import_snapshot_path(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            path = str(user_input.get("path") or "").strip()
            try:
                snap = _load_json_path(path)
            except Exception:
                errors["base"] = "cannot_read"
            else:
                self._snapshot = snap
                return await self.async_step_import_snapshot_confirm()

        return self.async_show_form(
            step_id="import_snapshot_path",
            data_schema=STEP_IMPORT_PATH,
            errors=errors,
            description_placeholders={
                "hint": f"Tip: snapshots are generated to {EXPORT_DIR}",
            },
        )

    async def async_step_import_snapshot_paste(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            raw = str(user_input.get("json") or "").strip()
            try:
                snap = json.loads(raw)
                if not isinstance(snap, dict):
                    raise ValueError("not an object")
            except Exception:
                errors["base"] = "invalid_json"
            else:
                self._snapshot = snap
                return await self.async_step_import_snapshot_confirm()

        return self.async_show_form(step_id="import_snapshot_paste", data_schema=STEP_IMPORT_PASTE, errors=errors)

    async def async_step_import_snapshot_confirm(self, user_input: dict | None = None) -> FlowResult:
        snap = self._snapshot or {}

        if user_input is not None:
            if not user_input.get("confirm"):
                return self.async_show_form(
                    step_id="import_snapshot_confirm",
                    data_schema=STEP_CONFIRM,
                    errors={"base": "confirm_required"},
                )

            await async_apply_config_snapshot(self.hass, self._entry, snap)
            return self.async_create_entry(title="", data={"result": "imported"})

        # Minimal preview text
        zones = snap.get("habitus_zones")
        n_zones = len(zones) if isinstance(zones, list) else 0
        return self.async_show_form(
            step_id="import_snapshot_confirm",
            data_schema=STEP_CONFIRM,
            description_placeholders={
                "zones": str(n_zones),
            },
        )
