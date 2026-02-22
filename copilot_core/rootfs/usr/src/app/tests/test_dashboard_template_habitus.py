"""Regression checks for Habitus zone handling in dashboard template."""

from pathlib import Path


def _dashboard_template() -> str:
    return (Path(__file__).resolve().parents[1] / "templates" / "dashboard.html").read_text(
        encoding="utf-8"
    )


def test_habitus_template_uses_hub_zone_api_routes() -> None:
    text = _dashboard_template()
    assert "/api/v1/hub/zones" in text
    assert "/api/v1/habitus/config" not in text


def test_habitus_template_exposes_room_multiselect() -> None:
    text = _dashboard_template()
    assert 'id="new-zone-rooms"' in text
    assert "Mehrfachauswahl" in text
