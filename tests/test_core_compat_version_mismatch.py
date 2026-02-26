"""Tests for Core/HA compatibility guardrails (version mismatch Repairs issue)."""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components"))

from ai_home_copilot.compat import (
    ISSUE_CORE_VERSION_MISMATCH,
    is_major_minor_mismatch,
    parse_semver,
)
import ai_home_copilot.compat as compat
from ai_home_copilot.const import DOMAIN


def test_parse_semver_accepts_v_prefix_and_suffix() -> None:
    assert parse_semver("10.1.2") == (10, 1, 2)
    assert parse_semver("v10.1.2") == (10, 1, 2)
    assert parse_semver("10.1.2-dev") == (10, 1, 2)
    assert parse_semver("10.1.2+build.7") == (10, 1, 2)
    assert parse_semver("unknown") is None


def test_is_major_minor_mismatch() -> None:
    assert is_major_minor_mismatch("10.1.2", "10.1.0") is False
    assert is_major_minor_mismatch("10.2.0", "10.1.9") is True
    assert is_major_minor_mismatch("11.0.0", "10.9.9") is True
    assert is_major_minor_mismatch("unknown", "10.1.0") is False


def test_async_update_core_version_mismatch_issue_creates_issue(monkeypatch: pytest.MonkeyPatch) -> None:
    created: dict[str, object] = {}
    deleted: list[str] = []
    mismatch_calls: list[tuple[object, object]] = []

    def _create_issue(hass, domain, issue_id, **kwargs):
        created["domain"] = domain
        created["issue_id"] = issue_id
        created["kwargs"] = kwargs

    def _delete_issue(hass, domain, issue_id):
        deleted.append(issue_id)

    monkeypatch.setattr(compat.ir, "async_create_issue", _create_issue)
    monkeypatch.setattr(compat.ir, "async_delete_issue", _delete_issue)
    def _mismatch(core_v, integ_v):
        mismatch_calls.append((core_v, integ_v))
        return True

    monkeypatch.setattr(compat, "is_major_minor_mismatch", _mismatch)
    assert compat.ir.async_create_issue is _create_issue

    hass = SimpleNamespace()
    compat.async_update_core_version_mismatch_issue(
        hass,
        core_version="10.2.0",
        integration_version="10.1.0",
        host="homeassistant.local",
        port=8909,
    )

    assert deleted == []
    assert mismatch_calls, "compat check did not run"
    assert created["domain"] == DOMAIN
    assert created["issue_id"] == ISSUE_CORE_VERSION_MISMATCH

    kwargs = created["kwargs"]
    assert kwargs["translation_key"] == ISSUE_CORE_VERSION_MISMATCH
    assert kwargs["severity"] == compat.ir.IssueSeverity.WARNING
    assert kwargs["is_fixable"] is False


def test_async_update_core_version_mismatch_issue_deletes_issue_when_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    deleted: list[str] = []
    mismatch_calls: list[tuple[object, object]] = []

    monkeypatch.setattr(compat.ir, "async_create_issue", lambda *a, **k: None)
    monkeypatch.setattr(compat.ir, "async_delete_issue", lambda _h, _d, issue_id: deleted.append(issue_id))
    def _mismatch(core_v, integ_v):
        mismatch_calls.append((core_v, integ_v))
        return False

    monkeypatch.setattr(compat, "is_major_minor_mismatch", _mismatch)

    hass = SimpleNamespace()
    compat.async_update_core_version_mismatch_issue(
        hass,
        core_version="10.1.9",
        integration_version="10.1.0",
        host="homeassistant.local",
        port=8909,
    )

    assert mismatch_calls, "compat check did not run"
    assert deleted == [ISSUE_CORE_VERSION_MISMATCH]
