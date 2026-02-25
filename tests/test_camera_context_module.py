"""Tests for camera context forwarding scheduling."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from custom_components.ai_home_copilot.core.modules.camera_context_module import (
    CameraContextModule,
    MotionAction,
)


class _FakeHass:
    def __init__(self) -> None:
        self.bus = MagicMock()

    def async_create_task(self, coro):
        return asyncio.create_task(coro)


@pytest.mark.asyncio
async def test_process_motion_schedules_forward_task() -> None:
    module = CameraContextModule()
    module._hass = _FakeHass()

    seen: asyncio.Queue = asyncio.Queue()

    async def _fake_forward(event_subtype: str, context: dict) -> None:
        await seen.put((event_subtype, context))

    module._forward_to_brain = _fake_forward  # type: ignore[method-assign]

    module._process_motion_to_neuron(
        {
            "camera_id": "cam_1",
            "camera_name": "Wohnzimmer Cam",
            "action": MotionAction.STARTED.value,
            "confidence": 0.9,
            "timestamp": "2026-02-25T16:00:00",
        }
    )

    subtype, context = await asyncio.wait_for(seen.get(), timeout=1.0)
    assert subtype == "motion"
    assert context["camera_id"] == "cam_1"

    # Task cleanup callback should remove finished tasks from the registry.
    await asyncio.sleep(0)
    assert not module._forward_tasks


@pytest.mark.asyncio
async def test_async_unload_cancels_pending_forward_tasks() -> None:
    module = CameraContextModule()
    module._hass = _FakeHass()

    gate = asyncio.Event()

    async def _blocking_forward(_event_subtype: str, _context: dict) -> None:
        await gate.wait()

    module._forward_to_brain = _blocking_forward  # type: ignore[method-assign]

    module._process_motion_to_neuron(
        {
            "camera_id": "cam_2",
            "camera_name": "Flur Cam",
            "action": MotionAction.STARTED.value,
            "confidence": 1.0,
            "timestamp": "2026-02-25T16:00:00",
        }
    )

    # Allow task to be created.
    await asyncio.sleep(0)
    assert module._forward_tasks

    ok = await module.async_unload_entry(SimpleNamespace())
    assert ok is True
    assert not module._forward_tasks

    gate.set()
