"""Integration tests for the forward/back communication pipeline.

These tests validate the critical roundtrip path:
HA event -> N3 envelope -> Core candidate payload -> decision sync back to Core.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.ai_home_copilot.const import DOMAIN
from custom_components.ai_home_copilot.core.modules.candidate_poller import _build_suggest_candidate
from custom_components.ai_home_copilot.forwarder_n3 import N3EventForwarder
from custom_components.ai_home_copilot.repairs import async_sync_decision_to_core


pytestmark = pytest.mark.integration


def _mk_state(*, state: str, attrs: dict, context: object | None = None):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        state=state,
        attributes=attrs,
        last_changed=now,
        last_updated=now,
        context=context,
    )


def _mk_context(*, ctx_id: str, user_id: str | None = None, parent_id: str | None = None):
    return SimpleNamespace(id=ctx_id, user_id=user_id, parent_id=parent_id)


@pytest.mark.asyncio
async def test_pipeline_roundtrip_forward_to_decision_sync(mock_hass):
    """Validate the critical forward/back communication pipeline behavior."""
    entry_id = "entry-1"

    # 1) Forward path: HA state change -> N3 privacy-safe envelope.
    forwarder = N3EventForwarder(mock_hass, {"core_url": "http://localhost:8909", "api_token": "token"})
    event_ctx = _mk_context(ctx_id="1234567890abcdef", user_id="user-1")
    event = SimpleNamespace(context=event_ctx)

    old_state = _mk_state(
        state="off",
        attrs={"brightness": 0, "friendly_name": "Kitchen Light", "access_token": "secret"},
    )
    new_state = _mk_state(
        state="on",
        attrs={"brightness": 180, "friendly_name": "Kitchen Light", "password": "hidden"},
        context=event_ctx,
    )

    envelope = forwarder._create_state_change_envelope(
        "light.kitchen",
        "light",
        old_state,
        new_state,
        event,
    )

    assert envelope["kind"] == "state_changed"
    assert envelope["entity_id"] == "light.kitchen"
    assert envelope["trigger"] == "user"
    assert envelope["context_id"] == "1234567890ab"  # truncated for privacy
    assert envelope["new"]["attrs"]["brightness"] == 180
    assert "friendly_name" not in envelope["new"]["attrs"]
    assert "password" not in envelope["new"]["attrs"]
    assert "access_token" not in envelope["old"]["attrs"]

    # 2) Candidate transport path: Core candidate -> HA Repairs candidate payload.
    raw_candidate = {
        "candidate_id": "cand-42",
        "pattern_id": "pattern-42",
        "metadata": {
            "trigger_entity": "binary_sensor.kitchen_motion",
            "target_entity": "light.kitchen",
            "blueprint_id": "ai_home_copilot/a_to_b_safe.yaml",
        },
        "evidence": {"support": 0.8, "confidence": 0.92, "lift": 2.7},
    }
    suggest_candidate = _build_suggest_candidate(raw_candidate)

    assert suggest_candidate is not None
    assert suggest_candidate.candidate_id == "core_cand-42"
    assert suggest_candidate.data["core_candidate_id"] == "cand-42"
    assert suggest_candidate.data["blueprint_inputs"]["a_entity"] == "binary_sensor.kitchen_motion"
    assert suggest_candidate.data["blueprint_inputs"]["b_target"]["entity_id"] == "light.kitchen"

    # 3) Back path: user decision in HA -> Core state sync.
    mock_hass.data = {
        DOMAIN: {
            entry_id: {"coordinator": SimpleNamespace(api=AsyncMock())},
        }
    }

    api = AsyncMock()
    with patch("custom_components.ai_home_copilot.repairs._get_core_api", return_value=api):
        await async_sync_decision_to_core(mock_hass, entry_id, "core_cand-42", "accepted")
        api.async_put.assert_awaited_once_with(
            "/api/v1/candidates/cand-42",
            {"state": "accepted"},
        )

        api.reset_mock()
        await async_sync_decision_to_core(
            mock_hass,
            entry_id,
            "core_cand-42",
            "deferred",
            retry_after_days=7,
        )
        api.async_put.assert_awaited_once_with(
            "/api/v1/candidates/cand-42",
            {"state": "deferred", "retry_after_days": 7},
        )
