"""Deployment configuration data class."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class DeploymentConfig:
    """Configuration for agent deployment operations.

    This class encapsulates all configuration settings related to
    agent deployment, providing a clean interface for accessing
    deployment-specific settings.
    """

    # Agent exclusion settings
    excluded_agents: List[str] = field(default_factory=list)
    case_sensitive_exclusion: bool = True
    user_excluded_agents: List[str] = field(default_factory=list)

    # Deployment behavior settings
    force_rebuild: bool = False
    deployment_mode: str = "update"  # "update" or "project"
    use_async: bool = False

    # Directory settings
    target_dir: Optional[Path] = None
    templates_dir: Optional[Path] = None
    base_agent_path: Optional[Path] = None
    working_directory: Optional[Path] = None

    # System instructions settings
    deploy_system_instructions: bool = True
    deploy_user_instructions: bool = True

    # Validation and repair settings
    repair_existing_agents: bool = True
    validate_agents: bool = True

    # Metrics and logging settings
    collect_metrics: bool = True
    log_level: str = "INFO"

    # Performance settings
    max_concurrent_operations: int = 10
    timeout_seconds: int = 300

    # Environment settings
    environment: str = "production"  # "development", "testing", "production"

    # Additional settings
    extra_settings: Dict[str, Any] = field(default_factory=dict)

    def is_development_mode(self) -> bool:
        """Check if running in development mode.

        Returns:
            True if in development mode
        """
        return self.environment == "development"

    def is_testing_mode(self) -> bool:
        """Check if running in testing mode.

        Returns:
            True if in testing mode
        """
        return self.environment == "testing"

    def is_production_mode(self) -> bool:
        """Check if running in production mode.

        Returns:
            True if in production mode
        """
        return self.environment == "production"

    def should_exclude_agent(self, agent_name: str) -> bool:
        """Check if an agent should be excluded from deployment.

        Args:
            agent_name: Name of the agent to check

        Returns:
            True if the agent should be excluded
        """
        if self.case_sensitive_exclusion:
            return agent_name in self.excluded_agents
        return agent_name.lower() in [name.lower() for name in self.excluded_agents]

    def get_effective_excluded_agents(self) -> List[str]:
        """Get the effective list of excluded agents.

        Combines regular excluded agents with user-specific exclusions.

        Returns:
            List of all excluded agent names
        """
        all_excluded = self.excluded_agents.copy()
        all_excluded.extend(self.user_excluded_agents)
        return list(set(all_excluded))  # Remove duplicates

    def merge_with_dict(self, config_dict: Dict[str, Any]) -> "DeploymentConfig":
        """Merge this config with a dictionary of settings.

        Args:
            config_dict: Dictionary of configuration settings

        Returns:
            New DeploymentConfig with merged settings
        """
        # Create a copy of current config
        new_config = DeploymentConfig(
            excluded_agents=self.excluded_agents.copy(),
            case_sensitive_exclusion=self.case_sensitive_exclusion,
            user_excluded_agents=self.user_excluded_agents.copy(),
            force_rebuild=self.force_rebuild,
            deployment_mode=self.deployment_mode,
            use_async=self.use_async,
            target_dir=self.target_dir,
            templates_dir=self.templates_dir,
            base_agent_path=self.base_agent_path,
            working_directory=self.working_directory,
            deploy_system_instructions=self.deploy_system_instructions,
            deploy_user_instructions=self.deploy_user_instructions,
            repair_existing_agents=self.repair_existing_agents,
            validate_agents=self.validate_agents,
            collect_metrics=self.collect_metrics,
            log_level=self.log_level,
            max_concurrent_operations=self.max_concurrent_operations,
            timeout_seconds=self.timeout_seconds,
            environment=self.environment,
            extra_settings=self.extra_settings.copy(),
        )

        # Update with values from dictionary
        for key, value in config_dict.items():
            if hasattr(new_config, key):
                setattr(new_config, key, value)
            else:
                new_config.extra_settings[key] = value

        return new_config

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation of the configuration
        """
        result = {
            "excluded_agents": self.excluded_agents,
            "case_sensitive_exclusion": self.case_sensitive_exclusion,
            "user_excluded_agents": self.user_excluded_agents,
            "force_rebuild": self.force_rebuild,
            "deployment_mode": self.deployment_mode,
            "use_async": self.use_async,
            "target_dir": str(self.target_dir) if self.target_dir else None,
            "templates_dir": str(self.templates_dir) if self.templates_dir else None,
            "base_agent_path": (
                str(self.base_agent_path) if self.base_agent_path else None
            ),
            "working_directory": (
                str(self.working_directory) if self.working_directory else None
            ),
            "deploy_system_instructions": self.deploy_system_instructions,
            "deploy_user_instructions": self.deploy_user_instructions,
            "repair_existing_agents": self.repair_existing_agents,
            "validate_agents": self.validate_agents,
            "collect_metrics": self.collect_metrics,
            "log_level": self.log_level,
            "max_concurrent_operations": self.max_concurrent_operations,
            "timeout_seconds": self.timeout_seconds,
            "environment": self.environment,
        }

        # Add extra settings
        result.update(self.extra_settings)

        return result
