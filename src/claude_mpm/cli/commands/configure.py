"""
Interactive configuration management command for claude-mpm CLI.

WHY: Users need an intuitive, interactive way to manage agent configurations,
edit templates, and configure behavior files without manually editing JSON/YAML files.

DESIGN DECISIONS:
- Use Rich for modern TUI with menus, tables, and panels
- Support both project-level and user-level configurations
- Provide non-interactive options for scripting
- Allow direct navigation to specific sections
"""

from pathlib import Path

from questionary import Style
from rich.console import Console
from rich.prompt import Confirm, Prompt

from ...core.config import Config
from ...core.deployment_context import DeploymentContext
from ...core.unified_config import UnifiedConfig
from ...services.agents.agent_recommendation_service import AgentRecommendationService
from ...services.version_service import VersionService
from ...utils.console import console as default_console
from ..shared import BaseCommand, CommandResult
from .agent_state_manager import SimpleAgentManager
from .configure_agent_display import AgentDisplay
from .configure_behavior_manager import BehaviorManager
from .configure_hook_manager import HookManager
from .configure_models import AgentConfig
from .configure_navigation import ConfigNavigation
from .configure_persistence import ConfigPersistence
from .configure_startup_manager import StartupManager
from .configure_template_editor import TemplateEditor
from .configure_validators import (
    parse_id_selection,
    validate_args as validate_configure_args,
)


class ConfigureCommand(BaseCommand):
    """Interactive configuration management command."""

    # Questionary style optimized for dark terminals (WCAG AAA compliant)
    QUESTIONARY_STYLE = Style(
        [
            ("selected", "fg:#e0e0e0 bold"),  # Light gray - excellent readability
            ("pointer", "fg:#ffd700 bold"),  # Gold/yellow - highly visible pointer
            ("highlighted", "fg:#e0e0e0"),  # Light gray - clear hover state
            ("question", "fg:#e0e0e0 bold"),  # Light gray bold - prominent questions
            ("checkbox", "fg:#00ff00"),  # Green - for checked boxes
            (
                "checkbox-selected",
                "fg:#00ff00 bold",
            ),  # Green bold - for checked selected boxes
        ]
    )

    def __init__(self):
        super().__init__("configure")
        self.console = default_console
        self.version_service = VersionService()
        self.current_scope = "project"
        self.project_dir = Path.cwd()
        self._ctx = DeploymentContext.from_project(self.project_dir)
        self.agent_manager = None
        self.hook_manager = HookManager(self.console)
        self.behavior_manager = None  # Initialized when scope is set
        self._agent_display = None  # Lazy-initialized
        self._persistence = None  # Lazy-initialized
        self._navigation = None  # Lazy-initialized
        self._template_editor = None  # Lazy-initialized
        self._startup_manager = None  # Lazy-initialized
        self._recommendation_service = None  # Lazy-initialized
        self._unified_config = None  # Lazy-initialized

    def validate_args(self, args) -> str | None:
        """Validate command arguments."""
        return validate_configure_args(args)

    @property
    def agent_display(self) -> AgentDisplay:
        """Lazy-initialize agent display handler."""
        if self._agent_display is None:
            if self.agent_manager is None:
                raise RuntimeError(
                    "agent_manager must be initialized before agent_display"
                )
            self._agent_display = AgentDisplay(
                self.console,
                self.agent_manager,
                self._get_agent_template_path,
                self._display_header,
            )
        return self._agent_display

    @property
    def persistence(self) -> ConfigPersistence:
        """Lazy-initialize persistence handler."""
        if self._persistence is None:
            # Note: agent_manager might be None for version_info calls
            self._persistence = ConfigPersistence(
                self.console,
                self.version_service,
                self.agent_manager,  # Can be None for version operations
                self._get_agent_template_path,
                self._display_header,
                self.current_scope,
                self.project_dir,
            )
        return self._persistence

    @property
    def navigation(self) -> ConfigNavigation:
        """Lazy-initialize navigation handler."""
        if self._navigation is None:
            self._navigation = ConfigNavigation(self.console, self.project_dir)
            # Sync scope from main command
            self._navigation.current_scope = self.current_scope
        return self._navigation

    @property
    def template_editor(self) -> TemplateEditor:
        """Lazy-initialize template editor."""
        if self._template_editor is None:
            if self.agent_manager is None:
                raise RuntimeError(
                    "agent_manager must be initialized before template_editor"
                )
            self._template_editor = TemplateEditor(
                self.console, self.agent_manager, self.current_scope, self.project_dir
            )
        return self._template_editor

    @property
    def startup_manager(self) -> StartupManager:
        """Lazy-initialize startup manager."""
        if self._startup_manager is None:
            if self.agent_manager is None:
                raise RuntimeError(
                    "agent_manager must be initialized before startup_manager"
                )
            self._startup_manager = StartupManager(
                self.agent_manager,
                self.console,
                self.current_scope,
                self.project_dir,
                self._display_header,
            )
        return self._startup_manager

    @property
    def recommendation_service(self) -> AgentRecommendationService:
        """Lazy-initialize recommendation service."""
        if self._recommendation_service is None:
            self._recommendation_service = AgentRecommendationService()
        return self._recommendation_service

    @property
    def unified_config(self) -> UnifiedConfig:
        """Lazy-initialize unified config."""
        if self._unified_config is None:
            try:
                self._unified_config = UnifiedConfig()
            except Exception as e:
                self.logger.warning(f"Failed to load unified config: {e}")
                # Fallback to default config
                self._unified_config = UnifiedConfig()
        return self._unified_config

    def run(self, args) -> CommandResult:
        """Execute the configure command."""
        # Set configuration scope
        self.current_scope = getattr(args, "scope", "project")
        if getattr(args, "project_dir", None):
            self.project_dir = Path(args.project_dir)

        # Initialize agent manager and behavior manager with appropriate config directory
        if self.current_scope == "user":
            self._ctx = DeploymentContext.from_user()
        else:
            self._ctx = DeploymentContext.from_project(self.project_dir)
        config_dir = self._ctx.config_dir
        self.agent_manager = SimpleAgentManager(config_dir)
        self.behavior_manager = BehaviorManager(
            config_dir, self.current_scope, self.console
        )

        # Disable colors if requested
        if getattr(args, "no_colors", False):
            self.console = Console(color_system=None)

        # Handle non-interactive options first
        if getattr(args, "list_agents", False):
            return self._list_agents_non_interactive()

        if getattr(args, "enable_agent", None):
            return self._enable_agent_non_interactive(args.enable_agent)

        if getattr(args, "disable_agent", None):
            return self._disable_agent_non_interactive(args.disable_agent)

        if getattr(args, "export_config", None):
            return self._export_config(args.export_config)

        if getattr(args, "import_config", None):
            return self._import_config(args.import_config)

        if getattr(args, "version_info", False):
            return self._show_version_info()

        # Handle hook installation
        if getattr(args, "install_hooks", False):
            return self._install_hooks(force=getattr(args, "force", False))

        if getattr(args, "verify_hooks", False):
            return self._verify_hooks()

        if getattr(args, "uninstall_hooks", False):
            return self._uninstall_hooks()

        # Handle direct navigation options
        if getattr(args, "agents", False):
            return self._run_agent_management()

        if getattr(args, "templates", False):
            return self._run_template_editing()

        if getattr(args, "behaviors", False):
            return self._run_behavior_management()

        if getattr(args, "startup", False):
            return self._run_startup_configuration()

        # Launch interactive TUI
        return self._run_interactive_tui(args)

    def _run_interactive_tui(self, args) -> CommandResult:
        """Run the main interactive menu interface."""
        # Rich-based menu interface
        try:
            self.console.clear()

            while True:
                # Display main menu
                self._display_header()
                choice = self._show_main_menu()

                if choice == "1":
                    self._manage_agents()
                elif choice == "2":
                    self._manage_skills()
                elif choice == "3":
                    self._edit_templates()
                elif choice == "4":
                    self._manage_behaviors()
                elif choice == "5":
                    # If user saves and wants to proceed to startup, exit the configurator
                    if self._manage_startup_configuration():
                        self.console.print(
                            "\n[green]Configuration saved. Exiting configurator...[/green]"
                        )
                        break
                elif choice == "6":
                    self._switch_scope()
                elif choice == "7":
                    self._show_version_info_interactive()
                elif choice == "l":
                    # Check for pending agent changes
                    if self.agent_manager and self.agent_manager.has_pending_changes():
                        should_save = Confirm.ask(
                            "[yellow]You have unsaved agent changes. Save them before launching?[/yellow]",
                            default=True,
                        )
                        if should_save:
                            self.agent_manager.commit_deferred_changes()
                            self.console.print("[green]✓ Agent changes saved[/green]")
                        else:
                            self.agent_manager.discard_deferred_changes()
                            self.console.print(
                                "[yellow]⚠ Agent changes discarded[/yellow]"
                            )

                    # Save all configuration
                    self.console.print("\n[cyan]Saving configuration...[/cyan]")
                    if self._save_all_configuration():
                        # Launch Claude MPM (this will replace the process if successful)
                        self._launch_claude_mpm()
                        # If execvp fails, we'll return here and break
                        break
                    self.console.print(
                        "[red]✗ Failed to save configuration. Not launching.[/red]"
                    )
                    Prompt.ask("\nPress Enter to continue")
                elif choice == "q":
                    self.console.print(
                        "\n[green]Configuration complete. Goodbye![/green]"
                    )
                    break
                else:
                    self.console.print("[red]Invalid choice. Please try again.[/red]")

            return CommandResult.success_result("Configuration completed")

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Configuration cancelled.[/yellow]")
            return CommandResult.success_result("Configuration cancelled")
        except Exception as e:
            self.logger.error(f"Configuration error: {e}", exc_info=True)
            return CommandResult.error_result(f"Configuration failed: {e}")

    def _display_header(self) -> None:
        """Display the TUI header."""
        # Sync scope to navigation before display
        self.navigation.current_scope = self.current_scope
        self.navigation.display_header()

    def _show_main_menu(self) -> str:
        """Show the main menu and get user choice."""
        # Sync scope to navigation before display
        self.navigation.current_scope = self.current_scope
        return self.navigation.show_main_menu()

    def _manage_agents(self) -> None:
        """Enhanced agent management (delegated)."""
        from .configure_agent_management import AgentManagementHandler

        AgentManagementHandler(self).manage_agents()

    def _load_agents_with_spinner(self) -> list[AgentConfig]:
        """Load agents with loading indicator (delegated)."""
        from .configure_agent_management import AgentManagementHandler

        return AgentManagementHandler(self).load_agents_with_spinner()

    def _display_agent_sources_and_list(self, agents: list[AgentConfig]) -> None:
        """Display agent sources and agent list (delegated)."""
        from .configure_agent_management import AgentManagementHandler

        AgentManagementHandler(self).display_agent_sources_and_list(agents)

    def _display_agents_table(self, agents: list[AgentConfig]) -> None:
        """Display a table of available agents."""
        self.agent_display.display_agents_table(agents)

    def _display_agents_with_pending_states(self, agents: list[AgentConfig]) -> None:
        """Display agents table with pending state indicators."""
        self.agent_display.display_agents_with_pending_states(agents)

    def _toggle_agents_interactive(self, agents: list[AgentConfig]) -> None:
        """Interactive multi-agent enable/disable (delegated)."""
        from .configure_agent_management import AgentManagementHandler

        AgentManagementHandler(self).toggle_agents_interactive(agents)

    def _auto_deploy_enabled_agents(self, agents: list[AgentConfig]) -> None:
        """Auto-deploy enabled agents after saving (delegated)."""
        from .configure_agent_management import AgentManagementHandler

        AgentManagementHandler(self).auto_deploy_enabled_agents(agents)

    def _customize_agent_template(self, agents: list[AgentConfig]) -> None:
        """Customize agent JSON template."""
        self.template_editor.customize_agent_template(agents)

    def _edit_agent_template(self, agent: AgentConfig) -> None:
        """Edit an agent's JSON template."""
        self.template_editor.edit_agent_template(agent)

    def _get_agent_template_path(self, agent_name: str) -> Path:
        """Get the path to an agent's template file."""
        return self.template_editor.get_agent_template_path(agent_name)

    def _edit_in_external_editor(self, template_path: Path, template: dict) -> None:
        """Open template in external editor."""
        self.template_editor.edit_in_external_editor(template_path, template)

    def _modify_template_field(self, template: dict, template_path: Path) -> None:
        """Add or modify a field in the template."""
        self.template_editor.modify_template_field(template, template_path)

    def _remove_template_field(self, template: dict, template_path: Path) -> None:
        """Remove a field from the template."""
        self.template_editor.remove_template_field(template, template_path)

    def _reset_template(self, agent: AgentConfig, template_path: Path) -> None:
        """Reset template to defaults."""
        self.template_editor.reset_template(agent, template_path)

    def _create_custom_template_copy(self, agent: AgentConfig, template: dict) -> None:
        """Create a customized copy of a system template."""
        self.template_editor.create_custom_template_copy(agent, template)

    def _view_full_template(self, template: dict) -> None:
        """View the full template without truncation."""
        self.template_editor.view_full_template(template)

    def _reset_agent_defaults(self, agents: list[AgentConfig]) -> None:
        """Reset an agent to default enabled state and remove custom template."""
        self.template_editor.reset_agent_defaults(agents)

    def _edit_templates(self) -> None:
        """Template editing interface."""
        self.template_editor.edit_templates_interface()

    def _manage_behaviors(self) -> None:
        """Behavior file management interface."""
        if self.behavior_manager is None:
            return
        # Note: BehaviorManager handles its own loop and clears screen
        # but doesn't display our header. We'll need to update BehaviorManager
        # to accept a header callback in the future. For now, just delegate.
        self.behavior_manager.manage_behaviors()

    def _manage_skills(self) -> None:
        """Skills management interface (delegated)."""
        from .configure_skills import SkillsHandler

        SkillsHandler(self).manage_skills()

    def _detect_skill_patterns(self, skills: list[dict]) -> dict[str, list[dict]]:
        """Group skills by detected common prefixes (delegated)."""
        from .configure_skills import SkillsHandler

        return SkillsHandler(self).detect_skill_patterns(skills)

    def _get_pattern_icon(self, prefix: str) -> str:
        """Get icon for a pattern prefix (delegated)."""
        from .configure_skills import SkillsHandler

        return SkillsHandler(self).get_pattern_icon(prefix)

    def _manage_skill_installation(self) -> None:
        """Manage skill installation (delegated)."""
        from .configure_skills import SkillsHandler

        SkillsHandler(self).manage_skill_installation()

    def _get_all_skills_from_git(self) -> list:
        """Get all skills from Git-based skill manager (delegated)."""
        from .configure_skills import SkillsHandler

        return SkillsHandler(self).get_all_skills_from_git()

    def _display_skills_table_grouped(self) -> None:
        """Display skills in a table grouped by category (delegated)."""
        from .configure_skills import SkillsHandler

        SkillsHandler(self).display_skills_table_grouped()

    def _get_deployed_skill_ids(self) -> set:
        """Get set of deployed skill IDs (delegated)."""
        from .configure_skills import SkillsHandler

        return SkillsHandler(self).get_deployed_skill_ids()

    def _install_skill(self, skill) -> None:
        """Install a skill (delegated)."""
        from .configure_skills import SkillsHandler

        SkillsHandler(self).install_skill(skill)

    def _uninstall_skill(self, skill) -> None:
        """Uninstall a skill (delegated)."""
        from .configure_skills import SkillsHandler

        SkillsHandler(self).uninstall_skill(skill)

    def _install_skill_from_dict(self, skill_dict: dict) -> None:
        """Install a skill from Git skill dict (delegated)."""
        from .configure_skills import SkillsHandler

        SkillsHandler(self).install_skill_from_dict(skill_dict)

    def _uninstall_skill_by_name(self, skill_name: str) -> None:
        """Uninstall a skill by name (delegated)."""
        from .configure_skills import SkillsHandler

        SkillsHandler(self).uninstall_skill_by_name(skill_name)

    def _display_behavior_files(self) -> None:
        """Display current behavior files."""
        if self.behavior_manager is None:
            return
        self.behavior_manager.display_behavior_files()

    def _edit_identity_config(self) -> None:
        """Edit identity configuration."""
        if self.behavior_manager is None:
            return
        self.behavior_manager.edit_identity_config()

    def _edit_workflow_config(self) -> None:
        """Edit workflow configuration."""
        if self.behavior_manager is None:
            return
        self.behavior_manager.edit_workflow_config()

    def _import_behavior_file(self) -> None:
        """Import a behavior file."""
        if self.behavior_manager is None:
            return
        self.behavior_manager.import_behavior_file()

    def _export_behavior_file(self) -> None:
        """Export a behavior file."""
        if self.behavior_manager is None:
            return
        self.behavior_manager.export_behavior_file()

    def _manage_startup_configuration(self) -> bool:
        """Manage startup configuration for MCP services and agents."""
        return self.startup_manager.manage_startup_configuration()

    def _load_startup_configuration(self, config: Config) -> dict:
        """Load current startup configuration from config."""
        return self.startup_manager.load_startup_configuration(config)

    def _display_startup_configuration(self, startup_config: dict) -> None:
        """Display current startup configuration in a table."""
        self.startup_manager.display_startup_configuration(startup_config)

    def _configure_mcp_services(self, startup_config: dict, config: Config) -> None:
        """Configure which MCP services to enable at startup."""
        self.startup_manager.configure_mcp_services(startup_config, config)

    def _configure_hook_services(self, startup_config: dict, config: Config) -> None:
        """Configure which hook services to enable at startup."""
        self.startup_manager.configure_hook_services(startup_config, config)

    def _configure_system_agents(self, startup_config: dict, config: Config) -> None:
        """Configure which system agents to deploy at startup."""
        self.startup_manager.configure_system_agents(startup_config, config)

    def _parse_id_selection(self, selection: str, max_id: int) -> list[int]:
        """Parse ID selection string (e.g., '1,3,5' or '1-4')."""
        return parse_id_selection(selection, max_id)

    def _enable_all_services(self, startup_config: dict, config: Config) -> None:
        """Enable all services and agents."""
        self.startup_manager.enable_all_services(startup_config, config)

    def _disable_all_services(self, startup_config: dict, config: Config) -> None:
        """Disable all services and agents."""
        self.startup_manager.disable_all_services(startup_config, config)

    def _reset_to_defaults(self, startup_config: dict, config: Config) -> None:
        """Reset startup configuration to defaults."""
        self.startup_manager.reset_to_defaults(startup_config, config)

    def _save_startup_configuration(self, startup_config: dict, config: Config) -> bool:
        """Save startup configuration to config file and return whether to proceed to startup."""
        return self.startup_manager.save_startup_configuration(startup_config, config)

    def _save_all_configuration(self) -> bool:
        """Save all configuration changes across all contexts."""
        return self.startup_manager.save_all_configuration()

    def _launch_claude_mpm(self) -> None:
        """Launch Claude MPM run command, replacing current process."""
        self.navigation.launch_claude_mpm()

    def _switch_scope(self) -> None:
        """Switch between project and user scope.

        After switching, ALL dependent managers must be reinitialized so they
        pick up the new scope's config_dir and deployment paths.  Lazy-init
        objects are reset to None so they get recreated on next access.
        """
        self.navigation.switch_scope()
        # Sync scope back from navigation
        self.current_scope = self.navigation.current_scope
        # Recreate deployment context for new scope
        if self.current_scope == "user":
            self._ctx = DeploymentContext.from_user()
        else:
            self._ctx = DeploymentContext.from_project(self.project_dir)

        # Reinitialize managers that depend on config_dir / scope
        config_dir = self._ctx.config_dir
        self.agent_manager = SimpleAgentManager(config_dir)
        self.behavior_manager = BehaviorManager(
            config_dir, self.current_scope, self.console
        )

        # Reset lazy-initialized objects so they pick up new scope on next access
        self._agent_display = None
        self._persistence = None
        self._template_editor = None
        self._startup_manager = None
        self._navigation = None

    def _show_version_info_interactive(self) -> None:
        """Show version information in interactive mode."""
        self.persistence.show_version_info_interactive()

    # Non-interactive command methods

    def _list_agents_non_interactive(self) -> CommandResult:
        """List agents in non-interactive mode (delegated)."""
        from .configure_non_interactive import NonInteractiveHandler

        return NonInteractiveHandler(self).list_agents_non_interactive()

    def _enable_agent_non_interactive(self, agent_name: str) -> CommandResult:
        """Enable an agent in non-interactive mode (delegated)."""
        from .configure_non_interactive import NonInteractiveHandler

        return NonInteractiveHandler(self).enable_agent_non_interactive(agent_name)

    def _disable_agent_non_interactive(self, agent_name: str) -> CommandResult:
        """Disable an agent in non-interactive mode (delegated)."""
        from .configure_non_interactive import NonInteractiveHandler

        return NonInteractiveHandler(self).disable_agent_non_interactive(agent_name)

    def _export_config(self, file_path: str) -> CommandResult:
        """Export configuration to a file."""
        return self.persistence.export_config(file_path)

    def _import_config(self, file_path: str) -> CommandResult:
        """Import configuration from a file."""
        return self.persistence.import_config(file_path)

    def _show_version_info(self) -> CommandResult:
        """Show version information in non-interactive mode."""
        return self.persistence.show_version_info()

    def _install_hooks(self, force: bool = False) -> CommandResult:
        """Install Claude MPM hooks for Claude Code integration."""
        # Share logger with hook manager for consistent error logging
        self.hook_manager.logger = self.logger
        return self.hook_manager.install_hooks(force=force)

    def _verify_hooks(self) -> CommandResult:
        """Verify that Claude MPM hooks are properly installed."""
        # Share logger with hook manager for consistent error logging
        self.hook_manager.logger = self.logger
        return self.hook_manager.verify_hooks()

    def _uninstall_hooks(self) -> CommandResult:
        """Uninstall Claude MPM hooks."""
        # Share logger with hook manager for consistent error logging
        self.hook_manager.logger = self.logger
        return self.hook_manager.uninstall_hooks()

    def _run_agent_management(self) -> CommandResult:
        """Jump directly to agent management (delegated)."""
        from .configure_non_interactive import NonInteractiveHandler

        return NonInteractiveHandler(self).run_agent_management()

    def _run_template_editing(self) -> CommandResult:
        """Jump directly to template editing (delegated)."""
        from .configure_non_interactive import NonInteractiveHandler

        return NonInteractiveHandler(self).run_template_editing()

    def _run_behavior_management(self) -> CommandResult:
        """Jump directly to behavior management."""
        if self.behavior_manager is None:
            return CommandResult.error_result("Behavior manager not initialized")
        return self.behavior_manager.run_behavior_management()

    def _run_startup_configuration(self) -> CommandResult:
        """Jump directly to startup configuration (delegated)."""
        from .configure_non_interactive import NonInteractiveHandler

        return NonInteractiveHandler(self).run_startup_configuration()

    # ========================================================================
    # Enhanced Agent Management Methods (Remote Agent Discovery Integration)
    # ========================================================================

    def _get_configured_sources(self) -> list[dict]:
        """Get list of configured agent sources (delegated)."""
        from .configure_agent_management import AgentManagementHandler

        return AgentManagementHandler(self).get_configured_sources()

    def _filter_agent_configs(
        self, agents: list[AgentConfig], filter_deployed: bool = False
    ) -> list[AgentConfig]:
        """Filter AgentConfig objects (delegated)."""
        from .configure_agent_management import AgentManagementHandler

        return AgentManagementHandler(self).filter_agent_configs(
            agents, filter_deployed=filter_deployed
        )

    @staticmethod
    def _calculate_column_widths(
        terminal_width: int, columns: dict[str, int]
    ) -> dict[str, int]:
        """Calculate dynamic column widths (delegated)."""
        from .configure_agent_management import AgentManagementHandler

        return AgentManagementHandler.calculate_column_widths(terminal_width, columns)

    def _format_display_name(self, name: str) -> str:
        """Format internal agent name to human-readable display name (delegated)."""
        from .configure_agent_management import AgentManagementHandler

        return AgentManagementHandler.format_display_name(name)

    def _display_agents_with_source_info(self, agents: list[AgentConfig]) -> None:
        """Display agents table with source information (delegated)."""
        from .configure_agent_management import AgentManagementHandler

        AgentManagementHandler(self).display_agents_with_source_info(agents)

    def _manage_sources(self) -> None:
        """Interactive source management (delegated)."""
        from .configure_agent_management import AgentManagementHandler

        AgentManagementHandler(self).manage_sources()

    def _deploy_agents_unified(self, agents: list[AgentConfig]) -> None:
        """Unified agent selection (delegated)."""
        from .configure_agent_deployment import AgentDeploymentHandler

        AgentDeploymentHandler(self).deploy_agents_unified(agents)

    def _deploy_agents_preset(self) -> None:
        """Install agents using preset configuration (delegated)."""
        from .configure_agent_deployment import AgentDeploymentHandler

        AgentDeploymentHandler(self).deploy_agents_preset()

    def _select_recommended_agents(self, agents: list[AgentConfig]) -> None:
        """Select and install recommended agents (delegated)."""
        from .configure_agent_deployment import AgentDeploymentHandler

        AgentDeploymentHandler(self).select_recommended_agents(agents)

    def _agent_file_paths(self, agent_name: str) -> list[Path]:
        """Return the list of paths to check for an agent file (delegated)."""
        from .configure_agent_deployment import AgentDeploymentHandler

        return AgentDeploymentHandler(self).agent_file_paths(agent_name)

    def _deployment_state_paths(self) -> list[Path]:
        """Return the list of deployment state file paths to check (delegated)."""
        from .configure_agent_deployment import AgentDeploymentHandler

        return AgentDeploymentHandler(self).deployment_state_paths()

    def _deploy_single_agent(
        self, agent: AgentConfig, show_feedback: bool = True
    ) -> bool:
        """Install a single agent to the appropriate location (delegated)."""
        from .configure_agent_deployment import AgentDeploymentHandler

        return AgentDeploymentHandler(self).deploy_single_agent(
            agent, show_feedback=show_feedback
        )

    def _remove_agents(self, agents: list[AgentConfig]) -> None:
        """Remove installed agents (delegated)."""
        from .configure_agent_deployment import AgentDeploymentHandler

        AgentDeploymentHandler(self).remove_agents(agents)

    def _view_agent_details_enhanced(self, agents: list[AgentConfig]) -> None:
        """View detailed agent information (delegated)."""
        from .configure_agent_deployment import AgentDeploymentHandler

        AgentDeploymentHandler(self).view_agent_details_enhanced(agents)


def manage_configure(args) -> int:
    """Main entry point for configuration management command.

    This function maintains backward compatibility while using the new BaseCommand pattern.
    """
    command = ConfigureCommand()
    result = command.execute(args)

    # Print result if needed
    if hasattr(args, "format") and args.format in ["json", "yaml"]:
        command.print_result(result, args)

    return result.exit_code
