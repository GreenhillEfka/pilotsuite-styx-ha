from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict
from typing import Any

from copilot_core.brain_graph.model import GraphEdge, GraphNode


class BrainGraphStore:
    """In-memory graph store with simple JSON persistence.

    v0.1 goals:
    - keep data shape stable
    - stay privacy-first (no raw HA payloads)
    - bounded limits enforced by service (not here)
    """

    def __init__(self, json_path: str = "/data/brain_graph.json", persist: bool = True):
        self._json_path = json_path
        self._persist = persist
        self._lock = threading.Lock()
        self.nodes: dict[str, GraphNode] = {}
        self.edges: dict[str, GraphEdge] = {}
        self._load_best_effort()

    @property
    def json_path(self) -> str:
        return self._json_path

    def _load_best_effort(self) -> None:
        if not self._persist:
            return
        try:
            with open(self._json_path, "r", encoding="utf-8") as fh:
                data = json.load(fh) or {}
            nodes = data.get("nodes") or []
            edges = data.get("edges") or []
            if isinstance(nodes, list):
                for n in nodes:
                    if isinstance(n, dict) and isinstance(n.get("id"), str):
                        try:
                            self.nodes[n["id"]] = GraphNode(
                                id=str(n["id"]),
                                kind=str(n.get("kind", "concept")),
                                label=str(n.get("label", n["id"])),
                                updated_at_ms=int(n.get("updated_at_ms", 0)),
                                score=float(n.get("score", 0.0)),
                                domain=n.get("domain"),
                                source=n.get("source"),
                                tags=n.get("tags"),
                                meta=n.get("meta"),
                            )
                        except Exception:
                            continue
            if isinstance(edges, list):
                for e in edges:
                    if isinstance(e, dict) and isinstance(e.get("id"), str):
                        try:
                            self.edges[e["id"]] = GraphEdge(
                                id=str(e["id"]),
                                from_id=str(e.get("from") or e.get("from_id") or ""),
                                to_id=str(e.get("to") or e.get("to_id") or ""),
                                type=str(e.get("type", "correlates")),
                                updated_at_ms=int(e.get("updated_at_ms", 0)),
                                weight=float(e.get("weight", 0.0)),
                                evidence=e.get("evidence"),
                                meta=e.get("meta"),
                            )
                        except Exception:
                            continue
        except Exception:
            # First run / no file / invalid JSON is fine.
            return

    def save_best_effort(self) -> None:
        if not self._persist:
            return
        with self._lock:
            try:
                os.makedirs(os.path.dirname(self._json_path), exist_ok=True)
                payload: dict[str, Any] = {
                    "version": 1,
                    "nodes": [asdict(n) for n in self.nodes.values()],
                    "edges": [
                        {
                            "id": e.id,
                            "from": e.from_id,
                            "to": e.to_id,
                            "type": e.type,
                            "updated_at_ms": e.updated_at_ms,
                            "weight": e.weight,
                        }
                        for e in self.edges.values()
                    ],
                }
                tmp = self._json_path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh, ensure_ascii=False)
                os.replace(tmp, self._json_path)
            except Exception:
                # best-effort; never crash request paths
                return
