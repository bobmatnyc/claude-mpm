"""Event detection for MPM Commander output."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EventType(Enum):
    """Types of events that can be detected in output."""

    ERROR = "error"
    IDLE = "idle"


@dataclass
class DetectedEvent:
    """An event detected in session output."""

    event_type: EventType
    content: str
    context: str  # Surrounding lines for context
    line_number: Optional[int] = None


class BasicEventDetector:
    """Phase 1: Detect errors and idle states only."""

    # ANSI escape code pattern
    ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    ERROR_PATTERNS = [
        r"Error:",
        r"Failed:",
        r"Exception:",
        r"Traceback \(most recent call last\):",
        r"Permission denied",
        r"command not found",
        r"FATAL:",
        r"✗",  # Claude Code error indicator
    ]

    IDLE_PATTERNS = [
        r"^>\s*$",  # Claude Code prompt
        r"^claude>\s*$",  # Alternative prompt
        r"^\$\s*$",  # Shell prompt
        r"What would you like",
    ]

    def strip_ansi(self, text: str) -> str:
        """Remove ANSI escape codes from text.

        Args:
            text: Text potentially containing ANSI codes

        Returns:
            Clean text with ANSI codes removed
        """
        return self.ANSI_ESCAPE.sub("", text)

    def detect_error(self, content: str) -> Optional[DetectedEvent]:
        """Check for error patterns in output.

        Args:
            content: Output content to check

        Returns:
            DetectedEvent if error found, None otherwise
        """
        clean = self.strip_ansi(content)
        lines = clean.split("\n")

        for i, line in enumerate(lines):
            for pattern in self.ERROR_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    # Extract context (3 lines before/after)
                    start = max(0, i - 3)
                    end = min(len(lines), i + 4)
                    context = "\n".join(lines[start:end])

                    return DetectedEvent(
                        event_type=EventType.ERROR,
                        content=line.strip(),
                        context=context,
                        line_number=i + 1,
                    )
        return None

    def detect_idle(self, content: str) -> bool:
        """Check if tool is waiting for input (last line is a prompt).

        Args:
            content: Output content to check

        Returns:
            True if session appears to be idle (waiting for input)
        """
        clean = self.strip_ansi(content)
        lines = clean.strip().split("\n")
        if not lines:
            return False

        last_line = lines[-1]
        return any(re.search(p, last_line) for p in self.IDLE_PATTERNS)
