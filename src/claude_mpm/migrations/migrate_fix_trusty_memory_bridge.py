"""Repair broken trusty-memory MCP entries to use the bridge binary.

Bug (#567): earlier versions of claude-mpm wrote a broken trusty-memory MCP
server entry of the form ``command="trusty-memory", args=["serve", "--mcp"]``
(and variant forms such as ``args=["serve", "--palace", "claude-mpm", "--mcp"]``).
``trusty-memory serve`` starts the HTTP daemon, not an MCP stdio server, so
Claude Code could never speak MCP to it. The correct invocation is the
dedicated bridge binary ``trusty-memory-mcp-bridge`` (no args), which ships
alongside ``trusty-memory``.

This migration scans the same config locations as
:mod:`migrate_fix_mcp_command_args` and rewrites any entry where
``command == "trusty-memory"`` AND ``args`` contains ``"--mcp"`` to
``command="trusty-memory-mcp-bridge", args=[]``.

Scanned locations (each optional — missing files are skipped):

* ``./.mcp.json`` (project-scoped)
* ``./.claude/settings.json`` and ``./.claude/settings.local.json``
* ``~/.claude/.mcp.json``
* ``~/.claude/settings.json``

Design constraints:

* **Match on presence of ``--mcp``**, not exact-array equality, so variant
  forms (extra ``--palace`` flags, etc.) are also repaired.
* **Idempotent**: an already-bridged entry has ``command`` of
  ``trusty-memory-mcp-bridge`` (not ``trusty-memory``), so re-running is a
  no-op. An absent entry is also a no-op.
* **Targeted**: only ``trusty-memory`` entries are touched. ``trusty-search``
  (``args=["serve"]``) and ``trusty-analyzer`` (``args=["mcp"]``) are left
  alone — they have no ``--mcp`` flag and a different ``command``.
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


def fix_trusty_memory_entry(server_config: dict[str, Any]) -> bool:
    """Fix a single broken trusty-memory entry in place.

    Rewrites entries where ``command == "trusty-memory"`` and ``args``
    contains ``"--mcp"`` to ``command="trusty-memory-mcp-bridge", args=[]``.

    Args:
        server_config: A single entry from an ``mcpServers`` mapping.

    Returns:
        True if the entry was modified, False otherwise.
    """
    if server_config.get("command") != "trusty-memory":
        return False

    args = server_config.get("args")
    if not isinstance(args, list) or "--mcp" not in args:
        return False

    server_config["command"] = "trusty-memory-mcp-bridge"
    server_config["args"] = []
    return True


def _fix_mcp_servers(servers: Any) -> int:
    """Apply :func:`fix_trusty_memory_entry` to every ``mcpServers`` entry.

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
        if fix_trusty_memory_entry(entry):
            fixed += 1
            logger.info(
                "Fixed MCP server '%s': rewired to trusty-memory-mcp-bridge",
                name,
            )
    return fixed


def _process_file(path: Path) -> bool:
    """Load ``path``, fix any broken trusty-memory entries, write back.

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
        "Fixed %d trusty-memory entr%s in %s",
        fixed,
        "y" if fixed == 1 else "ies",
        path,
    )
    return True


def _candidate_paths(project_dir: Path) -> list[Path]:
    """Return the set of config files we should scan.

    Mirrors :func:`migrate_fix_mcp_command_args._candidate_paths`. Order
    doesn't matter — each file is independent — but we keep project-level
    files first for log readability.
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
    """Scan known config locations and repair broken trusty-memory entries.

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
