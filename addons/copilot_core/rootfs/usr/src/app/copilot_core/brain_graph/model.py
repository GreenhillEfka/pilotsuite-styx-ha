from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

NodeKind = Literal["entity", "zone", "device", "person", "concept", "module", "event"]
EdgeType = Literal[
    "in_zone",
    "controls",
    "affects",
    "correlates",
    "triggered_by",
    "observed_with",
    "mentions",
]


@dataclass
class GraphNode:
    id: str
    kind: NodeKind
    label: str
    updated_at_ms: int
    score: float

    # Optional allowlist-ish fields
    domain: str | None = None
    source: dict[str, Any] | None = None
    tags: list[str] | None = None
    meta: dict[str, Any] | None = None


@dataclass
class GraphEdge:
    id: str
    from_id: str
    to_id: str
    type: EdgeType
    updated_at_ms: int
    weight: float

    evidence: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None


@dataclass
class GraphState:
    version: int = 1
    generated_at_ms: int = 0
    limits: dict[str, int] = field(default_factory=dict)
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
