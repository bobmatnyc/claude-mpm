"""Base framework abstraction for different AI coding assistants."""

import subprocess  # nosec B404 - Required for git operations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class InstanceInfo:
    """Information about a running framework instance.

    Attributes:
        name: Instance name (e.g., "myapp")
        project_path: Path to project directory
        framework: Framework identifier (e.g., "cc", "mpm")
        tmux_session: Tmux session name
        pane_target: Tmux pane target (e.g., "%1")
        git_branch: Current git branch if project is a git repo
        git_status: Git status summary if project is a git repo
        connected: Whether instance has an active adapter connection

    Example:
        >>> info = InstanceInfo(
        ...     name="myapp",
        ...     project_path=Path("/Users/user/myapp"),
        ...     framework="cc",
        ...     tmux_session="mpm-commander",
        ...     pane_target="%1",
        ...     git_branch="main",
        ...     git_status="clean",
        ...     connected=True
        ... )
    """

    name: str
    project_path: Path
    framework: str
    tmux_session: str
    pane_target: str
    git_branch: Optional[str] = None
    git_status: Optional[str] = None
    connected: bool = False


@dataclass
class RegisteredInstance:
    """Persistent instance configuration (survives daemon restart).

    Attributes:
        name: Instance identifier
        path: Project directory path (stored as string for JSON)
        framework: Framework identifier ("cc" or "mpm")
        registered_at: ISO timestamp when instance was registered

    Example:
        >>> instance = RegisteredInstance(
        ...     name="myapp",
        ...     path="/Users/user/myapp",
        ...     framework="cc",
        ...     registered_at="2024-01-15T10:30:00"
        ... )
        >>> instance.to_dict()
        {'name': 'myapp', 'path': '/Users/user/myapp', 'framework': 'cc', 'registered_at': '2024-01-15T10:30:00'}
    """

    name: str
    path: str
    framework: str
    registered_at: str

    def to_dict(self) -> dict:
        """Serialize for JSON storage."""
        return {
            "name": self.name,
            "path": self.path,
            "framework": self.framework,
            "registered_at": self.registered_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RegisteredInstance":
        """Deserialize from JSON."""
        return cls(
            name=data["name"],
            path=data["path"],
            framework=data["framework"],
            registered_at=data.get("registered_at", ""),
        )


class BaseFramework(ABC):
    """Base class for AI coding assistant frameworks.

    A framework represents a specific AI coding tool (Claude Code, Claude MPM, etc.)
    that can be launched in a project directory via tmux.

    Attributes:
        name: Short identifier (e.g., "cc", "mpm")
        display_name: Human-readable name (e.g., "Claude Code", "Claude MPM")
        command: The command to run (e.g., "claude")

    Example:
        >>> class MyFramework(BaseFramework):
        ...     name = "my"
        ...     display_name = "My Framework"
        ...     command = "my-command"
        ...
        ...     def get_startup_command(self, project_path: Path) -> str:
        ...         return f"cd {project_path} && my-command"
        ...
        ...     def is_available(self) -> bool:
        ...         return True
    """

    name: str  # "cc", "mpm", etc.
    display_name: str  # "Claude Code", "Claude MPM", etc.
    command: str  # The command to run

    @abstractmethod
    def get_startup_command(self, project_path: Path) -> str:
        """Get the command to start this framework in a project.

        Args:
            project_path: Path to the project directory

        Returns:
            Shell command string to start the framework

        Example:
            >>> framework = ClaudeCodeFramework()
            >>> framework.get_startup_command(Path("/Users/user/myapp"))
            "cd /Users/user/myapp && claude"
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this framework is installed/available.

        Returns:
            True if the framework command is available on the system

        Example:
            >>> framework = ClaudeCodeFramework()
            >>> framework.is_available()
            True
        """

    def get_git_info(self, project_path: Path) -> tuple[Optional[str], Optional[str]]:
        """Get git branch and status for project.

        Args:
            project_path: Path to the project directory

        Returns:
            Tuple of (branch, status) where:
            - branch: Current git branch name or None if not a git repo
            - status: "clean" if no changes, "dirty" if changes, or None if not a git repo

        Example:
            >>> framework = ClaudeCodeFramework()
            >>> branch, status = framework.get_git_info(Path("/Users/user/myapp"))
            >>> print(branch, status)
            main clean
        """
        if not (project_path / ".git").exists():
            return None, None

        try:
            # Get current branch
            result = subprocess.run(  # nosec B603, B607 - Controlled git command
                ["git", "-C", str(project_path), "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            branch = result.stdout.strip()

            # Check if working directory is clean
            result = subprocess.run(  # nosec B603, B607 - Controlled git command
                ["git", "-C", str(project_path), "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            )
            status = "clean" if not result.stdout.strip() else "dirty"

            return branch, status

        except (subprocess.CalledProcessError, FileNotFoundError):
            return None, None
