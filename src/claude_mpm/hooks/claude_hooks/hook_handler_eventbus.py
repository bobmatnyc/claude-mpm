#!/usr/bin/env python3
"""Optimized Claude Code hook handler with EventBus architecture.

This handler uses the EventBus for decoupled event emission instead of
direct Socket.IO connections. This provides better separation of concerns
and improved testability.

WHY EventBus approach:
- Decouples hook processing from Socket.IO implementation
- Enables multiple event consumers without code changes
- Simplifies testing by removing Socket.IO dependencies
- Provides centralized event routing and filtering
- Maintains backward compatibility with existing hooks
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
from pathlib import Path
from typing import Optional

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Import EventBus
try:
    from claude_mpm.services.event_bus import EventBus

    EVENTBUS_AVAILABLE = True
except ImportError:
    EVENTBUS_AVAILABLE = False
    EventBus = None

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
                        "source": source,
                    }
                },
            )


# Import constants for configuration
try:
    from claude_mpm.core.constants import TimeoutConfig
except ImportError:
    # Fallback values if constants module not available
    class TimeoutConfig:
        QUICK_TIMEOUT = 2.0


# Import other handler modules
try:
    from .event_handlers import EventHandlers
    from .memory_integration import MemoryHookManager
    from .response_tracking import ResponseTrackingManager
except ImportError:
    # Fallback for direct execution
    from event_handlers import EventHandlers
    from memory_integration import MemoryHookManager
    from response_tracking import ResponseTrackingManager

# Debug mode is enabled by default for better visibility into hook processing
DEBUG = os.environ.get("CLAUDE_MPM_HOOK_DEBUG", "true").lower() != "false"

# Global singleton handler instance
_global_handler = None
_handler_lock = threading.Lock()

# Track recent events to detect duplicates
_recent_events = deque(maxlen=10)
_events_lock = threading.Lock()


class HookHandler:
    """Main hook handler class using EventBus for event emission.

    WHY EventBus integration:
    - Replaces direct Socket.IO connections with EventBus publishing
    - Events are published once and consumed by multiple listeners
    - Failures in one consumer don't affect others
    - Simplified testing without Socket.IO dependencies
    """

    # Tracking dictionaries with size limits
    MAX_DELEGATION_TRACKING = 100
    MAX_PROMPT_TRACKING = 50
    MAX_CACHE_AGE_SECONDS = 1800  # 30 minutes

    def __init__(self):
        """Initialize the hook handler with EventBus."""
        # Initialize EventBus if available
        self.event_bus = EventBus.get_instance() if EVENTBUS_AVAILABLE else None
        self.event_normalizer = EventNormalizer()

        # Initialize tracking managers
        self.memory_manager = MemoryHookManager()
        self.response_tracker = ResponseTrackingManager()
        self.event_handlers = EventHandlers(self)

        # Delegation tracking
        self.active_delegations = {}
        self.delegation_requests = {}
        self.delegation_history = deque(maxlen=20)

        # Prompt tracking
        self.pending_prompts = {}

        # Git branch caching
        self._git_branch_cache = {}
        self._git_branch_cache_time = {}

        # Session tracking
        self.current_session_id = None

        # Cleanup old entries periodically
        self._last_cleanup = time.time()

        if self.event_bus:
            logger_msg = "HookHandler initialized with EventBus"
        else:
            logger_msg = "HookHandler initialized (EventBus not available)"

        if DEBUG:
            print(f"🚀 {logger_msg}", file=sys.stderr)

    def _emit_event(self, event_type: str, data: dict):
        """Emit an event through the EventBus.

        WHY this approach:
        - Single point of event emission
        - Consistent event normalization
        - Graceful fallback if EventBus unavailable
        - Easy to add metrics and monitoring

        Args:
            event_type: The event type (e.g., 'pre_tool', 'subagent_stop')
            data: The event data
        """
        if not self.event_bus:
            if DEBUG:
                print(
                    f"EventBus not available, cannot emit: hook.{event_type}",
                    file=sys.stderr,
                )
            return

        try:
            # Create event data for normalization
            raw_event = {
                "type": "hook",
                "subtype": event_type,
                "timestamp": datetime.now().isoformat(),
                "data": data,
                "source": "claude_hooks",
                "session_id": data.get("sessionId", self.current_session_id),
            }

            # Normalize the event
            normalized_event = self.event_normalizer.normalize(raw_event, source="hook")
            event_data = normalized_event.to_dict()

            # Publish to EventBus
            success = self.event_bus.publish(f"hook.{event_type}", event_data)

            if DEBUG:
                if success:
                    print(
                        f"✅ Published to EventBus: hook.{event_type}", file=sys.stderr
                    )
                else:
                    print(
                        f"⚠️ EventBus rejected event: hook.{event_type}", file=sys.stderr
                    )

            # Log important events
            if DEBUG and event_type in ["subagent_stop", "pre_tool"]:
                if event_type == "subagent_stop":
                    agent_type = data.get("agent_type", "unknown")
                    print(
                        f"📤 Published SubagentStop for agent '{agent_type}'",
                        file=sys.stderr,
                    )
                elif event_type == "pre_tool" and data.get("tool_name") == "Task":
                    delegation = data.get("delegation_details", {})
                    agent_type = delegation.get("agent_type", "unknown")
                    print(
                        f"📤 Published Task delegation to agent '{agent_type}'",
                        file=sys.stderr,
                    )

        except Exception as e:
            if DEBUG:
                print(
                    f"❌ Failed to publish event hook.{event_type}: {e}",
                    file=sys.stderr,
                )

    def _get_git_branch(self, working_dir: Optional[str] = None) -> str:
        """Get git branch for the given directory with caching."""
        # Use current working directory if not specified
        if not working_dir:
            working_dir = os.getcwd()

        # Check cache first (cache for 30 seconds)
        current_time = time.time()
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
                check=False,
            )

            # Restore original directory
            os.chdir(original_cwd)

            if result.returncode == 0 and result.stdout.strip():
                branch = result.stdout.strip()
                # Cache the result
                self._git_branch_cache[cache_key] = branch
                self._git_branch_cache_time[cache_key] = current_time
                return branch
            return "unknown"

        except Exception:
            return "unknown"

    def _cleanup_old_entries(self):
        """Clean up old entries to prevent memory growth."""
        time.time() - self.MAX_CACHE_AGE_SECONDS

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
            if time.time() - cache_time > self.MAX_CACHE_AGE_SECONDS
        ]
        for key in expired_keys:
            self._git_branch_cache.pop(key, None)
            self._git_branch_cache_time.pop(key, None)

    def handle_event(self, event: dict):
        """Process an event from Claude Code.

        Args:
            event: The event dictionary from Claude
        """
        # Periodic cleanup
        current_time = time.time()
        if current_time - self._last_cleanup > 300:  # Every 5 minutes
            self._cleanup_old_entries()
            self._last_cleanup = current_time

        # Extract event details
        event_type = event.get("type", "")
        event_name = event.get("name", "")

        # Update session ID if present
        if "sessionId" in event:
            self.current_session_id = event["sessionId"]

        # Detect duplicate events
        event_signature = (
            f"{event_type}:{event_name}:{json.dumps(event.get('data', ''))[:100]}"
        )
        with _events_lock:
            if event_signature in _recent_events:
                if DEBUG:
                    print(f"Skipping duplicate event: {event_type}", file=sys.stderr)
                return
            _recent_events.append(event_signature)

        # Route to appropriate handler
        if event_type == "Start":
            self.event_handlers.handle_start(event)
        elif event_type == "Stop":
            self.event_handlers.handle_stop(event)
        elif event_type == "UserPrompt":
            self.event_handlers.handle_user_prompt(event)
        elif event_type == "AssistantResponse":
            self.event_handlers.handle_assistant_response(event)
        elif event_type == "SubagentStart":
            self.event_handlers.handle_subagent_start(event)
        elif event_type == "SubagentStop":
            self.event_handlers.handle_subagent_stop(event)
        elif event_type == "PreToolExecution" and event_name == "Task":
            self.event_handlers.handle_task_delegation(event)
        elif event_type == "PreToolExecution":
            self.event_handlers.handle_pre_tool(event)
        elif event_type == "PostToolExecution":
            self.event_handlers.handle_post_tool(event)
        elif event_type == "PromptCachingBetaStats":
            # Ignore caching stats events
            pass
        # Log unhandled events in debug mode
        elif DEBUG:
            print(f"Unhandled event type: {event_type}", file=sys.stderr)


def get_handler() -> HookHandler:
    """Get or create the global hook handler instance.

    Returns:
        HookHandler: The singleton handler instance
    """
    global _global_handler
    if _global_handler is None:
        with _handler_lock:
            if _global_handler is None:
                _global_handler = HookHandler()
    return _global_handler


def main():
    """Main entry point for the hook handler."""
    if DEBUG:
        print("🎯 EventBus Hook Handler starting...", file=sys.stderr)

    handler = get_handler()

    # Set up signal handling for clean shutdown
    def signal_handler(signum, frame):
        if DEBUG:
            print("\n👋 Hook handler shutting down...", file=sys.stderr)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Process events from stdin
    try:
        while True:
            # Check if data is available with timeout
            readable, _, _ = select.select([sys.stdin], [], [], 0.1)
            if readable:
                line = sys.stdin.readline()
                if not line:
                    break

                try:
                    event = json.loads(line.strip())
                    handler.handle_event(event)

                    # Acknowledge event
                    print(json.dumps({"status": "ok"}))
                    sys.stdout.flush()

                except json.JSONDecodeError as e:
                    if DEBUG:
                        print(f"Invalid JSON: {e}", file=sys.stderr)
                    print(json.dumps({"status": "error", "message": str(e)}))
                    sys.stdout.flush()
                except Exception as e:
                    if DEBUG:
                        print(f"Error processing event: {e}", file=sys.stderr)
                    print(json.dumps({"status": "error", "message": str(e)}))
                    sys.stdout.flush()

    except KeyboardInterrupt:
        if DEBUG:
            print("\n👋 Hook handler interrupted", file=sys.stderr)
    finally:
        if DEBUG:
            print("Hook handler exiting", file=sys.stderr)


if __name__ == "__main__":
    main()
