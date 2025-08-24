"""
Metrics Event Consumer
=====================

Collects metrics and statistics from events.
"""

import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict, List

from claude_mpm.core.logging_config import get_logger

from ..core import Event
from ..interfaces import ConsumerConfig, ConsumerPriority, IEventConsumer


class MetricsConsumer(IEventConsumer):
    """
    Collects metrics and statistics from events.

    Features:
    - Event counting by topic and type
    - Rate calculation (events per second)
    - Latency tracking
    - Top event analysis
    - Time-windowed statistics
    """

    def __init__(
        self,
        window_size: int = 300,  # 5 minutes
        top_n: int = 10,
        report_interval: float = 60.0,  # Report every minute
    ):
        """
        Initialize metrics consumer.

        Args:
            window_size: Time window for statistics (seconds)
            top_n: Number of top events to track
            report_interval: How often to report metrics (seconds)
        """
        self.logger = get_logger("MetricsConsumer")

        # Configuration
        self.window_size = window_size
        self.top_n = top_n
        self.report_interval = report_interval

        # State
        self._initialized = False
        self._last_report_time = time.time()

        # Metrics storage
        self._event_counts: Dict[str, int] = defaultdict(int)
        self._topic_counts: Dict[str, int] = defaultdict(int)
        self._type_counts: Dict[str, int] = defaultdict(int)
        self._source_counts: Dict[str, int] = defaultdict(int)

        # Time-windowed metrics
        self._recent_events: Deque[tuple] = deque()  # (timestamp, topic, type)
        self._latencies: Deque[float] = deque(maxlen=1000)

        # Error tracking
        self._error_counts: Dict[str, int] = defaultdict(int)

        # Performance metrics
        self._metrics = {
            "total_events": 0,
            "events_per_second": 0.0,
            "average_latency_ms": 0.0,
            "peak_rate": 0.0,
            "unique_topics": 0,
            "unique_types": 0,
        }

        # Consumer configuration
        self._config = ConsumerConfig(
            name="MetricsConsumer",
            topics=["**"],  # Monitor all events
            priority=ConsumerPriority.DEFERRED,  # Process after other consumers
        )

    async def initialize(self) -> bool:
        """Initialize the metrics consumer."""
        self._initialized = True
        self.logger.info("Metrics consumer initialized")
        return True

    async def consume(self, event: Event) -> bool:
        """Process a single event for metrics."""
        if not self._initialized:
            return False

        try:
            current_time = time.time()

            # Update counts
            self._event_counts[f"{event.topic}:{event.type}"] += 1
            self._topic_counts[event.topic] += 1
            self._type_counts[event.type] += 1
            self._source_counts[event.source] += 1
            self._metrics["total_events"] += 1

            # Track errors
            if event.metadata and event.metadata.consumers_failed:
                for consumer in event.metadata.consumers_failed:
                    self._error_counts[consumer] += 1

            # Add to recent events
            self._recent_events.append((current_time, event.topic, event.type))

            # Calculate latency if timestamp available
            if event.timestamp:
                latency = (current_time - event.timestamp.timestamp()) * 1000
                self._latencies.append(latency)

            # Clean old events from window
            cutoff_time = current_time - self.window_size
            while self._recent_events and self._recent_events[0][0] < cutoff_time:
                self._recent_events.popleft()

            # Report metrics periodically
            if current_time - self._last_report_time >= self.report_interval:
                await self._report_metrics()
                self._last_report_time = current_time

            return True

        except Exception as e:
            self.logger.error(f"Error processing event for metrics: {e}")
            return False

    async def consume_batch(self, events: List[Event]) -> int:
        """Process multiple events."""
        successful = 0
        for event in events:
            if await self.consume(event):
                successful += 1
        return successful

    async def shutdown(self) -> None:
        """Shutdown the consumer."""
        # Report final metrics
        await self._report_metrics()

        self.logger.info(
            f"Metrics consumer shutdown - processed {self._metrics['total_events']} events"
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
        # Calculate current metrics
        self._calculate_metrics()

        # Get top events
        top_events = sorted(
            self._event_counts.items(), key=lambda x: x[1], reverse=True
        )[: self.top_n]

        top_topics = sorted(
            self._topic_counts.items(), key=lambda x: x[1], reverse=True
        )[: self.top_n]

        return {
            **self._metrics,
            "top_events": dict(top_events),
            "top_topics": dict(top_topics),
            "error_counts": dict(self._error_counts),
            "window_size_seconds": self.window_size,
        }

    def _calculate_metrics(self) -> None:
        """Calculate current metrics."""
        # Events per second
        if self._recent_events:
            time_span = time.time() - self._recent_events[0][0]
            if time_span > 0:
                self._metrics["events_per_second"] = (
                    len(self._recent_events) / time_span
                )

        # Average latency
        if self._latencies:
            self._metrics["average_latency_ms"] = sum(self._latencies) / len(
                self._latencies
            )

        # Unique counts
        self._metrics["unique_topics"] = len(self._topic_counts)
        self._metrics["unique_types"] = len(self._type_counts)

        # Peak rate
        self._metrics["peak_rate"] = max(
            self._metrics["peak_rate"], self._metrics["events_per_second"]
        )

    async def _report_metrics(self) -> None:
        """Report current metrics to log."""
        self._calculate_metrics()

        # Build report
        report = [
            "=== Event Metrics Report ===",
            f"Total Events: {self._metrics['total_events']}",
            f"Rate: {self._metrics['events_per_second']:.2f} events/sec",
            f"Avg Latency: {self._metrics['average_latency_ms']:.1f}ms",
            f"Unique Topics: {self._metrics['unique_topics']}",
            f"Unique Types: {self._metrics['unique_types']}",
        ]

        # Add top events
        top_events = sorted(
            self._event_counts.items(), key=lambda x: x[1], reverse=True
        )[:5]

        if top_events:
            report.append("\nTop Events:")
            for event_key, count in top_events:
                report.append(f"  {event_key}: {count}")

        # Add error summary
        if self._error_counts:
            report.append("\nErrors by Consumer:")
            for consumer, count in self._error_counts.items():
                report.append(f"  {consumer}: {count}")

        # Log report
        self.logger.info("\n".join(report))
