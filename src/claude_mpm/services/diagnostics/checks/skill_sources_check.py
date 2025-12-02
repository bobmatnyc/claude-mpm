"""
Check skill sources configuration and health.

WHY: Verify that the single-tier Git-based skill system is properly configured,
sources are accessible, and skills are discoverable from configured repositories.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from ....core.enums import OperationResult, ValidationSeverity
from ..models import DiagnosticResult
from .base_check import BaseDiagnosticCheck

logger = logging.getLogger(__name__)


class SkillSourcesCheck(BaseDiagnosticCheck):
    """Check skill sources configuration and health.

    Verifies:
    - Configuration file exists and is valid YAML
    - At least one source is configured
    - Enabled sources are accessible (HTTP 200)
    - Cache directory is healthy and writable
    - Priority conflicts are identified
    - Skills can be discovered from sources

    WHY: The single-tier system relies on Git sources being properly configured
    and accessible. This check ensures the skill deployment pipeline is healthy.
    """

    @property
    def name(self) -> str:
        return "skill_sources_check"

    @property
    def category(self) -> str:
        return "Skill Sources"

    def should_run(self) -> bool:
        """Check should run if single-tier system is in use.

        Returns:
            True if skill sources configuration exists or could exist
        """
        # Always run - we want to check if configuration should be created
        return True

    def run(self) -> DiagnosticResult:
        """Run skill sources diagnostics."""
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
                    message="Skill sources not configured",
                    details=details,
                    fix_command="claude-mpm skill-source add https://github.com/bobmatnyc/claude-mpm-skills",
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
                    fix_command="# Check YAML syntax and fix errors",
                    fix_description="Validate and fix configuration",
                    sub_results=sub_results if self.verbose else [],
                )

            # Load configuration for remaining checks
            from ....config.skill_sources import SkillSourceConfiguration

            config = SkillSourceConfiguration()
            sources = config.load()

            # Check 3: At least one source configured
            sources_result = self._check_sources_configured(sources)
            sub_results.append(sources_result)
            details["total_sources"] = len(sources)
            details["enabled_sources"] = len([s for s in sources if s.enabled])

            # Check 4: System repository accessible (if enabled)
            system_repo_result = self._check_system_repo_accessible(sources)
            if system_repo_result:
                sub_results.append(system_repo_result)

            # Check 5: Enabled sources reachable
            reachability_result = self._check_sources_reachable(sources)
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
            priority_result = self._check_priority_conflicts(sources)
            if priority_result:
                sub_results.append(priority_result)
                details["priority_conflicts"] = priority_result.details.get(
                    "conflict_count", 0
                )

            # Check 8: Skills discovered
            discovery_result = self._check_skills_discovered(config)
            sub_results.append(discovery_result)
            details["skills_discovered"] = discovery_result.details.get(
                "total_skills", 0
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
                message = f"Skill sources have {len(error_results)} critical issue(s)"
                fix_command = None
                fix_description = None
            elif warning_results:
                status = ValidationSeverity.WARNING
                message = f"Skill sources have {len(warning_results)} minor issue(s)"
                fix_command = "claude-mpm skill-source update"
                fix_description = "Update all sources to refresh cache"
            else:
                status = OperationResult.SUCCESS
                enabled_count = details["enabled_sources"]
                skills_count = details["skills_discovered"]
                message = f"All checks passed ({enabled_count} source(s), {skills_count} skill(s))"
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
            logger.exception("Skill sources check failed")
            return DiagnosticResult(
                category=self.category,
                status=ValidationSeverity.ERROR,
                message=f"Skill sources check failed: {e!s}",
                details={"error": str(e)},
            )

    def _check_config_file(self) -> DiagnosticResult:
        """Check if configuration file exists."""
        config_path = Path.home() / ".claude-mpm" / "config" / "skill_sources.yaml"

        if not config_path.exists():
            return DiagnosticResult(
                category="Configuration File",
                status=ValidationSeverity.ERROR,
                message=f"Configuration file not found: {config_path}",
                details={"path": str(config_path)},
                fix_command="claude-mpm skill-source add https://github.com/bobmatnyc/claude-mpm-skills",
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
        config_path = Path.home() / ".claude-mpm" / "config" / "skill_sources.yaml"

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

    def _check_sources_configured(self, sources: List) -> DiagnosticResult:
        """Check if at least one source is configured.

        Args:
            sources: List of SkillSource instances
        """
        total_sources = len(sources)

        if total_sources == 0:
            return DiagnosticResult(
                category="Sources Configured",
                status=ValidationSeverity.WARNING,
                message="No skill sources configured",
                details={"total": 0, "enabled": 0},
                fix_command="claude-mpm skill-source add https://github.com/bobmatnyc/claude-mpm-skills",
                fix_description="Add default skill repository",
            )

        enabled_sources = len([s for s in sources if s.enabled])

        if enabled_sources == 0:
            return DiagnosticResult(
                category="Sources Configured",
                status=ValidationSeverity.WARNING,
                message=f"{total_sources} source(s) configured but all disabled",
                details={"total": total_sources, "enabled": 0},
                fix_command="claude-mpm skill-source enable <source-id>",
                fix_description="Enable at least one source",
            )

        return DiagnosticResult(
            category="Sources Configured",
            status=OperationResult.SUCCESS,
            message=f"{enabled_sources} enabled source(s) ({total_sources} total)",
            details={"total": total_sources, "enabled": enabled_sources},
        )

    def _check_system_repo_accessible(
        self, sources: List
    ) -> Optional[DiagnosticResult]:
        """Check if system repository is accessible.

        Args:
            sources: List of SkillSource instances
        """
        # Find system repository (priority 0)
        system_sources = [s for s in sources if s.priority == 0 and s.enabled]

        if not system_sources:
            # No system repo or disabled, skip check
            return None

        system_repo = system_sources[0]
        return self._check_repo_accessible(
            system_repo.url, "System Repository", is_system=True
        )

    def _check_sources_reachable(self, sources: List) -> DiagnosticResult:
        """Check if enabled sources are reachable.

        Args:
            sources: List of SkillSource instances
        """
        enabled_sources = [s for s in sources if s.enabled]

        if not enabled_sources:
            return DiagnosticResult(
                category="Source Reachability",
                status=OperationResult.SKIPPED,
                message="No enabled sources to check",
                details={"reachable_count": 0, "unreachable_count": 0},
            )

        reachable = []
        unreachable = []
        details: Dict[str, str] = {}

        for source in enabled_sources:
            result = self._check_repo_accessible(source.url, source.id)
            if result.status == OperationResult.SUCCESS:
                reachable.append(source.id)
                details[source.id] = "reachable"
            else:
                unreachable.append(source.id)
                details[source.id] = result.message

        if len(unreachable) == len(enabled_sources):
            # All sources unreachable
            return DiagnosticResult(
                category="Source Reachability",
                status=ValidationSeverity.ERROR,
                message=f"All {len(enabled_sources)} source(s) unreachable",
                details={
                    "reachable_count": 0,
                    "unreachable_count": len(unreachable),
                    "sources": details,
                },
                fix_command="claude-mpm skill-source list",
                fix_description="Check source URLs and network connectivity",
            )
        if unreachable:
            # Some sources unreachable
            return DiagnosticResult(
                category="Source Reachability",
                status=ValidationSeverity.WARNING,
                message=f"{len(unreachable)}/{len(enabled_sources)} source(s) unreachable",
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
            message=f"All {len(enabled_sources)} source(s) reachable",
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
        cache_dir = Path.home() / ".claude-mpm" / "cache" / "skills"

        if not cache_dir.exists():
            return DiagnosticResult(
                category="Cache Directory",
                status=ValidationSeverity.WARNING,
                message=f"Cache directory does not exist: {cache_dir}",
                details={"path": str(cache_dir), "exists": False},
                fix_command="claude-mpm skill-source update",
                fix_description="Create cache directory and sync sources",
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

    def _check_priority_conflicts(self, sources: List) -> Optional[DiagnosticResult]:
        """Check for priority conflicts.

        Args:
            sources: List of SkillSource instances
        """
        enabled_sources = [s for s in sources if s.enabled]

        if len(enabled_sources) < 2:
            # No conflicts possible with 0-1 sources
            return None

        # Group sources by priority
        priority_groups: Dict[int, List[str]] = {}
        for source in enabled_sources:
            priority = source.priority
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(source.id)

        # Find conflicts (multiple sources with same priority)
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

    def _check_skills_discovered(self, config) -> DiagnosticResult:
        """Check if skills can be discovered from sources.

        Args:
            config: SkillSourceConfiguration instance
        """
        try:
            from ....services.skills.git_skill_source_manager import (
                GitSkillSourceManager,
            )

            cache_dir = Path.home() / ".claude-mpm" / "cache" / "skills"
            manager = GitSkillSourceManager(config, cache_dir)

            # Check if cache has any content
            if not cache_dir.exists() or not list(cache_dir.glob("*")):
                return DiagnosticResult(
                    category="Skill Discovery",
                    status=ValidationSeverity.INFO,
                    message="No cached skills (run: claude-mpm skill-source update)",
                    details={"total_skills": 0, "skills_by_source": {}},
                    fix_command="claude-mpm skill-source update",
                    fix_description="Sync sources to discover skills",
                )

            available_skills = manager.get_all_skills()

            if not available_skills:
                return DiagnosticResult(
                    category="Skill Discovery",
                    status=ValidationSeverity.WARNING,
                    message="No skills discovered from configured sources",
                    details={"total_skills": 0, "skills_by_source": {}},
                    fix_command="claude-mpm skill-source update",
                    fix_description="Sync sources to discover skills",
                )

            # Group skills by source
            skills_by_source: Dict[str, int] = {}
            for skill in available_skills:
                source = skill.get("source_id", "unknown")
                skills_by_source[source] = skills_by_source.get(source, 0) + 1

            return DiagnosticResult(
                category="Skill Discovery",
                status=OperationResult.SUCCESS,
                message=f"Discovered {len(available_skills)} skill(s)",
                details={
                    "total_skills": len(available_skills),
                    "skills_by_source": skills_by_source,
                    "skill_names": [s.get("name", "unknown") for s in available_skills],
                },
            )

        except Exception as e:
            logger.exception("Failed to discover skills")
            return DiagnosticResult(
                category="Skill Discovery",
                status=ValidationSeverity.WARNING,
                message=f"Skill discovery failed: {e!s}",
                details={"error": str(e)},
            )
