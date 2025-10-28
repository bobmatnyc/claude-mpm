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

import json
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.text import Text

from ...core.config import Config
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

    def __init__(self):
        super().__init__("configure")
        self.console = default_console
        self.version_service = VersionService()
        self.current_scope = "project"
        self.project_dir = Path.cwd()
        self.agent_manager = None
        self.hook_manager = HookManager(self.console)
        self.behavior_manager = None  # Initialized when scope is set
        self._agent_display = None  # Lazy-initialized
        self._persistence = None  # Lazy-initialized
        self._navigation = None  # Lazy-initialized
        self._template_editor = None  # Lazy-initialized
        self._startup_manager = None  # Lazy-initialized

    def validate_args(self, args) -> Optional[str]:
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

    def run(self, args) -> CommandResult:
        """Execute the configure command."""
        # Set configuration scope
        self.current_scope = getattr(args, "scope", "project")
        if getattr(args, "project_dir", None):
            self.project_dir = Path(args.project_dir)

        # Initialize agent manager and behavior manager with appropriate config directory
        if self.current_scope == "project":
            config_dir = self.project_dir / ".claude-mpm"
        else:
            config_dir = Path.home() / ".claude-mpm"
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
        """Agent management interface."""
        while True:
            self.console.clear()
            self._display_header()

            # Display available agents
            agents = self.agent_manager.discover_agents()
            self._display_agents_table(agents)

            # Show agent menu
            self.console.print("\n[bold]Agent Management Options:[/bold]")

            # Use Text objects to properly display shortcuts with styling
            text_t = Text("  ")
            text_t.append("[t]", style="bold blue")
            text_t.append(" Toggle agents (enable/disable multiple)")
            self.console.print(text_t)

            text_c = Text("  ")
            text_c.append("[c]", style="bold blue")
            text_c.append(" Customize agent template")
            self.console.print(text_c)

            text_v = Text("  ")
            text_v.append("[v]", style="bold blue")
            text_v.append(" View agent details")
            self.console.print(text_v)

            text_r = Text("  ")
            text_r.append("[r]", style="bold blue")
            text_r.append(" Reset agent to defaults")
            self.console.print(text_r)

            text_b = Text("  ")
            text_b.append("[b]", style="bold blue")
            text_b.append(" Back to main menu")
            self.console.print(text_b)

            self.console.print()

            choice = Prompt.ask("[bold blue]Select an option[/bold blue]", default="b")

            if choice == "b":
                break
            if choice == "t":
                self._toggle_agents_interactive(agents)
            elif choice == "c":
                self._customize_agent_template(agents)
            elif choice == "v":
                self._view_agent_details(agents)
            elif choice == "r":
                self._reset_agent_defaults(agents)
            else:
                self.console.print("[red]Invalid choice.[/red]")
                Prompt.ask("Press Enter to continue")

    def _display_agents_table(self, agents: List[AgentConfig]) -> None:
        """Display a table of available agents."""
        self.agent_display.display_agents_table(agents)

    def _display_agents_with_pending_states(self, agents: List[AgentConfig]) -> None:
        """Display agents table with pending state indicators."""
        self.agent_display.display_agents_with_pending_states(agents)

    def _toggle_agents_interactive(self, agents: List[AgentConfig]) -> None:
        """Interactive multi-agent enable/disable with batch save."""

        # Initialize pending states from current states
        for agent in agents:
            current_state = self.agent_manager.is_agent_enabled(agent.name)
            self.agent_manager.set_agent_enabled_deferred(agent.name, current_state)

        while True:
            # Display table with pending states
            self._display_agents_with_pending_states(agents)

            # Show menu
            self.console.print("\n[bold]Toggle Agent Status:[/bold]")
            text_toggle = Text("  ")
            text_toggle.append("[t]", style="bold blue")
            text_toggle.append(" Enter agent IDs to toggle (e.g., '1,3,5' or '1-4')")
            self.console.print(text_toggle)

            text_all = Text("  ")
            text_all.append("[a]", style="bold blue")
            text_all.append(" Enable all agents")
            self.console.print(text_all)

            text_none = Text("  ")
            text_none.append("[n]", style="bold blue")
            text_none.append(" Disable all agents")
            self.console.print(text_none)

            text_save = Text("  ")
            text_save.append("[s]", style="bold green")
            text_save.append(" Save changes and return")
            self.console.print(text_save)

            text_cancel = Text("  ")
            text_cancel.append("[c]", style="bold magenta")
            text_cancel.append(" Cancel (discard changes)")
            self.console.print(text_cancel)

            choice = (
                Prompt.ask("[bold blue]Select an option[/bold blue]", default="s")
                .strip()
                .lower()
            )

            if choice == "s":
                if self.agent_manager.has_pending_changes():
                    self.agent_manager.commit_deferred_changes()
                    self.console.print("[green]✓ Changes saved successfully![/green]")
                else:
                    self.console.print("[yellow]No changes to save.[/yellow]")
                Prompt.ask("Press Enter to continue")
                break
            if choice == "c":
                self.agent_manager.discard_deferred_changes()
                self.console.print("[yellow]Changes discarded.[/yellow]")
                Prompt.ask("Press Enter to continue")
                break
            if choice == "a":
                for agent in agents:
                    self.agent_manager.set_agent_enabled_deferred(agent.name, True)
            elif choice == "n":
                for agent in agents:
                    self.agent_manager.set_agent_enabled_deferred(agent.name, False)
            elif choice == "t" or choice.replace(",", "").replace("-", "").isdigit():
                selected_ids = self._parse_id_selection(
                    choice if choice != "t" else Prompt.ask("Enter IDs"), len(agents)
                )
                for idx in selected_ids:
                    if 1 <= idx <= len(agents):
                        agent = agents[idx - 1]
                        current = self.agent_manager.get_pending_state(agent.name)
                        self.agent_manager.set_agent_enabled_deferred(
                            agent.name, not current
                        )

    def _customize_agent_template(self, agents: List[AgentConfig]) -> None:
        """Customize agent JSON template."""
        self.template_editor.customize_agent_template(agents)

    def _edit_agent_template(self, agent: AgentConfig) -> None:
        """Edit an agent's JSON template."""
        self.template_editor.edit_agent_template(agent)

    def _get_agent_template_path(self, agent_name: str) -> Path:
        """Get the path to an agent's template file."""
        return self.template_editor.get_agent_template_path(agent_name)

    def _edit_in_external_editor(self, template_path: Path, template: Dict) -> None:
        """Open template in external editor."""
        self.template_editor.edit_in_external_editor(template_path, template)

    def _modify_template_field(self, template: Dict, template_path: Path) -> None:
        """Add or modify a field in the template."""
        self.template_editor.modify_template_field(template, template_path)

    def _remove_template_field(self, template: Dict, template_path: Path) -> None:
        """Remove a field from the template."""
        self.template_editor.remove_template_field(template, template_path)

    def _reset_template(self, agent: AgentConfig, template_path: Path) -> None:
        """Reset template to defaults."""
        self.template_editor.reset_template(agent, template_path)

    def _create_custom_template_copy(self, agent: AgentConfig, template: Dict) -> None:
        """Create a customized copy of a system template."""
        self.template_editor.create_custom_template_copy(agent, template)

    def _view_full_template(self, template: Dict) -> None:
        """View the full template without truncation."""
        self.template_editor.view_full_template(template)

    def _reset_agent_defaults(self, agents: List[AgentConfig]) -> None:
        """Reset an agent to default enabled state and remove custom template."""
        self.template_editor.reset_agent_defaults(agents)

    def _edit_templates(self) -> None:
        """Template editing interface."""
        self.template_editor.edit_templates_interface()

    def _manage_behaviors(self) -> None:
        """Behavior file management interface."""
        # Note: BehaviorManager handles its own loop and clears screen
        # but doesn't display our header. We'll need to update BehaviorManager
        # to accept a header callback in the future. For now, just delegate.
        self.behavior_manager.manage_behaviors()

    def _manage_skills(self) -> None:
        """Skills management interface."""
        from ...cli.interactive.skills_wizard import SkillsWizard
        from ...skills.skill_manager import get_manager

        wizard = SkillsWizard()
        manager = get_manager()

        while True:
            self.console.clear()
            self._display_header()

            self.console.print("\n[bold]Skills Management Options:[/bold]\n")
            self.console.print("  [1] View Available Skills")
            self.console.print("  [2] Configure Skills for Agents")
            self.console.print("  [3] View Current Skill Mappings")
            self.console.print("  [4] Auto-Link Skills to Agents")
            self.console.print("  [b] Back to Main Menu")
            self.console.print()

            choice = Prompt.ask("[bold blue]Select an option[/bold blue]", default="b")

            if choice == "1":
                # View available skills
                self.console.clear()
                self._display_header()
                wizard.list_available_skills()
                Prompt.ask("\nPress Enter to continue")

            elif choice == "2":
                # Configure skills interactively
                self.console.clear()
                self._display_header()

                # Get list of enabled agents
                agents = self.agent_manager.discover_agents()
                enabled_agents = [
                    a.name
                    for a in agents
                    if self.agent_manager.get_pending_state(a.name)
                ]

                if not enabled_agents:
                    self.console.print(
                        "[yellow]No agents are currently enabled.[/yellow]"
                    )
                    self.console.print(
                        "Please enable agents first in Agent Management."
                    )
                    Prompt.ask("\nPress Enter to continue")
                    continue

                # Run skills wizard
                success, mapping = wizard.run_interactive_selection(enabled_agents)

                if success:
                    # Save the configuration
                    manager.save_mappings_to_config()
                    self.console.print("\n[green]✓ Skills configuration saved![/green]")
                else:
                    self.console.print(
                        "\n[yellow]Skills configuration cancelled.[/yellow]"
                    )

                Prompt.ask("\nPress Enter to continue")

            elif choice == "3":
                # View current mappings
                self.console.clear()
                self._display_header()

                self.console.print("\n[bold]Current Skill Mappings:[/bold]\n")

                mappings = manager.list_agent_skill_mappings()
                if not mappings:
                    self.console.print("[dim]No skill mappings configured yet.[/dim]")
                else:
                    from rich.table import Table

                    table = Table(show_header=True, header_style="bold cyan")
                    table.add_column("Agent", style="yellow")
                    table.add_column("Skills", style="green")

                    for agent_id, skills in mappings.items():
                        skills_str = (
                            ", ".join(skills) if skills else "[dim](none)[/dim]"
                        )
                        table.add_row(agent_id, skills_str)

                    self.console.print(table)

                Prompt.ask("\nPress Enter to continue")

            elif choice == "4":
                # Auto-link skills
                self.console.clear()
                self._display_header()

                self.console.print("\n[bold]Auto-Linking Skills to Agents...[/bold]\n")

                # Get enabled agents
                agents = self.agent_manager.discover_agents()
                enabled_agents = [
                    a.name
                    for a in agents
                    if self.agent_manager.get_pending_state(a.name)
                ]

                if not enabled_agents:
                    self.console.print(
                        "[yellow]No agents are currently enabled.[/yellow]"
                    )
                    self.console.print(
                        "Please enable agents first in Agent Management."
                    )
                    Prompt.ask("\nPress Enter to continue")
                    continue

                # Auto-link
                mapping = wizard._auto_link_skills(enabled_agents)

                # Display preview
                self.console.print("Auto-linked skills:\n")
                for agent_id, skills in mapping.items():
                    self.console.print(f"  [yellow]{agent_id}[/yellow]:")
                    for skill in skills:
                        self.console.print(f"    - {skill}")

                # Confirm
                confirm = Confirm.ask("\nApply this configuration?", default=True)

                if confirm:
                    wizard._apply_skills_configuration(mapping)
                    manager.save_mappings_to_config()
                    self.console.print("\n[green]✓ Auto-linking complete![/green]")
                else:
                    self.console.print("\n[yellow]Auto-linking cancelled.[/yellow]")

                Prompt.ask("\nPress Enter to continue")

            elif choice == "b":
                break
            else:
                self.console.print("[red]Invalid choice. Please try again.[/red]")
                Prompt.ask("\nPress Enter to continue")

    def _display_behavior_files(self) -> None:
        """Display current behavior files."""
        self.behavior_manager.display_behavior_files()

    def _edit_identity_config(self) -> None:
        """Edit identity configuration."""
        self.behavior_manager.edit_identity_config()

    def _edit_workflow_config(self) -> None:
        """Edit workflow configuration."""
        self.behavior_manager.edit_workflow_config()

    def _import_behavior_file(self) -> None:
        """Import a behavior file."""
        self.behavior_manager.import_behavior_file()

    def _export_behavior_file(self) -> None:
        """Export a behavior file."""
        self.behavior_manager.export_behavior_file()

    def _manage_startup_configuration(self) -> bool:
        """Manage startup configuration for MCP services and agents."""
        return self.startup_manager.manage_startup_configuration()

    def _load_startup_configuration(self, config: Config) -> Dict:
        """Load current startup configuration from config."""
        return self.startup_manager.load_startup_configuration(config)

    def _display_startup_configuration(self, startup_config: Dict) -> None:
        """Display current startup configuration in a table."""
        self.startup_manager.display_startup_configuration(startup_config)

    def _configure_mcp_services(self, startup_config: Dict, config: Config) -> None:
        """Configure which MCP services to enable at startup."""
        self.startup_manager.configure_mcp_services(startup_config, config)

    def _configure_hook_services(self, startup_config: Dict, config: Config) -> None:
        """Configure which hook services to enable at startup."""
        self.startup_manager.configure_hook_services(startup_config, config)

    def _configure_system_agents(self, startup_config: Dict, config: Config) -> None:
        """Configure which system agents to deploy at startup."""
        self.startup_manager.configure_system_agents(startup_config, config)

    def _parse_id_selection(self, selection: str, max_id: int) -> List[int]:
        """Parse ID selection string (e.g., '1,3,5' or '1-4')."""
        return parse_id_selection(selection, max_id)

    def _enable_all_services(self, startup_config: Dict, config: Config) -> None:
        """Enable all services and agents."""
        self.startup_manager.enable_all_services(startup_config, config)

    def _disable_all_services(self, startup_config: Dict, config: Config) -> None:
        """Disable all services and agents."""
        self.startup_manager.disable_all_services(startup_config, config)

    def _reset_to_defaults(self, startup_config: Dict, config: Config) -> None:
        """Reset startup configuration to defaults."""
        self.startup_manager.reset_to_defaults(startup_config, config)

    def _save_startup_configuration(self, startup_config: Dict, config: Config) -> bool:
        """Save startup configuration to config file and return whether to proceed to startup."""
        return self.startup_manager.save_startup_configuration(startup_config, config)

    def _save_all_configuration(self) -> bool:
        """Save all configuration changes across all contexts."""
        return self.startup_manager.save_all_configuration()

    def _launch_claude_mpm(self) -> None:
        """Launch Claude MPM run command, replacing current process."""
        self.navigation.launch_claude_mpm()

    def _switch_scope(self) -> None:
        """Switch between project and user scope."""
        self.navigation.switch_scope()
        # Sync scope back from navigation
        self.current_scope = self.navigation.current_scope

    def _show_version_info_interactive(self) -> None:
        """Show version information in interactive mode."""
        self.persistence.show_version_info_interactive()

    # Non-interactive command methods

    def _list_agents_non_interactive(self) -> CommandResult:
        """List agents in non-interactive mode."""
        agents = self.agent_manager.discover_agents()

        data = []
        for agent in agents:
            data.append(
                {
                    "name": agent.name,
                    "enabled": self.agent_manager.is_agent_enabled(agent.name),
                    "description": agent.description,
                    "dependencies": agent.dependencies,
                }
            )

        # Print as JSON for scripting
        print(json.dumps(data, indent=2))

        return CommandResult.success_result("Agents listed", data={"agents": data})

    def _enable_agent_non_interactive(self, agent_name: str) -> CommandResult:
        """Enable an agent in non-interactive mode."""
        try:
            self.agent_manager.set_agent_enabled(agent_name, True)
            return CommandResult.success_result(f"Agent '{agent_name}' enabled")
        except Exception as e:
            return CommandResult.error_result(f"Failed to enable agent: {e}")

    def _disable_agent_non_interactive(self, agent_name: str) -> CommandResult:
        """Disable an agent in non-interactive mode."""
        try:
            self.agent_manager.set_agent_enabled(agent_name, False)
            return CommandResult.success_result(f"Agent '{agent_name}' disabled")
        except Exception as e:
            return CommandResult.error_result(f"Failed to disable agent: {e}")

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
        """Jump directly to agent management."""
        try:
            self._manage_agents()
            return CommandResult.success_result("Agent management completed")
        except KeyboardInterrupt:
            return CommandResult.success_result("Agent management cancelled")
        except Exception as e:
            return CommandResult.error_result(f"Agent management failed: {e}")

    def _run_template_editing(self) -> CommandResult:
        """Jump directly to template editing."""
        try:
            self._edit_templates()
            return CommandResult.success_result("Template editing completed")
        except KeyboardInterrupt:
            return CommandResult.success_result("Template editing cancelled")
        except Exception as e:
            return CommandResult.error_result(f"Template editing failed: {e}")

    def _run_behavior_management(self) -> CommandResult:
        """Jump directly to behavior management."""
        return self.behavior_manager.run_behavior_management()

    def _run_startup_configuration(self) -> CommandResult:
        """Jump directly to startup configuration."""
        try:
            proceed = self._manage_startup_configuration()
            if proceed:
                return CommandResult.success_result(
                    "Startup configuration saved, proceeding to startup"
                )
            return CommandResult.success_result("Startup configuration completed")
        except KeyboardInterrupt:
            return CommandResult.success_result("Startup configuration cancelled")
        except Exception as e:
            return CommandResult.error_result(f"Startup configuration failed: {e}")


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
