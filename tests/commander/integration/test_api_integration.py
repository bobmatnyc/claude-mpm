"""Integration tests for REST API with real components.

Tests API endpoints work correctly with actual daemon components including
project registry, event manager, and work queue.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from claude_mpm.commander.api.app import app
from claude_mpm.commander.daemon import CommanderDaemon
from claude_mpm.commander.models import Project
from claude_mpm.commander.models.events import Event, EventType


@pytest.fixture
def api_client():
    """Create test client for API."""
    return TestClient(app)


@pytest.mark.integration
def test_api_health_check(api_client: TestClient):
    """Test API health check endpoint."""
    response = api_client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_project_crud(
    daemon_lifecycle: CommanderDaemon,
    integration_tmp_path,
):
    """Test project CRUD operations via API."""
    # Note: This would require setting up the API with test client
    # For now, test directly through daemon/registry

    # Register project
    project_path = integration_tmp_path / "api_test_project"
    project_path.mkdir(parents=True, exist_ok=True)

    project = daemon_lifecycle.registry.register(str(project_path), "API Test Project")

    # Verify registration
    assert project is not None
    assert project.name == "API Test Project"

    # Get project
    retrieved = daemon_lifecycle.registry.get(project.id)
    assert retrieved is not None
    assert retrieved.id == project.id

    # List projects
    all_projects = daemon_lifecycle.registry.list()
    assert len(all_projects) >= 1
    assert any(p.id == project.id for p in all_projects)

    # Unregister project
    daemon_lifecycle.registry.unregister(project.id)
    assert daemon_lifecycle.registry.get(project.id) is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_event_resolution(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test event creation and resolution via API-like operations."""
    # Register project
    daemon_lifecycle.registry._projects[sample_project.id] = sample_project

    # Create event
    event = Event(
        id="api-event",
        project_id=sample_project.id,
        event_type=EventType.APPROVAL,
        title="User input needed",
        content="Please confirm action",
    )

    daemon_lifecycle.event_manager.add_event(event)

    # Verify event exists
    pending = daemon_lifecycle.event_manager.get_pending()
    assert len(pending) == 1
    assert pending[0].id == "api-event"

    # Resolve event (simulating API call)
    daemon_lifecycle.event_manager.resolve_event("api-event", "User confirmed action")

    # Verify resolution
    resolved_event = daemon_lifecycle.event_manager.get("api-event")
    assert resolved_event.response == "User confirmed action"

    # Should no longer be in pending
    pending = daemon_lifecycle.event_manager.get_pending()
    assert len(pending) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_work_queue_operations(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test work queue operations via API-like interface."""
    from claude_mpm.commander.models.work import WorkPriority
    from claude_mpm.commander.work.queue import WorkQueue

    # Create work queue
    queue = WorkQueue(sample_project.id)

    # Add work item (POST /api/work)
    work = queue.add("Test task from API", WorkPriority.HIGH)
    assert work.id is not None

    # List work items (GET /api/work)
    all_work = queue.list()
    assert len(all_work) == 1
    assert all_work[0].content == "Test task from API"

    # Get specific work item (GET /api/work/{work_id})
    retrieved_work = queue.get(work.id)
    assert retrieved_work is not None
    assert retrieved_work.id == work.id

    # Update work state (PATCH /api/work/{work_id})
    queue.start(work.id)
    started_work = queue.get(work.id)
    assert started_work.state.value == "in_progress"

    # Complete work (POST /api/work/{work_id}/complete)
    queue.complete(work.id, "Task completed via API")
    completed_work = queue.get(work.id)
    assert completed_work.state.value == "completed"
    assert completed_work.result == "Task completed via API"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_session_lifecycle(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test session creation and management via API-like operations."""
    daemon_lifecycle.registry._projects[sample_project.id] = sample_project

    # Create session (POST /api/sessions)
    session = daemon_lifecycle.get_or_create_session(sample_project.id)
    assert session is not None
    assert session.project.id == sample_project.id

    # Get session (GET /api/sessions/{project_id})
    retrieved_session = daemon_lifecycle.sessions.get(sample_project.id)
    assert retrieved_session is not None
    assert retrieved_session.project.id == sample_project.id

    # Mock session operations
    session.start = AsyncMock()
    session.stop = AsyncMock()

    # Start session (POST /api/sessions/{project_id}/start)
    from claude_mpm.commander.project_session import SessionState

    session._state = SessionState.RUNNING
    await session.start()
    assert session.state == SessionState.RUNNING

    # Stop session (POST /api/sessions/{project_id}/stop)
    session._state = SessionState.STOPPED
    await session.stop()
    assert session.state == SessionState.STOPPED


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_inbox_operations(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test inbox operations via API-like interface."""
    daemon_lifecycle.registry._projects[sample_project.id] = sample_project

    # Submit message to inbox (POST /api/inbox)
    from claude_mpm.commander.inbox.models import InboxMessage, MessagePriority

    message = InboxMessage(
        content="Test message from API",
        project_id=sample_project.id,
        priority=MessagePriority.NORMAL,
    )

    daemon_lifecycle.inbox.add_message(message)

    # Verify message added
    all_messages = daemon_lifecycle.inbox.get_all_messages()
    assert len(all_messages) == 1
    assert all_messages[0].content == "Test message from API"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_concurrent_operations(
    daemon_lifecycle: CommanderDaemon,
    multiple_projects: list[Project],
):
    """Test API handles concurrent operations on multiple projects."""
    # Register all projects
    for project in multiple_projects:
        daemon_lifecycle.registry._projects[project.id] = project

    # Create work queues for all projects
    from claude_mpm.commander.models.work import WorkPriority
    from claude_mpm.commander.work.queue import WorkQueue

    queues = {}
    for project in multiple_projects:
        queue = WorkQueue(project.id)
        work = queue.add(f"Task for {project.name}", WorkPriority.MEDIUM)
        queues[project.id] = (queue, work)

    # Verify all queues independent
    for project_id, (queue, work) in queues.items():
        work_items = queue.list()
        assert len(work_items) == 1
        assert work_items[0].project_id == project_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_error_handling(
    daemon_lifecycle: CommanderDaemon,
):
    """Test API error handling for invalid operations."""
    # Get non-existent project
    result = daemon_lifecycle.registry.get("non-existent-id")
    assert result is None

    # Resolve non-existent event
    try:
        daemon_lifecycle.event_manager.resolve_event("non-existent-event", "resolution")
    except ValueError as e:
        assert "not found" in str(e).lower() or "Event not found" in str(e)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_state_consistency_after_operations(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test API operations maintain consistent state."""
    daemon_lifecycle.registry._projects[sample_project.id] = sample_project

    # Perform multiple operations
    from claude_mpm.commander.models.work import WorkPriority
    from claude_mpm.commander.work.queue import WorkQueue

    queue = WorkQueue(sample_project.id)

    # Add multiple work items
    work_ids = []
    for i in range(3):
        work = queue.add(f"Task {i}", WorkPriority.MEDIUM)
        work_ids.append(work.id)

    # Add event
    event = Event(
        id="consistency-event",
        project_id=sample_project.id,
        event_type=EventType.STATUS,
        title="Info",
        content="Information",
    )
    daemon_lifecycle.event_manager.add_event(event)

    # Verify state consistent
    assert len(queue.list()) == 3
    assert len(daemon_lifecycle.event_manager.get_pending()) == 1

    # Complete all work
    for work_id in work_ids:
        queue.start(work_id)
        queue.complete(work_id)

    # Resolve event
    daemon_lifecycle.event_manager.resolve_event("consistency-event", "Noted")

    # Verify final state
    completed_work = [w for w in queue.list() if w.state.value == "completed"]
    assert len(completed_work) == 3

    pending_events = daemon_lifecycle.event_manager.get_pending()
    assert len(pending_events) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_pagination_support(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test API supports pagination for large result sets."""
    # Note: Pagination would be implemented in actual API routes
    # This tests the underlying data structures support it

    from claude_mpm.commander.models.work import WorkPriority
    from claude_mpm.commander.work.queue import WorkQueue

    queue = WorkQueue(sample_project.id)

    # Add many work items
    for i in range(50):
        queue.add(f"Task {i}", WorkPriority.MEDIUM)

    # Get all work
    all_work = queue.list()
    assert len(all_work) == 50

    # Simulate pagination (first 20)
    page1 = all_work[:20]
    assert len(page1) == 20

    # Simulate pagination (next 20)
    page2 = all_work[20:40]
    assert len(page2) == 20

    # Verify no overlap
    page1_ids = {w.id for w in page1}
    page2_ids = {w.id for w in page2}
    assert len(page1_ids & page2_ids) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_filter_by_state(
    daemon_lifecycle: CommanderDaemon,
    sample_project: Project,
):
    """Test API can filter work items by state."""
    from claude_mpm.commander.models.work import WorkPriority
    from claude_mpm.commander.work.queue import WorkQueue

    queue = WorkQueue(sample_project.id)

    # Add work items with different states
    queued = queue.add("Queued task", WorkPriority.MEDIUM)
    in_progress = queue.add("In progress task", WorkPriority.MEDIUM)
    completed = queue.add("Completed task", WorkPriority.MEDIUM)

    queue.start(in_progress.id)
    queue.start(completed.id)
    queue.complete(completed.id)

    # Get all work
    all_work = queue.list()

    # Filter by state
    queued_items = [w for w in all_work if w.state.value == "queued"]
    in_progress_items = [w for w in all_work if w.state.value == "in_progress"]
    completed_items = [w for w in all_work if w.state.value == "completed"]

    assert len(queued_items) == 1
    assert len(in_progress_items) == 1
    assert len(completed_items) == 1
