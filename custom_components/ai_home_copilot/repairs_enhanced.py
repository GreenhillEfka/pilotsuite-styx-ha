"""Enhanced Repairs UX - Zone Context, Mood Context, Risk Visualization.

Extends the base repairs with:
- Zone context (where does this pattern come from?)
- Mood context (why is this relevant now?)
- Risk visualization (high/medium/low with explanations)
- Rich evidence display
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class SuggestionContext:
    """Context for a CoPilot suggestion."""
    
    # Pattern info
    pattern: str  # "light.kitchen:on → switch.coffee:on"
    confidence: float  # 0.0 - 1.0
    lift: float  # > 1.0 means positive correlation
    support: int  # number of observations
    
    # Zone context
    zone_id: str = ""
    zone_name: str = ""
    zone_entities: list[str] = field(default_factory=list)
    
    # Mood context
    mood_type: str = ""  # relax, focus, active, etc.
    mood_value: float = 0.0
    mood_reason: str = ""
    
    # Risk/safety
    risk_level: str = "medium"  # low, medium, high
    safety_critical: bool = False
    requires_confirmation: bool = True
    
    # Evidence
    evidence: list[dict[str, Any]] = field(default_factory=list)
    timing_stats: dict[str, Any] = field(default_factory=dict)
    
    # Source
    source: str = "habitus"  # habitus, seed, zone_mining
    created_at: str = ""


def format_zone_context(zone_id: str, zone_name: str, entities: list[str]) -> str:
    """Format zone context for display."""
    if not zone_id:
        return "Global (no zone)"
    
    entity_count = len(entities)
    if entity_count <= 3:
        entity_str = ", ".join(entities)
    else:
        entity_str = f"{entity_count} entities"
    
    if zone_name:
        return f"{zone_name} ({entity_str})"
    return f"{zone_id} ({entity_str})"


def format_mood_context(mood_type: str, mood_value: float, mood_reason: str) -> str:
    """Format mood context for display."""
    if not mood_type:
        return "Neutral"
    
    mood_emoji = {
        "relax": "😌",
        "focus": "🎯",
        "active": "⚡",
        "sleep": "😴",
        "away": "🚪",
        "alert": "🚨",
        "social": "👥",
        "recovery": "💚",
    }
    
    emoji = mood_emoji.get(mood_type, "📊")
    intensity = int(mood_value * 100)
    
    if mood_reason:
        return f"{emoji} {mood_type.title()} ({intensity}%) – {mood_reason}"
    return f"{emoji} {mood_type.title()} ({intensity}%)"


def format_risk_level(risk_level: str, safety_critical: bool) -> str:
    """Format risk level with safety indicator."""
    risk_icons = {
        "low": "🟢",
        "medium": "🟡",
        "high": "🔴",
    }
    
    icon = risk_icons.get(risk_level, "⚪")
    
    if safety_critical:
        return f"{icon} HIGH (safety-critical entity)"
    
    risk_descriptions = {
        "low": "Low risk – routine automation",
        "medium": "Medium risk – review recommended",
        "high": "High risk – careful review required",
    }
    
    return f"{icon} {risk_descriptions.get(risk_level, risk_level.title())}"


def format_evidence(evidence: list[dict[str, Any]], timing: dict[str, Any]) -> str:
    """Format pattern evidence for display."""
    if not evidence:
        return ""
    
    lines = ["**Evidence:**"]
    
    # Timing stats
    if timing:
        median = timing.get("median_delay_sec")
        if median:
            lines.append(f"- Typical delay: {median:.1f}s")
        
        quartiles = timing.get("quartiles", [])
        if len(quartiles) >= 2:
            lines.append(f"- Range: {quartiles[0]:.1f}s – {quartiles[-1]:.1f}s")
    
    # Sample observations
    if evidence:
        lines.append(f"- {len(evidence)} observations recorded")
        if len(evidence) > 0:
            first = evidence[0]
            if "timestamp" in first:
                lines.append(f"- Most recent: {first['timestamp']}")
    
    return "\n".join(lines)


def format_suggestion_for_issue(
    ctx: SuggestionContext,
    blueprint_url: str = "",
) -> dict[str, str]:
    """Format suggestion context for HA issue description.
    
    Returns dict with placeholders for strings.json issue template.
    """
    zone_str = format_zone_context(ctx.zone_id, ctx.zone_name, ctx.zone_entities)
    mood_str = format_mood_context(ctx.mood_type, ctx.mood_value, ctx.mood_reason)
    risk_str = format_risk_level(ctx.risk_level, ctx.safety_critical)
    evidence_str = format_evidence(ctx.evidence, ctx.timing_stats)
    
    return {
        "title": ctx.pattern,
        "zone": zone_str,
        "confidence": f"{int(ctx.confidence * 100)}",
        "lift": f"{ctx.lift:.1f}",
        "mood_context": mood_str,
        "risk": risk_str,
        "safety_status": risk_str,
        "evidence": f"\n\n{evidence_str}" if evidence_str else "",
        "blueprint_url": blueprint_url,
        "pattern": ctx.pattern,
    }


@callback
def async_create_enhanced_issue(
    hass: HomeAssistant,
    *,
    issue_id: str,
    ctx: SuggestionContext,
    blueprint_url: str = "",
    entry_id: str = "",
    candidate_id: str = "",
    data: dict[str, Any] | None = None,
) -> None:
    """Create an enhanced repair issue with zone and mood context."""
    
    placeholders = format_suggestion_for_issue(ctx, blueprint_url)
    
    # Merge with additional data
    issue_data = {
        "entry_id": entry_id,
        "candidate_id": candidate_id,
        "zone_id": ctx.zone_id,
        "mood_type": ctx.mood_type,
        "risk": ctx.risk_level,
        "safety_critical": ctx.safety_critical,
        "confidence": ctx.confidence,
        "lift": ctx.lift,
        "pattern": ctx.pattern,
        **(data or {}),
    }
    
    # Add blueprint info if available
    if blueprint_url:
        issue_data["blueprint_url"] = blueprint_url
    
    # Determine issue type
    if ctx.source == "zone_pattern":
        translation_key = "zone_pattern"
    elif ctx.source == "seed":
        translation_key = "seed_suggestion"
    else:
        translation_key = "candidate_suggestion"
    
    # Create the issue
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        data=issue_data,
        translation_key=translation_key,
        translation_placeholders=placeholders,
        severity=ir.IssueSeverity.WARNING if ctx.risk_level != "high" else ir.IssueSeverity.ERROR,
        is_fixable=True,
        learn_more_url=blueprint_url or None,
    )
    
    _LOGGER.debug(
        "Created enhanced issue %s: pattern=%s, zone=%s, mood=%s, risk=%s",
        issue_id, ctx.pattern, ctx.zone_id, ctx.mood_type, ctx.risk_level
    )


async def async_get_suggestion_context_from_core(
    hass: HomeAssistant,
    entry_id: str,
    candidate_id: str,
) -> SuggestionContext | None:
    """Fetch suggestion context from Core Add-on API.
    
    Queries the Core for zone, mood, and pattern details.
    """
    from .api import CopilotApiClient, CopilotApiError
    
    ent_data = hass.data.get(DOMAIN, {}).get(entry_id)
    if not isinstance(ent_data, dict):
        return None
    
    coord = ent_data.get("coordinator")
    api: CopilotApiClient | None = getattr(coord, "api", None)
    if not isinstance(api, CopilotApiClient):
        return None
    
    try:
        # Try to get candidate details from Core
        candidate = await api.async_get(f"/api/v1/candidates/{candidate_id}")
        if not isinstance(candidate, dict):
            return None
        
        # Extract context
        return SuggestionContext(
            pattern=candidate.get("pattern", ""),
            confidence=float(candidate.get("confidence", 0.5)),
            lift=float(candidate.get("lift", 1.0)),
            support=int(candidate.get("support", 0)),
            zone_id=candidate.get("zone_id", ""),
            zone_name=candidate.get("zone_name", ""),
            zone_entities=candidate.get("zone_entities", []),
            mood_type=candidate.get("mood_type", ""),
            mood_value=float(candidate.get("mood_value", 0.0)),
            mood_reason=candidate.get("mood_reason", ""),
            risk_level=candidate.get("risk_level", "medium"),
            safety_critical=bool(candidate.get("safety_critical", False)),
            requires_confirmation=bool(candidate.get("requires_confirmation", True)),
            evidence=candidate.get("evidence", []),
            timing_stats=candidate.get("timing_stats", {}),
            source=candidate.get("source", "habitus"),
            created_at=candidate.get("created_at", ""),
        )
    except CopilotApiError as err:
        _LOGGER.debug("Failed to fetch suggestion context: %s", err)
        return None


def compute_risk_level(ctx: SuggestionContext) -> str:
    """Compute risk level based on context.
    
    Rules:
    - Safety-critical entities → HIGH
    - High confidence (>0.9) + high lift (>3.0) → LOW
    - Medium confidence (>0.7) + medium lift (>2.0) → MEDIUM
    - Otherwise → MEDIUM
    """
    if ctx.safety_critical:
        return "high"
    
    if ctx.confidence > 0.9 and ctx.lift > 3.0:
        return "low"
    
    if ctx.confidence > 0.7 and ctx.lift > 2.0:
        return "medium"
    
    return "medium"


def requires_explicit_confirmation(ctx: SuggestionContext) -> bool:
    """Determine if suggestion requires explicit user confirmation.
    
    Always True for:
    - Safety-critical entities
    - High risk
    - Zone governance requires confirmation
    """
    if ctx.safety_critical:
        return True
    if ctx.risk_level == "high":
        return True
    return ctx.requires_confirmation