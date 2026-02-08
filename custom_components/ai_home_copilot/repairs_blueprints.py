from __future__ import annotations

import asyncio
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .blueprints import async_install_blueprints
from .const import DOMAIN


_TX_STORE_KEY = "openclaw_repairs_transactions"
_TX_STORE_VERSION = 1


@dataclass(frozen=True)
class BlueprintApplyPlan:
    entry_id: str
    candidate_id: str
    issue_id: str

    blueprint_path: str
    blueprint_inputs: dict[str, Any]

    risk: str = "medium"
    slug: str = "ai_home_copilot__a_to_b_safe"
    automation_name: str = "AI Home CoPilot: A→B (safe)"


def _sha256_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


async def _async_read_bytes(path: Path) -> bytes:
    return await asyncio.get_running_loop().run_in_executor(None, path.read_bytes)


async def _async_write_bytes_atomic(path: Path, data: bytes) -> None:
    def _write() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)

    await asyncio.get_running_loop().run_in_executor(None, _write)


async def async_append_tx(hass: HomeAssistant, *, record: dict[str, Any]) -> None:
    store = Store(hass, _TX_STORE_VERSION, _TX_STORE_KEY)
    existing = await store.async_load() or {}
    items = existing.get("items")
    if not isinstance(items, list):
        items = []

    items.append(record)
    # Bounded: keep last 200 transactions.
    if len(items) > 200:
        items = items[-200:]

    await store.async_save({"items": items})


def async_build_plan_from_issue_data(
    *,
    entry_id: str,
    candidate_id: str,
    issue_id: str,
    data: dict[str, Any],
) -> BlueprintApplyPlan:
    blueprint_path = str(data.get("blueprint_id") or data.get("blueprint_path") or "")
    blueprint_inputs = data.get("blueprint_inputs")
    if not isinstance(blueprint_inputs, dict):
        blueprint_inputs = {}

    risk = str(data.get("risk") or "medium")

    if not blueprint_path:
        # Default to our shipped blueprint.
        blueprint_path = "ai_home_copilot/a_to_b_safe.yaml"

    return BlueprintApplyPlan(
        entry_id=entry_id,
        candidate_id=candidate_id,
        issue_id=issue_id,
        blueprint_path=blueprint_path,
        blueprint_inputs=blueprint_inputs,
        risk=risk,
    )


async def async_apply_plan(hass: HomeAssistant, plan: BlueprintApplyPlan) -> dict[str, Any]:
    """Apply a blueprint plan.

    Governance-first: caller must ensure explicit user confirmation.

    Best-effort reversible: we write a small transaction log with steps.
    """

    # Ensure shipped blueprint exists in user's blueprint directory.
    await async_install_blueprints(hass)

    # Ensure the referenced blueprint file exists. (We only support local blueprint paths.)
    blueprint_rel = Path("blueprints") / "automation" / plan.blueprint_path
    blueprint_dst = Path(hass.config.path(str(blueprint_rel)))

    if not blueprint_dst.exists():
        raise FileNotFoundError(f"Blueprint not installed: {blueprint_dst}")

    before = await _async_read_bytes(blueprint_dst)
    before_sha = _sha256_bytes(before)

    # v0.1: we do not modify the blueprint file. We only log its hash.

    # Create automation via HA storage collection (best-effort; API may vary across HA versions).
    automation_item = {
        "alias": plan.automation_name,
        "description": "Created by AI Home CoPilot via Repairs (governance-first)",
        "use_blueprint": {
            "path": plan.blueprint_path,
            "input": plan.blueprint_inputs,
        },
        "mode": "single",
    }

    automation_id = None
    created_ok = False
    error: str | None = None

    try:
        from homeassistant.components.automation import storage as automation_storage  # type: ignore

        get_coll = getattr(automation_storage, "async_get_storage_collection", None)
        if get_coll is None:
            raise RuntimeError("automation storage collection not available")

        coll = await get_coll(hass)

        # Try common method names.
        if hasattr(coll, "async_create_item"):
            res = await coll.async_create_item(automation_item)
        elif hasattr(coll, "async_create"):
            res = await coll.async_create(automation_item)
        else:
            raise RuntimeError("automation collection create method not found")

        if isinstance(res, dict):
            automation_id = res.get("id") or res.get("item_id")
        else:
            automation_id = getattr(res, "id", None) or getattr(res, "item_id", None)

        created_ok = True

        # Best-effort reload.
        await hass.services.async_call("automation", "reload", {}, blocking=False)
    except Exception as err:  # noqa: BLE001
        error = str(err)
        created_ok = False

    from datetime import datetime, timezone

    record = {
        "time": datetime.now(timezone.utc).isoformat(),
        "module": "repairs_blueprints",
        "entry_id": plan.entry_id,
        "candidate_id": plan.candidate_id,
        "risk": plan.risk,
        "actions": [
            {
                "kind": "blueprint_ref",
                "path": str(blueprint_rel),
                "sha256": before_sha,
            },
            {
                "kind": "create_automation",
                "ok": created_ok,
                "automation_id": automation_id,
                "use_blueprint": {"path": plan.blueprint_path},
            },
            {
                "kind": "automation_reload",
                "ok": True,
            },
        ],
        "result": {"ok": created_ok, "automation_id": automation_id, "error": error},
        "rollback": {
            "note": "v0.1: rollback is best-effort; disable the created automation in UI if needed",
            "automation_id": automation_id,
        },
    }

    await async_append_tx(hass, record=record)

    if not created_ok:
        raise RuntimeError(f"Failed to create automation: {error}")

    return {"ok": True, "automation_id": automation_id, "blueprint_sha256": before_sha}
