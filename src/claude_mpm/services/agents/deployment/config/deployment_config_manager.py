"""Deployment configuration manager."""

from pathlib import Path
from typing import Any, Dict, Optional

from claude_mpm.core.config import Config
from claude_mpm.core.logger import get_logger

from .deployment_config import DeploymentConfig


class DeploymentConfigManager:
    """Manager for deployment configuration.

    This class handles loading, processing, and validation of
    deployment-specific configuration settings.
    """

    def __init__(self):
        """Initialize the deployment configuration manager."""
        self.logger = get_logger(__name__)

    def load_deployment_config(
        self, config: Optional[Config] = None, **overrides
    ) -> DeploymentConfig:
        """Load deployment configuration from various sources.

        Args:
            config: Optional Config object to load from
            **overrides: Configuration overrides

        Returns:
            DeploymentConfig object with loaded settings
        """
        # Start with default configuration
        deployment_config = DeploymentConfig()

        # Load from Config object if provided
        if config:
            config_dict = self._extract_deployment_config(config)
            deployment_config = deployment_config.merge_with_dict(config_dict)

        # Apply overrides
        if overrides:
            deployment_config = deployment_config.merge_with_dict(overrides)

        # Validate configuration
        self._validate_config(deployment_config)

        self.logger.debug(
            f"Loaded deployment configuration: {deployment_config.environment} mode"
        )
        return deployment_config

    def _extract_deployment_config(self, config: Config) -> Dict[str, Any]:
        """Extract deployment-specific configuration from Config object.

        Args:
            config: Config object to extract from

        Returns:
            Dictionary of deployment configuration settings
        """
        config_dict = {}

        # Extract agent deployment settings
        config_dict["excluded_agents"] = config.get(
            "agent_deployment.excluded_agents", []
        )
        config_dict["case_sensitive_exclusion"] = config.get(
            "agent_deployment.case_sensitive_exclusion", True
        )
        config_dict["user_excluded_agents"] = config.get(
            "agent_deployment.user_excluded_agents", []
        )

        # Extract system instruction settings
        config_dict["deploy_system_instructions"] = config.get(
            "agent_deployment.deploy_system_instructions", True
        )
        config_dict["deploy_user_instructions"] = config.get(
            "agent_deployment.deploy_user_instructions", True
        )

        # Extract validation settings
        config_dict["repair_existing_agents"] = config.get(
            "agent_deployment.repair_existing_agents", True
        )
        config_dict["validate_agents"] = config.get(
            "agent_deployment.validate_agents", True
        )

        # Extract performance settings
        config_dict["use_async"] = config.get("agent_deployment.use_async", False)
        config_dict["max_concurrent_operations"] = config.get(
            "agent_deployment.max_concurrent_operations", 10
        )
        config_dict["timeout_seconds"] = config.get(
            "agent_deployment.timeout_seconds", 300
        )

        # Extract environment settings
        config_dict["environment"] = config.get("environment", "production")
        config_dict["log_level"] = config.get("logging.level", "INFO")

        # Extract metrics settings
        config_dict["collect_metrics"] = config.get(
            "agent_deployment.collect_metrics", True
        )

        return config_dict

    def _validate_config(self, config: DeploymentConfig) -> None:
        """Validate deployment configuration.

        Args:
            config: Configuration to validate

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate deployment mode
        valid_modes = ["update", "project"]
        if config.deployment_mode not in valid_modes:
            raise ValueError(
                f"Invalid deployment mode: {config.deployment_mode}. Must be one of: {valid_modes}"
            )

        # Validate environment
        valid_environments = ["development", "testing", "production"]
        if config.environment not in valid_environments:
            raise ValueError(
                f"Invalid environment: {config.environment}. Must be one of: {valid_environments}"
            )

        # Validate paths if provided
        if config.target_dir and not isinstance(config.target_dir, Path):
            try:
                config.target_dir = Path(config.target_dir)
            except Exception as e:
                raise ValueError(f"Invalid target_dir path: {config.target_dir}") from e

        if config.templates_dir and not isinstance(config.templates_dir, Path):
            try:
                config.templates_dir = Path(config.templates_dir)
            except Exception as e:
                raise ValueError(
                    f"Invalid templates_dir path: {config.templates_dir}"
                ) from e

        if config.base_agent_path and not isinstance(config.base_agent_path, Path):
            try:
                config.base_agent_path = Path(config.base_agent_path)
            except Exception as e:
                raise ValueError(
                    f"Invalid base_agent_path: {config.base_agent_path}"
                ) from e

        if config.working_directory and not isinstance(config.working_directory, Path):
            try:
                config.working_directory = Path(config.working_directory)
            except Exception as e:
                raise ValueError(
                    f"Invalid working_directory path: {config.working_directory}"
                ) from e

        # Validate numeric settings
        if config.max_concurrent_operations <= 0:
            raise ValueError("max_concurrent_operations must be positive")

        if config.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        self.logger.debug("Configuration validation passed")

    def create_config_from_context(self, context) -> DeploymentConfig:
        """Create deployment config from pipeline context.

        Args:
            context: Pipeline context or deployment context

        Returns:
            DeploymentConfig object
        """
        config_dict = {
            "target_dir": getattr(context, "target_dir", None),
            "force_rebuild": getattr(context, "force_rebuild", False),
            "deployment_mode": getattr(context, "deployment_mode", "update"),
            "use_async": getattr(context, "use_async", False),
            "working_directory": getattr(context, "working_directory", None),
            "templates_dir": getattr(context, "templates_dir", None),
            "base_agent_path": getattr(context, "base_agent_path", None),
        }

        # Remove None values
        config_dict = {k: v for k, v in config_dict.items() if v is not None}

        return self.load_deployment_config(
            config=getattr(context, "config", None), **config_dict
        )
