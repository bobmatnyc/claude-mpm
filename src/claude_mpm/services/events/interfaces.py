"""
Event Bus Interfaces
===================

Defines the contracts for event producers and consumers in the event bus system.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from re import Pattern
from typing import Any

from .core import Event


class ConsumerPriority(Enum):
    """Priority levels for event consumers."""

    CRITICAL = 1  # Process first (e.g., error handlers)
    HIGH = 2  # Important consumers (e.g., Socket.IO)
    NORMAL = 3  # Default priority
    LOW = 4  # Background processing
    DEFERRED = 5  # Process last (e.g., metrics, logging)


@dataclass
class ConsumerConfig:
    """Configuration for an event consumer."""

    name: str  # Consumer identifier
    topics: list[str] | None = None  # Topics to subscribe to (None = all)
    topic_pattern: Pattern | None = None  # Regex pattern for topics
    priority: ConsumerPriority = ConsumerPriority.NORMAL
    batch_size: int = 1  # Process events in batches
    batch_timeout: float = 0.0  # Max time to wait for batch
    max_retries: int = 3  # Retry failed events
    retry_backoff: float = 1.0  # Backoff multiplier
    error_handler: Callable | None = None  # Custom error handler
    filter_func: Callable | None = None  # Event filter function
    transform_func: Callable | None = None  # Event transformation


class IEventProducer(ABC):
    """
    Interface for event producers.

    Producers create and publish events to the event bus without
    knowing about consumers or handling errors.
    """

    @abstractmethod
    async def publish(self, event: Event) -> bool:
        """
        Publish an event to the bus.

        Args:
            event: The event to publish

        Returns:
            True if event was accepted, False otherwise
        """

    @abstractmethod
    async def publish_batch(self, events: list[Event]) -> int:
        """
        Publish multiple events efficiently.

        Args:
            events: List of events to publish

        Returns:
            Number of events successfully published
        """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Get the name of this event source."""


class IEventConsumer(ABC):
    """
    Interface for event consumers.

    Consumers subscribe to events and process them asynchronously.
    Each consumer is responsible for its own error handling.
    """

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the consumer.

        Returns:
            True if initialization successful
        """

    @abstractmethod
    async def consume(self, event: Event) -> bool:
        """
        Process a single event.

        Args:
            event: The event to process

        Returns:
            True if event processed successfully
        """

    @abstractmethod
    async def consume_batch(self, events: list[Event]) -> int:
        """
        Process multiple events in a batch.

        Args:
            events: List of events to process

        Returns:
            Number of events successfully processed
        """

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the consumer gracefully."""

    @property
    @abstractmethod
    def config(self) -> ConsumerConfig:
        """Get consumer configuration."""

    @property
    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if consumer is healthy."""

    @abstractmethod
    def get_metrics(self) -> dict[str, Any]:
        """
        Get consumer metrics.

        Returns:
            Dictionary of metrics (events processed, errors, etc.)
        """


class IEventBus(ABC):
    """
    Interface for the event bus.

    The event bus manages subscriptions and routes events from
    producers to consumers.
    """

    @abstractmethod
    async def start(self) -> None:
        """Start the event bus."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the event bus gracefully."""

    @abstractmethod
    async def publish(self, event: Event) -> bool:
        """
        Publish an event to the bus.

        Args:
            event: The event to publish

        Returns:
            True if event was queued successfully
        """

    @abstractmethod
    async def subscribe(self, consumer: IEventConsumer) -> bool:
        """
        Subscribe a consumer to the bus.

        Args:
            consumer: The consumer to subscribe

        Returns:
            True if subscription successful
        """

    @abstractmethod
    async def unsubscribe(self, consumer_name: str) -> bool:
        """
        Unsubscribe a consumer from the bus.

        Args:
            consumer_name: Name of the consumer to unsubscribe

        Returns:
            True if unsubscription successful
        """

    @abstractmethod
    def get_consumers(self) -> list[IEventConsumer]:
        """Get list of active consumers."""

    @abstractmethod
    def get_metrics(self) -> dict[str, Any]:
        """
        Get event bus metrics.

        Returns:
            Dictionary of metrics (queue size, throughput, etc.)
        """

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Check if event bus is running."""
