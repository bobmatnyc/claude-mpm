"""
Migration: Move MPM hooks from settings.local.json to project-level settings.json (v6.3.19).

Previously, ``HookInstaller`` wrote MPM hooks to ``.claude/settings.local.json``
(user-local, git-ignored). As of v6.3.19 hooks live in ``.claude/settings.json``
(team-shared, checked-in). This migration moves any MPM hook entries out of:

1. ``<project>/.claude/settings.local.json``
2. ``~/.claude/settings.json``

and merges them into ``<project>/.claude/settings.json``, deduplicating by
``event + command`` so re-running the migration is idempotent.

A hook entry is considered an "MPM hook" if its ``command`` (or any of its
``args``) contains one of: ``claude-hook``, ``claude-hook-fast``,
``claude-hook-handler``, ``message_check_hook``, ``tool_failure_hook``, or
``claude_mpm``.

When MPM hooks are successfully moved out of ``settings.local.json``, this
migration also strips ``"disableAllHooks": true`` from that file (it was a
stale guard for the now-moved hook entries).
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Substrings that identify a hook entry as belonging to claude-mpm.
_MPM_HOOK_MARKERS: tuple[str, ...] = (
    "claude-hook-fast",
    "claude-hook-handler",
    "claude-hook",
    "message_check_hook",
    "tool_failure_hook",
    "claude_mpm",
)


def _is_mpm_hook_command(hook_cmd: dict[str, Any]) -> bool:
    """Return True if a single hook command dict belongs to claude-mpm."""
    if not isinstance(hook_cmd, dict):
        return False
    if hook_cmd.get("type") != "command":
        return False

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


def _hook_key(event: str, hook_cmd: dict[str, Any]) -> tuple[str, str, str]:
    """Build a dedup key for a hook command: (event, command, args-json)."""
    command = str(hook_cmd.get("command", ""))
    args = hook_cmd.get("args") or []
    try:
        args_repr = json.dumps(args, sort_keys=True)
    except TypeError:
        args_repr = str(args)
    return (event, command, args_repr)


def _read_json(path: Path) -> dict[str, Any] | None:
    """Read a JSON file; return parsed dict or None on missing/invalid."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to read JSON from %s", path)
        return None


def _write_json(path: Path, data: dict[str, Any]) -> bool:
    """Write JSON with trailing newline."""
    try:
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return True
    except Exception:
        logger.exception("Failed to write JSON to %s", path)
        return False


def _extract_mpm_hooks(
    settings: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Pull MPM hook commands out of a settings dict.

    Mutates ``settings`` in-place: MPM hook commands are removed from each
    event's matcher blocks; empty matcher blocks and empty event lists are
    cleaned up; an empty ``hooks`` dict is removed.

    Returns:
        Mapping ``event -> list of removed hook command dicts``.
    """
    removed: dict[str, list[dict[str, Any]]] = {}
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return removed

    for event in list(hooks.keys()):
        matcher_blocks = hooks.get(event)
        if not isinstance(matcher_blocks, list):
            continue

        for block in matcher_blocks:
            if not isinstance(block, dict):
                continue
            block_hooks = block.get("hooks")
            if not isinstance(block_hooks, list):
                continue

            kept: list[dict[str, Any]] = []
            for hook_cmd in block_hooks:
                if _is_mpm_hook_command(hook_cmd):
                    removed.setdefault(event, []).append(hook_cmd)
                else:
                    kept.append(hook_cmd)
            block["hooks"] = kept

        # Drop matcher blocks whose hooks array is now empty.
        cleaned_blocks = [
            b for b in matcher_blocks if isinstance(b, dict) and b.get("hooks")
        ]
        if cleaned_blocks:
            hooks[event] = cleaned_blocks
        else:
            hooks.pop(event, None)

    if not hooks:
        settings.pop("hooks", None)

    return removed


def _existing_hook_keys(settings: dict[str, Any]) -> set[tuple[str, str, str]]:
    """Build the set of (event, command, args) keys already in settings."""
    keys: set[tuple[str, str, str]] = set()
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return keys

    for event, matcher_blocks in hooks.items():
        if not isinstance(matcher_blocks, list):
            continue
        for block in matcher_blocks:
            if not isinstance(block, dict):
                continue
            for hook_cmd in block.get("hooks", []) or []:
                if isinstance(hook_cmd, dict):
                    keys.add(_hook_key(event, hook_cmd))
    return keys


def _merge_into_settings_json(
    target: dict[str, Any],
    incoming: dict[str, list[dict[str, Any]]],
) -> int:
    """Merge incoming hook commands into target settings.

    Args:
        target: Project ``settings.json`` dict (will be mutated).
        incoming: Mapping of event -> list of hook command dicts to add.

    Returns:
        Number of hook commands actually added (after dedup).
    """
    if not incoming:
        return 0

    if "hooks" not in target or not isinstance(target["hooks"], dict):
        target["hooks"] = {}

    existing_keys = _existing_hook_keys(target)
    added = 0

    for event, hook_cmds in incoming.items():
        for hook_cmd in hook_cmds:
            key = _hook_key(event, hook_cmd)
            if key in existing_keys:
                continue

            event_blocks = target["hooks"].setdefault(event, [])

            # Try to append into an existing matcher: "*" block; else create one.
            placed = False
            for block in event_blocks:
                if (
                    isinstance(block, dict)
                    and block.get("matcher") == "*"
                    and isinstance(block.get("hooks"), list)
                ):
                    block["hooks"].append(hook_cmd)
                    placed = True
                    break

            if not placed:
                event_blocks.append({"matcher": "*", "hooks": [hook_cmd]})

            existing_keys.add(key)
            added += 1

    return added


def run_migration(installation_dir: Path | None = None) -> bool:
    """Move MPM hooks from settings.local.json (and user-global) into project settings.json.

    Args:
        installation_dir: Project root (defaults to ``Path.cwd()``).

    Returns:
        True on success.
    """
    project_root = installation_dir or Path.cwd()
    project_settings_path = project_root / ".claude" / "settings.json"
    project_local_path = project_root / ".claude" / "settings.local.json"
    user_global_path = Path.home() / ".claude" / "settings.json"

    # Load project settings.json (create empty if missing — we may write to it).
    project_settings = _read_json(project_settings_path) or {}

    total_added = 0

    # --- Source 1: project settings.local.json ----------------------------------
    local_settings = _read_json(project_local_path)
    moved_from_local = False
    if local_settings is not None:
        removed = _extract_mpm_hooks(local_settings)
        if removed:
            added = _merge_into_settings_json(project_settings, removed)
            total_added += added
            logger.info(
                "Moved %d MPM hook command(s) from %s into %s",
                added,
                project_local_path,
                project_settings_path,
            )
            moved_from_local = True

            # If we cleaned the legacy hook location, also drop the stale
            # disableAllHooks guard that was paired with those hooks.
            if local_settings.get("disableAllHooks") is True:
                local_settings.pop("disableAllHooks", None)
                logger.info(
                    "Removed stale 'disableAllHooks: true' from %s",
                    project_local_path,
                )

            if not _write_json(project_local_path, local_settings):
                return False

    # --- Source 2: ~/.claude/settings.json --------------------------------------
    # Only touch the user-global file if it currently contains MPM hooks; we
    # don't want to rewrite an untouched user-global settings file.
    if user_global_path != project_settings_path:
        user_settings = _read_json(user_global_path)
        if user_settings is not None:
            # Probe without mutating: copy is cheap and avoids accidental writes.
            probe_copy = json.loads(json.dumps(user_settings))
            probed_removed = _extract_mpm_hooks(probe_copy)
            if probed_removed:
                # Now actually extract from the real dict.
                removed_user = _extract_mpm_hooks(user_settings)
                added = _merge_into_settings_json(project_settings, removed_user)
                total_added += added
                logger.info(
                    "Moved %d MPM hook command(s) from %s into %s",
                    added,
                    user_global_path,
                    project_settings_path,
                )
                if not _write_json(user_global_path, user_settings):
                    return False

    # --- Write project settings.json --------------------------------------------
    if total_added > 0 or moved_from_local:
        project_settings_path.parent.mkdir(parents=True, exist_ok=True)
        if not _write_json(project_settings_path, project_settings):
            return False
        logger.info(
            "Hook migration complete: %d MPM hook command(s) consolidated into %s",
            total_added,
            project_settings_path,
        )
    else:
        logger.debug(
            "No MPM hooks found in settings.local.json or ~/.claude/settings.json — nothing to migrate"
        )

    return True
