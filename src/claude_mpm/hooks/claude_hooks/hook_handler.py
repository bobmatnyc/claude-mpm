#!/usr/bin/env python3
"""Refactored Claude Code hook handler with modular service architecture.

This handler uses a service-oriented architecture with:
- StateManagerService: Manages state and delegation tracking
- ConnectionManagerService: Handles SocketIO connections with HTTP fallback
- SubagentResponseProcessor: Processes complex subagent responses
- DuplicateEventDetector: Detects and filters duplicate events

WHY service-oriented approach:
- Better separation of concerns and modularity
- Easier testing and maintenance
- Reduced file size from 1040 to ~400 lines
- Clear service boundaries and responsibilities

NOTE: Requires Claude Code version 1.0.92 or higher for proper hook support.
Earlier versions do not support matcher-based hook configuration.
"""

import json
import os
import re
import select
import signal
import subprocess
import sys
import threading
from datetime import datetime, timezone
from typing import Optional, Tuple

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

"""
Debug mode configuration for hook processing.

WHY enabled by default: Hook processing can be complex and hard to debug.
Having debug output available by default helps diagnose issues during development.
Production deployments can disable via environment variable.

Performance Impact: Debug logging adds ~5-10% overhead but provides crucial
visibility into event flow, timing, and error conditions.
"""
DEBUG = os.environ.get("CLAUDE_MPM_HOOK_DEBUG", "true").lower() != "false"

"""
Conditional imports with graceful fallbacks for testing and modularity.

WHY conditional imports:
- Tests may not have full environment setup
- Allows hooks to work in minimal configurations
- Graceful degradation when dependencies unavailable
"""

# Import get_connection_pool for backward compatibility with tests
try:
    from claude_mpm.core.socketio_pool import get_connection_pool
except ImportError:
    get_connection_pool = None

"""
Global singleton pattern for hook handler.

WHY singleton:
- Only one handler should process Claude Code events
- Maintains consistent state across all hook invocations
- Prevents duplicate event processing
- Thread-safe initialization with lock

GOTCHA: Must use get_global_handler() not direct access to avoid race conditions.
"""
_global_handler = None
_handler_lock = threading.Lock()

"""
Version compatibility checking.

WHY version checking:
- Claude Code hook support was added in v1.0.92
- Earlier versions don't support matcher-based configuration
- Prevents confusing errors with unsupported versions

Security: Version checking prevents execution on incompatible environments.
"""
MIN_CLAUDE_VERSION = "1.0.92"


def check_claude_version() -> Tuple[bool, Optional[str]]:
    """
    Verify Claude Code version compatibility for hook support.

    Executes 'claude --version' command to detect installed version and
    compares against minimum required version for hook functionality.

    Version Checking Logic:
    1. Execute 'claude --version' with timeout
    2. Parse version string using regex
    3. Compare against MIN_CLAUDE_VERSION (1.0.92)
    4. Return compatibility status and detected version

    WHY this check is critical:
    - Hook support was added in Claude Code v1.0.92
    - Earlier versions don't understand matcher-based hooks
    - Prevents cryptic errors from unsupported configurations
    - Allows graceful fallback or user notification

    Error Handling:
    - Command timeout after 5 seconds
    - Subprocess errors caught and logged
    - Invalid version formats handled gracefully
    - Returns (False, None) on any failure

    Performance Notes:
    - Subprocess call has ~100ms overhead
    - Result should be cached by caller
    - Only called during initialization

    Returns:
        Tuple[bool, Optional[str]]:
            - bool: True if version is compatible
            - str|None: Detected version string, None if detection failed

    Examples:
        >>> is_compatible, version = check_claude_version()
        >>> if not is_compatible:
        ...     print(f"Claude Code {version or 'unknown'} is not supported")
    """
    try:
        # Try to detect Claude Code version
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode == 0:
            version_text = result.stdout.strip()
            # Extract version number (e.g., "1.0.92 (Claude Code)" -> "1.0.92")
            match = re.match(r"^([\d\.]+)", version_text)
            if match:
                version = match.group(1)

                # Compare versions
                def parse_version(v: str):
                    try:
                        return [int(x) for x in v.split(".")]
                    except (ValueError, AttributeError):
                        return [0]

                current = parse_version(version)
                required = parse_version(MIN_CLAUDE_VERSION)

                # Check if current version meets minimum
                for i in range(max(len(current), len(required))):
                    curr_part = current[i] if i < len(current) else 0
                    req_part = required[i] if i < len(required) else 0

                    if curr_part < req_part:
                        if DEBUG:
                            print(
                                f"⚠️  Claude Code {version} does not support matcher-based hooks "
                                f"(requires {MIN_CLAUDE_VERSION}+). Hook monitoring disabled.",
                                file=sys.stderr,
                            )
                        return False, version
                    if curr_part > req_part:
                        return True, version

                return True, version
    except Exception as e:
        if DEBUG:
            print(
                f"Warning: Could not detect Claude Code version: {e}", file=sys.stderr
            )

    return False, None


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

        # Backward compatibility properties for tests
        self.connection_pool = self.connection_manager.connection_pool

        # Expose state manager properties for backward compatibility
        self.active_delegations = self.state_manager.active_delegations
        self.delegation_history = self.state_manager.delegation_history
        self.delegation_requests = self.state_manager.delegation_requests
        self.pending_prompts = self.state_manager.pending_prompts

        # Initialize git branch cache (used by event_handlers)
        self._git_branch_cache = {}
        self._git_branch_cache_time = {}

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
                        f"[{datetime.now(timezone.utc).isoformat()}] Skipping duplicate event: {event.get('hook_event_name', 'unknown')} (PID: {os.getpid()})",
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
                    f"\n[{datetime.now(timezone.utc).isoformat()}] Processing hook event: {hook_type} (PID: {os.getpid()})",
                    file=sys.stderr,
                )

            # Perform periodic cleanup if needed
            if self.state_manager.increment_events_processed():
                self.state_manager.cleanup_old_entries()
                # Also cleanup old correlation files
                from .correlation_manager import CorrelationManager

                CorrelationManager.cleanup_old()
                if DEBUG:
                    print(
                        f"🧹 Performed cleanup after {self.state_manager.events_processed} events",
                        file=sys.stderr,
                    )

            # Route event to appropriate handler
            # Handlers can optionally return modified input for PreToolUse events
            modified_input = self._route_event(event)

            # Always continue execution (only if not already sent)
            if not _continue_sent:
                self._continue_execution(modified_input)
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

            parsed = json.loads(event_data)
            # Debug: Log the actual event format we receive
            if DEBUG:
                print(
                    f"Received event with keys: {list(parsed.keys())}", file=sys.stderr
                )
                for key in ["hook_event_name", "event", "type", "event_type"]:
                    if key in parsed:
                        print(f"  {key} = '{parsed[key]}'", file=sys.stderr)
            return parsed
        except (json.JSONDecodeError, ValueError) as e:
            if DEBUG:
                print(f"Failed to parse hook event: {e}", file=sys.stderr)
            return None
        except Exception as e:
            if DEBUG:
                print(f"Error reading hook event: {e}", file=sys.stderr)
            return None

    def _route_event(self, event: dict) -> Optional[dict]:
        """
        Route event to appropriate handler based on type.

        WHY: Centralized routing reduces complexity and makes
        it easier to add new event types.

        Args:
            event: Hook event dictionary

        Returns:
            Modified input for PreToolUse events (v2.0.30+), None otherwise
        """
        import time

        # Try multiple field names for compatibility
        hook_type = (
            event.get("hook_event_name")
            or event.get("event")
            or event.get("type")
            or event.get("event_type")
            or event.get("hook_event_type")
            or "unknown"
        )

        # Log the actual event structure for debugging
        if DEBUG and hook_type == "unknown":
            print(f"Unknown event format, keys: {list(event.keys())}", file=sys.stderr)
            print(f"Event sample: {str(event)[:200]}", file=sys.stderr)

        # Map event types to handlers
        event_handlers = {
            "UserPromptSubmit": self.event_handlers.handle_user_prompt_fast,
            "PreToolUse": self.event_handlers.handle_pre_tool_fast,
            "PostToolUse": self.event_handlers.handle_post_tool_fast,
            "Notification": self.event_handlers.handle_notification_fast,
            "Stop": self.event_handlers.handle_stop_fast,
            "SubagentStop": self.event_handlers.handle_subagent_stop_fast,
            "SubagentStart": self.event_handlers.handle_session_start_fast,
            "SessionStart": self.event_handlers.handle_session_start_fast,
            "AssistantResponse": self.event_handlers.handle_assistant_response,
        }

        # Call appropriate handler if exists
        handler = event_handlers.get(hook_type)
        if handler:
            # Track execution timing for hook emission
            start_time = time.time()
            success = False
            error_message = None
            result = None

            try:
                # Handlers can optionally return modified input
                result = handler(event)
                success = True
                # Only PreToolUse handlers should return modified input
                if hook_type == "PreToolUse" and result is not None:
                    return_value = result
                else:
                    return_value = None
            except Exception as e:
                error_message = str(e)
                return_value = None
                if DEBUG:
                    print(f"Error handling {hook_type}: {e}", file=sys.stderr)
            finally:
                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)

                # Emit hook execution event
                self._emit_hook_execution_event(
                    hook_type=hook_type,
                    event=event,
                    success=success,
                    duration_ms=duration_ms,
                    error_message=error_message,
                )

            return return_value

        return None

    def handle_subagent_stop(self, event: dict):
        """Delegate subagent stop processing to the specialized processor."""
        self.subagent_processor.process_subagent_stop(event)

    def _continue_execution(self, modified_input: Optional[dict] = None) -> None:
        """
        Send continue action to Claude with optional input modification.

        WHY: Centralized response ensures consistent format
        and makes it easier to add response modifications.

        Args:
            modified_input: Modified tool parameters for PreToolUse hooks (v2.0.30+)
        """
        if modified_input is not None:
            # Claude Code v2.0.30+ supports modifying PreToolUse tool inputs
            print(json.dumps({"action": "continue", "tool_input": modified_input}))
        else:
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

    def _get_event_key(self, event: dict) -> str:
        """Generate event key through duplicate detector (backward compatibility)."""
        return self.duplicate_detector.generate_event_key(event)

    def _emit_hook_execution_event(
        self,
        hook_type: str,
        event: dict,
        success: bool,
        duration_ms: int,
        error_message: Optional[str] = None,
    ):
        """Emit a structured JSON event for hook execution.

        This emits a normalized event following the claude_event schema to provide
        visibility into hook processing, timing, and success/failure status.

        Args:
            hook_type: The type of hook that executed (e.g., "UserPromptSubmit", "PreToolUse")
            event: The original hook event data
            success: Whether the hook executed successfully
            duration_ms: How long the hook took to execute in milliseconds
            error_message: Optional error message if the hook failed
        """
        # Generate a human-readable summary based on hook type
        summary = self._generate_hook_summary(hook_type, event, success)

        # Extract common fields
        session_id = event.get("session_id", "")
        working_dir = event.get("cwd", "")

        # Build hook execution data
        hook_data = {
            "hook_name": hook_type,
            "hook_type": hook_type,
            "session_id": session_id,
            "working_directory": working_dir,
            "success": success,
            "duration_ms": duration_ms,
            "result_summary": summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Add error information if present
        if error_message:
            hook_data["error_message"] = error_message

        # Add hook-specific context
        if hook_type == "PreToolUse":
            hook_data["tool_name"] = event.get("tool_name", "")
        elif hook_type == "PostToolUse":
            hook_data["tool_name"] = event.get("tool_name", "")
            hook_data["exit_code"] = event.get("exit_code", 0)
        elif hook_type == "UserPromptSubmit":
            prompt = event.get("prompt", "")
            hook_data["prompt_preview"] = prompt[:100] if len(prompt) > 100 else prompt
            hook_data["prompt_length"] = len(prompt)
        elif hook_type == "SubagentStop":
            hook_data["agent_type"] = event.get("agent_type", "unknown")
            hook_data["reason"] = event.get("reason", "unknown")

        # Emit through connection manager with proper structure
        # This uses the existing event infrastructure
        self._emit_socketio_event("", "hook_execution", hook_data)

        if DEBUG:
            print(
                f"📊 Hook execution event: {hook_type} - {duration_ms}ms - {'✅' if success else '❌'}",
                file=sys.stderr,
            )

    def _generate_hook_summary(self, hook_type: str, event: dict, success: bool) -> str:
        """Generate a human-readable summary of what the hook did.

        Args:
            hook_type: The type of hook
            event: The hook event data
            success: Whether the hook executed successfully

        Returns:
            A brief description of what happened
        """
        if not success:
            return f"Hook {hook_type} failed during processing"

        # Generate hook-specific summaries
        if hook_type == "UserPromptSubmit":
            prompt = event.get("prompt", "")
            if prompt.startswith("/"):
                return f"Processed command: {prompt.split()[0]}"
            return f"Processed user prompt ({len(prompt)} chars)"

        if hook_type == "PreToolUse":
            tool_name = event.get("tool_name", "unknown")
            return f"Pre-processing tool call: {tool_name}"

        if hook_type == "PostToolUse":
            tool_name = event.get("tool_name", "unknown")
            exit_code = event.get("exit_code", 0)
            status = "success" if exit_code == 0 else "failed"
            return f"Completed tool call: {tool_name} ({status})"

        if hook_type == "SubagentStop":
            agent_type = event.get("agent_type", "unknown")
            reason = event.get("reason", "unknown")
            return f"Subagent {agent_type} stopped: {reason}"

        if hook_type == "SessionStart":
            return "New session started"

        if hook_type == "Stop":
            reason = event.get("reason", "unknown")
            return f"Session stopped: {reason}"

        if hook_type == "Notification":
            notification_type = event.get("notification_type", "unknown")
            return f"Notification received: {notification_type}"

        if hook_type == "AssistantResponse":
            response_len = len(event.get("response", ""))
            return f"Assistant response generated ({response_len} chars)"

        # Default summary
        return f"Hook {hook_type} processed successfully"

    def __del__(self):
        """Cleanup on handler destruction."""
        # Clean up connection manager if it exists
        if hasattr(self, "connection_manager") and self.connection_manager:
            try:
                self.connection_manager.cleanup()
            except Exception:
                pass  # Ignore cleanup errors during destruction


def main():
    """Entry point with singleton pattern and proper cleanup."""
    global _global_handler
    _continue_printed = False  # Track if we've already printed continue

    # Check Claude Code version compatibility first
    is_compatible, version = check_claude_version()
    if not is_compatible:
        # Version incompatible - just continue without processing
        # This prevents errors on older Claude Code versions
        if DEBUG and version:
            print(
                f"Skipping hook processing due to version incompatibility ({version})",
                file=sys.stderr,
            )
        print(json.dumps({"action": "continue"}))
        sys.exit(0)

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
