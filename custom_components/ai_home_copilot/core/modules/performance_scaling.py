from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ...const import DOMAIN
from ..module import ModuleContext

_LOGGER = logging.getLogger(__name__)


class PerformanceScalingModule:
    """Performance & scaling guardrails (kernel v0.1).

    This module intentionally stays lightweight and primarily provides:
    - a stable place to attach future performance instrumentation
    - a single runtime hook point for entry-scoped scaling settings

    The core behavior changes for v0.1 live in the coordinator + forwarder:
    - coordinator backoff + concurrency limits
    - bounded in-memory queues + flush concurrency guard
    """

    name = "performance_scaling"

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        hass: HomeAssistant = ctx.hass
        entry: ConfigEntry = ctx.entry

        dom = hass.data.setdefault(DOMAIN, {})
        ent = dom.setdefault(entry.entry_id, {})
        if not isinstance(ent, dict):
            return

        # Expose a tiny, stable diagnostic surface. (Read by future sensors/diagnostics.)
        ent.setdefault(
            "performance_scaling",
            {
                "kernel_version": "0.1",
            },
        )

        _LOGGER.debug("Performance scaling kernel v0.1 active for entry %s", entry.entry_id)

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        hass: HomeAssistant = ctx.hass
        entry: ConfigEntry = ctx.entry

        data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if isinstance(data, dict):
            data.pop("performance_scaling", None)
        return True
