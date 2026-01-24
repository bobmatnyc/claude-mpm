"""
Startup migrations for claude-mpm.

This module provides a migration registry pattern for automatically fixing
configuration issues on first startup after an update. Migrations run once
and are tracked in ~/.claude-mpm/migrations.yaml.

Design Principles:
- Non-blocking: Failures log warnings but don't stop startup
- Idempotent: Safe to run multiple times (check before migrate)
- Tracked: Each migration runs only once per installation
- Early: Runs before agent sync in startup sequence
"""

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import yaml

from ..core.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class Migration:
    """Definition of a startup migration."""

    id: str
    description: str
    check: Callable[[], bool]  # Returns True if migration is needed
    migrate: Callable[[], bool]  # Returns True if migration succeeded


def _get_migrations_file() -> Path:
    """Get path to migrations tracking file."""
    return Path.home() / ".claude-mpm" / "migrations.yaml"


def _load_completed_migrations() -> dict:
    """Load completed migrations from tracking file.

    Returns:
        Dictionary with completed migrations data.
    """
    migrations_file = _get_migrations_file()
    if not migrations_file.exists():
        return {"migrations": []}

    try:
        with open(migrations_file) as f:
            data = yaml.safe_load(f) or {}
            return data if "migrations" in data else {"migrations": []}
    except Exception as e:
        logger.debug(f"Failed to load migrations file: {e}")
        return {"migrations": []}


def _save_completed_migration(migration_id: str) -> None:
    """Save a completed migration to tracking file.

    Args:
        migration_id: The ID of the completed migration.
    """
    migrations_file = _get_migrations_file()
    migrations_file.parent.mkdir(parents=True, exist_ok=True)

    data = _load_completed_migrations()

    # Add new migration entry
    data["migrations"].append(
        {"id": migration_id, "completed_at": datetime.now(timezone.utc).isoformat()}
    )

    try:
        with open(migrations_file, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False)
    except Exception as e:
        logger.warning(f"Failed to save migration tracking: {e}")


def _is_migration_completed(migration_id: str) -> bool:
    """Check if a migration has already been completed.

    Args:
        migration_id: The ID of the migration to check.

    Returns:
        True if the migration has been completed.
    """
    data = _load_completed_migrations()
    completed_ids = [m.get("id") for m in data.get("migrations", [])]
    return migration_id in completed_ids


# =============================================================================
# Migration: v5.6.76-cache-dir-rename
# =============================================================================


def _check_cache_dir_rename_needed() -> bool:
    """Check if cache directory rename is needed.

    Returns:
        True if ~/.claude-mpm/cache/remote-agents/ exists.
    """
    old_cache_dir = Path.home() / ".claude-mpm" / "cache" / "remote-agents"
    return old_cache_dir.exists()


def _count_files_in_dir(path: Path) -> int:
    """Count files recursively in a directory.

    Args:
        path: Directory path to count files in.

    Returns:
        Number of files (not directories) in the path.
    """
    if not path.exists():
        return 0
    try:
        return sum(1 for _ in path.rglob("*") if _.is_file())
    except Exception:
        return 0


def _migrate_cache_dir_rename() -> bool:
    """Rename remote-agents cache directory to agents.

    This migration:
    1. Moves ~/.claude-mpm/cache/remote-agents/ contents to ~/.claude-mpm/cache/agents/
    2. Removes the old remote-agents directory
    3. Updates configuration.yaml if it references the old path

    Returns:
        True if migration succeeded.
    """
    old_cache_dir = Path.home() / ".claude-mpm" / "cache" / "remote-agents"
    new_cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"

    try:
        # Count files before migration for verbose output
        file_count = _count_files_in_dir(old_cache_dir)
        print(f"   Before: ~/.claude-mpm/cache/remote-agents/ ({file_count} files)")

        # Step 1: Move directory contents
        if old_cache_dir.exists():
            # Ensure parent directory exists
            new_cache_dir.parent.mkdir(parents=True, exist_ok=True)

            if new_cache_dir.exists():
                # Merge: move contents from old to new
                for item in old_cache_dir.iterdir():
                    dest = new_cache_dir / item.name
                    if not dest.exists():
                        shutil.move(str(item), str(dest))
                # Remove old directory after moving contents
                shutil.rmtree(old_cache_dir, ignore_errors=True)
            else:
                # Simple rename if new dir doesn't exist
                shutil.move(str(old_cache_dir), str(new_cache_dir))

            logger.debug(
                f"Moved cache directory from {old_cache_dir} to {new_cache_dir}"
            )

        # Step 2: Update configuration.yaml if needed
        _update_configuration_cache_path()

        print("   After:  ~/.claude-mpm/cache/agents/")
        print("   ✓ Migration complete")

        return True

    except Exception as e:
        logger.warning(f"Cache directory migration failed: {e}")
        print(f"   ✗ Migration failed: {e}")
        return False


def _update_configuration_cache_path() -> None:
    """Update configuration.yaml to use new cache path if it references old path."""
    config_file = Path.home() / ".claude-mpm" / "configuration.yaml"
    if not config_file.exists():
        return

    try:
        with open(config_file) as f:
            content = f.read()

        old_path_pattern = "/.claude-mpm/cache/remote-agents"
        new_path_pattern = "/.claude-mpm/cache/agents"

        if old_path_pattern in content:
            updated_content = content.replace(old_path_pattern, new_path_pattern)
            with open(config_file, "w") as f:
                f.write(updated_content)
            logger.debug("Updated configuration.yaml cache_dir path")

    except Exception as e:
        logger.debug(f"Failed to update configuration.yaml: {e}")


# =============================================================================
# Migration: v5.6.80-clean-user-hooks
# =============================================================================


def _check_user_hooks_cleanup_needed() -> bool:
    """Check if user-level hooks contain duplicates.

    Returns:
        True if ~/.claude/settings.local.json has duplicate hook entries.
    """
    settings_file = Path.home() / ".claude" / "settings.local.json"
    if not settings_file.exists():
        return False

    try:
        with open(settings_file) as f:
            data = json.load(f)

        hooks = data.get("hooks", {})
        if not hooks:
            return False

        # Check each hook type for duplicates
        for hook_type, hook_list in hooks.items():
            if not isinstance(hook_list, list):
                continue

            # Collect all commands seen in this hook type
            seen_commands = set()
            for hook_entry in hook_list:
                if not isinstance(hook_entry, dict):
                    continue

                hook_commands = hook_entry.get("hooks", [])
                if not isinstance(hook_commands, list):
                    continue

                for cmd_entry in hook_commands:
                    if isinstance(cmd_entry, dict):
                        cmd = cmd_entry.get("command")
                        if cmd and cmd in seen_commands:
                            return True  # Found duplicate
                        if cmd:
                            seen_commands.add(cmd)

        return False

    except Exception as e:
        logger.debug(f"Failed to check user hooks: {e}")
        return False


def _clean_user_level_hooks() -> bool:
    """Clean duplicate hooks from ~/.claude/settings.local.json.

    This migration:
    1. Loads the user-level settings file
    2. Removes duplicate hook entries (keeping only first occurrence)
    3. Keeps the 'claude-hook' command intact
    4. Saves the cleaned configuration

    Returns:
        True if migration succeeded.
    """
    settings_file = Path.home() / ".claude" / "settings.local.json"

    if not settings_file.exists():
        print("   Cleaning user-level hooks... (none found)")
        return True

    try:
        with open(settings_file) as f:
            data = json.load(f)

        hooks = data.get("hooks", {})
        if not hooks:
            print("   Cleaning user-level hooks... (none found)")
            return True

        removed_count = 0

        # Clean each hook type
        for hook_type, hook_list in hooks.items():
            if not isinstance(hook_list, list):
                continue

            seen_commands = {}  # Track seen commands and their indices
            indices_to_remove = []

            for idx, hook_entry in enumerate(hook_list):
                if not isinstance(hook_entry, dict):
                    continue

                hook_commands = hook_entry.get("hooks", [])
                if not isinstance(hook_commands, list):
                    continue

                # Check for duplicate commands within this matcher
                for cmd_entry in hook_commands:
                    if isinstance(cmd_entry, dict):
                        cmd = cmd_entry.get("command")
                        if cmd:
                            if cmd in seen_commands:
                                # Mark this hook entry for removal
                                if idx not in indices_to_remove:
                                    indices_to_remove.append(idx)
                                    removed_count += 1
                            else:
                                seen_commands[cmd] = idx

            # Remove duplicate hook entries (in reverse order to maintain indices)
            for idx in sorted(indices_to_remove, reverse=True):
                hook_list.pop(idx)

        if removed_count > 0:
            with open(settings_file, "w") as f:
                json.dump(data, f, indent=4)
            print(f"   Cleaning user-level hooks... ({removed_count} removed)")
            logger.info(f"Cleaned {removed_count} duplicate hook entries")
        else:
            print("   Cleaning user-level hooks... (none found)")

        return True

    except Exception as e:
        logger.warning(f"Failed to clean user-level hooks: {e}")
        print(f"   ✗ Cleaning failed: {e}")
        return False


# =============================================================================
# Migration: v5.6.83-remove-hook-handler-sh
# =============================================================================


def _check_hook_handler_sh_exists() -> bool:
    """Check if any hooks contain claude-hook-handler.sh.

    Returns:
        True if claude-hook-handler.sh is found in any hook configuration.
    """
    # Check both user-level and project-level settings
    settings_files = [
        Path.home() / ".claude" / "settings.local.json",
        Path.cwd() / ".claude" / "settings.local.json",
    ]

    for settings_file in settings_files:
        if not settings_file.exists():
            continue

        try:
            with open(settings_file) as f:
                content = f.read()
                if "claude-hook-handler.sh" in content:
                    return True
        except Exception as e:
            logger.debug(f"Failed to check {settings_file}: {e}")
            continue

    return False


def _remove_hook_handler_sh() -> bool:
    """Remove claude-hook-handler.sh from hook configurations.

    This migration:
    1. Finds all settings files with claude-hook-handler.sh
    2. Removes those hook entries
    3. Optionally updates matchers to be more selective

    Returns:
        True if migration succeeded.
    """
    settings_files = [
        Path.home() / ".claude" / "settings.local.json",
        Path.cwd() / ".claude" / "settings.local.json",
    ]

    total_removed = 0

    for settings_file in settings_files:
        if not settings_file.exists():
            continue

        try:
            with open(settings_file) as f:
                data = json.load(f)

            hooks = data.get("hooks", {})
            if not hooks:
                continue

            file_removed = 0

            # Clean each hook type
            for hook_type, hook_list in hooks.items():
                if not isinstance(hook_list, list):
                    continue

                for hook_entry in hook_list:
                    if not isinstance(hook_entry, dict):
                        continue

                    hook_commands = hook_entry.get("hooks", [])
                    if not isinstance(hook_commands, list):
                        continue

                    # Filter out claude-hook-handler.sh commands
                    original_len = len(hook_commands)
                    hook_entry["hooks"] = [
                        cmd
                        for cmd in hook_commands
                        if not (
                            isinstance(cmd, dict)
                            and "claude-hook-handler.sh" in cmd.get("command", "")
                        )
                    ]
                    file_removed += original_len - len(hook_entry["hooks"])

            if file_removed > 0:
                with open(settings_file, "w") as f:
                    json.dump(data, f, indent=2)
                total_removed += file_removed
                logger.info(
                    f"Removed {file_removed} hook-handler.sh entries from {settings_file}"
                )

        except Exception as e:
            logger.warning(f"Failed to clean {settings_file}: {e}")
            continue

    if total_removed > 0:
        print(f"   Removed {total_removed} claude-hook-handler.sh entries")
    else:
        print("   No claude-hook-handler.sh entries found")

    print("   ✓ Migration complete")
    return True


# =============================================================================
# Migration: v5.6.86-upgrade-to-fast-hook
# =============================================================================


def _check_needs_fast_hook_upgrade() -> bool:
    """Check if hooks need upgrading to the fast bash hook.

    Returns:
        True if any hook uses claude-hook entry point or slow handler,
        but not the fast hook.
    """
    settings_files = [
        Path.home() / ".claude" / "settings.local.json",
        Path.cwd() / ".claude" / "settings.local.json",
    ]

    for settings_file in settings_files:
        if not settings_file.exists():
            continue

        try:
            with open(settings_file) as f:
                content = f.read()
                # Check if using old hooks but not fast hook
                has_old_hooks = (
                    '"claude-hook"' in content or "claude-hook-handler.sh" in content
                )
                has_fast_hook = "claude-hook-fast.sh" in content

                if has_old_hooks and not has_fast_hook:
                    return True
        except Exception as e:
            logger.debug(f"Failed to check {settings_file}: {e}")
            continue

    return False


def _upgrade_to_fast_hook() -> bool:
    """Upgrade hooks to use the fast bash hook.

    This migration:
    1. Finds all settings files with old hook commands
    2. Replaces them with the fast hook path
    3. Preserves other hook settings

    Returns:
        True if migration succeeded.
    """
    # Get the fast hook path
    try:
        from ..hooks.claude_hooks.installer import HookInstaller

        installer = HookInstaller()
        fast_hook_path = str(installer._get_fast_hook_script_path().absolute())
    except Exception as e:
        logger.warning(f"Could not get fast hook path: {e}")
        return False

    settings_files = [
        Path.home() / ".claude" / "settings.local.json",
        Path.cwd() / ".claude" / "settings.local.json",
    ]

    total_upgraded = 0

    for settings_file in settings_files:
        if not settings_file.exists():
            continue

        try:
            with open(settings_file) as f:
                data = json.load(f)

            hooks = data.get("hooks", {})
            if not hooks:
                continue

            file_upgraded = 0

            # Upgrade each hook type
            for hook_type, hook_list in hooks.items():
                if not isinstance(hook_list, list):
                    continue

                for hook_entry in hook_list:
                    if not isinstance(hook_entry, dict):
                        continue

                    hook_commands = hook_entry.get("hooks", [])
                    if not isinstance(hook_commands, list):
                        continue

                    # Upgrade old hook commands to fast hook
                    for cmd in hook_commands:
                        if not isinstance(cmd, dict):
                            continue
                        command = cmd.get("command", "")
                        if (
                            command == "claude-hook"
                            or "claude-hook-handler.sh" in command
                        ):
                            cmd["command"] = fast_hook_path
                            file_upgraded += 1

            if file_upgraded > 0:
                with open(settings_file, "w") as f:
                    json.dump(data, f, indent=2)
                total_upgraded += file_upgraded
                logger.info(
                    f"Upgraded {file_upgraded} hooks to fast hook in {settings_file}"
                )

        except Exception as e:
            logger.warning(f"Failed to upgrade hooks in {settings_file}: {e}")
            continue

    if total_upgraded > 0:
        print(f"   Upgraded {total_upgraded} hooks to fast bash hook (~52x faster)")
    else:
        print("   No hooks needed upgrading")

    print("   ✓ Migration complete")
    return True


# =============================================================================
# Migration Registry
# =============================================================================

MIGRATIONS: list[Migration] = [
    Migration(
        id="v5.6.76-cache-dir-rename",
        description="Rename remote-agents cache dir to agents",
        check=_check_cache_dir_rename_needed,
        migrate=_migrate_cache_dir_rename,
    ),
    Migration(
        id="v5.6.80-clean-user-hooks",
        description="Clean duplicate user-level hooks",
        check=_check_user_hooks_cleanup_needed,
        migrate=_clean_user_level_hooks,
    ),
    Migration(
        id="v5.6.83-remove-hook-handler-sh",
        description="Remove deprecated claude-hook-handler.sh",
        check=_check_hook_handler_sh_exists,
        migrate=_remove_hook_handler_sh,
    ),
    Migration(
        id="v5.6.86-upgrade-to-fast-hook",
        description="Upgrade hooks to fast bash hook (52x faster)",
        check=_check_needs_fast_hook_upgrade,
        migrate=_upgrade_to_fast_hook,
    ),
]


def run_migrations() -> list[str]:
    """Run all pending startup migrations.

    This function:
    1. Iterates through the migration registry
    2. Skips already-completed migrations
    3. Checks if each migration is needed
    4. Runs the migration if needed
    5. Tracks completed migrations

    Errors are logged but do not stop startup.

    Returns:
        List of migration descriptions that were successfully applied.
        Empty list if no migrations were needed or all failed.
    """
    applied_migrations: list[str] = []

    for migration in MIGRATIONS:
        try:
            # Skip if already completed
            if _is_migration_completed(migration.id):
                continue

            # Check if migration is needed
            if not migration.check():
                # Mark as completed even if not needed (condition doesn't apply)
                _save_completed_migration(migration.id)
                continue

            # Run the migration
            print(f"⚙️  Running startup migration: {migration.description}")
            logger.info(f"Running startup migration: {migration.id}")

            success = migration.migrate()

            if success:
                _save_completed_migration(migration.id)
                logger.info(f"Migration {migration.id} completed successfully")
                applied_migrations.append(migration.description)
            else:
                logger.warning(f"Migration {migration.id} failed")

        except Exception as e:
            # Non-blocking: log and continue
            logger.warning(f"Migration {migration.id} error: {e}")
            continue

    return applied_migrations
