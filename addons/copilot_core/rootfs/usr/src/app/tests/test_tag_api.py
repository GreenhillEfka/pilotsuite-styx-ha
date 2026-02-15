"""Basic integration tests for the tag-system API blueprint."""
from __future__ import annotations

import os
from pathlib import Path
import sys

try:  # pragma: no cover - dev envs without Flask should skip gracefully
    import flask  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - fallback when deps missing
    print("SKIP: Flask not installed; tag-system API tests skipped")
    raise SystemExit(0)

ASSIGNMENTS_FIXTURE = Path(__file__).with_name("test_tag_assignments_store.json")
if ASSIGNMENTS_FIXTURE.exists():
    ASSIGNMENTS_FIXTURE.unlink()
os.environ["COPILOT_TAG_ASSIGNMENTS_PATH"] = str(ASSIGNMENTS_FIXTURE)

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


def test_assignments_crud_flow():
    client = app.test_client()
    response = client.get("/api/v1/tag-system/assignments")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["assignments"] == []
    assert payload["count"] == 0

    empty_post = client.post(
        "/api/v1/tag-system/assignments",
        json={"subject_id": "light.kitchen"},
    )
    assert empty_post.status_code == 400

    create_resp = client.post(
        "/api/v1/tag-system/assignments",
        json={
            "subject_id": "light.kitchen",
            "subject_kind": "entity",
            "tag_id": "aicp.kind.light",
            "materialized": True,
            "meta": {"reason": "test"},
        },
    )
    assert create_resp.status_code == 201
    created = create_resp.get_json()
    assert created["ok"] is True
    assert created["created"] is True
    assert created["assignment"]["subject_id"] == "light.kitchen"

    list_resp = client.get("/api/v1/tag-system/assignments?subject_kind=entity")
    assert list_resp.status_code == 200
    listed = list_resp.get_json()
    assert listed["count"] == 1
    assert listed["assignments"][0]["subject_kind"] == "entity"

    # Second POST should update existing assignment instead of creating a new one
    update_resp = client.post(
        "/api/v1/tag-system/assignments",
        json={
            "subject_id": "light.kitchen",
            "subject_kind": "entity",
            "tag_id": "aicp.kind.light",
            "materialized": False,
        },
    )
    assert update_resp.status_code == 200
    updated_payload = update_resp.get_json()
    assert updated_payload["created"] is False
    assert updated_payload["assignment"]["materialized"] is False
