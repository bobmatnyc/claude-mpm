"""Multi-Source Agent Deployment Service

This service implements proper version comparison across multiple agent sources,
ensuring the highest version agent is deployed regardless of source.

Key Features:
- Discovers agents from multiple sources (system templates, project agents, user agents)
- Compares versions across all sources
- Deploys the highest version for each agent
- Tracks which source provided the deployed agent
- Maintains backward compatibility with existing deployment modes
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from claude_mpm.core.config import Config
from claude_mpm.core.logging_config import get_logger

from .agent_discovery_service import AgentDiscoveryService
from .agent_version_manager import AgentVersionManager
from .remote_agent_discovery_service import RemoteAgentDiscoveryService


def _normalize_agent_name(name: str) -> str:
    """Normalize agent name for consistent comparison.

    Converts spaces, underscores to hyphens and lowercases.
    Examples:
        "Dart Engineer" -> "dart-engineer"
        "dart_engineer" -> "dart-engineer"
        "DART-ENGINEER" -> "dart-engineer"
    """
    return name.lower().replace(" ", "-").replace("_", "-")


class MultiSourceAgentDeploymentService:
    """Service for deploying agents from multiple sources with version comparison.

    This service ensures that the highest version of each agent is deployed,
    regardless of whether it comes from system templates, project agents,
    user agents, or remote agents.

    4-Tier Agent Discovery:
    1. System templates (lowest priority) - Built-in agents
    2. User agents (DEPRECATED) - User-level customizations (~/.claude-mpm/agents/)
    3. Remote agents - Agents cached from GitHub
    4. Project agents (highest priority) - Project-specific customizations

    WHY: The current system processes agents from a single source at a time,
    which can result in lower version agents being deployed if they exist in
    a higher priority source. This service fixes that by comparing versions
    across all sources.

    DEPRECATION: User-level agents (~/.claude-mpm/agents/) are deprecated and
    will be removed in v5.0.0. Use project-level agents instead.
    """

    def __init__(self):
        """Initialize the multi-source deployment service."""
        self.logger = get_logger(__name__)
        self.version_manager = AgentVersionManager()

    def _read_template_version(self, template_path: Path) -> Optional[str]:
        """Read version from template file (supports both .md and .json formats).

        For .md files: Extract version from YAML frontmatter
        For .json files: Extract version from JSON structure

        Args:
            template_path: Path to template file

        Returns:
            Version string or None if version cannot be extracted
        """
        try:
            if template_path.suffix == ".md":
                # Parse markdown with YAML frontmatter
                content = template_path.read_text()

                # Extract YAML frontmatter (between --- markers)
                if not content.strip().startswith("---"):
                    return None

                parts = content.split("---", 2)
                if len(parts) < 3:
                    return None

                # Parse YAML frontmatter
                frontmatter = yaml.safe_load(parts[1])
                if not frontmatter:
                    return None

                # Extract version from frontmatter
                version = frontmatter.get("version")
                return version if version else None

            if template_path.suffix == ".json":
                # Parse JSON template
                template_data = json.loads(template_path.read_text())
                metadata = template_data.get("metadata", {})
                version = (
                    template_data.get("agent_version")
                    or template_data.get("version")
                    or metadata.get("version")
                )
                return version if version else None

            self.logger.warning(
                f"Unknown template format: {template_path.suffix} for {template_path.name}"
            )
            return None

        except yaml.YAMLError as e:
            self.logger.warning(
                f"Invalid YAML frontmatter in {template_path.name}: {e}"
            )
            return None
        except json.JSONDecodeError as e:
            self.logger.warning(f"Invalid JSON in {template_path.name}: {e}")
            return None
        except Exception as e:
            self.logger.warning(
                f"Error reading template version from {template_path.name}: {e}"
            )
            return None

    def _build_canonical_id_for_agent(self, agent_info: Dict[str, Any]) -> str:
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

    def discover_agents_from_all_sources(
        self,
        system_templates_dir: Optional[Path] = None,
        project_agents_dir: Optional[Path] = None,
        user_agents_dir: Optional[Path] = None,
        agents_cache_dir: Optional[Path] = None,
        working_directory: Optional[Path] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
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
        agents_by_name = {}

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

                # Use appropriate discovery service based on source type
                if source_name == "remote":
                    # Remote agents are Markdown, use RemoteAgentDiscoveryService
                    remote_service = RemoteAgentDiscoveryService(source_dir)
                    agents = remote_service.discover_remote_agents()
                else:
                    # Other sources are JSON, use AgentDiscoveryService
                    discovery_service = AgentDiscoveryService(source_dir)
                    # Pass log_discovery=False to avoid duplicate logging
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
        agents_cache_dir: Optional[Path] = None,
    ) -> List[Dict[str, Any]]:
        """Get all agents from a specific collection.

        NEW: Enables collection-based agent selection.

        Args:
            collection_id: Collection identifier (e.g., "bobmatnyc/claude-mpm-agents")
            agents_cache_dir: Directory containing agents cache

        Returns:
            List of agent dictionaries from the specified collection

        Example:
            >>> service = MultiSourceAgentDeploymentService()
            >>> agents = service.get_agents_by_collection("bobmatnyc/claude-mpm-agents")
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

    def select_highest_version_agents(
        self, agents_by_name: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Dict[str, Any]]:
        """Select the highest version agent from multiple sources.

        Args:
            agents_by_name: Dictionary mapping agent names to list of agent info

        Returns:
            Dictionary mapping agent names to the highest version agent info
        """
        selected_agents = {}

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

    def get_agents_for_deployment(
        self,
        system_templates_dir: Optional[Path] = None,
        project_agents_dir: Optional[Path] = None,
        user_agents_dir: Optional[Path] = None,
        agents_cache_dir: Optional[Path] = None,
        working_directory: Optional[Path] = None,
        excluded_agents: Optional[List[str]] = None,
        config: Optional[Config] = None,
        cleanup_outdated: bool = True,
    ) -> Tuple[Dict[str, Path], Dict[str, str], Dict[str, Any]]:
        """Get the highest version agents from all 4 tiers for deployment.

        Args:
            system_templates_dir: Directory containing system agent templates
            project_agents_dir: Directory containing project-specific agents
            user_agents_dir: Directory containing user custom agents (DEPRECATED)
            agents_cache_dir: Directory containing cached agents from Git sources
            working_directory: Current working directory for finding project agents
            excluded_agents: List of agent names to exclude from deployment
            config: Configuration object for additional filtering
            cleanup_outdated: Whether to cleanup outdated user agents (default: True)

        Returns:
            Tuple of:
            - Dictionary mapping agent names to template file paths
            - Dictionary mapping agent names to their source
            - Dictionary with cleanup results (removed, preserved, errors)
        """
        # Discover all available agents from 4 tiers
        agents_by_name = self.discover_agents_from_all_sources(
            system_templates_dir=system_templates_dir,
            project_agents_dir=project_agents_dir,
            user_agents_dir=user_agents_dir,
            agents_cache_dir=agents_cache_dir,
            working_directory=working_directory,
        )

        # Select highest version for each agent
        selected_agents = self.select_highest_version_agents(agents_by_name)

        # Clean up outdated user agents if enabled
        cleanup_results = {"removed": [], "preserved": [], "errors": []}
        if cleanup_outdated:
            # Check if cleanup is enabled in config or environment
            cleanup_enabled = True

            # Check environment variable first (for CI/CD and testing)
            env_cleanup = os.environ.get("CLAUDE_MPM_CLEANUP_USER_AGENTS", "").lower()
            if env_cleanup in ["false", "0", "no", "disabled"]:
                cleanup_enabled = False
                self.logger.debug(
                    "User agent cleanup disabled via environment variable"
                )

            # Check config if environment doesn't disable it
            if cleanup_enabled and config:
                cleanup_enabled = config.get(
                    "agent_deployment.cleanup_outdated_user_agents", True
                )

            if cleanup_enabled:
                cleanup_results = self.cleanup_outdated_user_agents(
                    agents_by_name, selected_agents
                )

        # Apply exclusion filters
        if excluded_agents:
            # Find agents to remove by matching normalized names
            # Normalization handles: "Dart Engineer", "dart_engineer", "dart-engineer"
            agents_to_remove = []
            excluded_set = {_normalize_agent_name(name) for name in excluded_agents}

            for canonical_id, agent_info in list(selected_agents.items()):
                # Check agent name field (normalized)
                agent_name = _normalize_agent_name(agent_info.get("name", ""))

                # Also check the agent_id portion of canonical_id (after the colon)
                # Example: "bobmatnyc/claude-mpm-agents:pm" -> "pm"
                raw_agent_id = (
                    canonical_id.split(":")[-1]
                    if ":" in canonical_id
                    else canonical_id
                )
                agent_id = _normalize_agent_name(raw_agent_id)

                # Check file stem from path (most reliable match)
                file_stem = ""
                path_str = agent_info.get("path") or agent_info.get("file_path")
                if path_str:
                    file_stem = _normalize_agent_name(Path(path_str).stem)

                if (
                    agent_name in excluded_set
                    or agent_id in excluded_set
                    or file_stem in excluded_set
                ):
                    agents_to_remove.append(canonical_id)
                    self.logger.info(
                        f"Excluding agent '{agent_info.get('name', raw_agent_id)}' "
                        f"(canonical_id: {canonical_id}) from deployment"
                    )

            # Remove matched agents
            for canonical_id in agents_to_remove:
                del selected_agents[canonical_id]

        # Apply config-based filtering if provided
        if config:
            selected_agents = self._apply_config_filters(selected_agents, config)

        # Create deployment mappings
        agents_to_deploy = {}
        agent_sources = {}

        for agent_name, agent_info in selected_agents.items():
            # Defensive: Try multiple path fields for backward compatibility (ticket 1M-480)
            # Priority: 'path' -> 'file_path' -> 'source_file'
            path_str = (
                agent_info.get("path")
                or agent_info.get("file_path")
                or agent_info.get("source_file")
            )

            if not path_str:
                self.logger.warning(
                    f"Agent '{agent_name}' missing path information (no 'path', 'file_path', or 'source_file' field)"
                )
                continue

            template_path = Path(path_str)
            if template_path.exists():
                # Use the file stem as the key for consistency
                file_stem = template_path.stem
                agents_to_deploy[file_stem] = template_path
                agent_sources[file_stem] = agent_info["source"]

                # Also keep the display name mapping for logging
                if file_stem != agent_name:
                    self.logger.debug(f"Mapping '{agent_name}' -> '{file_stem}'")
            else:
                self.logger.warning(
                    f"Template file not found for agent '{agent_name}': {template_path}"
                )

        self.logger.info(
            f"Selected {len(agents_to_deploy)} agents for deployment "
            f"(system: {sum(1 for s in agent_sources.values() if s == 'system')}, "
            f"project: {sum(1 for s in agent_sources.values() if s == 'project')}, "
            f"user: {sum(1 for s in agent_sources.values() if s == 'user')})"
        )

        return agents_to_deploy, agent_sources, cleanup_results

    def cleanup_excluded_agents(
        self,
        deployed_agents_dir: Path,
        agents_to_deploy: Dict[str, Path],
    ) -> Dict[str, Any]:
        """Remove agents from deployed directory that aren't in the deployment list.

        Similar to skill cleanup logic, this removes agents that were previously
        deployed but are no longer in the enabled agents list (e.g., filtered out
        by profile configuration).

        Args:
            deployed_agents_dir: Directory containing deployed agents (~/.claude/agents)
            agents_to_deploy: Dictionary mapping agent file stems to template paths

        Returns:
            Dictionary with cleanup results:
            - removed: List of removed agent names
            - errors: List of errors during cleanup
        """
        cleanup_results = {"removed": [], "errors": []}

        # Safety check - only operate on deployed agents directory
        if not deployed_agents_dir.exists():
            self.logger.debug("Deployed agents directory does not exist, no cleanup needed")
            return cleanup_results

        # Build set of agent names that should exist (file stems without .md extension)
        expected_agents = set(agents_to_deploy.keys())

        try:
            # Check each file in deployed_agents_dir
            for item in deployed_agents_dir.iterdir():
                # Only process .md files
                if not item.is_file() or item.suffix != ".md":
                    continue

                # Skip hidden files
                if item.name.startswith("."):
                    continue

                # Get agent name (file stem)
                agent_name = item.stem

                # Check if this agent should be kept
                if agent_name not in expected_agents:
                    try:
                        # Security: Validate path is within deployed_agents_dir
                        resolved_item = item.resolve()
                        resolved_target = deployed_agents_dir.resolve()

                        if not str(resolved_item).startswith(str(resolved_target)):
                            self.logger.error(
                                f"Refusing to remove path outside target directory: {item}"
                            )
                            cleanup_results["errors"].append(
                                {
                                    "agent": agent_name,
                                    "error": "Path outside target directory",
                                }
                            )
                            continue

                        # Remove the agent file
                        item.unlink()
                        cleanup_results["removed"].append(agent_name)
                        self.logger.info(f"Removed excluded agent: {agent_name}")

                    except PermissionError as e:
                        error_msg = f"Permission denied removing {agent_name}: {e}"
                        self.logger.error(error_msg)
                        cleanup_results["errors"].append(
                            {"agent": agent_name, "error": error_msg}
                        )
                    except Exception as e:
                        error_msg = f"Error removing {agent_name}: {e}"
                        self.logger.error(error_msg)
                        cleanup_results["errors"].append(
                            {"agent": agent_name, "error": error_msg}
                        )

        except Exception as e:
            self.logger.error(f"Error during agent cleanup: {e}")
            cleanup_results["errors"].append(
                {"agent": "cleanup_process", "error": str(e)}
            )

        # Log cleanup summary
        if cleanup_results["removed"]:
            self.logger.info(
                f"Cleanup complete: removed {len(cleanup_results['removed'])} excluded agents"
            )
        if cleanup_results["errors"]:
            self.logger.warning(
                f"Encountered {len(cleanup_results['errors'])} errors during cleanup"
            )

        return cleanup_results

    def cleanup_outdated_user_agents(
        self,
        agents_by_name: Dict[str, List[Dict[str, Any]]],
        selected_agents: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Remove outdated user agents when project or system agents have higher versions.

        WHY: When project agents are updated to newer versions, outdated user agent
        copies should be removed to prevent confusion and ensure the latest version
        is always used. User agents with same or higher versions are preserved to
        respect user customizations.

        Args:
            agents_by_name: Dictionary mapping agent names to list of agent info from different sources
            selected_agents: Dictionary mapping agent names to the selected highest version agent

        Returns:
            Dictionary with cleanup results:
            - removed: List of removed agent info
            - preserved: List of preserved agent info with reasons
            - errors: List of errors during cleanup
        """
        cleanup_results = {"removed": [], "preserved": [], "errors": []}

        # Get user agents directory
        user_agents_dir = Path.home() / ".claude-mpm" / "agents"

        # Safety check - only operate on user agents directory
        if not user_agents_dir.exists():
            self.logger.debug("User agents directory does not exist, no cleanup needed")
            return cleanup_results

        for agent_name, agent_versions in agents_by_name.items():
            # Skip if only one version exists
            if len(agent_versions) < 2:
                continue

            selected = selected_agents.get(agent_name)
            if not selected:
                continue

            # Process each version of this agent
            for agent_info in agent_versions:
                # Only consider user agents for cleanup
                if agent_info["source"] != "user":
                    continue

                # Defensive: Get path from agent_info (ticket 1M-480)
                path_str = (
                    agent_info.get("path")
                    or agent_info.get("file_path")
                    or agent_info.get("source_file")
                )
                if not path_str:
                    self.logger.warning(
                        f"User agent '{agent_name}' missing path information, skipping cleanup"
                    )
                    continue

                # Safety check - ensure path is within user agents directory
                user_agent_path = Path(path_str)
                try:
                    # Resolve paths to compare them safely
                    resolved_user_path = user_agent_path.resolve()
                    resolved_user_agents_dir = user_agents_dir.resolve()

                    # Verify the agent is actually in the user agents directory
                    if not str(resolved_user_path).startswith(
                        str(resolved_user_agents_dir)
                    ):
                        self.logger.warning(
                            f"Skipping cleanup for {agent_name}: path {user_agent_path} "
                            f"is not within user agents directory"
                        )
                        cleanup_results["errors"].append(
                            {
                                "agent": agent_name,
                                "error": "Path outside user agents directory",
                            }
                        )
                        continue
                except Exception as e:
                    self.logger.error(f"Error resolving paths for {agent_name}: {e}")
                    cleanup_results["errors"].append(
                        {"agent": agent_name, "error": f"Path resolution error: {e}"}
                    )
                    continue

                # Compare versions
                user_version = self.version_manager.parse_version(
                    agent_info.get("version", "0.0.0")
                )
                selected_version = self.version_manager.parse_version(
                    selected.get("version", "0.0.0")
                )

                version_comparison = self.version_manager.compare_versions(
                    user_version, selected_version
                )

                # Determine action based on version comparison and selected source
                if version_comparison < 0 and selected["source"] in [
                    "project",
                    "system",
                ]:
                    # User agent has lower version than selected project/system agent - remove it
                    if user_agent_path.exists():
                        try:
                            # Log before removal for audit trail
                            self.logger.info(
                                f"Removing outdated user agent: {agent_name} "
                                f"v{self.version_manager.format_version_display(user_version)} "
                                f"(superseded by {selected['source']} "
                                f"v{self.version_manager.format_version_display(selected_version)})"
                            )

                            # Remove the file
                            user_agent_path.unlink()

                            cleanup_results["removed"].append(
                                {
                                    "name": agent_name,
                                    "version": self.version_manager.format_version_display(
                                        user_version
                                    ),
                                    "path": str(user_agent_path),
                                    "reason": f"Superseded by {selected['source']} v{self.version_manager.format_version_display(selected_version)}",
                                }
                            )
                        except PermissionError as e:
                            error_msg = f"Permission denied removing {agent_name}: {e}"
                            self.logger.error(error_msg)
                            cleanup_results["errors"].append(
                                {"agent": agent_name, "error": error_msg}
                            )
                        except Exception as e:
                            error_msg = f"Error removing {agent_name}: {e}"
                            self.logger.error(error_msg)
                            cleanup_results["errors"].append(
                                {"agent": agent_name, "error": error_msg}
                            )
                else:
                    # Preserve the user agent
                    if version_comparison >= 0:
                        reason = "User version same or higher than selected version"
                    elif selected["source"] == "user":
                        reason = "User agent is the selected version"
                    else:
                        reason = "User customization preserved"

                    cleanup_results["preserved"].append(
                        {
                            "name": agent_name,
                            "version": self.version_manager.format_version_display(
                                user_version
                            ),
                            "reason": reason,
                        }
                    )

                    self.logger.debug(
                        f"Preserving user agent {agent_name} "
                        f"v{self.version_manager.format_version_display(user_version)}: {reason}"
                    )

        # Log cleanup summary
        if cleanup_results["removed"]:
            self.logger.info(
                f"Cleanup complete: removed {len(cleanup_results['removed'])} outdated user agents"
            )
        if cleanup_results["preserved"]:
            self.logger.debug(
                f"Preserved {len(cleanup_results['preserved'])} user agents"
            )
        if cleanup_results["errors"]:
            self.logger.warning(
                f"Encountered {len(cleanup_results['errors'])} errors during cleanup"
            )

        return cleanup_results

    def _is_user_created_agent(self, agent_file: Path) -> bool:
        """Check if an agent is user-created based on metadata.

        User agents are identified by:
        - Lack of MPM authorship indicators
        - Missing version or v0.0.0
        - Certain naming patterns

        Args:
            agent_file: Path to the agent file to check

        Returns:
            True if the agent appears to be user-created, False otherwise
        """
        try:
            content = agent_file.read_text()

            # Check for MPM authorship indicators
            mpm_indicators = [
                "author: claude-mpm",
                "author: 'claude-mpm'",
                'author: "claude-mpm"',
                "author: Claude MPM",
                "Claude MPM Team",
                "Generated by Claude MPM",
                "claude-mpm-project",
            ]

            for indicator in mpm_indicators:
                if indicator.lower() in content.lower():
                    return False  # This is an MPM agent

            # Check for version 0.0.0 (typical user agent default)
            if "version: 0.0.0" in content or "version: '0.0.0'" in content:
                return True

            return True  # Default to user-created if no MPM indicators

        except Exception:
            return True  # Default to user-created if we can't read it

    def _apply_config_filters(
        self, selected_agents: Dict[str, Dict[str, Any]], config: Config
    ) -> Dict[str, Dict[str, Any]]:
        """Apply configuration-based filtering to selected agents.

        Args:
            selected_agents: Dictionary of selected agents
            config: Configuration object

        Returns:
            Filtered dictionary of agents
        """
        filtered_agents = {}

        # Get exclusion patterns from config
        exclusion_patterns = config.get("agent_deployment.exclusion_patterns", [])

        # Get environment-specific exclusions
        environment = config.get("environment", "development")
        env_exclusions = config.get(f"agent_deployment.{environment}_exclusions", [])

        for agent_name, agent_info in selected_agents.items():
            # Check exclusion patterns
            excluded = False

            for pattern in exclusion_patterns:
                if pattern in agent_name:
                    self.logger.debug(
                        f"Excluding '{agent_name}' due to pattern '{pattern}'"
                    )
                    excluded = True
                    break

            # Check environment exclusions
            if not excluded and agent_name in env_exclusions:
                self.logger.debug(
                    f"Excluding '{agent_name}' due to {environment} environment"
                )
                excluded = True

            if not excluded:
                filtered_agents[agent_name] = agent_info

        return filtered_agents

    def compare_deployed_versions(
        self,
        deployed_agents_dir: Path,
        agents_to_deploy: Dict[str, Path],
        agent_sources: Dict[str, str],
    ) -> Dict[str, Any]:
        """Compare deployed agent versions with candidates for deployment.

        Args:
            deployed_agents_dir: Directory containing currently deployed agents
            agents_to_deploy: Dictionary mapping agent names to template paths
            agent_sources: Dictionary mapping agent names to their sources

        Returns:
            Dictionary with comparison results including which agents need updates
        """
        comparison_results = {
            "needs_update": [],
            "up_to_date": [],
            "new_agents": [],
            "orphaned_agents": [],  # System agents without templates
            "user_agents": [],  # User-created agents (no templates required)
            "version_upgrades": [],
            "version_downgrades": [],
            "source_changes": [],
        }

        for agent_name, template_path in agents_to_deploy.items():
            deployed_file = deployed_agents_dir / f"{agent_name}.md"

            if not deployed_file.exists():
                comparison_results["new_agents"].append(
                    {
                        "name": agent_name,
                        "source": agent_sources[agent_name],
                        "template": str(template_path),
                    }
                )
                comparison_results["needs_update"].append(agent_name)
                continue

            # Read template version using format-aware helper
            version_string = self._read_template_version(template_path)
            if not version_string:
                self.logger.warning(
                    f"Could not extract version from template for '{agent_name}', skipping"
                )
                continue

            try:
                template_version = self.version_manager.parse_version(version_string)
            except Exception as e:
                self.logger.warning(
                    f"Error parsing version '{version_string}' for '{agent_name}': {e}"
                )
                continue

            # Read deployed version
            try:
                deployed_content = deployed_file.read_text()
                deployed_version, _, _ = (
                    self.version_manager.extract_version_from_frontmatter(
                        deployed_content
                    )
                )

                # Extract source from deployed agent if available
                deployed_source = "unknown"
                if "source:" in deployed_content:
                    import re

                    source_match = re.search(
                        r"^source:\s*(.+)$", deployed_content, re.MULTILINE
                    )
                    if source_match:
                        deployed_source = source_match.group(1).strip()

                # If source is still unknown, try to infer it from deployment context
                if deployed_source == "unknown":
                    deployed_source = self._infer_agent_source_from_context(
                        agent_name, deployed_agents_dir
                    )
            except Exception as e:
                self.logger.warning(f"Error reading deployed agent '{agent_name}': {e}")
                comparison_results["needs_update"].append(agent_name)
                continue

            # Compare versions
            version_comparison = self.version_manager.compare_versions(
                template_version, deployed_version
            )

            if version_comparison > 0:
                # Template version is higher
                comparison_results["version_upgrades"].append(
                    {
                        "name": agent_name,
                        "deployed_version": self.version_manager.format_version_display(
                            deployed_version
                        ),
                        "new_version": self.version_manager.format_version_display(
                            template_version
                        ),
                        "source": agent_sources[agent_name],
                        "previous_source": deployed_source,
                    }
                )
                comparison_results["needs_update"].append(agent_name)

                if deployed_source != agent_sources[agent_name]:
                    comparison_results["source_changes"].append(
                        {
                            "name": agent_name,
                            "from_source": deployed_source,
                            "to_source": agent_sources[agent_name],
                        }
                    )
            elif version_comparison < 0:
                # Deployed version is higher (shouldn't happen with proper version management)
                comparison_results["version_downgrades"].append(
                    {
                        "name": agent_name,
                        "deployed_version": self.version_manager.format_version_display(
                            deployed_version
                        ),
                        "template_version": self.version_manager.format_version_display(
                            template_version
                        ),
                        "warning": "Deployed version is higher than template",
                    }
                )
                # Don't add to needs_update - keep the higher version
            else:
                # Versions are equal
                comparison_results["up_to_date"].append(
                    {
                        "name": agent_name,
                        "version": self.version_manager.format_version_display(
                            deployed_version
                        ),
                        "source": agent_sources[agent_name],
                    }
                )

        # Check for orphaned agents (deployed but no template)
        system_orphaned, user_orphaned = self._detect_orphaned_agents_simple(
            deployed_agents_dir, agents_to_deploy
        )
        comparison_results["orphaned_agents"] = system_orphaned
        comparison_results["user_agents"] = user_orphaned

        # Log summary
        summary_parts = [
            f"{len(comparison_results['needs_update'])} need updates",
            f"{len(comparison_results['up_to_date'])} up to date",
            f"{len(comparison_results['new_agents'])} new agents",
        ]
        if comparison_results["orphaned_agents"]:
            summary_parts.append(
                f"{len(comparison_results['orphaned_agents'])} system orphaned"
            )
        if comparison_results["user_agents"]:
            summary_parts.append(
                f"{len(comparison_results['user_agents'])} user agents"
            )

        self.logger.info(f"Version comparison complete: {', '.join(summary_parts)}")

        # Don't log upgrades here - let the caller decide when to log
        # This prevents repeated upgrade messages on every startup
        if comparison_results["version_upgrades"]:
            for upgrade in comparison_results["version_upgrades"]:
                self.logger.debug(
                    f"  Upgrade available: {upgrade['name']} "
                    f"{upgrade['deployed_version']} -> {upgrade['new_version']} "
                    f"(from {upgrade['source']})"
                )

        if comparison_results["source_changes"]:
            for change in comparison_results["source_changes"]:
                self.logger.debug(
                    f"  Source change available: {change['name']} "
                    f"from {change['from_source']} to {change['to_source']}"
                )

        if comparison_results["version_downgrades"]:
            for downgrade in comparison_results["version_downgrades"]:
                # Changed from warning to debug - deployed versions higher than templates
                # are not errors, just informational
                self.logger.debug(
                    f"  Note: {downgrade['name']} deployed version "
                    f"{downgrade['deployed_version']} is higher than template "
                    f"{downgrade['template_version']} (keeping deployed version)"
                )

        # Log system orphaned agents if found
        if comparison_results["orphaned_agents"]:
            self.logger.info(
                f"Found {len(comparison_results['orphaned_agents'])} system orphaned agent(s) "
                f"(deployed without templates):"
            )
            for orphan in comparison_results["orphaned_agents"]:
                self.logger.info(
                    f"  - {orphan['name']} v{orphan['version']} "
                    f"(consider removing or creating a template)"
                )

        # Log user agents at debug level if found
        if comparison_results["user_agents"]:
            self.logger.debug(
                f"Found {len(comparison_results['user_agents'])} user-created agent(s) "
                f"(no templates required):"
            )
            for user_agent in comparison_results["user_agents"]:
                self.logger.debug(
                    f"  - {user_agent['name']} v{user_agent['version']} "
                    f"(user-created agent)"
                )

        return comparison_results

    def _infer_agent_source_from_context(
        self, agent_name: str, deployed_agents_dir: Path
    ) -> str:
        """Infer the source of a deployed agent when source metadata is missing.

        This method attempts to determine the agent source based on:
        1. Deployment context (development vs pipx)
        2. Agent naming patterns
        3. Known system agents

        Args:
            agent_name: Name of the agent
            deployed_agents_dir: Directory where agent is deployed

        Returns:
            Inferred source string (system/project/user)
        """
        # List of known system agents that ship with claude-mpm
        system_agents = {
            "pm",
            "engineer",
            "qa",
            "research",
            "documentation",
            "ops",
            "security",
            "web-ui",
            "api-qa",
            "version-control",
        }

        # If this is a known system agent, it's from system
        if agent_name in system_agents:
            return "system"

        # Check deployment context
        from ....core.unified_paths import get_path_manager

        path_manager = get_path_manager()

        # If deployed_agents_dir is under user home/.claude/agents, check context
        user_claude_dir = Path.home() / ".claude" / "agents"
        if deployed_agents_dir == user_claude_dir:
            # Check if we're in development mode
            try:
                from ....core.unified_paths import DeploymentContext, PathContext

                deployment_context = PathContext.detect_deployment_context()

                if deployment_context in (
                    DeploymentContext.DEVELOPMENT,
                    DeploymentContext.EDITABLE_INSTALL,
                ):
                    # In development mode, unknown agents are likely system agents being tested
                    return "system"
                if (
                    deployment_context == DeploymentContext.PIPX_INSTALL
                    and agent_name.count("-") <= 2
                    and len(agent_name) <= 20
                ):
                    # In pipx mode, check if agent follows system naming patterns
                    return "system"
            except Exception:
                pass

        # Check if deployed to project-specific directory
        try:
            project_root = path_manager.project_root
            if str(deployed_agents_dir).startswith(str(project_root)):
                return "project"
        except Exception:
            pass

        # Default inference based on naming patterns
        # System agents typically have simple names
        if "-" not in agent_name or agent_name.count("-") <= 1:
            return "system"

        # Complex names are more likely to be user/project agents
        return "user"

    def detect_orphaned_agents(
        self, deployed_agents_dir: Path, available_agents: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect deployed agents that don't have corresponding templates.

        WHY: Orphaned agents can cause confusion with version warnings.
        This method identifies them so they can be handled appropriately.

        Args:
            deployed_agents_dir: Directory containing deployed agents
            available_agents: Dictionary of available agents from all sources

        Returns:
            List of orphaned agent information
        """
        orphaned = []

        if not deployed_agents_dir.exists():
            return orphaned

        # Build a mapping of file stems to agent names for comparison
        # Since available_agents uses display names like "Code Analysis Agent"
        # but deployed files use stems like "code_analyzer"
        available_stems = set()
        stem_to_name = {}

        for agent_name, agent_sources in available_agents.items():
            # Get the file path from the first source to extract the stem
            if (
                agent_sources
                and isinstance(agent_sources, list)
                and len(agent_sources) > 0
            ):
                first_source = agent_sources[0]
                if "file_path" in first_source:
                    file_path = Path(first_source["file_path"])
                    stem = file_path.stem
                    available_stems.add(stem)
                    stem_to_name[stem] = agent_name

        for deployed_file in deployed_agents_dir.glob("*.md"):
            agent_stem = deployed_file.stem

            # Skip if this agent has a template (check by stem, not display name)
            if agent_stem in available_stems:
                continue

            # This is an orphaned agent
            try:
                deployed_content = deployed_file.read_text()
                deployed_version, _, _ = (
                    self.version_manager.extract_version_from_frontmatter(
                        deployed_content
                    )
                )
                version_str = self.version_manager.format_version_display(
                    deployed_version
                )
            except Exception:
                version_str = "unknown"

            orphaned.append(
                {"name": agent_stem, "file": str(deployed_file), "version": version_str}
            )

        return orphaned

    def _detect_orphaned_agents_simple(
        self, deployed_agents_dir: Path, agents_to_deploy: Dict[str, Path]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Simple orphan detection that works with agents_to_deploy structure.

        Args:
            deployed_agents_dir: Directory containing deployed agents
            agents_to_deploy: Dictionary mapping file stems to template paths

        Returns:
            Tuple of (system_orphaned_agents, user_orphaned_agents)
        """
        system_orphaned = []
        user_orphaned = []

        if not deployed_agents_dir.exists():
            return system_orphaned, user_orphaned

        # agents_to_deploy already contains file stems as keys
        available_stems = set(agents_to_deploy.keys())

        for deployed_file in deployed_agents_dir.glob("*.md"):
            agent_stem = deployed_file.stem

            # Skip if this agent has a template (check by stem)
            if agent_stem in available_stems:
                continue

            # This is an orphaned agent - determine if it's user-created or system
            try:
                deployed_content = deployed_file.read_text()
                deployed_version, _, _ = (
                    self.version_manager.extract_version_from_frontmatter(
                        deployed_content
                    )
                )
                version_str = self.version_manager.format_version_display(
                    deployed_version
                )
            except Exception:
                version_str = "unknown"

            orphan_info = {
                "name": agent_stem,
                "file": str(deployed_file),
                "version": version_str,
            }

            # Determine if this is a user-created agent
            if self._is_user_created_agent(deployed_file):
                user_orphaned.append(orphan_info)
            else:
                system_orphaned.append(orphan_info)

        return system_orphaned, user_orphaned

    def cleanup_orphaned_agents(
        self, deployed_agents_dir: Path, dry_run: bool = True
    ) -> Dict[str, Any]:
        """Clean up orphaned agents that don't have templates.

        WHY: Orphaned agents can accumulate over time and cause confusion.
        This method provides a way to clean them up systematically.

        Args:
            deployed_agents_dir: Directory containing deployed agents
            dry_run: If True, only report what would be removed

        Returns:
            Dictionary with cleanup results
        """
        results = {"orphaned": [], "removed": [], "errors": []}

        # First, discover all available agents from all sources
        all_agents = self.discover_agents_from_all_sources()
        set(all_agents.keys())

        # Detect orphaned agents
        orphaned = self.detect_orphaned_agents(deployed_agents_dir, all_agents)
        results["orphaned"] = orphaned

        if not orphaned:
            self.logger.info("No orphaned agents found")
            return results

        self.logger.info(f"Found {len(orphaned)} orphaned agent(s)")

        for orphan in orphaned:
            agent_file = Path(orphan["file"])

            if dry_run:
                self.logger.info(
                    f"  Would remove: {orphan['name']} v{orphan['version']}"
                )
            else:
                try:
                    agent_file.unlink()
                    results["removed"].append(orphan["name"])
                    self.logger.info(
                        f"  Removed: {orphan['name']} v{orphan['version']}"
                    )
                except Exception as e:
                    error_msg = f"Failed to remove {orphan['name']}: {e}"
                    results["errors"].append(error_msg)
                    self.logger.error(f"  {error_msg}")

        if dry_run and orphaned:
            self.logger.info(
                "Run with dry_run=False to actually remove orphaned agents"
            )

        return results
