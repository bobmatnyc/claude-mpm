"""Tests for work item models."""

from datetime import datetime, timezone

import pytest

from claude_mpm.commander.models.work import WorkItem, WorkPriority, WorkState


class TestWorkPriority:
    """Test WorkPriority enum comparisons."""

    def test_priority_comparison(self):
        """Test priority level comparisons."""
        assert WorkPriority.CRITICAL > WorkPriority.HIGH
        assert WorkPriority.HIGH > WorkPriority.MEDIUM
        assert WorkPriority.MEDIUM > WorkPriority.LOW

        assert WorkPriority.LOW < WorkPriority.CRITICAL
        assert WorkPriority.MEDIUM <= WorkPriority.HIGH
        assert WorkPriority.HIGH >= WorkPriority.HIGH

    def test_priority_values(self):
        """Test priority integer values."""
        assert WorkPriority.CRITICAL.value == 4
        assert WorkPriority.HIGH.value == 3
        assert WorkPriority.MEDIUM.value == 2
        assert WorkPriority.LOW.value == 1


class TestWorkItem:
    """Test WorkItem data model."""

    @pytest.fixture
    def basic_work_item(self):
        """Create a basic work item for testing."""
        return WorkItem(
            id="work-123",
            project_id="proj-abc",
            content="Implement feature X",
        )

    def test_create_work_item_defaults(self, basic_work_item):
        """Test work item creation with default values."""
        assert basic_work_item.id == "work-123"
        assert basic_work_item.project_id == "proj-abc"
        assert basic_work_item.content == "Implement feature X"
        assert basic_work_item.state == WorkState.PENDING
        assert basic_work_item.priority == WorkPriority.MEDIUM
        assert isinstance(basic_work_item.created_at, datetime)
        assert basic_work_item.started_at is None
        assert basic_work_item.completed_at is None
        assert basic_work_item.result is None
        assert basic_work_item.error is None
        assert basic_work_item.depends_on == []
        assert basic_work_item.metadata == {}

    def test_create_work_item_custom(self):
        """Test work item creation with custom values."""
        work = WorkItem(
            id="work-456",
            project_id="proj-xyz",
            content="Fix bug",
            state=WorkState.QUEUED,
            priority=WorkPriority.HIGH,
            depends_on=["work-123"],
        )

        assert work.state == WorkState.QUEUED
        assert work.priority == WorkPriority.HIGH
        assert work.depends_on == ["work-123"]

    def test_can_start_no_dependencies(self, basic_work_item):
        """Test can_start with no dependencies."""
        assert basic_work_item.can_start(set())
        assert basic_work_item.can_start({"work-000"})

    def test_can_start_with_dependencies(self):
        """Test can_start with dependencies."""
        work = WorkItem(
            id="work-2",
            project_id="proj-1",
            content="Task",
            depends_on=["work-1"],
        )

        # Cannot start without dependency completed
        assert not work.can_start(set())
        assert not work.can_start({"work-0"})

        # Can start when dependency completed
        assert work.can_start({"work-1"})
        assert work.can_start({"work-1", "work-0"})

    def test_can_start_multiple_dependencies(self):
        """Test can_start with multiple dependencies."""
        work = WorkItem(
            id="work-3",
            project_id="proj-1",
            content="Task",
            depends_on=["work-1", "work-2"],
        )

        # Cannot start with partial dependencies
        assert not work.can_start(set())
        assert not work.can_start({"work-1"})
        assert not work.can_start({"work-2"})

        # Can start when all dependencies completed
        assert work.can_start({"work-1", "work-2"})
        assert work.can_start({"work-1", "work-2", "work-0"})

    def test_to_dict(self, basic_work_item):
        """Test serialization to dict."""
        data = basic_work_item.to_dict()

        assert data["id"] == "work-123"
        assert data["project_id"] == "proj-abc"
        assert data["content"] == "Implement feature X"
        assert data["state"] == "pending"
        assert data["priority"] == 2
        assert isinstance(data["created_at"], str)
        assert data["started_at"] is None
        assert data["completed_at"] is None
        assert data["result"] is None
        assert data["error"] is None
        assert data["depends_on"] == []
        assert data["metadata"] == {}

    def test_to_dict_with_timestamps(self):
        """Test serialization with all timestamps set."""
        now = datetime.now(timezone.utc)
        work = WorkItem(
            id="work-123",
            project_id="proj-abc",
            content="Task",
            state=WorkState.COMPLETED,
            created_at=now,
            started_at=now,
            completed_at=now,
        )

        data = work.to_dict()
        assert data["created_at"] == now.isoformat()
        assert data["started_at"] == now.isoformat()
        assert data["completed_at"] == now.isoformat()

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "id": "work-789",
            "project_id": "proj-xyz",
            "content": "Test task",
            "state": "queued",
            "priority": 3,
            "depends_on": ["work-456"],
            "metadata": {"key": "value"},
        }

        work = WorkItem.from_dict(data)

        assert work.id == "work-789"
        assert work.project_id == "proj-xyz"
        assert work.content == "Test task"
        assert work.state == WorkState.QUEUED
        assert work.priority == WorkPriority.HIGH
        assert work.depends_on == ["work-456"]
        assert work.metadata == {"key": "value"}

    def test_from_dict_with_timestamps(self):
        """Test deserialization with timestamp strings."""
        now = datetime.now(timezone.utc)
        data = {
            "id": "work-123",
            "project_id": "proj-abc",
            "content": "Task",
            "state": "completed",
            "priority": 2,
            "created_at": now.isoformat(),
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
        }

        work = WorkItem.from_dict(data)

        assert isinstance(work.created_at, datetime)
        assert isinstance(work.started_at, datetime)
        assert isinstance(work.completed_at, datetime)

    def test_from_dict_missing_state(self):
        """Test from_dict raises on missing state."""
        data = {
            "id": "work-123",
            "project_id": "proj-abc",
            "content": "Task",
            "priority": 2,
        }

        with pytest.raises(ValueError, match="Invalid or missing state"):
            WorkItem.from_dict(data)

    def test_from_dict_invalid_state(self):
        """Test from_dict raises on invalid state."""
        data = {
            "id": "work-123",
            "project_id": "proj-abc",
            "content": "Task",
            "state": "invalid_state",
            "priority": 2,
        }

        with pytest.raises(ValueError, match="Invalid or missing state"):
            WorkItem.from_dict(data)

    def test_from_dict_priority_as_string(self):
        """Test from_dict handles priority as string."""
        data = {
            "id": "work-123",
            "project_id": "proj-abc",
            "content": "Task",
            "state": "pending",
            "priority": "HIGH",
        }

        work = WorkItem.from_dict(data)
        assert work.priority == WorkPriority.HIGH

    def test_roundtrip_serialization(self, basic_work_item):
        """Test to_dict -> from_dict roundtrip."""
        data = basic_work_item.to_dict()
        restored = WorkItem.from_dict(data)

        assert restored.id == basic_work_item.id
        assert restored.project_id == basic_work_item.project_id
        assert restored.content == basic_work_item.content
        assert restored.state == basic_work_item.state
        assert restored.priority == basic_work_item.priority
        assert restored.depends_on == basic_work_item.depends_on
