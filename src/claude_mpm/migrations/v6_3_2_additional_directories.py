"""
Migration: Add permissions.additionalDirectories to .claude/settings.json (v6.3.2).

Adds `permissions.additionalDirectories: []` to the project-level settings.json
if the field is not already present.

Idempotent: if the field already exists (even with a non-empty value), it is
left unchanged.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def run_migration(installation_dir: Path | None = None) -> bool:
    """Add permissions.additionalDirectories to .claude/settings.json.

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

    # Ensure permissions dict exists.
    if "permissions" not in settings:
        settings["permissions"] = {}

    permissions: dict = settings["permissions"]

    if "additionalDirectories" in permissions:
        logger.debug(
            "permissions.additionalDirectories already present in %s — skipping",
            settings_path,
        )
        return True

    permissions["additionalDirectories"] = []

    try:
        settings_path.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        logger.info("Added permissions.additionalDirectories: [] to %s", settings_path)
    except Exception:
        logger.exception("Failed to write settings.json at %s", settings_path)
        return False

    return True
