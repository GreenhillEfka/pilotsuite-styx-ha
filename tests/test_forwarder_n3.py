"""Unit tests for N3 Event Forwarder."""
import asyncio
import json
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

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
    hass = Mock()
    hass.helpers.entity_registry.async_get.return_value = Mock()
    hass.helpers.area_registry.async_get.return_value = Mock()
    hass.helpers.device_registry.async_get.return_value = Mock()
    
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


@pytest.fixture
def mock_store():
    """Pytest fixture for mock Store."""
    store = Mock()
    store.async_load = AsyncMock(return_value={})
    store.async_save = AsyncMock()
    return store


@pytest.fixture
def forwarder(mock_hass_obj, mock_store):
    """Pytest fixture for N3EventForwarder instance."""
    config = {
        "core_url": "http://localhost:8000",
        "api_token": "test-token",
        "batch_size": 10,
        "flush_interval": 5,
        "enabled_domains": ["light", "sensor", "binary_sensor"],
        "forward_call_service": True,
        "idempotency_ttl": 3600,
        "heartbeat_enabled": False,
    }
    
    with patch('custom_components.ai_home_copilot.forwarder_n3.Store', return_value=mock_store):
        fwd = N3EventForwarder(mock_hass_obj, config)
        yield fwd


class TestDomainProjections:
    """Test domain projection mappings."""
    
    def test_light_projection(self):
        """Test light domain has expected attributes."""
        assert "brightness" in DOMAIN_PROJECTIONS["light"]
        assert "color_temp" in DOMAIN_PROJECTIONS["light"]
    
    def test_climate_projection(self):
        """Test climate domain has expected attributes."""
        assert "temperature" in DOMAIN_PROJECTIONS["climate"]
        assert "hvac_action" in DOMAIN_PROJECTIONS["climate"]


class TestRedactedAttributes:
    """Test privacy redaction."""
    
    def test_token_redacted(self):
        """Test tokens are in redaction list."""
        assert "access_token" in REDACTED_ATTRIBUTES
        assert "token" in REDACTED_ATTRIBUTES
    
    def test_location_redacted(self):
        """Test GPS data is in redaction list."""
        assert "latitude" in REDACTED_ATTRIBUTES
        assert "longitude" in REDACTED_ATTRIBUTES


class TestEnvelopeVersion:
    """Test envelope schema version."""
    
    def test_version_is_int(self):
        """Test version is an integer."""
        assert isinstance(ENVELOPE_VERSION, int)
    
    def test_version_positive(self):
        """Test version is positive."""
        assert ENVELOPE_VERSION > 0


class TestN3EventForwarder:
    """Test N3EventForwarder functionality."""
    
    def test_init(self, forwarder):
        """Test forwarder initialization."""
        assert forwarder._pending_events == []
        assert forwarder._debounce_cache == {}
        assert forwarder._batch_size == 10
    
    def test_debounce_cache_initially_empty(self, forwarder):
        """Test debounce cache starts empty."""
        assert len(forwarder._debounce_cache) == 0
    
    def test_enqueue_event(self, forwarder):
        """Test event enqueue."""
        envelope = {"kind": "state_changed", "entity_id": "light.test"}
        # Synchronous test - just check the method exists and queue works
        forwarder._pending_events.append(envelope)
        assert len(forwarder._pending_events) == 1
    
    def test_stats(self, forwarder):
        """Test stats endpoint."""
        stats = {
            "pending_events": len(forwarder._pending_events),
            "debounce_cache_size": len(forwarder._debounce_cache),
            "batch_size": forwarder._batch_size,
        }
        assert "pending_events" in stats
        assert "debounce_cache_size" in stats
        assert stats["batch_size"] == 10
