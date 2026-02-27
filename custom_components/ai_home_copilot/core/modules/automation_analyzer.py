"""Automation Analyzer Module - Analysiert HA-Automationen und generiert Vorschlaege.

Analysiert alle Home Assistant Automationen und liefert:
  - Health-Scores und Zonen-Zuordnung pro Automation
  - Reparaturhinweise (nie getriggert, disabled, fehlende Entities)
  - Verbesserungsvorschlaege (fehlende Automationen pro Zone)
  - User-Profil-Erkennung (Komfort vs. Sparsamkeit)

Pipeline:
  HA Automations → Analyse → Insights + Repair + Suggestions → hass.data + Event
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import entity_registry as er

from ...const import DOMAIN
from ..module import CopilotModule, ModuleContext

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


class HintSeverity(str, Enum):
    """Severity levels for repair hints."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class SuggestionType(str, Enum):
    """Types of improvement suggestions."""

    MISSING_MOTION_LIGHT = "missing_motion_light"
    MISSING_CLIMATE_SCHEDULE = "missing_climate_schedule"
    MISSING_COVER_SCHEDULE = "missing_cover_schedule"
    MISSING_MEDIA_PAUSE = "missing_media_pause"
    MISSING_NIGHT_MODE = "missing_night_mode"
    MISSING_PRESENCE_AWAY = "missing_presence_away"
    GENERAL = "general"


class HintType(str, Enum):
    """Types of repair hints."""

    NEVER_TRIGGERED = "never_triggered"
    DISABLED = "disabled"
    MISSING_ENTITY = "missing_entity"
    STALE = "stale"
    DUPLICATE = "duplicate"
    EMPTY_ACTIONS = "empty_actions"


@dataclass(frozen=True, slots=True)
class AutomationInsight:
    """Analysis result for a single automation."""

    automation_id: str
    name: str
    zone_ids: tuple[str, ...] = field(default_factory=tuple)
    trigger_type: str = "unknown"
    action_type: str = "unknown"
    last_triggered: str | None = None
    health_score: float = 1.0  # 0.0 = broken, 1.0 = healthy


@dataclass(frozen=True, slots=True)
class RepairHint:
    """A repair hint for an automation."""

    automation_id: str
    hint_type: str  # HintType value
    severity: str  # HintSeverity value
    message: str
    fix_suggestion: str


@dataclass(frozen=True, slots=True)
class ImprovementSuggestion:
    """A suggested new automation for a zone."""

    zone_id: str
    suggestion_type: str  # SuggestionType value
    title: str
    description: str
    example_yaml: str


# ---------------------------------------------------------------------------
# Entity-ID extraction patterns
# ---------------------------------------------------------------------------

_ENTITY_ID_RE = re.compile(
    r"\b([a-z_]+\.[a-z0-9][a-z0-9_]*)\b"
)


def _extract_entity_ids_from_obj(obj: Any) -> set[str]:
    """Recursively extract entity_id strings from a nested dict/list structure."""
    found: set[str] = set()
    if isinstance(obj, str):
        for m in _ENTITY_ID_RE.finditer(obj):
            candidate = m.group(1)
            # Only keep plausible HA domains
            domain = candidate.split(".", 1)[0]
            if domain in _HA_DOMAINS:
                found.add(candidate)
    elif isinstance(obj, dict):
        for v in obj.values():
            found.update(_extract_entity_ids_from_obj(v))
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            found.update(_extract_entity_ids_from_obj(item))
    return found


_HA_DOMAINS = frozenset({
    "automation", "binary_sensor", "button", "calendar", "camera", "climate",
    "cover", "device_tracker", "fan", "group", "humidifier", "input_boolean",
    "input_button", "input_datetime", "input_number", "input_select",
    "input_text", "light", "lock", "media_player", "number", "person",
    "remote", "scene", "script", "select", "sensor", "siren", "sun",
    "switch", "timer", "update", "vacuum", "water_heater", "weather", "zone",
})


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


class AutomationAnalyzerModule(CopilotModule):
    """Analysiert HA-Automationen, erkennt Probleme und schlaegt Verbesserungen vor."""

    @property
    def name(self) -> str:
        return "automation_analyzer"

    @property
    def version(self) -> str:
        return "1.0"

    def __init__(self) -> None:
        self._entity_to_zone: dict[str, set[str]] = {}
        self._zone_roles: dict[str, dict[str, list[str]]] = {}
        self._all_ha_entity_ids: set[str] = set()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        hass: HomeAssistant = ctx.hass
        entry: ConfigEntry = ctx.entry

        # Build entity-to-zone mapping from zones_config
        self._build_zone_mapping(hass, entry)

        # Register service
        if not hass.services.has_service(DOMAIN, "analyze_automations"):
            hass.services.async_register(
                DOMAIN,
                "analyze_automations",
                self._handle_analyze_service,
                schema=vol.Schema({}),
            )

        # Run initial analysis
        result = await self.analyze_all(hass)

        # Store result
        entry_data = hass.data.setdefault(DOMAIN, {}).setdefault(entry.entry_id, {})
        entry_data["automation_analysis"] = result

        # Fire completion event
        hass.bus.async_fire(
            f"{DOMAIN}_automation_analysis_complete",
            {
                "entry_id": entry.entry_id,
                "insights_count": len(result.get("insights", [])),
                "repair_hints_count": len(result.get("repair_hints", [])),
                "suggestions_count": len(result.get("suggestions", [])),
            },
        )

        _LOGGER.info(
            "AutomationAnalyzerModule initialized: %d insights, %d hints, %d suggestions",
            len(result.get("insights", [])),
            len(result.get("repair_hints", [])),
            len(result.get("suggestions", [])),
        )

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        # Service bleibt registriert (shared, idempotent)
        entry_data = ctx.hass.data.get(DOMAIN, {}).get(ctx.entry.entry_id)
        if isinstance(entry_data, dict):
            entry_data.pop("automation_analysis", None)
        return True

    # ------------------------------------------------------------------
    # Zone mapping
    # ------------------------------------------------------------------

    def _build_zone_mapping(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Build entity_id -> zone_ids mapping from habitus zones store."""
        self._entity_to_zone.clear()
        self._zone_roles.clear()

        # Try loading from hass.data (zones may already be loaded by habitus store)
        zones_data: list[dict[str, Any]] = []
        try:
            import importlib.resources
            import pathlib

            zones_path = (
                pathlib.Path(__file__).resolve().parents[2]
                / "data"
                / "zones_config.json"
            )
            if zones_path.exists():
                raw = json.loads(zones_path.read_text(encoding="utf-8"))
                zones_data = raw.get("zones", []) if isinstance(raw, dict) else []
        except Exception:
            _LOGGER.debug("Could not load zones_config.json for automation analyzer")

        for zone in zones_data:
            zone_id = zone.get("zone_id", "")
            if not zone_id:
                continue

            entities_map = zone.get("entities", {})
            self._zone_roles[zone_id] = {}

            for role, entity_ids in entities_map.items():
                if not isinstance(entity_ids, list):
                    continue
                self._zone_roles[zone_id][role] = list(entity_ids)
                for eid in entity_ids:
                    self._entity_to_zone.setdefault(eid, set()).add(zone_id)

        # Collect all known HA entity IDs for existence checking
        self._all_ha_entity_ids = {
            state.entity_id for state in hass.states.async_all()
        }

    # ------------------------------------------------------------------
    # Service handler
    # ------------------------------------------------------------------

    async def _handle_analyze_service(self, call: ServiceCall) -> None:
        """Handle the analyze_automations service call."""
        hass = call.hass if hasattr(call, "hass") else None
        if hass is None:
            _LOGGER.warning("analyze_automations: no hass reference on ServiceCall")
            return

        # Refresh entity set
        self._all_ha_entity_ids = {
            state.entity_id for state in hass.states.async_all()
        }

        result = await self.analyze_all(hass)

        # Store in all entry_ids
        for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
            if isinstance(entry_data, dict) and entry_id != "_global":
                entry_data["automation_analysis"] = result

        hass.bus.async_fire(
            f"{DOMAIN}_automation_analysis_complete",
            {
                "insights_count": len(result.get("insights", [])),
                "repair_hints_count": len(result.get("repair_hints", [])),
                "suggestions_count": len(result.get("suggestions", [])),
            },
        )

    # ------------------------------------------------------------------
    # Core analysis
    # ------------------------------------------------------------------

    async def analyze_all(self, hass: HomeAssistant) -> dict[str, Any]:
        """Run full analysis and return JSON-serialisable result dict."""
        automations = hass.states.async_all("automation")

        insights: list[AutomationInsight] = []
        repair_hints: list[RepairHint] = []

        for state in automations:
            entity_id = state.entity_id
            attrs = state.attributes or {}
            friendly_name = attrs.get("friendly_name", entity_id)
            last_triggered = attrs.get("last_triggered")
            current = attrs.get("current", 0)
            automation_id = attrs.get("id", entity_id)

            # Determine trigger and action types from the automation config
            trigger_type = self._detect_trigger_type(attrs)
            action_type = self._detect_action_type(attrs)

            # Extract referenced entity IDs and map to zones
            referenced = self._extract_referenced_entities(attrs)
            zone_ids = set()
            for ref_eid in referenced:
                zone_ids.update(self._entity_to_zone.get(ref_eid, set()))

            # Health score
            health, hints = self._compute_health(
                entity_id, friendly_name, state.state, attrs, last_triggered, referenced
            )
            repair_hints.extend(hints)

            insight = AutomationInsight(
                automation_id=automation_id,
                name=friendly_name,
                zone_ids=tuple(sorted(zone_ids)),
                trigger_type=trigger_type,
                action_type=action_type,
                last_triggered=(
                    last_triggered.isoformat()
                    if isinstance(last_triggered, datetime)
                    else str(last_triggered) if last_triggered else None
                ),
                health_score=round(health, 2),
            )
            insights.append(insight)

        suggestions = self._get_improvement_suggestions(insights)
        user_profile = self._get_user_profile_from_automations(insights)

        return {
            "insights": [asdict(i) for i in insights],
            "repair_hints": [asdict(h) for h in repair_hints],
            "suggestions": [asdict(s) for s in suggestions],
            "user_profile": user_profile,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "automation_count": len(automations),
        }

    # ------------------------------------------------------------------
    # get_repair_hints (public convenience)
    # ------------------------------------------------------------------

    def get_repair_hints(self, hass: HomeAssistant) -> list[RepairHint]:
        """Synchronous access to cached repair hints (from last analysis)."""
        for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
            if isinstance(entry_data, dict) and "automation_analysis" in entry_data:
                raw = entry_data["automation_analysis"].get("repair_hints", [])
                return [
                    RepairHint(**h) if isinstance(h, dict) else h
                    for h in raw
                ]
        return []

    # ------------------------------------------------------------------
    # get_improvement_suggestions (public convenience)
    # ------------------------------------------------------------------

    def get_improvement_suggestions(self, hass: HomeAssistant) -> list[ImprovementSuggestion]:
        """Synchronous access to cached improvement suggestions."""
        for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
            if isinstance(entry_data, dict) and "automation_analysis" in entry_data:
                raw = entry_data["automation_analysis"].get("suggestions", [])
                return [
                    ImprovementSuggestion(**s) if isinstance(s, dict) else s
                    for s in raw
                ]
        return []

    # ------------------------------------------------------------------
    # get_user_profile_from_automations (public convenience)
    # ------------------------------------------------------------------

    def get_user_profile_from_automations(self, hass: HomeAssistant) -> dict[str, Any]:
        """Synchronous access to cached user profile."""
        for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
            if isinstance(entry_data, dict) and "automation_analysis" in entry_data:
                return entry_data["automation_analysis"].get("user_profile", {})
        return {}

    # ------------------------------------------------------------------
    # Trigger / Action type detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_trigger_type(attrs: dict[str, Any]) -> str:
        """Heuristically detect the primary trigger type from automation attributes."""
        # HA exposes trigger info only partially via state attributes.
        # We inspect friendly_name and id for clues.
        name_lower = str(attrs.get("friendly_name", "")).lower()
        aid = str(attrs.get("id", "")).lower()
        combined = f"{name_lower} {aid}"

        if any(kw in combined for kw in ("motion", "bewegung", "presence", "praesenz")):
            return "motion"
        if any(kw in combined for kw in ("time", "zeit", "schedule", "zeitplan", "cron")):
            return "time"
        if any(kw in combined for kw in ("sun", "sonne", "sunset", "sunrise")):
            return "sun"
        if any(kw in combined for kw in ("state", "zustand", "status")):
            return "state"
        if any(kw in combined for kw in ("webhook", "api", "mqtt")):
            return "event"
        if any(kw in combined for kw in ("button", "taster", "schalter", "switch")):
            return "device"
        return "unknown"

    @staticmethod
    def _detect_action_type(attrs: dict[str, Any]) -> str:
        """Heuristically detect the primary action type from automation attributes."""
        name_lower = str(attrs.get("friendly_name", "")).lower()
        aid = str(attrs.get("id", "")).lower()
        combined = f"{name_lower} {aid}"

        if any(kw in combined for kw in ("licht", "light", "beleuchtung", "lampe")):
            return "light"
        if any(kw in combined for kw in ("climate", "heizung", "thermostat", "temperatur")):
            return "climate"
        if any(kw in combined for kw in ("cover", "rollo", "jalousie", "shutter")):
            return "cover"
        if any(kw in combined for kw in ("media", "musik", "music", "speaker", "lautsprecher")):
            return "media"
        if any(kw in combined for kw in ("lock", "schloss", "alarm")):
            return "security"
        if any(kw in combined for kw in ("notify", "benachrichtigung", "nachricht", "notification")):
            return "notification"
        if any(kw in combined for kw in ("scene", "szene")):
            return "scene"
        return "unknown"

    # ------------------------------------------------------------------
    # Entity reference extraction
    # ------------------------------------------------------------------

    def _extract_referenced_entities(self, attrs: dict[str, Any]) -> set[str]:
        """Extract entity_ids referenced in triggers and actions."""
        return _extract_entity_ids_from_obj(attrs)

    # ------------------------------------------------------------------
    # Health scoring
    # ------------------------------------------------------------------

    def _compute_health(
        self,
        entity_id: str,
        friendly_name: str,
        state: str,
        attrs: dict[str, Any],
        last_triggered: Any,
        referenced_entities: set[str],
    ) -> tuple[float, list[RepairHint]]:
        """Compute health score (0..1) and collect repair hints."""
        score = 1.0
        hints: list[RepairHint] = []

        # 1. Disabled automation
        if state == "off":
            score -= 0.3
            hints.append(RepairHint(
                automation_id=entity_id,
                hint_type=HintType.DISABLED.value,
                severity=HintSeverity.WARNING.value,
                message=f"Automation '{friendly_name}' ist deaktiviert.",
                fix_suggestion=(
                    "Pruefe ob die Automation noch benoetigt wird. "
                    "Aktiviere sie oder loesche sie, um die Uebersicht zu behalten."
                ),
            ))

        # 2. Never triggered
        if last_triggered is None:
            score -= 0.4
            hints.append(RepairHint(
                automation_id=entity_id,
                hint_type=HintType.NEVER_TRIGGERED.value,
                severity=HintSeverity.WARNING.value,
                message=f"Automation '{friendly_name}' wurde noch nie ausgeloest.",
                fix_suggestion=(
                    "Ueberpruefen: Ist der Trigger korrekt konfiguriert? "
                    "Sind die Trigger-Entities erreichbar?"
                ),
            ))
        elif isinstance(last_triggered, datetime):
            # 3. Stale (not triggered in >30 days)
            age_days = (datetime.now(timezone.utc) - last_triggered).days
            if age_days > 30:
                penalty = min(0.2, age_days / 365.0)
                score -= penalty
                hints.append(RepairHint(
                    automation_id=entity_id,
                    hint_type=HintType.STALE.value,
                    severity=HintSeverity.INFO.value,
                    message=(
                        f"Automation '{friendly_name}' wurde seit {age_days} Tagen "
                        f"nicht mehr ausgeloest."
                    ),
                    fix_suggestion=(
                        "Pruefe ob die Bedingungen noch zutreffen oder ob "
                        "die Automation veraltet ist."
                    ),
                ))

        # 4. Missing entity references
        missing = referenced_entities - self._all_ha_entity_ids
        # Exclude the automation entity itself (always valid)
        missing.discard(entity_id)
        if missing:
            penalty = min(0.5, len(missing) * 0.15)
            score -= penalty
            for m_eid in sorted(missing):
                hints.append(RepairHint(
                    automation_id=entity_id,
                    hint_type=HintType.MISSING_ENTITY.value,
                    severity=HintSeverity.ERROR.value,
                    message=(
                        f"Automation '{friendly_name}' referenziert "
                        f"'{m_eid}', aber diese Entity existiert nicht."
                    ),
                    fix_suggestion=(
                        f"Ersetze '{m_eid}' durch eine gueltige Entity-ID "
                        f"oder entferne die Referenz."
                    ),
                ))

        return max(0.0, score), hints

    # ------------------------------------------------------------------
    # Improvement suggestions
    # ------------------------------------------------------------------

    def _get_improvement_suggestions(
        self, insights: list[AutomationInsight]
    ) -> list[ImprovementSuggestion]:
        """Analyse zones and existing automations to find missing patterns."""
        suggestions: list[ImprovementSuggestion] = []

        # Build set of (zone_id, action_type) pairs covered by existing automations
        covered: set[tuple[str, str]] = set()
        for insight in insights:
            for zid in insight.zone_ids:
                covered.add((zid, insight.action_type))

        for zone_id, roles in self._zone_roles.items():
            has_motion = bool(roles.get("motion"))
            has_lights = bool(roles.get("lights"))
            has_climate = bool(roles.get("heating"))
            has_cover = bool(roles.get("cover"))
            has_media = bool(roles.get("media"))

            # 1. Motion + Light but no auto-light automation
            if has_motion and has_lights and (zone_id, "light") not in covered:
                motion_eid = roles["motion"][0]
                light_eid = roles["lights"][0]
                suggestions.append(ImprovementSuggestion(
                    zone_id=zone_id,
                    suggestion_type=SuggestionType.MISSING_MOTION_LIGHT.value,
                    title=f"Automatisches Licht bei Bewegung ({zone_id})",
                    description=(
                        f"Zone '{zone_id}' hat Bewegungssensoren und Lichter, "
                        f"aber keine Automation die Licht bei Bewegung einschaltet."
                    ),
                    example_yaml=_yaml_motion_light(zone_id, motion_eid, light_eid),
                ))

            # 2. Climate but no schedule
            if has_climate and (zone_id, "climate") not in covered:
                climate_eid = roles["heating"][0]
                suggestions.append(ImprovementSuggestion(
                    zone_id=zone_id,
                    suggestion_type=SuggestionType.MISSING_CLIMATE_SCHEDULE.value,
                    title=f"Heizplan fuer {zone_id}",
                    description=(
                        f"Zone '{zone_id}' hat Thermostate, aber keine zeitgesteuerte "
                        f"Heiz-Automation (Nachtabsenkung, Tagesmodus)."
                    ),
                    example_yaml=_yaml_climate_schedule(zone_id, climate_eid),
                ))

            # 3. Cover but no schedule
            if has_cover and (zone_id, "cover") not in covered:
                cover_eid = roles["cover"][0]
                suggestions.append(ImprovementSuggestion(
                    zone_id=zone_id,
                    suggestion_type=SuggestionType.MISSING_COVER_SCHEDULE.value,
                    title=f"Automatischer Rolladen ({zone_id})",
                    description=(
                        f"Zone '{zone_id}' hat Rollos/Cover, aber keine Automation "
                        f"fuer Sonnenuntergang/Sonnenaufgang."
                    ),
                    example_yaml=_yaml_cover_schedule(zone_id, cover_eid),
                ))

            # 4. Media but no pause on leave
            if has_media and has_motion and (zone_id, "media") not in covered:
                suggestions.append(ImprovementSuggestion(
                    zone_id=zone_id,
                    suggestion_type=SuggestionType.MISSING_MEDIA_PAUSE.value,
                    title=f"Media pausieren bei Abwesenheit ({zone_id})",
                    description=(
                        f"Zone '{zone_id}' hat Media-Player und Bewegungssensoren, "
                        f"aber keine Automation die Media pausiert wenn niemand da ist."
                    ),
                    example_yaml=_yaml_media_pause(zone_id, roles["media"][0], roles["motion"][0]),
                ))

        return suggestions

    # ------------------------------------------------------------------
    # User profile detection
    # ------------------------------------------------------------------

    @staticmethod
    def _get_user_profile_from_automations(
        insights: list[AutomationInsight],
    ) -> dict[str, Any]:
        """Detect user patterns from automation portfolio.

        Returns a dict with:
        - comfort_score (0..1): How many automations prioritise comfort
        - efficiency_score (0..1): How many automations prioritise energy saving
        - security_score (0..1): How many automations are security-related
        - coverage_by_zone: dict[zone_id, list[action_type]]
        - dominant_trigger: most common trigger type
        - automation_count: total
        - active_count: enabled
        - health_avg: average health score
        """
        if not insights:
            return {
                "comfort_score": 0.0,
                "efficiency_score": 0.0,
                "security_score": 0.0,
                "coverage_by_zone": {},
                "dominant_trigger": "unknown",
                "automation_count": 0,
                "active_count": 0,
                "health_avg": 0.0,
            }

        comfort_actions = {"light", "media", "scene", "cover"}
        efficiency_actions = {"climate"}
        security_actions = {"security", "notification"}

        comfort_count = 0
        efficiency_count = 0
        security_count = 0
        active_count = 0
        health_sum = 0.0
        trigger_counter: dict[str, int] = {}
        coverage: dict[str, set[str]] = {}

        for insight in insights:
            health_sum += insight.health_score
            if insight.health_score > 0.0:
                active_count += 1

            if insight.action_type in comfort_actions:
                comfort_count += 1
            if insight.action_type in efficiency_actions:
                efficiency_count += 1
            if insight.action_type in security_actions:
                security_count += 1

            trigger_counter[insight.trigger_type] = (
                trigger_counter.get(insight.trigger_type, 0) + 1
            )

            for zid in insight.zone_ids:
                coverage.setdefault(zid, set()).add(insight.action_type)

        total = len(insights)
        dominant_trigger = max(trigger_counter, key=trigger_counter.get) if trigger_counter else "unknown"

        return {
            "comfort_score": round(comfort_count / total, 2),
            "efficiency_score": round(efficiency_count / total, 2),
            "security_score": round(security_count / total, 2),
            "coverage_by_zone": {
                zid: sorted(actions) for zid, actions in coverage.items()
            },
            "dominant_trigger": dominant_trigger,
            "automation_count": total,
            "active_count": active_count,
            "health_avg": round(health_sum / total, 2),
        }


# ---------------------------------------------------------------------------
# YAML template helpers
# ---------------------------------------------------------------------------


def _yaml_motion_light(zone_id: str, motion_eid: str, light_eid: str) -> str:
    return f"""\
alias: "Auto-Licht bei Bewegung ({zone_id})"
description: "Schaltet Licht ein bei Bewegung und aus nach 5 Minuten Ruhe."
trigger:
  - platform: state
    entity_id: {motion_eid}
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: {light_eid}
  - wait_for_trigger:
      - platform: state
        entity_id: {motion_eid}
        to: "off"
        for: "00:05:00"
  - service: light.turn_off
    target:
      entity_id: {light_eid}
mode: restart"""


def _yaml_climate_schedule(zone_id: str, climate_eid: str) -> str:
    return f"""\
alias: "Heizplan ({zone_id})"
description: "Nachtabsenkung 22:00, Tagesmodus 06:00."
trigger:
  - platform: time
    at: "06:00:00"
    id: morning
  - platform: time
    at: "22:00:00"
    id: night
action:
  - choose:
      - conditions:
          - condition: trigger
            id: morning
        sequence:
          - service: climate.set_temperature
            target:
              entity_id: {climate_eid}
            data:
              temperature: 21
      - conditions:
          - condition: trigger
            id: night
        sequence:
          - service: climate.set_temperature
            target:
              entity_id: {climate_eid}
            data:
              temperature: 17
mode: single"""


def _yaml_cover_schedule(zone_id: str, cover_eid: str) -> str:
    return f"""\
alias: "Rolladen Zeitsteuerung ({zone_id})"
description: "Rollos hoch bei Sonnenaufgang, runter bei Sonnenuntergang."
trigger:
  - platform: sun
    event: sunrise
    offset: "+00:15:00"
    id: open
  - platform: sun
    event: sunset
    offset: "-00:10:00"
    id: close
action:
  - choose:
      - conditions:
          - condition: trigger
            id: open
        sequence:
          - service: cover.open_cover
            target:
              entity_id: {cover_eid}
      - conditions:
          - condition: trigger
            id: close
        sequence:
          - service: cover.close_cover
            target:
              entity_id: {cover_eid}
mode: single"""


def _yaml_media_pause(zone_id: str, media_eid: str, motion_eid: str) -> str:
    return f"""\
alias: "Media pausieren bei Abwesenheit ({zone_id})"
description: "Pausiert Media-Player wenn kein Bewegung fuer 10 Minuten."
trigger:
  - platform: state
    entity_id: {motion_eid}
    to: "off"
    for: "00:10:00"
condition:
  - condition: state
    entity_id: {media_eid}
    state: playing
action:
  - service: media_player.media_pause
    target:
      entity_id: {media_eid}
mode: single"""
