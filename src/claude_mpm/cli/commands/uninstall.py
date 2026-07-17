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

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from ...services.hook_installer_service import HookInstallerService
from ...utils.console import console as default_console
from ..shared import BaseCommand, CommandResult


class UninstallCommand(BaseCommand):
    """Handle uninstallation of Claude MPM components."""

    def __init__(self, console: Console | None = None):
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
            if args.component == "all" or args.all:
                return self._uninstall_all(args)
            if args.component == "global":
                return self._uninstall_global(args)
            if args.component == "hooks":
                return self._uninstall_hooks(args)
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

    def _uninstall_global(self, args) -> CommandResult:
        """Remove MPM-owned artifacts from the global ``~/.claude/`` directory.

        WHAT: Runs a dry-run pass to build a preview, prints it, and — unless
        ``--dry-run`` was given — confirms (respecting ``--yes``) before running
        the real cleanup of agent templates, output-styles, the statusline
        script, and MPM-owned ``settings.json`` keys.

        WHY: claude-mpm historically wrote these into the shared, cross-project
        ``~/.claude/`` namespace, breaking other harnesses (issue #924); users
        need a safe, previewable removal path that never touches non-MPM files.

        Args:
            args: Parsed command line arguments. Honours ``--dry-run`` (preview
                only) and ``--yes`` (skip the confirmation prompt).

        Returns:
            CommandResult indicating success or failure.
        """
        from .uninstall_global import run_global_cleanup

        dry_run = bool(getattr(args, "dry_run", False))

        # First pass is always a dry run so we can show a preview and confirm.
        preview = run_global_cleanup(dry_run=True)

        if preview.total == 0:
            self.console.print(
                "[green]No global claude-mpm artifacts found in ~/.claude/.[/green]"
            )
            return CommandResult.success_result("Nothing to clean")

        verb = "Would remove" if dry_run else "Will remove"
        self.console.print(
            f"\n[cyan]{verb} the following global claude-mpm artifacts:[/cyan]"
        )
        for path in preview.removed_files:
            self.console.print(f"  • {path}")
        for key in preview.settings_keys:
            self.console.print(f"  • ~/.claude/settings.json → {key}")

        if dry_run:
            self.console.print("\n[yellow]Dry run — no changes were made.[/yellow]")
            return CommandResult.success_result(
                f"Dry run: {preview.total} artifact(s) would be removed"
            )

        if not getattr(args, "yes", False):
            if not Confirm.ask(
                "\n[yellow]Remove these global claude-mpm artifacts?[/yellow]"
            ):
                self.console.print("[yellow]Uninstallation cancelled.[/yellow]")
                return CommandResult.success_result("Uninstallation cancelled by user")

        summary = run_global_cleanup(dry_run=False)
        self.console.print(
            Panel(
                f"[green]✓ Removed {len(summary.removed_files)} file(s) and "
                f"{len(summary.settings_keys)} settings key(s) from ~/.claude/.[/green]\n\n"
                "Other Claude settings and non-MPM files were preserved.",
                title="Global Cleanup Complete",
                border_style="green",
            )
        )
        return CommandResult.success_result(
            f"Removed {summary.total} global artifact(s)"
        )

    def _uninstall_all(self, args) -> CommandResult:
        """Uninstall all Claude MPM components (hooks + global artifacts).

        Args:
            args: Parsed command line arguments.

        Returns:
            CommandResult indicating success or failure.
        """
        hooks_result = self._uninstall_hooks(args)
        global_result = self._uninstall_global(args)

        if not hooks_result.success:
            return hooks_result
        if not global_result.success:
            return global_result
        return CommandResult.success_result("All Claude MPM components uninstalled")


def add_uninstall_parser(subparsers):
    """Add the uninstall subparser.

    WHAT: Registers the ``uninstall`` subcommand with its component argument
    (``hooks`` / ``global`` / ``all``) and the ``--yes``, ``--force``, ``--all``,
    and ``--dry-run`` options.

    WHY: Centralising argument registration keeps the CLI surface for uninstall
    in one place and lets ``--dry-run`` preview the global cleanup (issue #924).

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
        choices=["hooks", "global", "all"],
        default="hooks",
        help=(
            "Component to uninstall: 'hooks' (default), 'global' (MPM-owned "
            "artifacts in ~/.claude/: agents, output-styles, statusline.sh, "
            "settings keys), or 'all'"
        ),
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

    # Preview mode (applies to the 'global' component)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be removed without making changes",
    )

    return parser
