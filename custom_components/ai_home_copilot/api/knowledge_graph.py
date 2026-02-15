"""Knowledge Graph API client for AI Home CoPilot.

Provides async access to the Core Add-on Knowledge Graph endpoints.
The Knowledge Graph captures relationships between entities, patterns,
moods, and contexts for intelligent home automation.

API endpoints (Core Add-on):
- GET /api/v1/kg/stats - Graph statistics
- GET /api/v1/kg/nodes - List nodes
- GET /api/v1/kg/nodes/<id> - Get specific node
- POST /api/v1/kg/nodes - Create node
- GET /api/v1/kg/edges - List edges
- POST /api/v1/kg/edges - Create edge
- POST /api/v1/kg/query - Query graph
- POST /api/v1/kg/import/patterns - Import from Habitus
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import aiohttp

from ..const import HEADER_AUTH

_LOGGER = logging.getLogger(__name__)


class NodeType(Enum):
    """Types of nodes in the Knowledge Graph."""
    ENTITY = "entity"
    DOMAIN = "domain"
    AREA = "area"
    ZONE = "zone"
    PATTERN = "pattern"
    MOOD = "mood"
    CAPABILITY = "cap"
    TAG = "tag"
    TIME_CONTEXT = "time"
    USER = "user"


class EdgeType(Enum):
    """Types of edges in the Knowledge Graph."""
    BELONGS_TO = "belongs_to"
    HAS_CAPABILITY = "has_cap"
    HAS_TAG = "has_tag"
    TRIGGERS = "triggers"
    CORRELATES_WITH = "correlates"
    ACTIVE_DURING = "active_during"
    RELATES_TO_MOOD = "relates_mood"
    PREFERRED_BY = "preferred_by"
    AVOIDED_BY = "avoided_by"


@dataclass
class KGNode:
    """A node in the Knowledge Graph."""
    id: str
    type: NodeType
    label: str
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: int = 0
    updated_at: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "label": self.label,
            "properties": self.properties,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KGNode":
        return cls(
            id=data["id"],
            type=NodeType(data["type"]),
            label=data.get("label", data["id"]),
            properties=data.get("properties", {}),
            created_at=data.get("created_at", 0),
            updated_at=data.get("updated_at", 0),
        )


@dataclass
class KGEdge:
    """An edge (relationship) in the Knowledge Graph."""
    source: str
    target: str
    type: EdgeType
    weight: float = 1.0
    confidence: float = 0.0
    source_type: str = "inferred"
    evidence: dict[str, Any] = field(default_factory=dict)
    created_at: int = 0
    updated_at: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type.value,
            "weight": self.weight,
            "confidence": self.confidence,
            "source_type": self.source_type,
            "evidence": self.evidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KGEdge":
        return cls(
            source=data["source"],
            target=data["target"],
            type=EdgeType(data["type"]),
            weight=data.get("weight", 1.0),
            confidence=data.get("confidence", 0.0),
            source_type=data.get("source_type", "inferred"),
            evidence=data.get("evidence", {}),
            created_at=data.get("created_at", 0),
            updated_at=data.get("updated_at", 0),
        )

    @property
    def id(self) -> str:
        return f"{self.source}:{self.type.value}:{self.target}"


@dataclass
class KGStats:
    """Knowledge Graph statistics."""
    node_count: int = 0
    edge_count: int = 0
    nodes_by_type: dict[str, int] = field(default_factory=dict)
    edges_by_type: dict[str, int] = field(default_factory=dict)
    last_updated: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KGStats":
        return cls(
            node_count=data.get("node_count", 0),
            edge_count=data.get("edge_count", 0),
            nodes_by_type=data.get("nodes_by_type", {}),
            edges_by_type=data.get("edges_by_type", {}),
            last_updated=data.get("last_updated", 0),
        )


@dataclass
class KGQuery:
    """A query against the Knowledge Graph."""
    query_type: str  # semantic, structural, causal, temporal, contextual
    entity_id: Optional[str] = None
    zone_id: Optional[str] = None
    mood: Optional[str] = None
    time_context: Optional[str] = None
    pattern_id: Optional[str] = None
    max_results: int = 10
    min_confidence: float = 0.5
    include_evidence: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_type": self.query_type,
            "entity_id": self.entity_id,
            "zone_id": self.zone_id,
            "mood": self.mood,
            "time_context": self.time_context,
            "pattern_id": self.pattern_id,
            "max_results": self.max_results,
            "min_confidence": self.min_confidence,
            "include_evidence": self.include_evidence,
        }


@dataclass
class KGQueryResult:
    """Result from a Knowledge Graph query."""
    nodes: list[KGNode] = field(default_factory=list)
    edges: list[KGEdge] = field(default_factory=list)
    confidence: float = 0.0
    sources: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KGQueryResult":
        return cls(
            nodes=[KGNode.from_dict(n) for n in data.get("nodes", [])],
            edges=[KGEdge.from_dict(e) for e in data.get("edges", [])],
            confidence=data.get("confidence", 0.0),
            sources=data.get("sources", []),
            evidence=data.get("evidence", {}),
        )


class KnowledgeGraphError(Exception):
    """Knowledge Graph API error."""
    pass


class KnowledgeGraphClient:
    """Async client for Knowledge Graph API."""

    def __init__(self, session: aiohttp.ClientSession, base_url: str, token: str | None):
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._token = token

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._token:
            headers[HEADER_AUTH] = self._token
        return headers

    async def _get(self, path: str) -> dict:
        url = f"{self._base_url}{path}"
        try:
            async with self._session.get(
                url,
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    raise KnowledgeGraphError(f"HTTP {resp.status} for {url}: {body[:200]}")
                return await resp.json()
        except asyncio.TimeoutError as e:
            raise KnowledgeGraphError(f"Timeout calling {url}") from e
        except aiohttp.ClientError as e:
            raise KnowledgeGraphError(f"Client error calling {url}: {e}") from e

    async def _post(self, path: str, payload: dict) -> dict:
        url = f"{self._base_url}{path}"
        try:
            async with self._session.post(
                url,
                json=payload,
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    raise KnowledgeGraphError(f"HTTP {resp.status} for {url}: {body[:200]}")
                if resp.status == 204:
                    return {}
                ctype = resp.headers.get("Content-Type", "")
                if "json" in ctype:
                    return await resp.json()
                return {"text": (await resp.text())[:2000]}
        except asyncio.TimeoutError as e:
            raise KnowledgeGraphError(f"Timeout calling {url}") from e
        except aiohttp.ClientError as e:
            raise KnowledgeGraphError(f"Client error calling {url}: {e}") from e

    # ==================== Stats ====================

    async def get_stats(self) -> KGStats:
        """Get knowledge graph statistics."""
        data = await self._get("/api/v1/kg/stats")
        if not data.get("ok"):
            raise KnowledgeGraphError(data.get("error", "Unknown error"))
        return KGStats.from_dict(data.get("stats", {}))

    # ==================== Node Operations ====================

    async def list_nodes(
        self,
        node_type: NodeType | None = None,
        limit: int = 100,
    ) -> list[KGNode]:
        """List nodes with optional type filter."""
        params = {"limit": str(min(limit, 500))}
        if node_type:
            params["type"] = node_type.value
        data = await self._get(f"/api/v1/kg/nodes?{self._encode_params(params)}")
        if not data.get("ok"):
            raise KnowledgeGraphError(data.get("error", "Unknown error"))
        return [KGNode.from_dict(n) for n in data.get("nodes", [])]

    async def get_node(self, node_id: str) -> KGNode | None:
        """Get a specific node by ID."""
        data = await self._get(f"/api/v1/kg/nodes/{node_id}")
        if not data.get("ok"):
            if "not found" in data.get("error", "").lower():
                return None
            raise KnowledgeGraphError(data.get("error", "Unknown error"))
        return KGNode.from_dict(data.get("node", {}))

    async def create_node(self, node: KGNode) -> KGNode:
        """Create a new node."""
        data = await self._post("/api/v1/kg/nodes", node.to_dict())
        if not data.get("ok"):
            raise KnowledgeGraphError(data.get("error", "Unknown error"))
        return KGNode.from_dict(data.get("node", {}))

    async def add_entity_node(
        self,
        entity_id: str,
        label: str | None = None,
        domain: str | None = None,
        area: str | None = None,
    ) -> KGNode:
        """Add an entity node to the graph."""
        props = {}
        if domain:
            props["domain"] = domain
        if area:
            props["area"] = area
        node = KGNode(
            id=entity_id,
            type=NodeType.ENTITY,
            label=label or entity_id,
            properties=props,
        )
        return await self.create_node(node)

    # ==================== Edge Operations ====================

    async def list_edges(
        self,
        source: str | None = None,
        target: str | None = None,
        edge_type: EdgeType | None = None,
        limit: int = 100,
    ) -> list[KGEdge]:
        """List edges with optional filters."""
        params = {"limit": str(min(limit, 500))}
        if source:
            params["source"] = source
        if target:
            params["target"] = target
        if edge_type:
            params["type"] = edge_type.value
        data = await self._get(f"/api/v1/kg/edges?{self._encode_params(params)}")
        if not data.get("ok"):
            raise KnowledgeGraphError(data.get("error", "Unknown error"))
        return [KGEdge.from_dict(e) for e in data.get("edges", [])]

    async def create_edge(self, edge: KGEdge) -> KGEdge:
        """Create a new edge."""
        data = await self._post("/api/v1/kg/edges", edge.to_dict())
        if not data.get("ok"):
            raise KnowledgeGraphError(data.get("error", "Unknown error"))
        return KGEdge.from_dict(data.get("edge", {}))

    async def add_relationship(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        weight: float = 1.0,
        confidence: float = 0.0,
        evidence: dict | None = None,
    ) -> KGEdge:
        """Add a relationship between two nodes."""
        edge = KGEdge(
            source=source_id,
            target=target_id,
            type=edge_type,
            weight=weight,
            confidence=confidence,
            evidence=evidence or {},
        )
        return await self.create_edge(edge)

    # ==================== Query Operations ====================

    async def query(self, query: KGQuery) -> KGQueryResult:
        """Execute a graph query."""
        data = await self._post("/api/v1/kg/query", query.to_dict())
        if not data.get("ok"):
            raise KnowledgeGraphError(data.get("error", "Unknown error"))
        return KGQueryResult.from_dict(data.get("result", {}))

    async def find_related(
        self,
        entity_id: str,
        max_results: int = 10,
        min_confidence: float = 0.3,
    ) -> KGQueryResult:
        """Find entities related to a given entity."""
        query = KGQuery(
            query_type="structural",
            entity_id=entity_id,
            max_results=max_results,
            min_confidence=min_confidence,
        )
        return await self.query(query)

    async def find_by_mood(
        self,
        mood: str,
        max_results: int = 10,
    ) -> KGQueryResult:
        """Find patterns and entities related to a mood."""
        query = KGQuery(
            query_type="contextual",
            mood=mood,
            max_results=max_results,
        )
        return await self.query(query)

    async def find_by_zone(
        self,
        zone_id: str,
        max_results: int = 20,
    ) -> KGQueryResult:
        """Find entities and patterns for a zone."""
        query = KGQuery(
            query_type="structural",
            zone_id=zone_id,
            max_results=max_results,
        )
        return await self.query(query)

    async def find_triggers(
        self,
        entity_id: str,
        max_results: int = 10,
    ) -> KGQueryResult:
        """Find what triggers or is triggered by an entity."""
        query = KGQuery(
            query_type="causal",
            entity_id=entity_id,
            max_results=max_results,
        )
        return await self.query(query)

    # ==================== Import Operations ====================

    async def import_patterns_from_habitus(self, zone_id: str | None = None) -> dict:
        """Import Habitus patterns into the Knowledge Graph."""
        payload = {}
        if zone_id:
            payload["zone_id"] = zone_id
        data = await self._post("/api/v1/kg/import/patterns", payload)
        return data

    # ==================== Helpers ====================

    @staticmethod
    def _encode_params(params: dict) -> str:
        """Encode URL parameters."""
        import urllib.parse
        return urllib.parse.urlencode(params)


__all__ = [
    "NodeType",
    "EdgeType",
    "KGNode",
    "KGEdge",
    "KGStats",
    "KGQuery",
    "KGQueryResult",
    "KnowledgeGraphError",
    "KnowledgeGraphClient",
]