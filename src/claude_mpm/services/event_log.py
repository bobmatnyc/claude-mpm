"""Event Log Service for persistent event storage.

WHY this is needed:
- Decouple event producers from consumers
- Persist events for later processing (e.g., autotodos CLI)
- Enable event-driven architecture patterns
- Provide audit trail of system events

DESIGN DECISION: Simple JSON file storage because:
- Human-readable and inspectable
- No additional database dependencies
- Fast for small event volumes
- Easy to clear and manage
- Follows existing pattern (hook_error_memory)
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from ..core.logger import get_logger

# Event status types
EventStatus = Literal["pending", "resolved", "archived"]

# Max message length to prevent file bloat
MAX_MESSAGE_LENGTH = 2000


class EventLog:
    """Persistent event log with simple JSON storage.

    WHY this design:
    - Store events with timestamp, type, payload, status
    - Support filtering by status and event type
    - Prevent file bloat with message truncation
    - Enable mark-as-resolved workflow
    - Keep it simple - no complex queries needed
    """

    def __init__(self, log_file: Optional[Path] = None):
        """Initialize event log.

        Args:
            log_file: Path to event log file (default: .claude-mpm/event_log.json)
        """
        self.logger = get_logger("event_log")

        # Use default location if not specified
        if log_file is None:
            log_file = Path.cwd() / ".claude-mpm" / "event_log.json"

        self.log_file = log_file
        self.events: List[Dict[str, Any]] = self._load_events()

    def _load_events(self) -> List[Dict[str, Any]]:
        """Load events from disk.

        Returns:
            List of event records
        """
        if not self.log_file.exists():
            return []

        try:
            content = self.log_file.read_text()
            if not content.strip():
                return []
            data = json.loads(content)

            # Validate structure
            if not isinstance(data, list):
                self.logger.warning("Event log is not a list, resetting")
                return []

            return data
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse event log: {e}, resetting")
            return []
        except Exception as e:
            self.logger.error(f"Error loading event log: {e}")
            return []

    def _save_events(self):
        """Persist events to disk."""
        try:
            # Ensure directory exists
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

            # Write with pretty formatting for human readability
            self.log_file.write_text(json.dumps(self.events, indent=2))
        except Exception as e:
            self.logger.error(f"Failed to save event log: {e}")

    def _truncate_message(self, message: str) -> str:
        """Truncate message to prevent file bloat.

        Args:
            message: Message to truncate

        Returns:
            Truncated message with ellipsis if needed
        """
        if len(message) <= MAX_MESSAGE_LENGTH:
            return message

        return message[:MAX_MESSAGE_LENGTH] + "... (truncated)"

    def append_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        status: EventStatus = "pending",
    ) -> str:
        """Append a new event to the log.

        Args:
            event_type: Type of event (e.g., "autotodo.error", "hook.error")
            payload: Event data (will be truncated if too large)
            status: Event status (default: "pending")

        Returns:
            Event ID (timestamp-based for simplicity)
        """
        # Truncate any message fields in payload
        truncated_payload = payload.copy()
        if "message" in truncated_payload:
            truncated_payload["message"] = self._truncate_message(
                str(truncated_payload["message"])
            )
        if "full_message" in truncated_payload:
            truncated_payload["full_message"] = self._truncate_message(
                str(truncated_payload["full_message"])
            )

        # Create event record
        timestamp = datetime.now(timezone.utc).isoformat()
        event = {
            "id": timestamp,  # Use timestamp as ID for simplicity
            "timestamp": timestamp,
            "event_type": event_type,
            "payload": truncated_payload,
            "status": status,
        }

        # Append and save
        self.events.append(event)
        self._save_events()

        self.logger.debug(f"Appended event: {event_type} (status: {status})")
        return timestamp

    def list_events(
        self,
        event_type: Optional[str] = None,
        status: Optional[EventStatus] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List events with optional filtering.

        Args:
            event_type: Filter by event type (e.g., "autotodo.error")
            status: Filter by status (e.g., "pending")
            limit: Maximum number of events to return (most recent first)

        Returns:
            List of matching events
        """
        # Filter events
        filtered = self.events

        if event_type:
            filtered = [e for e in filtered if e["event_type"] == event_type]

        if status:
            filtered = [e for e in filtered if e["status"] == status]

        # Sort by timestamp (most recent first)
        filtered = sorted(filtered, key=lambda e: e["timestamp"], reverse=True)

        # Apply limit
        if limit:
            filtered = filtered[:limit]

        return filtered

    def mark_resolved(self, event_id: str) -> bool:
        """Mark an event as resolved.

        Args:
            event_id: Event ID (timestamp)

        Returns:
            True if event was found and updated
        """
        for event in self.events:
            if event["id"] == event_id:
                event["status"] = "resolved"
                event["resolved_at"] = datetime.now(timezone.utc).isoformat()
                self._save_events()
                self.logger.debug(f"Marked event resolved: {event_id}")
                return True

        return False

    def mark_all_resolved(
        self, event_type: Optional[str] = None, status: EventStatus = "pending"
    ) -> int:
        """Mark multiple events as resolved.

        Args:
            event_type: Optional filter by event type
            status: Filter by current status (default: "pending")

        Returns:
            Number of events marked as resolved
        """
        count = 0
        now = datetime.now(timezone.utc).isoformat()

        for event in self.events:
            # Check filters
            if event["status"] != status:
                continue
            if event_type and event["event_type"] != event_type:
                continue

            # Mark resolved
            event["status"] = "resolved"
            event["resolved_at"] = now
            count += 1

        if count > 0:
            self._save_events()
            self.logger.debug(f"Marked {count} events as resolved")

        return count

    def clear_resolved(self, older_than_days: Optional[int] = None) -> int:
        """Remove resolved events from the log.

        Args:
            older_than_days: Only clear events older than N days

        Returns:
            Number of events removed
        """
        if older_than_days:
            # Calculate cutoff timestamp
            from datetime import timedelta

            cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
            cutoff_iso = cutoff.isoformat()

            # Keep events that are NOT resolved OR are newer than cutoff
            before_count = len(self.events)
            self.events = [
                e
                for e in self.events
                if e["status"] != "resolved" or e.get("resolved_at", "") > cutoff_iso
            ]
            removed = before_count - len(self.events)
        else:
            # Remove all resolved events
            before_count = len(self.events)
            self.events = [e for e in self.events if e["status"] != "resolved"]
            removed = before_count - len(self.events)

        if removed > 0:
            self._save_events()
            self.logger.debug(f"Cleared {removed} resolved events")

        return removed

    def get_stats(self) -> Dict[str, Any]:
        """Get event log statistics.

        Returns:
            Dictionary with event counts by status and type
        """
        stats = {
            "total_events": len(self.events),
            "by_status": {"pending": 0, "resolved": 0, "archived": 0},
            "by_type": {},
            "log_file": str(self.log_file),
        }

        for event in self.events:
            # Count by status
            status = event["status"]
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

            # Count by type
            event_type = event["event_type"]
            stats["by_type"][event_type] = stats["by_type"].get(event_type, 0) + 1

        return stats


# Global instance
_event_log: Optional[EventLog] = None


def get_event_log(log_file: Optional[Path] = None) -> EventLog:
    """Get the global event log instance.

    Args:
        log_file: Optional custom log file path

    Returns:
        EventLog instance
    """
    global _event_log
    if _event_log is None:
        _event_log = EventLog(log_file)
    return _event_log
