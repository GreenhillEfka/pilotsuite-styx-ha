"""Test HA Errors Digest enhanced functionality."""

import pytest
from custom_components.ai_home_copilot.ha_errors_digest import (
    _parse_traceback_signature,
    _group_entries,
    _format_grouped_entries,
    _split_log_entries,
)


class TestTracebackSignature:
    """Test traceback signature extraction."""

    def test_simple_error(self):
        entry = [
            "2026-02-10 09:00:00.123 ERROR (MainThread) [custom_components.ai_home_copilot.api] Error occurred",
            "Traceback (most recent call last):",
            '  File "/config/custom_components/ai_home_copilot/api.py", line 42, in process',
            "    result = some_function()",
            "ValueError: invalid value",
        ]
        signature = _parse_traceback_signature(entry)
        assert signature == "ValueError@api.py"

    def test_complex_error_path(self):
        entry = [
            "2026-02-10 09:00:00.123 ERROR (MainThread) [custom_components.ai_home_copilot] Error",
            "Traceback (most recent call last):",
            '  File "/config/custom_components/ai_home_copilot/brain_graph_sync.py", line 156, in sync',
            "    await self._process_batch()",
            "RuntimeError: Connection failed",
        ]
        signature = _parse_traceback_signature(entry)
        assert signature == "RuntimeError@brain_graph_sync.py"

    def test_unknown_fallback(self):
        entry = [
            "2026-02-10 09:00:00.123 WARNING (MainThread) [some_component] Warning",
            "Something went wrong but no clear traceback",
        ]
        signature = _parse_traceback_signature(entry)
        assert signature == "Unknown@unknown"


class TestEntryGrouping:
    """Test error entry grouping functionality."""

    def test_group_similar_errors(self):
        entries = [
            "ValueError@api.py error 1",
            "RuntimeError@sync.py error 1", 
            "ValueError@api.py error 2",
            "ValueError@api.py error 3",
        ]
        
        grouped = _group_entries(entries)
        
        # Should have 2 groups
        assert len(grouped) == 2
        
        # ValueError@api.py should be first (most frequent)
        first_sig, first_entries = grouped[0]
        assert first_sig == "ValueError@api.py"
        assert len(first_entries) == 3
        
        # RuntimeError@sync.py should be second
        second_sig, second_entries = grouped[1]
        assert second_sig == "RuntimeError@sync.py"
        assert len(second_entries) == 1

    def test_format_grouped_single(self):
        grouped = [("ValueError@api.py", ["Error occurred in api"])]
        result = _format_grouped_entries(grouped)
        
        assert "🔸 **ValueError@api.py**" in result
        assert "Error occurred in api" in result
        assert "1x" not in result  # Single occurrence doesn't show count

    def test_format_grouped_multiple(self):
        grouped = [("RuntimeError@sync.py", ["Error 1", "Error 2", "Error 3"])]
        result = _format_grouped_entries(grouped)
        
        assert "🔸 **RuntimeError@sync.py** (3x)" in result
        assert "Error 3" in result  # Should show latest occurrence


class TestLogEntryParsing:
    """Test log entry splitting."""

    def test_split_multiline_entries(self):
        lines = [
            "2026-02-10 09:00:00.123 ERROR (MainThread) First error",
            "  Continuation line without timestamp",
            "  Another continuation",
            "2026-02-10 09:00:01.456 WARNING (MainThread) Second error",
            "  Its continuation",
        ]
        
        entries = _split_log_entries(lines)
        
        assert len(entries) == 2
        assert len(entries[0]) == 3  # Error + 2 continuations
        assert len(entries[1]) == 2  # Warning + 1 continuation
        assert "First error" in entries[0][0]
        assert "Second error" in entries[1][0]


if __name__ == "__main__":
    pytest.main([__file__])