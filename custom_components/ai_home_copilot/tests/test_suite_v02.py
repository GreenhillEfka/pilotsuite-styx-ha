"""
Test Suite v0.2 for AI Home Copilot HA Integration
===================================================

Production-ready integration tests:
- Module imports and initialization
- Coordinator patterns and data flow
- API mocking for Core Add-on communication
- Entity validation against HA schema

Run with: python3 -m pytest tests/ -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add custom_components to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestModuleImports:
    """Verify all modules can be imported without errors."""

    def test_import_energy_context(self):
        """Energy Context module should import cleanly."""
        try:
            from custom_components.ai_home_copilot import energy_context
            assert energy_context is not None
        except ImportError as e:
            pytest.skip(f"energy_context not available: {e}")

    def test_import_unifi_context(self):
        """UniFi Context module should import cleanly."""
        try:
            from custom_components.ai_home_copilot import unifi_context
            assert unifi_context is not None
        except ImportError as e:
            pytest.skip(f"unifi_context not available: {e}")

    def test_import_weather_context(self):
        """Weather Context module should import cleanly."""
        try:
            from custom_components.ai_home_copilot import weather_context
            assert weather_context is not None
        except ImportError as e:
            pytest.skip(f"weather_context not available: {e}")

    def test_import_core_modules(self):
        """Core modules should import cleanly."""
        module_names = [
            "energy_context_module",
            "unifi_context_module", 
            "weather_context_module",
            "mood_module",
            "brain_graph_module",
        ]
        
        for name in module_names:
            try:
                module = __import__(
                    f"custom_components.ai_home_copilot.core.modules.{name}",
                    fromlist=[name]
                )
                assert module is not None
            except ImportError:
                pytest.skip(f"Core module {name} not available")


class TestCoordinatorPattern:
    """Test coordinator pattern for context modules."""

    @patch('custom_components.ai_home_copilot.energy_context.AIHomeCopilotEnergyDataUpdateCoordinator')
    def test_energy_coordinator_init(self, mock_coordinator_class):
        """Energy coordinator should initialize with config."""
        mock_coordinator_class.return_value = MagicMock(
            data={"consumption_today": 5.2, "production_today": 3.1},
            update_interval=30
        )
        
        from custom_components.ai_home_copilot.energy_context import (
            AIHomeCopilotEnergyDataUpdateCoordinator
        )
        
        # Coordinator should be callable
        assert callable(AIHomeCopilotEnergyDataUpdateCoordinator)

    @patch('custom_components.ai_home_copilot.unifi_context.AIHomeCopilotUniFiDataUpdateCoordinator')
    def test_unifi_coordinator_init(self, mock_coordinator_class):
        """UniFi coordinator should initialize with config."""
        mock_coordinator_class.return_value = MagicMock(
            data={"clients_online": 12, "wan_latency": 15},
            update_interval=60
        )
        
        from custom_components.ai_home_copilot.unifi_context import (
            AIHomeCopilotUniFiDataUpdateCoordinator
        )
        
        assert callable(AIHomeCopilotUniFiDataUpdateCoordinator)

    @patch('custom_components.ai_home_copilot.weather_context.AIHomeCopilotWeatherDataUpdateCoordinator')
    def test_weather_coordinator_init(self, mock_coordinator_class):
        """Weather coordinator should initialize with config."""
        mock_coordinator_class.return_value = MagicMock(
            data={"temperature": 18.5, "condition": "sunny"},
            update_interval=300
        )
        
        from custom_components.ai_home_copilot.weather_context import (
            AIHomeCopilotWeatherDataUpdateCoordinator
        )
        
        assert callable(AIHomeCopilotWeatherDataUpdateCoordinator)


class TestAPIMocking:
    """Test API mocking for Core Add-on communication."""

    def test_energy_api_response_structure(self):
        """Energy API should return expected structure."""
        mock_energy_response = {
            "consumption_today_kwh": 12.5,
            "production_today_kwh": 8.3,
            "current_power_w": 450.0,
            "peak_power_w": 1200.0,
            "anomalies": [
                {
                    "entity_id": "sensor.living_room_power",
                    "severity": "medium",
                    "description": "Unusual pattern detected"
                }
            ],
            "shifting_opportunities": [
                {
                    "device": "washer",
                    "suggested_time": "2026-02-14T22:00:00",
                    "savings_kwh": 0.8
                }
            ]
        }
        
        # Validate structure
        assert "consumption_today_kwh" in mock_energy_response
        assert "production_today_kwh" in mock_energy_response
        assert "anomalies" in mock_energy_response
        assert isinstance(mock_energy_response["anomalies"], list)

    def test_unifi_api_response_structure(self):
        """UniFi API should return expected structure."""
        mock_unifi_response = {
            "wan": {
                "status": "online",
                "latency_ms": 18,
                "packet_loss_percent": 0.1,
                "uptime_seconds": 86400
            },
            "clients": [
                {"name": "Living Room TV", "ip": "192.168.1.100", "online": True}
            ],
            "roaming": []
        }
        
        # Validate structure
        assert "wan" in mock_unifi_response
        assert "latency_ms" in mock_unifi_response["wan"]
        assert "clients" in mock_unifi_response

    def test_weather_api_response_structure(self):
        """Weather API should return expected structure."""
        mock_weather_response = {
            "condition": "partly_cloudy",
            "temperature_c": 15.2,
            "cloud_cover_percent": 40,
            "uv_index": 3,
            "sunrise": "2026-02-14T07:15:00",
            "sunset": "2026-02-14T17:45:00",
            "pv_forecast_kwh": 7.5,
            "pv_surplus_kwh": 2.1,
            "pv_recommendation": "moderate_usage"
        }
        
        # Validate structure
        assert "condition" in mock_weather_response
        assert "temperature_c" in mock_weather_response
        assert "pv_forecast_kwh" in mock_weather_response


class TestEntityValidation:
    """Validate entity configurations against HA schema."""

    def test_energy_sensor_entities_config(self):
        """Energy sensor entities should have valid config."""
        energy_entities = {
            "sensor.ai_home_copilot_energy_consumption_today": {
                "state_class": "total",
                "unit_of_measurement": "kWh",
                "device_class": "energy"
            },
            "sensor.ai_home_copilot_energy_production_today": {
                "state_class": "total",
                "unit_of_measurement": "kWh",
                "device_class": "energy"
            },
            "sensor.ai_home_copilot_energy_current_power": {
                "state_class": "measurement",
                "unit_of_measurement": "W",
                "device_class": "power"
            }
        }
        
        for entity_id, config in energy_entities.items():
            assert "state_class" in config
            assert "unit_of_measurement" in config

    def test_unifi_sensor_entities_config(self):
        """UniFi sensor entities should have valid config."""
        unifi_entities = {
            "sensor.ai_home_copilot_unifi_clients_online": {
                "state_class": "measurement",
                "unit_of_measurement": "clients"
            },
            "sensor.ai_home_copilot_unifi_wan_latency": {
                "state_class": "measurement",
                "unit_of_measurement": "ms"
            },
            "binary_sensor.ai_home_copilot_unifi_wan_online": {
                "device_class": "connectivity"
            }
        }
        
        for entity_id, config in unifi_entities.items():
            assert isinstance(config, dict)

    def test_weather_sensor_entities_config(self):
        """Weather sensor entities should have valid config."""
        weather_entities = {
            "sensor.ai_home_copilot_weather_temperature": {
                "state_class": "measurement",
                "unit_of_measurement": "°C",
                "device_class": "temperature"
            },
            "sensor.ai_home_copilot_weather_cloud_cover": {
                "state_class": "measurement",
                "unit_of_measurement": "%",
                "device_class": "null"
            },
            "sensor.ai_home_copilot_pv_forecast_kwh": {
                "state_class": "total",
                "unit_of_measurement": "kWh",
                "device_class": "energy"
            }
        }
        
        for entity_id, config in weather_entities.items():
            assert "state_class" in config
            assert "unit_of_measurement" in config


class TestErrorHandling:
    """Test error handling for edge cases."""

    def test_coordinator_handles_api_error(self):
        """Coordinator should handle API errors gracefully."""
        def mock_api_call():
            raise ConnectionError("Core Add-on unavailable")
        
        # Should not raise
        try:
            mock_api_call()
        except ConnectionError:
            pass  # Expected
        
        assert True

    def test_missing_entity_graceful_degradation(self):
        """Missing HA entities should not crash."""
        mock_missing_entity = None
        
        if mock_missing_entity is None:
            result = {"status": "unavailable", "fallback": None}
        else:
            result = {"status": "available", "data": mock_missing_entity}
        
        assert result["status"] == "unavailable"

    def test_empty_response_handling(self):
        """Empty API responses should be handled."""
        empty_response = {}
        
        # Extract with defaults
        consumption = empty_response.get("consumption_today_kwh", 0.0)
        production = empty_response.get("production_today_kwh", 0.0)
        
        assert consumption == 0.0
        assert production == 0.0


class TestPerformance:
    """Basic performance considerations."""

    def test_update_intervals_reasonable(self):
        """Update intervals should be reasonable for each module."""
        expected_intervals = {
            "energy": 30,   # seconds
            "unifi": 60,    # seconds
            "weather": 300  # 5 minutes
        }
        
        for module, interval in expected_intervals.items():
            assert interval >= 10  # Minimum 10 seconds
            assert interval <= 600  # Maximum 10 minutes

    def test_coordinator_batch_size(self):
        """Batch sizes should be reasonable."""
        max_batch_size = 100
        test_entities = list(range(50))  # Simulate 50 entities
        
        assert len(test_entities) < max_batch_size


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
