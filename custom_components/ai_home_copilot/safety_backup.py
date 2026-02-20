from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_STORAGE_VERSION = 1
_STORAGE_KEY = f"{DOMAIN}.safety_backup"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _store(hass: HomeAssistant) -> Store:
    global_data = hass.data.setdefault(DOMAIN, {}).setdefault("_global", {})
    st = global_data.get("safety_backup_store")
    if st is None:
        st = Store(hass, _STORAGE_VERSION, _STORAGE_KEY)
        global_data["safety_backup_store"] = st
    return st


async def _load(hass: HomeAssistant) -> dict[str, Any]:
    return await _store(hass).async_load() or {}


async def _save(hass: HomeAssistant, data: dict[str, Any]) -> None:
    await _store(hass).async_save(data)


@dataclass(frozen=True)
class SafetyBackupResult:
    service: str
    started_at: str


async def async_create_safety_backup(hass: HomeAssistant) -> SafetyBackupResult:
    """Create a 'safety point' backup.

    Privacy/governance-first:
    - We do not auto-run this. It is triggered only via a button.
    - We call the most appropriate HA backup service if available.

    Notes:
    - On HA OS / supervised, `backup.create_automatic` is the preferred action.
    - On core/container, `backup.create` may be available.
    """

    # Prefer automatic backup action (available on all install types).
    if hass.services.has_service("backup", "create_automatic"):
        await hass.services.async_call("backup", "create_automatic", {}, blocking=True)
        service = "backup.create_automatic"
    elif hass.services.has_service("backup", "create"):
        await hass.services.async_call("backup", "create", {}, blocking=True)
        service = "backup.create"
    # Legacy supervisor services (best effort)
    elif hass.services.has_service("hassio", "snapshot_full"):
        await hass.services.async_call("hassio", "snapshot_full", {}, blocking=True)
        service = "hassio.snapshot_full"
    else:
        raise RuntimeError(
            "Kein Backup-Service gefunden. Erwartet: backup.create_automatic oder backup.create."
        )

    started_at = _now_iso()

    st = await _load(hass)
    st["last_started_at"] = started_at
    st["last_service"] = service
    await _save(hass, st)

    persistent_notification.async_create(
        hass,
        (
            "Safety-Backup wurde gestartet.\n\n"
            f"Service: {service}\n"
            f"Zeit: {started_at}\n\n"
            "Hinweis: Den Fortschritt siehst du unter Einstellungen → System → Backups.\n"
            "(Dieses Backup wird nur manuell per Button gestartet – nicht automatisch bei Updates.)"
        ),
        title="PilotSuite Safety Backup",
        notification_id="ai_home_copilot_safety_backup",
    )

    return SafetyBackupResult(service=service, started_at=started_at)


async def async_show_safety_backup_status(hass: HomeAssistant) -> None:
    st = await _load(hass)
    last_time = st.get("last_started_at")
    last_service = st.get("last_service")

    msg = "Safety-Backup Status\n"
    if last_time:
        msg += f"\nZuletzt gestartet: {last_time}"
    else:
        msg += "\nNoch kein Safety-Backup gestartet."

    if last_service:
        msg += f"\nService: {last_service}"

    # Also surface backup integration entities if present.
    backup_event = hass.states.get("event.backup_automatic_backup")
    if backup_event is not None:
        ev_type = backup_event.attributes.get("event_type")
        stage = backup_event.attributes.get("backup_stage")
        failed = backup_event.attributes.get("failed_reason")
        msg += "\n\nAutomatisches Backup (HA):"
        if ev_type:
            msg += f"\n- Status: {ev_type}"
        if stage:
            msg += f"\n- Stage: {stage}"
        if failed:
            msg += f"\n- Fehler: {failed}"

    persistent_notification.async_create(
        hass,
        msg,
        title="PilotSuite Safety Backup",
        notification_id="ai_home_copilot_safety_backup",
    )
