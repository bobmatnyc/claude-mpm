"""Tests for Hook Error Memory System.

WHY comprehensive testing is critical:
- Error detection affects system reliability
- Wrong detection could skip valid hooks
- Memory persistence must be robust
- Fix suggestions need to be helpful
"""

import json
import tempfile
from pathlib import Path

import pytest

from claude_mpm.core.hook_error_memory import HookErrorMemory, get_hook_error_memory


class TestHookErrorMemory:
    """Test suite for HookErrorMemory class."""

    @pytest.fixture
    def temp_memory_file(self):
        """Create temporary memory file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_path = Path(f.name)
        yield temp_path
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    @pytest.fixture
    def error_memory(self, temp_memory_file):
        """Create HookErrorMemory instance with temp file."""
        return HookErrorMemory(memory_file=temp_memory_file)

    def test_initialization(self, temp_memory_file):
        """Test error memory initialization."""
        memory = HookErrorMemory(memory_file=temp_memory_file)
        assert memory.memory_file == temp_memory_file
        assert memory.errors == {}

    def test_detect_file_not_found_error(self, error_memory):
        """Test detection of file not found errors."""
        output = ""
        stderr = "Error: (eval):1: no such file or directory: /path/to/missing/file.sh"
        returncode = 1

        error_info = error_memory.detect_error(output, stderr, returncode)

        assert error_info is not None
        # Could match either eval_error or file_not_found depending on pattern order
        assert error_info["type"] in ["eval_error", "file_not_found"]
        assert (
            "/path/to/missing/file.sh" in error_info["details"]
            or "no such file" in error_info["details"]
        )

    def test_detect_command_not_found_error(self, error_memory):
        """Test detection of command not found errors."""
        output = ""
        stderr = "command not found: nonexistent_command"
        returncode = 127

        error_info = error_memory.detect_error(output, stderr, returncode)

        assert error_info is not None
        assert error_info["type"] == "command_not_found"
        assert "nonexistent_command" in error_info["details"]

    def test_detect_permission_denied_error(self, error_memory):
        """Test detection of permission denied errors."""
        output = ""
        stderr = "permission denied: /usr/local/bin/restricted_script.sh"
        returncode = 126

        error_info = error_memory.detect_error(output, stderr, returncode)

        assert error_info is not None
        assert error_info["type"] == "permission_denied"
        assert "restricted_script.sh" in error_info["details"]

    def test_detect_syntax_error(self, error_memory):
        """Test detection of syntax errors."""
        output = ""
        stderr = "syntax error near unexpected token"
        returncode = 2

        error_info = error_memory.detect_error(output, stderr, returncode)

        assert error_info is not None
        assert error_info["type"] == "syntax_error"

    def test_detect_general_error(self, error_memory):
        """Test detection of general errors."""
        output = ""
        stderr = "Error: Something went wrong"
        returncode = 1

        error_info = error_memory.detect_error(output, stderr, returncode)

        assert error_info is not None
        assert error_info["type"] in ["general_error", "eval_error"]

    def test_no_error_on_success(self, error_memory):
        """Test that successful execution doesn't trigger error detection."""
        output = "Hook executed successfully"
        stderr = ""
        returncode = 0

        error_info = error_memory.detect_error(output, stderr, returncode)

        assert error_info is None

    def test_record_error(self, error_memory):
        """Test recording an error."""
        error_info = {
            "type": "file_not_found",
            "pattern": "no such file",
            "match": "no such file or directory: /test/file.sh",
            "details": "/test/file.sh",
            "returncode": 1,
        }

        error_memory.record_error(error_info, "PreToolUse")

        # Check error was recorded
        assert len(error_memory.errors) == 1
        recorded = next(iter(error_memory.errors.values()))
        assert recorded["type"] == "file_not_found"
        assert recorded["hook_type"] == "PreToolUse"
        assert recorded["count"] == 1

    def test_record_duplicate_error_increments_count(self, error_memory):
        """Test that recording the same error increments count."""
        error_info = {
            "type": "file_not_found",
            "pattern": "no such file",
            "match": "no such file or directory: /test/file.sh",
            "details": "/test/file.sh",
            "returncode": 1,
        }

        # Record same error twice
        error_memory.record_error(error_info, "PreToolUse")
        error_memory.record_error(error_info, "PreToolUse")

        # Should only have one entry with count=2
        assert len(error_memory.errors) == 1
        recorded = next(iter(error_memory.errors.values()))
        assert recorded["count"] == 2

    def test_is_known_failing_hook(self, error_memory):
        """Test checking if hook is known to fail."""
        error_info = {
            "type": "file_not_found",
            "pattern": "no such file",
            "match": "no such file or directory: /test/file.sh",
            "details": "/test/file.sh",
            "returncode": 1,
        }

        # Not failing yet (count < 2)
        error_memory.record_error(error_info, "PreToolUse")
        assert error_memory.is_known_failing_hook("PreToolUse") is None

        # Now failing (count >= 2)
        error_memory.record_error(error_info, "PreToolUse")
        result = error_memory.is_known_failing_hook("PreToolUse")
        assert result is not None
        assert result["count"] == 2

    def test_should_skip_hook(self, error_memory):
        """Test should_skip_hook logic."""
        error_info = {
            "type": "file_not_found",
            "pattern": "no such file",
            "match": "no such file or directory: /test/file.sh",
            "details": "/test/file.sh",
            "returncode": 1,
        }

        # Should not skip with 1 failure
        error_memory.record_error(error_info, "PreToolUse")
        assert error_memory.should_skip_hook("PreToolUse") is False

        # Should skip with 2+ failures
        error_memory.record_error(error_info, "PreToolUse")
        assert error_memory.should_skip_hook("PreToolUse") is True

    def test_suggest_fix_file_not_found(self, error_memory):
        """Test fix suggestion for file not found error."""
        error_info = {
            "type": "file_not_found",
            "details": "/test/missing.sh",
        }

        suggestion = error_memory.suggest_fix(error_info)

        assert "File not found" in suggestion
        assert "/test/missing.sh" in suggestion
        assert "chmod +x" in suggestion

    def test_suggest_fix_command_not_found(self, error_memory):
        """Test fix suggestion for command not found error."""
        error_info = {
            "type": "command_not_found",
            "details": "missing_cmd",
        }

        suggestion = error_memory.suggest_fix(error_info)

        assert "Command not found" in suggestion
        assert "missing_cmd" in suggestion
        assert "which" in suggestion

    def test_suggest_fix_permission_denied(self, error_memory):
        """Test fix suggestion for permission denied error."""
        error_info = {
            "type": "permission_denied",
            "details": "/restricted/file.sh",
        }

        suggestion = error_memory.suggest_fix(error_info)

        assert "Permission denied" in suggestion
        assert "/restricted/file.sh" in suggestion
        assert "chmod" in suggestion

    def test_clear_all_errors(self, error_memory):
        """Test clearing all errors."""
        error_info = {
            "type": "file_not_found",
            "pattern": "no such file",
            "match": "no such file or directory: /test/file.sh",
            "details": "/test/file.sh",
            "returncode": 1,
        }

        # Record some errors
        error_memory.record_error(error_info, "PreToolUse")
        error_memory.record_error(error_info, "PostToolUse")
        assert len(error_memory.errors) >= 1

        # Clear all
        error_memory.clear_errors()
        assert len(error_memory.errors) == 0

    def test_clear_errors_for_specific_hook(self, error_memory):
        """Test clearing errors for specific hook type."""
        error_info1 = {
            "type": "file_not_found",
            "pattern": "no such file",
            "match": "no such file: /test1.sh",
            "details": "/test1.sh",
            "returncode": 1,
        }
        error_info2 = {
            "type": "file_not_found",
            "pattern": "no such file",
            "match": "no such file: /test2.sh",
            "details": "/test2.sh",
            "returncode": 1,
        }

        # Record errors for different hooks
        error_memory.record_error(error_info1, "PreToolUse")
        error_memory.record_error(error_info2, "PostToolUse")
        initial_count = len(error_memory.errors)
        assert initial_count >= 2

        # Clear only PreToolUse errors
        error_memory.clear_errors("PreToolUse")

        # Should have fewer errors now
        assert len(error_memory.errors) < initial_count

    def test_get_error_summary(self, error_memory):
        """Test getting error summary."""
        error_info1 = {
            "type": "file_not_found",
            "pattern": "no such file",
            "match": "no such file: /test1.sh",
            "details": "/test1.sh",
            "returncode": 1,
        }
        error_info2 = {
            "type": "command_not_found",
            "pattern": "command not found",
            "match": "command not found: test_cmd",
            "details": "test_cmd",
            "returncode": 127,
        }

        # Record some errors
        error_memory.record_error(error_info1, "PreToolUse")
        error_memory.record_error(error_info1, "PreToolUse")  # Same error twice
        error_memory.record_error(error_info2, "PostToolUse")

        summary = error_memory.get_error_summary()

        assert summary["unique_errors"] >= 2
        assert summary["total_errors"] >= 3
        assert "file_not_found" in summary["errors_by_type"]
        assert "command_not_found" in summary["errors_by_type"]
        assert "PreToolUse" in summary["errors_by_hook"]
        assert "PostToolUse" in summary["errors_by_hook"]

    def test_persistence(self, temp_memory_file):
        """Test that errors persist across instances."""
        error_info = {
            "type": "file_not_found",
            "pattern": "no such file",
            "match": "no such file: /test.sh",
            "details": "/test.sh",
            "returncode": 1,
        }

        # Create first instance and record error
        memory1 = HookErrorMemory(memory_file=temp_memory_file)
        memory1.record_error(error_info, "PreToolUse")
        initial_count = len(memory1.errors)
        assert initial_count >= 1

        # Create second instance - should load persisted errors
        memory2 = HookErrorMemory(memory_file=temp_memory_file)
        assert len(memory2.errors) == initial_count

    def test_empty_output_handling(self, error_memory):
        """Test handling of empty output."""
        error_info = error_memory.detect_error("", "", 0)
        assert error_info is None

    def test_unknown_error_with_non_zero_exit(self, error_memory):
        """Test handling of unknown errors with non-zero exit code."""
        output = "Some non-standard error message"
        stderr = "Weird error format"
        returncode = 42

        error_info = error_memory.detect_error(output, stderr, returncode)

        # Should detect as unknown error
        assert error_info is not None
        assert error_info["type"] == "unknown_error"
        assert error_info["returncode"] == 42

    def test_corrupted_memory_file_handling(self, temp_memory_file):
        """Test handling of corrupted memory file."""
        # Write corrupted JSON to file
        temp_memory_file.write_text("{ this is not valid JSON }")

        # Should handle gracefully and start with empty errors
        memory = HookErrorMemory(memory_file=temp_memory_file)
        assert memory.errors == {}

    def test_global_instance_singleton(self):
        """Test that get_hook_error_memory returns singleton instance."""
        memory1 = get_hook_error_memory()
        memory2 = get_hook_error_memory()

        # Should be the same instance
        assert memory1 is memory2


class TestErrorDetectionPatterns:
    """Test specific error pattern detection."""

    @pytest.fixture
    def error_memory(self):
        """Create fresh error memory for each test."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_path = Path(f.name)
        memory = HookErrorMemory(memory_file=temp_path)
        yield memory
        if temp_path.exists():
            temp_path.unlink()

    def test_real_world_file_not_found_pattern(self, error_memory):
        """Test detection of real error from the issue description."""
        output = ""
        stderr = "Error: (eval):1: no such file or directory: /Users/masa/Projects/claude-mpm/scripts/run_tests_sequential.sh"
        returncode = 1

        error_info = error_memory.detect_error(output, stderr, returncode)

        assert error_info is not None
        # Could be detected as eval_error or file_not_found depending on pattern order
        assert error_info["type"] in ["eval_error", "file_not_found"]
        assert "run_tests_sequential.sh" in error_info["details"]

    def test_multiline_error_detection(self, error_memory):
        """Test detection of errors in multiline output."""
        output = """
Line 1: Some output
Line 2: More output
Error: no such file or directory: /missing.sh
Line 4: After error
"""
        stderr = ""
        returncode = 1

        error_info = error_memory.detect_error(output, stderr, returncode)

        assert error_info is not None
        assert "/missing.sh" in error_info["details"]

    def test_error_in_stdout_vs_stderr(self, error_memory):
        """Test that errors are detected in both stdout and stderr."""
        # Error in stdout
        error_info1 = error_memory.detect_error("Error: command not found: test", "", 1)
        assert error_info1 is not None

        # Error in stderr
        error_info2 = error_memory.detect_error("", "Error: command not found: test", 1)
        assert error_info2 is not None


class TestErrorMemoryIntegration:
    """Integration tests for error memory system."""

    @pytest.fixture
    def error_memory(self):
        """Create error memory with temp file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_path = Path(f.name)
        memory = HookErrorMemory(memory_file=temp_path)
        yield memory
        if temp_path.exists():
            temp_path.unlink()

    def test_full_error_lifecycle(self, error_memory):
        """Test complete error lifecycle: detect -> record -> skip -> clear -> retry."""
        # 1. Detect error
        error_info = error_memory.detect_error(
            "", "no such file or directory: /test.sh", 1
        )
        assert error_info is not None

        # 2. Record error (first time)
        error_memory.record_error(error_info, "PreToolUse")
        assert not error_memory.should_skip_hook("PreToolUse")  # Don't skip yet

        # 3. Record error again
        error_memory.record_error(error_info, "PreToolUse")
        assert error_memory.should_skip_hook("PreToolUse")  # Now skip

        # 4. Clear errors
        error_memory.clear_errors()
        assert not error_memory.should_skip_hook("PreToolUse")  # Can retry

    def test_different_hooks_tracked_separately(self, error_memory):
        """Test that errors for different hooks are tracked separately."""
        error_info = {
            "type": "file_not_found",
            "pattern": "no such file",
            "match": "no such file: /test.sh",
            "details": "/test.sh",
            "returncode": 1,
        }

        # Record for PreToolUse
        error_memory.record_error(error_info, "PreToolUse")
        error_memory.record_error(error_info, "PreToolUse")

        # PreToolUse should be skipped
        assert error_memory.should_skip_hook("PreToolUse")

        # PostToolUse should not be skipped
        assert not error_memory.should_skip_hook("PostToolUse")
