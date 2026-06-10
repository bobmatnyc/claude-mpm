"""
Migration to deduplicate claude-hook registrations in .claude/settings.json.

WHAT: Collapses duplicate MPM hook entries that differ only in ``timeout``
      into a single canonical entry per event, keeping the higher timeout.

WHY: Two independent installers (HookInstaller and HookInstallerService)
     wrote hook entries with different timeouts (15 vs 60) to the same file.
     The dedup key in the v6_3_19 migration excluded ``timeout``, so entries
     differing only in timeout were both kept, causing each event to fire
     twice (issue #677).

This migration:
1. Reads .claude/settings.json (and settings.local.json if present) for the
   current project.  The search starts from ``Path.cwd()`` and walks upward
   through parent directories until it finds a ``.claude`` directory (or
   reaches the filesystem root), so it works correctly even when invoked
   from a subdirectory.
2. For each hook event, finds all MPM entries (``_mpm: true`` or a legacy
   command-string match).  When multiple MPM entries share the same
   ``command`` + ``args`` fingerprint (i.e. are duplicates differing only in
   ``timeout`` or other metadata), it collapses them into a single entry
   using the CANONICAL timeout for that event.
3. Preserves non-MPM / user hook entries untouched.
4. Is idempotent (second run is a no-op) and fail-open (wraps I/O in
   try/except — a failure logs a warning but does not crash startup).
5. Rotates backups: keeps only the 5 most-recent MPM backup files per
   settings file; older ones are deleted (fail-open on cleanup errors).

References
----------
SPEC-HOOKS-04~1 : docs/specs/hooks.md#SPEC-HOOKS-04~1
"""

import json
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from claude_mpm.hooks.timeout_constants import (
    CANONICAL_HOOK_TIMEOUTS as _CANONICAL_TIMEOUTS,  # noqa: F401 — re-exported under the _CANONICAL_TIMEOUTS alias so tests/migrations/test_dedup_hook_registrations.py::test_canonical_timeout_map_consistency can assert object identity with the shared module
    DEFAULT_HOOK_TIMEOUT as _DEFAULT_TIMEOUT,  # noqa: F401 — re-exported under the _DEFAULT_TIMEOUT alias so the same consistency test can assert value equality
    canonical_timeout as _canonical_timeout,
)

logger = logging.getLogger(__name__)

# Substrings used to recognise a legacy MPM hook entry (written before the
# ``_mpm`` marker was introduced — mirrors the v6_3_19 migration list).
_MPM_HOOK_MARKERS: tuple[str, ...] = (
    "claude-hook-fast",
    "claude-hook-handler",
    "claude-hook",
    "message_check_hook",
    "tool_failure_hook",
    "claude_mpm",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_mpm_hook_command(hook_cmd: dict[str, Any]) -> bool:
    """Return True if a single hook command dict belongs to claude-mpm."""
    if not isinstance(hook_cmd, dict):
        return False
    if hook_cmd.get("type") != "command":
        return False
    # Primary: explicit marker.
    if hook_cmd.get("_mpm") is True:
        return True
    # Legacy fallback: substring matching.
    command = str(hook_cmd.get("command", ""))
    if any(marker in command for marker in _MPM_HOOK_MARKERS):
        return True
    args = hook_cmd.get("args") or []
    if isinstance(args, list):
        for arg in args:
            if isinstance(arg, str) and any(
                marker in arg for marker in _MPM_HOOK_MARKERS
            ):
                return True
    return False


def _hook_fingerprint(hook_cmd: dict[str, Any]) -> tuple[str, str]:
    """Build a fingerprint that ignores ``timeout`` (and other metadata).

    Two MPM hook entries are considered *duplicates* if they have the same
    ``(command, args-json)`` fingerprint — i.e. they call the same binary
    with the same arguments and differ only in ``timeout`` or other flags.
    """
    command = str(hook_cmd.get("command", ""))
    args = hook_cmd.get("args") or []
    try:
        args_repr = json.dumps(args, sort_keys=True)
    except (TypeError, ValueError):
        args_repr = str(args)
    return (command, args_repr)


def _dedup_hooks_in_block(
    block_hooks: list[dict[str, Any]], event_type: str
) -> list[dict[str, Any]]:
    """Collapse duplicate MPM hook commands within a single matcher block.

    Non-MPM hooks are kept as-is. For MPM hooks sharing the same fingerprint,
    a single entry is emitted with:
    - ``command`` and ``args`` from the first occurrence
    - ``timeout`` = canonical_timeout(event_type) — the shared authoritative value,
      matching what the installer writes so migration and installer converge.
    - ``_mpm = True``

    Args:
        block_hooks: The list of hook command dicts for one matcher block.
        event_type: The event name (e.g. "PreToolUse") for timeout lookup.

    Returns:
        Deduplicated list; order of first-seen MPM entries preserved.
    """
    seen_fingerprints: dict[tuple[str, str], dict[str, Any]] = {}
    result: list[dict[str, Any]] = []

    for hook in block_hooks:
        if not _is_mpm_hook_command(hook):
            result.append(hook)
            continue

        fp = _hook_fingerprint(hook)
        if fp not in seen_fingerprints:
            # First occurrence: store a clean copy and emit it in-place.
            # Always use the canonical timeout so migration and installer agree.
            canonical: dict[str, Any] = {
                "type": "command",
                "command": fp[0],
                "_mpm": True,
                "timeout": _canonical_timeout(event_type),
            }
            # Preserve args only when non-empty.
            args = hook.get("args") or []
            if args:
                canonical["args"] = list(args)
            # Preserve optional sub-service marker if present.
            if "_mpm_service" in hook:
                canonical["_mpm_service"] = hook["_mpm_service"]
            seen_fingerprints[fp] = canonical
            result.append(canonical)
        else:
            # Duplicate: canonical timeout is already set; just skip entry.
            pass

    return result


def _dedup_settings(settings: dict[str, Any]) -> int:
    """Deduplicate MPM hook entries in a parsed settings dict.

    Mutates ``settings`` in-place.

    Returns:
        Total number of duplicate entries removed.
    """
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return 0

    total_removed = 0

    for event_type, matcher_blocks in hooks.items():
        if not isinstance(matcher_blocks, list):
            continue

        for block in matcher_blocks:
            if not isinstance(block, dict):
                continue
            block_hooks = block.get("hooks")
            if not isinstance(block_hooks, list):
                continue

            deduped = _dedup_hooks_in_block(block_hooks, event_type)
            removed = len(block_hooks) - len(deduped)
            if removed:
                block["hooks"] = deduped
                total_removed += removed

    return total_removed


def _find_project_claude_dir(start: Path) -> Path | None:
    """Walk upward from ``start`` to find the nearest ``.claude`` directory.

    Stops when it finds a ``.claude`` directory or a project-root marker
    (``.git``, ``pyproject.toml``, ``setup.py``), or when it reaches the
    filesystem root.  Returns the path to the ``.claude`` directory if found,
    otherwise ``None``.

    Known limitation: a ``.claude`` directory located *above* the nearest
    ``.git`` / ``pyproject.toml`` boundary will not be found.  This is
    acceptable common-case behaviour — if you run from inside a nested project,
    the parent project's ``.claude`` is intentionally out of scope.

    This is fail-open: any unexpected error returns ``None``.
    """
    try:
        current = start.resolve()
        while True:
            claude_dir = current / ".claude"
            if claude_dir.is_dir():
                return claude_dir
            # Stop at well-known project-root markers so we don't walk too far.
            # Note: .claude is checked BEFORE the markers at each level, so a
            # .claude directory co-located with .git (the common case) is found.
            for marker in (".git", "pyproject.toml", "setup.py"):
                if (current / marker).exists():
                    return None
            parent = current.parent
            if parent == current:
                # Reached the filesystem root.
                return None
            current = parent
    except Exception:
        return None


def _get_candidate_settings_paths() -> list[Path]:
    """Return settings files that may contain duplicate hook entries.

    Why: duplicates accumulate in both project-level and user-level settings
    because the installer runs in different contexts (interactive setup writes
    to ~/.claude/settings.json; project startup writes to ./.claude/settings.json).
    Only scanning the project directory misses the user-level accumulation.
    What: returns settings files from the nearest project .claude/ directory
    (walking up from cwd) AND from ~/.claude/.  Each file is included only if it
    exists.  Files are deduplicated so a home-dir project is not processed twice.
    Test: create duplicate MPM hooks in a temp ~/.claude/settings.json, run the
    migration, and assert all but one entry per event are removed.
    """
    seen: set[Path] = set()
    candidates: list[Path] = []

    # Project-level: walk upward from cwd.
    project_claude_dir = _find_project_claude_dir(Path.cwd())
    if project_claude_dir is not None:
        for name in ("settings.json", "settings.local.json"):
            path = (project_claude_dir / name).resolve()
            if path.exists() and path not in seen:
                seen.add(path)
                candidates.append(path)

    # User-level: always include ~/.claude/settings.json when it exists.
    user_claude_dir = Path.home() / ".claude"
    for name in ("settings.json", "settings.local.json"):
        path = (user_claude_dir / name).resolve()
        if path.exists() and path not in seen:
            seen.add(path)
            candidates.append(path)

    return candidates


_BACKUP_KEEP = 5  # Maximum number of MPM backups retained per settings file.


def _rotate_backups(path: Path) -> None:
    """Delete old MPM backups for ``path``, keeping only the ``_BACKUP_KEEP`` newest.

    Backup files are named ``<stem>.json.backup_<timestamp>``.  This helper is
    fail-open: any error is silently ignored so it never blocks startup.
    """
    try:
        stem = path.stem  # e.g. "settings"
        pattern = f"{stem}.json.backup_*"
        backups = sorted(path.parent.glob(pattern))
        excess = backups[: max(0, len(backups) - _BACKUP_KEEP)]
        for old_backup in excess:
            try:
                old_backup.unlink()
                logger.debug("  Deleted old backup: %s", old_backup)
            except OSError:
                pass
    except Exception:
        pass


def _migrate_file(path: Path) -> bool:
    """Dedup MPM hook entries in a single settings file.

    Args:
        path: Path to the settings JSON file.

    Returns:
        True on success (including when no changes were needed).
    """
    logger.info("Processing: %s", path)

    try:
        with open(path) as fh:
            settings = json.load(fh)
    except json.JSONDecodeError as exc:
        logger.warning("  Failed to parse JSON in %s: %s — skipping", path, exc)
        return True  # fail-open: don't crash startup
    except OSError as exc:
        logger.warning("  Failed to read %s: %s — skipping", path, exc)
        return True

    try:
        removed_count = _dedup_settings(settings)
    except Exception as exc:  # fail-open
        logger.warning("  Unexpected error deduplicating %s: %s — skipping", path, exc)
        return True

    if removed_count == 0:
        logger.info("  No duplicate MPM hook entries found — nothing to do")
        return True

    # Create a timestamped backup before writing, then rotate old backups.
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(f".json.backup_{timestamp}")
    try:
        shutil.copy2(path, backup_path)
        logger.info("  Backup created: %s", backup_path)
    except OSError as exc:
        logger.warning("  Could not create backup (non-fatal): %s", exc)

    _rotate_backups(path)

    try:
        with open(path, "w") as fh:
            json.dump(settings, fh, indent=2)
        logger.info(
            "  Removed %d duplicate MPM hook entry/entries from: %s",
            removed_count,
            path,
        )
    except OSError as exc:
        logger.warning("  Failed to write %s: %s — skipping", path, exc)
        return True  # fail-open

    return True


def run_migration() -> bool:
    """Dedup MPM claude-hook registrations in project Claude settings.

    Intended to be called by the migration runner on first startup of
    claude-mpm >= 6.5.20.

    Returns:
        True if all candidate files were processed (or no changes needed).
        Always returns True — this migration is fail-open so it never
        crashes startup even if an unexpected error occurs.
    """
    try:
        paths = _get_candidate_settings_paths()
        if not paths:
            logger.info("No .claude/settings*.json files found — nothing to migrate")
            return True

        results = [_migrate_file(p) for p in paths]
        return all(results)
    except Exception as exc:  # fail-open outer guard
        logger.warning(
            "dedup_hook_registrations migration encountered an unexpected error: %s — "
            "startup will continue normally",
            exc,
        )
        return True
