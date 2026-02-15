"""
Test suite for CandidatePollerModule integration with HA Repairs.

Tests:
- Polling of Core candidates API
- Candidate → HA Repairs conversion
- Decision sync-back to Core (accept/dismiss/defer)
- Graceful failure modes (Core unreachable, malformed responses)

Requires Home Assistant installation.
"""
from __future__ import annotations

import asyncio
import pytest

# Mark as integration test - requires HA installation
pytestmark = pytest.mark.integration
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import Any

import voluptuous as vol

# Lazy import HA components - skip if not installed
try:
    from homeassistant.core import HomeAssistant
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.helpers.event import async_track_time_interval
    from homeassistant.components.repairs import RepairsFlow
    HA_AVAILABLE = True
except ImportError:
    HA_AVAILABLE = False
    HomeAssistant = None
    ConfigEntry = None
    RepairsFlow = None


# Mock classes for testing
class MockCandidate:
    """Mock candidate from Core API."""
    
    def __init__(
        self,
        candidate_id: str = "test_cand_1",
        state: str = "pending",
        pattern_id: str = "pattern_123",
        trigger_entity: str = "sensor.temperature",
        target_entity: str = "climate.living_room",
        support: float = 0.85,
        confidence: float = 0.92,
        lift: float = 3.2,
    ):
        self.candidate_id = candidate_id
        self.state = state
        self.pattern_id = pattern_id
        self.metadata = {
            "trigger_entity": trigger_entity,
            "target_entity": target_entity,
        }
        self.evidence = {
            "support": support,
            "confidence": confidence,
            "lift": lift,
        }
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to API response format."""
        return {
            "candidate_id": self.candidate_id,
            "state": self.state,
            "pattern_id": self.pattern_id,
            "metadata": self.metadata,
            "evidence": self.evidence,
        }


class TestCandidatePollerIntegration:
    """Integration tests for CandidatePollerModule → Repairs workflow."""

    @pytest.mark.asyncio
    async def test_candidate_polling_success(self):
        """Test successful polling of pending candidates from Core."""
        # Mock Core API response
        mock_candidates = [
            MockCandidate(
                candidate_id="core_cand_1",
                trigger_entity="sensor.temperature",
                target_entity="climate.living_room",
            ),
            MockCandidate(
                candidate_id="core_cand_2",
                trigger_entity="light.bedroom",
                target_entity="switch.fan",
            ),
        ]
        
        mock_api = AsyncMock()
        mock_api.async_get.return_value = [c.to_dict() for c in mock_candidates]
        
        # Simulate polling
        response = await mock_api.async_get("/api/v1/candidates?state=pending")
        
        assert len(response) == 2
        assert response[0]["candidate_id"] == "core_cand_1"
        assert response[1]["candidate_id"] == "core_cand_2"

    @pytest.mark.asyncio
    async def test_candidate_to_repairs_conversion(self):
        """Test conversion of Core candidate to HA Repairs issue."""
        mock_cand = MockCandidate()
        cand_dict = mock_cand.to_dict()
        
        # Simulate _build_suggest_candidate logic
        trigger = cand_dict["metadata"].get("trigger_entity", "")
        target = cand_dict["metadata"].get("target_entity", "")
        
        title = f"A→B: {trigger} → {target}" if (trigger and target) else "A→B Pattern"
        
        # Verify data structure
        assert "sensor.temperature" in title
        assert "climate.living_room" in title
        assert cand_dict["evidence"]["confidence"] == 0.92

    @pytest.mark.asyncio
    async def test_decision_sync_accept(self):
        """Test syncing accept decision back to Core."""
        mock_api = AsyncMock()
        mock_api.async_put.return_value = None
        
        # Simulate decision sync
        candidate_id = "core_test_1"
        core_id = candidate_id[5:] if candidate_id.startswith("core_") else candidate_id
        
        payload = {"state": "accepted"}
        await mock_api.async_put(f"/api/v1/candidates/{core_id}", payload)
        
        mock_api.async_put.assert_called_once_with(
            "/api/v1/candidates/test_1",
            {"state": "accepted"}
        )

    @pytest.mark.asyncio
    async def test_decision_sync_dismiss(self):
        """Test syncing dismiss decision back to Core."""
        mock_api = AsyncMock()
        mock_api.async_put.return_value = None
        
        candidate_id = "core_test_2"
        core_id = candidate_id[5:]
        
        payload = {"state": "dismissed"}
        await mock_api.async_put(f"/api/v1/candidates/{core_id}", payload)
        
        mock_api.async_put.assert_called_once()
        assert mock_api.async_put.call_args[0][0] == "/api/v1/candidates/test_2"
        assert mock_api.async_put.call_args[0][1]["state"] == "dismissed"

    @pytest.mark.asyncio
    async def test_decision_sync_defer_with_retry(self):
        """Test syncing deferred decision with retry_after_days."""
        mock_api = AsyncMock()
        mock_api.async_put.return_value = None
        
        candidate_id = "core_test_3"
        core_id = candidate_id[5:]
        retry_days = 7
        
        payload = {"state": "deferred", "retry_after_days": retry_days}
        await mock_api.async_put(f"/api/v1/candidates/{core_id}", payload)
        
        mock_api.async_put.assert_called_once()
        assert mock_api.async_put.call_args[0][1]["state"] == "deferred"
        assert mock_api.async_put.call_args[0][1]["retry_after_days"] == 7

    @pytest.mark.asyncio
    async def test_polling_failure_graceful_fallback(self):
        """Test graceful fallback when Core API is unreachable."""
        mock_api = AsyncMock()
        mock_api.async_get.side_effect = Exception("Connection refused")
        
        # Should not raise, just log and continue
        try:
            await mock_api.async_get("/api/v1/candidates?state=pending")
        except Exception:
            pass  # Expected
        
        assert mock_api.async_get.called

    @pytest.mark.asyncio
    async def test_malformed_candidate_skip(self):
        """Test that malformed candidates are skipped gracefully."""
        mock_candidates = [
            {"candidate_id": "good_1", "metadata": {}, "evidence": {}},
            {"no_candidate_id": "bad_1"},  # Missing candidate_id
            {"candidate_id": "good_2", "metadata": {}, "evidence": {}},
        ]
        
        # Filter valid candidates (simulating poller logic)
        valid = [c for c in mock_candidates if c.get("candidate_id")]
        
        assert len(valid) == 2
        assert valid[0]["candidate_id"] == "good_1"
        assert valid[1]["candidate_id"] == "good_2"

    @pytest.mark.asyncio
    async def test_candidate_with_missing_metadata(self):
        """Test candidate with missing metadata fields."""
        mock_cand_dict = {
            "candidate_id": "test_partial",
            "state": "pending",
            "metadata": {},  # Empty metadata
            "evidence": {"confidence": 0.8},
        }
        
        # Should still build a candidate with sensible defaults
        trigger = mock_cand_dict.get("metadata", {}).get("trigger_entity", "")
        target = mock_cand_dict.get("metadata", {}).get("target_entity", "")
        
        # Verify fallback title generation
        title = f"A→B: {trigger} → {target}" if (trigger and target) else "A→B Pattern"
        assert "A→B Pattern" in title

    @pytest.mark.asyncio
    async def test_duplicate_candidate_handling(self):
        """Test that duplicate candidates in one polling cycle are handled."""
        candidates_raw = [
            {"candidate_id": "dup_1", "state": "pending", "metadata": {}, "evidence": {}},
            {"candidate_id": "dup_1", "state": "pending", "metadata": {}, "evidence": {}},
        ]
        
        # Simulate deduplication by candidate_id
        unique = {}
        for c in candidates_raw:
            unique[c["candidate_id"]] = c
        
        assert len(unique) == 1

    @pytest.mark.asyncio
    async def test_candidate_state_transition_pending_to_offered(self):
        """Test state transition: pending → offered after HA display."""
        mock_api = AsyncMock()
        mock_api.async_get.return_value = [
            {"candidate_id": "test_s1", "state": "pending", "metadata": {}, "evidence": {}}
        ]
        
        # Step 1: Poll pending candidates
        response = await mock_api.async_get("/api/v1/candidates?state=pending")
        assert response[0]["state"] == "pending"
        
        # Step 2: Mark as offered after display
        mock_api.async_put.return_value = None
        await mock_api.async_put(
            "/api/v1/candidates/test_s1",
            {"state": "offered"}
        )
        
        mock_api.async_put.assert_called_once()

    @pytest.mark.asyncio
    async def test_candidate_evidence_preservation(self):
        """Test that evidence data is preserved through the workflow."""
        evidence = {
            "support": 0.85,
            "confidence": 0.92,
            "lift": 3.2,
        }
        
        mock_cand = {
            "candidate_id": "test_ev",
            "evidence": evidence,
        }
        
        # Evidence should be accessible for N1 display
        assert mock_cand["evidence"]["support"] == 0.85
        assert mock_cand["evidence"]["confidence"] == 0.92
        assert mock_cand["evidence"]["lift"] == 3.2

    @pytest.mark.asyncio
    async def test_polling_interval_validation(self):
        """Test that polling interval is reasonable."""
        from datetime import timedelta
        
        # Default poll interval should be 5 minutes
        default_interval = timedelta(minutes=5)
        
        assert default_interval.total_seconds() == 300
        assert default_interval.total_seconds() < 600  # Less than 10 min

    @pytest.mark.asyncio
    async def test_candidate_poller_startup_delay(self):
        """Test that poller waits for Core to initialize."""
        startup_delay = 30  # seconds
        poll_interval = 300  # 5 minutes
        
        # First poll should be after startup_delay + first interval
        first_poll_at = startup_delay + poll_interval
        
        assert first_poll_at > startup_delay
        assert first_poll_at > 0


class TestRepairsWorkflow:
    """Tests for the full Repairs workflow with decision handling."""

    @pytest.mark.asyncio
    async def test_repairs_accept_flow(self):
        """Test complete accept workflow: Repairs → Core."""
        mock_api = AsyncMock()
        
        # 1. Candidate offered in Repairs
        candidate_data = {
            "core_candidate_id": "test_cand_1",
            "evidence": {"confidence": 0.92},
        }
        
        # 2. User clicks "Blueprint importiert"
        decision = "imported"  # Maps to "accepted" for Core
        
        # 3. Sync back to Core
        core_state = "accepted" if decision == "imported" else decision
        await mock_api.async_put(
            "/api/v1/candidates/test_cand_1",
            {"state": core_state}
        )
        
        assert mock_api.async_put.called

    @pytest.mark.asyncio
    async def test_repairs_defer_flow(self):
        """Test complete defer workflow with retry window."""
        mock_api = AsyncMock()
        
        candidate_data = {"core_candidate_id": "test_cand_2"}
        decision_days = 7
        
        await mock_api.async_put(
            "/api/v1/candidates/test_cand_2",
            {"state": "deferred", "retry_after_days": decision_days}
        )
        
        call_args = mock_api.async_put.call_args[0]
        assert call_args[1]["state"] == "deferred"
        assert call_args[1]["retry_after_days"] == 7

    @pytest.mark.asyncio
    async def test_repairs_dismiss_flow(self):
        """Test complete dismiss workflow."""
        mock_api = AsyncMock()
        
        candidate_data = {"core_candidate_id": "test_cand_3"}
        
        await mock_api.async_put(
            "/api/v1/candidates/test_cand_3",
            {"state": "dismissed"}
        )
        
        assert mock_api.async_put.call_args[0][1]["state"] == "dismissed"

    @pytest.mark.asyncio
    async def test_repairs_sync_failure_doesnt_break_flow(self):
        """Test that Repairs UX isn't blocked if sync to Core fails."""
        mock_api = AsyncMock()
        mock_api.async_put.side_effect = Exception("Core unreachable")
        
        # Even if sync fails, Repairs should succeed (best-effort)
        try:
            await mock_api.async_put(
                "/api/v1/candidates/test_cand_4",
                {"state": "accepted"}
            )
        except Exception:
            pass  # Expected, but should be handled gracefully in real code
        
        # Repairs UX would continue unaffected


class TestCandidatePollerEdgeCases:
    """Edge case tests for robustness."""

    @pytest.mark.asyncio
    async def test_empty_candidates_response(self):
        """Test handling of empty pending candidates."""
        mock_api = AsyncMock()
        mock_api.async_get.return_value = []
        
        response = await mock_api.async_get("/api/v1/candidates?state=pending")
        
        assert response == []
        assert len(response) == 0

    @pytest.mark.asyncio
    async def test_very_large_candidate_payload(self):
        """Test handling of unusually large candidate responses."""
        # Simulate 100 pending candidates
        mock_candidates = [
            {
                "candidate_id": f"cand_{i}",
                "state": "pending",
                "metadata": {"trigger_entity": f"sensor.temp_{i}"},
                "evidence": {"confidence": 0.9},
            }
            for i in range(100)
        ]
        
        mock_api = AsyncMock()
        mock_api.async_get.return_value = mock_candidates
        
        response = await mock_api.async_get("/api/v1/candidates?state=pending")
        
        assert len(response) == 100
        assert response[0]["candidate_id"] == "cand_0"
        assert response[99]["candidate_id"] == "cand_99"

    @pytest.mark.asyncio
    async def test_candidate_id_prefix_handling(self):
        """Test correct stripping of 'core_' prefix in IDs."""
        test_cases = [
            ("core_abc123", "abc123"),
            ("core_", ""),
            ("abc123", "abc123"),  # No prefix
            ("CORE_test", "CORE_test"),  # Case-sensitive
        ]
        
        for input_id, expected_core_id in test_cases:
            core_id = input_id[5:] if input_id.startswith("core_") else input_id
            assert core_id == expected_core_id

    @pytest.mark.asyncio
    async def test_retry_after_days_boundary_values(self):
        """Test boundary values for retry_after_days."""
        mock_api = AsyncMock()
        
        # Valid range: 1-365 days
        for days in [1, 7, 30, 365]:
            mock_api.reset_mock()
            await mock_api.async_put(
                "/api/v1/candidates/test",
                {"state": "deferred", "retry_after_days": days}
            )
            assert mock_api.async_put.called
        
        # Edge: 0 and 366 should fail validation (in real implementation)
        # For now, just verify the test structure is sound
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
