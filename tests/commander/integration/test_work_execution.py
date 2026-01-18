"""Integration tests for autonomous work execution in daemon main loop."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.commander.config import DaemonConfig
from claude_mpm.commander.daemon import CommanderDaemon
from claude_mpm.commander.models.events import EventType
from claude_mpm.commander.models.work import WorkPriority


@pytest.mark.asyncio
async def test_daemon_executes_queued_work():
    """Test that daemon main loop picks up and executes queued work."""
    # Configure daemon with short intervals for testing
    config = DaemonConfig(
        state_dir="/tmp/mpm_test_work_exec",
        poll_interval=0.1,
        save_interval=60.0,
    )

    daemon = CommanderDaemon(config)

    try:
        # Register a test project
        project = daemon.registry.register("/tmp/test-project", "Test Project")

        # Get or create session
        session = daemon.get_or_create_session(project.id)

        # Start the session (this would normally spawn Claude Code)
        with patch.object(
            session.executor, "spawn", new_callable=AsyncMock
        ) as mock_spawn:
            mock_spawn.return_value = "%123"
            await session.start()

        # Add work to queue
        queue = daemon.work_queues[project.id]
        work_item = queue.add("Implement user authentication", WorkPriority.HIGH)

        assert work_item.state.value == "queued"

        # Mock send_message to avoid actual tmux interaction
        executor = daemon.work_executors[project.id]
        with patch.object(
            executor.runtime, "send_message", new_callable=AsyncMock
        ) as mock_send:
            # Run one iteration of the daemon loop
            await daemon._execute_pending_work()

            # Verify work was picked up and sent to runtime
            mock_send.assert_called_once_with("%123", "Implement user authentication")

            # Verify work state changed to IN_PROGRESS
            assert work_item.state.value == "in_progress"

    finally:
        # Cleanup
        await daemon.stop()


@pytest.mark.asyncio
async def test_daemon_resumes_paused_sessions_on_event_resolution():
    """Test that daemon resumes paused sessions when blocking events are resolved."""
    config = DaemonConfig(
        state_dir="/tmp/mpm_test_resume",
        poll_interval=0.1,
    )

    daemon = CommanderDaemon(config)

    try:
        # Register project and create session
        project = daemon.registry.register("/tmp/test-project", "Test Project")
        session = daemon.get_or_create_session(project.id)

        # Start session
        with patch.object(
            session.executor, "spawn", new_callable=AsyncMock
        ) as mock_spawn:
            mock_spawn.return_value = "%123"
            await session.start()

        # Create a blocking event
        event = daemon.event_manager.create(
            project_id=project.id,
            session_id=None,
            event_type=EventType.DECISION_NEEDED,
            title="Should we proceed?",
            content="Confirm deployment to production",
        )

        # Pause the session due to the event
        await session.pause(event.id)

        assert session.state.value == "paused"
        assert session.pause_reason == event.id

        # Resolve the event
        daemon.event_manager.respond(event.id, "yes")

        # Run one iteration of the daemon loop
        await daemon._check_and_resume_sessions()

        # Verify session was resumed
        assert session.state.value == "running"
        assert session.pause_reason is None

    finally:
        await daemon.stop()


@pytest.mark.asyncio
async def test_daemon_skips_paused_sessions_for_work_execution():
    """Test that daemon doesn't execute work for paused sessions."""
    config = DaemonConfig(
        state_dir="/tmp/mpm_test_skip_paused",
        poll_interval=0.1,
    )

    daemon = CommanderDaemon(config)

    try:
        # Register project and create session
        project = daemon.registry.register("/tmp/test-project", "Test Project")
        session = daemon.get_or_create_session(project.id)

        # Start session
        with patch.object(
            session.executor, "spawn", new_callable=AsyncMock
        ) as mock_spawn:
            mock_spawn.return_value = "%123"
            await session.start()

        # Pause the session
        await session.pause("User intervention needed")

        # Add work to queue
        queue = daemon.work_queues[project.id]
        queue.add("Implement feature", WorkPriority.HIGH)

        # Mock send_message
        executor = daemon.work_executors[project.id]
        with patch.object(
            executor.runtime, "send_message", new_callable=AsyncMock
        ) as mock_send:
            # Run one iteration of work execution
            await daemon._execute_pending_work()

            # Verify NO work was executed (session is paused)
            mock_send.assert_not_called()

    finally:
        await daemon.stop()


@pytest.mark.asyncio
async def test_daemon_handles_work_execution_errors():
    """Test that daemon handles errors during work execution gracefully."""
    config = DaemonConfig(
        state_dir="/tmp/mpm_test_exec_errors",
        poll_interval=0.1,
    )

    daemon = CommanderDaemon(config)

    try:
        # Register project and create session
        project = daemon.registry.register("/tmp/test-project", "Test Project")
        session = daemon.get_or_create_session(project.id)

        # Start session
        with patch.object(
            session.executor, "spawn", new_callable=AsyncMock
        ) as mock_spawn:
            mock_spawn.return_value = "%123"
            await session.start()

        # Add work to queue
        queue = daemon.work_queues[project.id]
        work_item = queue.add("Implement feature", WorkPriority.HIGH)

        # Mock send_message to raise an error
        executor = daemon.work_executors[project.id]
        with patch.object(
            executor.runtime, "send_message", new_callable=AsyncMock
        ) as mock_send:
            mock_send.side_effect = RuntimeError("Tmux pane not found")

            # Run one iteration - should handle error gracefully
            await daemon._execute_pending_work()

            # Verify work was marked as failed
            assert work_item.state.value == "failed"
            assert "Tmux pane not found" in work_item.error

    finally:
        await daemon.stop()
