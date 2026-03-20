#!/usr/bin/env python3
"""
Migration to remove unsupported v2.1.47+ hook events from Claude settings.

This migration:
1. Detects the installed Claude Code version
2. If the version is older than v2.1.47, removes hook entries that are not
   recognized by the installed version:
   - WorktreeCreate / WorktreeRemove
   - TeammateIdle / TaskCompleted
   - ConfigChange
3. Leaves settings unchanged if Claude Code >= v2.1.47 (hooks are valid).

Background:
    Prior to claude-mpm v5.9.48, these hook event types were written
    unconditionally to settings.local.json, causing "Invalid key in record"
    warnings at startup on older Claude Code installations.

Usage:
    python -m claude_mpm.migrations.migrate_remove_unsupported_hooks [--dry-run]
"""

import argparse
import json
import logging
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Hook event types added in Claude Code v2.1.47
UNSUPPORTED_HOOK_EVENTS = [
    "WorktreeCreate",
    "WorktreeRemove",
    "TeammateIdle",
    "TaskCompleted",
    "ConfigChange",
]


def get_settings_paths() -> list[Path]:
    """Get paths to all Claude settings files that may contain stale hooks."""
    paths = []

    # Project-level settings
    project_settings = Path.cwd() / ".claude" / "settings.local.json"
    if project_settings.exists():
        paths.append(project_settings)

    # User-level settings
    user_settings = Path.home() / ".claude" / "settings.json"
    if user_settings.exists():
        paths.append(user_settings)

    user_local_settings = Path.home() / ".claude" / "settings.local.json"
    if user_local_settings.exists():
        paths.append(user_local_settings)

    return paths


def _claude_supports_new_hooks() -> bool:
    """Return True if the installed Claude Code version supports v2.1.47+ hooks.

    Uses the same logic as HookInstaller.supports_new_hooks() but without
    requiring a full HookInstaller instance, to keep the migration self-contained.

    Returns:
        True if Claude Code >= 2.1.47, False if older or undetectable.
    """
    try:
        from ..hooks.claude_hooks.installer import HookInstaller

        installer = HookInstaller()
        return installer.supports_new_hooks()
    except Exception as e:
        logger.debug(f"Could not check Claude version via HookInstaller: {e}")
        # Fall back to conservative approach
        return _detect_version_fallback()


def _detect_version_fallback() -> bool:
    """Fallback version detection without HookInstaller dependency.

    Returns:
        True if version >= 2.1.47, False otherwise (including unknown).
    """
    import re
    import subprocess

    try:
        result = subprocess.run(
            ["claude", "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stdout.strip() or result.stderr.strip()
        # Extract semver from output like "1.0.0 (build ...)" or "Claude Code 2.1.47"
        match = re.search(r"(\d+)\.(\d+)\.(\d+)", output)
        if not match:
            return False
        major, minor, patch = (
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
        )
        min_major, min_minor, min_patch = 2, 1, 47
        if major != min_major:
            return major > min_major
        if minor != min_minor:
            return minor > min_minor
        return patch >= min_patch
    except Exception:
        return False


def remove_unsupported_hooks(
    settings: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Remove v2.1.47+ hook event entries from settings.

    Args:
        settings: Current settings dictionary

    Returns:
        Tuple of (modified settings, list of removed event types)
    """
    if "hooks" not in settings:
        return settings, []

    removed = []
    for event_type in UNSUPPORTED_HOOK_EVENTS:
        if event_type in settings["hooks"]:
            del settings["hooks"][event_type]
            removed.append(event_type)

    return settings, removed


def backup_settings(path: Path) -> Path:
    """Create a timestamped backup of a settings file.

    Args:
        path: Path to settings file

    Returns:
        Path to backup file
    """
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(f".json.backup_{timestamp}")
    shutil.copy2(path, backup_path)
    return backup_path


def migrate_file(path: Path, dry_run: bool = False) -> bool:
    """Remove unsupported hook events from a single settings file.

    Args:
        path: Path to settings file
        dry_run: If True, only show what would be done

    Returns:
        True if file was processed successfully (or no changes needed)
    """
    logger.info(f"Processing: {path}")

    try:
        with open(path) as f:
            settings = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"  Failed to parse JSON: {e}")
        return False
    except OSError as e:
        logger.error(f"  Failed to read file: {e}")
        return False

    migrated, removed = remove_unsupported_hooks(settings)

    if not removed:
        logger.info("  No unsupported hooks found — nothing to do")
        return True

    logger.info(f"  Found unsupported hook events: {removed}")

    if dry_run:
        logger.info(f"  [DRY RUN] Would remove: {removed}")
        return True

    # Backup and write
    backup_path = backup_settings(path)
    logger.info(f"  Backup created: {backup_path}")

    try:
        with open(path, "w") as f:
            json.dump(migrated, f, indent=2)
    except OSError as e:
        logger.error(f"  Failed to write file: {e}")
        return False

    logger.info(f"  Removed {len(removed)} unsupported hook event(s) from: {path}")
    return True


def migrate_all_settings() -> bool:
    """Run migration on all detected settings files.

    This is the callable used by the migration runner for automatic
    migrations on version upgrade.

    Only removes hooks if the installed Claude Code version does not support
    the v2.1.47+ hook events (or version is undetectable). No-ops for users
    already on Claude Code >= 2.1.47.

    Returns:
        True if migration was successful (or not needed).
    """
    if _claude_supports_new_hooks():
        # Claude Code >= 2.1.47: hooks are valid, nothing to clean up
        logger.info(
            "Claude Code >= 2.1.47 detected — v2.1.47+ hooks are supported, skipping cleanup"
        )
        return True

    logger.info(
        "Claude Code < 2.1.47 (or undetectable) — removing unsupported hook events"
    )

    paths = get_settings_paths()
    if not paths:
        # No settings files found — nothing to migrate
        logger.info("No Claude settings files found — nothing to migrate")
        return True

    success = 0
    for path in paths:
        if migrate_file(path, dry_run=False):
            success += 1

    return success == len(paths)


def main() -> int:
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(
        description="Remove unsupported v2.1.47+ hook events from Claude settings"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Migrate a specific file instead of auto-detecting",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Remove hooks regardless of Claude Code version",
    )
    args = parser.parse_args()

    if not args.force and _claude_supports_new_hooks():
        logger.info("Claude Code >= 2.1.47 — hooks are supported, nothing to remove")
        logger.info("Use --force to remove them anyway")
        return 0

    if args.file:
        paths = [args.file] if args.file.exists() else []
    else:
        paths = get_settings_paths()

    if not paths:
        logger.warning("No Claude settings files found")
        return 0

    logger.info(f"Found {len(paths)} settings file(s) to process")
    if args.dry_run:
        logger.info("[DRY RUN MODE]")

    success = 0
    for path in paths:
        if migrate_file(path, dry_run=args.dry_run):
            success += 1

    logger.info(f"\nMigration complete: {success}/{len(paths)} files processed")
    return 0 if success == len(paths) else 1


if __name__ == "__main__":
    sys.exit(main())
