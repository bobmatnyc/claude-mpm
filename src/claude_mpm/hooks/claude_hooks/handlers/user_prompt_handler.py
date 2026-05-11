#!/usr/bin/env python3
"""User prompt event handler.

Extracted from ``event_handlers.EventHandlers`` as part of the #509 refactor.
Behavior is preserved verbatim; only the surrounding structure has changed.
"""

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from .base import DEBUG, BaseEventHandler, _log


class UserPromptHandler:
    """Handle UserPromptSubmit events."""

    def __init__(self, base: BaseEventHandler):
        self.base = base
        # Mirror hook_handler reference for parity with original code paths
        self.hook_handler = base.hook_handler

    def handle_user_prompt_fast(self, event):
        """Handle user prompt with comprehensive data capture.

        WHY enhanced data capture:
        - Provides full context for debugging and monitoring
        - Captures prompt text, working directory, and session context
        - Enables better filtering and analysis in dashboard
        """
        prompt = event.get("prompt", "")

        # Skip /mpm commands to reduce noise unless debug is enabled
        if prompt.startswith("/mpm") and not DEBUG:
            return

        # Detect and save @alias for sticky project context
        self._save_project_alias_if_present(prompt)

        # Emit immediate acknowledgment for long-running command feedback
        project_name = (
            event.get("cwd", "").split("/")[-1] if event.get("cwd") else "unknown"
        )
        ack_data = {
            "prompt_preview": prompt[:80] + "..." if len(prompt) > 80 else prompt,
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "received",
            "project": project_name,
        }
        self.hook_handler._emit_socketio_event("", "command_acknowledged", ack_data)

        # Capture PM-level directive to persistent memory (non-blocking)
        self._capture_pm_directive(prompt, project_name)

        # Get working directory and git branch
        working_dir = event.get("cwd", "")
        git_branch = (
            self.base._get_git_branch(working_dir) if working_dir else "Unknown"
        )

        # Extract comprehensive prompt data
        prompt_data = {
            "prompt_text": prompt,
            "prompt_preview": prompt[:200] if len(prompt) > 200 else prompt,
            "prompt_length": len(prompt),
            "session_id": event.get("session_id", ""),
            "working_directory": working_dir,
            "git_branch": git_branch,
            "timestamp": datetime.now(UTC).isoformat(),
            "is_command": prompt.startswith("/"),
            "contains_code": "```" in prompt
            or "python" in prompt.lower()
            or "javascript" in prompt.lower(),
            "urgency": (
                "high"
                if any(
                    word in prompt.lower()
                    for word in ["urgent", "error", "bug", "fix", "broken"]
                )
                else "normal"
            ),
        }

        # Store prompt for comprehensive response tracking if enabled
        try:
            rtm = getattr(self.hook_handler, "response_tracking_manager", None)
            if (
                rtm
                and getattr(rtm, "response_tracking_enabled", False)
                and getattr(rtm, "track_all_interactions", False)
            ):
                session_id = event.get("session_id", "")
                if session_id:
                    pending_prompts = getattr(self.hook_handler, "pending_prompts", {})
                    pending_prompts[session_id] = {
                        "prompt": prompt,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "working_directory": working_dir,
                    }
                    if DEBUG:
                        _log(
                            f"Stored prompt for comprehensive tracking: session {session_id[:8]}..."
                        )
        except Exception:  # nosec B110
            # Response tracking is optional - silently continue if it fails
            pass

        # Record user message for auto-pause if active
        auto_pause = getattr(self.hook_handler, "auto_pause_handler", None)
        if auto_pause and auto_pause.is_pause_active():
            try:
                auto_pause.on_user_message(prompt)
            except Exception as e:
                if DEBUG:
                    _log(f"Auto-pause user message recording error: {e}")

        # Check for incoming messages (cross-project messaging)
        try:
            from claude_mpm.hooks import message_check_hook

            message_notification = message_check_hook()
            if message_notification:
                # Inject message notification into PM context
                # This will appear in the next system reminder
                prompt_data["message_notification"] = message_notification
                if DEBUG:
                    _log("Message notification added to prompt data")
        except Exception as e:
            if DEBUG:
                _log(f"Message check hook error: {e}")

        # Emit normalized event (namespace no longer needed with normalized events)
        self.hook_handler._emit_socketio_event("", "user_prompt", prompt_data)

    def _save_project_alias_if_present(self, prompt: str) -> None:
        """Detect @alias in prompt and save to state file for sticky context.

        WHY this feature:
        - Enables 'sticky' project context for subsequent prompts
        - User types '@myproject do something' once, then future prompts
          without @ automatically use the same project context
        - State file: ~/.claude-mpm/state/last_project.json

        Format: {"alias": "myproject", "timestamp": "..."}
        """
        if not prompt:
            return

        # Pattern: @alias at start of prompt (project context reference)
        # Matches @word but not @@ or email-like patterns
        match = re.match(r"^@([a-zA-Z][a-zA-Z0-9_-]*)\s", prompt)
        if not match:
            return

        alias = match.group(1)

        # Save to state file
        try:
            state_dir = Path.home() / ".claude-mpm" / "state"
            state_dir.mkdir(parents=True, exist_ok=True)

            state_file = state_dir / "last_project.json"
            state_data = {
                "alias": alias,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            with open(state_file, "w") as f:
                json.dump(state_data, f, indent=2)

            if DEBUG:
                _log(f"Saved project alias '{alias}' to {state_file}")

        except Exception as e:
            if DEBUG:
                _log(f"Failed to save project alias: {e}")
            # Non-fatal: sticky context is a convenience feature

    def _capture_pm_directive(self, prompt: str, project: str | None = None) -> None:
        """Capture PM-level directive to persistent memory.

        Stores user orchestration commands for context enrichment:
        - Preferences ("always use PR model")
        - Workflows ("when deploying, run tests first")
        - Directives ("implement feature X")

        Args:
            prompt: User prompt to capture
            project: Project context (from @alias or cwd)
        """
        # Skip internal commands and very short prompts
        if prompt.startswith("/") or len(prompt) < 10:
            return

        try:
            from claude_mpm.memory import get_pm_memory

            pm_memory = get_pm_memory(enabled=True)
            pm_memory.capture_directive(prompt, project=project)

            if DEBUG:
                _log(f"Captured PM directive for project '{project}'")

        except ImportError:
            # kuzu-memory not installed - silently skip
            pass
        except Exception as e:
            if DEBUG:
                _log(f"Failed to capture PM directive: {e}")
            # Non-fatal: memory capture is optional
