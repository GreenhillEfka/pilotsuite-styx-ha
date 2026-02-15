"""Unit tests for entity_id sanitization in brain_graph_sync."""
import pytest
from custom_components.ai_home_copilot.brain_graph_sync import (
    sanitize_entity_id,
    sanitize_node_id,
)


class TestEntityIdSanitization:
    """Tests for entity_id sanitization security fixes."""

    def test_sanitize_normal_entity_id(self):
        """Test that normal entity IDs pass through unchanged."""
        assert sanitize_entity_id("light.kitchen") == "light.kitchen"
        assert sanitize_entity_id("sensor.temperature_living_room") == "sensor.temperature_living_room"
        assert sanitize_entity_id("switch.garden_light_1") == "switch.garden_light_1"

    def test_sanitize_entity_id_with_special_chars(self):
        """Test that special characters are replaced."""
        # Path traversal attempts
        assert sanitize_entity_id("light../../../etc/passwd") == "light_etc_passwd"
        assert sanitize_entity_id("sensor.<script>alert('xss')</script>") == "sensor.script_alert_xss_script"
        
        # SQL injection attempts (though not used in SQL)
        assert sanitize_entity_id("light'; DROP TABLE--") == "light_DROP_TABLE"
        
        # Newline injection
        assert sanitize_entity_id("light.kitchen\nmalicious") == "light.kitchen_malicious"

    def test_sanitize_entity_id_unicode(self):
        """Test that unicode characters are handled."""
        # Unicode chars are replaced
        assert sanitize_entity_id("light.küche") == "light.k_che"
        assert sanitize_entity_id("sensor.温度") == "sensor_"

    def test_sanitize_entity_id_empty(self):
        """Test empty entity_id returns 'unknown'."""
        assert sanitize_entity_id("") == "unknown"
        assert sanitize_entity_id(None) == "unknown"

    def test_sanitize_entity_id_multiple_underscores(self):
        """Test that multiple underscores are collapsed."""
        assert sanitize_entity_id("light..kitchen...lamp") == "light.kitchen.lamp"
        assert sanitize_entity_id("sensor___test") == "sensor_test"

    def test_sanitize_node_id(self):
        """Test node ID construction with sanitization."""
        assert sanitize_node_id("entity", "light.kitchen") == "entity:light.kitchen"
        assert sanitize_node_id("area", "living_room") == "area:living_room"
        assert sanitize_node_id("device", "abc-123-xyz") == "device:abc-123-xyz"

    def test_sanitize_node_id_malicious_input(self):
        """Test node ID construction with malicious input."""
        # Path traversal in identifier
        node_id = sanitize_node_id("entity", "../../../etc/passwd")
        assert node_id == "entity:_etc_passwd"
        assert ".." not in node_id
        assert "/" not in node_id

    def test_sanitize_preserves_domain_structure(self):
        """Test that domain.entity structure is preserved."""
        result = sanitize_entity_id("light.kitchen_ceiling")
        assert result.startswith("light.")
        assert "." in result  # Domain separator preserved
        
    def test_sanitize_state_values(self):
        """Test sanitization of state values (can be arbitrary strings)."""
        # States can be user-defined strings
        assert sanitize_entity_id("on") == "on"
        assert sanitize_entity_id("off") == "off"
        assert sanitize_entity_id("heat_cool") == "heat_cool"
        assert sanitize_entity_id("playing<podcast>") == "playing_podcast"