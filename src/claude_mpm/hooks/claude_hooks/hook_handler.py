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

# Suppress RuntimeWarning from frozen runpy (prevents REPL pollution in Claude Code)
# Must be before other imports to suppress warnings during import
import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning)

import json
import os
import re
import select
import signal
import subprocess  # nosec B404
import sys
import threading
from datetime import datetime, timezone
from typing import Optional, Tuple

# Import extracted modules with fallback for direct execution
try:
    # Try relative imports first (when imported as module)
    from .auto_pause_handler import AutoPauseHandler
    from .event_handlers import EventHandlers
    from .memory_integration import MemoryHookManager
    from .response_tracking import ResponseTrackingManager
    from .services import (
        ConnectionManagerService,
        DuplicateEventDetector,
        HookServiceContainer,
        StateManagerService,
        SubagentResponseProcessor,
    )
except ImportError:
    # Fall back to absolute imports (when run directly)
    from pathlib import Path

    # Add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent))

    from auto_pause_handler import AutoPauseHandler
    from event_handlers import EventHandlers
    from memory_integration import MemoryHookManager
    from response_tracking import ResponseTrackingManager
    from services import (
        ConnectionManagerService,
        DuplicateEventDetector,
        HookServiceContainer,
        StateManagerService,
        SubagentResponseProcessor,
    )

# Import CorrelationManager with fallback (used in _route_event cleanup)
# WHY at top level: Runtime relative imports fail with "no known parent package" error
try:
    from .correlation_manager import CorrelationManager
except ImportError:
    try:
        from correlation_manager import CorrelationManager
    except ImportError:
        # Fallback: create a no-op class if module unavailable
        class CorrelationManager:
            @staticmethod
            def cleanup_old():
                pass


"""
Debug mode configuration for hook processing.

WHY disabled by default: Production users should see clean output without debug noise.
Hook errors appear less confusing when debug output is minimal.
Development and debugging can enable via CLAUDE_MPM_HOOK_DEBUG=true.

Performance Impact: Debug logging adds ~5-10% overhead but provides crucial
visibility into event flow, timing, and error conditions when enabled.
"""
DEBUG = os.environ.get("CLAUDE_MPM_HOOK_DEBUG", "false").lower() == "true"


def _log(message: str) -> None:
    """Log message to file if DEBUG enabled. Never write to stderr.

    WHY: Claude Code interprets ANY stderr output as a hook error.
    Writing to stderr causes confusing "hook error" messages even for debug logs.

    This helper ensures all debug output goes to a log file instead.
    """
    if DEBUG:
        try:
            with open("/tmp/claude-mpm-hook.log", "a") as f:  # nosec B108
                f.write(f"[{datetime.now(timezone.utc).isoformat()}] {message}\n")
        except Exception:  # nosec B110 - intentional silent failure
            pass  # Never disrupt hook execution


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
# Minimum version for user-invocable skills support
MIN_SKILLS_VERSION = "2.1.3"


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
        result = subprocess.run(  # nosec B603 B607 - Safe: hardcoded claude CLI with --version flag, no user input
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
                        _log(
                            f"⚠️  Claude Code {version} does not support matcher-based hooks "
                            f"(requires {MIN_CLAUDE_VERSION}+). Hook monitoring disabled."
                        )
                        return False, version
                    if curr_part > req_part:
                        return True, version

                return True, version
    except Exception as e:
        _log(f"Warning: Could not detect Claude Code version: {e}")

    return False, None


class ClaudeHookHandler:
    """Refactored hook handler with service-oriented architecture.

    WHY service-oriented approach:
    - Modular design with clear service boundaries
    - Each service handles a specific responsibility
    - Easier to test, maintain, and extend
    - Reduced complexity in main handler class

    Supports Dependency Injection:
    - Pass a HookServiceContainer to override default services
    - Useful for testing with mock services
    - Maintains backward compatibility when no container is provided
    """

    def __init__(self, container: Optional[HookServiceContainer] = None):
        """Initialize hook handler with optional DI container.

        Args:
            container: Optional HookServiceContainer for dependency injection.
                      If None, services are created directly (backward compatible).
        """
        # Use container if provided, otherwise create services directly
        if container is not None:
            # DI mode: get services from container
            self._container = container
            self.state_manager = container.get_state_manager()
            self.connection_manager = container.get_connection_manager()
            self.duplicate_detector = container.get_duplicate_detector()
            self.memory_hook_manager = container.get_memory_hook_manager()
            self.response_tracking_manager = container.get_response_tracking_manager()
            self.auto_pause_handler = container.get_auto_pause_handler()

            # Event handlers need reference to this handler (circular, but contained)
            self.event_handlers = EventHandlers(self)

            # Subagent processor with injected dependencies
            self.subagent_processor = container.get_subagent_processor(
                self.state_manager,
                self.response_tracking_manager,
                self.connection_manager,
            )
        else:
            # Backward compatible mode: create services directly
            self._container = None
            self.state_manager = StateManagerService()
            self.connection_manager = ConnectionManagerService()
            self.duplicate_detector = DuplicateEventDetector()

            # Initialize extracted managers
            self.memory_hook_manager = MemoryHookManager()
            self.response_tracking_manager = ResponseTrackingManager()
            self.event_handlers = EventHandlers(self)

            # Initialize subagent processor with dependencies
            self.subagent_processor = SubagentResponseProcessor(
                self.state_manager,
                self.response_tracking_manager,
                self.connection_manager,
            )

            # Initialize auto-pause handler
            try:
                self.auto_pause_handler = AutoPauseHandler()
            except Exception as e:
                self.auto_pause_handler = None
                _log(f"Auto-pause initialization failed: {e}")

        # Link auto-pause handler to response tracking manager
        if self.auto_pause_handler and hasattr(self, "response_tracking_manager"):
            self.response_tracking_manager.auto_pause_handler = self.auto_pause_handler

        # Backward compatibility properties for tests
        # Note: HTTP-based connection manager doesn't use connection_pool
        self.connection_pool = None  # Deprecated: No longer needed with HTTP emission

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
            _log(f"Hook handler timeout (pid: {os.getpid()})")
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
                _log(
                    f"[{datetime.now(timezone.utc).isoformat()}] Skipping duplicate event: {event.get('hook_event_name', 'unknown')} (PID: {os.getpid()})"
                )
                # Still need to output continue for this invocation
                if not _continue_sent:
                    self._continue_execution()
                    _continue_sent = True
                return

            # Debug: Log that we're processing an event
            hook_type = event.get("hook_event_name", "unknown")
            _log(
                f"\n[{datetime.now(timezone.utc).isoformat()}] Processing hook event: {hook_type} (PID: {os.getpid()})"
            )

            # Perform periodic cleanup if needed
            if self.state_manager.increment_events_processed():
                self.state_manager.cleanup_old_entries()
                # Also cleanup old correlation files
                CorrelationManager.cleanup_old()
                _log(
                    f"🧹 Performed cleanup after {self.state_manager.events_processed} events"
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
                _log("No hook event data received within timeout")
                return None

            # Data is available, read it
            event_data = sys.stdin.read()
            if not event_data.strip():
                # Empty or whitespace-only data
                return None

            parsed = json.loads(event_data)
            # Debug: Log the actual event format we receive
            _log(f"Received event with keys: {list(parsed.keys())}")
            for key in ["hook_event_name", "event", "type", "event_type"]:
                if key in parsed:
                    _log(f"  {key} = '{parsed[key]}'")
            return parsed
        except (json.JSONDecodeError, ValueError) as e:
            _log(f"Failed to parse hook event: {e}")
            return None
        except Exception as e:
            _log(f"Error reading hook event: {e}")
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
        if hook_type == "unknown":
            _log(f"Unknown event format, keys: {list(event.keys())}")
            _log(f"Event sample: {str(event)[:200]}")

        # Map event types to handlers
        event_handlers = {
            "UserPromptSubmit": self.event_handlers.handle_user_prompt_fast,
            "PreToolUse": self.event_handlers.handle_pre_tool_fast,
            "PostToolUse": self.event_handlers.handle_post_tool_fast,
            "Notification": self.event_handlers.handle_notification_fast,
            "Stop": self.event_handlers.handle_stop_fast,
            "SubagentStop": self.event_handlers.handle_subagent_stop_fast,
            "SubagentStart": self.event_handlers.handle_subagent_start_fast,
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
                _log(f"Error handling {hook_type}: {e}")
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
            print(
                json.dumps({"continue": True, "tool_input": modified_input}),
                flush=True,
            )
        else:
            print(json.dumps({"continue": True}), flush=True)

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
            "hook_type": hook_type,  # Actual hook type (PreToolUse, UserPromptSubmit, etc.)
            "hook_event_type": hook_type,  # Additional field for clarity
            "session_id": session_id,
            "working_directory": working_dir,
            "success": success,
            "duration_ms": duration_ms,
            "result_summary": summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "claude_hook_handler",  # Explicit source identification
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

        _log(
            f"📊 Hook execution event: {hook_type} - {duration_ms}ms - {'✅' if success else '❌'}"
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
        # Finalize any active auto-pause session
        if hasattr(self, "auto_pause_handler") and self.auto_pause_handler:
            try:
                self.auto_pause_handler.on_session_end()
            except Exception:
                pass  # nosec B110 - Intentionally ignore cleanup errors during handler destruction

        # Clean up connection manager if it exists
        if hasattr(self, "connection_manager") and self.connection_manager:
            try:
                self.connection_manager.cleanup()
            except Exception:
                pass  # nosec B110 - Intentionally ignore cleanup errors during handler destruction


def main():
    """Entry point with singleton pattern and proper cleanup."""
    global _global_handler
    _continue_printed = False  # Track if we've already printed continue

    # Check Claude Code version compatibility first
    is_compatible, version = check_claude_version()
    if not is_compatible:
        # Version incompatible - just continue without processing
        # This prevents errors on older Claude Code versions
        if version:
            _log(f"Skipping hook processing due to version incompatibility ({version})")
        print(json.dumps({"continue": True}), flush=True)
        sys.exit(0)

    def cleanup_handler(signum=None, frame=None):
        """Cleanup handler for signals and exit."""
        nonlocal _continue_printed
        _log(f"Hook handler cleanup (pid: {os.getpid()}, signal: {signum})")
        # Only output continue if we haven't already (i.e., if interrupted by signal)
        if signum is not None and not _continue_printed:
            print(json.dumps({"continue": True}), flush=True)
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
                _log(f"✅ Created new ClaudeHookHandler singleton (pid: {os.getpid()})")
            else:
                _log(
                    f"♻️ Reusing existing ClaudeHookHandler singleton (pid: {os.getpid()})"
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
            print(json.dumps({"continue": True}), flush=True)
            _continue_printed = True
        # Log error for debugging
        _log(f"Hook handler error: {e}")
        sys.exit(0)  # Exit cleanly even on error


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Catastrophic failure (import error, etc.) - always output valid JSON
        print(json.dumps({"continue": True}), flush=True)
        sys.exit(0)
