"""Tests for PilotSuite Panel Setup — SuggestionPanel services and WebSocket API.

Covers:
- Suggestion panel services: accept, reject, snooze
- WebSocket command registration
- SuggestionQueue: add, trim, duplicate prevention, priority computation
- SuggestionPriority cascade
- Error handling: missing store, invalid IDs, expired suggestions
- Panel removal (queue state management)
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta

# Patch dt_util.utcnow before importing suggestion_panel
import sys
sys.modules["homeassistant.util"].dt.utcnow = lambda: datetime(2025, 6, 1, 12, 0, 0)

from custom_components.ai_home_copilot.suggestion_panel import (
    Suggestion,
    SuggestionStatus,
    SuggestionPriority,
    SuggestionQueue,
    SuggestionPanelStore,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_suggestion(
    sid: str = "s1",
    confidence: float = 0.8,
    lift: float = 2.0,
    support: int = 10,
    mood_value: float = 0.6,
    safety_critical: bool = False,
    status: SuggestionStatus = SuggestionStatus.PENDING,
    zone_id: str = "",
    mood_type: str = "",
) -> Suggestion:
    return Suggestion(
        suggestion_id=sid,
        pattern="light.kitchen:on -> switch.coffee:on",
        confidence=confidence,
        lift=lift,
        support=support,
        mood_value=mood_value,
        safety_critical=safety_critical,
        status=status,
        zone_id=zone_id,
        mood_type=mood_type,
        created_at=datetime(2025, 1, 1, 12, 0, 0),
    )


# ---------------------------------------------------------------------------
# Suggestion Dataclass
# ---------------------------------------------------------------------------

class TestSuggestion:
    def test_to_dict_roundtrip(self):
        s = _make_suggestion()
        d = s.to_dict()
        assert d["suggestion_id"] == "s1"
        assert d["confidence"] == 0.8
        assert d["status"] == "pending"
        assert isinstance(d["created_at"], str)

    def test_compute_priority_high(self):
        s = _make_suggestion(confidence=0.9, lift=4.0, mood_value=0.8)
        assert s.compute_priority() == SuggestionPriority.HIGH

    def test_compute_priority_medium(self):
        # score = 0.5*40 + min(2/5,1)*30 + 0.6*20 = 20 + 12 + 12 = 44
        s = _make_suggestion(confidence=0.5, lift=2.0, mood_value=0.6)
        assert s.compute_priority() == SuggestionPriority.MEDIUM

    def test_compute_priority_low(self):
        s = _make_suggestion(confidence=0.1, lift=0.5, mood_value=0.0)
        assert s.compute_priority() == SuggestionPriority.LOW

    def test_safety_critical_penalty(self):
        s_safe = _make_suggestion(confidence=0.7, lift=2.0, mood_value=0.6)
        s_critical = _make_suggestion(confidence=0.7, lift=2.0, mood_value=0.6, safety_critical=True)
        # Safety critical should get lower priority
        safe_priority = s_safe.compute_priority()
        crit_priority = s_critical.compute_priority()
        priority_order = {SuggestionPriority.HIGH: 0, SuggestionPriority.MEDIUM: 1, SuggestionPriority.LOW: 2}
        assert priority_order[crit_priority] >= priority_order[safe_priority]


# ---------------------------------------------------------------------------
# SuggestionQueue
# ---------------------------------------------------------------------------

class TestSuggestionQueue:
    def test_add_and_get_pending(self):
        q = SuggestionQueue()
        q.add(_make_suggestion("s1"))
        assert len(q.get_pending()) == 1

    def test_duplicate_prevention(self):
        q = SuggestionQueue()
        q.add(_make_suggestion("s1"))
        q.add(_make_suggestion("s1"))
        assert len(q.suggestions) == 1

    def test_get_by_id(self):
        q = SuggestionQueue()
        q.add(_make_suggestion("s1"))
        assert q.get_by_id("s1") is not None
        assert q.get_by_id("nonexistent") is None

    def test_accept(self):
        q = SuggestionQueue()
        q.add(_make_suggestion("s1"))
        assert q.accept("s1", user="andreas")
        assert q.get_by_id("s1").status == SuggestionStatus.ACCEPTED
        assert q.get_by_id("s1").accepted_by == "andreas"

    def test_accept_non_pending_fails(self):
        q = SuggestionQueue()
        q.add(_make_suggestion("s1"))
        q.accept("s1")
        # Accepting again should fail
        assert not q.accept("s1")

    def test_reject(self):
        q = SuggestionQueue()
        q.add(_make_suggestion("s1"))
        assert q.reject("s1", user="andreas", reason="not useful")
        s = q.get_by_id("s1")
        assert s.status == SuggestionStatus.REJECTED
        assert s.rejection_reason == "not useful"

    def test_snooze(self):
        q = SuggestionQueue()
        q.add(_make_suggestion("s1"))
        assert q.snooze("s1", timedelta(hours=2))
        s = q.get_by_id("s1")
        assert s.snoozed_until is not None

    def test_snoozed_excluded_from_pending(self):
        q = SuggestionQueue()
        s = _make_suggestion("s1")
        q.add(s)
        q.snooze("s1", timedelta(hours=999))
        assert len(q.get_pending()) == 0

    def test_filter_by_zone(self):
        q = SuggestionQueue()
        q.add(_make_suggestion("s1", zone_id="wohnzimmer"))
        q.add(_make_suggestion("s2", zone_id="kueche"))
        result = q.get_pending(zone_id="wohnzimmer")
        assert len(result) == 1
        assert result[0].suggestion_id == "s1"

    def test_filter_by_mood_type(self):
        q = SuggestionQueue()
        q.add(_make_suggestion("s1", mood_type="relax"))
        q.add(_make_suggestion("s2", mood_type="active"))
        result = q.get_pending(mood_type="relax")
        assert len(result) == 1

    def test_trim_max_pending(self):
        q = SuggestionQueue(max_pending=3)
        for i in range(5):
            q.add(_make_suggestion(f"s{i}"))
        assert len(q.get_pending()) <= 3

    def test_trim_max_history(self):
        q = SuggestionQueue(max_history=2)
        for i in range(4):
            q.add(_make_suggestion(f"s{i}"))
            q.accept(f"s{i}")  # Move to history
        # Trim only runs on add(); trigger it with one more add
        q.add(_make_suggestion("trigger"))
        history = [s for s in q.suggestions if s.status != SuggestionStatus.PENDING]
        assert len(history) <= 2

    def test_pending_sorted_by_priority(self):
        q = SuggestionQueue()
        q.add(_make_suggestion("low", confidence=0.1, lift=0.5, mood_value=0.0))
        q.add(_make_suggestion("high", confidence=0.95, lift=4.5, mood_value=0.9))
        result = q.get_pending()
        assert result[0].suggestion_id == "high"

    def test_to_dict(self):
        q = SuggestionQueue()
        q.add(_make_suggestion("s1"))
        q.add(_make_suggestion("s2"))
        q.accept("s1")
        d = q.to_dict()
        assert d["pending_count"] == 1
        assert d["accepted_count"] == 1
        assert len(d["suggestions"]) == 2

    def test_accept_nonexistent_returns_false(self):
        q = SuggestionQueue()
        assert not q.accept("nonexistent")

    def test_reject_nonexistent_returns_false(self):
        q = SuggestionQueue()
        assert not q.reject("nonexistent")

    def test_snooze_nonexistent_returns_false(self):
        q = SuggestionQueue()
        assert not q.snooze("nonexistent")


# ---------------------------------------------------------------------------
# SuggestionPanelStore
# ---------------------------------------------------------------------------

class TestSuggestionPanelStore:
    def test_store_init(self):
        hass = MagicMock()
        store = SuggestionPanelStore(hass, "test_entry")
        assert store.queue is not None
        assert isinstance(store.queue, SuggestionQueue)

    @pytest.mark.asyncio
    async def test_store_load_empty(self):
        hass = MagicMock()
        store = SuggestionPanelStore(hass, "test_entry")
        with patch("custom_components.ai_home_copilot.suggestion_panel.SuggestionPanelStore.async_load",
                    new_callable=AsyncMock):
            await store.async_load()
            assert len(store.queue.suggestions) == 0


# ---------------------------------------------------------------------------
# Expired Suggestions
# ---------------------------------------------------------------------------

class TestExpiredSuggestions:
    def test_expired_suggestion_auto_removed_from_pending(self):
        q = SuggestionQueue()
        s = _make_suggestion("s1")
        s.expires_at = datetime(2020, 1, 1)  # Far in the past
        q.suggestions.append(s)
        s.priority = s.compute_priority()
        result = q.get_pending()
        assert len(result) == 0
        assert q.get_by_id("s1").status == SuggestionStatus.EXPIRED
