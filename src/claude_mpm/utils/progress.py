"""ASCII Progress Bar Utility for Git Operations.

WHY: Provides visual feedback during long-running operations like agent/skill downloads
from Git sources. Enhances user experience with real-time progress indicators.

DESIGN DECISION: Terminal-aware progress bar with graceful degradation

Rationale: Use sys.stdout for line overwriting with \r to create animated progress bars.
Detect TTY environments to avoid breaking non-interactive terminals (CI/CD, pipes).
ASCII-based to ensure compatibility across all terminal types.

Trade-offs:
- Performance: Progress updates are throttled to avoid output flooding
- Compatibility: Works in both TTY and non-TTY modes (graceful degradation)
- Simplicity: Pure Python, no external dependencies (tqdm would be overkill)

Extension Points: Can be extended to support multi-line progress (parallel downloads),
nested progress bars, or integration with logging frameworks.

Performance:
- Time Complexity: O(1) for each update operation
- Space Complexity: O(1) - no state accumulation
- Expected Performance: <1ms per update, negligible overhead

Example Usage:
    >>> with ProgressBar(total=100, prefix="Downloading") as pb:
    ...     for i in range(100):
    ...         time.sleep(0.01)
    ...         pb.update(i + 1)
    ...         # Progress bar updates automatically
    >>> # Automatically prints completion message and newline
"""

import os
import sys
import time
from typing import Any, Optional


class ProgressBar:
    """ASCII progress bar for terminal output.

    Features:
    - Animated progress bar with percentage
    - Current/total item counter
    - Customizable prefix message
    - TTY detection for safe degradation
    - Automatic terminal width detection
    - Context manager support for cleanup

    Design Decision: Use █ (U+2588) for filled sections and ░ (U+2591) for empty

    Rationale: These Unicode block characters provide clear visual progress while
    maintaining compatibility with most modern terminals. Alternative ASCII chars
    like '#' and '-' were rejected for being less visually appealing.

    Compatibility: Gracefully degrades to simple logging in non-TTY environments
    (CI/CD, redirected output, etc.)
    """

    def __init__(
        self,
        total: int,
        prefix: str = "Progress",
        bar_width: int = 20,
        show_percentage: bool = True,
        show_counter: bool = True,
        enabled: Optional[bool] = None,
    ):
        """Initialize progress bar.

        Args:
            total: Total number of items to process
            prefix: Message to display before progress bar (e.g., "Downloading")
            bar_width: Width of the progress bar in characters (default: 20)
            show_percentage: Show percentage complete (default: True)
            show_counter: Show current/total counter (default: True)
            enabled: Override TTY detection (None = auto-detect, True = always show, False = disable)

        Example:
            >>> pb = ProgressBar(100, prefix="Syncing agents", bar_width=30)
            >>> pb.update(50, message="agent.md")
            >>> # Displays: Syncing agents [███████████████░░░░░░░░░░░░░░░] 50% (50/100) agent.md
        """
        self.total = total
        self.prefix = prefix
        self.bar_width = bar_width
        self.show_percentage = show_percentage
        self.show_counter = show_counter
        self.current = 0
        self.start_time = time.time()
        self.last_update_time = 0.0
        self.update_throttle = (
            0.1  # Minimum seconds between updates (throttle to 10 Hz)
        )

        # Auto-detect TTY unless explicitly overridden
        if enabled is None:
            self.enabled = self._is_tty()
        else:
            self.enabled = enabled

        # Terminal width detection for preventing overflow
        self.terminal_width = self._get_terminal_width()

    def _is_tty(self) -> bool:
        """Check if stdout is a TTY (interactive terminal).

        Returns:
            True if stdout is a TTY, False otherwise (e.g., piped, redirected)

        Design Decision: Disable progress bars in non-TTY environments

        Rationale: Progress bars use \r (carriage return) for line overwriting,
        which appears as garbage in log files, CI/CD output, and piped commands.
        Detecting TTY ensures clean output in all contexts.

        Example:
            $ python script.py              # TTY - progress bars enabled
            $ python script.py > log.txt    # Non-TTY - simple logging
            $ python script.py | grep foo   # Non-TTY - simple logging
        """
        try:
            return sys.stdout.isatty()
        except AttributeError:
            # sys.stdout might not have isatty() in some environments
            return False

    def _get_terminal_width(self) -> int:
        """Get terminal width for preventing line overflow.

        Returns:
            Terminal width in characters (default: 80 if detection fails)

        Error Handling:
        - OSError: Returns 80 (standard terminal width)
        - AttributeError: Returns 80 (fallback)
        - ValueError: Returns 80 (invalid terminal size)
        """
        try:
            # Try to get terminal size from os module (Python 3.3+)
            size = os.get_terminal_size()
            return size.columns
        except (OSError, AttributeError, ValueError):
            # Fallback to standard terminal width
            return 80

    def update(self, current: int, message: str = "") -> None:
        """Update progress bar to current position.

        Args:
            current: Current progress value (0 to total)
            message: Optional message to display after progress bar (e.g., filename)

        Performance: Updates are throttled to 10 Hz to avoid output flooding.
        Non-TTY mode: Logs milestone updates (0%, 25%, 50%, 75%, 100%) instead of every update.

        Example:
            >>> pb = ProgressBar(10, prefix="Downloading")
            >>> for i in range(10):
            ...     pb.update(i + 1, message=f"file_{i}.md")
            >>> # Progress bar updates in-place, then prints completion
        """
        self.current = min(current, self.total)  # Clamp to total

        # Throttle updates to avoid flooding terminal
        current_time = time.time()
        if (
            current_time - self.last_update_time < self.update_throttle
            and current < self.total
        ):
            return  # Skip update, too soon since last one

        self.last_update_time = current_time

        if not self.enabled:
            # Non-TTY mode: Log milestone updates only
            self._log_milestone(message)
            return

        # TTY mode: Render and display progress bar
        self._render_progress_bar(message)

    def _log_milestone(self, message: str) -> None:
        """Log progress at milestone percentages in non-TTY mode.

        Milestones: 0%, 25%, 50%, 75%, 100%

        Args:
            message: Optional message to include in log

        Design Decision: Log milestones instead of every update in non-TTY

        Rationale: Avoids flooding logs with hundreds of progress lines while
        still providing useful feedback. Rejected logging every update because
        it creates noise in CI/CD logs and log files.

        Respects show_percentage and show_counter settings for consistent output
        across TTY and non-TTY modes.
        """
        percentage = int((self.current / self.total) * 100) if self.total > 0 else 0

        # Log at milestones: 0%, 25%, 50%, 75%, 100%
        milestones = [0, 25, 50, 75, 100]
        if percentage in milestones or self.current == self.total:
            # Build output respecting show_percentage and show_counter settings
            if message and not (self.show_counter or self.show_percentage):
                # Simple format: "Prefix: message"
                output = f"{self.prefix}: {message}"
            else:
                # Complex format with counter/percentage
                parts = [self.prefix]

                if self.show_counter:
                    parts.append(f"{self.current}/{self.total}")

                if self.show_percentage:
                    parts.append(f"({percentage}%)")

                if message:
                    parts.append(f"- {message}")

                output = " ".join(parts)

            print(output, flush=True)

    def _render_progress_bar(self, message: str) -> None:
        """Render and display progress bar in TTY mode.

        Args:
            message: Optional message to display after progress bar

        Output Format:
            [Prefix] [████████░░░░░░░░░░░░] XX% (current/total) message

        Design Decision: Use \r to overwrite same line for animation effect

        Rationale: Creates smooth animation by updating the same line instead
        of printing new lines. Requires TTY for proper display (hence TTY check).

        Terminal Width Handling:
        - Calculates available space based on terminal width
        - Truncates message if output would overflow
        - Ensures progress bar always fits on one line
        """
        percentage = int((self.current / self.total) * 100) if self.total > 0 else 0
        filled = (
            int(self.bar_width * self.current / self.total) if self.total > 0 else 0
        )
        bar = "█" * filled + "░" * (self.bar_width - filled)

        # Build output components
        parts = [f"{self.prefix} [{bar}]"]

        if self.show_percentage:
            parts.append(f"{percentage}%")

        if self.show_counter:
            parts.append(f"({self.current}/{self.total})")

        if message:
            parts.append(message)

        output = " ".join(parts)

        # Truncate if exceeds terminal width (leave 2 chars margin)
        max_width = self.terminal_width - 2
        if len(output) > max_width:
            # Truncate message part, preserve progress bar
            truncate_at = max_width - 3  # Leave room for "..."
            output = output[:truncate_at] + "..."

        # Pad output to terminal width to clear previous longer text
        # This prevents text artifacts when current message is shorter than previous
        padded_output = output.ljust(max_width)

        # Write to stdout with carriage return (overwrite current line)
        sys.stdout.write(f"\r{padded_output}")
        sys.stdout.flush()

    def finish(self, message: str = "Complete") -> None:
        """Complete progress bar and print final message.

        Args:
            message: Final message to display (default: "Complete")

        Design Decision: Print newline after completion to prevent terminal corruption

        Rationale: Without newline, next shell prompt or log message would
        overwrite the final progress bar state. Explicit finish() ensures
        clean terminal output.

        Bug Fix: Avoid duplicate completion messages in non-TTY mode by not
        calling update() again if already at 100%. The final milestone was
        already logged during the last update() call.

        Example:
            >>> pb = ProgressBar(100)
            >>> pb.update(100)
            >>> pb.finish(message="Download complete")
            >>> # Output: [████████████████████] 100% (100/100) Download complete
        """
        if self.enabled:
            # TTY mode: Update to show final message, then add newline
            self.update(self.total, message=message)
            sys.stdout.write("\n")
            sys.stdout.flush()
        # Non-TTY mode: Only log if not already at 100%
        # If already at 100%, _log_milestone() already printed during last update()
        elif self.current < self.total:
            self.update(self.total, message=message)

    def __enter__(self) -> "ProgressBar":
        """Context manager entry.

        Returns:
            Self for use in with statements

        Example:
            >>> with ProgressBar(100, prefix="Processing") as pb:
            ...     for i in range(100):
            ...         pb.update(i + 1)
            >>> # Automatically calls finish() on exit
        """
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """Context manager exit - ensures finish() is called.

        Args:
            exc_type: Exception type (if raised)
            exc_val: Exception value (if raised)
            exc_tb: Exception traceback (if raised)

        Error Handling:
        - Calls finish() even if exception occurred
        - Displays "Failed" message if exception raised
        - Re-raises exception after cleanup

        Returns:
            None (does not suppress exceptions)
        """
        if exc_type is not None:
            # Exception occurred - finish with error message
            self.finish(message="Failed")
        else:
            # Normal completion
            self.finish()

        # Don't suppress exceptions (returning None is equivalent to returning False)


# Convenience function for simple use cases
def create_progress_bar(
    total: int,
    prefix: str = "Progress",
    enabled: Optional[bool] = None,
) -> ProgressBar:
    """Create a progress bar with sensible defaults.

    Args:
        total: Total number of items
        prefix: Progress message
        enabled: Override TTY detection (None = auto)

    Returns:
        Configured ProgressBar instance

    Example:
        >>> pb = create_progress_bar(100, "Downloading agents")
        >>> for i in range(100):
        ...     pb.update(i + 1, message=f"agent_{i}.md")
        >>> pb.finish()
    """
    return ProgressBar(
        total=total,
        prefix=prefix,
        bar_width=20,
        show_percentage=True,
        show_counter=True,
        enabled=enabled,
    )
