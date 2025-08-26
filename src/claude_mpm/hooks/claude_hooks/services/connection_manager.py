"""Connection management service for Claude hook handler.

This service manages:
- SocketIO connection pool initialization
- EventBus initialization
- Event emission through both channels
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


# Import EventBus for decoupled event distribution
try:
    from claude_mpm.services.event_bus import EventBus

    EVENTBUS_AVAILABLE = True
except ImportError:
    EVENTBUS_AVAILABLE = False
    EventBus = None


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

        # Initialize EventBus for in-process event distribution (optional)
        self.event_bus = None
        self._initialize_eventbus()

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

    def _initialize_eventbus(self):
        """Initialize the EventBus for in-process distribution."""
        if EVENTBUS_AVAILABLE:
            try:
                self.event_bus = EventBus.get_instance()
                if DEBUG:
                    print("✅ EventBus initialized for hook handler", file=sys.stderr)
            except Exception as e:
                if DEBUG:
                    print(f"⚠️ Failed to initialize EventBus: {e}", file=sys.stderr)
                self.event_bus = None

    def emit_event(self, namespace: str, event: str, data: dict):
        """Emit event through both connection pool and EventBus.

        WHY dual approach:
        - Connection pool: Direct Socket.IO connection for inter-process communication
        - EventBus: For in-process subscribers (if any)
        - Ensures events reach the dashboard regardless of process boundaries
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

        # First, try to emit through direct Socket.IO connection pool
        # This is the primary path for inter-process communication
        if self.connection_pool:
            try:
                # Emit to Socket.IO server directly
                self.connection_pool.emit("claude_event", claude_event_data)
                if DEBUG:
                    print(f"✅ Emitted via connection pool: {event}", file=sys.stderr)
            except Exception as e:
                if DEBUG:
                    print(f"⚠️ Failed to emit via connection pool: {e}", file=sys.stderr)

        # Also publish to EventBus for any in-process subscribers
        if self.event_bus and EVENTBUS_AVAILABLE:
            try:
                # Publish to EventBus with topic format: hook.{event}
                topic = f"hook.{event}"
                self.event_bus.publish(topic, claude_event_data)

                # Enhanced verification logging
                if DEBUG:
                    print(f"✅ Published to EventBus: {topic}", file=sys.stderr)
                    # Get EventBus stats to verify publication
                    if hasattr(self.event_bus, "get_stats"):
                        stats = self.event_bus.get_stats()
                        print(
                            f"📊 EventBus stats after publish: {stats}", file=sys.stderr
                        )
                    # Log the number of data keys being published
                    if isinstance(claude_event_data, dict):
                        print(
                            f"📦 Published data keys: {list(claude_event_data.keys())}",
                            file=sys.stderr,
                        )
            except Exception as e:
                if DEBUG:
                    print(f"⚠️ Failed to publish to EventBus: {e}", file=sys.stderr)
                    import traceback

                    traceback.print_exc(file=sys.stderr)

        # Warn if neither method is available
        if not self.connection_pool and not self.event_bus and DEBUG:
            print(f"⚠️ No event emission method available for: {event}", file=sys.stderr)

    def cleanup(self):
        """Cleanup connections on service destruction."""
        # Clean up connection pool if it exists
        if self.connection_pool:
            try:
                self.connection_pool.cleanup()
            except:
                pass  # Ignore cleanup errors during destruction
