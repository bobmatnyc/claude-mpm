"""
Uninstall command for claude-mpm CLI.

WHY: Users need a straightforward way to cleanly uninstall Claude MPM hooks
and other components without navigating through configuration menus.

DESIGN DECISIONS:
- Provide clear feedback about what is being removed
- Preserve user's other Claude settings
- Support both interactive confirmation and --yes flag
- Allow selective uninstallation of components
"""

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from ...services.hook_installer_service import HookInstallerService
from ...utils.console import console as default_console
from ..shared import BaseCommand, CommandResult


class UninstallCommand(BaseCommand):
    """Handle uninstallation of Claude MPM components."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize the uninstall command.

        Args:
            console: Optional Rich console for output.
        """
        super().__init__("uninstall")
        self.console = console or default_console
        self.hook_service = HookInstallerService()

    def run(self, args) -> CommandResult:
        """Execute the uninstall command.

        Args:
            args: Parsed command line arguments.

        Returns:
            CommandResult indicating success or failure.
        """
        try:
            # Check what component to uninstall
            if args.component == "hooks" or args.all:
                return self._uninstall_hooks(args)
            if args.component == "all":
                return self._uninstall_all(args)
            # Default to hooks if no component specified
            return self._uninstall_hooks(args)

        except Exception as e:
            self.console.print(f"[red]Error during uninstallation: {e}[/red]")
            return CommandResult.error_result(str(e))

    def _uninstall_hooks(self, args) -> CommandResult:
        """Uninstall Claude MPM hooks.

        Args:
            args: Parsed command line arguments.

        Returns:
            CommandResult indicating success or failure.
        """
        try:
            # Check if hooks are installed
            if not self.hook_service.is_hooks_configured():
                self.console.print(
                    "[yellow]No Claude MPM hooks are currently installed.[/yellow]"
                )
                return CommandResult.success_result("No hooks to uninstall")

            # Get hook status for display
            status = self.hook_service.get_hook_status()

            # Show what will be removed
            self.console.print(
                "\n[cyan]The following Claude MPM hooks will be removed:[/cyan]"
            )
            for hook_type, configured in status.get("hook_types", {}).items():
                if configured:
                    self.console.print(f"  • {hook_type}")

            # Confirm unless --yes flag is provided
            if not args.yes:
                if not Confirm.ask(
                    "\n[yellow]Do you want to proceed with uninstallation?[/yellow]"
                ):
                    self.console.print("[yellow]Uninstallation cancelled.[/yellow]")
                    return CommandResult.success_result(
                        "Uninstallation cancelled by user"
                    )

            # Perform uninstallation
            self.console.print("\n[cyan]Uninstalling Claude MPM hooks...[/cyan]")
            success = self.hook_service.uninstall_hooks()

            if success:
                self.console.print(
                    Panel(
                        "[green]✓ Claude MPM hooks have been successfully uninstalled.[/green]\n\n"
                        "Your other Claude settings have been preserved.",
                        title="Uninstallation Complete",
                        border_style="green",
                    )
                )
                return CommandResult.success_result("Hooks uninstalled successfully")
            self.console.print(
                "[red]Failed to uninstall hooks. Check the logs for details.[/red]"
            )
            return CommandResult.error_result("Failed to uninstall hooks")

        except Exception as e:
            return CommandResult.error_result(f"Error uninstalling hooks: {e}")

    def _uninstall_all(self, args) -> CommandResult:
        """Uninstall all Claude MPM components.

        Args:
            args: Parsed command line arguments.

        Returns:
            CommandResult indicating success or failure.
        """
        # For now, we only have hooks to uninstall
        # This method can be extended in the future for other components
        return self._uninstall_hooks(args)

        # Additional cleanup can be added here
        # For example: removing agent configurations, cache, etc.


def add_uninstall_parser(subparsers):
    """Add the uninstall subparser.

    Args:
        subparsers: The subparsers object from the main parser.

    Returns:
        The configured uninstall parser.
    """
    parser = subparsers.add_parser(
        "uninstall",
        help="Uninstall Claude MPM components",
        description="Remove Claude MPM hooks and other components while preserving other Claude settings",
    )

    # Component selection
    parser.add_argument(
        "component",
        nargs="?",
        choices=["hooks", "all"],
        default="hooks",
        help="Component to uninstall (default: hooks)",
    )

    # Confirmation bypass
    parser.add_argument(
        "-y", "--yes", action="store_true", help="Skip confirmation prompt"
    )

    # Force uninstall
    parser.add_argument(
        "--force", action="store_true", help="Force uninstallation even if errors occur"
    )

    # All components
    parser.add_argument(
        "--all", action="store_true", help="Uninstall all Claude MPM components"
    )

    return parser
