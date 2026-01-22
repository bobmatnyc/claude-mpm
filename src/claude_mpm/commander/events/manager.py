"""EventManager for MPM Commander inbox system.

Manages event lifecycle, inbox queries, and project event tracking.
"""

import asyncio
import logging
import threading
import uuid
from asyncio import Queue
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from ..models.events import (
    DEFAULT_PRIORITIES,
    Event,
    EventPriority,
    EventStatus,
    EventType,
)

logger = logging.getLogger(__name__)


class EventManager:
    """Manages event lifecycle and inbox queries.

    Thread-safe event storage with support for:
    - Creating events with automatic priority assignment
    - Querying pending events by project or globally
    - Inbox sorting by priority then timestamp
    - Responding to, acknowledging, or dismissing events
    - Detecting blocking events
    - Clearing project events

    Example:
        manager = EventManager()
        event = manager.create(
            project_id="proj_123",
            event_type=EventType.DECISION_NEEDED,
            title="Choose deployment target",
            options=["staging", "production"]
        )
        inbox = manager.get_inbox()
        manager.respond(event.id, "staging")
    """

    def __init__(self) -> None:
        """Initialize empty event storage."""
        self._events: Dict[str, Event] = {}
        self._project_index: Dict[str, List[str]] = {}  # project_id -> event_ids
        self._lock = threading.RLock()
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._event_queue: Queue = Queue()

    def create(
        self,
        project_id: str,
        event_type: EventType,
        title: str,
        content: str = "",
        session_id: Optional[str] = None,
        priority: Optional[EventPriority] = None,
        options: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Event:
        """Create and queue a new event.

        Args:
            project_id: ID of project raising this event
            event_type: Type of event
            title: Short summary
            content: Detailed description
            session_id: Optional session ID
            priority: Optional priority (uses default if not specified)
            options: For DECISION_NEEDED, list of choices
            context: Additional structured data

        Returns:
            The created Event

        Example:
            event = manager.create(
                project_id="proj_123",
                event_type=EventType.ERROR,
                title="Database connection failed",
                content="Could not connect to postgres://..."
            )
        """
        with self._lock:
            event_id = f"evt_{uuid.uuid4().hex[:12]}"

            # Use default priority if not specified
            if priority is None:
                priority = DEFAULT_PRIORITIES.get(event_type, EventPriority.NORMAL)

            event = Event(
                id=event_id,
                project_id=project_id,
                session_id=session_id,
                type=event_type,
                priority=priority,
                title=title,
                content=content,
                context=context or {},
                options=options,
            )

            self._events[event_id] = event

            # Index by project
            if project_id not in self._project_index:
                self._project_index[project_id] = []
            self._project_index[project_id].append(event_id)

            logger.info("Created event %s: [%s] %s", event_id, event_type.value, title)
            return event

    def add_event(self, event: Event) -> None:
        """Add existing event to manager (for loading from persistence).

        Args:
            event: Event instance to add

        Example:
            # Load events from disk and add to manager
            for event in loaded_events:
                manager.add_event(event)
        """
        with self._lock:
            self._events[event.id] = event

            # Index by project
            if event.project_id not in self._project_index:
                self._project_index[event.project_id] = []
            if event.id not in self._project_index[event.project_id]:
                self._project_index[event.project_id].append(event.id)

            logger.debug("Added event %s to manager", event.id)

    def get(self, event_id: str) -> Optional[Event]:
        """Get event by ID.

        Args:
            event_id: Unique event identifier

        Returns:
            Event if found, None otherwise
        """
        return self._events.get(event_id)

    def get_pending(self, project_id: Optional[str] = None) -> List[Event]:
        """Get all pending events, optionally filtered by project.

        Args:
            project_id: If provided, only return events for this project

        Returns:
            List of pending events (unsorted)

        Example:
            # Get all pending events
            all_pending = manager.get_pending()

            # Get pending events for one project
            project_pending = manager.get_pending("proj_123")
        """
        with self._lock:
            if project_id:
                event_ids = self._project_index.get(project_id, [])
                events = [self._events[eid] for eid in event_ids if eid in self._events]
            else:
                events = list(self._events.values())

            return [e for e in events if e.status == EventStatus.PENDING]

    def get_inbox(self, limit: int = 50) -> List[Event]:
        """Get events for inbox, sorted by priority then time.

        Sorting order:
        1. Priority: CRITICAL > HIGH > NORMAL > LOW > INFO
        2. Within same priority: oldest first (created_at ascending)

        Args:
            limit: Maximum number of events to return

        Returns:
            Sorted list of pending events, limited to `limit` items

        Example:
            inbox = manager.get_inbox(limit=20)
            for event in inbox:
                print(f"{event.priority.value}: {event.title}")
        """
        with self._lock:
            pending = [
                e for e in self._events.values() if e.status == EventStatus.PENDING
            ]

            # Sort by priority (CRITICAL first) then by created_at (oldest first)
            priority_order = [
                EventPriority.CRITICAL,
                EventPriority.HIGH,
                EventPriority.NORMAL,
                EventPriority.LOW,
                EventPriority.INFO,
            ]

            def sort_key(event: Event) -> tuple[int, datetime]:
                pri_idx = (
                    priority_order.index(event.priority)
                    if event.priority in priority_order
                    else 99
                )
                return (pri_idx, event.created_at)

            sorted_events = sorted(pending, key=sort_key)
            return sorted_events[:limit]

    def respond(self, event_id: str, response: str) -> Event:
        """Record response to event and mark as resolved.

        Args:
            event_id: ID of event to respond to
            response: User's response text

        Returns:
            The updated Event

        Raises:
            KeyError: If event_id not found

        Example:
            event = manager.respond("evt_abc123", "Deploy to staging")
        """
        with self._lock:
            event = self._events.get(event_id)
            if not event:
                raise KeyError(f"Event not found: {event_id}")

            event.response = response
            event.responded_at = datetime.now(timezone.utc)
            event.status = EventStatus.RESOLVED

            logger.info("Responded to event %s: %s", event_id, response[:50])
            return event

    def dismiss(self, event_id: str) -> Event:
        """Mark event as dismissed without providing a response.

        Args:
            event_id: ID of event to dismiss

        Returns:
            The updated Event

        Raises:
            KeyError: If event_id not found

        Example:
            manager.dismiss("evt_abc123")
        """
        with self._lock:
            event = self._events.get(event_id)
            if not event:
                raise KeyError(f"Event not found: {event_id}")

            event.status = EventStatus.DISMISSED

            logger.info("Dismissed event %s", event_id)
            return event

    def acknowledge(self, event_id: str) -> Event:
        """Mark event as seen but not resolved yet.

        Args:
            event_id: ID of event to acknowledge

        Returns:
            The updated Event

        Raises:
            KeyError: If event_id not found

        Example:
            manager.acknowledge("evt_abc123")
        """
        with self._lock:
            event = self._events.get(event_id)
            if not event:
                raise KeyError(f"Event not found: {event_id}")

            event.status = EventStatus.ACKNOWLEDGED

            logger.info("Acknowledged event %s", event_id)
            return event

    def get_blocking_events(self, project_id: Optional[str] = None) -> List[Event]:
        """Get events that are blocking progress.

        Args:
            project_id: If provided, include project-scoped blocking events
                       for this project. Always includes global blocking events.

        Returns:
            List of blocking events

        Example:
            # Get all blocking events (global scope only)
            blockers = manager.get_blocking_events()

            # Get blocking events for specific project (global + project scope)
            blockers = manager.get_blocking_events("proj_123")
        """
        with self._lock:
            pending = self.get_pending(project_id)
            return [e for e in pending if e.is_blocking]

    def clear_project_events(self, project_id: str) -> int:
        """Clear all events for a project.

        Args:
            project_id: ID of project whose events should be cleared

        Returns:
            Number of events removed

        Example:
            removed = manager.clear_project_events("proj_123")
            print(f"Cleared {removed} events")
        """
        with self._lock:
            event_ids = self._project_index.pop(project_id, [])
            for eid in event_ids:
                self._events.pop(eid, None)
            return len(event_ids)

    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        """Subscribe callback to event type.

        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs (sync or async)

        Example:
            def on_error(event):
                print(f"Error: {event.title}")

            manager.subscribe(EventType.ERROR, on_error)
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable) -> None:
        """Unsubscribe callback from event type.

        Args:
            event_type: Type of event to unsubscribe from
            callback: Function to remove from subscribers

        Example:
            manager.unsubscribe(EventType.ERROR, on_error)
        """
        if (
            event_type in self._subscribers
            and callback in self._subscribers[event_type]
        ):
            self._subscribers[event_type].remove(callback)

    async def emit(self, event: Event) -> None:
        """Emit event to all subscribers.

        Queues the event and notifies all subscribed callbacks.
        Supports both sync and async callbacks.

        Args:
            event: Event to emit

        Example:
            await manager.emit(event)
        """
        await self._event_queue.put(event)
        if event.type in self._subscribers:
            for callback in self._subscribers[event.type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Subscriber callback error: {e}")
