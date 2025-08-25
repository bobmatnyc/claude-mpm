"""Base agent locator service for finding base agent configuration files."""

import logging
import os
from pathlib import Path
from typing import Optional


class BaseAgentLocator:
    """Service for locating base agent configuration files.

    This service handles the priority-based search for base_agent.json
    files across multiple possible locations including environment
    variables, development paths, and user overrides.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the base agent locator.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)

    def find_base_agent_file(self, paths_agents_dir: Path) -> Path:
        """Find base agent file with priority-based search.

        Priority order:
        1. Environment variable override (CLAUDE_MPM_BASE_AGENT_PATH)
        2. Current working directory (for local development)
        3. Known development locations
        4. User override location (~/.claude/agents/)
        5. Framework agents directory (from paths)

        Args:
            paths_agents_dir: Framework agents directory from paths

        Returns:
            Path to base agent file
        """
        # Priority 0: Check environment variable override
        env_path = os.environ.get("CLAUDE_MPM_BASE_AGENT_PATH")
        if env_path:
            env_base_agent = Path(env_path)
            if env_base_agent.exists():
                self.logger.info(
                    f"Using environment variable base_agent: {env_base_agent}"
                )
                return env_base_agent
            self.logger.warning(
                f"CLAUDE_MPM_BASE_AGENT_PATH set but file doesn't exist: {env_base_agent}"
            )

        # Priority 1: Check current working directory for local development
        cwd = Path.cwd()
        cwd_base_agent = cwd / "src" / "claude_mpm" / "agents" / "base_agent.json"
        if cwd_base_agent.exists():
            self.logger.info(
                f"Using local development base_agent from cwd: {cwd_base_agent}"
            )
            return cwd_base_agent

        # Priority 2: Check known development locations
        known_dev_paths = [
            Path(
                "/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/base_agent.json"
            ),
            Path.home()
            / "Projects"
            / "claude-mpm"
            / "src"
            / "claude_mpm"
            / "agents"
            / "base_agent.json",
            Path.home()
            / "projects"
            / "claude-mpm"
            / "src"
            / "claude_mpm"
            / "agents"
            / "base_agent.json",
        ]

        for dev_path in known_dev_paths:
            if dev_path.exists():
                self.logger.info(f"Using development base_agent: {dev_path}")
                return dev_path

        # Priority 3: Check user override location
        user_base_agent = Path.home() / ".claude" / "agents" / "base_agent.json"
        if user_base_agent.exists():
            self.logger.info(f"Using user override base_agent: {user_base_agent}")
            return user_base_agent

        # Priority 4: Use framework agents directory (fallback)
        framework_base_agent = paths_agents_dir / "base_agent.json"
        if framework_base_agent.exists():
            self.logger.info(f"Using framework base_agent: {framework_base_agent}")
            return framework_base_agent

        # If still not found, log all searched locations and raise error
        self.logger.error("Base agent file not found in any location:")
        self.logger.error(f"  1. CWD: {cwd_base_agent}")
        self.logger.error(f"  2. Dev paths: {known_dev_paths}")
        self.logger.error(f"  3. User: {user_base_agent}")
        self.logger.error(f"  4. Framework: {framework_base_agent}")

        # Final fallback to framework path even if it doesn't exist
        # (will fail later with better error message)
        return framework_base_agent

    def determine_source_tier(self, templates_dir: Path) -> str:
        """Determine the source tier for logging.

        Args:
            templates_dir: Templates directory path

        Returns:
            Source tier string (framework/user/project)
        """
        templates_str = str(templates_dir.resolve())

        # Check if this is a user-level installation
        if str(Path.home()) in templates_str and ".claude-mpm" in templates_str:
            return "user"

        # Check if this is a project-level installation
        if ".claude-mpm" in templates_str:
            return "project"

        # Default to framework
        return "framework"
