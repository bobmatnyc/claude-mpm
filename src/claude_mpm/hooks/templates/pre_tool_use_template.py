#!/usr/bin/env python3
"""
PreToolUse Hook Template for Claude Code v2.0.30+

This template demonstrates how to create PreToolUse hooks that can modify
tool inputs before execution. Use cases include:

1. Context Injection: Add project context to Read/Edit operations
2. Security Guards: Validate file paths before operations
3. Logging: Log tool invocations before execution
4. Parameter Enhancement: Add default parameters to tool calls

Requirements:
- Claude Code v2.0.30 or higher
- Hook must be configured with "modifyInput": true in settings.json

Input Format (stdin):
{
  "hook_event_name": "PreToolUse",
  "tool_name": "Edit",
  "tool_input": {
    "file_path": "/path/to/file.py",
    "old_string": "foo",
    "new_string": "bar"
  },
  "session_id": "abc123...",
  "cwd": "/working/directory"
}

Output Format (stdout):
{
  "action": "continue",
  "tool_input": {
    "file_path": "/path/to/file.py",
    "old_string": "foo",
    "new_string": "bar_modified"
  }
}

Or to block execution:
{
  "action": "block",
  "message": "Reason for blocking"
}

Or to continue without modification:
{
  "action": "continue"
}
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional


class PreToolUseHook:
    """Base class for PreToolUse hooks with input modification support."""

    def __init__(self):
        """Initialize the hook."""
        self.debug = os.environ.get("CLAUDE_MPM_HOOK_DEBUG", "false").lower() == "true"

    def log_debug(self, message: str) -> None:
        """Log debug message to stderr."""
        if self.debug:
            print(f"[PreToolUse Hook] {message}", file=sys.stderr)

    def read_event(self) -> Optional[Dict[str, Any]]:
        """Read and parse the hook event from stdin."""
        try:
            event_data = sys.stdin.read()
            if not event_data.strip():
                return None
            return json.loads(event_data)
        except json.JSONDecodeError as e:
            self.log_debug(f"Failed to parse event: {e}")
            return None
        except Exception as e:
            self.log_debug(f"Error reading event: {e}")
            return None

    def continue_execution(
        self, modified_input: Optional[Dict[str, Any]] = None
    ) -> None:
        """Continue execution with optional modified input."""
        response = {"action": "continue"}
        if modified_input is not None:
            response["tool_input"] = modified_input
        print(json.dumps(response))

    def block_execution(self, message: str) -> None:
        """Block execution with a message."""
        response = {"action": "block", "message": message}
        print(json.dumps(response))

    def modify_input(
        self, tool_name: str, tool_input: Dict[str, Any], event: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Modify tool input before execution.

        Override this method in subclasses to implement custom logic.

        Args:
            tool_name: Name of the tool being invoked
            tool_input: Original tool input parameters
            event: Full event data including session_id, cwd, etc.

        Returns:
            Modified tool input dict, or None to continue without modification
        """
        # Default: no modification
        return None

    def should_block(
        self, tool_name: str, tool_input: Dict[str, Any], event: Dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Check if execution should be blocked.

        Override this method in subclasses to implement validation logic.

        Args:
            tool_name: Name of the tool being invoked
            tool_input: Original tool input parameters
            event: Full event data including session_id, cwd, etc.

        Returns:
            Tuple of (should_block, reason)
        """
        # Default: don't block
        return False, ""

    def run(self) -> None:
        """Main entry point for the hook."""
        try:
            # Read event from stdin
            event = self.read_event()
            if not event:
                self.continue_execution()
                return

            tool_name = event.get("tool_name", "")
            tool_input = event.get("tool_input", {})

            self.log_debug(
                f"Processing {tool_name} with input: {list(tool_input.keys())}"
            )

            # Check if execution should be blocked
            should_block, reason = self.should_block(tool_name, tool_input, event)
            if should_block:
                self.log_debug(f"Blocking {tool_name}: {reason}")
                self.block_execution(reason)
                return

            # Try to modify input
            modified_input = self.modify_input(tool_name, tool_input, event)
            if modified_input is not None:
                self.log_debug(f"Modified {tool_name} input")
                self.continue_execution(modified_input)
            else:
                self.log_debug(f"No modification for {tool_name}")
                self.continue_execution()

        except Exception as e:
            self.log_debug(f"Hook error: {e}")
            # Always continue on error to avoid blocking Claude
            self.continue_execution()


# ============================================================================
# Example Implementations
# ============================================================================


class ContextInjectionHook(PreToolUseHook):
    """
    Example: Auto-inject project context into Read/Edit tool calls.

    This hook adds project-specific context as comments to file operations.
    """

    def __init__(self):
        super().__init__()
        self.project_context = self._load_project_context()

    def _load_project_context(self) -> str:
        """Load project context from a file or environment."""
        # Example: Load from .claude-context file
        context_file = Path.cwd() / ".claude-context"
        if context_file.exists():
            return context_file.read_text()
        return ""

    def modify_input(
        self, tool_name: str, tool_input: Dict[str, Any], event: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Inject context into Read operations."""
        if tool_name == "Read" and self.project_context:
            # Add context as a note (this is conceptual - actual implementation depends on use case)
            modified = tool_input.copy()
            # You could add context to a metadata field if the tool supports it
            modified["_context"] = self.project_context[:200]
            return modified
        return None


class SecurityGuardHook(PreToolUseHook):
    """
    Example: Validate file paths before file operations.

    This hook blocks operations on sensitive files or directories.
    """

    BLOCKED_PATHS = [
        ".env",
        "credentials.json",
        "secrets/",
        ".ssh/",
        "id_rsa",
    ]

    def should_block(
        self, tool_name: str, tool_input: Dict[str, Any], event: Dict[str, Any]
    ) -> tuple[bool, str]:
        """Block operations on sensitive files."""
        if tool_name in ["Write", "Edit", "Read"]:
            file_path = tool_input.get("file_path", "")
            if any(blocked in file_path for blocked in self.BLOCKED_PATHS):
                return True, f"Access to sensitive file blocked: {file_path}"
        return False, ""


class LoggingHook(PreToolUseHook):
    """
    Example: Log all tool invocations before execution.

    This hook logs tool calls to a file for debugging and audit purposes.
    """

    def __init__(self):
        super().__init__()
        self.log_file = Path.home() / ".claude-mpm" / "tool-calls.log"
        self.log_file.parent.mkdir(exist_ok=True)

    def modify_input(
        self, tool_name: str, tool_input: Dict[str, Any], event: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Log the tool call."""
        try:
            from datetime import datetime, timezone

            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tool_name": tool_name,
                "session_id": event.get("session_id", ""),
                "cwd": event.get("cwd", ""),
                "parameters": list(tool_input.keys()),
            }
            with self.log_file.open("a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            self.log_debug(f"Failed to log tool call: {e}")

        # Don't modify input, just log
        return None


class ParameterEnhancementHook(PreToolUseHook):
    """
    Example: Add default parameters to tool calls.

    This hook adds default values to tool parameters if not provided.
    """

    def modify_input(
        self, tool_name: str, tool_input: Dict[str, Any], event: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Add default parameters."""
        modified = tool_input.copy()

        if tool_name == "Bash":
            # Add default timeout if not specified
            if "timeout" not in modified:
                modified["timeout"] = 30000  # 30 seconds
                return modified

        elif tool_name == "Grep":
            # Add line numbers by default
            if "-n" not in modified:
                modified["-n"] = True
                return modified

        return None


# ============================================================================
# Main Entry Point
# ============================================================================


def main():
    """Main entry point - choose which hook implementation to use."""
    # Select which hook implementation to use
    # Uncomment the one you want to use:

    # hook = ContextInjectionHook()
    # hook = SecurityGuardHook()
    # hook = LoggingHook()
    # hook = ParameterEnhancementHook()

    # Default: use base hook (no modification)
    hook = PreToolUseHook()

    hook.run()


if __name__ == "__main__":
    main()
