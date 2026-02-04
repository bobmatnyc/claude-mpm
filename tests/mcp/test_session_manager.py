"""Tests for SessionManager.

Tests session lifecycle, concurrency control, and state management.
All subprocess operations are mocked.
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.mcp.errors import SessionError
from claude_mpm.mcp.models import SessionInfo, SessionResult, SessionStatus
from claude_mpm.mcp.session_manager import SessionManager


class TestSessionManagerInit:
    """Tests for SessionManager initialization."""

    def test_default_max_concurrent(self):
        """Should default to 5 max concurrent sessions."""
        manager = SessionManager()

        # Check semaphore initial value
        assert manager._semaphore._value == 5

    def test_custom_max_concurrent(self):
        """Should accept custom max_concurrent value."""
        manager = SessionManager(max_concurrent=10)

        assert manager._semaphore._value == 10

    def test_default_timeout_none(self):
        """Should default to no timeout."""
        manager = SessionManager()

        assert manager._default_timeout is None

    def test_custom_default_timeout(self):
        """Should accept custom default timeout."""
        manager = SessionManager(default_timeout=60.0)

        assert manager._default_timeout == 60.0

    def test_initial_state_empty(self):
        """Should start with no sessions."""
        manager = SessionManager()

        assert manager._sessions == {}
        assert manager._processes == {}


class TestStartSession:
    """Tests for start_session() method."""

    @pytest.mark.asyncio
    async def test_creates_session_and_returns_result(self):
        """start_session should create session and return result."""
        manager = SessionManager()

        mock_result = SessionResult(
            success=True,
            session_id="new-session-123",
            output="Hello, world!",
            messages=[{"type": "assistant"}],
        )

        mock_subprocess = MagicMock()
        mock_subprocess.working_directory = "/test/dir"
        mock_subprocess.start_session = AsyncMock(
            return_value=("new-session-123", MagicMock())
        )
        mock_subprocess.wait_for_completion = AsyncMock(return_value=mock_result)

        with patch(
            "claude_mpm.mcp.session_manager.ClaudeMPMSubprocess",
            return_value=mock_subprocess,
        ):
            result = await manager.start_session(
                prompt="Hello",
                working_directory="/test/dir",
            )

        assert result.success is True
        assert result.session_id == "new-session-123"
        assert result.output == "Hello, world!"

    @pytest.mark.asyncio
    async def test_tracks_session(self):
        """start_session should track session in internal dict."""
        manager = SessionManager()

        mock_result = SessionResult(
            success=True,
            session_id="tracked-123",
        )

        mock_subprocess = MagicMock()
        mock_subprocess.working_directory = "/project"
        mock_subprocess.start_session = AsyncMock(
            return_value=("tracked-123", MagicMock())
        )
        mock_subprocess.wait_for_completion = AsyncMock(return_value=mock_result)

        with patch(
            "claude_mpm.mcp.session_manager.ClaudeMPMSubprocess",
            return_value=mock_subprocess,
        ):
            await manager.start_session(prompt="Test")

        assert "tracked-123" in manager._sessions
        assert manager._sessions["tracked-123"].session_id == "tracked-123"

    @pytest.mark.asyncio
    async def test_session_status_transitions(self):
        """start_session should transition through status states."""
        manager = SessionManager()
        status_transitions = []

        mock_result = SessionResult(success=True, session_id="status-test")

        mock_subprocess = MagicMock()
        mock_subprocess.working_directory = "/test"
        mock_subprocess.start_session = AsyncMock(
            return_value=("status-test", MagicMock())
        )

        async def slow_wait(*args, **kwargs):
            # Capture status after registration
            await asyncio.sleep(0.01)
            if "status-test" in manager._sessions:
                status_transitions.append(manager._sessions["status-test"].status)
            return mock_result

        mock_subprocess.wait_for_completion = slow_wait

        with patch(
            "claude_mpm.mcp.session_manager.ClaudeMPMSubprocess",
            return_value=mock_subprocess,
        ):
            await manager.start_session(prompt="Test")

        # After completion, status should be COMPLETED
        assert manager._sessions["status-test"].status == SessionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_passes_options_to_subprocess(self):
        """start_session should pass all options to subprocess."""
        manager = SessionManager()

        mock_result = SessionResult(success=True, session_id="opts-test")

        mock_subprocess = MagicMock()
        mock_subprocess.working_directory = "/custom"
        mock_subprocess.start_session = AsyncMock(
            return_value=("opts-test", MagicMock())
        )
        mock_subprocess.wait_for_completion = AsyncMock(return_value=mock_result)

        with patch(
            "claude_mpm.mcp.session_manager.ClaudeMPMSubprocess",
            return_value=mock_subprocess,
        ) as MockClass:
            await manager.start_session(
                prompt="Test",
                working_directory="/custom",
                no_hooks=True,
                no_tickets=True,
                timeout=30.0,
                env_overrides={"MY_VAR": "value"},
            )

            MockClass.assert_called_once_with(
                working_directory="/custom",
                env_overrides={"MY_VAR": "value"},
            )

            mock_subprocess.start_session.assert_called_once_with(
                prompt="Test",
                no_hooks=True,
                no_tickets=True,
            )

    @pytest.mark.asyncio
    async def test_error_status_on_failure(self):
        """start_session should set ERROR status on failure."""
        manager = SessionManager()

        mock_result = SessionResult(
            success=False,
            session_id="fail-test",
            error="Something went wrong",
        )

        mock_subprocess = MagicMock()
        mock_subprocess.working_directory = "/test"
        mock_subprocess.start_session = AsyncMock(
            return_value=("fail-test", MagicMock())
        )
        mock_subprocess.wait_for_completion = AsyncMock(return_value=mock_result)

        with patch(
            "claude_mpm.mcp.session_manager.ClaudeMPMSubprocess",
            return_value=mock_subprocess,
        ):
            result = await manager.start_session(prompt="Test")

        assert result.success is False
        assert manager._sessions["fail-test"].status == SessionStatus.ERROR

    @pytest.mark.asyncio
    async def test_handles_session_error(self):
        """start_session should propagate SessionError."""
        manager = SessionManager()

        mock_subprocess = MagicMock()
        mock_subprocess.working_directory = "/test"
        mock_subprocess.start_session = AsyncMock(
            return_value=("err-test", MagicMock())
        )
        mock_subprocess.wait_for_completion = AsyncMock(
            side_effect=SessionError("Timeout", session_id="err-test")
        )

        with patch(
            "claude_mpm.mcp.session_manager.ClaudeMPMSubprocess",
            return_value=mock_subprocess,
        ):
            with pytest.raises(SessionError):
                await manager.start_session(prompt="Test")

        # Session should be in ERROR state
        assert manager._sessions["err-test"].status == SessionStatus.ERROR

    @pytest.mark.asyncio
    async def test_handles_unexpected_exception(self):
        """start_session should wrap unexpected exceptions in SessionError."""
        manager = SessionManager()

        mock_subprocess = MagicMock()
        mock_subprocess.working_directory = "/test"
        mock_subprocess.start_session = AsyncMock(
            return_value=("exc-test", MagicMock())
        )
        mock_subprocess.wait_for_completion = AsyncMock(
            side_effect=RuntimeError("Unexpected")
        )

        with patch(
            "claude_mpm.mcp.session_manager.ClaudeMPMSubprocess",
            return_value=mock_subprocess,
        ):
            with pytest.raises(SessionError) as exc_info:
                await manager.start_session(prompt="Test")

        assert "Failed to start session" in str(exc_info.value)
        assert exc_info.value.session_id == "exc-test"


class TestContinueSession:
    """Tests for continue_session() method."""

    @pytest.mark.asyncio
    async def test_continues_existing_session(self):
        """continue_session should continue a tracked session."""
        manager = SessionManager()

        # Pre-populate session
        mock_subprocess = MagicMock()
        mock_subprocess.continue_session = AsyncMock(return_value=MagicMock())
        mock_subprocess.wait_for_completion = AsyncMock(
            return_value=SessionResult(
                success=True, session_id="existing-123", output="Continued"
            )
        )
        mock_subprocess.working_directory = "/test"

        manager._sessions["existing-123"] = SessionInfo(
            session_id="existing-123",
            status=SessionStatus.COMPLETED,
            start_time="2025-01-01T00:00:00Z",
            working_directory="/test",
        )
        manager._processes["existing-123"] = mock_subprocess

        result = await manager.continue_session(
            session_id="existing-123",
            prompt="Continue",
        )

        assert result.success is True
        assert result.output == "Continued"

    @pytest.mark.asyncio
    async def test_creates_new_subprocess_for_unknown_session(self):
        """continue_session should create subprocess for unknown session."""
        manager = SessionManager()

        mock_result = SessionResult(success=True, session_id="unknown-456")

        mock_subprocess = MagicMock()
        mock_subprocess.continue_session = AsyncMock(return_value=MagicMock())
        mock_subprocess.wait_for_completion = AsyncMock(return_value=mock_result)
        mock_subprocess.working_directory = "/default"

        with patch(
            "claude_mpm.mcp.session_manager.ClaudeMPMSubprocess",
            return_value=mock_subprocess,
        ):
            result = await manager.continue_session(
                session_id="unknown-456",
                prompt="Resume",
            )

        assert result.success is True
        assert "unknown-456" in manager._sessions

    @pytest.mark.asyncio
    async def test_fork_parameter(self):
        """continue_session should pass fork parameter to subprocess."""
        manager = SessionManager()

        mock_subprocess = MagicMock()
        mock_subprocess.continue_session = AsyncMock(return_value=MagicMock())
        mock_subprocess.wait_for_completion = AsyncMock(
            return_value=SessionResult(success=True, session_id="fork-test")
        )
        mock_subprocess.working_directory = "/test"

        with patch(
            "claude_mpm.mcp.session_manager.ClaudeMPMSubprocess",
            return_value=mock_subprocess,
        ):
            await manager.continue_session(
                session_id="fork-test",
                prompt="Fork",
                fork=True,
            )

        mock_subprocess.continue_session.assert_called_with(
            session_id="fork-test",
            prompt="Fork",
            fork=True,
        )


class TestGetSessionStatus:
    """Tests for get_session_status() method."""

    @pytest.mark.asyncio
    async def test_returns_session_info(self):
        """get_session_status should return SessionInfo for known session."""
        manager = SessionManager()

        manager._sessions["status-123"] = SessionInfo(
            session_id="status-123",
            status=SessionStatus.ACTIVE,
            start_time="2025-01-01T00:00:00Z",
            working_directory="/test",
            message_count=5,
        )

        result = await manager.get_session_status("status-123")

        assert result is not None
        assert result.session_id == "status-123"
        assert result.status == SessionStatus.ACTIVE
        assert result.message_count == 5

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_session(self):
        """get_session_status should return None for unknown session."""
        manager = SessionManager()

        result = await manager.get_session_status("nonexistent")

        assert result is None


class TestListSessions:
    """Tests for list_sessions() method."""

    @pytest.mark.asyncio
    async def test_returns_all_sessions(self):
        """list_sessions should return all sessions when no filter."""
        manager = SessionManager()

        manager._sessions = {
            "s1": SessionInfo(
                session_id="s1",
                status=SessionStatus.ACTIVE,
                start_time="2025-01-01T00:00:00Z",
                working_directory="/test",
            ),
            "s2": SessionInfo(
                session_id="s2",
                status=SessionStatus.COMPLETED,
                start_time="2025-01-01T00:00:00Z",
                working_directory="/test",
            ),
            "s3": SessionInfo(
                session_id="s3",
                status=SessionStatus.ERROR,
                start_time="2025-01-01T00:00:00Z",
                working_directory="/test",
            ),
        }

        result = await manager.list_sessions()

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_filters_by_status(self):
        """list_sessions should filter by status when provided."""
        manager = SessionManager()

        manager._sessions = {
            "s1": SessionInfo(
                session_id="s1",
                status=SessionStatus.ACTIVE,
                start_time="2025-01-01T00:00:00Z",
                working_directory="/test",
            ),
            "s2": SessionInfo(
                session_id="s2",
                status=SessionStatus.ACTIVE,
                start_time="2025-01-01T00:00:00Z",
                working_directory="/test",
            ),
            "s3": SessionInfo(
                session_id="s3",
                status=SessionStatus.COMPLETED,
                start_time="2025-01-01T00:00:00Z",
                working_directory="/test",
            ),
        }

        result = await manager.list_sessions(status=SessionStatus.ACTIVE)

        assert len(result) == 2
        assert all(s.status == SessionStatus.ACTIVE for s in result)

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_sessions(self):
        """list_sessions should return empty list when no sessions."""
        manager = SessionManager()

        result = await manager.list_sessions()

        assert result == []


class TestStopSession:
    """Tests for stop_session() method."""

    @pytest.mark.asyncio
    async def test_stops_existing_session(self):
        """stop_session should stop a tracked session."""
        manager = SessionManager()

        mock_subprocess = MagicMock()
        mock_subprocess.terminate = AsyncMock()

        manager._sessions["stop-123"] = SessionInfo(
            session_id="stop-123",
            status=SessionStatus.ACTIVE,
            start_time="2025-01-01T00:00:00Z",
            working_directory="/test",
        )
        manager._processes["stop-123"] = mock_subprocess

        result = await manager.stop_session("stop-123")

        assert result is True
        mock_subprocess.terminate.assert_called_once_with(force=False)
        assert manager._sessions["stop-123"].status == SessionStatus.STOPPED

    @pytest.mark.asyncio
    async def test_force_stop(self):
        """stop_session should force kill when force=True."""
        manager = SessionManager()

        mock_subprocess = MagicMock()
        mock_subprocess.terminate = AsyncMock()

        manager._sessions["force-123"] = SessionInfo(
            session_id="force-123",
            status=SessionStatus.ACTIVE,
            start_time="2025-01-01T00:00:00Z",
            working_directory="/test",
        )
        manager._processes["force-123"] = mock_subprocess

        result = await manager.stop_session("force-123", force=True)

        assert result is True
        mock_subprocess.terminate.assert_called_once_with(force=True)

    @pytest.mark.asyncio
    async def test_returns_false_for_unknown_session(self):
        """stop_session should return False for unknown session."""
        manager = SessionManager()

        result = await manager.stop_session("nonexistent")

        assert result is False


class TestGetActiveCount:
    """Tests for get_active_count() method."""

    @pytest.mark.asyncio
    async def test_counts_active_sessions(self):
        """get_active_count should count ACTIVE and STARTING sessions."""
        manager = SessionManager()

        manager._sessions = {
            "s1": SessionInfo(
                session_id="s1",
                status=SessionStatus.STARTING,
                start_time="2025-01-01T00:00:00Z",
                working_directory="/test",
            ),
            "s2": SessionInfo(
                session_id="s2",
                status=SessionStatus.ACTIVE,
                start_time="2025-01-01T00:00:00Z",
                working_directory="/test",
            ),
            "s3": SessionInfo(
                session_id="s3",
                status=SessionStatus.COMPLETED,
                start_time="2025-01-01T00:00:00Z",
                working_directory="/test",
            ),
            "s4": SessionInfo(
                session_id="s4",
                status=SessionStatus.ACTIVE,
                start_time="2025-01-01T00:00:00Z",
                working_directory="/test",
            ),
        }

        result = await manager.get_active_count()

        assert result == 3  # 1 STARTING + 2 ACTIVE

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_active(self):
        """get_active_count should return 0 when no active sessions."""
        manager = SessionManager()

        manager._sessions = {
            "s1": SessionInfo(
                session_id="s1",
                status=SessionStatus.COMPLETED,
                start_time="2025-01-01T00:00:00Z",
                working_directory="/test",
            ),
        }

        result = await manager.get_active_count()

        assert result == 0


class TestShutdown:
    """Tests for shutdown() method."""

    @pytest.mark.asyncio
    async def test_stops_all_sessions(self):
        """shutdown should stop all active sessions."""
        manager = SessionManager()

        mock_subprocess1 = MagicMock()
        mock_subprocess1.terminate = AsyncMock()

        mock_subprocess2 = MagicMock()
        mock_subprocess2.terminate = AsyncMock()

        manager._sessions = {
            "s1": SessionInfo(
                session_id="s1",
                status=SessionStatus.ACTIVE,
                start_time="2025-01-01T00:00:00Z",
                working_directory="/test",
            ),
            "s2": SessionInfo(
                session_id="s2",
                status=SessionStatus.ACTIVE,
                start_time="2025-01-01T00:00:00Z",
                working_directory="/test",
            ),
        }
        manager._processes = {
            "s1": mock_subprocess1,
            "s2": mock_subprocess2,
        }

        await manager.shutdown()

        mock_subprocess1.terminate.assert_called_once_with(force=True)
        mock_subprocess2.terminate.assert_called_once_with(force=True)

    @pytest.mark.asyncio
    async def test_clears_internal_state(self):
        """shutdown should clear internal dictionaries."""
        manager = SessionManager()

        mock_subprocess = MagicMock()
        mock_subprocess.terminate = AsyncMock()

        manager._sessions = {
            "s1": SessionInfo(
                session_id="s1",
                status=SessionStatus.COMPLETED,
                start_time="2025-01-01T00:00:00Z",
                working_directory="/test",
            ),
        }
        manager._processes = {"s1": mock_subprocess}

        await manager.shutdown()

        assert manager._sessions == {}
        assert manager._processes == {}


class TestConcurrencyLimit:
    """Tests for concurrency control via semaphore."""

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrent_sessions(self):
        """Should enforce max_concurrent via semaphore."""
        manager = SessionManager(max_concurrent=2)

        # Track concurrent execution
        concurrent_count = 0
        max_concurrent_seen = 0

        async def mock_wait(*args, **kwargs):
            nonlocal concurrent_count, max_concurrent_seen
            concurrent_count += 1
            max_concurrent_seen = max(max_concurrent_seen, concurrent_count)
            await asyncio.sleep(0.05)
            concurrent_count -= 1
            return SessionResult(success=True, session_id=f"sess-{id(args)}")

        def create_mock_subprocess(*args, **kwargs):
            mock = MagicMock()
            mock.working_directory = "/test"
            mock.start_session = AsyncMock(
                return_value=(f"sess-{id(mock)}", MagicMock())
            )
            mock.wait_for_completion = mock_wait
            return mock

        with patch(
            "claude_mpm.mcp.session_manager.ClaudeMPMSubprocess",
            side_effect=create_mock_subprocess,
        ):
            # Start 5 sessions concurrently
            tasks = [
                asyncio.create_task(manager.start_session(prompt=f"Test {i}"))
                for i in range(5)
            ]
            await asyncio.gather(*tasks)

        # Should never have exceeded max_concurrent=2
        assert max_concurrent_seen <= 2


class TestCleanupSession:
    """Tests for cleanup_session() method."""

    @pytest.mark.asyncio
    async def test_removes_session(self):
        """cleanup_session should remove session from tracking."""
        manager = SessionManager()

        mock_subprocess = MagicMock()
        mock_subprocess.process = None
        mock_subprocess.terminate = AsyncMock()

        manager._sessions["cleanup-123"] = SessionInfo(
            session_id="cleanup-123",
            status=SessionStatus.COMPLETED,
            start_time="2025-01-01T00:00:00Z",
            working_directory="/test",
        )
        manager._processes["cleanup-123"] = mock_subprocess

        result = await manager.cleanup_session("cleanup-123")

        assert result is True
        assert "cleanup-123" not in manager._sessions
        assert "cleanup-123" not in manager._processes

    @pytest.mark.asyncio
    async def test_terminates_running_process(self):
        """cleanup_session should terminate process if still running."""
        manager = SessionManager()

        mock_subprocess = MagicMock()
        mock_subprocess.process = MagicMock()  # Has running process
        mock_subprocess.terminate = AsyncMock()

        manager._sessions["running-123"] = SessionInfo(
            session_id="running-123",
            status=SessionStatus.ACTIVE,
            start_time="2025-01-01T00:00:00Z",
            working_directory="/test",
        )
        manager._processes["running-123"] = mock_subprocess

        await manager.cleanup_session("running-123")

        mock_subprocess.terminate.assert_called_once_with(force=True)

    @pytest.mark.asyncio
    async def test_returns_false_for_unknown_session(self):
        """cleanup_session should return False for unknown session."""
        manager = SessionManager()

        result = await manager.cleanup_session("nonexistent")

        assert result is False
