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
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

import questionary
import questionary.constants
import questionary.prompts.common  # For checkbox symbol customization
from questionary import Choice, Separator, Style
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.text import Text

from ...core.config import Config
from ...services.agents.agent_recommendation_service import AgentRecommendationService
from ...services.version_service import VersionService
from ...utils.agent_filters import apply_all_filters, get_deployed_agent_ids
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
        self.agent_manager = None
        self.hook_manager = HookManager(self.console)
        self.behavior_manager = None  # Initialized when scope is set
        self._agent_display = None  # Lazy-initialized
        self._persistence = None  # Lazy-initialized
        self._navigation = None  # Lazy-initialized
        self._template_editor = None  # Lazy-initialized
        self._startup_manager = None  # Lazy-initialized
        self._recommendation_service = None  # Lazy-initialized

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

    @property
    def recommendation_service(self) -> AgentRecommendationService:
        """Lazy-initialize recommendation service."""
        if self._recommendation_service is None:
            self._recommendation_service = AgentRecommendationService()
        return self._recommendation_service

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
        """Enhanced agent management with remote agent discovery and installation."""
        while True:
            self.console.clear()
            self.navigation.display_header()
            self.console.print("\n[bold blue]═══ Agent Management ═══[/bold blue]\n")

            # Load all agents with spinner (don't show partial state)
            agents = self._load_agents_with_spinner()

            if not agents:
                self.console.print("[yellow]No agents found[/yellow]")
                self.console.print(
                    "[dim]Configure sources with 'claude-mpm agent-source add'[/dim]\n"
                )
                Prompt.ask("\nPress Enter to continue")
                break

            # Now display everything at once (after all data loaded)
            self._display_agent_sources_and_list(agents)

            # Step 3: Simplified menu - only "Select Agents" option
            self.console.print()
            self.logger.debug("About to show agent management menu")
            try:
                choice = questionary.select(
                    "Agent Management:",
                    choices=[
                        "Select Agents",
                        questionary.Separator(),
                        "← Back to main menu",
                    ],
                    style=self.QUESTIONARY_STYLE,
                ).ask()

                if choice is None or choice == "← Back to main menu":
                    break

                # Map selection to action
                if choice == "Select Agents":
                    self.logger.debug("User selected 'Select Agents' from menu")
                    self._deploy_agents_unified(agents)
                    # Loop back to show updated state after deployment

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Operation cancelled[/yellow]")
                break
            except Exception as e:
                # Handle questionary menu failure
                import sys

                self.logger.error(f"Agent management menu failed: {e}", exc_info=True)
                self.console.print("[red]Error: Interactive menu failed[/red]")
                self.console.print(f"[dim]Reason: {e}[/dim]")
                if not sys.stdin.isatty():
                    self.console.print(
                        "[dim]Interactive terminal required for this operation[/dim]"
                    )
                    self.console.print("[dim]Use command-line options instead:[/dim]")
                    self.console.print(
                        "[dim]  claude-mpm configure --list-agents[/dim]"
                    )
                    self.console.print(
                        "[dim]  claude-mpm configure --enable-agent <id>[/dim]"
                    )
                Prompt.ask("\nPress Enter to continue")
                break

    def _load_agents_with_spinner(self) -> List[AgentConfig]:
        """Load agents with loading indicator, don't show partial state.

        Returns:
            List of discovered agents with deployment status set.
        """

        agents = []
        with self.console.status(
            "[bold blue]Loading agents...[/bold blue]", spinner="dots"
        ):
            try:
                # Discover agents (includes both local and remote)
                agents = self.agent_manager.discover_agents(include_remote=True)

                # Set deployment status on each agent for display
                deployed_ids = get_deployed_agent_ids()
                for agent in agents:
                    # Use agent_id (technical ID) for comparison, not display name
                    agent_id = getattr(agent, "agent_id", agent.name)
                    agent_leaf_name = agent_id.split("/")[-1]
                    agent.is_deployed = agent_leaf_name in deployed_ids

                # Filter BASE_AGENT from display (1M-502 Phase 1)
                agents = self._filter_agent_configs(agents, filter_deployed=False)

            except Exception as e:
                self.console.print(f"[red]Error discovering agents: {e}[/red]")
                self.logger.error(f"Agent discovery failed: {e}", exc_info=True)
                agents = []

        return agents

    def _display_agent_sources_and_list(self, agents: List[AgentConfig]) -> None:
        """Display agent sources and agent list (only after all data loaded).

        Args:
            agents: List of discovered agents with deployment status.
        """
        from rich.table import Table

        # Step 1: Show configured sources
        self.console.print("[bold white]═══ Agent Sources ═══[/bold white]\n")

        sources = self._get_configured_sources()
        if sources:
            sources_table = Table(show_header=True, header_style="bold white")
            sources_table.add_column(
                "Source",
                style="bright_yellow",
                width=40,
                no_wrap=True,
                overflow="ellipsis",
            )
            sources_table.add_column("Status", style="green", width=15, no_wrap=True)
            sources_table.add_column("Agents", style="yellow", width=10, no_wrap=True)

            for source in sources:
                status = "✓ Active" if source.get("enabled", True) else "Disabled"
                agent_count = source.get("agent_count", "?")
                sources_table.add_row(source["identifier"], status, str(agent_count))

            self.console.print(sources_table)
        else:
            self.console.print("[yellow]No agent sources configured[/yellow]")
            self.console.print(
                "[dim]Default source 'bobmatnyc/claude-mpm-agents' will be used[/dim]\n"
            )

        # Step 2: Display available agents
        self.console.print("\n[bold white]═══ Available Agents ═══[/bold white]\n")

        if agents:
            # Show progress spinner while recommendation service processes agents
            with self.console.status(
                "[bold blue]Preparing agent list...[/bold blue]", spinner="dots"
            ):
                self._display_agents_with_source_info(agents)
        else:
            self.console.print("[yellow]No agents available[/yellow]")

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

                    # Auto-deploy enabled agents to .claude/agents/
                    self._auto_deploy_enabled_agents(agents)
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

    def _auto_deploy_enabled_agents(self, agents: List[AgentConfig]) -> None:
        """Auto-deploy enabled agents after saving configuration.

        WHY: When users enable agents, they expect them to be deployed
        automatically to .claude/agents/ so they're available for use.
        """
        try:
            # Get list of enabled agents from states
            enabled_agents = [
                agent
                for agent in agents
                if self.agent_manager.is_agent_enabled(agent.name)
            ]

            if not enabled_agents:
                return

            # Show deployment progress
            self.console.print(
                f"\n[bold blue]Deploying {len(enabled_agents)} enabled agent(s)...[/bold blue]"
            )

            # Deploy each enabled agent
            success_count = 0
            failed_count = 0

            for agent in enabled_agents:
                # Deploy to .claude/agents/ (project-level)
                try:
                    if self._deploy_single_agent(agent, show_feedback=False):
                        success_count += 1
                        self.console.print(f"[green]✓ Deployed: {agent.name}[/green]")
                    else:
                        failed_count += 1
                        self.console.print(f"[yellow]⚠ Skipped: {agent.name}[/yellow]")
                except Exception as e:
                    failed_count += 1
                    self.logger.error(f"Failed to deploy {agent.name}: {e}")
                    self.console.print(f"[red]✗ Failed: {agent.name}[/red]")

            # Show summary
            if success_count > 0:
                self.console.print(
                    f"\n[green]✓ Successfully deployed {success_count} agent(s) to .claude/agents/[/green]"
                )
            if failed_count > 0:
                self.console.print(
                    f"[yellow]⚠ {failed_count} agent(s) failed or were skipped[/yellow]"
                )

        except Exception as e:
            self.logger.error(f"Auto-deployment failed: {e}", exc_info=True)
            self.console.print(f"[red]✗ Auto-deployment error: {e}[/red]")

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
                # Filter BASE_AGENT from all agent operations (1M-502 Phase 1)
                agents = self._filter_agent_configs(agents, filter_deployed=False)
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

                    table = Table(show_header=True, header_style="bold white")
                    table.add_column("Agent", style="white", no_wrap=True)
                    table.add_column("Skills", style="green", no_wrap=True)

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
                # Filter BASE_AGENT from all agent operations (1M-502 Phase 1)
                agents = self._filter_agent_configs(agents, filter_deployed=False)
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
        # Filter BASE_AGENT from all agent lists (1M-502 Phase 1)
        agents = self._filter_agent_configs(agents, filter_deployed=False)

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

    # ========================================================================
    # Enhanced Agent Management Methods (Remote Agent Discovery Integration)
    # ========================================================================

    def _get_configured_sources(self) -> List[Dict]:
        """Get list of configured agent sources with agent counts."""
        try:
            from claude_mpm.config.agent_sources import AgentSourceConfiguration

            config = AgentSourceConfiguration.load()

            # Convert repositories to source dictionaries
            sources = []
            for repo in config.repositories:
                # Extract identifier from repository
                identifier = repo.identifier

                # Count agents in cache
                # Note: identifier already includes subdirectory path (e.g., "bobmatnyc/claude-mpm-agents/agents")
                cache_dir = (
                    Path.home() / ".claude-mpm" / "cache" / "agents" / identifier
                )
                agent_count = 0
                if cache_dir.exists():
                    # cache_dir IS the agents directory - no need to append /agents
                    agent_count = len(list(cache_dir.rglob("*.md")))

                sources.append(
                    {
                        "identifier": identifier,
                        "url": repo.url,
                        "enabled": repo.enabled,
                        "priority": repo.priority,
                        "agent_count": agent_count,
                    }
                )

            return sources
        except Exception as e:
            self.logger.warning(f"Failed to get configured sources: {e}")
            return []

    def _filter_agent_configs(
        self, agents: List[AgentConfig], filter_deployed: bool = False
    ) -> List[AgentConfig]:
        """Filter AgentConfig objects using agent_filters utilities.

        Converts AgentConfig objects to dictionaries for filtering,
        then back to AgentConfig. Always filters BASE_AGENT.
        Optionally filters deployed agents.

        Args:
            agents: List of AgentConfig objects
            filter_deployed: Whether to filter out deployed agents (default: False)

        Returns:
            Filtered list of AgentConfig objects
        """
        # Convert AgentConfig to dict format for filtering
        agent_dicts = []
        for agent in agents:
            agent_dicts.append(
                {
                    "agent_id": agent.name,
                    "name": agent.name,
                    "description": agent.description,
                    "deployed": getattr(agent, "is_deployed", False),
                }
            )

        # Apply filters (always filter BASE_AGENT)
        filtered_dicts = apply_all_filters(
            agent_dicts, filter_base=True, filter_deployed=filter_deployed
        )

        # Convert back to AgentConfig objects
        filtered_names = {d["agent_id"] for d in filtered_dicts}
        return [a for a in agents if a.name in filtered_names]

    @staticmethod
    def _calculate_column_widths(
        terminal_width: int, columns: Dict[str, int]
    ) -> Dict[str, int]:
        """Calculate dynamic column widths based on terminal size.

        Args:
            terminal_width: Current terminal width in characters
            columns: Dict mapping column names to minimum widths

        Returns:
            Dict mapping column names to calculated widths

        Design:
            - Ensures minimum widths are respected
            - Distributes extra space proportionally
            - Handles narrow terminals gracefully (minimum 80 chars)
        """
        # Ensure minimum terminal width
        min_terminal_width = 80
        terminal_width = max(terminal_width, min_terminal_width)

        # Calculate total minimum width needed
        total_min_width = sum(columns.values())

        # Account for table borders and padding (2 chars per column + 2 for edges)
        overhead = (len(columns) * 2) + 2
        available_width = terminal_width - overhead

        # If we have extra space, distribute proportionally
        if available_width > total_min_width:
            extra_space = available_width - total_min_width
            total_weight = sum(columns.values())

            result = {}
            for col_name, min_width in columns.items():
                # Distribute extra space based on minimum width proportion
                proportion = min_width / total_weight
                extra = int(extra_space * proportion)
                result[col_name] = min_width + extra
            return result
        # Terminal too narrow, use minimum widths
        return columns.copy()

    def _format_display_name(self, name: str) -> str:
        """Format internal agent name to human-readable display name.

        Converts underscores/hyphens to spaces and title-cases.
        Examples:
            agentic_coder_optimizer -> Agentic Coder Optimizer
            python-engineer -> Python Engineer
            api_qa_agent -> Api Qa Agent

        Args:
            name: Internal agent name (may contain underscores, hyphens)

        Returns:
            Human-readable display name
        """
        return name.replace("_", " ").replace("-", " ").title()

    def _display_agents_with_source_info(self, agents: List[AgentConfig]) -> None:
        """Display agents table with source information and installation status."""
        from rich.table import Table

        # Get recommended agents for this project
        try:
            recommended_agents = self.recommendation_service.get_recommended_agents(
                str(self.project_dir)
            )
        except Exception as e:
            self.logger.warning(f"Failed to get recommended agents: {e}")
            recommended_agents = set()

        # Get terminal width and calculate dynamic column widths
        terminal_width = shutil.get_terminal_size().columns
        min_widths = {
            "#": 4,
            "Agent ID": 30,
            "Name": 20,
            "Source": 15,
            "Status": 10,
        }
        widths = self._calculate_column_widths(terminal_width, min_widths)

        agents_table = Table(show_header=True, header_style="bold cyan")
        agents_table.add_column(
            "#", style="bright_black", width=widths["#"], no_wrap=True
        )
        agents_table.add_column(
            "Agent ID",
            style="bright_black",
            width=widths["Agent ID"],
            no_wrap=True,
            overflow="ellipsis",
        )
        agents_table.add_column(
            "Name",
            style="bright_cyan",
            width=widths["Name"],
            no_wrap=True,
            overflow="ellipsis",
        )
        agents_table.add_column(
            "Source",
            style="bright_yellow",
            width=widths["Source"],
            no_wrap=True,
        )
        agents_table.add_column(
            "Status", style="bright_black", width=widths["Status"], no_wrap=True
        )

        # FIX 3: Get deployed agent IDs once, before the loop (efficiency)
        deployed_ids = get_deployed_agent_ids()

        recommended_count = 0
        for idx, agent in enumerate(agents, 1):
            # Determine source with repo name
            source_type = getattr(agent, "source_type", "local")

            if source_type == "remote":
                # Get repo name from agent metadata
                source_dict = getattr(agent, "source_dict", {})
                repo_url = source_dict.get("source", "")

                # Extract repo name from URL
                if (
                    "bobmatnyc/claude-mpm" in repo_url
                    or "claude-mpm" in repo_url.lower()
                ):
                    source_label = "MPM Agents"
                elif "/" in repo_url:
                    # Extract last part of org/repo
                    parts = repo_url.rstrip("/").split("/")
                    if len(parts) >= 2:
                        source_label = f"{parts[-2]}/{parts[-1]}"
                    else:
                        source_label = "Community"
                else:
                    source_label = "Community"
            else:
                source_label = "Local"

            # FIX 2: Check actual deployment status from .claude/agents/ directory
            # Use agent_id (technical ID like "python-engineer") not display name
            agent_id = getattr(agent, "agent_id", agent.name)
            is_installed = agent_id in deployed_ids
            if is_installed:
                status = "[green]Installed[/green]"
            else:
                status = "Available"

            # Check if agent is recommended
            # Handle both hierarchical paths (e.g., "engineer/backend/python-engineer")
            # and leaf names (e.g., "python-engineer")
            agent_full_path = agent.name
            agent_leaf_name = (
                agent_full_path.split("/")[-1]
                if "/" in agent_full_path
                else agent_full_path
            )

            for recommended_id in recommended_agents:
                # Check if the recommended_id matches either the full path or just the leaf name
                recommended_leaf = (
                    recommended_id.split("/")[-1]
                    if "/" in recommended_id
                    else recommended_id
                )
                if (
                    agent_full_path == recommended_id
                    or agent_leaf_name == recommended_leaf
                ):
                    recommended_count += 1
                    break

            # FIX 1: Show agent_id (technical ID) in first column, not display name
            agent_id_display = getattr(agent, "agent_id", agent.name)

            # Get display name and format it properly
            # Raw display_name from YAML may contain underscores (e.g., "agentic_coder_optimizer")
            raw_display_name = getattr(agent, "display_name", agent.name)
            display_name = self._format_display_name(raw_display_name)

            agents_table.add_row(
                str(idx), agent_id_display, display_name, source_label, status
            )

        self.console.print(agents_table)

        # Show legend if there are recommended agents
        if recommended_count > 0:
            # Get detection summary for context
            try:
                summary = self.recommendation_service.get_detection_summary(
                    str(self.project_dir)
                )
                detected_langs = (
                    ", ".join(summary.get("detected_languages", [])) or "None"
                )
                ", ".join(summary.get("detected_frameworks", [])) or "None"
                self.console.print(
                    f"\n[dim]* = recommended for this project "
                    f"(detected: {detected_langs})[/dim]"
                )
            except Exception:
                self.console.print("\n[dim]* = recommended for this project[/dim]")

        # Show installed vs available count (use deployed_ids for accuracy)
        # Use agent_id (technical ID) for comparison, not display name
        installed_count = sum(
            1 for a in agents if getattr(a, "agent_id", a.name) in deployed_ids
        )
        available_count = len(agents) - installed_count
        self.console.print(
            f"\n[green]✓ {installed_count} installed[/green] | "
            f"[dim]{available_count} available[/dim] | "
            f"[yellow]{recommended_count} recommended[/yellow] | "
            f"[dim]Total: {len(agents)}[/dim]"
        )

    def _manage_sources(self) -> None:
        """Interactive source management."""
        self.console.print("\n[bold white]═══ Manage Agent Sources ═══[/bold white]\n")
        self.console.print(
            "[dim]Use 'claude-mpm agent-source' command to add/remove sources[/dim]"
        )
        self.console.print("\nExamples:")
        self.console.print("  claude-mpm agent-source add <git-url>")
        self.console.print("  claude-mpm agent-source remove <identifier>")
        self.console.print("  claude-mpm agent-source list")
        Prompt.ask("\nPress Enter to continue")

    def _deploy_agents_unified(self, agents: List[AgentConfig]) -> None:
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

        # Build mapping: leaf name -> full path for deployed agents
        # Use agent_id (technical ID) for comparison, not display name
        deployed_full_paths = set()
        for agent in agents:
            agent_id = getattr(agent, "agent_id", agent.name)
            agent_leaf_name = agent_id.split("/")[-1]
            if agent_leaf_name in deployed_ids:
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
        questionary.prompts.common.INDICATOR_SELECTED = "[✓]"
        questionary.prompts.common.INDICATOR_UNSELECTED = "[ ]"

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
                    choices.append(
                        Choice(
                            f"  [Deselect all from {collection_id}]",
                            value=f"__DESELECT_ALL_{collection_id}__",
                            checked=False,
                        )
                    )
                else:
                    choices.append(
                        Choice(
                            f"  [Select all from {collection_id}]",
                            value=f"__SELECT_ALL_{collection_id}__",
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

                        # Check if agent is deployed (exists in .claude/agents/)

                        # Format choice text (no asterisk needed)
                        choice_text = f"    {display_name}"

                        is_selected = agent_id in current_selection

                        choices.append(
                            Choice(
                                title=choice_text,
                                value=agent_id,  # Use agent_id for value
                                checked=is_selected,
                            )
                        )

            self.console.print("\n[bold cyan]Select Agents to Install[/bold cyan]")
            self.console.print("[dim][✓] Checked = Installed (uncheck to remove)[/dim]")
            self.console.print(
                "[dim][ ] Unchecked = Available (check to install)[/dim]"
            )
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
            break

        # Determine changes
        to_deploy = final_selection - deployed_full_paths
        to_remove = deployed_full_paths - final_selection

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

                # Remove from all possible locations
                paths_to_check = [
                    Path.cwd() / ".claude-mpm" / "agents" / f"{leaf_name}.md",
                    Path.cwd() / ".claude" / "agents" / f"{leaf_name}.md",
                    Path.home() / ".claude" / "agents" / f"{leaf_name}.md",
                ]

                removed = False
                for path in paths_to_check:
                    if path.exists():
                        path.unlink()
                        removed = True

                # Also remove from virtual deployment state
                deployment_state_paths = [
                    Path.cwd() / ".claude" / "agents" / ".mpm_deployment_state",
                    Path.home() / ".claude" / "agents" / ".mpm_deployment_state",
                ]

                for state_path in deployment_state_paths:
                    if state_path.exists():
                        try:
                            with state_path.open() as f:
                                state = json.load(f)
                            agents_in_state = state.get("last_check_results", {}).get(
                                "agents", {}
                            )
                            if leaf_name in agents_in_state:
                                del agents_in_state[leaf_name]
                                removed = True
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

    def _deploy_agents_individual(self, agents: List[AgentConfig]) -> None:
        """Manage agent installation state (unified install/remove interface).

        DEPRECATED: Use _deploy_agents_unified instead.
        This method is kept for backward compatibility but should not be used.
        """
        if not agents:
            self.console.print("[yellow]No agents available[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return

        # Get ALL agents (filter BASE_AGENT but keep deployed agents visible)
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

        # Get deployed agent IDs (original state - for calculating final changes)
        # NOTE: deployed_ids contains LEAF NAMES (e.g., "python-engineer")
        deployed_ids = get_deployed_agent_ids()

        if not all_agents:
            self.console.print("[yellow]No agents available[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return

        # Build mapping: leaf name -> full path for deployed agents
        # This allows comparing deployed_ids (leaf names) with agent.agent_id (full paths)
        deployed_full_paths = set()
        for agent in agents:
            # FIX: Use agent_id (technical ID) instead of display name
            agent_id = getattr(agent, "agent_id", agent.name)
            agent_leaf_name = agent_id.split("/")[-1]
            if agent_leaf_name in deployed_ids:
                deployed_full_paths.add(agent_id)

        # Track current selection state (starts with deployed full paths, updated after each iteration)
        current_selection = deployed_full_paths.copy()

        # Loop to allow adjusting selection
        while True:
            # Build agent mapping and collections
            agent_map = {}  # For lookup after selection
            collections = defaultdict(list)

            for agent in agents:
                # FIX: Use agent_id (technical ID) for comparison
                agent_id = getattr(agent, "agent_id", agent.name)
                if agent_id in {a["agent_id"] for a in all_agents}:
                    # Determine collection ID
                    source_type = getattr(agent, "source_type", "local")
                    if source_type == "remote":
                        source_dict = getattr(agent, "source_dict", {})
                        repo_url = source_dict.get("source", "")
                        # Extract repository name from URL
                        if "/" in repo_url:
                            parts = repo_url.rstrip("/").split("/")
                            if len(parts) >= 2:
                                collection_id = f"{parts[-2]}/{parts[-1]}"
                            else:
                                collection_id = "remote"
                        else:
                            collection_id = "remote"
                    else:
                        collection_id = "local"

                    collections[collection_id].append(agent)
                    agent_map[agent_id] = agent  # FIX: Use agent_id as key

            # STEP 1: Collection-level selection
            self.console.print("\n[bold cyan]Select Agent Collections[/bold cyan]")
            self.console.print(
                "[dim]Checking a collection installs ALL agents in that collection[/dim]"
            )
            self.console.print(
                "[dim]Unchecking a collection removes ALL agents in that collection[/dim]"
            )
            self.console.print(
                "[dim]For partial deployment, use 'Fine-tune individual agents'[/dim]\n"
            )

            collection_choices = []
            for collection_id in sorted(collections.keys()):
                agents_in_collection = collections[collection_id]

                # Check if ANY agent in this collection is currently deployed
                # This reflects actual deployment state, not just selection
                # FIX: Use agent_id for comparison with current_selection
                any_deployed = any(
                    getattr(agent, "agent_id", agent.name) in current_selection
                    for agent in agents_in_collection
                )

                # Count deployed agents for display
                # FIX: Use agent_id for comparison with current_selection
                deployed_count = sum(
                    1
                    for agent in agents_in_collection
                    if getattr(agent, "agent_id", agent.name) in current_selection
                )

                collection_choices.append(
                    Choice(
                        f"{collection_id} ({deployed_count}/{len(agents_in_collection)} deployed)",
                        value=collection_id,
                        checked=any_deployed,
                    )
                )

            # Add option to fine-tune individual agents
            collection_choices.append(Separator())
            collection_choices.append(
                Choice(
                    "→ Fine-tune individual agents...",
                    value="__INDIVIDUAL__",
                    checked=False,
                )
            )

            # Monkey-patch questionary symbols for better visibility
            questionary.prompts.common.INDICATOR_SELECTED = "[✓]"
            questionary.prompts.common.INDICATOR_UNSELECTED = "[ ]"

            try:
                selected_collections = questionary.checkbox(
                    "Select agent collections to deploy:",
                    choices=collection_choices,
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
                    self.console.print(
                        "[dim]  --enable-agent/--disable-agent for scripting[/dim]"
                    )
                else:
                    self.console.print(
                        "[dim]This might be a terminal compatibility issue.[/dim]"
                    )
                Prompt.ask("\nPress Enter to continue")
                return

            # Handle cancellation
            if selected_collections is None:
                import sys

                if not sys.stdin.isatty():
                    self.console.print(
                        "[red]Error: Interactive terminal required for agent selection[/red]"
                    )
                    self.console.print(
                        "[dim]Use --list-agents to see available agents[/dim]"
                    )
                    self.console.print(
                        "[dim]Use --enable-agent/--disable-agent for non-interactive mode[/dim]"
                    )
                else:
                    self.console.print("[yellow]No changes made[/yellow]")
                Prompt.ask("\nPress Enter to continue")
                return

            # STEP 2: Check if user wants individual selection
            if "__INDIVIDUAL__" in selected_collections:
                # Remove the __INDIVIDUAL__ marker
                selected_collections = [
                    c for c in selected_collections if c != "__INDIVIDUAL__"
                ]

                # Build individual agent choices with grouping
                agent_choices = []
                for collection_id in sorted(collections.keys()):
                    agents_in_collection = collections[collection_id]

                    # Add collection header separator
                    agent_choices.append(
                        Separator(
                            f"\n── {collection_id} ({len(agents_in_collection)} agents) ──"
                        )
                    )

                    # Add individual agents from this collection
                    # FIX: Use agent_id for sorting, comparison, and values
                    for agent in sorted(
                        agents_in_collection,
                        key=lambda a: getattr(a, "agent_id", a.name),
                    ):
                        agent_id = getattr(agent, "agent_id", agent.name)
                        raw_display_name = getattr(agent, "display_name", agent.name)
                        display_name = self._format_display_name(raw_display_name)
                        is_selected = agent_id in deployed_full_paths

                        choice_text = f"{agent_id}"
                        if display_name and display_name != agent_id:
                            choice_text += f" - {display_name}"

                        agent_choices.append(
                            Choice(
                                title=choice_text, value=agent_id, checked=is_selected
                            )
                        )

                self.console.print(
                    "\n[bold cyan]Fine-tune Individual Agents[/bold cyan]"
                )
                self.console.print(
                    "[dim][✓] Checked = Installed (uncheck to remove)[/dim]"
                )
                self.console.print(
                    "[dim][ ] Unchecked = Available (check to install)[/dim]"
                )
                self.console.print(
                    "[dim]Use arrow keys to navigate, space to toggle, Enter to apply[/dim]\n"
                )

                try:
                    selected_agent_ids = questionary.checkbox(
                        "Select individual agents:",
                        choices=agent_choices,
                        style=self.QUESTIONARY_STYLE,
                    ).ask()
                except Exception as e:
                    import sys

                    self.logger.error(
                        f"Questionary checkbox failed: {e}", exc_info=True
                    )
                    self.console.print(
                        "[red]Error: Could not display interactive menu[/red]"
                    )
                    self.console.print(f"[dim]Reason: {e}[/dim]")
                    Prompt.ask("\nPress Enter to continue")
                    return

                if selected_agent_ids is None:
                    self.console.print("[yellow]No changes made[/yellow]")
                    Prompt.ask("\nPress Enter to continue")
                    return

                # Update current_selection with individual selections
                current_selection = set(selected_agent_ids)
            else:
                # Apply collection-level selections
                # For each collection, if it's selected, include ALL its agents
                # If it's not selected, exclude ALL its agents
                final_selections = set()
                for collection_id in selected_collections:
                    for agent in collections[collection_id]:
                        # FIX: Use agent_id for selection tracking
                        final_selections.add(getattr(agent, "agent_id", agent.name))

                # Update current_selection
                # This replaces the previous selection entirely with the new collection selections
                current_selection = final_selections

            # Determine actions based on ORIGINAL deployed state
            # Compare full paths to full paths (deployed_full_paths was built from deployed_ids)
            to_deploy = (
                current_selection - deployed_full_paths
            )  # Selected but not originally deployed

            # For removal, verify files actually exist before adding to the set
            # This prevents "Not found" warnings when multiple agents share leaf names
            to_remove = set()
            for agent_id in deployed_full_paths - current_selection:
                # Extract leaf name to check file existence
                leaf_name = agent_id.split("/")[-1] if "/" in agent_id else agent_id

                # Check all possible locations
                paths_to_check = [
                    Path.cwd() / ".claude-mpm" / "agents" / f"{leaf_name}.md",
                    Path.cwd() / ".claude" / "agents" / f"{leaf_name}.md",
                    Path.home() / ".claude" / "agents" / f"{leaf_name}.md",
                ]

                # Also check virtual deployment state
                state_exists = False
                deployment_state_paths = [
                    Path.cwd() / ".claude" / "agents" / ".mpm_deployment_state",
                    Path.home() / ".claude" / "agents" / ".mpm_deployment_state",
                ]

                for state_path in deployment_state_paths:
                    if state_path.exists():
                        try:
                            import json

                            with state_path.open() as f:
                                state = json.load(f)
                            agents_in_state = state.get("last_check_results", {}).get(
                                "agents", {}
                            )
                            if leaf_name in agents_in_state:
                                state_exists = True
                                break
                        except (json.JSONDecodeError, KeyError):
                            continue

                # Only add to removal set if file or state entry actually exists
                if any(p.exists() for p in paths_to_check) or state_exists:
                    to_remove.add(agent_id)

            if not to_deploy and not to_remove:
                self.console.print(
                    "[yellow]No changes needed - all selected agents are already installed[/yellow]"
                )
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

            # Ask user to confirm, adjust, or cancel
            action = questionary.select(
                "\nWhat would you like to do?",
                choices=[
                    questionary.Choice("Apply these changes", value="apply"),
                    questionary.Choice("Adjust selection", value="adjust"),
                    questionary.Choice("Cancel", value="cancel"),
                ],
                default="apply",
                style=self.QUESTIONARY_STYLE,
            ).ask()

            if action == "cancel":
                self.console.print("[yellow]Changes cancelled[/yellow]")
                Prompt.ask("\nPress Enter to continue")
                return
            if action == "adjust":
                # current_selection is already updated, loop will use it
                continue

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
                    # Note: Path is already imported at module level (line 17)

                    # Extract leaf name to match deployed filename
                    # agent_id may be hierarchical (e.g., "engineer/mobile/tauri-engineer")
                    # but deployed files use flattened leaf names (e.g., "tauri-engineer.md")
                    if "/" in agent_id:
                        leaf_name = agent_id.split("/")[-1]
                    else:
                        leaf_name = agent_id

                    # Remove from project, legacy, and user locations
                    project_path = (
                        Path.cwd() / ".claude-mpm" / "agents" / f"{leaf_name}.md"
                    )
                    legacy_path = Path.cwd() / ".claude" / "agents" / f"{leaf_name}.md"
                    user_path = Path.home() / ".claude" / "agents" / f"{leaf_name}.md"

                    removed = False
                    for path in [project_path, legacy_path, user_path]:
                        if path.exists():
                            path.unlink()
                            removed = True

                    # Also remove from virtual deployment state
                    deployment_state_paths = [
                        Path.cwd() / ".claude" / "agents" / ".mpm_deployment_state",
                        Path.home() / ".claude" / "agents" / ".mpm_deployment_state",
                    ]

                    for state_path in deployment_state_paths:
                        if state_path.exists():
                            try:
                                with state_path.open() as f:
                                    state = json.load(f)

                                # Remove agent from deployment state
                                # Deployment state uses leaf names, not full hierarchical paths
                                agents = state.get("last_check_results", {}).get(
                                    "agents", {}
                                )
                                if leaf_name in agents:
                                    del agents[leaf_name]
                                    removed = True

                                    # Save updated state
                                    with state_path.open("w") as f:
                                        json.dump(state, f, indent=2)
                            except (json.JSONDecodeError, KeyError) as e:
                                # Log but don't fail - physical removal still counts
                                self.logger.debug(
                                    f"Failed to update deployment state at {state_path}: {e}"
                                )

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
                self.console.print(
                    f"[green]✓ Installed {deploy_success} agent(s)[/green]"
                )
            if deploy_fail > 0:
                self.console.print(
                    f"[red]✗ Failed to install {deploy_fail} agent(s)[/red]"
                )
            if remove_success > 0:
                self.console.print(
                    f"[green]✓ Removed {remove_success} agent(s)[/green]"
                )
            if remove_fail > 0:
                self.console.print(
                    f"[red]✗ Failed to remove {remove_fail} agent(s)[/red]"
                )

            Prompt.ask("\nPress Enter to continue")
            # Exit the loop after successful execution
            break

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

    def _select_recommended_agents(self, agents: List[AgentConfig]) -> None:
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
        except Exception:
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

                # Determine target file name (use leaf name from hierarchical ID)
                if "/" in full_agent_id:
                    target_name = full_agent_id.split("/")[-1] + ".md"
                else:
                    target_name = full_agent_id + ".md"

                # Deploy to project-level agents directory
                target_dir = self.project_dir / ".claude" / "agents"
                target_dir.mkdir(parents=True, exist_ok=True)
                target_file = target_dir / target_name

                if show_feedback:
                    self.console.print(
                        f"\n[white]Installing {full_agent_id}...[/white]"
                    )

                # Copy the agent file
                import shutil

                shutil.copy2(source_file, target_file)

                if show_feedback:
                    self.console.print(
                        f"[green]✓ Successfully installed {full_agent_id} to {target_file}[/green]"
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
            if show_feedback:
                self.console.print(f"[red]Error installing agent: {e}[/red]")
                self.logger.error(f"Agent installation failed: {e}", exc_info=True)
                Prompt.ask("\nPress Enter to continue")
            return False

    def _remove_agents(self, agents: List[AgentConfig]) -> None:
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

                # Determine possible file names (hierarchical and leaf)
                file_names = [f"{full_agent_id}.md"]
                if "/" in full_agent_id:
                    leaf_name = full_agent_id.split("/")[-1]
                    file_names.append(f"{leaf_name}.md")

                # Remove from both project and user directories
                removed = False
                project_agent_dir = Path.cwd() / ".claude-mpm" / "agents"
                user_agent_dir = Path.home() / ".claude" / "agents"

                for file_name in file_names:
                    project_file = project_agent_dir / file_name
                    user_file = user_agent_dir / file_name

                    if project_file.exists():
                        project_file.unlink()
                        removed = True
                        self.console.print(f"[green]✓ Removed {project_file}[/green]")

                    if user_file.exists():
                        user_file.unlink()
                        removed = True
                        self.console.print(f"[green]✓ Removed {user_file}[/green]")

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

    def _view_agent_details_enhanced(self, agents: List[AgentConfig]) -> None:
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
