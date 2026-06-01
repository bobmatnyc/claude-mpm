"""Base agent locator service for finding the base agent markdown source.

The single base source of truth is ``BASE_AGENT.md`` (framework
``src/claude_mpm/agents/BASE_AGENT.md``). The legacy ``base_agent.json`` was
removed — its ``narrative_fields.instructions`` were never composed into any
deployed agent (``build_agent_markdown`` only ever read the JSON's absent
top-level ``instructions``/``content`` keys as a fallback), so the file was
inert build bloat. ``BASE_AGENT.md`` is the actively maintained source.
"""

import logging
import os
from pathlib import Path

# Name of the base agent markdown source of truth.
BASE_AGENT_FILENAME = "BASE_AGENT.md"


class BaseAgentLocator:
    """Service for locating the base agent markdown source file.

    This service handles the priority-based search for ``BASE_AGENT.md``
    across multiple possible locations including environment variables,
    development paths, and user overrides.
    """

    def __init__(self, logger: logging.Logger | None = None):
        """Initialize the base agent locator.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)

    def find_base_agent_file(self, paths_agents_dir: Path) -> Path:
        """Find the base agent markdown file with priority-based search.

        Priority order:
        1. Environment variable override (CLAUDE_MPM_BASE_AGENT_PATH)
        2. Current working directory (for local development)
        3. User override location (~/.claude/agents/)
        4. Framework agents directory (from paths)

        Args:
            paths_agents_dir: Framework agents directory from paths

        Returns:
            Path to the base agent markdown file (may not exist; deployment
            tolerates a missing base source — it degrades to an empty base).
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
        cwd_base_agent = (
            Path.cwd() / "src" / "claude_mpm" / "agents" / BASE_AGENT_FILENAME
        )
        if cwd_base_agent.exists():
            self.logger.info(
                f"Using local development base_agent from cwd: {cwd_base_agent}"
            )
            return cwd_base_agent

        # Priority 2: Check user override location
        user_base_agent = Path.home() / ".claude" / "agents" / BASE_AGENT_FILENAME
        if user_base_agent.exists():
            self.logger.info(f"Using user override base_agent: {user_base_agent}")
            return user_base_agent

        # Priority 3: Use framework agents directory (fallback)
        framework_base_agent = paths_agents_dir / BASE_AGENT_FILENAME
        if framework_base_agent.exists():
            self.logger.info(f"Using framework base_agent: {framework_base_agent}")
            return framework_base_agent

        # If still not found, log searched locations. Deployment tolerates a
        # missing base source, so return the framework path for a clear message.
        self.logger.warning(
            f"Base agent markdown not found (CWD: {cwd_base_agent}, "
            f"User: {user_base_agent}, Framework: {framework_base_agent})"
        )
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
