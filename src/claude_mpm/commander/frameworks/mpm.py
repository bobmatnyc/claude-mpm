"""Claude MPM framework implementation."""

import shlex
import shutil
from pathlib import Path

from .base import BaseFramework


class MPMFramework(BaseFramework):
    """Claude MPM framework.

    This framework launches Claude with MPM agent loading via CLAUDE.md.
    It uses the same 'claude' command as Claude Code, but relies on CLAUDE.md
    in the project to load the MPM agent system.

    Example:
        >>> framework = MPMFramework()
        >>> framework.name
        'mpm'
        >>> framework.is_available()
        True
        >>> framework.get_startup_command(Path("/Users/user/myapp"))
        "cd '/Users/user/myapp' && claude --dangerously-skip-permissions"
    """

    name = "mpm"
    display_name = "Claude MPM"
    command = "claude"  # Uses claude with MPM agent loading

    def get_startup_command(self, project_path: Path) -> str:
        """Get the command to start Claude MPM in a project.

        The MPM framework uses the standard 'claude' command, but expects
        a CLAUDE.md file in the project to load the MPM agent system.

        Args:
            project_path: Path to the project directory

        Returns:
            Shell command string to start Claude with MPM

        Example:
            >>> framework = MPMFramework()
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
            >>> framework = MPMFramework()
            >>> framework.is_available()
            True
        """
        return shutil.which("claude") is not None
