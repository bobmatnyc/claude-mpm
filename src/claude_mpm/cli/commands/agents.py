"""
Agents command implementation for claude-mpm.

WHY: This module manages Claude Code native agents, including listing, deploying,
and cleaning agent deployments. Refactored to use shared utilities for consistency.

DESIGN DECISIONS:
- Use AgentCommand base class for consistent CLI patterns
- Leverage shared utilities for argument parsing and output formatting
- Maintain backward compatibility with existing functionality
- Support multiple output formats (json, yaml, table, text)
"""

import json
from pathlib import Path

from ...constants import AgentCommands
from ...services.cli.agent_cleanup_service import AgentCleanupService
from ...services.cli.agent_dependency_service import AgentDependencyService
from ...services.cli.agent_listing_service import AgentListingService
from ...services.cli.agent_output_formatter import AgentOutputFormatter
from ...services.cli.agent_validation_service import AgentValidationService
from ..shared import (
    AgentCommand,
    CommandResult,
)
from ..utils import get_agent_versions_display


class AgentsCommand(AgentCommand):
    """Agent management command using shared utilities."""

    def __init__(self):
        super().__init__("agents")
        self._deployment_service = None
        self._listing_service = None
        self._validation_service = None
        self._dependency_service = None
        self._cleanup_service = None
        self._formatter = AgentOutputFormatter()

    @property
    def deployment_service(self):
        """Get deployment service instance (lazy loaded)."""
        if self._deployment_service is None:
            try:
                from ...services import AgentDeploymentService
                from ...services.agents.deployment.deployment_wrapper import (
                    DeploymentServiceWrapper,
                )

                base_service = AgentDeploymentService()
                self._deployment_service = DeploymentServiceWrapper(base_service)
            except ImportError:
                raise ImportError("Agent deployment service not available")
        return self._deployment_service

    @property
    def listing_service(self):
        """Get listing service instance (lazy loaded)."""
        if self._listing_service is None:
            self._listing_service = AgentListingService(
                deployment_service=self.deployment_service
            )
        return self._listing_service

    @property
    def validation_service(self):
        """Get validation service instance (lazy loaded)."""
        if self._validation_service is None:
            self._validation_service = AgentValidationService()
        return self._validation_service

    @property
    def dependency_service(self):
        """Get dependency service instance (lazy loaded)."""
        if self._dependency_service is None:
            self._dependency_service = AgentDependencyService()
        return self._dependency_service

    @property
    def cleanup_service(self):
        """Get cleanup service instance (lazy loaded)."""
        if self._cleanup_service is None:
            self._cleanup_service = AgentCleanupService(
                deployment_service=self.deployment_service
            )
        return self._cleanup_service

    def validate_args(self, args) -> str:
        """Validate command arguments."""
        # Most agent commands are optional, so basic validation
        return None

    def run(self, args) -> CommandResult:
        """Execute the agent command."""
        try:
            # Handle default case (no subcommand)
            if not hasattr(args, "agents_command") or not args.agents_command:
                return self._show_agent_versions(args)

            # Route to appropriate subcommand
            command_map = {
                AgentCommands.LIST.value: self._list_agents,
                AgentCommands.DEPLOY.value: lambda a: self._deploy_agents(
                    a, force=False
                ),
                AgentCommands.FORCE_DEPLOY.value: lambda a: self._deploy_agents(
                    a, force=True
                ),
                AgentCommands.CLEAN.value: self._clean_agents,
                AgentCommands.VIEW.value: self._view_agent,
                AgentCommands.FIX.value: self._fix_agents,
                "deps-check": self._check_agent_dependencies,
                "deps-install": self._install_agent_dependencies,
                "deps-list": self._list_agent_dependencies,
                "deps-fix": self._fix_agent_dependencies,
                "cleanup-orphaned": self._cleanup_orphaned_agents,
            }

            if args.agents_command in command_map:
                return command_map[args.agents_command](args)
            return CommandResult.error_result(
                f"Unknown agent command: {args.agents_command}"
            )

        except ImportError:
            self.logger.error("Agent deployment service not available")
            return CommandResult.error_result("Agent deployment service not available")
        except Exception as e:
            self.logger.error(f"Error managing agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error managing agents: {e}")

    def _show_agent_versions(self, args) -> CommandResult:
        """Show current agent versions as default action."""
        try:
            agent_versions = get_agent_versions_display()

            output_format = getattr(args, "format", "text")
            if output_format in ["json", "yaml"]:
                # Parse the agent versions display into structured data
                if agent_versions:
                    data = {"agent_versions": agent_versions, "has_agents": True}
                    formatted = (
                        self._formatter.format_as_json(data)
                        if output_format == "json"
                        else self._formatter.format_as_yaml(data)
                    )
                    print(formatted)
                    return CommandResult.success_result(
                        "Agent versions retrieved", data=data
                    )
                data = {
                    "agent_versions": None,
                    "has_agents": False,
                    "suggestion": "To deploy agents, run: claude-mpm --mpm:agents deploy",
                }
                formatted = (
                    self._formatter.format_as_json(data)
                    if output_format == "json"
                    else self._formatter.format_as_yaml(data)
                )
                print(formatted)
                return CommandResult.success_result(
                    "No deployed agents found", data=data
                )
            # Text output
            if agent_versions:
                print(agent_versions)
                return CommandResult.success_result("Agent versions displayed")
            print("No deployed agents found")
            print("\nTo deploy agents, run: claude-mpm --mpm:agents deploy")
            return CommandResult.success_result("No deployed agents found")

        except Exception as e:
            self.logger.error(f"Error getting agent versions: {e}", exc_info=True)
            return CommandResult.error_result(f"Error getting agent versions: {e}")

    def _list_agents(self, args) -> CommandResult:
        """List available or deployed agents."""
        try:
            output_format = getattr(args, "format", "text")

            if hasattr(args, "by_tier") and args.by_tier:
                return self._list_agents_by_tier(args)
            if getattr(args, "system", False):
                return self._list_system_agents(args)
            if getattr(args, "deployed", False):
                return self._list_deployed_agents(args)
            # Default: show usage
            usage_msg = "Use --system to list system agents, --deployed to list deployed agents, or --by-tier to group by precedence"

            if output_format in ["json", "yaml"]:
                return CommandResult.error_result(
                    "No list option specified",
                    data={
                        "usage": usage_msg,
                        "available_options": ["--system", "--deployed", "--by-tier"],
                    },
                )
            print(usage_msg)
            return CommandResult.error_result("No list option specified")

        except Exception as e:
            self.logger.error(f"Error listing agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error listing agents: {e}")

    def _list_system_agents(self, args) -> CommandResult:
        """List available agent templates."""
        try:
            verbose = getattr(args, "verbose", False)
            agents = self.listing_service.list_system_agents(verbose=verbose)

            output_format = getattr(args, "format", "text")
            quiet = getattr(args, "quiet", False)

            # Convert AgentInfo objects to dicts for formatter
            agents_data = [
                {
                    "name": agent.name,
                    "type": agent.type,
                    "path": agent.path,
                    "file": Path(agent.path).name if agent.path else "Unknown",
                    "description": agent.description,
                    "specializations": agent.specializations,
                    "version": agent.version,
                }
                for agent in agents
            ]

            formatted = self._formatter.format_agent_list(
                agents_data, output_format=output_format, verbose=verbose, quiet=quiet
            )
            print(formatted)

            return CommandResult.success_result(
                f"Listed {len(agents)} agent templates",
                data={"agents": agents_data, "count": len(agents)},
            )

        except Exception as e:
            self.logger.error(f"Error listing system agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error listing system agents: {e}")

    def _list_deployed_agents(self, args) -> CommandResult:
        """List deployed agents."""
        try:
            verbose = getattr(args, "verbose", False)
            agents, warnings = self.listing_service.list_deployed_agents(
                verbose=verbose
            )

            output_format = getattr(args, "format", "text")
            quiet = getattr(args, "quiet", False)

            # Convert AgentInfo objects to dicts for formatter
            agents_data = [
                {
                    "name": agent.name,
                    "type": agent.type,
                    "tier": agent.tier,
                    "path": agent.path,
                    "file": Path(agent.path).name if agent.path else "Unknown",
                    "description": agent.description,
                    "specializations": agent.specializations,
                    "version": agent.version,
                }
                for agent in agents
            ]

            # Format the agent list
            formatted = self._formatter.format_agent_list(
                agents_data, output_format=output_format, verbose=verbose, quiet=quiet
            )
            print(formatted)

            # Add warnings for text output
            if output_format == "text" and warnings:
                print("\nWarnings:")
                for warning in warnings:
                    print(f"  ⚠️  {warning}")

            return CommandResult.success_result(
                f"Listed {len(agents)} deployed agents",
                data={
                    "agents": agents_data,
                    "warnings": warnings,
                    "count": len(agents),
                },
            )

        except Exception as e:
            self.logger.error(f"Error listing deployed agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error listing deployed agents: {e}")

    def _list_agents_by_tier(self, args) -> CommandResult:
        """List agents grouped by tier/precedence."""
        try:
            tier_info = self.listing_service.list_agents_by_tier()
            output_format = getattr(args, "format", "text")

            # Convert to format expected by formatter
            agents_by_tier = {
                "project": [
                    {
                        "name": agent.name,
                        "type": agent.type,
                        "path": agent.path,
                        "active": agent.active,
                        "overridden_by": agent.overridden_by,
                    }
                    for agent in tier_info.project
                ],
                "user": [
                    {
                        "name": agent.name,
                        "type": agent.type,
                        "path": agent.path,
                        "active": agent.active,
                        "overridden_by": agent.overridden_by,
                    }
                    for agent in tier_info.user
                ],
                "system": [
                    {
                        "name": agent.name,
                        "type": agent.type,
                        "path": agent.path,
                        "active": agent.active,
                        "overridden_by": agent.overridden_by,
                    }
                    for agent in tier_info.system
                ],
                "summary": {
                    "total_count": tier_info.total_count,
                    "active_count": tier_info.active_count,
                    "project_count": len(tier_info.project),
                    "user_count": len(tier_info.user),
                    "system_count": len(tier_info.system),
                },
            }

            formatted = self._formatter.format_agents_by_tier(
                agents_by_tier, output_format=output_format
            )
            print(formatted)

            return CommandResult.success_result(
                "Agents listed by tier", data=agents_by_tier
            )

        except Exception as e:
            self.logger.error(f"Error listing agents by tier: {e}", exc_info=True)
            return CommandResult.error_result(f"Error listing agents by tier: {e}")

    def _deploy_agents(self, args, force=False) -> CommandResult:
        """Deploy both system and project agents."""
        try:
            # Deploy system agents
            system_result = self.deployment_service.deploy_system_agents(force=force)

            # Deploy project agents if they exist
            project_result = self.deployment_service.deploy_project_agents(force=force)

            # Combine results
            combined_result = {
                "deployed_count": system_result.get("deployed_count", 0)
                + project_result.get("deployed_count", 0),
                "deployed": system_result.get("deployed", [])
                + project_result.get("deployed", []),
                "updated_count": system_result.get("updated_count", 0)
                + project_result.get("updated_count", 0),
                "updated": system_result.get("updated", [])
                + project_result.get("updated", []),
                "skipped": system_result.get("skipped", [])
                + project_result.get("skipped", []),
                "errors": system_result.get("errors", [])
                + project_result.get("errors", []),
                "target_dir": system_result.get("target_dir")
                or project_result.get("target_dir"),
            }

            output_format = getattr(args, "format", "text")
            verbose = getattr(args, "verbose", False)

            formatted = self._formatter.format_deployment_result(
                combined_result, output_format=output_format, verbose=verbose
            )
            print(formatted)

            return CommandResult.success_result(
                f"Deployed {combined_result['deployed_count']} agents",
                data={
                    "system_agents": system_result,
                    "project_agents": project_result,
                    "total_deployed": combined_result["deployed_count"],
                },
            )

        except Exception as e:
            self.logger.error(f"Error deploying agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error deploying agents: {e}")

    def _clean_agents(self, args) -> CommandResult:
        """Clean deployed agents."""
        try:
            result = self.cleanup_service.clean_deployed_agents()

            output_format = getattr(args, "format", "text")
            dry_run = False  # Regular clean is not a dry run

            formatted = self._formatter.format_cleanup_result(
                result, output_format=output_format, dry_run=dry_run
            )
            print(formatted)

            cleaned_count = result.get("cleaned_count", 0)
            return CommandResult.success_result(
                f"Cleaned {cleaned_count} agents", data=result
            )

        except Exception as e:
            self.logger.error(f"Error cleaning agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error cleaning agents: {e}")

    def _view_agent(self, args) -> CommandResult:
        """View details of a specific agent."""
        try:
            agent_name = getattr(args, "agent_name", None)
            if not agent_name:
                return CommandResult.error_result(
                    "Agent name is required for view command"
                )

            # Get agent details from listing service
            agent_details = self.listing_service.get_agent_details(agent_name)

            if not agent_details:
                # Try to find the agent to provide helpful error message
                agent = self.listing_service.find_agent(agent_name)
                if not agent:
                    return CommandResult.error_result(f"Agent '{agent_name}' not found")
                return CommandResult.error_result(
                    f"Could not retrieve details for agent '{agent_name}'"
                )

            output_format = getattr(args, "format", "text")
            verbose = getattr(args, "verbose", False)

            formatted = self._formatter.format_agent_details(
                agent_details, output_format=output_format, verbose=verbose
            )
            print(formatted)

            return CommandResult.success_result(
                f"Displayed details for {agent_name}", data=agent_details
            )

        except Exception as e:
            self.logger.error(f"Error viewing agent: {e}", exc_info=True)
            return CommandResult.error_result(f"Error viewing agent: {e}")

    def _fix_agents(self, args) -> CommandResult:
        """Fix agent frontmatter issues using validation service."""
        try:
            dry_run = getattr(args, "dry_run", False)
            agent_name = getattr(args, "agent_name", None)
            fix_all = getattr(args, "all", False)

            output_format = getattr(args, "format", "text")

            # Determine what to fix
            if fix_all:
                # Fix all agents
                result = self.validation_service.fix_all_agents(dry_run=dry_run)

                if output_format in ["json", "yaml"]:
                    formatted = (
                        self._formatter.format_as_json(result)
                        if output_format == "json"
                        else self._formatter.format_as_yaml(result)
                    )
                    print(formatted)
                else:
                    # Text output
                    mode = "DRY RUN" if dry_run else "FIX"
                    print(
                        f"\n🔧 {mode}: Checking {result.get('total_agents', 0)} agent(s) for frontmatter issues...\n"
                    )

                    if result.get("results"):
                        for agent_result in result["results"]:
                            print(f"📄 {agent_result['agent']}:")
                            if agent_result.get("skipped"):
                                print(
                                    f"  ⚠️  Skipped: {agent_result.get('reason', 'Unknown reason')}"
                                )
                            elif agent_result.get("was_valid"):
                                print("  ✓ No issues found")
                            else:
                                if agent_result.get("errors_found", 0) > 0:
                                    print(
                                        f"  ❌ Errors found: {agent_result['errors_found']}"
                                    )
                                if agent_result.get("warnings_found", 0) > 0:
                                    print(
                                        f"  ⚠️  Warnings found: {agent_result['warnings_found']}"
                                    )
                                if dry_run:
                                    if agent_result.get("corrections_available", 0) > 0:
                                        print(
                                            f"  🔧 Would fix: {agent_result['corrections_available']} issues"
                                        )
                                elif agent_result.get("corrections_made", 0) > 0:
                                    print(
                                        f"  ✓ Fixed: {agent_result['corrections_made']} issues"
                                    )
                            print()

                    # Summary
                    print("=" * 80)
                    print("SUMMARY:")
                    print(f"  Agents checked: {result.get('agents_checked', 0)}")
                    print(
                        f"  Total issues found: {result.get('total_issues_found', 0)}"
                    )
                    if dry_run:
                        print(
                            f"  Issues that would be fixed: {result.get('total_corrections_available', 0)}"
                        )
                        print("\n💡 Run without --dry-run to apply fixes")
                    else:
                        print(
                            f"  Issues fixed: {result.get('total_corrections_made', 0)}"
                        )
                        if result.get("total_corrections_made", 0) > 0:
                            print("\n✓ Frontmatter issues have been fixed!")
                    print("=" * 80 + "\n")

                msg = f"{'Would fix' if dry_run else 'Fixed'} {result.get('total_corrections_available' if dry_run else 'total_corrections_made', 0)} issues"
                return CommandResult.success_result(msg, data=result)

            if agent_name:
                # Fix specific agent
                result = self.validation_service.fix_agent_frontmatter(
                    agent_name, dry_run=dry_run
                )

                if not result.get("success"):
                    return CommandResult.error_result(
                        result.get("error", "Failed to fix agent")
                    )

                if output_format in ["json", "yaml"]:
                    formatted = (
                        self._formatter.format_as_json(result)
                        if output_format == "json"
                        else self._formatter.format_as_yaml(result)
                    )
                    print(formatted)
                else:
                    # Text output
                    mode = "DRY RUN" if dry_run else "FIX"
                    print(
                        f"\n🔧 {mode}: Checking agent '{agent_name}' for frontmatter issues...\n"
                    )

                    print(f"📄 {agent_name}:")
                    if result.get("was_valid"):
                        print("  ✓ No issues found")
                    else:
                        if result.get("errors_found"):
                            print("  ❌ Errors:")
                            for error in result["errors_found"]:
                                print(f"    - {error}")
                        if result.get("warnings_found"):
                            print("  ⚠️  Warnings:")
                            for warning in result["warnings_found"]:
                                print(f"    - {warning}")
                        if dry_run:
                            if result.get("corrections_available"):
                                print("  🔧 Would fix:")
                                for correction in result["corrections_available"]:
                                    print(f"    - {correction}")
                        elif result.get("corrections_made"):
                            print("  ✓ Fixed:")
                            for correction in result["corrections_made"]:
                                print(f"    - {correction}")
                    print()

                    if dry_run and result.get("corrections_available"):
                        print("💡 Run without --dry-run to apply fixes\n")
                    elif not dry_run and result.get("corrections_made"):
                        print("✓ Frontmatter issues have been fixed!\n")

                msg = f"{'Would fix' if dry_run else 'Fixed'} agent '{agent_name}'"
                return CommandResult.success_result(msg, data=result)

            # No agent specified and not --all
            usage_msg = "Please specify an agent name or use --all to fix all agents\nUsage: claude-mpm agents fix [agent_name] [--dry-run] [--all]"
            if output_format in ["json", "yaml"]:
                return CommandResult.error_result(
                    "No agent specified", data={"usage": usage_msg}
                )
            print(f"❌ {usage_msg}")
            return CommandResult.error_result("No agent specified")

        except Exception as e:
            self.logger.error(f"Error fixing agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error fixing agents: {e}")

    def _check_agent_dependencies(self, args) -> CommandResult:
        """Check agent dependencies."""
        try:
            agent_name = getattr(args, "agent", None)
            result = self.dependency_service.check_dependencies(agent_name=agent_name)

            if not result["success"]:
                if "available_agents" in result:
                    print(f"❌ Agent '{agent_name}' is not deployed")
                    print(
                        f"   Available agents: {', '.join(result['available_agents'])}"
                    )
                return CommandResult.error_result(
                    result.get("error", "Dependency check failed")
                )

            # Print the formatted report
            print(result["report"])

            return CommandResult.success_result(
                "Dependency check completed", data=result
            )

        except Exception as e:
            self.logger.error(f"Error checking dependencies: {e}", exc_info=True)
            return CommandResult.error_result(f"Error checking dependencies: {e}")

    def _install_agent_dependencies(self, args) -> CommandResult:
        """Install agent dependencies."""
        try:
            agent_name = getattr(args, "agent", None)
            dry_run = getattr(args, "dry_run", False)
            result = self.dependency_service.install_dependencies(
                agent_name=agent_name, dry_run=dry_run
            )

            if not result["success"]:
                if "available_agents" in result:
                    print(f"❌ Agent '{agent_name}' is not deployed")
                    print(
                        f"   Available agents: {', '.join(result['available_agents'])}"
                    )
                return CommandResult.error_result(
                    result.get("error", "Installation failed")
                )

            if result.get("missing_count") == 0:
                print("✅ All Python dependencies are already installed")
            elif dry_run:
                print(
                    f"Found {len(result['missing_dependencies'])} missing dependencies:"
                )
                for dep in result["missing_dependencies"]:
                    print(f"  - {dep}")
                print("\n--dry-run specified, not installing anything")
                print(f"Would install: {result['install_command']}")
            else:
                print(
                    f"✅ Successfully installed {len(result.get('installed', []))} dependencies"
                )
                if result.get("still_missing"):
                    print(
                        f"⚠️  {len(result['still_missing'])} dependencies still missing after installation"
                    )
                elif result.get("fully_resolved"):
                    print("✅ All dependencies verified after installation")

            return CommandResult.success_result(
                "Dependency installation completed", data=result
            )

        except Exception as e:
            self.logger.error(f"Error installing dependencies: {e}", exc_info=True)
            return CommandResult.error_result(f"Error installing dependencies: {e}")

    def _list_agent_dependencies(self, args) -> CommandResult:
        """List agent dependencies."""
        try:
            output_format = getattr(args, "format", "text")
            result = self.dependency_service.list_dependencies(
                format_type=output_format
            )

            if not result["success"]:
                return CommandResult.error_result(result.get("error", "Listing failed"))

            # Format output based on requested format
            if output_format == "pip":
                for dep in result["dependencies"]:
                    print(dep)
            elif output_format == "json":
                print(json.dumps(result["data"], indent=2))
            else:  # text format
                print("=" * 60)
                print("DEPENDENCIES FROM DEPLOYED AGENTS")
                print("=" * 60)
                print()

                if result["python_dependencies"]:
                    print(
                        f"Python Dependencies ({len(result['python_dependencies'])}):"
                    )
                    print("-" * 30)
                    for dep in result["python_dependencies"]:
                        print(f"  {dep}")
                    print()

                if result["system_dependencies"]:
                    print(
                        f"System Dependencies ({len(result['system_dependencies'])}):"
                    )
                    print("-" * 30)
                    for dep in result["system_dependencies"]:
                        print(f"  {dep}")
                    print()

                print("Per-Agent Dependencies:")
                print("-" * 30)
                for agent_id in sorted(result["per_agent"].keys()):
                    deps = result["per_agent"][agent_id]
                    python_count = len(deps.get("python", []))
                    system_count = len(deps.get("system", []))
                    if python_count or system_count:
                        print(
                            f"  {agent_id}: {python_count} Python, {system_count} System"
                        )

            return CommandResult.success_result(
                "Dependency listing completed", data=result
            )

        except Exception as e:
            self.logger.error(f"Error listing dependencies: {e}", exc_info=True)
            return CommandResult.error_result(f"Error listing dependencies: {e}")

    def _fix_agent_dependencies(self, args) -> CommandResult:
        """Fix agent dependency issues."""
        try:
            max_retries = getattr(args, "max_retries", 3)
            agent_name = getattr(args, "agent", None)

            print("=" * 70)
            print("FIXING AGENT DEPENDENCIES WITH RETRY LOGIC")
            print("=" * 70)
            print()

            result = self.dependency_service.fix_dependencies(
                max_retries=max_retries, agent_name=agent_name
            )

            if not result["success"]:
                if "error" in result and "not deployed" in result["error"]:
                    print(f"❌ {result['error']}")
                return CommandResult.error_result(result.get("error", "Fix failed"))

            if result.get("message") == "No deployed agents found":
                print("No deployed agents found")
                return CommandResult.success_result("No agents to fix")

            if result.get("message") == "All dependencies are already satisfied":
                print("\n✅ All dependencies are already satisfied!")
                return CommandResult.success_result("All dependencies satisfied")

            # Show what's missing
            if result.get("missing_python"):
                print(f"\n❌ Missing Python packages: {len(result['missing_python'])}")
                for pkg in result["missing_python"][:10]:
                    print(f"   - {pkg}")
                if len(result["missing_python"]) > 10:
                    print(f"   ... and {len(result['missing_python']) - 10} more")

            if result.get("missing_system"):
                print(f"\n❌ Missing system commands: {len(result['missing_system'])}")
                for cmd in result["missing_system"]:
                    print(f"   - {cmd}")
                print("\n⚠️  System dependencies must be installed manually:")
                print(f"  macOS:  brew install {' '.join(result['missing_system'])}")
                print(f"  Ubuntu: apt-get install {' '.join(result['missing_system'])}")

            # Show incompatible packages
            if result.get("incompatible"):
                print(
                    f"\n⚠️  Skipping {len(result['incompatible'])} incompatible packages:"
                )
                for pkg in result["incompatible"][:5]:
                    print(f"   - {pkg}")
                if len(result["incompatible"]) > 5:
                    print(f"   ... and {len(result['incompatible']) - 5} more")

            # Show installation results
            if result.get("fixed_python") or result.get("failed_python"):
                print("\n" + "=" * 70)
                print("INSTALLATION RESULTS:")
                print("=" * 70)

                if result.get("fixed_python"):
                    print(
                        f"✅ Successfully installed: {len(result['fixed_python'])} packages"
                    )

                if result.get("failed_python"):
                    print(
                        f"❌ Failed to install: {len(result['failed_python'])} packages"
                    )
                    errors = result.get("errors", {})
                    for pkg in result["failed_python"]:
                        print(f"   - {pkg}: {errors.get(pkg, 'Unknown error')}")

                # Final verification
                if result.get("still_missing") is not None:
                    if not result["still_missing"]:
                        print("\n✅ All Python dependencies are now satisfied!")
                    else:
                        print(
                            f"\n⚠️  Still missing {len(result['still_missing'])} packages"
                        )
                        print("\nTry running again or install manually:")
                        missing_sample = result["still_missing"][:3]
                        print(f"  pip install {' '.join(missing_sample)}")

            print("\n" + "=" * 70)
            print("DONE")
            print("=" * 70)

            return CommandResult.success_result("Dependency fix completed", data=result)

        except Exception as e:
            self.logger.error(f"Error fixing dependencies: {e}", exc_info=True)
            return CommandResult.error_result(f"Error fixing dependencies: {e}")

    def _cleanup_orphaned_agents(self, args) -> CommandResult:
        """Clean up orphaned agents that don't have templates."""
        try:
            # Determine agents directory
            agents_dir = None
            if hasattr(args, "agents_dir") and args.agents_dir:
                agents_dir = args.agents_dir

            # Determine if we're doing a dry run
            dry_run = getattr(args, "dry_run", True)
            if hasattr(args, "force") and args.force:
                dry_run = False

            # Perform cleanup using the cleanup service
            results = self.cleanup_service.clean_orphaned_agents(
                agents_dir=agents_dir, dry_run=dry_run
            )

            output_format = getattr(args, "format", "text")

            formatted = self._formatter.format_cleanup_result(
                results, output_format=output_format, dry_run=dry_run
            )
            print(formatted)

            # Determine success/error based on results
            if results.get("errors") and not dry_run:
                return CommandResult.error_result(
                    f"Cleanup completed with {len(results['errors'])} errors",
                    data=results,
                )

            return CommandResult.success_result(
                f"Cleanup {'preview' if dry_run else 'completed'}", data=results
            )

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}", exc_info=True)
            return CommandResult.error_result(f"Error during cleanup: {e}")


def manage_agents(args):
    """
    Main entry point for agent management commands.

    This function maintains backward compatibility while using the new AgentCommand pattern.
    """
    command = AgentsCommand()
    result = command.execute(args)

    # Print result if structured output format is requested
    if hasattr(args, "format") and args.format in ["json", "yaml"]:
        command.print_result(result, args)

    return result.exit_code
