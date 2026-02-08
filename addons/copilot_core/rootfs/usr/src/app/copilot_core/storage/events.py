import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Event:
    """Canonical event envelope.

    Designed to map cleanly from HA event bus / state changes / intent results.
    """

    id: str
    ts: str
    type: str
    source: str = ""
    entity_id: str = ""
    user_id: str = ""
    text: str = ""
    attributes: dict[str, Any] | None = None

    @staticmethod
    def from_payload(payload: dict[str, Any]) -> "Event":
        # Safe defaults; no validation explosions.
        eid = str(payload.get("id") or payload.get("event_id") or "")
        if not eid:
            # cheap unique-ish id: ts + hash of content
            eid = f"evt_{int(datetime.now(timezone.utc).timestamp() * 1000)}"

        ts = str(payload.get("ts") or payload.get("time") or payload.get("timestamp") or _now_iso())
        typ = str(payload.get("type") or payload.get("event_type") or "unknown")

        return Event(
            id=eid,
            ts=ts,
            type=typ,
            source=str(payload.get("source") or ""),
            entity_id=str(payload.get("entity_id") or ""),
            user_id=str(payload.get("user_id") or ""),
            text=str(payload.get("text") or payload.get("message") or ""),
            attributes=(payload.get("attributes") if isinstance(payload.get("attributes"), dict) else None),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ts": self.ts,
            "type": self.type,
            "source": self.source,
            "entity_id": self.entity_id,
            "user_id": self.user_id,
            "text": self.text,
            "attributes": self.attributes or {},
        }


class EventStore:
    """Small event ingest store.

    - Memory ring buffer always enabled.
    - Optional JSONL persistence for debugging/bootstrapping.
    """

    def __init__(self, *, cache_max: int = 500, persist: bool = False, jsonl_path: str = "/data/events.jsonl"):
        self.cache_max = max(1, cache_max)
        self.persist = bool(persist)
        self.jsonl_path = jsonl_path
        self._cache: list[dict[str, Any]] = []

        # Load tail on boot if file exists
        if self.persist:
            self._load_tail()

    def _load_tail(self) -> None:
        try:
            with open(self.jsonl_path, "r", encoding="utf-8") as fh:
                lines = fh.readlines()[-self.cache_max :]
            for line in lines:
                try:
                    self._cache.append(json.loads(line))
                except Exception:
                    continue
        except Exception:
            return

    def append(self, payload: dict[str, Any]) -> dict[str, Any]:
        evt = Event.from_payload(payload).to_dict()
        evt["received"] = _now_iso()

        if self.persist:
            os.makedirs(os.path.dirname(self.jsonl_path), exist_ok=True)
            with open(self.jsonl_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(evt, ensure_ascii=False) + "\n")

        self._cache.append(evt)
        if len(self._cache) > self.cache_max:
            del self._cache[: len(self._cache) - self.cache_max]

        return evt

    def extend(self, items: Iterable[dict[str, Any]]) -> int:
        n = 0
        for it in items:
            try:
                self.append(it)
                n += 1
            except Exception:
                continue
        return n

    def list(self, *, limit: int = 50, since_ts: Optional[str] = None) -> list[dict[str, Any]]:
        items = self._cache
        if since_ts:
            # naive filter (string compare works for ISO8601; good enough for scaffold)
            items = [e for e in items if str(e.get("ts", "")) >= since_ts]
        limit = max(1, min(int(limit), self.cache_max))
        return items[-limit:]
