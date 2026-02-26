"""Core/HA compatibility helpers.

This module implements a small, HA-docs friendly guardrail:
- Compare Core add-on version and HA integration version (major/minor).
- Surface mismatch via Home Assistant Repairs (issue_registry).

We keep this conservative: unknown/invalid versions do not create noise.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ISSUE_CORE_VERSION_MISMATCH = "core_version_mismatch"

_SEMVER_RE = re.compile(r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)")


def parse_semver(value: str | None) -> tuple[int, int, int] | None:
    """Parse a semver-ish string into (major, minor, patch).

    Accepts:
    - "10.1.2"
    - "v10.1.2"
    - "10.1.2-dev"
    - "10.1.2+build"
    """
    raw = str(value or "").strip()
    if not raw:
        return None

    m = _SEMVER_RE.search(raw)
    if not m:
        return None
    try:
        return (
            int(m.group("major")),
            int(m.group("minor")),
            int(m.group("patch")),
        )
    except Exception:  # noqa: BLE001
        return None


def major_minor(version: tuple[int, int, int] | None) -> tuple[int, int] | None:
    if not version:
        return None
    return version[0], version[1]


def is_major_minor_mismatch(core_version: str | None, integration_version: str | None) -> bool:
    """Return True if both versions parse and major/minor differ."""
    core = major_minor(parse_semver(core_version))
    integ = major_minor(parse_semver(integration_version))
    if not core or not integ:
        return False
    return core != integ


def async_update_core_version_mismatch_issue(
    hass: HomeAssistant,
    *,
    core_version: str | None,
    integration_version: str | None,
    host: str,
    port: int,
    extra: dict[str, Any] | None = None,
) -> None:
    """Create or delete the version mismatch Repairs issue."""
    if is_major_minor_mismatch(core_version, integration_version):
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_CORE_VERSION_MISMATCH,
            data={
                "core_version": str(core_version or "unknown"),
                "integration_version": str(integration_version or "unknown"),
                "host": host,
                "port": int(port),
                **(extra or {}),
            },
            translation_key=ISSUE_CORE_VERSION_MISMATCH,
            translation_placeholders={
                "core_version": str(core_version or "unknown"),
                "integration_version": str(integration_version or "unknown"),
                "host": host,
                "port": str(int(port)),
            },
            severity=ir.IssueSeverity.WARNING,
            is_fixable=False,
        )
        return

    # Best-effort cleanup once versions match (or are unknown).
    try:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_CORE_VERSION_MISMATCH)
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Could not delete issue %s (best-effort)", ISSUE_CORE_VERSION_MISMATCH)
