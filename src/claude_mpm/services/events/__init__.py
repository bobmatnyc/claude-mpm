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

from .core import Event, EventBus, EventMetadata, EventPriority
from .interfaces import IEventConsumer, IEventProducer, ConsumerConfig
from .consumers import (
    SocketIOConsumer,
    LoggingConsumer,
    MetricsConsumer,
    DeadLetterConsumer,
)
from .producers import HookEventProducer, SystemEventProducer

__all__ = [
    # Core
    "Event",
    "EventBus",
    "EventMetadata",
    "EventPriority",
    # Interfaces
    "IEventConsumer",
    "IEventProducer",
    "ConsumerConfig",
    # Consumers
    "SocketIOConsumer",
    "LoggingConsumer",
    "MetricsConsumer",
    "DeadLetterConsumer",
    # Producers
    "HookEventProducer",
    "SystemEventProducer",
]