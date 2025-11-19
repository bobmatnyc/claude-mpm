"""Integration tests for HookManager with error detection.

WHY integration testing is important:
- Verify error detection works end-to-end
- Ensure hook skipping logic works correctly
- Test interaction between components
- Validate real-world error scenarios
"""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_mpm.core.hook_error_memory import HookErrorMemory
from claude_mpm.core.hook_manager import HookManager


class TestHookManagerErrorDetection:
    """Test HookManager integration with error detection."""

    @pytest.fixture
    def temp_memory_file(self):
        """Create temporary memory file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_path = Path(f.name)
        yield temp_path
        if temp_path.exists():
            temp_path.unlink()

    @pytest.fixture
    def hook_manager(self, temp_memory_file):
        """Create HookManager with mocked error memory."""
        manager = HookManager()
        # Replace error memory with test instance
        manager.error_memory = HookErrorMemory(memory_file=temp_memory_file)
        return manager

    @pytest.fixture(autouse=True)
    def cleanup_hook_manager(self, hook_manager):
        """Ensure hook manager is cleaned up after each test."""
        yield
        # Shutdown background thread
        if hook_manager:
            hook_manager.shutdown()

    def test_error_detection_on_file_not_found(self, hook_manager):
        """Test that file not found errors are detected and recorded."""
        with patch("subprocess.run") as mock_run:
            # Simulate file not found error
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "Error: no such file or directory: /missing/script.sh"
            mock_run.return_value = mock_result

            # Execute hook that will fail
            hook_data = {
                "hook_type": "PreToolUse",
                "event_data": {"tool_name": "TestTool"},
            }
            hook_manager._execute_hook_sync(hook_data)

            # Check error was recorded
            assert len(hook_manager.error_memory.errors) >= 1
            # Verify error type
            recorded = next(iter(hook_manager.error_memory.errors.values()))
            assert recorded["type"] in ["file_not_found", "general_error"]

    def test_hook_skipped_after_repeated_failures(self, hook_manager):
        """Test that hooks are skipped after failing multiple times."""
        with patch("subprocess.run") as mock_run:
            # Simulate repeated failures
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "Error: no such file or directory: /missing/script.sh"
            mock_run.return_value = mock_result

            hook_data = {
                "hook_type": "PreToolUse",
                "event_data": {"tool_name": "TestTool"},
            }

            # First execution - should run
            hook_manager._execute_hook_sync(hook_data)
            assert mock_run.call_count == 1

            # Second execution - should run but record error
            hook_manager._execute_hook_sync(hook_data)
            assert mock_run.call_count == 2

            # Third execution - should be skipped
            initial_call_count = mock_run.call_count
            hook_manager._execute_hook_sync(hook_data)
            # Should not have made another subprocess call
            assert mock_run.call_count == initial_call_count

    def test_different_hook_types_tracked_separately(self, hook_manager):
        """Test that errors for different hook types are tracked separately."""
        with patch("subprocess.run") as mock_run:
            # Simulate error
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "Error: command not found: missing_cmd"
            mock_run.return_value = mock_result

            # Fail PreToolUse twice
            pre_hook_data = {
                "hook_type": "PreToolUse",
                "event_data": {"tool_name": "TestTool"},
            }
            hook_manager._execute_hook_sync(pre_hook_data)
            hook_manager._execute_hook_sync(pre_hook_data)

            # PreToolUse should be skipped
            assert hook_manager.error_memory.should_skip_hook("PreToolUse")

            # PostToolUse should not be skipped
            assert not hook_manager.error_memory.should_skip_hook("PostToolUse")

            # PostToolUse should still execute
            post_hook_data = {
                "hook_type": "PostToolUse",
                "event_data": {"tool_name": "TestTool"},
            }
            pre_count = mock_run.call_count
            hook_manager._execute_hook_sync(post_hook_data)
            # Should have made subprocess call
            assert mock_run.call_count > pre_count

    def test_successful_execution_not_recorded_as_error(self, hook_manager):
        """Test that successful hook execution doesn't record errors."""
        with patch("subprocess.run") as mock_run:
            # Simulate success
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "Hook executed successfully"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            hook_data = {
                "hook_type": "PreToolUse",
                "event_data": {"tool_name": "TestTool"},
            }
            hook_manager._execute_hook_sync(hook_data)

            # No errors should be recorded
            assert len(hook_manager.error_memory.errors) == 0

    def test_error_memory_persistence(self, hook_manager, temp_memory_file):
        """Test that errors persist across HookManager instances."""
        with patch("subprocess.run") as mock_run:
            # Simulate error
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "Error: permission denied: /restricted.sh"
            mock_run.return_value = mock_result

            hook_data = {
                "hook_type": "PreToolUse",
                "event_data": {"tool_name": "TestTool"},
            }

            # Record errors with first instance
            hook_manager._execute_hook_sync(hook_data)
            hook_manager._execute_hook_sync(hook_data)
            initial_count = len(hook_manager.error_memory.errors)
            assert initial_count >= 1

            # Shutdown first instance
            hook_manager.shutdown()

            # Create new instance with same memory file
            new_manager = HookManager()
            new_manager.error_memory = HookErrorMemory(memory_file=temp_memory_file)

            # Should have loaded persisted errors
            assert len(new_manager.error_memory.errors) == initial_count
            assert new_manager.error_memory.should_skip_hook("PreToolUse")

            # Cleanup
            new_manager.shutdown()

    def test_timeout_errors_not_recorded(self, hook_manager):
        """Test that timeout errors are logged but not recorded in error memory."""
        from subprocess import TimeoutExpired

        with patch("subprocess.run") as mock_run:
            # Simulate timeout
            mock_run.side_effect = TimeoutExpired("cmd", 5)

            hook_data = {
                "hook_type": "PreToolUse",
                "event_data": {"tool_name": "TestTool"},
            }
            hook_manager._execute_hook_sync(hook_data)

            # Timeout should not be recorded as persistent error
            # (it could be transient)
            assert len(hook_manager.error_memory.errors) == 0

    def test_multiple_error_types_recorded(self, hook_manager):
        """Test that different error types are recorded separately."""
        with patch("subprocess.run") as mock_run:
            # First error type: file not found
            mock_result1 = Mock()
            mock_result1.returncode = 1
            mock_result1.stdout = ""
            mock_result1.stderr = "Error: no such file or directory: /missing1.sh"

            # Second error type: permission denied
            mock_result2 = Mock()
            mock_result2.returncode = 1
            mock_result2.stdout = ""
            mock_result2.stderr = "Error: permission denied: /restricted.sh"

            # Execute with different errors
            mock_run.return_value = mock_result1
            hook_manager._execute_hook_sync(
                {"hook_type": "PreToolUse", "event_data": {"tool_name": "TestTool1"}}
            )

            mock_run.return_value = mock_result2
            hook_manager._execute_hook_sync(
                {"hook_type": "PreToolUse", "event_data": {"tool_name": "TestTool2"}}
            )

            # Should have recorded both errors
            assert len(hook_manager.error_memory.errors) >= 2

    def test_error_summary_accessible(self, hook_manager):
        """Test that error summary can be accessed."""
        with patch("subprocess.run") as mock_run:
            # Simulate error
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "Error: command not found: test_cmd"
            mock_run.return_value = mock_result

            # Record some errors
            hook_data = {
                "hook_type": "PreToolUse",
                "event_data": {"tool_name": "TestTool"},
            }
            hook_manager._execute_hook_sync(hook_data)
            hook_manager._execute_hook_sync(hook_data)

            # Get summary
            summary = hook_manager.error_memory.get_error_summary()

            assert summary["total_errors"] >= 2
            assert summary["unique_errors"] >= 1
            assert "PreToolUse" in summary["errors_by_hook"]


class TestHookManagerErrorRecovery:
    """Test error recovery and retry mechanisms."""

    @pytest.fixture
    def temp_memory_file(self):
        """Create temporary memory file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_path = Path(f.name)
        yield temp_path
        if temp_path.exists():
            temp_path.unlink()

    @pytest.fixture
    def hook_manager(self, temp_memory_file):
        """Create HookManager with test error memory."""
        manager = HookManager()
        manager.error_memory = HookErrorMemory(memory_file=temp_memory_file)
        return manager

    @pytest.fixture(autouse=True)
    def cleanup_hook_manager(self, hook_manager):
        """Cleanup hook manager."""
        yield
        if hook_manager:
            hook_manager.shutdown()

    def test_clear_errors_allows_retry(self, hook_manager):
        """Test that clearing errors allows hooks to be retried."""
        with patch("subprocess.run") as mock_run:
            # Simulate repeated failures
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "Error: no such file or directory: /missing.sh"
            mock_run.return_value = mock_result

            hook_data = {
                "hook_type": "PreToolUse",
                "event_data": {"tool_name": "TestTool"},
            }

            # Fail twice to trigger skip
            hook_manager._execute_hook_sync(hook_data)
            hook_manager._execute_hook_sync(hook_data)
            assert hook_manager.error_memory.should_skip_hook("PreToolUse")

            # Clear errors
            hook_manager.error_memory.clear_errors()

            # Should no longer skip
            assert not hook_manager.error_memory.should_skip_hook("PreToolUse")

            # Should execute again
            pre_count = mock_run.call_count
            hook_manager._execute_hook_sync(hook_data)
            assert mock_run.call_count > pre_count

    def test_partial_error_clear(self, hook_manager):
        """Test clearing errors for specific hook type."""
        with patch("subprocess.run") as mock_run:
            # Simulate error
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "Error: test error"
            mock_run.return_value = mock_result

            # Fail different hook types
            for hook_type in ["PreToolUse", "PostToolUse"]:
                hook_data = {
                    "hook_type": hook_type,
                    "event_data": {"tool_name": "TestTool"},
                }
                hook_manager._execute_hook_sync(hook_data)
                hook_manager._execute_hook_sync(hook_data)

            # Both should be skipped
            assert hook_manager.error_memory.should_skip_hook("PreToolUse")
            assert hook_manager.error_memory.should_skip_hook("PostToolUse")

            # Clear only PreToolUse errors
            hook_manager.error_memory.clear_errors("PreToolUse")

            # PreToolUse should be cleared, PostToolUse still skipped
            assert not hook_manager.error_memory.should_skip_hook("PreToolUse")
            assert hook_manager.error_memory.should_skip_hook("PostToolUse")


class TestRealWorldScenarios:
    """Test real-world error scenarios."""

    @pytest.fixture
    def temp_memory_file(self):
        """Create temporary memory file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_path = Path(f.name)
        yield temp_path
        if temp_path.exists():
            temp_path.unlink()

    @pytest.fixture
    def hook_manager(self, temp_memory_file):
        """Create HookManager with test error memory."""
        manager = HookManager()
        manager.error_memory = HookErrorMemory(memory_file=temp_memory_file)
        return manager

    @pytest.fixture(autouse=True)
    def cleanup_hook_manager(self, hook_manager):
        """Cleanup hook manager."""
        yield
        if hook_manager:
            hook_manager.shutdown()

    def test_issue_example_error(self, hook_manager):
        """Test the exact error from the issue description."""
        with patch("subprocess.run") as mock_run:
            # Simulate the exact error from the issue
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "Error: (eval):1: no such file or directory: /Users/masa/Projects/claude-mpm/scripts/run_tests_sequential.sh"
            mock_run.return_value = mock_result

            hook_data = {
                "hook_type": "PreToolUse",
                "event_data": {"tool_name": "TestTool"},
            }

            # First execution - should run and record error
            hook_manager._execute_hook_sync(hook_data)
            assert len(hook_manager.error_memory.errors) >= 1

            # Second execution - should run and increment count
            hook_manager._execute_hook_sync(hook_data)

            # Third execution - should be skipped
            initial_call_count = mock_run.call_count
            hook_manager._execute_hook_sync(hook_data)
            assert mock_run.call_count == initial_call_count  # No new call

            # Verify error details
            error_data = hook_manager.error_memory.is_known_failing_hook("PreToolUse")
            assert error_data is not None
            assert "run_tests_sequential.sh" in error_data["details"]
