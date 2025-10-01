"""
Comprehensive test suite for Config Migration utility.

Tests critical functionality including:
- Migration from old to new config formats
- Data preservation during migration
- Rollback on migration failure
- Version detection and routing
- Backup creation before migration
- Permission preservation
- Settings validation after migration
- Edge cases (empty configs, corrupted data)
"""

import pytest

# Skip entire module - config_migration module was removed in refactoring
pytestmark = pytest.mark.skip(
    reason="config_migration module was removed in refactoring - functionality integrated elsewhere"
)

import contextlib
import json
import os
from pathlib import Path
from unittest.mock import patch

import yaml

# from claude_mpm.utils.config_migration import (
#     ConfigMigrationError,
#     ConfigMigrator,
#     migrate_config,
# )  # Module removed


class TestConfigMigratorBasics:
    """Test basic configuration migration functionality."""

    def test_init_with_project_root():
        """Test initialization with explicit project root."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            assert migrator.project_root == Path(tmpdir)
            assert migrator.claude_mpm_dir == Path(tmpdir) / ".claude-mpm"
            assert migrator.config_dir == Path(tmpdir) / ".claude-mpm" / "config"
            assert (
                migrator.new_config_path == Path(tmpdir) / ".claude-mpm" / "config.yaml"
            )

    def test_auto_detect_project_root():
        """Test automatic project root detection."""
        with tmp_path as tmpdir:
            # Create .claude-mpm directory
            claude_dir = Path(tmpdir) / ".claude-mpm"
            claude_dir.mkdir()

            # Change to project directory
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                migrator = ConfigMigrator()

                assert migrator.project_root == Path(tmpdir)
            finally:
                os.chdir(original_cwd)

    def test_detect_project_root_parent_dir():
        """Test detection when .claude-mpm is in parent directory."""
        with tmp_path as tmpdir:
            # Create .claude-mpm in parent
            claude_dir = Path(tmpdir) / ".claude-mpm"
            claude_dir.mkdir()

            # Create subdirectory and change to it
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()

            original_cwd = os.getcwd()
            try:
                os.chdir(subdir)
                migrator = ConfigMigrator()

                assert migrator.project_root == Path(tmpdir)
            finally:
                os.chdir(original_cwd)


class TestMigrationDetection:
    """Test migration need detection."""

    def test_needs_migration_old_structure_exists():
        """Test detection when old config structure exists."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create old structure
            migrator.config_dir.mkdir(parents=True)
            migrator.project_json.write_text('{"name": "test"}')

            assert migrator.needs_migration()

    def test_needs_migration_new_structure_complete():
        """Test detection when new structure is complete."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create complete new structure
            migrator.claude_mpm_dir.mkdir(parents=True)
            config = {
                "project": {"name": "test"},
                "response_tracking": {"enabled": True},
            }
            with migrator.new_config_path.open("w") as f:
                yaml.dump(config, f)

            assert not migrator.needs_migration()

    def test_needs_migration_partial_new_structure():
        """Test detection when new structure is incomplete."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create old structure
            migrator.config_dir.mkdir(parents=True)
            migrator.project_json.write_text('{"name": "test"}')

            # Create incomplete new structure (missing sections)
            migrator.claude_mpm_dir.mkdir(parents=True)
            config = {"some_other_section": {}}
            with migrator.new_config_path.open("w") as f:
                yaml.dump(config, f)

            assert migrator.needs_migration()

    def test_needs_migration_corrupted_new_config():
        """Test detection when new config is corrupted."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create old structure
            migrator.config_dir.mkdir(parents=True)
            migrator.project_json.write_text('{"name": "test"}')

            # Create corrupted new config
            migrator.claude_mpm_dir.mkdir(parents=True)
            migrator.new_config_path.write_text("invalid: yaml: content:")

            assert migrator.needs_migration()


class TestMigrationProcess:
    """Test the actual migration process."""

    def test_migrate_project_json():
        """Test migration of project.json to consolidated config."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create old project.json
            migrator.config_dir.mkdir(parents=True)
            project_data = {
                "name": "Test Project",
                "version": "1.0.0",
                "description": "Test description",
            }
            with migrator.project_json.open("w") as f:
                json.dump(project_data, f)

            # Perform migration
            success = migrator.migrate()
            assert success

            # Verify migrated data
            with migrator.new_config_path.open() as f:
                config = yaml.safe_load(f)

            assert config["project"] == project_data

    def test_migrate_response_tracking_json():
        """Test migration of response_tracking.json."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create old response_tracking.json
            migrator.config_dir.mkdir(parents=True)
            tracking_data = {
                "enabled": True,
                "max_responses": 100,
                "retention_days": 30,
            }
            with migrator.response_tracking_json.open("w") as f:
                json.dump(tracking_data, f)

            # Perform migration
            success = migrator.migrate()
            assert success

            # Verify migrated data
            with migrator.new_config_path.open() as f:
                config = yaml.safe_load(f)

            assert config["response_tracking"] == tracking_data

    def test_migrate_both_configs():
        """Test migration of both config files together."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create both old config files
            migrator.config_dir.mkdir(parents=True)

            project_data = {"name": "Project", "version": "1.0"}
            with migrator.project_json.open("w") as f:
                json.dump(project_data, f)

            tracking_data = {"enabled": True}
            with migrator.response_tracking_json.open("w") as f:
                json.dump(tracking_data, f)

            # Perform migration
            success = migrator.migrate()
            assert success

            # Verify both migrated
            with migrator.new_config_path.open() as f:
                config = yaml.safe_load(f)

            assert config["project"] == project_data
            assert config["response_tracking"] == tracking_data

    def test_migrate_terminal_settings():
        """Test migration of old terminal settings to new structure."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create old config with flat terminal settings
            migrator.claude_mpm_dir.mkdir(parents=True)
            old_config = {
                "terminal_debug_logging": True,
                "terminal_use_preexec_fn": False,
                "terminal_retry_without_preexec": True,
                "other_setting": "value",
            }
            with migrator.old_config_yaml.open("w") as f:
                yaml.dump(old_config, f)

            # Perform migration
            success = migrator.migrate()
            assert success

            # Verify terminal settings are nested
            with migrator.new_config_path.open() as f:
                config = yaml.safe_load(f)

            assert config["terminal"]["debug_logging"]
            assert not config["terminal"]["use_preexec_fn"]
            assert config["terminal"]["retry_without_preexec"]

            # Flat settings should be removed
            assert "terminal_debug_logging" not in config
            assert "terminal_use_preexec_fn" not in config
            assert "terminal_retry_without_preexec" not in config


class TestDryRun:
    """Test dry run functionality."""

    def test_dry_run_no_changes():
        """Test that dry run doesn't modify files."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create old structure
            migrator.config_dir.mkdir(parents=True)
            migrator.project_json.write_text('{"name": "test"}')

            # Perform dry run
            success = migrator.migrate(dry_run=True)
            assert success

            # Files should not be modified
            assert not migrator.new_config_path.exists()
            assert migrator.project_json.exists()

    def test_dry_run_shows_what_would_migrate():
        """Test that dry run reports what would be migrated."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create old files
            migrator.config_dir.mkdir(parents=True)
            migrator.project_json.write_text('{"name": "test"}')
            migrator.response_tracking_json.write_text('{"enabled": true}')

            # Capture log output
            with patch("claude_mpm.utils.config_migration.logger") as mock_logger:
                migrator.migrate(dry_run=True)

                # Should log what would be migrated
                log_messages = [call[0][0] for call in mock_logger.info.call_args_list]
                assert any("project.json" in msg for msg in log_messages)
                assert any("response_tracking.json" in msg for msg in log_messages)


class TestBackupAndRestore:
    """Test backup creation and restoration."""

    def test_backup_creation():
        """Test that backups are created before migration."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create old files
            migrator.config_dir.mkdir(parents=True)
            migrator.project_json.write_text('{"name": "original"}')

            # Perform migration
            migrator.migrate(create_backup=True)

            # Backup should exist
            assert migrator.backup_dir.exists()
            backup_files = list(migrator.backup_dir.glob("*.json"))
            assert len(backup_files) > 0

            # Backup should contain original content
            backup_content = backup_files[0].read_text()
            assert '"name": "original"' in backup_content

    def test_no_backup_option():
        """Test migration without creating backup."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create old files
            migrator.config_dir.mkdir(parents=True)
            migrator.project_json.write_text('{"name": "test"}')

            # Perform migration without backup
            migrator.migrate(create_backup=False)

            # Backup directory should not exist
            assert not migrator.backup_dir.exists()

    def test_list_backups():
        """Test listing available backups."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create multiple backups
            migrator.backup_dir.mkdir(parents=True)

            for i in range(3):
                backup_file = migrator.backup_dir / f"project_{i}.json"
                backup_file.write_text(f'{{"backup": {i}}}')

            backups = migrator.list_backups()

            assert len(backups) == 3
            for backup in backups:
                assert "name" in backup
                assert "path" in backup
                assert "size" in backup
                assert "created" in backup

    def test_restore_from_backup():
        """Test restoring configuration from backup."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create backup
            migrator.backup_dir.mkdir(parents=True)
            backup_data = {"name": "backup_version"}
            backup_file = migrator.backup_dir / "project_backup.json"
            with backup_file.open("w") as f:
                json.dump(backup_data, f)

            # Restore from backup
            success = migrator.restore_from_backup("project_backup.json")
            assert success

            # Verify restored content
            assert migrator.project_json.exists()
            with migrator.project_json.open() as f:
                restored = json.load(f)

            assert restored == backup_data

    def test_restore_nonexistent_backup():
        """Test restoring from non-existent backup."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            success = migrator.restore_from_backup("nonexistent.json")
            assert not success


class TestRollback:
    """Test rollback functionality."""

    def test_rollback_on_error():
        """Test automatic rollback when migration fails."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create old files
            migrator.config_dir.mkdir(parents=True)
            original_data = {"name": "original"}
            with migrator.project_json.open("w") as f:
                json.dump(original_data, f)

            # Make migration fail
            with patch.object(
                migrator,
                "_save_consolidated_config",
                side_effect=Exception("Save failed"),
            ), contextlib.suppress(ConfigMigrationError):
                migrator.migrate()

            # Original files should still exist (rolled back)
            assert migrator.project_json.exists()
            with migrator.project_json.open() as f:
                data = json.load(f)
            assert data == original_data

    def test_rollback_without_backup():
        """Test rollback behavior when no backup exists."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Try rollback without backup
            migrator._rollback_migration()

            # Should handle gracefully (no exception)
            assert not migrator.backup_dir.exists()


class TestCleanup:
    """Test old file cleanup after migration."""

    def test_cleanup_old_files():
        """Test that old files are removed after successful migration."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create old files
            migrator.config_dir.mkdir(parents=True)
            migrator.project_json.write_text('{"name": "test"}')
            migrator.response_tracking_json.write_text('{"enabled": true}')

            # Perform migration
            migrator.migrate()

            # Old files should be removed
            assert not migrator.project_json.exists()
            assert not migrator.response_tracking_json.exists()

    def test_preserve_mcp_services():
        """Test that mcp_services.yaml is preserved during cleanup."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create old files and mcp_services.yaml
            migrator.config_dir.mkdir(parents=True)
            migrator.project_json.write_text('{"name": "test"}')

            mcp_services = migrator.config_dir / "mcp_services.yaml"
            mcp_services.write_text("services: {}")

            # Perform migration
            migrator.migrate()

            # mcp_services.yaml should still exist
            assert mcp_services.exists()
            # Config directory should still exist
            assert migrator.config_dir.exists()

    def test_remove_empty_config_dir():
        """Test that empty config directory is removed."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create only old files (no mcp_services.yaml)
            migrator.config_dir.mkdir(parents=True)
            migrator.project_json.write_text('{"name": "test"}')

            # Perform migration
            migrator.migrate()

            # Config directory should be removed if empty
            assert not migrator.config_dir.exists()


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_corrupted_json_file():
        """Test handling of corrupted JSON files."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create corrupted JSON
            migrator.config_dir.mkdir(parents=True)
            migrator.project_json.write_text("{invalid json}")

            # Should handle gracefully
            success = migrator.migrate()
            assert success

            # Should create config with empty project section
            with migrator.new_config_path.open() as f:
                config = yaml.safe_load(f)
            assert config["project"] == {}

    def test_permission_error():
        """Test handling of permission errors."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create old file
            migrator.config_dir.mkdir(parents=True)
            migrator.project_json.write_text('{"name": "test"}')

            # Make new config path unwritable
            migrator.claude_mpm_dir.mkdir(parents=True)

            with patch(
                "builtins.open", side_effect=PermissionError("Permission denied")
            ), pytest.raises(ConfigMigrationError):
                migrator.migrate()

    def test_disk_full():
        """Test handling when disk is full."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create old file
            migrator.config_dir.mkdir(parents=True)
            migrator.project_json.write_text('{"name": "test"}')

            with patch("builtins.open", side_effect=OSError("No space left on device")):
                with pytest.raises(ConfigMigrationError):
                    migrator.migrate()


class TestDataPreservation:
    """Test that data is preserved correctly during migration."""

    def test_preserve_all_fields():
        """Test that all fields are preserved during migration."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create complex config
            migrator.config_dir.mkdir(parents=True)

            project_data = {
                "name": "Complex Project",
                "version": "2.1.3",
                "description": "A complex test project",
                "custom_field": {"nested": {"data": [1, 2, 3]}},
                "unicode": "世界 🌍 مرحبا",
            }
            with migrator.project_json.open("w") as f:
                json.dump(project_data, f, ensure_ascii=False)

            # Perform migration
            migrator.migrate()

            # Verify all fields preserved
            with migrator.new_config_path.open() as f:
                config = yaml.safe_load(f)

            assert config["project"] == project_data
            assert config["project"]["unicode"] == "世界 🌍 مرحبا"

    def test_preserve_existing_config():
        """Test that existing config sections are preserved."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create existing new config with some sections
            migrator.claude_mpm_dir.mkdir(parents=True)
            existing_config = {
                "existing_section": {"key": "value"},
                "another_section": [1, 2, 3],
            }
            with migrator.new_config_path.open("w") as f:
                yaml.dump(existing_config, f)

            # Create old config to migrate
            migrator.config_dir.mkdir(parents=True)
            migrator.project_json.write_text('{"name": "test"}')

            # Perform migration
            migrator.migrate()

            # Verify existing sections preserved
            with migrator.new_config_path.open() as f:
                config = yaml.safe_load(f)

            assert config["existing_section"] == {"key": "value"}
            assert config["another_section"] == [1, 2, 3]
            assert config["project"] == {"name": "test"}

    def test_yaml_formatting_preserved():
        """Test that YAML formatting is reasonable after migration."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create old config
            migrator.config_dir.mkdir(parents=True)
            migrator.project_json.write_text('{"name": "test"}')

            # Perform migration
            migrator.migrate()

            # Check YAML formatting
            content = migrator.new_config_path.read_text()

            # Should have header comment
            assert content.startswith("# Claude MPM Configuration")

            # Should use 2-space indentation
            assert "  " in content

            # Should not use flow style
            assert "{" not in content or "project:" not in content


class TestConvenienceFunction:
    """Test the convenience migrate_config function."""

    def test_migrate_config_success():
        """Test convenience function for successful migration."""
        with tmp_path as tmpdir:
            # Create old structure
            config_dir = Path(tmpdir) / ".claude-mpm" / "config"
            config_dir.mkdir(parents=True)
            (config_dir / "project.json").write_text('{"name": "test"}')

            # Use convenience function
            success = migrate_config(Path(tmpdir))
            assert success

            # Verify migration happened
            new_config = Path(tmpdir) / ".claude-mpm" / "config.yaml"
            assert new_config.exists()

    def test_migrate_config_not_needed():
        """Test convenience function when migration not needed."""
        with tmp_path as tmpdir:
            # Create complete new structure
            claude_dir = Path(tmpdir) / ".claude-mpm"
            claude_dir.mkdir()
            config_path = claude_dir / "config.yaml"
            config = {
                "project": {"name": "test"},
                "response_tracking": {"enabled": True},
            }
            with config_path.open("w") as f:
                yaml.dump(config, f)

            # Should return success without doing anything
            success = migrate_config(Path(tmpdir))
            assert success

    def test_migrate_config_dry_run():
        """Test convenience function with dry run."""
        with tmp_path as tmpdir:
            # Create old structure
            config_dir = Path(tmpdir) / ".claude-mpm" / "config"
            config_dir.mkdir(parents=True)
            (config_dir / "project.json").write_text('{"name": "test"}')

            # Dry run should not modify files
            success = migrate_config(Path(tmpdir), dry_run=True)
            assert success

            # New config should not exist
            new_config = Path(tmpdir) / ".claude-mpm" / "config.yaml"
            assert not new_config.exists()


class TestEdgeCases:
    """Test edge cases and unusual scenarios."""

    def test_empty_config_files():
        """Test migration of empty config files."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create empty files
            migrator.config_dir.mkdir(parents=True)
            migrator.project_json.write_text("{}")
            migrator.response_tracking_json.write_text("{}")

            # Should migrate successfully
            success = migrator.migrate()
            assert success

            # Result should have empty sections
            with migrator.new_config_path.open() as f:
                config = yaml.safe_load(f)

            assert config["project"] == {}
            assert config["response_tracking"] == {}

    def test_very_large_config():
        """Test migration of very large configuration."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create large config
            migrator.config_dir.mkdir(parents=True)
            large_data = {"data": ["item" * 100 for _ in range(10000)]}  # Large array
            with migrator.project_json.open("w") as f:
                json.dump(large_data, f)

            # Should handle large data
            success = migrator.migrate()
            assert success

            # Verify data integrity
            with migrator.new_config_path.open() as f:
                config = yaml.safe_load(f)

            assert len(config["project"]["data"]) == 10000

    def test_special_characters_in_paths():
        """Test handling of special characters in file paths."""
        with tmp_path as tmpdir:
            # Create directory with spaces
            special_dir = Path(tmpdir) / "project with spaces"
            special_dir.mkdir()

            migrator = ConfigMigrator(special_dir)

            # Create old config
            migrator.config_dir.mkdir(parents=True)
            migrator.project_json.write_text('{"name": "test"}')

            # Should handle special characters
            success = migrator.migrate()
            assert success

    def test_symlinked_config_files():
        """Test migration when config files are symlinks."""
        with tmp_path as tmpdir:
            migrator = ConfigMigrator(Path(tmpdir))

            # Create actual file elsewhere
            actual_file = Path(tmpdir) / "actual_project.json"
            actual_file.write_text('{"name": "symlinked"}')

            # Create symlink to it
            migrator.config_dir.mkdir(parents=True)
            migrator.project_json.symlink_to(actual_file)

            # Should follow symlink and migrate content
            success = migrator.migrate()
            assert success

            # Verify content was migrated
            with migrator.new_config_path.open() as f:
                config = yaml.safe_load(f)

            assert config["project"]["name"] == "symlinked"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
