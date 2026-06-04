"""
Listing / discovery handler for agents command.

WHY: Extracted from agents.py to keep the main command file focused on routing.
This handler manages all agent listing/discovery commands: show versions,
list (system/deployed/by-tier), list available from sources, and discover.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ...core.enums import OutputFormat
from ..shared import CommandResult

if TYPE_CHECKING:
    from .agents import AgentsCommand


class AgentListingHandler:
    """Handles agent listing and discovery commands."""

    def __init__(self, cmd: AgentsCommand) -> None:
        self.cmd = cmd

    @property
    def _logger(self):
        return self.cmd.logger

    def show_agent_versions(self, args) -> CommandResult:
        """Show current agent versions as default action."""
        try:
            # Import via the parent agents module so tests can patch
            # `claude_mpm.cli.commands.agents.get_agent_versions_display`.
            from . import agents as _agents_module

            agent_versions = _agents_module.get_agent_versions_display()

            output_format = self.cmd._get_output_format(args)
            if self.cmd._is_structured_format(output_format):
                # Parse the agent versions display into structured data
                if agent_versions:
                    data = {"agent_versions": agent_versions, "has_agents": True}
                    formatted = (
                        self.cmd._formatter.format_as_json(data)
                        if str(output_format).lower() == OutputFormat.JSON
                        else self.cmd._formatter.format_as_yaml(data)
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
                    self.cmd._formatter.format_as_json(data)
                    if str(output_format).lower() == OutputFormat.JSON
                    else self.cmd._formatter.format_as_yaml(data)
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
            self._logger.error(f"Error getting agent versions: {e}", exc_info=True)
            return CommandResult.error_result(f"Error getting agent versions: {e}")

    def list_agents(self, args) -> CommandResult:
        """List available or deployed agents."""
        try:
            output_format = self.cmd._get_output_format(args)

            if hasattr(args, "by_tier") and args.by_tier:
                return self.list_agents_by_tier(args)
            if getattr(args, "system", False):
                return self.list_system_agents(args)
            if getattr(args, "deployed", False):
                return self.list_deployed_agents(args)
            # Default: show usage
            usage_msg = "Use --system to list system agents, --deployed to list deployed agents, or --by-tier to group by precedence"

            if self.cmd._is_structured_format(output_format):
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
            self._logger.error(f"Error listing agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error listing agents: {e}")

    def list_system_agents(self, args) -> CommandResult:
        """List available agent templates."""
        try:
            verbose = getattr(args, "verbose", False)
            agents = self.cmd.listing_service.list_system_agents(verbose=verbose)

            # Apply filter if provided
            filter_term = getattr(args, "filter", None)
            if filter_term:
                agents = self.cmd._filter_agents(agents, filter_term)

            output_format = self.cmd._get_output_format(args)
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
                    "source": agent.source,
                }
                for agent in agents
            ]

            formatted = self.cmd._formatter.format_agent_list(
                agents_data, output_format=output_format, verbose=verbose, quiet=quiet
            )
            print(formatted)

            return CommandResult.success_result(
                f"Listed {len(agents)} agent templates",
                data={"agents": agents_data, "count": len(agents)},
            )

        except Exception as e:
            self._logger.error(f"Error listing system agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error listing system agents: {e}")

    def list_deployed_agents(self, args) -> CommandResult:
        """List deployed agents."""
        try:
            verbose = getattr(args, "verbose", False)
            agents, warnings = self.cmd.listing_service.list_deployed_agents(
                verbose=verbose
            )

            # Apply filter if provided
            filter_term = getattr(args, "filter", None)
            if filter_term:
                agents = self.cmd._filter_agents(agents, filter_term)

            output_format = self.cmd._get_output_format(args)
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
                    "source": agent.source,
                }
                for agent in agents
            ]

            # Format the agent list
            formatted = self.cmd._formatter.format_agent_list(
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
            self._logger.error(f"Error listing deployed agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error listing deployed agents: {e}")

    def list_agents_by_tier(self, args) -> CommandResult:
        """List agents grouped by tier/precedence."""
        try:
            tier_info = self.cmd.listing_service.list_agents_by_tier()
            output_format = self.cmd._get_output_format(args)

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

            formatted = self.cmd._formatter.format_agents_by_tier(
                agents_by_tier, output_format=output_format
            )
            print(formatted)

            return CommandResult.success_result(
                "Agents listed by tier", data=agents_by_tier
            )

        except Exception as e:
            self._logger.error(f"Error listing agents by tier: {e}", exc_info=True)
            return CommandResult.error_result(f"Error listing agents by tier: {e}")

    def list_available_from_sources(self, args) -> CommandResult:
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
            self._logger.error(f"Error listing available agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error listing available agents: {e}")

    def discover_agents(self, args) -> CommandResult:
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
            self._logger.error(f"Error discovering agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error discovering agents: {e}")
