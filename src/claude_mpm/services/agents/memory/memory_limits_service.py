#!/usr/bin/env python3
"""Memory Limits Service - Manages memory size limits and configuration."""

import logging
from typing import Any, Dict, Optional

from claude_mpm.core.config import Config


class MemoryLimitsService:
    """Service for managing memory limits and configuration."""

    # Default limits
    DEFAULT_MEMORY_LIMITS = {
        "max_file_size_kb": 80,  # 80KB (20k tokens)
        "max_items": 100,  # Maximum total memory items
        "max_line_length": 120,
    }

    def __init__(self, config: Optional[Config] = None):
        """Initialize the memory limits service.

        Args:
            config: Optional Config object for reading configuration
        """
        self.config = config or Config()
        self.logger = logging.getLogger(__name__)
        self.memory_limits = self._init_memory_limits()

    def _init_memory_limits(self) -> Dict[str, Any]:
        """Initialize memory limits from configuration.

        Returns:
            Dictionary of memory limits
        """
        try:
            limits = self.DEFAULT_MEMORY_LIMITS.copy()

            # Try to load from config
            if hasattr(self.config, "agent_memory_limits"):
                config_limits = self.config.agent_memory_limits
                if isinstance(config_limits, dict):
                    limits.update(config_limits)

            self.logger.debug(f"Initialized memory limits: {limits}")
            return limits

        except Exception as e:
            self.logger.warning(f"Failed to load memory limits from config: {e}")
            return self.DEFAULT_MEMORY_LIMITS.copy()

    def get_agent_limits(self, agent_id: str) -> Dict[str, Any]:
        """Get memory limits for a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Dictionary of memory limits for the agent
        """
        # Start with default limits
        limits = self.memory_limits.copy()

        # Check for agent-specific overrides
        try:
            if hasattr(self.config, "agents") and agent_id in self.config.agents:
                agent_config = self.config.agents[agent_id]
                if "memory_limits" in agent_config:
                    limits.update(agent_config["memory_limits"])
        except Exception as e:
            self.logger.debug(f"No agent-specific limits for {agent_id}: {e}")

        return limits

    def get_agent_auto_learning(self, agent_id: str) -> bool:
        """Get auto-learning setting for a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            True if auto-learning is enabled, False otherwise
        """
        try:
            # Check agent-specific config
            if hasattr(self.config, "agents") and agent_id in self.config.agents:
                agent_config = self.config.agents[agent_id]
                if "auto_learning" in agent_config:
                    return agent_config["auto_learning"]

            # Check global config
            if hasattr(self.config, "agent_auto_learning"):
                return self.config.agent_auto_learning

        except Exception as e:
            self.logger.debug(f"Error checking auto-learning for {agent_id}: {e}")

        # Default to True (auto-learning enabled)
        return True
