"""Interactive Brain Graph Panel v0.8 with D3.js visualization.

Generates an interactive HTML/JS visualization from Core graph state.
Privacy-first: all data stays local; no external dependencies.

Version 0.8 (2026-02-16):
- Interactive D3.js visualization with zoom/pan
- Filter by Node Kind, Zone, or text search
- Click nodes for detailed info panel
- Color-coded node types (light, sensor, zone, media_player, etc.)
- Legend with all node kinds
- Stats display (node/edge counts)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import html
import json
import math
from pathlib import Path
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant

from .privacy import sanitize_text


@dataclass
class NodeViz:
    """Visualization node data."""
    node_id: str
    label: str
    kind: str
    domain: str | None
    zone: str | None
    score: float
    x: float
    y: float
    meta: dict[str, Any]


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except Exception:  # noqa: BLE001
        return default


def _safe_str(x: Any, max_chars: int = 80) -> str:
    if x is None:
        return ""
    s = str(x)
    return s[:max_chars]


def _normalize_scores(nodes: list[dict[str, Any]]) -> list[float]:
    raw: list[float] = []
    for n in nodes:
        if not isinstance(n, dict):
            raw.append(0.0)
            continue
        raw.append(_safe_float(n.get("score"), 0.0))

    if not raw:
        return []

    lo = min(raw)
    hi = max(raw)
    if hi - lo < 1e-9:
        return [0.5 for _ in raw]

    return [(v - lo) / (hi - lo) for v in raw]


# Color palette for node kinds
KIND_COLORS = {
    "entity": "#4aa3df",
    "device": "#6b8e23",
    "area": "#daa520",
    "zone": "#daa520",
    "service": "#e06666",
    "automation": "#9370db",
    "sensor": "#20b2aa",
    "binary_sensor": "#20b2aa",
    "light": "#ffd700",
    "switch": "#87ceeb",
    "climate": "#ff6b6b",
    "media_player": "#9b59b6",
    "person": "#ff9f43",
    "device_tracker": "#ff9f43",
    "default": "#8899aa",
}


def _get_kind_color(kind: str | None) -> str:
    if not kind:
        return KIND_COLORS["default"]
    return KIND_COLORS.get(kind.lower(), KIND_COLORS["default"])


def _render_interactive_html(
    *,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    title: str,
) -> str:
    """Generate interactive HTML with JavaScript for zoom/pan/filter."""
    
    width = 1200
    height = 900
    cx = width / 2
    cy = height / 2
    radius = min(width, height) * 0.38

    scores = _normalize_scores(nodes)

    viz_nodes: list[NodeViz] = []
    id_to_idx: dict[str, int] = {}

    # Process nodes
    for i, n in enumerate(nodes[:200]):
        if not isinstance(n, dict):
            continue
        
        raw_id = n.get("id")
        raw_label = n.get("label")
        kind = _safe_str(n.get("kind"), 30).lower() or "entity"
        domain = _safe_str(n.get("domain"), 30) or None
        zone = _safe_str(n.get("zone"), 30) or None
        
        nid = sanitize_text(raw_id, max_chars=80) or f"node_{i}"
        label = sanitize_text(raw_label, max_chars=60) or nid

        # Circular layout
        a = (2 * math.pi * i) / max(1, min(len(nodes), 200))
        x = cx + radius * math.cos(a)
        y = cy + radius * math.sin(a)

        score = scores[i] if i < len(scores) else 0.5
        
        # Extract safe meta
        meta = {}
        if isinstance(n.get("meta"), dict):
            for k, v in n.get("meta", {}).items():
                if k in ("updated_at", "source", "tags"):
                    meta[k] = v

        id_to_idx[nid] = len(viz_nodes)
        viz_nodes.append(NodeViz(
            node_id=nid,
            label=label,
            kind=kind,
            domain=domain,
            zone=zone,
            score=score,
            x=x,
            y=y,
            meta=meta,
        ))

    # Process edges
    edge_data: list[dict[str, Any]] = []
    for e in edges[:400]:
        if not isinstance(e, dict):
            continue
        frm = sanitize_text(e.get("from"), max_chars=80)
        to = sanitize_text(e.get("to"), max_chars=80)
        if not frm or not to:
            continue
        if frm not in id_to_idx or to not in id_to_idx:
            continue
        
        edge_data.append({
            "from": frm,
            "to": to,
            "type": _safe_str(e.get("type"), 20) or "relates_to",
            "weight": _safe_float(e.get("weight"), 0.5),
        })

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Prepare node data for JavaScript - sanitize all fields before JSON dump
    nodes_json = json.dumps([
        {
            "id": html.escape(sanitize_text(n.node_id, max_chars=80)),
            "label": html.escape(sanitize_text(n.label, max_chars=60)),
            "kind": html.escape(sanitize_text(n.kind, max_chars=30)),
            "domain": html.escape(sanitize_text(n.domain, max_chars=30)) if n.domain else None,
            "zone": html.escape(sanitize_text(n.zone, max_chars=30)) if n.zone else None,
            "score": round(n.score, 3),
            "x": round(n.x, 1),
            "y": round(n.y, 1),
            "color": _get_kind_color(n.kind),
        }
        for n in viz_nodes
    ], ensure_ascii=False)
    
    edges_json = json.dumps([
        {
            "from": html.escape(sanitize_text(e.get("from"), max_chars=80)),
            "to": html.escape(sanitize_text(e.get("to"), max_chars=80)),
            "type": html.escape(sanitize_text(e.get("type"), max_chars=30)) if e.get("type") else None,
            "weight": round(float(e.get("weight", 0)), 3) if e.get("weight") is not None else None,
        }
        for e in edge_data
    ], ensure_ascii=False)
    
    # Collect unique kinds/zones for filters
    kinds = sorted(set(n.kind for n in viz_nodes if n.kind))
    zones = sorted(set(n.zone for n in viz_nodes if n.zone))
    
    kinds_json = json.dumps(kinds)
    zones_json = json.dumps(zones)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{sanitize_text(title, max_chars=120)}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            padding: 0;
            background: #0f1720;
            color: #e6eef6;
            font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
            overflow: hidden;
        }}
        
        .container {{
            display: flex;
            height: 100vh;
            width: 100vw;
        }}
        
        .sidebar {{
            width: 280px;
            min-width: 280px;
            background: #151d28;
            border-right: 1px solid #263343;
            padding: 16px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}
        
        .main {{
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        
        header {{
            padding: 12px 16px;
            background: #151d28;
            border-bottom: 1px solid #263343;
        }}
        
        header h1 {{
            margin: 0 0 4px 0;
            font-size: 18px;
        }}
        
        .meta {{
            color: #9fb1c3;
            font-size: 13px;
        }}
        
        .graph-container {{
            flex: 1;
            overflow: hidden;
            position: relative;
            background: #0b121a;
        }}
        
        #graph-svg {{
            width: 100%;
            height: 100%;
            cursor: grab;
        }}
        
        #graph-svg.grabbing {{
            cursor: grabbing;
        }}
        
        .section {{
            background: #1a2433;
            border-radius: 8px;
            padding: 12px;
        }}
        
        .section h3 {{
            margin: 0 0 8px 0;
            font-size: 14px;
            color: #9fb1c3;
        }}
        
        .filter-group {{
            margin-bottom: 8px;
        }}
        
        .filter-group label {{
            display: block;
            font-size: 12px;
            margin-bottom: 4px;
            color: #8ba3b8;
        }}
        
        select, input[type="text"] {{
            width: 100%;
            padding: 8px;
            background: #0f1720;
            border: 1px solid #263343;
            border-radius: 4px;
            color: #e6eef6;
            font-size: 13px;
        }}
        
        select:focus, input:focus {{
            outline: none;
            border-color: #4aa3df;
        }}
        
        .btn {{
            padding: 8px 16px;
            background: #263343;
            border: 1px solid #364354;
            border-radius: 4px;
            color: #e6eef6;
            cursor: pointer;
            font-size: 13px;
            transition: background 0.2s;
        }}
        
        .btn:hover {{
            background: #364354;
        }}
        
        .btn.primary {{
            background: #4aa3df;
            border-color: #4aa3df;
        }}
        
        .btn.primary:hover {{
            background: #3d8bc7;
        }}
        
        .legend {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 6px;
            font-size: 11px;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        
        .legend-color {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
            font-size: 12px;
        }}
        
        .stat {{
            text-align: center;
            padding: 8px;
            background: #0f1720;
            border-radius: 4px;
        }}
        
        .stat-value {{
            font-size: 20px;
            font-weight: bold;
            color: #4aa3df;
        }}
        
        .stat-label {{
            color: #8ba3b8;
            font-size: 11px;
        }}
        
        .node-detail {{
            position: absolute;
            top: 16px;
            right: 16px;
            width: 260px;
            background: #151d28;
            border: 1px solid #263343;
            border-radius: 8px;
            padding: 16px;
            display: none;
            z-index: 100;
        }}
        
        .node-detail.visible {{
            display: block;
        }}
        
        .node-detail h4 {{
            margin: 0 0 12px 0;
            font-size: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .node-detail .close {{
            background: none;
            border: none;
            color: #8ba3b8;
            cursor: pointer;
            font-size: 18px;
            padding: 0;
        }}
        
        .node-detail .close:hover {{
            color: #e6eef6;
        }}
        
        .detail-row {{
            display: flex;
            justify-content: space-between;
            padding: 4px 0;
            font-size: 12px;
            border-bottom: 1px solid #1a2433;
        }}
        
        .detail-row:last-child {{
            border-bottom: none;
        }}
        
        .detail-label {{
            color: #8ba3b8;
        }}
        
        .detail-value {{
            color: #e6eef6;
        }}
        
        .controls {{
            position: absolute;
            bottom: 16px;
            left: 16px;
            display: flex;
            gap: 8px;
            z-index: 50;
        }}
        
        .zoom-info {{
            position: absolute;
            bottom: 16px;
            right: 16px;
            font-size: 12px;
            color: #8ba3b8;
            background: #151d28;
            padding: 4px 8px;
            border-radius: 4px;
        }}
        
        .edge {{
            stroke: #3a4a5a;
            stroke-opacity: 0.4;
            stroke-width: 1;
            transition: stroke-opacity 0.2s;
        }}
        
        .edge.highlighted {{
            stroke: #4aa3df;
            stroke-opacity: 0.8;
            stroke-width: 2;
        }}
        
        .node-circle {{
            stroke: #1b4d6b;
            stroke-width: 1;
            cursor: pointer;
            transition: stroke-width 0.2s, filter 0.2s;
        }}
        
        .node-circle:hover {{
            stroke-width: 2;
            filter: brightness(1.2);
        }}
        
        .node-circle.selected {{
            stroke: #ffd700;
            stroke-width: 3;
        }}
        
        .node-circle.filtered {{
            opacity: 0.2;
        }}
        
        .node-label {{
            font-size: 10px;
            fill: #9fb1c3;
            fill-opacity: 0.7;
            pointer-events: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <div class="section">
                <h3>📊 Stats</h3>
                <div class="stats">
                    <div class="stat">
                        <div class="stat-value" id="node-count">{len(viz_nodes)}</div>
                        <div class="stat-label">Nodes</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="edge-count">{len(edges)}</div>
                        <div class="stat-label">Edges</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h3>🔍 Filter</h3>
                <div class="filter-group">
                    <label>Node Kind</label>
                    <select id="filter-kind">
                        <option value="">All Kinds</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Zone</label>
                    <select id="filter-zone">
                        <option value="">All Zones</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Search</label>
                    <input type="text" id="filter-search" placeholder="Search nodes..." />
                </div>
                <button class="btn" onclick="resetFilters()">Reset Filters</button>
            </div>
            
            <div class="section">
                <h3>🎨 Legend (Node Kinds)</h3>
                <div class="legend" id="legend"></div>
            </div>
            
            <div class="section">
                <h3>⚡ Actions</h3>
                <button class="btn primary" onclick="refreshGraph()">Refresh</button>
            </div>
        </div>
        
        <div class="main">
            <header>
                <h1>🧠 Brain Graph</h1>
                <div class="meta">Generated: {now} · Interactive View</div>
            </header>
            
            <div class="graph-container">
                <svg id="graph-svg" viewBox="0 0 {width} {height}">
                    <defs>
                        <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
                            <polygon points="0 0, 10 3.5, 0 7" fill="#3a4a5a" />
                        </marker>
                    </defs>
                    <g id="edges-layer"></g>
                    <g id="nodes-layer"></g>
                    <g id="labels-layer"></g>
                </svg>
                
                <div class="controls">
                    <button class="btn" onclick="zoomIn()">+ Zoom</button>
                    <button class="btn" onclick="zoomOut()">- Zoom</button>
                    <button class="btn" onclick="resetView()">Reset View</button>
                </div>
                
                <div class="zoom-info" id="zoom-info">Zoom: 100%</div>
                
                <div class="node-detail" id="node-detail">
                    <h4>
                        <span id="detail-title">Node</span>
                        <button class="close" onclick="hideNodeDetail()">×</button>
                    </h4>
                    <div id="detail-content"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Graph data
        const nodes = {nodes_json};
        const edges = {edges_json};
        const kinds = {kinds_json};
        const zones = {zones_json};
        
        // State
        let selectedNode = null;
        let zoom = 1;
        let panX = 0;
        let panY = 0;
        let isDragging = false;
        let dragStart = {{ x: 0, y: 0 }};
        
        // SVG elements
        const svg = document.getElementById('graph-svg');
        const edgesLayer = document.getElementById('edges-layer');
        const nodesLayer = document.getElementById('nodes-layer');
        const labelsLayer = document.getElementById('labels-layer');
        
        // Initialize filters
        function initFilters() {{
            const kindSelect = document.getElementById('filter-kind');
            kinds.forEach(k => {{
                const opt = document.createElement('option');
                opt.value = k;
                opt.textContent = k;
                kindSelect.appendChild(opt);
            }});
            
            const zoneSelect = document.getElementById('filter-zone');
            zones.forEach(z => {{
                const opt = document.createElement('option');
                opt.value = z;
                opt.textContent = z;
                zoneSelect.appendChild(opt);
            }});
            
            // Build legend
            const legend = document.getElementById('legend');
            const colorMap = {{
                entity: '#4aa3df',
                device: '#6b8e23',
                area: '#daa520',
                zone: '#daa520',
                service: '#e06666',
                automation: '#9370db',
                sensor: '#20b2aa',
                binary_sensor: '#20b2aa',
                light: '#ffd700',
                switch: '#87ceeb',
                climate: '#ff6b6b',
                media_player: '#9b59b6',
                person: '#ff9f43',
                device_tracker: '#ff9f43',
            }};
            
            kinds.forEach(k => {{
                const item = document.createElement('div');
                item.className = 'legend-item';
                const color = document.createElement('div');
                color.className = 'legend-color';
                color.style.background = colorMap[k] || '#8899aa';
                const label = document.createElement('span');
                label.textContent = k;
                item.appendChild(color);
                item.appendChild(label);
                legend.appendChild(item);
            }});
        }}
        
        // Render graph
        function renderGraph() {{
            edgesLayer.innerHTML = '';
            nodesLayer.innerHTML = '';
            labelsLayer.innerHTML = '';
            
            const kindFilter = document.getElementById('filter-kind').value;
            const zoneFilter = document.getElementById('filter-zone').value;
            const searchFilter = document.getElementById('filter-search').value.toLowerCase();
            
            // Determine visible nodes
            const visibleNodes = new Set();
            nodes.forEach(n => {{
                const matchKind = !kindFilter || n.kind === kindFilter;
                const matchZone = !zoneFilter || n.zone === zoneFilter;
                const matchSearch = !searchFilter || 
                    n.label.toLowerCase().includes(searchFilter) ||
                    n.id.toLowerCase().includes(searchFilter);
                
                if (matchKind && matchZone && matchSearch) {{
                    visibleNodes.add(n.id);
                }}
            }});
            
            // Render edges
            edges.forEach(e => {{
                if (!visibleNodes.has(e.from) || !visibleNodes.has(e.to)) return;
                
                const n1 = nodes.find(n => n.id === e.from);
                const n2 = nodes.find(n => n.id === e.to);
                if (!n1 || !n2) return;
                
                const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                line.setAttribute('x1', n1.x);
                line.setAttribute('y1', n1.y);
                line.setAttribute('x2', n2.x);
                line.setAttribute('y2', n2.y);
                line.setAttribute('class', 'edge');
                line.setAttribute('data-from', e.from);
                line.setAttribute('data-to', e.to);
                edgesLayer.appendChild(line);
            }});
            
            // Render nodes
            nodes.forEach(n => {{
                const isVisible = visibleNodes.has(n.id);
                const r = 4 + 10 * n.score;
                
                const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                circle.setAttribute('cx', n.x);
                circle.setAttribute('cy', n.y);
                circle.setAttribute('r', r);
                circle.setAttribute('fill', n.color);
                circle.setAttribute('class', 'node-circle' + (isVisible ? '' : ' filtered'));
                circle.setAttribute('data-id', n.id);
                circle.addEventListener('click', () => showNodeDetail(n));
                nodesLayer.appendChild(circle);
                
                // Label (only for visible, high-score nodes)
                if (isVisible && n.score > 0.4) {{
                    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                    text.setAttribute('x', n.x + r + 3);
                    text.setAttribute('y', n.y + 4);
                    text.setAttribute('class', 'node-label');
                    text.textContent = n.label.substring(0, 20);
                    labelsLayer.appendChild(text);
                }}
            }});
            
            updateTransform();
        }}
        
        // Node detail panel
        function showNodeDetail(node) {{
            selectedNode = node;
            
            // Highlight selected node
            document.querySelectorAll('.node-circle').forEach(c => {{
                c.classList.remove('selected');
                if (c.getAttribute('data-id') === node.id) {{
                    c.classList.add('selected');
                }}
            }});
            
            // Highlight connected edges
            document.querySelectorAll('.edge').forEach(e => {{
                e.classList.remove('highlighted');
                if (e.getAttribute('data-from') === node.id || e.getAttribute('data-to') === node.id) {{
                    e.classList.add('highlighted');
                }}
            }});
            
            // Show detail panel
            const panel = document.getElementById('node-detail');
            document.getElementById('detail-title').textContent = node.label;
            
            const content = document.getElementById('detail-content');
            content.innerHTML = `
                <div class="detail-row">
                    <span class="detail-label">ID</span>
                    <span class="detail-value">${{node.id}}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Kind</span>
                    <span class="detail-value">${{node.kind}}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Domain</span>
                    <span class="detail-value">${{node.domain || '—'}}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Zone</span>
                    <span class="detail-value">${{node.zone || '—'}}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Score</span>
                    <span class="detail-value">${{(node.score * 100).toFixed(1)}}%</span>
                </div>
            `;
            
            panel.classList.add('visible');
        }}
        
        function hideNodeDetail() {{
            selectedNode = null;
            document.getElementById('node-detail').classList.remove('visible');
            document.querySelectorAll('.node-circle').forEach(c => c.classList.remove('selected'));
            document.querySelectorAll('.edge').forEach(e => e.classList.remove('highlighted'));
        }}
        
        // Zoom & Pan
        function updateTransform() {{
            const transform = `translate(${{panX}}px, ${{panY}}px) scale(${{zoom}})`;
            edgesLayer.style.transform = transform;
            nodesLayer.style.transform = transform;
            labelsLayer.style.transform = transform;
            document.getElementById('zoom-info').textContent = `Zoom: ${{Math.round(zoom * 100)}}%`;
        }}
        
        function zoomIn() {{
            zoom = Math.min(3, zoom * 1.2);
            updateTransform();
        }}
        
        function zoomOut() {{
            zoom = Math.max(0.3, zoom / 1.2);
            updateTransform();
        }}
        
        function resetView() {{
            zoom = 1;
            panX = 0;
            panY = 0;
            updateTransform();
        }}
        
        // Pan with mouse drag
        svg.addEventListener('mousedown', (e) => {{
            if (e.target.tagName === 'circle') return;
            isDragging = true;
            dragStart = {{ x: e.clientX - panX, y: e.clientY - panY }};
            svg.classList.add('grabbing');
        }});
        
        document.addEventListener('mousemove', (e) => {{
            if (!isDragging) return;
            panX = e.clientX - dragStart.x;
            panY = e.clientY - dragStart.y;
            updateTransform();
        }});
        
        document.addEventListener('mouseup', () => {{
            isDragging = false;
            svg.classList.remove('grabbing');
        }});
        
        // Zoom with wheel
        svg.addEventListener('wheel', (e) => {{
            e.preventDefault();
            if (e.deltaY < 0) {{
                zoom = Math.min(3, zoom * 1.1);
            }} else {{
                zoom = Math.max(0.3, zoom / 1.1);
            }}
            updateTransform();
        }});
        
        // Filters
        function resetFilters() {{
            document.getElementById('filter-kind').value = '';
            document.getElementById('filter-zone').value = '';
            document.getElementById('filter-search').value = '';
            renderGraph();
        }}
        
        document.getElementById('filter-kind').addEventListener('change', renderGraph);
        document.getElementById('filter-zone').addEventListener('change', renderGraph);
        document.getElementById('filter-search').addEventListener('input', renderGraph);
        
        // Refresh (reload page)
        function refreshGraph() {{
            location.reload();
        }}
        
        // Initialize
        initFilters();
        renderGraph();
    </script>
</body>
</html>'''


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


async def async_publish_brain_graph_panel(hass: HomeAssistant, coordinator) -> Path | None:
    """Fetch graph state and publish an interactive HTML panel.

    Returns the written path on success, else None.
    """
    url = "/api/v1/graph/state?limitNodes=200&limitEdges=400"
    try:
        data = await coordinator.api.async_get(url)
    except Exception as err:  # noqa: BLE001
        persistent_notification.async_create(
            hass,
            f"Failed to fetch core graph state: {sanitize_text(err, max_chars=240)}",
            title="AI Home CoPilot Brain Graph Panel",
            notification_id="ai_home_copilot_brain_graph_panel",
        )
        return None

    nodes = data.get("nodes") if isinstance(data, dict) else None
    edges = data.get("edges") if isinstance(data, dict) else None
    if not isinstance(nodes, list):
        nodes = []
    if not isinstance(edges, list):
        edges = []

    html = _render_interactive_html(
        nodes=nodes,
        edges=edges,
        title="AI Home CoPilot Brain Graph",
    )

    panel_path = Path("/config/www/ai_home_copilot/brain_graph_panel.html")
    await hass.async_add_executor_job(_write_text, panel_path, html)

    url_local = "/local/ai_home_copilot/brain_graph_panel.html"
    msg = "\n".join([
        f"Interactive Brain Graph Panel: {url_local}",
        "",
        "Features:",
        "• Zoom/Pan (mouse wheel + drag)",
        "• Filter by Node Kind, Zone, or Search",
        "• Click nodes for details",
        "",
        "Lovelace iframe card:",
        "```yaml",
        "type: iframe",
        f"url: {url_local}",
        "aspect_ratio: 75%",
        "```",
    ])

    persistent_notification.async_create(
        hass,
        msg,
        title="AI Home CoPilot Brain Graph Panel",
        notification_id="ai_home_copilot_brain_graph_panel",
    )

    return panel_path