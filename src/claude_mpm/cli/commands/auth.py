"""
Auth management commands for claude-mpm CLI.

WHY: The gworkspace-mcp binary stores OAuth tokens in .gworkspace-mcp/tokens.json
at the project level. The existing 'claude-mpm oauth refresh' uses a different
encrypted token store and does not refresh these tokens. This module provides
direct token refresh against the Google OAuth2 token endpoint using only stdlib.

DESIGN DECISIONS:
- Use only stdlib (urllib.request) for HTTP to avoid adding dependencies
- Load credentials from .env.local first, then os.environ
- Refresh token is read from the tokens.json file stored by gworkspace-mcp
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from ..shared import BaseCommand, CommandResult

console = Console()

# Default service name matching the gworkspace-mcp token store key
_DEFAULT_SERVICE = "gworkspace-mcp"
_TOKENS_FILE = Path(".gworkspace-mcp") / "tokens.json"
_ENV_LOCAL = Path(".env.local")
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"  # nosec B105


class AuthCommand(BaseCommand):
    """Command handler for auth subcommands."""

    def __init__(self):
        super().__init__("auth")

    def run(self, args) -> CommandResult:
        """Dispatch to the appropriate auth subcommand."""
        auth_command = getattr(args, "auth_command", None)

        if auth_command == "refresh":
            return self._refresh_tokens(args)
        if auth_command == "status":
            return self._status(args)

        self._show_help()
        return CommandResult.success_result("Help displayed")

    def _show_help(self) -> None:
        console.print("\n[bold]claude-mpm auth[/bold] - Manage authentication tokens\n")
        console.print("  [cyan]refresh[/cyan]  Refresh tokens without browser")
        console.print("  [cyan]status[/cyan]   Show token expiry status\n")

    # ------------------------------------------------------------------
    # Subcommand: refresh
    # ------------------------------------------------------------------

    def _refresh_tokens(self, args) -> CommandResult:
        """Refresh gworkspace-mcp tokens from .gworkspace-mcp/tokens.json."""
        refresh_all = getattr(args, "all", False)
        service = getattr(args, "service", _DEFAULT_SERVICE)
        tokens_path = self.working_dir / _TOKENS_FILE

        client_id, client_secret = _load_credentials(self.working_dir)
        if not client_id or not client_secret:
            return CommandResult.error_result(
                "Missing GOOGLE_OAUTH_CLIENT_ID or GOOGLE_OAUTH_CLIENT_SECRET. "
                "Set them in .env.local or as environment variables."
            )

        if refresh_all:
            return self._refresh_all_services(tokens_path, client_id, client_secret)

        return _refresh_gworkspace_token(tokens_path, service, client_id, client_secret)

    def _refresh_all_services(
        self, tokens_path: Path, client_id: str, client_secret: str
    ) -> CommandResult:
        """Refresh tokens for every service in the tokens file."""
        if not tokens_path.exists():
            return CommandResult.error_result(f"Token file not found: {tokens_path}")

        try:
            tokens_data = json.loads(tokens_path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            return CommandResult.error_result(f"Cannot read token file: {exc}")

        errors = []
        for service in list(tokens_data.keys()):
            result = _refresh_gworkspace_token(
                tokens_path, service, client_id, client_secret
            )
            if not result.success:
                errors.append(f"{service}: {result.message}")

        if errors:
            return CommandResult.error_result(
                "Some services failed to refresh:\n" + "\n".join(errors)
            )
        return CommandResult.success_result("All services refreshed successfully")

    # ------------------------------------------------------------------
    # Subcommand: status
    # ------------------------------------------------------------------

    def _status(self, args) -> CommandResult:
        """Show token expiry status for all services in tokens.json."""
        tokens_path = self.working_dir / _TOKENS_FILE

        if not tokens_path.exists():
            console.print(f"[yellow]Token file not found: {tokens_path}[/yellow]")
            return CommandResult.success_result("No token file found")

        try:
            tokens_data = json.loads(tokens_path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            return CommandResult.error_result(f"Cannot read token file: {exc}")

        table = Table(title="Auth Token Status")
        table.add_column("Service", style="cyan")
        table.add_column("Expires At", style="white")
        table.add_column("Status", style="white")

        now = datetime.now(UTC)
        for service, entry in tokens_data.items():
            token = entry.get("token", {})
            expires_at_str = token.get("expires_at", "")
            if expires_at_str:
                try:
                    expires_at = datetime.fromisoformat(
                        expires_at_str.replace("Z", "+00:00")
                    )
                    delta = expires_at - now
                    if delta.total_seconds() < 0:
                        status = "[red]EXPIRED[/red]"
                    elif delta.total_seconds() < 300:
                        status = "[yellow]EXPIRING SOON[/yellow]"
                    else:
                        status = "[green]VALID[/green]"
                    expires_display = expires_at.strftime("%Y-%m-%d %H:%M UTC")
                except ValueError:
                    expires_display = expires_at_str
                    status = "[yellow]UNKNOWN[/yellow]"
            else:
                expires_display = "N/A"
                status = "[yellow]UNKNOWN[/yellow]"

            table.add_row(service, expires_display, status)

        console.print(table)
        return CommandResult.success_result("Status displayed")


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _load_credentials(working_dir: Path) -> tuple[str | None, str | None]:
    """Load Google OAuth credentials from .env.local then environment.

    Checks .env.local in working_dir first (highest priority), then falls
    back to os.environ so that existing env-var setups continue to work.

    Returns:
        (client_id, client_secret) - either may be None if not found.
    """
    env_local = working_dir / _ENV_LOCAL
    env_vars: dict = {}

    if env_local.exists():
        try:
            for line in env_local.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                env_vars[key.strip()] = value.strip().strip('"').strip("'")
        except OSError:
            pass

    client_id = env_vars.get("GOOGLE_OAUTH_CLIENT_ID") or os.environ.get(
        "GOOGLE_OAUTH_CLIENT_ID"
    )
    client_secret = env_vars.get("GOOGLE_OAUTH_CLIENT_SECRET") or os.environ.get(
        "GOOGLE_OAUTH_CLIENT_SECRET"
    )
    return client_id, client_secret


def _refresh_gworkspace_token(
    tokens_path: Path, service: str, client_id: str, client_secret: str
) -> CommandResult:
    """Call Google token endpoint to refresh a single service's access token.

    Reads the refresh_token from tokens_path, posts to the Google OAuth2
    token endpoint using urllib (stdlib only), and writes the updated
    access_token and expires_at back to tokens_path.

    Args:
        tokens_path: Path to .gworkspace-mcp/tokens.json
        service:     Key inside the JSON (e.g. "gworkspace-mcp")
        client_id:   Google OAuth client ID
        client_secret: Google OAuth client secret

    Returns:
        CommandResult indicating success or failure.
    """
    if not tokens_path.exists():
        return CommandResult.error_result(f"Token file not found: {tokens_path}")

    try:
        tokens_data = json.loads(tokens_path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        return CommandResult.error_result(f"Cannot read token file: {exc}")

    if service not in tokens_data:
        return CommandResult.error_result(
            f"Service '{service}' not found in {tokens_path}. "
            f"Available: {', '.join(tokens_data.keys())}"
        )

    token = tokens_data[service].get("token", {})
    refresh_token = token.get("refresh_token")
    if not refresh_token:
        return CommandResult.error_result(
            f"No refresh_token stored for '{service}'. Re-run 'claude-mpm oauth setup {service}'."
        )

    console.print(f"[cyan]Refreshing token for '{service}'...[/cyan]")

    payload = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }
    ).encode()

    req = urllib.request.Request(
        _GOOGLE_TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
            response_data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        return CommandResult.error_result(
            f"Google token endpoint returned {exc.code}: {body}"
        )
    except (urllib.error.URLError, OSError) as exc:
        return CommandResult.error_result(f"Network error during token refresh: {exc}")

    new_access_token = response_data.get("access_token")
    if not new_access_token:
        return CommandResult.error_result(
            f"Google did not return an access_token. Response: {response_data}"
        )

    # Compute expiry from expires_in (seconds) if provided
    expires_in = response_data.get("expires_in", 3600)
    from datetime import timedelta

    expires_at = datetime.now(UTC) + timedelta(seconds=int(expires_in))
    expires_at_str = expires_at.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Update token fields in place; preserve refresh_token and scopes
    token["access_token"] = new_access_token
    token["expires_at"] = expires_at_str
    if "refresh_token" in response_data:
        token["refresh_token"] = response_data["refresh_token"]

    tokens_data[service]["token"] = token

    try:
        tokens_path.write_text(json.dumps(tokens_data, indent=2))
    except OSError as exc:
        return CommandResult.error_result(f"Cannot write updated token file: {exc}")

    console.print(
        f"[green]Token refreshed for '{service}'. Expires: {expires_at_str}[/green]"
    )
    return CommandResult.success_result(
        f"Token refreshed for '{service}'", data={"expires_at": expires_at_str}
    )


def manage_auth(args) -> int:
    """Main entry point for auth management commands.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    command = AuthCommand()
    result = command.execute(args)
    return result.exit_code
