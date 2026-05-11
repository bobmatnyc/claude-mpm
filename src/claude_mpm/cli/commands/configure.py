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

from collections import defaultdict
from pathlib import Path

import questionary
import questionary.constants
import questionary.prompts.common  # For checkbox symbol customization
from questionary import Choice, Separator, Style
from rich.console import Console
from rich.prompt import Confirm, Prompt

from ...core.config import Config
from ...core.deployment_context import DeploymentContext
from ...core.unified_config import UnifiedConfig
from ...services.agents.agent_recommendation_service import AgentRecommendationService
from ...services.version_service import VersionService
from ...utils.agent_filters import (
    normalize_agent_id,
    normalize_agent_id_for_comparison,
)
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
        """Unified agent selection with inline controls for recommended, presets, and collections.

        Design:
        - Single nested checkbox list with grouped agents by source/category
        - Inline controls at top: Select all, Select recommended, Select presets
        - Asterisk (*) marks recommended agents
        - Visual hierarchy: Source → Category → Individual agents
        - Loop with visual feedback: Controls update checkmarks immediately
        """
        if not agents:
            self.console.print("[yellow]No agents available[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return

        from claude_mpm.utils.agent_filters import (
            filter_base_agents,
            get_deployed_agent_ids,
        )

        # Filter BASE_AGENT but keep deployed agents visible
        all_agents = filter_base_agents(
            [
                {
                    "agent_id": getattr(a, "agent_id", a.name),
                    "name": a.name,
                    "description": a.description,
                    "deployed": getattr(a, "is_deployed", False),
                }
                for a in agents
            ]
        )

        if not all_agents:
            self.console.print("[yellow]No agents available[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return

        # Get deployed agent IDs and recommended agents
        deployed_ids = get_deployed_agent_ids()

        try:
            recommended_agent_ids = self.recommendation_service.get_recommended_agents(
                str(self.project_dir)
            )
        except Exception as e:
            self.logger.warning(f"Failed to get recommended agents: {e}")
            recommended_agent_ids = set()

        # Build mapping: normalized name -> full path for deployed agents
        # Use agent_id (technical ID) for comparison, not display name
        deployed_full_paths = set()
        for agent in agents:
            agent_id = getattr(agent, "agent_id", agent.name)
            normalized_id = normalize_agent_id_for_comparison(agent_id)
            if normalized_id in deployed_ids:
                # Store agent_id for selection tracking (not display name)
                deployed_full_paths.add(agent_id)

        # Track current selection state (starts with deployed, updated in loop)
        current_selection = deployed_full_paths.copy()

        # Group agents by source/collection
        agent_map = {}
        collections = defaultdict(list)

        for agent in agents:
            # Use agent_id (technical ID) for comparison, not display name
            agent_id = getattr(agent, "agent_id", agent.name)
            if agent_id in {a["agent_id"] for a in all_agents}:
                # Determine collection ID
                source_type = getattr(agent, "source_type", "local")
                if source_type == "remote":
                    source_dict = getattr(agent, "source_dict", {})
                    repo_url = source_dict.get("source", "")
                    if "/" in repo_url:
                        parts = repo_url.rstrip("/").split("/")
                        if len(parts) >= 2:
                            # Use more readable collection name
                            if (
                                "bobmatnyc/claude-mpm" in repo_url
                                or "claude-mpm" in repo_url.lower()
                            ):
                                collection_id = "MPM Agents"
                            else:
                                collection_id = f"{parts[-2]}/{parts[-1]}"
                        else:
                            collection_id = "Community Agents"
                    else:
                        collection_id = "Community Agents"
                else:
                    collection_id = "Local Agents"

                collections[collection_id].append(agent)
                agent_map[agent_id] = agent

        # Monkey-patch questionary symbols for better visibility
        questionary.prompts.common.INDICATOR_SELECTED = "[✓]"  # type: ignore[attr-defined]
        questionary.prompts.common.INDICATOR_UNSELECTED = "[ ]"  # type: ignore[attr-defined]

        # MAIN LOOP: Re-display UI when controls are used
        while True:
            # Build unified checkbox choices with inline controls
            choices = []

            for collection_id in sorted(collections.keys()):
                agents_in_collection = collections[collection_id]

                # Count selected/total agents in collection
                # Use agent_id for selection tracking, not display name
                selected_count = sum(
                    1
                    for agent in agents_in_collection
                    if getattr(agent, "agent_id", agent.name) in current_selection
                )
                total_count = len(agents_in_collection)

                # Add collection header
                choices.append(
                    Separator(
                        f"\n── {collection_id} ({selected_count}/{total_count} selected) ──"
                    )
                )

                # Determine if all agents in collection are selected
                all_selected = selected_count == total_count

                # Add inline control: Select/Deselect all from this collection
                if all_selected:
                    deselect_value = f"__DESELECT_ALL_{collection_id}__"
                    choices.append(
                        Choice(
                            f"  [Deselect all from {collection_id}]",  # nosec B608
                            value=deselect_value,
                            checked=False,
                        )
                    )
                else:
                    select_value = f"__SELECT_ALL_{collection_id}__"
                    choices.append(
                        Choice(
                            f"  [Select all from {collection_id}]",  # nosec B608
                            value=select_value,
                            checked=False,
                        )
                    )

                # Add inline control: Select recommended from this collection
                recommended_in_collection = [
                    a
                    for a in agents_in_collection
                    if any(
                        a.name == rec_id
                        or a.name.split("/")[-1] == rec_id.split("/")[-1]
                        for rec_id in recommended_agent_ids
                    )
                ]
                if recommended_in_collection:
                    recommended_selected = sum(
                        1
                        for a in recommended_in_collection
                        if a.name in current_selection
                    )
                    if recommended_selected == len(recommended_in_collection):
                        choices.append(
                            Choice(
                                f"  [Deselect recommended ({len(recommended_in_collection)} agents)]",
                                value=f"__DESELECT_REC_{collection_id}__",
                                checked=False,
                            )
                        )
                    else:
                        choices.append(
                            Choice(
                                f"  [Select recommended ({len(recommended_in_collection)} agents)]",
                                value=f"__SELECT_REC_{collection_id}__",
                                checked=False,
                            )
                        )

                # Add separator before individual agents
                choices.append(Separator())

                # Group agents by category within collection (if hierarchical)
                category_groups = defaultdict(list)
                for agent in sorted(agents_in_collection, key=lambda a: a.name):
                    # Extract category from hierarchical path (e.g., "engineer/backend/python-engineer")
                    parts = agent.name.split("/")
                    if len(parts) > 1:
                        category = "/".join(parts[:-1])  # e.g., "engineer/backend"
                    else:
                        category = ""  # No category
                    category_groups[category].append(agent)

                # Display agents grouped by category
                for category in sorted(category_groups.keys()):
                    agents_in_category = category_groups[category]

                    # Add category separator if hierarchical
                    if category:
                        choices.append(Separator(f"  {category}/"))

                    # Add individual agents
                    for agent in agents_in_category:
                        # Use agent_id (technical ID) for all tracking/selection
                        agent_id = getattr(agent, "agent_id", agent.name)
                        agent_leaf_name = agent_id.split("/")[-1]
                        raw_display_name = getattr(
                            agent, "display_name", agent_leaf_name
                        )
                        display_name = self._format_display_name(raw_display_name)

                        # Check if agent is required (cannot be unchecked)
                        required_agents = set(self.unified_config.agents.required)
                        is_required = (
                            agent_leaf_name in required_agents
                            or agent_id in required_agents
                        )

                        # Format choice text with [Required] indicator
                        if is_required:
                            choice_text = f"    {display_name} [Required]"
                        else:
                            choice_text = f"    {display_name}"

                        # Required agents are always selected
                        is_selected = is_required or agent_id in current_selection

                        # Add to current selection if required
                        if is_required:
                            current_selection.add(agent_id)

                        choices.append(
                            Choice(
                                title=choice_text,
                                value=agent_id,  # Use agent_id for value
                                checked=is_selected,
                                disabled="required"
                                if is_required
                                else None,  # Disable checkbox for required agents
                            )
                        )

            self.console.print("\n[bold cyan]Select Agents to Install[/bold cyan]")
            self.console.print("[dim][✓] Checked = Installed (uncheck to remove)[/dim]")
            self.console.print(
                "[dim][ ] Unchecked = Available (check to install)[/dim]"
            )
            self.console.print("[dim][Required] = Core agents (always installed)[/dim]")
            self.console.print(
                "[dim]Use arrow keys to navigate, space to toggle, Enter to apply[/dim]\n"
            )

            try:
                selected_values = questionary.checkbox(
                    "Select agents:",
                    choices=choices,
                    instruction="(Space to toggle, Enter to continue)",
                    style=self.QUESTIONARY_STYLE,
                ).ask()
            except Exception as e:
                import sys

                self.logger.error(f"Questionary checkbox failed: {e}", exc_info=True)
                self.console.print(
                    "[red]Error: Could not display interactive menu[/red]"
                )
                self.console.print(f"[dim]Reason: {e}[/dim]")
                if not sys.stdin.isatty():
                    self.console.print("[dim]Interactive terminal required. Use:[/dim]")
                    self.console.print(
                        "[dim]  --list-agents to see available agents[/dim]"
                    )
                Prompt.ask("\nPress Enter to continue")
                return

            if selected_values is None:
                self.console.print("[yellow]No changes made[/yellow]")
                Prompt.ask("\nPress Enter to continue")
                return

            # Check for inline control selections
            controls_selected = [v for v in selected_values if v.startswith("__")]

            if controls_selected:
                # Process controls and update current_selection
                for control in controls_selected:
                    if control.startswith("__SELECT_ALL_"):
                        collection_id = control.replace("__SELECT_ALL_", "").replace(
                            "__", ""
                        )
                        # Add all agents from this collection to current_selection
                        for agent in collections[collection_id]:
                            agent_id = getattr(agent, "agent_id", agent.name)
                            current_selection.add(agent_id)
                    elif control.startswith("__DESELECT_ALL_"):
                        collection_id = control.replace("__DESELECT_ALL_", "").replace(
                            "__", ""
                        )
                        # Remove all agents from this collection
                        for agent in collections[collection_id]:
                            agent_id = getattr(agent, "agent_id", agent.name)
                            current_selection.discard(agent_id)
                    elif control.startswith("__SELECT_REC_"):
                        collection_id = control.replace("__SELECT_REC_", "").replace(
                            "__", ""
                        )
                        # Add all recommended agents from this collection
                        for agent in collections[collection_id]:
                            agent_id = getattr(agent, "agent_id", agent.name)
                            if any(
                                agent_id == rec_id
                                or agent_id.split("/")[-1] == rec_id.split("/")[-1]
                                for rec_id in recommended_agent_ids
                            ):
                                current_selection.add(agent_id)
                    elif control.startswith("__DESELECT_REC_"):
                        collection_id = control.replace("__DESELECT_REC_", "").replace(
                            "__", ""
                        )
                        # Remove all recommended agents from this collection
                        for agent in collections[collection_id]:
                            agent_id = getattr(agent, "agent_id", agent.name)
                            if any(
                                agent_id == rec_id
                                or agent_id.split("/")[-1] == rec_id.split("/")[-1]
                                for rec_id in recommended_agent_ids
                            ):
                                current_selection.discard(agent_id)

                # Loop back to re-display with updated selections
                continue

            # No controls selected - use the individual selections as final
            final_selection = set(selected_values)

            # Ensure required agents are always in the final selection
            required_agents = set(self.unified_config.agents.required)
            for agent in agents:
                agent_id = getattr(agent, "agent_id", agent.name)
                agent_leaf_name = agent_id.split("/")[-1]
                if agent_leaf_name in required_agents or agent_id in required_agents:
                    final_selection.add(agent_id)

            break

        # Determine changes
        to_deploy = final_selection - deployed_full_paths
        to_remove = deployed_full_paths - final_selection

        # Prevent removal of required agents
        required_agents = set(self.unified_config.agents.required)
        to_remove_filtered = set()
        for agent_id in to_remove:
            agent_leaf_name = agent_id.split("/")[-1]
            if (
                agent_leaf_name not in required_agents
                and agent_id not in required_agents
            ):
                to_remove_filtered.add(agent_id)
            else:
                self.console.print(
                    f"[yellow]⚠ Cannot remove required agent: {agent_id}[/yellow]"
                )
        to_remove = to_remove_filtered

        if not to_deploy and not to_remove:
            self.console.print("[yellow]No changes needed[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return

        # Show what will happen
        self.console.print("\n[bold]Changes to apply:[/bold]")
        if to_deploy:
            self.console.print(f"[green]Install {len(to_deploy)} agent(s)[/green]")
            for agent_id in to_deploy:
                self.console.print(f"  + {agent_id}")
        if to_remove:
            self.console.print(f"[red]Remove {len(to_remove)} agent(s)[/red]")
            for agent_id in to_remove:
                self.console.print(f"  - {agent_id}")

        # Confirm
        if not Confirm.ask("\nApply these changes?", default=True):
            self.console.print("[yellow]Changes cancelled[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return

        # Execute changes
        deploy_success = 0
        deploy_fail = 0
        remove_success = 0
        remove_fail = 0

        # Install new agents
        for agent_id in to_deploy:
            agent = agent_map.get(agent_id)
            if agent and self._deploy_single_agent(agent, show_feedback=False):
                deploy_success += 1
                self.console.print(f"[green]✓ Installed: {agent_id}[/green]")
            else:
                deploy_fail += 1
                self.console.print(f"[red]✗ Failed to install: {agent_id}[/red]")

        # Remove agents
        for agent_id in to_remove:
            try:
                import json

                # Extract leaf name to match deployed filename
                leaf_name = agent_id.split("/")[-1] if "/" in agent_id else agent_id
                normalized_leaf = normalize_agent_id_for_comparison(leaf_name)

                # Remove from scope-aware path (primary) + legacy locations
                # _agent_file_paths already normalizes and checks both variants
                paths_to_check = self._agent_file_paths(leaf_name)

                removed = False
                for path in paths_to_check:
                    if path.exists():
                        path.unlink()
                        removed = True

                # Also remove from virtual deployment state
                # Check both raw and normalized keys for safety
                keys_to_check = {leaf_name, normalized_leaf}
                for state_path in self._deployment_state_paths():
                    if state_path.exists():
                        try:
                            with state_path.open() as f:
                                state = json.load(f)
                            agents_in_state = state.get("last_check_results", {}).get(
                                "agents", {}
                            )
                            for key in keys_to_check:
                                if key in agents_in_state:
                                    del agents_in_state[key]
                                    removed = True
                            if removed:
                                with state_path.open("w") as f:
                                    json.dump(state, f, indent=2)
                        except (json.JSONDecodeError, KeyError):
                            pass

                if removed:
                    remove_success += 1
                    self.console.print(f"[green]✓ Removed: {agent_id}[/green]")
                else:
                    remove_fail += 1
                    self.console.print(f"[yellow]⚠ Not found: {agent_id}[/yellow]")
            except Exception as e:
                remove_fail += 1
                self.console.print(f"[red]✗ Failed to remove {agent_id}: {e}[/red]")

        # Show summary
        self.console.print()
        if deploy_success > 0:
            self.console.print(f"[green]✓ Installed {deploy_success} agent(s)[/green]")
        if deploy_fail > 0:
            self.console.print(f"[red]✗ Failed to install {deploy_fail} agent(s)[/red]")
        if remove_success > 0:
            self.console.print(f"[green]✓ Removed {remove_success} agent(s)[/green]")
        if remove_fail > 0:
            self.console.print(f"[red]✗ Failed to remove {remove_fail} agent(s)[/red]")

        Prompt.ask("\nPress Enter to continue")

    def _deploy_agents_preset(self) -> None:
        """Install agents using preset configuration."""
        try:
            from claude_mpm.services.agents.agent_preset_service import (
                AgentPresetService,
            )
            from claude_mpm.services.agents.git_source_manager import GitSourceManager

            source_manager = GitSourceManager()
            preset_service = AgentPresetService(source_manager)

            presets = preset_service.list_presets()

            if not presets:
                self.console.print("[yellow]No presets available[/yellow]")
                Prompt.ask("\nPress Enter to continue")
                return

            self.console.print("\n[bold white]═══ Available Presets ═══[/bold white]\n")
            for idx, preset in enumerate(presets, 1):
                self.console.print(f"  {idx}. [white]{preset['name']}[/white]")
                self.console.print(f"     {preset['description']}")
                self.console.print(f"     [dim]Agents: {len(preset['agents'])}[/dim]\n")

            selection = Prompt.ask("\nEnter preset number (or 'c' to cancel)")
            if selection.lower() == "c":
                return

            idx = int(selection) - 1
            if 0 <= idx < len(presets):
                preset_name = presets[idx]["name"]

                # Resolve and deploy preset
                resolution = preset_service.resolve_agents(preset_name)

                if resolution.get("missing_agents"):
                    self.console.print(
                        f"[red]Missing agents: {len(resolution['missing_agents'])}[/red]"
                    )
                    for agent_id in resolution["missing_agents"]:
                        self.console.print(f"  • {agent_id}")
                    Prompt.ask("\nPress Enter to continue")
                    return

                # Confirm installation
                self.console.print(
                    f"\n[bold]Preset '{preset_name}' includes {len(resolution['agents'])} agents[/bold]"
                )
                if Confirm.ask("Install all agents?", default=True):
                    installed = 0
                    for agent in resolution["agents"]:
                        # Convert dict to AgentConfig-like object for installation
                        agent_config = AgentConfig(
                            name=agent.get("agent_id", "unknown"),
                            description=agent.get("metadata", {}).get(
                                "description", ""
                            ),
                            dependencies=[],
                        )
                        agent_config.source_dict = agent
                        agent_config.full_agent_id = agent.get("agent_id", "unknown")

                        if self._deploy_single_agent(agent_config, show_feedback=False):
                            installed += 1

                    self.console.print(
                        f"\n[green]✓ Installed {installed}/{len(resolution['agents'])} agents[/green]"
                    )

                Prompt.ask("\nPress Enter to continue")
            else:
                self.console.print("[red]Invalid selection[/red]")
                Prompt.ask("\nPress Enter to continue")

        except Exception as e:
            self.console.print(f"[red]Error installing preset: {e}[/red]")
            self.logger.error(f"Preset installation failed: {e}", exc_info=True)
            Prompt.ask("\nPress Enter to continue")

    def _select_recommended_agents(self, agents: list[AgentConfig]) -> None:
        """Select and install recommended agents based on toolchain detection."""
        if not agents:
            self.console.print("[yellow]No agents available[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return

        self.console.clear()
        self.console.print(
            "\n[bold white]═══ Recommended Agents for This Project ═══[/bold white]\n"
        )

        # Get recommended agent IDs
        try:
            recommended_agent_ids = self.recommendation_service.get_recommended_agents(
                str(self.project_dir)
            )
        except Exception as e:
            self.console.print(f"[red]Error detecting toolchain: {e}[/red]")
            self.logger.error(f"Toolchain detection failed: {e}", exc_info=True)
            Prompt.ask("\nPress Enter to continue")
            return

        if not recommended_agent_ids:
            self.console.print("[yellow]No recommended agents found[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return

        # Get detection summary
        try:
            summary = self.recommendation_service.get_detection_summary(
                str(self.project_dir)
            )

            self.console.print("[bold]Detected Project Stack:[/bold]")
            if summary.get("detected_languages"):
                self.console.print(
                    f"  Languages: [cyan]{', '.join(summary['detected_languages'])}[/cyan]"
                )
            if summary.get("detected_frameworks"):
                self.console.print(
                    f"  Frameworks: [cyan]{', '.join(summary['detected_frameworks'])}[/cyan]"
                )
            self.console.print(
                f"  Detection Quality: [{'green' if summary.get('detection_quality') == 'high' else 'yellow'}]{summary.get('detection_quality', 'unknown')}[/]"
            )
            self.console.print()
        except Exception:  # nosec B110 - Suppress broad except for failed safety check
            # Silent failure on safety check - non-critical feature
            pass

        # Build mapping: agent_id -> AgentConfig
        agent_map = {agent.name: agent for agent in agents}

        # Also check leaf names for matching
        for agent in agents:
            leaf_name = agent.name.split("/")[-1] if "/" in agent.name else agent.name
            if leaf_name not in agent_map:
                agent_map[leaf_name] = agent

        # Find matching agents from available agents
        matched_agents = []
        for recommended_id in recommended_agent_ids:
            # Try full path match first
            if recommended_id in agent_map:
                matched_agents.append(agent_map[recommended_id])
            else:
                # Try leaf name match
                recommended_leaf = (
                    recommended_id.split("/")[-1]
                    if "/" in recommended_id
                    else recommended_id
                )
                if recommended_leaf in agent_map:
                    matched_agents.append(agent_map[recommended_leaf])

        if not matched_agents:
            self.console.print(
                "[yellow]No matching agents found in available sources[/yellow]"
            )
            Prompt.ask("\nPress Enter to continue")
            return

        # Display recommended agents
        self.console.print(
            f"[bold]Recommended Agents ({len(matched_agents)}):[/bold]\n"
        )

        from rich.table import Table

        rec_table = Table(show_header=True, header_style="bold white")
        rec_table.add_column("#", style="dim", width=4)
        rec_table.add_column("Agent ID", style="cyan", width=40)
        rec_table.add_column("Status", style="white", width=15)

        for idx, agent in enumerate(matched_agents, 1):
            is_installed = getattr(agent, "is_deployed", False)
            status = (
                "[green]Already Installed[/green]"
                if is_installed
                else "[yellow]Not Installed[/yellow]"
            )
            rec_table.add_row(str(idx), agent.name, status)

        self.console.print(rec_table)

        # Count how many need installation
        to_install = [a for a in matched_agents if not getattr(a, "is_deployed", False)]
        already_installed = len(matched_agents) - len(to_install)

        self.console.print()
        if already_installed > 0:
            self.console.print(
                f"[green]✓ {already_installed} already installed[/green]"
            )
        if to_install:
            self.console.print(
                f"[yellow]⚠ {len(to_install)} need installation[/yellow]"
            )
        else:
            self.console.print(
                "[green]✓ All recommended agents are already installed![/green]"
            )
            Prompt.ask("\nPress Enter to continue")
            return

        # Ask for confirmation
        self.console.print()
        if not Confirm.ask(
            f"Install {len(to_install)} recommended agent(s)?", default=True
        ):
            self.console.print("[yellow]Installation cancelled[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return

        # Install agents
        self.console.print("\n[bold]Installing recommended agents...[/bold]\n")

        success_count = 0
        fail_count = 0

        for agent in to_install:
            try:
                if self._deploy_single_agent(agent, show_feedback=False):
                    success_count += 1
                    self.console.print(f"[green]✓ Installed: {agent.name}[/green]")
                else:
                    fail_count += 1
                    self.console.print(f"[red]✗ Failed: {agent.name}[/red]")
            except Exception as e:
                fail_count += 1
                self.console.print(f"[red]✗ Failed: {agent.name} - {e}[/red]")

        # Show summary
        self.console.print()
        if success_count > 0:
            self.console.print(
                f"[green]✓ Successfully installed {success_count} agent(s)[/green]"
            )
        if fail_count > 0:
            self.console.print(f"[red]✗ Failed to install {fail_count} agent(s)[/red]")

        Prompt.ask("\nPress Enter to continue")

    def _agent_file_paths(self, agent_name: str) -> list[Path]:
        """Return the list of paths to check for an agent file.

        The primary path is the active scope's agents_dir. Legacy locations
        (project .claude-mpm/agents/, project .claude/agents/, user
        ~/.claude/agents/) are included as secondary cleanup targets so that
        agents deployed to the wrong location by older code are still found
        and removed.

        Normalizes agent_name (underscore -> dash, lowercase, strip -agent
        suffix) and also checks the raw name for backward compatibility with
        agents deployed before normalization was added.
        """
        normalized = normalize_agent_id_for_comparison(agent_name)

        # Build the set of name variants to check
        names_to_check = [normalized]
        if agent_name != normalized:
            names_to_check.append(agent_name)  # Also check raw for backward compat

        dirs_to_check = [
            self._ctx.agents_dir,
            Path.cwd() / ".claude-mpm" / "agents",
            Path.cwd() / ".claude" / "agents",
            Path.home() / ".claude" / "agents",
        ]

        # Build paths for all name variants across all locations, deduplicated
        seen: set[Path] = set()
        paths: list[Path] = []
        for name in names_to_check:
            for d in dirs_to_check:
                p = d / f"{name}.md"
                if p not in seen:
                    seen.add(p)
                    paths.append(p)
        return paths

    def _deployment_state_paths(self) -> list[Path]:
        """Return the list of deployment state file paths to check.

        Includes the active scope path plus legacy locations for cleanup.
        """
        primary = self._ctx.agents_dir / ".mpm_deployment_state"
        legacy_paths = [
            Path.cwd() / ".claude" / "agents" / ".mpm_deployment_state",
            Path.home() / ".claude" / "agents" / ".mpm_deployment_state",
        ]
        seen = {primary}
        paths = [primary]
        for p in legacy_paths:
            if p not in seen:
                seen.add(p)
                paths.append(p)
        return paths

    def _deploy_single_agent(
        self, agent: AgentConfig, show_feedback: bool = True
    ) -> bool:
        """Install a single agent to the appropriate location."""
        try:
            # Check if this is a remote agent with source_dict
            source_dict = getattr(agent, "source_dict", None)
            full_agent_id = getattr(agent, "full_agent_id", agent.name)

            if source_dict:
                # Deploy remote agent using its source file
                source_file = Path(source_dict.get("source_file", ""))
                if not source_file.exists():
                    if show_feedback:
                        self.console.print(
                            f"[red]✗ Source file not found: {source_file}[/red]"
                        )
                    return False

                # Deploy to scope-aware agents directory
                target_dir = self._ctx.agents_dir

                if show_feedback:
                    self.console.print(
                        f"\n[white]Installing {full_agent_id}...[/white]"
                    )

                from claude_mpm.services.agents.deployment_utils import (
                    deploy_agent_file,
                )

                # NOTE: deploy_agent_file derives the target filename from
                # source_file.name (not full_agent_id).  This works because
                # cache files are named after their agent IDs in production.
                deploy_result = deploy_agent_file(
                    source_file=source_file,
                    deployment_dir=target_dir,
                    cleanup_legacy=True,
                    ensure_frontmatter=True,
                    force=True,  # CRITICAL: configure expects always-write semantics
                )

                if not deploy_result.success:
                    if show_feedback:
                        self.console.print(
                            f"[red]✗ Failed to install {full_agent_id}: {deploy_result.error}[/red]"
                        )
                    return False

                if show_feedback:
                    action = deploy_result.action
                    self.console.print(
                        f"[green]✓ Successfully installed {full_agent_id} ({action})[/green]"
                    )
                    Prompt.ask("\nPress Enter to continue")

                return True
            # Legacy local template installation (not implemented here)
            if show_feedback:
                self.console.print(
                    "[yellow]Local template installation not yet implemented[/yellow]"
                )
                Prompt.ask("\nPress Enter to continue")
            return False

        except Exception as e:
            self.logger.error(f"Agent installation failed: {e}", exc_info=True)
            if show_feedback:
                self.console.print(f"[red]Error installing agent: {e}[/red]")
                Prompt.ask("\nPress Enter to continue")
            return False

    def _remove_agents(self, agents: list[AgentConfig]) -> None:
        """Remove installed agents."""
        # Filter to installed agents only
        installed = [a for a in agents if getattr(a, "is_deployed", False)]

        if not installed:
            self.console.print("[yellow]No agents are currently installed[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return

        self.console.print(f"\n[bold]Installed agents ({len(installed)}):[/bold]")
        for idx, agent in enumerate(installed, 1):
            raw_display_name = getattr(agent, "display_name", agent.name)
            display_name = self._format_display_name(raw_display_name)
            self.console.print(f"  {idx}. {agent.name} - {display_name}")

        selection = Prompt.ask("\nEnter agent number to remove (or 'c' to cancel)")
        if selection.lower() == "c":
            return

        try:
            idx = int(selection) - 1
            if 0 <= idx < len(installed):
                agent = installed[idx]
                full_agent_id = getattr(agent, "full_agent_id", agent.name)
                # Normalize so that e.g. "dart_engineer" -> "dart-engineer"
                full_agent_id = normalize_agent_id(full_agent_id)

                # Determine possible file names (normalized leaf name)
                file_names = [f"{full_agent_id}.md"]

                # Remove from active scope's agents directory
                removed = False
                scope_agent_dir = self._ctx.agents_dir

                for file_name in file_names:
                    scope_file = scope_agent_dir / file_name

                    if scope_file.exists():
                        scope_file.unlink()
                        removed = True
                        self.console.print(f"[green]✓ Removed {scope_file}[/green]")

                if removed:
                    self.console.print(
                        f"[green]✓ Successfully removed {full_agent_id}[/green]"
                    )
                else:
                    self.console.print("[yellow]Agent files not found[/yellow]")

                Prompt.ask("\nPress Enter to continue")
            else:
                self.console.print("[red]Invalid selection[/red]")
                Prompt.ask("\nPress Enter to continue")

        except (ValueError, IndexError):
            self.console.print("[red]Invalid selection[/red]")
            Prompt.ask("\nPress Enter to continue")

    def _view_agent_details_enhanced(self, agents: list[AgentConfig]) -> None:
        """View detailed agent information with enhanced remote agent details."""
        if not agents:
            self.console.print("[yellow]No agents available[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return

        self.console.print(f"\n[bold]Available agents ({len(agents)}):[/bold]")
        for idx, agent in enumerate(agents, 1):
            raw_display_name = getattr(agent, "display_name", agent.name)
            display_name = self._format_display_name(raw_display_name)
            self.console.print(f"  {idx}. {agent.name} - {display_name}")

        selection = Prompt.ask("\nEnter agent number to view (or 'c' to cancel)")
        if selection.lower() == "c":
            return

        try:
            idx = int(selection) - 1
            if 0 <= idx < len(agents):
                agent = agents[idx]

                self.console.clear()
                self.console.print("\n[bold white]═══ Agent Details ═══[/bold white]\n")

                # Basic info
                self.console.print(f"[bold]ID:[/bold] {agent.name}")
                raw_display_name = getattr(agent, "display_name", "N/A")
                display_name = (
                    self._format_display_name(raw_display_name)
                    if raw_display_name != "N/A"
                    else "N/A"
                )
                self.console.print(f"[bold]Name:[/bold] {display_name}")
                self.console.print(f"[bold]Description:[/bold] {agent.description}")

                # Source info
                source_type = getattr(agent, "source_type", "local")
                self.console.print(f"[bold]Source Type:[/bold] {source_type}")

                if source_type == "remote":
                    source_dict = getattr(agent, "source_dict", {})
                    category = source_dict.get("category", "N/A")
                    source = source_dict.get("source", "N/A")
                    version = source_dict.get("version", "N/A")

                    self.console.print(f"[bold]Category:[/bold] {category}")
                    self.console.print(f"[bold]Source:[/bold] {source}")
                    self.console.print(f"[bold]Version:[/bold] {version[:16]}...")

                # Installation status
                is_installed = getattr(agent, "is_deployed", False)
                status = "Installed" if is_installed else "Available"
                self.console.print(f"[bold]Status:[/bold] {status}")

                Prompt.ask("\nPress Enter to continue")
            else:
                self.console.print("[red]Invalid selection[/red]")
                Prompt.ask("\nPress Enter to continue")

        except (ValueError, IndexError):
            self.console.print("[red]Invalid selection[/red]")
            Prompt.ask("\nPress Enter to continue")


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
