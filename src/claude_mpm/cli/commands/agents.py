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

from pathlib import Path

from ...constants import AgentCommands
from ...core.enums import OutputFormat
from ...services.cli.agent_cleanup_service import AgentCleanupService
from ...services.cli.agent_dependency_service import AgentDependencyService
from ...services.cli.agent_listing_service import AgentListingService
from ...services.cli.agent_output_formatter import AgentOutputFormatter
from ...services.cli.agent_validation_service import AgentValidationService
from ..shared import AgentCommand, CommandResult
from ..utils import get_agent_versions_display  # re-exported for test patching
from .agents_cleanup import handle_agents_cleanup

__all__ = ["AgentsCommand", "get_agent_versions_display", "manage_agents"]


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
        """Show current agent versions as default action (delegated)."""
        from .agents_list import AgentListingHandler

        return AgentListingHandler(self).show_agent_versions(args)

    def _list_agents(self, args) -> CommandResult:
        """List available or deployed agents (delegated)."""
        from .agents_list import AgentListingHandler

        return AgentListingHandler(self).list_agents(args)

    def _list_system_agents(self, args) -> CommandResult:
        """List available agent templates (delegated)."""
        from .agents_list import AgentListingHandler

        return AgentListingHandler(self).list_system_agents(args)

    def _list_deployed_agents(self, args) -> CommandResult:
        """List deployed agents (delegated)."""
        from .agents_list import AgentListingHandler

        return AgentListingHandler(self).list_deployed_agents(args)

    def _list_agents_by_tier(self, args) -> CommandResult:
        """List agents grouped by tier/precedence (delegated)."""
        from .agents_list import AgentListingHandler

        return AgentListingHandler(self).list_agents_by_tier(args)

    def _list_available_from_sources(self, args) -> CommandResult:
        """List available agents from configured git sources (delegated)."""
        from .agents_list import AgentListingHandler

        return AgentListingHandler(self).list_available_from_sources(args)

    def _discover_agents(self, args) -> CommandResult:
        """Discover agents with rich filtering (delegated)."""
        from .agents_list import AgentListingHandler

        return AgentListingHandler(self).discover_agents(args)

    def _deploy_agents(self, args, force=False) -> CommandResult:
        """Deploy agents using two-phase sync: cache then deploy (delegated)."""
        from .agents_deploy import AgentDeployHandler

        return AgentDeployHandler(self).deploy_agents(args, force=force)

    def _deploy_preset(self, args) -> CommandResult:
        """Deploy agents by preset name (delegated)."""
        from .agents_deploy import AgentDeployHandler

        return AgentDeployHandler(self).deploy_preset(args)

    def _clean_agents(self, args) -> CommandResult:
        """Clean deployed agents (delegated)."""
        from .agents_fix import AgentFixHandler

        return AgentFixHandler(self).clean_agents(args)

    def _view_agent(self, args) -> CommandResult:
        """View details of a specific agent (delegated)."""
        from .agents_fix import AgentFixHandler

        return AgentFixHandler(self).view_agent(args)

    def _fix_agents(self, args) -> CommandResult:
        """Fix agent frontmatter issues (delegated)."""
        from .agents_fix import AgentFixHandler

        return AgentFixHandler(self).fix_agents(args)

    def _check_agent_dependencies(self, args) -> CommandResult:
        """Check agent dependencies (delegated)."""
        from .agents_deps import AgentDepsHandler

        return AgentDepsHandler(self).check_agent_dependencies(args)

    def _install_agent_dependencies(self, args) -> CommandResult:
        """Install agent dependencies (delegated)."""
        from .agents_deps import AgentDepsHandler

        return AgentDepsHandler(self).install_agent_dependencies(args)

    def _list_agent_dependencies(self, args) -> CommandResult:
        """List agent dependencies (delegated)."""
        from .agents_deps import AgentDepsHandler

        return AgentDepsHandler(self).list_agent_dependencies(args)

    def _fix_agent_dependencies(self, args) -> CommandResult:
        """Fix agent dependency issues (delegated)."""
        from .agents_deps import AgentDepsHandler

        return AgentDepsHandler(self).fix_agent_dependencies(args)

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
        """Deploy minimal configuration (6 core agents) (delegated)."""
        from .agents_deploy import AgentDeployHandler

        return AgentDeployHandler(self).deploy_minimal_configuration(args)

    def _deploy_auto_configure(self, args) -> CommandResult:
        """Auto-detect toolchain and deploy matching agents (delegated)."""
        from .agents_deploy import AgentDeployHandler

        return AgentDeployHandler(self).deploy_auto_configure(args)

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
