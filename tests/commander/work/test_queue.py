"""Tests for work queue."""

import pytest

from claude_mpm.commander.models.work import WorkPriority, WorkState
from claude_mpm.commander.work.queue import WorkQueue


class TestWorkQueue:
    """Test WorkQueue operations."""

    @pytest.fixture
    def queue(self):
        """Create a work queue for testing."""
        return WorkQueue("proj-123")

    def test_init(self, queue):
        """Test queue initialization."""
        assert queue.project_id == "proj-123"
        assert queue.pending_count == 0
        assert queue.completed_ids == set()

    def test_add_work(self, queue):
        """Test adding work to queue."""
        work = queue.add("Implement feature X")

        assert work.id.startswith("work-")
        assert work.project_id == "proj-123"
        assert work.content == "Implement feature X"
        assert work.state == WorkState.QUEUED
        assert work.priority == WorkPriority.MEDIUM

    def test_add_work_with_priority(self, queue):
        """Test adding work with custom priority."""
        work = queue.add("Fix critical bug", priority=WorkPriority.CRITICAL)

        assert work.priority == WorkPriority.CRITICAL
        assert work.state == WorkState.QUEUED

    def test_add_work_with_dependencies(self, queue):
        """Test adding work with dependencies."""
        work = queue.add("Task B", depends_on=["work-a"])

        assert work.depends_on == ["work-a"]

    def test_get_next_empty_queue(self, queue):
        """Test get_next on empty queue."""
        assert queue.get_next() is None

    def test_get_next_single_item(self, queue):
        """Test get_next with single item."""
        work1 = queue.add("Task 1")
        next_work = queue.get_next()

        assert next_work.id == work1.id

    def test_get_next_priority_order(self, queue):
        """Test get_next respects priority order."""
        work_low = queue.add("Low priority", priority=WorkPriority.LOW)
        work_high = queue.add("High priority", priority=WorkPriority.HIGH)
        work_medium = queue.add("Medium priority", priority=WorkPriority.MEDIUM)

        # Should get high priority first
        next_work = queue.get_next()
        assert next_work.id == work_high.id

    def test_get_next_fifo_within_priority(self, queue):
        """Test get_next is FIFO within same priority."""
        work1 = queue.add("First task", priority=WorkPriority.HIGH)
        work2 = queue.add("Second task", priority=WorkPriority.HIGH)

        # Should get older item first
        next_work = queue.get_next()
        assert next_work.id == work1.id

    def test_get_next_blocked_by_dependencies(self, queue):
        """Test get_next skips items with unsatisfied dependencies."""
        work1 = queue.add("Task 1")
        work2 = queue.add("Task 2", depends_on=[work1.id])

        # work2 depends on work1, so should get work1 first
        next_work = queue.get_next()
        assert next_work.id == work1.id

        # Mark work1 complete, now work2 should be available
        queue.start(work1.id)
        queue.complete(work1.id)
        next_work = queue.get_next()
        assert next_work.id == work2.id

    def test_start_work(self, queue):
        """Test starting work item."""
        work = queue.add("Task")

        assert queue.start(work.id)
        assert work.state == WorkState.IN_PROGRESS
        assert work.started_at is not None

    def test_start_nonexistent_work(self, queue):
        """Test starting nonexistent work fails."""
        assert not queue.start("nonexistent-id")

    def test_start_work_wrong_state(self, queue):
        """Test starting work in wrong state fails."""
        work = queue.add("Task")
        queue.start(work.id)  # Move to IN_PROGRESS
        queue.complete(work.id)  # Move to COMPLETED

        assert not queue.start(work.id)

    def test_complete_work(self, queue):
        """Test completing work item."""
        work = queue.add("Task")
        queue.start(work.id)

        assert queue.complete(work.id, result="Success")
        assert work.state == WorkState.COMPLETED
        assert work.completed_at is not None
        assert work.result == "Success"

    def test_complete_work_no_result(self, queue):
        """Test completing work without result message."""
        work = queue.add("Task")
        queue.start(work.id)

        assert queue.complete(work.id)
        assert work.state == WorkState.COMPLETED
        assert work.result is None

    def test_fail_work(self, queue):
        """Test failing work item."""
        work = queue.add("Task")
        queue.start(work.id)

        assert queue.fail(work.id, "Timeout error")
        assert work.state == WorkState.FAILED
        assert work.completed_at is not None
        assert work.error == "Timeout error"

    def test_block_work(self, queue):
        """Test blocking work item."""
        work = queue.add("Task")
        queue.start(work.id)

        assert queue.block(work.id, "Waiting for approval")
        assert work.state == WorkState.BLOCKED
        assert work.metadata["block_reason"] == "Waiting for approval"

    def test_unblock_work(self, queue):
        """Test unblocking work item."""
        work = queue.add("Task")
        queue.start(work.id)
        queue.block(work.id, "Waiting")

        assert queue.unblock(work.id)
        assert work.state == WorkState.IN_PROGRESS
        assert "block_reason" not in work.metadata

    def test_cancel_pending_work(self, queue):
        """Test cancelling pending work."""
        work = queue.add("Task")

        assert queue.cancel(work.id)
        assert work.state == WorkState.CANCELLED
        assert work.completed_at is not None

    def test_cancel_in_progress_work_fails(self, queue):
        """Test cancelling in-progress work fails."""
        work = queue.add("Task")
        queue.start(work.id)

        assert not queue.cancel(work.id)

    def test_get_work_by_id(self, queue):
        """Test getting work item by ID."""
        work1 = queue.add("Task 1")
        work2 = queue.add("Task 2")

        retrieved = queue.get(work1.id)
        assert retrieved.id == work1.id
        assert retrieved.content == "Task 1"

    def test_get_nonexistent_work(self, queue):
        """Test getting nonexistent work returns None."""
        assert queue.get("nonexistent-id") is None

    def test_list_all_work(self, queue):
        """Test listing all work items."""
        work1 = queue.add("Task 1")
        work2 = queue.add("Task 2")
        work3 = queue.add("Task 3")

        all_items = queue.list()
        assert len(all_items) == 3
        assert {w.id for w in all_items} == {work1.id, work2.id, work3.id}

    def test_list_work_by_state(self, queue):
        """Test listing work filtered by state."""
        work1 = queue.add("Task 1")
        work2 = queue.add("Task 2")
        work3 = queue.add("Task 3")

        queue.start(work2.id)
        queue.start(work3.id)
        queue.complete(work3.id)

        # List only queued items
        queued = queue.list(WorkState.QUEUED)
        assert len(queued) == 1
        assert queued[0].id == work1.id

        # List only in-progress items
        in_progress = queue.list(WorkState.IN_PROGRESS)
        assert len(in_progress) == 1
        assert in_progress[0].id == work2.id

    def test_pending_count(self, queue):
        """Test pending count property."""
        assert queue.pending_count == 0

        queue.add("Task 1")
        queue.add("Task 2")
        assert queue.pending_count == 2

        work3 = queue.add("Task 3")
        queue.start(work3.id)
        assert queue.pending_count == 2  # Still 2 QUEUED items

        queue.complete(work3.id)
        assert queue.pending_count == 2  # Still 2 QUEUED items

    def test_completed_ids(self, queue):
        """Test completed_ids property."""
        assert queue.completed_ids == set()

        work1 = queue.add("Task 1")
        work2 = queue.add("Task 2")
        work3 = queue.add("Task 3")

        queue.start(work1.id)
        queue.complete(work1.id)

        assert queue.completed_ids == {work1.id}

        queue.start(work2.id)
        queue.complete(work2.id)

        assert queue.completed_ids == {work1.id, work2.id}

    def test_load_items(self, queue):
        """Test loading items into queue."""
        from claude_mpm.commander.models.work import WorkItem

        items = [
            WorkItem(id="work-1", project_id="proj-123", content="Task 1"),
            WorkItem(id="work-2", project_id="proj-123", content="Task 2"),
        ]

        queue.load_items(items)

        assert len(queue.list()) == 2
        assert queue.get("work-1").content == "Task 1"
        assert queue.get("work-2").content == "Task 2"

    def test_load_items_filters_wrong_project(self, queue):
        """Test load_items filters items from wrong project."""
        from claude_mpm.commander.models.work import WorkItem

        items = [
            WorkItem(id="work-1", project_id="proj-123", content="Task 1"),
            WorkItem(
                id="work-2", project_id="proj-999", content="Task 2"
            ),  # Wrong project
        ]

        queue.load_items(items)

        assert len(queue.list()) == 1
        assert queue.get("work-1") is not None
        assert queue.get("work-2") is None
