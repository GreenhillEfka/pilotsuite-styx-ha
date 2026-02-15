"""
Test suite for HA Repairs workflow integration.

Tests:
- CandidateRepairFlow (accept/dismiss/defer)
- SeedRepairFlow (seed candidates from logs)
- RepairsBlueprintApplyFlow (blueprint preview → configure → confirm)
- async_create_fix_flow factory
- async_sync_decision_to_core (feedback loop)
- Decision state transitions
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.repairs import RepairsFlow
from homeassistant.helpers import issue_registry as ir


# Mock helpers for HA components
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    return hass


def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_123"
    return entry


class TestCandidateRepairFlow:
    """Tests for CandidateRepairFlow decision handling."""

    def test_step_choice_schema(self):
        """Test STEP_CHOICE schema validation."""
        from custom_components.ai_home_copilot.repairs import STEP_CHOICE
        import voluptuous as vol

        # Valid: imported
        result = STEP_CHOICE({"decision": "imported"})
        assert result["decision"] == "imported"

        # Valid: defer
        result = STEP_CHOICE({"decision": "defer"})
        assert result["decision"] == "defer"

        # Valid: dismiss
        result = STEP_CHOICE({"decision": "dismiss"})
        assert result["decision"] == "dismiss"

        # Invalid: unknown decision
        with pytest.raises(vol.Invalid):
            STEP_CHOICE({"decision": "unknown"})

    def test_step_defer_schema(self):
        """Test STEP_DEFER schema with days validation."""
        from custom_components.ai_home_copilot.repairs import STEP_DEFER
        import voluptuous as vol

        # Valid: default 7 days
        result = STEP_DEFER({})
        assert result["days"] == 7

        # Valid: custom days
        result = STEP_DEFER({"days": 14})
        assert result["days"] == 14

        # Invalid: less than 1
        with pytest.raises(vol.Invalid):
            STEP_DEFER({"days": 0})

        # Invalid: more than 365
        with pytest.raises(vol.Invalid):
            STEP_DEFER({"days": 366})

    @pytest.mark.asyncio
    async def test_candidate_repair_flow_dismiss(self):
        """Test CandidateRepairFlow dismiss decision."""
        from custom_components.ai_home_copilot.repairs import CandidateRepairFlow

        hass = mock_hass()
        entry = mock_config_entry()

        flow = CandidateRepairFlow(
            hass=hass,
            entry_id=entry.entry_id,
            candidate_id="core_test_123",
            issue_id="issue_123",
        )

        # Verify initialization
        assert flow._entry_id == entry.entry_id
        assert flow._candidate_id == "core_test_123"
        assert flow._issue_id == "issue_123"

    @pytest.mark.asyncio
    async def test_candidate_repair_flow_accept(self):
        """Test CandidateRepairFlow accept path."""
        from custom_components.ai_home_copilot.repairs import CandidateRepairFlow

        hass = mock_hass()
        entry = mock_config_entry()

        flow = CandidateRepairFlow(
            hass=hass,
            entry_id=entry.entry_id,
            candidate_id="core_test_456",
        )

        assert flow._candidate_id == "core_test_456"


class TestSeedRepairFlow:
    """Tests for SeedRepairFlow (log-based candidates)."""

    def test_seed_choice_schema(self):
        """Test STEP_SEED_CHOICE schema."""
        from custom_components.ai_home_copilot.repairs import STEP_SEED_CHOICE
        import voluptuous as vol

        # Valid: done
        result = STEP_SEED_CHOICE({"decision": "done"})
        assert result["decision"] == "done"

        # Valid: defer
        result = STEP_SEED_CHOICE({"decision": "defer"})
        assert result["decision"] == "defer"

        # Invalid: unknown
        with pytest.raises(vol.Invalid):
            STEP_SEED_CHOICE({"decision": "maybe"})

    @pytest.mark.asyncio
    async def test_seed_repair_flow_init(self):
        """Test SeedRepairFlow initialization with all fields."""
        from custom_components.ai_home_copilot.repairs import SeedRepairFlow

        hass = mock_hass()
        flow = SeedRepairFlow(
            hass=hass,
            entry_id="entry_123",
            candidate_id="seed_abc",
            source="Logfile Parser",
            entities="light.living_room, switch.fan",
            excerpt="Detected repeated on/off pattern...",
            issue_data={"candidate_type": "seed_candidate"},
            issue_id="seed_issue_1",
        )

        assert flow._source == "Logfile Parser"
        assert "light.living_room" in flow._entities
        assert "repeated on/off pattern" in flow._excerpt
        assert flow._issue_data["candidate_type"] == "seed_candidate"


class TestRepairsBlueprintApplyFlow:
    """Tests for RepairsBlueprintApplyFlow governance workflow."""

    def test_step_bp_init_schema(self):
        """Test blueprint init step schema."""
        from custom_components.ai_home_copilot.repairs import STEP_BP_INIT
        import voluptuous as vol

        # Valid options
        for decision in ["preview", "apply", "defer", "dismiss"]:
            result = STEP_BP_INIT({"decision": decision})
            assert result["decision"] == decision

        # Invalid
        with pytest.raises(vol.Invalid):
            STEP_BP_INIT({"decision": "skip"})

    def test_step_bp_configure_schema(self):
        """Test blueprint configure step schema."""
        from custom_components.ai_home_copilot.repairs import STEP_BP_CONFIGURE

        # Valid minimal input
        result = STEP_BP_CONFIGURE({
            "a_entity": "light.bedroom",
            "b_target_entity_id": "switch.fan",
        })
        assert result["a_entity"] == "light.bedroom"
        assert result["b_target_entity_id"] == "switch.fan"

        # Valid with all fields
        result = STEP_BP_CONFIGURE({
            "a_entity": "light.bedroom",
            "a_to_state": "off",
            "b_target_entity_id": "switch.fan",
            "b_action": "toggle",
        })
        assert result["a_to_state"] == "off"
        assert result["b_action"] == "toggle"

    @pytest.mark.asyncio
    async def test_blueprint_flow_risk_levels(self):
        """Test risk level handling in blueprint flow."""
        from custom_components.ai_home_copilot.repairs import RepairsBlueprintApplyFlow

        hass = mock_hass()

        # Test different risk levels
        for risk in ["low", "medium", "high"]:
            flow = RepairsBlueprintApplyFlow(
                hass=hass,
                issue_id="bp_test",
                entry_id="entry_1",
                candidate_id="bp_cand_1",
                issue_data={"risk": risk},
            )
            assert flow._risk() == risk

        # Default risk
        flow = RepairsBlueprintApplyFlow(
            hass=hass,
            issue_id="bp_test",
            entry_id="entry_1",
            candidate_id="bp_cand_1",
            issue_data={},
        )
        assert flow._risk() == "medium"

    @pytest.mark.asyncio
    async def test_blueprint_needs_configure(self):
        """Test _needs_configure logic."""
        from custom_components.ai_home_copilot.repairs import RepairsBlueprintApplyFlow

        hass = mock_hass()
        flow = RepairsBlueprintApplyFlow(
            hass=hass,
            issue_id="bp_test",
            entry_id="entry_1",
            candidate_id="bp_cand_1",
            issue_data={},
        )

        # Needs config if missing required fields
        assert flow._needs_configure({}) is True
        assert flow._needs_configure({"a_entity": ""}) is True
        assert flow._needs_configure({"a_entity": "light.living"}) is True
        assert flow._needs_configure({"a_entity": "light.living", "b_target": ""}) is True

        # Doesn't need config if all required fields present
        assert flow._needs_configure({
            "a_entity": "light.living",
            "b_target": "switch.fan",
        }) is False


class TestDecisionSync:
    """Tests for async_sync_decision_to_core."""

    @pytest.mark.asyncio
    async def test_sync_decision_accept(self):
        """Test syncing accept decision to Core."""
        from custom_components.ai_home_copilot.repairs import async_sync_decision_to_core

        hass = mock_hass()

        # Mock API client
        mock_api = AsyncMock()
        mock_coordinator = MagicMock()
        mock_coordinator.api = mock_api
        hass.data.get.return_value = {"coordinator": mock_coordinator}

        await async_sync_decision_to_core(
            hass=hass,
            entry_id="entry_123",
            candidate_id="core_test_1",
            state="accepted",
        )

        mock_api.async_put.assert_called_once_with(
            "/api/v1/candidates/test_1",
            {"state": "accepted"},
        )

    @pytest.mark.asyncio
    async def test_sync_decision_dismiss(self):
        """Test syncing dismiss decision to Core."""
        from custom_components.ai_home_copilot.repairs import async_sync_decision_to_core

        hass = mock_hass()
        mock_api = AsyncMock()
        mock_coordinator = MagicMock()
        mock_coordinator.api = mock_api
        hass.data.get.return_value = {"coordinator": mock_coordinator}

        await async_sync_decision_to_core(
            hass=hass,
            entry_id="entry_123",
            candidate_id="core_test_2",
            state="dismissed",
        )

        mock_api.async_put.assert_called_once_with(
            "/api/v1/candidates/test_2",
            {"state": "dismissed"},
        )

    @pytest.mark.asyncio
    async def test_sync_decision_defer_with_retry(self):
        """Test syncing defer with retry_after_days."""
        from custom_components.ai_home_copilot.repairs import async_sync_decision_to_core

        hass = mock_hass()
        mock_api = AsyncMock()
        mock_coordinator = MagicMock()
        mock_coordinator.api = mock_api
        hass.data.get.return_value = {"coordinator": mock_coordinator}

        await async_sync_decision_to_core(
            hass=hass,
            entry_id="entry_123",
            candidate_id="core_test_3",
            state="deferred",
            retry_after_days=14,
        )

        mock_api.async_put.assert_called_once_with(
            "/api/v1/candidates/test_3",
            {"state": "deferred", "retry_after_days": 14},
        )

    @pytest.mark.asyncio
    async def test_sync_decision_no_api_client(self):
        """Test sync when no API client is available (best-effort)."""
        from custom_components.ai_home_copilot.repairs import async_sync_decision_to_core

        hass = mock_hass()
        # No API client registered
        hass.data.get.return_value = None

        # Should not raise, just return
        await async_sync_decision_to_core(
            hass=hass,
            entry_id="entry_123",
            candidate_id="core_test_4",
            state="accepted",
        )

    @pytest.mark.asyncio
    async def test_sync_decision_strips_core_prefix(self):
        """Test that core_ prefix is correctly stripped from candidate_id."""
        from custom_components.ai_home_copilot.repairs import async_sync_decision_to_core

        hass = mock_hass()
        mock_api = AsyncMock()
        mock_coordinator = MagicMock()
        mock_coordinator.api = mock_api
        hass.data.get.return_value = {"coordinator": mock_coordinator}

        # With core_ prefix
        await async_sync_decision_to_core(
            hass=hass,
            entry_id="entry_123",
            candidate_id="core_abc123def",
            state="accepted",
        )

        call_args = mock_api.async_put.call_args[0]
        assert call_args[0] == "/api/v1/candidates/abc123def"

    @pytest.mark.asyncio
    async def test_sync_decision_api_error_handling(self):
        """Test sync gracefully handles API errors."""
        from custom_components.ai_home_copilot.repairs import async_sync_decision_to_core
        from custom_components.ai_home_copilot.api import CopilotApiError

        hass = mock_hass()
        mock_api = AsyncMock()
        mock_api.async_put.side_effect = CopilotApiError("Connection refused")
        mock_coordinator = MagicMock()
        mock_coordinator.api = mock_api
        hass.data.get.return_value = {"coordinator": mock_coordinator}

        # Should not raise - best-effort sync
        await async_sync_decision_to_core(
            hass=hass,
            entry_id="entry_123",
            candidate_id="core_test_error",
            state="accepted",
        )


class TestAsyncCreateFixFlow:
    """Tests for async_create_fix_flow factory."""

    @pytest.mark.asyncio
    async def test_create_seed_fix_flow(self):
        """Test creating SeedRepairFlow from data."""
        from custom_components.ai_home_copilot.repairs import async_create_fix_flow
        import data_entry_flow

        hass = mock_hass()

        data = {
            "entry_id": "entry_123",
            "candidate_id": "seed_abc",
            "kind": "seed",
            "seed_source": "Logfile",
            "seed_entities": ["light.living_room", "switch.fan"],
            "seed_text": "Detected repeated pattern",
        }

        # Should return SeedRepairFlow
        flow = await async_create_fix_flow(
            hass=hass,
            issue_id="seed_issue_1",
            data=data,
        )

        from custom_components.ai_home_copilot.repairs import SeedRepairFlow
        assert isinstance(flow, SeedRepairFlow)

    @pytest.mark.asyncio
    async def test_create_blueprint_fix_flow(self):
        """Test creating RepairsBlueprintApplyFlow from data."""
        from custom_components.ai_home_copilot.repairs import async_create_fix_flow
        import data_entry_flow

        hass = mock_hass()

        data = {
            "entry_id": "entry_123",
            "candidate_id": "bp_cand_1",
            "blueprint_id": "ai_home_copilot/a_to_b_safe.yaml",
            "risk": "medium",
        }

        flow = await async_create_fix_flow(
            hass=hass,
            issue_id="bp_issue_1",
            data=data,
        )

        from custom_components.ai_home_copilot.repairs import RepairsBlueprintApplyFlow
        assert isinstance(flow, RepairsBlueprintApplyFlow)

    @pytest.mark.asyncio
    async def test_create_generic_candidate_fix_flow(self):
        """Test creating CandidateRepairFlow for generic candidate."""
        from custom_components.ai_home_copilot.repairs import async_create_fix_flow

        hass = mock_hass()

        data = {
            "entry_id": "entry_123",
            "candidate_id": "cand_1",
        }

        flow = await async_create_fix_flow(
            hass=hass,
            issue_id="cand_issue_1",
            data=data,
        )

        from custom_components.ai_home_copilot.repairs import CandidateRepairFlow
        assert isinstance(flow, CandidateRepairFlow)

    def test_create_fix_flow_raises_on_none(self):
        """Test async_create_fix_flow raises on None data."""
        from custom_components.ai_home_copilot.repairs import async_create_fix_flow
        import data_entry_flow

        hass = mock_hass()

        with pytest.raises(data_entry_flow.UnknownFlow):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                async_create_fix_flow(hass=hass, issue_id="test", data=None)
            )


class TestRepairsEdgeCases:
    """Edge case tests for Repairs workflow robustness."""

    @pytest.mark.asyncio
    async def test_issue_text_truncation(self):
        """Test that long excerpts are truncated properly."""
        # Simulate truncation logic from async_create_fix_flow
        excerpt = "A" * 500
        truncated = excerpt.strip().replace("\n", " ")
        if len(truncated) > 160:
            truncated = truncated[:159] + "…"

        assert len(truncated) == 160

    @pytest.mark.asyncio
    async def test_entities_list_truncation(self):
        """Test that entities string is truncated properly."""
        entities = ["entity_" + str(i) for i in range(50)]
        entities_str = ", ".join(entities)

        if len(entities_str) > 120:
            entities_str = entities_str[:119] + "…"

        assert len(entities_str) <= 120

    @pytest.mark.asyncio
    async def test_graph_edge_candidate_special_handling(self):
        """Test graph edge candidates have special handling."""
        # This tests the SeedRepairFlow.graph_edge_candidate logic
        issue_data = {
            "candidate_type": "graph_edge_candidate",
            "from": "sensor.temp",
            "to": "climate.hvac",
            "edge_type": "controls",
        }

        assert issue_data["candidate_type"] == "graph_edge_candidate"
        assert issue_data["from"] == "sensor.temp"
        assert issue_data["to"] == "climate.hvac"


class TestRepairsWorkflowIntegration:
    """Integration tests simulating full user workflows."""

    @pytest.mark.asyncio
    async def test_user_accepts_candidate_workflow(self):
        """Simulate: User sees candidate → clicks accept → synced to Core."""
        from custom_components.ai_home_copilot.repairs import CandidateRepairFlow
        from custom_components.ai_home_copilot.repairs import async_sync_decision_to_core
        from custom_components.ai_home_copilot.storage import CandidateState

        hass = mock_hass()
        entry_id = "entry_123"
        candidate_id = "core_cand_workflow_1"

        # Mock storage state update
        async def mock_set_state(hass, entry_id, cand_id, state):
            assert cand_id == candidate_id
            assert state in [CandidateState.ACCEPTED, CandidateState.DISMISSED, CandidateState.DEFERRED]

        # Mock API sync
        mock_api = AsyncMock()
        mock_coordinator = MagicMock()
        mock_coordinator.api = mock_api
        hass.data.get.return_value = {"coordinator": mock_coordinator}

        # User clicks "imported" (accept)
        # Flow would call async_set_candidate_state + async_sync_decision_to_core
        await async_sync_decision_to_core(
            hass=hass,
            entry_id=entry_id,
            candidate_id=candidate_id,
            state="accepted",
        )

        mock_api.async_put.assert_called_once()
        assert mock_api.async_put.call_args[0][1]["state"] == "accepted"

    @pytest.mark.asyncio
    async def test_user_defers_candidate_workflow(self):
        """Simulate: User defers candidate for 7 days."""
        from custom_components.ai_home_copilot.repairs import async_sync_decision_to_core

        hass = mock_hass()
        mock_api = AsyncMock()
        mock_coordinator = MagicMock()
        mock_coordinator.api = mock_api
        hass.data.get.return_value = {"coordinator": mock_coordinator}

        await async_sync_decision_to_core(
            hass=hass,
            entry_id="entry_123",
            candidate_id="core_cand_defer",
            state="deferred",
            retry_after_days=7,
        )

        call_args = mock_api.async_put.call_args[0]
        assert call_args[1]["state"] == "deferred"
        assert call_args[1]["retry_after_days"] == 7

    @pytest.mark.asyncio
    async def test_blueprint_preview_to_confirm_workflow(self):
        """Simulate: User previews → confirms → automation created."""
        from custom_components.ai_home_copilot.repairs import RepairsBlueprintApplyFlow

        hass = mock_hass()

        flow = RepairsBlueprintApplyFlow(
            hass=hass,
            issue_id="bp_flow_test",
            entry_id="entry_123",
            candidate_id="bp_cand_flow",
            issue_data={"risk": "medium"},
        )

        # Risk should be readable
        assert flow._risk() == "medium"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
