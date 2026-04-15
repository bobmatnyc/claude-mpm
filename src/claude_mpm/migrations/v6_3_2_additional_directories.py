"""
Migration: Add permissions.additionalDirectories to .claude/settings.json (v6.3.2).

Adds an empty ``permissions.additionalDirectories`` array to the project's
``.claude/settings.json`` if the key is absent.

- Skips silently when settings.json does not exist.
- Idempotent: re-running the migration leaves existing values untouched.
- Writes the updated file with 2-space indentation and a trailing newline.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def run_migration(installation_dir: Path | None = None) -> bool:
    """Add permissions.additionalDirectories to .claude/settings.json if missing.

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

    # Ensure permissions key exists
    if "permissions" not in data:
        data["permissions"] = {}

    permissions: dict = data["permissions"]

    # Idempotent: skip if already set
    if "additionalDirectories" in permissions:
        logger.debug(
            "permissions.additionalDirectories already present in %s — skipping",
            settings_path,
        )
        return True

    permissions["additionalDirectories"] = []
    logger.info("Added permissions.additionalDirectories to %s", settings_path)

    try:
        settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    except OSError as e:
        logger.error("Failed to write settings.json: %s", e)
        return False

    return True
