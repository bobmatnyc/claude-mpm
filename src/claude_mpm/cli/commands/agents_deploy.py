"""
Deployment handler for agents command.

WHY: Extracted from agents.py to keep the main command file focused on routing.
This handler manages agent deployment commands: standard deploy, preset
deploy, minimal configuration deploy, and auto-configure deploy.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ...core.enums import OutputFormat
from ..shared import CommandResult

if TYPE_CHECKING:
    from .agents import AgentsCommand


class AgentDeployHandler:
    """Handles agent deployment commands."""

    def __init__(self, cmd: AgentsCommand) -> None:
        self.cmd = cmd

    @property
    def _logger(self):
        return self.cmd.logger

    def deploy_agents(self, args, force=False) -> CommandResult:
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
                return self.deploy_preset(args)

            from ...config.agent_sources import AgentSourceConfiguration
            from ...services.agents.sources.git_source_sync_service import (
                GitSourceSyncService,
            )
            from ...services.agents.sync_orchestrator import AgentSyncOrchestrator

            project_dir = Path.cwd()

            self._logger.info("Phase 1: Syncing agents to cache...")

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
                self._logger.error(f"Sync failed: {error_msg}")
                return CommandResult.error_result(f"Sync failed: {error_msg}")

            self._logger.info(
                f"Phase 1 complete: {orch_result.total_downloaded + orch_result.cache_hits} agents in cache"
                f" ({orch_result.total_downloaded} downloaded, {orch_result.cache_hits} cached)"
            )
            self._logger.info(f"Phase 2: Deploying agents to {project_dir}...")

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

            output_format = self.cmd._get_output_format(args)
            verbose = getattr(args, "verbose", False)

            formatted = self.cmd._formatter.format_deployment_result(
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
            self._logger.error(f"Error deploying agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error deploying agents: {e}")

    def deploy_preset(self, args) -> CommandResult:
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
            self._logger.error(f"Error deploying preset: {e}", exc_info=True)
            print(f"\n❌ Error deploying preset: {e}")
            return CommandResult.error_result(f"Error deploying preset: {e}")

    def deploy_minimal_configuration(self, args) -> CommandResult:
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
            output_format = self.cmd._get_output_format(args)
            if self.cmd._is_structured_format(output_format):
                formatted = (
                    self.cmd._formatter.format_as_json(result)
                    if str(output_format).lower() == OutputFormat.JSON
                    else self.cmd._formatter.format_as_yaml(result)
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
            self._logger.error(
                f"Error deploying minimal configuration: {e}", exc_info=True
            )
            return CommandResult.error_result(
                f"Error deploying minimal configuration: {e}"
            )

    def deploy_auto_configure(self, args) -> CommandResult:
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
            output_format = self.cmd._get_output_format(args)
            if self.cmd._is_structured_format(output_format):
                formatted = (
                    self.cmd._formatter.format_as_json(result)
                    if str(output_format).lower() == OutputFormat.JSON
                    else self.cmd._formatter.format_as_yaml(result)
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
            self._logger.error(f"Error in auto-configure: {e}", exc_info=True)
            return CommandResult.error_result(f"Error in auto-configure: {e}")
