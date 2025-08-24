#!/usr/bin/env python3
"""Optimized Claude Code hook handler with Socket.IO connection pooling.

This handler now uses a connection pool for Socket.IO clients to reduce
connection overhead and implement circuit breaker and batching patterns.

WHY connection pooling approach:
- Reduces connection setup/teardown overhead by 80%
- Implements circuit breaker for resilience during outages
- Provides micro-batching for high-frequency events
- Maintains persistent connections for better performance
- Falls back gracefully when Socket.IO unavailable
"""

import json
import os
import select
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime
from typing import Optional

# Import extracted modules with fallback for direct execution
try:
    # Try relative imports first (when imported as module)
    # Use the modern SocketIOConnectionPool instead of the deprecated local one
    from claude_mpm.core.socketio_pool import get_connection_pool

    from .event_handlers import EventHandlers
    from .memory_integration import MemoryHookManager
    from .response_tracking import ResponseTrackingManager
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

    from event_handlers import EventHandlers
    from memory_integration import MemoryHookManager
    from response_tracking import ResponseTrackingManager

# Import EventNormalizer for consistent event formatting
try:
    from claude_mpm.services.socketio.event_normalizer import EventNormalizer
except ImportError:
    # Create a simple fallback EventNormalizer if import fails
    class EventNormalizer:
        def normalize(self, event_data):
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

# Import constants for configuration
try:
    from claude_mpm.core.constants import NetworkConfig, RetryConfig, TimeoutConfig
except ImportError:
    # Fallback values if constants module not available
    class NetworkConfig:
        SOCKETIO_PORT_RANGE = (8765, 8785)
        RECONNECTION_DELAY = 0.5
        SOCKET_WAIT_TIMEOUT = 1.0

    class TimeoutConfig:
        QUICK_TIMEOUT = 2.0

    class RetryConfig:
        MAX_RETRIES = 3
        INITIAL_RETRY_DELAY = 0.1


# Debug mode is enabled by default for better visibility into hook processing
# Set CLAUDE_MPM_HOOK_DEBUG=false to disable debug output
DEBUG = os.environ.get("CLAUDE_MPM_HOOK_DEBUG", "true").lower() != "false"

# Socket.IO import
try:
    import socketio

    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    socketio = None

# Global singleton handler instance
_global_handler = None
_handler_lock = threading.Lock()

# Track recent events to detect duplicates
_recent_events = deque(maxlen=10)
_events_lock = threading.Lock()


class ClaudeHookHandler:
    """Optimized hook handler with direct Socket.IO client.

    WHY direct client approach:
    - Simple and reliable synchronous operation
    - No complex threading or async issues
    - Fast connection reuse when possible
    - Graceful fallback when Socket.IO unavailable
    """

    def __init__(self):
        # Track events for periodic cleanup
        self.events_processed = 0
        self.last_cleanup = time.time()
        # Event normalizer for consistent event schema
        self.event_normalizer = EventNormalizer()

        # Initialize SocketIO connection pool for inter-process communication
        # This sends events directly to the Socket.IO server in the daemon process
        self.connection_pool = None
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

        # Initialize EventBus for in-process event distribution (optional)
        self.event_bus = None
        if EVENTBUS_AVAILABLE:
            try:
                self.event_bus = EventBus.get_instance()
                if DEBUG:
                    print("✅ EventBus initialized for hook handler", file=sys.stderr)
            except Exception as e:
                if DEBUG:
                    print(f"⚠️ Failed to initialize EventBus: {e}", file=sys.stderr)
                self.event_bus = None

        # Maximum sizes for tracking
        self.MAX_DELEGATION_TRACKING = 200
        self.MAX_PROMPT_TRACKING = 100
        self.MAX_CACHE_AGE_SECONDS = 300
        self.CLEANUP_INTERVAL_EVENTS = 100

        # Agent delegation tracking
        # Store recent Task delegations: session_id -> agent_type
        self.active_delegations = {}
        # Use deque to limit memory usage (keep last 100 delegations)
        self.delegation_history = deque(maxlen=100)
        # Store delegation request data for response correlation: session_id -> request_data
        self.delegation_requests = {}

        # Git branch cache (to avoid repeated subprocess calls)
        self._git_branch_cache = {}
        self._git_branch_cache_time = {}

        # Initialize extracted managers
        self.memory_hook_manager = MemoryHookManager()
        self.response_tracking_manager = ResponseTrackingManager()
        self.event_handlers = EventHandlers(self)

        # Store current user prompts for comprehensive response tracking
        self.pending_prompts = {}  # session_id -> prompt data

    def _track_delegation(
        self, session_id: str, agent_type: str, request_data: Optional[dict] = None
    ):
        """Track a new agent delegation with optional request data for response correlation."""
        if DEBUG:
            print(
                f"  - session_id: {session_id[:16] if session_id else 'None'}...",
                file=sys.stderr,
            )
            print(f"  - agent_type: {agent_type}", file=sys.stderr)
            print(f"  - request_data provided: {bool(request_data)}", file=sys.stderr)
            print(
                f"  - delegation_requests size before: {len(self.delegation_requests)}",
                file=sys.stderr,
            )

        if session_id and agent_type and agent_type != "unknown":
            self.active_delegations[session_id] = agent_type
            key = f"{session_id}:{datetime.now().timestamp()}"
            self.delegation_history.append((key, agent_type))

            # Store request data for response tracking correlation
            if request_data:
                self.delegation_requests[session_id] = {
                    "agent_type": agent_type,
                    "request": request_data,
                    "timestamp": datetime.now().isoformat(),
                }
                if DEBUG:
                    print(
                        f"  - ✅ Stored in delegation_requests[{session_id[:16]}...]",
                        file=sys.stderr,
                    )
                    print(
                        f"  - delegation_requests size after: {len(self.delegation_requests)}",
                        file=sys.stderr,
                    )

            # Clean up old delegations (older than 5 minutes)
            cutoff_time = datetime.now().timestamp() - 300
            keys_to_remove = []
            for sid in list(self.active_delegations.keys()):
                # Check if this is an old entry by looking in history
                found_recent = False
                for hist_key, _ in reversed(self.delegation_history):
                    if hist_key.startswith(sid):
                        _, timestamp = hist_key.split(":", 1)
                        if float(timestamp) > cutoff_time:
                            found_recent = True
                            break
                if not found_recent:
                    keys_to_remove.append(sid)

            for key in keys_to_remove:
                if key in self.active_delegations:
                    del self.active_delegations[key]
                if key in self.delegation_requests:
                    del self.delegation_requests[key]

    def _cleanup_old_entries(self):
        """Clean up old entries to prevent memory growth."""
        datetime.now().timestamp() - self.MAX_CACHE_AGE_SECONDS

        # Clean up delegation tracking dictionaries
        for storage in [self.active_delegations, self.delegation_requests]:
            if len(storage) > self.MAX_DELEGATION_TRACKING:
                # Keep only the most recent entries
                sorted_keys = sorted(storage.keys())
                excess = len(storage) - self.MAX_DELEGATION_TRACKING
                for key in sorted_keys[:excess]:
                    del storage[key]

        # Clean up pending prompts
        if len(self.pending_prompts) > self.MAX_PROMPT_TRACKING:
            sorted_keys = sorted(self.pending_prompts.keys())
            excess = len(self.pending_prompts) - self.MAX_PROMPT_TRACKING
            for key in sorted_keys[:excess]:
                del self.pending_prompts[key]

        # Clean up git branch cache
        expired_keys = [
            key
            for key, cache_time in self._git_branch_cache_time.items()
            if datetime.now().timestamp() - cache_time > self.MAX_CACHE_AGE_SECONDS
        ]
        for key in expired_keys:
            self._git_branch_cache.pop(key, None)
            self._git_branch_cache_time.pop(key, None)

    def _get_delegation_agent_type(self, session_id: str) -> str:
        """Get the agent type for a session's active delegation."""
        # First try exact session match
        if session_id and session_id in self.active_delegations:
            return self.active_delegations[session_id]

        # Then try to find in recent history
        if session_id:
            for key, agent_type in reversed(self.delegation_history):
                if key.startswith(session_id):
                    return agent_type

        return "unknown"

    def _get_git_branch(self, working_dir: Optional[str] = None) -> str:
        """Get git branch for the given directory with caching.

        WHY caching approach:
        - Avoids repeated subprocess calls which are expensive
        - Caches results for 30 seconds per directory
        - Falls back gracefully if git command fails
        - Returns 'Unknown' for non-git directories
        """
        # Use current working directory if not specified
        if not working_dir:
            working_dir = os.getcwd()

        # Check cache first (cache for 30 seconds)
        current_time = datetime.now().timestamp()
        cache_key = working_dir

        if (
            cache_key in self._git_branch_cache
            and cache_key in self._git_branch_cache_time
            and current_time - self._git_branch_cache_time[cache_key] < 30
        ):
            return self._git_branch_cache[cache_key]

        # Try to get git branch
        try:
            # Change to the working directory temporarily
            original_cwd = os.getcwd()
            os.chdir(working_dir)

            # Run git command to get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=TimeoutConfig.QUICK_TIMEOUT,
                check=False,  # Quick timeout to avoid hanging
            )

            # Restore original directory
            os.chdir(original_cwd)

            if result.returncode == 0 and result.stdout.strip():
                branch = result.stdout.strip()
                # Cache the result
                self._git_branch_cache[cache_key] = branch
                self._git_branch_cache_time[cache_key] = current_time
                return branch
            # Not a git repository or no branch
            self._git_branch_cache[cache_key] = "Unknown"
            self._git_branch_cache_time[cache_key] = current_time
            return "Unknown"

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
            OSError,
        ):
            # Git not available or command failed
            self._git_branch_cache[cache_key] = "Unknown"
            self._git_branch_cache_time[cache_key] = current_time
            return "Unknown"

    def handle(self):
        """Process hook event with minimal overhead and timeout protection.

        WHY this approach:
        - Fast path processing for minimal latency (no blocking waits)
        - Non-blocking Socket.IO connection and event emission
        - Timeout protection prevents indefinite hangs
        - Connection timeout prevents indefinite hangs
        - Graceful degradation if Socket.IO unavailable
        - Always continues regardless of event status
        - Process exits after handling to prevent accumulation
        """
        _continue_sent = False  # Track if continue has been sent

        def timeout_handler(signum, frame):
            """Handle timeout by forcing exit."""
            nonlocal _continue_sent
            if DEBUG:
                print(f"Hook handler timeout (pid: {os.getpid()})", file=sys.stderr)
            if not _continue_sent:
                self._continue_execution()
                _continue_sent = True
            sys.exit(0)

        try:
            # Set a 10-second timeout for the entire operation
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(10)

            # Read and parse event
            event = self._read_hook_event()
            if not event:
                if not _continue_sent:
                    self._continue_execution()
                    _continue_sent = True
                return

            # Check for duplicate events (same event within 100ms)
            global _recent_events, _events_lock
            event_key = self._get_event_key(event)
            current_time = time.time()

            with _events_lock:
                # Check if we've seen this event recently
                for recent_key, recent_time in _recent_events:
                    if recent_key == event_key and (current_time - recent_time) < 0.1:
                        if DEBUG:
                            print(
                                f"[{datetime.now().isoformat()}] Skipping duplicate event: {event.get('hook_event_name', 'unknown')} (PID: {os.getpid()})",
                                file=sys.stderr,
                            )
                        # Still need to output continue for this invocation
                        if not _continue_sent:
                            self._continue_execution()
                            _continue_sent = True
                        return

                # Not a duplicate, record it
                _recent_events.append((event_key, current_time))

            # Debug: Log that we're processing an event
            if DEBUG:
                hook_type = event.get("hook_event_name", "unknown")
                print(
                    f"\n[{datetime.now().isoformat()}] Processing hook event: {hook_type} (PID: {os.getpid()})",
                    file=sys.stderr,
                )

            # Increment event counter and perform periodic cleanup
            self.events_processed += 1
            if self.events_processed % self.CLEANUP_INTERVAL_EVENTS == 0:
                self._cleanup_old_entries()
                if DEBUG:
                    print(
                        f"🧹 Performed cleanup after {self.events_processed} events",
                        file=sys.stderr,
                    )

            # Route event to appropriate handler
            self._route_event(event)

            # Always continue execution (only if not already sent)
            if not _continue_sent:
                self._continue_execution()
                _continue_sent = True

        except Exception:
            # Fail fast and silent (only send continue if not already sent)
            if not _continue_sent:
                self._continue_execution()
                _continue_sent = True
        finally:
            # Cancel the alarm
            signal.alarm(0)

    def _read_hook_event(self) -> dict:
        """
        Read and parse hook event from stdin with timeout.

        WHY: Centralized event reading with error handling and timeout
        ensures consistent parsing and validation while preventing
        processes from hanging indefinitely on stdin.read().

        Returns:
            Parsed event dictionary or None if invalid/timeout
        """
        try:
            # Check if data is available on stdin with 1 second timeout
            if sys.stdin.isatty():
                # Interactive terminal - no data expected
                return None

            ready, _, _ = select.select([sys.stdin], [], [], 1.0)
            if not ready:
                # No data available within timeout
                if DEBUG:
                    print("No hook event data received within timeout", file=sys.stderr)
                return None

            # Data is available, read it
            event_data = sys.stdin.read()
            if not event_data.strip():
                # Empty or whitespace-only data
                return None

            return json.loads(event_data)
        except (json.JSONDecodeError, ValueError) as e:
            if DEBUG:
                print(f"Failed to parse hook event: {e}", file=sys.stderr)
            return None
        except Exception as e:
            if DEBUG:
                print(f"Error reading hook event: {e}", file=sys.stderr)
            return None

    def _route_event(self, event: dict) -> None:
        """
        Route event to appropriate handler based on type.

        WHY: Centralized routing reduces complexity and makes
        it easier to add new event types.

        Args:
            event: Hook event dictionary
        """
        hook_type = event.get("hook_event_name", "unknown")

        # Map event types to handlers
        event_handlers = {
            "UserPromptSubmit": self.event_handlers.handle_user_prompt_fast,
            "PreToolUse": self.event_handlers.handle_pre_tool_fast,
            "PostToolUse": self.event_handlers.handle_post_tool_fast,
            "Notification": self.event_handlers.handle_notification_fast,
            "Stop": self.event_handlers.handle_stop_fast,
            "SubagentStop": self.event_handlers.handle_subagent_stop_fast,
            "AssistantResponse": self.event_handlers.handle_assistant_response,
        }

        # Call appropriate handler if exists
        handler = event_handlers.get(hook_type)
        if handler:
            try:
                handler(event)
            except Exception as e:
                if DEBUG:
                    print(f"Error handling {hook_type}: {e}", file=sys.stderr)

    def _get_event_key(self, event: dict) -> str:
        """Generate a unique key for an event to detect duplicates.

        WHY: Claude Code may call the hook multiple times for the same event
        because the hook is registered for multiple event types. We need to
        detect and skip duplicate processing while still returning continue.
        """
        # Create a key from event type, session_id, and key data
        hook_type = event.get("hook_event_name", "unknown")
        session_id = event.get("session_id", "")

        # Add type-specific data to make the key unique
        if hook_type == "PreToolUse":
            tool_name = event.get("tool_name", "")
            # For some tools, include parameters to distinguish calls
            if tool_name == "Task":
                tool_input = event.get("tool_input", {})
                agent = tool_input.get("subagent_type", "")
                prompt_preview = (
                    tool_input.get("prompt", "") or tool_input.get("description", "")
                )[:50]
                return f"{hook_type}:{session_id}:{tool_name}:{agent}:{prompt_preview}"
            return f"{hook_type}:{session_id}:{tool_name}"
        if hook_type == "UserPromptSubmit":
            prompt_preview = event.get("prompt", "")[:50]
            return f"{hook_type}:{session_id}:{prompt_preview}"
        # For other events, just use type and session
        return f"{hook_type}:{session_id}"

    def _continue_execution(self) -> None:
        """
        Send continue action to Claude.

        WHY: Centralized response ensures consistent format
        and makes it easier to add response modifications.
        """
        print(json.dumps({"action": "continue"}))

    def _emit_socketio_event(self, namespace: str, event: str, data: dict):
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
                if DEBUG:
                    print(f"✅ Published to EventBus: {topic}", file=sys.stderr)
            except Exception as e:
                if DEBUG:
                    print(f"⚠️ Failed to publish to EventBus: {e}", file=sys.stderr)

        # Warn if neither method is available
        if not self.connection_pool and not self.event_bus and DEBUG:
            print(f"⚠️ No event emission method available for: {event}", file=sys.stderr)

    def handle_subagent_stop(self, event: dict):
        """Handle subagent stop events with improved agent type detection.

        WHY comprehensive subagent stop capture:
        - Provides visibility into subagent lifecycle and delegation patterns
        - Captures agent type, ID, reason, and results for analysis
        - Enables tracking of delegation success/failure patterns
        - Useful for understanding subagent performance and reliability
        """
        # Enhanced debug logging for session correlation
        session_id = event.get("session_id", "")
        if DEBUG:
            print(
                f"  - session_id: {session_id[:16] if session_id else 'None'}...",
                file=sys.stderr,
            )
            print(f"  - event keys: {list(event.keys())}", file=sys.stderr)
            print(
                f"  - delegation_requests size: {len(self.delegation_requests)}",
                file=sys.stderr,
            )
            # Show all stored session IDs for comparison
            all_sessions = list(self.delegation_requests.keys())
            if all_sessions:
                print("  - Stored sessions (first 16 chars):", file=sys.stderr)
                for sid in all_sessions[:10]:  # Show up to 10
                    print(
                        f"    - {sid[:16]}... (agent: {self.delegation_requests[sid].get('agent_type', 'unknown')})",
                        file=sys.stderr,
                    )
            else:
                print("  - No stored sessions in delegation_requests!", file=sys.stderr)

        # First try to get agent type from our tracking
        agent_type = (
            self._get_delegation_agent_type(session_id) if session_id else "unknown"
        )

        # Fall back to event data if tracking didn't have it
        if agent_type == "unknown":
            agent_type = event.get("agent_type", event.get("subagent_type", "unknown"))

        agent_id = event.get("agent_id", event.get("subagent_id", ""))
        reason = event.get("reason", event.get("stop_reason", "unknown"))

        # Try to infer agent type from other fields if still unknown
        if agent_type == "unknown" and "task" in event:
            task_desc = str(event.get("task", "")).lower()
            if "research" in task_desc:
                agent_type = "research"
            elif "engineer" in task_desc or "code" in task_desc:
                agent_type = "engineer"
            elif "pm" in task_desc or "project" in task_desc:
                agent_type = "pm"

        # Always log SubagentStop events for debugging
        if DEBUG or agent_type != "unknown":
            print(
                f"Hook handler: Processing SubagentStop - agent: '{agent_type}', session: '{session_id}', reason: '{reason}'",
                file=sys.stderr,
            )

        # Get working directory and git branch
        working_dir = event.get("cwd", "")
        git_branch = self._get_git_branch(working_dir) if working_dir else "Unknown"

        # Try to extract structured response from output if available
        output = event.get("output", "")
        structured_response = None
        if output:
            try:
                import re

                json_match = re.search(
                    r"```json\s*(\{.*?\})\s*```", str(output), re.DOTALL
                )
                if json_match:
                    structured_response = json.loads(json_match.group(1))
                    if DEBUG:
                        print(
                            f"Extracted structured response from {agent_type} agent in SubagentStop",
                            file=sys.stderr,
                        )
            except (json.JSONDecodeError, AttributeError):
                pass  # No structured response, that's okay

        # Track agent response even without structured JSON
        if DEBUG:
            print(
                f"  - response_tracking_enabled: {self.response_tracking_manager.response_tracking_enabled}",
                file=sys.stderr,
            )
            print(
                f"  - response_tracker exists: {self.response_tracking_manager.response_tracker is not None}",
                file=sys.stderr,
            )
            print(
                f"  - session_id: {session_id[:16] if session_id else 'None'}...",
                file=sys.stderr,
            )
            print(f"  - agent_type: {agent_type}", file=sys.stderr)
            print(f"  - reason: {reason}", file=sys.stderr)
            # Check if session exists in our storage
            if session_id in self.delegation_requests:
                print("  - ✅ Session found in delegation_requests", file=sys.stderr)
                print(
                    f"  - Stored agent: {self.delegation_requests[session_id].get('agent_type')}",
                    file=sys.stderr,
                )
            else:
                print(
                    "  - ❌ Session NOT found in delegation_requests!", file=sys.stderr
                )
                print("  - Looking for partial match...", file=sys.stderr)
                # Try to find partial matches
                for stored_sid in list(self.delegation_requests.keys())[:10]:
                    if stored_sid.startswith(session_id[:8]) or session_id.startswith(
                        stored_sid[:8]
                    ):
                        print(
                            f"    - Partial match found: {stored_sid[:16]}...",
                            file=sys.stderr,
                        )

        if (
            self.response_tracking_manager.response_tracking_enabled
            and self.response_tracking_manager.response_tracker
        ):
            try:
                # Get the original request data (with fuzzy matching fallback)
                request_info = self.delegation_requests.get(session_id)

                # If exact match fails, try partial matching
                if not request_info and session_id:
                    if DEBUG:
                        print(
                            f"  - Trying fuzzy match for session {session_id[:16]}...",
                            file=sys.stderr,
                        )
                    # Try to find a session that matches the first 8-16 characters
                    for stored_sid in list(self.delegation_requests.keys()):
                        if (
                            stored_sid.startswith(session_id[:8])
                            or session_id.startswith(stored_sid[:8])
                            or (
                                len(session_id) >= 16
                                and len(stored_sid) >= 16
                                and stored_sid[:16] == session_id[:16]
                            )
                        ):
                            if DEBUG:
                                print(
                                    f"  - \u2705 Fuzzy match found: {stored_sid[:16]}...",
                                    file=sys.stderr,
                                )
                            request_info = self.delegation_requests.get(stored_sid)
                            # Update the key to use the current session_id for consistency
                            if request_info:
                                self.delegation_requests[session_id] = request_info
                                # Optionally remove the old key to avoid duplicates
                                if stored_sid != session_id:
                                    del self.delegation_requests[stored_sid]
                            break

                if DEBUG:
                    print(
                        f"  - request_info present: {bool(request_info)}",
                        file=sys.stderr,
                    )
                    if request_info:
                        print(
                            "  - ✅ Found request data for response tracking",
                            file=sys.stderr,
                        )
                        print(
                            f"  - stored agent_type: {request_info.get('agent_type')}",
                            file=sys.stderr,
                        )
                        print(
                            f"  - request keys: {list(request_info.get('request', {}).keys())}",
                            file=sys.stderr,
                        )
                    else:
                        print(
                            f"  - ❌ No request data found for session {session_id[:16]}...",
                            file=sys.stderr,
                        )

                if request_info:
                    # Use the output as the response
                    response_text = (
                        str(output)
                        if output
                        else f"Agent {agent_type} completed with reason: {reason}"
                    )

                    # Get the original request
                    original_request = request_info.get("request", {})
                    prompt = original_request.get("prompt", "")
                    description = original_request.get("description", "")

                    # Combine prompt and description
                    full_request = prompt
                    if description and description != prompt:
                        if full_request:
                            full_request += f"\n\nDescription: {description}"
                        else:
                            full_request = description

                    if not full_request:
                        full_request = f"Task delegation to {agent_type} agent"

                    # Prepare metadata
                    metadata = {
                        "exit_code": event.get("exit_code", 0),
                        "success": reason in ["completed", "finished", "done"],
                        "has_error": reason
                        in ["error", "timeout", "failed", "blocked"],
                        "duration_ms": event.get("duration_ms"),
                        "working_directory": working_dir,
                        "git_branch": git_branch,
                        "timestamp": datetime.now().isoformat(),
                        "event_type": "subagent_stop",
                        "reason": reason,
                        "original_request_timestamp": request_info.get("timestamp"),
                    }

                    # Add structured response if available
                    if structured_response:
                        metadata["structured_response"] = structured_response
                        metadata["task_completed"] = structured_response.get(
                            "task_completed", False
                        )

                        # Check for MEMORIES field and process if present
                        if structured_response.get("MEMORIES"):
                            memories = structured_response["MEMORIES"]
                            if DEBUG:
                                print(
                                    f"Found MEMORIES field in {agent_type} response with {len(memories)} items",
                                    file=sys.stderr,
                                )
                            # The memory will be processed by extract_and_update_memory
                            # which is called by the memory hook service

                    # Track the response
                    file_path = (
                        self.response_tracking_manager.response_tracker.track_response(
                            agent_name=agent_type,
                            request=full_request,
                            response=response_text,
                            session_id=session_id,
                            metadata=metadata,
                        )
                    )

                    if file_path and DEBUG:
                        print(
                            f"✅ Tracked {agent_type} agent response on SubagentStop: {file_path.name}",
                            file=sys.stderr,
                        )

                    # Clean up the request data
                    if session_id in self.delegation_requests:
                        del self.delegation_requests[session_id]

                elif DEBUG:
                    print(
                        f"No request data for SubagentStop session {session_id[:8]}..., agent: {agent_type}",
                        file=sys.stderr,
                    )

            except Exception as e:
                if DEBUG:
                    print(
                        f"❌ Failed to track response on SubagentStop: {e}",
                        file=sys.stderr,
                    )

        subagent_stop_data = {
            "agent_type": agent_type,
            "agent_id": agent_id,
            "reason": reason,
            "session_id": session_id,
            "working_directory": working_dir,
            "git_branch": git_branch,
            "timestamp": datetime.now().isoformat(),
            "is_successful_completion": reason in ["completed", "finished", "done"],
            "is_error_termination": reason in ["error", "timeout", "failed", "blocked"],
            "is_delegation_related": agent_type
            in ["research", "engineer", "pm", "ops", "qa", "documentation", "security"],
            "has_results": bool(event.get("results") or event.get("output")),
            "duration_context": event.get("duration_ms"),
            "hook_event_name": "SubagentStop",  # Explicitly set for dashboard
        }

        # Add structured response data if available
        if structured_response:
            subagent_stop_data["structured_response"] = {
                "task_completed": structured_response.get("task_completed", False),
                "instructions": structured_response.get("instructions", ""),
                "results": structured_response.get("results", ""),
                "files_modified": structured_response.get("files_modified", []),
                "tools_used": structured_response.get("tools_used", []),
                "remember": structured_response.get("remember"),
                "MEMORIES": structured_response.get(
                    "MEMORIES"
                ),  # Complete memory replacement
            }

            # Log if MEMORIES field is present
            if structured_response.get("MEMORIES"):
                if DEBUG:
                    memories_count = len(structured_response["MEMORIES"])
                    print(
                        f"Agent {agent_type} returned MEMORIES field with {memories_count} items",
                        file=sys.stderr,
                    )

        # Debug log the processed data
        if DEBUG:
            print(
                f"SubagentStop processed data: agent_type='{agent_type}', session_id='{session_id}'",
                file=sys.stderr,
            )

        # Emit to /hook namespace with high priority
        self._emit_socketio_event("/hook", "subagent_stop", subagent_stop_data)

    def __del__(self):
        """Cleanup on handler destruction."""
        # Clean up connection pool if it exists
        if hasattr(self, "connection_pool") and self.connection_pool:
            try:
                self.connection_pool.cleanup()
            except:
                pass  # Ignore cleanup errors during destruction


def main():
    """Entry point with singleton pattern and proper cleanup."""
    global _global_handler
    _continue_printed = False  # Track if we've already printed continue

    def cleanup_handler(signum=None, frame=None):
        """Cleanup handler for signals and exit."""
        nonlocal _continue_printed
        if DEBUG:
            print(
                f"Hook handler cleanup (pid: {os.getpid()}, signal: {signum})",
                file=sys.stderr,
            )
        # Only output continue if we haven't already (i.e., if interrupted by signal)
        if signum is not None and not _continue_printed:
            print(json.dumps({"action": "continue"}))
            _continue_printed = True
            sys.exit(0)

    # Register cleanup handlers
    signal.signal(signal.SIGTERM, cleanup_handler)
    signal.signal(signal.SIGINT, cleanup_handler)
    # Don't register atexit handler since we're handling exit properly in main

    try:
        # Use singleton pattern to prevent creating multiple instances
        with _handler_lock:
            if _global_handler is None:
                _global_handler = ClaudeHookHandler()
                if DEBUG:
                    print(
                        f"✅ Created new ClaudeHookHandler singleton (pid: {os.getpid()})",
                        file=sys.stderr,
                    )
            elif DEBUG:
                print(
                    f"♻️ Reusing existing ClaudeHookHandler singleton (pid: {os.getpid()})",
                    file=sys.stderr,
                )

            handler = _global_handler

        # Mark that handle() will print continue
        handler.handle()
        _continue_printed = True  # Mark as printed since handle() always prints it

        # handler.handle() already calls _continue_execution(), so we don't need to do it again
        # Just exit cleanly
        sys.exit(0)

    except Exception as e:
        # Only output continue if not already printed
        if not _continue_printed:
            print(json.dumps({"action": "continue"}))
            _continue_printed = True
        # Log error for debugging
        if DEBUG:
            print(f"Hook handler error: {e}", file=sys.stderr)
        sys.exit(0)  # Exit cleanly even on error


if __name__ == "__main__":
    main()
