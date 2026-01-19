"""Integration test for API work queue → daemon auto-execution flow.

This test verifies that work added via the API is automatically picked up
and executed by the daemon's main loop, including auto-session creation.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from claude_mpm.commander.config import DaemonConfig
from claude_mpm.commander.daemon import CommanderDaemon
from claude_mpm.commander.models.work import WorkPriority, WorkState
from claude_mpm.commander.work.queue import WorkQueue


@pytest.fixture
def test_project_dir(tmp_path):
    """Create a temporary test project directory."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    return str(project_dir)


@pytest.mark.asyncio
async def test_api_work_auto_executes_via_daemon(tmp_path):
    """Test that work added via API (shared queue) auto-executes in daemon loop.

    This is the critical test that verifies the fix for:
    - API creates work in shared work_queues dict
    - Daemon detects work in _execute_pending_work()
    - Daemon auto-creates session for project
    - Daemon executes the work automatically
    """
    # Configure daemon
    config = DaemonConfig(
        state_dir=str(tmp_path / "state"),
        poll_interval=0.1,
        save_interval=60.0,
    )

    daemon = CommanderDaemon(config)

    try:
        # Create test project directory
        project_dir = tmp_path / "test_project"
        project_dir.mkdir(parents=True, exist_ok=True)

        # Register a test project
        project = daemon.registry.register(str(project_dir), "API Test Project")

        # Simulate API adding work to the SHARED work queue
        # (This is what the API route does now)
        if project.id not in daemon.work_queues:
            daemon.work_queues[project.id] = WorkQueue(project.id)

        queue = daemon.work_queues[project.id]
        work_item = queue.add("Implement OAuth authentication", WorkPriority.HIGH)

        # Verify work was added to queue
        assert work_item.state == WorkState.QUEUED
        assert queue.pending_count == 1

        # Verify NO session exists yet (this is key - API doesn't create sessions)
        assert project.id not in daemon.sessions

        # Mock the RuntimeExecutor spawn and send_message to avoid actual tmux
        from claude_mpm.commander.runtime.executor import RuntimeExecutor

        with patch.object(
            RuntimeExecutor, "spawn", new_callable=AsyncMock
        ) as mock_spawn, patch.object(
            RuntimeExecutor, "send_message", new_callable=AsyncMock
        ) as mock_send:
            mock_spawn.return_value = "%123"

            # Run daemon's work execution loop (first iteration)
            # This should:
            # 1. Detect work in daemon.work_queues[project.id]
            # 2. Auto-create session for project
            # 3. Start the session
            # 4. Execute the work
            await daemon._execute_pending_work()

            # Verify session was auto-created
            assert project.id in daemon.sessions
            session = daemon.sessions[project.id]

            # Verify session was started (spawned)
            mock_spawn.assert_called_once()

            # Verify work was executed (sent to runtime)
            mock_send.assert_called_once_with("%123", "Implement OAuth authentication")

            # Verify work state changed to IN_PROGRESS
            assert work_item.state == WorkState.IN_PROGRESS

    finally:
        # Cleanup
        await daemon.stop()


@pytest.mark.asyncio
async def test_api_work_with_no_daemon_queues_in_sync(tmp_path):
    """Test that API and daemon share the same work queue instances.

    This verifies the core fix: API uses daemon.work_queues, not project._work_queue.
    """
    config = DaemonConfig(
        state_dir=str(tmp_path / "state"),
        poll_interval=0.1,
    )

    daemon = CommanderDaemon(config)

    try:
        # Create and register project
        project_dir = tmp_path / "test_project"
        project_dir.mkdir(parents=True, exist_ok=True)
        project = daemon.registry.register(str(project_dir), "Sync Test")

        # Simulate API adding work (uses daemon.work_queues)
        daemon.work_queues[project.id] = WorkQueue(project.id)
        api_queue = daemon.work_queues[project.id]
        api_work = api_queue.add("API task", WorkPriority.MEDIUM)

        # Daemon should see the same work in its queue
        daemon_queue = daemon.work_queues[project.id]
        assert daemon_queue is api_queue  # Same instance!
        assert daemon_queue.pending_count == 1

        # Get work from daemon's perspective
        daemon_work = daemon_queue.get(api_work.id)
        assert daemon_work is not None
        assert daemon_work.id == api_work.id
        assert daemon_work.content == "API task"

        # State changes are visible on both sides
        daemon_queue.start(api_work.id)
        assert api_work.state == WorkState.IN_PROGRESS

    finally:
        await daemon.stop()


@pytest.mark.asyncio
async def test_multiple_projects_api_work_auto_execution(tmp_path):
    """Test that daemon handles work for multiple projects added via API."""
    config = DaemonConfig(
        state_dir=str(tmp_path / "state"),
        poll_interval=0.1,
    )

    daemon = CommanderDaemon(config)

    try:
        # Create and register multiple projects
        proj1_dir = tmp_path / "project1"
        proj2_dir = tmp_path / "project2"
        proj1_dir.mkdir(parents=True, exist_ok=True)
        proj2_dir.mkdir(parents=True, exist_ok=True)

        project1 = daemon.registry.register(str(proj1_dir), "Project 1")
        project2 = daemon.registry.register(str(proj2_dir), "Project 2")

        # Add work via API for both projects
        daemon.work_queues[project1.id] = WorkQueue(project1.id)
        daemon.work_queues[project2.id] = WorkQueue(project2.id)

        work1 = daemon.work_queues[project1.id].add(
            "Task for project 1", WorkPriority.HIGH
        )
        work2 = daemon.work_queues[project2.id].add(
            "Task for project 2", WorkPriority.HIGH
        )

        # Verify no sessions exist yet
        assert project1.id not in daemon.sessions
        assert project2.id not in daemon.sessions

        # Mock runtime operations
        from claude_mpm.commander.runtime.executor import RuntimeExecutor

        # Mock spawn to return unique pane IDs for each project
        pane_counter = [0]

        def mock_spawn_unique(*args, **kwargs):
            pane_counter[0] += 1
            return f"%{100 + pane_counter[0]}"

        with patch.object(
            RuntimeExecutor, "spawn", new_callable=AsyncMock
        ) as mock_spawn, patch.object(
            RuntimeExecutor, "send_message", new_callable=AsyncMock
        ) as mock_send:
            mock_spawn.side_effect = mock_spawn_unique

            # Run work execution
            await daemon._execute_pending_work()

            # Verify sessions auto-created for both projects
            assert project1.id in daemon.sessions
            assert project2.id in daemon.sessions

            # Verify both spawned
            assert mock_spawn.call_count == 2

            # Verify both work items executed
            assert mock_send.call_count == 2

            # Verify work states
            assert work1.state == WorkState.IN_PROGRESS
            assert work2.state == WorkState.IN_PROGRESS

    finally:
        await daemon.stop()


@pytest.mark.asyncio
async def test_daemon_skips_projects_without_work(tmp_path):
    """Test that daemon doesn't create sessions for projects without work."""
    config = DaemonConfig(
        state_dir=str(tmp_path / "state"),
        poll_interval=0.1,
    )

    daemon = CommanderDaemon(config)

    try:
        # Create and register project but DON'T add work
        project_dir = tmp_path / "test_project"
        project_dir.mkdir(parents=True, exist_ok=True)
        project = daemon.registry.register(str(project_dir), "No Work Project")

        # Create empty work queue (no work added)
        daemon.work_queues[project.id] = WorkQueue(project.id)

        # Verify no work
        assert daemon.work_queues[project.id].pending_count == 0

        # Run work execution
        await daemon._execute_pending_work()

        # Verify NO session was created (no work to execute)
        assert project.id not in daemon.sessions

    finally:
        await daemon.stop()
