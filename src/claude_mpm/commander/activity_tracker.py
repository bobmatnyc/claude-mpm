"""Activity Tracker for MPM Commander Sessions.

Tracks real-time metrics for each tmux session:
- total_lines: Total lines in scrollback
- lines_since_prompt: New lines since last user prompt
- seconds_since_change: Time since last output
- seconds_since_prompt: Time since last user input
- last_user_input: The last prompt sent by user
- last_agent_output: Last agent response OR "working..." if active

These metrics enable quick assessment of agent state:
- Active: seconds_since_change < 5s, lines growing
- Waiting: seconds_since_change > 30s
- Finished: seconds_since_change > 60s, no new lines
"""

import logging
import subprocess  # nosec B404 - required for tmux interaction
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ActivityStats:
    """Activity statistics for a single session."""

    # Line tracking
    total_lines: int = 0
    lines_since_prompt: int = 0
    baseline_lines: int = 0  # Lines at last prompt

    # Timestamps
    last_prompt_time: float = 0.0
    last_output_time: float = 0.0
    created_at: float = field(default_factory=time.time)

    # Content tracking
    last_user_input: str = ""
    last_agent_output: str = ""  # "working..." when active
    is_working: bool = False

    # Claude Code state (parsed from status line, e.g. "bypass permissions on")
    claude_state: str = ""

    # Computed (updated on access)
    @property
    def seconds_since_change(self) -> float:
        """Seconds since last output line."""
        if self.last_output_time == 0:
            return 0.0
        return time.time() - self.last_output_time

    @property
    def seconds_since_prompt(self) -> float:
        """Seconds since last user prompt."""
        if self.last_prompt_time == 0:
            return 0.0
        return time.time() - self.last_prompt_time

    @property
    def agent_status(self) -> str:
        """Derive agent status from metrics."""
        if self.last_prompt_time == 0:
            return "idle"
        if self.is_working:
            if self.seconds_since_change < 5:
                return "active"
            if self.seconds_since_change < 30:
                return "thinking"
            return "stalled"
        return "finished"

    def to_dict(self) -> dict:
        """Export stats as dictionary for API response."""
        return {
            "total_lines": self.total_lines,
            "lines_since_prompt": self.lines_since_prompt,
            "seconds_since_change": round(self.seconds_since_change, 1),
            "seconds_since_prompt": round(self.seconds_since_prompt, 1),
            "last_user_input": self.last_user_input,
            "last_agent_output": self.last_agent_output
            if not self.is_working
            else "working...",
            "is_working": self.is_working,
            "status": self.agent_status,
            "claude_state": self.claude_state,
            "last_prompt_time": self.last_prompt_time,
            "last_output_time": self.last_output_time,
        }


class ActivityTracker:
    """Tracks activity metrics for all MPM Commander sessions.

    Uses a combination of:
    1. Hook-driven updates (UserPromptSubmit, Stop, PostToolUse)
    2. Polling (1s interval) for real-time line counting

    Usage:
        tracker = ActivityTracker()
        tracker.start_polling()

        # On user prompt (from hook)
        tracker.on_user_prompt("session-1", "%5", "What is Python?")

        # On agent stop (from hook)
        tracker.on_agent_stop("session-1", "Python is a programming language...")

        # Get stats for UI
        stats = tracker.get_stats("session-1")
    """

    def __init__(self, poll_interval: float = 1.0):
        """Initialize the activity tracker.

        Args:
            poll_interval: Seconds between polling cycles (default: 1.0)
        """
        self._stats: Dict[str, ActivityStats] = {}
        self._tmux_targets: Dict[str, str] = {}  # session_id -> pane_id
        self._poll_interval = poll_interval
        self._polling_thread: Optional[threading.Thread] = None
        self._stop_polling = threading.Event()
        self._lock = threading.Lock()
        self._on_update_callbacks: list[Callable[[str, dict], None]] = []

    def register_session(self, session_id: str, tmux_target: str) -> None:
        """Register a session for tracking.

        Args:
            session_id: Unique session identifier
            tmux_target: Tmux pane ID (e.g., "%5")
        """
        with self._lock:
            if session_id not in self._stats:
                self._stats[session_id] = ActivityStats()
                self._tmux_targets[session_id] = tmux_target
                # Initialize with current line count
                try:
                    lines = self._get_tmux_line_count(tmux_target)
                    self._stats[session_id].total_lines = lines
                    self._stats[session_id].baseline_lines = lines
                except Exception as e:
                    logger.warning(
                        f"Failed to get initial line count for {session_id}: {e}"
                    )
                logger.info(
                    f"Registered session {session_id} with target {tmux_target}"
                )

    def unregister_session(self, session_id: str) -> None:
        """Remove a session from tracking.

        Args:
            session_id: Session to remove
        """
        with self._lock:
            self._stats.pop(session_id, None)
            self._tmux_targets.pop(session_id, None)
            logger.info(f"Unregistered session {session_id}")

    def on_user_prompt(
        self, session_id: str, tmux_target: str, prompt_text: str
    ) -> None:
        """Handle UserPromptSubmit hook event.

        Called when user sends a new prompt. Resets turn metrics.

        Args:
            session_id: Session identifier
            tmux_target: Tmux pane ID
            prompt_text: The user's input text
        """
        with self._lock:
            # Auto-register if needed
            if session_id not in self._stats:
                self.register_session(session_id, tmux_target)

            stats = self._stats[session_id]
            now = time.time()

            # Get current line count as baseline
            try:
                current_lines = self._get_tmux_line_count(tmux_target)
                stats.baseline_lines = current_lines
                stats.total_lines = current_lines
            except Exception as e:
                logger.warning(f"Failed to get line count on prompt: {e}")

            # Reset turn metrics
            stats.last_prompt_time = now
            stats.last_output_time = now  # Consider prompt as activity
            stats.lines_since_prompt = 0
            stats.last_user_input = prompt_text[:500]  # Truncate for storage
            stats.last_agent_output = ""
            stats.is_working = True

            logger.debug(f"User prompt for {session_id}: {prompt_text[:50]}...")
            self._notify_update(session_id)

    def on_agent_stop(self, session_id: str, response_text: str) -> None:
        """Handle Stop hook event.

        Called when agent finishes response. Finalizes turn metrics.

        Args:
            session_id: Session identifier
            response_text: The agent's response text
        """
        with self._lock:
            if session_id not in self._stats:
                logger.warning(f"on_agent_stop: Unknown session {session_id}")
                return

            stats = self._stats[session_id]
            now = time.time()

            # Update metrics
            stats.last_output_time = now
            stats.is_working = False

            # Store truncated response
            if response_text:
                # Keep last 500 chars for display
                stats.last_agent_output = (
                    response_text[-500:] if len(response_text) > 500 else response_text
                )

            # Final line count
            if session_id in self._tmux_targets:
                try:
                    current_lines = self._get_tmux_line_count(
                        self._tmux_targets[session_id]
                    )
                    stats.lines_since_prompt = current_lines - stats.baseline_lines
                    stats.total_lines = current_lines
                except Exception as e:
                    logger.warning(f"Failed to get final line count: {e}")

            logger.debug(
                f"Agent stopped for {session_id}, lines_since_prompt={stats.lines_since_prompt}"
            )
            self._notify_update(session_id)

    def on_tool_output(self, session_id: str, tool_name: str, output_text: str) -> None:
        """Handle PostToolUse hook event.

        Called after a tool execution. Updates activity timestamp.

        Args:
            session_id: Session identifier
            tool_name: Name of the tool that was used
            output_text: Tool output (optional)
        """
        with self._lock:
            if session_id not in self._stats:
                return

            stats = self._stats[session_id]
            stats.last_output_time = time.time()

            # Update line count if we have tmux target
            if session_id in self._tmux_targets:
                try:
                    current_lines = self._get_tmux_line_count(
                        self._tmux_targets[session_id]
                    )
                    if current_lines > stats.total_lines:
                        diff = current_lines - stats.total_lines
                        stats.total_lines = current_lines
                        stats.lines_since_prompt += diff
                except Exception as e:
                    logger.debug(f"Failed to update line count on tool: {e}")

            self._notify_update(session_id)

    def get_stats(self, session_id: str) -> Optional[dict]:
        """Get current stats for a session.

        Args:
            session_id: Session identifier

        Returns:
            Dict with all metrics or None if session not found
        """
        with self._lock:
            if session_id not in self._stats:
                return None
            return self._stats[session_id].to_dict()

    def get_all_stats(self) -> Dict[str, dict]:
        """Get stats for all tracked sessions.

        Returns:
            Dict mapping session_id to stats dict
        """
        with self._lock:
            return {sid: stats.to_dict() for sid, stats in self._stats.items()}

    def add_update_callback(self, callback: Callable[[str, dict], None]) -> None:
        """Register callback for stats updates.

        Callback receives (session_id, stats_dict) on each update.

        Args:
            callback: Function to call on updates
        """
        self._on_update_callbacks.append(callback)

    def _notify_update(self, session_id: str) -> None:
        """Notify all callbacks of a stats update."""
        if session_id in self._stats:
            stats_dict = self._stats[session_id].to_dict()
            for callback in self._on_update_callbacks:
                try:
                    callback(session_id, stats_dict)
                except Exception as e:
                    logger.error(f"Update callback error: {e}")

    def _get_tmux_line_count(self, target: str) -> int:
        """Get total line count from tmux pane.

        Args:
            target: Tmux pane ID (e.g., "%5")

        Returns:
            Total lines in scrollback + visible area
        """
        try:
            result = subprocess.run(  # nosec B603 B607 - trusted tmux command
                ["tmux", "display", "-p", "-t", target, "#{history_size}"],
                capture_output=True,
                text=True,
                check=True,
                timeout=2,
            )
            history_size = int(result.stdout.strip())

            # Also get pane height for total
            result2 = subprocess.run(  # nosec B603 B607 - trusted tmux command
                ["tmux", "display", "-p", "-t", target, "#{pane_height}"],
                capture_output=True,
                text=True,
                check=True,
                timeout=2,
            )
            pane_height = int(result2.stdout.strip())

            return history_size + pane_height
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout getting line count for {target}")
            raise
        except (subprocess.CalledProcessError, ValueError) as e:
            logger.debug(f"Failed to get line count for {target}: {e}")
            raise

    def _get_tmux_last_lines(self, target: str, num_lines: int = 5) -> str:
        """Get last N lines from tmux pane.

        Args:
            target: Tmux pane target
            num_lines: Number of lines to capture

        Returns:
            Last N lines as string, or empty string on error
        """
        try:
            result = subprocess.run(  # nosec B603 B607 - trusted tmux command
                ["tmux", "capture-pane", "-p", "-t", target, "-S", f"-{num_lines}"],
                capture_output=True,
                text=True,
                check=True,
                timeout=2,
            )
            return result.stdout
        except Exception as e:
            logger.debug(f"Failed to capture pane output: {e}")
            return ""

    def _parse_claude_state(self, output: str) -> str:
        """Parse Claude Code state from terminal output.

        Looks for patterns like:
        - "▸▸ bypass permissions on (shift+tab to cycle)"
        - "Update available! Run: brew upgrade claude-code"

        Args:
            output: Terminal output text

        Returns:
            Extracted state string or empty string
        """
        import re

        lines = output.strip().split("\n")

        # Search from bottom up for state indicators
        for line in reversed(lines):
            line = line.strip()
            # Skip empty lines and ANSI codes
            clean_line = re.sub(r"\x1b\[[0-9;]*m", "", line)

            # Check for permission state (▸▸ prefix)
            if "▸▸" in clean_line or "»" in clean_line:
                # Extract the state text
                match = re.search(r"[▸»]+\s*(.+?)(?:\s*\(|$)", clean_line)
                if match:
                    return match.group(1).strip()

            # Check for update available
            if "Update available" in clean_line:
                return "Update available"

            # Check for common Claude Code states
            if "bypass permissions" in clean_line.lower():
                return "bypass permissions on"

        return ""

    def _poll_cycle(self) -> None:
        """Execute one polling cycle for all sessions."""
        with self._lock:
            for session_id, target in list(self._tmux_targets.items()):
                if session_id not in self._stats:
                    continue

                stats = self._stats[session_id]
                changed = False

                try:
                    current_lines = self._get_tmux_line_count(target)

                    if current_lines > stats.total_lines:
                        diff = current_lines - stats.total_lines
                        stats.total_lines = current_lines
                        stats.lines_since_prompt += diff
                        stats.last_output_time = time.time()
                        logger.debug(f"Poll: {session_id} +{diff} lines")
                        changed = True

                    # Parse Claude Code state from last lines
                    last_output = self._get_tmux_last_lines(target, 10)
                    if last_output:
                        new_state = self._parse_claude_state(last_output)
                        if new_state != stats.claude_state:
                            stats.claude_state = new_state
                            changed = True

                    if changed:
                        self._notify_update(session_id)

                except Exception as e:
                    logger.debug(f"Poll error for {session_id}: {e}")

    def start_polling(self) -> None:
        """Start background polling thread."""
        if self._polling_thread and self._polling_thread.is_alive():
            logger.warning("Polling already running")
            return

        self._stop_polling.clear()

        def poll_loop():
            logger.info(f"Activity polling started (interval: {self._poll_interval}s)")
            while not self._stop_polling.is_set():
                self._poll_cycle()
                self._stop_polling.wait(self._poll_interval)
            logger.info("Activity polling stopped")

        self._polling_thread = threading.Thread(target=poll_loop, daemon=True)
        self._polling_thread.start()

    def stop_polling(self) -> None:
        """Stop background polling thread."""
        self._stop_polling.set()
        if self._polling_thread:
            self._polling_thread.join(timeout=2)


# Global tracker instance
_tracker: Optional[ActivityTracker] = None


def get_tracker() -> ActivityTracker:
    """Get or create the global ActivityTracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = ActivityTracker()
    return _tracker
