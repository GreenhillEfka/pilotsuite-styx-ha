"""
Brain Graph module for AI Home CoPilot.

Privacy-first, bounded graph of entities, zones, devices, and relationships
with automatic decay and salience-based pruning.

Submodules:
- model: GraphNode, GraphEdge data models
- store: Persistent graph storage (SQLite)
- service: High-level graph operations
- bridge: Bridge to Candidates Store for pattern extraction
- render: DOT/SVG graph rendering
"""

from .model import GraphNode, GraphEdge
from .service import BrainGraphService
from .store import GraphStore
from .bridge import GraphCandidatesBridge, CandidatePattern, PatternExtractionConfig

__all__ = [
    "GraphNode", 
    "GraphEdge", 
    "BrainGraphService", 
    "GraphStore",
    "GraphCandidatesBridge",
    "CandidatePattern",
    "PatternExtractionConfig"
]