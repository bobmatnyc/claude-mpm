"""Tests for MCP session data models.

Tests SessionStatus enum, SessionInfo dataclass, and SessionResult dataclass
to verify correct instantiation and field handling.
"""

from dataclasses import asdict

import pytest

from claude_mpm.mcp.models import SessionInfo, SessionResult, SessionStatus


class TestSessionStatus:
    """Tests for SessionStatus enum."""

    def test_starting_status_value(self):
        """SessionStatus.STARTING should have value 'starting'."""
        assert SessionStatus.STARTING.value == "starting"

    def test_active_status_value(self):
        """SessionStatus.ACTIVE should have value 'active'."""
        assert SessionStatus.ACTIVE.value == "active"

    def test_completed_status_value(self):
        """SessionStatus.COMPLETED should have value 'completed'."""
        assert SessionStatus.COMPLETED.value == "completed"

    def test_error_status_value(self):
        """SessionStatus.ERROR should have value 'error'."""
        assert SessionStatus.ERROR.value == "error"

    def test_stopped_status_value(self):
        """SessionStatus.STOPPED should have value 'stopped'."""
        assert SessionStatus.STOPPED.value == "stopped"

    def test_all_statuses_exist(self):
        """All expected status values should be defined in the enum."""
        expected_statuses = {"starting", "active", "completed", "error", "stopped"}
        actual_statuses = {status.value for status in SessionStatus}
        assert actual_statuses == expected_statuses

    def test_status_from_value(self):
        """SessionStatus should be constructible from string value."""
        assert SessionStatus("starting") == SessionStatus.STARTING
        assert SessionStatus("active") == SessionStatus.ACTIVE
        assert SessionStatus("completed") == SessionStatus.COMPLETED
        assert SessionStatus("error") == SessionStatus.ERROR
        assert SessionStatus("stopped") == SessionStatus.STOPPED

    def test_invalid_status_value_raises(self):
        """Invalid status value should raise ValueError."""
        with pytest.raises(ValueError):
            SessionStatus("invalid_status")


class TestSessionInfo:
    """Tests for SessionInfo dataclass."""

    def test_creation_with_required_fields(self):
        """SessionInfo should be created with required fields only."""
        info = SessionInfo(
            session_id="test-123",
            status=SessionStatus.ACTIVE,
            start_time="2025-01-01T00:00:00Z",
            working_directory="/path/to/project",
        )

        assert info.session_id == "test-123"
        assert info.status == SessionStatus.ACTIVE
        assert info.start_time == "2025-01-01T00:00:00Z"
        assert info.working_directory == "/path/to/project"

    def test_default_optional_fields(self):
        """SessionInfo optional fields should have correct defaults."""
        info = SessionInfo(
            session_id="test-123",
            status=SessionStatus.STARTING,
            start_time="2025-01-01T00:00:00Z",
            working_directory="/path/to/project",
        )

        assert info.last_activity is None
        assert info.message_count == 0
        assert info.last_output is None

    def test_creation_with_all_fields(self):
        """SessionInfo should accept all fields including optional ones."""
        info = SessionInfo(
            session_id="test-456",
            status=SessionStatus.COMPLETED,
            start_time="2025-01-01T00:00:00Z",
            working_directory="/path/to/project",
            last_activity="2025-01-01T01:00:00Z",
            message_count=5,
            last_output="Task completed successfully",
        )

        assert info.session_id == "test-456"
        assert info.status == SessionStatus.COMPLETED
        assert info.last_activity == "2025-01-01T01:00:00Z"
        assert info.message_count == 5
        assert info.last_output == "Task completed successfully"

    def test_asdict_conversion(self):
        """SessionInfo should convert to dict correctly."""
        info = SessionInfo(
            session_id="test-789",
            status=SessionStatus.ERROR,
            start_time="2025-01-01T00:00:00Z",
            working_directory="/tmp",
            message_count=3,
        )

        data = asdict(info)

        assert data["session_id"] == "test-789"
        assert data["status"] == SessionStatus.ERROR  # Note: Enum not converted
        assert data["start_time"] == "2025-01-01T00:00:00Z"
        assert data["working_directory"] == "/tmp"
        assert data["message_count"] == 3

    def test_different_status_values(self):
        """SessionInfo should work with all status values."""
        for status in SessionStatus:
            info = SessionInfo(
                session_id=f"test-{status.value}",
                status=status,
                start_time="2025-01-01T00:00:00Z",
                working_directory="/tmp",
            )
            assert info.status == status


class TestSessionResult:
    """Tests for SessionResult dataclass."""

    def test_creation_with_success_only(self):
        """SessionResult should be created with success flag only."""
        result = SessionResult(success=True)

        assert result.success is True
        assert result.session_id is None
        assert result.output is None
        assert result.error is None
        assert result.messages == []

    def test_creation_with_failure(self):
        """SessionResult should handle failure case."""
        result = SessionResult(success=False)

        assert result.success is False

    def test_creation_with_all_fields(self):
        """SessionResult should accept all fields."""
        messages = [
            {"type": "assistant", "content": "Hello"},
            {"type": "tool", "name": "read_file"},
        ]

        result = SessionResult(
            success=True,
            session_id="session-123",
            output="Operation completed",
            error=None,
            messages=messages,
        )

        assert result.success is True
        assert result.session_id == "session-123"
        assert result.output == "Operation completed"
        assert result.error is None
        assert len(result.messages) == 2
        assert result.messages[0]["type"] == "assistant"

    def test_error_result(self):
        """SessionResult should handle error case with error message."""
        result = SessionResult(
            success=False,
            session_id="session-456",
            error="Timeout occurred",
        )

        assert result.success is False
        assert result.session_id == "session-456"
        assert result.error == "Timeout occurred"

    def test_messages_default_is_empty_list(self):
        """SessionResult messages should default to empty list, not None."""
        result = SessionResult(success=True)

        assert result.messages == []
        assert isinstance(result.messages, list)

    def test_messages_independence(self):
        """Each SessionResult should have its own messages list."""
        result1 = SessionResult(success=True)
        result2 = SessionResult(success=True)

        result1.messages.append({"test": "data"})

        assert result1.messages == [{"test": "data"}]
        assert result2.messages == []

    def test_asdict_conversion(self):
        """SessionResult should convert to dict correctly."""
        result = SessionResult(
            success=True,
            session_id="test-id",
            output="output text",
            error=None,
            messages=[{"type": "result"}],
        )

        data = asdict(result)

        assert data["success"] is True
        assert data["session_id"] == "test-id"
        assert data["output"] == "output text"
        assert data["error"] is None
        assert data["messages"] == [{"type": "result"}]
