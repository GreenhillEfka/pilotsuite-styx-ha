"""Home Alerts Dashboard Card - PilotSuite

Lovelace card for displaying home alerts and health score.

Usage in Lovelace:
  type: custom:home-alerts-card
  title: Handlungsbedarf
  show_health_score: true
  categories:
    - battery
    - climate
    - presence
    - system
"""

from __future__ import annotations

import logging
from typing import Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

CARD_VERSION = "0.1.0"


def get_alerts_for_dashboard(hass: HomeAssistant, entry_id: str) -> dict:
    """Get alerts data for dashboard rendering.
    
    Returns a dict with:
    - alerts: list of alert dicts
    - health_score: int 0-100
    - counts: dict of category -> count
    - last_scan: ISO timestamp
    """
    from ..core.modules.home_alerts_module import get_home_alerts_module
    
    module = get_home_alerts_module(hass, entry_id)
    if not module:
        return {
            "alerts": [],
            "health_score": 100,
            "counts": {"battery": 0, "climate": 0, "presence": 0, "system": 0},
            "last_scan": None
        }
    
    state = module.get_state()
    
    alerts_data = []
    for alert in module.get_alerts():
        alerts_data.append({
            "alert_id": alert.alert_id,
            "category": alert.category,
            "severity": alert.severity,
            "title": alert.title,
            "message": alert.message,
            "entity_id": alert.entity_id,
            "value": alert.value,
            "target": alert.target,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
            "acknowledged": alert.acknowledged,
            "actions": alert.actions
        })
    
    return {
        "alerts": alerts_data,
        "health_score": state.health_score,
        "counts": state.alerts_by_category,
        "last_scan": state.last_scan.isoformat() if state.last_scan else None
    }


class HomeAlertsData:
    """Data class for home alerts card state."""
    
    def __init__(self, hass: HomeAssistant, config: dict):
        self._hass = hass
        self._config = config
        self._entry_id = config.get("entry_id")
        self._categories = config.get("categories", ["battery", "climate", "presence", "system"])
        self._show_health_score = config.get("show_health_score", True)
        self._max_alerts = config.get("max_alerts", 10)
    
    @property
    def alerts(self) -> list[dict]:
        """Get current alerts."""
        data = get_alerts_for_dashboard(self._hass, self._entry_id)
        alerts = data.get("alerts", [])
        
        # Filter by categories
        if self._categories:
            alerts = [a for a in alerts if a["category"] in self._categories]
        
        # Limit count
        return alerts[:self._max_alerts]
    
    @property
    def health_score(self) -> int:
        """Get health score."""
        data = get_alerts_for_dashboard(self._hass, self._entry_id)
        return data.get("health_score", 100)
    
    @property
    def counts(self) -> dict:
        """Get alert counts by category."""
        data = get_alerts_for_dashboard(self._hass, self._entry_id)
        return data.get("counts", {})
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        from ..core.modules.home_alerts_module import get_home_alerts_module
        
        module = get_home_alerts_module(self._hass, self._entry_id)
        if module:
            return module.acknowledge_alert(alert_id)
        return False


# Lovelace Card Definition (YAML format for frontend)
LOVELACE_CARD_YAML = """
type: custom:home-alerts-card
name: Handlungsbedarf
icon: mdi:alert-circle
show_health_score: true
categories:
  - battery
  - climate
  - presence
  - system
max_alerts: 10
"""

# Dashboard Card HTML Template (for React Board)
DASHBOARD_CARD_HTML = """
<div class="home-alerts-card">
  <div class="health-score">
    <ha-gauge
      min="0"
      max="100"
      value="{health_score}"
      severity="{severity}"
    ></ha-gauge>
    <span class="label">Home Health</span>
  </div>
  
  <div class="alert-counts">
    <div class="count battery">
      <ha-icon icon="mdi:battery-alert"></ha-icon>
      <span>{battery_count}</span>
    </div>
    <div class="count climate">
      <ha-icon icon="mdi:thermometer-alert"></ha-icon>
      <span>{climate_count}</span>
    </div>
    <div class="count presence">
      <ha-icon icon="mdi:account-alert"></ha-icon>
      <span>{presence_count}</span>
    </div>
    <div class="count system">
      <ha-icon icon="mdi:alert-circle"></ha-icon>
      <span>{system_count}</span>
    </div>
  </div>
  
  <div class="alerts-list">
    {alerts_html}
  </div>
</div>

<style>
.home-alerts-card {
  padding: 16px;
  background: var(--card-background-color);
  border-radius: var(--ha-card-border-radius);
}

.health-score {
  text-align: center;
  margin-bottom: 16px;
}

.alert-counts {
  display: flex;
  justify-content: space-around;
  margin-bottom: 16px;
}

.alert-counts .count {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.alerts-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.alert-item {
  padding: 12px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.alert-item.critical {
  background: var(--error-color);
  color: white;
}

.alert-item.high {
  background: var(--warning-color);
}

.alert-item.medium {
  background: var(--info-color);
}

.alert-item.low {
  background: var(--primary-color);
  opacity: 0.7;
}
</style>
"""