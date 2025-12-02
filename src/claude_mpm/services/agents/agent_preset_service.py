"""Service for managing agent preset configurations.

This service resolves preset names to concrete agent lists, validates preset
availability against configured sources, and provides metadata for CLI display.

Design Decision: Separate service layer for presets
Rationale: Keeps CLI commands thin, enables easy testing, allows preset logic
to be reused across multiple command interfaces.

Trade-offs:
- Abstraction: Added layer vs. direct preset access in CLI
- Testability: Easy to mock service in CLI tests
- Reusability: Preset logic available to web UI, API, etc.
"""

from typing import Any, Dict, List

from ...config.agent_presets import (
    PRESETS,
    get_preset_agents,
    get_preset_info,
    get_preset_names,
)
from ...core.logging_config import get_logger
from .git_source_manager import GitSourceManager

logger = get_logger(__name__)


class AgentPresetService:
    """Service for resolving and validating agent presets.

    This service bridges preset definitions and git source management,
    providing a unified interface for preset-based agent deployment.

    Attributes:
        source_manager: GitSourceManager for agent resolution
    """

    def __init__(self, source_manager: GitSourceManager):
        """Initialize with GitSourceManager for agent resolution.

        Args:
            source_manager: GitSourceManager instance for accessing agent sources
        """
        self.source_manager = source_manager

    def list_presets(self) -> List[Dict[str, Any]]:
        """List all available presets with metadata.

        Returns:
            List of preset info dicts with keys:
            - name: Preset name (str)
            - description: Human-readable description (str)
            - agent_count: Number of agents in preset (int)
            - use_cases: List of use case strings (List[str])

        Example:
            >>> service = AgentPresetService(source_manager)
            >>> presets = service.list_presets()
            >>> len(presets) >= 10
            True
            >>> all('name' in p for p in presets)
            True
        """
        return [get_preset_info(name) for name in get_preset_names()]

    def validate_preset(self, preset_name: str) -> bool:
        """Check if preset name is valid.

        Args:
            preset_name: Name of preset to validate

        Returns:
            True if preset exists, False otherwise

        Example:
            >>> service.validate_preset('minimal')
            True
            >>> service.validate_preset('invalid-preset')
            False
        """
        return preset_name in PRESETS

    def get_preset_agents(self, preset_name: str) -> List[str]:
        """Get agent list for preset.

        Args:
            preset_name: Name of preset

        Returns:
            List of agent IDs (e.g., ["universal/memory-manager", ...])

        Raises:
            ValueError: If preset name invalid

        Example:
            >>> agents = service.get_preset_agents('minimal')
            >>> len(agents)
            6
        """
        return get_preset_agents(preset_name)

    def resolve_agents(
        self, preset_name: str, validate_availability: bool = True
    ) -> Dict[str, Any]:
        """Resolve preset to actual agent definitions from configured sources.

        This method cross-references preset agent IDs with available agents
        from configured git sources, detecting missing agents and conflicts.

        Args:
            preset_name: Name of preset
            validate_availability: Check if agents exist in sources

        Returns:
            Dict with keys:
            - preset_info: Preset metadata (dict)
            - agents: List of agent dicts with source attribution (List[dict])
            - missing_agents: List of agent IDs not found (List[str])
            - conflicts: List of agents found in multiple sources (List[dict])

        Raises:
            ValueError: If preset name invalid

        Example:
            >>> result = service.resolve_agents('minimal', validate_availability=True)
            >>> 'preset_info' in result
            True
            >>> 'agents' in result
            True
            >>> 'missing_agents' in result
            True

        Design Decision: Graceful degradation for missing agents
        Rationale: Allow deployment to proceed with warnings rather than
        failing completely. Users may have subset of sources configured.
        """
        logger.debug(f"[DEBUG] resolve_agents START: preset_name={preset_name}")

        if not self.validate_preset(preset_name):
            raise ValueError(f"Unknown preset: {preset_name}")

        logger.debug("[DEBUG] Validation passed")
        preset_info = get_preset_info(preset_name)
        logger.debug(f"[DEBUG] Got preset info: {preset_info.get('name')}")

        agent_ids = self.get_preset_agents(preset_name)
        logger.debug(f"[DEBUG] Got agent IDs: {len(agent_ids)} agents")

        result = {
            "preset_info": preset_info,
            "agents": [],
            "missing_agents": [],
            "conflicts": [],
        }

        if not validate_availability:
            # Return agent IDs without validation
            logger.debug("[DEBUG] Skipping validation, returning agent IDs only")
            result["agents"] = [{"agent_id": aid} for aid in agent_ids]
            return result

        # Get all cached agents from sources
        logger.debug("[DEBUG] Calling source_manager.list_cached_agents()")
        all_agents = self.source_manager.list_cached_agents()
        logger.debug(f"[DEBUG] Got {len(all_agents)} agents from source manager")

        # Build lookup: agent_id -> list of sources
        # Each entry is (source_identifier, agent_data)
        logger.debug("[DEBUG] Building agent_sources lookup table")
        agent_sources: Dict[str, List[tuple]] = {}
        for idx, agent in enumerate(all_agents):
            if idx % 10 == 0:
                logger.debug(f"[DEBUG] Processing agent {idx}/{len(all_agents)}")
            # Handle both 'agent_id' and 'id' keys for compatibility
            agent_id = agent.get("agent_id") or agent.get("id")
            if not agent_id:
                logger.warning(f"Agent missing agent_id field: {agent.keys()}")
                continue

            # Bug #5 fix: Handle both string and dict formats for 'source' field
            # GitSourceManager sets source as string (repo_identifier)
            # Some agents may have source as dict with 'identifier' key
            source_value = agent.get("source", "unknown")
            if isinstance(source_value, dict):
                source = source_value.get("identifier", "unknown")
            else:
                source = source_value  # Already a string

            if agent_id not in agent_sources:
                agent_sources[agent_id] = []
            agent_sources[agent_id].append((source, agent))

        logger.debug(
            f"[DEBUG] Built lookup table with {len(agent_sources)} unique agents"
        )

        # Resolve each agent in preset
        logger.debug(f"[DEBUG] Resolving {len(agent_ids)} preset agents")
        for idx, agent_id in enumerate(agent_ids):
            logger.debug(
                f"[DEBUG] Resolving agent {idx + 1}/{len(agent_ids)}: {agent_id}"
            )
            if agent_id not in agent_sources:
                logger.debug(f"[DEBUG] Agent {agent_id} not found in sources (missing)")
                result["missing_agents"].append(agent_id)
                continue

            sources = agent_sources[agent_id]
            logger.debug(f"[DEBUG] Agent {agent_id} found in {len(sources)} source(s)")

            # Conflict if agent found in multiple sources
            if len(sources) > 1:
                logger.debug(
                    f"[DEBUG] Agent {agent_id} has conflict (multiple sources)"
                )
                result["conflicts"].append(
                    {
                        "agent_id": agent_id,
                        "sources": [s[0] for s in sources],
                    }
                )

            # Use first source (highest priority)
            source_name, agent_data = sources[0]
            result["agents"].append(
                {
                    "agent_id": agent_id,
                    "source": source_name,
                    "metadata": agent_data,
                }
            )

        logger.debug(
            f"[DEBUG] resolve_agents COMPLETE: {len(result['agents'])} resolved"
        )
        return result
