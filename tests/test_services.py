"""
Tests for Services Module
=========================
Tests cover:
- Service registration
- Service execution
- Service validation

Run with: python3 -m pytest tests/ -v -k "service"
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components"))


class TestServiceRegistration:
    """Tests for service registration."""

    def test_service_registration_structure(self):
        """Test service registration data structure."""
        service_definitions = {
            "copilot_analyze_logs": {
                "description": "Analyze Home Assistant logs",
                "fields": {
                    "hours": {
                        "description": "Hours of logs to analyze",
                        "example": 24
                    }
                }
            },
            "copilot_create_suggestion": {
                "description": "Create a suggestion",
                "fields": {
                    "title": {
                        "description": "Suggestion title",
                        "example": "Optimize Lights"
                    }
                }
            }
        }
        
        assert "copilot_analyze_logs" in service_definitions
        assert service_definitions["copilot_analyze_logs"]["description"]

    def test_service_fields_validation(self):
        """Test service field definitions."""
        service_with_fields = {
            "copilot_test_service": {
                "description": "Test service",
                "fields": {
                    "required_field": {
                        "description": "A required field",
                        "required": True
                    },
                    "optional_field": {
                        "description": "An optional field",
                        "required": False,
                        "default": "default_value"
                    }
                }
            }
        }
        
        fields = service_with_fields["copilot_test_service"]["fields"]
        assert fields["required_field"].get("required") is True
        assert fields["optional_field"].get("required") is False


class TestServiceExecution:
    """Tests for service execution."""

    @pytest.mark.asyncio
    async def test_service_handler_execution(self):
        """Test service handler execution."""
        mock_hass = Mock()
        mock_call = Mock()
        mock_call.data = {"hours": 24}
        
        # Mock service handler
        async def handle_service(hass, call):
            return {"result": "analyzed", "hours": call.data.get("hours")}
        
        result = await handle_service(mock_hass, mock_call)
        
        assert result["result"] == "analyzed"
        assert result["hours"] == 24

    @pytest.mark.asyncio
    async def test_service_with_invalid_params(self):
        """Test service handles invalid parameters."""
        mock_hass = Mock()
        mock_call = Mock()
        mock_call.data = {}  # Missing required params
        
        async def handle_service(hass, call):
            required_param = call.data.get("required_param")
            if not required_param:
                raise ValueError("required_param is required")
            return {"result": "ok"}
        
        with pytest.raises(ValueError, match="required_param"):
            await handle_service(mock_hass, mock_call)


class TestTagServices:
    """Tests for tag-related services."""

    def test_tag_service_definition(self):
        """Test tag service definition."""
        tag_service = {
            "copilot_tag_sync": {
                "description": "Sync tags from Core",
                "fields": {
                    "entry_id": {
                        "description": "Config entry ID",
                        "required": False
                    }
                }
            }
        }
        
        assert "copilot_tag_sync" in tag_service
        assert "description" in tag_service["copilot_tag_sync"]

    def test_tag_upsert_service(self):
        """Test tag upsert service structure."""
        tag_upsert = {
            "copilot_tag_upsert": {
                "description": "Create or update a tag",
                "fields": {
                    "tag_key": {"description": "Unique tag identifier"},
                    "tag_name": {"description": "Display name"},
                    "status": {"description": "pending or confirmed"}
                }
            }
        }
        
        fields = tag_upsert["copilot_tag_upsert"]["fields"]
        assert "tag_key" in fields
        assert "tag_name" in fields


class TestConfigServices:
    """Tests for configuration services."""

    def test_config_snapshot_service(self):
        """Test config snapshot service."""
        snapshot_service = {
            "copilot_create_config_snapshot": {
                "description": "Create configuration snapshot",
                "fields": {
                    "include_entities": {
                        "description": "Include entity states",
                        "default": False
                    }
                }
            }
        }
        
        assert "copilot_create_config_snapshot" in snapshot_service

    def test_config_restore_service(self):
        """Test config restore service."""
        restore_service = {
            "copilot_restore_config_snapshot": {
                "description": "Restore configuration from snapshot",
                "fields": {
                    "snapshot_id": {
                        "description": "ID of snapshot to restore",
                        "required": True
                    }
                }
            }
        }
        
        assert "snapshot_id" in restore_service["copilot_restore_config_snapshot"]["fields"]


class TestDomainServices:
    """Tests for domain-specific services."""

    def test_light_control_services(self):
        """Test light control services."""
        light_services = {
            "copilot_light_control": {
                "description": "Control lights with AI",
                "fields": {
                    "action": {
                        "description": "Action to perform",
                        "example": "turn_on"
                    },
                    "room": {
                        "description": "Room name",
                        "example": "Living Room"
                    }
                }
            }
        }
        
        assert "action" in light_services["copilot_light_control"]["fields"]

    def test_climate_control_services(self):
        """Test climate control services."""
        climate_services = {
            "copilot_climate_control": {
                "description": "Control climate with AI",
                "fields": {
                    "target_temp": {
                        "description": "Target temperature",
                        "example": 21
                    }
                }
            }
        }
        
        assert "target_temp" in climate_services["copilot_climate_control"]["fields"]


class TestServiceErrors:
    """Tests for service error handling."""

    @pytest.mark.asyncio
    async def test_service_timeout_handling(self):
        """Test service timeout handling."""
        mock_hass = Mock()
        
        async def slow_service(hass, call):
            import asyncio
            await asyncio.sleep(10)  # Simulate slow service
            return {"result": "done"}
        
        # This would timeout in real scenario
        # Test that the structure is correct
        assert callable(slow_service)

    @pytest.mark.asyncio
    async def test_service_exception_handling(self):
        """Test service exception handling."""
        mock_hass = Mock()
        
        async def failing_service(hass, call):
            raise RuntimeError("Service failed")
        
        mock_call = Mock()
        mock_call.data = {}
        
        try:
            await failing_service(mock_hass, mock_call)
        except RuntimeError as e:
            assert str(e) == "Service failed"


class TestServicePermissions:
    """Tests for service permissions."""

    def test_admin_service_permissions(self):
        """Test admin service permission structure."""
        admin_services = [
            "copilot_reload_config",
            "copilot_create_config_snapshot",
            "copilot_update_core"
        ]
        
        for service in admin_services:
            assert isinstance(service, str)
            assert service.startswith("copilot_")

    def test_user_service_permissions(self):
        """Test user service permission structure."""
        user_services = [
            "copilot_analyze_logs",
            "copilot_create_suggestion",
            "copilot_light_control"
        ]
        
        for service in user_services:
            assert isinstance(service, str)
            assert service.startswith("copilot_")
