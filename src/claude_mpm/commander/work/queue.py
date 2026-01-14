"""Work queue management for MPM Commander.

This module provides WorkQueue for managing work items within a project,
including priority-based execution and dependency resolution.
"""

import logging
import uuid
from typing import List, Optional

from ..models.work import WorkItem, WorkPriority, WorkState

logger = logging.getLogger(__name__)


class WorkQueue:
    """Manages work items for a project.

    Provides operations for adding, retrieving, and updating work items
    with support for priority-based execution and linear dependencies.

    Attributes:
        project_id: ID of the project this queue belongs to
        _items: Internal storage of work items by ID

    Example:
        >>> queue = WorkQueue("proj-123")
        >>> work = queue.add("Implement feature X", priority=WorkPriority.HIGH)
        >>> next_work = queue.get_next()
        >>> queue.start(next_work.id)
        >>> queue.complete(next_work.id, "Feature implemented")
    """

    def __init__(self, project_id: str):
        """Initialize work queue for a project.

        Args:
            project_id: Unique project identifier
        """
        self.project_id = project_id
        self._items: dict[str, WorkItem] = {}
        logger.debug(f"Initialized WorkQueue for project {project_id}")

    def add(
        self,
        content: str,
        priority: WorkPriority = WorkPriority.MEDIUM,
        depends_on: Optional[List[str]] = None,
    ) -> WorkItem:
        """Add work item to queue.

        Args:
            content: The task/message to execute
            priority: Execution priority (default: MEDIUM)
            depends_on: List of work item IDs that must complete first

        Returns:
            The created WorkItem

        Example:
            >>> work = queue.add("Fix bug #123", WorkPriority.HIGH)
            >>> work.state
            <WorkState.QUEUED: 'queued'>
        """
        work_id = f"work-{uuid.uuid4().hex[:8]}"

        work = WorkItem(
            id=work_id,
            project_id=self.project_id,
            content=content,
            state=WorkState.QUEUED,
            priority=priority,
            depends_on=depends_on or [],
        )

        self._items[work_id] = work
        logger.info(
            f"Added work item {work_id} to project {self.project_id} "
            f"with priority {priority.name}"
        )

        return work

    def get_next(self) -> Optional[WorkItem]:
        """Get next ready work item (dependencies satisfied, highest priority).

        Returns work items in this order:
        1. QUEUED items with satisfied dependencies
        2. Ordered by priority (CRITICAL > HIGH > MEDIUM > LOW)
        3. Within same priority, oldest first (FIFO)

        Returns:
            Next executable work item, or None if queue empty or all blocked

        Example:
            >>> work = queue.get_next()
            >>> if work:
            ...     print(f"Next: {work.content}")
        """
        # Get all completed work IDs for dependency checking
        completed = self.completed_ids

        # Filter for QUEUED items with satisfied dependencies
        ready_items = [
            item
            for item in self._items.values()
            if item.state == WorkState.QUEUED and item.can_start(completed)
        ]

        if not ready_items:
            return None

        # Sort by priority (descending), then by created_at (ascending)
        ready_items.sort(key=lambda x: (-x.priority.value, x.created_at))

        next_item = ready_items[0]
        logger.debug(
            f"Next work item for {self.project_id}: {next_item.id} "
            f"(priority={next_item.priority.name})"
        )

        return next_item

    def start(self, work_id: str) -> bool:
        """Mark work as in progress.

        Args:
            work_id: Work item ID to start

        Returns:
            True if state changed, False if not found or invalid state

        Example:
            >>> queue.start("work-123")
            True
        """
        item = self._items.get(work_id)
        if not item:
            logger.warning(f"Work item {work_id} not found")
            return False

        if item.state != WorkState.QUEUED:
            logger.warning(
                f"Work item {work_id} not QUEUED (current: {item.state.value})"
            )
            return False

        from datetime import datetime, timezone

        item.state = WorkState.IN_PROGRESS
        item.started_at = datetime.now(timezone.utc)

        logger.info(f"Started work item {work_id}")
        return True

    def complete(self, work_id: str, result: Optional[str] = None) -> bool:
        """Mark work as completed.

        Args:
            work_id: Work item ID to complete
            result: Optional result message

        Returns:
            True if state changed, False if not found or invalid state

        Example:
            >>> queue.complete("work-123", "Successfully implemented feature")
            True
        """
        item = self._items.get(work_id)
        if not item:
            logger.warning(f"Work item {work_id} not found")
            return False

        if item.state not in (WorkState.IN_PROGRESS, WorkState.BLOCKED):
            logger.warning(
                f"Work item {work_id} not IN_PROGRESS or BLOCKED "
                f"(current: {item.state.value})"
            )
            return False

        from datetime import datetime, timezone

        item.state = WorkState.COMPLETED
        item.completed_at = datetime.now(timezone.utc)
        item.result = result

        logger.info(f"Completed work item {work_id}")
        return True

    def fail(self, work_id: str, error: str) -> bool:
        """Mark work as failed.

        Args:
            work_id: Work item ID to fail
            error: Error message

        Returns:
            True if state changed, False if not found or invalid state

        Example:
            >>> queue.fail("work-123", "Execution timeout")
            True
        """
        item = self._items.get(work_id)
        if not item:
            logger.warning(f"Work item {work_id} not found")
            return False

        if item.state not in (WorkState.IN_PROGRESS, WorkState.BLOCKED):
            logger.warning(
                f"Work item {work_id} not IN_PROGRESS or BLOCKED "
                f"(current: {item.state.value})"
            )
            return False

        from datetime import datetime, timezone

        item.state = WorkState.FAILED
        item.completed_at = datetime.now(timezone.utc)
        item.error = error

        logger.error(f"Failed work item {work_id}: {error}")
        return True

    def block(self, work_id: str, reason: str) -> bool:
        """Mark work as blocked (e.g., waiting for event resolution).

        Args:
            work_id: Work item ID to block
            reason: Reason for blocking

        Returns:
            True if state changed, False if not found or invalid state

        Example:
            >>> queue.block("work-123", "Waiting for user approval")
            True
        """
        item = self._items.get(work_id)
        if not item:
            logger.warning(f"Work item {work_id} not found")
            return False

        if item.state != WorkState.IN_PROGRESS:
            logger.warning(
                f"Work item {work_id} not IN_PROGRESS (current: {item.state.value})"
            )
            return False

        item.state = WorkState.BLOCKED
        item.metadata["block_reason"] = reason

        logger.info(f"Blocked work item {work_id}: {reason}")
        return True

    def unblock(self, work_id: str) -> bool:
        """Unblock work item (resume execution).

        Args:
            work_id: Work item ID to unblock

        Returns:
            True if state changed, False if not found or invalid state

        Example:
            >>> queue.unblock("work-123")
            True
        """
        item = self._items.get(work_id)
        if not item:
            logger.warning(f"Work item {work_id} not found")
            return False

        if item.state != WorkState.BLOCKED:
            logger.warning(
                f"Work item {work_id} not BLOCKED (current: {item.state.value})"
            )
            return False

        item.state = WorkState.IN_PROGRESS
        if "block_reason" in item.metadata:
            del item.metadata["block_reason"]

        logger.info(f"Unblocked work item {work_id}")
        return True

    def cancel(self, work_id: str) -> bool:
        """Cancel pending work.

        Args:
            work_id: Work item ID to cancel

        Returns:
            True if state changed, False if not found or invalid state

        Example:
            >>> queue.cancel("work-123")
            True
        """
        item = self._items.get(work_id)
        if not item:
            logger.warning(f"Work item {work_id} not found")
            return False

        if item.state not in (WorkState.PENDING, WorkState.QUEUED, WorkState.BLOCKED):
            logger.warning(
                f"Cannot cancel work item {work_id} in state {item.state.value}"
            )
            return False

        from datetime import datetime, timezone

        item.state = WorkState.CANCELLED
        item.completed_at = datetime.now(timezone.utc)

        logger.info(f"Cancelled work item {work_id}")
        return True

    def get(self, work_id: str) -> Optional[WorkItem]:
        """Get work item by ID.

        Args:
            work_id: Work item ID to retrieve

        Returns:
            WorkItem if found, None otherwise

        Example:
            >>> work = queue.get("work-123")
            >>> if work:
            ...     print(work.content)
        """
        return self._items.get(work_id)

    def list(self, state: Optional[WorkState] = None) -> List[WorkItem]:
        """List work items, optionally filtered by state.

        Args:
            state: Optional state filter

        Returns:
            List of work items matching criteria (may be empty)

        Example:
            >>> queued = queue.list(WorkState.QUEUED)
            >>> all_items = queue.list()
        """
        if state is None:
            return list(self._items.values())

        return [item for item in self._items.values() if item.state == state]

    @property
    def pending_count(self) -> int:
        """Get count of pending/queued work items.

        Returns:
            Number of items in PENDING or QUEUED state

        Example:
            >>> count = queue.pending_count
        """
        return sum(
            1
            for item in self._items.values()
            if item.state in (WorkState.PENDING, WorkState.QUEUED)
        )

    @property
    def completed_ids(self) -> set[str]:
        """Get IDs of completed work items (for dependency checking).

        Returns:
            Set of work item IDs in COMPLETED state

        Example:
            >>> completed = queue.completed_ids
        """
        return {
            item.id
            for item in self._items.values()
            if item.state == WorkState.COMPLETED
        }

    def load_items(self, items: List[WorkItem]) -> None:
        """Load work items from persistence.

        Args:
            items: List of WorkItem instances to load

        Example:
            >>> queue.load_items(persisted_items)
        """
        for item in items:
            if item.project_id != self.project_id:
                logger.warning(
                    f"Skipping work item {item.id} - wrong project "
                    f"(expected {self.project_id}, got {item.project_id})"
                )
                continue

            self._items[item.id] = item

        logger.info(f"Loaded {len(items)} work items for project {self.project_id}")
