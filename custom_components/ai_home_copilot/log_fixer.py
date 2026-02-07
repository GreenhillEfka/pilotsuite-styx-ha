from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
import re
from collections import deque
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .log_store import (
    FixTransaction,
    Finding,
    FindingType,
    async_get_log_fixer_state,
    async_record_findings,
    async_set_last_fix_transaction,
    async_get_last_fix_transaction,
)

_LOG_PATH = "/config/home-assistant.log"
_DEFAULT_TAIL_LINES = 4000


_MANIFEST_PARSE_RE = re.compile(
    r"/config/custom_components/(?P<integration>[^/]+)/manifest\.json",
    re.IGNORECASE,
)
_SETUP_FAILED_RE = re.compile(
    r"(?:Setup failed for custom integration|Error setting up custom integration)\s+(?P<integration>[a-zA-Z0-9_]+)",
)
_STATE_ATTR_TOO_LARGE_RE = re.compile(
    r"State attributes for (?P<entity_id>[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+) exceed(?:ed)? maximum size of 16384",
    re.IGNORECASE,
)
_BLOCKING_IMPORT_MODULE_RE = re.compile(
    r"Detected blocking call to import_module",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AnalyzeResult:
    findings: list[Finding]
    scanned_lines: int


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tail_file_sync(path: str, max_lines: int) -> list[str]:
    """Read last max_lines lines from a text file without loading entire file."""
    dq: deque[str] = deque(maxlen=max_lines)
    # Best effort: log file may contain bad bytes.
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            dq.append(line.rstrip("\n"))
    return list(dq)


def _parse_findings(lines: list[str]) -> list[Finding]:
    now = _utc_now_iso()

    # aggregate by finding_id
    agg: dict[str, dict[str, Any]] = {}

    def upsert(finding: Finding, sample_line: str) -> None:
        rec = agg.get(finding.finding_id)
        if rec is None:
            agg[finding.finding_id] = {
                "finding": finding,
                "count": 1,
                "sample_lines": [sample_line],
                "first_seen": now,
                "last_seen": now,
            }
            return
        rec["count"] += 1
        rec["last_seen"] = now
        samples: list[str] = rec["sample_lines"]
        if len(samples) < 3:
            samples.append(sample_line)

    for line in lines:
        # 1) manifest parse errors (high signal only)
        if "manifest.json" in line and (
            "Error parsing" in line
            or "JSONDecodeError" in line
            or "Invalid manifest" in line
        ):
            m = _MANIFEST_PARSE_RE.search(line)
            if m:
                integration = m.group("integration")
                fid = f"manifest_parse_{integration}".replace("-", "_")
                finding = Finding(
                    finding_id=fid,
                    finding_type=FindingType.MANIFEST_PARSE_ERROR,
                    title=f"Manifest parse error: {integration}",
                    details={
                        "integration": integration,
                        "manifest_path": f"/config/custom_components/{integration}/manifest.json",
                    },
                    is_fixable=True,
                )
                upsert(finding, line)
                continue

        # 2) setup failed
        m2 = _SETUP_FAILED_RE.search(line)
        if m2:
            integration = m2.group("integration")
            fid = f"setup_failed_{integration}".replace("-", "_")
            finding = Finding(
                finding_id=fid,
                finding_type=FindingType.SETUP_FAILED,
                title=f"Setup failed: {integration}",
                details={"integration": integration},
                is_fixable=False,
            )
            upsert(finding, line)
            continue

        # 3) attributes too large
        m3 = _STATE_ATTR_TOO_LARGE_RE.search(line)
        if m3:
            entity_id = m3.group("entity_id")
            fid = f"state_attr_oversize_{entity_id}".replace("-", "_")
            finding = Finding(
                finding_id=fid,
                finding_type=FindingType.STATE_ATTR_OVERSIZE,
                title=f"State attributes too large: {entity_id}",
                details={"entity_id": entity_id},
                is_fixable=False,
            )
            upsert(finding, line)
            continue

        # 4) blocking import_module
        if _BLOCKING_IMPORT_MODULE_RE.search(line):
            fid = "blocking_import_module"
            finding = Finding(
                finding_id=fid,
                finding_type=FindingType.BLOCKING_IMPORT_MODULE,
                title="Blocking call: import_module",
                details={},
                is_fixable=False,
            )
            upsert(finding, line)
            continue

    out: list[Finding] = []
    for rec in agg.values():
        f: Finding = rec["finding"]
        out.append(
            Finding(
                finding_id=f.finding_id,
                finding_type=f.finding_type,
                title=f.title,
                details={
                    **f.details,
                    "count": rec["count"],
                    "first_seen": rec["first_seen"],
                    "last_seen": rec["last_seen"],
                    "sample_lines": rec["sample_lines"],
                },
                is_fixable=f.is_fixable,
            )
        )
    return out


async def async_analyze_logs(hass: HomeAssistant, *, tail_lines: int = _DEFAULT_TAIL_LINES) -> AnalyzeResult:
    lines: list[str] = []
    try:
        lines = await hass.async_add_executor_job(_tail_file_sync, _LOG_PATH, tail_lines)
    except FileNotFoundError:
        # On fresh installs or when path differs.
        lines = []

    findings = _parse_findings(lines)
    await async_record_findings(hass, findings)

    # Create/refresh issues.
    for finding in findings:
        _async_create_issue_for_finding(hass, finding)

    return AnalyzeResult(findings=findings, scanned_lines=len(lines))


def _issue_id(finding: Finding) -> str:
    return f"log_{finding.finding_id}".replace("-", "_")


def _async_create_issue_for_finding(hass: HomeAssistant, finding: Finding) -> None:
    translation_key = {
        FindingType.MANIFEST_PARSE_ERROR: "log_manifest_parse_error",
        FindingType.SETUP_FAILED: "log_setup_failed",
        FindingType.STATE_ATTR_OVERSIZE: "log_state_attr_oversize",
        FindingType.BLOCKING_IMPORT_MODULE: "log_blocking_import_module",
    }[finding.finding_type]

    placeholders: dict[str, str] = {}
    if finding.finding_type in (FindingType.MANIFEST_PARSE_ERROR, FindingType.SETUP_FAILED):
        integ = str(finding.details.get("integration", ""))
        placeholders["integration"] = integ
    if finding.finding_type == FindingType.STATE_ATTR_OVERSIZE:
        placeholders["entity_id"] = str(finding.details.get("entity_id", ""))

    ir.async_create_issue(
        hass,
        DOMAIN,
        _issue_id(finding),
        is_fixable=finding.is_fixable,
        is_persistent=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key=translation_key,
        translation_placeholders=placeholders,
        data={
            "finding_id": finding.finding_id,
            # Include only small metadata; no big blobs.
            "finding_type": finding.finding_type,
        },
    )


def _safe_dst_for_disable(integration: str) -> str:
    base = f"/config/custom_components/{integration}"
    return base + ".__disabled__"


def _rename_sync(src: str, dst: str) -> None:
    os.rename(src, dst)


async def async_disable_custom_integration_for_manifest_error(
    hass: HomeAssistant, *, integration: str, issue_id: str
) -> FixTransaction:
    """Disable a broken custom integration by renaming its folder.

    Safe + reversible: rename only.
    """
    src = f"/config/custom_components/{integration}"
    dst = _safe_dst_for_disable(integration)

    # Ensure we don't overwrite an existing disabled folder.
    def _check_and_rename() -> None:
        if not os.path.isdir(src):
            raise FileNotFoundError(src)
        if os.path.exists(dst):
            raise FileExistsError(dst)
        _rename_sync(src, dst)

    await hass.async_add_executor_job(_check_and_rename)

    tx = FixTransaction(
        action="disable_custom_integration",
        issue_id=issue_id,
        when=_utc_now_iso(),
        data={"integration": integration, "src": src, "dst": dst},
    )
    await async_set_last_fix_transaction(hass, tx)
    return tx


async def async_rollback_last_fix(hass: HomeAssistant) -> FixTransaction | None:
    tx = await async_get_last_fix_transaction(hass)
    if tx is None:
        return None

    if tx.action == "disable_custom_integration":
        src = str(tx.data.get("dst", ""))
        dst = str(tx.data.get("src", ""))

        def _check_and_rename_back() -> None:
            if not src or not dst:
                raise ValueError("Missing src/dst")
            if not os.path.isdir(src):
                raise FileNotFoundError(src)
            if os.path.exists(dst):
                raise FileExistsError(dst)
            _rename_sync(src, dst)

        await hass.async_add_executor_job(_check_and_rename_back)

        rollback_tx = FixTransaction(
            action="rollback_disable_custom_integration",
            issue_id=tx.issue_id,
            when=_utc_now_iso(),
            data={"src": src, "dst": dst, "rolled_back": True},
        )
        # Clear last fix (or set to rollback tx). We'll set to rollback record.
        await async_set_last_fix_transaction(hass, rollback_tx)
        return rollback_tx

    # Unknown action: do nothing
    return None
