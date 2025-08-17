"""Deployment configuration loading for agent deployment service.

This module handles loading and processing of deployment configuration.
Extracted from AgentDeploymentService to reduce complexity and improve maintainability.
"""

import logging
from typing import Optional, Tuple

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

        # Get agent exclusion configuration
        excluded_agents = config.get("agent_deployment.excluded_agents", [])
        case_sensitive = config.get("agent_deployment.case_sensitive", False)
        exclude_dependencies = config.get(
            "agent_deployment.exclude_dependencies", False
        )

        # Normalize excluded agents list for comparison
        if not case_sensitive:
            excluded_agents = [agent.lower() for agent in excluded_agents]

        # Log exclusion configuration if agents are being excluded
        if excluded_agents:
            self.logger.info(f"Excluding agents from deployment: {excluded_agents}")
            self.logger.debug(f"Case sensitive matching: {case_sensitive}")
            self.logger.debug(f"Exclude dependencies: {exclude_dependencies}")

        return config, excluded_agents
