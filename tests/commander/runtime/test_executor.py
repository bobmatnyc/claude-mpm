"""Tests for RuntimeExecutor."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.commander.models.project import Project
from claude_mpm.commander.runtime.executor import RuntimeExecutor
from claude_mpm.commander.tmux_orchestrator import TmuxOrchestrator


@pytest.fixture
def mock_orchestrator():
    """Create mock TmuxOrchestrator."""
    orchestrator = MagicMock(spec=TmuxOrchestrator)
    orchestrator.session_exists.return_value = True
    orchestrator.create_pane.return_value = "%5"
    orchestrator.send_keys.return_value = True
    orchestrator.kill_pane.return_value = True
    orchestrator.list_panes.return_value = [
        {"id": "%5", "path": "/test/path", "pid": "1234", "active": True}
    ]
    return orchestrator


@pytest.fixture
def sample_project():
    """Create sample project."""
    return Project(id="proj_123", name="Test Project", path="/test/project")


@pytest.fixture
def executor(mock_orchestrator):
    """Create RuntimeExecutor with mock orchestrator."""
    return RuntimeExecutor(mock_orchestrator)


class TestRuntimeExecutorInit:
    """Test RuntimeExecutor initialization."""

    def test_init_with_orchestrator(self, mock_orchestrator):
        """Test initialization with valid orchestrator."""
        executor = RuntimeExecutor(mock_orchestrator)
        assert executor.orchestrator == mock_orchestrator

    def test_init_without_orchestrator(self):
        """Test initialization fails without orchestrator."""
        with pytest.raises(ValueError, match="Orchestrator cannot be None"):
            RuntimeExecutor(None)


class TestRuntimeExecutorSpawn:
    """Test spawning Claude Code processes."""

    @pytest.mark.asyncio
    async def test_spawn_creates_pane_and_sends_command(
        self, executor, mock_orchestrator, sample_project
    ):
        """Test spawn creates pane and sends command."""
        pane_target = await executor.spawn(sample_project, "claude")

        # Should create session if needed
        mock_orchestrator.session_exists.assert_called_once()

        # Should create pane with project path
        mock_orchestrator.create_pane.assert_called_once_with(
            sample_project.id, sample_project.path
        )

        # Should send command
        mock_orchestrator.send_keys.assert_called_once_with("%5", "claude", enter=True)

        # Should return pane target
        assert pane_target == "%5"

    @pytest.mark.asyncio
    async def test_spawn_creates_session_if_not_exists(
        self, executor, mock_orchestrator, sample_project
    ):
        """Test spawn creates tmux session if it doesn't exist."""
        mock_orchestrator.session_exists.return_value = False

        await executor.spawn(sample_project)

        mock_orchestrator.create_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_spawn_with_custom_command(
        self, executor, mock_orchestrator, sample_project
    ):
        """Test spawn with custom command."""
        await executor.spawn(sample_project, "custom-command")

        mock_orchestrator.send_keys.assert_called_once_with(
            "%5", "custom-command", enter=True
        )

    @pytest.mark.asyncio
    async def test_spawn_without_project(self, executor):
        """Test spawn fails without project."""
        with pytest.raises(ValueError, match="Project cannot be None"):
            await executor.spawn(None)

    @pytest.mark.asyncio
    async def test_spawn_without_project_path(self, executor):
        """Test spawn fails without project path."""
        project = Project(id="proj_123", name="Test", path=None)
        with pytest.raises(ValueError, match="Project path cannot be None"):
            await executor.spawn(project)

    @pytest.mark.asyncio
    async def test_spawn_handles_pane_creation_failure(
        self, executor, mock_orchestrator, sample_project
    ):
        """Test spawn handles pane creation failure."""
        mock_orchestrator.create_pane.side_effect = RuntimeError("Pane creation failed")

        with pytest.raises(RuntimeError, match="Failed to spawn claude"):
            await executor.spawn(sample_project)


class TestRuntimeExecutorSendMessage:
    """Test sending messages to running instances."""

    @pytest.mark.asyncio
    async def test_send_message_success(self, executor, mock_orchestrator):
        """Test sending message successfully."""
        await executor.send_message("%5", "Test message")

        mock_orchestrator.send_keys.assert_called_once_with(
            "%5", "Test message", enter=True
        )

    @pytest.mark.asyncio
    async def test_send_message_without_pane_target(self, executor):
        """Test send_message fails without pane target."""
        with pytest.raises(ValueError, match="Pane target cannot be None"):
            await executor.send_message("", "message")

    @pytest.mark.asyncio
    async def test_send_message_without_message(self, executor):
        """Test send_message fails without message."""
        with pytest.raises(ValueError, match="Message cannot be None"):
            await executor.send_message("%5", "")

    @pytest.mark.asyncio
    async def test_send_message_handles_failure(self, executor, mock_orchestrator):
        """Test send_message handles tmux failure."""
        mock_orchestrator.send_keys.side_effect = RuntimeError("Send failed")

        with pytest.raises(RuntimeError, match="Failed to send message"):
            await executor.send_message("%5", "Test message")


class TestRuntimeExecutorTerminate:
    """Test terminating Claude Code instances."""

    @pytest.mark.asyncio
    async def test_terminate_success(self, executor, mock_orchestrator):
        """Test terminating pane successfully."""
        await executor.terminate("%5")

        mock_orchestrator.kill_pane.assert_called_once_with("%5")

    @pytest.mark.asyncio
    async def test_terminate_without_pane_target(self, executor):
        """Test terminate fails without pane target."""
        with pytest.raises(ValueError, match="Pane target cannot be None"):
            await executor.terminate("")

    @pytest.mark.asyncio
    async def test_terminate_handles_failure(self, executor, mock_orchestrator):
        """Test terminate handles tmux failure."""
        mock_orchestrator.kill_pane.side_effect = RuntimeError("Kill failed")

        with pytest.raises(RuntimeError, match="Failed to terminate"):
            await executor.terminate("%5")


class TestRuntimeExecutorIsRunning:
    """Test checking if pane is running."""

    def test_is_running_returns_true_for_active_pane(self, executor, mock_orchestrator):
        """Test is_running returns True for active pane."""
        assert executor.is_running("%5") is True

    def test_is_running_returns_false_for_inactive_pane(
        self, executor, mock_orchestrator
    ):
        """Test is_running returns False for inactive pane."""
        assert executor.is_running("%99") is False

    def test_is_running_returns_false_for_empty_target(self, executor):
        """Test is_running returns False for empty target."""
        assert executor.is_running("") is False

    def test_is_running_handles_list_panes_failure(self, executor, mock_orchestrator):
        """Test is_running handles list_panes failure gracefully."""
        mock_orchestrator.list_panes.side_effect = RuntimeError("List failed")

        assert executor.is_running("%5") is False


class TestRuntimeExecutorIntegration:
    """Integration tests for RuntimeExecutor workflow."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, executor, mock_orchestrator, sample_project):
        """Test full spawn -> send -> terminate lifecycle."""
        # Spawn
        pane_target = await executor.spawn(sample_project)
        assert pane_target == "%5"

        # Send message
        await executor.send_message(pane_target, "Do something")

        # Check running
        assert executor.is_running(pane_target) is True

        # Terminate
        await executor.terminate(pane_target)

        # Verify all operations called
        assert mock_orchestrator.create_pane.call_count == 1
        assert mock_orchestrator.send_keys.call_count == 2  # spawn + send_message
        assert mock_orchestrator.kill_pane.call_count == 1
