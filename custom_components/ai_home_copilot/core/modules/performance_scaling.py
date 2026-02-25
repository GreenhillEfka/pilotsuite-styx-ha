"""Performance Monitoring Module (v5.0.0).

Tracks API response times, memory usage, entity counts, coordinator
update latency, and alert thresholds.  Integrates with the existing
PerformanceGuardrails rate-limiting infrastructure.

Expanded from v0.1 stub to full monitoring kernel v1.0.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ...const import DOMAIN
from ..module import ModuleContext
from .performance_guardrails import get_guardrails

_LOGGER = logging.getLogger(__name__)

# Alert thresholds (configurable at runtime)
DEFAULT_THRESHOLDS = {
    "api_response_time_ms": 2000,
    "coordinator_update_ms": 5000,
    "entity_count_max": 200,
    # 3 GB default to reduce false positives on normal HA host workloads.
    "memory_usage_mb_max": 3072,
    "error_rate_percent": 5.0,
}

# Avoid repeating identical warnings every minute in steady-state overloads.
ALERT_LOG_THROTTLE_S = 15 * 60
# Require sustained breaches to avoid restart spike noise.
ALERT_STREAK_REQUIRED = 3
MEMORY_ALERT_CLEAR_FACTOR = 0.92
MEMORY_ALERT_HEADROOM_MB = 96
MIN_REASONABLE_MEMORY_THRESHOLD_MB = 2048


@dataclass
class PerformanceSnapshot:
    """A point-in-time performance reading."""

    timestamp: float
    api_response_times_ms: List[float] = field(default_factory=list)
    coordinator_latency_ms: float = 0.0
    entity_count: int = 0
    memory_usage_mb: float = 0.0
    error_count: int = 0
    request_count: int = 0
    alerts: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PerformanceScalingModule:
    """Performance monitoring and scaling guardrails (kernel v1.0).

    Provides:
    - API response time tracking (rolling window, percentiles)
    - Memory usage monitoring (via /proc/self/status on Linux)
    - Entity count metrics
    - Coordinator update latency tracking
    - Alert thresholds with configurable limits
    - Integration with PerformanceGuardrails rate limiting
    """

    name = "performance_scaling"

    def __init__(self) -> None:
        self._api_response_times: deque[float] = deque(maxlen=500)
        self._coordinator_latencies: deque[float] = deque(maxlen=100)
        self._error_count: int = 0
        self._request_count: int = 0
        self._thresholds: Dict[str, float] = dict(DEFAULT_THRESHOLDS)
        self._alerts: deque[Dict[str, Any]] = deque(maxlen=100)
        self._monitor_task: Optional[asyncio.Task] = None
        self._hass: Optional[HomeAssistant] = None
        self._entry: Optional[ConfigEntry] = None
        self._last_alert_log_ts: Dict[str, float] = {}
        self._suppressed_alerts: Dict[str, int] = {}
        self._alert_streaks: Dict[str, int] = {}

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        self._hass = ctx.hass
        self._entry = ctx.entry
        self._auto_tune_memory_threshold()

        dom = ctx.hass.data.setdefault(DOMAIN, {})
        ent = dom.setdefault(ctx.entry.entry_id, {})
        if not isinstance(ent, dict):
            return

        ent["performance_scaling"] = {
            "kernel_version": "1.0",
            "module": self,
        }

        # Start background monitor (every 60s)
        self._monitor_task = ctx.hass.async_create_task(self._monitor_loop())

        _LOGGER.info(
            "Performance scaling kernel v1.0 active for entry %s (memory threshold: %.0f MB)",
            ctx.entry.entry_id,
            self._thresholds.get("memory_usage_mb_max", 0),
        )

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        data = ctx.hass.data.get(DOMAIN, {}).get(ctx.entry.entry_id)
        if isinstance(data, dict):
            data.pop("performance_scaling", None)

        self._hass = None
        self._entry = None
        return True

    # --- Tracking API (called by coordinator/forwarder) -------------------

    def record_api_response(self, duration_ms: float) -> None:
        """Record an API response time in milliseconds."""
        self._api_response_times.append(duration_ms)
        self._request_count += 1

    def record_api_error(self) -> None:
        """Record an API error."""
        self._error_count += 1
        self._request_count += 1

    def record_coordinator_update(self, duration_ms: float) -> None:
        """Record a coordinator update latency."""
        self._coordinator_latencies.append(duration_ms)

    def set_threshold(self, key: str, value: float) -> None:
        """Set an alert threshold at runtime."""
        if key in self._thresholds:
            self._thresholds[key] = value

    # --- Query API --------------------------------------------------------

    def get_snapshot(self) -> PerformanceSnapshot:
        """Get current performance snapshot."""
        api_times = list(self._api_response_times)
        coord_latency = (
            self._coordinator_latencies[-1]
            if self._coordinator_latencies
            else 0.0
        )

        return PerformanceSnapshot(
            timestamp=time.time(),
            api_response_times_ms=api_times[-20:],
            coordinator_latency_ms=round(coord_latency, 1),
            entity_count=self._count_entities(),
            memory_usage_mb=self._get_memory_mb(),
            error_count=self._error_count,
            request_count=self._request_count,
            alerts=list(self._alerts)[-10:],
        )

    def get_percentiles(self) -> Dict[str, float]:
        """Get API response time percentiles."""
        times = sorted(self._api_response_times)
        if not times:
            return {"p50": 0, "p90": 0, "p95": 0, "p99": 0, "count": 0}

        def percentile(data: list, p: float) -> float:
            idx = int(len(data) * p / 100)
            return data[min(idx, len(data) - 1)]

        return {
            "p50": round(percentile(times, 50), 1),
            "p90": round(percentile(times, 90), 1),
            "p95": round(percentile(times, 95), 1),
            "p99": round(percentile(times, 99), 1),
            "count": len(times),
        }

    def get_guardrails_status(self) -> Dict[str, Any]:
        """Get rate limiter status from PerformanceGuardrails."""
        guardrails = get_guardrails()
        return guardrails.get_status()

    # --- Internal ---------------------------------------------------------

    def _count_entities(self) -> int:
        """Count PilotSuite entities in HA."""
        if not self._hass:
            return 0
        try:
            all_states = self._hass.states.async_all()
            return sum(
                1
                for s in all_states
                if s.entity_id.startswith("sensor.ai_home_copilot")
                or s.entity_id.startswith("button.ai_home_copilot")
                or s.entity_id.startswith("binary_sensor.ai_home_copilot")
            )
        except Exception:
            return 0

    @staticmethod
    def _get_memory_mb() -> float:
        """Get current process memory usage in MB (Linux only)."""
        try:
            with open("/proc/self/status", "r") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        kb = int(line.split()[1])
                        return round(kb / 1024, 1)
        except Exception:
            pass
        return 0.0

    def _check_alerts(self) -> List[Dict[str, Any]]:
        """Check all thresholds and generate alerts."""
        alerts = []
        now = time.time()

        # API response time
        if self._api_response_times:
            avg_ms = sum(self._api_response_times) / len(
                self._api_response_times
            )
            if avg_ms > self._thresholds["api_response_time_ms"]:
                alerts.append(
                    {
                        "type": "api_slow",
                        "message": (
                            f"Average API response {avg_ms:.0f}ms "
                            f"exceeds {self._thresholds['api_response_time_ms']}ms"
                        ),
                        "timestamp": now,
                        "value": avg_ms,
                    }
                )

        # Coordinator latency
        if self._coordinator_latencies:
            latest = self._coordinator_latencies[-1]
            if latest > self._thresholds["coordinator_update_ms"]:
                alerts.append(
                    {
                        "type": "coordinator_slow",
                        "message": (
                            f"Coordinator update {latest:.0f}ms "
                            f"exceeds {self._thresholds['coordinator_update_ms']}ms"
                        ),
                        "timestamp": now,
                        "value": latest,
                    }
                )

        # Entity count
        entity_count = self._count_entities()
        if entity_count > self._thresholds["entity_count_max"]:
            alerts.append(
                {
                    "type": "entity_count_high",
                    "message": (
                        f"Entity count {entity_count} "
                        f"exceeds {self._thresholds['entity_count_max']}"
                    ),
                    "timestamp": now,
                    "value": entity_count,
                }
            )

        # Memory
        memory_mb = self._get_memory_mb()
        mem_key = "memory_high"
        mem_threshold = float(self._thresholds["memory_usage_mb_max"])
        mem_trigger = mem_threshold + MEMORY_ALERT_HEADROOM_MB
        mem_clear = mem_threshold * MEMORY_ALERT_CLEAR_FACTOR
        if memory_mb > mem_trigger:
            streak = self._alert_streaks.get(mem_key, 0) + 1
            self._alert_streaks[mem_key] = streak
            if streak >= ALERT_STREAK_REQUIRED:
                alerts.append(
                    {
                        "type": mem_key,
                        "message": (
                            f"Memory {memory_mb:.1f}MB "
                            f"exceeds {mem_threshold:.0f}MB"
                        ),
                        "timestamp": now,
                        "value": memory_mb,
                        "streak": streak,
                    }
                )
        elif memory_mb < mem_clear:
            self._alert_streaks[mem_key] = 0

        # Error rate
        if self._request_count > 0:
            error_rate = (self._error_count / self._request_count) * 100
            if error_rate > self._thresholds["error_rate_percent"]:
                alerts.append(
                    {
                        "type": "error_rate_high",
                        "message": (
                            f"Error rate {error_rate:.1f}% "
                            f"exceeds {self._thresholds['error_rate_percent']}%"
                        ),
                        "timestamp": now,
                        "value": error_rate,
                    }
                )

        return alerts

    def _auto_tune_memory_threshold(self) -> None:
        """Tune memory threshold to avoid noisy alerts on larger HA hosts.

        Legacy versions used low defaults (256/1536 MB), which are too low for
        modern HA setups with many integrations. We now enforce a sane floor.
        """
        configured = float(self._thresholds.get("memory_usage_mb_max", 0))
        if configured < MIN_REASONABLE_MEMORY_THRESHOLD_MB:
            configured = MIN_REASONABLE_MEMORY_THRESHOLD_MB

        auto_limit = self._detect_memory_limit_mb()
        if auto_limit:
            # Keep headroom for other HA components.
            suggested = max(
                MIN_REASONABLE_MEMORY_THRESHOLD_MB,
                min(8192.0, auto_limit * 0.80),
            )
            configured = max(configured, suggested)

        self._thresholds["memory_usage_mb_max"] = float(configured)

    @staticmethod
    def _detect_memory_limit_mb() -> float | None:
        """Best-effort detection of process/container memory limit."""
        candidates = (
            "/sys/fs/cgroup/memory.max",  # cgroup v2
            "/sys/fs/cgroup/memory/memory.limit_in_bytes",  # cgroup v1
        )
        for path in candidates:
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    raw = handle.read().strip()
                if not raw or raw.lower() == "max":
                    continue
                value = int(raw)
                # Ignore bogus "no limit" values.
                if value <= 0 or value >= 1 << 60:
                    continue
                return round(value / (1024 * 1024), 1)
            except Exception:
                continue

        # Fallback to MemTotal from /proc/meminfo.
        try:
            with open("/proc/meminfo", "r", encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("MemTotal:"):
                        parts = line.split()
                        if len(parts) >= 2:
                            kb = int(parts[1])
                            if kb > 0:
                                return round(kb / 1024, 1)
                        break
        except Exception:
            pass

        env_limit = os.environ.get("HASS_MEMORY_LIMIT_MB")
        if env_limit:
            try:
                parsed = float(env_limit)
                if parsed > 0:
                    return parsed
            except ValueError:
                return None
        return None

    async def _monitor_loop(self) -> None:
        """Background task: check alerts every 60 seconds."""
        while True:
            try:
                await asyncio.sleep(60)
                alerts = self._check_alerts()
                for alert in alerts:
                    self._alerts.append(alert)
                    self._log_alert(alert)
            except asyncio.CancelledError:
                break
            except Exception:
                _LOGGER.exception("Performance monitor error")

    def _log_alert(self, alert: Dict[str, Any]) -> None:
        """Log an alert with duplicate-throttling."""
        alert_type = str(alert.get("type", "unknown"))
        now = time.time()
        last_logged = self._last_alert_log_ts.get(alert_type, 0.0)
        if (now - last_logged) < ALERT_LOG_THROTTLE_S:
            self._suppressed_alerts[alert_type] = self._suppressed_alerts.get(alert_type, 0) + 1
            return

        suppressed = self._suppressed_alerts.pop(alert_type, 0)
        self._last_alert_log_ts[alert_type] = now
        if suppressed:
            _LOGGER.warning(
                "Performance alert: %s (plus %d duplicate alerts suppressed)",
                alert["message"],
                suppressed,
            )
        else:
            _LOGGER.warning("Performance alert: %s", alert["message"])
