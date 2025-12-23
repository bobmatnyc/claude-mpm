"""Agents directory resolution for deployment service.

This module handles determining the correct agents directory for deployment
based on different deployment scenarios and target directories.

DEPLOYMENT ARCHITECTURE:
=======================

Agent Source Locations (Discovery):
-----------------------------------
1. System Agents:  ~/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents/
   - Synced from GitHub repository
   - Read-only (managed by git pull)
   - 44+ agents organized by category

2. User Agents:    ~/.claude-mpm/agents/
   - User-created custom agents
   - Personal agent definitions

3. Project Agents: .claude-mpm/agents/
   - Project-specific agents
   - Overrides for system/user agents

Agent Deployment Target (Runtime):
----------------------------------
ALL AGENTS DEPLOY TO: <project_root>/.claude/agents/
   - Single deployment location for ALL agents (system, user, project)
   - Claude Code discovers agents from this directory
   - Ensures consistent agent availability across sessions
   - Simplifies agent management and version control

Why Project-Level Deployment?
------------------------------
1. **Consistency**: All team members work with same agents
2. **Versioning**: Agent deployments tracked in git
3. **Isolation**: Different projects can have different agent versions
4. **Performance**: No global agent conflicts or version mismatches

Example Flow:
-------------
1. User runs: claude-mpm agents deploy
2. Agents synced from GitHub → ~/.claude-mpm/cache/agents/
3. Agents deployed FROM cache → .claude/agents/
4. Claude Code discovers agents FROM .claude/agents/

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

        DEPLOYMENT STRATEGY:
        ====================
        Always deploy to project .claude/agents directory regardless of agent
        source (system, user, or project). This ensures:
        - All agents available in single location
        - Claude Code agent discovery works consistently
        - Version control tracks deployed agents
        - No global agent conflicts between projects

        LOGIC FLOW:
        -----------
        1. If target_dir is None (default case):
           → Deploy to: <working_directory>/.claude/agents
           → This is 99% of use cases (standard deployment)

        2. If target_dir is provided explicitly:
           → Normalize the path based on directory name:
             - Already "agents" directory? → Use as-is
             - Is ".claude-mpm" directory? → Add /agents
             - Is ".claude" directory? → Add /agents
             - Otherwise? → Treat as project root, add /.claude/agents

        EXAMPLES:
        ---------
        Standard deployment (target_dir=None):
          working_directory = /Users/masa/Projects/my-app
          → Returns: /Users/masa/Projects/my-app/.claude/agents

        Explicit target (target_dir="/some/path/.claude"):
          → Returns: /some/path/.claude/agents

        Explicit target (target_dir="/some/path/.claude/agents"):
          → Returns: /some/path/.claude/agents (no modification)

        Args:
            target_dir: Optional target directory override
                       None = use default project .claude/agents (recommended)
                       Path = explicitly specify deployment location (advanced)

        Returns:
            Path: Resolved agents directory path

        Note:
            The default behavior (target_dir=None) is the recommended approach.
            Only provide target_dir for advanced use cases or testing.
        """
        if not target_dir:
            # DEFAULT CASE: Deploy to project .claude/agents directory
            # This is the standard behavior for all normal deployments
            # Example: /Users/masa/Projects/my-app → /Users/masa/Projects/my-app/.claude/agents
            return self.working_directory / ".claude" / "agents"

        # EXPLICIT TARGET CASE: User/caller provided specific target directory
        # Normalize target_dir to proper agents directory based on structure
        target_dir = Path(target_dir)

        # Pattern 1: Already an agents directory
        if target_dir.name == "agents":
            # Already targeting agents dir explicitly, use as-is
            # Example: /some/path/.claude/agents → /some/path/.claude/agents
            return target_dir

        # Pattern 2: Targeting .claude-mpm directory
        if target_dir.name == ".claude-mpm":
            # Add agents subdirectory to .claude-mpm
            # Example: /some/path/.claude-mpm → /some/path/.claude-mpm/agents
            return target_dir / "agents"

        # Pattern 3: Targeting .claude directory
        if target_dir.name == ".claude":
            # Add agents subdirectory to .claude
            # Example: /some/path/.claude → /some/path/.claude/agents
            return target_dir / "agents"

        # Pattern 4: Targeting project root or other directory
        # Assume it's a project directory, add full .claude/agents path
        # Example: /some/project → /some/project/.claude/agents
        return target_dir / ".claude" / "agents"
