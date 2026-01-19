"""Tests for Commander daemon."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.commander.config import DaemonConfig
from claude_mpm.commander.daemon import CommanderDaemon
from claude_mpm.commander.models import Project, ProjectState


@pytest.fixture
def daemon_config(tmp_path: Path) -> DaemonConfig:
    """Create test daemon configuration.

    Args:
        tmp_path: Pytest temporary directory

    Returns:
        DaemonConfig with test settings
    """
    return DaemonConfig(
        host="127.0.0.1",
        port=18765,  # Test port
        log_level="DEBUG",
        state_dir=tmp_path / "commander",
        max_projects=5,
        poll_interval=0.1,  # Fast polling for tests
    )


@pytest.fixture
def mock_tmux() -> MagicMock:
    """Create mock TmuxOrchestrator.

    Returns:
        Mocked TmuxOrchestrator
    """
    mock = MagicMock()
    mock.session_exists.return_value = False
    mock.create_session.return_value = None
    return mock


class TestDaemonConfig:
    """Tests for DaemonConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = DaemonConfig()

        assert config.host == "127.0.0.1"
        assert config.port == 8766
        assert config.log_level == "INFO"
        assert config.max_projects == 10
        assert config.healthcheck_interval == 30
        assert config.save_interval == 30
        assert config.poll_interval == 2.0

    def test_custom_config(self, tmp_path: Path):
        """Test custom configuration values."""
        state_dir = tmp_path / "custom"
        config = DaemonConfig(
            host="0.0.0.0",
            port=9000,
            log_level="DEBUG",
            state_dir=state_dir,
            max_projects=20,
        )

        assert config.host == "0.0.0.0"
        assert config.port == 9000
        assert config.log_level == "DEBUG"
        assert config.state_dir == state_dir
        assert config.max_projects == 20

    def test_state_dir_creation(self, tmp_path: Path):
        """Test state directory is created on init."""
        state_dir = tmp_path / "commander" / "state"
        config = DaemonConfig(state_dir=state_dir)

        assert config.state_dir.exists()
        assert config.state_dir.is_dir()

    def test_state_dir_expansion(self):
        """Test home directory expansion."""
        config = DaemonConfig(state_dir=Path("~/.claude-mpm/test"))

        assert "~" not in str(config.state_dir)
        assert config.state_dir.is_absolute()


class TestCommanderDaemon:
    """Tests for CommanderDaemon."""

    def test_init(self, daemon_config: DaemonConfig):
        """Test daemon initialization."""
        with patch("claude_mpm.commander.daemon.TmuxOrchestrator"):
            daemon = CommanderDaemon(daemon_config)

            assert daemon.config == daemon_config
            assert not daemon.is_running
            assert len(daemon.sessions) == 0

    def test_init_invalid_config(self):
        """Test initialization with invalid config."""
        with pytest.raises(ValueError, match="Config cannot be None"):
            CommanderDaemon(None)

    @pytest.mark.asyncio
    async def test_start_creates_tmux_session(
        self, daemon_config: DaemonConfig, mock_tmux: MagicMock
    ):
        """Test daemon start creates tmux session."""
        with patch(
            "claude_mpm.commander.daemon.TmuxOrchestrator", return_value=mock_tmux
        ), patch("claude_mpm.commander.daemon.uvicorn.Server") as mock_server:
            # Mock server.serve() to return immediately
            mock_server_instance = MagicMock()
            mock_server_instance.serve = AsyncMock()
            mock_server.return_value = mock_server_instance

            daemon = CommanderDaemon(daemon_config)
            await daemon.start()

            # Give time for background tasks to start
            await asyncio.sleep(0.1)

            assert daemon.is_running
            mock_tmux.session_exists.assert_called_once()
            mock_tmux.create_session.assert_called_once()

            await daemon.stop()

    @pytest.mark.asyncio
    async def test_start_already_running(self, daemon_config: DaemonConfig):
        """Test starting already running daemon raises error."""
        with patch("claude_mpm.commander.daemon.TmuxOrchestrator"), patch(
            "claude_mpm.commander.daemon.uvicorn.Server"
        ) as mock_server:
            mock_server_instance = MagicMock()
            mock_server_instance.serve = AsyncMock()
            mock_server.return_value = mock_server_instance

            daemon = CommanderDaemon(daemon_config)
            await daemon.start()

            with pytest.raises(RuntimeError, match="already running"):
                await daemon.start()

            await daemon.stop()

    @pytest.mark.asyncio
    async def test_stop_graceful_shutdown(self, daemon_config: DaemonConfig):
        """Test graceful shutdown stops all sessions."""
        with patch("claude_mpm.commander.daemon.TmuxOrchestrator"), patch(
            "claude_mpm.commander.daemon.uvicorn.Server"
        ) as mock_server:
            mock_server_instance = MagicMock()
            mock_server_instance.serve = AsyncMock()
            mock_server.return_value = mock_server_instance

            daemon = CommanderDaemon(daemon_config)
            await daemon.start()

            # Create mock session
            mock_session = AsyncMock()
            daemon.sessions["test-project"] = mock_session

            await daemon.stop()

            assert not daemon.is_running
            mock_session.stop.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stop_not_running(self, daemon_config: DaemonConfig):
        """Test stopping non-running daemon is safe."""
        with patch("claude_mpm.commander.daemon.TmuxOrchestrator"):
            daemon = CommanderDaemon(daemon_config)

            # Should not raise error
            await daemon.stop()
            assert not daemon.is_running

    @pytest.mark.asyncio
    async def test_main_loop_runs(self, daemon_config: DaemonConfig):
        """Test main loop executes while daemon running."""
        with patch("claude_mpm.commander.daemon.TmuxOrchestrator"), patch(
            "claude_mpm.commander.daemon.uvicorn.Server"
        ) as mock_server:
            mock_server_instance = MagicMock()
            mock_server_instance.serve = AsyncMock()
            mock_server.return_value = mock_server_instance

            daemon = CommanderDaemon(daemon_config)
            await daemon.start()

            # Let main loop run a few iterations
            await asyncio.sleep(0.3)

            assert daemon.is_running

            await daemon.stop()
            assert not daemon.is_running

    @pytest.mark.asyncio
    async def test_main_loop_handles_errors(self, daemon_config: DaemonConfig):
        """Test main loop continues despite errors."""
        with patch("claude_mpm.commander.daemon.TmuxOrchestrator"), patch(
            "claude_mpm.commander.daemon.uvicorn.Server"
        ) as mock_server:
            mock_server_instance = MagicMock()
            mock_server_instance.serve = AsyncMock()
            mock_server.return_value = mock_server_instance

            daemon = CommanderDaemon(daemon_config)

            # Inject error into main loop
            original_run = daemon.run
            error_count = 0

            async def run_with_error():
                nonlocal error_count
                while daemon._running and error_count < 2:
                    error_count += 1
                    raise ValueError("Test error in main loop")

            daemon.run = run_with_error

            await daemon.start()
            await asyncio.sleep(0.3)

            # Daemon should still be running despite errors
            assert daemon.is_running

            await daemon.stop()

    def test_get_or_create_session_existing(self, daemon_config: DaemonConfig):
        """Test getting existing session."""
        with patch("claude_mpm.commander.daemon.TmuxOrchestrator"):
            daemon = CommanderDaemon(daemon_config)

            # Create mock session
            mock_session = MagicMock()
            daemon.sessions["test-project"] = mock_session

            session = daemon.get_or_create_session("test-project")

            assert session == mock_session

    def test_get_or_create_session_new(
        self, daemon_config: DaemonConfig, tmp_path: Path
    ):
        """Test creating new session for project."""
        with patch("claude_mpm.commander.daemon.TmuxOrchestrator"):
            daemon = CommanderDaemon(daemon_config)

            # Register project
            project = daemon.registry.register(str(tmp_path), "test-project")

            session = daemon.get_or_create_session(project.id)

            assert session is not None
            assert project.id in daemon.sessions

    def test_get_or_create_session_not_found(self, daemon_config: DaemonConfig):
        """Test error when project not found."""
        with patch("claude_mpm.commander.daemon.TmuxOrchestrator"):
            daemon = CommanderDaemon(daemon_config)

            with pytest.raises(ValueError, match="Project not found"):
                daemon.get_or_create_session("nonexistent-project")
