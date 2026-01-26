#!/usr/bin/env python3
"""
Migration script to update Claude Code hooks to async configuration.

This migration:
1. Reads existing .claude/settings.local.json and ~/.claude/settings.json
2. Deduplicates hook entries
3. Adds timeout configurations for async execution
4. Cleans up malformed or redundant hook configurations

Usage:
    python -m claude_mpm.migrations.migrate_async_hooks [--dry-run]
"""

import argparse
import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def get_settings_paths() -> list[Path]:
    """Get paths to Claude settings files."""
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


def deduplicate_hooks(hooks_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate hook commands from a hooks list.

    Args:
        hooks_list: List of hook configurations for an event type

    Returns:
        Deduplicated list with unique commands
    """
    result = []
    seen_matchers: dict[str, dict[str, Any]] = {}

    for hook_config in hooks_list:
        matcher = hook_config.get("matcher", "*")

        if matcher not in seen_matchers:
            # First time seeing this matcher
            seen_matchers[matcher] = {
                "matcher": matcher,
                "hooks": [],
            }

        # Process individual hook commands
        if "hooks" in hook_config:
            seen_commands: set[str] = set()

            # Collect existing commands for this matcher
            for existing_hook in seen_matchers[matcher].get("hooks", []):
                if "command" in existing_hook:
                    seen_commands.add(existing_hook["command"])

            # Add new unique commands
            for hook in hook_config["hooks"]:
                if hook.get("type") == "command":
                    command = hook.get("command", "")
                    if command and command not in seen_commands:
                        seen_commands.add(command)
                        # Add timeout if not present
                        if "timeout" not in hook:
                            hook["timeout"] = 60
                        seen_matchers[matcher]["hooks"].append(hook)
                elif hook.get("type") == "prompt":
                    # Keep prompt hooks as-is
                    seen_matchers[matcher]["hooks"].append(hook)

    # Build result from deduplicated matchers
    for matcher_config in seen_matchers.values():
        if matcher_config["hooks"]:  # Only add if there are hooks
            result.append(matcher_config)

    return result


def migrate_settings(settings: dict[str, Any]) -> dict[str, Any]:
    """Migrate settings to async hook configuration.

    Args:
        settings: Current settings dictionary

    Returns:
        Migrated settings with async hooks
    """
    if "hooks" not in settings:
        return settings

    hooks = settings["hooks"]

    # Process each hook event type
    for event_type in list(hooks.keys()):
        # Skip comment keys
        if event_type.startswith("//"):
            continue

        if isinstance(hooks[event_type], list):
            hooks[event_type] = deduplicate_hooks(hooks[event_type])

    return settings


def backup_settings(path: Path) -> Path:
    """Create a backup of settings file.

    Args:
        path: Path to settings file

    Returns:
        Path to backup file
    """
    from datetime import timezone

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(f".json.backup_{timestamp}")
    shutil.copy2(path, backup_path)
    return backup_path


def migrate_file(path: Path, dry_run: bool = False) -> bool:
    """Migrate a single settings file.

    Args:
        path: Path to settings file
        dry_run: If True, only show what would be done

    Returns:
        True if migration was successful
    """
    logger.info(f"Processing: {path}")

    try:
        with open(path) as f:
            settings = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"  Failed to parse JSON: {e}")
        return False

    # Count hooks before migration
    hooks_before = 0
    if "hooks" in settings:
        for event_type, hook_list in settings["hooks"].items():
            if isinstance(hook_list, list):
                for hook_config in hook_list:
                    if "hooks" in hook_config:
                        hooks_before += len(hook_config["hooks"])

    # Migrate settings
    migrated = migrate_settings(settings)

    # Count hooks after migration
    hooks_after = 0
    if "hooks" in migrated:
        for event_type, hook_list in migrated["hooks"].items():
            if isinstance(hook_list, list):
                for hook_config in hook_list:
                    if "hooks" in hook_config:
                        hooks_after += len(hook_config["hooks"])

    logger.info(
        f"  Hooks: {hooks_before} -> {hooks_after} (removed {hooks_before - hooks_after} duplicates)"
    )

    if dry_run:
        logger.info("  [DRY RUN] Would update file")
        logger.info(
            f"  [DRY RUN] Preview:\n{json.dumps(migrated.get('hooks', {}), indent=2)[:500]}..."
        )
        return True

    # Backup and write
    backup_path = backup_settings(path)
    logger.info(f"  Backup created: {backup_path}")

    with open(path, "w") as f:
        json.dump(migrated, f, indent=2)

    logger.info(f"  Updated: {path}")
    return True


def main() -> int:
    """Main entry point for migration."""
    parser = argparse.ArgumentParser(
        description="Migrate Claude Code hooks to async configuration"
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
    args = parser.parse_args()

    if args.file:
        paths = [args.file] if args.file.exists() else []
    else:
        paths = get_settings_paths()

    if not paths:
        logger.warning("No Claude settings files found to migrate")
        return 0

    logger.info(f"Found {len(paths)} settings file(s) to migrate")
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
