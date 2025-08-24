"""Deployed Agent Discovery Service.

This service discovers and analyzes deployed agents in the project,
handling both new standardized schema and legacy agent formats.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.agent_registry import AgentRegistryAdapter
from claude_mpm.core.unified_paths import get_path_manager
from claude_mpm.services.shared import ConfigServiceBase

logger = logging.getLogger(__name__)


class DeployedAgentDiscovery(ConfigServiceBase):
    """Discovers and analyzes deployed agents in the project."""

    def __init__(
        self,
        project_root: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the discovery service.

        Args:
            project_root: Project root path. Defaults to auto-detected root.
            config: Configuration dictionary
        """
        super().__init__("deployed_agent_discovery", config=config)

        # Initialize project root using configuration
        self.project_root = self.get_config_value(
            "project_root",
            default=project_root or get_path_manager().project_root,
            config_type=Path,
        )
        self.agent_registry = AgentRegistryAdapter()
        self.logger.debug(
            f"Initialized DeployedAgentDiscovery with root: {self.project_root}"
        )

    def discover_deployed_agents(self) -> List[Dict[str, Any]]:
        """Discover all deployed agents following hierarchy precedence.

        Returns:
            List of agent information dictionaries with standardized fields.
        """
        try:
            # Get effective agents (respects project > user > system precedence)
            agents = self.agent_registry.list_agents()

            # Handle both dict and list formats
            if isinstance(agents, dict):
                agent_list = list(agents.values())
            else:
                agent_list = list(agents)

            logger.debug(f"Found {len(agent_list)} entries in registry")

            deployed_agents = []
            filtered_count = 0
            for agent in agent_list:
                try:
                    agent_info = self._extract_agent_info(agent)
                    if agent_info and self._is_valid_agent(agent_info):
                        deployed_agents.append(agent_info)
                        logger.debug(f"Extracted info for agent: {agent_info['id']}")
                    elif agent_info:
                        filtered_count += 1
                        logger.debug(
                            f"Filtered out non-deployable agent: {agent_info.get('id', 'unknown')}"
                        )
                except Exception as e:
                    logger.error(f"Failed to extract info from agent {agent}: {e}")
                    continue

            return deployed_agents

        except Exception as e:
            logger.error(f"Failed to discover deployed agents: {e}")
            # Return empty list on failure to allow graceful degradation
            return []

    def _extract_agent_info(self, agent) -> Dict[str, Any]:
        """Extract relevant information from agent definition.

        Args:
            agent: Agent object from registry (can be dict or object)

        Returns:
            Dictionary with standardized agent information
        """
        try:
            # Handle dictionary format (current format from registry)
            if isinstance(agent, dict):
                # If we have a path, try to load full agent data from JSON
                agent_path = agent.get("path")
                if agent_path and agent_path.endswith(".json"):
                    full_data = self._load_full_agent_data(agent_path)
                    if full_data:
                        return self._extract_from_json_data(full_data, agent)

                # Otherwise use basic info from registry
                return {
                    "id": agent.get("type", agent.get("name", "unknown")),
                    "name": agent.get("name", "Unknown"),
                    "description": agent.get("description", "No description available"),
                    "specializations": agent.get("specializations", []),
                    "capabilities": agent.get("capabilities", {}),
                    "source_tier": agent.get("tier", "system"),
                    "tools": agent.get("tools", []),
                }
            # Handle object format with metadata (new standardized schema)
            if hasattr(agent, "metadata"):
                return {
                    "id": agent.agent_id,
                    "name": agent.metadata.name,
                    "description": agent.metadata.description,
                    "specializations": agent.metadata.specializations,
                    "capabilities": getattr(agent, "capabilities", {}),
                    "source_tier": self._determine_source_tier(agent),
                    "tools": (
                        getattr(agent.configuration, "tools", [])
                        if hasattr(agent, "configuration")
                        else []
                    ),
                }
            # Legacy object format fallback
            agent_type = getattr(agent, "type", None)
            agent_name = getattr(agent, "name", None)

            # Generate name from type if name not present
            if not agent_name and agent_type:
                agent_name = agent_type.replace("_", " ").title()
            elif not agent_name:
                agent_name = "Unknown Agent"

            return {
                "id": getattr(agent, "agent_id", agent_type or "unknown"),
                "name": agent_name,
                "description": getattr(
                    agent, "description", "No description available"
                ),
                "specializations": getattr(agent, "specializations", []),
                "capabilities": {},
                "source_tier": self._determine_source_tier(agent),
                "tools": getattr(agent, "tools", []),
            }
        except Exception as e:
            logger.error(f"Error extracting agent info: {e}")
            return None

    def _load_full_agent_data(self, agent_path: str) -> Dict[str, Any]:
        """Load full agent data from JSON file.

        Args:
            agent_path: Path to agent JSON file

        Returns:
            Full agent data dictionary or None if loading fails
        """
        try:
            path = Path(agent_path)
            if path.exists() and path.suffix == ".json":
                with open(path) as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load full agent data from {agent_path}: {e}")
        return None

    def _extract_from_json_data(
        self, json_data: Dict[str, Any], registry_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract agent info from full JSON data.

        Args:
            json_data: Full agent JSON data
            registry_info: Basic info from registry

        Returns:
            Extracted agent information
        """
        # Extract metadata
        metadata = json_data.get("metadata", {})
        capabilities = json_data.get("capabilities", {})
        configuration = json_data.get("configuration", {})

        return {
            "id": json_data.get("agent_type", registry_info.get("type", "unknown")),
            "name": metadata.get("name", registry_info.get("name", "Unknown")),
            "description": metadata.get(
                "description",
                registry_info.get("description", "No description available"),
            ),
            "specializations": metadata.get(
                "specializations", registry_info.get("specializations", [])
            ),
            "capabilities": capabilities,
            "source_tier": registry_info.get("tier", "system"),
            "tools": configuration.get("tools", []),
        }

    def _determine_source_tier(self, agent) -> str:
        """Determine if agent comes from project, user, or system tier.

        Args:
            agent: Agent object from registry (can be dict or object)

        Returns:
            Source tier string: 'project', 'user', or 'system'
        """
        # Handle dictionary format
        if isinstance(agent, dict):
            return agent.get("tier", "system")

        # First check if agent has explicit source_tier attribute
        if hasattr(agent, "source_tier"):
            return agent.source_tier

        # Try to determine from file path if available
        if hasattr(agent, "source_path"):
            source_path = str(agent.source_path)
            if ".claude/agents" in source_path:
                return "project"
            if str(Path.home()) in source_path:
                return "user"

        # Default to system tier
        return "system"

    def _is_valid_agent(self, agent_info: Dict[str, Any]) -> bool:
        """Check if agent is a valid deployable agent (not a template).

        Args:
            agent_info: Extracted agent information

        Returns:
            True if agent is valid, False if it's a template or invalid
        """
        # Filter out known templates and non-agent files
        invalid_names = [
            "BASE_AGENT_TEMPLATE",
            "INSTRUCTIONS",
            "base_agent",
            "template",
            "MEMORIES",
            "TODOWRITE",
        ]

        agent_id = agent_info.get("id", "").upper()
        agent_name = agent_info.get("name", "").upper()

        for invalid in invalid_names:
            if invalid.upper() in agent_id or invalid.upper() in agent_name:
                logger.debug(
                    f"Filtering out template/invalid agent: {agent_info['id']}"
                )
                return False

        return True

    def get_precedence_order(self) -> List[str]:
        """
        Get the precedence order for agent discovery.

        Returns:
            List of tiers in precedence order (highest to lowest)
        """
        return ["project", "user", "system"]
