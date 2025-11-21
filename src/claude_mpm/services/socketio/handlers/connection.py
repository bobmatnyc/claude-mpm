"""Connection event handlers for Socket.IO.

WHY: This module handles all connection-related events including connect,
disconnect, status requests, and history management. Separating these
from other handlers makes connection management more maintainable.
"""

import asyncio
import functools
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from claude_mpm.core.logging_utils import get_logger

from .base import BaseEventHandler

logger = get_logger(__name__)


def timeout_handler(timeout_seconds: float = 5.0):
    """Decorator to add timeout protection to async handlers.

    WHY: Network operations can hang indefinitely, causing resource leaks
    and poor user experience. This decorator ensures handlers complete
    within a reasonable time or fail gracefully.

    Args:
        timeout_seconds: Maximum time allowed for handler execution (default: 5s)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            handler_name = func.__name__
            start_time = time.time()

            try:
                # Create a task with timeout
                result = await asyncio.wait_for(
                    func(*args, **kwargs), timeout=timeout_seconds
                )

                elapsed = time.time() - start_time
                if elapsed > timeout_seconds * 0.8:  # Warn if close to timeout
                    logger.warning(
                        f"⚠️ Handler {handler_name} took {elapsed:.2f}s "
                        f"(close to {timeout_seconds}s timeout)"
                    )

                return result

            except asyncio.TimeoutError:
                elapsed = time.time() - start_time
                logger.error(
                    f"❌ Handler {handler_name} timed out after {elapsed:.2f}s"
                )

                return None

            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    f"❌ Handler {handler_name} failed after {elapsed:.2f}s: {e}"
                )
                raise

        return wrapper

    return decorator


class ConnectionEventHandler(BaseEventHandler):
    """Handles Socket.IO connection lifecycle events.

    WHY: Connection management is a critical aspect of the Socket.IO server
    that deserves its own focused handler. This includes client connections,
    disconnections, status updates, and event history management.
    """

    def __init__(self, server):
        """Initialize connection handler with health monitoring.

        WHY: We need to track connection health metrics and implement
        ping/pong mechanism for detecting stale connections.
        """
        super().__init__(server)

        # Connection health tracking
        self.connection_metrics = {}
        self.last_ping_times = {}
        self.ping_interval = 45  # seconds - avoid conflict with Engine.IO pings
        self.ping_timeout = 20  # seconds - more lenient timeout
        self.stale_check_interval = 90  # seconds - less frequent checks

        # Health monitoring tasks (will be started after event registration)
        self.ping_task = None
        self.stale_check_task = None

    def _start_health_monitoring(self):
        """Start background tasks for connection health monitoring.

        WHY: We need to actively monitor connection health to detect
        and clean up stale connections, ensuring reliable event delivery.
        """
        # Only start if we have a valid event loop and tasks aren't already running
        if hasattr(self.server, "core") and hasattr(self.server.core, "loop"):
            loop = self.server.core.loop
            if loop and not loop.is_closed():
                if not self.ping_task or self.ping_task.done():
                    self.ping_task = asyncio.run_coroutine_threadsafe(
                        self._periodic_ping(), loop
                    )
                    self.logger.info("🏓 Started connection ping monitoring")

                if not self.stale_check_task or self.stale_check_task.done():
                    self.stale_check_task = asyncio.run_coroutine_threadsafe(
                        self._check_stale_connections(), loop
                    )
                    self.logger.info("🧹 Started stale connection checker")

    def stop_health_monitoring(self):
        """Stop health monitoring tasks.

        WHY: Clean shutdown requires stopping background tasks to
        prevent errors and resource leaks.
        """
        if self.ping_task and not self.ping_task.done():
            self.ping_task.cancel()
            self.logger.info("🚫 Stopped connection ping monitoring")

        if self.stale_check_task and not self.stale_check_task.done():
            self.stale_check_task.cancel()
            self.logger.info("🚫 Stopped stale connection checker")

    async def _periodic_ping(self):
        """Send periodic pings to all connected clients.

        WHY: WebSocket connections can silently fail. Regular pings
        help detect dead connections and maintain connection state.
        """
        while True:
            try:
                await asyncio.sleep(self.ping_interval)

                if not self.clients:
                    continue

                current_time = time.time()
                disconnected = []

                for sid in list(self.clients):
                    try:
                        # Send ping and record time (using new schema)
                        await self.sio.emit(
                            "ping",
                            {
                                "type": "system",
                                "subtype": "ping",
                                "timestamp": current_time,
                                "source": "server",
                            },
                            room=sid,
                        )
                        self.last_ping_times[sid] = current_time

                        # Update connection metrics
                        if sid not in self.connection_metrics:
                            self.connection_metrics[sid] = {
                                "connected_at": current_time,
                                "reconnects": 0,
                                "failures": 0,
                                "last_activity": current_time,
                            }
                        self.connection_metrics[sid]["last_activity"] = current_time

                    except Exception as e:
                        self.logger.warning(f"Failed to ping client {sid}: {e}")
                        disconnected.append(sid)

                # Clean up failed connections
                for sid in disconnected:
                    await self._cleanup_stale_connection(sid)

                if self.clients:
                    self.logger.debug(
                        f"🏓 Sent pings to {len(self.clients)} clients, "
                        f"{len(disconnected)} failed"
                    )

            except Exception as e:
                self.logger.error(f"Error in periodic ping: {e}")

    async def _check_stale_connections(self):
        """Check for and clean up stale connections.

        WHY: Some clients may not properly disconnect, leaving zombie
        connections that consume resources and prevent proper cleanup.
        """
        while True:
            try:
                await asyncio.sleep(self.stale_check_interval)

                current_time = time.time()
                stale_threshold = current_time - (
                    self.ping_timeout + self.ping_interval
                )
                stale_sids = []

                for sid in list(self.clients):
                    last_ping = self.last_ping_times.get(sid, 0)

                    if last_ping < stale_threshold:
                        stale_sids.append(sid)
                        self.logger.warning(
                            f"🧟 Detected stale connection {sid} "
                            f"(last ping: {current_time - last_ping:.1f}s ago)"
                        )

                # Clean up stale connections
                for sid in stale_sids:
                    await self._cleanup_stale_connection(sid)

                if stale_sids:
                    self.logger.info(
                        f"🧹 Cleaned up {len(stale_sids)} stale connections"
                    )

            except Exception as e:
                self.logger.error(f"Error checking stale connections: {e}")

    async def _cleanup_stale_connection(self, sid: str):
        """Clean up a stale or dead connection.

        WHY: Proper cleanup prevents memory leaks and ensures
        accurate connection tracking.
        """
        try:
            if sid in self.clients:
                self.clients.remove(sid)

            if sid in self.last_ping_times:
                del self.last_ping_times[sid]

            if sid in self.connection_metrics:
                metrics = self.connection_metrics[sid]
                uptime = time.time() - metrics.get("connected_at", 0)
                self.logger.info(
                    f"📊 Connection {sid} stats - uptime: {uptime:.1f}s, "
                    f"reconnects: {metrics.get('reconnects', 0)}, "
                    f"failures: {metrics.get('failures', 0)}"
                )
                del self.connection_metrics[sid]

            # Force disconnect if still connected
            try:
                await self.sio.disconnect(sid)
            except Exception:
                pass  # Already disconnected

            self.logger.info(f"🔌 Cleaned up stale connection: {sid}")

        except Exception as e:
            self.logger.error(f"Error cleaning up connection {sid}: {e}")

    def register_events(self) -> None:
        """Register connection-related event handlers."""

        # Start health monitoring now that we're registering events
        self._start_health_monitoring()

        @self.sio.event
        @timeout_handler(timeout_seconds=5.0)
        async def connect(sid, environ, *args):
            """Handle client connection.

            WHY: When a client connects, we need to track them, send initial
            status information, and provide recent event history so they have
            context for what's happening in the session.
            """
            self.clients.add(sid)
            client_addr = environ.get("REMOTE_ADDR", "unknown")
            user_agent = environ.get("HTTP_USER_AGENT", "unknown")
            self.logger.info(f"🔗 NEW CLIENT CONNECTED: {sid} from {client_addr}")
            self.logger.info(f"📱 User Agent: {user_agent[:100]}...")
            self.logger.info(f"📈 Total clients now: {len(self.clients)}")

            # Get monitor build info
            monitor_build_info = {}
            try:
                from ....services.monitor_build_service import get_monitor_build_service

                monitor_service = get_monitor_build_service()
                monitor_build_info = monitor_service.get_build_info_sync()
            except Exception as e:
                self.logger.debug(f"Could not get monitor build info: {e}")
                monitor_build_info = {
                    "monitor": {
                        "version": "1.0.0",
                        "build": 1,
                        "formatted_build": "0001",
                    },
                    "mpm": {"version": "unknown", "build": "unknown"},
                }

            # Send initial status immediately with enhanced data (using new schema)
            status_data = {
                "type": "connection",
                "subtype": "status",
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "source": "server",
                "session_id": self.server.session_id,
                "data": {
                    "server": "claude-mpm-python-socketio",
                    "clients_connected": len(self.clients),
                    "claude_status": self.server.claude_status,
                    "claude_pid": self.server.claude_pid,
                    "server_version": "2.0.0",
                    "client_id": sid,
                    "build_info": monitor_build_info,
                },
            }

            try:
                await self.emit_to_client(sid, "status", status_data)
                await self.emit_to_client(
                    sid,
                    "welcome",
                    {
                        "type": "connection",
                        "subtype": "welcome",
                        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                        "source": "server",
                        "session_id": self.server.session_id,
                        "data": {
                            "message": "Connected to Claude MPM Socket.IO server",
                            "client_id": sid,
                            "server_time": datetime.now(timezone.utc).isoformat() + "Z",
                            "build_info": monitor_build_info,
                        },
                    },
                )

                # Automatically send the last 50 events to new clients
                await self._send_event_history(sid, limit=50)

                self.logger.debug(
                    f"✅ Sent welcome messages and event history to client {sid}"
                )
            except Exception as e:
                self.log_error(f"sending welcome to client {sid}", e)

        @self.sio.event
        @timeout_handler(timeout_seconds=3.0)
        async def disconnect(sid, *args):
            """Handle client disconnection.

            WHY: We need to clean up client tracking when they disconnect
            to maintain accurate connection counts and avoid memory leaks.
            """
            if sid in self.clients:
                self.clients.remove(sid)
                self.logger.info(f"🔌 CLIENT DISCONNECTED: {sid}")
                self.logger.info(f"📉 Total clients now: {len(self.clients)}")
            else:
                self.logger.warning(f"⚠️  Attempted to disconnect unknown client: {sid}")

            # Clean up health tracking
            if sid in self.last_ping_times:
                del self.last_ping_times[sid]
            if sid in self.connection_metrics:
                del self.connection_metrics[sid]

        @self.sio.event
        @timeout_handler(timeout_seconds=3.0)
        async def get_status(sid):
            """Handle status request.

            WHY: Clients need to query current server status on demand
            to update their UI or verify connection health.
            """
            status_data = {
                "type": "connection",
                "subtype": "status",
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "source": "server",
                "session_id": self.server.session_id,
                "data": {
                    "server": "claude-mpm-python-socketio",
                    "clients_connected": len(self.clients),
                    "claude_status": self.server.claude_status,
                    "claude_pid": self.server.claude_pid,
                },
            }
            await self.emit_to_client(sid, "status", status_data)

        @self.sio.event
        @timeout_handler(timeout_seconds=5.0)
        async def get_history(sid, data=None):
            """Handle history request.

            WHY: Clients may need to request specific event history
            to reconstruct state or filter by event types.
            """
            params = data or {}
            event_types = params.get("event_types", [])
            limit = min(params.get("limit", 100), len(self.event_history))

            await self._send_event_history(sid, event_types=event_types, limit=limit)

        @self.sio.event
        @timeout_handler(timeout_seconds=5.0)
        async def request_history(sid, data=None):
            """Handle legacy history request (for client compatibility).

            WHY: Maintains backward compatibility with clients using
            the older 'request.history' event name.
            """
            params = data or {}
            event_types = params.get("event_types", [])
            limit = min(params.get("limit", 50), len(self.event_history))

            await self._send_event_history(sid, event_types=event_types, limit=limit)

        @self.sio.event
        @timeout_handler(timeout_seconds=3.0)
        async def subscribe(sid, data=None):
            """Handle subscription request.

            WHY: Allows clients to subscribe to specific event channels
            for filtered event streaming.
            """
            channels = data.get("channels", ["*"]) if data else ["*"]
            await self.emit_to_client(
                sid,
                "subscribed",
                {
                    "type": "connection",
                    "subtype": "subscribed",
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    "source": "server",
                    "data": {"channels": channels},
                },
            )

        @self.sio.event
        @timeout_handler(timeout_seconds=5.0)
        async def claude_event(sid, data):
            """Handle events from client proxies.

            WHY: Client proxies send events that need to be stored
            in history and re-broadcast to other clients.
            """
            # Add debug logging
            self.logger.info(f"🔵 Received claude_event from {sid}: {data}")

            # Check if this is a hook event and route to HookEventHandler
            # Hook events can have either:
            # 1. Normalized format: type="hook", subtype="pre_tool"
            # 2. Legacy format: type="hook.pre_tool"
            if isinstance(data, dict):
                event_type = data.get("type", "")
                data.get("subtype", "")

                # Check for both normalized and legacy formats
                is_hook_event = False
                if isinstance(event_type, str):
                    # Legacy format: type="hook.something"
                    if event_type.startswith("hook.") or event_type == "hook":
                        is_hook_event = True

                if is_hook_event:
                    # Get the hook handler if available
                    hook_handler = None
                    # Check if event_registry exists and has handlers
                    if (
                        hasattr(self.server, "event_registry")
                        and self.server.event_registry
                    ) and hasattr(self.server.event_registry, "handlers"):
                        for handler in self.server.event_registry.handlers:
                            if handler.__class__.__name__ == "HookEventHandler":
                                hook_handler = handler
                                break

                    if hook_handler and hasattr(hook_handler, "process_hook_event"):
                        # Let the hook handler process this event
                        await hook_handler.process_hook_event(data)
                        # Don't double-store or double-broadcast, return early
                        return

            # Normalize event format before storing in history
            normalized_event = self._normalize_event(data)

            # Store in history - flatten if it's a nested structure
            # If the normalized event has data.event, promote it to top level
            if isinstance(normalized_event, dict) and "data" in normalized_event:
                if (
                    isinstance(normalized_event["data"], dict)
                    and "event" in normalized_event["data"]
                ):
                    # This is a nested event, flatten it
                    flattened = {
                        "type": normalized_event.get("type", "unknown"),
                        "event": normalized_event["data"].get("event"),
                        "timestamp": normalized_event.get("timestamp")
                        or normalized_event["data"].get("timestamp"),
                        "data": normalized_event["data"].get("data", {}),
                    }
                    self.event_history.append(flattened)
                else:
                    self.event_history.append(normalized_event)
            else:
                self.event_history.append(normalized_event)
            self.logger.info(
                f"📚 Event from client stored in history (total: {len(self.event_history)})"
            )

            # Re-broadcast to all other clients
            self.logger.info(
                f"📡 Broadcasting claude_event to all clients except {sid}"
            )
            await self.broadcast_event("claude_event", data, skip_sid=sid)
            self.logger.info("✅ Broadcast complete")

        @self.sio.event
        async def pong(sid, data=None):
            """Handle pong response from client.

            WHY: Clients respond to our pings with pongs, confirming
            they're still alive and the connection is healthy.
            """
            current_time = time.time()

            # Update last activity time
            if sid in self.connection_metrics:
                self.connection_metrics[sid]["last_activity"] = current_time

            # Calculate round-trip time if timestamp provided
            if data and "timestamp" in data:
                rtt = current_time - data["timestamp"]
                if rtt < 10:  # Reasonable RTT
                    self.logger.debug(f"🏓 Pong from {sid}, RTT: {rtt * 1000:.1f}ms")

    def _normalize_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize event format to ensure consistency.

        WHY: Different clients may send events in different formats.
        This ensures all events have a consistent 'type' field for
        proper display in the dashboard, while preserving the original
        'event' field for hook events.
        """
        if not isinstance(event_data, dict):
            return event_data

        # Make a copy to avoid modifying the original
        normalized = dict(event_data)

        # If event has no 'type' but has 'event' field (legacy format)
        if "type" not in normalized and "event" in normalized:
            event_name = normalized["event"]

            # Map common event names to proper type
            if event_name in ["TestStart", "TestEnd"]:
                normalized["type"] = "test"
            elif event_name in ["SubagentStart", "SubagentStop"]:
                normalized["type"] = "subagent"
            elif event_name == "ToolCall":
                normalized["type"] = "tool"
            elif event_name == "UserPrompt":
                normalized["type"] = "hook"
                normalized["subtype"] = "user_prompt"
            else:
                # Default to system type for unknown events
                normalized["type"] = "system"

            # Note: We keep the 'event' field for backward compatibility
            # Dashboard may use it for display purposes

        # Ensure there's always a type field
        if "type" not in normalized:
            normalized["type"] = "unknown"

        return normalized

    async def _send_event_history(
        self, sid: str, event_types: Optional[List[str]] = None, limit: int = 50
    ):
        """Send event history to a specific client.

        WHY: When clients connect to the dashboard, they need context from recent events
        to understand what's been happening. This sends the most recent events in
        chronological order (oldest first) so the dashboard displays them properly.

        Args:
            sid: Socket.IO session ID of the client
            event_types: Optional list of event types to filter by
            limit: Maximum number of events to send (default: 50)
        """
        try:
            if not self.event_history:
                self.logger.debug(f"No event history to send to client {sid}")
                return

            # Limit to reasonable number to avoid overwhelming client
            limit = min(limit, 100)

            # Get the most recent events, filtered by type if specified
            history = []
            for event in reversed(self.event_history):
                if not event_types or event.get("type") in event_types:
                    history.append(event)
                    if len(history) >= limit:
                        break

            # Reverse to get chronological order (oldest first)
            history = list(reversed(history))

            if history:
                # Send as 'history' event that the client expects
                await self.emit_to_client(
                    sid,
                    "history",
                    {
                        "events": history,
                        "count": len(history),
                        "total_available": len(self.event_history),
                    },
                )

                self.logger.info(
                    f"📚 Sent {len(history)} historical events to client {sid}"
                )
            else:
                self.logger.debug(
                    f"No matching events found for client {sid} with filters: {event_types}"
                )

        except Exception as e:
            self.log_error(
                f"sending event history to client {sid}",
                e,
                {"event_types": event_types, "limit": limit},
            )
