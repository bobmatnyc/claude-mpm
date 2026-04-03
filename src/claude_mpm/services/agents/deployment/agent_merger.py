"""Agent Merger — discovers agents from multiple sources and selects the highest version.

Single responsibility: combine agents from the 4-tier hierarchy (system → user → remote →
project) and surface one winner per agent using semantic version comparison.
"""

from pathlib import Path
from typing import Any

from claude_mpm.core.logging_config import get_logger

from .agent_discovery_service import AgentDiscoveryService
from .agent_version_manager import AgentVersionManager
from .remote_agent_discovery_service import RemoteAgentDiscoveryService


class AgentMerger:
    """Discovers agents from all 4 tiers and selects the highest version per agent.

    4-Tier Agent Discovery (lowest to highest priority):
    1. System templates  — built-in agents shipped with claude-mpm
    2. User agents       — DEPRECATED (~/.claude-mpm/agents/)
    3. Remote agents     — agents cached from GitHub
    4. Project agents    — project-specific customisations (highest priority)

    The priority hierarchy is enforced at *discovery* time via canonical IDs; the
    actual version winner is chosen by ``select_highest_version_agents`` so that a
    higher-versioned system agent can still beat a stale project copy.
    """

    def __init__(self, version_manager: AgentVersionManager | None = None) -> None:
        self.logger = get_logger(__name__)
        self.version_manager = version_manager or AgentVersionManager()

    # ------------------------------------------------------------------
    # Canonical ID helpers
    # ------------------------------------------------------------------

    def _build_canonical_id_for_agent(self, agent_info: dict[str, Any]) -> str:
        """Build or retrieve canonical_id for an agent.

        NEW: Supports enhanced agent matching via canonical_id.

        Priority:
        1. Use existing canonical_id from agent_info if present
        2. Generate from collection_id + agent_id if available
        3. Fallback to legacy:{filename} for backward compatibility

        Args:
            agent_info: Agent dictionary with metadata

        Returns:
            Canonical ID string for matching

        Example:
            Remote agent: "bobmatnyc/claude-mpm-agents:pm"
            Legacy agent: "legacy:custom-agent"
        """
        # Priority 1: Existing canonical_id
        if "canonical_id" in agent_info:
            return agent_info["canonical_id"]

        # Priority 2: Generate from collection_id + agent_id
        collection_id = agent_info.get("collection_id")
        agent_id = agent_info.get("agent_id")

        if collection_id and agent_id:
            canonical_id = f"{collection_id}:{agent_id}"
            # Cache it in agent_info for future use
            agent_info["canonical_id"] = canonical_id
            return canonical_id

        # Priority 3: Fallback to legacy format
        # Use filename or agent name
        agent_name = agent_info.get("name") or agent_info.get("metadata", {}).get(
            "name", "unknown"
        )

        # Extract filename from path
        path_str = (
            agent_info.get("path")
            or agent_info.get("file_path")
            or agent_info.get("source_file")
        )

        if path_str:
            filename = Path(path_str).stem
            canonical_id = f"legacy:{filename}"
        else:
            canonical_id = f"legacy:{agent_name}"

        # Cache it
        agent_info["canonical_id"] = canonical_id
        return canonical_id

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover_agents_from_all_sources(
        self,
        system_templates_dir: Path | None = None,
        project_agents_dir: Path | None = None,
        user_agents_dir: Path | None = None,
        agents_cache_dir: Path | None = None,
        working_directory: Path | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Discover agents from all 4 tiers (system, user, cache, project).

        Priority hierarchy (highest to lowest):
        4. Project agents - Highest priority, project-specific customizations
        3. Cached agents - GitHub-synced agents from cache
        2. User agents - DEPRECATED, user-level customizations
        1. System templates - Lowest priority, built-in agents

        Args:
            system_templates_dir: Directory containing system agent templates
            project_agents_dir: Directory containing project-specific agents
            user_agents_dir: Directory containing user custom agents (DEPRECATED)
            agents_cache_dir: Directory containing cached agents from Git sources
            working_directory: Current working directory for finding project agents

        Returns:
            Dictionary mapping agent names to list of agent info from different sources

        Deprecation Warning:
            User-level agents are deprecated and will show a warning if found.
            Use 'claude-mpm agents migrate-to-project' to migrate them.
        """
        agents_by_name: dict[str, list[dict[str, Any]]] = {}

        # Determine directories if not provided
        if not system_templates_dir:
            # Use default system templates location
            from claude_mpm.config.paths import paths

            system_templates_dir = paths.agents_dir / "templates"

        if not project_agents_dir and working_directory:
            # Check for project agents in working directory
            project_agents_dir = working_directory / ".claude-mpm" / "agents"
            if not project_agents_dir.exists():
                project_agents_dir = None

        if not user_agents_dir:
            # Check for user agents in home directory
            user_agents_dir = Path.home() / ".claude-mpm" / "agents"
            if not user_agents_dir.exists():
                user_agents_dir = None

        if not agents_cache_dir:
            # Check for agents in cache directory
            cache_dir = Path.home() / ".claude-mpm" / "cache"
            agents_cache_dir = cache_dir / "agents"
            if not agents_cache_dir.exists():
                agents_cache_dir = None

        # Discover agents from each source in priority order
        # Note: We process in reverse priority order (system first) and build up the dictionary
        # The select_highest_version_agents() method will handle the actual prioritization
        sources = [
            ("system", system_templates_dir),
            ("user", user_agents_dir),
            ("remote", agents_cache_dir),
            ("project", project_agents_dir),
        ]

        # Track if we found user agents for deprecation warning
        user_agents_found = False

        for source_name, source_dir in sources:
            if source_dir and source_dir.exists():
                self.logger.debug(
                    f"Discovering agents from {source_name} source: {source_dir}"
                )

                # Use AgentDiscoveryService for all sources (unified discovery)
                discovery_service = AgentDiscoveryService(source_dir)

                if source_name == "remote":
                    # For remote (git cache), use shared git discovery method
                    agents = discovery_service.discover_git_cached_agents(
                        cache_dir=source_dir, log_discovery=False
                    )
                else:
                    # For other sources, use standard discovery
                    agents = discovery_service.list_available_agents(
                        log_discovery=False
                    )

                # Track user agents for deprecation warning
                if source_name == "user" and agents:
                    user_agents_found = True

                for agent_info in agents:
                    agent_name = agent_info.get("name") or agent_info.get(
                        "metadata", {}
                    ).get("name")
                    if not agent_name:
                        continue

                    # Add source information
                    agent_info["source"] = source_name
                    agent_info["source_dir"] = str(source_dir)

                    # NEW: Build canonical_id for enhanced matching
                    canonical_id = self._build_canonical_id_for_agent(agent_info)

                    # Group by canonical_id (PRIMARY) for enhanced matching
                    # This allows matching agents from different sources with same canonical_id
                    # while maintaining backward compatibility with name-based matching
                    matching_key = canonical_id

                    # Initialize list if this is the first occurrence of this agent
                    if matching_key not in agents_by_name:
                        agents_by_name[matching_key] = []

                    agents_by_name[matching_key].append(agent_info)

                # Use more specific log message
                self.logger.info(
                    f"Discovered {len(agents)} {source_name} agent templates from {source_dir.name}"
                )

        # Show deprecation warning if user agents found
        if user_agents_found:
            self.logger.warning(
                "\n"
                "⚠️  DEPRECATION WARNING: User-level agents found in ~/.claude-mpm/agents/\n"
                "   User-level agent deployment is deprecated and will be removed in v5.0.0\n"
                "\n"
                "   Why this change?\n"
                "   - Project isolation: Agents should be project-specific\n"
                "   - Version control: Project agents can be versioned with your code\n"
                "   - Team consistency: All team members use the same agents\n"
                "\n"
                "   Migration:\n"
                "   1. Run: claude-mpm agents migrate-to-project\n"
                "   2. Verify agents work in .claude-mpm/agents/\n"
                "   3. Remove: rm -rf ~/.claude-mpm/agents/\n"
                "\n"
                "   Learn more: https://docs.claude-mpm.dev/agents/migration\n"
            )

        return agents_by_name

    def get_agents_by_collection(
        self,
        collection_id: str,
        agents_cache_dir: Path | None = None,
    ) -> list[dict[str, Any]]:
        """Get all agents from a specific collection.

        NEW: Enables collection-based agent selection.

        Args:
            collection_id: Collection identifier (e.g., "bobmatnyc/claude-mpm-agents")
            agents_cache_dir: Directory containing agents cache

        Returns:
            List of agent dictionaries from the specified collection

        Example:
            >>> merger = AgentMerger()
            >>> agents = merger.get_agents_by_collection("bobmatnyc/claude-mpm-agents")
            >>> len(agents)
            45
        """
        if not agents_cache_dir:
            cache_dir = Path.home() / ".claude-mpm" / "cache"
            agents_cache_dir = cache_dir / "agents"

        if not agents_cache_dir.exists():
            self.logger.warning(f"Agents cache directory not found: {agents_cache_dir}")
            return []

        # Use RemoteAgentDiscoveryService to get collection agents
        remote_service = RemoteAgentDiscoveryService(agents_cache_dir)
        collection_agents = remote_service.get_agents_by_collection(collection_id)

        self.logger.info(
            f"Retrieved {len(collection_agents)} agents from collection '{collection_id}'"
        )

        return collection_agents

    # ------------------------------------------------------------------
    # Version selection
    # ------------------------------------------------------------------

    def select_highest_version_agents(
        self, agents_by_name: dict[str, list[dict[str, Any]]]
    ) -> dict[str, dict[str, Any]]:
        """Select the highest version agent from multiple sources.

        Args:
            agents_by_name: Dictionary mapping agent names to list of agent info

        Returns:
            Dictionary mapping agent names to the highest version agent info
        """
        selected_agents: dict[str, dict[str, Any]] = {}

        for agent_name, agent_versions in agents_by_name.items():
            if not agent_versions:
                continue

            # If only one version exists, use it
            if len(agent_versions) == 1:
                selected_agents[agent_name] = agent_versions[0]
                self.logger.debug(
                    f"Agent '{agent_name}' has single source: {agent_versions[0]['source']}"
                )
                continue

            # Compare versions to find the highest
            highest_version_agent = None
            highest_version_tuple = (0, 0, 0)

            for agent_info in agent_versions:
                version_str = agent_info.get("version", "0.0.0")
                version_tuple = self.version_manager.parse_version(version_str)

                self.logger.debug(
                    f"Agent '{agent_name}' from {agent_info['source']}: "
                    f"version {version_str} -> {version_tuple}"
                )

                # Compare with current highest
                if (
                    self.version_manager.compare_versions(
                        version_tuple, highest_version_tuple
                    )
                    > 0
                ):
                    highest_version_agent = agent_info
                    highest_version_tuple = version_tuple

            if highest_version_agent:
                selected_agents[agent_name] = highest_version_agent
                self.logger.info(
                    f"Selected agent '{agent_name}' version {highest_version_agent['version']} "
                    f"from {highest_version_agent['source']} source"
                )

                # Log if a higher priority source was overridden by version
                for other_agent in agent_versions:
                    if other_agent != highest_version_agent:
                        # Parse both versions for comparison
                        other_version = self.version_manager.parse_version(
                            other_agent.get("version", "0.0.0")
                        )
                        highest_version = self.version_manager.parse_version(
                            highest_version_agent.get("version", "0.0.0")
                        )

                        # Compare the versions
                        version_comparison = self.version_manager.compare_versions(
                            other_version, highest_version
                        )

                        # Only warn if the other version is actually lower
                        if version_comparison < 0:
                            if (
                                other_agent["source"] == "project"
                                and highest_version_agent["source"] == "system"
                            ):
                                self.logger.warning(
                                    f"Project agent '{agent_name}' v{other_agent['version']} "
                                    f"overridden by higher system version v{highest_version_agent['version']}"
                                )
                            elif other_agent[
                                "source"
                            ] == "user" and highest_version_agent["source"] in [
                                "system",
                                "project",
                            ]:
                                self.logger.warning(
                                    f"User agent '{agent_name}' v{other_agent['version']} "
                                    f"overridden by higher {highest_version_agent['source']} version v{highest_version_agent['version']}"
                                )
                        elif (
                            version_comparison == 0
                            and other_agent["source"] != highest_version_agent["source"]
                        ):
                            # Log info when versions are equal but different sources
                            self.logger.info(
                                f"Using {highest_version_agent['source']} source for '{agent_name}' "
                                f"(same version v{highest_version_agent['version']} as {other_agent['source']} source)"
                            )

        return selected_agents
