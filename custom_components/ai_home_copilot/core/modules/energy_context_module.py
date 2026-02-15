"""N0 Energy Context v0.2 – Energy monitoring context module.

Provides energy data from Core Add-on for other CoPilot modules.
Exposes consumption, production, anomalies, and load shifting opportunities.

Privacy-first: only aggregated values, no device-level granularity unless user-approved.

Integration with Mood System:
- Provides frugality score based on current consumption vs baseline
- get_frugality_mood_factor() returns a MoodScore-compatible dict
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypedDict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ...const import CONF_HOST, CONF_PORT, CONF_TOKEN, DOMAIN
from ..module import ModuleContext
from ...energy_context import EnergyContextCoordinator, create_energy_context
from ...energy_context_entities import async_setup_energy_entities

_LOGGER = logging.getLogger(__name__)


class EnergySnapshot(TypedDict):
    """Energy data snapshot for other modules."""
    timestamp: datetime
    consumption_today_kwh: float
    production_today_kwh: float
    current_power_watts: float
    peak_power_today_watts: float
    anomalies_detected: int
    shifting_opportunities: list[str]
    baseline_kwh: float


@dataclass
class FrugalityMoodFactor:
    """Frugality mood factor from energy context.
    
    Attributes:
        score: 0.0-1.0 where 1.0 = most frugal (low consumption)
        consumption_vs_baseline: Ratio of current consumption to baseline
        mood_type: Associated mood type ("frugal" or "wasteful")
        confidence: Confidence in the assessment
        reasons: List of contributing factors
    """
    score: float
    consumption_vs_baseline: float
    mood_type: str
    confidence: float
    reasons: list[dict[str, Any]]


class EnergyContextModule:
    """Energy context provider for other CoPilot modules.

    Fetches energy data from Core Add-on and exposes it as entities.
    Provides frugality scoring for mood system integration.
    """

    name: str = "energy_context"

    def __init__(self) -> None:
        self._hass: HomeAssistant | None = None
        self._entry: ConfigEntry | None = None
        self._coordinator: EnergyContextCoordinator | None = None

    @property
    def coordinator(self) -> EnergyContextCoordinator | None:
        """Get the energy coordinator."""
        return self._coordinator

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Set up energy context tracking."""
        self._hass = ctx.hass
        self._entry = ctx.entry

        data: dict[str, Any] = {**ctx.entry.data, **ctx.entry.options}

        host: str | None = data.get(CONF_HOST)
        port: int = data.get(CONF_PORT, 8909)
        token: str | None = data.get(CONF_TOKEN)

        if not host:
            _LOGGER.warning("EnergyContext: no host configured — module idle")
            return

        # Create coordinator
        self._coordinator = create_energy_context(
            hass=ctx.hass,
            host=host,
            port=port,
            token=token,
        )

        try:
            await self._coordinator.async_config_entry_first_refresh()
        except Exception as err:
            _LOGGER.warning(
                "EnergyContext: failed initial refresh (Core Add-on may be down): %s",
                err,
            )
            # Continue anyway - Core Add-on might not be running

        # Set up entities
        if self._coordinator:
            await async_setup_energy_entities(ctx.hass, self._coordinator)

        # Store reference for other modules
        domain_data: dict[str, Any] = ctx.hass.data.setdefault(DOMAIN, {})
        entry_data: dict[str, Any] = domain_data.setdefault(ctx.entry.entry_id, {})
        entry_data["energy_context_module"] = self

        _LOGGER.info("EnergyContext v0.2: initialized (host=%s:%s)", host, port)

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload energy context tracking."""
        domain_data: dict[str, Any] | None = ctx.hass.data.get(DOMAIN)
        if domain_data:
            entry_data: dict[str, Any] = domain_data.get(ctx.entry.entry_id, {})
            entry_data.pop("energy_context_module", None)

        self._coordinator = None
        self._hass = None
        self._entry = None

        _LOGGER.debug("EnergyContext: unloaded")
        return True

    def get_snapshot(self) -> EnergySnapshot | None:
        """Get current energy snapshot for other modules.
        
        Returns:
            EnergySnapshot with current energy data, or None if unavailable
        """
        if not self._coordinator or not self._coordinator.data:
            return None

        data = self._coordinator.data
        return EnergySnapshot(
            timestamp=data.timestamp,
            consumption_today_kwh=data.total_consumption_today_kwh,
            production_today_kwh=data.total_production_today_kwh,
            current_power_watts=data.current_power_watts,
            peak_power_today_watts=data.peak_power_today_watts,
            anomalies_detected=data.anomalies_detected,
            shifting_opportunities=data.shifting_opportunities,
            baseline_kwh=data.baseline_kwh,
        )

    def get_frugality_mood_factor(self) -> FrugalityMoodFactor | None:
        """Get frugality mood factor for mood system integration.
        
        Calculates how frugal current energy consumption is compared to baseline.
        
        Returns:
            FrugalityMoodFactor with score and reasons, or None if unavailable
        """
        snapshot = self.get_snapshot()
        if not snapshot:
            return None
        
        baseline_kwh = snapshot["baseline_kwh"]
        consumption_kwh = snapshot["consumption_today_kwh"]
        
        if baseline_kwh <= 0:
            # No baseline to compare - assume neutral
            return FrugalityMoodFactor(
                score=0.5,
                consumption_vs_baseline=1.0,
                mood_type="neutral",
                confidence=0.3,
                reasons=[{"reason": "no_baseline", "weight": 1.0}],
            )
        
        # Calculate consumption vs baseline ratio
        ratio = consumption_kwh / baseline_kwh
        
        # Calculate frugality score (inverse of ratio, clamped 0-1)
        if ratio <= 0.5:
            # Well under baseline - very frugal
            score = 1.0
            mood_type = "frugal"
        elif ratio <= 1.0:
            # Under or at baseline
            score = 1.0 - (ratio - 0.5) * 0.5  # 0.75-1.0
            mood_type = "frugal"
        elif ratio <= 1.5:
            # Slightly over baseline
            score = 0.5 - (ratio - 1.0) * 0.5  # 0.25-0.5
            mood_type = "neutral"
        else:
            # Significantly over baseline - wasteful
            score = max(0.0, 0.25 - (ratio - 1.5) * 0.2)
            mood_type = "wasteful"
        
        # Confidence based on data quality
        confidence = 0.8 if consumption_kwh > 0.1 else 0.5
        
        # Build reasons
        reasons: list[dict[str, Any]] = [
            {
                "reason": f"consumption_{consumption_kwh:.1f}kwh",
                "weight": 0.6,
                "baseline_kwh": baseline_kwh,
                "ratio": ratio,
            },
        ]
        
        if snapshot["anomalies_detected"] > 0:
            reasons.append({
                "reason": "energy_anomalies",
                "weight": 0.2,
                "count": snapshot["anomalies_detected"],
            })
        
        if snapshot["shifting_opportunities"]:
            reasons.append({
                "reason": "load_shifting_possible",
                "weight": 0.2,
                "opportunities": snapshot["shifting_opportunities"][:3],
            })
        
        return FrugalityMoodFactor(
            score=round(score, 2),
            consumption_vs_baseline=round(ratio, 2),
            mood_type=mood_type,
            confidence=confidence,
            reasons=reasons,
        )

    def to_mood_dict(self) -> dict[str, Any] | None:
        """Convert energy context to mood-compatible dict.
        
        Used by mood system to integrate energy as a contributing factor.
        
        Returns:
            Dict compatible with MoodScore format, or None if unavailable
        """
        factor = self.get_frugality_mood_factor()
        if not factor:
            return None
        
        return {
            "mood_type": factor.mood_type,
            "value": factor.score,
            "confidence": factor.confidence,
            "source": "energy_context",
            "factors": factor.reasons,
        }
