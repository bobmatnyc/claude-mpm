"""
Migration to remove stale memory_capture hook entries from Claude settings.

Memory capture was previously implemented as a standalone hook module
(claude_mpm.hooks.memory_capture) installed into PostToolUse, Stop,
SubagentStop, SessionStart, and UserPromptSubmit. This functionality
has been moved to trusty-memory (issue #555) and the module has been
removed.

This migration:
1. Scans .claude/settings.json (and settings.local.json if present) for
   any hook entries with `"_mpm_service": "memory-capture"` or that
   reference `claude_mpm.hooks.memory_capture` in their args.
2. Removes those entries, cleaning up empty hook arrays and matcher blocks
   as needed.

Background:
    The hook caused `PostToolUse:Agent hook error — Failed with non-blocking
    status code: No module named claude_mpm.hooks.memory_capture` whenever
    Claude Code tried to invoke the removed module.
"""

import json
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _is_memory_capture_hook(hook_cmd: dict[str, Any]) -> bool:
    """Return True if this hook command entry references memory_capture.

    Args:
        hook_cmd: A single hook command dict from the hooks list.

    Returns:
        True if the entry should be removed.
    """
    if not isinstance(hook_cmd, dict):
        return False
    # Primary signal: explicit service marker added when the hook was installed
    if hook_cmd.get("_mpm_service") == "memory-capture":
        return True
    # Secondary signal: args array contains the module name
    args = hook_cmd.get("args", [])
    if isinstance(args, list) and "claude_mpm.hooks.memory_capture" in args:
        return True
    # Tertiary: command string itself (unlikely but defensive)
    command = hook_cmd.get("command", "")
    if "memory_capture" in str(command):
        return True
    return False


def _strip_memory_capture_from_settings(
    settings: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    """Remove all memory_capture hook entries from a settings dict.

    Args:
        settings: Parsed settings dictionary (mutated in-place).

    Returns:
        Tuple of (updated settings, number of entries removed).
    """
    removed_count = 0
    hooks_section = settings.get("hooks")
    if not isinstance(hooks_section, dict):
        return settings, 0

    event_types_to_delete: list[str] = []

    for event_type, event_configs in hooks_section.items():
        if not isinstance(event_configs, list):
            continue

        # Each event config is a dict with optional "matcher" and "hooks" list
        cleaned_configs: list[dict[str, Any]] = []
        for config in event_configs:
            if not isinstance(config, dict):
                cleaned_configs.append(config)
                continue

            hook_list = config.get("hooks")
            if not isinstance(hook_list, list):
                cleaned_configs.append(config)
                continue

            filtered = [h for h in hook_list if not _is_memory_capture_hook(h)]
            n_removed = len(hook_list) - len(filtered)
            removed_count += n_removed

            if not filtered:
                # Entire matcher block is now empty — drop the block
                continue

            config = dict(config)  # shallow copy to avoid mutating original
            config["hooks"] = filtered
            cleaned_configs.append(config)

        if cleaned_configs:
            hooks_section[event_type] = cleaned_configs
        else:
            event_types_to_delete.append(event_type)

    for event_type in event_types_to_delete:
        del hooks_section[event_type]

    return settings, removed_count


def _get_candidate_settings_paths() -> list[Path]:
    """Return settings files that may contain stale memory_capture entries."""
    candidates: list[Path] = []

    for name in ("settings.json", "settings.local.json"):
        path = Path.cwd() / ".claude" / name
        if path.exists():
            candidates.append(path)

    return candidates


def _migrate_file(path: Path) -> bool:
    """Strip memory_capture hooks from a single settings file.

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
        logger.error("  Failed to parse JSON: %s", exc)
        return False
    except OSError as exc:
        logger.error("  Failed to read file: %s", exc)
        return False

    settings, removed_count = _strip_memory_capture_from_settings(settings)

    if removed_count == 0:
        logger.info("  No memory_capture hook entries found — nothing to do")
        return True

    # Create a timestamped backup before writing
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(f".json.backup_{timestamp}")
    try:
        shutil.copy2(path, backup_path)
        logger.info("  Backup created: %s", backup_path)
    except OSError as exc:
        logger.warning("  Could not create backup: %s", exc)

    try:
        with open(path, "w") as fh:
            json.dump(settings, fh, indent=2)
        logger.info(
            "  Removed %d memory_capture hook entry/entries from: %s",
            removed_count,
            path,
        )
    except OSError as exc:
        logger.error("  Failed to write file: %s", exc)
        return False

    return True


def run_migration() -> bool:
    """Strip stale memory_capture hooks from project Claude settings.

    Intended to be called by the migration runner on first startup of
    claude-mpm >= 6.4.9.

    Returns:
        True if all candidate files were processed successfully (or no
        changes were needed).
    """
    paths = _get_candidate_settings_paths()
    if not paths:
        logger.info("No .claude/settings*.json files found — nothing to migrate")
        return True

    results = [_migrate_file(p) for p in paths]
    return all(results)
