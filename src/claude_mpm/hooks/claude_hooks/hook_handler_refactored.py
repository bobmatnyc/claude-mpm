#!/usr/bin/env python3
"""Refactored Claude Code hook handler with modular service architecture.

This handler uses a service-oriented architecture with:
- StateManagerService: Manages state and delegation tracking
- ConnectionManagerService: Handles SocketIO and EventBus connections
- SubagentResponseProcessor: Processes complex subagent responses
- DuplicateEventDetector: Detects and filters duplicate events

WHY service-oriented approach:
- Better separation of concerns and modularity
- Easier testing and maintenance
- Reduced file size from 1040 to ~400 lines
- Clear service boundaries and responsibilities
"""

import json
import os
import select
import signal
import sys
import threading
from datetime import datetime

# Import extracted modules with fallback for direct execution
try:
    # Try relative imports first (when imported as module)
    from .event_handlers import EventHandlers
    from .memory_integration import MemoryHookManager
    from .response_tracking import ResponseTrackingManager
    from .services import (
        ConnectionManagerService,
        DuplicateEventDetector,
        StateManagerService,
        SubagentResponseProcessor,
    )
except ImportError:
    # Fall back to absolute imports (when run directly)
    from pathlib import Path

    # Add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent))

    from event_handlers import EventHandlers
    from memory_integration import MemoryHookManager
    from response_tracking import ResponseTrackingManager
    from services import (
        ConnectionManagerService,
        DuplicateEventDetector,
        StateManagerService,
        SubagentResponseProcessor,
    )

# Debug mode is enabled by default for better visibility into hook processing
# Set CLAUDE_MPM_HOOK_DEBUG=false to disable debug output
DEBUG = os.environ.get("CLAUDE_MPM_HOOK_DEBUG", "true").lower() != "false"

# Global singleton handler instance
_global_handler = None
_handler_lock = threading.Lock()


class ClaudeHookHandler:
    """Refactored hook handler with service-oriented architecture.

    WHY service-oriented approach:
    - Modular design with clear service boundaries
    - Each service handles a specific responsibility
    - Easier to test, maintain, and extend
    - Reduced complexity in main handler class
    """

    def __init__(self):
        # Initialize services
        self.state_manager = StateManagerService()
        self.connection_manager = ConnectionManagerService()
        self.duplicate_detector = DuplicateEventDetector()

        # Initialize extracted managers
        self.memory_hook_manager = MemoryHookManager()
        self.response_tracking_manager = ResponseTrackingManager()
        self.event_handlers = EventHandlers(self)

        # Initialize subagent processor with dependencies
        self.subagent_processor = SubagentResponseProcessor(
            self.state_manager, self.response_tracking_manager, self.connection_manager
        )

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
            if self.duplicate_detector.is_duplicate(event):
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

            # Debug: Log that we're processing an event
            if DEBUG:
                hook_type = event.get("hook_event_name", "unknown")
                print(
                    f"\n[{datetime.now().isoformat()}] Processing hook event: {hook_type} (PID: {os.getpid()})",
                    file=sys.stderr,
                )

            # Perform periodic cleanup if needed
            if self.state_manager.increment_events_processed():
                self.state_manager.cleanup_old_entries()
                if DEBUG:
                    print(
                        f"🧹 Performed cleanup after {self.state_manager.events_processed} events",
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
            "SubagentStop": self.handle_subagent_stop,
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

    def handle_subagent_stop(self, event: dict):
        """Delegate subagent stop processing to the specialized processor."""
        self.subagent_processor.process_subagent_stop(event)

    def _continue_execution(self) -> None:
        """
        Send continue action to Claude.

        WHY: Centralized response ensures consistent format
        and makes it easier to add response modifications.
        """
        print(json.dumps({"action": "continue"}))

    # Delegation methods for compatibility with event_handlers
    def _track_delegation(self, session_id: str, agent_type: str, request_data=None):
        """Track delegation through state manager."""
        self.state_manager.track_delegation(session_id, agent_type, request_data)

    def _get_delegation_agent_type(self, session_id: str) -> str:
        """Get delegation agent type through state manager."""
        return self.state_manager.get_delegation_agent_type(session_id)

    def _get_git_branch(self, working_dir=None) -> str:
        """Get git branch through state manager."""
        return self.state_manager.get_git_branch(working_dir)

    def _emit_socketio_event(self, namespace: str, event: str, data: dict):
        """Emit event through connection manager."""
        self.connection_manager.emit_event(namespace, event, data)

    def __del__(self):
        """Cleanup on handler destruction."""
        # Clean up connection manager if it exists
        if hasattr(self, "connection_manager") and self.connection_manager:
            try:
                self.connection_manager.cleanup()
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
