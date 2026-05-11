"""
Deployment configuration handler for agents command.

WHY: Extracted from agents.py to keep the main command file focused on routing.
This handler manages agent deployment configuration (configure / migrate).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ..shared import CommandResult

if TYPE_CHECKING:
    from .agents import AgentsCommand


class AgentConfigureHandler:
    """Handles deployment configuration and migration commands."""

    def __init__(self, cmd: AgentsCommand) -> None:
        self.cmd = cmd

    @property
    def _logger(self):
        return self.cmd.logger

    def configure_deployment(self, args) -> CommandResult:
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

                loader = DeploymentConfigLoader(self._logger)
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
                return self.configure_deployment_interactive(config_path)

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

            return CommandResult.success_result("Deployment configuration displayed")

        except Exception as e:
            self._logger.error(f"Error configuring deployment: {e}", exc_info=True)
            return CommandResult.error_result(f"Error configuring deployment: {e}")

    def configure_deployment_interactive(self, config_path: Path) -> CommandResult:
        """Interactive mode for configuring agent deployment."""
        try:
            import questionary
            import yaml

            def prompt_yes_no(question: str, default: bool = True) -> bool:
                result = questionary.confirm(question, default=default).ask()
                return bool(result)

            def prompt_choice(question: str, choices: list[str]) -> str:
                result = questionary.select(question, choices=choices).ask()
                return str(result) if result is not None else choices[0]

            def prompt_multiselect(
                question: str,
                choices: list[str],
                default: list[str] | None = None,
            ) -> list[str]:
                checked_defaults = set(default or [])
                choice_objects = [
                    questionary.Choice(c, checked=(c in checked_defaults))
                    for c in choices
                ]
                result = questionary.checkbox(question, choices=choice_objects).ask()
                return list(result) if result is not None else []

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
                from ...services.cli.agent_listing_service import AgentListingService

                listing_service = AgentListingService()
                agents, _ = listing_service.list_deployed_agents()
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
                from ...services.cli.agent_listing_service import AgentListingService

                listing_service = AgentListingService()
                agents, _ = listing_service.list_deployed_agents()
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
            self._logger.error(
                f"Error in interactive configuration: {e}", exc_info=True
            )
            return CommandResult.error_result(
                f"Error in interactive configuration: {e}"
            )

    def migrate_to_project(self, args) -> CommandResult:
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
            self._logger.error(f"Error migrating agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error migrating agents: {e}")
