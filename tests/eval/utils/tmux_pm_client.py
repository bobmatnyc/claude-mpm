"""
Tmux-based PM client for behavioral evaluations.

Communicates with a running claude-mpm PM instance in a tmux session,
sending prompts and capturing responses with timeout handling.
"""

import re
import subprocess
import time
from typing import Optional


class TmuxPMClient:
    """Client for sending prompts to a PM instance running in tmux."""

    def __init__(self, session: str = "mpm-eval", pane: str = "mpm-eval:0.0"):
        """
        Initialize the tmux PM client.

        Args:
            session: Tmux session name (default: mpm-eval)
            pane: Tmux pane address (default: mpm-eval:0.0)
        """
        self.session = session
        self.pane = pane

    def is_running(self) -> bool:
        """Check if the tmux session is alive and responsive."""
        try:
            result = subprocess.run(
                ["tmux", "list-sessions", "-F", "#{session_name}"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return self.session in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _strip_ansi(self, text: str) -> str:
        """Remove ANSI escape codes from text."""
        return re.sub(r"\x1b\[[0-9;]*m", "", text)

    def _capture_pane(self) -> str:
        """Capture current pane content."""
        try:
            result = subprocess.run(
                ["tmux", "capture-pane", "-t", self.pane, "-p"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return ""

    def _get_last_line_count(self, text: str) -> int:
        """Get line count to detect when output stabilizes."""
        return len(text.splitlines())

    def send_prompt(self, prompt: str, timeout: int = 30) -> str:
        """
        Send a prompt to the PM instance and wait for response.

        Polls the pane every 500ms until output stabilizes (unchanged for 2s).

        Args:
            prompt: The prompt text to send
            timeout: Maximum seconds to wait for response (default: 30)

        Returns:
            The response text with ANSI codes stripped
        """
        # Capture baseline before sending
        baseline = self._capture_pane()
        baseline_lines = self._get_last_line_count(baseline)

        # Send the prompt
        try:
            subprocess.run(
                ["tmux", "send-keys", "-t", self.pane, prompt],
                timeout=5,
                check=True,
            )
            subprocess.run(
                ["tmux", "send-keys", "-t", self.pane, "C-m"],
                timeout=5,
                check=True,
            )
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            raise RuntimeError(f"Failed to send prompt: {e}") from e

        # Poll until output stabilizes
        start_time = time.time()
        last_output = baseline
        stable_time = 0.0
        stable_threshold = 2.0  # Declare done when unchanged for 2s
        poll_interval = 0.5

        while time.time() - start_time < timeout:
            time.sleep(poll_interval)
            current_output = self._capture_pane()

            if current_output == last_output:
                stable_time += poll_interval
                if stable_time >= stable_threshold:
                    # Output has stabilized
                    break
            else:
                # Output changed, reset stability timer
                stable_time = 0.0
                last_output = current_output

        # Extract only the new output (lines after baseline)
        final_lines = last_output.splitlines()
        baseline_lines_count = baseline_lines

        if len(final_lines) > baseline_lines_count:
            new_output = "\n".join(final_lines[baseline_lines_count:])
        else:
            # Output on same lines, return last part
            new_output = last_output

        # Strip ANSI codes
        cleaned = self._strip_ansi(new_output)
        return cleaned.strip()

    def reset(self) -> None:
        """Send Ctrl+C to clear any in-progress state."""
        try:
            subprocess.run(
                ["tmux", "send-keys", "-t", self.pane, "C-c"],
                timeout=5,
                check=True,
            )
            time.sleep(0.3)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass
