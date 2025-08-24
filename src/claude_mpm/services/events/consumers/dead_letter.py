"""
Dead Letter Queue Consumer
=========================

Handles events that failed processing in other consumers.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.logging_config import get_logger

from ..core import Event
from ..interfaces import ConsumerConfig, ConsumerPriority, IEventConsumer


class DeadLetterConsumer(IEventConsumer):
    """
    Handles failed events by persisting them for later analysis.

    Features:
    - Persist failed events to disk
    - Configurable retention policy
    - Event replay capability
    - Failed event analysis
    """

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        retention_days: int = 7,
        topics: Optional[List[str]] = None,
    ):
        """
        Initialize dead letter consumer.

        Args:
            output_dir: Directory to store failed events
            max_file_size: Maximum size per file (bytes)
            retention_days: How long to keep failed events
            topics: Topics to handle (None = all failed events)
        """
        self.logger = get_logger("DeadLetterConsumer")

        # Configuration
        self.output_dir = output_dir or Path.home() / ".claude-mpm" / "dead-letter"
        self.max_file_size = max_file_size
        self.retention_days = retention_days

        # State
        self._initialized = False
        self._current_file: Optional[Path] = None
        self._current_file_size = 0

        # Metrics
        self._metrics = {
            "events_stored": 0,
            "events_replayed": 0,
            "files_created": 0,
            "total_size_bytes": 0,
        }

        # Consumer configuration
        self._config = ConsumerConfig(
            name="DeadLetterConsumer",
            topics=topics or ["error.**", "failed.**"],
            priority=ConsumerPriority.CRITICAL,  # Process failed events first
            filter_func=self._should_store,
        )

    async def initialize(self) -> bool:
        """Initialize the dead letter consumer."""
        try:
            # Create output directory
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Clean old files
            await self._cleanup_old_files()

            # Initialize current file
            self._rotate_file()

            self._initialized = True
            self.logger.info(
                f"Dead letter consumer initialized (output: {self.output_dir})"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize dead letter consumer: {e}")
            return False

    async def consume(self, event: Event) -> bool:
        """Store a failed event."""
        if not self._initialized:
            return False

        try:
            # Serialize event
            event_data = self._serialize_event(event)
            event_json = json.dumps(event_data) + "\n"
            event_bytes = event_json.encode("utf-8")

            # Check if rotation needed
            if self._current_file_size + len(event_bytes) > self.max_file_size:
                self._rotate_file()

            # Write to file
            with open(self._current_file, "a") as f:
                f.write(event_json)

            # Update metrics
            self._current_file_size += len(event_bytes)
            self._metrics["events_stored"] += 1
            self._metrics["total_size_bytes"] += len(event_bytes)

            self.logger.debug(
                f"Stored failed event: {event.topic}/{event.type} "
                f"(reason: {event.metadata.error_messages if event.metadata else 'unknown'})"
            )

            return True

        except Exception as e:
            self.logger.error(f"Error storing failed event: {e}")
            return False

    async def consume_batch(self, events: List[Event]) -> int:
        """Store multiple failed events."""
        successful = 0
        for event in events:
            if await self.consume(event):
                successful += 1
        return successful

    async def shutdown(self) -> None:
        """Shutdown the consumer."""
        self.logger.info(
            f"Dead letter consumer shutdown - stored {self._metrics['events_stored']} events"
        )
        self._initialized = False

    async def replay_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        topic_filter: Optional[str] = None,
    ) -> List[Event]:
        """
        Replay stored events for reprocessing.

        Args:
            start_time: Start of time range
            end_time: End of time range
            topic_filter: Topic pattern to filter

        Returns:
            List of events matching criteria
        """
        replayed_events = []

        # Find files in time range
        for file_path in sorted(self.output_dir.glob("dead-letter-*.jsonl")):
            try:
                with open(file_path) as f:
                    for line in f:
                        event_data = json.loads(line)

                        # Apply filters
                        event_time = datetime.fromisoformat(event_data["timestamp"])

                        if start_time and event_time < start_time:
                            continue
                        if end_time and event_time > end_time:
                            continue
                        if topic_filter and not event_data["topic"].startswith(
                            topic_filter
                        ):
                            continue

                        # Reconstruct event
                        event = self._deserialize_event(event_data)
                        replayed_events.append(event)

            except Exception as e:
                self.logger.error(f"Error replaying events from {file_path}: {e}")

        self._metrics["events_replayed"] += len(replayed_events)
        self.logger.info(f"Replayed {len(replayed_events)} events")

        return replayed_events

    @property
    def config(self) -> ConsumerConfig:
        """Get consumer configuration."""
        return self._config

    @property
    def is_healthy(self) -> bool:
        """Check if consumer is healthy."""
        return self._initialized and self._current_file is not None

    def get_metrics(self) -> Dict[str, Any]:
        """Get consumer metrics."""
        return {
            **self._metrics,
            "current_file": str(self._current_file) if self._current_file else None,
            "current_file_size": self._current_file_size,
        }

    def _should_store(self, event: Event) -> bool:
        """
        Determine if an event should be stored.

        Only store events that have actually failed processing.
        """
        if not event.metadata:
            return False

        # Store if any consumers failed
        if event.metadata.consumers_failed:
            return True

        # Store if max retries exceeded
        if event.metadata.retry_count >= event.metadata.max_retries:
            return True

        # Store if event has error messages
        return bool(event.metadata.error_messages)

    def _serialize_event(self, event: Event) -> Dict[str, Any]:
        """Serialize an event for storage."""
        return {
            "id": event.id,
            "topic": event.topic,
            "type": event.type,
            "timestamp": event.timestamp.isoformat(),
            "source": event.source,
            "data": event.data,
            "correlation_id": event.correlation_id,
            "priority": event.priority.name,
            "metadata": (
                {
                    "retry_count": event.metadata.retry_count if event.metadata else 0,
                    "consumers_failed": (
                        list(event.metadata.consumers_failed) if event.metadata else []
                    ),
                    "error_messages": (
                        event.metadata.error_messages if event.metadata else []
                    ),
                }
                if event.metadata
                else None
            ),
        }

    def _deserialize_event(self, data: Dict[str, Any]) -> Event:
        """Deserialize an event from storage."""
        from ..core import EventMetadata, EventPriority

        # Reconstruct metadata
        metadata = None
        if data.get("metadata"):
            metadata = EventMetadata(
                retry_count=data["metadata"].get("retry_count", 0),
                consumers_failed=set(data["metadata"].get("consumers_failed", [])),
                error_messages=data["metadata"].get("error_messages", []),
            )

        return Event(
            id=data["id"],
            topic=data["topic"],
            type=data["type"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data["source"],
            data=data["data"],
            metadata=metadata,
            correlation_id=data.get("correlation_id"),
            priority=EventPriority[data.get("priority", "NORMAL")],
        )

    def _rotate_file(self) -> None:
        """Rotate to a new output file."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self._current_file = self.output_dir / f"dead-letter-{timestamp}.jsonl"
        self._current_file_size = 0
        self._metrics["files_created"] += 1

        self.logger.debug(f"Rotated to new file: {self._current_file}")

    async def _cleanup_old_files(self) -> None:
        """Remove files older than retention period."""
        cutoff_time = datetime.now().timestamp() - (self.retention_days * 86400)

        for file_path in self.output_dir.glob("dead-letter-*.jsonl"):
            try:
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    self.logger.info(f"Removed old dead letter file: {file_path}")
            except Exception as e:
                self.logger.error(f"Error removing old file {file_path}: {e}")
