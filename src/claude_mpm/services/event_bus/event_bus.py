"""Event Bus implementation using pyee.

WHY pyee over alternatives:
- AsyncIOEventEmitter supports both sync and async handlers
- Battle-tested library with minimal dependencies
- Simple EventEmitter pattern familiar to developers
- Thread-safe for multi-threaded environments
- Efficient event dispatch with minimal overhead
"""

import asyncio
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

from pyee.asyncio import AsyncIOEventEmitter

# Configure logger
from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


class EventBus:
    """Singleton Event Bus for decoupled event handling.

    WHY singleton pattern:
    - Ensures single point of event coordination
    - Prevents duplicate event processing
    - Simplifies configuration and management
    - Thread-safe initialization with proper locking
    """

    _instance: Optional["EventBus"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "EventBus":
        """Ensure singleton instance creation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the event bus once."""
        # Only initialize once
        if hasattr(self, "_initialized"):
            return

        self._initialized = True
        self._emitter = AsyncIOEventEmitter()
        self._enabled = True
        self._event_filters: Set[str] = set()
        self._stats = {
            "events_published": 0,
            "events_filtered": 0,
            "events_failed": 0,
            "last_event_time": None,
        }
        self._debug = False

        # Event history for debugging (limited size)
        self._event_history: List[Dict[str, Any]] = []
        self._max_history_size = 100

        # Track async handler tasks to prevent garbage collection
        self._handler_tasks: Set[asyncio.Task] = set()

        # Track handler wrappers for removal
        self._handler_wrappers: Dict[tuple, Callable] = {}

        logger.info("EventBus initialized")

    @classmethod
    def get_instance(cls) -> "EventBus":
        """Get the singleton EventBus instance.

        Returns:
            EventBus: The singleton instance
        """
        return cls()

    def enable(self) -> None:
        """Enable event bus processing."""
        self._enabled = True
        logger.info("EventBus enabled")

    def disable(self) -> None:
        """Disable event bus processing (for testing or maintenance)."""
        self._enabled = False
        logger.info("EventBus disabled")

    def set_debug(self, debug: bool) -> None:
        """Enable or disable debug logging.

        Args:
            debug: Whether to enable debug logging
        """
        self._debug = debug
        if debug:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

    def add_filter(self, pattern: str) -> None:
        """Add an event filter pattern.

        Only events matching filter patterns will be processed.
        Use wildcards: 'hook.*' matches all hook events.

        Args:
            pattern: Event name pattern to allow
        """
        self._event_filters.add(pattern)
        logger.debug(f"Added event filter: {pattern}")

    def remove_filter(self, pattern: str) -> None:
        """Remove an event filter pattern.

        Args:
            pattern: Event name pattern to remove
        """
        self._event_filters.discard(pattern)
        logger.debug(f"Removed event filter: {pattern}")

    def clear_filters(self) -> None:
        """Clear all event filters (allow all events)."""
        self._event_filters.clear()
        logger.debug("Cleared all event filters")

    def _should_process_event(self, event_type: str) -> bool:
        """Check if an event should be processed based on filters.

        Args:
            event_type: The event type to check

        Returns:
            bool: True if event should be processed
        """
        # If no filters, process all events
        if not self._event_filters:
            return True

        # Check if event matches any filter
        for filter_pattern in self._event_filters:
            if filter_pattern.endswith("*"):
                # Wildcard pattern
                prefix = filter_pattern[:-1]
                if event_type.startswith(prefix):
                    return True
            elif event_type == filter_pattern:
                # Exact match
                return True

        return False

    def publish(self, event_type: str, data: Any) -> bool:
        """Publish an event synchronously (for use from sync contexts like hooks).

        This method is thread-safe and can be called from any thread.
        Events are dispatched asynchronously to handlers.

        Args:
            event_type: The event type (e.g., 'hook.pre_tool')
            data: The event data

        Returns:
            bool: True if event was published, False if filtered or disabled
        """
        if not self._enabled:
            if self._debug:
                logger.debug(f"EventBus disabled, dropping event: {event_type}")
            return False

        # Check filters
        if not self._should_process_event(event_type):
            self._stats["events_filtered"] += 1
            if self._debug:
                logger.debug(f"Event filtered out: {event_type}")
            return False

        try:
            # Record event in history
            self._record_event(event_type, data)

            # Emit event to regular handlers (pyee handles thread safety)
            self._emitter.emit(event_type, data)

            # Also emit to wildcard handlers
            if hasattr(self, "_wildcard_handlers"):
                for prefix, handlers in self._wildcard_handlers.items():
                    if event_type.startswith(prefix):
                        for handler in handlers:
                            try:
                                # Call with event_type and data for wildcard handlers
                                if asyncio.iscoroutinefunction(handler):
                                    # Schedule async handlers with tracking
                                    try:
                                        loop = asyncio.get_event_loop()
                                        if loop.is_running():
                                            task = asyncio.create_task(
                                                handler(event_type, data)
                                            )
                                            self._handler_tasks.add(task)
                                            task.add_done_callback(
                                                self._handler_tasks.discard
                                            )
                                        else:
                                            loop.run_until_complete(
                                                handler(event_type, data)
                                            )
                                    except RuntimeError:
                                        # No event loop, skip async handler
                                        pass
                                else:
                                    handler(event_type, data)
                            except Exception as e:
                                if self._debug:
                                    logger.debug(f"Wildcard handler error: {e}")

            # Update stats
            self._stats["events_published"] += 1
            self._stats["last_event_time"] = datetime.now(timezone.utc).isoformat()

            if self._debug:
                logger.debug(f"Published event: {event_type}")

            return True

        except Exception as e:
            self._stats["events_failed"] += 1
            logger.error(f"Failed to publish event {event_type}: {e}")
            return False

    async def publish_async(self, event_type: str, data: Any) -> bool:
        """Publish an event from an async context.

        Args:
            event_type: The event type
            data: The event data

        Returns:
            bool: True if event was published
        """
        # Just delegate to sync publish (pyee handles both)
        return self.publish(event_type, data)

    def on(self, event_type: str, handler: Callable) -> None:
        """Register an event handler.

        The handler can be sync or async. For async handlers,
        they will be scheduled on the event loop.

        Args:
            event_type: The event type to listen for (supports wildcards)
            handler: The handler function
        """
        if event_type.endswith("*"):
            # Store wildcard handlers separately
            if not hasattr(self, "_wildcard_handlers"):
                self._wildcard_handlers = {}

            prefix = event_type[:-1]
            if prefix not in self._wildcard_handlers:
                self._wildcard_handlers[prefix] = []
            self._wildcard_handlers[prefix].append(handler)

            logger.debug(f"Registered wildcard handler for: {event_type}")
        else:
            # Wrap handler to catch exceptions and prevent them from stopping other handlers
            def safe_handler(data):
                try:
                    handler(data)
                except Exception as e:
                    if self._debug:
                        logger.debug(f"Handler error for {event_type}: {e}")

            # Store mapping for later removal
            wrapper_key = (event_type, handler)
            self._handler_wrappers[wrapper_key] = safe_handler

            # Regular event registration with wrapped handler
            self._emitter.on(event_type, safe_handler)
            logger.debug(f"Registered handler for: {event_type}")

    def once(self, event_type: str, handler: Callable) -> None:
        """Register a one-time event handler.

        Args:
            event_type: The event type to listen for
            handler: The handler function
        """
        self._emitter.once(event_type, handler)
        logger.debug(f"Registered one-time handler for: {event_type}")

    def remove_listener(self, event_type: str, handler: Callable) -> None:
        """Remove an event handler.

        Args:
            event_type: The event type
            handler: The handler to remove
        """
        # Check if we have a wrapped version of this handler
        wrapper_key = (event_type, handler)
        if wrapper_key in self._handler_wrappers:
            # Remove the wrapped handler from pyee
            wrapped_handler = self._handler_wrappers[wrapper_key]
            self._emitter.remove_listener(event_type, wrapped_handler)
            # Remove from our tracking dict
            del self._handler_wrappers[wrapper_key]
        else:
            # No wrapper, remove directly (e.g., for wildcard handlers or direct registrations)
            self._emitter.remove_listener(event_type, handler)
        logger.debug(f"Removed handler for: {event_type}")

    def remove_all_listeners(self, event_type: Optional[str] = None) -> None:
        """Remove all listeners for an event type, or all listeners.

        Args:
            event_type: Optional event type. If None, removes all listeners.
        """
        if event_type:
            self._emitter.remove_all_listeners(event_type)
            # Clean up wrappers for this event type
            wrappers_to_remove = [
                key for key in self._handler_wrappers if key[0] == event_type
            ]
            for key in wrappers_to_remove:
                del self._handler_wrappers[key]
            logger.debug(f"Removed all handlers for: {event_type}")
        else:
            self._emitter.remove_all_listeners()
            # Clean up all wrappers
            self._handler_wrappers.clear()
            logger.debug("Removed all event handlers")

    def _record_event(self, event_type: str, data: Any) -> None:
        """Record event in history for debugging.

        Args:
            event_type: The event type
            data: The event data
        """
        event_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "data": data,
        }

        self._event_history.append(event_record)

        # Trim history if too large
        if len(self._event_history) > self._max_history_size:
            self._event_history = self._event_history[-self._max_history_size :]

    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics.

        Returns:
            dict: Statistics about event processing
        """
        return {
            **self._stats,
            "enabled": self._enabled,
            "filters_active": len(self._event_filters) > 0,
            "filter_count": len(self._event_filters),
            "history_size": len(self._event_history),
        }

    def get_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent events from history.

        Args:
            limit: Maximum number of events to return

        Returns:
            list: Recent events
        """
        return self._event_history[-limit:]

    def clear_history(self) -> None:
        """Clear the event history."""
        self._event_history.clear()
        logger.debug("Cleared event history")

    def reset_stats(self) -> None:
        """Reset event statistics."""
        self._stats = {
            "events_published": 0,
            "events_filtered": 0,
            "events_failed": 0,
            "last_event_time": None,
        }
        logger.debug("Reset event statistics")
