"""API provider management command for claude-mpm CLI.

WHY: Users need to switch between Bedrock and Anthropic backends from the CLI.
This provides a simple interface for viewing and changing the API provider
configuration.

DESIGN DECISION: Uses BaseCommand pattern for consistency with other CLI commands.
Configuration changes are saved to .claude-mpm/configuration.yaml and take effect
on the next claude-mpm session.
"""

import argparse
import os
from pathlib import Path
from typing import Optional

from rich.panel import Panel
from rich.table import Table

from ...config.api_provider import APIBackend, APIProviderConfig
from ...utils.console import console
from ..shared import BaseCommand, CommandResult


class ProviderCommand(BaseCommand):
    """API provider management command."""

    def __init__(self) -> None:
        super().__init__("provider")

    def validate_args(self, args: argparse.Namespace) -> Optional[str]:
        """Validate command arguments."""
        # provider_command can be None (show status), bedrock, anthropic, or status
        valid_commands = [None, "bedrock", "anthropic", "status"]
        provider_command = getattr(args, "provider_command", None)
        if provider_command not in valid_commands:
            return f"Unknown provider command: {provider_command}. Valid commands: bedrock, anthropic, status"
        return None

    def run(self, args: argparse.Namespace) -> CommandResult:
        """Execute the provider command."""
        provider_command = getattr(args, "provider_command", None)

        if provider_command is None or provider_command == "status":
            return self._show_status(args)
        if provider_command == "bedrock":
            return self._switch_to_bedrock(args)
        if provider_command == "anthropic":
            return self._switch_to_anthropic(args)
        # Unknown command
        return CommandResult.error_result(
            f"Unknown provider command: {provider_command}"
        )

    def _get_config_path(self, args: argparse.Namespace) -> Path:
        """Get the configuration file path."""
        if hasattr(args, "config") and args.config:
            return Path(args.config)
        return self.working_dir / ".claude-mpm" / "configuration.yaml"

    def _show_status(self, args: argparse.Namespace) -> CommandResult:
        """Show current API provider configuration."""
        config_path = self._get_config_path(args)
        config = APIProviderConfig.load(config_path)

        # Build status table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="white")

        # Current backend
        backend_style = "green" if config.backend == APIBackend.BEDROCK else "yellow"
        table.add_row(
            "Backend", f"[{backend_style}]{config.backend.value}[/{backend_style}]"
        )

        # Bedrock settings
        table.add_row("Bedrock Region", config.bedrock.region)
        table.add_row("Bedrock Model", config.bedrock.model)

        # Anthropic settings
        table.add_row("Anthropic Model", config.anthropic.model)

        # Environment status
        bedrock_env = os.environ.get("CLAUDE_CODE_USE_BEDROCK", "not set")
        api_key_status = (
            "set" if "ANTHROPIC_API_KEY" in os.environ else "not set"
        )  # pragma: allowlist secret
        table.add_row("", "")  # Separator
        table.add_row("ENV: CLAUDE_CODE_USE_BEDROCK", bedrock_env)
        table.add_row(
            "ENV: ANTHROPIC_API_KEY", api_key_status
        )  # pragma: allowlist secret

        # Config file location
        config_exists = "exists" if config_path.exists() else "not found"
        table.add_row("Config File", f"{config_path} ({config_exists})")

        # Display panel
        panel = Panel(
            table,
            title="API Provider Configuration",
            border_style="blue",
        )
        console.print(panel)

        # Show active configuration message
        if config.backend == APIBackend.BEDROCK:
            console.print(
                f"\n[green]Active:[/green] Using AWS Bedrock in {config.bedrock.region}"
            )
            console.print(f"         Model: {config.bedrock.model}")
        else:
            console.print("\n[yellow]Active:[/yellow] Using Anthropic API directly")
            console.print(f"         Model: {config.anthropic.model}")
            if "ANTHROPIC_API_KEY" not in os.environ:  # pragma: allowlist secret
                console.print(
                    "[red]Warning:[/red] ANTHROPIC_API_KEY not set in environment"  # pragma: allowlist secret
                )

        return CommandResult.success_result(
            "Provider status displayed",
            data=config.to_dict(),
        )

    def _switch_to_bedrock(self, args: argparse.Namespace) -> CommandResult:
        """Switch to Bedrock backend."""
        config_path = self._get_config_path(args)
        config = APIProviderConfig.load(config_path)

        # Update backend
        config.backend = APIBackend.BEDROCK

        # Update region if specified
        if hasattr(args, "region") and args.region:
            config.bedrock.region = args.region

        # Update model if specified
        if hasattr(args, "model") and args.model:
            config.bedrock.model = args.model

        # Save configuration
        try:
            config.save(config_path)
        except Exception as e:
            return CommandResult.error_result(f"Failed to save configuration: {e}")

        # Display success message
        console.print("\n[green]Switched to AWS Bedrock backend[/green]")
        console.print(f"  Region: {config.bedrock.region}")
        console.print(f"  Model:  {config.bedrock.model}")
        console.print(f"\nConfiguration saved to: {config_path}")
        console.print(
            "\n[dim]Changes will take effect on next claude-mpm session.[/dim]"
        )

        return CommandResult.success_result(
            "Switched to Bedrock backend",
            data={
                "backend": "bedrock",
                "region": config.bedrock.region,
                "model": config.bedrock.model,
            },
        )

    def _switch_to_anthropic(self, args: argparse.Namespace) -> CommandResult:
        """Switch to Anthropic backend."""
        config_path = self._get_config_path(args)
        config = APIProviderConfig.load(config_path)

        # Update backend
        config.backend = APIBackend.ANTHROPIC

        # Update model if specified
        if hasattr(args, "model") and args.model:
            config.anthropic.model = args.model

        # Save configuration
        try:
            config.save(config_path)
        except Exception as e:
            return CommandResult.error_result(f"Failed to save configuration: {e}")

        # Display success message
        console.print("\n[yellow]Switched to Anthropic API backend[/yellow]")
        console.print(f"  Model: {config.anthropic.model}")
        console.print(f"\nConfiguration saved to: {config_path}")

        # Check for API key
        if "ANTHROPIC_API_KEY" not in os.environ:  # pragma: allowlist secret
            console.print(
                "\n[red]Warning:[/red] ANTHROPIC_API_KEY not found in environment."  # pragma: allowlist secret
            )
            console.print(
                "         Please set this environment variable before starting a session."
            )

        console.print(
            "\n[dim]Changes will take effect on next claude-mpm session.[/dim]"
        )

        return CommandResult.success_result(
            "Switched to Anthropic backend",
            data={
                "backend": "anthropic",
                "model": config.anthropic.model,
            },
        )


def manage_provider(args: argparse.Namespace) -> int:
    """Main entry point for provider management command.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    command = ProviderCommand()
    result = command.execute(args)
    return result.exit_code
