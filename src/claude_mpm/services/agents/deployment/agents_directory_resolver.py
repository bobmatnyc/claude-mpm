"""Agents directory resolution for deployment service.

This module handles determining the correct agents directory for deployment
based on different deployment scenarios and target directories.
Extracted from AgentDeploymentService to reduce complexity.
"""

from pathlib import Path
from typing import Optional


class AgentsDirectoryResolver:
    """Resolves the correct agents directory for deployment."""

    def __init__(
        self,
        working_directory: Path,
        is_system_deployment: bool,
        is_project_specific: bool,
    ):
        """
        Initialize the resolver.

        Args:
            working_directory: Current working directory
            is_system_deployment: Whether this is a system agent deployment
            is_project_specific: Whether this is a project-specific deployment
        """
        self.working_directory = working_directory
        self.is_system_deployment = is_system_deployment
        self.is_project_specific = is_project_specific

    def determine_agents_directory(self, target_dir: Optional[Path]) -> Path:
        """
        Determine the correct agents directory based on input.

        Different deployment scenarios require different directory
        structures. This method centralizes the logic for consistency.

        HIERARCHY:
        - System agents → Deploy to ~/.claude/agents/ (user's home directory)
        - User custom agents from ~/.claude-mpm/agents/ → Deploy to ~/.claude/agents/
        - Project-specific agents from <project>/.claude-mpm/agents/ → Deploy to <project>/.claude/agents/

        Args:
            target_dir: Optional target directory

        Returns:
            Path to agents directory
        """
        if not target_dir:
            # Default deployment location depends on agent source
            # Check if we're deploying system agents or user/project agents
            if self.is_system_deployment:
                # System agents go to user's home ~/.claude/agents/
                return Path.home() / ".claude" / "agents"
            elif self.is_project_specific:
                # Project agents stay in project directory
                return self.working_directory / ".claude" / "agents"
            else:
                # Default: User custom agents go to home ~/.claude/agents/
                return Path.home() / ".claude" / "agents"

        # If target_dir provided, use it directly (caller decides structure)
        target_dir = Path(target_dir)

        # Check if this is already an agents directory
        if target_dir.name == "agents":
            # Already an agents directory, use as-is
            return target_dir
        elif target_dir.name == ".claude-mpm":
            # .claude-mpm directory, add agents subdirectory
            return target_dir / "agents"
        elif target_dir.name == ".claude":
            # .claude directory, add agents subdirectory
            return target_dir / "agents"
        else:
            # Assume it's a project directory, add .claude/agents
            return target_dir / ".claude" / "agents"
