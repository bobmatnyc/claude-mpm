"""Tests for EventHandler."""

from unittest.mock import Mock

import pytest

from claude_mpm.commander.events.manager import EventManager
from claude_mpm.commander.inbox import Inbox
from claude_mpm.commander.models.events import EventPriority, EventStatus, EventType
from claude_mpm.commander.models.project import Project, ProjectState
from claude_mpm.commander.project_session import ProjectSession, SessionState
from claude_mpm.commander.registry import ProjectRegistry
from claude_mpm.commander.runtime.executor import RuntimeExecutor
from claude_mpm.commander.tmux_orchestrator import TmuxOrchestrator
from claude_mpm.commander.workflow.event_handler import EventHandler


class TestEventHandler:
    """Test EventHandler event processing and resolution."""

    @pytest.fixture
    def registry(self):
        """Create a project registry."""
        return ProjectRegistry()

    @pytest.fixture
    def event_manager(self):
        """Create an event manager."""
        return EventManager()

    @pytest.fixture
    def inbox(self, event_manager, registry):
        """Create an inbox."""
        return Inbox(event_manager, registry)

    @pytest.fixture
    def tmux_orchestrator(self):
        """Create a mocked TmuxOrchestrator."""
        mock = Mock(spec=TmuxOrchestrator)
        mock.session_exists.return_value = True
        mock.create_pane.return_value = "%1"
        mock.list_panes.return_value = [{"id": "%1"}]
        mock.send_keys = Mock()
        return mock

    @pytest.fixture
    def project(self):
        """Create a test project."""
        return Project(
            id="proj_test",
            name="Test Project",
            path="/test/path",
            state=ProjectState.IDLE,
        )

    @pytest.fixture
    def session_manager(self, project, tmux_orchestrator):
        """Create a session manager with one test session."""
        executor = RuntimeExecutor(tmux_orchestrator)
        session = ProjectSession(project, tmux_orchestrator, executor=executor)
        return {project.id: session}

    @pytest.fixture
    def handler(self, inbox, session_manager):
        """Create an EventHandler."""
        return EventHandler(inbox, session_manager)

    def test_init(self, inbox, session_manager):
        """Test EventHandler initialization."""
        handler = EventHandler(inbox, session_manager)
        assert handler.inbox is inbox
        assert handler.session_manager is session_manager

    def test_init_validation(self):
        """Test EventHandler initialization validation."""
        with pytest.raises(ValueError, match="Inbox cannot be None"):
            EventHandler(None, {})

        with pytest.raises(ValueError, match="Session manager cannot be None"):
            EventHandler(Inbox(EventManager(), ProjectRegistry()), None)

    def test_is_blocking_event_types(self, handler, event_manager):
        """Test is_blocking correctly identifies blocking event types."""
        # Blocking event types (when PENDING)
        blocking_types = [
            EventType.ERROR,
            EventType.DECISION_NEEDED,
            EventType.APPROVAL,
        ]

        for event_type in blocking_types:
            event = event_manager.create(
                project_id="proj_test",
                event_type=event_type,
                title="Test blocking event",
            )
            assert handler.is_blocking(event), f"{event_type} should be blocking"

        # Non-blocking event types
        non_blocking_types = [
            EventType.TASK_COMPLETE,
            EventType.MILESTONE,
            EventType.STATUS,
            EventType.PROJECT_IDLE,
            EventType.CLARIFICATION,
        ]

        for event_type in non_blocking_types:
            event = event_manager.create(
                project_id="proj_test",
                event_type=event_type,
                title="Test non-blocking event",
            )
            assert not handler.is_blocking(event), (
                f"{event_type} should not be blocking"
            )

    def test_is_blocking_only_pending_events(self, handler, event_manager):
        """Test is_blocking only returns True for PENDING events."""
        # Create blocking event type
        event = event_manager.create(
            project_id="proj_test",
            event_type=EventType.ERROR,
            title="Test error",
        )

        # Initially PENDING - should be blocking
        assert event.status == EventStatus.PENDING
        assert handler.is_blocking(event)

        # Resolve event - should no longer be blocking
        event_manager.respond(event.id, "Fixed")
        assert event.status == EventStatus.RESOLVED
        assert not handler.is_blocking(event)

    @pytest.mark.asyncio
    async def test_process_non_blocking_event(
        self, handler, event_manager, session_manager
    ):
        """Test processing non-blocking event doesn't pause session."""
        # Start session
        session = session_manager["proj_test"]
        await session.start()
        assert session.state == SessionState.RUNNING

        # Create non-blocking event
        event = event_manager.create(
            project_id="proj_test",
            event_type=EventType.STATUS,
            title="Progress update",
        )

        # Process event
        await handler.process_event(event)

        # Session should still be RUNNING
        assert session.state == SessionState.RUNNING

    @pytest.mark.asyncio
    async def test_process_blocking_event_pauses_session(
        self, handler, event_manager, session_manager
    ):
        """Test processing blocking event pauses session."""
        # Start session
        session = session_manager["proj_test"]
        await session.start()
        assert session.state == SessionState.RUNNING

        # Create blocking event
        event = event_manager.create(
            project_id="proj_test",
            event_type=EventType.ERROR,
            title="Critical error",
        )

        # Process event
        await handler.process_event(event)

        # Session should be PAUSED
        assert session.state == SessionState.PAUSED
        assert event.id in session.pause_reason

    @pytest.mark.asyncio
    async def test_process_event_no_session(self, handler, event_manager):
        """Test processing event when no session exists."""
        # Create event for non-existent project
        event = event_manager.create(
            project_id="proj_nonexistent",
            event_type=EventType.ERROR,
            title="Error for missing project",
        )

        # Should not raise exception
        await handler.process_event(event)

    @pytest.mark.asyncio
    async def test_resolve_event_resumes_session(
        self, handler, event_manager, session_manager, tmux_orchestrator
    ):
        """Test resolving blocking event resumes paused session."""
        # Start session
        session = session_manager["proj_test"]
        await session.start()
        session.active_pane = "%1"

        # Create and process blocking event
        event = event_manager.create(
            project_id="proj_test",
            event_type=EventType.DECISION_NEEDED,
            title="Choose option",
            options=["A", "B"],
        )
        await handler.process_event(event)
        assert session.state == SessionState.PAUSED

        # Resolve event
        success = await handler.resolve_event(event.id, "Option A")

        # Should be successful
        assert success

        # Session should be RUNNING again
        assert session.state == SessionState.RUNNING

        # Event should be RESOLVED
        assert event.status == EventStatus.RESOLVED
        assert event.response == "Option A"

        # Response should have been sent to pane (last call after the initial 'claude' command)
        assert tmux_orchestrator.send_keys.call_count == 2
        tmux_orchestrator.send_keys.assert_called_with("%1", "Option A", enter=True)

    @pytest.mark.asyncio
    async def test_resolve_non_blocking_event(
        self, handler, event_manager, session_manager
    ):
        """Test resolving non-blocking event doesn't affect session."""
        # Start session
        session = session_manager["proj_test"]
        await session.start()
        initial_state = session.state

        # Create non-blocking event
        event = event_manager.create(
            project_id="proj_test",
            event_type=EventType.STATUS,
            title="Status update",
        )

        # Resolve event
        success = await handler.resolve_event(event.id, "Acknowledged")

        # Should be successful
        assert success

        # Event should be RESOLVED
        assert event.status == EventStatus.RESOLVED

        # Session state unchanged
        assert session.state == initial_state

    @pytest.mark.asyncio
    async def test_resolve_event_not_found(self, handler):
        """Test resolving non-existent event raises KeyError."""
        with pytest.raises(KeyError, match="Event not found"):
            await handler.resolve_event("evt_nonexistent", "Response")

    @pytest.mark.asyncio
    async def test_resolve_event_no_session(self, handler, event_manager):
        """Test resolving event when session doesn't exist."""
        # Create event for non-existent project
        event = event_manager.create(
            project_id="proj_nonexistent",
            event_type=EventType.ERROR,
            title="Error",
        )

        # Resolve should not raise, but returns False
        success = await handler.resolve_event(event.id, "Fixed")
        assert not success

        # Event should still be RESOLVED
        assert event.status == EventStatus.RESOLVED

    @pytest.mark.asyncio
    async def test_resolve_event_session_not_paused_for_this_event(
        self, handler, event_manager, session_manager
    ):
        """Test resolving when session paused for different reason."""
        # Start and pause session for different reason
        session = session_manager["proj_test"]
        await session.start()
        await session.pause("Other reason")

        # Create and resolve event
        event = event_manager.create(
            project_id="proj_test",
            event_type=EventType.ERROR,
            title="Error",
        )

        success = await handler.resolve_event(event.id, "Fixed")

        # Should succeed (event resolved) but not resume session
        assert success
        assert event.status == EventStatus.RESOLVED
        assert session.state == SessionState.PAUSED  # Still paused

    @pytest.mark.asyncio
    async def test_get_pending_events_all(self, handler, event_manager):
        """Test getting all pending events."""
        # Create events for multiple projects
        event1 = event_manager.create(
            project_id="proj_1", event_type=EventType.ERROR, title="Error 1"
        )
        event2 = event_manager.create(
            project_id="proj_2", event_type=EventType.DECISION_NEEDED, title="Decision"
        )
        event3 = event_manager.create(
            project_id="proj_1", event_type=EventType.STATUS, title="Status"
        )

        # Resolve one event
        event_manager.respond(event3.id, "Acknowledged")

        # Get all pending
        pending = await handler.get_pending_events()

        # Should return 2 pending events
        assert len(pending) == 2
        pending_ids = {e.id for e in pending}
        assert event1.id in pending_ids
        assert event2.id in pending_ids
        assert event3.id not in pending_ids

    @pytest.mark.asyncio
    async def test_get_pending_events_filtered_by_project(self, handler, event_manager):
        """Test getting pending events filtered by project."""
        # Create events for multiple projects
        event1 = event_manager.create(
            project_id="proj_1", event_type=EventType.ERROR, title="Error 1"
        )
        event2 = event_manager.create(
            project_id="proj_2", event_type=EventType.DECISION_NEEDED, title="Decision"
        )
        event3 = event_manager.create(
            project_id="proj_1", event_type=EventType.STATUS, title="Status"
        )

        # Get pending for proj_1
        pending = await handler.get_pending_events("proj_1")

        # Should return 2 events from proj_1
        assert len(pending) == 2
        pending_ids = {e.id for e in pending}
        assert event1.id in pending_ids
        assert event3.id in pending_ids
        assert event2.id not in pending_ids
