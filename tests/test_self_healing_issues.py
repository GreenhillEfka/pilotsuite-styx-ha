"""Tests for Self-Healing HA Repair Issue creation.

Tests the automation analyzer's repair issue creation and cleanup.

Run with: pytest tests/test_self_healing_issues.py -v
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


_IR_PATH = "custom_components.ai_home_copilot.core.modules.automation_analyzer.ir"


class TestRepairIssueCreation:
    """Tests for _create_repair_issues in AutomationAnalyzerModule."""

    def _make_mock_ir(self, existing_issues=None):
        """Create a mock issue_registry and set it as the patched ir."""
        mock_ir = MagicMock()
        mock_issue_reg = MagicMock()
        mock_issue_reg.issues = existing_issues or {}
        mock_ir.async_get.return_value = mock_issue_reg
        return mock_ir

    @pytest.mark.asyncio
    async def test_create_issues_from_error_hints(self):
        """Test that ERROR hints create repair issues."""
        from custom_components.ai_home_copilot.core.modules.automation_analyzer import (
            AutomationAnalyzerModule,
        )

        module = AutomationAnalyzerModule()
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test"

        mock_ir = self._make_mock_ir()

        with patch(_IR_PATH, mock_ir):
            hints = [
                {
                    "automation_id": "automation.test",
                    "hint_type": "missing_entity",
                    "severity": "error",
                    "message": "Entity not found",
                    "fix_suggestion": "Replace entity",
                }
            ]

            await module._create_repair_issues(hass, entry, hints)

            mock_ir.async_create_issue.assert_called_once()
            call_args = mock_ir.async_create_issue.call_args
            assert call_args[1]["severity"] == "error"
            assert call_args[1]["translation_key"] == "automation_repair_hint"

    @pytest.mark.asyncio
    async def test_skip_info_hints(self):
        """Test that INFO hints do NOT create repair issues."""
        from custom_components.ai_home_copilot.core.modules.automation_analyzer import (
            AutomationAnalyzerModule,
        )

        module = AutomationAnalyzerModule()
        hass = MagicMock()
        entry = MagicMock()

        mock_ir = self._make_mock_ir()

        with patch(_IR_PATH, mock_ir):
            hints = [
                {
                    "automation_id": "automation.test",
                    "hint_type": "stale",
                    "severity": "info",
                    "message": "Not triggered in 45 days",
                    "fix_suggestion": "Check conditions",
                }
            ]

            await module._create_repair_issues(hass, entry, hints)

            mock_ir.async_create_issue.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_warning_hints(self):
        """Test that WARNING hints create repair issues."""
        from custom_components.ai_home_copilot.core.modules.automation_analyzer import (
            AutomationAnalyzerModule,
        )

        module = AutomationAnalyzerModule()
        hass = MagicMock()
        entry = MagicMock()

        mock_ir = self._make_mock_ir()

        with patch(_IR_PATH, mock_ir):
            hints = [
                {
                    "automation_id": "automation.disabled_test",
                    "hint_type": "disabled",
                    "severity": "warning",
                    "message": "Automation is disabled",
                    "fix_suggestion": "Enable or delete",
                }
            ]

            await module._create_repair_issues(hass, entry, hints)

            mock_ir.async_create_issue.assert_called_once()
            call_args = mock_ir.async_create_issue.call_args
            assert call_args[1]["severity"] == "warning"

    @pytest.mark.asyncio
    async def test_cleanup_old_issues(self):
        """Test that old automation_hint_ issues are cleaned up."""
        from custom_components.ai_home_copilot.core.modules.automation_analyzer import (
            AutomationAnalyzerModule,
        )

        module = AutomationAnalyzerModule()
        hass = MagicMock()
        entry = MagicMock()

        mock_ir = self._make_mock_ir(existing_issues={
            ("ai_home_copilot", "automation_hint_0_disabled"): MagicMock(),
            ("ai_home_copilot", "other_issue"): MagicMock(),
        })

        with patch(_IR_PATH, mock_ir):
            await module._create_repair_issues(hass, entry, [])

            # Should only delete the automation_hint_ issue
            mock_ir.async_delete_issue.assert_called_once_with(
                hass, "ai_home_copilot", "automation_hint_0_disabled"
            )

    @pytest.mark.asyncio
    async def test_multiple_hints_mixed(self):
        """Test creating issues from multiple mixed-severity hints."""
        from custom_components.ai_home_copilot.core.modules.automation_analyzer import (
            AutomationAnalyzerModule,
        )

        module = AutomationAnalyzerModule()
        hass = MagicMock()
        entry = MagicMock()

        mock_ir = self._make_mock_ir()

        with patch(_IR_PATH, mock_ir):
            hints = [
                {"automation_id": "a1", "hint_type": "disabled", "severity": "warning",
                 "message": "Disabled", "fix_suggestion": "Enable"},
                {"automation_id": "a2", "hint_type": "stale", "severity": "info",
                 "message": "Stale", "fix_suggestion": "Check"},
                {"automation_id": "a3", "hint_type": "missing_entity", "severity": "error",
                 "message": "Missing", "fix_suggestion": "Replace"},
            ]

            await module._create_repair_issues(hass, entry, hints)

            # Only warning + error = 2 calls
            assert mock_ir.async_create_issue.call_count == 2

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self):
        """Test graceful handling when issue_registry methods fail."""
        from custom_components.ai_home_copilot.core.modules.automation_analyzer import (
            AutomationAnalyzerModule,
        )

        module = AutomationAnalyzerModule()
        hass = MagicMock()
        entry = MagicMock()

        mock_ir = MagicMock()
        mock_ir.async_get.side_effect = Exception("Registry unavailable")

        with patch(_IR_PATH, mock_ir):
            # Should not raise
            await module._create_repair_issues(hass, entry, [
                {"automation_id": "a1", "hint_type": "error", "severity": "error",
                 "message": "Test", "fix_suggestion": "Fix"}
            ])

    @pytest.mark.asyncio
    async def test_empty_hints_list(self):
        """Test with empty hints list."""
        from custom_components.ai_home_copilot.core.modules.automation_analyzer import (
            AutomationAnalyzerModule,
        )

        module = AutomationAnalyzerModule()
        hass = MagicMock()
        entry = MagicMock()

        mock_ir = self._make_mock_ir()

        with patch(_IR_PATH, mock_ir):
            await module._create_repair_issues(hass, entry, [])
            mock_ir.async_create_issue.assert_not_called()

    def test_strings_json_has_automation_repair_hint(self):
        """Test that strings.json contains the automation_repair_hint key."""
        import json
        from pathlib import Path

        strings_path = Path("custom_components/ai_home_copilot/strings.json")
        data = json.loads(strings_path.read_text(encoding="utf-8"))

        assert "automation_repair_hint" in data["issues"]
        assert "{automation}" in data["issues"]["automation_repair_hint"]["title"]
        assert "{message}" in data["issues"]["automation_repair_hint"]["description"]
        assert "{fix}" in data["issues"]["automation_repair_hint"]["description"]
