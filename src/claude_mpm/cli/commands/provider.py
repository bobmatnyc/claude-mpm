"""API provider management command for claude-mpm CLI.

WHY: Users need to switch between Bedrock and Anthropic backends from the CLI.
This provides a simple interface for viewing and changing the API provider
configuration.

DESIGN DECISION: Uses BaseCommand pattern for consistency with other CLI commands.
Configuration changes are saved to .claude-mpm/configuration.yaml and take effect
on the next claude-mpm session.
"""

import argparse
import json
import os
import subprocess
from pathlib import Path

from rich.panel import Panel
from rich.table import Table

from ...config.api_provider import APIBackend, APIProviderConfig
from ...utils.console import console
from ..shared import BaseCommand, CommandResult


class ProviderCommand(BaseCommand):
    """API provider management command."""

    def __init__(self) -> None:
        super().__init__("provider")

    def validate_args(self, args: argparse.Namespace) -> str | None:
        """Validate command arguments."""
        # provider_command can be None (show status), bedrock, anthropic, anthropic-login, or status
        valid_commands = [None, "bedrock", "anthropic", "anthropic-login", "status"]
        provider_command = getattr(args, "provider_command", None)
        if provider_command not in valid_commands:
            return f"Unknown provider command: {provider_command}. Valid commands: bedrock, anthropic, anthropic-login, status"
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
        if provider_command == "anthropic-login":
            return self._switch_to_anthropic_login(args)
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

            # Show auth method details
            if "ANTHROPIC_API_KEY" in os.environ:  # pragma: allowlist secret
                console.print("         Auth: API key")
            else:
                auth_info = ProviderCommand._get_auth_status()
                if auth_info.get("authenticated"):
                    auth_line = "         Auth: Claude.ai OAuth"
                    if auth_info.get("email"):
                        auth_line += f" ({auth_info['email']})"
                    console.print(auth_line)
                    if auth_info.get("subscription"):
                        console.print(
                            f"         Subscription: {auth_info['subscription']}"
                        )
                else:
                    console.print(
                        "[dim]Note:[/dim] No API key set — using Claude.ai login or set ANTHROPIC_API_KEY"  # pragma: allowlist secret
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

        # Check for API key (optional - Claude Code also supports OAuth login)
        if "ANTHROPIC_API_KEY" not in os.environ:  # pragma: allowlist secret
            console.print(
                "\n[dim]Note:[/dim] ANTHROPIC_API_KEY not found in environment."  # pragma: allowlist secret
            )
            console.print("       To authenticate, choose one method:")
            console.print("")
            console.print(
                "         1. [green]Browser login[/green] (recommended for Pro/Max subscribers):"
            )
            console.print("            Run: [bold]claude auth login[/bold]")
            console.print(
                "            Or use [bold]/login[/bold] inside your next claude-mpm session"
            )
            console.print("")
            console.print("         2. [yellow]API key[/yellow]:")
            console.print(
                "            export ANTHROPIC_API_KEY=sk-ant-..."  # pragma: allowlist secret
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

    def _switch_to_anthropic_login(self, args: argparse.Namespace) -> CommandResult:
        """Switch to Anthropic backend, clear all API keys, and trigger OAuth login.

        WHY: Users may have stale ANTHROPIC_API_KEY env vars or config remnants
        that interfere with the Claude.ai OAuth login path. This mode aggressively
        clears everything and ensures the OAuth flow is used.
        """
        config_path = self._get_config_path(args)
        config = APIProviderConfig.load(config_path)

        # Step a) Set backend to anthropic
        config.backend = APIBackend.ANTHROPIC
        # Clear any stored api_key or model override
        config.anthropic.model = ""

        # Save configuration
        try:
            config.save(config_path)
        except Exception as e:
            return CommandResult.error_result(f"Failed to save configuration: {e}")

        # Also strip api_key from the api_provider section in the config YAML
        self._remove_api_key_from_config(config_path)

        # Step b) Force-clear ANTHROPIC_API_KEY from current process env
        os.environ.pop("ANTHROPIC_API_KEY", None)  # pragma: allowlist secret

        # Step b) Remove ANTHROPIC_API_KEY from .env.local if present
        self._remove_key_from_env_local("ANTHROPIC_API_KEY")  # pragma: allowlist secret

        # Step c) Unset Bedrock env vars
        for var in [
            "CLAUDE_CODE_USE_BEDROCK",
            "ANTHROPIC_BEDROCK_BASE_URL",
            "ANTHROPIC_MODEL",
        ]:
            os.environ.pop(var, None)

        console.print("\n[green]API keys cleared[/green]")

        # Step d) Trigger `claude auth login` interactively
        console.print("\nLaunching Claude.ai OAuth login...\n")
        try:
            login_result = subprocess.run(
                ["claude", "auth", "login"],
                check=False,
            )
            login_ok = login_result.returncode == 0
        except FileNotFoundError:
            console.print(
                "[red]Error:[/red] 'claude' binary not found. "
                "Install Claude Code first: npm install -g @anthropic-ai/claude-code"
            )
            return CommandResult.error_result("claude binary not found")
        except Exception as e:
            console.print(f"[red]Error:[/red] Failed to run 'claude auth login': {e}")
            return CommandResult.error_result(f"Login failed: {e}")

        # Step e) Verify auth succeeded
        auth_info = self._get_auth_status()

        if login_ok and auth_info.get("authenticated"):
            console.print("\n[green]Authenticated via Claude.ai[/green]")
            if auth_info.get("email"):
                console.print(f"  Email: {auth_info['email']}")
            if auth_info.get("subscription"):
                console.print(f"  Subscription: {auth_info['subscription']}")
            console.print(
                "\n  You're ready to use claude-mpm with your Claude.ai subscription."
            )
            return CommandResult.success_result(
                "Switched to Anthropic backend with OAuth login",
                data={
                    "backend": "anthropic",
                    "auth_method": "oauth",
                    **auth_info,
                },
            )
        console.print("\n[red]Authentication failed[/red]")
        console.print("  Run 'claude auth login' manually to try again.")
        return CommandResult.error_result("Authentication failed")

    @staticmethod
    def _remove_api_key_from_config(config_path: Path) -> None:
        """Remove any api_key field from the api_provider section in the YAML config."""
        if not config_path.exists():
            return
        try:
            import yaml

            with open(config_path) as f:
                data = yaml.safe_load(f) or {}

            api_provider = data.get("api_provider", {})
            changed = False
            if "api_key" in api_provider:
                del api_provider["api_key"]
                changed = True
            anthropic_section = api_provider.get("anthropic", {})
            if isinstance(anthropic_section, dict) and "api_key" in anthropic_section:
                del anthropic_section["api_key"]
                changed = True

            if changed:
                with open(config_path, "w") as f:
                    yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        except Exception:
            pass  # Best-effort cleanup

    @staticmethod
    def _remove_key_from_env_local(key: str) -> None:
        """Remove a key from .env.local if the file exists."""
        env_local = Path.cwd() / ".env.local"
        if not env_local.exists():
            return
        try:
            lines = env_local.read_text().splitlines(keepends=True)
            filtered = [
                line
                for line in lines
                if not line.strip().startswith(f"{key}=")
                and not line.strip().startswith(f"export {key}=")
            ]
            if len(filtered) != len(lines):
                env_local.write_text("".join(filtered))
        except Exception:
            pass  # Best-effort cleanup

    @staticmethod
    def _get_auth_status() -> dict:
        """Run 'claude auth status' and parse the result.

        Returns:
            Dictionary with keys: authenticated, email, subscription (all optional).
        """
        info: dict = {"authenticated": False}
        try:
            result = subprocess.run(
                ["claude", "auth", "status"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                stdout = result.stdout.lower()
                if "logged in" in stdout:
                    info["authenticated"] = True

                # Try to parse JSON output if available
                try:
                    data = json.loads(result.stdout)
                    info["authenticated"] = True
                    if "email" in data:
                        info["email"] = data["email"]
                    if "subscription" in data:
                        info["subscription"] = data["subscription"]
                except (json.JSONDecodeError, ValueError):
                    # Parse text output for email
                    for line in result.stdout.splitlines():
                        line_stripped = line.strip()
                        if "@" in line_stripped and "email" not in info:
                            # Extract what looks like an email
                            for word in line_stripped.split():
                                if "@" in word and "." in word:
                                    info["email"] = word.strip("()")
                                    break
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return info


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
