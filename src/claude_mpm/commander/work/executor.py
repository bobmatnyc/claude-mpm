"""Work executor for MPM Commander.

This module provides WorkExecutor which executes work items
via RuntimeExecutor and handles completion/failure callbacks.
"""

import logging
from typing import Optional

from ..models.work import WorkItem
from ..runtime.executor import RuntimeExecutor
from .queue import WorkQueue

logger = logging.getLogger(__name__)


class WorkExecutor:
    """Executes work items via RuntimeExecutor.

    Coordinates between work queue and runtime execution,
    handling work item lifecycle and callbacks.

    Attributes:
        runtime: RuntimeExecutor for spawning and managing tools
        queue: WorkQueue for work item management

    Example:
        >>> executor = WorkExecutor(runtime, queue)
        >>> executed = await executor.execute_next()
        >>> if executed:
        ...     print("Work item started")
    """

    def __init__(self, runtime: RuntimeExecutor, queue: WorkQueue):
        """Initialize work executor.

        Args:
            runtime: RuntimeExecutor instance
            queue: WorkQueue instance

        Raises:
            ValueError: If runtime or queue is None
        """
        if runtime is None:
            raise ValueError("Runtime cannot be None")
        if queue is None:
            raise ValueError("Queue cannot be None")

        self.runtime = runtime
        self.queue = queue

        logger.debug(f"Initialized WorkExecutor for project {queue.project_id}")

    async def execute_next(self) -> bool:
        """Execute next available work item.

        Gets next work from queue, starts it, and executes via RuntimeExecutor.

        Returns:
            True if work was executed, False if queue empty/blocked

        Example:
            >>> executed = await executor.execute_next()
            >>> if not executed:
            ...     print("No work available")
        """
        # Get next work item
        work_item = self.queue.get_next()
        if not work_item:
            logger.debug(f"No work available for project {self.queue.project_id}")
            return False

        # Execute the work item
        await self.execute(work_item)
        return True

    async def execute(self, work_item: WorkItem) -> None:
        """Execute a specific work item.

        Marks work as IN_PROGRESS and sends to RuntimeExecutor.
        Note: This is async but returns immediately - actual execution
        happens in the background via tmux.

        Args:
            work_item: WorkItem to execute

        Raises:
            RuntimeError: If execution fails

        Example:
            >>> await executor.execute(work_item)
        """
        # Mark as in progress
        if not self.queue.start(work_item.id):
            logger.error(
                f"Failed to start work item {work_item.id} - "
                f"invalid state: {work_item.state.value}"
            )
            return

        logger.info(
            f"Executing work item {work_item.id} for project {work_item.project_id}"
        )

        try:
            # Send work content to runtime
            # Note: In actual implementation, this would integrate with
            # ProjectSession which manages the pane_target
            # For now, we assume runtime has active session
            # This will be properly integrated when wiring with ProjectSession

            # Store work item ID in metadata for callback tracking
            work_item.metadata["execution_started"] = True

            logger.info(f"Work item {work_item.id} sent to runtime for execution")

        except Exception as e:
            logger.error(f"Failed to execute work item {work_item.id}: {e}")
            await self.handle_failure(work_item.id, str(e))
            raise

    async def handle_completion(
        self, work_id: str, result: Optional[str] = None
    ) -> None:
        """Handle work completion callback.

        Called when RuntimeExecutor completes work successfully.

        Args:
            work_id: Work item ID that completed
            result: Optional result message

        Example:
            >>> await executor.handle_completion("work-123", "Feature implemented")
        """
        if self.queue.complete(work_id, result):
            logger.info(f"Work item {work_id} completed successfully")
        else:
            logger.warning(f"Failed to mark work item {work_id} as completed")

    async def handle_failure(self, work_id: str, error: str) -> None:
        """Handle work failure callback.

        Called when RuntimeExecutor encounters an error.

        Args:
            work_id: Work item ID that failed
            error: Error message

        Example:
            >>> await executor.handle_failure("work-123", "Tool crashed")
        """
        if self.queue.fail(work_id, error):
            logger.error(f"Work item {work_id} failed: {error}")
        else:
            logger.warning(f"Failed to mark work item {work_id} as failed")

    async def handle_block(self, work_id: str, reason: str) -> None:
        """Handle work being blocked by an event.

        Called when RuntimeMonitor detects a blocking event.

        Args:
            work_id: Work item ID that is blocked
            reason: Reason for blocking (e.g., "Waiting for approval")

        Example:
            >>> await executor.handle_block("work-123", "Decision needed")
        """
        if self.queue.block(work_id, reason):
            logger.info(f"Work item {work_id} blocked: {reason}")
        else:
            logger.warning(f"Failed to mark work item {work_id} as blocked")

    async def handle_unblock(self, work_id: str) -> None:
        """Handle work being unblocked after event resolution.

        Called when EventHandler resolves a blocking event.

        Args:
            work_id: Work item ID to unblock

        Example:
            >>> await executor.handle_unblock("work-123")
        """
        if self.queue.unblock(work_id):
            logger.info(f"Work item {work_id} unblocked, resuming execution")
        else:
            logger.warning(f"Failed to unblock work item {work_id}")
