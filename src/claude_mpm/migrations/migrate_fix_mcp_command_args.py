"""Fix MCP server configs where ``command`` contains spaces.

Bug: ``claude mcp add <name> "<command> <args>"`` stores the entire string as
``command`` with empty ``args``, instead of splitting on whitespace into
``command: "binary"`` + ``args: ["arg1", "arg2"]``. Claude Code then fails to
spawn the MCP server because it tries to exec the full string as a single
binary path.

This migration scans known config locations for ``mcpServers`` entries whose
``command`` field contains a space, splits the first token off as the actual
binary, and prepends any remaining tokens to the existing ``args`` list.

Scanned locations (each optional — missing files are skipped):

* ``./.mcp.json`` (project-scoped)
* ``./.claude/settings.json`` and ``./.claude/settings.local.json``
* ``~/.claude/.mcp.json``
* ``~/.claude/settings.json``

Design constraints:

* **Idempotent**: a fixed entry has no space in ``command``, so re-running is
  a no-op.
* **Graceful**: malformed JSON or unreadable files are skipped with a warning
  rather than aborting the whole migration.
* **Conservative writes**: the file is only rewritten when at least one entry
  in it was actually modified.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def fix_command_args(server_config: dict[str, Any]) -> bool:
    """Fix a single server config entry in place.

    If ``command`` contains a space, split on whitespace: first token becomes
    the new ``command``, remaining tokens are prepended to any existing
    ``args`` list.

    Args:
        server_config: A single entry from an ``mcpServers`` mapping.

    Returns:
        True if the entry was modified, False otherwise.
    """
    command = server_config.get("command")
    if not isinstance(command, str) or " " not in command:
        return False

    parts = command.split()
    if not parts:
        return False

    existing_args = server_config.get("args")
    if not isinstance(existing_args, list):
        existing_args = []

    server_config["command"] = parts[0]
    server_config["args"] = parts[1:] + existing_args
    return True


def _fix_mcp_servers(servers: Any) -> int:
    """Apply :func:`fix_command_args` to every entry in an ``mcpServers`` map.

    Returns the number of entries modified. A non-dict ``servers`` value (or
    a non-dict entry within it) is silently skipped — we don't want a single
    weird entry to abort the whole migration.
    """
    if not isinstance(servers, dict):
        return 0

    fixed = 0
    for name, entry in servers.items():
        if not isinstance(entry, dict):
            continue
        if fix_command_args(entry):
            fixed += 1
            logger.info(
                "Fixed MCP server '%s': split command into command + args",
                name,
            )
    return fixed


def _process_file(path: Path) -> bool:
    """Load ``path``, fix any broken ``mcpServers`` entries, write back.

    Returns True iff the file was modified (and therefore rewritten). Missing
    files, non-JSON files, and files without ``mcpServers`` are all no-ops.
    """
    if not path.exists():
        return False

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Skipping %s: cannot parse JSON (%s)", path, exc)
        return False

    if not isinstance(data, dict):
        return False

    servers = data.get("mcpServers")
    fixed = _fix_mcp_servers(servers)
    if not fixed:
        return False

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    except OSError as exc:
        logger.warning("Failed to write %s: %s", path, exc)
        return False

    logger.info(
        "Fixed %d MCP server entr%s in %s", fixed, "y" if fixed == 1 else "ies", path
    )
    return True


def _candidate_paths(project_dir: Path) -> list[Path]:
    """Return the set of config files we should scan.

    Order doesn't matter — each file is independent — but we keep
    project-level files first for log readability.
    """
    home = Path.home()
    return [
        project_dir / ".mcp.json",
        project_dir / ".claude" / "settings.json",
        project_dir / ".claude" / "settings.local.json",
        home / ".claude" / ".mcp.json",
        home / ".claude" / "settings.json",
    ]


def run_migration(project_dir: Path | None = None) -> bool:
    """Scan known config locations and fix broken ``mcpServers`` entries.

    Args:
        project_dir: Project root to scan (defaults to CWD). Tests inject a
            temp directory here.

    Returns:
        True if any file was modified, False if everything was already valid
        (or no relevant files existed).
    """
    project_dir = project_dir or Path.cwd()

    any_changed = False
    for path in _candidate_paths(project_dir):
        if _process_file(path):
            any_changed = True

    return any_changed
