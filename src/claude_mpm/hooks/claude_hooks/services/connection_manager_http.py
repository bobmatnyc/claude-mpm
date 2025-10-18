"""HTTP-based connection management service for Claude hook handler.

This service manages:
- HTTP POST event emission for ephemeral hook processes
- Direct event emission without EventBus complexity

DESIGN DECISION: Use stateless HTTP POST instead of persistent SocketIO
connections because hook handlers are ephemeral processes (< 1 second lifetime).
This eliminates disconnection issues and matches the process lifecycle.
"""

import asyncio
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

# Debug mode is enabled by default for better visibility into hook processing
DEBUG = os.environ.get("CLAUDE_MPM_HOOK_DEBUG", "true").lower() != "false"

# Import requests for HTTP POST communication
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

# Import high-performance event emitter - lazy loaded in _async_emit()
# to reduce hook handler initialization time by ~85% (792ms -> minimal)

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


# EventBus removed - using direct HTTP POST only
# This eliminates duplicate events and simplifies the architecture


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

        # EventBus removed - using direct HTTP POST only

        # For backward compatibility with tests
        self.connection_pool = None  # No longer used

        # Track async emit tasks to prevent garbage collection
        self._emit_tasks: set = set()

        # Thread pool for non-blocking HTTP requests
        # WHY: Prevents HTTP POST from blocking hook processing (2s timeout → 0ms blocking)
        # max_workers=2: Sufficient for low-frequency HTTP fallback events
        self._http_executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="http-emit"
        )

        if DEBUG:
            print(
                f"✅ HTTP connection manager initialized - endpoint: {self.http_endpoint}",
                file=sys.stderr,
            )

    def emit_event(self, namespace: str, event: str, data: dict):
        """Emit event using high-performance async emitter with HTTP fallback.

        WHY Hybrid approach:
        - Direct async calls for ultra-low latency in-process events
        - HTTP POST fallback for cross-process communication
        - Connection pooling for memory protection
        - Automatic routing based on availability
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

        # Try high-performance async emitter first (direct calls)
        success = self._try_async_emit(namespace, event, claude_event_data)
        if success:
            return

        # Fallback to HTTP POST for cross-process communication
        self._try_http_emit(namespace, event, claude_event_data)

    def _try_async_emit(self, namespace: str, event: str, data: dict) -> bool:
        """Try to emit event using high-performance async emitter."""
        try:
            # Run async emission in the current event loop or create one
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop, create a new one
                pass

            if loop:
                # We're in an async context, create a task with tracking
                task = loop.create_task(self._async_emit(namespace, event, data))
                self._emit_tasks.add(task)
                task.add_done_callback(self._emit_tasks.discard)
                # Don't wait for completion to maintain low latency
                if DEBUG:
                    print(f"✅ Async emit scheduled: {event}", file=sys.stderr)
                return True
            # No event loop, run synchronously
            success = asyncio.run(self._async_emit(namespace, event, data))
            if DEBUG and success:
                print(f"✅ Async emit successful: {event}", file=sys.stderr)
            return success

        except Exception as e:
            if DEBUG:
                print(f"⚠️ Async emit failed: {e}", file=sys.stderr)
            return False

    async def _async_emit(self, namespace: str, event: str, data: dict) -> bool:
        """Async helper for event emission."""
        try:
            # Lazy load event emitter to reduce initialization overhead
            from claude_mpm.services.monitor.event_emitter import get_event_emitter

            emitter = await get_event_emitter()
            return await emitter.emit_event(namespace, "claude_event", data)
        except ImportError:
            if DEBUG:
                print("⚠️ Event emitter not available", file=sys.stderr)
            return False
        except Exception as e:
            if DEBUG:
                print(f"⚠️ Async emitter error: {e}", file=sys.stderr)
            return False

    def _try_http_emit(self, namespace: str, event: str, data: dict):
        """Try to emit event using HTTP POST fallback (non-blocking).

        WHY non-blocking: HTTP POST can take up to 2 seconds (timeout),
        blocking hook processing. Thread pool makes it fire-and-forget.
        """
        if not REQUESTS_AVAILABLE:
            if DEBUG:
                print(
                    "⚠️ requests module not available - cannot emit via HTTP",
                    file=sys.stderr,
                )
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
                    print(f"✅ HTTP POST successful: {event}", file=sys.stderr)
            elif DEBUG:
                print(
                    f"⚠️ HTTP POST failed with status {response.status_code}: {event}",
                    file=sys.stderr,
                )

        except requests.exceptions.Timeout:
            if DEBUG:
                print(f"⚠️ HTTP POST timeout for: {event}", file=sys.stderr)
        except requests.exceptions.ConnectionError:
            if DEBUG:
                print(
                    f"⚠️ HTTP POST connection failed for: {event} (server not running?)",
                    file=sys.stderr,
                )
        except Exception as e:
            if DEBUG:
                print(f"⚠️ HTTP POST error for {event}: {e}", file=sys.stderr)

    def cleanup(self):
        """Cleanup connections on service destruction."""
        # Shutdown HTTP executor gracefully
        if hasattr(self, "_http_executor"):
            self._http_executor.shutdown(wait=False)
            if DEBUG:
                print("✅ HTTP executor shutdown", file=sys.stderr)
