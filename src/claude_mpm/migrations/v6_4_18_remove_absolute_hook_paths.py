"""
Migration: Remove absolute hook paths from project-level settings.json (v6.4.18).

Historically ``HookInstaller.get_hook_command()`` could return the absolute
path to ``claude-hook-fast.sh`` or ``claude-hook-handler.sh`` and write it
into the team-shared ``.claude/settings.json``.  Those absolute paths are
machine-specific (e.g. ``/Users/masa/Projects/...``) and must not live in a
committed file (issue #563).

This migration scans ``.claude/settings.json`` for hook command entries whose
``command`` value is an absolute path that contains one of the known MPM
script names, and replaces them with the portable ``"claude-hook"`` PATH
entry point.  Entries that are already ``"claude-hook"`` are left untouched,
so the migration is idempotent.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Substrings that identify an absolute-path hook command as belonging to MPM.
_MPM_SCRIPT_NAMES: tuple[str, ...] = (
    "claude-hook-fast.sh",
    "claude-hook-handler.sh",
    "claude-mpm-hook.sh",
)

_REPLACEMENT_COMMAND = "claude-hook"


def _is_absolute_mpm_hook(command: str) -> bool:
    """Return True if *command* is an absolute path to a known MPM hook script."""
    if not command.startswith("/"):
        return False
    return any(script in command for script in _MPM_SCRIPT_NAMES)


def _clean_hooks(settings: dict[str, Any]) -> int:
    """Replace absolute MPM hook paths with ``"claude-hook"`` in *settings*.

    Mutates *settings* in-place.

    Returns:
        Number of hook command entries that were replaced.
    """
    replaced = 0
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return replaced

    for _event, matcher_blocks in hooks.items():
        if not isinstance(matcher_blocks, list):
            continue
        for block in matcher_blocks:
            if not isinstance(block, dict):
                continue
            block_hooks = block.get("hooks")
            if not isinstance(block_hooks, list):
                continue
            for hook_cmd in block_hooks:
                if not isinstance(hook_cmd, dict):
                    continue
                command = hook_cmd.get("command", "")
                if _is_absolute_mpm_hook(command):
                    logger.info(
                        "Replacing absolute hook path '%s' with '%s'",
                        command,
                        _REPLACEMENT_COMMAND,
                    )
                    hook_cmd["command"] = _REPLACEMENT_COMMAND
                    replaced += 1

    return replaced


def check_needs_migration(installation_dir: Path | None = None) -> bool:
    """Return True if ``.claude/settings.json`` contains absolute MPM hook paths.

    Args:
        installation_dir: Project root (defaults to ``Path.cwd()``).
    """
    project_root = installation_dir or Path.cwd()
    settings_path = project_root / ".claude" / "settings.json"
    if not settings_path.exists():
        return False
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except Exception:
        return False

    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return False

    for _event, matcher_blocks in hooks.items():
        if not isinstance(matcher_blocks, list):
            continue
        for block in matcher_blocks:
            if not isinstance(block, dict):
                continue
            for hook_cmd in block.get("hooks") or []:
                if isinstance(hook_cmd, dict) and _is_absolute_mpm_hook(
                    hook_cmd.get("command", "")
                ):
                    return True
    return False


def run_migration(installation_dir: Path | None = None) -> bool:
    """Remove absolute MPM hook paths from ``.claude/settings.json``.

    Args:
        installation_dir: Project root (defaults to ``Path.cwd()``).

    Returns:
        True on success (including no-op runs).
    """
    project_root = installation_dir or Path.cwd()
    settings_path = project_root / ".claude" / "settings.json"

    if not settings_path.exists():
        logger.debug("No .claude/settings.json found — nothing to migrate")
        return True

    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.warning(
            "Could not parse %s: %s — skipping migration", settings_path, exc
        )
        return False

    replaced = _clean_hooks(data)
    if replaced == 0:
        logger.debug("No absolute MPM hook paths found in %s", settings_path)
        return True

    try:
        settings_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        logger.info(
            "Replaced %d absolute hook path(s) with '%s' in %s",
            replaced,
            _REPLACEMENT_COMMAND,
            settings_path,
        )
    except OSError as exc:
        logger.warning("Failed to write %s: %s", settings_path, exc)
        return False

    return True
