"""HTTP-based connection management service for Claude hook handler.

This service manages:
- HTTP POST event emission for ephemeral hook processes
- Direct event emission without EventBus complexity

DESIGN DECISION: Use stateless HTTP POST instead of persistent SocketIO
connections because hook handlers are ephemeral processes (< 1 second lifetime).
This eliminates disconnection issues and matches the process lifecycle.

DESIGN DECISION: Synchronous HTTP POST only (no async)
Hook handlers are too short-lived (~25ms lifecycle) to benefit from async.
Using asyncio.run() creates event loops that close before HTTP operations complete,
causing "Event loop is closed" errors. Synchronous HTTP POST in a thread pool
is simpler and more reliable for ephemeral processes.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

# Try to import _log from hook_handler, fall back to no-op
try:
    from claude_mpm.hooks.claude_hooks.hook_handler import _log
except ImportError:

    def _log(msg: str) -> None:
        pass  # Silent fallback


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
                            "timestamp", datetime.now(timezone.utc).isoformat()
                        ),
                        "data": event_data.get("data", event_data),
                    }
                },
            )


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

        # Thread pool for non-blocking HTTP requests
        # WHY: Prevents HTTP POST from blocking hook processing (2s timeout → 0ms blocking)
        # max_workers=2: Sufficient for low-frequency hook events
        self._http_executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="http-emit"
        )

        if DEBUG:
            _log(
                f"✅ HTTP connection manager initialized - endpoint: {self.http_endpoint}"
            )

    def emit_event(self, namespace: str, event: str, data: dict):
        """Emit event using HTTP POST.

        WHY HTTP POST only:
        - Hook handlers are ephemeral (~25ms lifecycle)
        - Async emission causes "Event loop is closed" errors
        - HTTP POST in thread pool is simpler and more reliable
        - Completes in 20-50ms, which is acceptable for hook handlers
        """
        # Create event data for normalization
        raw_event = {
            "type": "hook",
            "subtype": event,  # e.g., "user_prompt", "pre_tool", "subagent_stop"
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
                _log(f"Hook handler: Publishing SubagentStop for agent '{agent_type}'")
            elif event == "pre_tool" and data.get("tool_name") == "Task":
                delegation = data.get("delegation_details", {})
                agent_type = delegation.get("agent_type", "unknown")
                _log(
                    f"Hook handler: Publishing Task delegation to agent '{agent_type}'"
                )

        # Emit via HTTP POST (non-blocking, runs in thread pool)
        self._try_http_emit(namespace, event, claude_event_data)

    def _try_http_emit(self, namespace: str, event: str, data: dict):
        """Try to emit event using HTTP POST fallback (non-blocking).

        WHY non-blocking: HTTP POST can take up to 2 seconds (timeout),
        blocking hook processing. Thread pool makes it fire-and-forget.
        """
        if not REQUESTS_AVAILABLE:
            if DEBUG:
                _log("⚠️ requests module not available - cannot emit via HTTP")
            return

        # Submit to thread pool - don't wait for result (fire-and-forget)
        self._http_executor.submit(self._http_emit_blocking, namespace, event, data)

    def _http_emit_blocking(self, namespace: str, event: str, data: dict):
        """HTTP emission in background thread (blocking operation isolated)."""
        try:
            # Create payload for HTTP API
            payload = {
                "namespace": namespace,
                "event": "claude_event",  # Standard event name for dashboard
                "data": data,
            }

            # Send HTTP POST with reasonable timeout
            response = requests.post(
                self.http_endpoint,
                json=payload,
                timeout=2.0,  # 2 second timeout
                headers={"Content-Type": "application/json"},
            )

            if response.status_code in [200, 204]:
                if DEBUG:
                    _log(f"✅ HTTP POST successful: {event}")
            elif DEBUG:
                _log(f"⚠️ HTTP POST failed with status {response.status_code}: {event}")

        except requests.exceptions.Timeout:
            if DEBUG:
                _log(f"⚠️ HTTP POST timeout for: {event}")
        except requests.exceptions.ConnectionError:
            if DEBUG:
                _log(
                    f"⚠️ HTTP POST connection failed for: {event} (server not running?)"
                )
        except Exception as e:
            if DEBUG:
                _log(f"⚠️ HTTP POST error for {event}: {e}")

    def cleanup(self):
        """Cleanup connections on service destruction."""
        # Shutdown HTTP executor gracefully
        if hasattr(self, "_http_executor"):
            self._http_executor.shutdown(wait=False)
            if DEBUG:
                _log("✅ HTTP executor shutdown")
