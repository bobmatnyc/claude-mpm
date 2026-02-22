"""Central configuration for command behavior.

This module defines which commands should skip framework initialization
(lightweight commands) and provides utilities to check command behavior.

Why centralized config:
- Single source of truth for command categorization
- Easier to add new lightweight commands
- Consistent behavior across CLI startup, display, and execution
"""

# Commands that run without framework initialization
# These commands are fast utilities that don't need Claude Code or background services
LIGHTWEIGHT_COMMANDS = {
    # Configuration and setup
    "config",
    "configure",
    "oauth",
    "setup",
    "gh",  # GitHub multi-account management
    # Diagnostics and tools
    "tools",
    "debug",
    "doctor",
    "diagnose",
    "check-health",
    # Installation management
    "uninstall",
    "upgrade",
    "verify",
    # Error and postmortem analysis
    "hook-errors",
    "autotodos",
    "postmortem",
    "pm-analysis",
    # Integrations
    "slack",
    "mcp",  # MCP server management
    # Info commands
    "info",
    # Cross-project messaging
    "message",
}


def is_lightweight_command(command: str) -> bool:
    """Check if command should skip framework initialization.

    Args:
        command: The command name to check

    Returns:
        True if the command is lightweight (fast, no framework needed)
        False if the command requires full framework initialization

    Examples:
        >>> is_lightweight_command("config")
        True
        >>> is_lightweight_command("run")
        False
    """
    return command in LIGHTWEIGHT_COMMANDS
