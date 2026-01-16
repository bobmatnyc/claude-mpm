"""Integration tests for daemon lifecycle management.

Tests daemon startup, shutdown, signal handling, and state persistence
across the entire system.
"""

import asyncio
import signal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.commander.config import DaemonConfig
from claude_mpm.commander.daemon import CommanderDaemon
from claude_mpm.commander.models import Project, ProjectState
from claude_mpm.commander.models.events import Event, EventPriority, EventType
from claude_mpm.commander.project_session import SessionState


@pytest.mark.integration
@pytest.mark.asyncio
async def test_daemon_start_initializes_all_subsystems(
    integration_config: DaemonConfig,
):
    """Test daemon start initializes registry, orchestrator, event manager, inbox."""
    with patch("claude_mpm.commander.daemon.TmuxOrchestrator") as mock_tmux_cls, patch(
        "claude_mpm.commander.daemon.uvicorn.Server"
    ) as mock_server_cls:
        mock_tmux = MagicMock()
        mock_tmux.session_exists.return_value = False
        mock_tmux_cls.return_value = mock_tmux

        mock_server = MagicMock()
        mock_server.serve = AsyncMock()
        mock_server_cls.return_value = mock_server

        daemon = CommanderDaemon(integration_config)

        assert not daemon.is_running
        assert daemon.registry is not None
        assert daemon.orchestrator is not None
        assert daemon.event_manager is not None
        assert daemon.inbox is not None
        assert daemon.state_store is not None
        assert daemon.event_store is not None

        await daemon.start()

        assert daemon.is_running
        mock_tmux.session_exists.assert_called()
        mock_tmux.create_session.assert_called_once()

        await daemon.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_daemon_stop_saves_state_gracefully(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test daemon stop persists state and cleans up resources."""
    # Register project
    daemon_lifecycle.registry._projects[sample_project.id] = sample_project
    daemon_lifecycle.registry._path_index[sample_project.path] = sample_project.id

    # Create session
    session = daemon_lifecycle.get_or_create_session(sample_project.id)
    assert session is not None

    # Mock session stop
    session.stop = AsyncMock()

    # Stop daemon
    await daemon_lifecycle.stop()

    # Verify state
    assert not daemon_lifecycle.is_running
    session.stop.assert_awaited_once()

    # Verify state files exist
    state_dir = daemon_lifecycle.config.state_dir
    assert state_dir.exists()
    assert (state_dir / "projects.json").exists()
    assert (state_dir / "sessions.json").exists()
    assert (state_dir / "events.json").exists()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_daemon_restart_recovers_projects(integration_config: DaemonConfig):
    """Test daemon restart recovers registered projects from disk."""
    with patch("claude_mpm.commander.daemon.TmuxOrchestrator") as mock_tmux_cls, patch(
        "claude_mpm.commander.daemon.uvicorn.Server"
    ) as mock_server_cls:
        mock_tmux = MagicMock()
        mock_tmux.session_exists.return_value = False
        mock_tmux_cls.return_value = mock_tmux

        mock_server = MagicMock()
        mock_server.serve = AsyncMock()
        mock_server_cls.return_value = mock_server

        # First daemon instance
        daemon1 = CommanderDaemon(integration_config)
        await daemon1.start()

        # Register project
        test_path = integration_config.state_dir / "test_project"
        test_path.mkdir(parents=True, exist_ok=True)
        project = daemon1.registry.register(str(test_path), "Test Project")
        project_id = project.id

        # Save state and stop
        await daemon1._save_state()
        await daemon1.stop()

        # Second daemon instance (restart)
        daemon2 = CommanderDaemon(integration_config)
        await daemon2.start()

        # Verify project recovered
        recovered_project = daemon2.registry.get(project_id)
        assert recovered_project is not None
        assert recovered_project.id == project_id
        assert recovered_project.name == "Test Project"
        assert recovered_project.path == str(test_path)

        await daemon2.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_daemon_restart_recovers_sessions(integration_config: DaemonConfig):
    """Test daemon restart recovers active sessions from disk."""
    with patch("claude_mpm.commander.daemon.TmuxOrchestrator") as mock_tmux_cls, patch(
        "claude_mpm.commander.daemon.uvicorn.Server"
    ) as mock_server_cls:
        mock_tmux = MagicMock()
        mock_tmux.session_exists.return_value = False
        mock_tmux_cls.return_value = mock_tmux

        mock_server = MagicMock()
        mock_server.serve = AsyncMock()
        mock_server_cls.return_value = mock_server

        # First daemon instance
        daemon1 = CommanderDaemon(integration_config)
        await daemon1.start()

        # Register project and create session
        test_path = integration_config.state_dir / "test_project"
        test_path.mkdir(parents=True, exist_ok=True)
        project = daemon1.registry.register(str(test_path), "Test Project")

        session = daemon1.get_or_create_session(project.id)
        session._state = SessionState.RUNNING
        session.active_pane = "test:pane.0"

        # Save state before stopping (stop() clears active_pane)
        await daemon1._save_state()

        # Don't call stop() - it would clear active_pane and save again
        # Just mark as not running to skip cleanup
        daemon1._running = False

        # Second daemon instance (restart)
        daemon2 = CommanderDaemon(integration_config)
        await daemon2.start()

        # Verify session recovered
        assert project.id in daemon2.sessions
        recovered_session = daemon2.sessions[project.id]
        assert recovered_session.active_pane == "test:pane.0"

        await daemon2.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_daemon_restart_recovers_events(integration_config: DaemonConfig):
    """Test daemon restart recovers pending events from disk."""
    with patch("claude_mpm.commander.daemon.TmuxOrchestrator") as mock_tmux_cls, patch(
        "claude_mpm.commander.daemon.uvicorn.Server"
    ) as mock_server_cls:
        mock_tmux = MagicMock()
        mock_tmux.session_exists.return_value = False
        mock_tmux_cls.return_value = mock_tmux

        mock_server = MagicMock()
        mock_server.serve = AsyncMock()
        mock_server_cls.return_value = mock_server

        # First daemon instance
        daemon1 = CommanderDaemon(integration_config)
        await daemon1.start()

        # Add event
        from claude_mpm.commander.models.events import Event, EventType

        test_path = integration_config.state_dir / "test_project"
        test_path.mkdir(parents=True, exist_ok=True)
        project = daemon1.registry.register(str(test_path), "Test Project")

        event = Event(
            id="event-test",
            project_id=project.id,
            type=EventType.APPROVAL,
            priority=EventPriority.HIGH,
            title="Test Event",
            content="This is a test event",
        )
        daemon1.event_manager.add_event(event)

        # Save and stop
        await daemon1._save_state()
        await daemon1.stop()

        # Second daemon instance (restart)
        daemon2 = CommanderDaemon(integration_config)
        await daemon2.start()

        # Verify event recovered
        recovered_events = daemon2.event_manager.get_pending()
        assert len(recovered_events) == 1
        assert recovered_events[0].id == "event-test"
        assert recovered_events[0].title == "Test Event"

        await daemon2.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_daemon_handles_corrupt_state_files(integration_config: DaemonConfig):
    """Test daemon handles corrupt state files gracefully."""
    with patch("claude_mpm.commander.daemon.TmuxOrchestrator") as mock_tmux_cls, patch(
        "claude_mpm.commander.daemon.uvicorn.Server"
    ) as mock_server_cls:
        mock_tmux = MagicMock()
        mock_tmux.session_exists.return_value = False
        mock_tmux_cls.return_value = mock_tmux

        mock_server = MagicMock()
        mock_server.serve = AsyncMock()
        mock_server_cls.return_value = mock_server

        # Create corrupt state file
        state_dir = integration_config.state_dir
        state_dir.mkdir(parents=True, exist_ok=True)

        (state_dir / "projects.json").write_text("{ invalid json }")
        (state_dir / "sessions.json").write_text("{ also: invalid }")
        (state_dir / "events.json").write_text("not json at all")

        # Daemon should start despite corrupt files
        daemon = CommanderDaemon(integration_config)
        await daemon.start()

        assert daemon.is_running
        assert len(daemon.registry._projects) == 0  # No projects recovered
        assert len(daemon.sessions) == 0  # No sessions recovered

        await daemon.stop()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_daemon_periodic_state_persistence(integration_config: DaemonConfig):
    """Test daemon periodically persists state during runtime."""
    # Use very short save interval for testing
    integration_config.save_interval = 0.5  # 500ms

    with patch("claude_mpm.commander.daemon.TmuxOrchestrator") as mock_tmux_cls, patch(
        "claude_mpm.commander.daemon.uvicorn.Server"
    ) as mock_server_cls:
        mock_tmux = MagicMock()
        mock_tmux.session_exists.return_value = False
        mock_tmux_cls.return_value = mock_tmux

        mock_server = MagicMock()
        mock_server.serve = AsyncMock()
        mock_server_cls.return_value = mock_server

        daemon = CommanderDaemon(integration_config)
        await daemon.start()

        # Register project
        test_path = integration_config.state_dir / "test_project"
        test_path.mkdir(parents=True, exist_ok=True)
        project = daemon.registry.register(str(test_path), "Test Project")

        # Wait for at least one periodic save
        await asyncio.sleep(0.7)

        # Verify state was saved
        state_dir = daemon.config.state_dir
        assert (state_dir / "projects.json").exists()

        # Verify we can read the saved state
        import json

        projects_file = json.loads((state_dir / "projects.json").read_text())
        assert len(projects_file["projects"]) == 1
        assert projects_file["projects"][0]["name"] == "Test Project"

        await daemon.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_daemon_multiple_stop_calls_safe(integration_config: DaemonConfig):
    """Test multiple daemon.stop() calls are safe (idempotent)."""
    with patch("claude_mpm.commander.daemon.TmuxOrchestrator") as mock_tmux_cls, patch(
        "claude_mpm.commander.daemon.uvicorn.Server"
    ) as mock_server_cls:
        mock_tmux = MagicMock()
        mock_tmux.session_exists.return_value = False
        mock_tmux_cls.return_value = mock_tmux

        mock_server = MagicMock()
        mock_server.serve = AsyncMock()
        mock_server_cls.return_value = mock_server

        daemon = CommanderDaemon(integration_config)
        await daemon.start()

        # Stop multiple times
        await daemon.stop()
        await daemon.stop()
        await daemon.stop()

        assert not daemon.is_running


@pytest.mark.integration
@pytest.mark.asyncio
async def test_daemon_session_stop_errors_dont_block_shutdown(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test daemon stops gracefully even if session.stop() raises errors."""
    # Register project
    daemon_lifecycle.registry._projects[sample_project.id] = sample_project

    # Create session with failing stop()
    session = daemon_lifecycle.get_or_create_session(sample_project.id)
    session.stop = AsyncMock(side_effect=RuntimeError("Session stop failed"))

    # Daemon should still stop gracefully
    await daemon_lifecycle.stop()

    assert not daemon_lifecycle.is_running
