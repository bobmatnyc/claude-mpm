"""Connection event handlers for Socket.IO.

WHY: This module handles all connection-related events including connect,
disconnect, status requests, and history management. Separating these
from other handlers makes connection management more maintainable.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from ....core.typing_utils import ClaudeStatus, EventData, SocketId
from .base import BaseEventHandler


class ConnectionEventHandler(BaseEventHandler):
    """Handles Socket.IO connection lifecycle events.

    WHY: Connection management is a critical aspect of the Socket.IO server
    that deserves its own focused handler. This includes client connections,
    disconnections, status updates, and event history management.
    """

    def register_events(self) -> None:
        """Register connection-related event handlers."""

        @self.sio.event
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

            # Send initial status immediately with enhanced data
            status_data = {
                "server": "claude-mpm-python-socketio",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "clients_connected": len(self.clients),
                "session_id": self.server.session_id,
                "claude_status": self.server.claude_status,
                "claude_pid": self.server.claude_pid,
                "server_version": "2.0.0",
                "client_id": sid,
            }

            try:
                await self.emit_to_client(sid, "status", status_data)
                await self.emit_to_client(
                    sid,
                    "welcome",
                    {
                        "message": "Connected to Claude MPM Socket.IO server",
                        "client_id": sid,
                        "server_time": datetime.utcnow().isoformat() + "Z",
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
        async def disconnect(sid):
            """Handle client disconnection.

            WHY: We need to clean up client tracking when they disconnect
            to maintain accurate connection counts and avoid memory leaks.
            """
            if sid in self.clients:
                self.clients.remove(sid)
                self.logger.info(f"🔌 CLIENT DISCONNECTED: {sid}")
                self.logger.info(f"📉 Total clients now: {len(self.clients)}")
            else:
                self.logger.warning(
                    f"⚠️  Attempted to disconnect unknown client: {sid}"
                )

        @self.sio.event
        async def get_status(sid, data=None):
            """Handle status request.

            WHY: Clients need to query current server status on demand
            to update their UI or verify connection health.
            """
            status_data = {
                "server": "claude-mpm-python-socketio",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "clients_connected": len(self.clients),
                "session_id": self.server.session_id,
                "claude_status": self.server.claude_status,
                "claude_pid": self.server.claude_pid,
            }
            await self.emit_to_client(sid, "status", status_data)

        @self.sio.event
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
        async def subscribe(sid, data=None):
            """Handle subscription request.

            WHY: Allows clients to subscribe to specific event channels
            for filtered event streaming.
            """
            channels = data.get("channels", ["*"]) if data else ["*"]
            await self.emit_to_client(sid, "subscribed", {"channels": channels})

        @self.sio.event
        async def claude_event(sid, data):
            """Handle events from client proxies.

            WHY: Client proxies send events that need to be stored
            in history and re-broadcast to other clients.
            """
            # Add debug logging
            self.logger.info(f"🔵 Received claude_event from {sid}: {data}")
            
            # Check if this is a hook event and route to HookEventHandler
            if isinstance(data, dict) and data.get("type") == "hook":
                # Get the hook handler if available
                hook_handler = None
                # Check if event_registry exists and has handlers
                if hasattr(self.server, 'event_registry') and self.server.event_registry and hasattr(self.server.event_registry, 'handlers'):
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
            
            # Store in history
            self.event_history.append(normalized_event)
            self.logger.info(
                f"📚 Event from client stored in history (total: {len(self.event_history)})"
            )

            # Re-broadcast to all other clients
            self.logger.info(f"📡 Broadcasting claude_event to all clients except {sid}")
            await self.broadcast_event("claude_event", data, skip_sid=sid)
            self.logger.info(f"✅ Broadcast complete")

    def _normalize_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize event format to ensure consistency.
        
        WHY: Different clients may send events in different formats.
        This ensures all events have a consistent 'type' field for
        proper display in the dashboard.
        """
        if not isinstance(event_data, dict):
            return event_data
            
        # Make a copy to avoid modifying the original
        normalized = dict(event_data)
        
        # If event has no 'type' but has 'event' field (legacy format)
        if 'type' not in normalized and 'event' in normalized:
            event_name = normalized['event']
            
            # Map common event names to proper type
            if event_name in ['TestStart', 'TestEnd']:
                normalized['type'] = 'test'
            elif event_name in ['SubagentStart', 'SubagentStop']:
                normalized['type'] = 'subagent'
            elif event_name == 'ToolCall':
                normalized['type'] = 'tool'
            elif event_name == 'UserPrompt':
                normalized['type'] = 'hook.user_prompt'
            else:
                # Default to system type for unknown events
                normalized['type'] = 'system'
        
        # Ensure there's always a type field
        if 'type' not in normalized:
            normalized['type'] = 'unknown'
            
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
