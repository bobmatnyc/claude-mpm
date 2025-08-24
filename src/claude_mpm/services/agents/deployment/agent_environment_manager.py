"""Agent Environment Manager Service

This service handles environment configuration for Claude agent discovery and execution.
Manages environment variables, paths, and runtime configuration.

Extracted from AgentDeploymentService as part of the refactoring to improve
maintainability and testability.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from claude_mpm.core.logging_config import get_logger


class AgentEnvironmentManager:
    """Service for managing Claude agent environment configuration.

    This service handles:
    - Setting Claude environment variables
    - Managing agent discovery paths
    - Configuring runtime parameters
    - Environment validation and verification
    """

    def __init__(self):
        """Initialize the environment manager."""
        self.logger = get_logger(__name__)

    def set_claude_environment(
        self, config_dir: Optional[Path] = None
    ) -> Dict[str, str]:
        """
        Set Claude environment variables for agent discovery.

        This configures the environment so Claude can discover and use deployed agents.
        Essential for proper agent functionality in Claude Code.

        Args:
            config_dir: Claude configuration directory (default: .claude/)

        Returns:
            Dictionary of environment variables that were set
        """
        if not config_dir:
            config_dir = Path.cwd() / ".claude"

        # Ensure config directory exists
        config_dir.mkdir(parents=True, exist_ok=True)

        # Set environment variables for Claude agent discovery
        env_vars = {
            "CLAUDE_CONFIG_DIR": str(config_dir.absolute()),
            "CLAUDE_MAX_PARALLEL_SUBAGENTS": "3",  # Reasonable default
            "CLAUDE_TIMEOUT": "300",  # 5 minutes default timeout
        }

        # Apply environment variables
        for key, value in env_vars.items():
            os.environ[key] = value
            self.logger.debug(f"Set environment variable: {key}={value}")

        self.logger.info(
            f"Claude environment configured for agent discovery in {config_dir}"
        )
        return env_vars

    def get_current_environment(self) -> Dict[str, str]:
        """
        Get current Claude-related environment variables.

        Returns:
            Dictionary of current Claude environment variables
        """
        claude_env_vars = {}

        # Check for Claude-specific environment variables
        claude_prefixes = ["CLAUDE_", "ANTHROPIC_"]

        for key, value in os.environ.items():
            if any(key.startswith(prefix) for prefix in claude_prefixes):
                claude_env_vars[key] = value

        return claude_env_vars

    def validate_environment(self, config_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Validate the current Claude environment configuration.

        Args:
            config_dir: Claude configuration directory to validate

        Returns:
            Dictionary with validation results
        """
        if not config_dir:
            config_dir = Path.cwd() / ".claude"

        validation_results = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "config_dir_exists": False,
            "agents_dir_exists": False,
            "environment_variables": {},
            "recommendations": [],
        }

        # Check if config directory exists
        if config_dir.exists():
            validation_results["config_dir_exists"] = True
            self.logger.debug(f"Config directory exists: {config_dir}")
        else:
            validation_results["valid"] = False
            validation_results["errors"].append(
                f"Config directory does not exist: {config_dir}"
            )

        # Check if agents directory exists
        agents_dir = config_dir / "agents"
        if agents_dir.exists():
            validation_results["agents_dir_exists"] = True
            self.logger.debug(f"Agents directory exists: {agents_dir}")
        else:
            validation_results["warnings"].append(
                f"Agents directory does not exist: {agents_dir}"
            )

        # Check environment variables
        current_env = self.get_current_environment()
        validation_results["environment_variables"] = current_env

        # Validate required environment variables
        required_vars = ["CLAUDE_CONFIG_DIR"]
        for var in required_vars:
            if var not in current_env:
                validation_results["warnings"].append(
                    f"Missing environment variable: {var}"
                )
                validation_results["recommendations"].append(
                    f"Set {var} to point to your Claude config directory"
                )

        # Check if CLAUDE_CONFIG_DIR points to the right place
        if "CLAUDE_CONFIG_DIR" in current_env:
            env_config_dir = Path(current_env["CLAUDE_CONFIG_DIR"])
            if env_config_dir != config_dir.absolute():
                validation_results["warnings"].append(
                    f"CLAUDE_CONFIG_DIR ({env_config_dir}) doesn't match expected path ({config_dir.absolute()})"
                )

        # Performance recommendations
        if "CLAUDE_MAX_PARALLEL_SUBAGENTS" not in current_env:
            validation_results["recommendations"].append(
                "Consider setting CLAUDE_MAX_PARALLEL_SUBAGENTS for better performance"
            )

        if "CLAUDE_TIMEOUT" not in current_env:
            validation_results["recommendations"].append(
                "Consider setting CLAUDE_TIMEOUT to prevent long-running operations"
            )

        return validation_results

    def setup_development_environment(
        self, config_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Set up a complete development environment for Claude agents.

        Args:
            config_dir: Claude configuration directory

        Returns:
            Dictionary with setup results
        """
        if not config_dir:
            config_dir = Path.cwd() / ".claude"

        setup_results = {
            "success": True,
            "created_directories": [],
            "set_environment_variables": {},
            "errors": [],
        }

        try:
            # Create necessary directories
            directories_to_create = [
                config_dir,
                config_dir / "agents",
                config_dir / "logs",
                config_dir / "cache",
            ]

            for directory in directories_to_create:
                if not directory.exists():
                    directory.mkdir(parents=True, exist_ok=True)
                    setup_results["created_directories"].append(str(directory))
                    self.logger.info(f"Created directory: {directory}")

            # Set up environment variables
            env_vars = self.set_claude_environment(config_dir)
            setup_results["set_environment_variables"] = env_vars

            # Create a basic .gitignore for the config directory
            gitignore_path = config_dir / ".gitignore"
            if not gitignore_path.exists():
                gitignore_content = """# Claude configuration files
logs/
cache/
*.log
*.tmp

# Keep agents directory but ignore specific files if needed
# agents/
"""
                gitignore_path.write_text(gitignore_content)
                self.logger.info(f"Created .gitignore: {gitignore_path}")

        except Exception as e:
            setup_results["success"] = False
            setup_results["errors"].append(str(e))
            self.logger.error(f"Failed to set up development environment: {e}")

        return setup_results

    def get_environment_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the current environment.

        Returns:
            Dictionary with environment information
        """
        current_env = self.get_current_environment()

        return {
            "claude_environment_variables": current_env,
            "python_path": os.environ.get("PYTHONPATH", "Not set"),
            "current_working_directory": str(Path.cwd()),
            "user_home_directory": str(Path.home()),
            "claude_config_locations": self._find_claude_config_locations(),
        }

    def cleanup_environment(self) -> Dict[str, Any]:
        """
        Clean up Claude environment variables.

        Returns:
            Dictionary with cleanup results
        """
        cleanup_results = {"removed_variables": [], "errors": []}

        try:
            # Remove Claude-specific environment variables
            claude_vars = [key for key in os.environ if key.startswith("CLAUDE_")]

            for var in claude_vars:
                if var in os.environ:
                    del os.environ[var]
                    cleanup_results["removed_variables"].append(var)
                    self.logger.debug(f"Removed environment variable: {var}")

            self.logger.info(
                f"Cleaned up {len(cleanup_results['removed_variables'])} environment variables"
            )

        except Exception as e:
            cleanup_results["errors"].append(str(e))
            self.logger.error(f"Error during environment cleanup: {e}")

        return cleanup_results

    def _find_claude_config_locations(self) -> list:
        """Find potential Claude configuration directories."""
        potential_locations = [
            Path.cwd() / ".claude",
            Path.home() / ".claude",
            Path.home() / ".config" / "claude",
        ]

        existing_locations = []
        for location in potential_locations:
            if location.exists():
                existing_locations.append(str(location))

        return existing_locations
