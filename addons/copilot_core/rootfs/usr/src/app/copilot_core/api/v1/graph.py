from __future__ import annotations

from flask import Blueprint, current_app, jsonify, make_response, request

from copilot_core.brain_graph.service import BrainGraphService
from copilot_core.brain_graph.store import BrainGraphStore

bp = Blueprint("graph", __name__, url_prefix="/graph")

_STORE: BrainGraphStore | None = None
_SVC: BrainGraphService | None = None


def _svc() -> BrainGraphService:
    global _STORE, _SVC
    if _SVC is not None:
        return _SVC

    cfg = current_app.config.get("COPILOT_CFG")
    data_dir = str(getattr(cfg, "data_dir", "/data"))
    json_path = str(getattr(cfg, "brain_graph_json_path", f"{data_dir}/brain_graph.json"))
    persist = bool(getattr(cfg, "brain_graph_persist", True))

    _STORE = BrainGraphStore(json_path=json_path, persist=persist)
    _SVC = BrainGraphService(
        _STORE,
        nodes_max=int(getattr(cfg, "brain_graph_nodes_max", 500)),
        edges_max=int(getattr(cfg, "brain_graph_edges_max", 1500)),
    )
    return _SVC


@bp.get("/state")
def graph_state():
    # Multi-value query params: kind=...&kind=...
    kinds = request.args.getlist("kind")
    domains = request.args.getlist("domain")
    center = request.args.get("center")

    try:
        hops = int(request.args.get("hops", "1"))
    except Exception:
        hops = 1

    try:
        limit_nodes = int(request.args.get("limitNodes", request.args.get("limit_nodes", "200")))
    except Exception:
        limit_nodes = 200

    try:
        limit_edges = int(request.args.get("limitEdges", request.args.get("limit_edges", "400")))
    except Exception:
        limit_edges = 400

    # Server-side caps: tighter than storage maxima by default.
    limit_nodes = max(1, min(limit_nodes, 500))
    limit_edges = max(1, min(limit_edges, 1500))
    hops = max(0, min(hops, 2))

    state = _svc().export_state(
        kind=kinds,
        domain=domains,
        center=center,
        hops=hops,
        limit_nodes=limit_nodes,
        limit_edges=limit_edges,
    )
    return jsonify(state)


@bp.get("/snapshot.svg")
def graph_snapshot_svg():
    # v0.1: keep lightweight. Returning a placeholder (or 501) is acceptable.
    svg = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"640\" height=\"120\">\n"
        "  <rect x=\"0\" y=\"0\" width=\"100%\" height=\"100%\" fill=\"#111\"/>\n"
        "  <text x=\"20\" y=\"55\" fill=\"#eee\" font-family=\"monospace\" font-size=\"16\">"
        "Brain Graph snapshot.svg not implemented (v0.1 placeholder)"
        "</text>\n"
        "  <text x=\"20\" y=\"85\" fill=\"#aaa\" font-family=\"monospace\" font-size=\"12\">"
        "Use /api/v1/graph/state for JSON."
        "</text>\n"
        "</svg>\n"
    )
    resp = make_response(svg, 200)
    resp.headers["Content-Type"] = "image/svg+xml; charset=utf-8"
    return resp
