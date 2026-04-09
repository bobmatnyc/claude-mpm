"""
Settings management commands for claude-mpm.

WHY: Provides tools to manage and clean Claude Code settings files,
including removing invalid hook keys that cause startup warnings.

DESIGN DECISIONS:
- Use patterns from startup_migrations.py for consistency
- Backup files before modification for safety
- Support both dry-run and actual cleanup modes
- Allow targeting specific files or scanning all settings files
"""

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from ...core.logging_utils import get_logger

logger = get_logger(__name__)


def add_settings_parser(subparsers):
    """Add settings command parser.

    WHY: Provides a namespace for settings-related operations, starting
    with hook cleanup but extensible for future settings management.
    """
    parser = subparsers.add_parser(
        "settings",
        help="Manage Claude Code settings files"
    )

    settings_subparsers = parser.add_subparsers(
        dest="settings_command",
        help="Settings subcommands"
    )

    # clean-hooks subcommand
    clean_hooks = settings_subparsers.add_parser(
        "clean-hooks",
        help="Remove invalid hook keys from settings files"
    )

    clean_hooks.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be removed without making changes"
    )

    clean_hooks.add_argument(
        "--file",
        type=Path,
        help="Clean a specific settings file (otherwise scans all)"
    )

    clean_hooks.set_defaults(func=settings_clean_hooks_command)


def settings_clean_hooks_command(args):
    """Clean invalid hook keys from settings files.

    WHY: Users upgrading or downgrading Claude Code versions may have
    incompatible hook keys that cause "Invalid key in record" warnings.

    Args:
        args: Command line arguments from argparse
    """
    # Core hook events supported by all Claude Code versions
    CORE_HOOK_EVENTS = frozenset([
        "PreToolUse", "PostToolUse", "Stop", "SubagentStop",
        "SessionStart", "UserPromptSubmit"
    ])

    # Hook events added in Claude Code v2.1.47+
    NEW_HOOK_EVENTS = frozenset([
        "WorktreeCreate", "WorktreeRemove", "TeammateIdle",
        "TaskCompleted", "ConfigChange"
    ])

    # Determine valid hook keys based on Claude Code version
    try:
        from ...hooks.claude_hooks.installer import HookInstaller
        installer = HookInstaller()
        if installer.supports_new_hooks():
            valid_keys = CORE_HOOK_EVENTS | NEW_HOOK_EVENTS
            print("✓ Claude Code v2.1.47+ detected - all hook events are valid")
        else:
            valid_keys = CORE_HOOK_EVENTS
            version = installer.get_claude_version() or "unknown"
            print(f"⚠ Claude Code {version} detected - v2.1.47+ hooks will be removed")
    except Exception as e:
        logger.warning(f"Could not determine Claude Code version: {e}")
        valid_keys = CORE_HOOK_EVENTS
        print("⚠ Could not determine Claude Code version - using conservative cleanup")

    # Determine which files to scan
    if args.file:
        settings_files = [args.file]
    else:
        settings_files = [
            Path.home() / ".claude" / "settings.json",
            Path.home() / ".claude" / "settings.local.json",
            Path.cwd() / ".claude" / "settings.local.json",
        ]

    total_removed = 0
    files_modified = 0

    for settings_file in settings_files:
        if not settings_file.exists():
            continue

        try:
            # Load settings file
            with open(settings_file) as f:
                data = json.load(f)

            hooks = data.get("hooks", {})
            if not hooks:
                continue

            # Find invalid keys
            invalid_keys = []
            for hook_key in list(hooks.keys()):
                if hook_key not in valid_keys:
                    invalid_keys.append(hook_key)

            if not invalid_keys:
                continue

            # Report findings
            print(f"\n📄 {settings_file}")
            for key in invalid_keys:
                hook_count = len(hooks[key]) if isinstance(hooks[key], list) else 1
                print(f"   ├─ {key}: {hook_count} hook(s)")

            if args.dry_run:
                print("   └─ [DRY RUN] Would remove these keys")
                total_removed += len(invalid_keys)
                continue

            # Backup file before modification
            backup_path = settings_file.with_suffix(
                f".backup.{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
            )
            shutil.copy2(settings_file, backup_path)
            logger.info(f"Created backup: {backup_path}")

            # Remove invalid keys
            for key in invalid_keys:
                del hooks[key]
                total_removed += 1

            # Write updated settings
            with open(settings_file, "w") as f:
                json.dump(data, f, indent=2)

            files_modified += 1
            print(f"   ✓ Removed {len(invalid_keys)} invalid key(s)")
            print(f"   └─ Backup saved: {backup_path.name}")

        except Exception as e:
            logger.error(f"Failed to process {settings_file}: {e}")
            print(f"   ✗ Error: {e}")
            continue

    # Summary
    print()
    if args.dry_run and total_removed > 0:
        print(f"[DRY RUN] Would remove {total_removed} invalid hook key(s)")
        print("Run without --dry-run to apply changes")
    elif args.dry_run:
        print("✓ No invalid hook keys found")
    elif total_removed > 0:
        print(f"✓ Removed {total_removed} invalid hook key(s) from {files_modified} file(s)")
    else:
        print("✓ No invalid hook keys found")
