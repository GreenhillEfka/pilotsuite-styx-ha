from __future__ import annotations

import os
import shutil
from collections import Counter
from datetime import datetime, timezone

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant

from .systemhealth_store import async_get_state, async_set_last_generated, async_set_last_published
from .privacy import sanitize_path, sanitize_text

EXPORT_DIR = "/config/ai_home_copilot/exports"
PUBLISH_DIR = "/config/www/ai_home_copilot"


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _fmt_bytes(n: int | None) -> str:
    if n is None:
        return "(unknown)"
    if n < 0:
        return "(unknown)"
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    v = float(n)
    i = 0
    while v >= 1024 and i < len(units) - 1:
        v /= 1024
        i += 1
    if i == 0:
        return f"{int(v)} {units[i]}"
    return f"{v:.1f} {units[i]}"



def _redact_line(line: str) -> str:
    # Centralized sanitization kernel (security_privacy v0.1).
    return sanitize_text(line, max_chars=400)


def _read_tail_lines(path: str, *, max_lines: int = 500) -> list[str]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()
    return lines[-max_lines:]


def _extract_top_warnings(lines: list[str], *, limit: int = 30) -> list[str]:
    # Prefer actionable warnings around recorder/db/perf.
    keep: list[str] = []
    keywords = (
        "recorder",
        "database",
        "sqlite",
        "mariadb",
        "postgres",
        "db ",
        "db_",
        "slow",
        "locked",
        "iowait",
        "timeout",
    )
    for ln in lines:
        if "WARNING" in ln or "ERROR" in ln:
            low = ln.lower()
            if any(k in low for k in keywords):
                keep.append(_redact_line(ln.rstrip()))

    # If nothing matched, fall back to last WARNING/ERROR lines.
    if not keep:
        for ln in lines:
            if "WARNING" in ln or "ERROR" in ln:
                keep.append(_redact_line(ln.rstrip()))

    return keep[-limit:]


def _sqlite_db_path(hass: HomeAssistant) -> str:
    # Default HA path for SQLite.
    return hass.config.path("home-assistant_v2.db")


async def async_generate_systemhealth_report(hass: HomeAssistant) -> str:
    """Generate a privacy-first markdown report under /config.

    The report is local-only by default; publishing is a separate step.
    """

    os.makedirs(EXPORT_DIR, exist_ok=True)

    generated = datetime.now(timezone.utc)

    # Entities summary.
    states = hass.states.async_all()
    total_entities = len(states)
    domain_counts = Counter()
    for st in states:
        try:
            domain = st.entity_id.split(".", 1)[0]
        except Exception:  # noqa: BLE001
            continue
        domain_counts[domain] += 1

    top_domains = domain_counts.most_common(12)

    # Recorder/DB (SQLite) size.
    db_path = _sqlite_db_path(hass)
    db_size: int | None = None
    db_mtime: str | None = None
    if os.path.exists(db_path):
        try:
            st = os.stat(db_path)
            db_size = int(st.st_size)
            db_mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
        except OSError:
            db_size = None
            db_mtime = None

    # Top warnings from log tail.
    log_path = hass.config.path("home-assistant.log")
    tail = await hass.async_add_executor_job(_read_tail_lines, log_path)
    top_warn = _extract_top_warnings(tail)

    # Risk heuristics.
    db_risk = "unknown"
    if db_size is not None:
        if db_size > 10 * 1024 * 1024 * 1024:
            db_risk = "acute"
        elif db_size > 2 * 1024 * 1024 * 1024:
            db_risk = "high"
        elif db_size > 500 * 1024 * 1024:
            db_risk = "watch"
        else:
            db_risk = "ok"

    ent_risk = "ok"
    if total_entities > 4000:
        ent_risk = "high"
    elif total_entities > 2000:
        ent_risk = "watch"

    # Compose report.
    lines: list[str] = []
    lines.append("# AI Home CoPilot — SystemHealth report")
    lines.append("")
    lines.append(f"generated: {generated.isoformat()}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- entities_total: {total_entities} (risk={ent_risk})")
    if os.path.exists(db_path):
        lines.append(f"- recorder_db: sqlite ({_fmt_bytes(db_size)}) (risk={db_risk})")
        if db_mtime:
            lines.append(f"  - mtime_utc: {db_mtime}")
        lines.append(f"  - path: {sanitize_path(db_path)}")
    else:
        lines.append("- recorder_db: sqlite file not found at default path")
        lines.append(f"  - checked: {sanitize_path(db_path)}")
        lines.append("  - note: this usually means an external DB is configured, or HA is not using SQLite")
    lines.append("")

    lines.append("## Entities")
    lines.append("")
    lines.append("Top domains (count):")
    for dom, cnt in top_domains:
        lines.append(f"- {dom}: {cnt}")
    lines.append("")

    lines.append("## Top warnings (tail of home-assistant.log)")
    lines.append("")
    if top_warn:
        for ln in top_warn:
            lines.append(f"- {ln}")
    else:
        lines.append("(no WARNING/ERROR lines found in the last log tail)")
    lines.append("")

    lines.append("## Suggested next actions (no changes applied)")
    lines.append("")
    if db_risk in ("watch", "high", "acute"):
        lines.append("- Review Recorder settings (purge_keep_days / auto_purge / auto_repack) and consider excluding noisy entities.")
        lines.append("- If using SQLite and DB is large: run `recorder.purge` with `repack: true` (manual, after review).")
    if ent_risk in ("watch", "high"):
        lines.append("- Audit integrations generating many entities (templates/MQTT/diagnostic entities) and disable what you do not need.")
    if top_warn:
        lines.append("- Investigate the warnings above; repeated 'database locked' / slow recorder queries are strong signals of DB/I/O issues.")
    if db_risk == "ok" and ent_risk == "ok" and not top_warn:
        lines.append("- No obvious issues detected by v0.1 heuristics.")

    fname = f"ai_home_copilot_systemhealth_{_now_stamp()}.md"
    out_path = os.path.join(EXPORT_DIR, fname)

    def _write(path: str, text: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    await hass.async_add_executor_job(_write, out_path, "\n".join(lines) + "\n")

    await async_set_last_generated(hass, out_path)

    persistent_notification.async_create(
        hass,
        f"Generated SystemHealth report:\n{out_path}",
        title="AI Home CoPilot SystemHealth",
        notification_id="ai_home_copilot_systemhealth",
    )

    return out_path


async def async_publish_last_systemhealth_report(hass: HomeAssistant) -> str:
    state = await async_get_state(hass)
    src = state.last_generated_path
    if not src:
        raise ValueError("No report generated yet. Click 'SystemHealth report' first.")

    os.makedirs(PUBLISH_DIR, exist_ok=True)
    base = os.path.basename(src)
    dst = os.path.join(PUBLISH_DIR, base)
    await hass.async_add_executor_job(shutil.copyfile, src, dst)

    await async_set_last_published(hass, dst)

    url = f"/local/ai_home_copilot/{base}"
    persistent_notification.async_create(
        hass,
        f"Published SystemHealth report for download:\n{url}",
        title="AI Home CoPilot SystemHealth",
        notification_id="ai_home_copilot_systemhealth",
    )

    return url


async def async_generate_and_publish_systemhealth_report(hass: HomeAssistant) -> str:
    await async_generate_systemhealth_report(hass)
    return await async_publish_last_systemhealth_report(hass)
