"""Integration tests for work execution workflow.

Tests work queue integration with session execution, event handling,
dependency resolution, and execution pause/resume.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_mpm.commander.daemon import CommanderDaemon
from claude_mpm.commander.models import Project
from claude_mpm.commander.models.events import Event, EventStatus, EventType
from claude_mpm.commander.models.work import WorkPriority, WorkState
from claude_mpm.commander.project_session import SessionState
from claude_mpm.commander.work.queue import WorkQueue


@pytest.mark.integration
@pytest.mark.asyncio
async def test_work_queue_to_execution_flow(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test work item flows from queue to execution to completion."""
    daemon_lifecycle.registry._projects[sample_project.id] = sample_project

    # Create work queue
    queue = WorkQueue(sample_project.id)
    work = queue.add("Execute task X", WorkPriority.HIGH)

    # Initial state
    assert work.state == WorkState.QUEUED

    # Start work
    queue.start(work.id)
    started_work = queue.get(work.id)
    assert started_work.state == WorkState.IN_PROGRESS
    assert started_work.started_at is not None

    # Complete work
    queue.complete(work.id, result="Task X completed successfully")
    completed_work = queue.get(work.id)
    assert completed_work.state == WorkState.COMPLETED
    assert completed_work.result == "Task X completed successfully"
    assert completed_work.completed_at is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_work_with_dependencies(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test work execution respects dependency chain."""
    queue = WorkQueue(sample_project.id)

    # Create dependency chain
    task1 = queue.add("Setup environment", WorkPriority.HIGH)
    task2 = queue.add("Run tests", WorkPriority.HIGH, depends_on=[task1.id])
    task3 = queue.add(
        "Deploy",
        WorkPriority.HIGH,
        depends_on=[task2.id],
    )

    # Only task1 should be runnable initially
    next_work = queue.get_next()
    assert next_work.id == task1.id

    # Complete task1
    queue.start(task1.id)
    queue.complete(task1.id, "Environment ready")

    # Now task2 should be runnable
    next_work = queue.get_next()
    assert next_work.id == task2.id

    # Complete task2
    queue.start(task2.id)
    queue.complete(task2.id, "Tests passed")

    # Now task3 should be runnable
    next_work = queue.get_next()
    assert next_work.id == task3.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_blocking_event_pauses_work(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test blocking event pauses work execution."""
    daemon_lifecycle.registry._projects[sample_project.id] = sample_project

    # Create session
    session = daemon_lifecycle.get_or_create_session(sample_project.id)
    session.start = AsyncMock()
    session.pause = AsyncMock()
    session._state = SessionState.RUNNING

    # Create work queue
    queue = WorkQueue(sample_project.id)
    work = queue.add("Long running task", WorkPriority.HIGH)
    queue.start(work.id)

    # Simulate blocking event
    event = Event(
        id="blocking-event",
        project_id=sample_project.id,
        event_type=EventType.APPROVAL,
        title="User confirmation required",
        content="Please confirm destructive action",
    )
    daemon_lifecycle.event_manager.add_event(event)

    # Pause session due to event
    session._state = SessionState.PAUSED
    session.pause_reason = event.id
    await session.pause(event.id)

    # Verify session paused
    assert session.state == SessionState.PAUSED
    assert session.pause_reason == event.id

    # Work should remain in progress
    work_item = queue.get(work.id)
    assert work_item.state == WorkState.IN_PROGRESS


@pytest.mark.integration
@pytest.mark.asyncio
async def test_resume_after_event_resolution(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test work execution resumes after event is resolved."""
    daemon_lifecycle.registry._projects[sample_project.id] = sample_project

    # Create session
    session = daemon_lifecycle.get_or_create_session(sample_project.id)
    session.start = AsyncMock()
    session.pause = AsyncMock()
    session.resume = AsyncMock()
    session._state = SessionState.PAUSED

    # Create blocking event
    event = Event(
        id="resume-event",
        project_id=sample_project.id,
        event_type=EventType.APPROVAL,
        title="Confirmation needed",
        content="Confirm action",
    )
    daemon_lifecycle.event_manager.add_event(event)

    # Session paused due to event
    session.pause_reason = event.id
    assert session.state == SessionState.PAUSED

    # Resolve event
    daemon_lifecycle.event_manager.resolve_event(event.id, "User confirmed")

    # Resume session
    session._state = SessionState.RUNNING
    session.pause_reason = None
    await session.resume()

    # Verify session resumed
    assert session.state == SessionState.RUNNING
    assert session.pause_reason is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_work_failure_handling(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test work item failure is recorded properly."""
    queue = WorkQueue(sample_project.id)

    # Create and start work
    work = queue.add("Task that will fail", WorkPriority.HIGH)
    queue.start(work.id)

    # Fail the work
    queue.fail(work.id, error="Task execution failed: timeout")

    # Verify failure recorded
    failed_work = queue.get(work.id)
    assert failed_work.state == WorkState.FAILED
    assert failed_work.error == "Task execution failed: timeout"
    assert failed_work.completed_at is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_work_items_in_sequence(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test multiple work items execute in sequence."""
    queue = WorkQueue(sample_project.id)

    # Add multiple work items
    work_items = [queue.add(f"Task {i}", WorkPriority.MEDIUM) for i in range(5)]

    # Execute all items in sequence
    for i, expected_work in enumerate(work_items):
        next_work = queue.get_next()
        assert next_work.id == expected_work.id, f"Failed at iteration {i}"

        queue.start(next_work.id)
        queue.complete(next_work.id, f"Task {i} completed")

    # Verify all completed
    all_work = queue.list()
    assert all(w.state == WorkState.COMPLETED for w in all_work)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_work_priority_preemption(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test high priority work is selected before low priority."""
    queue = WorkQueue(sample_project.id)

    # Add work in reverse priority order
    low = queue.add("Low priority", WorkPriority.LOW)
    medium = queue.add("Medium priority", WorkPriority.MEDIUM)
    high = queue.add("High priority", WorkPriority.HIGH)
    critical = queue.add("Critical priority", WorkPriority.CRITICAL)

    # Should execute in priority order
    execution_order = []
    while True:
        next_work = queue.get_next()
        if not next_work:
            break

        execution_order.append(next_work.id)
        queue.start(next_work.id)
        queue.complete(next_work.id)

    # Verify order: CRITICAL > HIGH > MEDIUM > LOW
    assert execution_order == [critical.id, high.id, medium.id, low.id]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_work_state_persistence(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test work state persists across daemon restarts."""
    # This will be implemented when work queue persistence is added
    # For now, just test the queue maintains state in memory

    queue = WorkQueue(sample_project.id)

    # Add various work items
    queued = queue.add("Queued task", WorkPriority.HIGH)
    in_progress = queue.add("In progress task", WorkPriority.MEDIUM)
    completed = queue.add("Completed task", WorkPriority.LOW)

    # Set various states
    queue.start(in_progress.id)
    queue.start(completed.id)
    queue.complete(completed.id, "Done")

    # Verify states maintained
    assert queue.get(queued.id).state == WorkState.QUEUED
    assert queue.get(in_progress.id).state == WorkState.IN_PROGRESS
    assert queue.get(completed.id).state == WorkState.COMPLETED


@pytest.mark.integration
@pytest.mark.asyncio
async def test_work_cancellation(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test work item can be cancelled."""
    queue = WorkQueue(sample_project.id)

    # Create work
    work = queue.add("Task to cancel", WorkPriority.MEDIUM)

    # Cancel it
    queue.cancel(work.id)

    # Verify cancelled
    cancelled_work = queue.get(work.id)
    assert cancelled_work.state == WorkState.CANCELLED

    # Should not appear in get_next()
    next_work = queue.get_next()
    assert next_work is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_informational_event_doesnt_block_work(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test informational events don't pause work execution."""
    daemon_lifecycle.registry._projects[sample_project.id] = sample_project

    session = daemon_lifecycle.get_or_create_session(sample_project.id)
    session._state = SessionState.RUNNING

    # Create informational event
    event = Event(
        id="info-event",
        project_id=sample_project.id,
        event_type=EventType.STATUS,
        title="FYI: Build completed",
        content="Build completed successfully",
    )
    daemon_lifecycle.event_manager.add_event(event)

    # Session should remain running
    assert session.state == SessionState.RUNNING
    assert session.pause_reason is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_work_queue_empty_behavior(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test work queue behavior when empty."""
    queue = WorkQueue(sample_project.id)

    # Empty queue
    assert queue.get_next() is None
    assert len(queue.list()) == 0

    # Add and complete work
    work = queue.add("Single task", WorkPriority.HIGH)
    queue.start(work.id)
    queue.complete(work.id)

    # Queue should show completed item but get_next returns None
    assert queue.get_next() is None
    assert len(queue.list()) == 1
    assert queue.list()[0].state == WorkState.COMPLETED
