"""Search tool MCP setup handlers: Brave Search, Tavily, Firecrawl."""

from __future__ import annotations

import os
from typing import Any

from ....shared import CommandResult
from .._shared import console


class SearchToolsMixin:
    """Mixin: web search MCP server setup (brave / tavily / firecrawl)."""

    # ------------------------------------------------------------------
    # Declare methods provided by McpConfigMixin at runtime via MRO.
    # These stubs satisfy Pyright without creating circular imports.
    # ------------------------------------------------------------------

    def _load_mcp_config(self) -> dict[str, Any]: ...  # pragma: no cover

    def _save_mcp_config(self, config: dict[str, Any]) -> None: ...  # pragma: no cover

    def _setup_brave_search(self, _args) -> CommandResult:
        """Set up Brave Search MCP server for web search."""
        _ = _args  # args passed by caller dispatch; not used in this implementation
        console.print("\n[bold cyan]Brave Search MCP Setup[/bold cyan]")
        console.print("This will configure Brave Search for web research.\n")

        # Check for API key
        api_key = os.getenv("BRAVE_API_KEY")
        if not api_key:
            console.print("[yellow]⚠️  BRAVE_API_KEY not found in environment[/yellow]")
            console.print("\nTo use Brave Search:")
            console.print("1. Get an API key from: https://brave.com/search/api/")
            console.print("2. Set environment variable:")
            console.print(
                "   export BRAVE_API_KEY='your-api-key'"  # pragma: allowlist secret
            )
            console.print("3. Run setup again\n")

            from rich.prompt import Prompt

            skip = Prompt.ask(
                "Continue without API key? (will configure but won't work until key added)",
                choices=["y", "n"],
                default="n",
            )
            if skip.lower() != "y":
                return CommandResult.error_result("Brave Search API key required")

        # Configure in .mcp.json
        try:
            mcp_config = self._load_mcp_config()

            # Check if already configured
            if "brave-search" in mcp_config.get("mcpServers", {}):
                console.print("[yellow]⚠️  brave-search already configured[/yellow]")
                from rich.prompt import Prompt

                overwrite = Prompt.ask("Overwrite?", choices=["y", "n"], default="n")
                if overwrite.lower() != "y":
                    return CommandResult.error_result("Setup cancelled")

            # Add Brave Search configuration
            if "mcpServers" not in mcp_config:
                mcp_config["mcpServers"] = {}

            mcp_config["mcpServers"]["brave-search"] = {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-brave-search"],
                "env": {"BRAVE_API_KEY": api_key or "${BRAVE_API_KEY}"},
            }

            self._save_mcp_config(mcp_config)
            console.print("[green]✓ Brave Search configured successfully[/green]")

            return CommandResult.success_result("Brave Search setup complete")

        except Exception as e:
            console.print(f"[red]✗ Error setting up Brave Search: {e}[/red]")
            return CommandResult.error_result(f"Setup failed: {e}")

    def _setup_tavily(self, _args) -> CommandResult:
        """Set up Tavily MCP server for AI-optimized search."""
        _ = _args  # args passed by caller dispatch; not used in this implementation
        console.print("\n[bold cyan]Tavily Search MCP Setup[/bold cyan]")
        console.print("This will configure Tavily for AI-optimized research.\n")

        # Check for API key
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            console.print("[yellow]⚠️  TAVILY_API_KEY not found in environment[/yellow]")
            console.print("\nTo use Tavily:")
            console.print("1. Get an API key from: https://tavily.com/")
            console.print("2. Set environment variable:")
            console.print(
                "   export TAVILY_API_KEY='your-api-key'"  # pragma: allowlist secret
            )
            console.print("3. Run setup again\n")

            from rich.prompt import Prompt

            skip = Prompt.ask(
                "Continue without API key? (will configure but won't work until key added)",
                choices=["y", "n"],
                default="n",
            )
            if skip.lower() != "y":
                return CommandResult.error_result("Tavily API key required")

        # Configure in .mcp.json
        try:
            mcp_config = self._load_mcp_config()

            # Check if already configured
            if "tavily" in mcp_config.get("mcpServers", {}):
                console.print("[yellow]⚠️  tavily already configured[/yellow]")
                from rich.prompt import Prompt

                overwrite = Prompt.ask("Overwrite?", choices=["y", "n"], default="n")
                if overwrite.lower() != "y":
                    return CommandResult.error_result("Setup cancelled")

            # Add Tavily configuration
            if "mcpServers" not in mcp_config:
                mcp_config["mcpServers"] = {}

            mcp_config["mcpServers"]["tavily"] = {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-tavily"],
                "env": {"TAVILY_API_KEY": api_key or "${TAVILY_API_KEY}"},
            }

            self._save_mcp_config(mcp_config)
            console.print("[green]✓ Tavily configured successfully[/green]")

            return CommandResult.success_result("Tavily setup complete")

        except Exception as e:
            console.print(f"[red]✗ Error setting up Tavily: {e}[/red]")
            return CommandResult.error_result(f"Setup failed: {e}")

    def _setup_firecrawl(self, _args) -> CommandResult:
        """Set up Firecrawl MCP server for web scraping."""
        _ = _args  # args passed by caller dispatch; not used in this implementation
        console.print("\n[bold cyan]Firecrawl MCP Setup[/bold cyan]")
        console.print("This will configure Firecrawl for web scraping.\n")

        # Check for API key
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            console.print(
                "[yellow]⚠️  FIRECRAWL_API_KEY not found in environment[/yellow]"
            )
            console.print("\nTo use Firecrawl:")
            console.print("1. Get an API key from: https://firecrawl.dev/")
            console.print("2. Set environment variable:")
            console.print(
                "   export FIRECRAWL_API_KEY='your-api-key'"  # pragma: allowlist secret
            )
            console.print("3. Run setup again\n")

            from rich.prompt import Prompt

            skip = Prompt.ask(
                "Continue without API key? (will configure but won't work until key added)",
                choices=["y", "n"],
                default="n",
            )
            if skip.lower() != "y":
                return CommandResult.error_result("Firecrawl API key required")

        # Configure in .mcp.json
        try:
            mcp_config = self._load_mcp_config()

            # Check if already configured
            if "firecrawl" in mcp_config.get("mcpServers", {}):
                console.print("[yellow]⚠️  firecrawl already configured[/yellow]")
                from rich.prompt import Prompt

                overwrite = Prompt.ask("Overwrite?", choices=["y", "n"], default="n")
                if overwrite.lower() != "y":
                    return CommandResult.error_result("Setup cancelled")

            # Add Firecrawl configuration
            if "mcpServers" not in mcp_config:
                mcp_config["mcpServers"] = {}

            mcp_config["mcpServers"]["firecrawl"] = {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@mendable/firecrawl-mcp"],
                "env": {"FIRECRAWL_API_KEY": api_key or "${FIRECRAWL_API_KEY}"},
            }

            self._save_mcp_config(mcp_config)
            console.print("[green]✓ Firecrawl configured successfully[/green]")

            return CommandResult.success_result("Firecrawl setup complete")

        except Exception as e:
            console.print(f"[red]✗ Error setting up Firecrawl: {e}[/red]")
            return CommandResult.error_result(f"Setup failed: {e}")
