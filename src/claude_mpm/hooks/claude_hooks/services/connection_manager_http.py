"""HTTP-based connection management service for Claude hook handler.

This service manages:
- HTTP POST event emission for ephemeral hook processes
- EventBus initialization (optional)
- Event emission through both channels

DESIGN DECISION: Use stateless HTTP POST instead of persistent SocketIO
connections because hook handlers are ephemeral processes (< 1 second lifetime).
This eliminates disconnection issues and matches the process lifecycle.
"""

import os
import sys
from datetime import datetime

# Debug mode is enabled by default for better visibility into hook processing
DEBUG = os.environ.get("CLAUDE_MPM_HOOK_DEBUG", "true").lower() != "false"

# Import requests for HTTP POST communication
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

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
    """Manages connections for the Claude hook handler using HTTP POST."""

    def __init__(self):
        """Initialize connection management service."""
        # Event normalizer for consistent event schema
        self.event_normalizer = EventNormalizer()

        # Server configuration for HTTP POST
        self.server_host = os.environ.get("CLAUDE_MPM_SERVER_HOST", "localhost")
        self.server_port = int(os.environ.get("CLAUDE_MPM_SERVER_PORT", "8765"))
        self.http_endpoint = f"http://{self.server_host}:{self.server_port}/api/events"

        # Initialize EventBus for in-process event distribution (optional)
        self.event_bus = None
        self._initialize_eventbus()

        # For backward compatibility with tests
        self.connection_pool = None  # No longer used

        if DEBUG:
            print(
                f"✅ HTTP connection manager initialized - endpoint: {self.http_endpoint}",
                file=sys.stderr,
            )

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
        """Emit event using HTTP POST and optionally EventBus.

        WHY HTTP POST approach:
        - Stateless: Perfect for ephemeral hook processes
        - Fire-and-forget: No connection management needed
        - Fast: Minimal overhead, no handshake
        - Reliable: Server handles buffering and retries
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

        # Primary method: HTTP POST to server
        # This is fire-and-forget with a short timeout
        if REQUESTS_AVAILABLE:
            try:
                # Send HTTP POST with short timeout (fire-and-forget pattern)
                response = requests.post(
                    self.http_endpoint,
                    json=claude_event_data,
                    timeout=0.5,  # 500ms timeout - don't wait long
                    headers={"Content-Type": "application/json"},
                )
                if DEBUG and response.status_code == 204:
                    print(f"✅ Emitted via HTTP POST: {event}", file=sys.stderr)
                elif DEBUG and response.status_code != 204:
                    print(
                        f"⚠️ HTTP POST returned status {response.status_code} for: {event}",
                        file=sys.stderr,
                    )
            except requests.exceptions.Timeout:
                # Timeout is expected for fire-and-forget pattern
                if DEBUG:
                    print(f"✅ HTTP POST sent (timeout OK): {event}", file=sys.stderr)
            except requests.exceptions.ConnectionError:
                # Server might not be running - this is OK
                if DEBUG:
                    print(f"⚠️ Server not available for: {event}", file=sys.stderr)
            except Exception as e:
                if DEBUG:
                    print(f"⚠️ Failed to emit via HTTP POST: {e}", file=sys.stderr)
        elif DEBUG:
            print(
                "⚠️ requests module not available - cannot emit via HTTP",
                file=sys.stderr,
            )

        # Also publish to EventBus for any in-process subscribers
        if self.event_bus and EVENTBUS_AVAILABLE:
            try:
                # Publish to EventBus with topic format: hook.{event}
                topic = f"hook.{event}"
                self.event_bus.publish(topic, claude_event_data)
                if DEBUG:
                    print(f"✅ Published to EventBus: {topic}", file=sys.stderr)
            except Exception as e:
                if DEBUG:
                    print(f"⚠️ Failed to publish to EventBus: {e}", file=sys.stderr)

    def cleanup(self):
        """Cleanup connections on service destruction."""
        # Nothing to cleanup for HTTP POST approach
