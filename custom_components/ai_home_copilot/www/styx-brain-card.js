/**
 * PilotSuite Brain Graph Card v2.0.0
 *
 * Lovelace custom card that renders a force-directed SVG brain graph
 * from sensor.pilotsuite_brain_graph_nodes / _edges.
 */

const DOMAIN_COLORS = {
  light: "#f9d71c",
  switch: "#4caf50",
  sensor: "#2196f3",
  binary_sensor: "#03a9f4",
  climate: "#ff9800",
  media_player: "#e91e63",
  cover: "#9c27b0",
  person: "#00bcd4",
  automation: "#ff5722",
  script: "#795548",
  device_tracker: "#607d8b",
  default: "#4aa3df",
};

class StyxBrainCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._nodes = [];
    this._edges = [];
  }

  static getConfigElement() {
    return document.createElement("hui-generic-entity-row");
  }

  static getStubConfig() {
    return { entity: "sensor.pilotsuite_brain_graph_nodes" };
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("Please define an entity");
    }
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
    const nodeEntity = hass.states[this._config.entity];
    const edgeEntityId =
      this._config.edge_entity || "sensor.pilotsuite_brain_graph_edges";
    const edgeEntity = hass.states[edgeEntityId];

    const nodes = nodeEntity
      ? nodeEntity.attributes.nodes || nodeEntity.attributes.graph_nodes || []
      : [];
    const edges = edgeEntity
      ? edgeEntity.attributes.edges || edgeEntity.attributes.graph_edges || []
      : [];

    if (
      JSON.stringify(nodes) !== JSON.stringify(this._nodes) ||
      JSON.stringify(edges) !== JSON.stringify(this._edges)
    ) {
      this._nodes = nodes;
      this._edges = edges;
      this._render();
    }
  }

  getCardSize() {
    return 5;
  }

  _colorForDomain(domain) {
    return DOMAIN_COLORS[domain] || DOMAIN_COLORS.default;
  }

  _layoutNodes(nodes, w, h) {
    const cx = w / 2;
    const cy = h / 2;
    const r = Math.min(w, h) * 0.38;
    const count = Math.max(1, nodes.length);
    return nodes.map((n, i) => {
      const angle = (2 * Math.PI * i) / count;
      const jitter = (Math.sin(i * 7) * r) / 10;
      return {
        ...n,
        x: cx + (r + jitter) * Math.cos(angle),
        y: cy + (r + jitter) * Math.sin(angle),
      };
    });
  }

  _render() {
    const w = 480;
    const h = 360;
    const positioned = this._layoutNodes(this._nodes.slice(0, 120), w, h);

    const idMap = {};
    positioned.forEach((n, i) => {
      idMap[n.id || n.node_id || `n${i}`] = n;
    });

    let edgeSvg = "";
    this._edges.slice(0, 240).forEach((e) => {
      const src = idMap[e.from || e.source_id];
      const tgt = idMap[e.to || e.target_id];
      if (src && tgt) {
        edgeSvg += `<line x1="${src.x}" y1="${src.y}" x2="${tgt.x}" y2="${tgt.y}"
          stroke="#89a" stroke-opacity="0.3" stroke-width="1"/>`;
      }
    });

    let nodeSvg = "";
    positioned.forEach((n) => {
      const score = Math.max(0, Math.min(1, n.score || 0.5));
      const radius = 4 + 8 * score;
      const domain = (n.domain || "default").split(".")[0];
      const fill = this._colorForDomain(domain);
      const label =
        (n.label || n.name || n.id || "").substring(0, 20);
      nodeSvg += `<circle cx="${n.x}" cy="${n.y}" r="${radius}"
        fill="${fill}" fill-opacity="${0.3 + 0.7 * score}" stroke="#1b4d6b" stroke-width="0.8">
        <title>${label}</title></circle>`;
      if (positioned.length <= 40) {
        nodeSvg += `<text x="${n.x + radius + 3}" y="${n.y + 3}"
          font-size="9" fill="#aab8c5" font-family="system-ui,sans-serif">${label}</text>`;
      }
    });

    const nodeCount = this._nodes.length;
    const edgeCount = this._edges.length;

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        .card {
          background: var(--card-background-color, #0a0e14);
          border-radius: var(--ha-card-border-radius, 12px);
          padding: 16px;
          color: var(--primary-text-color, #e6eef6);
          font-family: var(--paper-font-body1_-_font-family, system-ui, sans-serif);
        }
        .header {
          display: flex; justify-content: space-between; align-items: center;
          margin-bottom: 12px;
        }
        .title { font-size: 16px; font-weight: 600; }
        .meta { font-size: 12px; color: var(--secondary-text-color, #9fb1c3); }
        svg {
          width: 100%; height: auto;
          background: #0b121a; border: 1px solid #263343; border-radius: 8px;
        }
      </style>
      <ha-card>
        <div class="card">
          <div class="header">
            <span class="title">Brain Graph</span>
            <span class="meta">${nodeCount} nodes &middot; ${edgeCount} edges</span>
          </div>
          <svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Brain graph visualization">
            <rect x="0" y="0" width="${w}" height="${h}" fill="#0b121a"/>
            <g>${edgeSvg}</g>
            <g>${nodeSvg}</g>
          </svg>
        </div>
      </ha-card>`;
  }
}

customElements.define("styx-brain-card", StyxBrainCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "styx-brain-card",
  name: "PilotSuite Brain Graph",
  description: "Visualizes the PilotSuite knowledge brain graph with domain-colored nodes.",
  preview: true,
});
