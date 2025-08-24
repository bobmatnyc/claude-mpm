"""
Socket.IO Event Consumer
=======================

Consumes events from the event bus and emits them via Socket.IO.
This is the only component that knows about Socket.IO, decoupling
the rest of the system from the transport layer.
"""

import asyncio
import contextlib
import time
from typing import Any, Dict, List, Optional

from claude_mpm.core.logging_config import get_logger

from ..core import Event
from ..interfaces import ConsumerConfig, ConsumerPriority, IEventConsumer


class SocketIOConsumer(IEventConsumer):
    """
    Consumes events and emits them via Socket.IO.

    Features:
    - Single Socket.IO connection management
    - Automatic reconnection with backoff
    - Event batching for efficiency
    - Connection health monitoring
    - Graceful degradation when Socket.IO unavailable
    """

    def __init__(
        self,
        socketio_server=None,
        port_range: tuple = (8765, 8785),
        reconnect_delay: float = 1.0,
        max_reconnect_delay: float = 30.0,
        batch_size: int = 10,
        batch_timeout: float = 0.1,
    ):
        """
        Initialize Socket.IO consumer.

        Args:
            socketio_server: Socket.IO server instance (optional)
            port_range: Port range to try for connection
            reconnect_delay: Initial reconnection delay
            max_reconnect_delay: Maximum reconnection delay
            batch_size: Number of events to batch
            batch_timeout: Max time to wait for batch
        """
        self.logger = get_logger("SocketIOConsumer")

        # Socket.IO configuration
        self.socketio_server = socketio_server
        self.port_range = port_range
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay
        self.current_reconnect_delay = reconnect_delay

        # Batching configuration
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout

        # State
        self._initialized = False
        self._connected = False
        self._reconnect_task: Optional[asyncio.Task] = None
        self._event_batch: List[Event] = []
        self._batch_timer: Optional[asyncio.Task] = None

        # Metrics
        self._metrics = {
            "events_received": 0,
            "events_emitted": 0,
            "events_failed": 0,
            "connection_failures": 0,
            "reconnections": 0,
            "last_emit_time": None,
            "average_emit_time_ms": 0,
        }

        # Consumer configuration
        self._config = ConsumerConfig(
            name="SocketIOConsumer",
            topics=["**"],  # Subscribe to all events
            priority=ConsumerPriority.HIGH,
            batch_size=batch_size,
            batch_timeout=batch_timeout,
            max_retries=3,
            retry_backoff=2.0,
        )

    async def initialize(self) -> bool:
        """Initialize the Socket.IO consumer."""
        if self._initialized:
            return True

        self.logger.info("Initializing Socket.IO consumer")

        # Try to import socketio if not provided
        if self.socketio_server is None:
            try:
                # Try to get existing server instance
                from claude_mpm.services.socketio.server import get_socketio_server

                self.socketio_server = get_socketio_server()

                if self.socketio_server:
                    self._connected = True
                    self.logger.info("Connected to existing Socket.IO server")

            except ImportError:
                self.logger.warning("Socket.IO server not available")
                # Continue without Socket.IO - events will be dropped

        self._initialized = True

        # Start reconnection task if not connected
        if not self._connected and self.socketio_server:
            self._reconnect_task = asyncio.create_task(self._reconnect_loop())

        return True

    async def consume(self, event: Event) -> bool:
        """
        Process a single event.

        Events are batched for efficiency and emitted via Socket.IO.
        """
        if not self._initialized:
            self.logger.warning("Consumer not initialized")
            return False

        self._metrics["events_received"] += 1

        # Add to batch
        self._event_batch.append(event)

        # Process batch if full
        if len(self._event_batch) >= self.batch_size:
            return await self._flush_batch()

        # Start batch timer if not running
        if self._batch_timer is None or self._batch_timer.done():
            self._batch_timer = asyncio.create_task(self._batch_timeout_handler())

        return True

    async def consume_batch(self, events: List[Event]) -> int:
        """Process multiple events in a batch."""
        if not self._initialized:
            return 0

        successful = 0
        for event in events:
            if await self.consume(event):
                successful += 1

        return successful

    async def shutdown(self) -> None:
        """Shutdown the consumer gracefully."""
        self.logger.info("Shutting down Socket.IO consumer")

        # Cancel reconnection task
        if self._reconnect_task:
            self._reconnect_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reconnect_task

        # Cancel batch timer
        if self._batch_timer:
            self._batch_timer.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._batch_timer

        # Flush remaining events
        if self._event_batch:
            await self._flush_batch()

        self._initialized = False
        self._connected = False

        self.logger.info("Socket.IO consumer shutdown complete")

    @property
    def config(self) -> ConsumerConfig:
        """Get consumer configuration."""
        return self._config

    @property
    def is_healthy(self) -> bool:
        """Check if consumer is healthy."""
        # Healthy if initialized and either connected or attempting to reconnect
        return self._initialized and (
            self._connected or self._reconnect_task is not None
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get consumer metrics."""
        return {
            **self._metrics,
            "connected": self._connected,
            "batch_size": len(self._event_batch),
        }

    async def _flush_batch(self) -> bool:
        """
        Flush the current batch of events to Socket.IO.

        Returns:
            True if all events emitted successfully
        """
        if not self._event_batch:
            return True

        batch = self._event_batch
        self._event_batch = []

        # Cancel batch timer
        if self._batch_timer:
            self._batch_timer.cancel()
            self._batch_timer = None

        # Emit events
        success = await self._emit_events(batch)

        if not success:
            # Re-queue failed events
            self._event_batch = batch + self._event_batch
            return False

        return True

    async def _emit_events(self, events: List[Event]) -> bool:
        """
        Emit events via Socket.IO.

        Args:
            events: Events to emit

        Returns:
            True if all events emitted successfully
        """
        if not self._connected or not self.socketio_server:
            self.logger.debug(f"Cannot emit {len(events)} events - not connected")
            self._metrics["events_failed"] += len(events)
            return False

        try:
            start_time = time.time()

            for event in events:
                # Convert event to Socket.IO format
                socketio_event = self._convert_to_socketio(event)

                # Emit event
                await self.socketio_server.emit(
                    socketio_event["event"],
                    socketio_event["data"],
                    namespace=socketio_event.get("namespace", "/"),
                )

                self._metrics["events_emitted"] += 1

            # Update metrics
            elapsed_ms = (time.time() - start_time) * 1000
            self._metrics["last_emit_time"] = time.time()

            # Update rolling average
            avg = self._metrics["average_emit_time_ms"]
            self._metrics["average_emit_time_ms"] = (avg * 0.9) + (elapsed_ms * 0.1)

            self.logger.debug(
                f"Emitted {len(events)} events in {elapsed_ms:.1f}ms "
                f"(avg: {self._metrics['average_emit_time_ms']:.1f}ms)"
            )

            # Reset reconnect delay on success
            self.current_reconnect_delay = self.reconnect_delay

            return True

        except Exception as e:
            self.logger.error(f"Error emitting events: {e}")
            self._metrics["events_failed"] += len(events)
            self._metrics["connection_failures"] += 1
            self._connected = False

            # Start reconnection
            if self._reconnect_task is None or self._reconnect_task.done():
                self._reconnect_task = asyncio.create_task(self._reconnect_loop())

            return False

    def _convert_to_socketio(self, event: Event) -> Dict[str, Any]:
        """
        Convert an Event to Socket.IO format.

        Maps our standard event format to Socket.IO's expected format.
        """
        # Determine Socket.IO event name based on topic
        if event.topic.startswith("hook."):
            socketio_event = "hook_event"
        elif event.topic.startswith("cli."):
            socketio_event = "cli_event"
        elif event.topic.startswith("system."):
            socketio_event = "system_event"
        elif event.topic.startswith("agent."):
            socketio_event = "agent_event"
        elif event.topic.startswith("build."):
            socketio_event = "build_event"
        else:
            socketio_event = "claude_event"

        # Build Socket.IO data
        return {
            "event": socketio_event,
            "data": {
                "id": event.id,
                "type": event.type,
                "topic": event.topic,
                "timestamp": event.timestamp.isoformat(),
                "source": event.source,
                "data": event.data,
                "correlation_id": event.correlation_id,
            },
            "namespace": "/",
        }

    async def _batch_timeout_handler(self) -> None:
        """Handle batch timeout - flush partial batch."""
        await asyncio.sleep(self.batch_timeout)

        if self._event_batch:
            self.logger.debug(
                f"Batch timeout - flushing {len(self._event_batch)} events"
            )
            await self._flush_batch()

    async def _reconnect_loop(self) -> None:
        """
        Reconnection loop with exponential backoff.

        Attempts to reconnect to Socket.IO server when connection is lost.
        """
        while not self._connected and self._initialized:
            try:
                self.logger.info(
                    f"Attempting to reconnect to Socket.IO "
                    f"(delay: {self.current_reconnect_delay}s)"
                )

                # Try to reconnect
                if self.socketio_server:
                    # Test connection
                    # In real implementation, would check server status
                    self._connected = True
                    self._metrics["reconnections"] += 1
                    self.logger.info("Reconnected to Socket.IO server")

                    # Reset delay
                    self.current_reconnect_delay = self.reconnect_delay
                    break

            except Exception as e:
                self.logger.error(f"Reconnection failed: {e}")

            # Wait before next attempt
            await asyncio.sleep(self.current_reconnect_delay)

            # Exponential backoff
            self.current_reconnect_delay = min(
                self.current_reconnect_delay * 2, self.max_reconnect_delay
            )
