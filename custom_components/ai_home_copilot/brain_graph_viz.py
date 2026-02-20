"""Brain graph visualization (minimal, local-only).

Generates a simple HTML/SVG file from the core graph state endpoint.

Privacy-first: node labels/ids are sanitized and clamped; no meta dumps.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from pathlib import Path
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant

from .privacy import sanitize_text


@dataclass
class _NodeViz:
    node_id: str
    label: str
    score: float
    x: float
    y: float


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


def _normalize_scores(nodes: list[dict[str, Any]]) -> list[float]:
    raw: list[float] = []
    for n in nodes:
        if not isinstance(n, dict):
            raw.append(0.0)
            continue
        # score field is best effort; keep minimal.
        raw.append(_safe_float(n.get("score"), 0.0))

    if not raw:
        return []

    lo = min(raw)
    hi = max(raw)
    if hi - lo < 1e-9:
        # all same -> mid emphasis
        return [0.5 for _ in raw]

    out: list[float] = []
    for v in raw:
        out.append((v - lo) / (hi - lo))
    return out


def _render_html(
    *,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    title: str,
) -> str:
    width = 1000
    height = 800
    cx = width / 2
    cy = height / 2
    radius = min(width, height) * 0.38

    scores = _normalize_scores(nodes)

    viz_nodes: list[_NodeViz] = []
    id_to_idx: dict[str, int] = {}

    for i, n in enumerate(nodes[:120]):
        if not isinstance(n, dict):
            continue
        raw_id = n.get("id")
        raw_label = n.get("label")

        nid = sanitize_text(raw_id, max_chars=80) or f"node_{i}"
        label = sanitize_text(raw_label, max_chars=60) or nid

        # circular layout
        a = (2 * math.pi * i) / max(1, min(len(nodes), 120))
        x = cx + radius * math.cos(a)
        y = cy + radius * math.sin(a)

        score = scores[i] if i < len(scores) else 0.5

        id_to_idx[nid] = len(viz_nodes)
        viz_nodes.append(_NodeViz(node_id=nid, label=label, score=score, x=x, y=y))

    # Build SVG primitives
    edge_lines: list[str] = []
    for e in edges[:240]:
        if not isinstance(e, dict):
            continue
        frm = sanitize_text(e.get("from"), max_chars=80)
        to = sanitize_text(e.get("to"), max_chars=80)
        if not frm or not to:
            continue
        if frm not in id_to_idx or to not in id_to_idx:
            continue
        n1 = viz_nodes[id_to_idx[frm]]
        n2 = viz_nodes[id_to_idx[to]]
        edge_lines.append(
            f'<line x1="{n1.x:.1f}" y1="{n1.y:.1f}" x2="{n2.x:.1f}" y2="{n2.y:.1f}" '
            'stroke="#89a" stroke-opacity="0.35" stroke-width="1" />'
        )

    node_circles: list[str] = []
    node_labels: list[str] = []
    for n in viz_nodes:
        r = 4.0 + 10.0 * max(0.0, min(1.0, n.score))
        op = 0.25 + 0.75 * max(0.0, min(1.0, n.score))
        node_circles.append(
            f'<circle cx="{n.x:.1f}" cy="{n.y:.1f}" r="{r:.1f}" '
            f'fill="#4aa3df" fill-opacity="{op:.3f}" stroke="#1b4d6b" stroke-width="1">'
            f"<title>{n.label}</title></circle>"
        )
        # keep labels subtle to avoid clutter
        node_labels.append(
            f'<text x="{n.x + r + 3:.1f}" y="{n.y + 4:.1f}" '
            'font-size="11" fill="#dde" fill-opacity="0.70" '
            'font-family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif">'
            f"{n.label}</text>"
        )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Minimal HTML wrapper; no external scripts.
    return "\n".join(
        [
            "<!doctype html>",
            "<html lang=\"en\">",
            "<head>",
            "  <meta charset=\"utf-8\" />",
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />",
            f"  <title>{sanitize_text(title, max_chars=120)}</title>",
            "  <style>",
            "    body { margin: 0; background: #0f1720; color: #e6eef6; }",
            "    header { padding: 12px 16px; border-bottom: 1px solid #263343; }",
            "    .meta { color: #9fb1c3; font-size: 13px; }",
            "    .wrap { padding: 8px 12px 18px; }",
            "    svg { width: 100%; height: auto; background: #0b121a; border: 1px solid #263343; border-radius: 8px; }",
            "  </style>",
            "</head>",
            "<body>",
            "  <header>",
            f"    <div><strong>{sanitize_text(title, max_chars=120)}</strong></div>",
            f"    <div class=\"meta\">Generated: {now} · Nodes: {len(viz_nodes)} · Edges: {len(edge_lines)}</div>",
            "  </header>",
            "  <div class=\"wrap\">",
            f"    <svg viewBox=\"0 0 {width} {height}\" role=\"img\" aria-label=\"Brain graph visualization\">",
            "      <rect x=\"0\" y=\"0\" width=\"100%\" height=\"100%\" fill=\"#0b121a\" />",
            "      <g>",
            *edge_lines,
            "      </g>",
            "      <g>",
            *node_circles,
            "      </g>",
            "      <g>",
            *node_labels,
            "      </g>",
            "    </svg>",
            "  </div>",
            "</body>",
            "</html>",
        ]
    )


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


async def async_publish_brain_graph_viz(hass: HomeAssistant, coordinator) -> Path | None:
    """Fetch graph state and publish a local HTML viz.

    Returns the written path on success, else None.
    """

    url = "/api/v1/graph/state?limitNodes=120&limitEdges=240"
    try:
        data = await coordinator.api.async_get(url)
    except Exception as err:  # noqa: BLE001
        persistent_notification.async_create(
            hass,
            f"Failed to fetch core graph state: {sanitize_text(err, max_chars=240)}",
            title="PilotSuite Brain graph viz",
            notification_id="ai_home_copilot_brain_graph_viz",
        )
        return None

    nodes = data.get("nodes") if isinstance(data, dict) else None
    edges = data.get("edges") if isinstance(data, dict) else None
    if not isinstance(nodes, list):
        nodes = []
    if not isinstance(edges, list):
        edges = []

    html = _render_html(
        nodes=nodes,
        edges=edges,
        title="PilotSuite brain graph (preview)",
    )

    latest_path = Path("/config/www/ai_home_copilot/brain_graph_latest.html")

    # No archive by default (avoid clutter). If you want history later,
    # we can add an opt-in archive option.
    await hass.async_add_executor_job(_write_text, latest_path, html)

    url_local = "/local/ai_home_copilot/brain_graph_latest.html"
    msg = "\n".join(
        [
            f"Brain graph visualization published: {url_local}",
            "",
            "Lovelace iframe card example:",
            "```yaml",
            "type: iframe",
            f"url: {url_local}",
            "aspect_ratio: 60%",
            "```",
        ]
    )

    persistent_notification.async_create(
        hass,
        msg,
        title="PilotSuite Brain graph viz",
        notification_id="ai_home_copilot_brain_graph_viz",
    )

    return latest_path
