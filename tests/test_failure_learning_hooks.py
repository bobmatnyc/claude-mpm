#!/usr/bin/env python3
"""
Unit tests for failure-learning hooks.

Tests cover:
- FailureDetectionHook: Detects failures from tool outputs
- FixDetectionHook: Matches fixes with failures
- LearningExtractionHook: Extracts and persists learnings
- Integration: End-to-end failure-learning cycle
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from claude_mpm.hooks.base_hook import HookContext, HookResult, HookType
from claude_mpm.hooks.failure_learning import (
    FailureDetectionHook,
    FixDetectionHook,
    LearningExtractionHook,
    get_failure_detection_hook,
    get_fix_detection_hook,
    get_learning_extraction_hook,
)
from claude_mpm.services.memory.failure_tracker import (
    get_failure_tracker,
    reset_failure_tracker,
)


class TestFailureDetectionHook:
    """Test FailureDetectionHook behavior."""

    def setup_method(self):
        """Reset tracker before each test."""
        reset_failure_tracker()
        self.hook = FailureDetectionHook()

    def test_hook_initialization(self):
        """Test hook is initialized with correct priority."""
        assert self.hook.name == "failure_detection"
        assert self.hook.priority == 85
        assert self.hook.enabled

    def test_factory_function(self):
        """Test factory function creates hook instance."""
        hook = get_failure_detection_hook()
        assert isinstance(hook, FailureDetectionHook)
        assert hook.priority == 85

    def test_validate_requires_post_delegation(self):
        """Test validation requires POST_DELEGATION hook type."""
        # Valid context
        valid_context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={"tool_name": "Bash", "output": "Error: Test"},
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )
        assert self.hook.validate(valid_context)

        # Invalid hook type
        invalid_context = HookContext(
            hook_type=HookType.PRE_DELEGATION,
            data={"tool_name": "Bash"},
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )
        assert not self.hook.validate(invalid_context)

    def test_validate_requires_tool_name(self):
        """Test validation requires tool_name in data."""
        # Valid context
        valid_context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={"tool_name": "Bash"},
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )
        assert self.hook.validate(valid_context)

        # Missing tool_name
        invalid_context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={},
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )
        assert not self.hook.validate(invalid_context)

    def test_execute_detects_bash_error(self):
        """Test hook detects errors from Bash tool."""
        context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={
                "tool_name": "Bash",
                "output": "Error: Command not found",
                "exit_code": 1,
            },
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        result = self.hook.execute(context)

        assert result.success
        assert result.metadata.get("failure_detected")
        assert "failure_id" in result.metadata

        # Verify failure was recorded
        tracker = get_failure_tracker()
        assert len(tracker.failures) == 1
        assert tracker.failures[0].tool_name == "Bash"

    def test_execute_detects_test_failure(self):
        """Test hook detects test failures."""
        context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={
                "tool_name": "Bash",
                "output": "FAILED tests/test_example.py::test_foo",
                "exit_code": 1,
            },
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        result = self.hook.execute(context)

        assert result.success
        assert result.metadata.get("failure_detected")

        # Verify task was classified as test
        tracker = get_failure_tracker()
        assert tracker.failures[0].task_type == "test"

    def test_execute_skips_unmonitored_tools(self):
        """Test hook skips tools not in MONITORED_TOOLS."""
        context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={
                "tool_name": "Read",  # Not monitored
                "output": "Error: File not found",
                "exit_code": 1,
            },
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        result = self.hook.execute(context)

        assert result.success
        assert not result.metadata or not result.metadata.get("failure_detected")

        # Verify no failure recorded
        tracker = get_failure_tracker()
        assert len(tracker.failures) == 0

    def test_execute_skips_successful_execution(self):
        """Test hook skips successful executions."""
        context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={
                "tool_name": "Bash",
                "output": "Success! All tests passed",
                "exit_code": 0,
            },
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        result = self.hook.execute(context)

        assert result.success
        assert not result.metadata or not result.metadata.get("failure_detected")

        # Verify no failure recorded
        tracker = get_failure_tracker()
        assert len(tracker.failures) == 0

    def test_execute_includes_context(self):
        """Test hook includes context in failure event."""
        context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={
                "tool_name": "Bash",
                "output": "Error: Build failed",
                "exit_code": 1,
                "agent_type": "engineer",
                "working_directory": "/project",
            },
            metadata={},
            timestamp=datetime.now(timezone.utc),
            session_id="test-session-123",
        )

        result = self.hook.execute(context)

        assert result.success

        # Verify context was captured
        tracker = get_failure_tracker()
        failure = tracker.failures[0]
        assert failure.context.get("agent_type") == "engineer"
        assert failure.context.get("session_id") == "test-session-123"


class TestFixDetectionHook:
    """Test FixDetectionHook behavior."""

    def setup_method(self):
        """Reset tracker before each test."""
        reset_failure_tracker()
        self.hook = FixDetectionHook()

    def test_hook_initialization(self):
        """Test hook is initialized with correct priority."""
        assert self.hook.name == "fix_detection"
        assert self.hook.priority == 87
        assert self.hook.enabled

    def test_factory_function(self):
        """Test factory function creates hook instance."""
        hook = get_fix_detection_hook()
        assert isinstance(hook, FixDetectionHook)
        assert hook.priority == 87

    def test_execute_detects_fix(self):
        """Test hook detects fix for previous failure."""
        # First, create a failure
        tracker = get_failure_tracker()
        tracker.detect_failure("Bash", "Error: Test failed")

        # Now simulate a successful execution
        context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={"tool_name": "Bash", "output": "All tests passed", "exit_code": 0},
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        result = self.hook.execute(context)

        assert result.success
        assert result.metadata.get("fix_detected")
        assert "failure_id" in result.metadata
        assert "fix_event" in result.metadata
        assert "failure_event" in result.metadata

    def test_execute_skips_when_no_failures(self):
        """Test hook skips when there are no failures to fix."""
        context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={"tool_name": "Bash", "output": "Success", "exit_code": 0},
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        result = self.hook.execute(context)

        assert result.success
        assert not result.metadata or not result.metadata.get("fix_detected")

    def test_execute_skips_failed_execution(self):
        """Test hook skips executions with non-zero exit code."""
        # Create a failure first
        tracker = get_failure_tracker()
        tracker.detect_failure("Bash", "Error: Test failed")

        # Try with failed execution
        context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={"tool_name": "Bash", "output": "Still failing", "exit_code": 1},
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        result = self.hook.execute(context)

        assert result.success
        assert not result.metadata or not result.metadata.get("fix_detected")

    def test_execute_skips_unmonitored_tools(self):
        """Test hook skips tools not in MONITORED_TOOLS."""
        # Create a failure with Bash
        tracker = get_failure_tracker()
        tracker.detect_failure("Bash", "Error: Test failed")

        # Try to fix with unmonitored tool
        context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={
                "tool_name": "Read",  # Not monitored
                "output": "Success",
                "exit_code": 0,
            },
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        result = self.hook.execute(context)

        assert result.success
        assert not result.metadata or not result.metadata.get("fix_detected")


class TestLearningExtractionHook:
    """Test LearningExtractionHook behavior."""

    def setup_method(self):
        """Reset tracker before each test."""
        reset_failure_tracker()
        self.hook = LearningExtractionHook()

    def test_hook_initialization(self):
        """Test hook is initialized with correct priority."""
        assert self.hook.name == "learning_extraction"
        assert self.hook.priority == 89
        assert self.hook.enabled

    def test_factory_function(self):
        """Test factory function creates hook instance."""
        hook = get_learning_extraction_hook()
        assert isinstance(hook, LearningExtractionHook)
        assert hook.priority == 89

    def test_validate_requires_fix_detected(self):
        """Test validation requires fix_detected metadata."""
        # Valid context with fix_detected
        valid_context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={},
            metadata={"fix_detected": True},
            timestamp=datetime.now(timezone.utc),
        )
        assert self.hook.validate(valid_context)

        # Missing fix_detected
        invalid_context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={},
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )
        assert not self.hook.validate(invalid_context)

    @patch("claude_mpm.services.agents.memory.agent_memory_manager.get_memory_manager")
    def test_execute_extracts_learning(self, mock_get_memory_manager):
        """Test hook extracts learning from fix event."""
        # Mock memory manager
        mock_manager = Mock()
        mock_manager.update_agent_memory = Mock(return_value=True)
        mock_get_memory_manager.return_value = mock_manager

        # Create failure and fix
        tracker = get_failure_tracker()
        failure = tracker.detect_failure("Bash", "Error: Test failed")
        fix_result = tracker.detect_fix("Bash", "Success", exit_code=0)
        fix_event, failure_event = fix_result

        # Execute hook
        context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={},
            metadata={
                "fix_detected": True,
                "failure_event": failure_event,
                "fix_event": fix_event,
            },
            timestamp=datetime.now(timezone.utc),
        )

        result = self.hook.execute(context)

        assert result.success
        assert result.metadata.get("learning_extracted")
        assert "target_agent" in result.metadata
        assert "learning_category" in result.metadata

        # Verify memory manager was called
        mock_manager.update_agent_memory.assert_called_once()

    @patch("claude_mpm.services.agents.memory.agent_memory_manager.get_memory_manager")
    def test_execute_writes_to_agent_memory(self, mock_get_memory_manager):
        """Test hook writes learning to agent memory."""
        # Mock memory manager
        mock_manager = Mock()
        mock_manager.update_agent_memory = Mock(return_value=True)
        mock_get_memory_manager.return_value = mock_manager

        # Create failure and fix with specific agent
        tracker = get_failure_tracker()
        failure = tracker.detect_failure(
            "Bash", "FAILED tests/test_example.py", {"agent_type": "qa"}
        )
        fix_result = tracker.detect_fix("Bash", "Success", exit_code=0)
        fix_event, failure_event = fix_result

        # Execute hook
        context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={"agent_type": "qa"},
            metadata={
                "fix_detected": True,
                "failure_event": failure_event,
                "fix_event": fix_event,
            },
            timestamp=datetime.now(timezone.utc),
        )

        result = self.hook.execute(context)

        assert result.success

        # Verify memory was updated for correct agent
        call_args = mock_manager.update_agent_memory.call_args
        assert call_args[1]["agent_id"] == "qa"

    def test_execute_skips_when_no_fix_detected(self):
        """Test hook skips execution when fix not detected."""
        context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={},
            metadata={},  # No fix_detected
            timestamp=datetime.now(timezone.utc),
        )

        result = self.hook.execute(context)

        assert result.success
        assert not result.metadata or not result.metadata.get("learning_extracted")


class TestIntegration:
    """Test end-to-end failure-learning cycle."""

    def setup_method(self):
        """Reset tracker and create hooks before each test."""
        reset_failure_tracker()
        self.failure_hook = FailureDetectionHook()
        self.fix_hook = FixDetectionHook()
        self.learning_hook = LearningExtractionHook()

    @patch("claude_mpm.services.agents.memory.agent_memory_manager.get_memory_manager")
    def test_complete_failure_learning_cycle(self, mock_get_memory_manager):
        """Test complete cycle: failure → fix → learning."""
        # Mock memory manager
        mock_manager = Mock()
        mock_manager.update_agent_memory = Mock(return_value=True)
        mock_get_memory_manager.return_value = mock_manager

        # Step 1: Failure occurs
        failure_context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={
                "tool_name": "Bash",
                "output": "Error: Test failed",
                "exit_code": 1,
                "agent_type": "qa",
            },
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        failure_result = self.failure_hook.execute(failure_context)
        assert failure_result.success
        assert failure_result.metadata.get("failure_detected")

        # Step 2: Fix occurs
        fix_context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={
                "tool_name": "Bash",
                "output": "All tests passed",
                "exit_code": 0,
                "agent_type": "qa",
            },
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        fix_result = self.fix_hook.execute(fix_context)
        assert fix_result.success
        assert fix_result.metadata.get("fix_detected")

        # Step 3: Learning extraction
        learning_context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={"agent_type": "qa"},
            metadata={
                "fix_detected": True,
                "failure_event": fix_result.metadata["failure_event"],
                "fix_event": fix_result.metadata["fix_event"],
            },
            timestamp=datetime.now(timezone.utc),
        )

        learning_result = self.learning_hook.execute(learning_context)
        assert learning_result.success
        assert learning_result.metadata.get("learning_extracted")
        assert learning_result.metadata["target_agent"] == "qa"

        # Verify learning was written to memory
        mock_manager.update_agent_memory.assert_called_once()

    def test_hook_priority_ordering(self):
        """Test hooks are ordered by priority."""
        hooks = [self.failure_hook, self.fix_hook, self.learning_hook]
        sorted_hooks = sorted(hooks)

        assert sorted_hooks[0].priority == 85  # Failure detection
        assert sorted_hooks[1].priority == 87  # Fix detection
        assert sorted_hooks[2].priority == 89  # Learning extraction


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
