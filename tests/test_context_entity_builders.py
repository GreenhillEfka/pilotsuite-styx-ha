from __future__ import annotations

from types import SimpleNamespace

from custom_components.ai_home_copilot.core.module import ModuleContext
from custom_components.ai_home_copilot.unifi_context_entities import (
    build_unifi_binary_entities,
    build_unifi_sensor_entities,
)
from custom_components.ai_home_copilot.weather_context_entities import build_weather_entities


class _DummyEntry:
    entry_id = "entry-123"
    domain = "ai_home_copilot"


def test_module_context_exposes_compat_properties() -> None:
    ctx = ModuleContext(hass=object(), entry=_DummyEntry())
    assert ctx.entry_id == "entry-123"
    assert ctx.domain == "ai_home_copilot"


def test_weather_entities_builder_shape() -> None:
    entities = build_weather_entities(SimpleNamespace(data=None))
    assert len(entities) == 7
    assert entities[0]._attr_unique_id == "ai_home_copilot_weather_condition"


def test_unifi_entities_builder_shape() -> None:
    sensor_entities = build_unifi_sensor_entities(SimpleNamespace(data=None))
    binary_entities = build_unifi_binary_entities(SimpleNamespace(data=None))
    assert len(sensor_entities) == 4
    assert len(binary_entities) == 2
    assert sensor_entities[0]._attr_unique_id == "ai_home_copilot_unifi_clients_online"
    assert binary_entities[0]._attr_unique_id == "ai_home_copilot_unifi_wan_online"
