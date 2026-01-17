"""BlockManager for coordinating work blocking with events.

This module provides BlockManager which automatically blocks/unblocks
work items based on blocking event detection and resolution.
"""

import logging
from typing import Dict, List, Optional, Set

from ..events.manager import EventManager
from ..models.events import Event
from ..models.work import WorkState
from ..work.executor import WorkExecutor
from ..work.queue import WorkQueue

logger = logging.getLogger(__name__)


class BlockManager:
    """Coordinates blocking events with work execution.

    Monitors blocking events and automatically blocks/unblocks work items
    based on event lifecycle. Tracks event-to-work relationships for precise
    unblocking when events are resolved.

    Attributes:
        event_manager: EventManager for querying blocking events
        work_queues: Dict mapping project_id -> WorkQueue
        work_executors: Dict mapping project_id -> WorkExecutor

    Example:
        >>> manager = BlockManager(event_manager, work_queues, work_executors)
        >>> blocked = await manager.check_and_block(event)
        >>> unblocked = await manager.check_and_unblock(event_id)
    """

    def __init__(
        self,
        event_manager: EventManager,
        work_queues: Dict[str, WorkQueue],
        work_executors: Dict[str, WorkExecutor],
    ):
        """Initialize BlockManager.

        Args:
            event_manager: EventManager instance
            work_queues: Dict mapping project_id -> WorkQueue
            work_executors: Dict mapping project_id -> WorkExecutor

        Raises:
            ValueError: If any required parameter is None
        """
        if event_manager is None:
            raise ValueError("EventManager cannot be None")
        if work_queues is None:
            raise ValueError("work_queues cannot be None")
        if work_executors is None:
            raise ValueError("work_executors cannot be None")

        self.event_manager = event_manager
        self.work_queues = work_queues
        self.work_executors = work_executors

        # Track event-to-work mapping: event_id -> set of work_ids
        self._event_work_mapping: Dict[str, Set[str]] = {}

        logger.debug("BlockManager initialized")

    async def check_and_block(self, event: Event) -> List[str]:
        """Check if event is blocking and block affected work.

        When a blocking event is detected:
        1. Determine blocking scope (project or all)
        2. Find all in-progress work items in scope
        3. Block each work item via WorkExecutor
        4. Track event-to-work mapping for later unblocking

        Args:
            event: Event to check for blocking

        Returns:
            List of work item IDs that were blocked

        Example:
            >>> event = Event(type=EventType.ERROR, ...)
            >>> blocked = await manager.check_and_block(event)
            >>> print(f"Blocked {len(blocked)} work items")
        """
        if not event.is_blocking:
            logger.debug("Event %s is not blocking, no action needed", event.id)
            return []

        logger.info(
            "Processing blocking event %s (scope: %s): %s",
            event.id,
            event.blocking_scope,
            event.title,
        )

        blocked_work_ids = []

        # Determine which projects to block based on scope
        if event.blocking_scope == "all":
            # Block all projects
            target_projects = list(self.work_queues.keys())
            logger.info("Event %s blocks ALL projects", event.id)
        elif event.blocking_scope == "project":
            # Block only this project
            target_projects = [event.project_id]
            logger.info("Event %s blocks project %s only", event.id, event.project_id)
        else:
            logger.warning(
                "Unknown blocking scope '%s' for event %s",
                event.blocking_scope,
                event.id,
            )
            return []

        # Block in-progress work in target projects
        for project_id in target_projects:
            queue = self.work_queues.get(project_id)
            if not queue:
                logger.debug("No work queue for project %s", project_id)
                continue

            executor = self.work_executors.get(project_id)
            if not executor:
                logger.debug("No work executor for project %s", project_id)
                continue

            # Get in-progress work items
            in_progress = queue.list(WorkState.IN_PROGRESS)

            for work_item in in_progress:
                # Block the work item
                block_reason = f"Event {event.id}: {event.title}"
                success = await executor.handle_block(work_item.id, block_reason)

                if success:
                    blocked_work_ids.append(work_item.id)
                    logger.info(
                        "Blocked work item %s for project %s: %s",
                        work_item.id,
                        project_id,
                        block_reason,
                    )
                else:
                    logger.warning(
                        "Failed to block work item %s for project %s",
                        work_item.id,
                        project_id,
                    )

        # Track event-to-work mapping
        if blocked_work_ids:
            self._event_work_mapping[event.id] = set(blocked_work_ids)
            logger.info(
                "Event %s blocked %d work items: %s",
                event.id,
                len(blocked_work_ids),
                blocked_work_ids,
            )

        return blocked_work_ids

    async def check_and_unblock(self, event_id: str) -> List[str]:
        """Unblock work items when event is resolved.

        When a blocking event is resolved:
        1. Look up which work items were blocked by this event
        2. Unblock each work item via WorkExecutor
        3. Remove event-to-work mapping

        Args:
            event_id: ID of resolved event

        Returns:
            List of work item IDs that were unblocked

        Example:
            >>> unblocked = await manager.check_and_unblock("evt_123")
            >>> print(f"Unblocked {len(unblocked)} work items")
        """
        # Get work items blocked by this event
        work_ids = self._event_work_mapping.pop(event_id, set())

        if not work_ids:
            logger.debug("No work items blocked by event %s", event_id)
            return []

        logger.info(
            "Unblocking %d work items for resolved event %s", len(work_ids), event_id
        )

        unblocked_work_ids = []

        # Unblock each work item
        for work_id in work_ids:
            # Find which project this work belongs to
            project_id = self._find_work_project(work_id)
            if not project_id:
                logger.warning("Cannot find project for work item %s", work_id)
                continue

            executor = self.work_executors.get(project_id)
            if not executor:
                logger.warning("No executor for project %s", project_id)
                continue

            # Unblock the work item
            success = await executor.handle_unblock(work_id)

            if success:
                unblocked_work_ids.append(work_id)
                logger.info("Unblocked work item %s", work_id)
            else:
                logger.warning("Failed to unblock work item %s", work_id)

        return unblocked_work_ids

    def _find_work_project(self, work_id: str) -> Optional[str]:
        """Find which project a work item belongs to.

        Args:
            work_id: Work item ID to search for

        Returns:
            Project ID if found, None otherwise
        """
        for project_id, queue in self.work_queues.items():
            work_item = queue.get(work_id)
            if work_item:
                return project_id
        return None

    def get_blocked_work(self, event_id: str) -> Set[str]:
        """Get work items blocked by a specific event.

        Args:
            event_id: Event ID to check

        Returns:
            Set of work item IDs blocked by this event

        Example:
            >>> work_ids = manager.get_blocked_work("evt_123")
        """
        return self._event_work_mapping.get(event_id, set()).copy()

    def get_blocking_events(self, work_id: str) -> List[str]:
        """Get events that are blocking a specific work item.

        Args:
            work_id: Work item ID to check

        Returns:
            List of event IDs blocking this work item

        Example:
            >>> events = manager.get_blocking_events("work-123")
        """
        blocking_events = []
        for event_id, work_ids in self._event_work_mapping.items():
            if work_id in work_ids:
                blocking_events.append(event_id)
        return blocking_events

    def is_work_blocked(self, work_id: str) -> bool:
        """Check if a work item is currently blocked.

        Args:
            work_id: Work item ID to check

        Returns:
            True if work item is blocked by any event, False otherwise

        Example:
            >>> if manager.is_work_blocked("work-123"):
            ...     print("Work is blocked")
        """
        return len(self.get_blocking_events(work_id)) > 0

    def clear_project_mappings(self, project_id: str) -> int:
        """Clear all event-work mappings for a project.

        Called when a project is shut down or reset.

        Args:
            project_id: Project ID to clear

        Returns:
            Number of work items that had mappings removed

        Example:
            >>> count = manager.clear_project_mappings("proj_123")
        """
        queue = self.work_queues.get(project_id)
        if not queue:
            return 0

        # Get all work IDs for this project
        all_work = queue.list()
        project_work_ids = {w.id for w in all_work}

        removed_count = 0

        # Remove work items from event mappings
        for event_id in list(self._event_work_mapping.keys()):
            work_ids = self._event_work_mapping[event_id]
            original_len = len(work_ids)

            # Remove project work items
            work_ids.difference_update(project_work_ids)

            removed_count += original_len - len(work_ids)

            # Remove empty mappings
            if not work_ids:
                del self._event_work_mapping[event_id]

        logger.info(
            "Cleared %d work item mappings for project %s", removed_count, project_id
        )

        return removed_count
