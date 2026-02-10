"""Simple unit tests for N3 Event Forwarder."""
import asyncio
import sys
import traceback
from unittest.mock import Mock
from datetime import datetime, timezone

sys.path.insert(0, '/config/.openclaw/workspace/ai_home_copilot_hacs_repo')

from custom_components.ai_home_copilot.forwarder_n3 import (
    N3EventForwarder,
    ENVELOPE_VERSION,
)


class MockState:
    """Mock HA state object."""
    def __init__(self, state: str, attributes: dict = None, last_changed=None, last_updated=None, context=None):
        self.state = state
        self.attributes = attributes or {}
        self.last_changed = last_changed or datetime.now(timezone.utc)
        self.last_updated = last_updated or datetime.now(timezone.utc)
        self.context = context


class MockContext:
    """Mock HA context object."""
    def __init__(self, id: str = "test-context-id", user_id: str = None, parent_id: str = None):
        self.id = id
        self.user_id = user_id
        self.parent_id = parent_id


class MockEvent:
    """Mock HA event object."""
    def __init__(self, event_type: str, data: dict, context=None):
        self.event_type = event_type
        self.data = data
        self.context = context or MockContext()


def create_mock_hass():
    """Create mock HomeAssistant instance."""
    hass = Mock()
    
    # Mock registries
    entity_registry = Mock()
    entity_registry.entities.values.return_value = []
    hass.helpers.entity_registry.async_get.return_value = entity_registry
    
    area_registry = Mock()
    hass.helpers.area_registry.async_get.return_value = area_registry
    
    device_registry = Mock()
    hass.helpers.device_registry.async_get.return_value = device_registry
    
    return hass


def create_forwarder_config():
    """Create default forwarder configuration."""
    return {
        "core_url": "http://localhost:8099",
        "api_token": "test-token",
        "enabled_domains": ["light", "sensor"],
        "batch_size": 10,
        "flush_interval": 0.1,
        "forward_call_service": True,
    }


def test_init():
    """Test forwarder initialization."""
    mock_hass = create_mock_hass()
    config = create_forwarder_config()
    
    forwarder = N3EventForwarder(mock_hass, config)
    
    assert forwarder.hass == mock_hass
    assert forwarder._core_url == "http://localhost:8099"
    assert forwarder._api_token == "test-token"
    assert forwarder._batch_size == 10
    assert forwarder._flush_interval == 0.1
    assert "light" in forwarder._enabled_domains
    assert "sensor" in forwarder._enabled_domains


def test_project_attributes_light():
    """Test attribute projection for light domain."""
    mock_hass = create_mock_hass()
    config = create_forwarder_config()
    forwarder = N3EventForwarder(mock_hass, config)
    
    # Test with light attributes
    attrs = {
        "brightness": 180,
        "color_temp": 380,
        "rgb_color": [255, 0, 0],
        "friendly_name": "Test Light",  # Should be redacted by default
        "supported_features": 123,  # Not in projection list
        "entity_picture": "/image.png",  # Redacted for privacy
    }
    
    projected = forwarder._project_attributes("light", attrs)
    
    assert projected["brightness"] == 180
    assert projected["color_temp"] == 380
    assert projected["rgb_color"] == [255, 0, 0]
    assert "friendly_name" not in projected
    assert "supported_features" not in projected
    assert "entity_picture" not in projected


def test_project_attributes_sensor():
    """Test attribute projection for sensor domain."""
    mock_hass = create_mock_hass()
    config = create_forwarder_config()
    forwarder = N3EventForwarder(mock_hass, config)
    
    attrs = {
        "unit_of_measurement": "°C",
        "device_class": "temperature",
        "state_class": "measurement",
        "friendly_name": "Temperature Sensor",
        "custom_attr": "should_not_appear",
    }
    
    projected = forwarder._project_attributes("sensor", attrs)
    
    assert projected["unit_of_measurement"] == "°C"
    assert projected["device_class"] == "temperature"
    assert projected["state_class"] == "measurement"
    assert "friendly_name" not in projected
    assert "custom_attr" not in projected


def test_project_attributes_unknown_domain():
    """Test attribute projection for unknown domain."""
    mock_hass = create_mock_hass()
    config = create_forwarder_config()
    forwarder = N3EventForwarder(mock_hass, config)
    
    attrs = {
        "some_attr": "value",
        "another_attr": 123,
    }
    
    # Unknown domains should project no attributes
    projected = forwarder._project_attributes("unknown_domain", attrs)
    assert projected == {}


def test_redact_context_id():
    """Test context ID redaction."""
    mock_hass = create_mock_hass()
    config = create_forwarder_config()
    forwarder = N3EventForwarder(mock_hass, config)
    
    full_context_id = "01234567-89ab-cdef-0123-456789abcdef"
    
    # Default: truncate to 12 chars
    redacted = forwarder._redact_context_id(full_context_id)
    assert redacted == "01234567-89a"
    assert len(redacted) == 12
    
    # With keep_full_context_ids enabled
    forwarder._keep_full_context_ids = True
    redacted = forwarder._redact_context_id(full_context_id)
    assert redacted == full_context_id


def test_extract_entity_ids_from_service_data():
    """Test entity ID extraction from service data."""
    mock_hass = create_mock_hass()
    config = create_forwarder_config()
    forwarder = N3EventForwarder(mock_hass, config)
    
    # Single entity_id as string
    service_data = {"entity_id": "light.test"}
    entity_ids = forwarder._extract_entity_ids_from_service_data(service_data)
    assert entity_ids == ["light.test"]
    
    # Multiple entity_ids as list
    service_data = {"entity_id": ["light.test1", "light.test2"]}
    entity_ids = forwarder._extract_entity_ids_from_service_data(service_data)
    assert entity_ids == ["light.test1", "light.test2"]
    
    # No entity_id
    service_data = {"some_other_param": "value"}
    entity_ids = forwarder._extract_entity_ids_from_service_data(service_data)
    assert entity_ids == []


def test_should_forward_entity_debounce():
    """Test entity debouncing logic."""
    mock_hass = create_mock_hass()
    config = create_forwarder_config()
    forwarder = N3EventForwarder(mock_hass, config)
    forwarder._debounce_intervals = {"sensor": 1.0}
    
    entity_id = "sensor.test"
    
    # First call should be allowed
    assert forwarder._should_forward_entity(entity_id, "sensor") == True
    
    # Immediate second call should be blocked
    assert forwarder._should_forward_entity(entity_id, "sensor") == False
    
    # Different entity should be allowed
    assert forwarder._should_forward_entity("sensor.other", "sensor") == True
    
    # Domain without debounce should always be allowed
    assert forwarder._should_forward_entity("light.test", "light") == True
    assert forwarder._should_forward_entity("light.test", "light") == True


def test_is_event_new_idempotency():
    """Test event idempotency checking."""
    mock_hass = create_mock_hass()
    config = create_forwarder_config()
    forwarder = N3EventForwarder(mock_hass, config)
    forwarder._idempotency_ttl = 10  # 10 seconds TTL
    
    event_key = "state_changed:test-context-id"
    
    # First occurrence should be new
    assert forwarder._is_event_new(event_key) == True
    
    # Immediate duplicate should not be new
    assert forwarder._is_event_new(event_key) == False
    
    # Different event should be new
    assert forwarder._is_event_new("state_changed:other-context-id") == True
    
    # With TTL disabled
    forwarder._idempotency_ttl = 0
    assert forwarder._is_event_new(event_key) == True  # Should always be true


def test_create_state_change_envelope():
    """Test state change envelope creation."""
    mock_hass = create_mock_hass()
    config = create_forwarder_config()
    forwarder = N3EventForwarder(mock_hass, config)
    forwarder._entity_to_zone = {"light.test": "living_room"}
    
    # Create mock states and event
    old_state = MockState("off", {"brightness": 0})
    new_state = MockState("on", {"brightness": 180, "color_temp": 380})
    context = MockContext("test-context-123", user_id="user-123")
    event = MockEvent("state_changed", {"entity_id": "light.test"}, context)
    
    envelope = forwarder._create_state_change_envelope(
        "light.test", "light", old_state, new_state, event
    )
    
    # Verify envelope structure
    assert envelope["v"] == ENVELOPE_VERSION
    assert envelope["src"] == "ha"
    assert envelope["kind"] == "state_changed"
    assert envelope["entity_id"] == "light.test"
    assert envelope["domain"] == "light"
    assert envelope["zone_id"] == "living_room"
    assert envelope["context_id"] == "test-context"  # Truncated
    assert envelope["trigger"] == "user"  # Because user_id is set
    
    # Verify state data
    assert envelope["old"]["state"] == "off"
    assert envelope["old"]["attrs"]["brightness"] == 0
    assert envelope["new"]["state"] == "on"
    assert envelope["new"]["attrs"]["brightness"] == 180
    assert envelope["new"]["attrs"]["color_temp"] == 380
    
    # Verify timestamps exist
    assert "ts" in envelope
    assert "last_changed" in envelope
    assert "last_updated" in envelope


def test_create_call_service_envelope():
    """Test call_service envelope creation."""
    mock_hass = create_mock_hass()
    config = create_forwarder_config()
    forwarder = N3EventForwarder(mock_hass, config)
    forwarder._entity_to_zone = {
        "light.test1": "living_room",
        "light.test2": "kitchen"
    }
    
    context = MockContext("service-context-456", parent_id="automation-123")
    event = MockEvent("call_service", {"domain": "light", "service": "turn_on"}, context)
    
    entity_ids = ["light.test1", "light.test2"]
    
    envelope = forwarder._create_call_service_envelope(
        "light", "turn_on", entity_ids, event
    )
    
    # Verify envelope structure
    assert envelope["v"] == ENVELOPE_VERSION
    assert envelope["src"] == "ha"
    assert envelope["kind"] == "call_service"
    assert envelope["entity_id"] == "light.test1"  # First entity
    assert envelope["domain"] == "light"
    assert envelope["zone_id"] == "living_room"  # First zone
    assert envelope["context_id"] == "service-cont"  # Truncated
    assert envelope["trigger"] == "automation"  # Because parent_id is set
    assert envelope["service"] == "turn_on"
    assert envelope["entity_ids"] == entity_ids
    assert envelope["zone_ids"] == ["kitchen", "living_room"]  # Sorted


async def test_enqueue_event_max_queue_size():
    """Test event queue size limiting."""
    mock_hass = create_mock_hass()
    config = create_forwarder_config()
    config["max_queue_size"] = 3
    forwarder = N3EventForwarder(mock_hass, config)
    
    # Mock session to prevent actual HTTP calls
    forwarder._session = Mock()
    
    # Add events up to limit
    for i in range(5):  # More than max_queue_size
        envelope = {"test": f"event_{i}"}
        await forwarder._enqueue_event(envelope)
    
    # Should only keep the last max_queue_size events
    assert len(forwarder._pending_events) == 3
    assert forwarder._pending_events[0]["test"] == "event_2"
    assert forwarder._pending_events[1]["test"] == "event_3"
    assert forwarder._pending_events[2]["test"] == "event_4"


def run_test(test_func):
    """Run a single test function."""
    try:
        if asyncio.iscoroutinefunction(test_func):
            asyncio.run(test_func())
        else:
            test_func()
        print(f"✓ {test_func.__name__}")
        return True
    except Exception as e:
        print(f"✗ {test_func.__name__}: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    test_functions = [
        test_init,
        test_project_attributes_light,
        test_project_attributes_sensor,
        test_project_attributes_unknown_domain,
        test_redact_context_id,
        test_extract_entity_ids_from_service_data,
        test_should_forward_entity_debounce,
        test_is_event_new_idempotency,
        test_create_state_change_envelope,
        test_create_call_service_envelope,
        test_enqueue_event_max_queue_size,
    ]
    
    tests_passed = 0
    tests_total = len(test_functions)
    
    for test_func in test_functions:
        if run_test(test_func):
            tests_passed += 1
    
    print(f"\nResults: {tests_passed}/{tests_total} tests passed")
    
    if tests_passed == tests_total:
        print("All N3 Forwarder tests passed!")
        return 0
    else:
        print("Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())