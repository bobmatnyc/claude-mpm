"""
Migration: Add PermissionRequest hook to .claude/settings.json (v6.3.2).

Adds a `PermissionRequest` hook entry to the project-level settings.json
hooks section if it is not already present.

The hook command is derived from the existing `PreToolUse` hook (first
matcher whose command contains "claude-hook" or the first hook command found).
Falls back to "claude-hook" if no PreToolUse hook is found.

Idempotent: if a PermissionRequest hook already exists it is left unchanged.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_FALLBACK_COMMAND = "claude-hook"


def _derive_hook_command(hooks_section: dict) -> str:
    """Derive the hook command from the existing PreToolUse hook.

    Args:
        hooks_section: The `hooks` dict from settings.json.

    Returns:
        Command string to use for the PermissionRequest hook.
    """
    pre_tool_use = hooks_section.get("PreToolUse", [])
    for matcher_block in pre_tool_use:
        for hook in matcher_block.get("hooks", []):
            cmd: str = str(hook.get("command", ""))
            # Prefer a command that looks like our hook dispatcher.
            if "claude-hook" in cmd:
                return cmd
            if cmd:
                return cmd  # First non-empty command wins.
    return _FALLBACK_COMMAND


def _build_permission_request_entry(command: str, timeout: int = 60) -> list[dict]:
    """Build the PermissionRequest hook list entry.

    Args:
        command: Hook dispatcher command.
        timeout: Timeout in seconds.

    Returns:
        List suitable for settings["hooks"]["PermissionRequest"].
    """
    return [
        {
            "matcher": "*",
            "hooks": [
                {
                    "type": "command",
                    "command": command,
                    "timeout": timeout,
                }
            ],
        }
    ]


def run_migration(installation_dir: Path | None = None) -> bool:
    """Add PermissionRequest hook to .claude/settings.json.

    Args:
        installation_dir: Root of the project (default: cwd).

    Returns:
        True on success.
    """
    project_root = installation_dir or Path.cwd()
    settings_path = project_root / ".claude" / "settings.json"

    if not settings_path.exists():
        logger.debug("No settings.json found at %s — skipping", settings_path)
        return True

    try:
        content = settings_path.read_text(encoding="utf-8")
        settings: dict = json.loads(content)
    except Exception:
        logger.exception("Failed to read settings.json at %s", settings_path)
        return False

    # Ensure hooks dict exists.
    if "hooks" not in settings:
        settings["hooks"] = {}

    hooks: dict = settings["hooks"]

    if "PermissionRequest" in hooks:
        logger.debug(
            "PermissionRequest hook already present in %s — skipping", settings_path
        )
        return True

    command = _derive_hook_command(hooks)
    hooks["PermissionRequest"] = _build_permission_request_entry(command)

    try:
        settings_path.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        logger.info(
            "Added PermissionRequest hook (command=%r) to %s", command, settings_path
        )
    except Exception:
        logger.exception("Failed to write settings.json at %s", settings_path)
        return False

    return True
