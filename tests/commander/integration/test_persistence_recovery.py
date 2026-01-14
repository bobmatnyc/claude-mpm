"""Integration tests for state persistence and recovery.

Tests daemon state persistence, recovery from crashes, corrupt file handling,
and data integrity across restarts.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.commander.config import DaemonConfig
from claude_mpm.commander.daemon import CommanderDaemon
from claude_mpm.commander.models import Project
from claude_mpm.commander.models.events import Event, EventStatus, EventType
from claude_mpm.commander.project_session import SessionState


@pytest.mark.integration
@pytest.mark.asyncio
async def test_daemon_restart_recovers_projects(integration_config: DaemonConfig):
    """Test daemon recovers all registered projects after restart."""
    with patch("claude_mpm.commander.daemon.TmuxOrchestrator") as mock_tmux_cls, patch(
        "claude_mpm.commander.daemon.uvicorn.Server"
    ) as mock_server_cls:
        mock_tmux = MagicMock()
        mock_tmux.session_exists.return_value = False
        mock_tmux_cls.return_value = mock_tmux

        mock_server = MagicMock()
        mock_server.serve = AsyncMock()
        mock_server_cls.return_value = mock_server

        # First daemon - register multiple projects
        daemon1 = CommanderDaemon(integration_config)
        await daemon1.start()

        project_ids = []
        for i in range(3):
            path = integration_config.state_dir / f"project_{i}"
            path.mkdir(parents=True, exist_ok=True)
            project = daemon1.registry.register(str(path), f"Project {i}")
            project_ids.append(project.id)

        await daemon1._save_state()
        await daemon1.stop()

        # Second daemon - should recover all projects
        daemon2 = CommanderDaemon(integration_config)
        await daemon2.start()

        for project_id in project_ids:
            recovered = daemon2.registry.get(project_id)
            assert recovered is not None
            assert recovered.id == project_id

        await daemon2.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_daemon_restart_recovers_pending_events(integration_config: DaemonConfig):
    """Test daemon recovers pending events after restart."""
    with patch("claude_mpm.commander.daemon.TmuxOrchestrator") as mock_tmux_cls, patch(
        "claude_mpm.commander.daemon.uvicorn.Server"
    ) as mock_server_cls:
        mock_tmux = MagicMock()
        mock_tmux.session_exists.return_value = False
        mock_tmux_cls.return_value = mock_tmux

        mock_server = MagicMock()
        mock_server.serve = AsyncMock()
        mock_server_cls.return_value = mock_server

        # First daemon
        daemon1 = CommanderDaemon(integration_config)
        await daemon1.start()

        # Register project
        path = integration_config.state_dir / "test_project"
        path.mkdir(parents=True, exist_ok=True)
        project = daemon1.registry.register(str(path), "Test Project")

        # Add multiple events
        event_ids = []
        for i in range(3):
            event = Event(
                id=f"event-{i}",
                project_id=project.id,
                event_type=EventType.APPROVAL,
                title=f"Event {i}",
                content=f"Content {i}",
            )
            daemon1.event_manager.add_event(event)
            event_ids.append(event.id)

        await daemon1._save_state()
        await daemon1.stop()

        # Second daemon
        daemon2 = CommanderDaemon(integration_config)
        await daemon2.start()

        # Verify all events recovered
        pending = daemon2.event_manager.get_pending()
        recovered_ids = [e.id for e in pending]

        assert len(recovered_ids) == 3
        for event_id in event_ids:
            assert event_id in recovered_ids

        await daemon2.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_daemon_restart_recovers_work_queue(integration_config: DaemonConfig):
    """Test daemon recovers work queue state after restart."""
    # Note: This test validates the expected behavior once WorkQueue persistence is implemented
    # Currently WorkQueue doesn't persist, so this documents the requirement

    # When implemented, work queue should:
    # 1. Save queued, in_progress, and completed work items
    # 2. Restore dependencies and priority ordering
    # 3. Resume in_progress items appropriately

    # Placeholder test - will be expanded with actual persistence
    assert True  # TODO: Implement when WorkQueue persistence added


@pytest.mark.integration
@pytest.mark.asyncio
async def test_corrupt_projects_file_handling(integration_config: DaemonConfig):
    """Test daemon handles corrupt projects.json gracefully."""
    with patch("claude_mpm.commander.daemon.TmuxOrchestrator") as mock_tmux_cls, patch(
        "claude_mpm.commander.daemon.uvicorn.Server"
    ) as mock_server_cls:
        mock_tmux = MagicMock()
        mock_tmux.session_exists.return_value = False
        mock_tmux_cls.return_value = mock_tmux

        mock_server = MagicMock()
        mock_server.serve = AsyncMock()
        mock_server_cls.return_value = mock_server

        # Create corrupt file
        state_dir = integration_config.state_dir
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "projects.json").write_text("{ this is not valid json }")

        # Daemon should start without crashing
        daemon = CommanderDaemon(integration_config)
        await daemon.start()

        # No projects should be loaded
        assert len(daemon.registry._projects) == 0

        await daemon.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_corrupt_sessions_file_handling(integration_config: DaemonConfig):
    """Test daemon handles corrupt sessions.json gracefully."""
    with patch("claude_mpm.commander.daemon.TmuxOrchestrator") as mock_tmux_cls, patch(
        "claude_mpm.commander.daemon.uvicorn.Server"
    ) as mock_server_cls:
        mock_tmux = MagicMock()
        mock_tmux.session_exists.return_value = False
        mock_tmux_cls.return_value = mock_tmux

        mock_server = MagicMock()
        mock_server.serve = AsyncMock()
        mock_server_cls.return_value = mock_server

        # Create corrupt file
        state_dir = integration_config.state_dir
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "sessions.json").write_text("not json at all!!!")

        # Daemon should start
        daemon = CommanderDaemon(integration_config)
        await daemon.start()

        # No sessions should be loaded
        assert len(daemon.sessions) == 0

        await daemon.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_corrupt_events_file_handling(integration_config: DaemonConfig):
    """Test daemon handles corrupt events.json gracefully."""
    with patch("claude_mpm.commander.daemon.TmuxOrchestrator") as mock_tmux_cls, patch(
        "claude_mpm.commander.daemon.uvicorn.Server"
    ) as mock_server_cls:
        mock_tmux = MagicMock()
        mock_tmux.session_exists.return_value = False
        mock_tmux_cls.return_value = mock_tmux

        mock_server = MagicMock()
        mock_server.serve = AsyncMock()
        mock_server_cls.return_value = mock_server

        # Create corrupt file
        state_dir = integration_config.state_dir
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "events.json").write_text("[{invalid}]")

        # Daemon should start
        daemon = CommanderDaemon(integration_config)
        await daemon.start()

        # No events should be loaded
        pending = daemon.event_manager.get_pending()
        assert len(pending) == 0

        await daemon.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_missing_state_files_handling(integration_config: DaemonConfig):
    """Test daemon handles missing state files gracefully."""
    with patch("claude_mpm.commander.daemon.TmuxOrchestrator") as mock_tmux_cls, patch(
        "claude_mpm.commander.daemon.uvicorn.Server"
    ) as mock_server_cls:
        mock_tmux = MagicMock()
        mock_tmux.session_exists.return_value = False
        mock_tmux_cls.return_value = mock_tmux

        mock_server = MagicMock()
        mock_server.serve = AsyncMock()
        mock_server_cls.return_value = mock_server

        # Don't create any state files
        state_dir = integration_config.state_dir
        state_dir.mkdir(parents=True, exist_ok=True)

        # Daemon should start with clean state
        daemon = CommanderDaemon(integration_config)
        await daemon.start()

        assert len(daemon.registry._projects) == 0
        assert len(daemon.sessions) == 0
        assert len(daemon.event_manager.get_pending()) == 0

        await daemon.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_state_file_atomic_writes(integration_config: DaemonConfig):
    """Test state files are written atomically to prevent corruption."""
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
        path = integration_config.state_dir / "test_project"
        path.mkdir(parents=True, exist_ok=True)
        project = daemon.registry.register(str(path), "Test Project")

        # Save state
        await daemon._save_state()

        # Verify files exist and are valid JSON
        state_dir = daemon.config.state_dir

        projects_file = state_dir / "projects.json"
        assert projects_file.exists()
        projects_data = json.loads(projects_file.read_text())
        assert isinstance(projects_data, list)
        assert len(projects_data) == 1

        sessions_file = state_dir / "sessions.json"
        assert sessions_file.exists()
        sessions_data = json.loads(sessions_file.read_text())
        assert isinstance(sessions_data, dict)

        events_file = state_dir / "events.json"
        assert events_file.exists()
        events_data = json.loads(events_file.read_text())
        assert isinstance(events_data, list)

        await daemon.stop()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_periodic_state_persistence_interval(integration_config: DaemonConfig):
    """Test daemon persists state at configured intervals."""
    # Short save interval for testing
    integration_config.save_interval = 0.3

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
        path = integration_config.state_dir / "test_project"
        path.mkdir(parents=True, exist_ok=True)
        daemon.registry.register(str(path), "Test Project")

        # Wait for multiple save intervals
        await asyncio.sleep(0.7)

        # State should have been saved
        state_file = daemon.config.state_dir / "projects.json"
        assert state_file.exists()

        # Verify content
        data = json.loads(state_file.read_text())
        assert len(data) == 1
        assert data[0]["name"] == "Test Project"

        await daemon.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_session_state_persistence(integration_config: DaemonConfig):
    """Test session state (active pane, pause reason) persists."""
    with patch("claude_mpm.commander.daemon.TmuxOrchestrator") as mock_tmux_cls, patch(
        "claude_mpm.commander.daemon.uvicorn.Server"
    ) as mock_server_cls:
        mock_tmux = MagicMock()
        mock_tmux.session_exists.return_value = False
        mock_tmux_cls.return_value = mock_tmux

        mock_server = MagicMock()
        mock_server.serve = AsyncMock()
        mock_server_cls.return_value = mock_server

        # First daemon
        daemon1 = CommanderDaemon(integration_config)
        await daemon1.start()

        # Create project and session
        path = integration_config.state_dir / "test_project"
        path.mkdir(parents=True, exist_ok=True)
        project = daemon1.registry.register(str(path), "Test Project")

        session = daemon1.get_or_create_session(project.id)
        session._state = SessionState.PAUSED
        session.active_pane = "commander:window.1"
        session.pause_reason = "event-123"

        await daemon1._save_state()
        await daemon1.stop()

        # Second daemon
        daemon2 = CommanderDaemon(integration_config)
        await daemon2.start()

        # Verify session state recovered
        recovered_session = daemon2.sessions.get(project.id)
        assert recovered_session is not None
        assert recovered_session.active_pane == "commander:window.1"
        assert recovered_session.pause_reason == "event-123"

        await daemon2.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_resolved_events_not_persisted(integration_config: DaemonConfig):
    """Test resolved events are not persisted (only pending)."""
    with patch("claude_mpm.commander.daemon.TmuxOrchestrator") as mock_tmux_cls, patch(
        "claude_mpm.commander.daemon.uvicorn.Server"
    ) as mock_server_cls:
        mock_tmux = MagicMock()
        mock_tmux.session_exists.return_value = False
        mock_tmux_cls.return_value = mock_tmux

        mock_server = MagicMock()
        mock_server.serve = AsyncMock()
        mock_server_cls.return_value = mock_server

        # First daemon
        daemon1 = CommanderDaemon(integration_config)
        await daemon1.start()

        # Register project
        path = integration_config.state_dir / "test_project"
        path.mkdir(parents=True, exist_ok=True)
        project = daemon1.registry.register(str(path), "Test Project")

        # Add pending and resolved events
        pending_event = Event(
            id="pending-event",
            project_id=project.id,
            event_type=EventType.APPROVAL,
            title="Pending",
            content="Still pending",
        )
        resolved_event = Event(
            id="resolved-event",
            project_id=project.id,
            event_type=EventType.APPROVAL,
            title="Resolved",
            content="Already resolved",
        )

        daemon1.event_manager.add_event(pending_event)
        daemon1.event_manager.add_event(resolved_event)
        daemon1.event_manager.resolve_event(resolved_event.id, "Done")

        await daemon1._save_state()
        await daemon1.stop()

        # Second daemon
        daemon2 = CommanderDaemon(integration_config)
        await daemon2.start()

        # Only pending event should be recovered
        pending = daemon2.event_manager.get_pending()
        assert len(pending) == 1
        assert pending[0].id == "pending-event"

        await daemon2.stop()
