"""Google Workspace MCP setup handler (delegates to OAuth + gworkspace-mcp)."""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404
from datetime import UTC
from pathlib import Path

from ....constants import SetupService
from ....shared import CommandResult
from .._shared import console
from ..mcp_config import AuthFailedError, _mcp_config_transaction


class GoogleWorkspaceMixin:
    """Mixin: gworkspace-mcp setup + .gitignore update + registry write."""

    def _add_gworkspace_to_gitignore(self) -> None:
        """Add .gworkspace-mcp/ to project .gitignore to prevent token commits."""
        gitignore_path = Path.cwd() / ".gitignore"
        gworkspace_entry = ".gworkspace-mcp/"

        # Check if .gitignore exists
        if not gitignore_path.exists():
            console.print(
                f"[dim]No .gitignore found at {gitignore_path}, skipping gitignore update[/dim]"
            )
            return

        try:
            # Read existing content
            with open(gitignore_path) as f:
                content = f.read()

            # Check if already present
            if gworkspace_entry in content:
                console.print("[dim].gworkspace-mcp/ already in .gitignore[/dim]")
                return

            # Append entry
            with open(gitignore_path, "a") as f:
                # Add newline if file doesn't end with one
                if content and not content.endswith("\n"):
                    f.write("\n")
                f.write(f"{gworkspace_entry}\n")

            console.print("[green]✓ Added .gworkspace-mcp/ to .gitignore[/green]")

        except Exception as e:
            console.print(f"[yellow]Warning: Could not update .gitignore: {e}[/yellow]")

    def _setup_google_workspace(self, args) -> CommandResult:
        """Set up Google Workspace MCP (delegates to OAuth setup)."""
        console.print(
            "This will configure OAuth authentication for Google Workspace.\n"
        )

        # Use centralized package installer
        console.print("[cyan]Checking gworkspace-mcp installation...[/cyan]")

        from .....services.package_installer import (
            InstallAction,
            PackageInstallerService,
            get_spec,
        )

        installer = PackageInstallerService()
        spec = get_spec(SetupService.GWORKSPACE_MCP)

        force = getattr(args, "force", False)
        upgrade = getattr(args, "upgrade", False)

        # Check if already installed and no flags set
        if installer.is_installed(spec) and not force and not upgrade:
            console.print("[green]✓ gworkspace-mcp already installed[/green]")
        else:
            console.print("[cyan]Detecting installation method...[/cyan]")
            success, message = installer.install(
                spec, InstallAction.INSTALL, force=force, upgrade=upgrade
            )
            if success:
                console.print(f"[green]✓ {message}[/green]\n")
            else:
                return CommandResult.error_result(message)

        # Validate existing tokens before skipping setup
        tokens_path = Path.home() / ".gworkspace-mcp" / "tokens.json"
        token_valid = False
        if tokens_path.exists() and tokens_path.stat().st_size > 10 and not force:
            try:
                token_data = json.loads(tokens_path.read_text())
                # Must contain at least one usable credential
                has_token = bool(
                    token_data.get("token")
                    or token_data.get("refresh_token")
                    or token_data.get("access_token")
                )
                if has_token:
                    # Check expiry if present
                    expiry_str = token_data.get("expiry") or token_data.get(
                        "expires_at"
                    )
                    if expiry_str:
                        from datetime import datetime

                        expiry = datetime.fromisoformat(str(expiry_str))
                        if expiry.tzinfo is None:
                            expiry = expiry.replace(tzinfo=UTC)
                        if expiry > datetime.now(UTC):
                            token_valid = True
                        elif token_data.get("refresh_token"):
                            # Expired but refresh_token can renew it
                            token_valid = True
                    else:
                        # No expiry field means we trust the token
                        token_valid = True
            except (json.JSONDecodeError, ValueError, OSError):
                token_valid = False

        if token_valid:
            console.print("[green]✓ Already authenticated (tokens validated)[/green]")
            exit_code = 0
        else:
            # Detect credentials from environment or .env files
            from ...oauth import _detect_google_credentials

            client_id, client_secret, source = _detect_google_credentials()

            if client_id and client_secret:
                console.print(f"[dim]Using credentials from {source}[/dim]")
                # Set environment variables for the setup command
                env = os.environ.copy()
                env["GOOGLE_OAUTH_CLIENT_ID"] = client_id
                env["GOOGLE_OAUTH_CLIENT_SECRET"] = client_secret

                console.print("[cyan]Running gworkspace-mcp setup...[/cyan]\n")
                try:
                    setup_result = subprocess.run(  # nosec B603 B607
                        ["gworkspace-mcp", "setup"],
                        check=False,
                        env=env,
                    )
                    exit_code = setup_result.returncode
                except Exception as e:
                    console.print(f"[red]Failed to run setup: {e}[/red]")
                    exit_code = 1
            else:
                console.print(
                    "[yellow]No OAuth credentials found.[/yellow]\n"
                    "[dim]Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET in:[/dim]\n"
                    "  - Environment variables, or\n"
                    "  - .env.local file, or\n"
                    "  - .env file\n"
                )
                return CommandResult.error_result(
                    "OAuth credentials required. See above for details."
                )

        # Only update .mcp.json if auth (gworkspace-mcp setup) actually
        # succeeded. Writing the config when auth fails (e.g. port conflict,
        # user cancelled OAuth) leaves a broken entry behind — see issue #493.
        if exit_code != 0:
            console.print(
                "[red]✗ gworkspace-mcp setup did not complete successfully; "
                ".mcp.json was not modified.[/red]"
            )
            return CommandResult(
                success=False,
                exit_code=exit_code,
                message="Google Workspace MCP setup",
            )

        # Configure MCP server in .mcp.json with rollback semantics so any
        # downstream failure (gitignore update, registry write) does not
        # leave behind a partially-written .mcp.json entry.
        from ...oauth import _ensure_mcp_configured

        try:
            with _mcp_config_transaction():
                _ensure_mcp_configured("gworkspace-mcp", Path.cwd())

                # Add .gworkspace-mcp/ to .gitignore if not present
                self._add_gworkspace_to_gitignore()
        except AuthFailedError as exc:
            return CommandResult.error_result(
                f"Google Workspace MCP setup failed after auth: {exc}"
            )

        # Register service in setup registry (only reached when exit_code == 0
        # since we return early above on auth failure).
        try:
            from claude_mpm.services.setup_registry import SetupRegistry

            registry = SetupRegistry()

            # Get CLI help for the tool
            cli_help = ""
            try:
                help_result = subprocess.run(  # nosec B603 B607
                    ["gworkspace-mcp", "--help"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if help_result.returncode == 0:
                    cli_help = help_result.stdout
            except Exception:  # nosec B110
                pass  # Help text is optional, failure is non-fatal

            # Register with known tools
            registry.add_service(
                name="gworkspace-mcp",
                service_type="mcp",
                version="0.1.2",  # TODO: Get from package
                tools=[
                    "search_gmail_messages",
                    "get_gmail_message_content",
                    "list_calendar_events",
                    "get_calendar_event",
                    "search_drive_files",
                    "get_drive_file_content",
                ],
                cli_help=cli_help,
                config_location="user",
            )
        except Exception as e:
            console.print(f"[dim]Warning: Could not update setup registry: {e}[/dim]")

        return CommandResult(
            success=True,
            exit_code=0,
            message="Google Workspace MCP setup",
        )
