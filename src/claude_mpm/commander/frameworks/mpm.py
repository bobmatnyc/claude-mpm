"""Claude MPM framework implementation."""

import shlex
import shutil
from pathlib import Path

from .base import BaseFramework


class MPMFramework(BaseFramework):
    """Claude MPM framework.

    This framework launches Claude MPM with full agent orchestration.

    Example:
        >>> framework = MPMFramework()
        >>> framework.name
        'mpm'
        >>> framework.is_available()
        True
        >>> framework.get_startup_command(Path("/Users/user/myapp"))
        "cd '/Users/user/myapp' && claude-mpm --dangerously-skip-permissions"
    """

    name = "mpm"
    display_name = "Claude MPM"
    command = "claude-mpm"

    def get_startup_command(self, project_path: Path) -> str:
        """Get the command to start Claude MPM in a project.

        Args:
            project_path: Path to the project directory

        Returns:
            Shell command string to start Claude MPM

        Example:
            >>> framework = MPMFramework()
            >>> framework.get_startup_command(Path("/Users/user/myapp"))
            "cd '/Users/user/myapp' && claude-mpm --dangerously-skip-permissions"
        """
        quoted_path = shlex.quote(str(project_path))
        return f"cd {quoted_path} && claude-mpm --dangerously-skip-permissions"

    def is_available(self) -> bool:
        """Check if 'claude-mpm' command is available.

        Returns:
            True if 'claude-mpm' command exists in PATH

        Example:
            >>> framework = MPMFramework()
            >>> framework.is_available()
            True
        """
        return shutil.which("claude-mpm") is not None
