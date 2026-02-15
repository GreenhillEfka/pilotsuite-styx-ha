#!/usr/bin/env python3
"""
Tests for brain graph storage layer.
"""

import time
import tempfile
import os
from copilot_core.brain_graph.model import GraphNode, GraphEdge
from copilot_core.brain_graph.store import GraphStore


def test_store_initialization():
    """Test store initialization with temporary database."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        store = GraphStore(db_path=db_path, max_nodes=10, max_edges=20)
        
        assert store.max_nodes == 10
        assert store.max_edges == 20
        assert os.path.exists(db_path)


def test_node_upsert_and_get():
    """Test node storage and retrieval."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        store = GraphStore(db_path=db_path)
        
        now_ms = int(time.time() * 1000)
        node = GraphNode(
            id="test:node1",
            kind="entity",
            label="Test Node",
            updated_at_ms=now_ms,
            score=2.5,
            domain="light",
            tags=["test"],
            meta={"key": "value"}
        )
        
        # Insert node
        success = store.upsert_node(node)
        assert success
        
        # Retrieve node
        retrieved = store.get_node("test:node1")
        assert retrieved is not None
        assert retrieved.id == "test:node1"
        assert retrieved.label == "Test Node"
        assert retrieved.score == 2.5
        assert retrieved.domain == "light"
        assert retrieved.tags == ["test"]
        assert retrieved.meta["key"] == "value"


def test_edge_upsert_and_get():
    """Test edge storage and retrieval."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        store = GraphStore(db_path=db_path)
        
        # First create nodes
        now_ms = int(time.time() * 1000)
        node1 = GraphNode(
            id="test:node1", kind="entity", label="Node 1",
            updated_at_ms=now_ms, score=1.0
        )
        node2 = GraphNode(
            id="test:node2", kind="entity", label="Node 2", 
            updated_at_ms=now_ms, score=1.0
        )
        
        store.upsert_node(node1)
        store.upsert_node(node2)
        
        # Create edge
        edge = GraphEdge(
            id="test_edge",
            from_node="test:node1",
            to_node="test:node2",
            edge_type="controls",
            updated_at_ms=now_ms,
            weight=1.5,
            evidence={"kind": "rule"},
            meta={"confidence": 0.8}
        )
        
        # Insert edge
        success = store.upsert_edge(edge)
        assert success
        
        # Retrieve edges
        edges = store.get_edges(from_node="test:node1")
        assert len(edges) == 1
        
        retrieved_edge = edges[0]
        assert retrieved_edge.from_node == "test:node1"
        assert retrieved_edge.to_node == "test:node2"
        assert retrieved_edge.edge_type == "controls"
        assert retrieved_edge.weight == 1.5


def test_node_filtering():
    """Test node filtering by kind and domain."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        store = GraphStore(db_path=db_path)
        
        now_ms = int(time.time() * 1000)
        
        # Create nodes of different kinds/domains
        nodes = [
            GraphNode("light:1", "entity", "Light 1", now_ms, 2.0, domain="light"),
            GraphNode("light:2", "entity", "Light 2", now_ms, 1.5, domain="light"),
            GraphNode("sensor:1", "entity", "Sensor 1", now_ms, 1.0, domain="sensor"),
            GraphNode("zone:kitchen", "zone", "Kitchen", now_ms, 3.0),
        ]
        
        for node in nodes:
            store.upsert_node(node)
        
        # Filter by kind
        entity_nodes = store.get_nodes(kinds=["entity"])
        assert len(entity_nodes) == 3
        
        zone_nodes = store.get_nodes(kinds=["zone"])
        assert len(zone_nodes) == 1
        
        # Filter by domain
        light_nodes = store.get_nodes(domains=["light"])
        assert len(light_nodes) == 2
        
        # Combined filter
        light_entities = store.get_nodes(kinds=["entity"], domains=["light"])
        assert len(light_entities) == 2


def test_neighborhood_query():
    """Test neighborhood querying."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        store = GraphStore(db_path=db_path)
        
        now_ms = int(time.time() * 1000)
        
        # Create a small graph: center -> node1, center -> node2, node2 -> node3
        nodes = [
            GraphNode("center", "entity", "Center", now_ms, 3.0),
            GraphNode("node1", "entity", "Node 1", now_ms, 2.0),
            GraphNode("node2", "entity", "Node 2", now_ms, 2.0),  
            GraphNode("node3", "entity", "Node 3", now_ms, 1.0),
        ]
        
        edges = [
            GraphEdge("e1", "center", "node1", "controls", now_ms, 1.0),
            GraphEdge("e2", "center", "node2", "controls", now_ms, 1.0),
            GraphEdge("e3", "node2", "node3", "affects", now_ms, 0.5),
        ]
        
        for node in nodes:
            store.upsert_node(node)
        for edge in edges:
            store.upsert_edge(edge)
        
        # 1-hop neighborhood
        nodes_1hop, edges_1hop = store.get_neighborhood("center", hops=1)
        node_ids = {n.id for n in nodes_1hop}
        assert "center" in node_ids
        assert "node1" in node_ids
        assert "node2" in node_ids
        assert "node3" not in node_ids  # Not directly connected
        assert len(edges_1hop) == 2
        
        # 2-hop neighborhood
        nodes_2hop, edges_2hop = store.get_neighborhood("center", hops=2)
        node_ids_2hop = {n.id for n in nodes_2hop}
        assert "node3" in node_ids_2hop  # Should be included now
        assert len(edges_2hop) == 3


def test_graph_pruning():
    """Test graph pruning based on salience."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        store = GraphStore(
            db_path=db_path,
            max_nodes=3,
            max_edges=2,
            node_min_score=0.5,
            edge_min_weight=0.3
        )
        
        now_ms = int(time.time() * 1000)
        old_ms = now_ms - (48 * 3600 * 1000)  # 48 hours ago
        
        # Create nodes with different scores and ages
        nodes = [
            GraphNode("high:1", "entity", "High Score", now_ms, 5.0),      # Keep (high recent)
            GraphNode("high:2", "entity", "High Old", old_ms, 5.0),        # Keep (high old -> decayed)
            GraphNode("med:1", "entity", "Medium", now_ms, 2.0),           # Keep (medium recent) 
            GraphNode("low:1", "entity", "Low Recent", now_ms, 0.1),       # Remove (too low)
            GraphNode("low:2", "entity", "Low Old", old_ms, 1.0),          # Remove (decayed + limit)
        ]
        
        # Create edges
        edges = [
            GraphEdge("e1", "high:1", "high:2", "correlates", now_ms, 1.0),  # Keep
            GraphEdge("e2", "med:1", "high:1", "affects", now_ms, 0.8),      # Keep  
            GraphEdge("e3", "low:1", "low:2", "correlates", old_ms, 0.2),    # Remove (weak)
            GraphEdge("e4", "low:2", "high:2", "mentions", now_ms, 0.5),     # Remove (capacity)
        ]
        
        # Insert all
        for node in nodes:
            store.upsert_node(node)
        for edge in edges:
            store.upsert_edge(edge)
        
        # Verify initial state
        stats_before = store.get_stats()
        assert stats_before["nodes"] == 5
        assert stats_before["edges"] == 4
        
        # Prune
        prune_stats = store.prune_graph(now_ms)
        
        # Check results
        stats_after = store.get_stats()
        assert stats_after["nodes"] <= 3  # Max nodes limit
        assert stats_after["edges"] <= 2  # Max edges limit
        
        # High-salience nodes should remain
        high_node = store.get_node("high:1")
        assert high_node is not None


def test_stats():
    """Test statistics reporting."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        store = GraphStore(db_path=db_path, max_nodes=100, max_edges=200)
        
        # Initially empty
        stats = store.get_stats()
        assert stats["nodes"] == 0
        assert stats["edges"] == 0
        assert stats["max_nodes"] == 100
        assert stats["max_edges"] == 200
        
        # Add some data
        now_ms = int(time.time() * 1000)
        store.upsert_node(GraphNode("n1", "entity", "Node 1", now_ms, 1.0))
        store.upsert_node(GraphNode("n2", "entity", "Node 2", now_ms, 1.0))
        store.upsert_edge(GraphEdge("e1", "n1", "n2", "controls", now_ms, 1.0))
        
        stats = store.get_stats()
        assert stats["nodes"] == 2
        assert stats["edges"] == 1


if __name__ == "__main__":
    print("Testing store initialization...")
    test_store_initialization()
    
    print("Testing node upsert/get...")
    test_node_upsert_and_get()
    
    print("Testing edge upsert/get...")
    test_edge_upsert_and_get()
    
    print("Testing node filtering...")
    test_node_filtering()
    
    print("Testing neighborhood queries...")
    test_neighborhood_query()
    
    print("Testing graph pruning...")
    test_graph_pruning()
    
    print("Testing statistics...")
    test_stats()
    
    print("✅ All brain graph store tests passed!")