"""Tests for branded + legacy habitus dashboard generation paths."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components"))

from ai_home_copilot.habitus_dashboard import (  # noqa: E402
    async_generate_habitus_zones_dashboard,
    async_publish_last_habitus_dashboard,
)
from ai_home_copilot.habitus_dashboard_store import HabitusDashboardState  # noqa: E402
from ai_home_copilot.habitus_zones_store_v2 import HabitusZoneV2  # noqa: E402


class _DummyConfig:
    def __init__(self, root: Path) -> None:
        self._root = root

    def path(self, *parts: str) -> str:
        return str(self._root.joinpath(*parts))


class _DummyHass:
    def __init__(self, root: Path) -> None:
        self.config = _DummyConfig(root)
        self.data: dict[str, object] = {}
        self.states = SimpleNamespace(get=lambda _entity_id: None)

    async def async_add_executor_job(self, fn, *args):  # noqa: ANN001
        return fn(*args)


@pytest.mark.asyncio
async def test_generate_habitus_dashboard_writes_primary_and_legacy_mirror(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hass = _DummyHass(tmp_path)
    state = HabitusDashboardState()

    async def _fake_get_zones(_hass, _entry_id):
        return [
            HabitusZoneV2(
                zone_id="zone:living room",
                name="Wohnzimmer: EG",
                entity_ids=("binary_sensor.motion_wohnzimmer", "light.retrolampe"),
                entities={"lights": ("light.retrolampe",)},
            )
        ]

    async def _fake_get_state(_hass):
        return state

    async def _fake_set_state(_hass, new_state):
        nonlocal state
        state = new_state

    monkeypatch.setattr("ai_home_copilot.habitus_dashboard.async_get_zones_v2", _fake_get_zones)
    monkeypatch.setattr("ai_home_copilot.habitus_dashboard.async_get_state", _fake_get_state)
    monkeypatch.setattr("ai_home_copilot.habitus_dashboard.async_set_state", _fake_set_state)
    monkeypatch.setattr(
        "ai_home_copilot.habitus_dashboard.persistent_notification.async_create",
        lambda *_args, **_kwargs: None,
    )

    out_path = await async_generate_habitus_zones_dashboard(hass, "entry-1", notify=False)

    primary_latest = tmp_path / "pilotsuite-styx" / "habitus_zones_dashboard_latest.yaml"
    legacy_latest = tmp_path / "ai_home_copilot" / "habitus_zones_dashboard_latest.yaml"

    assert "pilotsuite-styx" in str(out_path)
    assert primary_latest.exists()
    assert legacy_latest.exists()

    content = primary_latest.read_text(encoding="utf-8")
    assert 'title: "Wohnzimmer: EG"' in content
    assert 'path: "hz-zone-living-room"' in content


@pytest.mark.asyncio
async def test_publish_habitus_dashboard_writes_www_primary_and_legacy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hass = _DummyHass(tmp_path)
    state = HabitusDashboardState(
        last_path=str(tmp_path / "pilotsuite-styx" / "habitus_zones_dashboard_20260222_120000.yaml")
    )

    async def _fake_get_state(_hass):
        return state

    async def _fake_set_state(_hass, new_state):
        nonlocal state
        state = new_state

    monkeypatch.setattr("ai_home_copilot.habitus_dashboard.async_get_state", _fake_get_state)
    monkeypatch.setattr("ai_home_copilot.habitus_dashboard.async_set_state", _fake_set_state)
    monkeypatch.setattr(
        "ai_home_copilot.habitus_dashboard.persistent_notification.async_create",
        lambda *_args, **_kwargs: None,
    )

    src = tmp_path / "pilotsuite-styx" / "habitus_zones_dashboard_latest.yaml"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("title: Habitus-Zonen\nviews: []\n", encoding="utf-8")

    url = await async_publish_last_habitus_dashboard(hass)

    primary_www = tmp_path / "www" / "pilotsuite-styx" / "habitus_zones_dashboard_latest.yaml"
    legacy_www = tmp_path / "www" / "ai_home_copilot" / "habitus_zones_dashboard_latest.yaml"

    assert url == "/local/pilotsuite-styx/habitus_zones_dashboard_latest.yaml"
    assert primary_www.exists()
    assert legacy_www.exists()
