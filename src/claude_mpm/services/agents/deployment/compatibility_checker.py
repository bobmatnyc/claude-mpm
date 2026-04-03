"""Compatibility Checker — compares deployed agent versions against deployment candidates.

Single responsibility: given the set of deployed agents and candidate templates, report
which need updates, which are up-to-date, and which are orphaned.
"""

from pathlib import Path
from typing import Any

from claude_mpm.core.logging_config import get_logger

from .agent_version_manager import AgentVersionManager
from .manifest_fetcher import ManifestFetcher


class CompatibilityChecker:
    """Compares deployed agent versions with candidates and detects orphans.

    Responsibilities:
    - compare_deployed_versions: full diff between deployed dir and candidates
    - detect_orphaned_agents: find deployed agents with no template (DEPRECATED API)
    - _detect_orphaned_agents_simple: internal helper used by compare_deployed_versions
    - _infer_agent_source_from_context: heuristic source inference when metadata absent
    """

    def __init__(
        self,
        version_manager: AgentVersionManager | None = None,
        manifest_fetcher: ManifestFetcher | None = None,
    ) -> None:
        self.logger = get_logger(__name__)
        self.version_manager = version_manager or AgentVersionManager()
        self.manifest_fetcher = manifest_fetcher or ManifestFetcher()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compare_deployed_versions(
        self,
        deployed_agents_dir: Path,
        agents_to_deploy: dict[str, Path],
        agent_sources: dict[str, str],
    ) -> dict[str, Any]:
        """Compare deployed agent versions with candidates for deployment.

        Args:
            deployed_agents_dir: Directory containing currently deployed agents
            agents_to_deploy: Dictionary mapping agent names to template paths
            agent_sources: Dictionary mapping agent names to their sources

        Returns:
            Dictionary with comparison results including which agents need updates
        """
        comparison_results: dict[str, Any] = {
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
            version_string = self.manifest_fetcher.read_template_version(template_path)
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

    def detect_orphaned_agents(
        self, deployed_agents_dir: Path, available_agents: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Detect deployed agents that don't have corresponding templates.

        DEPRECATED: This method is retained only for backward compatibility.
        All orphan detection and removal should use the canonical System A in
        startup_reconciliation.py::_detect_and_remove_orphaned_agents().

        Unlike System A, this method includes proper provenance filtering via
        is_mpm_managed_file() so only MPM-managed agents are reported as orphans.

        Args:
            deployed_agents_dir: Directory containing deployed agents
            available_agents: Dictionary of available agents from all sources

        Returns:
            List of orphaned agent information (only MPM-managed agents)
        """
        from claude_mpm.utils.agent_provenance import is_mpm_managed_file

        orphaned = []

        if not deployed_agents_dir.exists():
            return orphaned

        # Build a mapping of file stems to agent names for comparison
        available_stems = set()

        for _, agent_sources in available_agents.items():
            if (
                agent_sources
                and isinstance(agent_sources, list)
                and len(agent_sources) > 0
            ):
                first_source = agent_sources[0]
                if "file_path" in first_source:
                    file_path = Path(first_source["file_path"])
                    available_stems.add(file_path.stem)

        for deployed_file in deployed_agents_dir.glob("*.md"):
            agent_stem = deployed_file.stem

            # Skip if this agent has a template
            if agent_stem in available_stems:
                continue

            # Only report MPM-managed agents as orphans (provenance check)
            if not is_mpm_managed_file(deployed_file):
                continue

            # This is an orphaned MPM-managed agent
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

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _detect_orphaned_agents_simple(
        self, deployed_agents_dir: Path, agents_to_deploy: dict[str, Path]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Simple orphan detection that works with agents_to_deploy structure.

        Args:
            deployed_agents_dir: Directory containing deployed agents
            agents_to_deploy: Dictionary mapping file stems to template paths

        Returns:
            Tuple of (system_orphaned_agents, user_orphaned_agents)
        """
        system_orphaned: list[dict[str, Any]] = []
        user_orphaned: list[dict[str, Any]] = []

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

    def _is_user_created_agent(self, agent_file: Path) -> bool:
        """Check if an agent is user-created (not MPM-managed)."""
        from claude_mpm.utils.agent_provenance import is_mpm_managed_file

        return not is_mpm_managed_file(agent_file)

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
