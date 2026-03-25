#!/usr/bin/env python3
"""
Migration: Consolidate deprecated binary references in .mcp.json.

Migrates old standalone binary and python -m invocations to the unified
'claude-mpm mcp serve <name>' format.

Old format examples:
    "python -m claude_mpm.mcp.messaging_server"
        -> "claude-mpm mcp serve messaging"
    "mpm-session-server"
        -> "claude-mpm mcp serve session"
    "confluence-mcp"
        -> "claude-mpm mcp serve confluence"

This migration:
- Is non-destructive (creates .mcp.json.bak backup)
- Is idempotent (running twice has no additional effect)
- Preserves non-MPM servers (kuzu-memory, mcp-ticketer, etc.)
- Preserves 'uv run --directory' wrappers when present
- Supports --dry-run to preview changes

Version: 5.12.0
Date: 2026-03-25
"""

import json
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# ─── Migration patterns ──────────────────────────────────────────────────────

# Module-based invocations: the Python module path that appears in args
# after "python" "-m" in a uv/python invocation.
_MODULE_MIGRATIONS: dict[str, dict[str, str]] = {
    "claude_mpm.mcp.messaging_server": {
        "server_name": "messaging",
        "description": "MPM cross-project messaging",
    },
    "claude_mpm.mcp.slack_user_proxy_server": {
        "server_name": "slack-proxy",
        "description": "Slack user proxy for MPM",
    },
    "claude_mpm.mcp.session_server": {
        "server_name": "session",
        "description": "MPM session server (stdio)",
    },
    "claude_mpm.mcp.session_server_http": {
        "server_name": "session-http",
        "description": "MPM session server (HTTP)",
    },
    "claude_mpm.mcp.confluence_server": {
        "server_name": "confluence",
        "description": "Confluence MCP server",
    },
}

# Binary-based invocations: the old standalone command name
_BINARY_MIGRATIONS: dict[str, dict[str, str]] = {
    "mpm-session-server-http": {
        "server_name": "session-http",
        "description": "MPM session server (HTTP)",
    },
    "mpm-session-server": {
        "server_name": "session",
        "description": "MPM session server (stdio)",
    },
    "confluence-mcp": {
        "server_name": "confluence",
        "description": "Confluence MCP server",
    },
}


def _is_already_migrated(server_config: dict) -> bool:
    """Check if a server config already uses the new 'claude-mpm mcp serve' format.

    Args:
        server_config: The mcpServers entry dict.

    Returns:
        True if the config already uses the consolidated format.
    """
    args = server_config.get("args", [])

    # Direct invocation: command=claude-mpm, args contains ["mcp", "serve", ...]
    if server_config.get("command") == "claude-mpm":
        if len(args) >= 2 and args[0] == "mcp" and args[1] == "serve":
            return True

    # uv-wrapped invocation: command=uv, args contains [..., "claude-mpm", "mcp", "serve", ...]
    if server_config.get("command") == "uv":
        for i, arg in enumerate(args):
            if arg == "claude-mpm" and i + 2 < len(args):
                if args[i + 1] == "mcp" and args[i + 2] == "serve":
                    return True

    return False


def _find_module_in_args(args: list[str]) -> str | None:
    """Find a deprecated module path in the args list.

    Looks for patterns like:
        ["run", "--directory", "/some/path", "python", "-m", "claude_mpm.mcp.messaging_server"]

    Args:
        args: The args list from the server config.

    Returns:
        The module path if found, None otherwise.
    """
    for i, arg in enumerate(args):
        if arg == "-m" and i + 1 < len(args):
            module = args[i + 1]
            if module in _MODULE_MIGRATIONS:
                return module
        # Also check for the module appearing directly (without -m)
        if arg in _MODULE_MIGRATIONS:
            return arg
    return None


def _migrate_module_invocation(server_config: dict, module: str) -> dict:
    """Migrate a module-based invocation to consolidated format.

    Handles both:
    - uv run --directory /path python -m claude_mpm.mcp.X
    - python -m claude_mpm.mcp.X

    Preserves 'uv run --directory /path' wrapper if present.

    Args:
        server_config: The original server config dict.
        module: The deprecated module path found.

    Returns:
        Updated server config dict.
    """
    migration = _MODULE_MIGRATIONS[module]
    server_name = migration["server_name"]
    new_config = dict(server_config)
    args = list(server_config.get("args", []))

    if server_config.get("command") == "uv":
        # Preserve uv run --directory wrapper
        # Find the "python" or "-m" marker and replace from there
        # New pattern: uv run --directory /path claude-mpm mcp serve <name>
        new_args = []
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "python":
                # Replace python -m module with claude-mpm mcp serve <name>
                new_args.extend(["claude-mpm", "mcp", "serve", server_name])
                break
            if arg in _MODULE_MIGRATIONS:
                # Module appears directly (without python -m)
                new_args.extend(["claude-mpm", "mcp", "serve", server_name])
                break
            new_args.append(arg)
            i += 1
        new_config["args"] = new_args
    else:
        # Direct invocation: python -m module -> claude-mpm mcp serve <name>
        new_config["command"] = "claude-mpm"
        new_config["args"] = ["mcp", "serve", server_name]

    return new_config


def _migrate_binary_invocation(server_config: dict, binary: str) -> dict:
    """Migrate a binary-based invocation to consolidated format.

    Handles:
    - command: mpm-session-server -> command: claude-mpm, args: [mcp, serve, session]
    - command: uv, args: [run, ..., mpm-session-server] -> same with claude-mpm replacement

    Args:
        server_config: The original server config dict.
        binary: The deprecated binary name found.

    Returns:
        Updated server config dict.
    """
    migration = _BINARY_MIGRATIONS[binary]
    server_name = migration["server_name"]
    new_config = dict(server_config)

    if server_config.get("command") == binary:
        # Direct binary invocation
        new_config["command"] = "claude-mpm"
        old_args = list(server_config.get("args", []))
        new_config["args"] = ["mcp", "serve", server_name, *old_args]
    elif server_config.get("command") == "uv":
        # uv-wrapped binary invocation
        args = list(server_config.get("args", []))
        new_args = []
        for arg in args:
            if arg == binary:
                new_args.extend(["claude-mpm", "mcp", "serve", server_name])
            else:
                new_args.append(arg)
        new_config["args"] = new_args

    return new_config


def migrate_mcp_json(project_dir: Path, dry_run: bool = False) -> dict:
    """Migrate .mcp.json in the given project directory.

    Detects old binary/module invocations in .mcp.json server configs
    and migrates them to the consolidated 'claude-mpm mcp serve <name>'
    format.

    Args:
        project_dir: Path to the project directory containing .mcp.json.
        dry_run: If True, preview changes without writing.

    Returns:
        Dict with migration report:
            - migrated: list of (server_name, description) that were migrated
            - skipped: list of server names already in new format
            - unchanged: list of server names that are not MPM servers
            - errors: list of error messages
            - dry_run: whether this was a dry run
            - backup_path: path to backup file (if created)
    """
    result: dict = {
        "migrated": [],
        "skipped": [],
        "unchanged": [],
        "errors": [],
        "dry_run": dry_run,
        "backup_path": None,
    }

    mcp_json_path = project_dir / ".mcp.json"

    # Check if file exists
    if not mcp_json_path.exists():
        logger.debug("No .mcp.json found at %s", mcp_json_path)
        return result

    # Read and parse
    try:
        content = mcp_json_path.read_text(encoding="utf-8")
        data = json.loads(content)
    except json.JSONDecodeError as e:
        result["errors"].append(f"Malformed .mcp.json: {e}")
        return result
    except OSError as e:
        result["errors"].append(f"Cannot read .mcp.json: {e}")
        return result

    servers = data.get("mcpServers", {})
    if not servers:
        return result

    changed = False

    for server_name, server_config in list(servers.items()):
        if not isinstance(server_config, dict):
            continue

        # Skip already-migrated entries
        if _is_already_migrated(server_config):
            result["skipped"].append(server_name)
            continue

        # Check for module-based invocations
        args = server_config.get("args", [])
        module = _find_module_in_args(args)
        if module:
            migration_info = _MODULE_MIGRATIONS[module]
            new_config = _migrate_module_invocation(server_config, module)
            servers[server_name] = new_config
            result["migrated"].append((server_name, migration_info["description"]))
            changed = True
            continue

        # Check for binary-based invocations
        command = server_config.get("command", "")

        # Direct binary command
        if command in _BINARY_MIGRATIONS:
            migration_info = _BINARY_MIGRATIONS[command]
            new_config = _migrate_binary_invocation(server_config, command)
            servers[server_name] = new_config
            result["migrated"].append((server_name, migration_info["description"]))
            changed = True
            continue

        # Binary in uv args
        if command == "uv":
            found_binary = None
            for arg in args:
                if arg in _BINARY_MIGRATIONS:
                    found_binary = arg
                    break
            if found_binary:
                migration_info = _BINARY_MIGRATIONS[found_binary]
                new_config = _migrate_binary_invocation(server_config, found_binary)
                servers[server_name] = new_config
                result["migrated"].append((server_name, migration_info["description"]))
                changed = True
                continue

        # Not an MPM server - leave untouched
        result["unchanged"].append(server_name)

    # Write changes
    if changed and not dry_run:
        # Create backup
        backup_path = mcp_json_path.with_suffix(".json.bak")
        try:
            shutil.copy2(str(mcp_json_path), str(backup_path))
            result["backup_path"] = str(backup_path)
        except OSError as e:
            result["errors"].append(f"Failed to create backup: {e}")
            return result

        # Write updated file
        try:
            mcp_json_path.write_text(
                json.dumps(data, indent=2) + "\n", encoding="utf-8"
            )
        except OSError as e:
            result["errors"].append(f"Failed to write .mcp.json: {e}")
            # Restore from backup
            try:
                shutil.copy2(str(backup_path), str(mcp_json_path))
            except OSError:
                result["errors"].append(
                    "CRITICAL: Failed to restore backup after write failure"
                )

    return result


def check_needs_migration(project_dir: Path | None = None) -> bool:
    """Check if any .mcp.json files need binary consolidation migration.

    Scans the current working directory for .mcp.json with old-format
    server invocations.

    Args:
        project_dir: Directory to check. Defaults to cwd.

    Returns:
        True if migration is needed.
    """
    if project_dir is None:
        project_dir = Path.cwd()

    mcp_json_path = project_dir / ".mcp.json"
    if not mcp_json_path.exists():
        return False

    try:
        data = json.loads(mcp_json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False

    servers = data.get("mcpServers", {})
    for server_config in servers.values():
        if not isinstance(server_config, dict):
            continue

        if _is_already_migrated(server_config):
            continue

        # Check for module patterns
        args = server_config.get("args", [])
        if _find_module_in_args(args):
            return True

        # Check for binary patterns
        command = server_config.get("command", "")
        if command in _BINARY_MIGRATIONS:
            return True

        if command == "uv":
            for arg in args:
                if arg in _BINARY_MIGRATIONS:
                    return True

    return False


def run_migration(dry_run: bool = False) -> bool:
    """Run the binary consolidation migration on current directory.

    This is the entry point called by the migration registry.

    Args:
        dry_run: If True, only preview changes.

    Returns:
        True if migration succeeded (or nothing needed migrating).
    """
    project_dir = Path.cwd()
    result = migrate_mcp_json(project_dir, dry_run=dry_run)

    if result["migrated"]:
        for name, desc in result["migrated"]:
            action = "[DRY RUN] Would migrate" if dry_run else "Migrated"
            print(f"   {action} '{name}' -> claude-mpm mcp serve ({desc})")
        if result.get("backup_path"):
            print(f"   Backup: {result['backup_path']}")
    else:
        print("   No old-format MCP server references found")

    if result["errors"]:
        for error in result["errors"]:
            print(f"   Error: {error}")
        return False

    print("   Migration complete")
    return True
