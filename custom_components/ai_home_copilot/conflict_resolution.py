"""Conflict Resolution Engine for Multi-User Preferences.

Detects when multiple active users have divergent mood preferences,
surfaces conflicts via sensors, and provides resolution strategies.

Strategies:
- weighted: Priority-weighted aggregation (default, automatic)
- compromise: Average all preferences equally
- override: Single user's preference wins

Privacy: All data stays local in HA.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

_LOGGER = logging.getLogger(__name__)

# Divergence threshold — if any mood axis differs by more than this
# between any two users, a conflict is flagged.
_DIVERGENCE_THRESHOLD = 0.3


@dataclass
class ConflictDetail:
    """A single preference conflict between users."""

    axis: str  # "comfort", "frugality", "joy"
    user_a: str
    user_b: str
    value_a: float
    value_b: float
    divergence: float  # abs(value_a - value_b)


@dataclass
class ConflictState:
    """Current conflict state."""

    active: bool = False
    conflicts: List[ConflictDetail] = field(default_factory=list)
    users_involved: List[str] = field(default_factory=list)
    resolution: str = "weighted"  # weighted | compromise | override
    override_user: Optional[str] = None
    resolved_mood: Dict[str, float] = field(default_factory=dict)
    detected_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active": self.active,
            "conflict_count": len(self.conflicts),
            "users_involved": self.users_involved,
            "resolution": self.resolution,
            "override_user": self.override_user,
            "resolved_mood": self.resolved_mood,
            "details": [
                {
                    "axis": c.axis,
                    "user_a": c.user_a,
                    "user_b": c.user_b,
                    "value_a": round(c.value_a, 2),
                    "value_b": round(c.value_b, 2),
                    "divergence": round(c.divergence, 2),
                }
                for c in self.conflicts
            ],
        }


class ConflictResolver:
    """Detects and resolves multi-user preference conflicts."""

    def __init__(self, threshold: float = _DIVERGENCE_THRESHOLD):
        self.threshold = threshold
        self._state = ConflictState()
        self._resolution_strategy = "weighted"
        self._override_user: Optional[str] = None
        self._resolution_history: List[Dict[str, Any]] = []

    @property
    def state(self) -> ConflictState:
        return self._state

    def set_strategy(self, strategy: str, override_user: Optional[str] = None) -> None:
        """Set the resolution strategy."""
        if strategy not in ("weighted", "compromise", "override"):
            raise ValueError(f"Unknown strategy: {strategy}")
        self._resolution_strategy = strategy
        self._override_user = override_user
        _LOGGER.info("Conflict resolution strategy set to: %s", strategy)

    def evaluate(
        self,
        user_moods: Dict[str, Dict[str, float]],
        user_priorities: Dict[str, float],
    ) -> ConflictState:
        """Evaluate preferences and detect conflicts.

        Args:
            user_moods: {user_id: {comfort, frugality, joy}}
            user_priorities: {user_id: priority_float}

        Returns:
            Updated ConflictState.
        """
        users = list(user_moods.keys())
        conflicts: List[ConflictDetail] = []

        # Pairwise comparison on each axis
        for i, ua in enumerate(users):
            for ub in users[i + 1 :]:
                mood_a = user_moods[ua]
                mood_b = user_moods[ub]
                for axis in ("comfort", "frugality", "joy"):
                    va = mood_a.get(axis, 0.5)
                    vb = mood_b.get(axis, 0.5)
                    div = abs(va - vb)
                    if div >= self.threshold:
                        conflicts.append(
                            ConflictDetail(
                                axis=axis,
                                user_a=ua,
                                user_b=ub,
                                value_a=va,
                                value_b=vb,
                                divergence=div,
                            )
                        )

        # Resolve
        resolved = self._resolve(user_moods, user_priorities)

        self._state = ConflictState(
            active=len(conflicts) > 0,
            conflicts=conflicts,
            users_involved=users,
            resolution=self._resolution_strategy,
            override_user=self._override_user if self._resolution_strategy == "override" else None,
            resolved_mood=resolved,
            detected_at=time.time() if conflicts else 0.0,
        )

        if conflicts:
            _LOGGER.info(
                "Conflict detected: %d issue(s) between %s — resolved via %s",
                len(conflicts),
                ", ".join(users),
                self._resolution_strategy,
            )

        return self._state

    def _resolve(
        self,
        user_moods: Dict[str, Dict[str, float]],
        user_priorities: Dict[str, float],
    ) -> Dict[str, float]:
        """Apply resolution strategy."""
        if not user_moods:
            return {"comfort": 0.5, "frugality": 0.5, "joy": 0.5}

        if self._resolution_strategy == "override" and self._override_user:
            if self._override_user in user_moods:
                return dict(user_moods[self._override_user])

        if self._resolution_strategy == "compromise":
            # Equal-weight average
            mood = {"comfort": 0.0, "frugality": 0.0, "joy": 0.0}
            for um in user_moods.values():
                for k in mood:
                    mood[k] += um.get(k, 0.5)
            n = len(user_moods)
            return {k: round(v / n, 3) for k, v in mood.items()}

        # Default: weighted by priority
        mood = {"comfort": 0.0, "frugality": 0.0, "joy": 0.0}
        total_w = 0.0
        for uid, um in user_moods.items():
            w = user_priorities.get(uid, 0.5)
            for k in mood:
                mood[k] += um.get(k, 0.5) * w
            total_w += w
        if total_w > 0:
            mood = {k: round(v / total_w, 3) for k, v in mood.items()}
        return mood
