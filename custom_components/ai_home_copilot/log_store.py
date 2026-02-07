from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.log_fixer"


class FindingType(StrEnum):
    MANIFEST_PARSE_ERROR = "manifest_parse_error"
    SETUP_FAILED = "setup_failed"
    STATE_ATTR_OVERSIZE = "state_attr_oversize"
    BLOCKING_IMPORT_MODULE = "blocking_import_module"


@dataclass(frozen=True)
class Finding:
    finding_id: str
    finding_type: FindingType
    title: str
    details: dict[str, Any]
    is_fixable: bool = False


@dataclass(frozen=True)
class FixTransaction:
    action: str
    issue_id: str
    when: str
    data: dict[str, Any]


def _get_store(hass: HomeAssistant) -> Store:
    global_data = hass.data.setdefault(DOMAIN, {}).setdefault("_global", {})
    store = global_data.get("log_fixer_store")
    if store is None:
        store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        global_data["log_fixer_store"] = store
    return store


async def _load(hass: HomeAssistant) -> dict[str, Any]:
    store = _get_store(hass)
    data = await store.async_load() or {}
    data.setdefault("findings", {})
    # last_fix is a single record.
    return data


async def _save(hass: HomeAssistant, data: dict[str, Any]) -> None:
    store = _get_store(hass)
    await store.async_save(data)


async def async_record_findings(hass: HomeAssistant, findings: list[Finding]) -> None:
    data = await _load(hass)
    findings_dict: dict[str, Any] = data.setdefault("findings", {})

    for finding in findings:
        findings_dict[finding.finding_id] = {
            "finding_id": finding.finding_id,
            "finding_type": finding.finding_type,
            "title": finding.title,
            "details": finding.details,
            "is_fixable": finding.is_fixable,
        }

    await _save(hass, data)


async def async_get_log_fixer_state(hass: HomeAssistant) -> dict[str, Any]:
    """Return full stored data (small)."""
    return await _load(hass)


async def async_set_last_fix_transaction(hass: HomeAssistant, tx: FixTransaction) -> None:
    data = await _load(hass)
    data["last_fix"] = asdict(tx)
    await _save(hass, data)


async def async_get_last_fix_transaction(hass: HomeAssistant) -> FixTransaction | None:
    data = await _load(hass)
    rec = data.get("last_fix")
    if not isinstance(rec, dict):
        return None

    try:
        return FixTransaction(
            action=str(rec.get("action", "")),
            issue_id=str(rec.get("issue_id", "")),
            when=str(rec.get("when", "")),
            data=dict(rec.get("data") or {}),
        )
    except Exception:  # noqa: BLE001
        return None
