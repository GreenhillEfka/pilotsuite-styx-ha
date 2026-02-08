from __future__ import annotations

import hashlib
import math
import re
import time
from dataclasses import asdict
from typing import Any, Iterable

from copilot_core.brain_graph.model import EdgeType, GraphEdge, GraphNode, NodeKind
from copilot_core.brain_graph.store import BrainGraphStore


_RE_EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
_RE_URL = re.compile(r"https?://", re.IGNORECASE)
_RE_IP = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
_RE_PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def now_ms() -> int:
    return int(time.time() * 1000)


def _stable_edge_id(from_id: str, type_: str, to_id: str) -> str:
    raw = f"{from_id}|{type_}|{to_id}".encode("utf-8")
    h = hashlib.sha256(raw).hexdigest()[:16]
    return f"e:{h}"


def _sanitize_meta(meta: dict[str, Any] | None, *, max_bytes: int = 2048) -> dict[str, Any] | None:
    if not meta or not isinstance(meta, dict):
        return None

    out: dict[str, Any] = {}
    for k, v in meta.items():
        if not isinstance(k, str):
            continue
        # Keep only simple scalar values.
        if isinstance(v, (int, float, bool)):
            out[k] = v
        elif isinstance(v, str):
            s = v.strip()
            # Redact likely sensitive patterns.
            if _RE_EMAIL.search(s) or _RE_URL.search(s) or _RE_IP.search(s) or _RE_PHONE.search(s):
                continue
            # Truncate strings.
            if len(s) > 120:
                s = s[:120] + "…"
            out[k] = s
        else:
            continue

    # Enforce max size (roughly)
    try:
        if len(str(out).encode("utf-8")) > max_bytes:
            # If too big, drop entirely (v0.1 simplicity)
            return None
    except Exception:
        return None

    return out or None


class BrainGraphService:
    def __init__(
        self,
        store: BrainGraphStore,
        *,
        nodes_max: int = 500,
        edges_max: int = 1500,
        node_half_life_ms: int = 24 * 3600 * 1000,
        edge_half_life_ms: int = 12 * 3600 * 1000,
        node_min: float = 0.05,
        edge_min: float = 0.05,
    ):
        self.store = store
        self.nodes_max = nodes_max
        self.edges_max = edges_max
        self.node_half_life_ms = node_half_life_ms
        self.edge_half_life_ms = edge_half_life_ms
        self.node_min = node_min
        self.edge_min = edge_min

    def touch_node(
        self,
        node_id: str,
        *,
        delta: float = 1.0,
        label: str | None = None,
        kind: NodeKind = "concept",
        domain: str | None = None,
        meta_patch: dict[str, Any] | None = None,
        now: int | None = None,
    ) -> GraphNode:
        t = int(now or now_ms())
        n = self.store.nodes.get(node_id)
        if n is None:
            n = GraphNode(
                id=node_id,
                kind=kind,
                label=label or node_id,
                domain=domain,
                updated_at_ms=t,
                score=max(0.0, float(delta)),
                meta=_sanitize_meta(meta_patch),
            )
            self.store.nodes[node_id] = n
        else:
            n.score = float(n.score) + float(delta)
            n.updated_at_ms = t
            if label:
                n.label = label
            if domain:
                n.domain = domain
            if meta_patch:
                merged = dict(n.meta or {})
                merged.update(_sanitize_meta(meta_patch) or {})
                n.meta = _sanitize_meta(merged)

        return n

    def touch_edge(
        self,
        from_id: str,
        type_: EdgeType,
        to_id: str,
        *,
        delta: float = 1.0,
        meta_patch: dict[str, Any] | None = None,
        now: int | None = None,
    ) -> GraphEdge:
        t = int(now or now_ms())
        edge_id = _stable_edge_id(from_id, type_, to_id)
        e = self.store.edges.get(edge_id)
        if e is None:
            e = GraphEdge(
                id=edge_id,
                from_id=from_id,
                to_id=to_id,
                type=type_,
                updated_at_ms=t,
                weight=max(0.0, float(delta)),
                meta=_sanitize_meta(meta_patch),
            )
            self.store.edges[edge_id] = e
        else:
            e.weight = float(e.weight) + float(delta)
            e.updated_at_ms = t
            if meta_patch:
                merged = dict(e.meta or {})
                merged.update(_sanitize_meta(meta_patch) or {})
                e.meta = _sanitize_meta(merged)
        return e

    def _decay(self, value: float, age_ms: int, half_life_ms: int) -> float:
        if value <= 0:
            return 0.0
        if age_ms <= 0:
            return float(value)
        if half_life_ms <= 0:
            return float(value)
        # exponential decay: v * 0.5^(age/half_life)
        return float(value) * math.pow(0.5, float(age_ms) / float(half_life_ms))

    def _effective_node_score(self, n: GraphNode, t: int) -> float:
        return self._decay(float(n.score), t - int(n.updated_at_ms), self.node_half_life_ms)

    def _effective_edge_weight(self, e: GraphEdge, t: int) -> float:
        return self._decay(float(e.weight), t - int(e.updated_at_ms), self.edge_half_life_ms)

    def prune(self, *, now: int | None = None) -> None:
        t = int(now or now_ms())

        # 1) drop low-weight edges
        eff_edges: list[tuple[str, float, int]] = []  # (id, eff_w, updated)
        for eid, e in list(self.store.edges.items()):
            w = self._effective_edge_weight(e, t)
            if w < self.edge_min:
                self.store.edges.pop(eid, None)
            else:
                eff_edges.append((eid, w, int(e.updated_at_ms)))

        # 2) keep top-K edges
        if len(eff_edges) > self.edges_max:
            eff_edges.sort(key=lambda x: (x[1], x[2]), reverse=True)
            keep = {eid for (eid, _, _) in eff_edges[: self.edges_max]}
            for eid in list(self.store.edges.keys()):
                if eid not in keep:
                    self.store.edges.pop(eid, None)

        # 3) drop nodes with low score and no remaining edges
        incident: set[str] = set()
        for e in self.store.edges.values():
            incident.add(e.from_id)
            incident.add(e.to_id)

        eff_nodes: list[tuple[str, float, int]] = []
        for nid, n in list(self.store.nodes.items()):
            s = self._effective_node_score(n, t)
            if s < self.node_min and nid not in incident:
                self.store.nodes.pop(nid, None)
            else:
                eff_nodes.append((nid, s, int(n.updated_at_ms)))

        # 4) keep top-K nodes
        if len(eff_nodes) > self.nodes_max:
            eff_nodes.sort(key=lambda x: (x[1], x[2]), reverse=True)
            keep_nodes = {nid for (nid, _, _) in eff_nodes[: self.nodes_max]}
            for nid in list(self.store.nodes.keys()):
                if nid not in keep_nodes:
                    self.store.nodes.pop(nid, None)

            # remove edges incident to removed nodes
            for eid, e in list(self.store.edges.items()):
                if e.from_id not in keep_nodes or e.to_id not in keep_nodes:
                    self.store.edges.pop(eid, None)

    def export_state(
        self,
        *,
        kind: Iterable[str] | None = None,
        domain: Iterable[str] | None = None,
        center: str | None = None,
        hops: int = 1,
        limit_nodes: int = 500,
        limit_edges: int = 1500,
        now: int | None = None,
    ) -> dict[str, Any]:
        """Export a bounded, privacy-first view of the graph.

        This intentionally omits meta/evidence in v0.1.
        """
        t = int(now or now_ms())
        self.prune(now=t)

        kinds = {k for k in (kind or []) if isinstance(k, str)}
        domains = {d for d in (domain or []) if isinstance(d, str)}

        # Initial node selection
        nodes = list(self.store.nodes.values())
        if kinds:
            nodes = [n for n in nodes if n.kind in kinds]
        if domains:
            nodes = [n for n in nodes if (n.domain or "") in domains]

        # Neighborhood mode
        if center and isinstance(center, str) and center:
            selected: set[str] = set([center]) if center in self.store.nodes else set()
            frontier = set(selected)
            for _ in range(max(0, min(int(hops), 2))):
                nxt: set[str] = set()
                for e in self.store.edges.values():
                    if e.from_id in frontier:
                        nxt.add(e.to_id)
                    if e.to_id in frontier:
                        nxt.add(e.from_id)
                nxt = {nid for nid in nxt if nid in self.store.nodes}
                nxt -= selected
                selected |= nxt
                frontier = nxt
            nodes = [self.store.nodes[nid] for nid in selected]

        # Top-K nodes by effective score
        nodes.sort(key=lambda n: (self._effective_node_score(n, t), int(n.updated_at_ms)), reverse=True)
        limit_nodes = max(1, min(int(limit_nodes), self.nodes_max))
        nodes = nodes[:limit_nodes]
        keep_ids = {n.id for n in nodes}

        # Edges among kept nodes
        edges = [e for e in self.store.edges.values() if e.from_id in keep_ids and e.to_id in keep_ids]
        edges.sort(key=lambda e: (self._effective_edge_weight(e, t), int(e.updated_at_ms)), reverse=True)
        limit_edges = max(1, min(int(limit_edges), self.edges_max))
        edges = edges[:limit_edges]

        return {
            "version": 1,
            "generated_at_ms": t,
            "limits": {"nodes_max": self.nodes_max, "edges_max": self.edges_max},
            "nodes": [
                {
                    "id": n.id,
                    "kind": n.kind,
                    "label": n.label,
                    **({"domain": n.domain} if n.domain else {}),
                    "score": round(self._effective_node_score(n, t), 6),
                    "updated_at_ms": int(n.updated_at_ms),
                }
                for n in nodes
            ],
            "edges": [
                {
                    "id": e.id,
                    "from": e.from_id,
                    "to": e.to_id,
                    "type": e.type,
                    "weight": round(self._effective_edge_weight(e, t), 6),
                    "updated_at_ms": int(e.updated_at_ms),
                }
                for e in edges
            ],
        }

    def persist_best_effort(self) -> None:
        # Persist after pruning; only minimal serialization is used.
        self.prune()
        self.store.save_best_effort()

    def debug_counts(self) -> dict[str, int]:
        return {"nodes": len(self.store.nodes), "edges": len(self.store.edges)}
