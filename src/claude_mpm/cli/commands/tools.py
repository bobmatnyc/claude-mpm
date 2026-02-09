"""
CLI command for claude-mpm tools framework.

WHY: Provides bulk operation capabilities for MCP services via CLI.
Agents can call these tools directly for batch processing.

USAGE:
    claude-mpm tools <service> <action> [options]

EXAMPLES:
    claude-mpm tools google gmail-export --query "from:john@example.com"
    claude-mpm tools slack messages-export --channel general --days 30
"""

import json
from typing import Any

from rich.console import Console

from claude_mpm.tools import get_service, list_services, load_services

from ..shared import BaseCommand, CommandResult

console = Console()


class ToolsCommand(BaseCommand):
    """Tools command for bulk MCP operations."""

    def __init__(self):
        super().__init__("tools")

    def validate_args(self, args) -> str | None:
        """Validate command arguments."""
        # Check if service is provided
        if not hasattr(args, "service") or not args.service:
            return "Service name required. Available services: " + ", ".join(
                list_services() or ["(none - services not yet implemented)"]
            )

        # Load services if not already loaded
        load_services()

        # Check if service exists
        service_class = get_service(args.service)
        if not service_class:
            available = list_services()
            if available:
                return f"Unknown service '{args.service}'. Available: {', '.join(available)}"
            return f"Unknown service '{args.service}'. No services are currently registered."

        # Check if action is provided
        if not hasattr(args, "action") or not args.action:
            service = service_class()
            actions = service.get_actions()
            return (
                f"Action required for {args.service}. Available: {', '.join(actions)}"
            )

        return None

    def run(self, args) -> CommandResult:
        """Execute the tools command."""
        # Load services
        load_services()

        # Get service module
        service_class = get_service(args.service)
        if not service_class:
            return CommandResult.error_result(f"Service {args.service} not found")

        try:
            # Instantiate service
            service = service_class()

            # Validate action
            service.validate_action(args.action)

            # Prepare kwargs from args
            kwargs = self._prepare_kwargs(args)

            # Execute action
            result = service.execute(args.action, **kwargs)

            # Output result
            self._output_result(result, args)

            # Return command result
            if result.success:
                return CommandResult.success_result(
                    f"Action {args.action} completed successfully"
                )
            return CommandResult.error_result(result.error or "Action failed")

        except ValueError as e:
            console.print(f"\n[red]Error:[/red] {e}\n", style="bold")
            return CommandResult.error_result(str(e))
        except Exception as e:
            console.print(f"\n[red]Error:[/red] {e}\n", style="bold")
            if args.debug:
                import traceback

                traceback.print_exc()
            return CommandResult.error_result(f"Unexpected error: {e}")

    def _prepare_kwargs(self, args) -> dict[str, Any]:
        """Prepare kwargs from parsed arguments.

        Extracts all non-standard arguments to pass to tool execute().
        """
        # Standard args to exclude
        exclude = {
            "command",
            "service",
            "action",
            "format",
            "output",
            "verbose",
            "debug",
            "quiet",
            "logging",
            "config",
            "project_dir",
            "no_hooks",
            "no_tickets",
            "func",
        }

        kwargs = {}
        for key, value in vars(args).items():
            if key not in exclude and value is not None:
                kwargs[key] = value

        return kwargs

    def _output_result(self, result, args) -> None:
        """Output result based on format option."""
        output_format = getattr(args, "format", "json")

        if output_format == "json":
            result_dict = result.to_dict()
            output = json.dumps(result_dict, indent=2)

            # Write to file or stdout
            output_file = getattr(args, "output", None)
            if output_file:
                with open(output_file, "w") as f:
                    f.write(output)
                console.print(f"[green]Output written to {output_file}[/green]")
            else:
                print(output)  # Use print() for clean JSON output

        elif output_format == "text":
            if result.success:
                console.print("[green]✓[/green] Success")
                if result.data:
                    console.print(result.data)
            else:
                console.print("[red]✗[/red] Failed")
                if result.error:
                    console.print(f"[red]{result.error}[/red]")


def manage_tools(args) -> int:
    """Main entry point for tools command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    command = ToolsCommand()
    result = command.execute(args)

    # Print error message if command failed
    if not result.success and result.message:
        console.print(f"\n[red]Error:[/red] {result.message}\n", style="bold")

    return result.exit_code
