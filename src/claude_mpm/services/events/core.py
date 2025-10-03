"""
Event Bus Core Implementation
============================

The central event bus that manages event flow from producers to consumers.
"""

import asyncio
import contextlib
import re
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Set

from claude_mpm.core.logging_config import get_logger

from .interfaces import ConsumerPriority, IEventBus, IEventConsumer


class EventPriority(Enum):
    """Priority levels for events."""

    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


@dataclass
class EventMetadata:
    """Metadata associated with an event."""

    retry_count: int = 0
    max_retries: int = 3
    published_at: Optional[datetime] = None
    consumed_at: Optional[datetime] = None
    consumers_processed: Set[str] = field(default_factory=set)
    consumers_failed: Set[str] = field(default_factory=set)
    error_messages: List[str] = field(default_factory=list)


@dataclass
class Event:
    """
    Standard event format for the event bus.

    All events flowing through the system use this format.
    """

    id: str  # Unique event ID
    topic: str  # Event topic (e.g., "hook.response")
    type: str  # Event type (e.g., "AssistantResponse")
    timestamp: datetime  # When event was created
    source: str  # Who created the event
    data: Dict[str, Any]  # Event payload
    metadata: Optional[EventMetadata] = None  # Event metadata
    correlation_id: Optional[str] = None  # For tracking related events
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = EventMetadata()
        if not self.id:
            self.id = str(uuid.uuid4())
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)

    def matches_topic(self, pattern: str) -> bool:
        """
        Check if event matches a topic pattern.

        Supports wildcards:
        - * matches any single segment
        - ** matches any number of segments

        Examples:
        - "hook.*" matches "hook.response" but not "hook.tool.usage"
        - "hook.**" matches both "hook.response" and "hook.tool.usage"
        """
        if pattern in {"**", "*"}:
            return True

        # Convert wildcard pattern to regex
        regex_pattern = pattern.replace(".", r"\.")
        regex_pattern = regex_pattern.replace("**", ".*")
        regex_pattern = regex_pattern.replace("*", "[^.]+")
        regex_pattern = f"^{regex_pattern}$"

        return bool(re.match(regex_pattern, self.topic))


class EventBus(IEventBus):
    """
    Central event bus implementation.

    Features:
    - Async event processing
    - Topic-based routing
    - Consumer priority
    - Error isolation
    - Metrics tracking
    - Optional persistence
    """

    def __init__(
        self,
        max_queue_size: int = 10000,
        process_interval: float = 0.01,
        batch_timeout: float = 0.1,
        enable_metrics: bool = True,
        enable_persistence: bool = False,
    ):
        """
        Initialize the event bus.

        Args:
            max_queue_size: Maximum events in queue
            process_interval: How often to process events (seconds)
            batch_timeout: Max time to wait for batch (seconds)
            enable_metrics: Track metrics
            enable_persistence: Persist events to disk
        """
        self.logger = get_logger("EventBus")

        # Configuration
        self.max_queue_size = max_queue_size
        self.process_interval = process_interval
        self.batch_timeout = batch_timeout
        self.enable_metrics = enable_metrics
        self.enable_persistence = enable_persistence

        # State
        self._running = False
        self._processing_task: Optional[asyncio.Task] = None

        # Event queue (priority-based)
        self._event_queues: Dict[EventPriority, Deque[Event]] = {
            priority: deque(maxlen=max_queue_size // 4) for priority in EventPriority
        }

        # Consumers
        self._consumers: Dict[str, IEventConsumer] = {}
        self._consumer_topics: Dict[str, List[str]] = {}
        self._topic_consumers: Dict[str, Set[str]] = defaultdict(set)

        # Metrics
        self._metrics = {
            "events_published": 0,
            "events_processed": 0,
            "events_failed": 0,
            "events_dropped": 0,
            "consumers_active": 0,
            "queue_size": 0,
            "processing_time_ms": 0,
            "last_event_time": None,
        }

        # Dead letter queue for failed events
        self._dead_letter_queue: Deque[Event] = deque(maxlen=1000)

    async def start(self) -> None:
        """Start the event bus."""
        if self._running:
            self.logger.warning("Event bus already running")
            return

        self.logger.info("Starting event bus")
        self._running = True

        # Start processing task
        self._processing_task = asyncio.create_task(self._process_events())

        self.logger.info("Event bus started")

    async def stop(self) -> None:
        """Stop the event bus gracefully."""
        if not self._running:
            return

        self.logger.info("Stopping event bus")
        self._running = False

        # Wait for processing to complete
        if self._processing_task:
            self._processing_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._processing_task

        # Process remaining events
        await self._flush_events()

        # Shutdown consumers
        for consumer in self._consumers.values():
            try:
                await consumer.shutdown()
            except Exception as e:
                self.logger.error(
                    f"Error shutting down consumer {consumer.config.name}: {e}"
                )

        self.logger.info("Event bus stopped")

    async def publish(self, event: Event) -> bool:
        """
        Publish an event to the bus.

        Events are queued based on priority and processed asynchronously.
        """
        if not self._running:
            self.logger.warning("Cannot publish event - bus not running")
            return False

        # Check queue size
        total_size = sum(len(q) for q in self._event_queues.values())
        if total_size >= self.max_queue_size:
            self.logger.error(
                f"Event queue full ({total_size}/{self.max_queue_size}), dropping event"
            )
            self._metrics["events_dropped"] += 1
            return False

        # Add metadata
        if event.metadata:
            event.metadata.published_at = datetime.now(timezone.utc)

        # Queue event
        self._event_queues[event.priority].append(event)
        self._metrics["events_published"] += 1
        self._metrics["queue_size"] = total_size + 1

        self.logger.debug(
            f"Published event: {event.topic}/{event.type} (priority={event.priority.name})"
        )
        return True

    async def subscribe(self, consumer: IEventConsumer) -> bool:
        """Subscribe a consumer to the bus."""
        config = consumer.config

        if config.name in self._consumers:
            self.logger.warning(f"Consumer {config.name} already subscribed")
            return False

        try:
            # Initialize consumer
            if not await consumer.initialize():
                self.logger.error(f"Failed to initialize consumer {config.name}")
                return False

            # Register consumer
            self._consumers[config.name] = consumer

            # Register topics
            if config.topics:
                self._consumer_topics[config.name] = config.topics
                for topic in config.topics:
                    self._topic_consumers[topic].add(config.name)
            else:
                # Consumer receives all events
                self._consumer_topics[config.name] = ["**"]
                self._topic_consumers["**"].add(config.name)

            self._metrics["consumers_active"] = len(self._consumers)

            self.logger.info(
                f"Subscribed consumer {config.name} to topics: "
                f"{self._consumer_topics[config.name]}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error subscribing consumer {config.name}: {e}")
            return False

    async def unsubscribe(self, consumer_name: str) -> bool:
        """Unsubscribe a consumer from the bus."""
        if consumer_name not in self._consumers:
            self.logger.warning(f"Consumer {consumer_name} not found")
            return False

        try:
            consumer = self._consumers[consumer_name]

            # Shutdown consumer
            await consumer.shutdown()

            # Remove from registries
            del self._consumers[consumer_name]

            # Remove topic subscriptions
            if consumer_name in self._consumer_topics:
                for topic in self._consumer_topics[consumer_name]:
                    self._topic_consumers[topic].discard(consumer_name)
                del self._consumer_topics[consumer_name]

            self._metrics["consumers_active"] = len(self._consumers)

            self.logger.info(f"Unsubscribed consumer {consumer_name}")
            return True

        except Exception as e:
            self.logger.error(f"Error unsubscribing consumer {consumer_name}: {e}")
            return False

    def get_consumers(self) -> List[IEventConsumer]:
        """Get list of active consumers."""
        return list(self._consumers.values())

    def get_metrics(self) -> Dict[str, Any]:
        """Get event bus metrics."""
        return {
            **self._metrics,
            "dead_letter_queue_size": len(self._dead_letter_queue),
            "consumers": {
                name: consumer.get_metrics()
                for name, consumer in self._consumers.items()
            },
        }

    @property
    def is_running(self) -> bool:
        """Check if event bus is running."""
        return self._running

    async def _process_events(self) -> None:
        """
        Main event processing loop.

        Continuously processes events from the queue and routes them
        to appropriate consumers.
        """
        while self._running:
            try:
                # Process events by priority
                events_processed = 0

                for priority in EventPriority:
                    queue = self._event_queues[priority]

                    # Process up to batch_size events
                    batch = []
                    while queue and len(batch) < 10:
                        batch.append(queue.popleft())

                    if batch:
                        await self._route_events(batch)
                        events_processed += len(batch)

                # Update metrics
                if events_processed > 0:
                    self._metrics["events_processed"] += events_processed
                    self._metrics["last_event_time"] = datetime.now(timezone.utc)
                    self._metrics["queue_size"] = sum(
                        len(q) for q in self._event_queues.values()
                    )

                # Sleep if no events
                if events_processed == 0:
                    await asyncio.sleep(self.process_interval)

            except Exception as e:
                self.logger.error(f"Error in event processing loop: {e}")
                await asyncio.sleep(1)  # Back off on error

    async def _route_events(self, events: List[Event]) -> None:
        """
        Route events to appropriate consumers.

        Events are routed based on topic subscriptions.
        Consumers are called in priority order.
        """
        for event in events:
            # Find matching consumers
            matching_consumers = set()

            # Check exact topic matches
            if event.topic in self._topic_consumers:
                matching_consumers.update(self._topic_consumers[event.topic])

            # Check wildcard subscriptions
            for pattern, consumers in self._topic_consumers.items():
                if "*" in pattern and event.matches_topic(pattern):
                    matching_consumers.update(consumers)

            # Check consumers with no specific topics (receive all)
            if "**" in self._topic_consumers:
                matching_consumers.update(self._topic_consumers["**"])

            # Sort consumers by priority
            consumers_by_priority = defaultdict(list)
            for consumer_name in matching_consumers:
                if consumer_name in self._consumers:
                    consumer = self._consumers[consumer_name]
                    consumers_by_priority[consumer.config.priority].append(consumer)

            # Process event with each consumer
            for priority in ConsumerPriority:
                for consumer in consumers_by_priority[priority]:
                    await self._deliver_to_consumer(event, consumer)

    async def _deliver_to_consumer(
        self, event: Event, consumer: IEventConsumer
    ) -> None:
        """
        Deliver an event to a specific consumer.

        Handles errors gracefully without affecting other consumers.
        """
        try:
            # Apply filter if configured
            if consumer.config.filter_func and not consumer.config.filter_func(event):
                return

            # Apply transformation if configured
            if consumer.config.transform_func:
                event = consumer.config.transform_func(event)

            # Process event
            start_time = time.time()
            success = await consumer.consume(event)
            elapsed_ms = (time.time() - start_time) * 1000

            # Update metrics
            if success:
                event.metadata.consumers_processed.add(consumer.config.name)
                self.logger.debug(
                    f"Delivered event {event.id} to {consumer.config.name} "
                    f"({elapsed_ms:.1f}ms)"
                )
            else:
                event.metadata.consumers_failed.add(consumer.config.name)
                self.logger.warning(
                    f"Consumer {consumer.config.name} failed to process event {event.id}"
                )

                # Add to dead letter queue if all retries exhausted
                if event.metadata.retry_count >= event.metadata.max_retries:
                    self._dead_letter_queue.append(event)
                    self._metrics["events_failed"] += 1

        except Exception as e:
            self.logger.error(
                f"Error delivering event {event.id} to consumer "
                f"{consumer.config.name}: {e}"
            )
            event.metadata.consumers_failed.add(consumer.config.name)
            event.metadata.error_messages.append(str(e))

            # Use custom error handler if provided
            if consumer.config.error_handler:
                try:
                    await consumer.config.error_handler(event, e)
                except Exception as handler_error:
                    self.logger.error(
                        f"Error in custom error handler for {consumer.config.name}: "
                        f"{handler_error}"
                    )

    async def _flush_events(self) -> None:
        """Process all remaining events in the queue."""
        total_events = sum(len(q) for q in self._event_queues.values())

        if total_events > 0:
            self.logger.info(f"Flushing {total_events} remaining events")

            for priority in EventPriority:
                queue = self._event_queues[priority]
                while queue:
                    batch = []
                    for _ in range(min(10, len(queue))):
                        batch.append(queue.popleft())

                    if batch:
                        await self._route_events(batch)

            self.logger.info("Event flush complete")
