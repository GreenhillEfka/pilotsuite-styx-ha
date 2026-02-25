from __future__ import annotations

from custom_components.ai_home_copilot.binary_sensor import CopilotOnlineBinarySensor
from custom_components.ai_home_copilot.pipeline_health_entities import PipelineHealthSensor


class _DummyCoordinator:
    def __init__(self, data: dict | None) -> None:
        self.data = data
        self._config = {"host": "127.0.0.1", "port": 8909}
        self.last_update_success = True

    def async_add_listener(self, _update_callback):
        return lambda: None


def test_online_binary_sensor_reads_dict_payload() -> None:
    sensor = CopilotOnlineBinarySensor(_DummyCoordinator({"ok": True}))
    assert sensor.is_on is True


def test_online_binary_sensor_handles_missing_ok() -> None:
    sensor = CopilotOnlineBinarySensor(_DummyCoordinator({"version": "x"}))
    assert sensor.is_on is None


def test_pipeline_health_sensor_uses_dict_status() -> None:
    sensor = PipelineHealthSensor(_DummyCoordinator({"ok": True, "version": "7.7.13"}))

    assert sensor.native_value == "healthy"
    attrs = sensor.extra_state_attributes
    assert attrs["core_ok"] is True
    assert attrs["core_version"] == "7.7.13"
