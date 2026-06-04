#!/usr/bin/env python3
"""Auto-pause handler for Claude Code hooks.

WHY: Track cumulative token usage across Claude Code hook invocations so that
commit-cost trailers and the dashboard have accurate context-usage data.

CONTEXT AUTO-PAUSE IS DISABLED: This handler historically paused/aborted a
session (and any in-flight sub-agent) once context usage crossed 90%/95%,
emitting "session paused to prevent data loss". That behavior killed legitimate
active work and has been removed. Token usage is still MEASURED (via
ContextUsageTracker), but crossing a threshold NEVER triggers a pause, never
creates ACTIVE-PAUSE.jsonl, and never aborts a session or sub-agent. The
public method signatures are preserved to avoid breaking imports/tests.

DESIGN DECISIONS:
- Integrates with ContextUsageTracker for token tracking across hook invocations
- IncrementalPauseManager wiring is retained only so the recording API surface
  stays importable; no pause is ever started from threshold crossings
- Thread-safe - handles hook calls from multiple processes via file-based state
- Only reports NEW threshold crossings (informational; no pausing)
- Graceful error handling - tracking failures don't break main hook processing

USAGE:
    # Initialize handler in hook handler
    auto_pause = AutoPauseHandler()

    # Monitor token usage from API responses
    if "usage" in metadata:
        threshold_crossed = auto_pause.on_usage_update(metadata["usage"])
        if threshold_crossed:
            warning = auto_pause.emit_threshold_warning(threshold_crossed)
            _log(f"\n⚠️  {warning}")

    # Record actions during pause mode
    if auto_pause.is_pause_active():
        auto_pause.on_tool_call(tool_name, tool_args)
        auto_pause.on_assistant_response(response_summary)

    # Finalize on session end
    session_file = auto_pause.on_session_end()
"""

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from claude_mpm.core.logger import get_logger
from claude_mpm.services.cli.incremental_pause_manager import IncrementalPauseManager
from claude_mpm.services.infrastructure.context_usage_tracker import (
    ContextUsageTracker,
)

# Try to import _log from hook_handler, fall back to no-op
try:
    from claude_mpm.hooks.claude_hooks.hook_handler import _log
except ImportError:

    def _log(msg: str) -> None:
        pass  # Silent fallback


logger = get_logger(__name__)

# Debug mode
DEBUG = os.environ.get("CLAUDE_MPM_HOOK_DEBUG", "false").lower() == "true"

# Warning messages for threshold crossings
THRESHOLD_WARNINGS = {
    "caution": "Context usage at 70%. Consider wrapping up current work.",
    "warning": "Context usage at 85%. Session nearing capacity.",
    "auto_pause": "Context usage at 90%. Consider wrapping up or running /compact (auto-pause is disabled).",
    "critical": "Context usage at 95%. Consider wrapping up or running /compact (auto-pause is disabled).",
}

# Maximum length for summaries to avoid storing full responses
MAX_SUMMARY_LENGTH = 500


class AutoPauseHandler:
    """Handler for automatic session pausing based on context usage thresholds.

    Integrates with Claude Code hooks to:
    1. Track cumulative token usage from API responses (for metering only)
    2. Report NEW threshold crossings informationally

    Auto-pause is DISABLED: thresholds never start a pause, never write
    ACTIVE-PAUSE.jsonl, and never abort a session or sub-agent. The action
    recording API (on_tool_call/on_assistant_response/on_user_message) remains
    but is effectively dormant because is_pause_active() never becomes True from
    a threshold crossing.

    Features:
    - File-based state persistence (works across hook process restarts)
    - Thread-safe through atomic file operations
    - Graceful error handling (failures don't break main hook flow)
    - Only reports NEW threshold crossings (informational; no pausing)
    - Summarizes long content to prevent memory bloat
    """

    def __init__(self, project_path: Path | None = None):
        """Initialize auto-pause handler.

        Args:
            project_path: Project root path (default: current directory)
        """
        self.project_path = (project_path or Path.cwd()).resolve()

        # Initialize services
        self.tracker = ContextUsageTracker(self.project_path)
        self.pause_manager = IncrementalPauseManager(self.project_path)

        # Track previous threshold to detect NEW crossings
        self._previous_threshold: str | None = None

        # Load initial state
        try:
            current_state = self.tracker.get_current_state()
            self._previous_threshold = current_state.threshold_reached

            if DEBUG:
                _log(
                    f"AutoPauseHandler initialized: "
                    f"{current_state.percentage_used:.1f}% context used, "
                    f"threshold: {current_state.threshold_reached}"
                )
        except Exception as e:
            logger.error(f"Failed to initialize AutoPauseHandler: {e}")
            # Continue with None - will initialize on first update

    def on_usage_update(self, usage: dict[str, Any]) -> str | None:
        """Process token usage from a Claude API response.

        Args:
            usage: Dict with 'input_tokens', 'output_tokens',
                   'cache_creation_input_tokens', 'cache_read_input_tokens'

        Returns:
            Threshold name if a NEW threshold was crossed ('caution', 'warning',
            'auto_pause', 'critical'), or None if no new threshold crossed.

        Raises:
            ValueError: If usage data is invalid
        """
        try:
            # Extract token counts
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            cache_creation = usage.get("cache_creation_input_tokens", 0)
            cache_read = usage.get("cache_read_input_tokens", 0)

            # Validate token counts
            if any(
                t < 0 for t in [input_tokens, output_tokens, cache_creation, cache_read]
            ):
                raise ValueError("Token counts cannot be negative")

            # Update cumulative usage
            state = self.tracker.update_usage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_creation=cache_creation,
                cache_read=cache_read,
            )

            # Check if we crossed a NEW threshold
            current_threshold = state.threshold_reached
            new_threshold_crossed = None

            if current_threshold != self._previous_threshold:
                # Determine if this is a higher threshold
                threshold_order = ["caution", "warning", "auto_pause", "critical"]

                prev_idx = (
                    threshold_order.index(self._previous_threshold)
                    if self._previous_threshold in threshold_order
                    else -1
                )
                curr_idx = (
                    threshold_order.index(current_threshold)
                    if current_threshold in threshold_order
                    else -1
                )

                if curr_idx > prev_idx:
                    new_threshold_crossed = current_threshold
                    self._previous_threshold = current_threshold

                    if DEBUG:
                        _log(
                            f"Context threshold crossed: {current_threshold} "
                            f"({state.percentage_used:.1f}%)"
                        )

                    # NOTE: Auto-pause triggering is DISABLED. Token usage is still
                    # tracked (via tracker.update_usage above) so commit-cost
                    # trailers and the dashboard keep working, but crossing the
                    # 90%/95% threshold no longer pauses or aborts the session /
                    # sub-agent. See _trigger_auto_pause() docstring for rationale.

            return new_threshold_crossed

        except Exception as e:
            logger.error(f"Failed to update usage: {e}")
            if DEBUG:
                _log(f"❌ Usage update failed: {e}")
            # Don't propagate error - auto-pause is optional
            return None

    def on_tool_call(self, tool_name: str, tool_args: dict[str, Any]) -> None:
        """Record a tool call if auto-pause is active.

        Args:
            tool_name: Name of the tool being called
            tool_args: Tool arguments dictionary

        Raises:
            RuntimeError: If append operation fails (optional, logged only)
        """
        if not self.is_pause_active():
            return

        try:
            # Summarize tool args to avoid storing large data
            args_summary = self._summarize_dict(tool_args)

            # Get current context percentage
            state = self.tracker.get_current_state()

            # Record action
            self.pause_manager.append_action(
                action_type="tool_call",
                action_data={
                    "tool": tool_name,
                    "args_summary": args_summary,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                context_percentage=state.percentage_used / 100,
            )

            if DEBUG:
                _log(f"Recorded tool call during pause: {tool_name}")

        except Exception as e:
            logger.error(f"Failed to record tool call: {e}")
            if DEBUG:
                _log(f"❌ Failed to record tool call: {e}")

    def on_assistant_response(self, response_summary: str) -> None:
        """Record an assistant response if auto-pause is active.

        Args:
            response_summary: Summary of assistant response (will be truncated)

        Raises:
            RuntimeError: If append operation fails (optional, logged only)
        """
        if not self.is_pause_active():
            return

        try:
            # Truncate long responses
            summary = self._truncate_text(response_summary, MAX_SUMMARY_LENGTH)

            # Get current context percentage
            state = self.tracker.get_current_state()

            # Record action
            self.pause_manager.append_action(
                action_type="assistant_response",
                action_data={
                    "summary": summary,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                context_percentage=state.percentage_used / 100,
            )

            if DEBUG:
                _log(
                    f"Recorded assistant response during pause (length: {len(summary)})"
                )

        except Exception as e:
            logger.error(f"Failed to record assistant response: {e}")
            if DEBUG:
                _log(f"❌ Failed to record assistant response: {e}")

    def on_user_message(self, message_summary: str) -> None:
        """Record a user message if auto-pause is active.

        Args:
            message_summary: Summary of user message (will be truncated)

        Raises:
            RuntimeError: If append operation fails (optional, logged only)
        """
        if not self.is_pause_active():
            return

        try:
            # Truncate long messages
            summary = self._truncate_text(message_summary, MAX_SUMMARY_LENGTH)

            # Get current context percentage
            state = self.tracker.get_current_state()

            # Record action
            self.pause_manager.append_action(
                action_type="user_message",
                action_data={
                    "summary": summary,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                context_percentage=state.percentage_used / 100,
            )

            if DEBUG:
                _log(f"Recorded user message during pause (length: {len(summary)})")

        except Exception as e:
            logger.error(f"Failed to record user message: {e}")
            if DEBUG:
                _log(f"❌ Failed to record user message: {e}")

    def on_session_end(self) -> Path | None:
        """Called when session ends. Finalizes any active pause.

        Returns:
            Path to finalized session file, or None if no pause was active.

        Raises:
            RuntimeError: If finalization fails
        """
        if not self.is_pause_active():
            if DEBUG:
                _log("No active pause to finalize")
            return None

        try:
            # Finalize the pause session
            session_path = self.pause_manager.finalize_pause(create_full_snapshot=True)

            if session_path and DEBUG:
                _log(f"✅ Session finalized: {session_path.name}")

            return session_path

        except Exception as e:
            logger.error(f"Failed to finalize pause session: {e}")
            if DEBUG:
                _log(f"❌ Failed to finalize pause: {e}")
            raise

    def is_pause_active(self) -> bool:
        """Check if auto-pause mode is currently active.

        Returns:
            True if auto-pause has been triggered and is capturing actions
        """
        return self.pause_manager.is_pause_active()

    def get_status(self) -> dict[str, Any]:
        """Get current status for display/logging.

        Returns:
            Dict with: context_percentage, threshold_reached,
            pause_active, actions_recorded, etc.
        """
        try:
            state = self.tracker.get_current_state()
            pause_summary = self.pause_manager.get_pause_summary()

            status = {
                "context_percentage": round(state.percentage_used, 2),
                "threshold_reached": state.threshold_reached,
                "auto_pause_active": state.auto_pause_active,
                "pause_active": self.is_pause_active(),
                "session_id": state.session_id,
                "total_tokens": (
                    state.cumulative_input_tokens + state.cumulative_output_tokens
                ),
                "budget": ContextUsageTracker.CONTEXT_BUDGET,
            }

            # Add pause details if active
            if pause_summary:
                status["pause_details"] = {
                    "action_count": pause_summary["action_count"],
                    "duration_seconds": pause_summary["duration_seconds"],
                    "context_range": pause_summary["context_range"],
                    "last_action_type": pause_summary["last_action_type"],
                }

            return status

        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {"error": str(e)}

    def emit_threshold_warning(self, threshold: str) -> str:
        """Generate a warning message for threshold crossing.

        Args:
            threshold: Threshold name ('caution', 'warning', 'auto_pause', 'critical')

        Returns:
            User-friendly warning message string
        """
        warning = THRESHOLD_WARNINGS.get(
            threshold, f"Context usage threshold reached: {threshold}"
        )

        # Add context percentage to warning
        try:
            state = self.tracker.get_current_state()
            warning = f"{warning} ({state.percentage_used:.1f}%)"
        except Exception:
            pass  # nosec B110 - Intentionally ignore formatting errors, warning is already constructed

        return warning

    def _trigger_auto_pause(self, state) -> None:
        """DISABLED no-op — context-usage auto-pause has been removed.

        Why: At high context % the auto-pause used to abort active work (including
        in-flight sub-agent delegations) by writing ACTIVE-PAUSE.jsonl and emitting
        "session paused to prevent data loss". This killed legitimate work. The
        explicit decision is to NEVER auto-pause/abort based on context %, while
        KEEPING token-usage metering (commit-cost trailers + dashboard depend on
        it — see ContextUsageTracker.update_usage / set_session_snapshot).
        What: Intentionally does nothing. Does not start an incremental pause and
        never creates ACTIVE-PAUSE.jsonl. The method signature is preserved so any
        external callers/tests importing it keep working.
        Test: Call with any state; assert is_pause_active() stays False and no
        ACTIVE-PAUSE.jsonl is created.

        Args:
            state: Current context usage state (unused — pausing is disabled)
        """
        return  # no-op: auto-pause permanently disabled

    def _summarize_dict(
        self, data: dict[str, Any], max_items: int = 10
    ) -> dict[str, Any]:
        """Create a summary of a dictionary by limiting items and truncating values.

        Args:
            data: Dictionary to summarize
            max_items: Maximum number of items to include

        Returns:
            Summarized dictionary
        """
        summary = {}

        for i, (key, value) in enumerate(data.items()):
            if i >= max_items:
                summary["..."] = f"({len(data) - max_items} more items)"
                break

            # Truncate string values
            if isinstance(value, str):
                summary[key] = self._truncate_text(value, 100)
            elif isinstance(value, (list, dict)):
                summary[key] = f"<{type(value).__name__} with {len(value)} items>"
            else:
                summary[key] = str(value)[:100]

        return summary

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to maximum length with ellipsis.

        Args:
            text: Text to truncate
            max_length: Maximum length

        Returns:
            Truncated text with "..." suffix if truncated
        """
        if len(text) <= max_length:
            return text

        return text[: max_length - 3] + "..."
