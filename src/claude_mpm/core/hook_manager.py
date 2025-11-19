from pathlib import Path

"""Hook manager for manually triggering hook events in PM operations.

This module provides a way for the PM agent to manually trigger hook events
that would normally be handled by Claude Code's hook system. This ensures
consistency between PM operations and regular agent operations.

WHY this is needed:
- PM runs directly in Python, bypassing Claude Code's hook system
- TodoWrite and other PM operations should trigger the same hooks as agent operations
- Ensures consistent event streaming to Socket.IO dashboard
"""

import contextlib
import json
import os
import queue
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ..core.logger import get_logger
from .hook_error_memory import get_hook_error_memory
from .hook_performance_config import get_hook_performance_config
from .unified_paths import get_package_root


class HookManager:
    """Manager for manually triggering hook events from PM operations.

    WHY this design:
    - Mimics Claude Code's hook event structure exactly
    - Uses the same hook handler that regular agents use
    - Provides session tracking consistent with regular hook events
    - Enables PM operations to appear in Socket.IO dashboard
    """

    def __init__(self):
        self.logger = get_logger("hook_manager")
        self.session_id = self._get_or_create_session_id()
        self.hook_handler_path = self._find_hook_handler()

        # Initialize error memory for tracking and preventing repeated errors
        self.error_memory = get_hook_error_memory()

        # Initialize background hook processing for async execution
        self.performance_config = get_hook_performance_config()
        queue_config = self.performance_config.get_queue_config()
        self.hook_queue = queue.Queue(maxsize=queue_config["maxsize"])
        self.background_thread = None
        self.shutdown_event = threading.Event()

        # Start background processing if hook handler is available
        if self.hook_handler_path:
            self._start_background_processor()
            self.logger.debug(
                f"Hook handler found with async processing: {self.hook_handler_path}"
            )
        else:
            self.logger.debug("Hook handler not found - hooks will be skipped")

    def _get_or_create_session_id(self) -> str:
        """Get or create a session ID for hook events."""
        # Try to get session ID from environment (set by ClaudeRunner)
        session_id = os.environ.get("CLAUDE_MPM_SESSION_ID")
        if not session_id:
            # Generate new session ID
            session_id = str(uuid.uuid4())
            os.environ["CLAUDE_MPM_SESSION_ID"] = session_id
        return session_id

    def _start_background_processor(self):
        """Start background thread to process hooks asynchronously."""

        def process_hooks():
            """Background thread function to process hook queue."""
            while not self.shutdown_event.is_set():
                try:
                    # Get hook data with timeout to allow shutdown checking
                    hook_data = self.hook_queue.get(timeout=1.0)
                    if hook_data is None:  # Shutdown signal
                        break

                    # Process the hook synchronously in background thread
                    self._execute_hook_sync(hook_data)
                    self.hook_queue.task_done()

                except queue.Empty:
                    # Timeout - continue to check shutdown event
                    continue
                except Exception as e:
                    self.logger.error(f"Hook processing error: {e}")

        self.background_thread = threading.Thread(
            target=process_hooks, name="hook-processor", daemon=True
        )
        self.background_thread.start()
        self.logger.debug("Started background hook processor thread")

    def _execute_hook_sync(self, hook_data: Dict[str, Any]):
        """Execute a single hook synchronously in the background thread with error detection.

        WHY error detection:
        - Prevents repeated execution of failing hooks
        - Provides actionable error messages to users
        - Learns from failures to improve system reliability
        - Reduces log noise from repeated errors
        """
        try:
            hook_type = hook_data["hook_type"]
            event_data = hook_data["event_data"]

            # Check if this hook is known to fail repeatedly
            if self.error_memory.should_skip_hook(hook_type):
                known_error = self.error_memory.is_known_failing_hook(hook_type)
                if known_error:
                    # Log warning but don't spam - only on first skip
                    if known_error["count"] == 2:  # First time we're skipping
                        self.logger.warning(
                            f"⚠️  Skipping {hook_type} hook - failed {known_error['count']} times previously\n"
                            f"Error: {known_error['match']}\n"
                            f"To retry: rm {self.error_memory.memory_file}"
                        )
                return

            # Create the hook event
            hook_event = {
                "hook_event_name": hook_type,
                "session_id": self.session_id,
                "timestamp": hook_data.get(
                    "timestamp", datetime.now(timezone.utc).isoformat()
                ),
                **event_data,
            }

            event_json = json.dumps(hook_event)
            env = os.environ.copy()
            env["CLAUDE_MPM_HOOK_DEBUG"] = "true"

            # Execute with timeout in background thread
            result = subprocess.run(
                ["python", str(self.hook_handler_path)],
                input=event_json,
                text=True,
                capture_output=True,
                env=env,
                timeout=self.performance_config.background_timeout,
                check=False,
            )

            # Detect errors in the output
            error_info = self.error_memory.detect_error(
                result.stdout or "", result.stderr or "", result.returncode
            )

            if error_info:
                # Record the error
                self.error_memory.record_error(error_info, hook_type)

                # Get fix suggestion
                suggestion = self.error_memory.suggest_fix(error_info)

                # Log error with suggestion
                self.logger.warning(f"Hook {hook_type} error detected:\n{suggestion}")
            elif result.returncode != 0:
                # Non-zero return without detected pattern
                self.logger.debug(f"Hook {hook_type} returned code {result.returncode}")
                if result.stderr:
                    self.logger.debug(f"Hook stderr: {result.stderr}")

        except subprocess.TimeoutExpired:
            self.logger.debug(
                f"Hook {hook_data.get('hook_type', 'unknown')} timed out in background"
            )
        except Exception as e:
            self.logger.debug(f"Background hook execution error: {e}")

    def shutdown(self):
        """Shutdown the background hook processor."""
        if self.background_thread and self.background_thread.is_alive():
            self.shutdown_event.set()
            # Signal shutdown by putting None in queue
            with contextlib.suppress(queue.Full):
                self.hook_queue.put_nowait(None)

            # Wait for thread to finish
            self.background_thread.join(timeout=2.0)
            self.logger.debug("Background hook processor shutdown")

    def _find_hook_handler(self) -> Optional[Path]:
        """Find the hook handler script."""
        try:
            # Look for hook handler in the expected location
            hook_handler = (
                get_package_root() / "hooks" / "claude_hooks" / "hook_handler.py"
            )

            if hook_handler.exists():
                return hook_handler
            self.logger.warning(f"Hook handler not found at: {hook_handler}")
            return None
        except Exception as e:
            self.logger.error(f"Error finding hook handler: {e}")
            return None

    def trigger_pre_tool_hook(
        self, tool_name: str, tool_args: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Trigger PreToolUse hook event.

        Args:
            tool_name: Name of the tool being used (e.g., "TodoWrite")
            tool_args: Arguments passed to the tool

        Returns:
            bool: True if hook was triggered successfully
        """
        return self._trigger_hook_event(
            "PreToolUse",
            {
                "tool_name": tool_name,
                "tool_args": tool_args or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    def trigger_post_tool_hook(
        self, tool_name: str, exit_code: int = 0, result: Any = None
    ) -> bool:
        """Trigger PostToolUse hook event.

        Args:
            tool_name: Name of the tool that was used
            exit_code: Exit code (0 for success, non-zero for error)
            result: Result returned by the tool

        Returns:
            bool: True if hook was triggered successfully
        """
        return self._trigger_hook_event(
            "PostToolUse",
            {
                "tool_name": tool_name,
                "exit_code": exit_code,
                "result": str(result) if result is not None else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    def trigger_user_prompt_hook(self, prompt: str) -> bool:
        """Trigger UserPromptSubmit hook event.

        Args:
            prompt: The user prompt

        Returns:
            bool: True if hook was triggered successfully
        """
        return self._trigger_hook_event(
            "UserPromptSubmit",
            {"prompt": prompt, "timestamp": datetime.now(timezone.utc).isoformat()},
        )

    def _trigger_hook_event(self, hook_type: str, event_data: Dict[str, Any]) -> bool:
        """Trigger a hook event by queuing it for background processing.

        This method uses a background queue to process hooks asynchronously,
        providing minimal overhead on the main execution thread.

        Args:
            hook_type: Type of hook event
            event_data: Event data

        Returns:
            bool: True if hook was queued successfully (not execution success)
        """
        if not self.hook_handler_path:
            self.logger.debug("Hook handler not available - skipping hook event")
            return False

        # Check if this hook type is enabled
        if not self.performance_config.is_hook_enabled(hook_type):
            self.logger.debug(f"Hook type {hook_type} disabled by configuration")
            return True

        try:
            # Queue hook for background processing
            hook_data = {
                "hook_type": hook_type,
                "event_data": event_data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Try to queue without blocking
            self.hook_queue.put_nowait(hook_data)
            self.logger.debug(
                f"Successfully queued {hook_type} hook for background processing"
            )
            return True

        except queue.Full:
            self.logger.warning(f"Hook queue full, dropping {hook_type} event")
            return False
        except Exception as e:
            self.logger.error(f"Error queuing {hook_type} hook: {e}")
            return False


# Global instance
_hook_manager: Optional[HookManager] = None


def get_hook_manager() -> HookManager:
    """Get the global hook manager instance."""
    global _hook_manager
    if _hook_manager is None:
        _hook_manager = HookManager()
        # Register cleanup on exit
        import atexit

        atexit.register(_cleanup_hook_manager)
    return _hook_manager


def _cleanup_hook_manager():
    """Cleanup function to shutdown hook manager on exit."""
    global _hook_manager
    if _hook_manager is not None:
        _hook_manager.shutdown()
        _hook_manager = None


def trigger_tool_hooks(
    tool_name: str,
    tool_args: Optional[Dict[str, Any]] = None,
    result: Any = None,
    exit_code: int = 0,
):
    """Convenience function to trigger both pre and post tool hooks.

    Args:
        tool_name: Name of the tool
        tool_args: Arguments passed to the tool
        result: Result returned by the tool
        exit_code: Exit code (0 for success)
    """
    manager = get_hook_manager()

    # Trigger pre-tool hook
    manager.trigger_pre_tool_hook(tool_name, tool_args)

    # Trigger post-tool hook
    manager.trigger_post_tool_hook(tool_name, exit_code, result)
