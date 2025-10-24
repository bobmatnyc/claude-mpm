"""
CLI Helper Utilities
====================

This module provides helper functions for the CLI, including configuration
checks and user prompts.

Part of cli/__init__.py refactoring to reduce file size and improve modularity.
"""

import sys
from pathlib import Path


def has_configuration_file() -> bool:
    """Check if any configuration file exists in standard locations."""
    config_paths = [
        Path.cwd() / ".claude-mpm" / "configuration.yaml",
        Path.cwd() / ".claude-mpm" / "configuration.yml",
        Path.home() / ".claude-mpm" / "configuration.yaml",
        Path.home() / ".claude-mpm" / "configuration.yml",
    ]
    return any(path.exists() for path in config_paths)


def is_interactive_session() -> bool:
    """Check if running in an interactive terminal."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def should_skip_config_check(command: str | None) -> bool:
    """Check if command should skip configuration check."""
    skip_commands = ["configure", "doctor", "info", "mcp", "config"]
    return command in skip_commands if command else False


def prompt_for_configuration() -> bool:
    """Prompt user to run configuration wizard.

    Returns:
        bool: True if user wants to configure, False otherwise
    """
    from rich.console import Console as RichConsole
    from rich.prompt import Confirm

    console = RichConsole()

    console.print()
    console.print("[yellow]⚙️  Configuration Recommended[/yellow]")
    console.print()
    console.print("Claude MPM works best with proper configuration.")
    console.print("The configurator helps you:")
    console.print("  • Enable/disable MCP services (ticketer, browser, vector-search)")
    console.print("  • Configure hook services (monitor, dashboard)")
    console.print("  • Select system agents to use")
    console.print()

    return Confirm.ask("Would you like to run the configurator now?", default=True)


def handle_missing_configuration():
    """Handle missing configuration file by prompting user to configure.

    WHY: Centralizes the logic for handling missing configuration files,
    keeping main() cleaner and more focused.
    """
    if is_interactive_session():
        # Interactive: Offer to run configurator
        if prompt_for_configuration():
            from rich.console import Console as RichConsole

            # Import configure command only when needed
            from .commands.configure import ConfigureCommand

            console = RichConsole()
            config_cmd = ConfigureCommand()
            try:
                config_cmd.execute({})
                console.print(
                    "\n[green]✓[/green] Configuration complete! "
                    "Continuing with command...\n"
                )
            except Exception as e:
                console.print(f"\n[yellow]⚠[/yellow] Configuration error: {e}")
                console.print(
                    "[yellow]Continuing with default configuration...\n[/yellow]"
                )
        else:
            from rich.console import Console as RichConsole

            console = RichConsole()
            console.print("\n[dim]Using default configuration.[/dim]")
            console.print(
                "[dim]Run 'claude-mpm configure' anytime to set up your "
                "preferences.\n[/dim]"
            )
    else:
        # Non-interactive: Log message only
        import logging

        logger = logging.getLogger(__name__)
        logger.info(
            "Configuration file not found, using defaults. "
            "Run 'claude-mpm configure' to customize."
        )
