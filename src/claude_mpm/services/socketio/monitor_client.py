"""
SocketIO Monitor Client for claude-mpm dashboard.

WHY: This module provides a SocketIO client that connects the dashboard to the
independent monitor server, allowing the dashboard to receive events even when
running as a separate service.

DESIGN DECISIONS:
- Asynchronous client using python-socketio AsyncClient
- Automatic reconnection with exponential backoff
- Event relay from monitor to dashboard UI
- Graceful degradation when monitor is not available
- Health monitoring and connection status reporting
"""

import asyncio
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict

try:
    import socketio

    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    socketio = None

import contextlib

from ...core.logging_config import get_logger


class MonitorClient:
    """SocketIO client for connecting dashboard to monitor server.

    WHY: This client allows the dashboard service to receive events from
    the monitor server, enabling decoupled architecture where:
    - Monitor server (port 8766) collects events from hooks
    - Dashboard service (port 8765) provides UI and connects to monitor
    - Dashboard can restart without affecting event collection
    - Multiple dashboards can connect to the same monitor
    """

    def __init__(
        self,
        monitor_host: str = "localhost",
        monitor_port: int = 8766,
        auto_reconnect: bool = True,
    ):
        self.monitor_host = monitor_host
        self.monitor_port = monitor_port
        self.monitor_url = f"http://{monitor_host}:{monitor_port}"
        self.auto_reconnect = auto_reconnect

        self.logger = get_logger(__name__ + ".MonitorClient")

        # Client state
        self.client = None
        self.connected = False
        self.connecting = False
        self.should_stop = False
        self.connection_thread = None
        self.reconnect_task = None

        # Event handlers - functions to call when events are received
        self.event_handlers: Dict[str, Callable] = {}

        # Connection statistics
        self.stats = {
            "connection_attempts": 0,
            "successful_connections": 0,
            "events_received": 0,
            "last_connected": None,
            "last_disconnected": None,
            "auto_reconnect_enabled": auto_reconnect,
        }

        # Reconnection settings
        self.reconnect_delay = 1.0  # Start with 1 second
        self.max_reconnect_delay = 30.0  # Max 30 seconds between attempts
        self.reconnect_backoff = 1.5  # Exponential backoff multiplier

    def start(self) -> bool:
        """Start the monitor client and connect to monitor server."""
        if not SOCKETIO_AVAILABLE:
            self.logger.error("SocketIO not available - monitor client cannot start")
            return False

        if self.connected or self.connecting:
            self.logger.info("Monitor client already connected or connecting")
            return True

        self.logger.info(f"Starting monitor client connection to {self.monitor_url}")
        self.should_stop = False

        # Start connection in background thread
        self.connection_thread = threading.Thread(
            target=self._run_client, daemon=True, name="MonitorClient"
        )
        self.connection_thread.start()

        # Wait a moment for initial connection attempt
        time.sleep(1)
        return self.connecting or self.connected

    def stop(self):
        """Stop the monitor client and disconnect."""
        self.logger.info("Stopping monitor client")
        self.should_stop = True

        if self.reconnect_task:
            with contextlib.suppress(Exception):
                self.reconnect_task.cancel()

        if self.client and self.connected:
            try:
                # Use the event loop from the client thread
                if hasattr(self.client, "disconnect"):
                    asyncio.run(self.client.disconnect())
            except:
                pass

        self.connected = False
        self.connecting = False

        # Wait for thread to finish
        if self.connection_thread and self.connection_thread.is_alive():
            self.connection_thread.join(timeout=5)

    def add_event_handler(self, event_name: str, handler: Callable):
        """Add an event handler for a specific event type."""
        self.event_handlers[event_name] = handler
        self.logger.debug(f"Added event handler for '{event_name}'")

    def remove_event_handler(self, event_name: str):
        """Remove an event handler."""
        if event_name in self.event_handlers:
            del self.event_handlers[event_name]
            self.logger.debug(f"Removed event handler for '{event_name}'")

    def is_connected(self) -> bool:
        """Check if client is connected to monitor."""
        return self.connected

    def get_stats(self) -> Dict[str, Any]:
        """Get client connection statistics."""
        return {
            **self.stats,
            "connected": self.connected,
            "monitor_url": self.monitor_url,
            "uptime": (
                (
                    datetime.now()
                    - datetime.fromisoformat(self.stats["last_connected"])
                ).total_seconds()
                if self.stats["last_connected"] and self.connected
                else 0
            ),
        }

    def _run_client(self):
        """Run the client in its own event loop."""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Run the async client
            loop.run_until_complete(self._run_client_async())

        except Exception as e:
            self.logger.error(f"Error in monitor client thread: {e}")
        finally:
            self.connected = False
            self.connecting = False

    async def _run_client_async(self):
        """Run the async client with reconnection logic."""
        while not self.should_stop:
            try:
                await self._connect_to_monitor()

                if self.connected:
                    # Wait for disconnection or stop signal
                    while self.connected and not self.should_stop:
                        await asyncio.sleep(1)

                # Handle reconnection
                if not self.should_stop and self.auto_reconnect:
                    await self._handle_reconnection()
                else:
                    break

            except Exception as e:
                self.logger.error(f"Error in monitor client loop: {e}")
                if not self.auto_reconnect:
                    break
                await asyncio.sleep(self.reconnect_delay)

    async def _connect_to_monitor(self):
        """Establish connection to monitor server."""
        try:
            self.connecting = True
            self.stats["connection_attempts"] += 1

            self.logger.info(f"Connecting to monitor server at {self.monitor_url}")

            # Create new SocketIO client
            self.client = socketio.AsyncClient(
                logger=False,
                engineio_logger=False,
                reconnection=False,  # We handle reconnection ourselves
            )

            # Register event handlers
            self._register_client_events()

            # Connect to monitor server
            await self.client.connect(self.monitor_url)

            # Connection successful
            self.connected = True
            self.connecting = False
            self.stats["successful_connections"] += 1
            self.stats["last_connected"] = datetime.now().isoformat()
            self.reconnect_delay = 1.0  # Reset reconnect delay on successful connection

            self.logger.info(f"Connected to monitor server at {self.monitor_url}")

            # Request status from monitor
            await self.client.emit("get_status")

        except Exception as e:
            self.logger.error(f"Failed to connect to monitor server: {e}")
            self.connected = False
            self.connecting = False

            if self.client:
                with contextlib.suppress(Exception):
                    await self.client.disconnect()
                self.client = None

    def _register_client_events(self):
        """Register client-side event handlers."""

        @self.client.event
        async def connect():
            """Handle successful connection."""
            self.logger.info("Successfully connected to monitor server")

        @self.client.event
        async def disconnect():
            """Handle disconnection."""
            self.logger.info("Disconnected from monitor server")
            self.connected = False
            self.stats["last_disconnected"] = datetime.now().isoformat()

        @self.client.event
        async def connect_error(data):
            """Handle connection error."""
            self.logger.error(f"Connection error: {data}")
            self.connected = False

        @self.client.event
        async def status_response(data):
            """Handle status response from monitor."""
            self.logger.debug(f"Monitor server status: {data}")

        # Register handlers for all monitor events that we want to relay
        monitor_events = [
            "session_started",
            "session_ended",
            "claude_status",
            "claude_output",
            "agent_delegated",
            "todos_updated",
            "ticket_created",
            "memory_loaded",
            "memory_created",
            "memory_updated",
            "memory_injected",
            "file_changed",
            "git_status_changed",
            "project_analyzed",
            "connection_status",
            "heartbeat",
        ]

        for event_name in monitor_events:
            # Create a closure to capture the event name
            def make_handler(event_name):
                async def handler(data):
                    await self._handle_monitor_event(event_name, data)

                return handler

            self.client.on(event_name, make_handler(event_name))

    async def _handle_monitor_event(self, event_name: str, data: Any):
        """Handle event received from monitor server."""
        self.stats["events_received"] += 1
        self.logger.debug(f"Received event from monitor: {event_name}")

        # Call registered event handler if available
        if event_name in self.event_handlers:
            try:
                handler = self.event_handlers[event_name]
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                self.logger.error(f"Error in event handler for {event_name}: {e}")

    async def _handle_reconnection(self):
        """Handle reconnection with exponential backoff."""
        if self.should_stop:
            return

        self.logger.info(
            f"Attempting to reconnect in {self.reconnect_delay:.1f} seconds"
        )

        try:
            await asyncio.sleep(self.reconnect_delay)

            # Increase reconnect delay for next attempt (exponential backoff)
            self.reconnect_delay = min(
                self.reconnect_delay * self.reconnect_backoff, self.max_reconnect_delay
            )

        except asyncio.CancelledError:
            # Sleep was cancelled, probably due to stop()
            pass

    def send_to_monitor(self, event_name: str, data: Any = None) -> bool:
        """Send an event to the monitor server."""
        if not self.connected or not self.client:
            self.logger.warning(
                f"Cannot send event '{event_name}' - not connected to monitor"
            )
            return False

        try:
            # Schedule the emission in the client's event loop
            if hasattr(self.client, "emit"):
                # Create a simple coroutine to emit the event
                async def emit_event():
                    await self.client.emit(event_name, data)

                # Run it in the client's event loop if available
                if hasattr(self.client, "eio") and hasattr(self.client.eio, "loop"):
                    loop = self.client.eio.loop
                    if loop and not loop.is_closed():
                        asyncio.run_coroutine_threadsafe(emit_event(), loop)
                        return True

            return False

        except Exception as e:
            self.logger.error(f"Error sending event to monitor: {e}")
            return False
