"""
Migration: Add PermissionRequest hook entry to .claude/settings.json (v6.3.2).

Adds a ``PermissionRequest`` hook that matches the existing project hook pattern
(``claude-hook`` command, 60 s timeout) to ``.claude/settings.json`` if the key
is absent.

- Skips silently when settings.json does not exist.
- Idempotent: re-running the migration leaves an existing PermissionRequest
  entry untouched.
- Writes the updated file with 2-space indentation and a trailing newline.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_PERMISSION_REQUEST_ENTRY: list[dict] = [
    {
        "matcher": "*",
        "hooks": [
            {
                "type": "command",
                "command": "claude-hook",
                "timeout": 60,
            }
        ],
    }
]


def run_migration(installation_dir: Path | None = None) -> bool:
    """Add PermissionRequest hook to .claude/settings.json if missing.

    Args:
        installation_dir: Root of the project (default: cwd)

    Returns:
        True on success
    """
    project_root = installation_dir or Path.cwd()
    settings_path = project_root / ".claude" / "settings.json"

    if not settings_path.exists():
        logger.debug(
            "settings.json not found at %s — skipping migration", settings_path
        )
        return True

    try:
        content = settings_path.read_text(encoding="utf-8")
        data: dict = json.loads(content)
    except (OSError, json.JSONDecodeError) as e:
        logger.error("Failed to read settings.json: %s", e)
        return False

    # Ensure hooks key exists
    if "hooks" not in data:
        data["hooks"] = {}

    hooks: dict = data["hooks"]

    # Idempotent: skip if already set
    if "PermissionRequest" in hooks:
        logger.debug(
            "PermissionRequest hook already present in %s — skipping", settings_path
        )
        return True

    hooks["PermissionRequest"] = _PERMISSION_REQUEST_ENTRY
    logger.info("Added PermissionRequest hook entry to %s", settings_path)

    try:
        settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    except OSError as e:
        logger.error("Failed to write settings.json: %s", e)
        return False

    return True
