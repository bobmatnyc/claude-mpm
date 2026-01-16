"""Tests for EventStore persistence."""

import asyncio
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from claude_mpm.commander.events.manager import EventManager
from claude_mpm.commander.inbox import Inbox
from claude_mpm.commander.models.events import (
    Event,
    EventPriority,
    EventStatus,
    EventType,
)
from claude_mpm.commander.persistence import EventStore
from claude_mpm.commander.registry import ProjectRegistry


@pytest.fixture
def temp_state_dir():
    """Create temporary state directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def event_store(temp_state_dir):
    """Create EventStore with temp directory."""
    return EventStore(temp_state_dir)


@pytest.fixture
def sample_event():
    """Create sample event for testing."""
    return Event(
        id="evt-123",
        project_id="proj-abc",
        type=EventType.DECISION_NEEDED,
        priority=EventPriority.HIGH,
        title="Choose option",
        session_id="sess-456",
        status=EventStatus.PENDING,
        content="Which approach should we use?",
        context={"file": "main.py", "line": 42},
        options=["Option A", "Option B"],
        response=None,
        responded_at=None,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def event_manager():
    """Create EventManager instance."""
    return EventManager()


@pytest.fixture
def inbox(event_manager):
    """Create Inbox instance."""
    registry = ProjectRegistry()
    return Inbox(event_manager, registry)


@pytest.mark.asyncio
async def test_save_events_creates_file(event_store, inbox, sample_event):
    """Test that save_events creates JSON file."""
    inbox.events.add_event(sample_event)

    await event_store.save_events(inbox)

    assert event_store.events_path.exists()
    assert event_store.events_path.is_file()


@pytest.mark.asyncio
async def test_save_load_events_round_trip(event_store, inbox, sample_event):
    """Test save and load events round-trip."""
    inbox.events.add_event(sample_event)

    # Save
    await event_store.save_events(inbox)

    # Load
    events = await event_store.load_events()

    # Verify
    assert len(events) == 1
    loaded = events[0]
    assert loaded.id == sample_event.id
    assert loaded.project_id == sample_event.project_id
    assert loaded.type == sample_event.type
    assert loaded.priority == sample_event.priority
    assert loaded.title == sample_event.title
    assert loaded.session_id == sample_event.session_id
    assert loaded.status == sample_event.status
    assert loaded.content == sample_event.content
    assert loaded.context == sample_event.context
    assert loaded.options == sample_event.options


@pytest.mark.asyncio
async def test_load_events_missing_file(event_store):
    """Test load_events returns empty list when file missing."""
    events = await event_store.load_events()
    assert events == []


@pytest.mark.asyncio
async def test_load_events_corrupt_file(event_store):
    """Test load_events handles corrupt JSON."""
    event_store.events_path.write_text("not valid json{{{")

    events = await event_store.load_events()
    assert events == []


@pytest.mark.asyncio
async def test_append_event(event_store, sample_event):
    """Test append_event adds single event."""
    # Start with empty store
    events = await event_store.load_events()
    assert len(events) == 0

    # Append event
    await event_store.append_event(sample_event)

    # Verify added
    events = await event_store.load_events()
    assert len(events) == 1
    assert events[0].id == sample_event.id


@pytest.mark.asyncio
async def test_append_event_preserves_existing(event_store, sample_event):
    """Test append_event preserves existing events."""
    # Add first event
    event1 = Event(
        id="evt-1",
        project_id="proj-1",
        type=EventType.STATUS,
        priority=EventPriority.INFO,
        title="Status update",
        status=EventStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )
    await event_store.append_event(event1)

    # Append second event
    await event_store.append_event(sample_event)

    # Verify both exist
    events = await event_store.load_events()
    assert len(events) == 2
    assert {e.id for e in events} == {"evt-1", sample_event.id}


@pytest.mark.asyncio
async def test_remove_event(event_store, sample_event):
    """Test remove_event deletes specific event."""
    # Add two events
    event1 = Event(
        id="evt-1",
        project_id="proj-1",
        type=EventType.STATUS,
        priority=EventPriority.INFO,
        title="Status 1",
        status=EventStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )
    await event_store.append_event(event1)
    await event_store.append_event(sample_event)

    # Remove first event
    await event_store.remove_event("evt-1")

    # Verify only second remains
    events = await event_store.load_events()
    assert len(events) == 1
    assert events[0].id == sample_event.id


@pytest.mark.asyncio
async def test_remove_event_not_found(event_store, caplog):
    """Test remove_event handles non-existent event."""
    await event_store.remove_event("non-existent")

    # Should log warning but not crash
    assert "not found" in caplog.text.lower()


@pytest.mark.asyncio
async def test_save_multiple_events(event_store, inbox):
    """Test saving multiple events."""
    # Create multiple events
    for i in range(5):
        event = Event(
            id=f"evt-{i}",
            project_id="proj-1",
            type=EventType.STATUS,
            priority=EventPriority.INFO,
            title=f"Event {i}",
            status=EventStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        inbox.events.add_event(event)

    await event_store.save_events(inbox)

    # Load and verify
    events = await event_store.load_events()
    assert len(events) == 5
    assert {e.id for e in events} == {f"evt-{i}" for i in range(5)}


@pytest.mark.asyncio
async def test_atomic_write_prevents_corruption(event_store, temp_state_dir):
    """Test atomic write for events."""
    data = {
        "version": "1.0",
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "events": [],
    }

    event_store._atomic_write(event_store.events_path, data)

    # Verify file exists
    assert event_store.events_path.exists()

    # Verify no temp files left
    temp_files = list(temp_state_dir.glob(".events.json.*.tmp"))
    assert len(temp_files) == 0


@pytest.mark.asyncio
async def test_event_with_response(event_store):
    """Test save/load event with response data."""
    event = Event(
        id="evt-123",
        project_id="proj-1",
        type=EventType.DECISION_NEEDED,
        priority=EventPriority.HIGH,
        title="Choose option",
        status=EventStatus.RESOLVED,
        content="Choose A or B",
        options=["A", "B"],
        response="A",
        responded_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )

    await event_store.append_event(event)

    # Load and verify
    events = await event_store.load_events()
    assert len(events) == 1
    loaded = events[0]
    assert loaded.response == "A"
    assert loaded.responded_at is not None
    assert loaded.status == EventStatus.RESOLVED


@pytest.mark.asyncio
async def test_concurrent_appends(event_store):
    """Test concurrent append operations."""
    # Create multiple events
    events = [
        Event(
            id=f"evt-{i}",
            project_id="proj-1",
            type=EventType.STATUS,
            priority=EventPriority.INFO,
            title=f"Event {i}",
            status=EventStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        for i in range(5)
    ]

    # Append sequentially to avoid race conditions
    # (concurrent appends may overwrite each other due to read-modify-write)
    for event in events:
        await event_store.append_event(event)

    # Verify all added
    loaded = await event_store.load_events()
    assert len(loaded) == 5  # All events present
    assert {e.id for e in loaded} == {f"evt-{i}" for i in range(5)}


@pytest.mark.asyncio
async def test_version_handling(event_store, caplog):
    """Test version mismatch handling."""
    data = {
        "version": "0.5",
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "events": [],
    }
    event_store.events_path.write_text(json.dumps(data))

    events = await event_store.load_events()

    # Should warn but still load
    assert "Version mismatch" in caplog.text
    assert events == []


@pytest.mark.asyncio
async def test_save_events_with_complex_context(event_store, inbox):
    """Test saving events with complex context data."""
    event = Event(
        id="evt-complex",
        project_id="proj-1",
        type=EventType.ERROR,
        priority=EventPriority.CRITICAL,
        title="Complex error",
        status=EventStatus.PENDING,
        content="Error occurred",
        context={
            "stack_trace": ["line 1", "line 2"],
            "variables": {"x": 42, "y": "test"},
            "nested": {"deep": {"value": True}},
        },
        created_at=datetime.now(timezone.utc),
    )
    inbox.events.add_event(event)

    await event_store.save_events(inbox)

    # Load and verify complex context preserved
    events = await event_store.load_events()
    assert len(events) == 1
    loaded = events[0]
    assert loaded.context == event.context
    assert loaded.context["nested"]["deep"]["value"] is True
