"""
Check agent deployment and health.

WHY: Verify that agents are properly deployed, up-to-date, and functioning correctly.
"""

from pathlib import Path

from ..models import DiagnosticResult, DiagnosticStatus
from .base_check import BaseDiagnosticCheck


class AgentCheck(BaseDiagnosticCheck):
    """Check agent deployment and configuration."""

    @property
    def name(self) -> str:
        return "agent_check"

    @property
    def category(self) -> str:
        return "Agents"

    def run(self) -> DiagnosticResult:
        """Run agent diagnostics."""
        try:
            from ....services.agents.deployment.agent_discovery_service import (
                AgentDiscoveryService,
            )

            sub_results = []
            details = {}

            # Get available agents
            # AgentDiscoveryService requires templates_dir parameter
            templates_dir = Path(__file__).parents[3] / "agents" / "templates"
            discovery = AgentDiscoveryService(templates_dir)
            available_agents = discovery.list_available_agents()
            details["available_count"] = len(available_agents)
            details["available_agents"] = [
                a.get("name", "unknown") for a in available_agents
            ]

            # Check deployed agents
            deployed_result = self._check_deployed_agents()
            sub_results.append(deployed_result)
            details["deployed_count"] = deployed_result.details.get("count", 0)

            # Check agent versions
            version_result = self._check_agent_versions()
            sub_results.append(version_result)
            details["outdated_agents"] = version_result.details.get("outdated", [])

            # Validate agent configurations
            validation_result = self._validate_agents()
            sub_results.append(validation_result)

            # Check for common agent issues
            issues_result = self._check_common_issues()
            sub_results.append(issues_result)

            # Determine overall status
            deployed_count = details["deployed_count"]
            available_count = details["available_count"]

            if deployed_count == 0:
                status = DiagnosticStatus.ERROR
                message = f"No agents deployed (0/{available_count} available)"
                fix_command = "claude-mpm agents deploy"
                fix_description = "Deploy all available agents"
            elif deployed_count < available_count:
                status = DiagnosticStatus.WARNING
                message = f"{deployed_count}/{available_count} agents deployed"
                fix_command = "claude-mpm agents deploy"
                fix_description = (
                    f"Deploy remaining {available_count - deployed_count} agents"
                )
            elif any(r.status == DiagnosticStatus.ERROR for r in sub_results):
                status = DiagnosticStatus.ERROR
                message = "Agents have critical issues"
                fix_command = None
                fix_description = None
            elif any(r.status == DiagnosticStatus.WARNING for r in sub_results):
                status = DiagnosticStatus.WARNING
                message = "Agents have minor issues"
                fix_command = None
                fix_description = None
            else:
                status = DiagnosticStatus.OK
                message = f"All {deployed_count} agents properly deployed"
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
            return DiagnosticResult(
                category=self.category,
                status=DiagnosticStatus.ERROR,
                message=f"Agent check failed: {e!s}",
                details={"error": str(e)},
            )

    def _check_deployed_agents(self) -> DiagnosticResult:
        """Check deployed agents in both project and user directories."""
        import os

        # Check project-level agents first (preferred in development)
        project_agents_dir = Path(os.getcwd()) / ".claude" / "agents"
        user_agents_dir = Path.home() / ".claude" / "agents"

        # Determine which directory to check
        if project_agents_dir.exists():
            agents_dir = project_agents_dir
            location = "project"
        elif user_agents_dir.exists():
            agents_dir = user_agents_dir
            location = "user"
        else:
            # Neither exists, default to user directory for error message
            return DiagnosticResult(
                category="Deployed Agents",
                status=DiagnosticStatus.ERROR,
                message="No agents directory found (checked project and user)",
                details={
                    "project_path": str(project_agents_dir),
                    "user_path": str(user_agents_dir),
                    "count": 0,
                },
                fix_command="claude-mpm agents deploy",
                fix_description="Create agents directory and deploy agents",
            )

        # Count deployed agent files
        agent_files = list(agents_dir.glob("*.md"))

        if not agent_files:
            return DiagnosticResult(
                category="Deployed Agents",
                status=DiagnosticStatus.ERROR,
                message=f"No agents deployed in {location} directory",
                details={"path": str(agents_dir), "location": location, "count": 0},
                fix_command="claude-mpm agents deploy",
                fix_description="Deploy available agents",
            )

        # Check for required core agents
        core_agents = ["research.md", "engineer.md", "qa.md", "documentation.md"]
        deployed_names = [f.name for f in agent_files]
        missing_core = [a for a in core_agents if a not in deployed_names]

        if missing_core:
            return DiagnosticResult(
                category="Deployed Agents",
                status=DiagnosticStatus.WARNING,
                message=f"Missing core agents in {location}: {', '.join(missing_core)}",
                details={
                    "path": str(agents_dir),
                    "location": location,
                    "count": len(agent_files),
                    "deployed": deployed_names,
                    "missing_core": missing_core,
                },
                fix_command="claude-mpm agents deploy",
                fix_description="Deploy missing core agents",
            )

        return DiagnosticResult(
            category="Deployed Agents",
            status=DiagnosticStatus.OK,
            message=f"{len(agent_files)} agents deployed ({location} level)",
            details={
                "path": str(agents_dir),
                "location": location,
                "count": len(agent_files),
                "deployed": deployed_names,
            },
        )

    def _check_agent_versions(self) -> DiagnosticResult:
        """Check if deployed agents are up-to-date."""
        try:
            import os

            from ....services.agents.deployment.agent_version_manager import (
                AgentVersionManager,
            )

            version_manager = AgentVersionManager()

            # Check both project and user directories
            project_agents_dir = Path(os.getcwd()) / ".claude" / "agents"
            user_agents_dir = Path.home() / ".claude" / "agents"

            if project_agents_dir.exists():
                agents_dir = project_agents_dir
            elif user_agents_dir.exists():
                agents_dir = user_agents_dir
            else:
                return DiagnosticResult(
                    category="Agent Versions",
                    status=DiagnosticStatus.SKIPPED,
                    message="No agents to check",
                    details={},
                )

            outdated = []
            checked = 0

            for agent_file in agents_dir.glob("*.md"):
                checked += 1
                agent_name = agent_file.stem

                # Check if agent needs update (simplified check)
                if version_manager.needs_update(agent_name):
                    outdated.append(agent_name)

            if outdated:
                return DiagnosticResult(
                    category="Agent Versions",
                    status=DiagnosticStatus.WARNING,
                    message=f"{len(outdated)} agent(s) outdated",
                    details={"outdated": outdated, "checked": checked},
                    fix_command="claude-mpm agents update",
                    fix_description="Update agents to latest versions",
                )

            if checked == 0:
                return DiagnosticResult(
                    category="Agent Versions",
                    status=DiagnosticStatus.WARNING,
                    message="No agents to check",
                    details={"checked": 0},
                )

            return DiagnosticResult(
                category="Agent Versions",
                status=DiagnosticStatus.OK,
                message=f"All {checked} agents up-to-date",
                details={"checked": checked},
            )

        except Exception as e:
            return DiagnosticResult(
                category="Agent Versions",
                status=DiagnosticStatus.WARNING,
                message=f"Could not check versions: {e!s}",
                details={"error": str(e)},
            )

    def _validate_agents(self) -> DiagnosticResult:
        """Validate agent configurations."""
        try:
            import os

            from ....services.agents.deployment.agent_validator import AgentValidator

            AgentValidator()

            # Check both project and user directories
            project_agents_dir = Path(os.getcwd()) / ".claude" / "agents"
            user_agents_dir = Path.home() / ".claude" / "agents"

            if project_agents_dir.exists():
                agents_dir = project_agents_dir
            elif user_agents_dir.exists():
                agents_dir = user_agents_dir
            else:
                return DiagnosticResult(
                    category="Agent Validation",
                    status=DiagnosticStatus.SKIPPED,
                    message="No agents to validate",
                    details={},
                )

            invalid = []
            validated = 0

            for agent_file in agents_dir.glob("*.md"):
                validated += 1

                # Basic validation
                try:
                    with open(agent_file) as f:
                        content = f.read()

                        # Check for required sections
                        if "## Core Identity" not in content:
                            invalid.append(f"{agent_file.stem}: missing Core Identity")
                        elif len(content) < 100:
                            invalid.append(f"{agent_file.stem}: file too small")

                except Exception as e:
                    invalid.append(f"{agent_file.stem}: {e!s}")

            if invalid:
                return DiagnosticResult(
                    category="Agent Validation",
                    status=DiagnosticStatus.WARNING,
                    message=f"{len(invalid)} validation issue(s)",
                    details={"issues": invalid, "validated": validated},
                )

            return DiagnosticResult(
                category="Agent Validation",
                status=DiagnosticStatus.OK,
                message=f"All {validated} agents valid",
                details={"validated": validated},
            )

        except Exception as e:
            return DiagnosticResult(
                category="Agent Validation",
                status=DiagnosticStatus.WARNING,
                message=f"Validation failed: {e!s}",
                details={"error": str(e)},
            )

    def _check_common_issues(self) -> DiagnosticResult:
        """Check for common agent-related issues."""
        import os

        issues = []

        # Check both project and user directories
        project_agents_dir = Path(os.getcwd()) / ".claude" / "agents"
        user_agents_dir = Path.home() / ".claude" / "agents"

        if project_agents_dir.exists():
            agents_dir = project_agents_dir
        elif user_agents_dir.exists():
            agents_dir = user_agents_dir
        else:
            agents_dir = None

        # Check for duplicate agents
        if agents_dir and agents_dir.exists():
            agent_names = {}
            for agent_file in agents_dir.glob("*.md"):
                name = agent_file.stem.lower()
                if name in agent_names:
                    issues.append(f"Duplicate agent: {agent_file.stem}")
                else:
                    agent_names[name] = agent_file

        # Check permissions
        if agents_dir and agents_dir.exists():
            if not os.access(agents_dir, os.R_OK):
                issues.append("Agents directory not readable")
            if not os.access(agents_dir, os.W_OK):
                issues.append("Agents directory not writable")

        if issues:
            return DiagnosticResult(
                category="Common Issues",
                status=DiagnosticStatus.WARNING,
                message=f"{len(issues)} issue(s) found",
                details={"issues": issues},
            )

        return DiagnosticResult(
            category="Common Issues",
            status=DiagnosticStatus.OK,
            message="No common issues detected",
            details={},
        )
