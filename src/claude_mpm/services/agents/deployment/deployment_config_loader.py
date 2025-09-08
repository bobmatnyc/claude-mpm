"""Deployment configuration loading for agent deployment service.

This module handles loading and processing of deployment configuration.
Extracted from AgentDeploymentService to reduce complexity and improve maintainability.
"""

import logging
from typing import Any, Dict, Optional, Tuple

from claude_mpm.core.config import Config


class DeploymentConfigLoader:
    """Handles loading and processing of deployment configuration."""

    def __init__(self, logger: logging.Logger):
        """Initialize the config loader with a logger."""
        self.logger = logger

    def load_deployment_config(self, config: Optional[Config]) -> Tuple[Config, list]:
        """
        Load and process deployment configuration.

        Centralized configuration loading reduces duplication
        and ensures consistent handling of exclusion settings.

        Args:
            config: Optional configuration object

        Returns:
            Tuple of (config, excluded_agents)
        """
        # Load configuration if not provided
        if config is None:
            config = Config()

        # Get new configuration format first, fall back to legacy
        disabled_agents = config.get("agent_deployment.disabled_agents", [])

        # Fall back to legacy excluded_agents if disabled_agents is empty
        if not disabled_agents:
            disabled_agents = config.get("agent_deployment.excluded_agents", [])

        case_sensitive = config.get("agent_deployment.case_sensitive", False)
        exclude_dependencies = config.get(
            "agent_deployment.exclude_dependencies", False
        )

        # Normalize excluded agents list for comparison
        if not case_sensitive:
            disabled_agents = [agent.lower() for agent in disabled_agents]

        # Log exclusion configuration if agents are being excluded
        if disabled_agents:
            self.logger.info(f"Excluding agents from deployment: {disabled_agents}")
            self.logger.debug(f"Case sensitive matching: {case_sensitive}")
            self.logger.debug(f"Exclude dependencies: {exclude_dependencies}")

        return config, disabled_agents

    def get_deployment_settings(
        self, config: Optional[Config] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive deployment settings from configuration.

        Args:
            config: Optional configuration object

        Returns:
            Dictionary of deployment settings
        """
        if config is None:
            config = Config()

        return {
            "enabled_agents": config.get("agent_deployment.enabled_agents", []),
            "disabled_agents": config.get("agent_deployment.disabled_agents", [])
            or config.get("agent_deployment.excluded_agents", []),
            "deploy_system_agents": config.get(
                "agent_deployment.deploy_system_agents", True
            ),
            "deploy_local_agents": config.get(
                "agent_deployment.deploy_local_agents", True
            ),
            "deploy_user_agents": config.get(
                "agent_deployment.deploy_user_agents", True
            ),
            "prefer_local_over_system": config.get(
                "agent_deployment.prefer_local_over_system", True
            ),
            "version_comparison": config.get(
                "agent_deployment.version_comparison", True
            ),
            "case_sensitive": config.get("agent_deployment.case_sensitive", False),
            "exclude_dependencies": config.get(
                "agent_deployment.exclude_dependencies", False
            ),
        }

    def should_deploy_agent(
        self, agent_id: str, agent_source: str, config: Optional[Config] = None
    ) -> bool:
        """
        Check if an agent should be deployed based on configuration.

        Args:
            agent_id: The agent identifier
            agent_source: The source of the agent ('system', 'local', 'user')
            config: Optional configuration object

        Returns:
            True if the agent should be deployed, False otherwise
        """
        settings = self.get_deployment_settings(config)

        # Check if the source type is enabled
        if agent_source == "system" and not settings["deploy_system_agents"]:
            self.logger.debug(
                f"Skipping system agent {agent_id} - system agents disabled"
            )
            return False
        if agent_source == "local" and not settings["deploy_local_agents"]:
            self.logger.debug(
                f"Skipping local agent {agent_id} - local agents disabled"
            )
            return False
        if agent_source == "user" and not settings["deploy_user_agents"]:
            self.logger.debug(f"Skipping user agent {agent_id} - user agents disabled")
            return False

        # Normalize agent_id for comparison if not case sensitive
        check_id = agent_id if settings["case_sensitive"] else agent_id.lower()

        # Check enabled list (if specified, only these agents are deployed)
        enabled = settings["enabled_agents"]
        if enabled:
            enabled_list = (
                enabled if settings["case_sensitive"] else [a.lower() for a in enabled]
            )
            if check_id not in enabled_list:
                self.logger.debug(f"Skipping agent {agent_id} - not in enabled list")
                return False

        # Check disabled list
        disabled = settings["disabled_agents"]
        if disabled:
            disabled_list = (
                disabled
                if settings["case_sensitive"]
                else [a.lower() for a in disabled]
            )
            if check_id in disabled_list:
                self.logger.debug(f"Skipping agent {agent_id} - in disabled list")
                return False

        return True
