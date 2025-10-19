"""
Search command module for mcp-vector-search integration.

This module provides the /mpm-search command for semantic code search
using the mcp-vector-search service.
"""

import asyncio
import json
import sys
from typing import Any, Dict, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from claude_mpm.services.core.service_container import get_global_container

console = Console()


class MCPSearchInterface:
    """Interface for interacting with mcp-vector-search service."""

    def __init__(self):
        """Initialize the search interface."""
        self.container = get_global_container()
        self.mcp_gateway = None
        self.vector_search_available = False

    async def initialize(self):
        """Initialize the MCP gateway connection."""
        try:
            from claude_mpm.services.mcp_gateway import MCPGatewayService

            self.mcp_gateway = self.container.resolve(MCPGatewayService)
            if not self.mcp_gateway:
                self.mcp_gateway = MCPGatewayService()
                await self.mcp_gateway.initialize()

            # Check if vector search is available
            self.vector_search_available = await self._check_vector_search_available()

        except Exception as e:
            console.print(f"[red]Failed to initialize MCP gateway: {e}[/red]")
            raise

    async def _check_vector_search_available(self) -> bool:
        """Check if mcp-vector-search is available and offer installation if not."""
        import importlib.util

        # Check if package is installed
        spec = importlib.util.find_spec("mcp_vector_search")
        if spec is not None:
            return True

        # Package not found - offer installation
        console.print("\n[yellow]⚠️  mcp-vector-search not found[/yellow]")
        console.print("This package enables semantic code search (optional feature).")
        console.print("\nInstallation options:")
        console.print("  1. Install via pip (recommended for this project)")
        console.print("  2. Install via pipx (isolated, system-wide)")
        console.print("  3. Skip (use traditional grep/glob instead)")

        try:
            choice = input("\nChoose option (1/2/3) [3]: ").strip() or "3"

            if choice == "1":
                return await self._install_via_pip()
            if choice == "2":
                return await self._install_via_pipx()
            console.print(
                "[dim]Continuing with fallback search methods (grep/glob)[/dim]"
            )
            return False

        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Installation cancelled, using fallback methods[/dim]")
            return False

    async def _install_via_pip(self) -> bool:
        """Install mcp-vector-search via pip."""
        import subprocess

        try:
            console.print("\n[cyan]📦 Installing mcp-vector-search via pip...[/cyan]")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "mcp-vector-search"],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )

            if result.returncode == 0:
                console.print(
                    "[green]✓ Successfully installed mcp-vector-search[/green]"
                )
                return True

            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            console.print(f"[red]✗ Installation failed: {error_msg}[/red]")
            return False

        except subprocess.TimeoutExpired:
            console.print("[red]✗ Installation timed out[/red]")
            return False
        except Exception as e:
            console.print(f"[red]✗ Installation error: {e}[/red]")
            return False

    async def _install_via_pipx(self) -> bool:
        """Install mcp-vector-search via pipx."""
        import subprocess

        try:
            # Check if pipx is available
            pipx_check = subprocess.run(
                ["pipx", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            if pipx_check.returncode != 0:
                console.print("[red]✗ pipx is not installed[/red]")
                console.print("Install pipx first: python -m pip install pipx")
                return False

            console.print("\n[cyan]📦 Installing mcp-vector-search via pipx...[/cyan]")
            result = subprocess.run(
                ["pipx", "install", "mcp-vector-search"],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )

            if result.returncode == 0:
                console.print(
                    "[green]✓ Successfully installed mcp-vector-search[/green]"
                )
                return True

            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            console.print(f"[red]✗ Installation failed: {error_msg}[/red]")
            return False

        except FileNotFoundError:
            console.print("[red]✗ pipx command not found[/red]")
            console.print("Install pipx first: python -m pip install pipx")
            return False
        except subprocess.TimeoutExpired:
            console.print("[red]✗ Installation timed out[/red]")
            return False
        except Exception as e:
            console.print(f"[red]✗ Installation error: {e}[/red]")
            return False

    async def search_code(
        self,
        query: str,
        limit: int = 10,
        similarity_threshold: float = 0.3,
        file_extensions: Optional[list] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search code using semantic similarity."""
        params = {
            "query": query,
            "limit": limit,
            "similarity_threshold": similarity_threshold,
        }

        if file_extensions:
            params["file_extensions"] = file_extensions
        if language:
            params["language"] = language

        return await self._call_mcp_tool("mcp__mcp-vector-search__search_code", params)

    async def search_similar(
        self,
        file_path: str,
        function_name: Optional[str] = None,
        limit: int = 10,
        similarity_threshold: float = 0.3,
    ) -> Dict[str, Any]:
        """Find code similar to a specific file or function."""
        params = {
            "file_path": file_path,
            "limit": limit,
            "similarity_threshold": similarity_threshold,
        }

        if function_name:
            params["function_name"] = function_name

        return await self._call_mcp_tool(
            "mcp__mcp-vector-search__search_similar", params
        )

    async def search_context(
        self, description: str, focus_areas: Optional[list] = None, limit: int = 10
    ) -> Dict[str, Any]:
        """Search for code based on contextual description."""
        params = {"description": description, "limit": limit}

        if focus_areas:
            params["focus_areas"] = focus_areas

        return await self._call_mcp_tool(
            "mcp__mcp-vector-search__search_context", params
        )

    async def get_status(self) -> Dict[str, Any]:
        """Get project indexing status and statistics."""
        return await self._call_mcp_tool(
            "mcp__mcp-vector-search__get_project_status", {}
        )

    async def index_project(
        self, force: bool = False, file_extensions: Optional[list] = None
    ) -> Dict[str, Any]:
        """Index or reindex the project codebase."""
        params = {"force": force}

        if file_extensions:
            params["file_extensions"] = file_extensions

        return await self._call_mcp_tool(
            "mcp__mcp-vector-search__index_project", params
        )

    async def _call_mcp_tool(
        self, tool_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call an MCP tool through the gateway."""
        if not self.mcp_gateway:
            await self.initialize()

        # Check if vector search is available
        if not self.vector_search_available:
            return {
                "error": "mcp-vector-search is not available. Use traditional grep/glob tools instead, or run command again to install."
            }

        try:
            return await self.mcp_gateway.call_tool(tool_name, params)
        except Exception as e:
            return {"error": str(e)}


def display_search_results(results: Dict[str, Any], output_format: str = "rich"):
    """Display search results in the specified format."""
    if output_format == "json":
        console.print_json(json.dumps(results, indent=2))
        return

    if "error" in results:
        console.print(f"[red]Error: {results['error']}[/red]")
        return

    if not results.get("results"):
        console.print("[yellow]No results found.[/yellow]")
        return

    # Create a table for results
    table = Table(title="Search Results", show_header=True, header_style="bold magenta")
    table.add_column("File", style="cyan", no_wrap=False)
    table.add_column("Score", style="green", width=8)
    table.add_column("Type", style="yellow", width=10)
    table.add_column("Name", style="blue", no_wrap=False)

    for result in results["results"]:
        file_path = result.get("file_path", "Unknown")
        score = f"{result.get('score', 0):.3f}"
        item_type = result.get("type", "unknown")
        name = result.get("name", result.get("function_name", ""))

        table.add_row(file_path, score, item_type, name)

        # Show snippet if available
        if result.get("snippet"):
            snippet_panel = Panel(
                Syntax(
                    result["snippet"], result.get("language", "python"), theme="monokai"
                ),
                title=f"[cyan]{file_path}[/cyan]",
                border_style="dim",
            )
            console.print(snippet_panel)

    console.print(table)

    # Show statistics if available
    if "stats" in results:
        stats = results["stats"]
        console.print("\n[bold]Statistics:[/bold]")
        console.print(f"  Total indexed files: {stats.get('total_files', 0)}")
        console.print(f"  Total indexed functions: {stats.get('total_functions', 0)}")
        console.print(f"  Index last updated: {stats.get('last_updated', 'Unknown')}")


@click.command()
@click.argument("query", required=False)
@click.option("--similar", "-s", help="Find code similar to a specific file")
@click.option("--context", "-c", help="Search by contextual description")
@click.option("--index", is_flag=True, help="Index or reindex the project")
@click.option("--status", is_flag=True, help="Check index status")
@click.option("--limit", "-l", default=10, help="Maximum number of results")
@click.option("--threshold", "-t", default=0.3, help="Similarity threshold (0.0-1.0)")
@click.option("--language", help="Filter by programming language")
@click.option("--extensions", multiple=True, help="Filter by file extensions")
@click.option("--function", "-f", help="Function name (with --similar)")
@click.option("--focus", multiple=True, help="Focus areas (with --context)")
@click.option("--force", is_flag=True, help="Force reindexing (with --index)")
@click.option("--json", "output_json", is_flag=True, help="Output results as JSON")
async def search_command(
    query: Optional[str],
    similar: Optional[str],
    context: Optional[str],
    index: bool,
    status: bool,
    limit: int,
    threshold: float,
    language: Optional[str],
    extensions: tuple,
    function: Optional[str],
    focus: tuple,
    force: bool,
    output_json: bool,
):
    """
    Search the codebase using semantic search powered by mcp-vector-search.

    Examples:
        /mpm-search "authentication logic"
        /mpm-search --similar src/auth.py
        /mpm-search --context "find all API endpoints"
        /mpm-search --index --force
        /mpm-search --status
    """
    search = MCPSearchInterface()
    await search.initialize()

    output_format = "json" if output_json else "rich"

    try:
        # Show first-time usage tips if vector search is available
        if search.vector_search_available and not (index or status):
            console.print(
                "\n[dim]💡 Tip: Vector search provides semantic code understanding.[/dim]"
            )
            console.print(
                "[dim]   Run with --index first to index your project.[/dim]\n"
            )

        # Handle different operation modes
        if index:
            if not search.vector_search_available:
                console.print("[red]✗ mcp-vector-search is required for indexing[/red]")
                console.print(
                    "[dim]Install it or use traditional grep/glob for search[/dim]"
                )
                sys.exit(1)

            console.print("[cyan]Indexing project...[/cyan]")
            result = await search.index_project(
                force=force, file_extensions=list(extensions) if extensions else None
            )
            if "error" not in result:
                console.print("[green]✓ Project indexed successfully[/green]")
            display_search_results(result, output_format)

        elif status:
            if not search.vector_search_available:
                console.print(
                    "[red]✗ mcp-vector-search is required for status check[/red]"
                )
                console.print("[dim]Install it to use vector search features[/dim]")
                sys.exit(1)

            result = await search.get_status()
            display_search_results(result, output_format)

        elif similar:
            if not search.vector_search_available:
                console.print("[yellow]⚠️  Vector search not available[/yellow]")
                console.print("[dim]Similarity search requires mcp-vector-search[/dim]")
                console.print("[dim]Falling back to basic file search...[/dim]")
                sys.exit(1)

            result = await search.search_similar(
                file_path=similar,
                function_name=function,
                limit=limit,
                similarity_threshold=threshold,
            )
            display_search_results(result, output_format)

        elif context:
            if not search.vector_search_available:
                console.print("[yellow]⚠️  Vector search not available[/yellow]")
                console.print("[dim]Context search requires mcp-vector-search[/dim]")
                console.print("[dim]Try using grep for text-based search instead[/dim]")
                sys.exit(1)

            result = await search.search_context(
                description=context,
                focus_areas=list(focus) if focus else None,
                limit=limit,
            )
            display_search_results(result, output_format)

        elif query:
            if not search.vector_search_available:
                console.print("[yellow]⚠️  Vector search not available[/yellow]")
                console.print("[dim]Code search requires mcp-vector-search[/dim]")
                console.print(
                    "\n[cyan]Alternative: Use grep for pattern matching:[/cyan]"
                )
                console.print(f"  grep -r '{query}' .")
                sys.exit(1)

            result = await search.search_code(
                query=query,
                limit=limit,
                similarity_threshold=threshold,
                file_extensions=list(extensions) if extensions else None,
                language=language,
            )
            display_search_results(result, output_format)

        else:
            console.print(
                "[yellow]No search operation specified. Use --help for options.[/yellow]"
            )

    except Exception as e:
        console.print(f"[red]Search failed: {e}[/red]")
        if not output_json:
            console.print(
                "[dim]Tip: Make sure the project is indexed with --index first[/dim]"
            )
        sys.exit(1)


def main():
    """Main entry point for the search command."""
    asyncio.run(search_command())


if __name__ == "__main__":
    main()
