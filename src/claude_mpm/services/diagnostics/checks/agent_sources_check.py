"""
Check agent sources configuration and health.

WHY: Verify that the single-tier Git-based agent system is properly configured,
sources are accessible, and agents are discoverable from configured repositories.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from ....core.enums import OperationResult, ValidationSeverity
from ..models import DiagnosticResult
from .base_check import BaseDiagnosticCheck

logger = logging.getLogger(__name__)


class AgentSourcesCheck(BaseDiagnosticCheck):
    """Check agent sources configuration and health.

    Verifies:
    - Configuration file exists and is valid YAML
    - At least one source is configured
    - Enabled sources are accessible (HTTP 200)
    - Cache directory is healthy and writable
    - Priority conflicts are identified
    - Agents can be discovered from sources

    WHY: The single-tier system relies on Git sources being properly configured
    and accessible. This check ensures the agent deployment pipeline is healthy.
    """

    @property
    def name(self) -> str:
        return "agent_sources_check"

    @property
    def category(self) -> str:
        return "Agent Sources"

    def should_run(self) -> bool:
        """Check should run if single-tier system is in use.

        Returns:
            True if agent sources configuration exists or could exist
        """
        # Always run - we want to check if configuration should be created
        return True

    def run(self) -> DiagnosticResult:
        """Run agent sources diagnostics."""
        try:
            sub_results = []
            details = {}

            # Check 1: Configuration file exists
            config_result = self._check_config_file()
            sub_results.append(config_result)
            details["config_exists"] = config_result.status == OperationResult.SUCCESS

            # If no config file, return early with guidance
            if config_result.status == ValidationSeverity.ERROR:
                return DiagnosticResult(
                    category=self.category,
                    status=ValidationSeverity.ERROR,
                    message="Agent sources not configured",
                    details=details,
                    fix_command="claude-mpm agent-source add https://github.com/bobmatnyc/claude-mpm-agents",
                    fix_description="Add default system repository",
                    sub_results=sub_results if self.verbose else [],
                )

            # Check 2: Configuration is valid YAML
            config_valid_result = self._check_config_valid()
            sub_results.append(config_valid_result)
            if config_valid_result.status == ValidationSeverity.ERROR:
                return DiagnosticResult(
                    category=self.category,
                    status=ValidationSeverity.ERROR,
                    message="Invalid configuration file",
                    details=details,
                    fix_command="claude-mpm config validate",
                    fix_description="Validate and fix configuration",
                    sub_results=sub_results if self.verbose else [],
                )

            # Load configuration for remaining checks
            from ....config.agent_sources import AgentSourceConfiguration

            config = AgentSourceConfiguration.load()

            # Check 3: At least one source configured
            sources_result = self._check_sources_configured(config)
            sub_results.append(sources_result)
            details["total_sources"] = len(config.repositories) + (
                0 if config.disable_system_repo else 1
            )
            details["enabled_sources"] = len(config.get_enabled_repositories())

            # Check 4: System repository accessible (if enabled)
            system_repo_result = self._check_system_repo_accessible(config)
            if system_repo_result:
                sub_results.append(system_repo_result)

            # Check 5: Enabled sources reachable
            reachability_result = self._check_sources_reachable(config)
            sub_results.append(reachability_result)
            details["reachable_sources"] = reachability_result.details.get(
                "reachable_count", 0
            )
            details["unreachable_sources"] = reachability_result.details.get(
                "unreachable_count", 0
            )

            # Check 6: Cache directory healthy
            cache_result = self._check_cache_directory()
            sub_results.append(cache_result)
            details["cache_healthy"] = cache_result.status == OperationResult.SUCCESS

            # Check 7: Priority conflicts
            priority_result = self._check_priority_conflicts(config)
            if priority_result:
                sub_results.append(priority_result)
                details["priority_conflicts"] = priority_result.details.get(
                    "conflict_count", 0
                )

            # Check 8: Agents discovered
            discovery_result = self._check_agents_discovered(config)
            sub_results.append(discovery_result)
            details["agents_discovered"] = discovery_result.details.get(
                "total_agents", 0
            )

            # Determine overall status
            error_results = [
                r for r in sub_results if r.status == ValidationSeverity.ERROR
            ]
            warning_results = [
                r for r in sub_results if r.status == ValidationSeverity.WARNING
            ]

            if error_results:
                status = ValidationSeverity.ERROR
                message = f"Agent sources have {len(error_results)} critical issue(s)"
                fix_command = None
                fix_description = None
            elif warning_results:
                status = ValidationSeverity.WARNING
                message = f"Agent sources have {len(warning_results)} minor issue(s)"
                fix_command = "claude-mpm agent-source update"
                fix_description = "Update all sources to refresh cache"
            else:
                status = OperationResult.SUCCESS
                enabled_count = details["enabled_sources"]
                agents_count = details["agents_discovered"]
                message = f"All checks passed ({enabled_count} source(s), {agents_count} agent(s))"
                fix_command = None
                fix_description = None

            return DiagnosticResult(
                category=self.category,
                status=status,
                message=message,
                details=details,
                fix_command=fix_command,
                fix_description=fix_description,
                sub_results=sub_results if self.verbose else [],
            )

        except Exception as e:
            logger.exception("Agent sources check failed")
            return DiagnosticResult(
                category=self.category,
                status=ValidationSeverity.ERROR,
                message=f"Agent sources check failed: {e!s}",
                details={"error": str(e)},
            )

    def _check_config_file(self) -> DiagnosticResult:
        """Check if configuration file exists."""
        config_path = Path.home() / ".claude-mpm" / "config" / "agent_sources.yaml"

        if not config_path.exists():
            return DiagnosticResult(
                category="Configuration File",
                status=ValidationSeverity.ERROR,
                message=f"Configuration file not found: {config_path}",
                details={"path": str(config_path)},
                fix_command="claude-mpm agent-source add https://github.com/bobmatnyc/claude-mpm-agents",
                fix_description="Create configuration and add default repository",
            )

        return DiagnosticResult(
            category="Configuration File",
            status=OperationResult.SUCCESS,
            message=f"Found at {config_path}",
            details={"path": str(config_path)},
        )

    def _check_config_valid(self) -> DiagnosticResult:
        """Check if configuration is valid YAML."""
        config_path = Path.home() / ".claude-mpm" / "config" / "agent_sources.yaml"

        try:
            import yaml

            with open(config_path) as f:
                data = yaml.safe_load(f)

            if not data:
                return DiagnosticResult(
                    category="Configuration Validity",
                    status=ValidationSeverity.WARNING,
                    message="Configuration file is empty",
                    details={"path": str(config_path)},
                )

            # Basic structure validation
            if not isinstance(data, dict):
                return DiagnosticResult(
                    category="Configuration Validity",
                    status=ValidationSeverity.ERROR,
                    message="Configuration must be YAML dictionary",
                    details={"path": str(config_path), "type": str(type(data))},
                )

            return DiagnosticResult(
                category="Configuration Validity",
                status=OperationResult.SUCCESS,
                message="Configuration is valid YAML",
                details={"path": str(config_path)},
            )

        except yaml.YAMLError as e:
            return DiagnosticResult(
                category="Configuration Validity",
                status=ValidationSeverity.ERROR,
                message=f"Invalid YAML: {e!s}",
                details={"path": str(config_path), "error": str(e)},
                fix_command=f"cat {config_path}",
                fix_description="Check YAML syntax errors",
            )
        except Exception as e:
            return DiagnosticResult(
                category="Configuration Validity",
                status=ValidationSeverity.ERROR,
                message=f"Failed to read configuration: {e!s}",
                details={"path": str(config_path), "error": str(e)},
            )

    def _check_sources_configured(self, config) -> DiagnosticResult:
        """Check if at least one source is configured.

        Args:
            config: AgentSourceConfiguration instance
        """
        total_sources = len(config.repositories)
        if not config.disable_system_repo:
            total_sources += 1  # Count system repo

        if total_sources == 0:
            return DiagnosticResult(
                category="Sources Configured",
                status=ValidationSeverity.WARNING,
                message="No agent sources configured",
                details={"total": 0, "enabled": 0},
                fix_command="claude-mpm agent-source add https://github.com/bobmatnyc/claude-mpm-agents",
                fix_description="Add default agent repository",
            )

        enabled_sources = len(config.get_enabled_repositories())

        if enabled_sources == 0:
            return DiagnosticResult(
                category="Sources Configured",
                status=ValidationSeverity.WARNING,
                message=f"{total_sources} source(s) configured but all disabled",
                details={"total": total_sources, "enabled": 0},
                fix_command="claude-mpm source enable <source-id>",
                fix_description="Enable at least one source",
            )

        return DiagnosticResult(
            category="Sources Configured",
            status=OperationResult.SUCCESS,
            message=f"{enabled_sources} enabled source(s) ({total_sources} total)",
            details={"total": total_sources, "enabled": enabled_sources},
        )

    def _check_system_repo_accessible(self, config) -> Optional[DiagnosticResult]:
        """Check if system repository is accessible.

        Args:
            config: AgentSourceConfiguration instance
        """
        system_repo = config.get_system_repo()

        if not system_repo:
            # System repo disabled, skip check
            return None

        return self._check_repo_accessible(
            system_repo.url, "System Repository", is_system=True
        )

    def _check_sources_reachable(self, config) -> DiagnosticResult:
        """Check if enabled sources are reachable.

        Args:
            config: AgentSourceConfiguration instance
        """
        repos = config.get_enabled_repositories()

        if not repos:
            return DiagnosticResult(
                category="Source Reachability",
                status=OperationResult.SKIPPED,
                message="No enabled sources to check",
                details={"reachable_count": 0, "unreachable_count": 0},
            )

        reachable = []
        unreachable = []
        details: Dict[str, str] = {}

        for repo in repos:
            result = self._check_repo_accessible(repo.url, repo.identifier)
            if result.status == OperationResult.SUCCESS:
                reachable.append(repo.identifier)
                details[repo.identifier] = "reachable"
            else:
                unreachable.append(repo.identifier)
                details[repo.identifier] = result.message

        if len(unreachable) == len(repos):
            # All sources unreachable
            return DiagnosticResult(
                category="Source Reachability",
                status=ValidationSeverity.ERROR,
                message=f"All {len(repos)} source(s) unreachable",
                details={
                    "reachable_count": 0,
                    "unreachable_count": len(unreachable),
                    "sources": details,
                },
                fix_command="claude-mpm agent-source list",
                fix_description="Check source URLs and network connectivity",
            )
        if unreachable:
            # Some sources unreachable
            return DiagnosticResult(
                category="Source Reachability",
                status=ValidationSeverity.WARNING,
                message=f"{len(unreachable)}/{len(repos)} source(s) unreachable",
                details={
                    "reachable_count": len(reachable),
                    "unreachable_count": len(unreachable),
                    "sources": details,
                    "unreachable_sources": unreachable,
                },
            )
        # All sources reachable
        return DiagnosticResult(
            category="Source Reachability",
            status=OperationResult.SUCCESS,
            message=f"All {len(repos)} source(s) reachable",
            details={
                "reachable_count": len(reachable),
                "unreachable_count": 0,
                "sources": details,
            },
        )

    def _check_repo_accessible(
        self, url: str, identifier: str, is_system: bool = False
    ) -> DiagnosticResult:
        """Check if a repository is accessible via HTTP."""
        try:
            import urllib.request
            from urllib.error import HTTPError, URLError

            # Convert git URL to HTTPS if needed
            if url.startswith("git@github.com:"):
                url = url.replace("git@github.com:", "https://github.com/")
            if url.endswith(".git"):
                url = url[:-4]

            # Try to fetch repository (use HEAD request to be lightweight)
            req = urllib.request.Request(url, method="HEAD")
            req.add_header("User-Agent", "claude-mpm-doctor/1.0")

            with urllib.request.urlopen(req, timeout=5) as response:
                status = response.status

            if status == 200:
                return DiagnosticResult(
                    category=identifier,
                    status=OperationResult.SUCCESS,
                    message="Accessible",
                    details={"url": url, "status": status},
                )
            return DiagnosticResult(
                category=identifier,
                status=ValidationSeverity.WARNING,
                message=f"HTTP {status}",
                details={"url": url, "status": status},
            )

        except HTTPError as e:
            return DiagnosticResult(
                category=identifier,
                status=ValidationSeverity.WARNING,
                message=f"HTTP {e.code}",
                details={"url": url, "status": e.code, "error": str(e)},
            )
        except URLError as e:
            return DiagnosticResult(
                category=identifier,
                status=ValidationSeverity.WARNING,
                message=f"Network error: {e.reason}",
                details={"url": url, "error": str(e.reason)},
            )
        except Exception as e:
            return DiagnosticResult(
                category=identifier,
                status=ValidationSeverity.WARNING,
                message=f"Check failed: {e!s}",
                details={"url": url, "error": str(e)},
            )

    def _check_cache_directory(self) -> DiagnosticResult:
        """Check cache directory health."""
        cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"

        if not cache_dir.exists():
            return DiagnosticResult(
                category="Cache Directory",
                status=ValidationSeverity.WARNING,
                message=f"Cache directory does not exist: {cache_dir}",
                details={"path": str(cache_dir), "exists": False},
                fix_command="claude-mpm agent-source update",
                fix_description="Create cache directory and update sources",
            )

        # Check if writable
        if not cache_dir.is_dir():
            return DiagnosticResult(
                category="Cache Directory",
                status=ValidationSeverity.ERROR,
                message=f"Cache path exists but is not a directory: {cache_dir}",
                details={"path": str(cache_dir), "is_dir": False},
            )

        # Test write access
        try:
            test_file = cache_dir / ".write_test"
            test_file.touch()
            test_file.unlink()

            return DiagnosticResult(
                category="Cache Directory",
                status=OperationResult.SUCCESS,
                message=f"Cache directory healthy: {cache_dir}",
                details={"path": str(cache_dir), "writable": True},
            )

        except Exception as e:
            return DiagnosticResult(
                category="Cache Directory",
                status=ValidationSeverity.ERROR,
                message=f"Cache directory not writable: {e!s}",
                details={"path": str(cache_dir), "writable": False, "error": str(e)},
                fix_command=f"chmod -R u+w {cache_dir}",
                fix_description="Fix cache directory permissions",
            )

    def _check_priority_conflicts(self, config) -> Optional[DiagnosticResult]:
        """Check for priority conflicts.

        Args:
            config: AgentSourceConfiguration instance
        """
        repos = config.get_enabled_repositories()

        if len(repos) < 2:
            # No conflicts possible with 0-1 repos
            return None

        # Group repos by priority
        priority_groups: Dict[int, List[str]] = {}
        for repo in repos:
            priority = repo.priority
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(repo.identifier)

        # Find conflicts (multiple repos with same priority)
        conflicts = {p: ids for p, ids in priority_groups.items() if len(ids) > 1}

        if not conflicts:
            return DiagnosticResult(
                category="Priority Conflicts",
                status=OperationResult.SUCCESS,
                message="No priority conflicts detected",
                details={"conflict_count": 0},
            )

        conflict_details = []
        for priority, identifiers in conflicts.items():
            conflict_details.append(f"Priority {priority}: {', '.join(identifiers)}")

        return DiagnosticResult(
            category="Priority Conflicts",
            status=ValidationSeverity.INFO,
            message=f"{len(conflicts)} priority conflict(s) detected",
            details={
                "conflict_count": len(conflicts),
                "conflicts": conflict_details,
            },
            fix_description="Consider assigning unique priorities to avoid ambiguous resolution",
        )

    def _check_agents_discovered(self, config) -> DiagnosticResult:
        """Check if agents can be discovered from sources.

        Args:
            config: AgentSourceConfiguration instance
        """
        try:
            from ....services.agents.single_tier_deployment_service import (
                SingleTierDeploymentService,
            )

            deployment_dir = Path.home() / ".claude" / "agents"
            service = SingleTierDeploymentService(
                config=config, deployment_dir=deployment_dir
            )

            available_agents = service.list_available_agents()

            if not available_agents:
                return DiagnosticResult(
                    category="Agent Discovery",
                    status=ValidationSeverity.WARNING,
                    message="No agents discovered from configured sources",
                    details={"total_agents": 0, "agents_by_source": {}},
                    fix_command="claude-mpm agent-source update",
                    fix_description="Update sources to discover agents",
                )

            # Group agents by source
            agents_by_source: Dict[str, int] = {}
            for agent in available_agents:
                source = agent.get("source", "unknown")
                agents_by_source[source] = agents_by_source.get(source, 0) + 1

            return DiagnosticResult(
                category="Agent Discovery",
                status=OperationResult.SUCCESS,
                message=f"Discovered {len(available_agents)} agent(s)",
                details={
                    "total_agents": len(available_agents),
                    "agents_by_source": agents_by_source,
                    "agent_names": [a.get("name", "unknown") for a in available_agents],
                },
            )

        except Exception as e:
            logger.exception("Failed to discover agents")
            return DiagnosticResult(
                category="Agent Discovery",
                status=ValidationSeverity.WARNING,
                message=f"Agent discovery failed: {e!s}",
                details={"error": str(e)},
            )
