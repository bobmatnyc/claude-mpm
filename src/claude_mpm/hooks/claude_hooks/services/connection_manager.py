"""Connection management service for Claude hook handler.

This service implements the SINGLE-PATH EVENT EMISSION ARCHITECTURE
to eliminate duplicate events and improve performance.

ARCHITECTURE: Hook → ConnectionManager → Direct Socket.IO → Dashboard
                                      ↓ (fallback only)
                                    HTTP POST → Monitor → Dashboard

CRITICAL: This service must maintain the single emission path principle.
See docs/developer/EVENT_EMISSION_ARCHITECTURE.md for full documentation.

This service manages:
- SocketIO connection pool initialization
- Direct event emission with HTTP fallback
- Connection cleanup
"""

import os
import sys
from datetime import datetime

# Debug mode is enabled by default for better visibility into hook processing
DEBUG = os.environ.get("CLAUDE_MPM_HOOK_DEBUG", "true").lower() != "false"

# Import extracted modules with fallback for direct execution
try:
    # Try relative imports first (when imported as module)
    # Use the modern SocketIOConnectionPool instead of the deprecated local one
    from claude_mpm.core.socketio_pool import get_connection_pool
except ImportError:
    # Fall back to absolute imports (when run directly)
    from pathlib import Path

    # Add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent))

    # Try to import get_connection_pool from deprecated location
    try:
        from connection_pool import SocketIOConnectionPool

        def get_connection_pool():
            return SocketIOConnectionPool()

    except ImportError:
        get_connection_pool = None

# Import EventNormalizer for consistent event formatting
try:
    from claude_mpm.services.socketio.event_normalizer import EventNormalizer
except ImportError:
    # Create a simple fallback EventNormalizer if import fails
    class EventNormalizer:
        def normalize(self, event_data, source="hook"):
            """Simple fallback normalizer that returns event as-is."""
            return type(
                "NormalizedEvent",
                (),
                {
                    "to_dict": lambda: {
                        "event": "claude_event",
                        "type": event_data.get("type", "unknown"),
                        "subtype": event_data.get("subtype", "generic"),
                        "timestamp": event_data.get(
                            "timestamp", datetime.now().isoformat()
                        ),
                        "data": event_data.get("data", event_data),
                    }
                },
            )


# EventBus removed - using direct Socket.IO calls with HTTP fallback
# This eliminates duplicate events and improves performance


class ConnectionManagerService:
    """Manages connections for the Claude hook handler."""

    def __init__(self):
        """Initialize connection management service."""
        # Event normalizer for consistent event schema
        self.event_normalizer = EventNormalizer()

        # Initialize SocketIO connection pool for inter-process communication
        # This sends events directly to the Socket.IO server in the daemon process
        self.connection_pool = None
        self._initialize_socketio_pool()

        # EventBus removed - using direct Socket.IO with HTTP fallback only

    def _initialize_socketio_pool(self):
        """Initialize the SocketIO connection pool."""
        try:
            self.connection_pool = get_connection_pool()
            if DEBUG:
                print("✅ Modern SocketIO connection pool initialized", file=sys.stderr)
        except Exception as e:
            if DEBUG:
                print(
                    f"⚠️ Failed to initialize SocketIO connection pool: {e}",
                    file=sys.stderr,
                )
            self.connection_pool = None

    def emit_event(self, namespace: str, event: str, data: dict):
        """Emit event through direct Socket.IO connection with HTTP fallback.

        🚨 CRITICAL: This method implements the SINGLE-PATH EMISSION ARCHITECTURE.
        DO NOT add additional emission paths (EventBus, etc.) as this creates duplicates.
        See docs/developer/EVENT_EMISSION_ARCHITECTURE.md for details.

        High-performance single-path approach:
        - Primary: Direct Socket.IO connection for ultra-low latency
        - Fallback: HTTP POST for reliability when direct connection fails
        - Eliminates duplicate events from multiple emission paths
        """
        # Create event data for normalization
        raw_event = {
            "type": "hook",
            "subtype": event,  # e.g., "user_prompt", "pre_tool", "subagent_stop"
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "source": "claude_hooks",  # Identify the source
            "session_id": data.get("sessionId"),  # Include session if available
        }

        # Normalize the event using EventNormalizer for consistent schema
        normalized_event = self.event_normalizer.normalize(raw_event, source="hook")
        claude_event_data = normalized_event.to_dict()

        # Log important events for debugging
        if DEBUG and event in ["subagent_stop", "pre_tool"]:
            if event == "subagent_stop":
                agent_type = data.get("agent_type", "unknown")
                print(
                    f"Hook handler: Publishing SubagentStop for agent '{agent_type}'",
                    file=sys.stderr,
                )
            elif event == "pre_tool" and data.get("tool_name") == "Task":
                delegation = data.get("delegation_details", {})
                agent_type = delegation.get("agent_type", "unknown")
                print(
                    f"Hook handler: Publishing Task delegation to agent '{agent_type}'",
                    file=sys.stderr,
                )

        # Emit through direct Socket.IO connection pool (primary path)
        # This provides ultra-low latency direct async communication
        if self.connection_pool:
            try:
                # Emit to Socket.IO server directly
                self.connection_pool.emit("claude_event", claude_event_data)
                if DEBUG:
                    print(f"✅ Emitted via connection pool: {event}", file=sys.stderr)
                return  # Success - no need for fallback
            except Exception as e:
                if DEBUG:
                    print(f"⚠️ Failed to emit via connection pool: {e}", file=sys.stderr)

        # HTTP fallback for cross-process communication (when direct calls fail)
        # This replaces EventBus for reliability without the complexity
        self._try_http_fallback(claude_event_data)

    def _try_http_fallback(self, claude_event_data: dict):
        """HTTP fallback when direct Socket.IO connection fails."""
        try:
            import requests

            # Send to monitor server HTTP API
            response = requests.post(
                "http://localhost:8765/api/events",
                json=claude_event_data,
                timeout=2.0,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code in [200, 204]:
                if DEBUG:
                    print("✅ HTTP fallback successful", file=sys.stderr)
            elif DEBUG:
                print(
                    f"⚠️ HTTP fallback failed: {response.status_code}",
                    file=sys.stderr,
                )

        except Exception as e:
            if DEBUG:
                print(f"⚠️ HTTP fallback error: {e}", file=sys.stderr)

        # Warn if no emission method is available
        if not self.connection_pool and DEBUG:
            print(f"⚠️ No event emission method available for: {event}", file=sys.stderr)

    def cleanup(self):
        """Cleanup connections on service destruction."""
        # Clean up connection pool if it exists
        if self.connection_pool:
            try:
                self.connection_pool.cleanup()
            except:
                pass  # Ignore cleanup errors during destruction
