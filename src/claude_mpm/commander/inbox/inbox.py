"""Centralized inbox for MPM Commander.

Aggregates events from all projects with filtering, sorting, and pagination.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional

from ..events.manager import EventManager
from ..models.events import Event, EventPriority, EventType
from ..registry import ProjectRegistry
from .dedup import EventDeduplicator
from .models import InboxItem

logger = logging.getLogger(__name__)


@dataclass
class InboxCounts:
    """Count of events by priority.

    Provides quick summary statistics for inbox state.

    Attributes:
        critical: Count of CRITICAL priority events
        high: Count of HIGH priority events
        normal: Count of NORMAL priority events
        low: Count of LOW priority events
        info: Count of INFO priority events
        total: Total count of all events
    """

    critical: int = 0
    high: int = 0
    normal: int = 0
    low: int = 0
    info: int = 0
    total: int = 0


class Inbox:
    """Centralized inbox aggregating events from all projects.

    Provides a unified view of all pending events with:
    - Multi-level filtering (priority, project, event type)
    - Pagination support
    - Priority-based sorting
    - Project metadata enrichment
    - Deduplication

    Example:
        >>> inbox = Inbox(event_manager, project_registry)
        >>> items = inbox.get_items(limit=10, priority=EventPriority.HIGH)
        >>> counts = inbox.get_counts()
        >>> print(f"Total pending: {counts.total}")
    """

    def __init__(
        self,
        event_manager: EventManager,
        project_registry: ProjectRegistry,
        dedup_window: int = 60,
    ):
        """Initialize inbox with dependencies.

        Args:
            event_manager: Event lifecycle manager
            project_registry: Project registration system
            dedup_window: Deduplication window in seconds (default: 60)
        """
        self.events = event_manager
        self.projects = project_registry
        self.deduplicator = EventDeduplicator(window_seconds=dedup_window)

    def get_items(
        self,
        limit: int = 50,
        offset: int = 0,
        priority: Optional[EventPriority] = None,
        project_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
    ) -> List[InboxItem]:
        """Get inbox items with optional filtering and pagination.

        Applies filters in this order:
        1. Get all pending events (optionally for specific project)
        2. Filter by priority if specified
        3. Filter by event type if specified
        4. Sort by priority (high to low) then created_at (old to new)
        5. Paginate with limit and offset
        6. Enrich with project metadata

        Args:
            limit: Maximum number of items to return (default: 50)
            offset: Number of items to skip for pagination (default: 0)
            priority: Filter to specific priority level (optional)
            project_id: Filter to specific project (optional)
            event_type: Filter to specific event type (optional)

        Returns:
            List of enriched InboxItems, sorted and paginated

        Example:
            # Get first 20 critical events
            >>> items = inbox.get_items(limit=20, priority=EventPriority.CRITICAL)

            # Get high-priority errors for specific project
            >>> items = inbox.get_items(
            ...     priority=EventPriority.HIGH,
            ...     project_id="proj_123",
            ...     event_type=EventType.ERROR
            ... )

            # Pagination: get items 50-100
            >>> items = inbox.get_items(limit=50, offset=50)
        """
        # Get all pending events (optionally filtered by project)
        pending = self.events.get_pending(project_id)

        # Filter by priority
        if priority:
            pending = [e for e in pending if e.priority == priority]

        # Filter by event type
        if event_type:
            pending = [e for e in pending if e.type == event_type]

        # Sort by priority (CRITICAL first) then created_at (oldest first)
        priority_order = [
            EventPriority.CRITICAL,
            EventPriority.HIGH,
            EventPriority.NORMAL,
            EventPriority.LOW,
            EventPriority.INFO,
        ]

        def sort_key(event: Event):
            pri_idx = (
                priority_order.index(event.priority)
                if event.priority in priority_order
                else 99
            )
            return (pri_idx, event.created_at)

        sorted_events = sorted(pending, key=sort_key)

        # Paginate
        paginated = sorted_events[offset : offset + limit]

        # Enrich with project metadata
        items = []
        for event in paginated:
            project = self.projects.get(event.project_id)
            if project:
                session_runtime = None
                if event.session_id and event.session_id in project.sessions:
                    session_runtime = project.sessions[event.session_id].runtime

                items.append(
                    InboxItem(
                        event=event,
                        project_name=project.name,
                        project_path=project.path,
                        session_runtime=session_runtime,
                    )
                )

        return items

    def get_counts(self, project_id: Optional[str] = None) -> InboxCounts:
        """Get count of pending events by priority.

        Args:
            project_id: If provided, only count events for this project

        Returns:
            InboxCounts with breakdown by priority and total

        Example:
            >>> counts = inbox.get_counts()
            >>> print(f"Critical: {counts.critical}, Total: {counts.total}")

            >>> project_counts = inbox.get_counts(project_id="proj_123")
        """
        pending = self.events.get_pending(project_id)

        counts = InboxCounts()
        for event in pending:
            counts.total += 1
            if event.priority == EventPriority.CRITICAL:
                counts.critical += 1
            elif event.priority == EventPriority.HIGH:
                counts.high += 1
            elif event.priority == EventPriority.NORMAL:
                counts.normal += 1
            elif event.priority == EventPriority.LOW:
                counts.low += 1
            elif event.priority == EventPriority.INFO:
                counts.info += 1

        return counts

    def should_create_event(
        self, project_id: str, event_type: EventType, title: str
    ) -> bool:
        """Check if event should be created (not a duplicate).

        Uses deduplication to prevent creating duplicate events within
        the configured time window.

        Args:
            project_id: Project raising the event
            event_type: Type of event
            title: Event title

        Returns:
            True if event should be created, False if it's a duplicate

        Example:
            >>> if inbox.should_create_event("proj_123", EventType.ERROR, "Timeout"):
            ...     event = event_manager.create(...)
        """
        return not self.deduplicator.is_duplicate(project_id, event_type.value, title)
