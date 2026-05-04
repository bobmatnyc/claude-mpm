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
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

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
        {"id": migration_id, "completed_at": datetime.now(UTC).isoformat()}
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
    # Check global, user-level, and project-level settings
    settings_files = [
        Path.home() / ".claude" / "settings.json",  # global settings
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
        Path.home() / ".claude" / "settings.json",  # global settings
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
# Migration: v5.9.41-clean-stale-hook-paths
# =============================================================================

# Events that are NOT valid Claude Code hook events and should be removed
_INVALID_HOOK_EVENTS = frozenset(["SubagentStart"])


def _check_stale_hook_paths_exist() -> bool:
    """Check if any settings files contain stale hook paths or invalid events.

    A hook path is stale when the script it references no longer exists on
    disk (e.g., after a Python version upgrade that changes site-packages
    paths). ``SubagentStart`` is also not a valid Claude Code event and
    should be removed if present.

    Returns:
        True if stale entries are found in any settings file.
    """
    settings_files = [
        Path.home() / ".claude" / "settings.json",  # global settings
        Path.home() / ".claude" / "settings.local.json",
        Path.cwd() / ".claude" / "settings.local.json",
    ]

    for settings_file in settings_files:
        if not settings_file.exists():
            continue

        try:
            with open(settings_file) as f:
                data = json.load(f)

            hooks = data.get("hooks", {})
            if not hooks:
                continue

            # Check for invalid event names
            for event_type in hooks:
                if event_type in _INVALID_HOOK_EVENTS:
                    logger.debug(
                        f"Found invalid hook event '{event_type}' in {settings_file}"
                    )
                    return True

            # Check each hook command path for existence
            for hook_type, hook_list in hooks.items():
                if not isinstance(hook_list, list):
                    continue

                for hook_entry in hook_list:
                    if not isinstance(hook_entry, dict):
                        continue

                    hook_commands = hook_entry.get("hooks", [])
                    if not isinstance(hook_commands, list):
                        continue

                    for cmd_entry in hook_commands:
                        if not isinstance(cmd_entry, dict):
                            continue
                        command = cmd_entry.get("command", "")
                        # Only validate absolute paths — entry-point style
                        # commands (e.g. "claude-hook") are looked up via PATH
                        # and cannot be stat-checked here.
                        if command.startswith("/") and not Path(command).exists():
                            logger.debug(
                                f"Found stale hook path '{command}' in {settings_file}"
                            )
                            return True

        except Exception as e:
            logger.debug(f"Failed to check {settings_file}: {e}")
            continue

    return False


def _clean_stale_hook_paths() -> bool:
    """Remove stale hook paths and invalid events from all settings files.

    This migration:
    1. Scans ~/.claude/settings.json, ~/.claude/settings.local.json, and
       .claude/settings.local.json for hook entries.
    2. Removes any hook command entry whose absolute script path does not
       exist on disk (handles Python version upgrades that invalidate
       site-packages paths).
    3. Removes entire event keys that are not valid Claude Code events
       (currently only ``SubagentStart``).
    4. Removes hook_entry dicts that become empty after filtering.

    The migration is idempotent — running it on an already-clean file is
    a no-op.

    Returns:
        True if the migration ran without fatal errors.
    """
    settings_files = [
        Path.home() / ".claude" / "settings.json",  # global settings
        Path.home() / ".claude" / "settings.local.json",
        Path.cwd() / ".claude" / "settings.local.json",
    ]

    total_removed_paths = 0
    total_removed_events = 0

    for settings_file in settings_files:
        if not settings_file.exists():
            continue

        try:
            with open(settings_file) as f:
                data = json.load(f)

            hooks = data.get("hooks", {})
            if not hooks:
                continue

            file_changed = False
            removed_paths = 0
            removed_events = 0

            # Step 1: Remove invalid event keys entirely (e.g. SubagentStart)
            for event_type in list(hooks.keys()):
                if event_type in _INVALID_HOOK_EVENTS:
                    del hooks[event_type]
                    file_changed = True
                    removed_events += 1
                    logger.info(
                        f"Removed invalid hook event '{event_type}' from {settings_file}"
                    )

            # Step 2: Remove hook command entries with non-existent absolute paths
            for hook_type, hook_list in hooks.items():
                if not isinstance(hook_list, list):
                    continue

                for hook_entry in hook_list:
                    if not isinstance(hook_entry, dict):
                        continue

                    hook_commands = hook_entry.get("hooks", [])
                    if not isinstance(hook_commands, list):
                        continue

                    original_len = len(hook_commands)
                    hook_entry["hooks"] = [
                        cmd
                        for cmd in hook_commands
                        if not (
                            isinstance(cmd, dict)
                            and cmd.get("command", "").startswith("/")
                            and not Path(cmd["command"]).exists()
                        )
                    ]
                    delta = original_len - len(hook_entry["hooks"])
                    if delta:
                        removed_paths += delta
                        file_changed = True

            # Step 3: Prune hook_entry dicts that are now empty (no hooks left)
            for hook_type in list(hooks.keys()):
                hook_list = hooks[hook_type]
                if not isinstance(hook_list, list):
                    continue
                hooks[hook_type] = [
                    entry
                    for entry in hook_list
                    if isinstance(entry, dict) and entry.get("hooks")
                ]

            if file_changed:
                with open(settings_file, "w") as f:
                    json.dump(data, f, indent=2)
                total_removed_paths += removed_paths
                total_removed_events += removed_events
                logger.info(
                    f"Cleaned {settings_file}: "
                    f"{removed_paths} stale path(s), "
                    f"{removed_events} invalid event(s) removed"
                )

        except Exception as e:
            logger.warning(f"Failed to clean stale hooks in {settings_file}: {e}")
            continue

    if total_removed_paths or total_removed_events:
        print(
            f"   Removed {total_removed_paths} stale hook path(s) and "
            f"{total_removed_events} invalid event(s)"
        )
    else:
        print("   No stale hook paths or invalid events found")

    print("   ✓ Migration complete")
    return True


# =============================================================================
# Migration: v5.9.48-remove-unsupported-hook-events
# =============================================================================

# Hook event types added in Claude Code v2.1.47 that older versions reject
_NEW_HOOK_EVENTS = [
    "WorktreeCreate",
    "WorktreeRemove",
    "TeammateIdle",
    "TaskCompleted",
    "ConfigChange",
]


def _check_unsupported_hooks_exist() -> bool:
    """Check if any settings files contain v2.1.47+ hook events on an older install.

    Returns:
        True if unsupported hook events are found AND Claude Code < 2.1.47.
    """
    # If Claude Code supports these hooks, nothing to clean up
    try:
        from ..hooks.claude_hooks.installer import HookInstaller

        installer = HookInstaller()
        if installer.supports_new_hooks():
            return False
    except Exception:
        pass  # Unknown version — be conservative and check files anyway

    settings_files = [
        Path.home() / ".claude" / "settings.json",
        Path.home() / ".claude" / "settings.local.json",
        Path.cwd() / ".claude" / "settings.local.json",
    ]

    for settings_file in settings_files:
        if not settings_file.exists():
            continue

        try:
            with open(settings_file) as f:
                data = json.load(f)

            hooks = data.get("hooks", {})
            for event_type in _NEW_HOOK_EVENTS:
                if event_type in hooks:
                    logger.debug(
                        f"Found unsupported hook event '{event_type}' in {settings_file}"
                    )
                    return True
        except Exception as e:
            logger.debug(f"Failed to check {settings_file}: {e}")
            continue

    return False


def _remove_unsupported_hook_events() -> bool:
    """Remove v2.1.47+ hook events from all Claude settings files.

    These events cause "Invalid key in record" warnings at startup on
    Claude Code versions older than v2.1.47.

    Returns:
        True if migration succeeded.
    """
    settings_files = [
        Path.home() / ".claude" / "settings.json",
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
            removed = []
            for event_type in _NEW_HOOK_EVENTS:
                if event_type in hooks:
                    del hooks[event_type]
                    removed.append(event_type)

            if removed:
                with open(settings_file, "w") as f:
                    json.dump(data, f, indent=2)
                total_removed += len(removed)
                logger.info(
                    f"Removed unsupported hook events {removed} from {settings_file}"
                )

        except Exception as e:
            logger.warning(f"Failed to clean unsupported hooks in {settings_file}: {e}")
            continue

    if total_removed > 0:
        print(
            f"   Removed {total_removed} unsupported hook event(s) "
            f"(WorktreeCreate, WorktreeRemove, TeammateIdle, TaskCompleted, ConfigChange)"
        )
    else:
        print("   No unsupported hook events found")

    print("   ✓ Migration complete")
    return True


# =============================================================================
# Migration: v5.12.0-binary-consolidation
# =============================================================================


def _check_binary_consolidation_needed() -> bool:
    """Check if .mcp.json has old-format binary/module invocations.

    Returns:
        True if any server entry uses deprecated invocation patterns.
    """
    try:
        from ..migrations.migrate_binary_consolidation import check_needs_migration

        return check_needs_migration()
    except Exception as e:
        logger.debug(f"Failed to check binary consolidation: {e}")
        return False


def _migrate_binary_consolidation() -> bool:
    """Migrate .mcp.json from old binary/module invocations to consolidated format.

    Updates server entries to use 'claude-mpm mcp serve <name>' instead of
    deprecated standalone binaries or 'python -m' invocations.

    Returns:
        True if migration succeeded.
    """
    try:
        from ..migrations.migrate_binary_consolidation import run_migration

        return run_migration()
    except Exception as e:
        logger.warning(f"Binary consolidation migration failed: {e}")
        print(f"   Migration failed: {e}")
        return False


# =============================================================================
# Migration: v6.3.2-deploy-spinner-global
# =============================================================================

# Spinner-related keys that should be deployed to ~/.claude/settings.json so
# that MPM-themed spinner verbs and tips appear even when Claude Code is run
# outside a claude-mpm project (or in a project where the project-level
# deploy-claude-assets migration has not yet run).
_SPINNER_GLOBAL_KEYS: tuple[str, ...] = (
    "spinnerVerbs",
    "spinnerTipsEnabled",
    "spinnerTipsOverride",
)

# Tracking key written into ~/.claude/settings.json to record which template
# version of the spinner config has been deployed at the user-global level.
# Distinct from the project-level ``_mpm_version`` so it never collides with
# the project-level deploy-claude-assets migration.
_SPINNER_GLOBAL_VERSION_KEY = "_mpm_spinner_version"


def _check_spinner_global_needed() -> bool:
    """Check if spinner config needs to be deployed/updated in ~/.claude/settings.json.

    Returns:
        True if spinner keys are missing from ~/.claude/settings.json or if
        the deployed spinner template version is older than the bundled
        template version.
    """
    templates = _get_claude_assets_templates_dir()
    settings_template = templates / "settings.json"
    if not settings_template.exists():
        return False

    try:
        template_data = json.loads(settings_template.read_text())
    except Exception as exc:
        logger.debug("Failed to read settings template for spinner check: %s", exc)
        return False

    template_version = str(template_data.get("_mpm_version", "0.0.0"))

    user_settings = Path.home() / ".claude" / "settings.json"
    if not user_settings.exists():
        # Will be created during migration if any spinner keys exist in template
        return any(k in template_data for k in _SPINNER_GLOBAL_KEYS)

    try:
        existing = json.loads(user_settings.read_text())
    except Exception as exc:
        logger.debug("Failed to read user settings.json: %s", exc)
        # Be conservative: if we can't parse it, don't try to merge into it
        return False

    # Missing any spinner key → deploy
    for key in _SPINNER_GLOBAL_KEYS:
        if key in template_data and key not in existing:
            return True

    # Outdated tracking version → re-deploy
    existing_version = str(existing.get(_SPINNER_GLOBAL_VERSION_KEY, "0.0.0"))
    if existing_version < template_version:
        # Only need to redeploy if the template actually defines spinner keys
        return any(k in template_data for k in _SPINNER_GLOBAL_KEYS)

    return False


def _deploy_spinner_global() -> bool:
    """Deploy spinner-related keys from the bundled template into ~/.claude/settings.json.

    Behaviour:
    1. Reads the bundled ``settings.json`` template.
    2. Extracts only the keys listed in ``_SPINNER_GLOBAL_KEYS``.
    3. Merges those keys into ``~/.claude/settings.json``:
       - Creates the file (and parent dir) if absent.
       - Adds spinner keys that are missing.
       - Updates spinner keys when the template's ``_mpm_version`` is newer
         than ``_mpm_spinner_version`` recorded in the user settings.
       - Leaves every other key in the user file untouched.
    4. Writes ``_mpm_spinner_version`` to track the deployed template version.

    Returns:
        True on success (including idempotent no-op runs).
    """
    templates = _get_claude_assets_templates_dir()
    settings_template = templates / "settings.json"
    if not settings_template.exists():
        logger.warning(
            "settings.json template not found at %s — skipping", settings_template
        )
        print("   Template settings.json not found — skipping")
        return False

    try:
        template_data = json.loads(settings_template.read_text())
    except Exception as exc:
        logger.warning("Failed to parse settings template: %s", exc)
        print(f"   Failed to parse settings template: {exc}")
        return False

    template_version = str(template_data.get("_mpm_version", "0.0.0"))
    spinner_payload: dict = {
        key: template_data[key] for key in _SPINNER_GLOBAL_KEYS if key in template_data
    }

    if not spinner_payload:
        print("   Template has no spinner keys — nothing to deploy")
        return True

    user_settings = Path.home() / ".claude" / "settings.json"
    existing: dict = {}
    if user_settings.exists():
        try:
            existing = json.loads(user_settings.read_text())
        except json.JSONDecodeError as exc:
            logger.warning(
                "Refusing to merge into malformed %s: %s — aborting", user_settings, exc
            )
            print(
                f"   Refusing to overwrite malformed {user_settings.name}; "
                "fix it manually and re-run."
            )
            return False

    if not isinstance(existing, dict):
        logger.warning(
            "User settings is not a JSON object (got %s) — aborting", type(existing)
        )
        print("   ~/.claude/settings.json is not a JSON object — skipping")
        return False

    existing_version = str(existing.get(_SPINNER_GLOBAL_VERSION_KEY, "0.0.0"))
    template_is_newer = existing_version < template_version

    updated = dict(existing)
    changed_keys: list[str] = []
    for key, value in spinner_payload.items():
        if key not in updated or template_is_newer:
            updated[key] = value
            changed_keys.append(key)

    if not changed_keys and existing_version == template_version:
        print("   Spinner config already up-to-date in ~/.claude/settings.json")
        return True

    # Always stamp the version when we touch the file so subsequent runs are
    # truly idempotent.
    updated[_SPINNER_GLOBAL_VERSION_KEY] = template_version

    try:
        user_settings.parent.mkdir(parents=True, exist_ok=True)
        user_settings.write_text(json.dumps(updated, indent=2) + "\n")
    except OSError as exc:
        logger.warning("Failed to write %s: %s", user_settings, exc)
        print(f"   Failed to write {user_settings}: {exc}")
        return False

    if changed_keys:
        print(
            f"   Deployed {len(changed_keys)} spinner key(s) to "
            f"~/.claude/settings.json: {', '.join(sorted(changed_keys))}"
        )
    else:
        print("   Refreshed spinner version stamp in ~/.claude/settings.json")
    print("   ✓ Migration complete")
    return True


# =============================================================================
# Migration Registry
# =============================================================================

_CLAUDE_CODE_FOOTER_OLD = "Generated with [Claude Code](https://claude.ai/code)"
_CLAUDE_CODE_FOOTER_OLD_ALT = (
    "Generated with [Claude Code](https://claude.com/claude-code)"
)
_CLAUDE_MPM_FOOTER_NEW = (
    "🤖🤖 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)"
)


def _check_claude_code_footer_in_agents() -> bool:
    """Check if any deployed agent files still have the old Claude Code footer.

    Returns:
        True if old footer text is found in any agent markdown file.
    """
    search_dirs = [
        Path.home() / ".claude" / "agents",
        Path.home() / ".claude-mpm" / "cache" / "agents",
    ]
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for md_file in search_dir.glob("**/*.md"):
            try:
                content = md_file.read_text(encoding="utf-8", errors="ignore")
                if (
                    _CLAUDE_CODE_FOOTER_OLD in content
                    or _CLAUDE_CODE_FOOTER_OLD_ALT in content
                ):
                    return True
            except OSError:
                continue
    return False


def _replace_claude_code_footers_in_agents() -> bool:
    """Replace Claude Code footers with Claude MPM footers in deployed agent files.

    Scans ~/.claude/agents/ and ~/.claude-mpm/cache/agents/ for agent markdown
    files containing the old "Generated with [Claude Code]" footer and replaces
    them with "🤖🤖 Generated with [Claude MPM]".

    Returns:
        True if migration succeeded (or no files needed updating).
    """
    search_dirs = [
        Path.home() / ".claude" / "agents",
        Path.home() / ".claude-mpm" / "cache" / "agents",
    ]
    updated = 0
    errors = 0
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for md_file in search_dir.glob("**/*.md"):
            try:
                content = md_file.read_text(encoding="utf-8", errors="ignore")
                new_content = content.replace(
                    _CLAUDE_CODE_FOOTER_OLD, _CLAUDE_MPM_FOOTER_NEW
                )
                new_content = new_content.replace(
                    _CLAUDE_CODE_FOOTER_OLD_ALT, _CLAUDE_MPM_FOOTER_NEW
                )
                if new_content != content:
                    md_file.write_text(new_content, encoding="utf-8")
                    updated += 1
                    logger.debug(f"Updated footer in {md_file}")
            except OSError as e:
                logger.debug(f"Could not update {md_file}: {e}")
                errors += 1
    logger.info(f"Footer migration: updated {updated} files, {errors} errors")
    return errors == 0


# =============================================================================
# Migration: v5.10.0-standardize-agent-names
# =============================================================================

# Old agent filenames that were renamed in the agents repository
_STALE_AGENT_FILES = [
    "tmux-agent.md",  # renamed to tmux.md
    "content-agent.md",  # renamed to content.md
    "memory-manager-agent.md",  # renamed to memory-manager.md
    "web-ui.md",  # renamed to web-ui-engineer.md
]


def _check_agent_naming_migration_needed() -> bool:
    """Check if any stale agent files from the naming standardization exist.

    Checks the current project's .claude/agents/ directory for old-named
    agent files that have been renamed in the agents repository.

    Returns:
        True if any stale files exist in .claude/agents/
    """
    agents_dir = Path.cwd() / ".claude" / "agents"
    if not agents_dir.exists():
        return False

    return any((agents_dir / stale_file).exists() for stale_file in _STALE_AGENT_FILES)


def _migrate_agent_naming_standardization() -> bool:
    """Remove old-format agent files replaced by standardized naming.

    This migration removes the 4 agent files that were renamed in the
    agents repository naming standardization:
    - tmux-agent.md → tmux.md
    - content-agent.md → content.md
    - memory-manager-agent.md → memory-manager.md
    - web-ui.md → web-ui-engineer.md

    Only removes files that:
    1. Match the known stale filenames
    2. Are MPM-managed (author: claude-mpm in frontmatter)
    3. Actually exist in .claude/agents/

    Returns:
        True if migration succeeded (even if no files needed removing)
    """
    from claude_mpm.utils.agent_provenance import is_mpm_managed_agent

    agents_dir = Path.cwd() / ".claude" / "agents"
    if not agents_dir.exists():
        print("   No .claude/agents/ directory found")
        print("   ✓ Migration complete (no action needed)")
        return True

    removed = []
    preserved = []
    errors = []

    for stale_filename in _STALE_AGENT_FILES:
        stale_file = agents_dir / stale_filename
        if not stale_file.exists():
            continue

        try:
            content = stale_file.read_text(encoding="utf-8")

            # Safety: Only remove if it's an MPM agent
            if is_mpm_managed_agent(content):
                stale_file.unlink()
                removed.append(stale_filename)
                logger.info(f"Removed stale agent file: {stale_filename}")
            else:
                preserved.append(stale_filename)
                logger.info(f"Preserved user agent with stale name: {stale_filename}")
        except Exception as e:
            error_msg = f"Failed to process {stale_filename}: {e}"
            errors.append(error_msg)
            logger.warning(error_msg)

    # Report results
    if removed:
        print(f"   Removed {len(removed)} stale agent file(s): {', '.join(removed)}")
    if preserved:
        print(
            f"   Preserved {len(preserved)} user agent(s) with old names: "
            f"{', '.join(preserved)}"
        )
    if errors:
        print(f"   ⚠ {len(errors)} error(s) during cleanup")
    if not removed and not preserved and not errors:
        print("   No stale agent files found")

    print("   ✓ Migration complete")
    return len(errors) == 0


# Module-level cache for plugin scope check results (populated by check, used by migrate)
_plugin_scope_check_result: dict = {}


def _get_installed_plugins_file() -> Path:
    """Get the path to Claude Code's global plugin installation registry."""
    return Path.home() / ".claude" / "plugins" / "installed_plugins.json"


def _load_installed_plugins() -> dict:
    """Load installed plugins JSON.

    Returns:
        Parsed JSON dict, or empty structure on error/missing file.
    """
    plugins_file = _get_installed_plugins_file()
    if not plugins_file.exists():
        return {"version": 2, "plugins": {}}
    try:
        with open(plugins_file) as f:
            return json.load(f)
    except Exception as e:
        logger.debug(f"Failed to load installed_plugins.json: {e}")
        return {"version": 2, "plugins": {}}


def check_plugin_scope_v1() -> bool:
    """Check whether any user-scoped Claude Code plugins are foreign to this project.

    A plugin is considered "foreign" when:
    - It is installed at user scope (appears in every session), AND
    - Its name (the part before '@' in the plugin key) does NOT match the
      current project directory name.

    The check result is cached in _plugin_scope_check_result so that the
    migrate function can use it without re-parsing the file.

    Returns:
        True if at least one foreign user-scoped plugin is found.
    """
    global _plugin_scope_check_result

    project_name = Path.cwd().name
    data = _load_installed_plugins()
    plugins: dict = data.get("plugins", {})

    foreign: list[dict] = []
    for plugin_key, installations in plugins.items():
        plugin_name = plugin_key.split("@")[0]
        for entry in installations:
            if entry.get("scope") == "user" and plugin_name != project_name:
                foreign.append(
                    {
                        "key": plugin_key,
                        "name": plugin_name,
                        "entry": entry,
                    }
                )

    _plugin_scope_check_result = {
        "project_name": project_name,
        "foreign_plugins": foreign,
    }

    if foreign:
        logger.debug(
            f"Found {len(foreign)} user-scoped plugin(s) foreign to '{project_name}': "
            + ", ".join(p["key"] for p in foreign)
        )

    return len(foreign) > 0


def migrate_plugin_scope_v1() -> bool:
    """Offer to move foreign user-scoped plugins to project scope (opt-in).

    For each plugin identified by check_plugin_scope_v1, the user is prompted
    interactively. If confirmed, the plugin entry is:
    1. Removed from the user-scope list in the global installed_plugins.json
    2. Added as a project-scoped entry in {CWD}/.claude/plugins/installed_plugins.json

    This function is non-destructive: it always returns True (the migration is
    considered "done" once the user has been given the opportunity to act).

    Returns:
        True always (non-destructive; skipping a prompt is not a failure).
    """
    foreign_plugins: list[dict] = _plugin_scope_check_result.get("foreign_plugins", [])
    project_name: str = _plugin_scope_check_result.get("project_name", Path.cwd().name)

    if not foreign_plugins:
        return True

    global_plugins_file = _get_installed_plugins_file()
    project_plugins_file = Path.cwd() / ".claude" / "plugins" / "installed_plugins.json"

    # Load current global registry (may have changed since check)
    global_data = _load_installed_plugins()

    # Load or initialise project-level registry
    if project_plugins_file.exists():
        try:
            with open(project_plugins_file) as f:
                project_data: dict = json.load(f)
        except Exception:
            project_data = {"version": 2, "plugins": {}}
    else:
        project_data = {"version": 2, "plugins": {}}

    moved_any = False

    for plugin_info in foreign_plugins:
        plugin_key: str = plugin_info["key"]
        plugin_name: str = plugin_info["name"]
        original_entry: dict = plugin_info["entry"]

        try:
            answer = (
                input(
                    f"\n  Plugin '{plugin_name}' is user-scoped but not relevant to "
                    f"this project ('{project_name}').\n"
                    f"  Move to project-scope? [y/N] "
                )
                .strip()
                .lower()
            )
        except EOFError:
            # Non-interactive environment — skip silently
            answer = ""

        if answer != "y":
            logger.debug(f"Skipped scope move for plugin '{plugin_key}'")
            continue

        # Remove the user-scoped entry from the global registry
        global_installations: list = global_data.get("plugins", {}).get(plugin_key, [])
        updated_installations = [
            e
            for e in global_installations
            if not (
                e.get("scope") == "user"
                and e.get("installPath") == original_entry.get("installPath")
            )
        ]
        if updated_installations:
            global_data["plugins"][plugin_key] = updated_installations
        else:
            global_data["plugins"].pop(plugin_key, None)

        # Add a project-scoped entry in the project registry
        project_entry = dict(original_entry)
        project_entry["scope"] = "project"
        project_entry["projectPath"] = str(Path.cwd())

        project_plugins: dict = project_data.setdefault("plugins", {})
        existing_project_entries: list = project_plugins.get(plugin_key, [])
        # Avoid adding a duplicate project-scoped entry
        already_present = any(
            e.get("scope") == "project" and e.get("projectPath") == str(Path.cwd())
            for e in existing_project_entries
        )
        if not already_present:
            existing_project_entries.append(project_entry)
            project_plugins[plugin_key] = existing_project_entries

        moved_any = True
        print(f"   Moved '{plugin_name}' from user-scope to project-scope.")
        logger.info(
            f"Moved plugin '{plugin_key}' to project scope for '{project_name}'"
        )

    if moved_any:
        # Persist global registry changes
        try:
            with open(global_plugins_file, "w") as f:
                json.dump(global_data, f, indent=2)
            logger.debug(f"Updated global plugins registry: {global_plugins_file}")
        except Exception as e:
            logger.warning(f"Failed to write global plugins registry: {e}")
            print(f"   Warning: could not update global plugins file: {e}")

        # Persist project registry changes
        try:
            project_plugins_file.parent.mkdir(parents=True, exist_ok=True)
            with open(project_plugins_file, "w") as f:
                json.dump(project_data, f, indent=2)
            logger.debug(f"Updated project plugins registry: {project_plugins_file}")
        except Exception as e:
            logger.warning(f"Failed to write project plugins registry: {e}")
            print(f"   Warning: could not update project plugins file: {e}")
    else:
        print("   No plugins moved (all skipped or none selected).")

    print("   ✓ Plugin scope check complete")
    return True


# Explicit rename mapping for known mcp-named skills.
# Keys are current directory names; values are the desired names.
_MCP_SKILL_RENAME_MAP: dict[str, str] = {
    "mcp-vector-search": "vector-search",
    "mcp-vector-search-pr-mr-skill": "vector-search-pr-mr-skill",
    "toolchains-ai-protocols-mcp": "toolchains-ai-protocols-model-context",
    "universal-main-mcp-builder": "universal-main-protocol-builder",
}


def _get_target_skill_name(skill_name: str) -> str:
    """Return the canonical (mcp-free) name for a skill directory.

    Uses the explicit mapping first; falls back to replacing every occurrence
    of the substring "mcp" with "protocol".
    """
    if skill_name in _MCP_SKILL_RENAME_MAP:
        return _MCP_SKILL_RENAME_MAP[skill_name]
    return skill_name.replace("mcp", "protocol")


def _find_mcp_skill_dirs() -> list[tuple[Path, str]]:
    """Return (skills_dir, skill_name) pairs where the skill name contains 'mcp'.

    Scans both project-level (.claude/skills/) and user-level (~/.claude/skills/).
    Only directories are returned; regular files are ignored.
    """
    hits: list[tuple[Path, str]] = []
    candidates: list[Path] = [
        Path.cwd() / ".claude" / "skills",
        Path.home() / ".claude" / "skills",
    ]
    for skills_dir in candidates:
        if not skills_dir.is_dir():
            continue
        for entry in skills_dir.iterdir():
            if entry.is_dir() and "mcp" in entry.name:
                hits.append((skills_dir, entry.name))
    return hits


def _check_mcp_skills_need_rename() -> bool:
    """Return True if any skill directory contains 'mcp' in its name."""
    return bool(_find_mcp_skill_dirs())


def _rename_mcp_skills() -> bool:
    """Rename skill directories whose names contain 'mcp'.

    Uses _MCP_SKILL_RENAME_MAP for known names; for everything else replaces
    the substring "mcp" with "protocol".  The rename is idempotent: if the
    target directory already exists the source is left untouched and a warning
    is logged.

    Returns:
        True always (non-fatal; individual failures are logged).
    """
    hits = _find_mcp_skill_dirs()
    if not hits:
        print("   No mcp-named skill directories found.")
        return True

    for skills_dir, skill_name in hits:
        target_name = _get_target_skill_name(skill_name)
        src = skills_dir / skill_name
        dst = skills_dir / target_name

        if dst.exists():
            logger.warning(
                "Cannot rename skill '%s' → '%s': target already exists at %s",
                skill_name,
                target_name,
                dst,
            )
            print(f"   ⚠ Skipped '{skill_name}': '{target_name}' already exists.")
            continue

        try:
            src.rename(dst)
            print(f"   ✓ Renamed skill '{skill_name}' → '{target_name}'")
            logger.info(
                "Renamed skill directory '%s' → '%s' in %s",
                skill_name,
                target_name,
                skills_dir,
            )
        except OSError as exc:
            logger.warning("Failed to rename skill '%s': %s", skill_name, exc)
            print(f"   ⚠ Failed to rename '{skill_name}': {exc}")

    print("   ✓ MCP skill rename migration complete")
    return True


# =============================================================================
# Migration: v6.3.0-deploy-claude-assets
# =============================================================================

_DEPLOY_CLAUDE_ASSETS_VERSION = "6.3.0"


def _get_claude_assets_templates_dir() -> Path:
    """Return the path to the bundled .claude/ template directory."""
    try:
        import importlib.resources

        with importlib.resources.path("claude_mpm.templates", "claude") as p:
            return Path(p)
    except Exception:
        return Path(__file__).parent.parent / "templates" / "claude"


def _check_claude_assets_needed() -> bool:
    """Check if any .claude/ template assets are missing or settings needs update.

    Returns:
        True if any template file is absent in .claude/ or if settings.json
        needs an MPM version bump.
    """
    templates = _get_claude_assets_templates_dir()
    if not templates.exists():
        return False

    dot_claude = Path.cwd() / ".claude"

    # Check non-settings files
    for template_file in templates.rglob("*"):
        if not template_file.is_file():
            continue
        if template_file.name == "settings.json":
            continue
        rel = template_file.relative_to(templates)
        dest = dot_claude / rel
        if not dest.exists():
            return True

    # Check settings.json version
    settings_template = templates / "settings.json"
    if settings_template.exists():
        try:
            template_data = json.loads(settings_template.read_text())
            template_version = template_data.get("_mpm_version", "0.0.0")
            dest_settings = dot_claude / "settings.json"
            if dest_settings.exists():
                existing = json.loads(dest_settings.read_text())
                existing_version = existing.get("_mpm_version", "0.0.0")
                if existing_version < template_version:
                    return True
            else:
                return True
        except Exception:
            pass

    return False


def _merge_claude_settings(dest: Path, template: Path) -> bool:
    """Merge MPM-managed keys from template into dest settings.json.

    Only adds keys that are absent, or updates MPM-managed keys when the
    template version is newer than the existing version.  Never removes
    user-added keys.

    Args:
        dest: Destination settings.json path (may not exist yet).
        template: Source template settings.json path.

    Returns:
        True if the file was written (changed), False if no change was needed.
    """
    try:
        template_data = json.loads(template.read_text())
    except Exception as exc:
        logger.warning("Failed to read settings template: %s", exc)
        return False

    existing: dict = {}
    if dest.exists():
        try:
            existing = json.loads(dest.read_text())
        except json.JSONDecodeError:
            existing = {}

    updated = dict(existing)
    mpm_keys = {k for k in template_data if not k.startswith("_")}
    existing_version = existing.get("_mpm_version", "0.0.0")
    template_version = template_data.get("_mpm_version", "0.0.0")

    needs_update = False
    for key in mpm_keys:
        if key not in existing or (
            existing.get("_mpm_version") and existing_version < template_version
        ):
            updated[key] = template_data[key]
            needs_update = True

    if needs_update:
        updated["_mpm_managed"] = True
        updated["_mpm_version"] = template_version
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(updated, indent=2) + "\n")
        return True

    return False


def _deploy_claude_assets() -> bool:
    """Deploy .claude/ template assets (statusline, commands, settings) to cwd.

    Copies template files to .claude/ only when they are absent.  Never
    overwrites files that already exist (preserves user customisations).
    settings.json uses a merge strategy instead of overwrite.

    Returns:
        True if the migration ran without fatal errors.
    """
    import stat

    templates = _get_claude_assets_templates_dir()
    if not templates.exists():
        logger.warning("claude-assets template directory not found: %s", templates)
        print("   Template directory not found — skipping")
        return False

    dot_claude = Path.cwd() / ".claude"
    deployed = 0
    skipped = 0

    for template_file in templates.rglob("*"):
        if not template_file.is_file():
            continue
        if template_file.name == "settings.json":
            continue
        rel = template_file.relative_to(templates)
        dest = dot_claude / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            skipped += 1
            continue
        shutil.copy2(template_file, dest)
        if dest.suffix == ".sh":
            dest.chmod(dest.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        deployed += 1
        logger.info("Deployed asset: %s", rel)

    settings_template = templates / "settings.json"
    settings_changed = False
    if settings_template.exists():
        settings_changed = _merge_claude_settings(
            dot_claude / "settings.json", settings_template
        )
        if settings_changed:
            deployed += 1

    if deployed:
        print(
            f"   Deployed {deployed} asset(s) to .claude/ ({skipped} already present)"
        )
    else:
        print(f"   All assets already present ({skipped} checked)")

    print("   ✓ Migration complete")
    return True


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
    Migration(
        id="v5.9.41-clean-stale-hook-paths",
        description="Remove stale hook paths and invalid hook events from all settings files",
        check=_check_stale_hook_paths_exist,
        migrate=_clean_stale_hook_paths,
    ),
    Migration(
        id="v5.9.48-remove-unsupported-hook-events",
        description="Remove unsupported v2.1.47+ hook events (WorktreeCreate, WorktreeRemove, TeammateIdle, TaskCompleted, ConfigChange) from settings on Claude Code < 2.1.47",
        check=_check_unsupported_hooks_exist,
        migrate=_remove_unsupported_hook_events,
    ),
    Migration(
        id="v5.9.57-update-claude-code-footers",
        description="Replace 'Generated with Claude Code' footers with 'Generated with Claude MPM' in deployed agent files",
        check=_check_claude_code_footer_in_agents,
        migrate=_replace_claude_code_footers_in_agents,
    ),
    Migration(
        id="v5.10.0-standardize-agent-names",
        description="Remove old-format agent files replaced by naming standardization",
        check=_check_agent_naming_migration_needed,
        migrate=_migrate_agent_naming_standardization,
    ),
    Migration(
        id="v5.12.0-binary-consolidation",
        description="Migrate .mcp.json to consolidated 'claude-mpm mcp serve' format",
        check=_check_binary_consolidation_needed,
        migrate=_migrate_binary_consolidation,
    ),
    Migration(
        id="skill_scope_v1",
        description="Detect user-scoped Claude Code plugins bleeding into unrelated project sessions",
        check=check_plugin_scope_v1,
        migrate=migrate_plugin_scope_v1,
    ),
    Migration(
        id="v6.2.7-rename-mcp-skills",
        description="Rename skill directories whose names contain 'mcp' to avoid shadowing the native /mcp command",
        check=_check_mcp_skills_need_rename,
        migrate=_rename_mcp_skills,
    ),
    Migration(
        id="v6.3.0-deploy-claude-assets",
        description="Deploy .claude/ template assets (statusline.sh, slash commands, settings.json)",
        check=_check_claude_assets_needed,
        migrate=_deploy_claude_assets,
    ),
    Migration(
        id="v6.3.2-deploy-spinner-global",
        description="Deploy MPM spinner verbs/tips into ~/.claude/settings.json so they apply outside MPM projects",
        check=_check_spinner_global_needed,
        migrate=_deploy_spinner_global,
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
