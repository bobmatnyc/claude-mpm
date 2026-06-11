"""SetupCommand — thin dispatcher that wires service handlers together.

WHY: Users need a consistent way to set up various services and integrations.

DESIGN DECISIONS:
- Use BaseCommand for consistent CLI patterns
- Unified command structure: claude-mpm setup [services...]
- Support multiple services in one command with service-specific options
- Flags after a service name apply to that service
- Delegate to service-specific handler mixins (one mixin per service group)

Handlers live in ``setup/handlers/*.py`` and are composed via multiple
inheritance. This keeps each service's implementation isolated while
preserving a single ``SetupCommand`` surface for tests/callers.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404
import sys
from argparse import Namespace

from ...constants import GLOBAL_SETUP_FLAGS, VALUE_FLAGS, SetupFlag, SetupService
from ...shared import BaseCommand, CommandResult
from ._shared import console
from .autonomous import AutonomousSetupMixin
from .handlers.confluence import ConfluenceMixin
from .handlers.google_workspace import GoogleWorkspaceMixin
from .handlers.kuzu_memory import KuzuMemoryMixin
from .handlers.oauth import OAuthMixin
from .handlers.search_tools import SearchToolsMixin
from .handlers.skillset import SkillsetMixin
from .handlers.slack import SlackMixin
from .handlers.trusty import TrustyMixin
from .handlers.vector_search import VectorSearchMixin
from .manifest_integration import ManifestSetupMixin
from .mcp_config import McpConfigMixin
from .parse_args import AUTONOMOUS_SETUP_SERVICES, parse_service_args

# Keep constants names referenced for static analyzers (also re-exported below).
_ = (GLOBAL_SETUP_FLAGS, VALUE_FLAGS)


class SetupCommand(
    BaseCommand,
    McpConfigMixin,
    AutonomousSetupMixin,
    ManifestSetupMixin,
    SlackMixin,
    SearchToolsMixin,
    TrustyMixin,
    KuzuMemoryMixin,
    VectorSearchMixin,
    SkillsetMixin,
    GoogleWorkspaceMixin,
    ConfluenceMixin,
    OAuthMixin,
):
    """Unified setup command for all services."""

    def __init__(self):
        super().__init__("setup")

    def validate_args(self, args) -> str | None:
        """Validate command arguments."""
        # Parse service_args if present
        if hasattr(args, "service_args") and args.service_args:
            try:
                parsed = parse_service_args(args.service_args)
                args.parsed_services = parsed["services"]
                args.global_options = parsed["global_options"]

                # Validate OAuth requirements
                for service in parsed["services"]:
                    if service["name"] == str(SetupService.OAUTH):
                        oauth_svc_key = str(SetupFlag.OAUTH_SERVICE)
                        if oauth_svc_key not in service["options"]:
                            return (
                                f"OAuth setup requires {SetupFlag.OAUTH_SERVICE.cli_flag} flag. "
                                f"Example: claude-mpm setup oauth {SetupFlag.OAUTH_SERVICE.cli_flag} {SetupService.GWORKSPACE_MCP}"
                            )

                return None
            except ValueError as e:
                return str(e)

        return None

    def run(self, args) -> CommandResult:
        """Execute the setup command.

        WHAT: Dispatches explicit service names given on the command line; when
        no services are given, tries manifest-driven auto-setup first; falls back
        to help display when neither applies.

        WHY: The manifest-first check preserves the dormant-unless-detected
        contract (SPEC-MANIFEST-06~1): manifest code is entered only when a
        manifest file exists AND no explicit services were requested.  Explicit
        service lists always win.

        :spec: SPEC-MANIFEST-06~1
        """
        # Check if --provider was given (it can be used alone, without services)
        provider_key = str(SetupFlag.PROVIDER)
        has_provider_flag = bool(getattr(args, provider_key, None))

        # If no services and no --provider flag, try manifest auto-setup first.
        if not hasattr(args, "parsed_services") or not args.parsed_services:
            if not has_provider_flag:
                # Attempt manifest-driven setup (dormant → None when no manifest).
                manifest_result = self._run_manifest_services(args)
                if manifest_result is not None:
                    return manifest_result
                # No manifest → fall through to help display.
                self._show_help()
                return CommandResult.success_result("Help displayed")
            # --provider only: skip service processing, fall through to provider section
            services = []
        else:
            services = args.parsed_services

        # Process multiple services in sequence
        results = []
        for service_config in services:
            service_name = service_config["name"]
            service_options = service_config["options"]

            console.print(f"\n[bold cyan]Setting up {service_name}...[/bold cyan]")

            # Create a namespace object with the service options
            service_args = Namespace(**service_options)

            result = self._dispatch_service(service_name, service_args)

            results.append((service_name, result))

            # Track failure but continue processing remaining services
            if not result.success:
                console.print(
                    f"\n[red]✗ Setup failed for {service_name}[/red]",
                    style="bold",
                )
                # Don't return early - continue processing remaining services
            else:
                console.print(
                    f"[green]✓ {service_name} setup complete![/green]",
                    style="bold",
                )

        # Report results
        successful = [r for r in results if r[1].success]
        failed = [r for r in results if not r[1].success]

        if successful:
            console.print(
                f"\n[green]✓ {len(successful)} service(s) set up successfully[/green]",
                style="bold",
            )

        if failed:
            console.print(
                f"\n[red]✗ {len(failed)} service(s) failed to set up[/red]",
                style="bold",
            )

        # Handle --provider flag: configure API provider as part of setup
        provider_name = getattr(args, provider_key, None)
        if not provider_name:
            # Also check global_options (parsed from positional service_args)
            global_options_check = getattr(args, "global_options", {})
            provider_name = global_options_check.get(provider_key)
        if provider_name:
            self._configure_provider(args, provider_name)

        # Launch claude-mpm after all services are set up (unless --no-launch specified)
        # Only launch if at least one service succeeded
        # Check argparse flag first, then global_options, then per-service options
        no_launch_key = str(SetupFlag.NO_LAUNCH)
        no_launch = getattr(args, no_launch_key, False)
        if not no_launch:
            global_options = getattr(args, "global_options", {})
            no_launch = global_options.get(no_launch_key, False)
        # Also check if any service had --no-launch applied to it
        if not no_launch:
            no_launch = any(
                svc.get("options", {}).get(no_launch_key, False) for svc in services
            )
        if not no_launch and len(successful) > 0:
            console.print("\n[cyan]Launching claude-mpm...[/cyan]\n")
            try:
                # Replace current process with claude-mpm
                os.execvp("claude-mpm", ["claude-mpm"])  # nosec B606 B607
            except OSError:
                # If execvp fails (e.g., claude-mpm not in PATH), try subprocess
                subprocess.run(["claude-mpm"], check=False)  # nosec B603 B607
                sys.exit(0)

        # Return failure if all services failed, success if any succeeded
        # (If no services were requested, only --provider was used — that's a success)
        if results and len(failed) == len(results):
            return CommandResult.error_result(
                f"All {len(failed)} service(s) failed to set up"
            )
        if results:
            return CommandResult.success_result(
                f"Set up {len(successful)}/{len(results)} service(s) successfully"
            )
        return CommandResult.success_result("Setup complete")

    # ------------------------------------------------------------------
    # Dispatch & helpers
    # ------------------------------------------------------------------

    # Map of explicit service names to handler-method names on this class.
    # Declarative-first: services in AUTONOMOUS_SETUP_SERVICES are handled by
    # the generic _run_autonomous_setup() and are NOT listed here.
    _SERVICE_HANDLERS: dict[str, str] = {
        "gworkspace-mcp": "_setup_google_workspace",
        "slack-mpm": "_setup_slack_mpm",
        "confluence": "_setup_confluence",
        "kuzu-memory": "_setup_kuzu_memory",
        "mcp-vector-search": "_setup_mcp_vector_search",
        "mcp-skillset": "_setup_mcp_skillset",
        "oauth": "_setup_oauth",
        "brave-search": "_setup_brave_search",
        "tavily": "_setup_tavily",
        "firecrawl": "_setup_firecrawl",
        "trusty-search": "_setup_trusty_search",
        "trusty-memory": "_setup_trusty_memory",
        "trusty-analyze": "_setup_trusty_analyze",
    }

    def _dispatch_service(self, service_name: str, service_args) -> CommandResult:
        """Route a single service to its handler or the autonomous fallback."""
        # Declarative-first dispatch: check autonomous registry before custom handlers.
        if service_name in AUTONOMOUS_SETUP_SERVICES:
            return self._run_autonomous_setup(
                service_name, AUTONOMOUS_SETUP_SERVICES[service_name], service_args
            )

        handler_name = self._SERVICE_HANDLERS.get(service_name)
        if handler_name is not None:
            handler = getattr(self, handler_name)
            return handler(service_args)

        # Open-world fallback: if the binary exists and supports `setup`,
        # delegate automatically without requiring a custom _setup_* method.
        return self._try_autonomous_setup_fallback(service_name, service_args)

    def _configure_provider(self, args, provider_name: str) -> None:
        """Apply ``--provider`` (and optional ``--region``/``--model``) to config."""
        console.print(
            f"\n[bold cyan]Configuring API provider: {provider_name}...[/bold cyan]"
        )
        from ....config.api_provider import APIBackend, APIProviderConfig

        config_path = self.working_dir / ".claude-mpm" / "configuration.yaml"
        config = APIProviderConfig.load(config_path)
        region_key = str(SetupFlag.REGION)
        model_key = str(SetupFlag.MODEL)
        region = getattr(args, region_key, None)
        model = getattr(args, model_key, None)
        if provider_name == "anthropic":
            config.backend = APIBackend.ANTHROPIC
            if model:
                config.anthropic.model = model
            try:
                config.save(config_path)
                console.print(
                    f"[green]✓ Provider set to Anthropic (model: {config.anthropic.model})[/green]"
                )
            except Exception as e:
                console.print(f"[red]✗ Failed to save provider config: {e}[/red]")
        elif provider_name == "bedrock":
            config.backend = APIBackend.BEDROCK
            if region:
                config.bedrock.region = region
            if model:
                config.bedrock.model = model
            try:
                config.save(config_path)
                console.print(
                    f"[green]✓ Provider set to Bedrock (region: {config.bedrock.region}, model: {config.bedrock.model})[/green]"
                )
            except Exception as e:
                console.print(f"[red]✗ Failed to save provider config: {e}[/red]")

    def _show_help(self) -> None:
        """Display setup command help."""
        help_text = """
[bold]Setup Command:[/bold]
  setup SERVICE [OPTIONS] [SERVICE [OPTIONS] ...]

[bold]Available Services:[/bold]
  slack-mpm              Set up Slack MCP server (token-based)
  gworkspace-mcp         Set up Google Workspace MCP (includes OAuth)
  confluence             Set up Confluence integration
  kuzu-memory            Set up kuzu-memory graph-based memory backend
  mcp-vector-search      Set up mcp-vector-search semantic code search
  mcp-skillset           Set up mcp-skillset RAG-powered skills (USER-LEVEL)
  mcp-ticketer           Set up mcp-ticketer ticket management via MCP
  notion-mpm             Set up Notion MCP server (official @notionhq package)
  trusty-search          Set up trusty-search Rust hybrid code search daemon
  trusty-memory          Set up trusty-memory Rust AI memory daemon
  trusty-analyze         Set up trusty-analyze Rust code-analysis sidecar daemon
  oauth                  Set up OAuth authentication

[bold]Service Options:[/bold]
  --oauth-service NAME   Service name for OAuth (required for 'oauth')
  --no-browser           Don't auto-open browser for authentication (oauth only)
  --no-launch            Don't auto-launch claude-mpm after setup (all services)
  --force                Force credential re-entry (oauth) or reinstall (mcp-vector-search, mcp-skillset)
  --upgrade              Upgrade installed packages to latest version
  --provider PROVIDER    Set API provider: anthropic or bedrock (can be used alone)
  --region REGION        AWS region for Bedrock (used with --provider bedrock)
  --model MODEL          Model ID for the selected provider

[bold]Examples:[/bold]
  # Set up Slack MCP server
  claude-mpm setup slack-mpm

  # Slack without auto-launch
  claude-mpm setup slack-mpm --no-launch

  # Force re-validation of token
  claude-mpm setup slack-mpm --force

  # Multiple services (space-separated)
  claude-mpm setup slack-mpm gworkspace-mcp

  # Multiple services (comma-separated)
  claude-mpm setup slack-mpm,gworkspace-mcp

  # Service with options
  claude-mpm setup oauth --oauth-service gworkspace-mcp --no-browser

  # Multiple services with options
  claude-mpm setup slack-mpm oauth --oauth-service gworkspace-mcp --no-launch

  # Set up Notion MCP integration
  claude-mpm setup notion-mpm

  # Set up mcp-vector-search
  claude-mpm setup mcp-vector-search

  # With force flag to reinstall
  claude-mpm setup mcp-vector-search --force

[dim]Note: Flags apply to the service that precedes them.[/dim]
"""
        console.print(help_text)


def manage_setup(args) -> int:
    """Main entry point for setup commands.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    command = SetupCommand()
    result = command.execute(args)

    # Print error message if command failed
    if not result.success and result.message:
        console.print(f"\n[red]Error:[/red] {result.message}\n", style="bold")

    return result.exit_code
