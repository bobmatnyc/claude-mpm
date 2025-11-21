"""
Logging Event Consumer
=====================

Logs events for debugging and monitoring purposes.
"""

import json
from typing import Any, Dict, List, Optional

from claude_mpm.core.logging_config import get_logger

from ..core import Event
from ..interfaces import ConsumerConfig, ConsumerPriority, IEventConsumer


class LoggingConsumer(IEventConsumer):
    """
    Logs events for debugging and monitoring.

    Features:
    - Configurable log levels per topic
    - Structured logging with JSON support
    - Event filtering
    - Performance metrics
    """

    def __init__(
        self,
        log_level: str = "INFO",
        topics: Optional[List[str]] = None,
        format_json: bool = True,
        include_data: bool = True,
        max_data_length: int = 1000,
    ):
        """
        Initialize logging consumer.

        Args:
            log_level: Default log level (DEBUG, INFO, WARNING, ERROR)
            topics: Topics to log (None = all)
            format_json: Format data as JSON
            include_data: Include event data in logs
            max_data_length: Maximum data length to log
        """
        self.logger = get_logger("EventLogger")

        # Configuration
        self.log_level = log_level
        self.format_json = format_json
        self.include_data = include_data
        self.max_data_length = max_data_length

        # State
        self._initialized = False

        # Metrics
        self._metrics = {
            "events_logged": 0,
            "events_filtered": 0,
            "errors": 0,
        }

        # Consumer configuration
        self._config = ConsumerConfig(
            name="LoggingConsumer",
            topics=topics or ["**"],
            priority=ConsumerPriority.LOW,  # Log after other processing
        )

    async def initialize(self) -> bool:
        """Initialize the logging consumer."""
        self._initialized = True
        self.logger.info(
            f"Logging consumer initialized (level={self.log_level}, "
            f"topics={self._config.topics})"
        )
        return True

    async def consume(self, event: Event) -> bool:
        """Log a single event."""
        if not self._initialized:
            return False

        try:
            # Format log message
            message = self._format_event(event)

            # Determine log level
            level = self._get_log_level(event)

            # Log the event
            getattr(self.logger, level.lower())(message)

            self._metrics["events_logged"] += 1
            return True

        except Exception as e:
            self.logger.error(f"Error logging event: {e}")
            self._metrics["errors"] += 1
            return False

    async def consume_batch(self, events: List[Event]) -> int:
        """Log multiple events."""
        successful = 0
        for event in events:
            if await self.consume(event):
                successful += 1
        return successful

    async def shutdown(self) -> None:
        """Shutdown the consumer."""
        self.logger.info(
            f"Shutting down logging consumer (logged {self._metrics['events_logged']} events)"
        )
        self._initialized = False

    @property
    def config(self) -> ConsumerConfig:
        """Get consumer configuration."""
        return self._config

    @property
    def is_healthy(self) -> bool:
        """Check if consumer is healthy."""
        return self._initialized

    def get_metrics(self) -> Dict[str, Any]:
        """Get consumer metrics."""
        return self._metrics

    def _format_event(self, event: Event) -> str:
        """Format an event for logging."""
        # Build base message
        message = (
            f"[{event.topic}] {event.type} (id={event.id[:8]}, source={event.source})"
        )

        # Add data if configured
        if self.include_data and event.data:
            if self.format_json:
                data_str = json.dumps(event.data, indent=2)
            else:
                data_str = str(event.data)

            # Truncate if too long
            if len(data_str) > self.max_data_length:
                data_str = data_str[: self.max_data_length] + "..."

            message += f"\n{data_str}"

        # Add metadata if present
        if event.metadata:
            meta_info = []
            if event.metadata.retry_count > 0:
                meta_info.append(f"retries={event.metadata.retry_count}")
            if event.metadata.consumers_failed:
                meta_info.append(f"failed={event.metadata.consumers_failed}")

            if meta_info:
                message += f" [{', '.join(meta_info)}]"

        return message

    def _get_log_level(self, event: Event) -> str:
        """Determine log level for an event."""
        # Use ERROR for failed events
        if event.metadata and event.metadata.consumers_failed:
            return "ERROR"

        # Use WARNING for retried events
        if event.metadata and event.metadata.retry_count > 0:
            return "WARNING"

        # Use configured level for specific topics
        if event.topic.startswith("error."):
            return "ERROR"
        if event.topic.startswith("warning."):
            return "WARNING"
        if event.topic.startswith("debug."):
            return "DEBUG"

        # Default to configured level
        return self.log_level
