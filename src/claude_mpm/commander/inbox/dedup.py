"""Event deduplication logic for inbox system.

Prevents duplicate events within a configurable time window using
content hashing and time-based expiration.
"""

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict


@dataclass
class DedupEntry:
    """Deduplication cache entry.

    Tracks when an event was first seen and how many times it's appeared.

    Attributes:
        key: Unique deduplication key
        first_seen: When this key was first encountered
        count: Number of times this key has been seen
    """

    key: str
    first_seen: datetime
    count: int = 1


class EventDeduplicator:
    """Prevent duplicate events within a time window.

    Uses content hashing to detect duplicates and time-based expiration
    to automatically clean up old entries.

    The deduplication key is constructed from:
    - Project ID
    - Event type
    - Title hash (first 8 chars of MD5)

    Example:
        >>> dedup = EventDeduplicator(window_seconds=60)
        >>> dedup.is_duplicate("proj_123", "error", "Connection failed")
        False  # First occurrence
        >>> dedup.is_duplicate("proj_123", "error", "Connection failed")
        True   # Duplicate within 60 seconds
    """

    def __init__(self, window_seconds: int = 60):
        """Initialize deduplicator with time window.

        Args:
            window_seconds: Duration in seconds to consider events as duplicates.
                           Default is 60 seconds.
        """
        self.window = timedelta(seconds=window_seconds)
        self._seen: Dict[str, DedupEntry] = {}

    def make_key(self, project_id: str, event_type: str, title: str) -> str:
        """Create deduplication key from event attributes.

        Generates a key in the format: {project_id}:{event_type}:{title_hash}

        Args:
            project_id: Unique project identifier
            event_type: Type of event (from EventType enum)
            title: Event title text

        Returns:
            Composite key string for deduplication

        Example:
            >>> dedup = EventDeduplicator()
            >>> dedup.make_key("proj_123", "error", "Connection failed")
            'proj_123:error:a1b2c3d4'
        """
        title_hash = hashlib.md5(title.encode(), usedforsecurity=False).hexdigest()[:8]
        return f"{project_id}:{event_type}:{title_hash}"

    def is_duplicate(self, project_id: str, event_type: str, title: str) -> bool:
        """Check if this event is a duplicate within the window.

        Args:
            project_id: Unique project identifier
            event_type: Type of event
            title: Event title

        Returns:
            True if this is a duplicate, False if it's new

        Side Effects:
            - Increments count for duplicates
            - Creates new entry for new events
            - Cleans up expired entries

        Example:
            >>> dedup = EventDeduplicator(window_seconds=60)
            >>> dedup.is_duplicate("proj_123", "error", "Timeout")
            False  # First occurrence
            >>> dedup.is_duplicate("proj_123", "error", "Timeout")
            True   # Duplicate within window
        """
        self._cleanup_expired()
        key = self.make_key(project_id, event_type, title)

        if key in self._seen:
            self._seen[key].count += 1
            return True

        self._seen[key] = DedupEntry(
            key=key,
            first_seen=datetime.now(timezone.utc),
        )
        return False

    def _cleanup_expired(self) -> None:
        """Remove entries older than the deduplication window.

        Called automatically before each is_duplicate check to prevent
        unbounded memory growth.

        Side Effects:
            Removes all entries where (now - first_seen) > window
        """
        now = datetime.now(timezone.utc)
        expired = [k for k, v in self._seen.items() if now - v.first_seen > self.window]
        for k in expired:
            del self._seen[k]
