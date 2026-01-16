"""Tests for work executor."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_mpm.commander.models.work import WorkPriority, WorkState
from claude_mpm.commander.work.executor import WorkExecutor
from claude_mpm.commander.work.queue import WorkQueue


class TestWorkExecutor:
    """Test WorkExecutor operations."""

    @pytest.fixture
    def mock_runtime(self):
        """Create mock RuntimeExecutor."""
        return MagicMock()

    @pytest.fixture
    def queue(self):
        """Create work queue."""
        return WorkQueue("proj-123")

    @pytest.fixture
    def executor(self, mock_runtime, queue):
        """Create work executor."""
        return WorkExecutor(mock_runtime, queue)

    def test_init(self, mock_runtime, queue):
        """Test executor initialization."""
        executor = WorkExecutor(mock_runtime, queue)

        assert executor.runtime is mock_runtime
        assert executor.queue is queue

    def test_init_requires_runtime(self, queue):
        """Test initialization requires runtime."""
        with pytest.raises(ValueError, match="Runtime cannot be None"):
            WorkExecutor(None, queue)

    def test_init_requires_queue(self, mock_runtime):
        """Test initialization requires queue."""
        with pytest.raises(ValueError, match="Queue cannot be None"):
            WorkExecutor(mock_runtime, None)

    @pytest.mark.asyncio
    async def test_execute_next_empty_queue(self, executor):
        """Test execute_next with empty queue."""
        result = await executor.execute_next()

        assert result is False

    @pytest.mark.asyncio
    async def test_execute_next_with_work(self, executor, queue):
        """Test execute_next with work available."""
        queue.add("Task 1")

        result = await executor.execute_next()

        assert result is True

    @pytest.mark.asyncio
    async def test_execute_marks_work_in_progress(self, executor, queue):
        """Test execute marks work as IN_PROGRESS."""
        work = queue.add("Task 1")

        await executor.execute(work)

        assert work.state == WorkState.IN_PROGRESS
        assert work.started_at is not None

    @pytest.mark.asyncio
    async def test_execute_sets_metadata(self, executor, queue):
        """Test execute sets execution metadata."""
        work = queue.add("Task 1")

        await executor.execute(work)

        assert work.metadata.get("execution_started") is True

    @pytest.mark.asyncio
    async def test_handle_completion(self, executor, queue):
        """Test handle_completion callback."""
        work = queue.add("Task 1")
        queue.start(work.id)

        await executor.handle_completion(work.id, "Success")

        assert work.state == WorkState.COMPLETED
        assert work.result == "Success"
        assert work.completed_at is not None

    @pytest.mark.asyncio
    async def test_handle_completion_no_result(self, executor, queue):
        """Test handle_completion without result message."""
        work = queue.add("Task 1")
        queue.start(work.id)

        await executor.handle_completion(work.id)

        assert work.state == WorkState.COMPLETED
        assert work.result is None

    @pytest.mark.asyncio
    async def test_handle_failure(self, executor, queue):
        """Test handle_failure callback."""
        work = queue.add("Task 1")
        queue.start(work.id)

        await executor.handle_failure(work.id, "Execution timeout")

        assert work.state == WorkState.FAILED
        assert work.error == "Execution timeout"
        assert work.completed_at is not None

    @pytest.mark.asyncio
    async def test_handle_block(self, executor, queue):
        """Test handle_block callback."""
        work = queue.add("Task 1")
        queue.start(work.id)

        await executor.handle_block(work.id, "Waiting for approval")

        assert work.state == WorkState.BLOCKED
        assert work.metadata["block_reason"] == "Waiting for approval"

    @pytest.mark.asyncio
    async def test_handle_unblock(self, executor, queue):
        """Test handle_unblock callback."""
        work = queue.add("Task 1")
        queue.start(work.id)
        queue.block(work.id, "Waiting")

        await executor.handle_unblock(work.id)

        assert work.state == WorkState.IN_PROGRESS
        assert "block_reason" not in work.metadata

    @pytest.mark.asyncio
    async def test_execute_next_processes_highest_priority(self, executor, queue):
        """Test execute_next processes highest priority work."""
        work_low = queue.add("Low priority", priority=WorkPriority.LOW)
        work_high = queue.add("High priority", priority=WorkPriority.HIGH)

        await executor.execute_next()

        # High priority should be started first
        assert work_high.state == WorkState.IN_PROGRESS
        assert work_low.state == WorkState.QUEUED

    @pytest.mark.asyncio
    async def test_execute_next_respects_dependencies(self, executor, queue):
        """Test execute_next respects dependencies."""
        work1 = queue.add("Task 1")
        work2 = queue.add("Task 2", depends_on=[work1.id])

        # First execution should process work1
        result = await executor.execute_next()
        assert result is True
        assert work1.state == WorkState.IN_PROGRESS
        assert work2.state == WorkState.QUEUED

        # Complete work1
        await executor.handle_completion(work1.id)

        # Second execution should process work2
        result = await executor.execute_next()
        assert result is True
        assert work2.state == WorkState.IN_PROGRESS
