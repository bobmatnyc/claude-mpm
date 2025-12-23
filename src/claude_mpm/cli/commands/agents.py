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
from ...core.enums import OutputFormat
from ...services.cli.agent_cleanup_service import AgentCleanupService
from ...services.cli.agent_dependency_service import AgentDependencyService
from ...services.cli.agent_listing_service import AgentListingService
from ...services.cli.agent_output_formatter import AgentOutputFormatter
from ...services.cli.agent_validation_service import AgentValidationService
from ..shared import AgentCommand, CommandResult
from ..utils import get_agent_versions_display
from .agents_cleanup import handle_agents_cleanup


def _is_structured_output(args) -> bool:
    """Check if args specify structured output format (JSON/YAML)."""
    if hasattr(args, "format"):
        fmt = str(args.format).lower()
        return fmt in (OutputFormat.JSON, OutputFormat.YAML)
    return False


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
            except ImportError as e:
                raise ImportError("Agent deployment service not available") from e
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

    def _get_output_format(self, args) -> str:
        """
        Get output format from args with enum default.

        Args:
            args: Command arguments

        Returns:
            Output format string (compatible with both enum and string usage)
        """
        return getattr(args, "format", OutputFormat.TEXT)

    def _is_structured_format(self, format_str: str) -> bool:
        """
        Check if format is structured (JSON/YAML).

        Args:
            format_str: Format string to check

        Returns:
            True if format is JSON or YAML
        """
        fmt = str(format_str).lower()
        return fmt in (OutputFormat.JSON, OutputFormat.YAML)

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
                "cleanup": lambda a: self._handle_cleanup_command(a),
                "cleanup-orphaned": self._cleanup_orphaned_agents,
                # Local agent management commands
                "create": self._create_local_agent,
                "edit": self._edit_local_agent,
                "delete": self._delete_local_agent,
                "manage": self._manage_local_agents,
                "configure": self._configure_deployment,
                # Migration command (DEPRECATION support)
                "migrate-to-project": self._migrate_to_project,
                # Agent selection modes (Phase 3: 1M-382)
                "deploy-minimal": self._deploy_minimal_configuration,
                "deploy-auto": self._deploy_auto_configure,
                # Agent source management (Phase 2: 1M-442)
                "available": self._list_available_from_sources,
                # Agent discovery with rich filtering (Phase 1: Discovery & Browsing)
                "discover": self._discover_agents,
                # NEW: Collection-based agent management
                "list-collections": self._list_collections,
                "deploy-collection": self._deploy_collection,
                "list-by-collection": self._list_by_collection,
                # Cache git management commands
                "cache-status": self._cache_status,
                "cache-pull": self._cache_pull,
                "cache-push": self._cache_push,
                "cache-sync": self._cache_sync,
                "cache-commit": self._cache_commit,
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

            output_format = self._get_output_format(args)
            if self._is_structured_format(output_format):
                # Parse the agent versions display into structured data
                if agent_versions:
                    data = {"agent_versions": agent_versions, "has_agents": True}
                    formatted = (
                        self._formatter.format_as_json(data)
                        if str(output_format).lower() == OutputFormat.JSON
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
                    if str(output_format).lower() == OutputFormat.JSON
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
            output_format = self._get_output_format(args)

            if hasattr(args, "by_tier") and args.by_tier:
                return self._list_agents_by_tier(args)
            if getattr(args, "system", False):
                return self._list_system_agents(args)
            if getattr(args, "deployed", False):
                return self._list_deployed_agents(args)
            # Default: show usage
            usage_msg = "Use --system to list system agents, --deployed to list deployed agents, or --by-tier to group by precedence"

            if self._is_structured_format(output_format):
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

            output_format = self._get_output_format(args)
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

            output_format = self._get_output_format(args)
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
            if str(output_format).lower() == OutputFormat.TEXT and warnings:
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
            output_format = self._get_output_format(args)

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

    def _list_available_from_sources(self, args) -> CommandResult:
        """List available agents from all configured git sources.

        This command shows agents discovered from configured agent sources
        (Git repositories) after syncing their cache. Implements Phase 2 of 1M-442.

        Args:
            args: Command arguments with optional source filter and format

        Returns:
            CommandResult with agent list or error
        """
        try:
            from ...config.agent_sources import AgentSourceConfiguration
            from ...services.agents.git_source_manager import GitSourceManager

            # Load agent sources configuration
            config = AgentSourceConfiguration.load()
            enabled_repos = [r for r in config.repositories if r.enabled]

            if not enabled_repos:
                message = (
                    "No agent sources configured.\n\n"
                    "Configure sources with:\n"
                    "  claude-mpm agent-source add <url>\n\n"
                    "Example:\n"
                    "  claude-mpm agent-source add https://github.com/owner/repo/agents"
                )
                print(message)
                return CommandResult.error_result("No agent sources configured")

            # Initialize git source manager
            manager = GitSourceManager()

            # Sync all configured sources (with timeout)
            self.logger.info(f"Syncing {len(enabled_repos)} agent sources...")
            sync_results = {}

            for repo in enabled_repos:
                try:
                    result = manager.sync_repository(repo, force=False)
                    sync_results[repo.identifier] = result
                except Exception as e:
                    self.logger.warning(f"Failed to sync {repo.identifier}: {e}")
                    sync_results[repo.identifier] = {"synced": False, "error": str(e)}

            # Get source filter from args
            source_filter = getattr(args, "source", None)

            # List all cached agents
            all_agents = manager.list_cached_agents(repo_identifier=source_filter)

            if not all_agents:
                message = "No agents found in configured sources."
                if sync_results:
                    failed_count = sum(
                        1 for r in sync_results.values() if not r.get("synced")
                    )
                    if failed_count > 0:
                        message += f"\n\n{failed_count} source(s) failed to sync. Check logs for details."
                print(message)
                return CommandResult.success_result(message, data={"agents": []})

            # Format output
            output_format = getattr(args, "format", "table")

            if output_format == "json":
                import json

                print(json.dumps(all_agents, indent=2))
            elif output_format == "simple":
                for agent in all_agents:
                    name = agent.get("metadata", {}).get(
                        "name", agent.get("agent_id", "unknown")
                    )
                    repo = agent.get("repository", "unknown")
                    print(f"{name} (from {repo})")
            else:  # table format
                print(f"\n{'Agent Name':<30} {'Repository':<40} {'Version':<15}")
                print("=" * 85)
                for agent in all_agents:
                    name = agent.get("metadata", {}).get(
                        "name", agent.get("agent_id", "unknown")
                    )
                    repo = agent.get("repository", "unknown")
                    version = agent.get("version", "unknown")[:12]
                    print(f"{name:<30} {repo:<40} {version:<15}")
                print(
                    f"\nTotal: {len(all_agents)} agents from {len(sync_results)} sources"
                )

            return CommandResult.success_result(
                f"Listed {len(all_agents)} agents from sources",
                data={"agents": all_agents, "sync_results": sync_results},
            )

        except Exception as e:
            self.logger.error(f"Error listing available agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error listing available agents: {e}")

    def _discover_agents(self, args) -> CommandResult:
        """Discover agents with rich filtering capabilities.

        This command extends the 'available' command by adding semantic filtering
        based on AUTO-DEPLOY-INDEX.md categories. Users can filter by category,
        language, framework, platform, and specialization.

        Design Decision: Delegate to agents_discover.py module

        Rationale: Keep CLI command logic separate from routing logic for better
        testability and maintainability. The discover_command function handles
        all the complex filtering and formatting logic.

        Args:
            args: Command arguments with filter options:
                - source: Source repository filter
                - category: Category filter (e.g., 'engineer/backend')
                - language: Language filter (e.g., 'python')
                - framework: Framework filter (e.g., 'react')
                - platform: Platform filter (e.g., 'vercel')
                - specialization: Specialization filter (e.g., 'data')
                - format: Output format (table, json, simple)
                - verbose: Show descriptions and metadata

        Returns:
            CommandResult with filtered agent list or error

        Example:
            >>> # Called via: claude-mpm agents discover --category engineer/backend
            >>> _discover_agents(args)
            CommandResult(success=True, message="Discovered 8 agents")
        """
        try:
            from .agents_discover import discover_command

            # Call discover_command and convert exit code to CommandResult
            exit_code = discover_command(args)

            if exit_code == 0:
                return CommandResult.success_result("Agent discovery complete")
            return CommandResult.error_result("Agent discovery failed")

        except Exception as e:
            self.logger.error(f"Error discovering agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error discovering agents: {e}")

    def _deploy_agents(self, args, force=False) -> CommandResult:
        """Deploy agents using two-phase sync: cache → deploy.

        Phase 3 Integration (1M-486): Uses Git sync service for deployment.
        - Phase 1: Sync agents to ~/.claude-mpm/cache/agents/ (if needed)
        - Phase 2: Deploy from cache to project .claude-mpm/agents/

        This replaces the old single-tier deployment with a multi-project
        architecture where one cache serves multiple project deployments.
        """
        try:
            # Handle preset deployment (uses different path)
            if hasattr(args, "preset") and args.preset:
                return self._deploy_preset(args)

            from ...services.agents.sources.git_source_sync_service import (
                GitSourceSyncService,
            )

            # Initialize git sync service
            git_sync = GitSourceSyncService()
            project_dir = Path.cwd()

            self.logger.info("Phase 1: Syncing agents to cache...")

            # Sync to cache (downloads from GitHub if needed)
            sync_result = git_sync.sync_repository(force=force)

            if not sync_result.get("synced"):
                error_msg = sync_result.get("error", "Unknown sync error")
                self.logger.error(f"Sync failed: {error_msg}")
                return CommandResult.error_result(f"Sync failed: {error_msg}")

            self.logger.info(
                f"Phase 1 complete: {sync_result.get('agent_count', 0)} agents in cache"
            )
            self.logger.info(f"Phase 2: Deploying agents to {project_dir}...")

            # Deploy from cache to project directory
            deploy_result = git_sync.deploy_agents_to_project(
                project_dir=project_dir,
                agent_list=None,  # Deploy all cached agents
                force=force,
            )

            # Format combined results for output
            combined_result = {
                "deployed_count": len(deploy_result.get("deployed", []))
                + len(deploy_result.get("updated", [])),
                "deployed": deploy_result.get("deployed", []),
                "updated": deploy_result.get("updated", []),
                "skipped": deploy_result.get("skipped", []),
                "errors": deploy_result.get("failed", []),
                "target_dir": deploy_result.get("deployment_dir", ""),
                "sync_info": {
                    "cached_agents": sync_result.get("agent_count", 0),
                    "cache_dir": sync_result.get("cache_dir", ""),
                },
            }

            output_format = self._get_output_format(args)
            verbose = getattr(args, "verbose", False)

            formatted = self._formatter.format_deployment_result(
                combined_result, output_format=output_format, verbose=verbose
            )
            print(formatted)

            success_count = len(deploy_result["deployed"]) + len(
                deploy_result["updated"]
            )
            return CommandResult.success_result(
                f"Deployed {success_count} agents from cache",
                data={
                    "sync_result": sync_result,
                    "deploy_result": deploy_result,
                    "total_deployed": success_count,
                },
            )

        except Exception as e:
            self.logger.error(f"Error deploying agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error deploying agents: {e}")

    def _deploy_preset(self, args) -> CommandResult:
        """Deploy agents by preset name.

        This method implements Phase 2 of the agents/skills CLI redesign,
        enabling preset-based deployment like:
            claude-mpm agents deploy --preset python-dev

        Args:
            args: Command arguments with preset name and optional flags

        Returns:
            CommandResult with deployment status
        """
        try:
            from pathlib import Path

            from ...config.agent_sources import AgentSourceConfiguration
            from ...services.agents.agent_preset_service import AgentPresetService
            from ...services.agents.git_source_manager import GitSourceManager
            from ...services.agents.single_tier_deployment_service import (
                SingleTierDeploymentService,
            )

            preset_name = args.preset
            dry_run = getattr(args, "dry_run", False)

            # Initialize services
            config = AgentSourceConfiguration.load()
            deployment_dir = Path.home() / ".claude" / "agents"
            git_source_manager = GitSourceManager()
            preset_service = AgentPresetService(git_source_manager)
            deployment_service = SingleTierDeploymentService(config, deployment_dir)

            # Validate preset
            if not preset_service.validate_preset(preset_name):
                available = preset_service.list_presets()
                print(f"❌ Unknown preset: {preset_name}")
                print("\n📚 Available presets:")
                for preset in available:
                    print(
                        f"  • {preset['name']}: {preset['description']} ({preset['agent_count']} agents)"
                    )
                    print(f"    Use cases: {', '.join(preset['use_cases'])}")
                return CommandResult.error_result(f"Unknown preset: {preset_name}")

            # Resolve preset to agent list
            print(f"\n🔍 Resolving preset: {preset_name}")
            resolution = preset_service.resolve_agents(
                preset_name, validate_availability=True
            )

            # Show preset info
            preset_info = resolution["preset_info"]
            print(f"\n🎯 Preset: {preset_info['description']}")
            print(f"   Agents: {preset_info['agent_count']}")
            print(f"   Use cases: {', '.join(preset_info['use_cases'])}")

            # Show warnings for missing agents
            if resolution["missing_agents"]:
                print("\n⚠️  Missing agents (not found in configured sources):")
                for agent_id in resolution["missing_agents"]:
                    print(f"    • {agent_id}")
                print("\n💡 These agents are not available in your configured sources.")
                print("   Deployment will continue with available agents.")

            # Show conflicts
            if resolution["conflicts"]:
                print("\n⚠️  Priority conflicts detected:")
                for conflict in resolution["conflicts"]:
                    sources = ", ".join(conflict["sources"])
                    print(f"    • {conflict['agent_id']} (found in: {sources})")
                print("    Using highest priority source for each")

            # Dry run mode
            if dry_run:
                print("\n🔍 DRY RUN: Preview agent deployment\n")
                print("Agents to deploy:")
                for agent in resolution["agents"]:
                    source = agent.get("source", "unknown")
                    print(f"  ✓ {agent['agent_id']} (from {source})")
                print(
                    "\n💡 This is a dry run. Run without --dry-run to actually deploy."
                )
                return CommandResult.success_result(
                    "Dry run complete",
                    data={
                        "preset": preset_name,
                        "agents": resolution["agents"],
                        "missing": resolution["missing_agents"],
                    },
                )

            # Deploy agents
            print(f"\n📦 Deploying {len(resolution['agents'])} agents...")
            deployed_count = 0
            failed_count = 0
            skipped_count = len(resolution["missing_agents"])
            deployed_agents = []
            failed_agents = []

            for agent in resolution["agents"]:
                agent_id = agent["agent_id"]
                try:
                    # Deploy using single-tier deployment service
                    result = deployment_service.deploy_agent(
                        agent_id, source_repo=agent.get("source"), dry_run=False
                    )

                    if result.get("deployed"):
                        deployed_count += 1
                        deployed_agents.append(agent_id)
                        print(f"  ✓ {agent_id}")
                    else:
                        failed_count += 1
                        failed_agents.append(
                            {
                                "agent_id": agent_id,
                                "error": result.get("error", "Unknown"),
                            }
                        )
                        print(f"  ✗ {agent_id}: {result.get('error', 'Failed')}")

                except Exception as e:
                    failed_count += 1
                    failed_agents.append({"agent_id": agent_id, "error": str(e)})
                    print(f"  ✗ {agent_id}: {e}")

            # Summary
            print(f"\n{'=' * 60}")
            print("📊 Deployment Summary")
            print(f"{'=' * 60}")
            print(f"  ✅ Deployed: {deployed_count}")
            print(f"  ❌ Failed: {failed_count}")
            print(f"  ⏭️  Skipped: {skipped_count} (missing from sources)")
            print(f"{'=' * 60}\n")

            if failed_agents:
                print("❌ Failed agents:")
                for failure in failed_agents:
                    print(f"  • {failure['agent_id']}: {failure['error']}")
                print()

            if deployed_count > 0:
                print(f"✅ Successfully deployed {deployed_count} agents!")
                return CommandResult.success_result(
                    f"Deployed {deployed_count} agents from preset '{preset_name}'",
                    data={
                        "preset": preset_name,
                        "deployed": deployed_agents,
                        "failed": failed_agents,
                        "skipped": resolution["missing_agents"],
                    },
                )
            return CommandResult.error_result(
                f"No agents deployed from preset '{preset_name}'",
                data={
                    "preset": preset_name,
                    "failed": failed_agents,
                    "skipped": resolution["missing_agents"],
                },
            )

        except Exception as e:
            self.logger.error(f"Error deploying preset: {e}", exc_info=True)
            print(f"\n❌ Error deploying preset: {e}")
            return CommandResult.error_result(f"Error deploying preset: {e}")

    def _clean_agents(self, args) -> CommandResult:
        """Clean deployed agents."""
        try:
            result = self.cleanup_service.clean_deployed_agents()

            output_format = self._get_output_format(args)
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

            output_format = self._get_output_format(args)
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
            output_format = self._get_output_format(args)

            # Route to appropriate handler based on input
            if fix_all:
                return self._fix_all_agents(dry_run, output_format)
            if agent_name:
                return self._fix_single_agent(agent_name, dry_run, output_format)
            return self._handle_no_agent_specified(output_format)

        except Exception as e:
            self.logger.error(f"Error fixing agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error fixing agents: {e}")

    def _fix_all_agents(self, dry_run: bool, output_format: str) -> CommandResult:
        """Fix all agents' frontmatter issues."""
        result = self.validation_service.fix_all_agents(dry_run=dry_run)

        if self._is_structured_format(output_format):
            self._print_structured_output(result, output_format)
        else:
            self._print_all_agents_text_output(result, dry_run)

        msg = f"{'Would fix' if dry_run else 'Fixed'} {result.get('total_corrections_available' if dry_run else 'total_corrections_made', 0)} issues"
        return CommandResult.success_result(msg, data=result)

    def _fix_single_agent(
        self, agent_name: str, dry_run: bool, output_format: str
    ) -> CommandResult:
        """Fix a single agent's frontmatter issues."""
        result = self.validation_service.fix_agent_frontmatter(
            agent_name, dry_run=dry_run
        )

        if not result.get("success"):
            return CommandResult.error_result(
                result.get("error", "Failed to fix agent")
            )

        if self._is_structured_format(output_format):
            self._print_structured_output(result, output_format)
        else:
            self._print_single_agent_text_output(agent_name, result, dry_run)

        msg = f"{'Would fix' if dry_run else 'Fixed'} agent '{agent_name}'"
        return CommandResult.success_result(msg, data=result)

    def _handle_no_agent_specified(self, output_format: str) -> CommandResult:
        """Handle case where no agent is specified."""
        usage_msg = "Please specify an agent name or use --all to fix all agents\nUsage: claude-mpm agents fix [agent_name] [--dry-run] [--all]"
        if self._is_structured_format(output_format):
            return CommandResult.error_result(
                "No agent specified", data={"usage": usage_msg}
            )
        print(f"❌ {usage_msg}")
        return CommandResult.error_result("No agent specified")

    def _print_structured_output(self, result: dict, output_format: str) -> None:
        """Print result in JSON or YAML format."""
        formatted = (
            self._formatter.format_as_json(result)
            if str(output_format).lower() == OutputFormat.JSON
            else self._formatter.format_as_yaml(result)
        )
        print(formatted)

    def _print_all_agents_text_output(self, result: dict, dry_run: bool) -> None:
        """Print text output for all agents fix operation."""
        mode = "DRY RUN" if dry_run else "FIX"
        print(
            f"\n🔧 {mode}: Checking {result.get('total_agents', 0)} agent(s) for frontmatter issues...\n"
        )

        if result.get("results"):
            for agent_result in result["results"]:
                self._print_agent_result(agent_result, dry_run)

        self._print_all_agents_summary(result, dry_run)

    def _print_agent_result(self, agent_result: dict, dry_run: bool) -> None:
        """Print result for a single agent."""
        print(f"📄 {agent_result['agent']}:")
        if agent_result.get("skipped"):
            print(f"  ⚠️  Skipped: {agent_result.get('reason', 'Unknown reason')}")
        elif agent_result.get("was_valid"):
            print("  ✓ No issues found")
        else:
            self._print_agent_issues(agent_result, dry_run)
        print()

    def _print_agent_issues(self, agent_result: dict, dry_run: bool) -> None:
        """Print issues found for an agent."""
        if agent_result.get("errors_found", 0) > 0:
            print(f"  ❌ Errors found: {agent_result['errors_found']}")
        if agent_result.get("warnings_found", 0) > 0:
            print(f"  ⚠️  Warnings found: {agent_result['warnings_found']}")

        if dry_run:
            if agent_result.get("corrections_available", 0) > 0:
                print(f"  🔧 Would fix: {agent_result['corrections_available']} issues")
        elif agent_result.get("corrections_made", 0) > 0:
            print(f"  ✓ Fixed: {agent_result['corrections_made']} issues")

    def _print_all_agents_summary(self, result: dict, dry_run: bool) -> None:
        """Print summary for all agents fix operation."""
        print("=" * 80)
        print("SUMMARY:")
        print(f"  Agents checked: {result.get('agents_checked', 0)}")
        print(f"  Total issues found: {result.get('total_issues_found', 0)}")

        if dry_run:
            print(
                f"  Issues that would be fixed: {result.get('total_corrections_available', 0)}"
            )
            print("\n💡 Run without --dry-run to apply fixes")
        else:
            print(f"  Issues fixed: {result.get('total_corrections_made', 0)}")
            if result.get("total_corrections_made", 0) > 0:
                print("\n✓ Frontmatter issues have been fixed!")
        print("=" * 80 + "\n")

    def _print_single_agent_text_output(
        self, agent_name: str, result: dict, dry_run: bool
    ) -> None:
        """Print text output for single agent fix operation."""
        mode = "DRY RUN" if dry_run else "FIX"
        print(f"\n🔧 {mode}: Checking agent '{agent_name}' for frontmatter issues...\n")

        print(f"📄 {agent_name}:")
        if result.get("was_valid"):
            print("  ✓ No issues found")
        else:
            self._print_single_agent_issues(result, dry_run)
        print()

        self._print_single_agent_footer(result, dry_run)

    def _print_single_agent_issues(self, result: dict, dry_run: bool) -> None:
        """Print issues for a single agent."""
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

    def _print_single_agent_footer(self, result: dict, dry_run: bool) -> None:
        """Print footer message for single agent fix."""
        if dry_run and result.get("corrections_available"):
            print("💡 Run without --dry-run to apply fixes\n")
        elif not dry_run and result.get("corrections_made"):
            print("✓ Frontmatter issues have been fixed!\n")

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
            output_format = self._get_output_format(args)
            result = self.dependency_service.list_dependencies(
                format_type=output_format
            )

            if not result["success"]:
                return CommandResult.error_result(result.get("error", "Listing failed"))

            # Format output based on requested format
            if output_format == "pip":
                for dep in result["dependencies"]:
                    print(dep)
            elif str(output_format).lower() == OutputFormat.JSON:
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

    def _handle_cleanup_command(self, args) -> CommandResult:
        """Handle cleanup command with proper result wrapping."""
        exit_code = handle_agents_cleanup(args)
        return CommandResult(
            success=exit_code == 0,
            message=(
                "Agent cleanup complete" if exit_code == 0 else "Agent cleanup failed"
            ),
        )

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

            output_format = self._get_output_format(args)

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

    def _create_local_agent(self, args) -> CommandResult:
        """Create a new local agent template."""
        try:
            if getattr(args, "interactive", False):
                # Launch interactive wizard
                from ..interactive.agent_wizard import run_interactive_agent_wizard

                exit_code = run_interactive_agent_wizard()
                if exit_code == 0:
                    return CommandResult.success_result("Agent created successfully")
                return CommandResult.error_result("Agent creation cancelled or failed")

            # Non-interactive creation
            from ...services.agents.local_template_manager import (
                LocalAgentTemplateManager,
            )

            agent_id = getattr(args, "agent_id", None)
            if not agent_id:
                return CommandResult.error_result(
                    "--agent-id is required for non-interactive creation"
                )

            manager = LocalAgentTemplateManager()
            name = getattr(args, "name", agent_id.replace("-", " ").title())
            model = getattr(args, "model", "sonnet")
            inherit_from = getattr(args, "inherit_from", None)

            # Create basic template
            template = manager.create_local_template(
                agent_id=agent_id,
                name=name,
                description=f"Local agent: {name}",
                instructions="# Agent Instructions\n\nCustomize this agent's behavior here.",
                model=model,
                parent_agent=inherit_from,
                tier="project",
            )

            if template:
                return CommandResult.success_result(
                    f"Created local agent '{agent_id}' in .claude-mpm/agents/",
                    data={
                        "agent_id": agent_id,
                        "path": f".claude-mpm/agents/{agent_id}.json",
                    },
                )
            return CommandResult.error_result("Failed to create agent template")

        except Exception as e:
            self.logger.error(f"Error creating local agent: {e}", exc_info=True)
            return CommandResult.error_result(f"Error creating local agent: {e}")

    def _edit_local_agent(self, args) -> CommandResult:
        """Edit a local agent template."""
        try:
            agent_id = getattr(args, "agent_id", None)
            if not agent_id:
                return CommandResult.error_result("agent_id is required")

            import os
            import subprocess

            from ...services.agents.local_template_manager import (
                LocalAgentTemplateManager,
            )

            manager = LocalAgentTemplateManager()
            template = manager.get_local_template(agent_id)

            if not template:
                return CommandResult.error_result(f"Local agent '{agent_id}' not found")

            # Get template file path
            template_file = None
            if template.tier == "project":
                template_file = manager.project_agents_dir / f"{agent_id}.json"
            else:
                template_file = manager.user_agents_dir / f"{agent_id}.json"

            if not template_file or not template_file.exists():
                return CommandResult.error_result(
                    f"Template file not found for '{agent_id}'"
                )

            if getattr(args, "interactive", False):
                # Launch interactive editor
                from ..interactive.agent_wizard import AgentWizard

                wizard = AgentWizard()
                success, message = wizard._edit_agent_config(template)
                if success:
                    return CommandResult.success_result(message)
                return CommandResult.error_result(message)

            # Use system editor
            editor = getattr(args, "editor", None) or os.environ.get("EDITOR", "nano")
            subprocess.run([editor, str(template_file)], check=True)
            return CommandResult.success_result(
                f"Agent '{agent_id}' edited successfully"
            )

        except subprocess.CalledProcessError:
            return CommandResult.error_result("Editor exited with error")
        except Exception as e:
            self.logger.error(f"Error editing local agent: {e}", exc_info=True)
            return CommandResult.error_result(f"Error editing local agent: {e}")

    def _delete_local_agent(self, args) -> CommandResult:
        """Delete local agent templates."""
        try:
            agent_ids = getattr(args, "agent_ids", [])
            if not agent_ids:
                return CommandResult.error_result("No agent IDs specified")

            from ...services.agents.local_template_manager import (
                LocalAgentTemplateManager,
            )

            manager = LocalAgentTemplateManager()
            force = getattr(args, "force", False)
            keep_deployment = getattr(args, "keep_deployment", False)
            backup = getattr(args, "backup", False)

            # Confirmation if not forced
            if not force:
                print(f"\n⚠️  This will delete {len(agent_ids)} agent(s):")
                for agent_id in agent_ids:
                    print(f"  - {agent_id}")
                confirm = input("\nAre you sure? [y/N]: ").strip().lower()
                if confirm not in ["y", "yes"]:
                    return CommandResult.error_result("Deletion cancelled")

            # Delete agents
            if len(agent_ids) == 1:
                result = manager.delete_local_template(
                    agent_id=agent_ids[0],
                    tier="all",
                    delete_deployment=not keep_deployment,
                    backup_first=backup,
                )
                if result["success"]:
                    message = f"Successfully deleted agent '{agent_ids[0]}'"
                    if result["backup_location"]:
                        message += f"\nBackup saved to: {result['backup_location']}"
                    return CommandResult.success_result(message, data=result)
                return CommandResult.error_result(
                    f"Failed to delete agent: {', '.join(result['errors'])}"
                )
            results = manager.delete_multiple_templates(
                agent_ids=agent_ids,
                tier="all",
                delete_deployment=not keep_deployment,
                backup_first=backup,
            )

            message = ""
            if results["successful"]:
                message = (
                    f"Successfully deleted {len(results['successful'])} agent(s):\n"
                )
                for agent_id in results["successful"]:
                    message += f"  - {agent_id}\n"

            if results["failed"]:
                if message:
                    message += "\n"
                message += f"Failed to delete {len(results['failed'])} agent(s):\n"
                for agent_id in results["failed"]:
                    errors = results["details"][agent_id]["errors"]
                    message += f"  - {agent_id}: {', '.join(errors)}\n"

            if results["successful"]:
                return CommandResult.success_result(message.strip(), data=results)
            return CommandResult.error_result(message.strip(), data=results)

        except Exception as e:
            self.logger.error(f"Error deleting local agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error deleting local agents: {e}")

    def _manage_local_agents(self, args) -> CommandResult:
        """Redirect to main configuration interface (DEPRECATED)."""
        try:
            from rich.console import Console
            from rich.prompt import Confirm

            console = Console()

            console.print(
                "\n[bold cyan]╭─────────────────────────────────────────╮[/bold cyan]"
            )
            console.print(
                "[bold cyan]│  Agent Management Has Moved!            │[/bold cyan]"
            )
            console.print(
                "[bold cyan]╰─────────────────────────────────────────╯[/bold cyan]\n"
            )

            console.print("For a better experience with integrated configuration:")
            console.print("  • Agent management")
            console.print("  • Skills management")
            console.print("  • Template editing")
            console.print("  • Behavior configuration")
            console.print("  • Startup settings\n")

            console.print("Please use: [bold green]claude-mpm config[/bold green]\n")

            if Confirm.ask("Launch configuration interface now?", default=True):
                # Import and run config command directly
                from claude_mpm.cli.commands.configure import ConfigureCommand

                config_cmd = ConfigureCommand()
                return config_cmd.execute(args)
            console.print(
                "\n[dim]Run 'claude-mpm config' anytime to access agent management[/dim]"
            )
            return CommandResult.success_result("Redirected to config interface")

        except Exception as e:
            self.logger.error(f"Error redirecting to config: {e}", exc_info=True)
            return CommandResult.error_result(f"Error redirecting to config: {e}")

    def _configure_deployment(self, args) -> CommandResult:
        """Configure agent deployment settings."""
        try:
            from pathlib import Path

            import yaml

            from claude_mpm.core.config import Config

            config = Config()
            config_path = Path.cwd() / ".claude-mpm" / "configuration.yaml"

            # Handle show command
            if getattr(args, "show", False):
                from ...services.agents.deployment.deployment_config_loader import (
                    DeploymentConfigLoader,
                )

                loader = DeploymentConfigLoader(self.logger)
                settings = loader.get_deployment_settings(config)

                print("\n📋 Agent Deployment Configuration")
                print("=" * 50)
                print(f"Configuration file: {config_path}")
                print("\n🔧 Deployment Settings:")
                print(f"  Deploy system agents: {settings['deploy_system_agents']}")
                print(f"  Deploy local agents: {settings['deploy_local_agents']}")
                print(f"  Deploy user agents: {settings['deploy_user_agents']}")
                print(
                    f"  Prefer local over system: {settings['prefer_local_over_system']}"
                )
                print(f"  Version comparison: {settings['version_comparison']}")

                if settings["enabled_agents"]:
                    print(
                        f"\n✅ Enabled agents: {', '.join(settings['enabled_agents'])}"
                    )
                else:
                    print("\n✅ Enabled agents: All (no restrictions)")

                if settings["disabled_agents"]:
                    print(
                        f"❌ Disabled agents: {', '.join(settings['disabled_agents'])}"
                    )
                else:
                    print("❌ Disabled agents: None")

                print("\n" + "=" * 50)
                return CommandResult.success_result(
                    "Displayed deployment configuration"
                )

            # Handle interactive mode
            if getattr(args, "interactive", False):
                return self._configure_deployment_interactive(config_path)

            # Load current configuration
            if not config_path.exists():
                config_path.parent.mkdir(parents=True, exist_ok=True)
                config_data = {}
            else:
                with config_path.open() as f:
                    config_data = yaml.safe_load(f) or {}

            # Ensure agent_deployment section exists
            if "agent_deployment" not in config_data:
                config_data["agent_deployment"] = {}

            modified = False

            # Handle enable/disable operations
            if getattr(args, "enable_all", False):
                config_data["agent_deployment"]["enabled_agents"] = []
                config_data["agent_deployment"]["disabled_agents"] = []
                print("✅ Enabled all agents for deployment")
                modified = True

            if getattr(args, "enable_system", False):
                config_data["agent_deployment"]["deploy_system_agents"] = True
                print("✅ Enabled system agents for deployment")
                modified = True

            if getattr(args, "disable_system", False):
                config_data["agent_deployment"]["deploy_system_agents"] = False
                print("❌ Disabled system agents from deployment")
                modified = True

            if getattr(args, "enable_local", False):
                config_data["agent_deployment"]["deploy_local_agents"] = True
                print("✅ Enabled local agents for deployment")
                modified = True

            if getattr(args, "disable_local", False):
                config_data["agent_deployment"]["deploy_local_agents"] = False
                print("❌ Disabled local agents from deployment")
                modified = True

            if getattr(args, "enable", None):
                enabled = config_data["agent_deployment"].get("enabled_agents", [])
                disabled = config_data["agent_deployment"].get("disabled_agents", [])

                for agent_id in args.enable:
                    if agent_id not in enabled:
                        enabled.append(agent_id)
                    if agent_id in disabled:
                        disabled.remove(agent_id)

                config_data["agent_deployment"]["enabled_agents"] = enabled
                config_data["agent_deployment"]["disabled_agents"] = disabled
                print(f"✅ Enabled agents: {', '.join(args.enable)}")
                modified = True

            if getattr(args, "disable", None):
                disabled = config_data["agent_deployment"].get("disabled_agents", [])

                for agent_id in args.disable:
                    if agent_id not in disabled:
                        disabled.append(agent_id)

                config_data["agent_deployment"]["disabled_agents"] = disabled
                print(f"❌ Disabled agents: {', '.join(args.disable)}")
                modified = True

            # Save configuration if modified
            if modified:
                with config_path.open("w") as f:
                    yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
                print(f"\n💾 Configuration saved to {config_path}")
                return CommandResult.success_result("Deployment configuration updated")

            # If no modifications were made and not showing, display help
            if not getattr(args, "show", False):
                print("No configuration changes specified. Use --help for options.")
                return CommandResult.success_result("No changes made")

        except Exception as e:
            self.logger.error(f"Error configuring deployment: {e}", exc_info=True)
            return CommandResult.error_result(f"Error configuring deployment: {e}")

    def _configure_deployment_interactive(self, config_path: Path) -> CommandResult:
        """Interactive mode for configuring agent deployment."""
        try:
            import yaml

            from ...utils.ui_helpers import (
                prompt_choice,
                prompt_multiselect,
                prompt_yes_no,
            )

            # Load current configuration
            if config_path.exists():
                with config_path.open() as f:
                    config_data = yaml.safe_load(f) or {}
            else:
                config_data = {}

            if "agent_deployment" not in config_data:
                config_data["agent_deployment"] = {}

            settings = config_data["agent_deployment"]

            print("\n🎮 Interactive Agent Deployment Configuration")
            print("=" * 50)

            # Configure source types
            settings["deploy_system_agents"] = prompt_yes_no(
                "Deploy system agents?",
                default=settings.get("deploy_system_agents", True),
            )

            settings["deploy_local_agents"] = prompt_yes_no(
                "Deploy local project agents?",
                default=settings.get("deploy_local_agents", True),
            )

            settings["deploy_user_agents"] = prompt_yes_no(
                "Deploy user-level agents?",
                default=settings.get("deploy_user_agents", True),
            )

            # Configure version behavior
            settings["prefer_local_over_system"] = prompt_yes_no(
                "Should local agents override system agents with same ID?",
                default=settings.get("prefer_local_over_system", True),
            )

            settings["version_comparison"] = prompt_yes_no(
                "Compare versions across sources and deploy highest?",
                default=settings.get("version_comparison", True),
            )

            # Configure specific agents
            choice = prompt_choice(
                "How would you like to configure specific agents?",
                [
                    "No restrictions (all agents enabled)",
                    "Specify disabled agents",
                    "Specify enabled agents only",
                ],
            )

            if choice == "No restrictions (all agents enabled)":
                settings["enabled_agents"] = []
                settings["disabled_agents"] = []
            elif choice == "Specify disabled agents":
                # Get list of available agents
                from ...services.agents.listing_service import AgentListingService

                listing_service = AgentListingService()
                agents, _ = listing_service.list_all_agents()
                agent_ids = sorted({agent.name for agent in agents})

                if agent_ids:
                    disabled = prompt_multiselect(
                        "Select agents to disable:",
                        agent_ids,
                        default=settings.get("disabled_agents", []),
                    )
                    settings["disabled_agents"] = disabled
                    settings["enabled_agents"] = []
                else:
                    print("No agents found to configure")
            else:  # Specify enabled agents only
                from ...services.agents.listing_service import AgentListingService

                listing_service = AgentListingService()
                agents, _ = listing_service.list_all_agents()
                agent_ids = sorted({agent.name for agent in agents})

                if agent_ids:
                    enabled = prompt_multiselect(
                        "Select agents to enable (others will be disabled):",
                        agent_ids,
                        default=settings.get("enabled_agents", []),
                    )
                    settings["enabled_agents"] = enabled
                    settings["disabled_agents"] = []
                else:
                    print("No agents found to configure")

            # Save configuration
            config_data["agent_deployment"] = settings

            # Ensure parent directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)

            with config_path.open("w") as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

            print(f"\n✅ Configuration saved to {config_path}")

            # Show summary
            print("\n📋 New Configuration Summary:")
            print(
                f"  System agents: {'Enabled' if settings.get('deploy_system_agents', True) else 'Disabled'}"
            )
            print(
                f"  Local agents: {'Enabled' if settings.get('deploy_local_agents', True) else 'Disabled'}"
            )
            print(
                f"  User agents: {'Enabled' if settings.get('deploy_user_agents', True) else 'Disabled'}"
            )

            if settings.get("enabled_agents"):
                print(f"  Enabled specific: {', '.join(settings['enabled_agents'])}")
            elif settings.get("disabled_agents"):
                print(f"  Disabled specific: {', '.join(settings['disabled_agents'])}")
            else:
                print("  All agents enabled")

            return CommandResult.success_result("Interactive configuration completed")

        except KeyboardInterrupt:
            print("\n\nConfiguration cancelled.")
            return CommandResult.error_result("Configuration cancelled by user")
        except Exception as e:
            self.logger.error(f"Error in interactive configuration: {e}", exc_info=True)
            return CommandResult.error_result(
                f"Error in interactive configuration: {e}"
            )

    def _migrate_to_project(self, args) -> CommandResult:
        """Migrate user-level agents to project-level.

        DEPRECATION: User-level agents (~/.claude-mpm/agents/) are deprecated and
        will be removed in v5.0.0. This command migrates them to project-level
        (.claude-mpm/agents/) where they belong.

        Args:
            args: Command arguments with dry_run and force flags

        Returns:
            CommandResult with migration status
        """
        import shutil

        try:
            user_agents_dir = Path.home() / ".claude-mpm" / "agents"
            project_agents_dir = Path.cwd() / ".claude-mpm" / "agents"

            dry_run = getattr(args, "dry_run", False)
            force = getattr(args, "force", False)

            # Check if user agents directory exists
            if not user_agents_dir.exists():
                print("✅ No user-level agents found. Nothing to migrate.")
                return CommandResult.success_result("No user-level agents to migrate")

            # Find all user agent files
            user_agent_files = list(user_agents_dir.glob("*.json")) + list(
                user_agents_dir.glob("*.md")
            )

            if not user_agent_files:
                print("✅ No user-level agents found. Nothing to migrate.")
                return CommandResult.success_result("No user-level agents to migrate")

            # Display what we found
            print(f"\n📦 Found {len(user_agent_files)} user-level agent(s) to migrate:")
            for agent_file in user_agent_files:
                print(f"  - {agent_file.name}")

            if dry_run:
                print("\n🔍 DRY RUN: Would migrate to:")
                print(f"  → {project_agents_dir}")
                print("\nRun without --dry-run to perform the migration.")
                return CommandResult.success_result(
                    "Dry run completed",
                    data={
                        "user_agents_found": len(user_agent_files),
                        "target_directory": str(project_agents_dir),
                    },
                )

            # Create project agents directory
            project_agents_dir.mkdir(parents=True, exist_ok=True)

            # Migrate agents
            migrated = 0
            skipped = 0
            errors = []

            for agent_file in user_agent_files:
                target_file = project_agents_dir / agent_file.name

                # Check for conflicts
                if target_file.exists() and not force:
                    print(f"⚠️  Skipping {agent_file.name} (already exists in project)")
                    print("   Use --force to overwrite existing agents")
                    skipped += 1
                    continue

                try:
                    # Copy agent to project directory
                    shutil.copy2(agent_file, target_file)
                    migrated += 1
                    print(f"✅ Migrated {agent_file.name}")
                except Exception as e:
                    error_msg = f"Failed to migrate {agent_file.name}: {e}"
                    errors.append(error_msg)
                    print(f"❌ {error_msg}")

            # Summary
            print("\n📊 Migration Summary:")
            print(f"  ✅ Migrated: {migrated}/{len(user_agent_files)}")
            if skipped > 0:
                print(f"  ⏭️  Skipped: {skipped} (already exist)")
            if errors:
                print(f"  ❌ Errors: {len(errors)}")

            if migrated > 0:
                print(f"\n✅ Successfully migrated {migrated} agent(s) to:")
                print(f"   {project_agents_dir}")
                print(
                    "\n⚠️  IMPORTANT: Verify agents work correctly, then remove user-level agents:"
                )
                print(f"   rm -rf {user_agents_dir}")
                print("\n💡 Why this change?")
                print("   - Project isolation: Each project has its own agents")
                print("   - Version control: Agents can be versioned with your code")
                print("   - Team consistency: Everyone uses the same agents")

            return CommandResult.success_result(
                f"Migrated {migrated} agents",
                data={
                    "migrated": migrated,
                    "skipped": skipped,
                    "errors": errors,
                    "total": len(user_agent_files),
                },
            )

        except Exception as e:
            self.logger.error(f"Error migrating agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error migrating agents: {e}")

    def _deploy_minimal_configuration(self, args) -> CommandResult:
        """Deploy minimal configuration (6 core agents).

        Part of Phase 3 (1M-382): Agent Selection Modes.
        Deploy exactly 6 agents for basic Claude MPM workflow:
        engineer, documentation, qa, research, ops, ticketing.
        """
        try:
            from ...config.agent_sources import AgentSourceConfiguration
            from ...services.agents.agent_selection_service import AgentSelectionService
            from ...services.agents.single_tier_deployment_service import (
                SingleTierDeploymentService,
            )

            # Initialize services
            config = AgentSourceConfiguration.load()
            deployment_dir = Path.home() / ".claude" / "agents"
            deployment_service = SingleTierDeploymentService(config, deployment_dir)
            selection_service = AgentSelectionService(deployment_service)

            # Get dry_run flag
            dry_run = getattr(args, "dry_run", False)

            # Deploy minimal configuration
            print("🎯 Deploying minimal configuration (6 core agents)...")
            if dry_run:
                print("🔍 DRY RUN MODE - No agents will be deployed\n")

            result = selection_service.deploy_minimal_configuration(dry_run=dry_run)

            # Format output
            output_format = self._get_output_format(args)
            if self._is_structured_format(output_format):
                formatted = (
                    self._formatter.format_as_json(result)
                    if str(output_format).lower() == OutputFormat.JSON
                    else self._formatter.format_as_yaml(result)
                )
                print(formatted)
                return CommandResult.success_result(
                    f"Minimal configuration {result['status']}", data=result
                )

            # Text output
            print(f"\n{'=' * 60}")
            print(f"Status: {result['status'].upper()}")
            print(f"Mode: {result['mode']}")
            print(f"{'=' * 60}")
            print(
                f"\n📊 Summary: {result['deployed_count']} deployed, "
                f"{result['failed_count']} failed, {result['missing_count']} missing"
            )

            if result["deployed_agents"]:
                print(f"\n✅ Deployed agents ({len(result['deployed_agents'])}):")
                for agent in result["deployed_agents"]:
                    print(f"  • {agent}")

            if result["failed_agents"]:
                print(f"\n❌ Failed agents ({len(result['failed_agents'])}):")
                for agent in result["failed_agents"]:
                    print(f"  • {agent}")

            if result["missing_agents"]:
                print(f"\n⚠️  Missing agents ({len(result['missing_agents'])}):")
                for agent in result["missing_agents"]:
                    print(f"  • {agent}")
                print("\nThese agents are not available in configured sources.")

            if dry_run:
                print(
                    "\n💡 This was a dry run. Run without --dry-run to deploy agents."
                )

            return CommandResult.success_result(
                f"Minimal configuration {result['status']}", data=result
            )

        except Exception as e:
            self.logger.error(
                f"Error deploying minimal configuration: {e}", exc_info=True
            )
            return CommandResult.error_result(
                f"Error deploying minimal configuration: {e}"
            )

    def _deploy_auto_configure(self, args) -> CommandResult:
        """Auto-detect toolchain and deploy matching agents.

        Part of Phase 3 (1M-382): Agent Selection Modes.
        Detect project toolchain (languages, frameworks, build tools) and
        deploy matching specialized agents.
        """
        try:
            from ...config.agent_sources import AgentSourceConfiguration
            from ...services.agents.agent_selection_service import AgentSelectionService
            from ...services.agents.single_tier_deployment_service import (
                SingleTierDeploymentService,
            )

            # Initialize services
            config = AgentSourceConfiguration.load()
            deployment_dir = Path.home() / ".claude" / "agents"
            deployment_service = SingleTierDeploymentService(config, deployment_dir)
            selection_service = AgentSelectionService(deployment_service)

            # Get arguments
            project_path = getattr(args, "path", Path.cwd())
            dry_run = getattr(args, "dry_run", False)

            # Deploy auto-configure
            print(f"🔍 Auto-detecting toolchain in {project_path}...")
            if dry_run:
                print("🔍 DRY RUN MODE - No agents will be deployed\n")

            result = selection_service.deploy_auto_configure(
                project_path=project_path, dry_run=dry_run
            )

            # Format output
            output_format = self._get_output_format(args)
            if self._is_structured_format(output_format):
                formatted = (
                    self._formatter.format_as_json(result)
                    if str(output_format).lower() == OutputFormat.JSON
                    else self._formatter.format_as_yaml(result)
                )
                print(formatted)
                return CommandResult.success_result(
                    f"Auto-configure {result['status']}", data=result
                )

            # Text output
            print(f"\n{'=' * 60}")
            print(f"Status: {result['status'].upper()}")
            print(f"Mode: {result['mode']}")
            print(f"{'=' * 60}")

            # Show detected toolchain
            toolchain = result.get("toolchain", {})
            print("\n🔧 Detected Toolchain:")
            if toolchain.get("languages"):
                print(f"  Languages: {', '.join(toolchain['languages'])}")
            if toolchain.get("frameworks"):
                print(f"  Frameworks: {', '.join(toolchain['frameworks'])}")
            if toolchain.get("build_tools"):
                print(f"  Build Tools: {', '.join(toolchain['build_tools'])}")

            if not any(toolchain.values()):
                print("  (No toolchain detected)")

            # Show recommended agents
            recommended = result.get("recommended_agents", [])
            if recommended:
                print(f"\n🎯 Recommended agents ({len(recommended)}):")
                for agent in recommended:
                    print(f"  • {agent}")

            # Show deployment summary
            print(
                f"\n📊 Summary: {result['deployed_count']} deployed, "
                f"{result['failed_count']} failed, {result['missing_count']} missing"
            )

            if result.get("deployed_agents"):
                print(f"\n✅ Deployed agents ({len(result['deployed_agents'])}):")
                for agent in result["deployed_agents"]:
                    print(f"  • {agent}")

            if result.get("failed_agents"):
                print(f"\n❌ Failed agents ({len(result['failed_agents'])}):")
                for agent in result["failed_agents"]:
                    print(f"  • {agent}")

            if result.get("missing_agents"):
                print(f"\n⚠️  Missing agents ({len(result['missing_agents'])}):")
                for agent in result["missing_agents"]:
                    print(f"  • {agent}")
                print("\nThese agents are not available in configured sources.")

            if dry_run:
                print(
                    "\n💡 This was a dry run. Run without --dry-run to deploy agents."
                )

            return CommandResult.success_result(
                f"Auto-configure {result['status']}", data=result
            )

        except Exception as e:
            self.logger.error(f"Error in auto-configure: {e}", exc_info=True)
            return CommandResult.error_result(f"Error in auto-configure: {e}")

    def _list_collections(self, args) -> CommandResult:
        """List all available agent collections.

        NEW: Shows all collections with agent counts and metadata.
        Enables discovery of available agent collections before deployment.
        """
        try:
            from pathlib import Path

            from ...services.agents.deployment.remote_agent_discovery_service import (
                RemoteAgentDiscoveryService,
            )

            # Get remote agents cache directory
            cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"

            if not cache_dir.exists():
                return CommandResult.error_result(
                    "No remote agent collections found. Run 'claude-mpm agents deploy' first."
                )

            # Use RemoteAgentDiscoveryService to list collections
            remote_service = RemoteAgentDiscoveryService(cache_dir)
            collections = remote_service.list_collections()

            if not collections:
                return CommandResult.success_result(
                    "No agent collections found in cache.", data={"collections": []}
                )

            # Format output
            output_lines = ["Available Agent Collections:\n"]
            for collection in collections:
                output_lines.append(
                    f"  • {collection['collection_id']} ({collection['agent_count']} agents)"
                )

            return CommandResult.success_result(
                "\n".join(output_lines), data={"collections": collections}
            )

        except Exception as e:
            self.logger.error(f"Error listing collections: {e}", exc_info=True)
            return CommandResult.error_result(f"Error listing collections: {e}")

    def _deploy_collection(self, args) -> CommandResult:
        """Deploy all agents from a specific collection.

        NEW: Enables bulk deployment of all agents from a named collection.
        Useful for deploying entire agent sets at once.
        """
        try:
            from pathlib import Path

            from ...services.agents.deployment.multi_source_deployment_service import (
                MultiSourceAgentDeploymentService,
            )

            collection_id = args.collection_id

            # Get agents from collection
            service = MultiSourceAgentDeploymentService()
            cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"
            agents = service.get_agents_by_collection(collection_id, cache_dir)

            if not agents:
                return CommandResult.error_result(
                    f"No agents found in collection '{collection_id}'"
                )

            # Dry run mode
            if getattr(args, "dry_run", False):
                agent_names = [
                    agent.get("metadata", {}).get("name", "Unknown") for agent in agents
                ]
                output = f"Would deploy {len(agents)} agents from collection '{collection_id}':\n"
                for name in agent_names:
                    output += f"  • {name}\n"
                return CommandResult.success_result(
                    output,
                    data={"collection_id": collection_id, "agent_count": len(agents)},
                )

            # Deploy agents
            # TODO: Implement actual deployment logic using deployment service
            # For now, show what would be deployed
            return CommandResult.success_result(
                f"Deployment of collection '{collection_id}' would deploy {len(agents)} agents.\n"
                f"(Full deployment implementation pending)",
                data={
                    "collection_id": collection_id,
                    "agent_count": len(agents),
                    "status": "pending_implementation",
                },
            )

        except Exception as e:
            self.logger.error(f"Error deploying collection: {e}", exc_info=True)
            return CommandResult.error_result(f"Error deploying collection: {e}")

    def _list_by_collection(self, args) -> CommandResult:
        """List agents from a specific collection.

        NEW: Shows detailed information about agents in a collection.
        Supports multiple output formats (table, json, yaml).
        """
        try:
            import json as json_lib
            from pathlib import Path

            from ...services.agents.deployment.multi_source_deployment_service import (
                MultiSourceAgentDeploymentService,
            )

            collection_id = args.collection_id
            output_format = getattr(args, "format", "table")

            # Get agents from collection
            service = MultiSourceAgentDeploymentService()
            cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"
            agents = service.get_agents_by_collection(collection_id, cache_dir)

            if not agents:
                return CommandResult.error_result(
                    f"No agents found in collection '{collection_id}'"
                )

            # Format output based on requested format
            if output_format == "json":
                return CommandResult.success_result(
                    json_lib.dumps(agents, indent=2),
                    data={"collection_id": collection_id, "agents": agents},
                )
            if output_format == "yaml":
                try:
                    import yaml

                    return CommandResult.success_result(
                        yaml.dump(agents, default_flow_style=False),
                        data={"collection_id": collection_id, "agents": agents},
                    )
                except ImportError:
                    return CommandResult.error_result(
                        "YAML support not available (install PyYAML)"
                    )

            # Table format (default)
            output_lines = [f"Agents in collection '{collection_id}':\n"]
            for agent in agents:
                metadata = agent.get("metadata", {})
                name = metadata.get("name", "Unknown")
                description = metadata.get("description", "No description")
                version = agent.get("version", "unknown")
                output_lines.append(f"  • {name} (v{version})")
                output_lines.append(f"    {description}\n")

            return CommandResult.success_result(
                "\n".join(output_lines),
                data={"collection_id": collection_id, "agent_count": len(agents)},
            )

        except Exception as e:
            self.logger.error(f"Error listing collection agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error listing collection agents: {e}")

    def _cache_status(self, args) -> CommandResult:
        """Show git status of agent cache.

        Displays current branch, uncommitted changes, unpushed commits, and
        remote URL for the agent cache repository.
        """
        try:
            from ...services.agents.cache_git_manager import CacheGitManager

            cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"
            manager = CacheGitManager(cache_dir)

            if not manager.is_git_repo():
                print("❌ Cache is not a git repository")
                print(f"\nCache location: {cache_dir}")
                print(
                    "\n💡 This is expected if you haven't cloned the agents repository."
                )
                print("   The cache will be managed via HTTP sync instead.")
                return CommandResult.error_result("Cache is not a git repository")

            status = manager.get_status()
            output_format = self._get_output_format(args)

            if self._is_structured_format(output_format):
                formatted = (
                    self._formatter.format_as_json(status)
                    if str(output_format).lower() == OutputFormat.JSON
                    else self._formatter.format_as_yaml(status)
                )
                print(formatted)
                return CommandResult.success_result(
                    "Cache status retrieved", data=status
                )

            # Text output
            print(f"\n📁 Cache: {manager.repo_path}")
            print(f"🌿 Branch: {status.get('branch', 'unknown')}")

            if status.get("remote_url"):
                print(f"🔗 Remote: {status['remote_url']}")

            # Show sync status
            ahead = status.get("ahead", 0)
            behind = status.get("behind", 0)

            if ahead > 0:
                print(f"📤 Ahead of remote: {ahead} commit(s)")
            if behind > 0:
                print(f"📥 Behind remote: {behind} commit(s)")

            if ahead == 0 and behind == 0:
                print("✅ In sync with remote")

            # Show uncommitted changes
            uncommitted = status.get("uncommitted", [])
            if uncommitted:
                print(f"\n⚠️  Uncommitted changes: {len(uncommitted)}")
                for file in uncommitted[:10]:  # Show max 10 files
                    print(f"   - {file}")
                if len(uncommitted) > 10:
                    print(f"   ... and {len(uncommitted) - 10} more")
            else:
                print("\n✅ No uncommitted changes")

            # Overall status
            if status.get("is_clean"):
                print("\n✨ Cache is clean and up-to-date")
            else:
                print("\n💡 Run 'claude-mpm agents cache-sync' to sync with remote")

            return CommandResult.success_result("Cache status displayed", data=status)

        except Exception as e:
            self.logger.error(f"Error getting cache status: {e}", exc_info=True)
            return CommandResult.error_result(f"Error getting cache status: {e}")

    def _cache_pull(self, args) -> CommandResult:
        """Pull latest agents from remote repository."""
        try:
            from ...services.agents.cache_git_manager import CacheGitManager

            cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"
            manager = CacheGitManager(cache_dir)

            if not manager.is_git_repo():
                print("❌ Cache is not a git repository")
                return CommandResult.error_result("Cache is not a git repository")

            branch = getattr(args, "branch", "main")
            print(f"🔄 Pulling latest changes from {branch}...")

            success, msg = manager.pull_latest(branch)

            if success:
                print(f"✅ {msg}")
                return CommandResult.success_result(msg)
            print(f"❌ {msg}")
            return CommandResult.error_result(msg)

        except Exception as e:
            self.logger.error(f"Error pulling cache: {e}", exc_info=True)
            return CommandResult.error_result(f"Error pulling cache: {e}")

    def _cache_commit(self, args) -> CommandResult:
        """Commit changes to cache repository."""
        try:
            from ...services.agents.cache_git_manager import CacheGitManager

            cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"
            manager = CacheGitManager(cache_dir)

            if not manager.is_git_repo():
                print("❌ Cache is not a git repository")
                return CommandResult.error_result("Cache is not a git repository")

            # Get commit message from args
            message = getattr(args, "message", None)
            if not message:
                # Default message
                message = "feat: update agents from local development"

            print("💾 Committing changes...")
            success, msg = manager.commit_changes(message)

            if success:
                print(f"✅ {msg}")
                print(f"\n💡 Commit message: {message}")
                return CommandResult.success_result(msg)
            print(f"❌ {msg}")
            return CommandResult.error_result(msg)

        except Exception as e:
            self.logger.error(f"Error committing cache changes: {e}", exc_info=True)
            return CommandResult.error_result(f"Error committing cache changes: {e}")

    def _cache_push(self, args) -> CommandResult:
        """Push local agent changes to remote."""
        try:
            from ...services.agents.cache_git_manager import CacheGitManager

            cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"
            manager = CacheGitManager(cache_dir)

            if not manager.is_git_repo():
                print("❌ Cache is not a git repository")
                return CommandResult.error_result("Cache is not a git repository")

            # Check for uncommitted changes
            if manager.has_uncommitted_changes():
                print("⚠️  You have uncommitted changes.")
                print("\n💡 Commit changes first with:")
                print("   claude-mpm agents cache-commit --message 'your message'")

                # Ask if user wants to commit first
                auto_commit = getattr(args, "auto_commit", False)
                if auto_commit:
                    print("\n📝 Auto-committing changes...")
                    success, msg = manager.commit_changes("feat: update agents")
                    if not success:
                        print(f"❌ Commit failed: {msg}")
                        return CommandResult.error_result(f"Commit failed: {msg}")
                    print(f"✅ {msg}")
                else:
                    return CommandResult.error_result(
                        "Uncommitted changes detected. Commit first or use --auto-commit"
                    )

            # Push changes
            branch = getattr(args, "branch", "main")
            print(f"📤 Pushing changes to {branch}...")

            success, msg = manager.push_changes(branch)

            if success:
                print(f"✅ {msg}")
                return CommandResult.success_result(msg)
            print(f"❌ {msg}")
            return CommandResult.error_result(msg)

        except Exception as e:
            self.logger.error(f"Error pushing cache: {e}", exc_info=True)
            return CommandResult.error_result(f"Error pushing cache: {e}")

    def _cache_sync(self, args) -> CommandResult:
        """Full cache sync: pull, commit (if needed), push."""
        try:
            from ...services.agents.cache_git_manager import CacheGitManager

            cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"
            manager = CacheGitManager(cache_dir)

            if not manager.is_git_repo():
                print("❌ Cache is not a git repository")
                return CommandResult.error_result("Cache is not a git repository")

            print("🔄 Syncing cache with remote...\n")

            success, msg = manager.sync_with_remote()

            # Print detailed sync message
            print(msg)

            if success:
                print("\n✨ Cache sync complete!")
                return CommandResult.success_result("Cache synced successfully")

            print("\n❌ Cache sync failed. See details above.")
            return CommandResult.error_result("Cache sync failed")

        except Exception as e:
            self.logger.error(f"Error syncing cache: {e}", exc_info=True)
            return CommandResult.error_result(f"Error syncing cache: {e}")


def manage_agents(args):
    """
    Main entry point for agent management commands.

    This function maintains backward compatibility while using the new AgentCommand pattern.
    """
    command = AgentsCommand()
    result = command.execute(args)

    # Print result if structured output format is requested
    if _is_structured_output(args):
        command.print_result(result, args)

    return result.exit_code
