from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class MoodScore:
    """Scaffold output for mood scoring.

    This is deliberately conservative: no PII inference, no long retention.
    """

    ts: str
    window_seconds: int
    score: float  # -1..+1
    label: str
    signals: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "window_seconds": self.window_seconds,
            "score": self.score,
            "label": self.label,
            "signals": self.signals,
        }


class MoodScorer:
    """Very small scoring stub.

    Later iterations can:
    - plug in different engines (heuristic, ML, LLM)
    - incorporate candidate store + event store
    """

    def __init__(self, *, window_seconds: int = 3600):
        self.window_seconds = window_seconds

    def score_from_events(self, events: list[dict[str, Any]]) -> MoodScore:
        # Placeholder heuristic: count sentiment-ish event types.
        # Keep it simple and safe: default neutral.
        pos = sum(1 for e in events if str(e.get("type")) in ("compliment", "positive", "thanks"))
        neg = sum(1 for e in events if str(e.get("type")) in ("complaint", "negative", "frustration"))
        total = max(1, pos + neg)
        raw = (pos - neg) / total

        # clamp
        score = max(-1.0, min(1.0, float(raw)))
        label = "neutral"
        if score > 0.25:
            label = "positive"
        elif score < -0.25:
            label = "negative"

        return MoodScore(
            ts=_now_iso(),
            window_seconds=self.window_seconds,
            score=score,
            label=label,
            signals={"pos": pos, "neg": neg, "n_events": len(events)},
        )
