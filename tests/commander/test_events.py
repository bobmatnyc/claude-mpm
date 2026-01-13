"""Tests for Event Data Model and EventManager.

Tests cover:
- Event creation with all types
- Default priority assignment
- Inbox sorting (CRITICAL first, oldest first within priority)
- Status transitions (respond, dismiss, acknowledge)
- Pending event queries (all and by project)
- Blocking event detection
- Project event clearing
- Thread safety with concurrent access
"""

import threading
import time
from datetime import datetime, timezone

import pytest

from claude_mpm.commander.events.manager import EventManager
from claude_mpm.commander.models.events import (
    BLOCKING_EVENTS,
    DEFAULT_PRIORITIES,
    Event,
    EventPriority,
    EventStatus,
    EventType,
)


class TestEventModel:
    """Test Event dataclass and enums."""

    def test_event_creation(self):
        """Test creating event with all fields."""
        now = datetime.now(timezone.utc)
        event = Event(
            id="evt_123",
            project_id="proj_abc",
            type=EventType.DECISION_NEEDED,
            priority=EventPriority.HIGH,
            title="Choose deployment",
            content="Select target environment",
            options=["staging", "production"],
            context={"ticket_id": "PROJ-42"},
        )

        assert event.id == "evt_123"
        assert event.project_id == "proj_abc"
        assert event.type == EventType.DECISION_NEEDED
        assert event.priority == EventPriority.HIGH
        assert event.title == "Choose deployment"
        assert event.content == "Select target environment"
        assert event.options == ["staging", "production"]
        assert event.context == {"ticket_id": "PROJ-42"}
        assert event.status == EventStatus.PENDING
        assert event.response is None
        assert event.responded_at is None
        assert event.created_at >= now

    def test_event_defaults(self):
        """Test event creation with minimal required fields."""
        event = Event(
            id="evt_123",
            project_id="proj_abc",
            type=EventType.STATUS,
            priority=EventPriority.INFO,
            title="Build complete",
        )

        assert event.status == EventStatus.PENDING
        assert event.content == ""
        assert event.context == {}
        assert event.options is None
        assert event.session_id is None

    def test_event_is_blocking(self):
        """Test blocking event detection."""
        # ERROR blocks all projects
        error_event = Event(
            id="evt_1",
            project_id="proj_1",
            type=EventType.ERROR,
            priority=EventPriority.CRITICAL,
            title="Fatal error",
        )
        assert error_event.is_blocking is True
        assert error_event.blocking_scope == "all"

        # DECISION_NEEDED blocks project
        decision_event = Event(
            id="evt_2",
            project_id="proj_1",
            type=EventType.DECISION_NEEDED,
            priority=EventPriority.HIGH,
            title="Choose option",
        )
        assert decision_event.is_blocking is True
        assert decision_event.blocking_scope == "project"

        # STATUS doesn't block
        status_event = Event(
            id="evt_3",
            project_id="proj_1",
            type=EventType.STATUS,
            priority=EventPriority.INFO,
            title="Build complete",
        )
        assert status_event.is_blocking is False
        assert status_event.blocking_scope is None

        # Resolved events don't block
        resolved_event = Event(
            id="evt_4",
            project_id="proj_1",
            type=EventType.ERROR,
            priority=EventPriority.CRITICAL,
            title="Error resolved",
            status=EventStatus.RESOLVED,
        )
        assert resolved_event.is_blocking is False

    def test_priority_comparison(self):
        """Test priority ordering."""
        assert EventPriority.CRITICAL < EventPriority.HIGH
        assert EventPriority.HIGH < EventPriority.NORMAL
        assert EventPriority.NORMAL < EventPriority.LOW
        assert EventPriority.LOW < EventPriority.INFO

    def test_default_priorities(self):
        """Test default priority mapping."""
        assert DEFAULT_PRIORITIES[EventType.ERROR] == EventPriority.CRITICAL
        assert DEFAULT_PRIORITIES[EventType.DECISION_NEEDED] == EventPriority.HIGH
        assert DEFAULT_PRIORITIES[EventType.APPROVAL] == EventPriority.HIGH
        assert DEFAULT_PRIORITIES[EventType.CLARIFICATION] == EventPriority.NORMAL
        assert DEFAULT_PRIORITIES[EventType.TASK_COMPLETE] == EventPriority.LOW
        assert DEFAULT_PRIORITIES[EventType.STATUS] == EventPriority.INFO


class TestEventManager:
    """Test EventManager functionality."""

    def test_create_event(self):
        """Test creating events of different types."""
        manager = EventManager()

        # Create with all fields
        event1 = manager.create(
            project_id="proj_1",
            event_type=EventType.DECISION_NEEDED,
            title="Choose deployment",
            content="Select target",
            priority=EventPriority.HIGH,
            options=["staging", "prod"],
            context={"ticket": "PROJ-1"},
        )

        assert event1.id.startswith("evt_")
        assert event1.project_id == "proj_1"
        assert event1.type == EventType.DECISION_NEEDED
        assert event1.priority == EventPriority.HIGH
        assert event1.title == "Choose deployment"
        assert event1.options == ["staging", "prod"]

        # Create with minimal fields (should use default priority)
        event2 = manager.create(
            project_id="proj_2",
            event_type=EventType.ERROR,
            title="Database error",
        )

        assert event2.priority == EventPriority.CRITICAL  # Default for ERROR
        assert event2.content == ""
        assert event2.options is None

    def test_default_priority_assignment(self):
        """Test automatic priority assignment based on event type."""
        manager = EventManager()

        # Error should get CRITICAL
        error = manager.create("proj_1", EventType.ERROR, "Error occurred")
        assert error.priority == EventPriority.CRITICAL

        # Decision needed should get HIGH
        decision = manager.create("proj_1", EventType.DECISION_NEEDED, "Choose option")
        assert decision.priority == EventPriority.HIGH

        # Status should get INFO
        status = manager.create("proj_1", EventType.STATUS, "Build complete")
        assert status.priority == EventPriority.INFO

        # Task complete should get LOW
        task = manager.create("proj_1", EventType.TASK_COMPLETE, "Task done")
        assert task.priority == EventPriority.LOW

    def test_get_event(self):
        """Test retrieving event by ID."""
        manager = EventManager()

        event = manager.create("proj_1", EventType.STATUS, "Test event")
        retrieved = manager.get(event.id)

        assert retrieved is event
        assert retrieved.id == event.id

        # Non-existent event
        assert manager.get("evt_nonexistent") is None

    def test_get_pending(self):
        """Test getting pending events."""
        manager = EventManager()

        # Create events for different projects
        event1 = manager.create("proj_1", EventType.STATUS, "Event 1")
        event2 = manager.create("proj_1", EventType.ERROR, "Event 2")
        event3 = manager.create("proj_2", EventType.STATUS, "Event 3")

        # Resolve one event
        manager.respond(event2.id, "Fixed")

        # Get all pending
        all_pending = manager.get_pending()
        assert len(all_pending) == 2
        assert event1 in all_pending
        assert event3 in all_pending
        assert event2 not in all_pending

        # Get pending for specific project
        proj1_pending = manager.get_pending("proj_1")
        assert len(proj1_pending) == 1
        assert event1 in proj1_pending

    def test_inbox_sorting(self):
        """Test inbox sorting by priority then timestamp."""
        manager = EventManager()

        # Create events with different priorities (in random order)
        # Note: Add small delays to ensure different timestamps
        low = manager.create("proj_1", EventType.TASK_COMPLETE, "Low priority")
        time.sleep(0.001)

        critical = manager.create("proj_1", EventType.ERROR, "Critical error")
        time.sleep(0.001)

        info = manager.create("proj_1", EventType.STATUS, "Info status")
        time.sleep(0.001)

        high = manager.create("proj_1", EventType.DECISION_NEEDED, "High priority")
        time.sleep(0.001)

        normal = manager.create("proj_1", EventType.CLARIFICATION, "Normal priority")

        inbox = manager.get_inbox()

        # Should be sorted: CRITICAL, HIGH, NORMAL, LOW, INFO
        assert inbox[0] == critical
        assert inbox[1] == high
        assert inbox[2] == normal
        assert inbox[3] == low
        assert inbox[4] == info

    def test_inbox_sorting_same_priority(self):
        """Test inbox sorting by timestamp within same priority."""
        manager = EventManager()

        # Create multiple events with same priority
        event1 = manager.create("proj_1", EventType.STATUS, "First")
        time.sleep(0.001)
        event2 = manager.create("proj_1", EventType.STATUS, "Second")
        time.sleep(0.001)
        event3 = manager.create("proj_1", EventType.STATUS, "Third")

        inbox = manager.get_inbox()

        # Should be sorted by created_at (oldest first)
        assert inbox[0] == event1
        assert inbox[1] == event2
        assert inbox[2] == event3

    def test_inbox_limit(self):
        """Test inbox result limiting."""
        manager = EventManager()

        # Create 10 events
        for i in range(10):
            manager.create("proj_1", EventType.STATUS, f"Event {i}")

        inbox = manager.get_inbox(limit=5)
        assert len(inbox) == 5

    def test_respond_to_event(self):
        """Test responding to event."""
        manager = EventManager()

        event = manager.create("proj_1", EventType.DECISION_NEEDED, "Choose option")
        assert event.status == EventStatus.PENDING
        assert event.response is None
        assert event.responded_at is None

        before_response = datetime.now(timezone.utc)
        updated = manager.respond(event.id, "Option A")

        assert updated.status == EventStatus.RESOLVED
        assert updated.response == "Option A"
        assert updated.responded_at is not None
        assert updated.responded_at >= before_response

        # Event should no longer be in pending
        pending = manager.get_pending()
        assert event not in pending

    def test_dismiss_event(self):
        """Test dismissing event."""
        manager = EventManager()

        event = manager.create("proj_1", EventType.STATUS, "Info message")
        updated = manager.dismiss(event.id)

        assert updated.status == EventStatus.DISMISSED
        assert updated.response is None

        # Event should no longer be in pending
        pending = manager.get_pending()
        assert event not in pending

    def test_acknowledge_event(self):
        """Test acknowledging event."""
        manager = EventManager()

        event = manager.create("proj_1", EventType.ERROR, "Error occurred")
        updated = manager.acknowledge(event.id)

        assert updated.status == EventStatus.ACKNOWLEDGED
        assert updated.response is None

        # Event should no longer be in pending
        pending = manager.get_pending()
        assert event not in pending

    def test_status_transitions(self):
        """Test all status transition methods."""
        manager = EventManager()

        # Test respond
        event1 = manager.create("proj_1", EventType.DECISION_NEEDED, "Event 1")
        manager.respond(event1.id, "My response")
        assert manager.get(event1.id).status == EventStatus.RESOLVED

        # Test dismiss
        event2 = manager.create("proj_1", EventType.STATUS, "Event 2")
        manager.dismiss(event2.id)
        assert manager.get(event2.id).status == EventStatus.DISMISSED

        # Test acknowledge
        event3 = manager.create("proj_1", EventType.ERROR, "Event 3")
        manager.acknowledge(event3.id)
        assert manager.get(event3.id).status == EventStatus.ACKNOWLEDGED

    def test_status_transition_errors(self):
        """Test error handling in status transitions."""
        manager = EventManager()

        # Non-existent event
        with pytest.raises(KeyError, match="Event not found"):
            manager.respond("evt_nonexistent", "response")

        with pytest.raises(KeyError, match="Event not found"):
            manager.dismiss("evt_nonexistent")

        with pytest.raises(KeyError, match="Event not found"):
            manager.acknowledge("evt_nonexistent")

    def test_get_blocking_events(self):
        """Test getting blocking events."""
        manager = EventManager()

        # Create blocking events
        error = manager.create("proj_1", EventType.ERROR, "Critical error")
        decision = manager.create("proj_1", EventType.DECISION_NEEDED, "Choose option")
        approval = manager.create("proj_2", EventType.APPROVAL, "Approve deletion")

        # Create non-blocking events
        manager.create("proj_1", EventType.STATUS, "Info")
        manager.create("proj_1", EventType.TASK_COMPLETE, "Done")

        # Get all blocking events
        blocking = manager.get_blocking_events()
        assert len(blocking) == 3
        assert error in blocking
        assert decision in blocking
        assert approval in blocking

        # Get blocking events for specific project
        proj1_blocking = manager.get_blocking_events("proj_1")
        assert len(proj1_blocking) == 2
        assert error in proj1_blocking
        assert decision in proj1_blocking

    def test_blocking_events_exclude_resolved(self):
        """Test that resolved blocking events are not returned."""
        manager = EventManager()

        error = manager.create("proj_1", EventType.ERROR, "Error")
        decision = manager.create("proj_1", EventType.DECISION_NEEDED, "Choose")

        # Resolve error
        manager.respond(error.id, "Fixed")

        blocking = manager.get_blocking_events()
        assert len(blocking) == 1
        assert decision in blocking
        assert error not in blocking

    def test_clear_project_events(self):
        """Test clearing all events for a project."""
        manager = EventManager()

        # Create events for multiple projects
        manager.create("proj_1", EventType.STATUS, "Event 1")
        manager.create("proj_1", EventType.ERROR, "Event 2")
        manager.create("proj_2", EventType.STATUS, "Event 3")
        manager.create("proj_2", EventType.STATUS, "Event 4")

        # Clear proj_1 events
        removed = manager.clear_project_events("proj_1")
        assert removed == 2

        # proj_1 events should be gone
        proj1_events = manager.get_pending("proj_1")
        assert len(proj1_events) == 0

        # proj_2 events should remain
        proj2_events = manager.get_pending("proj_2")
        assert len(proj2_events) == 2

        # Clear non-existent project
        removed = manager.clear_project_events("proj_nonexistent")
        assert removed == 0

    def test_thread_safety(self):
        """Test concurrent access to EventManager."""
        manager = EventManager()
        errors = []

        def create_events(project_id, count):
            try:
                for i in range(count):
                    manager.create(
                        project_id=project_id,
                        event_type=EventType.STATUS,
                        title=f"Event {i}",
                    )
            except Exception as e:
                errors.append(e)

        def read_events():
            try:
                for _ in range(10):
                    manager.get_inbox()
                    manager.get_pending()
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        # Create threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=create_events, args=(f"proj_{i}", 10))
            threads.append(t)

        for _ in range(3):
            t = threading.Thread(target=read_events)
            threads.append(t)

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0

        # All events should be created
        all_events = manager.get_pending()
        assert len(all_events) == 50  # 5 projects * 10 events

    def test_project_index_consistency(self):
        """Test that project index stays consistent with events."""
        manager = EventManager()

        # Create events
        event1 = manager.create("proj_1", EventType.STATUS, "Event 1")
        event2 = manager.create("proj_1", EventType.STATUS, "Event 2")
        event3 = manager.create("proj_2", EventType.STATUS, "Event 3")

        # Verify project index
        proj1_events = manager.get_pending("proj_1")
        assert len(proj1_events) == 2

        # Clear project
        manager.clear_project_events("proj_1")

        # Verify index is cleaned up
        proj1_events = manager.get_pending("proj_1")
        assert len(proj1_events) == 0

        # Other project unaffected
        proj2_events = manager.get_pending("proj_2")
        assert len(proj2_events) == 1

    def test_all_event_types(self):
        """Test creating events of all types."""
        manager = EventManager()

        for event_type in EventType:
            event = manager.create("proj_1", event_type, f"Test {event_type.value}")
            assert event.type == event_type
            assert event.priority == DEFAULT_PRIORITIES.get(
                event_type, EventPriority.NORMAL
            )

    def test_session_id_tracking(self):
        """Test events can be associated with sessions."""
        manager = EventManager()

        event = manager.create(
            project_id="proj_1",
            event_type=EventType.DECISION_NEEDED,
            title="Choose option",
            session_id="sess_123",
        )

        assert event.session_id == "sess_123"

        # Can create events without session
        event2 = manager.create("proj_1", EventType.STATUS, "Status update")
        assert event2.session_id is None
