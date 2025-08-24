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
    ):
        """
        Initialize the resolver.

        Args:
            working_directory: Current working directory
        """
        self.working_directory = working_directory

    def determine_agents_directory(self, target_dir: Optional[Path]) -> Path:
        """
        Determine the correct agents directory based on input.

        MODIFIED: Always deploy to project .claude/agents directory
        regardless of agent source (system, user, or project).

        This ensures all agents are deployed at the project level while
        maintaining discovery from both user (~/.claude-mpm) and project
        (.claude-mpm) directories.

        Args:
            target_dir: Optional target directory

        Returns:
            Path to agents directory
        """
        if not target_dir:
            # Always deploy to project directory
            # This is the key change - all agents go to project .claude/agents
            return self.working_directory / ".claude" / "agents"

        # If target_dir provided, use it directly (caller decides structure)
        target_dir = Path(target_dir)

        # Check if this is already an agents directory
        if target_dir.name == "agents":
            # Already an agents directory, use as-is
            return target_dir
        if target_dir.name == ".claude-mpm":
            # .claude-mpm directory, add agents subdirectory
            return target_dir / "agents"
        if target_dir.name == ".claude":
            # .claude directory, add agents subdirectory
            return target_dir / "agents"
        # Assume it's a project directory, add .claude/agents
        return target_dir / ".claude" / "agents"
