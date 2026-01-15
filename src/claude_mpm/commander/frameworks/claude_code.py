"""Claude Code (cc) framework implementation."""

import shlex
import shutil
from pathlib import Path

from .base import BaseFramework


class ClaudeCodeFramework(BaseFramework):
    """Claude Code CLI framework.

    This framework launches the standard Claude Code CLI in a project directory.
    It uses the 'claude' command with appropriate flags for automated operation.

    Example:
        >>> framework = ClaudeCodeFramework()
        >>> framework.name
        'cc'
        >>> framework.is_available()
        True
        >>> framework.get_startup_command(Path("/Users/user/myapp"))
        "cd '/Users/user/myapp' && claude --dangerously-skip-permissions"
    """

    name = "cc"
    display_name = "Claude Code"
    command = "claude"

    def get_startup_command(self, project_path: Path) -> str:
        """Get the command to start Claude Code in a project.

        Args:
            project_path: Path to the project directory

        Returns:
            Shell command string to start Claude Code

        Example:
            >>> framework = ClaudeCodeFramework()
            >>> framework.get_startup_command(Path("/Users/user/myapp"))
            "cd '/Users/user/myapp' && claude --dangerously-skip-permissions"
        """
        quoted_path = shlex.quote(str(project_path))
        return f"cd {quoted_path} && claude --dangerously-skip-permissions"

    def is_available(self) -> bool:
        """Check if 'claude' command is available.

        Returns:
            True if 'claude' command exists in PATH

        Example:
            >>> framework = ClaudeCodeFramework()
            >>> framework.is_available()
            True
        """
        return shutil.which("claude") is not None
