#!/usr/bin/env python3
"""
Tests for brain graph service layer.
"""

import time
import tempfile
import os
from copilot_core.brain_graph.service import BrainGraphService
from copilot_core.brain_graph.store import GraphStore


def test_service_initialization():
    """Test service initialization with custom store."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        store = GraphStore(db_path=db_path)
        service = BrainGraphService(store=store)
        
        assert service.store == store
        assert service.node_half_life_hours == 24.0
        assert service.edge_half_life_hours == 12.0


def test_touch_node_new():
    """Test creating a new node via touch_node."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        store = GraphStore(db_path=db_path)
        service = BrainGraphService(store=store)
        
        # Touch new node
        node = service.touch_node(
            node_id="test:new",
            label="New Node",
            kind="entity",
            domain="light",
            delta=2.0,
            meta_patch={"brightness": 80}
        )
        
        assert node.id == "test:new"
        assert node.label == "New Node"
        assert node.kind == "entity"
        assert node.domain == "light"
        assert node.score == 2.0
        assert node.meta["brightness"] == 80
        
        # Verify it's stored
        stored_node = store.get_node("test:new")
        assert stored_node is not None
        assert stored_node.score == 2.0


def test_touch_node_update():
    """Test updating existing node via touch_node."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        store = GraphStore(db_path=db_path)
        service = BrainGraphService(store=store)
        
        # Create initial node
        node1 = service.touch_node(
            node_id="test:update",
            label="Original",
            kind="entity",
            delta=1.0,
            meta_patch={"key1": "value1"}
        )
        
        original_time = node1.updated_at_ms
        time.sleep(0.01)  # Ensure time difference
        
        # Update node
        node2 = service.touch_node(
            node_id="test:update",
            label="Updated",
            delta=1.5,
            meta_patch={"key2": "value2"}
        )
        
        assert node2.label == "Updated"
        assert node2.updated_at_ms > original_time
        assert node2.score > 1.0  # Should include decay + delta
        assert node2.meta["key1"] == "value1"  # Original meta preserved
        assert node2.meta["key2"] == "value2"  # New meta added


def test_touch_edge_new():
    """Test creating a new edge via touch_edge."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        store = GraphStore(db_path=db_path)
        service = BrainGraphService(store=store)
        
        # Create nodes first (edges need existing nodes)
        service.touch_node("node1", label="Node 1", kind="entity", delta=1.0)
        service.touch_node("node2", label="Node 2", kind="entity", delta=1.0)
        
        # Create edge
        edge = service.touch_edge(
            from_node="node1",
            edge_type="controls",
            to_node="node2",
            delta=2.0,
            evidence={"kind": "rule", "ref": "test_rule"},
            meta_patch={"confidence": 0.9}
        )
        
        assert edge.from_node == "node1"
        assert edge.to_node == "node2"
        assert edge.edge_type == "controls"
        assert edge.weight == 2.0
        assert edge.evidence["kind"] == "rule"
        assert edge.meta["confidence"] == 0.9


def test_link_shortcut():
    """Test the link shortcut method."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        store = GraphStore(db_path=db_path)
        service = BrainGraphService(store=store)
        
        # Create nodes
        service.touch_node("node1", label="Node 1", kind="entity", delta=1.0)
        service.touch_node("node2", label="Node 2", kind="entity", delta=1.0)
        
        # Link nodes
        edge = service.link(
            from_node="node1",
            edge_type="affects",
            to_node="node2",
            initial_weight=1.5,
            evidence={"kind": "observation"}
        )
        
        assert edge.weight == 1.5
        assert edge.evidence["kind"] == "observation"
        
        # Verify stored
        edges = store.get_edges(from_node="node1")
        assert len(edges) == 1


def test_get_graph_state_basic():
    """Test basic graph state retrieval."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        store = GraphStore(db_path=db_path)
        service = BrainGraphService(store=store)
        
        # Create test graph
        service.touch_node("light:1", label="Light 1", kind="entity", domain="light", delta=2.0)
        service.touch_node("sensor:1", label="Sensor 1", kind="entity", domain="sensor", delta=1.5)
        service.touch_node("kitchen", label="Kitchen", kind="zone", delta=3.0)
        
        service.link("light:1", "in_zone", "kitchen")
        service.link("sensor:1", "in_zone", "kitchen")
        
        # Get full state
        state = service.get_graph_state()
        
        assert state["version"] == 1
        assert "generated_at_ms" in state
        assert "limits" in state
        
        nodes = state["nodes"]
        edges = state["edges"]
        
        assert len(nodes) == 3
        assert len(edges) == 2
        
        # Check node data
        light_node = next(n for n in nodes if n["id"] == "light:1")
        assert light_node["kind"] == "entity"
        assert light_node["domain"] == "light"
        assert light_node["score"] >= 1.9  # Allow for minimal decay


def test_get_graph_state_filtered():
    """Test filtered graph state retrieval."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        store = GraphStore(db_path=db_path)
        service = BrainGraphService(store=store)
        
        # Create diverse graph
        service.touch_node("light:1", label="Light 1", kind="entity", domain="light", delta=2.0)
        service.touch_node("light:2", label="Light 2", kind="entity", domain="light", delta=1.0)
        service.touch_node("sensor:1", label="Sensor 1", kind="entity", domain="sensor", delta=1.5)
        service.touch_node("kitchen", label="Kitchen", kind="zone", delta=3.0)
        
        # Filter by kind
        entity_state = service.get_graph_state(kinds=["entity"])
        assert len(entity_state["nodes"]) == 3
        
        zone_state = service.get_graph_state(kinds=["zone"])
        assert len(zone_state["nodes"]) == 1
        
        # Filter by domain
        light_state = service.get_graph_state(domains=["light"])
        assert len(light_state["nodes"]) == 2


def test_get_graph_state_neighborhood():
    """Test neighborhood-based graph state retrieval."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        store = GraphStore(db_path=db_path)
        service = BrainGraphService(store=store)
        
        # Create graph: center -> node1, center -> node2, node2 -> node3
        service.touch_node("center", label="Center", kind="entity", delta=3.0)
        service.touch_node("node1", label="Node 1", kind="entity", delta=2.0)
        service.touch_node("node2", label="Node 2", kind="entity", delta=2.0)
        service.touch_node("node3", label="Node 3", kind="entity", delta=1.0)
        service.touch_node("isolated", label="Isolated", kind="entity", delta=1.0)
        
        service.link("center", "controls", "node1")
        service.link("center", "controls", "node2")
        service.link("node2", "affects", "node3")
        
        # 1-hop neighborhood from center
        state_1hop = service.get_graph_state(center_node="center", hops=1)
        node_ids = {n["id"] for n in state_1hop["nodes"]}
        
        assert "center" in node_ids
        assert "node1" in node_ids  
        assert "node2" in node_ids
        assert "node3" not in node_ids  # 2 hops away
        assert "isolated" not in node_ids  # Not connected
        
        # 2-hop neighborhood from center
        state_2hop = service.get_graph_state(center_node="center", hops=2)
        node_ids_2hop = {n["id"] for n in state_2hop["nodes"]}
        
        assert "node3" in node_ids_2hop
        assert "isolated" not in node_ids_2hop


def test_get_stats():
    """Test statistics retrieval."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        store = GraphStore(db_path=db_path, max_nodes=100, max_edges=200)
        service = BrainGraphService(
            store=store,
            node_half_life_hours=20.0,
            edge_half_life_hours=10.0
        )
        
        stats = service.get_stats()
        
        assert stats["nodes"] == 0
        assert stats["edges"] == 0
        assert stats["max_nodes"] == 100
        assert stats["max_edges"] == 200
        assert stats["config"]["node_half_life_hours"] == 20.0
        assert stats["config"]["edge_half_life_hours"] == 10.0


def test_ha_state_change_processing():
    """Test processing Home Assistant state change events."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        store = GraphStore(db_path=db_path)
        service = BrainGraphService(store=store)
        
        # Mock state change event
        event_data = {
            "event_type": "state_changed",
            "data": {
                "entity_id": "light.kitchen_main",
                "new_state": {"state": "on"},
                "old_state": {"state": "off"}
            }
        }
        
        # Process event
        service.process_ha_event(event_data)
        
        # Check that entity node was created
        node = store.get_node("ha.entity:light.kitchen_main")
        assert node is not None
        assert node.kind == "entity"
        assert node.domain == "light"
        assert "Kitchen Main" in node.label  # Title-cased from entity_id


def test_ha_service_call_processing():
    """Test processing Home Assistant service call events."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        store = GraphStore(db_path=db_path)
        service = BrainGraphService(store=store)
        
        # Mock service call event
        event_data = {
            "event_type": "call_service", 
            "data": {
                "domain": "light",
                "service": "turn_on",
                "service_data": {
                    "entity_id": ["light.kitchen", "light.living_room"]
                }
            }
        }
        
        # Process event
        service.process_ha_event(event_data)
        
        # Check that service node was created
        service_node = store.get_node("ha.service:light.turn_on")
        assert service_node is not None
        assert service_node.kind == "concept"
        assert "Light Turn On" in service_node.label
        
        # Check that affects edges were created
        edges = store.get_edges(from_node="ha.service:light.turn_on")
        assert len(edges) == 2
        
        edge_targets = {edge.to_node for edge in edges}
        assert "ha.entity:light.kitchen" in edge_targets
        assert "ha.entity:light.living_room" in edge_targets


if __name__ == "__main__":
    print("Testing service initialization...")
    test_service_initialization()
    
    print("Testing touch_node (new)...")
    test_touch_node_new()
    
    print("Testing touch_node (update)...")
    test_touch_node_update()
    
    print("Testing touch_edge (new)...")
    test_touch_edge_new()
    
    print("Testing link shortcut...")
    test_link_shortcut()
    
    print("Testing get_graph_state (basic)...")
    test_get_graph_state_basic()
    
    print("Testing get_graph_state (filtered)...")
    test_get_graph_state_filtered()
    
    print("Testing get_graph_state (neighborhood)...")
    test_get_graph_state_neighborhood()
    
    print("Testing get_stats...")
    test_get_stats()
    
    print("Testing HA state change processing...")
    test_ha_state_change_processing()
    
    print("Testing HA service call processing...")
    test_ha_service_call_processing()
    
    print("✅ All brain graph service tests passed!")