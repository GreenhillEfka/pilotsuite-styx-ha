"""Tests for Knowledge Graph API client."""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.knowledge_graph import (
    NodeType,
    EdgeType,
    KGNode,
    KGEdge,
    KGStats,
    KGQuery,
    KGQueryResult,
    KnowledgeGraphError,
    KnowledgeGraphClient,
)


class TestKGModels(unittest.TestCase):
    """Test data models."""

    def test_node_type_values(self):
        """Test NodeType enum values."""
        self.assertEqual(NodeType.ENTITY.value, "entity")
        self.assertEqual(NodeType.DOMAIN.value, "domain")
        self.assertEqual(NodeType.AREA.value, "area")
        self.assertEqual(NodeType.ZONE.value, "zone")
        self.assertEqual(NodeType.PATTERN.value, "pattern")
        self.assertEqual(NodeType.MOOD.value, "mood")
        self.assertEqual(NodeType.CAPABILITY.value, "cap")
        self.assertEqual(NodeType.TAG.value, "tag")
        self.assertEqual(NodeType.TIME_CONTEXT.value, "time")
        self.assertEqual(NodeType.USER.value, "user")

    def test_edge_type_values(self):
        """Test EdgeType enum values."""
        self.assertEqual(EdgeType.BELONGS_TO.value, "belongs_to")
        self.assertEqual(EdgeType.HAS_CAPABILITY.value, "has_cap")
        self.assertEqual(EdgeType.HAS_TAG.value, "has_tag")
        self.assertEqual(EdgeType.TRIGGERS.value, "triggers")
        self.assertEqual(EdgeType.CORRELATES_WITH.value, "correlates")
        self.assertEqual(EdgeType.ACTIVE_DURING.value, "active_during")
        self.assertEqual(EdgeType.RELATES_TO_MOOD.value, "relates_mood")
        self.assertEqual(EdgeType.PREFERRED_BY.value, "preferred_by")
        self.assertEqual(EdgeType.AVOIDED_BY.value, "avoided_by")

    def test_node_creation(self):
        """Test creating a node."""
        node = KGNode(
            id="light.kitchen",
            type=NodeType.ENTITY,
            label="Kitchen Light",
            properties={"domain": "light"},
        )
        self.assertEqual(node.id, "light.kitchen")
        self.assertEqual(node.type, NodeType.ENTITY)
        self.assertEqual(node.label, "Kitchen Light")
        self.assertIn("domain", node.properties)

    def test_node_to_dict(self):
        """Test node serialization."""
        node = KGNode(
            id="mood.relax",
            type=NodeType.MOOD,
            label="Relaxation",
        )
        data = node.to_dict()
        self.assertEqual(data["id"], "mood.relax")
        self.assertEqual(data["type"], "mood")
        self.assertEqual(data["label"], "Relaxation")

    def test_node_from_dict(self):
        """Test node deserialization."""
        data = {
            "id": "zone.west",
            "type": "zone",
            "label": "West Wing",
            "properties": {"entities": 5},
        }
        node = KGNode.from_dict(data)
        self.assertEqual(node.id, "zone.west")
        self.assertEqual(node.type, NodeType.ZONE)
        self.assertEqual(node.label, "West Wing")
        self.assertEqual(node.properties.get("entities"), 5)

    def test_edge_creation(self):
        """Test creating an edge."""
        edge = KGEdge(
            source="light.kitchen",
            target="area.kitchen",
            type=EdgeType.BELONGS_TO,
            weight=1.0,
            confidence=0.9,
        )
        self.assertEqual(edge.source, "light.kitchen")
        self.assertEqual(edge.target, "area.kitchen")
        self.assertEqual(edge.type, EdgeType.BELONGS_TO)
        self.assertEqual(edge.weight, 1.0)
        self.assertEqual(edge.confidence, 0.9)

    def test_edge_id(self):
        """Test edge ID generation."""
        edge = KGEdge(
            source="light.living",
            target="mood.relax",
            type=EdgeType.RELATES_TO_MOOD,
        )
        self.assertEqual(edge.id, "light.living:relates_mood:mood.relax")

    def test_edge_to_dict(self):
        """Test edge serialization."""
        edge = KGEdge(
            source="pattern.p1",
            target="light.kitchen",
            type=EdgeType.TRIGGERS,
            confidence=0.8,
            evidence={"count": 10, "success": 9},
        )
        data = edge.to_dict()
        self.assertEqual(data["source"], "pattern.p1")
        self.assertEqual(data["type"], "triggers")
        self.assertEqual(data["confidence"], 0.8)
        self.assertIn("count", data["evidence"])

    def test_edge_from_dict(self):
        """Test edge deserialization."""
        data = {
            "source": "sensor.motion",
            "target": "light.hallway",
            "type": "triggers",
            "weight": 0.9,
            "confidence": 0.7,
            "source_type": "learned",
        }
        edge = KGEdge.from_dict(data)
        self.assertEqual(edge.source, "sensor.motion")
        self.assertEqual(edge.target, "light.hallway")
        self.assertEqual(edge.type, EdgeType.TRIGGERS)
        self.assertEqual(edge.weight, 0.9)
        self.assertEqual(edge.confidence, 0.7)
        self.assertEqual(edge.source_type, "learned")

    def test_kg_stats_from_dict(self):
        """Test KGStats deserialization."""
        data = {
            "node_count": 100,
            "edge_count": 250,
            "nodes_by_type": {"entity": 50, "zone": 10},
            "edges_by_type": {"belongs_to": 100, "triggers": 50},
        }
        stats = KGStats.from_dict(data)
        self.assertEqual(stats.node_count, 100)
        self.assertEqual(stats.edge_count, 250)
        self.assertEqual(stats.nodes_by_type["entity"], 50)
        self.assertEqual(stats.edges_by_type["triggers"], 50)

    def test_kg_query_to_dict(self):
        """Test KGQuery serialization."""
        query = KGQuery(
            query_type="causal",
            entity_id="light.kitchen",
            max_results=5,
            min_confidence=0.6,
        )
        data = query.to_dict()
        self.assertEqual(data["query_type"], "causal")
        self.assertEqual(data["entity_id"], "light.kitchen")
        self.assertEqual(data["max_results"], 5)
        self.assertEqual(data["min_confidence"], 0.6)

    def test_kg_query_result_from_dict(self):
        """Test KGQueryResult deserialization."""
        data = {
            "nodes": [
                {"id": "light.kitchen", "type": "entity", "label": "Kitchen Light"},
                {"id": "mood.relax", "type": "mood", "label": "Relaxation"},
            ],
            "edges": [
                {
                    "source": "light.kitchen",
                    "target": "mood.relax",
                    "type": "relates_mood",
                }
            ],
            "confidence": 0.85,
            "sources": ["habitus", "manual"],
        }
        result = KGQueryResult.from_dict(data)
        self.assertEqual(len(result.nodes), 2)
        self.assertEqual(len(result.edges), 1)
        self.assertEqual(result.confidence, 0.85)
        self.assertEqual(result.sources, ["habitus", "manual"])
        self.assertEqual(result.nodes[0].id, "light.kitchen")
        self.assertEqual(result.edges[0].type, EdgeType.RELATES_TO_MOOD)


class TestKnowledgeGraphClient(unittest.TestCase):
    """Test Knowledge Graph client."""

    def setUp(self):
        """Set up test fixtures."""
        self.session = MagicMock()
        self.base_url = "http://localhost:8099"
        self.token = "test-token"
        self.client = KnowledgeGraphClient(self.session, self.base_url, self.token)

    def test_headers_with_token(self):
        """Test headers include auth token."""
        headers = self.client._headers()
        self.assertIn("Authorization", headers)

    def test_headers_without_token(self):
        """Test headers without auth token."""
        client = KnowledgeGraphClient(self.session, self.base_url, None)
        headers = client._headers()
        self.assertNotIn("Authorization", headers)

    def test_encode_params(self):
        """Test URL parameter encoding."""
        params = {"limit": "10", "type": "entity"}
        encoded = KnowledgeGraphClient._encode_params(params)
        self.assertIn("limit=10", encoded)
        self.assertIn("type=entity", encoded)

    @patch("aiohttp.ClientSession.get")
    async def test_get_stats(self, mock_get):
        """Test get_stats method."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "ok": True,
            "stats": {
                "node_count": 50,
                "edge_count": 120,
            }
        })
        mock_get.return_value.__aenter__.return_value = mock_response

        # Need to create a real session for async
        import aiohttp
        async with aiohttp.ClientSession() as session:
            client = KnowledgeGraphClient(session, self.base_url, self.token)
            stats = await client.get_stats()
            self.assertEqual(stats.node_count, 50)
            self.assertEqual(stats.edge_count, 120)

    @patch("aiohttp.ClientSession.get")
    async def test_list_nodes(self, mock_get):
        """Test list_nodes method."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "ok": True,
            "nodes": [
                {"id": "light.kitchen", "type": "entity", "label": "Kitchen"},
            ],
            "count": 1,
        })
        mock_get.return_value.__aenter__.return_value = mock_response

        import aiohttp
        async with aiohttp.ClientSession() as session:
            client = KnowledgeGraphClient(session, self.base_url, self.token)
            nodes = await client.list_nodes(NodeType.ENTITY, limit=10)
            self.assertEqual(len(nodes), 1)
            self.assertEqual(nodes[0].id, "light.kitchen")

    @patch("aiohttp.ClientSession.post")
    async def test_create_node(self, mock_post):
        """Test create_node method."""
        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.json = AsyncMock(return_value={
            "ok": True,
            "node": {
                "id": "light.test",
                "type": "entity",
                "label": "Test Light",
            }
        })
        mock_post.return_value.__aenter__.return_value = mock_response

        import aiohttp
        async with aiohttp.ClientSession() as session:
            client = KnowledgeGraphClient(session, self.base_url, self.token)
            node = KGNode(
                id="light.test",
                type=NodeType.ENTITY,
                label="Test Light",
            )
            created = await client.create_node(node)
            self.assertEqual(created.id, "light.test")

    @patch("aiohttp.ClientSession.post")
    async def test_add_relationship(self, mock_post):
        """Test add_relationship method."""
        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.json = AsyncMock(return_value={
            "ok": True,
            "edge": {
                "source": "light.test",
                "target": "area.living",
                "type": "belongs_to",
                "weight": 1.0,
            }
        })
        mock_post.return_value.__aenter__.return_value = mock_response

        import aiohttp
        async with aiohttp.ClientSession() as session:
            client = KnowledgeGraphClient(session, self.base_url, self.token)
            edge = await client.add_relationship(
                "light.test",
                "area.living",
                EdgeType.BELONGS_TO,
            )
            self.assertEqual(edge.source, "light.test")
            self.assertEqual(edge.target, "area.living")

    @patch("aiohttp.ClientSession.post")
    async def test_query(self, mock_post):
        """Test query method."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "ok": True,
            "result": {
                "nodes": [],
                "edges": [],
                "confidence": 0.0,
            }
        })
        mock_post.return_value.__aenter__.return_value = mock_response

        import aiohttp
        async with aiohttp.ClientSession() as session:
            client = KnowledgeGraphClient(session, self.base_url, self.token)
            query = KGQuery(query_type="structural", entity_id="light.test")
            result = await client.query(query)
            self.assertEqual(result.confidence, 0.0)


class TestKnowledgeGraphError(unittest.TestCase):
    """Test error handling."""

    def test_error_message(self):
        """Test error message."""
        error = KnowledgeGraphError("Something went wrong")
        self.assertEqual(str(error), "Something went wrong")


if __name__ == "__main__":
    unittest.main()