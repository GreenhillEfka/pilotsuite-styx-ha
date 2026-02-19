"""
Energy Optimizer -- Optimize device scheduling based on energy prices.

Integrates with Tibber, aWATTar, or manual price schedules to find
optimal times for high-consumption devices.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# aWATTar public API (no key required for DE/AT day-ahead prices)
AWATTAR_URL = "https://api.awattar.de/v1/marketdata"


class EnergyOptimizer:
    """Find optimal run windows for high-consumption devices.

    Prices are either set manually via :meth:`set_price_schedule` or
    fetched from a supported provider (aWATTar, Tibber).  The optimizer
    then finds the cheapest contiguous window of a given duration.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._prices: List[Dict[str, Any]] = []
        logger.info("EnergyOptimizer initialized")

    # ------------------------------------------------------------------
    # Price schedule management
    # ------------------------------------------------------------------

    def set_price_schedule(self, prices: List[Dict[str, Any]]) -> None:
        """Manually set the price schedule.

        Parameters
        ----------
        prices : list[dict]
            Each entry must have ``start`` (ISO), ``end`` (ISO), and
            ``price_eur_kwh`` (float).
        """
        with self._lock:
            self._prices = sorted(prices, key=lambda p: p["start"])
            logger.info("Price schedule set with %d slots", len(self._prices))

    def fetch_prices(
        self, provider: str = "awattar", region: str = "de"
    ) -> List[Dict[str, Any]]:
        """Fetch day-ahead prices from an external provider.

        Currently supported:
        - ``awattar`` (DE/AT, no API key)

        Returns the normalised price list and also stores it internally.
        """
        prices: List[Dict[str, Any]] = []

        if provider == "awattar":
            prices = self._fetch_awattar(region)
        else:
            logger.warning("Unknown price provider: %s", provider)
            return []

        with self._lock:
            self._prices = prices

        return prices

    # ------------------------------------------------------------------
    # Optimization
    # ------------------------------------------------------------------

    def find_optimal_window(
        self, duration_hours: float = 2.0, within_hours: float = 24.0
    ) -> Dict[str, Any]:
        """Find the cheapest contiguous window of *duration_hours*.

        Parameters
        ----------
        duration_hours : float
            Length of the desired run window.
        within_hours : float
            Look-ahead horizon from now.

        Returns
        -------
        dict
            ``start``, ``end``, ``avg_price_eur_kwh``, ``savings_vs_now``.
        """
        with self._lock:
            prices = list(self._prices)

        if not prices:
            return {
                "start": None,
                "end": None,
                "avg_price_eur_kwh": None,
                "savings_vs_now": 0.0,
                "error": "No price data available",
            }

        now = datetime.now(timezone.utc)
        horizon = now + timedelta(hours=within_hours)

        # Filter to slots within horizon
        valid = [
            p for p in prices
            if datetime.fromisoformat(p["start"].replace("Z", "+00:00")) < horizon
            and datetime.fromisoformat(p["end"].replace("Z", "+00:00")) > now
        ]

        if not valid:
            return {
                "start": None,
                "end": None,
                "avg_price_eur_kwh": None,
                "savings_vs_now": 0.0,
                "error": "No price slots within horizon",
            }

        # Sliding window: find the cheapest contiguous block
        slot_hours = self._slot_duration_hours(valid)
        slots_needed = max(1, int(duration_hours / slot_hours))

        best_avg = float("inf")
        best_start_idx = 0

        for i in range(len(valid) - slots_needed + 1):
            window = valid[i : i + slots_needed]
            avg = sum(s["price_eur_kwh"] for s in window) / len(window)
            if avg < best_avg:
                best_avg = avg
                best_start_idx = i

        best_window = valid[best_start_idx : best_start_idx + slots_needed]
        start_iso = best_window[0]["start"]
        end_iso = best_window[-1]["end"]

        # Current price for savings comparison
        current_price = self._current_price(valid, now)
        savings = (current_price - best_avg) if current_price else 0.0

        return {
            "start": start_iso,
            "end": end_iso,
            "avg_price_eur_kwh": round(best_avg, 6),
            "savings_vs_now": round(savings, 6),
        }

    def suggest_device_shift(
        self,
        device_entity: str,
        consumption_kwh: float,
        duration_hours: float,
    ) -> Dict[str, Any]:
        """Suggest when to run *device_entity* to minimise cost.

        Returns the optimal window plus estimated cost and savings.
        """
        window = self.find_optimal_window(
            duration_hours=duration_hours, within_hours=24.0
        )

        if window.get("start") is None:
            return {
                "device_entity": device_entity,
                "suggestion": "No price data; run at your convenience.",
                **window,
            }

        cost_optimal = window["avg_price_eur_kwh"] * consumption_kwh
        cost_now = (
            (window["avg_price_eur_kwh"] + window["savings_vs_now"])
            * consumption_kwh
        )

        return {
            "device_entity": device_entity,
            "consumption_kwh": consumption_kwh,
            "optimal_start": window["start"],
            "optimal_end": window["end"],
            "estimated_cost_eur": round(cost_optimal, 4),
            "cost_if_now_eur": round(cost_now, 4),
            "estimated_savings_eur": round(cost_now - cost_optimal, 4),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_awattar(self, region: str) -> List[Dict[str, Any]]:
        """Fetch aWATTar day-ahead prices."""
        import urllib.request
        import json

        base = AWATTAR_URL
        if region == "at":
            base = base.replace(".de", ".at")

        try:
            with urllib.request.urlopen(base, timeout=10) as resp:
                data = json.loads(resp.read().decode())
        except Exception as exc:
            logger.error("aWATTar fetch failed: %s", exc)
            return []

        prices: List[Dict[str, Any]] = []
        for item in data.get("data", []):
            start_dt = datetime.fromtimestamp(
                item["start_timestamp"] / 1000, tz=timezone.utc
            )
            end_dt = datetime.fromtimestamp(
                item["end_timestamp"] / 1000, tz=timezone.utc
            )
            # aWATTar returns EUR/MWh -> convert to EUR/kWh
            price_kwh = item["marketprice"] / 1000.0
            prices.append({
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "price_eur_kwh": round(price_kwh, 6),
            })

        logger.info("Fetched %d price slots from aWATTar (%s)", len(prices), region)
        return prices

    @staticmethod
    def _slot_duration_hours(slots: List[Dict[str, Any]]) -> float:
        """Infer the duration of one price slot in hours."""
        if len(slots) < 2:
            return 1.0
        s0 = datetime.fromisoformat(slots[0]["start"].replace("Z", "+00:00"))
        s1 = datetime.fromisoformat(slots[1]["start"].replace("Z", "+00:00"))
        return max(0.25, (s1 - s0).total_seconds() / 3600.0)

    @staticmethod
    def _current_price(
        slots: List[Dict[str, Any]], now: datetime
    ) -> Optional[float]:
        """Return the price of the slot containing *now*."""
        for s in slots:
            start = datetime.fromisoformat(s["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(s["end"].replace("Z", "+00:00"))
            if start <= now < end:
                return s["price_eur_kwh"]
        return None
