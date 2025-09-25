"""
Agent Listing Service for CLI commands
=======================================

WHY: The agent listing logic was previously embedded in the agents CLI command,
making it difficult to test and reuse. This service extracts that functionality
into a reusable, testable component that can be used by multiple CLI commands.

DESIGN DECISIONS:
- Interface-based design for dependency injection and testing
- Caching for performance optimization
- Integration with AgentRegistryAdapter for unified agent discovery
- Support for multiple listing modes (system, deployed, by-tier)
- Comprehensive error handling and logging
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ...core.agent_registry import AgentRegistryAdapter
from ...core.logger import get_logger
from ...services.agents.deployment import AgentDeploymentService
from ...services.agents.deployment.deployment_wrapper import DeploymentServiceWrapper


@dataclass
class AgentInfo:
    """Information about an agent."""

    name: str
    type: str
    tier: str
    path: str
    description: Optional[str] = None
    specializations: Optional[List[str]] = None
    version: Optional[str] = None
    deployed: bool = False
    active: bool = True
    overridden_by: Optional[List[str]] = None


@dataclass
class AgentTierInfo:
    """Information about agents grouped by tier."""

    project: List[AgentInfo]
    user: List[AgentInfo]
    system: List[AgentInfo]

    @property
    def total_count(self) -> int:
        """Get total number of agents across all tiers."""
        return len(self.project) + len(self.user) + len(self.system)

    @property
    def active_count(self) -> int:
        """Get count of active agents (not overridden)."""
        count = 0
        for agents in [self.project, self.user, self.system]:
            count += sum(1 for a in agents if a.active)
        return count


class IAgentListingService(ABC):
    """Interface for agent listing service."""

    @abstractmethod
    def list_system_agents(self, verbose: bool = False) -> List[AgentInfo]:
        """
        List available system agent templates.

        Args:
            verbose: Include detailed metadata

        Returns:
            List of system agent information
        """

    @abstractmethod
    def list_deployed_agents(
        self, verbose: bool = False
    ) -> Tuple[List[AgentInfo], List[str]]:
        """
        List currently deployed agents.

        Args:
            verbose: Include detailed metadata

        Returns:
            Tuple of (agent list, warnings)
        """

    @abstractmethod
    def list_agents_by_tier(self) -> AgentTierInfo:
        """
        List agents grouped by tier/precedence.

        Returns:
            Agent information grouped by tier
        """

    @abstractmethod
    def get_agent_details(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent details or None if not found
        """

    @abstractmethod
    def compare_versions(self, agent_name: str) -> Dict[str, Any]:
        """
        Compare versions of an agent across tiers.

        Args:
            agent_name: Name of the agent

        Returns:
            Version comparison data
        """

    @abstractmethod
    def find_agent(self, agent_name: str) -> Optional[AgentInfo]:
        """
        Find an agent by name across all sources.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent info or None if not found
        """

    @abstractmethod
    def clear_cache(self) -> None:
        """Clear the service cache."""


class AgentListingService(IAgentListingService):
    """Implementation of agent listing service."""

    def __init__(self, deployment_service: Optional[AgentDeploymentService] = None):
        """
        Initialize agent listing service.

        Args:
            deployment_service: Optional deployment service instance
        """
        self.logger = get_logger(self.__class__.__name__)
        self._deployment_service = deployment_service
        self._registry_adapter = None
        self._cache = {}
        self._cache_ttl = 60  # Cache for 60 seconds
        self._cache_times = {}

    @property
    def deployment_service(self) -> AgentDeploymentService:
        """Get deployment service instance (lazy loaded)."""
        if self._deployment_service is None:
            try:
                from ...services import AgentDeploymentService

                base_service = AgentDeploymentService()
                self._deployment_service = DeploymentServiceWrapper(base_service)
            except ImportError:
                raise ImportError("Agent deployment service not available")
        return self._deployment_service

    @property
    def registry_adapter(self) -> AgentRegistryAdapter:
        """Get registry adapter instance (lazy loaded)."""
        if self._registry_adapter is None:
            self._registry_adapter = AgentRegistryAdapter()
        return self._registry_adapter

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid."""
        if key not in self._cache_times:
            return False
        return (time.time() - self._cache_times[key]) < self._cache_ttl

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache if valid."""
        if self._is_cache_valid(key):
            return self._cache.get(key)
        return None

    def _set_cache(self, key: str, value: Any) -> None:
        """Set cache value."""
        self._cache[key] = value
        self._cache_times[key] = time.time()

    def list_system_agents(self, verbose: bool = False) -> List[AgentInfo]:
        """List available system agent templates."""
        cache_key = f"system_agents_{verbose}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        try:
            agents_data = self.deployment_service.list_available_agents()
            agents = []

            for agent_data in agents_data:
                agent = AgentInfo(
                    name=agent_data.get("name", ""),
                    type=agent_data.get("type", "agent"),
                    tier="system",
                    path=agent_data.get("path", ""),
                    description=agent_data.get("description") if verbose else None,
                    specializations=(
                        agent_data.get("specializations") if verbose else None
                    ),
                    version=agent_data.get("version") if verbose else None,
                )
                agents.append(agent)

            self._set_cache(cache_key, agents)
            return agents

        except Exception as e:
            self.logger.error(f"Error listing system agents: {e}", exc_info=True)
            return []

    def list_deployed_agents(
        self, verbose: bool = False
    ) -> Tuple[List[AgentInfo], List[str]]:
        """List currently deployed agents."""
        cache_key = f"deployed_agents_{verbose}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        try:
            verification = self.deployment_service.verify_deployment()
            agents_data = verification.get("agents_found", [])
            warnings = verification.get("warnings", [])

            agents = []
            for agent_data in agents_data:
                agent = AgentInfo(
                    name=agent_data.get("name", ""),
                    type=agent_data.get("type", "agent"),
                    tier=agent_data.get("tier", "system"),
                    path=agent_data.get("path", ""),
                    description=agent_data.get("description"),
                    specializations=(
                        agent_data.get("specializations") if verbose else None
                    ),
                    version=agent_data.get("version"),
                    deployed=True,
                )
                agents.append(agent)

            result = (agents, warnings)
            self._set_cache(cache_key, result)
            return result

        except Exception as e:
            self.logger.error(f"Error listing deployed agents: {e}", exc_info=True)
            return ([], [f"Error listing deployed agents: {e}"])

    def list_agents_by_tier(self) -> AgentTierInfo:
        """List agents grouped by tier/precedence."""
        cache_key = "agents_by_tier"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        try:
            if not self.registry_adapter.registry:
                self.logger.error("Could not initialize agent registry")
                return AgentTierInfo(project=[], user=[], system=[])

            # Get all agents and group by tier
            all_agents = self.registry_adapter.registry.list_agents()

            # Group agents by tier
            tiers = {"project": [], "user": [], "system": []}
            agent_names = set()

            for agent_id, metadata in all_agents.items():
                tier = metadata.get("tier", "system")
                if tier not in tiers:
                    continue

                agent_info = AgentInfo(
                    name=agent_id,
                    type=metadata.get("type", "agent"),
                    tier=tier,
                    path=metadata.get("path", ""),
                    description=metadata.get("description"),
                    specializations=metadata.get("specializations", []),
                    deployed=metadata.get("deployed", False),
                )

                tiers[tier].append(agent_info)
                agent_names.add(agent_id)

            # Check for overrides
            for tier_name in ["project", "user", "system"]:
                for agent in tiers[tier_name]:
                    overridden_by = []

                    # Check if overridden by higher tiers
                    if tier_name == "system":
                        # Check if overridden by user or project
                        if any(a.name == agent.name for a in tiers["user"]):
                            overridden_by.append("USER")
                        if any(a.name == agent.name for a in tiers["project"]):
                            overridden_by.append("PROJECT")
                    elif tier_name == "user":
                        # Check if overridden by project
                        if any(a.name == agent.name for a in tiers["project"]):
                            overridden_by.append("PROJECT")

                    if overridden_by:
                        agent.active = False
                        agent.overridden_by = overridden_by

            result = AgentTierInfo(
                project=tiers["project"], user=tiers["user"], system=tiers["system"]
            )

            self._set_cache(cache_key, result)
            return result

        except Exception as e:
            self.logger.error(f"Error listing agents by tier: {e}", exc_info=True)
            return AgentTierInfo(project=[], user=[], system=[])

    def get_agent_details(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific agent."""
        cache_key = f"agent_details_{agent_name}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        try:
            # Try to get from deployment service first
            details = self.deployment_service.get_agent_details(agent_name)

            if details:
                self._set_cache(cache_key, details)
                return details

            # Fall back to registry
            if not self.registry_adapter.registry:
                return None

            agent = self.registry_adapter.registry.get_agent(agent_name)
            if not agent:
                return None

            # Read agent file for full content
            agent_path = Path(agent.path)
            if not agent_path.exists():
                return None

            with open(agent_path) as f:
                content = f.read()

            details = {
                "name": getattr(agent, "name", agent_name),
                "type": getattr(agent, "type", "agent"),
                "tier": getattr(agent, "tier", "system"),
                "path": str(getattr(agent, "path", agent_path)),
                "description": getattr(agent, "description", None),
                "specializations": getattr(agent, "specializations", []),
                "content": content,
                "size": agent_path.stat().st_size,
                "modified": agent_path.stat().st_mtime,
            }

            self._set_cache(cache_key, details)
            return details

        except Exception as e:
            self.logger.error(f"Error getting agent details: {e}", exc_info=True)
            return None

    def compare_versions(self, agent_name: str) -> Dict[str, Any]:
        """Compare versions of an agent across tiers."""
        cache_key = f"version_compare_{agent_name}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        try:
            tier_info = self.list_agents_by_tier()
            versions = {}

            # Check each tier for the agent
            for tier_name, agents in [
                ("project", tier_info.project),
                ("user", tier_info.user),
                ("system", tier_info.system),
            ]:
                for agent in agents:
                    if agent.name == agent_name:
                        versions[tier_name] = {
                            "path": agent.path,
                            "version": agent.version,
                            "active": agent.active,
                            "overridden_by": agent.overridden_by,
                        }

            result = {
                "agent_name": agent_name,
                "versions": versions,
                "active_tier": next(
                    (tier for tier, v in versions.items() if v.get("active")), None
                ),
            }

            self._set_cache(cache_key, result)
            return result

        except Exception as e:
            self.logger.error(f"Error comparing versions: {e}", exc_info=True)
            return {"agent_name": agent_name, "versions": {}, "error": str(e)}

    def find_agent(self, agent_name: str) -> Optional[AgentInfo]:
        """Find an agent by name across all sources."""
        cache_key = f"find_agent_{agent_name}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        try:
            # First check deployed agents
            deployed, _ = self.list_deployed_agents()
            for agent in deployed:
                if agent.name == agent_name:
                    self._set_cache(cache_key, agent)
                    return agent

            # Check all tiers
            tier_info = self.list_agents_by_tier()
            for agents in [tier_info.project, tier_info.user, tier_info.system]:
                for agent in agents:
                    if agent.name == agent_name:
                        self._set_cache(cache_key, agent)
                        return agent

            return None

        except Exception as e:
            self.logger.error(f"Error finding agent: {e}", exc_info=True)
            return None

    def clear_cache(self) -> None:
        """Clear the service cache."""
        self._cache.clear()
        self._cache_times.clear()
        self.logger.debug("Agent listing service cache cleared")
