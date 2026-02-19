"""Home Alerts Module - AI Home CoPilot

Monitors critical home states and generates actionable alerts.
Part of the PilotSuite neuron ecosystem.

Alert Categories:
- Battery warnings (low battery devices)
- Climate deviations (rooms too hot/cold)
- Presence changes (arrivals/departures)
- System alerts (unreachable entities, errors)

Persistence:
- Acknowledged alert IDs persist via HA Storage (survives restarts)
- Alert history (daily aggregates) kept for 30 days for learning
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any, Optional

from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.const import STATE_HOME, STATE_NOT_HOME, STATE_UNKNOWN, STATE_UNAVAILABLE
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.storage import Store

from .module import CopilotModule, ModuleContext

_LOGGER = logging.getLogger(__name__)

# Alert severity levels
SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"
SEVERITY_CRITICAL = "critical"

# Thresholds
BATTERY_WARNING_THRESHOLD = 20  # %
BATTERY_CRITICAL_THRESHOLD = 10  # %
CLIMATE_DEVIATION_THRESHOLD = 2.0  # °C difference from target

# Persistence
STORAGE_KEY = "ai_home_copilot.home_alerts"
STORAGE_VERSION = 1
HISTORY_RETENTION_DAYS = 30


@dataclass
class Alert:
    """Single alert item."""
    alert_id: str
    category: str  # battery, climate, presence, system
    severity: str  # low, medium, high, critical
    title: str
    message: str
    entity_id: Optional[str] = None
    value: Optional[Any] = None
    target: Optional[Any] = None
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    actions: list[dict[str, str]] = field(default_factory=list)


@dataclass
class HomeAlertsState:
    """State data for HomeAlerts module."""
    alerts: list[Alert] = field(default_factory=list)
    last_scan: Optional[datetime] = None
    alerts_by_category: dict[str, int] = field(default_factory=lambda: {
        "battery": 0,
        "climate": 0,
        "presence": 0,
        "system": 0
    })
    health_score: int = 100  # 0-100, starts at 100, decreases with alerts


class HomeAlertsModule(CopilotModule):
    """Monitors critical home states and generates alerts.

    This module scans Home Assistant entities for:
    - Low battery devices (< 20%)
    - Climate deviations (room temp differs from target by > 2°C)
    - Presence state changes
    - System issues (unavailable entities, errors)

    Alerts are exposed via:
    - `sensor.ai_home_copilot_alerts` - Current alert count
    - `sensor.ai_home_copilot_health` - Home health score (0-100)
    - Dashboard Card - Visual alert display

    Persistence:
    - Acknowledged alert IDs survive restarts (HA Storage)
    - Daily alert history kept for 30 days (trend analysis)
    """

    @property
    def name(self) -> str:
        return "home_alerts"

    @property
    def version(self) -> str:
        return "0.2.0"

    def __init__(self):
        self._state = HomeAlertsState()
        self._hass: Optional[HomeAssistant] = None
        self._entry_id: Optional[str] = None
        self._unsub_callbacks: list = []
        self._store: Optional[Store] = None
        self._acknowledged_ids: set[str] = set()
        self._alert_history: list[dict] = []  # daily aggregates

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Set up the HomeAlerts module."""
        self._hass = ctx.hass
        self._entry_id = ctx.entry_id

        _LOGGER.info("Setting up HomeAlerts module v%s", self.version)

        # Initialize persistent storage
        self._store = Store(ctx.hass, STORAGE_VERSION, STORAGE_KEY)
        await self._load_persisted_state()

        # Store module state
        ctx.hass.data.setdefault("ai_home_copilot", {})
        ctx.hass.data["ai_home_copilot"].setdefault(ctx.entry_id, {})
        ctx.hass.data["ai_home_copilot"][ctx.entry_id]["home_alerts"] = self._state

        # Initial scan
        await self._async_scan_all()

        # Set up periodic scanning (every 5 minutes)
        unsub = ctx.hass.helpers.event.async_track_time_interval(
            self._async_periodic_scan,
            timedelta(minutes=5)
        )
        self._unsub_callbacks.append(unsub)

        # Track state changes for real-time alerts
        unsub = async_track_state_change_event(
            ctx.hass,
            self._get_tracked_entities(),
            self._async_state_changed
        )
        self._unsub_callbacks.append(unsub)

        _LOGGER.info(
            "HomeAlerts module setup complete. Found %d alerts, "
            "%d acknowledged IDs restored",
            len(self._state.alerts),
            len(self._acknowledged_ids),
        )

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload the HomeAlerts module."""
        _LOGGER.info("Unloading HomeAlerts module")
        await self._save_persisted_state()
        for unsub in self._unsub_callbacks:
            unsub()
        self._unsub_callbacks.clear()
        return True

    # ── Persistence ─────────────────────────────────────────────────────

    async def _load_persisted_state(self) -> None:
        """Load acknowledged IDs and alert history from HA Storage."""
        try:
            data = await self._store.async_load()
            if data:
                self._acknowledged_ids = set(data.get("acknowledged_ids", []))
                self._alert_history = data.get("alert_history", [])
                # Prune old history
                self._prune_history()
                _LOGGER.debug(
                    "Loaded %d acknowledged alert IDs, %d history entries",
                    len(self._acknowledged_ids),
                    len(self._alert_history),
                )
        except Exception:
            _LOGGER.exception("Failed to load persisted alert state")

    async def _save_persisted_state(self) -> None:
        """Save acknowledged IDs and alert history to HA Storage."""
        try:
            self._prune_history()
            await self._store.async_save({
                "acknowledged_ids": list(self._acknowledged_ids),
                "alert_history": self._alert_history[-HISTORY_RETENTION_DAYS:],
            })
        except Exception:
            _LOGGER.exception("Failed to save persisted alert state")

    def _prune_history(self) -> None:
        """Remove history entries older than retention period."""
        if not self._alert_history:
            return
        cutoff = (datetime.now() - timedelta(days=HISTORY_RETENTION_DAYS)).isoformat()
        self._alert_history = [
            h for h in self._alert_history if h.get("date", "") >= cutoff[:10]
        ]

    def _record_daily_snapshot(self) -> None:
        """Record today's alert counts for historical trending."""
        today = datetime.now().strftime("%Y-%m-%d")
        # Check if we already have today's entry
        for entry in self._alert_history:
            if entry.get("date") == today:
                # Update existing
                entry["counts"] = dict(self._state.alerts_by_category)
                entry["health_score"] = self._state.health_score
                entry["total"] = len(self._state.alerts)
                return
        # Add new
        self._alert_history.append({
            "date": today,
            "counts": dict(self._state.alerts_by_category),
            "health_score": self._state.health_score,
            "total": len(self._state.alerts),
        })

    # ── State ───────────────────────────────────────────────────────────

    def get_state(self) -> HomeAlertsState:
        """Get current module state."""
        return self._state

    def get_alerts(self, category: Optional[str] = None, severity: Optional[str] = None) -> list[Alert]:
        """Get filtered alerts."""
        alerts = self._state.alerts
        if category:
            alerts = [a for a in alerts if a.category == category]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        # Sort by severity (descending: critical > high > medium > low), then by created_at (descending: newest first)
        severity_order = {SEVERITY_CRITICAL: 4, SEVERITY_HIGH: 3, SEVERITY_MEDIUM: 2, SEVERITY_LOW: 1}
        return sorted(alerts, key=lambda a: (severity_order.get(a.severity, 0), a.created_at.timestamp()), reverse=True)

    def get_alert_history(self, days: int = 7) -> list[dict]:
        """Get daily alert history for trending/learning."""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        return [h for h in self._alert_history if h.get("date", "") >= cutoff]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert (persists across restarts)."""
        for alert in self._state.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                self._acknowledged_ids.add(alert_id)
                self._update_health_score()
                # Schedule async save
                if self._hass:
                    self._hass.async_create_task(self._save_persisted_state())
                return True
        return False

    async def _async_periodic_scan(self, now: datetime) -> None:
        """Periodic scan for alerts."""
        _LOGGER.debug("Running periodic alert scan")
        await self._async_scan_all()
        # Persist daily snapshot + save acknowledged state
        self._record_daily_snapshot()
        await self._save_persisted_state()

    async def _async_scan_all(self) -> None:
        """Scan all entities for alerts."""
        if not self._hass:
            return

        # Clear old alerts (refresh scan)
        self._state.alerts.clear()

        # Scan each category
        await self._async_scan_batteries()
        await self._async_scan_climate()
        await self._async_scan_system()

        # Re-apply persisted acknowledgments
        for alert in self._state.alerts:
            if alert.alert_id in self._acknowledged_ids:
                alert.acknowledged = True

        # Update counts
        self._update_alert_counts()
        self._update_health_score()
        self._state.last_scan = datetime.now()

    async def _async_scan_batteries(self) -> None:
        """Scan for low battery devices."""
        if not self._hass:
            return

        states = self._hass.states.async_all()

        for state in states:
            entity_id = state.entity_id

            # Skip non-sensor entities unless they have battery in the name
            if not entity_id.startswith("sensor.") and "battery" not in entity_id.lower():
                continue

            # Check for battery attribute or state
            battery_value = None

            # Try attribute first
            if "battery" in state.attributes:
                battery_value = state.attributes["battery"]
            elif "battery_level" in state.attributes:
                battery_value = state.attributes["battery_level"]
            # Try state as number
            elif state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE, "None", "none", ""):
                try:
                    battery_value = float(state.state)
                except (ValueError, TypeError):
                    pass

            if battery_value is None:
                continue

            try:
                battery_pct = float(battery_value)
            except (ValueError, TypeError):
                continue

            # Generate alert if below threshold
            if battery_pct <= BATTERY_CRITICAL_THRESHOLD:
                alert = Alert(
                    alert_id=f"battery_{entity_id}",
                    category="battery",
                    severity=SEVERITY_CRITICAL,
                    title=f"Kritischer Batteriestand: {state.name}",
                    message=f"{state.name} hat nur noch {battery_pct:.0f}% Batterie",
                    entity_id=entity_id,
                    value=battery_pct,
                    actions=[{"action": "acknowledge", "title": "Bestätigt"}]
                )
                self._state.alerts.append(alert)
            elif battery_pct <= BATTERY_WARNING_THRESHOLD:
                alert = Alert(
                    alert_id=f"battery_{entity_id}",
                    category="battery",
                    severity=SEVERITY_MEDIUM,
                    title=f"Niedriger Batteriestand: {state.name}",
                    message=f"{state.name} hat {battery_pct:.0f}% Batterie",
                    entity_id=entity_id,
                    value=battery_pct,
                    actions=[{"action": "acknowledge", "title": "Bestätigt"}]
                )
                self._state.alerts.append(alert)

    async def _async_scan_climate(self) -> None:
        """Scan for climate deviations."""
        if not self._hass:
            return

        states = self._hass.states.async_all()

        for state in states:
            if not state.entity_id.startswith("climate."):
                continue

            # Get current temperature
            current_temp = state.attributes.get("current_temperature")
            target_temp = state.attributes.get("temperature")

            if current_temp is None or target_temp is None:
                continue

            try:
                current = float(current_temp)
                target = float(target_temp)
            except (ValueError, TypeError):
                continue

            deviation = current - target

            if abs(deviation) > CLIMATE_DEVIATION_THRESHOLD:
                severity = SEVERITY_MEDIUM if abs(deviation) < 4 else SEVERITY_HIGH
                direction = "zu warm" if deviation > 0 else "zu kalt"

                alert = Alert(
                    alert_id=f"climate_{state.entity_id}",
                    category="climate",
                    severity=severity,
                    title=f"Klima-Abweichung: {state.name}",
                    message=f"{state.name} ist {direction} ({current:.1f}°C bei Ziel {target:.1f}°C)",
                    entity_id=state.entity_id,
                    value=current,
                    target=target,
                    actions=[
                        {"action": "adjust_temp", "title": "Anpassen"},
                        {"action": "acknowledge", "title": "Ignorieren"}
                    ]
                )
                self._state.alerts.append(alert)

    async def _async_scan_system(self) -> None:
        """Scan for system issues."""
        if not self._hass:
            return

        states = self._hass.states.async_all()
        unavailable_count = 0

        for state in states:
            if state.state == STATE_UNAVAILABLE:
                unavailable_count += 1

        if unavailable_count > 0:
            severity = SEVERITY_LOW if unavailable_count < 5 else SEVERITY_MEDIUM
            alert = Alert(
                alert_id="system_unavailable_entities",
                category="system",
                severity=severity,
                title="Nicht erreichbare Entities",
                message=f"{unavailable_count} Entities sind derzeit nicht erreichbar",
                value=unavailable_count,
                actions=[{"action": "reload", "title": "Neu laden"}]
            )
            self._state.alerts.append(alert)

    def _update_alert_counts(self) -> None:
        """Update alert counts by category."""
        counts = {"battery": 0, "climate": 0, "presence": 0, "system": 0}
        for alert in self._state.alerts:
            if alert.category in counts:
                counts[alert.category] += 1
        self._state.alerts_by_category = counts

    def _update_health_score(self) -> None:
        """Calculate home health score (0-100)."""
        score = 100

        for alert in self._state.alerts:
            if alert.acknowledged:
                continue

            # Deduct points based on severity
            if alert.severity == SEVERITY_CRITICAL:
                score -= 15
            elif alert.severity == SEVERITY_HIGH:
                score -= 10
            elif alert.severity == SEVERITY_MEDIUM:
                score -= 5
            elif alert.severity == SEVERITY_LOW:
                score -= 2

        self._state.health_score = max(0, min(100, score))

    def _get_tracked_entities(self) -> list[str]:
        """Get list of entities to track for real-time updates."""
        entities = []
        if self._hass:
            for state in self._hass.states.async_all():
                if "battery" in state.entity_id.lower():
                    entities.append(state.entity_id)
                elif state.entity_id.startswith("climate."):
                    entities.append(state.entity_id)
                elif state.entity_id.startswith("person."):
                    entities.append(state.entity_id)
        return entities

    @callback
    async def _async_state_changed(self, event: Event) -> None:
        """Handle state changes for real-time alerts."""
        entity_id = event.data.get("entity_id")
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")

        if not new_state:
            return

        # Handle presence changes
        if entity_id.startswith("person."):
            await self._async_handle_presence_change(entity_id, old_state, new_state)

        # Handle battery changes
        elif "battery" in entity_id.lower():
            await self._async_handle_battery_change(entity_id, new_state)

    async def _async_handle_presence_change(self, entity_id: str, old_state, new_state) -> None:
        """Handle presence state changes."""
        if not old_state or not new_state:
            return

        old = old_state.state
        new = new_state.state

        if old == new:
            return

        name = new_state.name or entity_id

        if new == STATE_HOME:
            alert = Alert(
                alert_id=f"presence_{entity_id}_{datetime.now().timestamp()}",
                category="presence",
                severity=SEVERITY_LOW,
                title=f"Ankunft: {name}",
                message=f"{name} ist zu Hause angekommen",
                entity_id=entity_id,
                value=new
            )
        elif new == STATE_NOT_HOME:
            alert = Alert(
                alert_id=f"presence_{entity_id}_{datetime.now().timestamp()}",
                category="presence",
                severity=SEVERITY_LOW,
                title=f"Abwesenheit: {name}",
                message=f"{name} hat das Haus verlassen",
                entity_id=entity_id,
                value=new
            )
        else:
            return

        self._state.alerts.append(alert)
        self._update_alert_counts()
        _LOGGER.debug("Presence alert: %s", alert.title)


# Module registration helper
def get_home_alerts_module(hass: HomeAssistant, entry_id: str) -> Optional[HomeAlertsModule]:
    """Get the HomeAlerts module instance for a config entry."""
    data = hass.data.get("ai_home_copilot", {}).get(entry_id, {})
    return data.get("home_alerts")
