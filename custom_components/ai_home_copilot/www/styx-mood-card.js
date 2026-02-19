/**
 * PilotSuite Mood Card v2.0.0
 *
 * Lovelace custom card showing circular gauges for Comfort, Joy, and
 * Frugality per zone, reading from sensor.pilotsuite_mood_* entities.
 */

const MOOD_GAUGE_DEFS = [
  { key: "comfort", label: "Comfort", start: "#2196f3", end: "#4caf50" },
  { key: "joy", label: "Joy", start: "#ff9800", end: "#f9d71c" },
  { key: "frugality", label: "Frugality", start: "#9c27b0", end: "#00bcd4" },
];

class StyxMoodCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
  }

  static getConfigElement() {
    return document.createElement("hui-generic-entity-row");
  }

  static getStubConfig() {
    return { entity: "sensor.pilotsuite_mood_comfort" };
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("Please define an entity");
    }
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 3;
  }

  _gaugeValue(entityId) {
    if (!this._hass) return 0;
    const state = this._hass.states[entityId];
    if (!state) return 0;
    const val = parseFloat(state.state);
    return isNaN(val) ? 0 : Math.max(0, Math.min(100, val));
  }

  _buildGaugeSvg(value, startColor, endColor, label) {
    const size = 100;
    const cx = size / 2;
    const cy = size / 2;
    const r = 38;
    const circumference = 2 * Math.PI * r;
    const pct = Math.max(0, Math.min(100, value));
    const offset = circumference - (circumference * pct) / 100;
    const gradId = `g_${label.toLowerCase()}`;

    return `
      <svg viewBox="0 0 ${size} ${size}" class="gauge">
        <defs>
          <linearGradient id="${gradId}" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="${startColor}"/>
            <stop offset="100%" stop-color="${endColor}"/>
          </linearGradient>
        </defs>
        <circle cx="${cx}" cy="${cy}" r="${r}"
          fill="none" stroke="#1e2a36" stroke-width="7"/>
        <circle cx="${cx}" cy="${cy}" r="${r}"
          fill="none" stroke="url(#${gradId})" stroke-width="7"
          stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"
          stroke-linecap="round" transform="rotate(-90 ${cx} ${cy})"
          style="transition: stroke-dashoffset 0.6s ease;"/>
        <text x="${cx}" y="${cy - 4}" text-anchor="middle"
          fill="var(--primary-text-color, #e6eef6)" font-size="16" font-weight="700"
          font-family="system-ui,sans-serif">${Math.round(pct)}%</text>
        <text x="${cx}" y="${cy + 12}" text-anchor="middle"
          fill="var(--secondary-text-color, #9fb1c3)" font-size="10"
          font-family="system-ui,sans-serif">${label}</text>
      </svg>`;
  }

  _render() {
    const baseEntity = this._config.entity || "sensor.pilotsuite_mood_comfort";
    const prefix = baseEntity.replace(/_comfort$/, "").replace(/_joy$/, "").replace(/_frugality$/, "");

    const gauges = MOOD_GAUGE_DEFS.map((def) => {
      const entityId = `${prefix}_${def.key}`;
      const value = this._gaugeValue(entityId);
      return this._buildGaugeSvg(value, def.start, def.end, def.label);
    }).join("");

    const zone = this._config.zone || "";
    const title = zone ? `Mood \u2013 ${zone}` : "Mood";

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
        .title { font-size: 16px; font-weight: 600; margin-bottom: 12px; }
        .gauges { display: flex; justify-content: space-around; gap: 8px; }
        .gauge { width: 110px; height: 110px; }
      </style>
      <ha-card>
        <div class="card">
          <div class="title">${title}</div>
          <div class="gauges">${gauges}</div>
        </div>
      </ha-card>`;
  }
}

customElements.define("styx-mood-card", StyxMoodCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "styx-mood-card",
  name: "PilotSuite Mood Gauges",
  description: "Circular gauges for Comfort, Joy, and Frugality mood dimensions.",
  preview: true,
});
