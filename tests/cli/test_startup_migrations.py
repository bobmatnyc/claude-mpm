"""
Tests for startup migrations module.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


class TestStartupMigrations:
    """Tests for the startup migrations system."""

    @pytest.fixture
    def temp_home(self, tmp_path):
        """Create a temporary home directory structure."""
        home = tmp_path / "home"
        home.mkdir()
        claude_mpm = home / ".claude-mpm"
        claude_mpm.mkdir()
        cache = claude_mpm / "cache"
        cache.mkdir()
        return home

    @pytest.fixture
    def patch_home(self, temp_home):
        """Patch Path.home() to return temp home."""
        with patch.object(Path, "home", return_value=temp_home):
            yield temp_home

    def test_check_cache_dir_rename_needed_true(self, patch_home):
        """Test that check returns True when remote-agents exists."""
        from claude_mpm.cli.startup_migrations import _check_cache_dir_rename_needed

        # Create old cache dir
        old_dir = patch_home / ".claude-mpm" / "cache" / "remote-agents"
        old_dir.mkdir(parents=True)

        assert _check_cache_dir_rename_needed() is True

    def test_check_cache_dir_rename_needed_false(self, patch_home):
        """Test that check returns False when remote-agents doesn't exist."""
        from claude_mpm.cli.startup_migrations import _check_cache_dir_rename_needed

        assert _check_cache_dir_rename_needed() is False

    def test_migrate_cache_dir_rename_simple(self, patch_home):
        """Test simple directory rename when new dir doesn't exist."""
        from claude_mpm.cli.startup_migrations import _migrate_cache_dir_rename

        # Create old cache dir with content
        old_dir = patch_home / ".claude-mpm" / "cache" / "remote-agents"
        old_dir.mkdir(parents=True)
        (old_dir / "test-agent").mkdir()
        (old_dir / "test-agent" / "agent.yaml").write_text("test: content")

        # Run migration
        result = _migrate_cache_dir_rename()

        # Verify
        assert result is True
        assert not old_dir.exists()
        new_dir = patch_home / ".claude-mpm" / "cache" / "agents"
        assert new_dir.exists()
        assert (new_dir / "test-agent" / "agent.yaml").exists()

    def test_migrate_cache_dir_rename_merge(self, patch_home):
        """Test directory merge when new dir already exists."""
        from claude_mpm.cli.startup_migrations import _migrate_cache_dir_rename

        # Create old cache dir with content
        old_dir = patch_home / ".claude-mpm" / "cache" / "remote-agents"
        old_dir.mkdir(parents=True)
        (old_dir / "old-agent").mkdir()
        (old_dir / "old-agent" / "agent.yaml").write_text("old: content")

        # Create new cache dir with different content
        new_dir = patch_home / ".claude-mpm" / "cache" / "agents"
        new_dir.mkdir(parents=True)
        (new_dir / "existing-agent").mkdir()
        (new_dir / "existing-agent" / "agent.yaml").write_text("existing: content")

        # Run migration
        result = _migrate_cache_dir_rename()

        # Verify
        assert result is True
        assert not old_dir.exists()
        assert new_dir.exists()
        # Both agents should exist
        assert (new_dir / "old-agent" / "agent.yaml").exists()
        assert (new_dir / "existing-agent" / "agent.yaml").exists()

    def test_update_configuration_cache_path(self, patch_home):
        """Test that configuration.yaml is updated with new path."""
        from claude_mpm.cli.startup_migrations import _update_configuration_cache_path

        # Create configuration.yaml with old path
        config_file = patch_home / ".claude-mpm" / "configuration.yaml"
        config_content = """
agent_sync:
  cache_dir: /Users/test/.claude-mpm/cache/remote-agents
  enabled: true
"""
        config_file.write_text(config_content)

        # Run update
        _update_configuration_cache_path()

        # Verify
        updated_content = config_file.read_text()
        assert "/.claude-mpm/cache/agents" in updated_content
        assert "/.claude-mpm/cache/remote-agents" not in updated_content

    def test_migration_tracking_load_save(self, patch_home):
        """Test loading and saving migration tracking."""
        from claude_mpm.cli.startup_migrations import (
            _is_migration_completed,
            _load_completed_migrations,
            _save_completed_migration,
        )

        # Initially no migrations
        data = _load_completed_migrations()
        assert data == {"migrations": []}
        assert _is_migration_completed("test-migration") is False

        # Save a migration
        _save_completed_migration("test-migration")

        # Verify it's tracked
        assert _is_migration_completed("test-migration") is True
        data = _load_completed_migrations()
        assert len(data["migrations"]) == 1
        assert data["migrations"][0]["id"] == "test-migration"

    def test_run_migrations_skips_completed(self, patch_home):
        """Test that run_migrations skips already completed migrations."""
        from claude_mpm.cli.startup_migrations import (
            MIGRATIONS,
            _is_migration_completed,
            _save_completed_migration,
            run_migrations,
        )

        # Pre-mark the migration as completed
        if MIGRATIONS:
            _save_completed_migration(MIGRATIONS[0].id)

        # Create old cache dir
        old_dir = patch_home / ".claude-mpm" / "cache" / "remote-agents"
        old_dir.mkdir(parents=True)
        (old_dir / "test-agent").mkdir()

        # Run migrations
        run_migrations()

        # Old dir should still exist (migration was skipped)
        assert old_dir.exists()

    def test_run_migrations_executes_pending(self, patch_home):
        """Test that run_migrations executes pending migrations."""
        from claude_mpm.cli.startup_migrations import MIGRATIONS, run_migrations

        # Create old cache dir
        old_dir = patch_home / ".claude-mpm" / "cache" / "remote-agents"
        old_dir.mkdir(parents=True)
        (old_dir / "test-agent").mkdir()

        # Run migrations
        run_migrations()

        # Old dir should be gone, new dir should exist
        assert not old_dir.exists()
        new_dir = patch_home / ".claude-mpm" / "cache" / "agents"
        assert new_dir.exists()

    def test_run_migrations_marks_complete_when_not_needed(self, patch_home):
        """Test that migration is marked complete even if condition doesn't apply."""
        from claude_mpm.cli.startup_migrations import (
            MIGRATIONS,
            _is_migration_completed,
            run_migrations,
        )

        # Don't create old cache dir - condition doesn't apply

        # Run migrations
        run_migrations()

        # Migration should still be marked as completed
        if MIGRATIONS:
            assert _is_migration_completed(MIGRATIONS[0].id) is True
