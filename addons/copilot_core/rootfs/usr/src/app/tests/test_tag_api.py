"""Basic integration tests for the tag-system API blueprint."""
from __future__ import annotations

from pathlib import Path
import sys

try:  # pragma: no cover - dev envs without Flask should skip gracefully
    import flask  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - fallback when deps missing
    print("SKIP: Flask not installed; tag-system API tests skipped")
    raise SystemExit(0)

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import app


def test_list_tags_endpoint():
    client = app.test_client()
    response = client.get("/api/v1/tag-system/tags?lang=en")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["count"] == len(payload["tags"])
    assert "schema_version" in payload
    light_tag = next((t for t in payload["tags"] if t["id"] == "aicp.kind.light"), None)
    assert light_tag is not None
    assert light_tag["display"]["lang"] == "en"
    assert light_tag["ha"]["materialize_as_label"] is True


def test_assignments_stub_endpoints():
    client = app.test_client()
    response = client.get("/api/v1/tag-system/assignments")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "stub"
    assert payload["assignments"] == []

    post_resp = client.post("/api/v1/tag-system/assignments", json={"subject_id": "light.kitchen"})
    assert post_resp.status_code == 501
    assert post_resp.get_json()["error"] == "not_implemented"
