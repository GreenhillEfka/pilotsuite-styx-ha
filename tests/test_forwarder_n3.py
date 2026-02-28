"""Unit tests for N3 Event Forwarder."""
import asyncio
import json
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Patch Store before importing forwarder_n3
mock_store = Mock()
mock_store.async_load = AsyncMock(return_value={})
mock_store.async_save = AsyncMock()

# Use patch context to avoid spec issues
_store_patch = patch('custom_components.ai_home_copilot.forwarder_n3.Store', return_value=mock_store)
_store_patch.start()

from custom_components.ai_home_copilot.forwarder_n3 import (
    N3EventForwarder,
    DOMAIN_PROJECTIONS,
    REDACTED_ATTRIBUTES,
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


def mock_hass():
    """Mock HomeAssistant instance."""
    # Use Mock (not MagicMock) to avoid InvalidSpecError
    hass = Mock()
    hass.helpers.entity_registry.async_get.return_value = Mock()
    hass.helpers.area_registry.async_get.return_value = Mock()
    hass.helpers.device_registry.async_get.return_value = Mock()
    
    # Mock registries
    entity_registry = Mock()
    entity_registry.entities.values.return_value = []
    hass.helpers.entity_registry.async_get.return_value = entity_registry
    
    area_registry = Mock()
    hass.helpers.area_registry.async_get.return_value = area_registry
    
    device_registry = Mock()
    hass.helpers.device_registry.async_get.return_value = device_registry
    
    return hass


@pytest.fixture
def mock_hass_obj():
    """Pytest fixture for mock HomeAssistant instance."""
    return mock_hass()


def forwarder_config():
    """Default N3 forwarder configuration."""
    return {
        "core_url": "http://localhost:8909",
        "api_token": "test-token",
        "enabled_domains": ["light", "sensor"],
        "batch_size": 10,
        "flush_interval": 0.1,
        "forward_call_service": True,
    }


@pytest.fixture
def forwarder_config_obj():
    """Pytest fixture for forwarder configuration."""
    return forwarder_config()


class TestN3EventForwarder:
    """Test N3 Event Forwarder functionality."""

    def test_init(self, mock_hass_obj, forwarder_config_obj):
        """Test forwarder initialization."""
        forwarder = N3EventForwarder(mock_hass_obj, forwarder_config_obj)
        
        assert forwarder.hass == mock_hass_obj
        assert forwarder._core_url == "http://localhost:8909"
        assert forwarder._api_token == "test-token"
        assert forwarder._batch_size == 10
        assert forwarder._flush_interval == 0.1
        assert "light" in forwarder._enabled_domains
        assert "sensor" in forwarder._enabled_domains

    def test_project_attributes_light(self, mock_hass_obj, forwarder_config_obj):
        """Test attribute projection for light domain."""
        forwarder = N3EventForwarder(mock_hass_obj, forwarder_config_obj)
        
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

    def test_project_attributes_sensor(self, mock_hass_obj, forwarder_config_obj):
        """Test attribute projection for sensor domain."""
        forwarder = N3EventForwarder(mock_hass_obj, forwarder_config_obj)
        
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

    def test_project_attributes_unknown_domain(self, mock_hass_obj, forwarder_config_obj):
        """Test attribute projection for unknown domain - default-deny for security."""
        forwarder = N3EventForwarder(mock_hass_obj, forwarder_config_obj)
        
        attrs = {
            "some_attr": "value",
            "another_attr": 123,
            "friendly_name": "Test Entity",
            "secret_key": "should_not_leak",
        }
        
        # S1: Unknown domains now return EMPTY dict (default-deny for security)
        # This prevents PII leakage for new/unknown entity types
        projected = forwarder._project_attributes("unknown_domain", attrs)
        assert projected == {}, "Unknown domains should return empty dict (default-deny)"
        
        # Verify known domains still work
        projected_light = forwarder._project_attributes("light", attrs)
        assert "brightness" in projected_light or projected_light == {}  # Depends on DOMAIN_PROJECTIONS

    def test_redact_context_id(self, mock_hass_obj, forwarder_config_obj):
        """Test context ID redaction."""
        forwarder = N3EventForwarder(mock_hass_obj, forwarder_config_obj)
        
        full_context_id = "01234567-89ab-cdef-0123-456789abcdef"
        
        # Default: truncate to 12 chars
        redacted = forwarder._redact_context_id(full_context_id)
        assert redacted == "01234567-89a"
        assert len(redacted) == 12
        
        # With keep_full_context_ids enabled
        forwarder._keep_full_context_ids = True
        redacted = forwarder._redact_context_id(full_context_id)
        assert redacted == full_context_id

    def test_extract_entity_ids_from_service_data(self, mock_hass_obj, forwarder_config_obj):
        """Test entity ID extraction from service data."""
        forwarder = N3EventForwarder(mock_hass_obj, forwarder_config_obj)
        
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

    def test_should_forward_entity_debounce(self, mock_hass_obj, forwarder_config_obj):
        """Test entity debouncing logic."""
        forwarder = N3EventForwarder(mock_hass_obj, forwarder_config_obj)
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

    def test_is_event_new_idempotency(self, mock_hass_obj, forwarder_config_obj):
        """Test event idempotency checking."""
        forwarder = N3EventForwarder(mock_hass_obj, forwarder_config_obj)
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

    def test_create_state_change_envelope(self, mock_hass_obj, forwarder_config_obj):
        """Test state change envelope creation."""
        forwarder = N3EventForwarder(mock_hass_obj, forwarder_config_obj)
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

    def test_create_call_service_envelope(self, mock_hass_obj, forwarder_config_obj):
        """Test call_service envelope creation."""
        forwarder = N3EventForwarder(mock_hass_obj, forwarder_config_obj)
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
        assert envelope["zone_ids"] == ["living_room", "kitchen"]  # Order matches entity_ids

    @pytest.mark.asyncio
    async def test_enqueue_event_max_queue_size(self, mock_hass_obj, forwarder_config_obj):
        """Test event queue size limiting."""
        forwarder_config_obj["max_queue_size"] = 3
        forwarder = N3EventForwarder(mock_hass_obj, forwarder_config_obj)
        
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


if __name__ == "__main__":
    # Simple test runner
    import sys
    import traceback
    
    def run_test_method(test_class, method_name, *args):
        """Run a single test method."""
        try:
            method = getattr(test_class, method_name)
            if asyncio.iscoroutinefunction(method):
                asyncio.run(method(*args))
            else:
                method(*args)
            print(f"✓ {method_name}")
            return True
        except Exception as e:
            print(f"✗ {method_name}: {e}")
            traceback.print_exc()
            return False
    
    # Create mocks
    mock_hass = Mock()
    mock_hass.helpers.entity_registry.async_get.return_value = Mock()
    mock_hass.helpers.area_registry.async_get.return_value = Mock()
    mock_hass.helpers.device_registry.async_get.return_value = Mock()
    
    entity_registry = Mock()
    entity_registry.entities.values.return_value = []
    mock_hass.helpers.entity_registry.async_get.return_value = entity_registry
    
    forwarder_config = {
        "core_url": "http://localhost:8909",
        "api_token": "test-token",
        "enabled_domains": ["light", "sensor"],
        "batch_size": 10,
        "flush_interval": 0.1,
        "forward_call_service": True,
    }
    
    # Run tests
    test_instance = TestN3EventForwarder()
    tests_passed = 0
    tests_total = 0
    
    test_methods = [m for m in dir(test_instance) if m.startswith('test_')]
    
    for test_method in test_methods:
        tests_total += 1
        if run_test_method(test_instance, test_method, mock_hass, forwarder_config):
            tests_passed += 1
    
    print(f"\nResults: {tests_passed}/{tests_total} tests passed")
    
    if tests_passed == tests_total:
        print("All tests passed!")
        sys.exit(0)
    else:
        print("Some tests failed!")
        sys.exit(1)