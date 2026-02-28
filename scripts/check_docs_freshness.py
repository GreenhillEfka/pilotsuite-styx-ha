#!/usr/bin/env python3
"""Docs freshness gate for PilotSuite dual-repo releases.

Checks:
1. Runtime version files are internally synchronized.
2. Key governance docs reference the current runtime version as baseline.
3. CHANGELOG / RELEASE_NOTES contain an entry for the current version.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _fail(errors: list[str], message: str) -> None:
    errors.append(message)


def _match_one(text: str, pattern: str) -> str | None:
    m = re.search(pattern, text, flags=re.MULTILINE)
    return m.group(1) if m else None


def _check_contains_version(
    errors: list[str], path: Path, version: str, hint: str | None = None
) -> None:
    text = _read(path)
    if version not in text:
        msg = f"{path}: missing version '{version}'"
        if hint:
            msg += f" ({hint})"
        _fail(errors, msg)


def _check_ha(root: Path, errors: list[str]) -> None:
    root_manifest = root / "manifest.json"
    integration_manifest = root / "custom_components" / "ai_home_copilot" / "manifest.json"

    root_ver = json.loads(_read(root_manifest)).get("version", "").strip()
    int_ver = json.loads(_read(integration_manifest)).get("version", "").strip()
    if not root_ver or not int_ver:
        _fail(errors, "HA manifest version missing")
        return
    if root_ver != int_ver:
        _fail(
            errors,
            f"HA version mismatch: manifest.json={root_ver} vs custom_components manifest={int_ver}",
        )
    version = int_ver

    index_text = _read(root / "INDEX.md")
    idx_baseline = _match_one(index_text, r"^-\s*Version:\s*`([^`]+)`")
    idx_release = _match_one(index_text, r"^Current release:\s*v([0-9]+\.[0-9]+\.[0-9]+)")
    if idx_baseline != version:
        _fail(errors, f"INDEX.md baseline version is '{idx_baseline}', expected '{version}'")
    if idx_release != version:
        _fail(errors, f"INDEX.md current release is '{idx_release}', expected '{version}'")

    project_status = _read(root / "PROJECT_STATUS.md")
    ps_ha = _match_one(project_status, r"-\s*HA integration:\s*`([^`]+)`")
    ps_core = _match_one(project_status, r"-\s*Core add-on:\s*`([^`]+)`")
    if ps_ha != version:
        _fail(errors, f"PROJECT_STATUS.md HA baseline is '{ps_ha}', expected '{version}'")
    if ps_core != version:
        _fail(errors, f"PROJECT_STATUS.md Core baseline is '{ps_core}', expected '{version}'")

    vision = _read(root / "VISION.md")
    v_ha = _match_one(vision, r"-\s*HA integration:\s*`([^`]+)`")
    v_core = _match_one(vision, r"-\s*Core add-on:\s*`([^`]+)`")
    if v_ha != version:
        _fail(errors, f"VISION.md HA baseline is '{v_ha}', expected '{version}'")
    if v_core != version:
        _fail(errors, f"VISION.md Core baseline is '{v_core}', expected '{version}'")

    plan = _read(root / "PROJEKTPLAN.md")
    if f"HA v{version}" not in plan or f"Core v{version}" not in plan:
        _fail(errors, f"PROJEKTPLAN.md baseline must include 'HA v{version}' and 'Core v{version}'")

    _check_contains_version(errors, root / "CHANGELOG.md", f"v{version}", hint="release entry")
    _check_contains_version(errors, root / "RELEASE_NOTES.md", f"v{version}", hint="release entry")


def _check_core(root: Path, errors: list[str]) -> None:
    config_yaml = _read(root / "copilot_core" / "config.yaml")
    manifest_json = json.loads(_read(root / "copilot_core" / "manifest.json"))
    version_file = _read(
        root / "copilot_core" / "rootfs" / "usr" / "src" / "app" / "VERSION"
    ).strip()

    config_ver = _match_one(config_yaml, r'^version:\s*"?(.*?)"?$')
    manifest_ver = manifest_json.get("domotz", {}).get("version", "").strip()
    if not config_ver or not manifest_ver or not version_file:
        _fail(errors, "Core version missing in one of config.yaml / manifest.json / VERSION")
        return

    versions = {config_ver.strip(), manifest_ver, version_file}
    if len(versions) != 1:
        _fail(
            errors,
            "Core version mismatch: "
            f"config.yaml={config_ver}, manifest.json={manifest_ver}, VERSION={version_file}",
        )
    version = version_file

    index_text = _read(root / "INDEX.md")
    idx_baseline = _match_one(index_text, r"^-\s*Version:\s*`([^`]+)`")
    idx_release = _match_one(index_text, r"^Current release:\s*v([0-9]+\.[0-9]+\.[0-9]+)")
    if idx_baseline != version:
        _fail(errors, f"INDEX.md baseline version is '{idx_baseline}', expected '{version}'")
    if idx_release != version:
        _fail(errors, f"INDEX.md current release is '{idx_release}', expected '{version}'")

    project_status = _read(root / "PROJECT_STATUS.md")
    ps_ha = _match_one(project_status, r"-\s*HA integration:\s*`([^`]+)`")
    ps_core = _match_one(project_status, r"-\s*Core add-on:\s*`([^`]+)`")
    if ps_ha != version:
        _fail(errors, f"PROJECT_STATUS.md HA baseline is '{ps_ha}', expected '{version}'")
    if ps_core != version:
        _fail(errors, f"PROJECT_STATUS.md Core baseline is '{ps_core}', expected '{version}'")

    vision = _read(root / "VISION.md")
    v_ha = _match_one(vision, r"-\s*HA integration:\s*`([^`]+)`")
    v_core = _match_one(vision, r"-\s*Core add-on:\s*`([^`]+)`")
    if v_ha != version:
        _fail(errors, f"VISION.md HA baseline is '{v_ha}', expected '{version}'")
    if v_core != version:
        _fail(errors, f"VISION.md Core baseline is '{v_core}', expected '{version}'")

    plan = _read(root / "PROJEKTPLAN.md")
    if f"HA v{version}" not in plan or f"Core v{version}" not in plan:
        _fail(errors, f"PROJEKTPLAN.md baseline must include 'HA v{version}' and 'Core v{version}'")

    _check_contains_version(errors, root / "CHANGELOG.md", f"[{version}]", hint="release entry")
    _check_contains_version(errors, root / "RELEASE_NOTES.md", f"[{version}]", hint="release entry")
    _check_contains_version(errors, root / "docs" / "ROADMAP.md", version, hint="current roadmap baseline")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors: list[str] = []

    is_ha = (root / "custom_components" / "ai_home_copilot" / "manifest.json").exists()
    is_core = (root / "copilot_core" / "config.yaml").exists()

    if is_ha:
        _check_ha(root, errors)
    elif is_core:
        _check_core(root, errors)
    else:
        print("Unknown repo layout for docs freshness checker", file=sys.stderr)
        return 2

    if errors:
        print("Docs freshness check failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    print("Docs freshness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
