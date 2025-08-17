#!/usr/bin/env python3
"""
Configuration Migration Script

Migrates claude-mpm configuration from scattered files to consolidated structure.
Run this script to update your configuration to the new format.
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.utils.config_migration import ConfigMigrationError, ConfigMigrator

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main migration function."""
    print("Claude MPM Configuration Migration Tool")
    print("=" * 40)

    # Detect project root
    project_root = Path.cwd()
    claude_mpm_dir = project_root / ".claude-mpm"

    if not claude_mpm_dir.exists():
        print(f"No .claude-mpm directory found in {project_root}")
        print("Please run this script from your project root directory.")
        return 1

    # Create migrator
    migrator = ConfigMigrator(project_root)

    # Check if migration is needed
    if not migrator.needs_migration():
        print("✓ Configuration is already up to date!")
        print(f"  Configuration file: {migrator.new_config_path}")
        return 0

    print("\nConfiguration migration needed:")
    print(f"  Project root: {project_root}")
    print(f"  Target file: {migrator.new_config_path}")

    # Show what will be migrated
    print("\nFiles to migrate:")
    if migrator.old_config_yaml.exists():
        print(f"  - {migrator.old_config_yaml.relative_to(project_root)}")
    if migrator.project_json.exists():
        print(f"  - {migrator.project_json.relative_to(project_root)}")
    if migrator.hooks_json.exists():
        print(f"  - {migrator.hooks_json.relative_to(project_root)}")
    if migrator.response_tracking_json.exists():
        print(f"  - {migrator.response_tracking_json.relative_to(project_root)}")

    # Ask for confirmation
    print("\nDo you want to proceed with migration?")
    print("(A backup will be created in .claude-mpm/config_backup/)")

    response = input("Continue? [y/N]: ").strip().lower()
    if response != "y":
        print("Migration cancelled.")
        return 1

    # Perform migration
    print("\nPerforming migration...")
    try:
        success = migrator.migrate(dry_run=False, create_backup=True)

        if success:
            print("\n✓ Migration completed successfully!")
            print(f"  New configuration: {migrator.new_config_path}")
            print(f"  Backup location: {migrator.backup_dir}")
            print("\nYou can now delete the old configuration files if desired.")
            return 0
        else:
            print("\n✗ Migration failed. Please check the logs.")
            return 1

    except ConfigMigrationError as e:
        print(f"\n✗ Migration error: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        logger.exception("Migration failed with unexpected error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
