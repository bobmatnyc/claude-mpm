#!/usr/bin/env python3
"""
Tests for PostmortemService.

WHY: Ensure postmortem analysis correctly categorizes errors and generates
appropriate improvement actions based on error source.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.analysis.postmortem_service import (
    ActionType,
    ErrorCategory,
    PostmortemService,
    get_postmortem_service,
)
from claude_mpm.services.memory.failure_tracker import FailureEvent, FailureTracker


class TestPostmortemService:
    """Test suite for PostmortemService."""

    @pytest.fixture
    def tracker(self):
        """Create a failure tracker with test data."""
        tracker = FailureTracker()
        return tracker

    @pytest.fixture
    def service(self, tracker):
        """Create a postmortem service with mocked tracker."""
        with patch(
            "claude_mpm.services.analysis.postmortem_service.get_failure_tracker",
            return_value=tracker,
        ):
            service = PostmortemService()
            return service

    def test_singleton_pattern(self):
        """Test that get_postmortem_service returns singleton."""
        service1 = get_postmortem_service()
        service2 = get_postmortem_service()
        assert service1 is service2

    def test_categorize_script_error(self, service):
        """Test categorization of script errors."""
        failure = FailureEvent(
            task_id="test-1",
            task_type="script",
            tool_name="Bash",
            error_message="ImportError: No module named 'foo'",
            context={"error_type": "import-error"},
        )

        analysis = service._analyze_failure(failure)

        assert analysis.category == ErrorCategory.SCRIPT
        assert analysis.action_type == ActionType.AUTO_FIX
        assert analysis.auto_fixable

    def test_categorize_skill_error(self, service):
        """Test categorization of skill errors."""
        failure = FailureEvent(
            task_id="test-2",
            task_type="execution",
            tool_name="Task",
            error_message="Skill validation failed",
            context={"error_type": "validation-error"},
        )

        # Mock file path to skill
        with patch.object(
            service,
            "_extract_file_path",
            return_value=Path(".claude/skills/my-skill.md"),
        ):
            analysis = service._analyze_failure(failure)

        assert analysis.category == ErrorCategory.SKILL
        assert analysis.action_type == ActionType.UPDATE_FILE

    def test_categorize_agent_error(self, service):
        """Test categorization of agent errors."""
        failure = FailureEvent(
            task_id="test-3",
            task_type="execution",
            tool_name="Task",
            error_message="Agent execution failed",
            context={"error_type": "execution-error", "agent_type": "engineer"},
        )

        # Mock file path to agent
        with patch.object(
            service,
            "_extract_file_path",
            return_value=Path(".claude/agents/engineer.md"),
        ):
            analysis = service._analyze_failure(failure)

        assert analysis.category == ErrorCategory.AGENT
        assert analysis.action_type == ActionType.CREATE_PR

    def test_categorize_user_code_error(self, service):
        """Test categorization of user code errors."""
        failure = FailureEvent(
            task_id="test-4",
            task_type="test",
            tool_name="Bash",
            error_message="TypeError: unsupported operand",
            context={"error_type": "type-error"},
        )

        # Mock file path to user code
        with patch.object(
            service, "_extract_file_path", return_value=Path("src/my_app/main.py")
        ):
            analysis = service._analyze_failure(failure)

        assert analysis.category == ErrorCategory.USER_CODE
        assert analysis.action_type == ActionType.SUGGEST

    def test_extract_file_path_from_error(self, service):
        """Test file path extraction from error messages."""
        failure = FailureEvent(
            task_id="test-5",
            task_type="script",
            tool_name="Bash",
            error_message='File "src/claude_mpm/scripts/test.py", line 42, in <module>',
            context={},
        )

        file_path = service._extract_file_path(failure)
        assert file_path == Path("src/claude_mpm/scripts/test.py")

    def test_priority_calculation(self, service):
        """Test priority calculation based on error type."""
        # Critical error
        failure_critical = FailureEvent(
            task_id="test-6",
            task_type="script",
            tool_name="Bash",
            error_message="SyntaxError: invalid syntax",
            context={"error_type": "syntax-error"},
        )
        priority = service._calculate_priority(failure_critical)
        assert priority == "critical"

        # High priority error
        failure_high = FailureEvent(
            task_id="test-7",
            task_type="test",
            tool_name="Bash",
            error_message="TypeError: unsupported operand",
            context={"error_type": "type-error"},
        )
        priority = service._calculate_priority(failure_high)
        assert priority == "high"

        # Medium priority (default)
        failure_medium = FailureEvent(
            task_id="test-8",
            task_type="execution",
            tool_name="Bash",
            error_message="Command failed",
            context={"error_type": "command-error"},
        )
        priority = service._calculate_priority(failure_medium)
        assert priority == "medium"

    def test_generate_auto_fix_action(self, service):
        """Test auto-fix action generation for scripts."""
        failure = FailureEvent(
            task_id="test-9",
            task_type="script",
            tool_name="Bash",
            error_message="ImportError: No module named 'foo'",
            context={"error_type": "import-error"},
        )

        analysis = service._analyze_failure(failure)
        analysis.affected_file = Path("src/claude_mpm/scripts/test.py")

        action = service._create_auto_fix_action(analysis)

        assert action.action_type == ActionType.AUTO_FIX
        assert len(action.commands) > 0
        assert "python -m py_compile" in action.commands[0]

    def test_generate_pr_action(self, service):
        """Test PR action generation for agents."""
        failure = FailureEvent(
            task_id="test-10",
            task_type="execution",
            tool_name="Task",
            error_message="Agent timeout on large dataset",
            context={"error_type": "timeout", "agent_type": "engineer"},
        )

        analysis = service._analyze_failure(failure)
        analysis.affected_file = Path(".claude/agents/engineer.md")
        analysis.category = ErrorCategory.AGENT
        analysis.action_type = ActionType.CREATE_PR

        action = service._create_pr_action(analysis)

        assert action.action_type == ActionType.CREATE_PR
        assert action.pr_branch is not None
        assert "fix/" in action.pr_branch
        assert action.pr_title is not None
        assert action.pr_body is not None
        assert "## Problem" in action.pr_body

    @patch("claude_mpm.services.session_manager.get_session_manager")
    def test_analyze_session(self, mock_session_mgr, service, tracker):
        """Test full session analysis."""
        # Mock session manager
        mock_mgr = MagicMock()
        mock_mgr.get_session_id.return_value = "test-session-123"
        mock_mgr._session_start_time = datetime.now(timezone.utc)
        mock_session_mgr.return_value = mock_mgr

        # Add test failures
        tracker.failures = [
            FailureEvent(
                task_id="f1",
                task_type="script",
                tool_name="Bash",
                error_message="ImportError: No module named 'foo'",
                context={"error_type": "import-error"},
            ),
            FailureEvent(
                task_id="f2",
                task_type="test",
                tool_name="Bash",
                error_message="Test failed: assertion error",
                context={"error_type": "test-failure"},
            ),
        ]

        # Run analysis
        report = service.analyze_session()

        # Verify report
        assert report.session_id == "test-session-123"
        assert report.total_errors == 2
        assert len(report.analyses) == 2
        assert len(report.actions) >= 1  # At least some actions generated
        assert report.stats["total_errors"] == 2

    def test_report_statistics(self, service, tracker):
        """Test statistics calculation in report."""
        # Add mixed failures
        tracker.failures = [
            FailureEvent(
                task_id="f1",
                task_type="script",
                tool_name="Bash",
                error_message="SyntaxError",
                context={"error_type": "syntax-error"},
            ),
            FailureEvent(
                task_id="f2",
                task_type="execution",
                tool_name="Task",
                error_message="Agent error",
                context={"error_type": "error", "agent_type": "engineer"},
            ),
            FailureEvent(
                task_id="f3",
                task_type="test",
                tool_name="Bash",
                error_message="Test failure",
                context={"error_type": "test-failure"},
            ),
        ]

        with patch("claude_mpm.services.session_manager.get_session_manager") as mock:
            mock_mgr = MagicMock()
            mock_mgr.get_session_id.return_value = "test"
            mock_mgr._session_start_time = datetime.now(timezone.utc)
            mock.return_value = mock_mgr

            report = service.analyze_session()

        # Verify statistics
        assert report.stats["total_errors"] == 3
        assert report.stats["critical_priority"] >= 1  # Syntax error is critical
        assert report.stats["total_actions"] >= 1


class TestErrorAnalysis:
    """Test error analysis functionality."""

    def test_file_path_extraction_patterns(self):
        """Test various file path extraction patterns."""
        service = PostmortemService()

        # Python traceback format
        failure1 = FailureEvent(
            task_id="t1",
            task_type="script",
            tool_name="Bash",
            error_message='File "path/to/file.py", line 10',
            context={},
        )
        path1 = service._extract_file_path(failure1)
        assert path1 == Path("path/to/file.py")

        # Path with line and column
        failure2 = FailureEvent(
            task_id="t2",
            task_type="script",
            tool_name="Bash",
            error_message="Error in src/main.py:42:10",
            context={},
        )
        path2 = service._extract_file_path(failure2)
        assert path2 == Path("src/main.py")

        # No path in message
        failure3 = FailureEvent(
            task_id="t3",
            task_type="script",
            tool_name="Bash",
            error_message="Generic error message",
            context={},
        )
        path3 = service._extract_file_path(failure3)
        assert path3 is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
