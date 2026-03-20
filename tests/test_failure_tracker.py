#!/usr/bin/env python3
"""
Unit tests for FailureTracker service.

Tests cover:
- Failure detection from various error patterns
- Task type classification
- Fix detection and matching with failures
- Learning extraction from failure-fix pairs
- Session statistics and reporting
"""

from datetime import datetime, timezone

import pytest

from claude_mpm.services.memory.failure_tracker import (
    FailureEvent,
    FailureTracker,
    FixEvent,
    Learning,
    get_failure_tracker,
    reset_failure_tracker,
)


class TestFailureDetection:
    """Test failure detection from tool outputs."""

    def setup_method(self):
        """Reset tracker before each test."""
        reset_failure_tracker()
        self.tracker = FailureTracker()

    def test_detect_simple_error(self):
        """Test detection of simple error message."""
        output = "Error: File not found"
        failure = self.tracker.detect_failure("Bash", output)

        assert failure is not None
        assert failure.task_type == "execution"
        assert failure.tool_name == "Bash"
        assert "File not found" in failure.error_message
        assert not failure.fixed

    def test_detect_exception(self):
        """Test detection of exception."""
        output = "Exception: Division by zero"
        failure = self.tracker.detect_failure("Bash", output)

        assert failure is not None
        assert "Division by zero" in failure.error_message
        assert failure.context.get("error_type") == "exception"

    def test_detect_test_failure(self):
        """Test detection of test failure."""
        output = "pytest output\nFAILED tests/test_example.py::test_something"
        failure = self.tracker.detect_failure("Bash", output)

        assert failure is not None
        assert failure.context.get("error_type") == "test-failure"
        assert failure.task_type == "test"  # Should classify as test

    def test_detect_command_failure(self):
        """Test detection of command failure."""
        output = "Command failed: make build"
        failure = self.tracker.detect_failure("Bash", output)

        assert failure is not None
        assert "make build" in failure.error_message

    def test_detect_syntax_error(self):
        """Test detection of Python syntax error."""
        output = "SyntaxError: invalid syntax"
        failure = self.tracker.detect_failure("NotebookEdit", output)

        assert failure is not None
        assert failure.context.get("error_type") == "syntax-error"

    def test_detect_import_error(self):
        """Test detection of import error."""
        output = "ImportError: No module named 'foo'"
        failure = self.tracker.detect_failure("Bash", output)

        assert failure is not None
        assert failure.context.get("error_type") == "import-error"

    def test_no_failure_on_success(self):
        """Test that success output doesn't trigger failure detection."""
        output = "All tests passed successfully"
        failure = self.tracker.detect_failure("Bash", output)

        assert failure is None

    def test_failure_with_context(self):
        """Test failure detection with additional context."""
        output = "Error: Database connection failed"
        context = {
            "agent_type": "engineer",
            "session_id": "test-session-123",
            "working_dir": "/project",
        }
        failure = self.tracker.detect_failure("Bash", output, context)

        assert failure is not None
        assert failure.context.get("agent_type") == "engineer"
        assert failure.context.get("session_id") == "test-session-123"


class TestTaskClassification:
    """Test task type classification."""

    def setup_method(self):
        """Reset tracker before each test."""
        reset_failure_tracker()
        self.tracker = FailureTracker()

    def test_classify_test_task(self):
        """Test classification of test-related tasks."""
        output = "pytest tests/test_example.py"
        context = {"command": "pytest"}
        task_type = self.tracker._classify_task_type(output, context)

        assert task_type == "test"

    def test_classify_build_task(self):
        """Test classification of build tasks."""
        output = "make: *** [build] Error 1"
        context = {"command": "make build"}
        task_type = self.tracker._classify_task_type(output, context)

        assert task_type == "build"

    def test_classify_lint_task(self):
        """Test classification of linting tasks."""
        output = "Running flake8..."
        context = {"command": "flake8 src/"}
        task_type = self.tracker._classify_task_type(output, context)

        assert task_type == "lint"

    def test_classify_git_task(self):
        """Test classification of git tasks."""
        output = "fatal: not a git repository"
        context = {"command": "git commit"}
        task_type = self.tracker._classify_task_type(output, context)

        assert task_type == "git"

    def test_classify_install_task(self):
        """Test classification of install tasks."""
        output = "Installing dependencies..."
        context = {"command": "pip install -r requirements.txt"}
        task_type = self.tracker._classify_task_type(output, context)

        assert task_type == "install"

    def test_classify_generic_execution(self):
        """Test classification of generic execution."""
        output = "Running script..."
        context = {"command": "echo hello"}
        task_type = self.tracker._classify_task_type(output, context)

        # Script pattern matches .py files, not "echo" commands
        # For pure echo, it should still be execution or script
        assert task_type in ["execution", "script"]


class TestFixDetection:
    """Test fix detection and matching with failures."""

    def setup_method(self):
        """Reset tracker before each test."""
        reset_failure_tracker()
        self.tracker = FailureTracker()

    def test_detect_fix_for_failure(self):
        """Test that fix is detected for matching failure."""
        # Create a failure
        failure_output = "Error: Test failed"
        failure = self.tracker.detect_failure("Bash", failure_output)
        assert failure is not None

        # Simulate a fix
        fix_output = "All tests passed"
        fix_result = self.tracker.detect_fix("Bash", fix_output, exit_code=0)

        assert fix_result is not None
        _fix_event, matched_failure = fix_result
        assert matched_failure.task_id == failure.task_id
        assert matched_failure.fixed
        assert matched_failure.fix_timestamp is not None

    def test_no_fix_without_failure(self):
        """Test that success doesn't create fix without prior failure."""
        fix_output = "Success"
        fix_result = self.tracker.detect_fix("Bash", fix_output, exit_code=0)

        assert fix_result is None

    def test_fix_matches_most_recent_failure(self):
        """Test that fix matches the most recent unfixed failure."""
        # Create two failures
        failure1 = self.tracker.detect_failure("Bash", "Error: First error")
        failure2 = self.tracker.detect_failure("Bash", "Error: Second error")

        # Simulate a fix
        fix_result = self.tracker.detect_fix("Bash", "Success", exit_code=0)

        assert fix_result is not None
        _, matched_failure = fix_result
        # Should match most recent failure
        assert matched_failure.task_id == failure2.task_id

    def test_fix_only_matches_same_tool(self):
        """Test that fix only matches failures from same tool."""
        # Create failure with Bash
        self.tracker.detect_failure("Bash", "Error: Test failed")

        # Try to fix with different tool
        fix_result = self.tracker.detect_fix("NotebookEdit", "Success", exit_code=0)

        # Should not match
        assert fix_result is None

    def test_fix_requires_success_exit_code(self):
        """Test that non-zero exit code doesn't detect fix."""
        # Create failure
        self.tracker.detect_failure("Bash", "Error: Test failed")

        # Try to fix with non-zero exit code
        fix_result = self.tracker.detect_fix("Bash", "Output", exit_code=1)

        assert fix_result is None

    def test_get_unfixed_failures(self):
        """Test getting unfixed failures."""
        # Create some failures
        failure1 = self.tracker.detect_failure("Bash", "Error: First")
        failure2 = self.tracker.detect_failure("Bash", "Error: Second")

        # Fix one (the most recent one will be fixed first due to reverse order matching)
        self.tracker.detect_fix("Bash", "Success", exit_code=0)

        # Get unfixed failures
        unfixed = self.tracker.get_unfixed_failures()

        # One failure should be unfixed
        assert len(unfixed) == 1
        # The unfixed one should be one of the two failures
        assert unfixed[0].task_id in [failure1.task_id, failure2.task_id]


class TestLearningExtraction:
    """Test learning extraction from failure-fix pairs."""

    def setup_method(self):
        """Reset tracker before each test."""
        reset_failure_tracker()
        self.tracker = FailureTracker()

    def test_extract_learning_from_fix(self):
        """Test learning extraction from failure-fix pair."""
        # Create failure and fix
        failure = self.tracker.detect_failure(
            "Bash", "Error: Test failed", {"agent_type": "qa"}
        )
        fix_result = self.tracker.detect_fix("Bash", "Success", exit_code=0)
        assert fix_result is not None

        fix_event, failure_event = fix_result

        # Extract learning
        learning = self.tracker.extract_learning(fix_event, failure_event)

        assert learning is not None
        assert learning.target_agent == "qa"
        # Category depends on error_type, which is "error" for "Error: Test failed"
        assert learning.category in ["Testing", "General", "Error Handling"]
        assert learning.problem
        assert learning.solution
        assert learning.failure_event == failure_event
        assert learning.fix_event == fix_event

    def test_learning_categorization(self):
        """Test that learnings are categorized correctly."""
        # Test-related learning
        failure = self.tracker.detect_failure("Bash", "FAILED tests/test_example.py")
        fix_result = self.tracker.detect_fix("Bash", "Success", exit_code=0)
        fix_event, failure_event = fix_result

        learning = self.tracker.extract_learning(fix_event, failure_event)
        assert learning.category == "Testing"

        # Reset for next test
        reset_failure_tracker()
        self.tracker = FailureTracker()

        # Import-related learning
        failure = self.tracker.detect_failure(
            "Bash", "ImportError: No module named 'foo'"
        )
        fix_result = self.tracker.detect_fix("Bash", "Success", exit_code=0)
        fix_event, failure_event = fix_result

        learning = self.tracker.extract_learning(fix_event, failure_event)
        assert learning.category == "Dependencies"

    def test_learning_to_markdown(self):
        """Test learning conversion to markdown format."""
        # Create learning
        failure = self.tracker.detect_failure("Bash", "Error: Build failed")
        fix_result = self.tracker.detect_fix("Bash", "Success", exit_code=0)
        fix_event, failure_event = fix_result

        learning = self.tracker.extract_learning(fix_event, failure_event)
        markdown = learning.to_markdown()

        # Verify markdown structure
        assert "##" in markdown  # Category header
        assert "**Problem**:" in markdown
        assert "**Solution**:" in markdown
        assert "**Context**:" in markdown
        assert "**Date**:" in markdown

    def test_agent_routing_by_task_type(self):
        """Test that learnings are routed to appropriate agents."""
        # Test task → qa agent
        failure = self.tracker.detect_failure("Bash", "FAILED tests/test_example.py")
        fix_result = self.tracker.detect_fix("Bash", "Success", exit_code=0)
        fix_event, failure_event = fix_result

        learning = self.tracker.extract_learning(fix_event, failure_event)
        assert learning.target_agent == "qa"

        # Reset for next test
        reset_failure_tracker()
        self.tracker = FailureTracker()

        # Build task → engineer agent
        failure = self.tracker.detect_failure(
            "Bash", "Error: Build failed", {"command": "make build"}
        )
        fix_result = self.tracker.detect_fix("Bash", "Success", exit_code=0)
        fix_event, failure_event = fix_result

        learning = self.tracker.extract_learning(fix_event, failure_event)
        assert learning.target_agent == "engineer"

    def test_get_learnings_for_agent(self):
        """Test filtering learnings by agent."""
        # Create learnings for different agents
        for i in range(3):
            failure = self.tracker.detect_failure("Bash", f"FAILED test_{i}")
            fix_result = self.tracker.detect_fix("Bash", "Success", exit_code=0)
            fix_event, failure_event = fix_result
            self.tracker.extract_learning(fix_event, failure_event, target_agent="qa")

        for i in range(2):
            failure = self.tracker.detect_failure(
                "Bash", f"Error: Build {i} failed", {"command": "make build"}
            )
            fix_result = self.tracker.detect_fix("Bash", "Success", exit_code=0)
            fix_event, failure_event = fix_result
            self.tracker.extract_learning(
                fix_event, failure_event, target_agent="engineer"
            )

        # Get learnings for each agent
        qa_learnings = self.tracker.get_learnings_for_agent("qa")
        engineer_learnings = self.tracker.get_learnings_for_agent("engineer")

        assert len(qa_learnings) == 3
        assert len(engineer_learnings) == 2


class TestSessionStatistics:
    """Test session statistics and reporting."""

    def setup_method(self):
        """Reset tracker before each test."""
        reset_failure_tracker()
        self.tracker = FailureTracker()

    def test_session_stats_empty(self):
        """Test stats for empty session."""
        stats = self.tracker.get_session_stats()

        assert stats["total_failures"] == 0
        assert stats["fixed_failures"] == 0
        assert stats["unfixed_failures"] == 0
        assert stats["total_fixes"] == 0
        assert stats["total_learnings"] == 0

    def test_session_stats_with_failures(self):
        """Test stats with failures only."""
        # Create some failures
        self.tracker.detect_failure("Bash", "Error: First")
        self.tracker.detect_failure("Bash", "Error: Second")
        self.tracker.detect_failure("Bash", "Error: Third")

        stats = self.tracker.get_session_stats()

        assert stats["total_failures"] == 3
        assert stats["fixed_failures"] == 0
        assert stats["unfixed_failures"] == 3
        assert stats["total_fixes"] == 0

    def test_session_stats_with_fixes(self):
        """Test stats with failures and fixes."""
        # Create failures and fixes
        self.tracker.detect_failure("Bash", "Error: First")
        self.tracker.detect_fix("Bash", "Success", exit_code=0)

        self.tracker.detect_failure("Bash", "Error: Second")
        self.tracker.detect_fix("Bash", "Success", exit_code=0)

        self.tracker.detect_failure("Bash", "Error: Third")  # Unfixed

        stats = self.tracker.get_session_stats()

        assert stats["total_failures"] == 3
        assert stats["fixed_failures"] == 2
        assert stats["unfixed_failures"] == 1
        assert stats["total_fixes"] == 2

    def test_session_stats_with_learnings(self):
        """Test stats with complete failure-fix-learning cycle."""
        # Create failure, fix, and learning
        failure = self.tracker.detect_failure("Bash", "Error: Test failed")
        fix_result = self.tracker.detect_fix("Bash", "Success", exit_code=0)
        fix_event, failure_event = fix_result
        self.tracker.extract_learning(fix_event, failure_event)

        stats = self.tracker.get_session_stats()

        assert stats["total_failures"] == 1
        assert stats["fixed_failures"] == 1
        assert stats["total_fixes"] == 1
        assert stats["total_learnings"] == 1


class TestSingletonBehavior:
    """Test singleton pattern for FailureTracker."""

    def test_get_failure_tracker_returns_same_instance(self):
        """Test that get_failure_tracker returns same instance."""
        tracker1 = get_failure_tracker()
        tracker2 = get_failure_tracker()

        assert tracker1 is tracker2

    def test_reset_failure_tracker(self):
        """Test that reset creates new instance."""
        tracker1 = get_failure_tracker()
        tracker1.detect_failure("Bash", "Error: Test")

        reset_failure_tracker()
        tracker2 = get_failure_tracker()

        # Should be different instance with empty state
        assert tracker1 is not tracker2
        assert len(tracker2.failures) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
