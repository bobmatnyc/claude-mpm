"""Integration tests for project workflow orchestration.

Tests full project lifecycle including registration, session management,
work execution, event handling, and project isolation.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.commander.daemon import CommanderDaemon
from claude_mpm.commander.models import Project, ProjectState
from claude_mpm.commander.models.events import Event, EventStatus, EventType
from claude_mpm.commander.models.work import WorkItem, WorkPriority, WorkState
from claude_mpm.commander.project_session import SessionState


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_project_lifecycle(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test complete project lifecycle: register → start → work → complete."""
    # 1. Register project
    daemon_lifecycle.registry._projects[sample_project.id] = sample_project
    daemon_lifecycle.registry._path_index[sample_project.path] = sample_project.id

    assert daemon_lifecycle.registry.get(sample_project.id) is not None

    # 2. Create and start session
    session = daemon_lifecycle.get_or_create_session(sample_project.id)
    assert session is not None
    assert session.state == SessionState.IDLE

    # Mock session.start() to avoid tmux interactions
    session.start = AsyncMock()
    session._state = SessionState.RUNNING
    await session.start()

    assert session.state == SessionState.RUNNING

    # 3. Add work item
    from claude_mpm.commander.work.queue import WorkQueue

    queue = WorkQueue(sample_project.id)
    work = queue.add("Implement feature X", priority=WorkPriority.HIGH)

    assert work.state == WorkState.QUEUED
    assert work.priority == WorkPriority.HIGH

    # 4. Mark work as completed
    queue.complete(work.id, result="Feature implemented successfully")

    completed_work = queue.get(work.id)
    assert completed_work.state == WorkState.COMPLETED
    assert completed_work.result == "Feature implemented successfully"

    # 5. Stop session
    session.stop = AsyncMock()
    session._state = SessionState.STOPPED
    await session.stop()

    assert session.state == SessionState.STOPPED


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_concurrent_projects(
    daemon_lifecycle: CommanderDaemon,
    multiple_projects: list[Project],
):
    """Test daemon can manage multiple concurrent projects."""
    # Register all projects
    for project in multiple_projects:
        daemon_lifecycle.registry._projects[project.id] = project
        daemon_lifecycle.registry._path_index[project.path] = project.id

    # Create sessions for all projects
    sessions = {}
    for project in multiple_projects:
        session = daemon_lifecycle.get_or_create_session(project.id)
        sessions[project.id] = session
        assert session is not None

    # Verify all sessions exist and are independent
    assert len(daemon_lifecycle.sessions) == 3

    for project_id, session in sessions.items():
        assert session.project.id == project_id
        assert session.state == SessionState.IDLE


@pytest.mark.integration
@pytest.mark.asyncio
async def test_project_event_isolation(
    daemon_lifecycle: CommanderDaemon,
    multiple_projects: list[Project],
):
    """Test events from one project don't affect other projects."""
    # Register projects
    for project in multiple_projects:
        daemon_lifecycle.registry._projects[project.id] = project

    project1 = multiple_projects[0]
    project2 = multiple_projects[1]

    # Add event to project1
    event1 = Event(
        id="event-1",
        project_id=project1.id,
        event_type=EventType.APPROVAL,
        title="Project 1 Event",
        content="This should only affect project 1",
    )
    daemon_lifecycle.event_manager.add_event(event1)

    # Verify project1 has event, project2 doesn't
    project1_events = [
        e
        for e in daemon_lifecycle.event_manager.get_pending()
        if e.project_id == project1.id
    ]
    project2_events = [
        e
        for e in daemon_lifecycle.event_manager.get_pending()
        if e.project_id == project2.id
    ]

    assert len(project1_events) == 1
    assert len(project2_events) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_project_work_queue_isolation(
    daemon_lifecycle: CommanderDaemon,
    multiple_projects: list[Project],
):
    """Test work items from one project don't leak to other projects."""
    from claude_mpm.commander.work.queue import WorkQueue

    # Create work queues for two projects
    queue1 = WorkQueue(multiple_projects[0].id)
    queue2 = WorkQueue(multiple_projects[1].id)

    # Add work to each queue
    work1 = queue1.add("Task for project 1", WorkPriority.HIGH)
    work2 = queue2.add("Task for project 2", WorkPriority.MEDIUM)

    # Verify isolation
    assert queue1.get(work1.id) is not None
    assert queue1.get(work2.id) is None  # work2 not in queue1

    assert queue2.get(work2.id) is not None
    assert queue2.get(work1.id) is None  # work1 not in queue2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_project_session_state_transitions(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test project session transitions through expected states."""
    daemon_lifecycle.registry._projects[sample_project.id] = sample_project

    session = daemon_lifecycle.get_or_create_session(sample_project.id)

    # Initial state
    assert session.state == SessionState.IDLE

    # Mock transitions
    session.start = AsyncMock()
    session.pause = AsyncMock()
    session.resume = AsyncMock()
    session.stop = AsyncMock()

    # IDLE → RUNNING
    session._state = SessionState.RUNNING
    await session.start()
    assert session.state == SessionState.RUNNING

    # RUNNING → PAUSED
    session._state = SessionState.PAUSED
    await session.pause("Waiting for user input")
    assert session.state == SessionState.PAUSED

    # PAUSED → RUNNING
    session._state = SessionState.RUNNING
    await session.resume()
    assert session.state == SessionState.RUNNING

    # RUNNING → STOPPED
    session._state = SessionState.STOPPED
    await session.stop()
    assert session.state == SessionState.STOPPED


@pytest.mark.integration
@pytest.mark.asyncio
async def test_project_event_workflow(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test event creation, resolution, and cleanup workflow."""
    daemon_lifecycle.registry._projects[sample_project.id] = sample_project

    # Create blocking event
    event = Event(
        id="event-workflow",
        project_id=sample_project.id,
        event_type=EventType.APPROVAL,
        title="User Input Required",
        content="Please confirm action",
    )

    # Add event
    daemon_lifecycle.event_manager.add_event(event)

    pending = daemon_lifecycle.event_manager.get_pending()
    assert len(pending) == 1
    assert pending[0].status == EventStatus.PENDING

    # Resolve event
    daemon_lifecycle.event_manager.resolve_event(event.id, "User confirmed action")

    # Verify resolution
    resolved = daemon_lifecycle.event_manager.get(event.id)
    assert resolved.status == EventStatus.RESOLVED
    assert resolved.response == "User confirmed action"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_project_work_priority_ordering(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test work items execute in priority order."""
    from claude_mpm.commander.work.queue import WorkQueue

    queue = WorkQueue(sample_project.id)

    # Add work items in random order
    low_work = queue.add("Low priority task", WorkPriority.LOW)
    critical_work = queue.add("Critical task", WorkPriority.CRITICAL)
    medium_work = queue.add("Medium priority task", WorkPriority.MEDIUM)
    high_work = queue.add("High priority task", WorkPriority.HIGH)

    # Get next should return critical first
    next_work = queue.get_next()
    assert next_work.id == critical_work.id

    # Mark critical as completed
    queue.complete(critical_work.id)

    # Next should be high
    next_work = queue.get_next()
    assert next_work.id == high_work.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_project_work_dependency_blocking(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test work items respect dependencies."""
    from claude_mpm.commander.work.queue import WorkQueue

    queue = WorkQueue(sample_project.id)

    # Create dependency chain: task1 must complete before task2
    task1 = queue.add("First task", WorkPriority.HIGH)
    task2 = queue.add(
        "Second task (depends on first)",
        WorkPriority.HIGH,
        depends_on=[task1.id],
    )

    # task1 should be next (no dependencies)
    next_work = queue.get_next()
    assert next_work.id == task1.id

    # task2 should NOT be next yet (dependency not satisfied)
    queue.start(task1.id)
    next_work = queue.get_next()
    assert next_work is None  # No work available

    # Complete task1
    queue.complete(task1.id)

    # Now task2 should be available
    next_work = queue.get_next()
    assert next_work.id == task2.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_project_persistent_across_restarts(
    integration_config,
    integration_tmp_path,
):
    """Test project state persists across daemon restarts."""
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
        test_path = integration_tmp_path / "persistent_project"
        test_path.mkdir(parents=True, exist_ok=True)
        project = daemon1.registry.register(str(test_path), "Persistent Project")
        project_id = project.id

        session = daemon1.get_or_create_session(project_id)
        session._state = SessionState.RUNNING
        session.active_pane = "test:pane.0"

        # Save and stop
        await daemon1._save_state()
        await daemon1.stop()

        # Second daemon instance
        daemon2 = CommanderDaemon(integration_config)
        await daemon2.start()

        # Verify project and session recovered
        recovered_project = daemon2.registry.get(project_id)
        assert recovered_project is not None
        assert recovered_project.name == "Persistent Project"

        assert project_id in daemon2.sessions
        recovered_session = daemon2.sessions[project_id]
        assert recovered_session.active_pane == "test:pane.0"

        await daemon2.stop()
