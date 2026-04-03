"""Multi-Source Agent Deployment Service

This service implements proper version comparison across multiple agent sources,
ensuring the highest version agent is deployed regardless of source.

Key Features:
- Discovers agents from multiple sources (system templates, project agents, user agents)
- Compares versions across all sources
- Deploys the highest version for each agent
- Tracks which source provided the deployed agent
- Maintains backward compatibility with existing deployment modes

Implementation note
-------------------
The heavy lifting is delegated to three focused collaborators:

* ManifestFetcher       — reads version metadata from .md / .json template files
* AgentMerger           — discovers agents from the 4-tier hierarchy and selects winners
* CompatibilityChecker  — diffs deployed agents against candidates; detects orphans

This class is the thin pipeline coordinator that wires them together and owns
the public API consumed by callers outside this package.
"""

import os
from pathlib import Path
from typing import Any

from claude_mpm.core.config import Config
from claude_mpm.core.logging_config import get_logger
from claude_mpm.services.agents.deployment_utils import normalize_deployment_filename
from claude_mpm.utils.agent_filters import normalize_agent_id

from .agent_merger import AgentMerger
from .agent_version_manager import AgentVersionManager
from .compatibility_checker import CompatibilityChecker
from .manifest_fetcher import ManifestFetcher


def _normalize_agent_name(name: str) -> str:
    """Normalize agent name for consistent comparison.

    Delegates to the canonical normalize_agent_id() normalizer which produces
    lowercase, kebab-case identifiers with no -agent suffix.

    Examples:
        "Dart Engineer" -> "dart-engineer"
        "dart_engineer" -> "dart-engineer"
        "DART-ENGINEER" -> "dart-engineer"
        "research-agent" -> "research"
    """
    return normalize_agent_id(name)


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

    def __init__(self) -> None:
        """Initialize the multi-source deployment service."""
        self.logger = get_logger(__name__)
        self.version_manager = AgentVersionManager()
        self._manifest_fetcher = ManifestFetcher()
        self._merger = AgentMerger(version_manager=self.version_manager)
        self._checker = CompatibilityChecker(
            version_manager=self.version_manager,
            manifest_fetcher=self._manifest_fetcher,
        )

    # ------------------------------------------------------------------
    # Delegated methods (kept for public API / backward compat)
    # ------------------------------------------------------------------

    def _read_template_version(self, template_path: Path) -> str | None:
        """Read version from template file (supports both .md and .json formats).

        Delegates to ManifestFetcher.read_template_version.
        """
        return self._manifest_fetcher.read_template_version(template_path)

    def _build_canonical_id_for_agent(self, agent_info: dict[str, Any]) -> str:
        """Build or retrieve canonical_id for an agent.

        Delegates to AgentMerger._build_canonical_id_for_agent.
        """
        return self._merger._build_canonical_id_for_agent(agent_info)

    def discover_agents_from_all_sources(
        self,
        system_templates_dir: Path | None = None,
        project_agents_dir: Path | None = None,
        user_agents_dir: Path | None = None,
        agents_cache_dir: Path | None = None,
        working_directory: Path | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Discover agents from all 4 tiers (system, user, cache, project).

        Delegates to AgentMerger.discover_agents_from_all_sources.
        """
        return self._merger.discover_agents_from_all_sources(
            system_templates_dir=system_templates_dir,
            project_agents_dir=project_agents_dir,
            user_agents_dir=user_agents_dir,
            agents_cache_dir=agents_cache_dir,
            working_directory=working_directory,
        )

    def get_agents_by_collection(
        self,
        collection_id: str,
        agents_cache_dir: Path | None = None,
    ) -> list[dict[str, Any]]:
        """Get all agents from a specific collection.

        Delegates to AgentMerger.get_agents_by_collection.
        """
        return self._merger.get_agents_by_collection(
            collection_id=collection_id,
            agents_cache_dir=agents_cache_dir,
        )

    def select_highest_version_agents(
        self, agents_by_name: dict[str, list[dict[str, Any]]]
    ) -> dict[str, dict[str, Any]]:
        """Select the highest version agent from multiple sources.

        Delegates to AgentMerger.select_highest_version_agents.
        """
        return self._merger.select_highest_version_agents(agents_by_name)

    def compare_deployed_versions(
        self,
        deployed_agents_dir: Path,
        agents_to_deploy: dict[str, Path],
        agent_sources: dict[str, str],
    ) -> dict[str, Any]:
        """Compare deployed agent versions with candidates for deployment.

        Delegates to CompatibilityChecker.compare_deployed_versions.
        """
        return self._checker.compare_deployed_versions(
            deployed_agents_dir=deployed_agents_dir,
            agents_to_deploy=agents_to_deploy,
            agent_sources=agent_sources,
        )

    def detect_orphaned_agents(
        self, deployed_agents_dir: Path, available_agents: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Detect deployed agents that don't have corresponding templates.

        DEPRECATED: retained for backward compatibility.
        Delegates to CompatibilityChecker.detect_orphaned_agents which uses
        is_mpm_managed_file() for provenance filtering so only MPM-managed
        agents are reported as orphans.
        """
        # Provenance guard: is_mpm_managed_file filtering lives in CompatibilityChecker
        return self._checker.detect_orphaned_agents(
            deployed_agents_dir=deployed_agents_dir,
            available_agents=available_agents,
        )

    def _infer_agent_source_from_context(
        self, agent_name: str, deployed_agents_dir: Path
    ) -> str:
        """Infer the source of a deployed agent when source metadata is missing.

        Delegates to CompatibilityChecker._infer_agent_source_from_context.
        """
        return self._checker._infer_agent_source_from_context(
            agent_name=agent_name,
            deployed_agents_dir=deployed_agents_dir,
        )

    def _detect_orphaned_agents_simple(
        self, deployed_agents_dir: Path, agents_to_deploy: dict[str, Path]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Simple orphan detection.

        Delegates to CompatibilityChecker._detect_orphaned_agents_simple.
        """
        return self._checker._detect_orphaned_agents_simple(
            deployed_agents_dir=deployed_agents_dir,
            agents_to_deploy=agents_to_deploy,
        )

    # ------------------------------------------------------------------
    # Pipeline coordinator methods (owned by this class)
    # ------------------------------------------------------------------

    def get_agents_for_deployment(
        self,
        system_templates_dir: Path | None = None,
        project_agents_dir: Path | None = None,
        user_agents_dir: Path | None = None,
        agents_cache_dir: Path | None = None,
        working_directory: Path | None = None,
        excluded_agents: list[str] | None = None,
        config: Config | None = None,
        cleanup_outdated: bool = True,
    ) -> tuple[dict[str, Path], dict[str, str], dict[str, Any]]:
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
        cleanup_results: dict[str, Any] = {"removed": [], "preserved": [], "errors": []}
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
                    canonical_id.split(":")[-1] if ":" in canonical_id else canonical_id
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
        agents_to_deploy: dict[str, Path] = {}
        agent_sources: dict[str, str] = {}

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
                # Use normalized stem as key so it matches the deployed filename
                # (e.g., "content-agent" → normalize → "content" to match "content.md")
                normalized_stem = Path(
                    normalize_deployment_filename(f"{template_path.stem}.md")
                ).stem
                agents_to_deploy[normalized_stem] = template_path
                agent_sources[normalized_stem] = agent_info["source"]

                # Also keep the display name mapping for logging
                if normalized_stem != agent_name:
                    self.logger.debug(f"Mapping '{agent_name}' -> '{normalized_stem}'")
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
        agents_to_deploy: dict[str, Path],
    ) -> dict[str, Any]:
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
        cleanup_results: dict[str, Any] = {"removed": [], "errors": []}

        # Safety check - only operate on deployed agents directory
        if not deployed_agents_dir.exists():
            self.logger.debug(
                "Deployed agents directory does not exist, no cleanup needed"
            )
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
        agents_by_name: dict[str, list[dict[str, Any]]],
        selected_agents: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
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
        cleanup_results: dict[str, Any] = {"removed": [], "preserved": [], "errors": []}

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
        """Check if an agent is user-created (not MPM-managed)."""
        return self._checker._is_user_created_agent(agent_file)

    def _apply_config_filters(
        self, selected_agents: dict[str, dict[str, Any]], config: Config
    ) -> dict[str, dict[str, Any]]:
        """Apply configuration-based filtering to selected agents.

        Args:
            selected_agents: Dictionary of selected agents
            config: Configuration object

        Returns:
            Filtered dictionary of agents
        """
        filtered_agents: dict[str, dict[str, Any]] = {}

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

    def cleanup_orphaned_agents(
        self, deployed_agents_dir: Path, dry_run: bool = True
    ) -> dict[str, Any]:
        """Clean up orphaned agents that don't have templates.

        DEPRECATED: This method is retained for backward compatibility with
        the CLI cleanup command and AgentCleanupService. All automatic orphan
        cleanup during startup uses the canonical System A in
        startup_reconciliation.py::_detect_and_remove_orphaned_agents().

        This method now delegates to detect_orphaned_agents() which includes
        provenance checks (is_mpm_managed_file), ensuring only MPM-managed
        agents are considered for removal.

        Args:
            deployed_agents_dir: Directory containing deployed agents
            dry_run: If True, only report what would be removed

        Returns:
            Dictionary with cleanup results
        """
        results: dict[str, Any] = {"orphaned": [], "removed": [], "errors": []}

        # First, discover all available agents from all sources
        all_agents = self.discover_agents_from_all_sources()

        # Detect orphaned agents (now includes provenance check)
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
