"""Rename stale ``trusty-analyzer`` MCP entry to ``trusty-analyze``.

WHAT: Removes the broken ``trusty-analyzer`` MCP server entry that older
    versions of claude-mpm wrote, replacing it with the canonical
    ``trusty-analyze`` entry (command ``trusty-analyze``, args ``["mcp"]``).
    Also unloads and removes the old ``com.bobmatnyc.trusty-analyzer`` launchd
    plist when present (macOS only).

WHY: PR #782 renamed the binary and all wiring from ``trusty-analyzer`` to
    ``trusty-analyze``.  Existing users who had already run
    ``claude-mpm setup trusty-analyze`` before the rename (when the old binary
    name was still ``trusty-analyzer``) are left with a broken MCP entry that
    tries to execute a non-existent binary, and a launchd plist that keeps
    respawning it.  This migration repairs both without user intervention.

Ordering relative to ``migrate_fix_trusty_memory_bridge``
----------------------------------------------------------
The bridge-fix migration (version 6.5.0) explicitly preserves any
``trusty-analyzer`` entry (it only touches ``trusty-memory`` entries).
This migration (6.5.34) runs *after* the bridge-fix and converts the
preserved-but-now-stale ``trusty-analyzer`` entry.  The two migrations are
therefore safe to run in sequence.

Scanned locations (mirrors ``migrate_fix_trusty_memory_bridge``):

* ``./.mcp.json`` (project-scoped)
* ``./.claude/settings.json`` and ``./.claude/settings.local.json``
* ``~/.claude/.mcp.json``
* ``~/.claude/settings.json``

Design constraints:

* **Idempotent**: if ``trusty-analyzer`` is absent (or already removed) the
  migration is a no-op.  If ``trusty-analyze`` already exists and
  ``trusty-analyzer`` is absent the migration is a no-op.
* **Merge-safe**: if both ``trusty-analyzer`` AND ``trusty-analyze`` already
  exist, the stale ``trusty-analyzer`` key is dropped (no duplicate).
* **Graceful**: malformed JSON, unreadable files, or subprocess errors are
  logged as warnings and never raise.
* **macOS-only launchd cleanup**: the plist removal block is guarded by
  ``sys.platform == "darwin"`` so the migration is a no-op on Linux/Windows.

References
----------
SPEC-INTEGRATIONS-09~1 : docs/specs/integrations.md#SPEC-INTEGRATIONS-09~1
"""

from __future__ import annotations

import json
import logging
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_OLD_KEY = "trusty-analyzer"
_NEW_KEY = "trusty-analyze"
_CANONICAL_ENTRY: dict[str, Any] = {
    "type": "stdio",
    "command": "trusty-analyze",
    "args": ["mcp"],
}
_OLD_PLIST_LABEL = "com.bobmatnyc.trusty-analyzer"


# ---------------------------------------------------------------------------
# MCP config helpers
# ---------------------------------------------------------------------------


def _fix_servers(servers: Any) -> bool:
    """Rename or drop the stale ``trusty-analyzer`` key in a ``mcpServers`` mapping.

    WHAT: Mutates *servers* in-place.  Returns True when a change was made.
    WHY: In-place mutation avoids constructing an entirely new dict and keeps
    key order stable for the rest of the entries.

    Logic:
    * Neither key present → no-op (return False).
    * Only ``trusty-analyzer`` present → rename to ``trusty-analyze``,
      overwrite command/args with canonical values.
    * Both present → drop ``trusty-analyzer`` (``trusty-analyze`` already
      exists, don't duplicate).
    * Only ``trusty-analyze`` present → no-op.
    """
    if not isinstance(servers, dict):
        return False

    has_old = _OLD_KEY in servers
    has_new = _NEW_KEY in servers

    if not has_old:
        return False

    if has_new:
        # Both exist: the new entry is already there, just drop the stale old one.
        del servers[_OLD_KEY]
        logger.info(
            "Dropped stale '%s' entry (canonical '%s' already present)",
            _OLD_KEY,
            _NEW_KEY,
        )
    else:
        # Only old exists: remove it and insert a fresh canonical entry.
        # We do NOT inherit unknown fields (e.g. a stale ``env`` pointing at the
        # old binary) from the old dict — build clean from _CANONICAL_ENTRY.
        servers.pop(_OLD_KEY)
        servers[_NEW_KEY] = {
            "type": _CANONICAL_ENTRY["type"],
            "command": _CANONICAL_ENTRY["command"],
            "args": list(_CANONICAL_ENTRY["args"]),
        }
        logger.info(
            "Renamed MCP server '%s' → '%s' with canonical command/args",
            _OLD_KEY,
            _NEW_KEY,
        )

    return True


def _process_file(path: Path) -> bool:
    """Load *path*, fix stale trusty-analyzer entry, write back if changed.

    Returns True iff the file was modified.  Missing / unreadable / malformed
    files are silently skipped.
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
    if not _fix_servers(servers):
        return False

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    except OSError as exc:
        logger.warning("Failed to write %s: %s", path, exc)
        return False

    logger.info("Updated %s: trusty-analyzer → trusty-analyze", path)
    return True


def _candidate_paths(project_dir: Path) -> list[Path]:
    """Return config file candidates to scan.

    Mirrors ``migrate_fix_trusty_memory_bridge._candidate_paths``.
    """
    home = Path.home()
    return [
        project_dir / ".mcp.json",
        project_dir / ".claude" / "settings.json",
        project_dir / ".claude" / "settings.local.json",
        home / ".claude" / ".mcp.json",
        home / ".claude" / "settings.json",
    ]


# ---------------------------------------------------------------------------
# launchd plist cleanup (macOS only)
# ---------------------------------------------------------------------------


def _cleanup_launchd_plist() -> bool:
    """Unload and remove the old ``com.bobmatnyc.trusty-analyzer`` launchd plist.

    WHAT: Returns True iff the plist was found and at least an unload or removal
    was attempted (i.e. something was actually cleaned up).  Returns False when
    the plist does not exist or on non-macOS platforms (pure no-op).
    WHY: The old plist keeps trying to start the absent ``trusty-analyzer``
    binary, generating repeated spawn-failure log noise and consuming launchd
    resources.  The bool return lets ``run_migration`` honour its documented
    contract (True iff anything was modified *or* cleaned up).

    Guard patterns (mirrors project hook/migration stability rules):
    * ``sys.platform`` check so the whole block is skipped on non-macOS.
    * Each subprocess call gets a ``timeout`` and ``check=False`` — errors are
      logged as warnings, never raised.
    * File removal is guarded by ``Path.exists()`` before ``Path.unlink()``.
    """
    if sys.platform != "darwin":
        return False

    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{_OLD_PLIST_LABEL}.plist"
    if not plist_path.exists():
        return False

    logger.info("Found stale launchd plist: %s — removing", plist_path)

    # Try ``launchctl bootout`` (macOS 10.10+), fall back to ``unload``.
    for cmd in (
        ["launchctl", "bootout", f"gui/{_get_uid()}", str(plist_path)],
        ["launchctl", "unload", str(plist_path)],
    ):
        try:
            result = subprocess.run(  # nosec B603 B607
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                logger.info("Unloaded launchd agent: %s", _OLD_PLIST_LABEL)
                break
            logger.debug(
                "launchctl cmd %s exited %d: %s",
                cmd[1],
                result.returncode,
                result.stderr.strip(),
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("launchctl call failed (%s): %s", cmd[1], exc)

    try:
        plist_path.unlink(missing_ok=True)
        logger.info("Removed plist: %s", plist_path)
    except OSError as exc:
        logger.warning("Could not remove plist %s: %s", plist_path, exc)

    # We found and acted on the plist (even if launchctl or unlink had errors).
    return True


def _get_uid() -> int:
    """Return the current process UID (POSIX).  Returns 0 on non-POSIX."""
    try:
        import os

        return os.getuid()
    except AttributeError:
        return 0


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_migration(project_dir: Path | None = None) -> bool:
    """Scan config files and repair stale ``trusty-analyzer`` MCP entries.

    Args:
        project_dir: Project root to scan (defaults to ``Path.cwd()``).
            Tests inject a temp directory here to keep the scan hermetic.

    Returns:
        True if any MCP config file was modified OR if the launchd plist was
        cleaned up.  False when everything was already up-to-date (or no
        relevant files existed).
    """
    project_dir = project_dir or Path.cwd()

    any_changed = False
    for path in _candidate_paths(project_dir):
        if _process_file(path):
            any_changed = True

    plist_cleaned = _cleanup_launchd_plist()

    return any_changed or plist_cleaned
