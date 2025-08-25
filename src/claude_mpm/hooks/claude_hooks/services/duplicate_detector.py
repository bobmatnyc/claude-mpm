"""Duplicate event detection service for Claude hook handler.

This service manages:
- Event key generation
- Duplicate event detection within time windows
- Recent event tracking
"""

import threading
import time
from collections import deque


class DuplicateEventDetector:
    """Detects and filters duplicate events."""

    def __init__(
        self, max_recent_events: int = 10, duplicate_window_seconds: float = 0.1
    ):
        """Initialize duplicate event detector.

        Args:
            max_recent_events: Maximum number of recent events to track
            duplicate_window_seconds: Time window in seconds for duplicate detection
        """
        # Track recent events to detect duplicates
        self._recent_events = deque(maxlen=max_recent_events)
        self._events_lock = threading.Lock()
        self.duplicate_window_seconds = duplicate_window_seconds

    def is_duplicate(self, event: dict) -> bool:
        """Check if an event is a duplicate of a recent event.

        Args:
            event: The event dictionary to check

        Returns:
            True if the event is a duplicate, False otherwise
        """
        event_key = self.generate_event_key(event)
        current_time = time.time()

        with self._events_lock:
            # Check if we've seen this event recently
            for recent_key, recent_time in self._recent_events:
                if (
                    recent_key == event_key
                    and (current_time - recent_time) < self.duplicate_window_seconds
                ):
                    return True

            # Not a duplicate, record it
            self._recent_events.append((event_key, current_time))
            return False

    def generate_event_key(self, event: dict) -> str:
        """Generate a unique key for an event to detect duplicates.

        WHY: Claude Code may call the hook multiple times for the same event
        because the hook is registered for multiple event types. We need to
        detect and skip duplicate processing while still returning continue.

        Args:
            event: The event dictionary

        Returns:
            A unique string key for the event
        """
        # Create a key from event type, session_id, and key data
        hook_type = event.get("hook_event_name", "unknown")
        session_id = event.get("session_id", "")

        # Add type-specific data to make the key unique
        if hook_type == "PreToolUse":
            tool_name = event.get("tool_name", "")
            # For some tools, include parameters to distinguish calls
            if tool_name == "Task":
                tool_input = event.get("tool_input", {})
                agent = tool_input.get("subagent_type", "")
                prompt_preview = (
                    tool_input.get("prompt", "") or tool_input.get("description", "")
                )[:50]
                return f"{hook_type}:{session_id}:{tool_name}:{agent}:{prompt_preview}"
            return f"{hook_type}:{session_id}:{tool_name}"

        if hook_type == "UserPromptSubmit":
            prompt_preview = event.get("prompt", "")[:50]
            return f"{hook_type}:{session_id}:{prompt_preview}"

        # For other events, just use type and session
        return f"{hook_type}:{session_id}"

    def clear_old_events(self):
        """Clear events older than the duplicate window."""
        current_time = time.time()
        cutoff_time = current_time - self.duplicate_window_seconds

        with self._events_lock:
            # Create a new deque with only recent events
            recent_only = deque(
                (key, timestamp)
                for key, timestamp in self._recent_events
                if timestamp > cutoff_time
            )
            recent_only.maxlen = self._recent_events.maxlen
            self._recent_events = recent_only
