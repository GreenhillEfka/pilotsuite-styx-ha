"""Tests for User Preference Module - stub compatibility tests."""

import pytest
from unittest.mock import Mock


class TestUserPreferenceModule:
    """Tests for UserPreferenceModule class - basic stub tests."""
    
    def test_import(self):
        """Test that the module can be imported."""
        from custom_components.ai_home_copilot.core.modules.user_preference_module import UserPreferenceModule
        assert UserPreferenceModule is not None
    
    def test_instantiation(self):
        """Test that the module can be instantiated."""
        from custom_components.ai_home_copilot.core.modules.user_preference_module import UserPreferenceModule
        module = UserPreferenceModule(Mock(), {})
        assert module is not None
    
    def test_has_async_setup(self):
        """Test that async_setup method exists."""
        from custom_components.ai_home_copilot.core.modules.user_preference_module import UserPreferenceModule
        module = UserPreferenceModule(Mock(), {})
        assert hasattr(module, 'async_setup')
    
    def test_has_async_unload(self):
        """Test that async_unload method exists."""
        from custom_components.ai_home_copilot.core.modules.user_preference_module import UserPreferenceModule
        module = UserPreferenceModule(Mock(), {})
        assert hasattr(module, 'async_unload')
    
    def test_has_get_preference(self):
        """Test that get_preference method exists."""
        from custom_components.ai_home_copilot.core.modules.user_preference_module import UserPreferenceModule
        module = UserPreferenceModule(Mock(), {})
        assert hasattr(module, 'get_preference')
    
    def test_has_set_preference(self):
        """Test that set_preference method exists."""
        from custom_components.ai_home_copilot.core.modules.user_preference_module import UserPreferenceModule
        module = UserPreferenceModule(Mock(), {})
        assert hasattr(module, 'set_preference')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
