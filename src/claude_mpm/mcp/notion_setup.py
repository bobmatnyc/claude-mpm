"""notion-mpm: Setup CLI for Notion MCP integration.

WHY: Provides autonomous setup for the official Notion MCP server
(@notionhq/notion-mcp-server) without duplicating the MCP server itself.
claude-mpm ships this lightweight binary that ONLY handles setup; the actual
MCP server is delegated to the official npm package at runtime.

USAGE:
    notion-mpm setup   - Configure credentials and .mcp.json
    notion-mpm         - Show usage (no args)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _load_env_local(cwd: Path) -> dict[str, str]:
    """Return variables from .env.local, searching cwd and each parent directory.

    Walks up the directory tree (cwd → parents) and stops as soon as an
    .env.local containing at least one key is found.  This mirrors the
    TokenManager search strategy so that ``notion-mpm setup`` works correctly
    regardless of which subdirectory the user invokes it from.
    """
    candidates = [cwd, *cwd.parents]
    for directory in candidates:
        env_local = directory / ".env.local"
        if not env_local.exists():
            continue
        result: dict[str, str] = {}
        try:
            with open(env_local) as fh:
                for raw in fh:
                    line = raw.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    result[key.strip()] = value.strip().strip('"').strip("'")
        except OSError:
            continue
        if result:
            return result
    return {}


def _save_env_local(cwd: Path, entries: dict[str, str]) -> None:
    """Append key=value pairs to .env.local (creates file if absent)."""
    env_local = cwd / ".env.local"
    with open(env_local, "a") as fh:
        for key, value in entries.items():
            fh.write(f'{key}="{value}"  # pragma: allowlist secret\n')


def _load_mcp_json(cwd: Path) -> dict:
    """Load .mcp.json from cwd; return empty structure if absent or invalid."""
    mcp_path = cwd / ".mcp.json"
    if mcp_path.exists():
        try:
            with open(mcp_path) as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                return {"mcpServers": {}}
            return data
        except (json.JSONDecodeError, OSError):
            return {"mcpServers": {}}
    return {"mcpServers": {}}


def _save_mcp_json(cwd: Path, config: dict) -> None:
    """Write .mcp.json with trailing newline."""
    mcp_path = cwd / ".mcp.json"
    with open(mcp_path, "w") as fh:
        json.dump(config, fh, indent=2)
        fh.write("\n")


def _run_setup() -> int:
    """Interactively collect Notion credentials and configure .mcp.json.

    Returns:
        Exit code (0 = success, 1 = cancelled/error).
    """
    from rich.console import Console
    from rich.prompt import Prompt

    console = Console()
    cwd = Path.cwd()

    console.print("\n[bold cyan]Notion MCP Setup[/bold cyan]")
    console.print(
        "Configures the official Notion MCP server (@notionhq/notion-mcp-server)\n"
        "so Claude Code can interact with your Notion workspace.\n"
    )

    # --- Step 1: Check for existing NOTION_API_KEY ---
    env_vars = _load_env_local(cwd)
    existing_key = env_vars.get("NOTION_API_KEY", "")

    if existing_key:
        console.print(
            f"[green]NOTION_API_KEY already set in .env.local "
            f"({existing_key[:8]}...)[/green]"
        )
        api_key = existing_key
        save_to_env = False
    else:
        console.print(
            "[dim]Get your integration token at: "
            "https://www.notion.so/my-integrations[/dim]\n"
        )
        api_key = Prompt.ask(
            "[cyan]Notion API key[/cyan] (ntn_... or secret_... from notion.so/my-integrations)",
            password=True,
        )
        if not api_key or not api_key.strip():
            console.print("[red]No API key provided. Setup cancelled.[/red]")
            return 1
        api_key = api_key.strip()
        save_to_env = True

    # --- Step 2: Optional database ID ---
    existing_db = env_vars.get("NOTION_DATABASE_ID", "")
    if existing_db:
        console.print(
            f"[green]NOTION_DATABASE_ID already set in .env.local "
            f"({existing_db[:8]}...)[/green]"
        )
        database_id = existing_db
    else:
        database_id = Prompt.ask(
            "[cyan]Notion Database ID[/cyan] (optional - press Enter to skip)",
            default="",
        ).strip()

    # --- Step 3: Persist credentials ---
    if save_to_env:
        entries: dict[str, str] = {"NOTION_API_KEY": api_key}
        if database_id:
            entries["NOTION_DATABASE_ID"] = database_id
        try:
            _save_env_local(cwd, entries)
            console.print(f"[green]Credentials saved to {cwd / '.env.local'}[/green]")
        except OSError as exc:
            console.print(
                f"[yellow]Warning: could not write .env.local: {exc}[/yellow]"
            )

    # --- Step 4: Configure .mcp.json ---
    try:
        config = _load_mcp_json(cwd)
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        if "notion-mcp" in config["mcpServers"]:
            console.print("[dim]notion-mcp already present in .mcp.json[/dim]")
        else:
            server_config: dict = {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@notionhq/notion-mcp-server"],
                "env": {
                    "NOTION_API_KEY": api_key,
                },
            }
            if database_id:
                server_config["env"]["NOTION_DATABASE_ID"] = database_id

            config["mcpServers"]["notion-mcp"] = server_config
            _save_mcp_json(cwd, config)
            console.print("[green]notion-mcp added to .mcp.json[/green]")
    except OSError as exc:
        console.print(f"[red]Failed to update .mcp.json: {exc}[/red]")
        return 1

    # --- Step 5: Next steps ---
    console.print(
        "\n[bold green]Notion MCP setup complete![/bold green]\n"
        "\n[dim]Next steps:[/dim]\n"
        "  1. Share your Notion databases/pages with the integration at notion.so\n"
        "  2. Restart Claude Code to load the new MCP server\n"
        "  3. Use Notion MCP tools directly in your Claude Code sessions\n"
    )
    return 0


def _show_usage() -> None:
    """Print short usage information."""
    from rich.console import Console

    Console().print(
        "\n[bold]notion-mpm[/bold] — Notion MCP setup helper\n\n"
        "[dim]Usage:[/dim]\n"
        "  notion-mpm setup   Configure Notion credentials and .mcp.json\n\n"
        "[dim]Or via claude-mpm:[/dim]\n"
        "  claude-mpm setup notion-mpm\n"
    )


def main() -> None:
    """Entry point for the notion-mpm console script."""
    args = sys.argv[1:]

    if args and args[0] == "setup":
        sys.exit(_run_setup())

    _show_usage()
    sys.exit(0)


if __name__ == "__main__":
    main()
