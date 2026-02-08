"""
Slack setup commands for claude-mpm CLI.

WHY: Users need a simple way to set up Slack MPM integration.

DESIGN DECISIONS:
- Use BaseCommand for consistent CLI patterns
- Run the distributed setup-slack-app.sh script
- Provide clear feedback during setup
"""

import os
import subprocess  # nosec B404
import sys
from pathlib import Path

from rich.console import Console

from ..shared import BaseCommand, CommandResult

console = Console()


class SlackCommand(BaseCommand):
    """Slack setup command."""

    def __init__(self):
        super().__init__("slack")

    def validate_args(self, args) -> str | None:
        """Validate command arguments."""
        # If no slack_command specified, default to showing help
        if not hasattr(args, "slack_command") or not args.slack_command:
            args.slack_command = None
            return None

        valid_commands = ["setup"]
        if args.slack_command not in valid_commands:
            return f"Unknown slack command: {args.slack_command}. Valid commands: {', '.join(valid_commands)}"

        return None

    def run(self, args) -> CommandResult:
        """Execute the Slack command."""
        # If no subcommand, show help
        if not hasattr(args, "slack_command") or not args.slack_command:
            self._show_help()
            return CommandResult.success_result("Help displayed")

        if args.slack_command == "setup":
            return self._run_setup(args)

        return CommandResult.error_result(
            f"Unknown slack command: {args.slack_command}"
        )

    def _show_help(self) -> None:
        """Display Slack command help."""
        help_text = """
[bold]Slack Commands:[/bold]
  slack setup    Set up Slack MPM integration

[bold]Example:[/bold]
  claude-mpm slack setup
"""
        console.print(help_text)

    def _run_setup(self, args) -> CommandResult:
        """Run the Slack setup script."""
        try:
            # Find the setup script in the installed package
            import claude_mpm

            package_dir = Path(claude_mpm.__file__).parent
            script_path = package_dir / "scripts" / "setup" / "setup-slack-app.sh"

            if not script_path.exists():
                return CommandResult.error_result(
                    f"Setup script not found at: {script_path}\n"
                    "This may be due to an older version. "
                    "Try: uv tool upgrade claude-mpm"
                )

            # Make sure script is executable
            script_path.chmod(0o755)

            console.print("[cyan]Running Slack setup wizard...[/cyan]\n")

            # Run the script
            result = subprocess.run(
                ["bash", str(script_path)],
                check=False,
                env=os.environ.copy(),
            )  # nosec B603 B607

            if result.returncode == 0:
                console.print("\n[green]✓ Slack setup complete![/green]")
                return CommandResult.success_result("Slack setup completed")
            else:
                return CommandResult.error_result(
                    f"Setup script exited with code {result.returncode}"
                )

        except KeyboardInterrupt:
            console.print("\n[yellow]Setup cancelled by user[/yellow]")
            return CommandResult.error_result("Setup cancelled")
        except Exception as e:
            return CommandResult.error_result(f"Error running setup: {e}")


def manage_slack(args) -> int:
    """Main entry point for Slack commands.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    command = SlackCommand()
    result = command.execute(args)
    return result.exit_code
