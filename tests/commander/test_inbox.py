"""Tests for MPM Commander inbox system.

Tests InboxItem, Inbox, EventDeduplicator, and API endpoints.
"""

import time
from datetime import datetime, timedelta, timezone

import pytest

from claude_mpm.commander.events.manager import EventManager
from claude_mpm.commander.inbox import (
    EventDeduplicator,
    Inbox,
    InboxCounts,
    InboxItem,
)
from claude_mpm.commander.models.events import Event, EventPriority, EventType
from claude_mpm.commander.models.project import Project, ProjectState
from claude_mpm.commander.registry import ProjectRegistry


class TestInboxItem:
    """Test InboxItem age calculation and display formatting."""

    def test_age_calculation(self):
        """Test that age property returns correct timedelta."""
        # Create event 5 minutes ago
        five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
        event = Event(
            id="evt_test",
            project_id="proj_123",
            type=EventType.STATUS,
            priority=EventPriority.INFO,
            title="Test event",
            created_at=five_min_ago,
        )

        item = InboxItem(
            event=event,
            project_name="Test Project",
            project_path="/test/path",
        )

        # Age should be approximately 5 minutes
        age_seconds = item.age.total_seconds()
        assert 290 <= age_seconds <= 310  # 5 min ± 10 seconds

    def test_age_display_seconds(self):
        """Test age_display for events less than 60 seconds old."""
        # Create event 30 seconds ago
        thirty_sec_ago = datetime.now(timezone.utc) - timedelta(seconds=30)
        event = Event(
            id="evt_test",
            project_id="proj_123",
            type=EventType.STATUS,
            priority=EventPriority.INFO,
            title="Test event",
            created_at=thirty_sec_ago,
        )

        item = InboxItem(
            event=event,
            project_name="Test Project",
            project_path="/test/path",
        )

        assert item.age_display.endswith("s ago")
        assert "30" in item.age_display or "29" in item.age_display

    def test_age_display_minutes(self):
        """Test age_display for events less than 60 minutes old."""
        # Create event 5 minutes ago
        five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
        event = Event(
            id="evt_test",
            project_id="proj_123",
            type=EventType.STATUS,
            priority=EventPriority.INFO,
            title="Test event",
            created_at=five_min_ago,
        )

        item = InboxItem(
            event=event,
            project_name="Test Project",
            project_path="/test/path",
        )

        assert item.age_display == "5m ago"

    def test_age_display_hours(self):
        """Test age_display for events less than 24 hours old."""
        # Create event 3 hours ago
        three_hr_ago = datetime.now(timezone.utc) - timedelta(hours=3)
        event = Event(
            id="evt_test",
            project_id="proj_123",
            type=EventType.STATUS,
            priority=EventPriority.INFO,
            title="Test event",
            created_at=three_hr_ago,
        )

        item = InboxItem(
            event=event,
            project_name="Test Project",
            project_path="/test/path",
        )

        assert item.age_display == "3h ago"

    def test_age_display_days(self):
        """Test age_display for events 24+ hours old."""
        # Create event 2 days ago
        two_days_ago = datetime.now(timezone.utc) - timedelta(days=2)
        event = Event(
            id="evt_test",
            project_id="proj_123",
            type=EventType.STATUS,
            priority=EventPriority.INFO,
            title="Test event",
            created_at=two_days_ago,
        )

        item = InboxItem(
            event=event,
            project_name="Test Project",
            project_path="/test/path",
        )

        assert item.age_display == "2d ago"


class TestEventDeduplicator:
    """Test EventDeduplicator deduplication logic."""

    def test_first_event_not_duplicate(self):
        """Test that first occurrence is not a duplicate."""
        dedup = EventDeduplicator(window_seconds=60)

        is_dup = dedup.is_duplicate("proj_123", "error", "Connection failed")
        assert is_dup is False

    def test_duplicate_within_window(self):
        """Test that duplicate within window is detected."""
        dedup = EventDeduplicator(window_seconds=60)

        # First occurrence
        dedup.is_duplicate("proj_123", "error", "Connection failed")

        # Second occurrence immediately after
        is_dup = dedup.is_duplicate("proj_123", "error", "Connection failed")
        assert is_dup is True

    def test_different_title_not_duplicate(self):
        """Test that different titles are not duplicates."""
        dedup = EventDeduplicator(window_seconds=60)

        dedup.is_duplicate("proj_123", "error", "Connection failed")
        is_dup = dedup.is_duplicate("proj_123", "error", "Timeout occurred")

        assert is_dup is False

    def test_different_project_not_duplicate(self):
        """Test that same title in different project is not a duplicate."""
        dedup = EventDeduplicator(window_seconds=60)

        dedup.is_duplicate("proj_123", "error", "Connection failed")
        is_dup = dedup.is_duplicate("proj_456", "error", "Connection failed")

        assert is_dup is False

    def test_different_event_type_not_duplicate(self):
        """Test that same title with different event type is not a duplicate."""
        dedup = EventDeduplicator(window_seconds=60)

        dedup.is_duplicate("proj_123", "error", "Something happened")
        is_dup = dedup.is_duplicate("proj_123", "status", "Something happened")

        assert is_dup is False

    def test_duplicate_after_window_expires(self):
        """Test that duplicate after window expires is not detected."""
        dedup = EventDeduplicator(window_seconds=1)  # 1 second window

        # First occurrence
        dedup.is_duplicate("proj_123", "error", "Connection failed")

        # Wait for window to expire
        time.sleep(1.1)

        # Second occurrence after window
        is_dup = dedup.is_duplicate("proj_123", "error", "Connection failed")
        assert is_dup is False

    def test_make_key_format(self):
        """Test that make_key produces expected format."""
        dedup = EventDeduplicator()

        key = dedup.make_key("proj_123", "error", "Connection failed")

        # Key should be: project_id:event_type:title_hash
        assert key.startswith("proj_123:error:")
        assert len(key.split(":")[-1]) == 8  # Hash is 8 characters


class TestInbox:
    """Test Inbox filtering, sorting, and pagination."""

    @pytest.fixture
    def setup(self, tmp_path):
        """Create event manager, project registry, and inbox."""
        event_manager = EventManager()
        project_registry = ProjectRegistry()
        inbox = Inbox(event_manager, project_registry)

        # Create a temp directory for test project
        test_project_path = tmp_path / "test_project"
        test_project_path.mkdir()

        # Register a test project
        project = project_registry.register(str(test_project_path), "Test Project")

        return {
            "event_manager": event_manager,
            "registry": project_registry,
            "inbox": inbox,
            "project": project,
            "tmp_path": tmp_path,
        }

    def test_get_items_sorting_by_priority(self, setup):
        """Test that items are sorted by priority (high to low)."""
        event_manager = setup["event_manager"]
        project = setup["project"]
        inbox = setup["inbox"]

        # Create events in random priority order
        event_manager.create(
            project.id, EventType.STATUS, "Low priority", priority=EventPriority.LOW
        )
        event_manager.create(
            project.id,
            EventType.ERROR,
            "Critical priority",
            priority=EventPriority.CRITICAL,
        )
        event_manager.create(
            project.id,
            EventType.STATUS,
            "Normal priority",
            priority=EventPriority.NORMAL,
        )
        event_manager.create(
            project.id, EventType.STATUS, "High priority", priority=EventPriority.HIGH
        )

        items = inbox.get_items()

        # Should be sorted: CRITICAL, HIGH, NORMAL, LOW
        assert items[0].event.priority == EventPriority.CRITICAL
        assert items[1].event.priority == EventPriority.HIGH
        assert items[2].event.priority == EventPriority.NORMAL
        assert items[3].event.priority == EventPriority.LOW

    def test_get_items_sorting_by_time(self, setup):
        """Test that items with same priority are sorted by time (oldest first)."""
        event_manager = setup["event_manager"]
        project = setup["project"]
        inbox = setup["inbox"]

        # Create events with same priority but different times
        event1 = event_manager.create(
            project.id, EventType.STATUS, "First", priority=EventPriority.NORMAL
        )
        time.sleep(0.01)  # Small delay
        event2 = event_manager.create(
            project.id, EventType.STATUS, "Second", priority=EventPriority.NORMAL
        )
        time.sleep(0.01)
        event3 = event_manager.create(
            project.id, EventType.STATUS, "Third", priority=EventPriority.NORMAL
        )

        items = inbox.get_items()

        # Should be sorted by created_at (oldest first)
        assert items[0].event.id == event1.id
        assert items[1].event.id == event2.id
        assert items[2].event.id == event3.id

    def test_get_items_filter_by_priority(self, setup):
        """Test filtering items by priority."""
        event_manager = setup["event_manager"]
        project = setup["project"]
        inbox = setup["inbox"]

        # Create events with different priorities
        event_manager.create(
            project.id, EventType.ERROR, "Critical", priority=EventPriority.CRITICAL
        )
        event_manager.create(
            project.id, EventType.STATUS, "High", priority=EventPriority.HIGH
        )
        event_manager.create(
            project.id, EventType.STATUS, "Normal", priority=EventPriority.NORMAL
        )

        # Filter for only HIGH priority
        items = inbox.get_items(priority=EventPriority.HIGH)

        assert len(items) == 1
        assert items[0].event.priority == EventPriority.HIGH

    def test_get_items_filter_by_project(self, setup):
        """Test filtering items by project ID."""
        event_manager = setup["event_manager"]
        registry = setup["registry"]
        inbox = setup["inbox"]
        project1 = setup["project"]
        tmp_path = setup["tmp_path"]

        # Create second project directory
        test_project_path2 = tmp_path / "test_project2"
        test_project_path2.mkdir()

        # Register second project
        project2 = registry.register(str(test_project_path2), "Test Project 2")

        # Create events for both projects
        event_manager.create(project1.id, EventType.STATUS, "Project 1 event")
        event_manager.create(project1.id, EventType.STATUS, "Project 1 event 2")
        event_manager.create(project2.id, EventType.STATUS, "Project 2 event")

        # Filter for project1 only
        items = inbox.get_items(project_id=project1.id)

        assert len(items) == 2
        assert all(item.event.project_id == project1.id for item in items)

    def test_get_items_filter_by_event_type(self, setup):
        """Test filtering items by event type."""
        event_manager = setup["event_manager"]
        project = setup["project"]
        inbox = setup["inbox"]

        # Create events with different types
        event_manager.create(project.id, EventType.ERROR, "Error event")
        event_manager.create(project.id, EventType.STATUS, "Status event")
        event_manager.create(project.id, EventType.ERROR, "Another error")

        # Filter for only ERROR events
        items = inbox.get_items(event_type=EventType.ERROR)

        assert len(items) == 2
        assert all(item.event.type == EventType.ERROR for item in items)

    def test_get_items_pagination(self, setup):
        """Test pagination with limit and offset."""
        event_manager = setup["event_manager"]
        project = setup["project"]
        inbox = setup["inbox"]

        # Create 10 events
        for i in range(10):
            event_manager.create(project.id, EventType.STATUS, f"Event {i}")

        # Get first 5
        items_page1 = inbox.get_items(limit=5, offset=0)
        assert len(items_page1) == 5

        # Get next 5
        items_page2 = inbox.get_items(limit=5, offset=5)
        assert len(items_page2) == 5

        # Ensure pages are different
        page1_ids = {item.event.id for item in items_page1}
        page2_ids = {item.event.id for item in items_page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_get_items_enrichment(self, setup):
        """Test that items are enriched with project metadata."""
        event_manager = setup["event_manager"]
        project = setup["project"]
        inbox = setup["inbox"]
        tmp_path = setup["tmp_path"]

        event_manager.create(project.id, EventType.STATUS, "Test event")

        items = inbox.get_items()

        assert len(items) == 1
        item = items[0]
        assert item.project_name == "Test Project"
        assert item.project_path == str(tmp_path / "test_project")

    def test_get_counts_all_priorities(self, setup):
        """Test InboxCounts calculation with all priority levels."""
        event_manager = setup["event_manager"]
        project = setup["project"]
        inbox = setup["inbox"]

        # Create events for each priority
        event_manager.create(
            project.id, EventType.ERROR, "Critical 1", priority=EventPriority.CRITICAL
        )
        event_manager.create(
            project.id, EventType.ERROR, "Critical 2", priority=EventPriority.CRITICAL
        )
        event_manager.create(
            project.id, EventType.STATUS, "High", priority=EventPriority.HIGH
        )
        event_manager.create(
            project.id, EventType.STATUS, "Normal", priority=EventPriority.NORMAL
        )
        event_manager.create(
            project.id, EventType.STATUS, "Low", priority=EventPriority.LOW
        )
        event_manager.create(
            project.id, EventType.STATUS, "Info", priority=EventPriority.INFO
        )

        counts = inbox.get_counts()

        assert counts.critical == 2
        assert counts.high == 1
        assert counts.normal == 1
        assert counts.low == 1
        assert counts.info == 1
        assert counts.total == 6

    def test_get_counts_by_project(self, setup):
        """Test InboxCounts filtered by project."""
        event_manager = setup["event_manager"]
        registry = setup["registry"]
        inbox = setup["inbox"]
        project1 = setup["project"]
        tmp_path = setup["tmp_path"]

        # Create second project directory
        test_project_path2 = tmp_path / "test_project2"
        test_project_path2.mkdir()

        # Register second project
        project2 = registry.register(str(test_project_path2), "Test Project 2")

        # Create events for both projects
        event_manager.create(
            project1.id, EventType.ERROR, "P1 Critical", priority=EventPriority.CRITICAL
        )
        event_manager.create(
            project1.id, EventType.STATUS, "P1 Normal", priority=EventPriority.NORMAL
        )
        event_manager.create(
            project2.id, EventType.ERROR, "P2 Critical", priority=EventPriority.CRITICAL
        )

        # Get counts for project1 only
        counts = inbox.get_counts(project_id=project1.id)

        assert counts.critical == 1
        assert counts.normal == 1
        assert counts.total == 2

    def test_should_create_event_first_occurrence(self, setup):
        """Test that should_create_event returns True for first occurrence."""
        inbox = setup["inbox"]

        should_create = inbox.should_create_event(
            "proj_123", EventType.ERROR, "Connection failed"
        )

        assert should_create is True

    def test_should_create_event_duplicate(self, setup):
        """Test that should_create_event returns False for duplicate."""
        inbox = setup["inbox"]

        # First occurrence
        inbox.should_create_event("proj_123", EventType.ERROR, "Connection failed")

        # Duplicate
        should_create = inbox.should_create_event(
            "proj_123", EventType.ERROR, "Connection failed"
        )

        assert should_create is False
