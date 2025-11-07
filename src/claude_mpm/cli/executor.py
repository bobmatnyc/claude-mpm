"""
CLI Command Executor
====================

This module handles command execution routing and argument preparation.

Part of cli/__init__.py refactoring to reduce file size and improve modularity.
"""

from ..constants import CLICommands
from .commands import (
    aggregate_command,
    cleanup_memory,
    manage_agent_manager,
    manage_agents,
    manage_config,
    manage_configure,
    manage_debug,
    manage_mcp,
    manage_memory,
    manage_monitor,
    manage_tickets,
    run_doctor,
    run_session,
    show_info,
)
from .commands.analyze_code import manage_analyze_code
from .commands.dashboard import manage_dashboard
from .commands.skills import manage_skills
from .commands.upgrade import upgrade


def ensure_run_attributes(args):
    """
    Ensure run command attributes exist when defaulting to run.

    WHY: When no command is specified, we default to 'run' but the args object
    won't have run-specific attributes from the subparser. This function ensures
    they exist with sensible defaults.

    Args:
        args: Parsed arguments object to update
    """
    # Set defaults for run command attributes
    args.no_tickets = getattr(args, "no_tickets", False)
    args.no_hooks = getattr(args, "no_hooks", False)
    args.intercept_commands = getattr(args, "intercept_commands", False)
    args.input = getattr(args, "input", None)
    args.non_interactive = getattr(args, "non_interactive", False)
    args.no_native_agents = getattr(args, "no_native_agents", False)

    # Handle claude_args - if --resume flag is set, add it to claude_args
    claude_args = getattr(args, "claude_args", [])
    if getattr(args, "resume", False):
        # Add --resume to claude_args if not already present
        if "--resume" not in claude_args:
            claude_args = ["--resume", *claude_args]
    args.claude_args = claude_args

    args.launch_method = getattr(args, "launch_method", "exec")
    args.websocket = getattr(args, "websocket", False)
    args.websocket_port = getattr(args, "websocket_port", 8765)
    # CRITICAL: Include mpm_resume attribute for session resumption
    args.mpm_resume = getattr(args, "mpm_resume", None)
    # Also include monitor and force attributes
    args.monitor = getattr(args, "monitor", False)
    args.force = getattr(args, "force", False)
    args.reload_agents = getattr(args, "reload_agents", False)
    # Include dependency checking attributes
    args.check_dependencies = getattr(args, "check_dependencies", True)
    args.force_check_dependencies = getattr(args, "force_check_dependencies", False)
    args.no_prompt = getattr(args, "no_prompt", False)
    args.force_prompt = getattr(args, "force_prompt", False)


def execute_command(command: str, args) -> int:
    """
    Execute the specified command.

    WHY: This function maps command names to their implementations, providing
    a single place to manage command routing. Experimental commands are imported
    lazily to avoid loading unnecessary code.

    DESIGN DECISION: run_guarded is imported only when needed to maintain
    separation between stable and experimental features. Command suggestions
    are provided for unknown commands to improve user experience.

    Args:
        command: The command name to execute
        args: Parsed command line arguments

    Returns:
        Exit code from the command
    """
    # Handle experimental run-guarded command separately with lazy import
    if command == "run-guarded":
        # Lazy import to avoid loading experimental code unless needed
        from .commands.run_guarded import execute_run_guarded

        result = execute_run_guarded(args)
        return result if result is not None else 0

    # Handle mpm-init command with lazy import
    if command == "mpm-init":
        # Lazy import to avoid loading unless needed
        from .commands.mpm_init_handler import manage_mpm_init

        result = manage_mpm_init(args)
        return result if result is not None else 0

    # Handle uninstall command with lazy import
    if command == "uninstall":
        # Lazy import to avoid loading unless needed
        from .commands.uninstall import UninstallCommand

        cmd = UninstallCommand()
        result = cmd.execute(args)
        # Convert CommandResult to exit code
        return result.exit_code if result else 0

    # Handle verify command with lazy import
    if command == "verify":
        # Lazy import to avoid loading unless needed
        from .commands.verify import handle_verify

        result = handle_verify(args)
        return result if result is not None else 0

    # Handle auto-configure command with lazy import
    if command == "auto-configure":
        # Lazy import to avoid loading unless needed
        from .commands.auto_configure import AutoConfigureCommand

        cmd = AutoConfigureCommand()
        result = cmd.run(args)
        # Convert CommandResult to exit code
        return result.exit_code if result else 0

    # Handle local-deploy command with lazy import
    if command == "local-deploy":
        # Lazy import to avoid loading unless needed
        from .commands.local_deploy import LocalDeployCommand

        cmd = LocalDeployCommand()
        result = cmd.run(args)
        # Convert CommandResult to exit code
        return result.exit_code if result else 0

    # Map stable commands to their implementations
    command_map = {
        CLICommands.RUN.value: run_session,
        # CLICommands.RUN_GUARDED.value is handled above
        CLICommands.TICKETS.value: manage_tickets,
        CLICommands.INFO.value: show_info,
        CLICommands.AGENTS.value: manage_agents,
        CLICommands.AGENT_MANAGER.value: manage_agent_manager,
        CLICommands.MEMORY.value: manage_memory,
        CLICommands.MONITOR.value: manage_monitor,
        CLICommands.DASHBOARD.value: manage_dashboard,
        CLICommands.CONFIG.value: manage_config,
        CLICommands.CONFIGURE.value: manage_configure,
        CLICommands.AGGREGATE.value: aggregate_command,
        CLICommands.ANALYZE_CODE.value: manage_analyze_code,
        CLICommands.CLEANUP.value: cleanup_memory,
        CLICommands.MCP.value: manage_mcp,
        CLICommands.DOCTOR.value: run_doctor,
        CLICommands.UPGRADE.value: upgrade,
        CLICommands.SKILLS.value: manage_skills,
        "debug": manage_debug,  # Add debug command
        "mpm-init": None,  # Will be handled separately with lazy import
    }

    # Execute command if found
    if command in command_map:
        result = command_map[command](args)
        # Commands may return None (success) or an exit code
        return result if result is not None else 0

    # Unknown command - provide suggestions
    from rich.console import Console

    from .utils import suggest_similar_commands

    console = Console(stderr=True)

    console.print(f"\n[red]Error:[/red] Unknown command: {command}\n", style="bold")

    # Get all valid commands for suggestions
    all_commands = [
        *command_map.keys(),
        "run-guarded",
        "uninstall",
        "verify",
        "auto-configure",
        "local-deploy",
    ]

    suggestion = suggest_similar_commands(command, all_commands)
    if suggestion:
        console.print(f"[yellow]{suggestion}[/yellow]\n")

    console.print("[dim]Run 'claude-mpm --help' for usage information.[/dim]\n")

    return 1
