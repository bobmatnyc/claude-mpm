"""Navigation and scope management for configure command.

WHY: Separate navigation, scope switching, and menu display logic from main
configure command to improve modularity. This handles the TUI interface
elements that guide users through the configuration system.

DESIGN DECISIONS:
- Display header with version and scope info
- Main menu with numbered options and descriptions
- Scope switching between project and user configurations
- Launch integration to transition to Claude MPM run
"""

import os
from pathlib import Path

from rich.box import ROUNDED
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text


class ConfigNavigation:
    """Handle scope switching and navigation for configure command.

    This class manages:
    - Header display with version and scope information
    - Main menu rendering with options
    - Scope switching (project ↔ user)
    - Claude MPM launch integration
    """

    def __init__(self, console: Console, project_dir: Path):
        """Initialize navigation handler.

        Args:
            console: Rich console for output
            project_dir: Current project directory
        """
        self.console = console
        self.project_dir = project_dir
        self.current_scope = "project"

    def display_header(self) -> None:
        """Display the TUI header with version and scope information.

        Shows:
        - Claude MPM branding and version
        - Current configuration scope (project/user)
        - Working directory
        """
        self.console.clear()

        # Get version for display
        from claude_mpm import __version__

        # Create header panel
        header_text = Text()
        header_text.append("Claude MPM ", style="bold blue")
        header_text.append("Configuration Interface", style="bold")
        header_text.append(f"\nv{__version__}", style="dim blue")

        scope_text = Text(f"Scope: {self.current_scope.upper()}", style="bold blue")
        dir_text = Text(f"Directory: {self.project_dir}", style="dim")

        header_content = Columns([header_text], align="center")
        subtitle_content = f"{scope_text} | {dir_text}"

        header_panel = Panel(
            header_content,
            subtitle=subtitle_content,
            box=ROUNDED,
            style="blue",
            padding=(1, 2),
        )

        self.console.print(header_panel)
        self.console.print()

    def show_main_menu(self) -> str:
        """Show the main menu and get user choice.

        Displays main configuration menu with options:
        1. Agent Management
        2. Skills Management
        3. Template Editing
        4. Behavior Files
        5. Startup Configuration
        6. Switch Scope
        7. Version Info
        l. Save & Launch
        q. Quit

        Returns:
            User's menu choice (lowercase, stripped)
        """
        menu_items = [
            ("1", "Agent Management", "Enable/disable agents and customize settings"),
            ("2", "Skills Management", "Configure skills for agents"),
            ("3", "Template Editing", "Edit agent JSON templates"),
            ("4", "Behavior Files", "Manage identity and workflow configurations"),
            (
                "5",
                "Startup Configuration",
                "Configure MCP services and agents to start",
            ),
            ("6", "Switch Scope", f"Current: {self.current_scope}"),
            ("7", "Version Info", "Display MPM and Claude versions"),
            ("l", "Save & Launch", "Save all changes and start Claude MPM"),
            ("q", "Quit", "Exit without launching"),
        ]

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Key", style="bold blue", width=4)  # Bolder shortcuts
        table.add_column("Option", style="bold", width=24)  # Wider for titles
        table.add_column("Description", style="")  # Use default terminal color

        for key, option, desc in menu_items:
            table.add_row(f"\\[{key}]", option, desc)

        menu_panel = Panel(
            table, title="[bold]Main Menu[/bold]", box=ROUNDED, style="green"
        )

        self.console.print(menu_panel)
        self.console.print()

        choice = Prompt.ask("[bold blue]Select an option[/bold blue]", default="q")
        # Strip whitespace to handle leading/trailing spaces
        return choice.strip().lower()

    def switch_scope(self) -> None:
        """Switch between project and user scope.

        Toggles current_scope between:
        - "project": Project-level configuration (.claude-mpm in project dir)
        - "user": User-level configuration (.claude-mpm in home dir)
        """
        self.current_scope = "user" if self.current_scope == "project" else "project"
        self.console.print(f"[green]Switched to {self.current_scope} scope[/green]")
        Prompt.ask("Press Enter to continue")

    def launch_claude_mpm(self) -> None:
        """Launch Claude MPM run command, replacing current process.

        Uses os.execvp to replace the configure process with 'claude-mpm run',
        providing a seamless transition from configuration to runtime.

        If launch fails, displays instructions for manual launch.
        """
        self.console.print("\n[bold cyan]═══ Launching Claude MPM ═══[/bold cyan]\n")

        try:
            # Use execvp to replace the current process with claude-mpm run
            # This ensures a clean transition from configurator to Claude MPM
            os.execvp("claude-mpm", ["claude-mpm", "run"])
        except Exception as e:
            self.console.print(
                f"[yellow]⚠ Could not launch Claude MPM automatically: {e}[/yellow]"
            )
            self.console.print(
                "[cyan]→ Please run 'claude-mpm run' manually to start.[/cyan]"
            )
            Prompt.ask("\nPress Enter to exit")
