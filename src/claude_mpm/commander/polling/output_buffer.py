"""Output buffer for tracking session output changes."""

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class OutputBuffer:
    """Tracks output from a session and detects changes."""

    session_id: str
    content: str = ""
    last_hash: str = ""
    last_update: Optional[datetime] = None
    lines_captured: int = 0

    def update(self, new_content: str) -> tuple[bool, str]:
        """Update buffer with new content.

        Args:
            new_content: The new output content to check

        Returns:
            Tuple of (has_changed, new_lines_only)
            - has_changed: True if content changed since last update
            - new_lines_only: Only the new lines added (diff)
        """
        new_hash = hashlib.md5(new_content.encode(), usedforsecurity=False).hexdigest()
        if new_hash == self.last_hash:
            return False, ""

        # Find new lines (diff)
        old_lines = self.content.split("\n") if self.content else []
        new_lines = new_content.split("\n")

        # Simple diff: new lines at the end
        if len(new_lines) > len(old_lines):
            diff = "\n".join(new_lines[len(old_lines) :])
        else:
            diff = new_content  # Content replaced entirely

        self.content = new_content
        self.last_hash = new_hash
        self.last_update = datetime.now(timezone.utc)
        self.lines_captured = len(new_lines)

        return True, diff
