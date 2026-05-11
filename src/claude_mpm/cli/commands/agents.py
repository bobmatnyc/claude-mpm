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

    def _filter_agents(self, agents, filter_term: str):
        """
        Filter agents by name, type, category, or tags (case-insensitive).

        Args:
            agents: List of AgentInfo objects
            filter_term: Filter string to match

        Returns:
            Filtered list of agents
        """
        if not filter_term:
            return agents

        filter_lower = filter_term.lower()
        filtered = []

        for agent in agents:
            # Check name
            if filter_lower in agent.name.lower():
                filtered.append(agent)
                continue

            # Check type
            if filter_lower in agent.type.lower():
                filtered.append(agent)
                continue

            # Check specializations (tags/category)
            if agent.specializations:
                if any(filter_lower in spec.lower() for spec in agent.specializations):
                    filtered.append(agent)
                    continue

        return filtered

    def validate_args(self, args) -> str | None:
        """Validate command arguments."""
        # Most agent commands are optional, so basic validation
        _ = args
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
                "cleanup": self._handle_cleanup_command,
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

            # Apply filter if provided
            filter_term = getattr(args, "filter", None)
            if filter_term:
                agents = self._filter_agents(agents, filter_term)

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

            # Apply filter if provided
            filter_term = getattr(args, "filter", None)
            if filter_term:
                agents = self._filter_agents(agents, filter_term)

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
            from ...services.agents.sync_orchestrator import AgentSyncOrchestrator

            # Sync default source via orchestrator (Phase 3 unification).
            # Scope to default repo only to preserve pre-refactor behaviour
            # where GitSourceSyncService() only synced bobmatnyc/claude-mpm-agents.
            source_config = AgentSourceConfiguration.load()
            default_repos = [
                r
                for r in source_config.get_enabled_repositories()
                if "claude-mpm-agents" in r.identifier
            ][:1]
            orchestrator = AgentSyncOrchestrator(show_progress=False)
            orch_result = orchestrator.sync(force=False, repos=default_repos)

            if not orch_result.enabled:
                message = (
                    "No agent sources configured.\n\n"
                    "Configure sources with:\n"
                    "  claude-mpm agent-source add <url>\n\n"
                    "Example:\n"
                    "  claude-mpm agent-source add https://github.com/owner/repo/agents"
                )
                print(message)
                return CommandResult.error_result("No agent sources configured")

            sync_results = orch_result.raw_results

            # Get source filter from args
            source_filter = getattr(args, "source", None)

            # List all cached agents (need GitSourceManager for discovery)
            manager = GitSourceManager()
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

            from ...config.agent_sources import AgentSourceConfiguration
            from ...services.agents.sources.git_source_sync_service import (
                GitSourceSyncService,
            )
            from ...services.agents.sync_orchestrator import AgentSyncOrchestrator

            project_dir = Path.cwd()

            self.logger.info("Phase 1: Syncing agents to cache...")

            # Phase 3 unification: use orchestrator for sync step.
            # INVARIANT: `agents deploy` is NEVER TTL-gated -- always pass
            # force=True when the user specifies --force.
            # Scope to default repo only -- the old GitSourceSyncService()
            # constructor only knew about bobmatnyc/claude-mpm-agents.
            source_config = AgentSourceConfiguration.load()
            default_repos = [
                r
                for r in source_config.get_enabled_repositories()
                if "claude-mpm-agents" in r.identifier
            ][:1]
            orchestrator = AgentSyncOrchestrator(show_progress=True)
            orch_result = orchestrator.sync(force=force, repos=default_repos)

            if not orch_result.enabled or (
                orch_result.sources_synced == 0 and orch_result.sources_failed > 0
            ):
                error_msg = (
                    f"No agents synced"
                    f"{f'; {orch_result.sources_failed} source(s) failed' if orch_result.sources_failed else ''}"
                )
                if orch_result.errors:
                    error_msg += f": {orch_result.errors[0]}"
                self.logger.error(f"Sync failed: {error_msg}")
                return CommandResult.error_result(f"Sync failed: {error_msg}")

            self.logger.info(
                f"Phase 1 complete: {orch_result.total_downloaded + orch_result.cache_hits} agents in cache"
                f" ({orch_result.total_downloaded} downloaded, {orch_result.cache_hits} cached)"
            )
            self.logger.info(f"Phase 2: Deploying agents to {project_dir}...")

            # Deploy from cache to project directory (deploy stays with GitSourceSyncService)
            git_sync = GitSourceSyncService()
            deploy_result = git_sync.deploy_agents_to_project(
                project_dir=project_dir,
                agent_list=None,  # Deploy all cached agents
                force=force,
            )

            # Format combined results for output
            agent_count = orch_result.total_downloaded + orch_result.cache_hits
            combined_result = {
                "deployed_count": len(deploy_result.get("deployed", []))
                + len(deploy_result.get("updated", [])),
                "deployed": deploy_result.get("deployed", []),
                "updated": deploy_result.get("updated", []),
                "skipped": deploy_result.get("skipped", []),
                "errors": deploy_result.get("failed", []),
                "target_dir": deploy_result.get("deployment_dir", ""),
                "sync_info": {
                    "cached_agents": agent_count,
                    "cache_dir": str(git_sync.cache_dir),
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
                    "sync_result": {
                        "sources_synced": orch_result.sources_synced,
                        "total_downloaded": orch_result.total_downloaded,
                        "cache_hits": orch_result.cache_hits,
                    },
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
        """Create a new local agent template (delegated)."""
        from .agents_local import AgentLocalHandler

        return AgentLocalHandler(self).create_local_agent(args)

    def _edit_local_agent(self, args) -> CommandResult:
        """Edit a local agent template (delegated)."""
        from .agents_local import AgentLocalHandler

        return AgentLocalHandler(self).edit_local_agent(args)

    def _delete_local_agent(self, args) -> CommandResult:
        """Delete local agent templates (delegated)."""
        from .agents_local import AgentLocalHandler

        return AgentLocalHandler(self).delete_local_agent(args)

    def _manage_local_agents(self, args) -> CommandResult:
        """Redirect to main configuration interface (DEPRECATED, delegated)."""
        from .agents_local import AgentLocalHandler

        return AgentLocalHandler(self).manage_local_agents(args)

    def _configure_deployment(self, args) -> CommandResult:
        """Configure agent deployment settings (delegated)."""
        from .agents_configure import AgentConfigureHandler

        return AgentConfigureHandler(self).configure_deployment(args)

    def _configure_deployment_interactive(self, config_path: Path) -> CommandResult:
        """Interactive mode for configuring agent deployment (delegated)."""
        from .agents_configure import AgentConfigureHandler

        return AgentConfigureHandler(self).configure_deployment_interactive(config_path)

    def _migrate_to_project(self, args) -> CommandResult:
        """Migrate user-level agents to project-level (delegated)."""
        from .agents_configure import AgentConfigureHandler

        return AgentConfigureHandler(self).migrate_to_project(args)

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
        """List all available agent collections (delegated)."""
        from .agents_collections import AgentCollectionsHandler

        return AgentCollectionsHandler(self).list_collections(args)

    def _deploy_collection(self, args) -> CommandResult:
        """Deploy all agents from a specific collection (delegated)."""
        from .agents_collections import AgentCollectionsHandler

        return AgentCollectionsHandler(self).deploy_collection(args)

    def _list_by_collection(self, args) -> CommandResult:
        """List agents from a specific collection (delegated)."""
        from .agents_collections import AgentCollectionsHandler

        return AgentCollectionsHandler(self).list_by_collection(args)

    def _cache_status(self, args) -> CommandResult:
        """Show git status of agent cache (delegated to AgentCacheHandler)."""
        from .agents_cache import AgentCacheHandler

        return AgentCacheHandler(self).cache_status(args)

    def _cache_pull(self, args) -> CommandResult:
        """Pull latest agents from remote repository (delegated)."""
        from .agents_cache import AgentCacheHandler

        return AgentCacheHandler(self).cache_pull(args)

    def _cache_commit(self, args) -> CommandResult:
        """Commit changes to cache repository (delegated)."""
        from .agents_cache import AgentCacheHandler

        return AgentCacheHandler(self).cache_commit(args)

    def _cache_push(self, args) -> CommandResult:
        """Push local agent changes to remote (delegated)."""
        from .agents_cache import AgentCacheHandler

        return AgentCacheHandler(self).cache_push(args)

    def _cache_sync(self, args) -> CommandResult:
        """Full cache sync: pull, commit (if needed), push (delegated)."""
        from .agents_cache import AgentCacheHandler

        return AgentCacheHandler(self).cache_sync(args)


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
