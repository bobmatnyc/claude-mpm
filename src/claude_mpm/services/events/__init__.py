"""
Event Bus System for Claude MPM
===============================

A decoupled event system that separates event producers from consumers,
providing reliable, testable, and maintainable event handling.

Key Components:
- EventBus: Core pub/sub system
- Event: Standard event format
- IEventProducer: Interface for event producers
- IEventConsumer: Interface for event consumers
- Various consumer implementations
"""

from .consumers import (
    DeadLetterConsumer,
    LoggingConsumer,
    MetricsConsumer,
    SocketIOConsumer,
)
from .core import Event, EventBus, EventMetadata, EventPriority
from .interfaces import ConsumerConfig, IEventConsumer, IEventProducer
from .producers import HookEventProducer, SystemEventProducer

__all__ = [
    "ConsumerConfig",
    "DeadLetterConsumer",
    # Core
    "Event",
    "EventBus",
    "EventMetadata",
    "EventPriority",
    # Producers
    "HookEventProducer",
    # Interfaces
    "IEventConsumer",
    "IEventProducer",
    "LoggingConsumer",
    "MetricsConsumer",
    # Consumers
    "SocketIOConsumer",
    "SystemEventProducer",
]
