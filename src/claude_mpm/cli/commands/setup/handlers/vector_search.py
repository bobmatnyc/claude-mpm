"""mcp-vector-search semantic code search setup handler."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404

from ....constants import SetupService
from ....shared import CommandResult
from .._shared import console


class VectorSearchMixin:
    """Mixin: mcp-vector-search install + index + MCP wiring."""

    def _setup_mcp_vector_search(self, args) -> CommandResult:
        """Set up mcp-vector-search semantic code search.

        Delegates to the native mcp-vector-search setup command for indexing
        and configuration, following the pattern used by mcp-ticketer.
        """
        try:
            console.print(
                "\n[bold]MCP Vector Search Setup[/bold]\n"
                "This will set up semantic code search with vector embeddings.\n"
            )

            # Use centralized package installer
            console.print("[cyan]Checking mcp-vector-search installation...[/cyan]")

            from .....services.package_installer import (
                InstallAction,
                PackageInstallerService,
                get_spec,
            )

            installer = PackageInstallerService()
            spec = get_spec(SetupService.MCP_VECTOR_SEARCH)

            force = getattr(args, "force", False)
            upgrade = getattr(args, "upgrade", False)

            # Check if binary exists (skip module import check for tool packages)
            if shutil.which("mcp-vector-search") and not force and not upgrade:
                console.print("[green]✓ mcp-vector-search already installed[/green]")
            else:
                console.print("[cyan]Detecting installation method...[/cyan]")
                success, message = installer.install(
                    spec, InstallAction.INSTALL, force=force, upgrade=upgrade
                )
                if success:
                    console.print(f"[green]✓ {message}[/green]")
                else:
                    return CommandResult.error_result(message)

            # Run the two non-interactive mcp-vector-search sub-commands.
            # WHY: `mcp-vector-search setup` calls setup_llm_api_keys(interactive=True)
            # which issues a Rich console.input() prompt.  With capture_output=True the
            # subprocess's stdin is /dev/null so the prompt blocks forever.
            # `index` and `install mcp` do the same work without interactive prompts.

            console.print("\n[cyan]Indexing codebase with mcp-vector-search...[/cyan]")
            index_args = ["mcp-vector-search", "index"]
            if force:
                index_args.append("--force")

            result = subprocess.run(
                index_args,
                capture_output=True,
                text=True,
                check=False,
            )  # nosec B603 B607

            if result.returncode != 0:
                console.print("[red]✗ mcp-vector-search index failed:[/red]")
                if result.stderr:
                    console.print(result.stderr)
                return CommandResult.error_result("mcp-vector-search index failed")

            console.print("[green]✓ Codebase indexed[/green]")
            console.print("\n[cyan]Configuring MCP integration...[/cyan]")

            install_result = subprocess.run(
                ["mcp-vector-search", "install", "mcp"],
                capture_output=True,
                text=True,
                check=False,
            )  # nosec B603 B607

            if install_result.returncode != 0:
                console.print("[red]✗ mcp-vector-search install mcp failed:[/red]")
                if install_result.stderr:
                    console.print(install_result.stderr)
                return CommandResult.error_result(
                    "mcp-vector-search MCP install failed"
                )

            console.print("\n[green]✓ MCP Vector Search setup complete![/green]")
            console.print(
                "\n[dim]What changed:[/dim]\n"
                "  1. mcp-vector-search installed (or re-used if already installed)\n"
                "  2. Codebase indexed for semantic search\n"
                "  3. MCP configuration updated in .mcp.json\n"
                "  4. MCP server available in Claude Code\n"
            )
            console.print(
                "\n[dim]Next steps:[/dim]\n"
                "  1. Restart Claude Code to load the MCP server\n"
                "  2. Use semantic search tools for better context retrieval\n"
            )

            return CommandResult.success_result("MCP Vector Search setup completed")

        except KeyboardInterrupt:
            console.print("\n[yellow]Setup cancelled by user[/yellow]")
            return CommandResult.error_result("Setup cancelled")
        except Exception as e:
            return CommandResult.error_result(f"Error during setup: {e}")
