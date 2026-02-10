"""
Brain Graph API endpoints.
"""

import time
from flask import Blueprint, request, jsonify, Response
from typing import Dict, Any

from .service import BrainGraphService
from .render import GraphRenderer
from ..api.security import require_api_key

# Create blueprint
brain_graph_bp = Blueprint('brain_graph', __name__, url_prefix='/api/v1/graph')

# Global service instance (will be initialized in main.py)
_brain_graph_service: BrainGraphService = None
_graph_renderer: GraphRenderer = None

def init_brain_graph_api(service: BrainGraphService, renderer: GraphRenderer = None):
    """Initialize the brain graph API with service instances."""
    global _brain_graph_service, _graph_renderer
    _brain_graph_service = service
    _graph_renderer = renderer or GraphRenderer()

@brain_graph_bp.route('/state', methods=['GET'])
@require_api_key
def get_graph_state() -> Response:
    """
    Get current graph state as JSON.
    
    Query parameters:
    - kind: filter by node kind (repeatable)
    - domain: filter by domain (repeatable)  
    - center: center node for neighborhood query
    - hops: number of hops for neighborhood (default 1)
    - limitNodes: max nodes to return
    - limitEdges: max edges to return
    """
    if not _brain_graph_service:
        return jsonify({"error": "Brain graph service not initialized"}), 503
    
    try:
        # Parse query parameters
        kinds = request.args.getlist('kind')
        domains = request.args.getlist('domain')
        center = request.args.get('center')
        hops = int(request.args.get('hops', 1))
        limit_nodes = _parse_int_param('limitNodes', default=None, max_value=500)
        limit_edges = _parse_int_param('limitEdges', default=None, max_value=1500)
        
        # Validate parameters
        if hops < 1 or hops > 3:
            return jsonify({"error": "hops must be between 1 and 3"}), 400
        
        valid_kinds = ['entity', 'zone', 'device', 'person', 'concept', 'module', 'event']
        for kind in kinds:
            if kind not in valid_kinds:
                return jsonify({"error": f"Invalid kind: {kind}"}), 400
        
        # Get graph state
        state = _brain_graph_service.get_graph_state(
            kinds=kinds or None,
            domains=domains or None,
            center_node=center,
            hops=hops,
            limit_nodes=limit_nodes,
            limit_edges=limit_edges
        )
        
        return jsonify(state)
        
    except ValueError as e:
        return jsonify({"error": f"Invalid parameter: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Internal error: {str(e)}"}), 500

@brain_graph_bp.route('/snapshot.svg', methods=['GET'])
@require_api_key
def get_graph_snapshot() -> Response:
    """
    Get graph visualization as SVG.
    
    Query parameters:
    - Same as /state plus:
    - layout: dot, neato, fdp (default dot)
    - theme: light, dark (default light)
    - label: short, full (default short)
    """
    if not _brain_graph_service or not _graph_renderer:
        error_svg = '''<?xml version="1.0"?>
<svg width="400" height="200" xmlns="http://www.w3.org/2000/svg">
    <text x="200" y="100" text-anchor="middle" fill="red">Service unavailable</text>
</svg>'''
        return Response(error_svg, mimetype='image/svg+xml'), 503
    
    try:
        # Parse visualization parameters
        layout = request.args.get('layout', 'dot')
        theme = request.args.get('theme', 'light') 
        label_style = request.args.get('label', 'short')
        
        # Parse same filter parameters as /state
        kinds = request.args.getlist('kind')
        domains = request.args.getlist('domain')
        center = request.args.get('center')
        hops = int(request.args.get('hops', 1))
        limit_nodes = _parse_int_param('limitNodes', default=120, max_value=120)  # Enforce render limits
        limit_edges = _parse_int_param('limitEdges', default=300, max_value=300)
        
        # Validate parameters
        if layout not in ['dot', 'neato', 'fdp', 'circo', 'twopi']:
            layout = 'dot'
        if theme not in ['light', 'dark']:
            theme = 'light'
        if label_style not in ['short', 'full']:
            label_style = 'short'
        if hops < 1 or hops > 3:
            hops = 1
        
        # Get graph state
        state = _brain_graph_service.get_graph_state(
            kinds=kinds or None,
            domains=domains or None,
            center_node=center,
            hops=hops,
            limit_nodes=limit_nodes,
            limit_edges=limit_edges
        )
        
        # Render as SVG
        svg_bytes = _graph_renderer.render_svg(
            graph_state=state,
            layout=layout,
            theme=theme,
            label_style=label_style
        )
        
        return Response(svg_bytes, mimetype='image/svg+xml')
        
    except Exception as e:
        error_svg = f'''<?xml version="1.0"?>
<svg width="400" height="200" xmlns="http://www.w3.org/2000/svg">
    <text x="200" y="80" text-anchor="middle" fill="red">Render Error</text>
    <text x="200" y="120" text-anchor="middle" font-size="12" fill="#666">{str(e)[:50]}</text>
</svg>'''
        return Response(error_svg, mimetype='image/svg+xml'), 500

@brain_graph_bp.route('/stats', methods=['GET'])
@require_api_key 
def get_graph_stats() -> Response:
    """Get brain graph statistics."""
    if not _brain_graph_service:
        return jsonify({"error": "Brain graph service not initialized"}), 503
    
    try:
        stats = _brain_graph_service.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": f"Internal error: {str(e)}"}), 500

@brain_graph_bp.route('/prune', methods=['POST'])
@require_api_key
def prune_graph() -> Response:
    """Manually trigger graph pruning."""
    if not _brain_graph_service:
        return jsonify({"error": "Brain graph service not initialized"}), 503
    
    try:
        stats = _brain_graph_service.prune_now()
        return jsonify({
            "message": "Graph pruned successfully",
            "stats": stats
        })
    except Exception as e:
        return jsonify({"error": f"Internal error: {str(e)}"}), 500

@brain_graph_bp.route('/patterns', methods=['GET'])
@require_api_key
def get_patterns() -> Response:
    """Get inferred patterns from the graph."""
    if not _brain_graph_service:
        return jsonify({"error": "Brain graph service not initialized"}), 503
    
    try:
        patterns = _brain_graph_service.infer_patterns()
        return jsonify({
            "version": 1,
            "generated_at_ms": int(time.time() * 1000),
            "patterns": patterns
        })
    except Exception as e:
        return jsonify({"error": f"Internal error: {str(e)}"}), 500

def _parse_int_param(param_name: str, default: int = None, max_value: int = None) -> int:
    """Parse integer parameter with validation."""
    value = request.args.get(param_name)
    
    if value is None:
        return default
    
    try:
        parsed = int(value)
        if parsed < 1:
            raise ValueError(f"{param_name} must be positive")
        if max_value and parsed > max_value:
            parsed = max_value
        return parsed
    except ValueError:
        raise ValueError(f"{param_name} must be a valid positive integer")