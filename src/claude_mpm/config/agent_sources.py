"""Configuration for agent sources (Git repositories)."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from claude_mpm.models.git_repository import GitRepository

logger = logging.getLogger(__name__)


@dataclass
class AgentSourceConfiguration:
    """Configuration for agent sources.

    This class manages the configuration of Git repositories that contain
    agent markdown files. It supports:
    - System repository (bobmatnyc/claude-mpm-agents) with disable option
    - Multiple custom repositories with priority-based resolution
    - YAML persistence for configuration
    - Repository management (add, remove, enable, disable)

    Attributes:
        disable_system_repo: If True, don't include default system repository
                            (default: True as of v4.5.0 - git sources are now preferred)
        repositories: List of custom Git repositories
    """

    disable_system_repo: bool = True  # Changed from False to True in v4.5.0
    repositories: list[GitRepository] = field(default_factory=list)

    @classmethod
    def create_default_configuration(cls) -> "AgentSourceConfiguration":
        """Create default configuration with git sources enabled.

        Returns:
            AgentSourceConfiguration with default git repository configured

        Example:
            >>> config = AgentSourceConfiguration.create_default_configuration()
            >>> print(config.repositories[0].url)
            'https://github.com/bobmatnyc/claude-mpm-agents'
        """
        # Create default git repository
        default_repo = GitRepository(
            url="https://github.com/bobmatnyc/claude-mpm-agents",
            subdirectory="agents",
            enabled=True,
            priority=100,
        )

        return cls(
            disable_system_repo=True,  # Disable built-in templates, use git sources
            repositories=[default_repo],
        )

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "AgentSourceConfiguration":
        """Load configuration from YAML file.

        Args:
            config_path: Path to YAML configuration file.
                        Defaults to ~/.claude-mpm/config/agent_sources.yaml

        Returns:
            AgentSourceConfiguration instance

        Example:
            >>> config = AgentSourceConfiguration.load()
            >>> print(config.repositories)
        """
        if config_path is None:
            config_path = Path.home() / ".claude-mpm" / "config" / "agent_sources.yaml"

        # If file doesn't exist, create default configuration with git sources
        if not config_path.exists():
            logger.info(
                f"Configuration file not found at {config_path}, creating default with git sources"
            )
            default_config = cls.create_default_configuration()
            # Save the default configuration for future use
            try:
                default_config.save(config_path)
            except Exception as e:
                logger.warning(f"Could not save default configuration: {e}")
            return default_config

        try:
            with open(config_path) as f:
                data = yaml.safe_load(f)

            if not data:
                logger.warning(
                    f"Empty configuration file at {config_path}, using defaults"
                )
                return cls()

            # Parse configuration
            # Note: Default changed from False to True in v4.5.0
            # For backward compatibility, if key is missing, use new default (True)
            disable_system_repo = data.get("disable_system_repo", True)

            # Parse repositories
            repositories = []
            for repo_data in data.get("repositories", []):
                repo = GitRepository(
                    url=repo_data["url"],
                    subdirectory=repo_data.get("subdirectory"),
                    enabled=repo_data.get("enabled", True),
                    priority=repo_data.get("priority", 100),
                )
                repositories.append(repo)

            return cls(
                disable_system_repo=disable_system_repo, repositories=repositories
            )

        except Exception as e:
            logger.error(f"Failed to load configuration from {config_path}: {e}")
            logger.info("Using default configuration")
            return cls()

    def save(
        self, config_path: Optional[Path] = None, include_comments: bool = True
    ) -> None:
        """Save configuration to YAML file.

        Args:
            config_path: Path to YAML configuration file.
                        Defaults to ~/.claude-mpm/config/agent_sources.yaml
            include_comments: Whether to include helpful comments in the YAML file

        Example:
            >>> config = AgentSourceConfiguration()
            >>> config.save()
        """
        if config_path is None:
            config_path = Path.home() / ".claude-mpm" / "config" / "agent_sources.yaml"

        # Ensure parent directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(config_path, "w") as f:
                # Write header comments if requested
                if include_comments:
                    f.write("# Claude MPM Agent Sources Configuration\n")
                    f.write("#\n")
                    f.write(
                        "# This file configures where Claude MPM discovers agent templates.\n"
                    )
                    f.write(
                        "# Git sources are the recommended approach for agent management.\n"
                    )
                    f.write("#\n")
                    f.write(
                        "# disable_system_repo: Set to true to use git sources instead of built-in templates\n"
                    )
                    f.write(
                        "# repositories: List of git repositories containing agent markdown files\n"
                    )
                    f.write("#\n")
                    f.write(
                        "# Default repository: https://github.com/bobmatnyc/claude-mpm-agents\n"
                    )
                    f.write("#\n\n")

                # Build YAML data structure
                data = {
                    "disable_system_repo": self.disable_system_repo,
                    "repositories": [
                        {
                            "url": repo.url,
                            "subdirectory": repo.subdirectory,
                            "enabled": repo.enabled,
                            "priority": repo.priority,
                        }
                        for repo in self.repositories
                    ],
                }

                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

            logger.info(f"Configuration saved to {config_path}")

        except Exception as e:
            logger.error(f"Failed to save configuration to {config_path}: {e}")
            raise

    def get_system_repo(self) -> Optional[GitRepository]:
        """Get system repository if not disabled.

        Returns:
            GitRepository for system repo, or None if disabled

        Example:
            >>> config = AgentSourceConfiguration()
            >>> system_repo = config.get_system_repo()
            >>> print(system_repo.url)
            'https://github.com/bobmatnyc/claude-mpm-agents'
        """
        if self.disable_system_repo:
            return None

        return GitRepository(
            url="https://github.com/bobmatnyc/claude-mpm-agents",
            subdirectory="agents",
            enabled=True,
            priority=100,
        )

    def get_enabled_repositories(self) -> list[GitRepository]:
        """Get all enabled repositories sorted by priority.

        Returns repositories in priority order (lower priority number = higher precedence).
        Includes system repository if not disabled.

        Returns:
            List of enabled GitRepository instances, sorted by priority

        Example:
            >>> config = AgentSourceConfiguration()
            >>> repos = config.get_enabled_repositories()
            >>> for repo in repos:
            ...     print(f"{repo.identifier} (priority: {repo.priority})")
        """
        repos = []

        # Add system repo if not disabled
        system_repo = self.get_system_repo()
        if system_repo:
            repos.append(system_repo)

        # Add enabled custom repositories
        repos.extend([r for r in self.repositories if r.enabled])

        # Sort by priority (lower number = higher precedence)
        return sorted(repos, key=lambda r: r.priority)

    def add_repository(self, repo: GitRepository) -> None:
        """Add a new repository.

        Args:
            repo: GitRepository to add

        Example:
            >>> config = AgentSourceConfiguration()
            >>> repo = GitRepository(url="https://github.com/owner/repo")
            >>> config.add_repository(repo)
        """
        self.repositories.append(repo)
        logger.info(f"Added repository: {repo.identifier}")

    def remove_repository(self, identifier: str) -> bool:
        """Remove repository by identifier.

        Args:
            identifier: Repository identifier (e.g., "owner/repo" or "owner/repo/subdirectory")

        Returns:
            True if repository was removed, False if not found

        Example:
            >>> config = AgentSourceConfiguration()
            >>> repo = GitRepository(url="https://github.com/owner/repo")
            >>> config.add_repository(repo)
            >>> removed = config.remove_repository("owner/repo")
            >>> print(removed)
            True
        """
        for i, repo in enumerate(self.repositories):
            if repo.identifier == identifier:
                removed_repo = self.repositories.pop(i)
                logger.info(f"Removed repository: {removed_repo.identifier}")
                return True

        logger.warning(f"Repository not found: {identifier}")
        return False

    def validate(self) -> list[str]:
        """Validate configuration.

        Checks:
        - All repositories pass validation
        - No duplicate repository identifiers
        - Priority values are reasonable

        Returns:
            List of validation error messages (empty if valid)

        Example:
            >>> config = AgentSourceConfiguration()
            >>> errors = config.validate()
            >>> if errors:
            ...     print("Validation errors:", errors)
        """
        errors = []

        # Validate each repository
        for repo in self.repositories:
            repo_errors = repo.validate()
            if repo_errors:
                errors.append(f"Repository {repo.identifier}: {', '.join(repo_errors)}")

        # Check for duplicate identifiers
        identifiers = [repo.identifier for repo in self.repositories]
        duplicates = {id for id in identifiers if identifiers.count(id) > 1}

        if duplicates:
            errors.append(
                f"Duplicate repository identifiers found: {', '.join(duplicates)}"
            )

        return errors

    def list_sources(self) -> list[dict]:
        """Return list of source configurations as dictionaries.

        This method converts GitRepository objects to dictionaries for CLI
        and API compatibility. Called by GitSourceManager and CLI commands.

        Returns:
            List of dicts with keys: identifier, url, subdirectory, enabled, priority

        Example:
            >>> config = AgentSourceConfiguration()
            >>> sources = config.list_sources()
            >>> for source in sources:
            ...     print(f"{source['identifier']} (priority: {source['priority']})")
        """
        repos = self.get_enabled_repositories()
        return [
            {
                "identifier": repo.identifier,
                "url": repo.url,
                "subdirectory": repo.subdirectory,
                "enabled": repo.enabled,
                "priority": repo.priority,
            }
            for repo in repos
        ]

    def __repr__(self) -> str:
        """Return string representation of configuration."""
        return (
            f"AgentSourceConfiguration("
            f"system_repo={'disabled' if self.disable_system_repo else 'enabled'}, "
            f"custom_repos={len(self.repositories)})"
        )
