"""Behavior file management for configure command.

This module handles operations on behavior configuration files including
identity and workflow configurations.

Extracted from configure.py (Phase 5/9) to reduce God Object complexity.
"""

import shutil
from pathlib import Path
from typing import Optional

from rich.box import ROUNDED
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from ...utils.console import console as default_console
from ..shared import CommandResult


class BehaviorManager:
    """Manage behavior configuration files.

    Handles:
    - Displaying available behavior files
    - Editing identity and workflow configs
    - Importing/exporting behavior files
    """

    def __init__(
        self,
        config_dir: Path,
        current_scope: str = "project",
        console: Optional[Console] = None,
    ):
        """Initialize behavior manager.

        Args:
            config_dir: Path to configuration directory
            current_scope: Current scope (project or user)
            console: Rich console for output (optional)
        """
        self.config_dir = config_dir
        self.current_scope = current_scope
        self.behaviors_dir = config_dir / "behaviors"
        self.console = console or default_console

        # Ensure behaviors directory exists
        self.behaviors_dir.mkdir(parents=True, exist_ok=True)

    def manage_behaviors(self) -> None:
        """Interactive behavior file management interface.

        Extracted from ConfigureCommand._manage_behaviors()
        """
        while True:
            self.console.clear()
            # Note: _display_header() is called from parent
            # We skip it here since it's a parent responsibility

            self.console.print("[bold]Behavior File Management[/bold]\n")

            # Display current behavior files
            self.display_behavior_files()

            # Show behavior menu
            self.console.print("\n[bold]Options:[/bold]")

            text_1 = Text("  ")
            text_1.append("[1]", style="bold blue")
            text_1.append(" Edit identity configuration")
            self.console.print(text_1)

            text_2 = Text("  ")
            text_2.append("[2]", style="bold blue")
            text_2.append(" Edit workflow configuration")
            self.console.print(text_2)

            text_3 = Text("  ")
            text_3.append("[3]", style="bold blue")
            text_3.append(" Import behavior file")
            self.console.print(text_3)

            text_4 = Text("  ")
            text_4.append("[4]", style="bold blue")
            text_4.append(" Export behavior file")
            self.console.print(text_4)

            text_b = Text("  ")
            text_b.append("[b]", style="bold blue")
            text_b.append(" Back to main menu")
            self.console.print(text_b)

            self.console.print()

            choice = Prompt.ask("[bold blue]Select an option[/bold blue]", default="b")

            if choice == "b":
                break
            if choice == "1":
                self.edit_identity_config()
            elif choice == "2":
                self.edit_workflow_config()
            elif choice == "3":
                self.import_behavior_file()
            elif choice == "4":
                self.export_behavior_file()
            else:
                self.console.print("[red]Invalid choice.[/red]")
                Prompt.ask("Press Enter to continue")

    def display_behavior_files(self) -> None:
        """Display current behavior files.

        Extracted from ConfigureCommand._display_behavior_files()
        """
        table = Table(title="Behavior Files", box=ROUNDED)
        table.add_column("File", style="bold blue", width=30)
        table.add_column("Size", style="dim", width=10)
        table.add_column("Modified", style="", width=20)

        identity_file = self.behaviors_dir / "identity.yaml"
        workflow_file = self.behaviors_dir / "workflow.yaml"

        for file_path in [identity_file, workflow_file]:
            if file_path.exists():
                stat = file_path.stat()
                size = f"{stat.st_size} bytes"
                modified = f"{stat.st_mtime:.0f}"  # Simplified timestamp
                table.add_row(file_path.name, size, modified)
            else:
                table.add_row(file_path.name, "[dim]Not found[/dim]", "-")

        self.console.print(table)

    def edit_identity_config(self) -> None:
        """Edit identity configuration.

        Extracted from ConfigureCommand._edit_identity_config()
        """
        self.console.print(
            "[yellow]Identity configuration editor - Coming soon![/yellow]"
        )
        Prompt.ask("Press Enter to continue")

    def edit_workflow_config(self) -> None:
        """Edit workflow configuration.

        Extracted from ConfigureCommand._edit_workflow_config()
        """
        self.console.print(
            "[yellow]Workflow configuration editor - Coming soon![/yellow]"
        )
        Prompt.ask("Press Enter to continue")

    def import_behavior_file(self) -> None:
        """Import a behavior file.

        Extracted from ConfigureCommand._import_behavior_file()
        """
        file_path = Prompt.ask("Enter path to behavior file to import")

        try:
            source = Path(file_path)
            if not source.exists():
                self.console.print(f"[red]File not found: {file_path}[/red]")
                return

            # Copy file
            target = self.behaviors_dir / source.name
            shutil.copy2(source, target)

            self.console.print(f"[green]Successfully imported {source.name}![/green]")

        except Exception as e:
            self.console.print(f"[red]Error importing file: {e}[/red]")

        Prompt.ask("Press Enter to continue")

    def export_behavior_file(self) -> None:
        """Export a behavior file.

        Extracted from ConfigureCommand._export_behavior_file()
        """
        self.console.print("[yellow]Behavior file export - Coming soon![/yellow]")
        Prompt.ask("Press Enter to continue")

    def run_behavior_management(self) -> CommandResult:
        """Run behavior management interface.

        Extracted from ConfigureCommand._run_behavior_management()

        Returns:
            CommandResult with status
        """
        try:
            self.manage_behaviors()
            return CommandResult.success_result("Behavior management completed")
        except KeyboardInterrupt:
            return CommandResult.success_result("Behavior management cancelled")
        except Exception as e:
            return CommandResult.error_result(f"Behavior management failed: {e}")
