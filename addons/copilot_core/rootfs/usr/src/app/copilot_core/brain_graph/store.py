"""
SQLite-based graph storage with bounded capacity and automatic pruning.
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .model import GraphNode, GraphEdge, NodeKind, EdgeType


class GraphStore:
    """SQLite-backed graph storage with bounded capacity."""
    
    def __init__(
        self,
        db_path: str = "/data/brain_graph.db",
        max_nodes: int = 500,
        max_edges: int = 1500,
        node_min_score: float = 0.1,
        edge_min_weight: float = 0.1
    ):
        self.db_path = Path(db_path)
        self.max_nodes = max_nodes
        self.max_edges = max_edges  
        self.node_min_score = node_min_score
        self.edge_min_weight = edge_min_weight
        
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    label TEXT NOT NULL,
                    updated_at_ms INTEGER NOT NULL,
                    score REAL NOT NULL,
                    domain TEXT,
                    source_json TEXT,
                    tags_json TEXT,
                    meta_json TEXT
                );
                
                CREATE TABLE IF NOT EXISTS edges (
                    id TEXT PRIMARY KEY,
                    from_node TEXT NOT NULL,
                    to_node TEXT NOT NULL,
                    edge_type TEXT NOT NULL,
                    updated_at_ms INTEGER NOT NULL,
                    weight REAL NOT NULL,
                    evidence_json TEXT,
                    meta_json TEXT,
                    FOREIGN KEY (from_node) REFERENCES nodes (id) ON DELETE CASCADE,
                    FOREIGN KEY (to_node) REFERENCES nodes (id) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_nodes_kind ON nodes (kind);
                CREATE INDEX IF NOT EXISTS idx_nodes_domain ON nodes (domain);
                CREATE INDEX IF NOT EXISTS idx_nodes_updated ON nodes (updated_at_ms);
                CREATE INDEX IF NOT EXISTS idx_nodes_score ON nodes (score);
                
                CREATE INDEX IF NOT EXISTS idx_edges_from ON edges (from_node);
                CREATE INDEX IF NOT EXISTS idx_edges_to ON edges (to_node);
                CREATE INDEX IF NOT EXISTS idx_edges_type ON edges (edge_type);
                CREATE INDEX IF NOT EXISTS idx_edges_updated ON edges (updated_at_ms);
                CREATE INDEX IF NOT EXISTS idx_edges_weight ON edges (weight);
            """)
    
    def upsert_node(self, node: GraphNode) -> bool:
        """Insert or update a node. Returns True if inserted/updated."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT OR REPLACE INTO nodes 
                (id, kind, label, updated_at_ms, score, domain, source_json, tags_json, meta_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    node.id,
                    node.kind,
                    node.label,
                    node.updated_at_ms,
                    node.score,
                    node.domain,
                    json.dumps(node.source) if node.source else None,
                    json.dumps(node.tags) if node.tags else None,
                    json.dumps(node.meta) if node.meta else None,
                )
            )
            
            return cursor.rowcount > 0
    
    def upsert_edge(self, edge: GraphEdge) -> bool:
        """Insert or update an edge. Returns True if inserted/updated."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT OR REPLACE INTO edges
                (id, from_node, to_node, edge_type, updated_at_ms, weight, evidence_json, meta_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    edge.id,
                    edge.from_node,
                    edge.to_node,
                    edge.edge_type,
                    edge.updated_at_ms,
                    edge.weight,
                    json.dumps(edge.evidence) if edge.evidence else None,
                    json.dumps(edge.meta) if edge.meta else None,
                )
            )
            
            return cursor.rowcount > 0
    
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Retrieve a node by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            return GraphNode(
                id=row["id"],
                kind=row["kind"],
                label=row["label"],
                updated_at_ms=row["updated_at_ms"],
                score=row["score"],
                domain=row["domain"],
                source=json.loads(row["source_json"]) if row["source_json"] else None,
                tags=json.loads(row["tags_json"]) if row["tags_json"] else None,
                meta=json.loads(row["meta_json"]) if row["meta_json"] else {},
            )
    
    def get_nodes(
        self,
        kinds: Optional[List[NodeKind]] = None,
        domains: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[GraphNode]:
        """Retrieve nodes with optional filtering."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM nodes WHERE 1=1"
            params = []
            
            if kinds:
                placeholders = ",".join("?" * len(kinds))
                query += f" AND kind IN ({placeholders})"
                params.extend(kinds)
                
            if domains:
                placeholders = ",".join("?" * len(domains))
                query += f" AND domain IN ({placeholders})"
                params.extend(domains)
                
            query += " ORDER BY score DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [
                GraphNode(
                    id=row["id"],
                    kind=row["kind"],
                    label=row["label"],
                    updated_at_ms=row["updated_at_ms"],
                    score=row["score"],
                    domain=row["domain"],
                    source=json.loads(row["source_json"]) if row["source_json"] else None,
                    tags=json.loads(row["tags_json"]) if row["tags_json"] else None,
                    meta=json.loads(row["meta_json"]) if row["meta_json"] else {},
                )
                for row in rows
            ]
    
    def get_edges(
        self,
        from_node: Optional[str] = None,
        to_node: Optional[str] = None,
        edge_types: Optional[List[EdgeType]] = None,
        limit: Optional[int] = None
    ) -> List[GraphEdge]:
        """Retrieve edges with optional filtering."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM edges WHERE 1=1"
            params = []
            
            if from_node:
                query += " AND from_node = ?"
                params.append(from_node)
                
            if to_node:
                query += " AND to_node = ?"
                params.append(to_node)
                
            if edge_types:
                placeholders = ",".join("?" * len(edge_types))
                query += f" AND edge_type IN ({placeholders})"
                params.extend(edge_types)
                
            query += " ORDER BY weight DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [
                GraphEdge(
                    id=row["id"],
                    from_node=row["from_node"],
                    to_node=row["to_node"],
                    edge_type=row["edge_type"],
                    updated_at_ms=row["updated_at_ms"],
                    weight=row["weight"],
                    evidence=json.loads(row["evidence_json"]) if row["evidence_json"] else None,
                    meta=json.loads(row["meta_json"]) if row["meta_json"] else {},
                )
                for row in rows
            ]
    
    def get_neighborhood(
        self, 
        center_node: str, 
        hops: int = 1,
        max_nodes: Optional[int] = None,
        max_edges: Optional[int] = None
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """Get nodes and edges within N hops of a center node."""
        visited_nodes: Set[str] = {center_node}
        current_layer = {center_node}
        
        # Expand outward for specified hops
        for _ in range(hops):
            next_layer = set()
            
            # Find all edges from current layer
            for node_id in current_layer:
                outbound_edges = self.get_edges(from_node=node_id)
                inbound_edges = self.get_edges(to_node=node_id)
                
                for edge in outbound_edges + inbound_edges:
                    neighbor = edge.to_node if edge.from_node == node_id else edge.from_node
                    if neighbor not in visited_nodes:
                        next_layer.add(neighbor)
                        
            visited_nodes.update(next_layer)
            current_layer = next_layer
            
            if not next_layer:
                break
        
        # Get all nodes in neighborhood
        nodes = []
        for node_id in visited_nodes:
            node = self.get_node(node_id)
            if node:
                nodes.append(node)
        
        # Apply limits by salience/recency
        if max_nodes and len(nodes) > max_nodes:
            nodes = sorted(nodes, key=lambda n: n.effective_score(), reverse=True)[:max_nodes]
            visited_nodes = {n.id for n in nodes}
        
        # Get edges between nodes in neighborhood
        edges = []
        for node_id in visited_nodes:
            node_edges = self.get_edges(from_node=node_id)
            for edge in node_edges:
                if edge.to_node in visited_nodes and edge not in edges:
                    edges.append(edge)
        
        if max_edges and len(edges) > max_edges:
            edges = sorted(edges, key=lambda e: e.effective_weight(), reverse=True)[:max_edges]
        
        return nodes, edges
    
    def prune_graph(self, now_ms: Optional[int] = None) -> Dict[str, int]:
        """Remove low-salience nodes/edges and enforce capacity limits."""
        if now_ms is None:
            now_ms = int(time.time() * 1000)
            
        stats = {"nodes_removed": 0, "edges_removed": 0}
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # First pass: Remove edges with very low effective weight
            cursor.execute("SELECT * FROM edges")
            weak_edge_ids = []
            
            for row in cursor.fetchall():
                edge = GraphEdge(
                    id=row[0],
                    from_node=row[1], 
                    to_node=row[2],
                    edge_type=row[3],
                    updated_at_ms=row[4],
                    weight=row[5],
                    evidence=json.loads(row[6]) if row[6] else None,
                    meta=json.loads(row[7]) if row[7] else {},
                )
                
                if edge.effective_weight(now_ms) < self.edge_min_weight:
                    weak_edge_ids.append(edge.id)
            
            if weak_edge_ids:
                placeholders = ",".join("?" * len(weak_edge_ids))
                cursor.execute(f"DELETE FROM edges WHERE id IN ({placeholders})", weak_edge_ids)
                stats["edges_removed"] += cursor.rowcount
            
            # Second pass: Enforce edge limit by keeping top edges by effective weight
            cursor.execute("SELECT COUNT(*) FROM edges")
            edge_count = cursor.fetchone()[0]
            
            if edge_count > self.max_edges:
                # Calculate effective weights and keep top N
                cursor.execute("SELECT * FROM edges")
                edges_with_weights = []
                
                for row in cursor.fetchall():
                    edge = GraphEdge(
                        id=row[0],
                        from_node=row[1],
                        to_node=row[2], 
                        edge_type=row[3],
                        updated_at_ms=row[4],
                        weight=row[5],
                        evidence=json.loads(row[6]) if row[6] else None,
                        meta=json.loads(row[7]) if row[7] else {},
                    )
                    effective_weight = edge.effective_weight(now_ms)
                    edges_with_weights.append((edge.id, effective_weight, edge.updated_at_ms))
                
                # Sort by weight desc, then recency desc for ties
                edges_with_weights.sort(key=lambda x: (x[1], x[2]), reverse=True)
                
                # Keep top N, remove the rest
                edges_to_remove = [edge_id for edge_id, _, _ in edges_with_weights[self.max_edges:]]
                
                if edges_to_remove:
                    placeholders = ",".join("?" * len(edges_to_remove))
                    cursor.execute(f"DELETE FROM edges WHERE id IN ({placeholders})", edges_to_remove)
                    stats["edges_removed"] += cursor.rowcount
            
            # Third pass: Remove nodes with low effective score and no edges
            cursor.execute("SELECT * FROM nodes")
            weak_node_ids = []
            
            for row in cursor.fetchall():
                node = GraphNode(
                    id=row[0],
                    kind=row[1],
                    label=row[2], 
                    updated_at_ms=row[3],
                    score=row[4],
                    domain=row[5],
                    source=json.loads(row[6]) if row[6] else None,
                    tags=json.loads(row[7]) if row[7] else None,
                    meta=json.loads(row[8]) if row[8] else {},
                )
                
                if node.effective_score(now_ms) < self.node_min_score:
                    # Check if node has any remaining edges
                    cursor.execute(
                        "SELECT COUNT(*) FROM edges WHERE from_node = ? OR to_node = ?",
                        (node.id, node.id)
                    )
                    edge_count = cursor.fetchone()[0]
                    
                    if edge_count == 0:
                        weak_node_ids.append(node.id)
            
            if weak_node_ids:
                placeholders = ",".join("?" * len(weak_node_ids))
                cursor.execute(f"DELETE FROM nodes WHERE id IN ({placeholders})", weak_node_ids)
                stats["nodes_removed"] += cursor.rowcount
            
            # Fourth pass: Enforce node limit by keeping top nodes by effective score
            cursor.execute("SELECT COUNT(*) FROM nodes")
            node_count = cursor.fetchone()[0]
            
            if node_count > self.max_nodes:
                # Calculate effective scores and keep top N
                cursor.execute("SELECT * FROM nodes")
                nodes_with_scores = []
                
                for row in cursor.fetchall():
                    node = GraphNode(
                        id=row[0],
                        kind=row[1],
                        label=row[2],
                        updated_at_ms=row[3], 
                        score=row[4],
                        domain=row[5],
                        source=json.loads(row[6]) if row[6] else None,
                        tags=json.loads(row[7]) if row[7] else None,
                        meta=json.loads(row[8]) if row[8] else {},
                    )
                    effective_score = node.effective_score(now_ms)
                    nodes_with_scores.append((node.id, effective_score, node.updated_at_ms))
                
                # Sort by score desc, then recency desc for ties
                nodes_with_scores.sort(key=lambda x: (x[1], x[2]), reverse=True)
                
                # Keep top N, remove the rest (and their edges)
                nodes_to_remove = [node_id for node_id, _, _ in nodes_with_scores[self.max_nodes:]]
                
                if nodes_to_remove:
                    placeholders = ",".join("?" * len(nodes_to_remove))
                    # Remove associated edges first
                    cursor.execute(f"DELETE FROM edges WHERE from_node IN ({placeholders}) OR to_node IN ({placeholders})", nodes_to_remove * 2)
                    # Remove nodes
                    cursor.execute(f"DELETE FROM nodes WHERE id IN ({placeholders})", nodes_to_remove)
                    stats["nodes_removed"] += cursor.rowcount
            
            conn.commit()
        
        return stats
    
    def get_stats(self) -> Dict[str, int]:
        """Get current graph statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM nodes")
            node_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM edges") 
            edge_count = cursor.fetchone()[0]
            
            return {
                "nodes": node_count,
                "edges": edge_count,
                "max_nodes": self.max_nodes,
                "max_edges": self.max_edges,
            }