from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

# Spec intent (v0.1): small, bounded storage under these keys.
_TX_STORE_KEY = "openclaw_update_transactions"
_TX_STORE_VERSION = 1

_REPORT_STORE_KEY = "openclaw_update_rollback_last_report"
_REPORT_STORE_VERSION = 1


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _store(hass: HomeAssistant, *, key: str, version: int) -> Store:
    cache = hass.data.setdefault("openclaw", {}).setdefault("update_rollback", {}).setdefault("stores", {})
    st = cache.get(key)
    if isinstance(st, Store):
        return st
    st = Store(hass, version=version, key=key)
    cache[key] = st
    return st


async def _tx_append(hass: HomeAssistant, rec: dict[str, Any]) -> None:
    data = await _store(hass, key=_TX_STORE_KEY, version=_TX_STORE_VERSION).async_load() or {}
    items = data.get("items")
    if not isinstance(items, list):
        items = []
    items.append(rec)
    if len(items) > 200:
        items = items[-200:]
    data["items"] = items
    data["updated_at"] = _now_iso()
    await _store(hass, key=_TX_STORE_KEY, version=_TX_STORE_VERSION).async_save(data)


@dataclass(frozen=True, slots=True)
class UpdateTarget:
    entity_id: str
    name: str
    installed_version: str | None
    latest_version: str | None
    release_url: str | None
    release_summary: str | None
    provider: str
    update_available: bool


def _as_str(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        return s if s else None
    return str(v)


def _provider_from_entity_id(entity_id: str) -> str:
    if entity_id.startswith("update.hacs_"):
        return "hacs"
    if entity_id.startswith("update."):
        return "ha"
    return "unknown"


async def async_collect_update_inventory(hass: HomeAssistant) -> list[UpdateTarget]:
    out: list[UpdateTarget] = []

    for st in hass.states.async_all("update"):
        try:
            entity_id = st.entity_id
            attrs = st.attributes or {}

            installed = _as_str(attrs.get("installed_version"))
            latest = _as_str(attrs.get("latest_version"))

            update_available = bool(
                installed
                and latest
                and installed != latest
                and st.state not in ("unavailable", "unknown")
            )

            out.append(
                UpdateTarget(
                    entity_id=entity_id,
                    name=_as_str(attrs.get("friendly_name")) or entity_id,
                    installed_version=installed,
                    latest_version=latest,
                    release_url=_as_str(attrs.get("release_url")),
                    release_summary=_as_str(attrs.get("release_summary")),
                    provider=_provider_from_entity_id(entity_id),
                    update_available=update_available,
                )
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("update_rollback: failed to parse %s: %s", getattr(st, "entity_id", "?"), err)

    out.sort(key=lambda t: (not t.update_available, (t.name or ""), t.entity_id))
    return out


def _fmt_target(t: UpdateTarget) -> str:
    iv = t.installed_version or "?"
    lv = t.latest_version or "?"
    line = f"- {t.name}: {iv} → {lv} ({t.entity_id})"

    meta: list[str] = [f"provider={t.provider}"]
    if t.release_url:
        meta.append(f"release={t.release_url}")
    if t.release_summary:
        meta.append(f"summary={t.release_summary}")

    if meta:
        line += "\n" + "  " + "\n  ".join(meta)
    return line


async def async_generate_update_rollback_report(hass: HomeAssistant) -> str:
    inv = await async_collect_update_inventory(hass)
    pending = [t for t in inv if t.update_available]

    lines: list[str] = []
    lines.append("Update & Rollback (v0.1) — Report")
    lines.append(f"generated_at: {_now_iso()}")
    lines.append("")
    lines.append(f"update_entities_total: {len(inv)}")
    lines.append(f"updates_available: {len(pending)}")
    lines.append("")

    if pending:
        lines.append("Pending updates:")
        lines.extend([_fmt_target(t) for t in pending[:50]])
        if len(pending) > 50:
            lines.append(f"- ...(truncated)... showing 50 of {len(pending)}")
        lines.append("")
    else:
        lines.append("Pending updates: none")
        lines.append("")

    lines.append("Next actions (governance-first):")
    lines.append("1) Create a Safety Point (Backup) BEFORE installing anything (manual button).")
    lines.append("2) Review release URLs + breaking changes.")
    lines.append("3) Install via HA UI / HACS UI (v0.1 does not auto-install).")
    lines.append("4) Restart gate: restart only if needed and only when you confirm it.")

    report = "\n".join(lines).strip() + "\n"

    # Persist last report (bounded)
    try:
        await _store(hass, key=_REPORT_STORE_KEY, version=_REPORT_STORE_VERSION).async_save(
            {"generated_at": _now_iso(), "report": report}
        )
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("update_rollback: failed to save last report: %s", err)

    # Append tx record (append-only, bounded)
    try:
        await _tx_append(
            hass,
            {
                "tx_id": f"{_now_iso()}_report",
                "timestamp": _now_iso(),
                "kind": "report",
                "updates_available": len(pending),
                "targets": [t.entity_id for t in pending],
            },
        )
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("update_rollback: failed to append tx: %s", err)

    return report


async def async_show_update_rollback_report(hass: HomeAssistant) -> None:
    report = await async_generate_update_rollback_report(hass)

    msg = report if len(report) <= 9000 else report[:8950] + "\n...(truncated)...\n"
    persistent_notification.async_create(
        hass,
        msg,
        title="AI Home CoPilot — Update/Rollback report",
        notification_id="ai_home_copilot_update_rollback_report",
    )
