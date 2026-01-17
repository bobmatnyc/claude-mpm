"""Integration tests for BlockManager with RuntimeMonitor and EventHandler."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.commander.core.block_manager import BlockManager
from claude_mpm.commander.events.manager import EventManager
from claude_mpm.commander.models.events import Event, EventType
from claude_mpm.commander.models.work import WorkItem, WorkPriority, WorkState
from claude_mpm.commander.runtime.executor import RuntimeExecutor
from claude_mpm.commander.runtime.monitor import RuntimeMonitor
from claude_mpm.commander.work.executor import WorkExecutor
from claude_mpm.commander.work.queue import WorkQueue
from claude_mpm.commander.workflow.event_handler import EventHandler


@pytest.fixture
def event_manager():
    """Create EventManager instance."""
    return EventManager()


@pytest.fixture
def work_queue():
    """Create WorkQueue instance."""
    return WorkQueue("test-project")


@pytest.fixture
def mock_orchestrator():
    """Create mock TmuxOrchestrator."""
    mock = MagicMock()
    mock.capture_output.return_value = ""
    return mock


@pytest.fixture
def runtime_executor(mock_orchestrator):
    """Create RuntimeExecutor instance."""
    return RuntimeExecutor(mock_orchestrator)


@pytest.fixture
def work_executor(runtime_executor, work_queue):
    """Create WorkExecutor instance."""
    return WorkExecutor(runtime=runtime_executor, queue=work_queue)


@pytest.fixture
def block_manager(event_manager, work_queue, work_executor):
    """Create BlockManager instance."""
    work_queues = {"test-project": work_queue}
    work_executors = {"test-project": work_executor}
    return BlockManager(
        event_manager=event_manager,
        work_queues=work_queues,
        work_executors=work_executors,
    )


class TestBlockManagerIntegration:
    """Integration tests for BlockManager with other components."""

    @pytest.mark.asyncio
    async def test_block_manager_blocks_work_on_blocking_event(
        self, event_manager, work_queue, work_executor, block_manager
    ):
        """Test BlockManager blocks work when blocking event detected."""
        # Add work item to queue
        work_item = work_queue.add(content="Test task", priority=WorkPriority.MEDIUM)
        work_queue.start(work_item.id)

        # Verify work is in progress
        assert work_item.state == WorkState.IN_PROGRESS

        # Create blocking event
        event = event_manager.create(
            project_id="test-project",
            session_id=None,
            event_type=EventType.ERROR,
            title="Critical error",
            content="Something went wrong",
        )

        # Verify event is blocking
        assert event.is_blocking

        # Block work via BlockManager
        blocked_work_ids = await block_manager.check_and_block(event)

        # Verify work was blocked
        assert work_item.id in blocked_work_ids
        assert work_item.state == WorkState.BLOCKED

    @pytest.mark.asyncio
    async def test_block_manager_unblocks_work_on_event_resolution(
        self, event_manager, work_queue, work_executor, block_manager
    ):
        """Test BlockManager unblocks work when event resolved."""
        # Add work item to queue
        work_item = work_queue.add(content="Test task", priority=WorkPriority.MEDIUM)
        work_queue.start(work_item.id)

        # Create blocking event
        event = event_manager.create(
            project_id="test-project",
            session_id=None,
            event_type=EventType.ERROR,
            title="Critical error",
            content="Something went wrong",
        )

        # Block work
        await block_manager.check_and_block(event)
        assert work_item.state == WorkState.BLOCKED

        # Unblock work via BlockManager
        unblocked_work_ids = await block_manager.check_and_unblock(event.id)

        # Verify work was unblocked
        assert work_item.id in unblocked_work_ids
        assert work_item.state == WorkState.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_runtime_monitor_with_block_manager(
        self, event_manager, work_queue, work_executor, block_manager, mock_orchestrator
    ):
        """Test RuntimeMonitor integrates with BlockManager."""
        from claude_mpm.commander.parsing.output_parser import OutputParser

        # Create parser and monitor with BlockManager
        parser = OutputParser(event_manager)
        monitor = RuntimeMonitor(
            orchestrator=mock_orchestrator,
            parser=parser,
            event_manager=event_manager,
            block_manager=block_manager,
        )

        # Verify BlockManager is set
        assert monitor.block_manager is block_manager

    @pytest.mark.asyncio
    async def test_event_handler_with_block_manager(self, event_manager, block_manager):
        """Test EventHandler integrates with BlockManager."""
        from claude_mpm.commander.inbox import Inbox
        from claude_mpm.commander.registry import ProjectRegistry

        # Create inbox and event handler with BlockManager
        registry = ProjectRegistry()
        inbox = Inbox(event_manager, registry)
        session_manager = {}

        event_handler = EventHandler(
            inbox=inbox,
            session_manager=session_manager,
            block_manager=block_manager,
        )

        # Verify BlockManager is set
        assert event_handler.block_manager is block_manager

    @pytest.mark.asyncio
    async def test_end_to_end_blocking_workflow(
        self, event_manager, work_queue, work_executor, block_manager
    ):
        """Test complete blocking/unblocking workflow."""
        # Add work item to queue
        work_item = work_queue.add(content="Test task", priority=WorkPriority.MEDIUM)
        work_queue.start(work_item.id)
        assert work_item.state == WorkState.IN_PROGRESS

        # Create blocking event (simulating RuntimeMonitor detection)
        event = event_manager.create(
            project_id="test-project",
            session_id=None,
            event_type=EventType.APPROVAL,
            title="Need permission",
            content="Can I proceed?",
        )

        # Block work (simulating RuntimeMonitor calling BlockManager)
        blocked_work_ids = await block_manager.check_and_block(event)
        assert work_item.id in blocked_work_ids
        assert work_item.state == WorkState.BLOCKED

        # Resolve event (simulating user response)
        event_manager.respond(event.id, "Yes, proceed")

        # Unblock work (simulating EventHandler calling BlockManager)
        unblocked_work_ids = await block_manager.check_and_unblock(event.id)
        assert work_item.id in unblocked_work_ids
        assert work_item.state == WorkState.IN_PROGRESS

        # Verify event-work mapping is cleared
        assert len(block_manager.get_blocked_work(event.id)) == 0
