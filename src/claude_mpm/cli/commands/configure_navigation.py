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

import questionary
from questionary import Style
from rich.box import ROUNDED
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text


class ConfigNavigation:
    """Handle scope switching and navigation for configure command.

    This class manages:
    - Header display with version and scope information
    - Main menu rendering with options
    - Scope switching (project ↔ user)
    - Claude MPM launch integration
    """

    # Questionary style matching Rich cyan theme
    QUESTIONARY_STYLE = Style(
        [
            ("selected", "fg:cyan bold"),
            ("pointer", "fg:cyan bold"),
            ("highlighted", "fg:cyan"),
            ("question", "fg:cyan bold"),
        ]
    )

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
        """Show the main menu and get user choice with arrow-key navigation.

        Displays main configuration menu with options:
        - Agent Management
        - Skills Management
        - Template Editing
        - Behavior Files
        - Startup Configuration
        - Switch Scope
        - Version Info
        - Save & Launch
        - Quit

        Returns:
            User's menu choice mapped to original key (1-7, l, q) for
            backward compatibility with existing code
        """
        try:
            choice = questionary.select(
                "Main Menu:",
                choices=[
                    "Agent Management",
                    "Skills Management",
                    "Template Editing",
                    "Behavior Files",
                    "Startup Configuration",
                    f"Switch Scope (Current: {self.current_scope})",
                    "Version Info",
                    questionary.Separator(),
                    "Save & Launch Claude MPM",
                    "Quit",
                ],
                style=self.QUESTIONARY_STYLE,
            ).ask()

            if choice is None:
                return "q"

            # Map natural language choices back to original key-based system
            # for backward compatibility
            choice_map = {
                "Agent Management": "1",
                "Skills Management": "2",
                "Template Editing": "3",
                "Behavior Files": "4",
                "Startup Configuration": "5",
                f"Switch Scope (Current: {self.current_scope})": "6",
                "Version Info": "7",
                "Save & Launch Claude MPM": "l",
                "Quit": "q",
            }

            return choice_map.get(choice, "q")

        except KeyboardInterrupt:
            return "q"

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
