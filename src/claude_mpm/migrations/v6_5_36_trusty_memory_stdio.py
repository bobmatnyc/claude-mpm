"""Rewrite stale trusty-memory bridge entries to the canonical stdio form.

WHAT: Scans the user's MCP config file(s) for ``trusty-memory`` entries that
    still use the old ``trusty-memory-mcp-bridge`` command (the bridge was
    broken in v0.15.2 when the daemon stopped binding its UDS socket).  Rewrites
    any such entry to the canonical direct-stdio form
    ``{"type":"stdio","command":"trusty-memory","args":["serve","--stdio"]}``.

WHY: Starting with claude-mpm 6.5.36, the framework default for trusty-memory
    switches from the bridge architecture to ``trusty-memory serve --stdio``
    (direct stdio mode, no daemon/socket required, spawned per-session by
    Claude Code).  Existing projects that were configured before this release
    will have a stale ``command: trusty-memory-mcp-bridge`` entry that no
    longer works.  This migration repairs them automatically so users do not
    have to re-run ``claude-mpm setup trusty-memory``.

Idempotency:
    * If the entry already uses the canonical stdio command — no change.
    * If the entry is absent — no change.
    * If both old and new keys coexist (impossible in practice but guarded) —
      only the new key is preserved.

Scanned locations (mirrors ``v6_5_34_rename_trusty_analyzer``):

* ``./.mcp.json`` (project-scoped)
* ``./.claude/settings.json`` and ``./.claude/settings.local.json``
* ``~/.claude/.mcp.json``
* ``~/.claude/settings.json``

Design constraints:

* **Safe writes**: uses :func:`_process_file` (load → mutate in-place →
  write) with per-file error handling; a write failure for one file never
  blocks the others.
* **No rollback needed**: each mutation is a single key-value replacement that
  cannot lose data (the old entry is always superseded by an equivalent one).
* **Never raises**: all errors are logged at ``warning`` level and swallowed.
* **Hermetic**: no subprocess calls, no network I/O, no binary detection.

References
----------
SPEC-INTEGRATIONS-09~1 : docs/specs/integrations.md#SPEC-INTEGRATIONS-09~1
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# The old bridge command that this migration replaces.
_OLD_COMMAND = "trusty-memory-mcp-bridge"

# Canonical stdio entry for trusty-memory (6.5.36+).
_CANONICAL_ENTRY: dict[str, Any] = {
    "type": "stdio",
    "command": "trusty-memory",
    "args": ["serve", "--stdio"],
}

_SERVICE_KEY = "trusty-memory"  # pragma: allowlist secret


# ---------------------------------------------------------------------------
# Per-file helpers
# ---------------------------------------------------------------------------


def _needs_rewrite(entry: Any) -> bool:
    """Return True iff ``entry`` is an old bridge-form trusty-memory config.

    WHAT: Detects the stale ``command: trusty-memory-mcp-bridge`` form
    (typically ``args: []``).  Returns False for any other shape (already
    canonical, unexpected type, etc.) so the migration never touches entries
    it does not recognise.

    WHY: Detecting by command name is robust against unknown args or extra
    fields that earlier versions may have written.
    """
    if not isinstance(entry, dict):
        return False
    return entry.get("command") == _OLD_COMMAND


def _fix_servers(servers: Any) -> bool:
    """Rewrite the stale trusty-memory entry in ``servers`` if present.

    WHAT: Mutates *servers* in-place.  Returns True when a change was made.
    WHY: In-place mutation keeps key order stable for the rest of the entries
    and avoids constructing an entirely new dict.

    Logic:
    * ``trusty-memory`` absent → no-op (return False).
    * ``trusty-memory`` present with old bridge command → overwrite with
      canonical entry (return True).
    * ``trusty-memory`` present with canonical or unrecognised command →
      no-op (return False).
    """
    if not isinstance(servers, dict):
        return False

    entry = servers.get(_SERVICE_KEY)
    if not _needs_rewrite(entry):
        return False

    # Build a fresh canonical entry — do NOT inherit stale fields from the
    # old bridge entry (e.g. a mismatched ``type`` or unexpected ``env``).
    servers[_SERVICE_KEY] = {
        "type": _CANONICAL_ENTRY["type"],
        "command": _CANONICAL_ENTRY["command"],
        "args": list(_CANONICAL_ENTRY["args"]),
    }
    logger.info(
        "Rewrote trusty-memory MCP entry: %s → %s %s",
        _OLD_COMMAND,
        _CANONICAL_ENTRY["command"],
        _CANONICAL_ENTRY["args"],
    )
    return True


def _process_file(path: Path) -> bool:
    """Load ``path``, fix stale trusty-memory entry, write back if changed.

    WHAT: Returns True iff the file was modified.  Missing, unreadable, or
    malformed files are silently skipped.
    WHY: Per-file error isolation — one bad file never blocks the others.
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

    logger.info(
        "Updated %s: trusty-memory-mcp-bridge → trusty-memory serve --stdio", path
    )
    return True


def _candidate_paths(project_dir: Path) -> list[Path]:
    """Return config file candidates to scan.

    WHAT: Mirrors ``v6_5_34_rename_trusty_analyzer._candidate_paths``.
    WHY: Covers project-scoped, settings, and user-scope config locations
    that could contain a stale trusty-memory entry.
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
# Public entry point
# ---------------------------------------------------------------------------


def run_migration(project_dir: Path | None = None) -> bool:
    """Scan config files and rewrite stale trusty-memory bridge entries.

    WHAT: Iterates over the candidate config paths for ``project_dir`` and
    rewrites any ``trusty-memory`` entry whose command is
    ``trusty-memory-mcp-bridge`` to the canonical stdio form
    ``{"type":"stdio","command":"trusty-memory","args":["serve","--stdio"]}``.

    WHY: trusty-memory's daemon+bridge architecture is broken in v0.15.2+;
    the fix is to use direct stdio mode.  This migration auto-repairs existing
    projects without requiring user intervention.

    Args:
        project_dir: Project root to scan (defaults to ``Path.cwd()``).
            Tests inject a temp directory here to keep the scan hermetic.

    Returns:
        True if any MCP config file was modified.  False when everything was
        already up-to-date (or no relevant files existed).  Never raises.
    """
    project_dir = project_dir or Path.cwd()

    any_changed = False
    for path in _candidate_paths(project_dir):
        try:
            if _process_file(path):
                any_changed = True
        except Exception as exc:
            logger.warning(
                "trusty-memory stdio migration: unexpected error for %s: %s", path, exc
            )

    return any_changed
