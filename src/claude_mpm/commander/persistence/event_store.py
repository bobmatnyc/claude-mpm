"""Event persistence for MPM Commander.

This module handles persistence and recovery of the event queue/inbox,
including append-only event logging and efficient event removal.
"""

import asyncio
import json
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from ..models.events import Event, EventPriority, EventStatus, EventType

logger = logging.getLogger(__name__)


class EventStore:
    """Persists and recovers events.

    Provides efficient event persistence with:
    - Batch save of all events
    - Append-only logging for real-time persistence
    - Safe event removal
    - Atomic writes to prevent corruption

    Attributes:
        state_dir: Directory for state files
        events_path: Path to events.json

    Example:
        >>> store = EventStore(Path("~/.claude-mpm/commander"))
        >>> await store.save_events(inbox)
        >>> events = await store.load_events()
    """

    VERSION = "1.0"

    def __init__(self, state_dir: Path):
        """Initialize event store.

        Args:
            state_dir: Directory for state files (created if needed)
        """
        self.state_dir = state_dir.expanduser()
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.events_path = self.state_dir / "events.json"

        logger.info(f"Initialized EventStore at {self.state_dir}")

    async def save_events(self, inbox: "Inbox") -> None:  # noqa: F821
        """Save pending events to disk.

        Args:
            inbox: Inbox containing events to persist

        Raises:
            IOError: If write fails
        """
        # Get all pending events from event manager
        events = inbox.events.get_pending()

        data = {
            "version": self.VERSION,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "events": [self._serialize_event(e) for e in events],
        }

        # Run sync I/O in executor
        await asyncio.get_event_loop().run_in_executor(
            None, self._atomic_write, self.events_path, data
        )

        logger.info(f"Saved {len(events)} events to {self.events_path}")

    async def load_events(self) -> List[Event]:
        """Load events from disk.

        Returns:
            List of Event instances (empty if file missing or corrupt)
        """
        if not self.events_path.exists():
            logger.info("No events file found, returning empty list")
            return []

        try:
            # Run sync I/O in executor
            data = await asyncio.get_event_loop().run_in_executor(
                None, self._read_json, self.events_path
            )

            if data.get("version") != self.VERSION:
                logger.warning(
                    f"Version mismatch: expected {self.VERSION}, "
                    f"got {data.get('version')}"
                )

            events = [self._deserialize_event(e) for e in data.get("events", [])]

            logger.info(f"Loaded {len(events)} events from {self.events_path}")
            return events

        except Exception as e:
            logger.error(f"Failed to load events: {e}", exc_info=True)
            return []

    async def append_event(self, event: Event) -> None:
        """Append single event (for real-time persistence).

        Loads existing events, adds new event, and saves atomically.
        For high-frequency updates, consider batching with save_events().

        Args:
            event: Event to append

        Raises:
            IOError: If write fails
        """
        # Load existing events
        events = await self.load_events()

        # Add new event
        events.append(event)

        # Save back
        data = {
            "version": self.VERSION,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "events": [self._serialize_event(e) for e in events],
        }

        await asyncio.get_event_loop().run_in_executor(
            None, self._atomic_write, self.events_path, data
        )

        logger.debug(f"Appended event {event.id} to {self.events_path}")

    async def remove_event(self, event_id: str) -> None:
        """Remove resolved event from store.

        Args:
            event_id: ID of event to remove

        Raises:
            IOError: If write fails
        """
        # Load existing events
        events = await self.load_events()

        # Filter out resolved event
        filtered = [e for e in events if e.id != event_id]

        if len(filtered) == len(events):
            logger.warning(f"Event {event_id} not found in store")
            return

        # Save back
        data = {
            "version": self.VERSION,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "events": [self._serialize_event(e) for e in filtered],
        }

        await asyncio.get_event_loop().run_in_executor(
            None, self._atomic_write, self.events_path, data
        )

        logger.debug(f"Removed event {event_id} from {self.events_path}")

    def _atomic_write(self, path: Path, data: Dict) -> None:
        """Write atomically (write to temp, then rename).

        Args:
            path: Target file path
            data: Data to serialize as JSON

        Raises:
            IOError: If write fails
        """
        # Write to temporary file in same directory
        fd, tmp_path = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
        )

        try:
            with open(fd, "w") as f:
                json.dump(data, f, indent=2)

            # Atomic rename
            Path(tmp_path).rename(path)

            logger.debug(f"Atomically wrote to {path}")

        except Exception as e:
            # Clean up temp file on error
            try:
                Path(tmp_path).unlink()
            except Exception:  # nosec B110
                pass  # Ignore errors during cleanup
            raise OSError(f"Failed to write {path}: {e}") from e

    def _read_json(self, path: Path) -> Dict:
        """Read JSON file.

        Args:
            path: File to read

        Returns:
            Parsed JSON data

        Raises:
            IOError: If read fails
        """
        with open(path) as f:
            return json.load(f)

    def _serialize_event(self, event: Event) -> Dict[str, Any]:
        """Serialize Event to JSON-compatible dict.

        Args:
            event: Event instance

        Returns:
            JSON-serializable dict
        """
        return {
            "id": event.id,
            "project_id": event.project_id,
            "type": event.type.value,
            "priority": event.priority.value,
            "title": event.title,
            "session_id": event.session_id,
            "status": event.status.value,
            "content": event.content,
            "context": event.context,
            "options": event.options,
            "response": event.response,
            "responded_at": (
                event.responded_at.isoformat() if event.responded_at else None
            ),
            "created_at": event.created_at.isoformat(),
        }

    def _deserialize_event(self, data: Dict[str, Any]) -> Event:
        """Deserialize Event from JSON dict.

        Args:
            data: Serialized event data

        Returns:
            Event instance
        """
        return Event(
            id=data["id"],
            project_id=data["project_id"],
            type=EventType(data["type"]),
            priority=EventPriority(data["priority"]),
            title=data["title"],
            session_id=data.get("session_id"),
            status=EventStatus(data["status"]),
            content=data.get("content", ""),
            context=data.get("context", {}),
            options=data.get("options"),
            response=data.get("response"),
            responded_at=(
                datetime.fromisoformat(data["responded_at"])
                if data.get("responded_at")
                else None
            ),
            created_at=datetime.fromisoformat(data["created_at"]),
        )
