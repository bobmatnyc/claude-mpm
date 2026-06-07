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
    "settings",  # Settings file management
    "gh",  # GitHub multi-account management
    # Diagnostics and tools
    "tools",
    "debug",
    "doctor",
    "diagnose",
    "check-health",
    # Installation management
    "install",
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
    # Migration management
    "migrate",
    # Message queue management
    "queue",
    # Statusline maintenance
    "update-statusline",
}

# Read-only subcommands that do NOT need the project workspace directory.
# Keyed by parent command name, value is the set of read-only subcommand values.
# Subcommands NOT listed here are treated as workspace-needing (safe default).
_READ_ONLY_SUBCOMMANDS: dict[str, set[str]] = {
    # monitor status/port only read state; start/stop/restart need the workspace
    "monitor": {"status", "port"},
    # agents list/view are read-only; deploy/force-deploy/fix/clean need workspace
    "agents": {"list", "view"},
    # skills list is read-only; deploy needs workspace
    "skills": {"list"},
    # memory status/show/view are read-only; init/add/build/clean need workspace
    "memory": {"status", "show", "view", "optimize", "cross-ref", "route"},
    # manifest validate/show are read-only; init needs workspace
    "manifest": {"validate", "show"},
    # dashboard status/open are read-only; start/stop need workspace
    "dashboard": {"status", "open"},
}

# Subcommand dest attribute names used by argparse for each parent command.
# These are the names argparse stores the chosen subcommand in (e.g. args.monitor_command).
_SUBCOMMAND_DEST: dict[str, str] = {
    "monitor": "monitor_command",
    "agents": "agents_command",
    "skills": "skills_command",
    "memory": "memory_command",
    "manifest": "manifest_command",
    "dashboard": "dashboard_command",
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


def needs_project_workspace(args) -> bool:
    """Return True if the given parsed args require the project-level .claude-mpm/ dir.

    WHAT: Gate function that decides whether ``initialize_project_directory()``
    should run for the current invocation.

    WHY: The framework previously created a ``.claude-mpm/`` directory in the
    current working directory on EVERY CLI invocation, including read-only
    commands such as ``doctor``, ``monitor status``, and ``agents list``.  This
    function allows the project-level init to be skipped for commands that only
    read cached data from ``~/.claude-mpm/`` and never write to the project dir.

    Classification rules (applied in order):
    1. ``--version`` / ``--help`` flags (no ``args.command`` set): NO workspace.
    2. Lightweight commands (``LIGHTWEIGHT_COMMANDS``): NO workspace.
    3. Commands with read-only subcommands (``_READ_ONLY_SUBCOMMANDS``): only if
       the chosen subcommand is in the read-only set.  Unknown/missing subcommands
       ERR TOWARD creating (workspace=True) per the bias rule.
    4. All other commands: YES workspace.

    Bias rule: when in doubt, return True (create the dir).  A false positive is
    a harmless stray directory; a false negative could break a workspace command.

    Args:
        args: Parsed argparse namespace (may lack ``command`` attribute for
              bare ``--version`` / ``--help`` invocations).

    Returns:
        True  — run ``initialize_project_directory()`` (workspace command).
        False — skip project-dir init (read-only / informational command).
    """
    command = getattr(args, "command", None)

    # Rule 1: bare --version / --help — no command attribute set
    if command is None:
        return False

    # Rule 2: lightweight commands never need the project workspace
    if is_lightweight_command(command):
        return False

    # Rule 3: commands that have mixed read-only / workspace subcommands
    if command in _READ_ONLY_SUBCOMMANDS:
        dest_attr = _SUBCOMMAND_DEST.get(command)
        subcommand = getattr(args, dest_attr, None) if dest_attr else None
        if subcommand is None:
            # No subcommand given — bias toward creating (True)
            return True
        # If the subcommand is in the read-only set, skip project init
        return subcommand not in _READ_ONLY_SUBCOMMANDS[command]

    # Rule 4: everything else needs the workspace
    return True
