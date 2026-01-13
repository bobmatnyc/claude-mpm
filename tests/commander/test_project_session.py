"""Tests for ProjectSession lifecycle coordinator."""

from unittest.mock import MagicMock

import pytest

from claude_mpm.commander.models import Project, ProjectState
from claude_mpm.commander.project_session import ProjectSession, SessionState


@pytest.fixture
def mock_tmux() -> MagicMock:
    """Create mock TmuxOrchestrator.

    Returns:
        Mocked TmuxOrchestrator
    """
    mock = MagicMock()
    mock.session_exists.return_value = False
    mock.create_session.return_value = None
    mock.kill_pane.return_value = None
    return mock


@pytest.fixture
def test_project() -> Project:
    """Create test project.

    Returns:
        Test Project instance
    """
    return Project(
        id="test-project-123",
        path="/tmp/test-project",
        name="Test Project",
    )


class TestSessionState:
    """Tests for SessionState enum."""

    def test_all_states_defined(self):
        """Test all expected states are defined."""
        assert SessionState.IDLE
        assert SessionState.STARTING
        assert SessionState.RUNNING
        assert SessionState.PAUSED
        assert SessionState.STOPPING
        assert SessionState.STOPPED


class TestProjectSession:
    """Tests for ProjectSession."""

    def test_init(self, test_project: Project, mock_tmux: MagicMock):
        """Test session initialization."""
        session = ProjectSession(test_project, mock_tmux)

        assert session.project == test_project
        assert session.orchestrator == mock_tmux
        assert session.state == SessionState.IDLE
        assert session.pause_reason is None

    def test_init_none_project(self, mock_tmux: MagicMock):
        """Test initialization with None project raises error."""
        with pytest.raises(ValueError, match="Project cannot be None"):
            ProjectSession(None, mock_tmux)

    def test_init_none_orchestrator(self, test_project: Project):
        """Test initialization with None orchestrator raises error."""
        with pytest.raises(ValueError, match="Orchestrator cannot be None"):
            ProjectSession(test_project, None)

    @pytest.mark.asyncio
    async def test_start_from_idle(self, test_project: Project, mock_tmux: MagicMock):
        """Test starting session from IDLE state."""
        session = ProjectSession(test_project, mock_tmux)

        await session.start()

        assert session.state == SessionState.RUNNING
        assert test_project.state == ProjectState.IDLE
        assert test_project.state_reason is None

    @pytest.mark.asyncio
    async def test_start_creates_tmux_session(
        self, test_project: Project, mock_tmux: MagicMock
    ):
        """Test start creates tmux session if not exists."""
        session = ProjectSession(test_project, mock_tmux)

        await session.start()

        mock_tmux.session_exists.assert_called_once()
        mock_tmux.create_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_from_non_idle_raises_error(
        self, test_project: Project, mock_tmux: MagicMock
    ):
        """Test starting from non-IDLE state raises error."""
        session = ProjectSession(test_project, mock_tmux)
        session._state = SessionState.RUNNING

        with pytest.raises(RuntimeError, match="Cannot start session"):
            await session.start()

    @pytest.mark.asyncio
    async def test_pause_from_running(
        self, test_project: Project, mock_tmux: MagicMock
    ):
        """Test pausing from RUNNING state."""
        session = ProjectSession(test_project, mock_tmux)
        await session.start()

        await session.pause("Waiting for user input")

        assert session.state == SessionState.PAUSED
        assert session.pause_reason == "Waiting for user input"
        assert test_project.state == ProjectState.BLOCKED

    @pytest.mark.asyncio
    async def test_pause_from_non_running_raises_error(
        self, test_project: Project, mock_tmux: MagicMock
    ):
        """Test pausing from non-RUNNING state raises error."""
        session = ProjectSession(test_project, mock_tmux)

        with pytest.raises(RuntimeError, match="Cannot pause session"):
            await session.pause("Test reason")

    @pytest.mark.asyncio
    async def test_resume_from_paused(
        self, test_project: Project, mock_tmux: MagicMock
    ):
        """Test resuming from PAUSED state."""
        session = ProjectSession(test_project, mock_tmux)
        await session.start()
        await session.pause("Test pause")

        await session.resume()

        assert session.state == SessionState.RUNNING
        assert session.pause_reason is None
        assert test_project.state == ProjectState.WORKING

    @pytest.mark.asyncio
    async def test_resume_from_non_paused_raises_error(
        self, test_project: Project, mock_tmux: MagicMock
    ):
        """Test resuming from non-PAUSED state raises error."""
        session = ProjectSession(test_project, mock_tmux)

        with pytest.raises(RuntimeError, match="Cannot resume session"):
            await session.resume()

    @pytest.mark.asyncio
    async def test_stop_from_running(self, test_project: Project, mock_tmux: MagicMock):
        """Test stopping from RUNNING state."""
        session = ProjectSession(test_project, mock_tmux)
        await session.start()

        await session.stop()

        assert session.state == SessionState.STOPPED
        assert test_project.state == ProjectState.IDLE

    @pytest.mark.asyncio
    async def test_stop_cleans_up_sessions(
        self, test_project: Project, mock_tmux: MagicMock
    ):
        """Test stop cleans up active tool sessions."""
        from claude_mpm.commander.models import ToolSession

        session = ProjectSession(test_project, mock_tmux)
        await session.start()

        # Add mock tool session
        tool_session = ToolSession(
            id="tool-123",
            project_id=test_project.id,
            runtime="claude-code",
            tmux_target="commander:test-project-cc",
        )
        test_project.sessions["tool-123"] = tool_session

        await session.stop()

        mock_tmux.kill_pane.assert_called_once_with("commander:test-project-cc")

    @pytest.mark.asyncio
    async def test_stop_handles_cleanup_errors(
        self, test_project: Project, mock_tmux: MagicMock
    ):
        """Test stop handles cleanup errors gracefully."""
        from claude_mpm.commander.models import ToolSession

        session = ProjectSession(test_project, mock_tmux)
        await session.start()

        # Add tool session
        tool_session = ToolSession(
            id="tool-123",
            project_id=test_project.id,
            runtime="claude-code",
            tmux_target="commander:test-project-cc",
        )
        test_project.sessions["tool-123"] = tool_session

        # Make kill_pane raise error
        mock_tmux.kill_pane.side_effect = Exception("Kill failed")

        # Should not raise, but still transition to STOPPED
        await session.stop()

        assert session.state == SessionState.STOPPED

    def test_is_ready_when_running(self, test_project: Project, mock_tmux: MagicMock):
        """Test is_ready returns True when RUNNING."""
        session = ProjectSession(test_project, mock_tmux)
        session._state = SessionState.RUNNING

        assert session.is_ready()

    def test_is_ready_when_not_running(
        self, test_project: Project, mock_tmux: MagicMock
    ):
        """Test is_ready returns False when not RUNNING."""
        session = ProjectSession(test_project, mock_tmux)

        assert not session.is_ready()

        session._state = SessionState.PAUSED
        assert not session.is_ready()

        session._state = SessionState.STOPPED
        assert not session.is_ready()

    def test_can_accept_work_when_idle(
        self, test_project: Project, mock_tmux: MagicMock
    ):
        """Test can_accept_work when IDLE with no active work."""
        session = ProjectSession(test_project, mock_tmux)

        assert session.can_accept_work()

    def test_can_accept_work_when_running_no_work(
        self, test_project: Project, mock_tmux: MagicMock
    ):
        """Test can_accept_work when RUNNING with no active work."""
        session = ProjectSession(test_project, mock_tmux)
        session._state = SessionState.RUNNING
        test_project.active_work = None

        assert session.can_accept_work()

    def test_cannot_accept_work_when_has_active_work(
        self, test_project: Project, mock_tmux: MagicMock
    ):
        """Test can_accept_work returns False when work active."""
        session = ProjectSession(test_project, mock_tmux)
        session._state = SessionState.RUNNING
        test_project.active_work = {"id": "work-123"}

        assert not session.can_accept_work()

    def test_cannot_accept_work_when_paused(
        self, test_project: Project, mock_tmux: MagicMock
    ):
        """Test can_accept_work returns False when PAUSED."""
        session = ProjectSession(test_project, mock_tmux)
        session._state = SessionState.PAUSED

        assert not session.can_accept_work()

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, test_project: Project, mock_tmux: MagicMock):
        """Test full session lifecycle: start -> pause -> resume -> stop."""
        session = ProjectSession(test_project, mock_tmux)

        # Start
        assert session.state == SessionState.IDLE
        await session.start()
        assert session.state == SessionState.RUNNING
        assert session.is_ready()

        # Pause
        await session.pause("Blocking event")
        assert session.state == SessionState.PAUSED
        assert not session.is_ready()
        assert session.pause_reason == "Blocking event"

        # Resume
        await session.resume()
        assert session.state == SessionState.RUNNING
        assert session.is_ready()
        assert session.pause_reason is None

        # Stop
        await session.stop()
        assert session.state == SessionState.STOPPED
        assert not session.is_ready()
