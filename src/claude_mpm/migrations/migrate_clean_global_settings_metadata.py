"""
Migration to remove stale _mpm_managed/_mpm_version metadata from global
~/.claude/settings.json (issue #676).

WHAT: Strips orphaned ``_mpm_managed``, ``_mpm_version``, and any leftover
      MPM-owned ``hooks`` entries from ``~/.claude/settings.json`` only.

WHY: A pre-6.3.x code path wrote the full MPM project-settings template
     (including ``_mpm_managed: true``, ``_mpm_version``, and hook entries)
     into the GLOBAL ``~/.claude/settings.json``.  The v6_3_19 migration moved
     the hooks to project-level settings but left the orphaned metadata behind.
     That orphaned metadata makes every plain ``claude`` session (outside a
     claude-mpm project) appear MPM-managed, and the stale ``_mpm_version``
     silently suppresses template upgrades.

     The INTENTIONAL global keys written by ``_deploy_spinner_global`` are
     ``spinnerVerbs``, ``spinnerTipsEnabled``, ``spinnerTipsOverride``, and
     ``_mpm_spinner_version`` — these are always preserved.

This migration:
1. Reads ``~/.claude/settings.json`` (no-op if absent).
2. Removes ``_mpm_managed`` and ``_mpm_version`` keys if present.
3. Removes any ``hooks`` entries where ``_mpm: true`` is set OR where
   ``command`` contains ``"claude-hook"`` (MPM-owned entries).
   Non-MPM / user hooks are left untouched.
4. If the ``hooks`` dict becomes empty after step 3, removes the empty key.
5. Creates a timestamped backup before writing, then rotates old backups
   (keeps at most 5).
6. Is idempotent (second run is a no-op), fail-open (wraps all I/O in
   try/except — failures are logged but never crash startup), and a no-op
   when the file does not exist or contains none of the stale keys.

References
----------
LINK: none
"""

import json
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Keys written intentionally by _deploy_spinner_global — must be preserved.
_SPINNER_KEYS: frozenset[str] = frozenset(
    {
        "spinnerVerbs",
        "spinnerTipsEnabled",
        "spinnerTipsOverride",
        "_mpm_spinner_version",
    }
)

# Top-level metadata keys that are stale in global settings.
_STALE_METADATA_KEYS: tuple[str, ...] = ("_mpm_managed", "_mpm_version")

# Substrings used to recognise an MPM hook command entry (mirrors the
# v6_3_19 / dedup_hook_registrations migration lists).
_MPM_HOOK_MARKERS: tuple[str, ...] = (
    "claude-hook-fast",
    "claude-hook-handler",
    "claude-hook",
    "message_check_hook",
    "tool_failure_hook",
    "claude_mpm",
)

_BACKUP_KEEP = 5  # Maximum number of MPM backups retained per settings file.


def _is_mpm_hook_command(hook_cmd: Any) -> bool:
    """Return True if this hook command dict is owned by claude-mpm.

    Args:
        hook_cmd: A single hook command entry (should be a dict).

    Returns:
        True when the entry should be removed from global settings.
    """
    if not isinstance(hook_cmd, dict):
        return False
    # Primary: explicit MPM ownership marker.
    if hook_cmd.get("_mpm") is True:
        return True
    # Secondary: command string contains a known MPM marker substring.
    command = str(hook_cmd.get("command", ""))
    if any(marker in command for marker in _MPM_HOOK_MARKERS):
        return True
    # Tertiary: any arg string contains an MPM marker.
    args = hook_cmd.get("args") or []
    if isinstance(args, list):
        for arg in args:
            if isinstance(arg, str) and any(
                marker in arg for marker in _MPM_HOOK_MARKERS
            ):
                return True
    return False


def _strip_stale_metadata(settings: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Remove stale MPM metadata and hook entries from a global settings dict.

    Mutates ``settings`` in-place and returns the updated dict alongside the
    total count of keys/entries removed.

    Preserves:
    - All user-authored keys.
    - All spinner keys (``spinnerVerbs``, ``spinnerTipsEnabled``,
      ``spinnerTipsOverride``, ``_mpm_spinner_version``).
    - All non-MPM hook entries.

    Args:
        settings: Parsed ``~/.claude/settings.json`` dict.

    Returns:
        Tuple of (updated settings, total count of items removed).
    """
    removed = 0

    # --- Step 1: remove stale top-level metadata keys -----------------------
    for key in _STALE_METADATA_KEYS:
        if key in settings:
            del settings[key]
            removed += 1
            logger.debug("Removed stale global key: %s", key)

    # --- Step 2: strip MPM-owned hook entries --------------------------------
    hooks = settings.get("hooks")
    if isinstance(hooks, dict):
        event_types_to_delete: list[str] = []

        for event_type, event_configs in hooks.items():
            if not isinstance(event_configs, list):
                continue

            cleaned_configs: list[dict[str, Any]] = []
            for config in event_configs:
                if not isinstance(config, dict):
                    cleaned_configs.append(config)
                    continue

                hook_list = config.get("hooks")
                if not isinstance(hook_list, list):
                    cleaned_configs.append(config)
                    continue

                filtered = [h for h in hook_list if not _is_mpm_hook_command(h)]
                n_removed = len(hook_list) - len(filtered)
                removed += n_removed

                if not filtered:
                    # Entire matcher block is now empty — drop it.
                    continue

                config = dict(config)  # shallow copy so we don't mutate the original
                config["hooks"] = filtered
                cleaned_configs.append(config)

            if cleaned_configs:
                hooks[event_type] = cleaned_configs
            else:
                event_types_to_delete.append(event_type)

        for event_type in event_types_to_delete:
            del hooks[event_type]

        # --- Step 3: drop the entire hooks key when it's now empty ----------
        if not hooks:
            del settings["hooks"]
            logger.debug("Removed empty 'hooks' key from global settings")

    return settings, removed


def _rotate_backups(path: Path) -> None:
    """Delete old MPM backups for ``path``, keeping only ``_BACKUP_KEEP`` newest.

    Fail-open: any error is silently swallowed.
    """
    try:
        stem = path.stem  # e.g. "settings"
        pattern = f"{stem}.json.backup_*"
        backups = sorted(path.parent.glob(pattern))
        excess = backups[: max(0, len(backups) - _BACKUP_KEEP)]
        for old_backup in excess:
            try:
                old_backup.unlink()
                logger.debug("Deleted old backup: %s", old_backup)
            except OSError:
                pass
    except Exception:
        pass


def run_migration() -> bool:
    """Remove stale MPM metadata from ``~/.claude/settings.json``.

    Intended to be called by the migration runner on first startup of
    claude-mpm >= 6.5.21.

    Returns:
        True in all cases — this migration is fail-open and must never crash
        startup.
    """
    try:
        global_settings = Path.home() / ".claude" / "settings.json"

        if not global_settings.exists():
            logger.info(
                "~/.claude/settings.json not found — nothing to migrate (issue #676)"
            )
            return True

        try:
            with open(global_settings, encoding="utf-8") as fh:
                settings = json.load(fh)
        except json.JSONDecodeError as exc:
            logger.warning(
                "clean_global_settings_metadata: could not parse %s: %s — skipping",
                global_settings,
                exc,
            )
            return True
        except OSError as exc:
            logger.warning(
                "clean_global_settings_metadata: could not read %s: %s — skipping",
                global_settings,
                exc,
            )
            return True

        if not isinstance(settings, dict):
            logger.warning(
                "clean_global_settings_metadata: %s is not a JSON object — skipping",
                global_settings,
            )
            return True

        settings, removed_count = _strip_stale_metadata(settings)

        if removed_count == 0:
            logger.info(
                "clean_global_settings_metadata: no stale metadata found in %s",
                global_settings,
            )
            return True

        # Create a timestamped backup before writing.
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        backup_path = global_settings.with_suffix(f".json.backup_{timestamp}")
        try:
            shutil.copy2(global_settings, backup_path)
            logger.info("Backup created: %s", backup_path)
        except OSError as exc:
            logger.warning("Could not create backup (non-fatal): %s", exc)

        _rotate_backups(global_settings)

        try:
            with open(global_settings, "w", encoding="utf-8") as fh:
                json.dump(settings, fh, indent=2)
            fh_path = global_settings  # for the log message
            logger.info(
                "clean_global_settings_metadata: removed %d stale item(s) from %s",
                removed_count,
                fh_path,
            )
        except OSError as exc:
            logger.warning(
                "clean_global_settings_metadata: failed to write %s: %s — skipping",
                global_settings,
                exc,
            )

        return True

    except Exception as exc:  # outermost fail-open guard
        logger.warning(
            "clean_global_settings_metadata migration encountered an unexpected "
            "error: %s — startup will continue normally",
            exc,
        )
        return True
