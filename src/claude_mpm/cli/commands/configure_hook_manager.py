"""Git hook installation and management for configure command.

This module handles installation, verification, and removal of git hooks
used by Claude MPM for automated workflows.

Extracted from configure.py (Phase 7/9) to reduce God Object complexity.
"""

from rich.console import Console
from rich.prompt import Confirm

from ...utils.console import console as default_console
from ..shared import CommandResult


class HookManager:
    """Manage git hook installation and verification.

    Handles:
    - Installing Claude Code integration hooks
    - Verifying hook installation status
    - Uninstalling hooks when requested
    """

    def __init__(self, console: Console = None):
        """Initialize hook manager.

        Args:
            console: Rich console for output (optional, defaults to shared console)
        """
        self.console = console or default_console
        self.logger = None  # Will be set from parent if needed

    def install_hooks(self, force: bool = False) -> CommandResult:
        """Install Claude MPM hooks for Claude Code integration.

        Extracted from ConfigureCommand._install_hooks() (CC=11)

        Args:
            force: Force reinstallation even if hooks exist

        Returns:
            CommandResult with installation status
        """
        try:
            from ...hooks.claude_hooks.installer import HookInstaller

            installer = HookInstaller()

            # Check Claude Code version compatibility first
            is_compatible, version_message = installer.is_version_compatible()
            self.console.print("[cyan]Checking Claude Code version...[/cyan]")
            self.console.print(version_message)

            if not is_compatible:
                self.console.print(
                    "\n[yellow]⚠ Hook monitoring is not available for your Claude Code version.[/yellow]"
                )
                self.console.print(
                    "The dashboard and other features will work without real-time monitoring."
                )
                self.console.print(
                    f"\n[dim]To enable monitoring, upgrade Claude Code to version {installer.MIN_CLAUDE_VERSION} or higher.[/dim]"
                )
                return CommandResult.success_result(
                    "Version incompatible with hook monitoring",
                    data={"compatible": False, "message": version_message},
                )

            # Check current status
            status = installer.get_status()
            if status["installed"] and not force:
                self.console.print("[yellow]Hooks are already installed.[/yellow]")
                self.console.print("Use --force to reinstall.")

                if not status["valid"]:
                    self.console.print("\n[red]However, there are issues:[/red]")
                    for issue in status["issues"]:
                        self.console.print(f"  - {issue}")

                return CommandResult.success_result(
                    "Hooks already installed", data=status
                )

            # Install hooks
            self.console.print("[cyan]Installing Claude MPM hooks...[/cyan]")
            success = installer.install_hooks(force=force)

            if success:
                self.console.print("[green]✓ Hooks installed successfully![/green]")
                self.console.print("\nYou can now use /mpm commands in Claude Code:")
                self.console.print("  /mpm         - Show help")
                self.console.print("  /mpm status  - Show claude-mpm status")

                # Verify installation
                is_valid, issues = installer.verify_hooks()
                if not is_valid:
                    self.console.print(
                        "\n[yellow]Warning: Installation completed but verification found issues:[/yellow]"
                    )
                    for issue in issues:
                        self.console.print(f"  - {issue}")

                return CommandResult.success_result("Hooks installed successfully")
            self.console.print("[red]✗ Hook installation failed[/red]")
            return CommandResult.error_result("Hook installation failed")

        except ImportError:
            self.console.print("[red]Error: HookInstaller module not found[/red]")
            self.console.print("Please ensure claude-mpm is properly installed.")
            return CommandResult.error_result("HookInstaller module not found")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Hook installation error: {e}", exc_info=True)
            return CommandResult.error_result(f"Hook installation failed: {e}")

    def verify_hooks(self) -> CommandResult:
        """Verify that Claude MPM hooks are properly installed.

        Extracted from ConfigureCommand._verify_hooks() (CC=10)

        Returns:
            CommandResult with verification status
        """
        try:
            from ...hooks.claude_hooks.installer import HookInstaller

            installer = HookInstaller()
            status = installer.get_status()

            self.console.print("[bold]Hook Installation Status[/bold]\n")

            # Show Claude Code version and compatibility
            if status.get("claude_version"):
                self.console.print(f"Claude Code Version: {status['claude_version']}")
                if status.get("version_compatible"):
                    self.console.print(
                        "[green]✓[/green] Version compatible with hook monitoring"
                    )
                else:
                    self.console.print(
                        f"[yellow]⚠[/yellow] {status.get('version_message', 'Version incompatible')}"
                    )
                    self.console.print()
            else:
                self.console.print(
                    "[yellow]Claude Code version could not be detected[/yellow]"
                )
            self.console.print()

            if status["installed"]:
                self.console.print(
                    f"[green]✓[/green] Hooks installed at: {status['hook_script']}"
                )
            else:
                self.console.print("[red]✗[/red] Hooks not installed")

            if status["settings_file"]:
                self.console.print(
                    f"[green]✓[/green] Settings file: {status['settings_file']}"
                )
            else:
                self.console.print("[red]✗[/red] Settings file not found")

            if status.get("configured_events"):
                self.console.print(
                    f"[green]✓[/green] Configured events: {', '.join(status['configured_events'])}"
                )
            else:
                self.console.print("[red]✗[/red] No events configured")

            if status["valid"]:
                self.console.print("\n[green]All checks passed![/green]")
            else:
                self.console.print("\n[red]Issues found:[/red]")
                for issue in status["issues"]:
                    self.console.print(f"  - {issue}")

            return CommandResult.success_result(
                "Hook verification complete", data=status
            )

        except ImportError:
            self.console.print("[red]Error: HookInstaller module not found[/red]")
            return CommandResult.error_result("HookInstaller module not found")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Hook verification error: {e}", exc_info=True)
            return CommandResult.error_result(f"Hook verification failed: {e}")

    def uninstall_hooks(self) -> CommandResult:
        """Uninstall Claude MPM hooks.

        Extracted from ConfigureCommand._uninstall_hooks() (CC=5)

        Returns:
            CommandResult with uninstallation status
        """
        try:
            from ...hooks.claude_hooks.installer import HookInstaller

            installer = HookInstaller()

            # Confirm uninstallation
            if not Confirm.ask(
                "[yellow]Are you sure you want to uninstall Claude MPM hooks?[/yellow]"
            ):
                return CommandResult.success_result("Uninstallation cancelled")

            self.console.print("[cyan]Uninstalling Claude MPM hooks...[/cyan]")
            success = installer.uninstall_hooks()

            if success:
                self.console.print("[green]✓ Hooks uninstalled successfully![/green]")
                return CommandResult.success_result("Hooks uninstalled successfully")
            self.console.print("[red]✗ Hook uninstallation failed[/red]")
            return CommandResult.error_result("Hook uninstallation failed")

        except ImportError:
            self.console.print("[red]Error: HookInstaller module not found[/red]")
            return CommandResult.error_result("HookInstaller module not found")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Hook uninstallation error: {e}", exc_info=True)
            return CommandResult.error_result(f"Hook uninstallation failed: {e}")
