/**
 * PilotSuite Habitus Card v2.0.0
 *
 * Lovelace custom card displaying discovered behavioral patterns
 * from sensor.pilotsuite_habitus_rules_count and its attributes.
 */

class StyxHabitusCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
  }

  static getConfigElement() {
    return document.createElement("hui-generic-entity-row");
  }

  static getStubConfig() {
    return { entity: "sensor.pilotsuite_habitus_rules_count", max_rules: 5 };
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("Please define an entity");
    }
    this._config = { max_rules: 5, ...config };
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 3;
  }

  _getRules() {
    if (!this._hass) return [];
    const state = this._hass.states[this._config.entity];
    if (!state) return [];

    const attrs = state.attributes || {};
    const rules = attrs.top_rules || attrs.rules || [];
    return rules.slice(0, this._config.max_rules);
  }

  _confidenceBadge(conf) {
    const pct = Math.round((conf || 0) * 100);
    let cls = "low";
    if (pct >= 80) cls = "high";
    else if (pct >= 50) cls = "mid";
    return `<span class="badge ${cls}">${pct}%</span>`;
  }

  _render() {
    const state = this._hass ? this._hass.states[this._config.entity] : null;
    const total = state ? parseInt(state.state, 10) || 0 : 0;
    const rules = this._getRules();

    let rulesHtml = "";
    if (rules.length === 0) {
      rulesHtml = `<div class="empty">No patterns discovered yet.</div>`;
    } else {
      rulesHtml = rules
        .map((r) => {
          const ante = r.A || r.antecedent || "?";
          const cons = r.B || r.consequent || "?";
          const conf = r.confidence || 0;
          return `
            <div class="rule">
              <div class="pair">
                <span class="ante">${this._esc(ante)}</span>
                <span class="arrow">\u2192</span>
                <span class="cons">${this._esc(cons)}</span>
              </div>
              ${this._confidenceBadge(conf)}
            </div>`;
        })
        .join("");
    }

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
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .title { font-size: 16px; font-weight: 600; }
        .count { font-size: 12px; color: var(--secondary-text-color, #9fb1c3); }
        .rule {
          display: flex; justify-content: space-between; align-items: center;
          padding: 8px 10px; margin-bottom: 6px;
          background: rgba(255,255,255,0.04); border-radius: 8px;
        }
        .pair { display: flex; align-items: center; gap: 6px; flex: 1; min-width: 0; }
        .ante, .cons {
          white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
          max-width: 140px; font-size: 13px;
        }
        .arrow { color: #4aa3df; font-size: 14px; flex-shrink: 0; }
        .badge {
          font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 10px;
          flex-shrink: 0; margin-left: 8px;
        }
        .badge.high { background: rgba(76,175,80,0.25); color: #81c784; }
        .badge.mid  { background: rgba(255,152,0,0.25); color: #ffb74d; }
        .badge.low  { background: rgba(244,67,54,0.25); color: #e57373; }
        .empty { font-size: 13px; color: var(--secondary-text-color, #9fb1c3); padding: 12px 0; text-align: center; }
      </style>
      <ha-card>
        <div class="card">
          <div class="header">
            <span class="title">Discovered Patterns</span>
            <span class="count">${total} rules</span>
          </div>
          ${rulesHtml}
        </div>
      </ha-card>`;
  }

  _esc(str) {
    const el = document.createElement("span");
    el.textContent = str;
    return el.innerHTML;
  }
}

customElements.define("styx-habitus-card", StyxHabitusCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "styx-habitus-card",
  name: "PilotSuite Habitus Patterns",
  description: "Shows discovered behavioral patterns with confidence badges.",
  preview: true,
});
