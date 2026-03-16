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
        """Patch Path.home() and Path.cwd() to return temp home.

        Also patches cwd to prevent migrations (like agent naming cleanup)
        from operating on the real project's .claude/agents/ directory.
        """
        with patch.object(Path, "home", return_value=temp_home):
            with patch.object(Path, "cwd", return_value=temp_home):
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


class TestAgentNamingMigration:
    """Tests for the v5.10.0-standardize-agent-names migration."""

    @pytest.fixture
    def agents_dir(self, tmp_path):
        """Create a temporary .claude/agents/ directory."""
        agents = tmp_path / ".claude" / "agents"
        agents.mkdir(parents=True)
        return agents

    def _write_mpm_agent(self, path: Path, name: str):
        """Write a mock MPM agent file."""
        path.write_text(
            f"---\nname: {name}\nauthor: claude-mpm\nversion: 1.0.0\n---\n"
            f"# {name}\n\nInstructions here."
        )

    def _write_user_agent(self, path: Path, name: str):
        """Write a mock user agent file."""
        path.write_text(
            f"---\nname: {name}\nauthor: john-doe\nversion: 1.0.0\n---\n"
            f"# {name}\n\nUser instructions."
        )

    def test_check_returns_true_when_stale_files_exist(self, agents_dir):
        """Check function detects stale files."""
        from claude_mpm.cli.startup_migrations import (
            _check_agent_naming_migration_needed,
        )

        self._write_mpm_agent(agents_dir / "tmux-agent.md", "Tmux Agent")
        with patch(
            "claude_mpm.cli.startup_migrations.Path.cwd",
            return_value=agents_dir.parent.parent,
        ):
            assert _check_agent_naming_migration_needed() is True

    def test_check_returns_false_when_no_stale_files(self, agents_dir):
        """Check function returns False when no stale files exist."""
        from claude_mpm.cli.startup_migrations import (
            _check_agent_naming_migration_needed,
        )

        self._write_mpm_agent(agents_dir / "tmux.md", "Tmux")
        with patch(
            "claude_mpm.cli.startup_migrations.Path.cwd",
            return_value=agents_dir.parent.parent,
        ):
            assert _check_agent_naming_migration_needed() is False

    def test_check_returns_false_when_no_agents_dir(self, tmp_path):
        """Check function returns False when .claude/agents/ doesn't exist."""
        from claude_mpm.cli.startup_migrations import (
            _check_agent_naming_migration_needed,
        )

        with patch("claude_mpm.cli.startup_migrations.Path.cwd", return_value=tmp_path):
            assert _check_agent_naming_migration_needed() is False

    def test_migrate_removes_stale_mpm_agents(self, agents_dir):
        """Migration removes MPM agents with stale names."""
        from claude_mpm.cli.startup_migrations import (
            _migrate_agent_naming_standardization,
        )

        self._write_mpm_agent(agents_dir / "tmux-agent.md", "Tmux Agent")
        self._write_mpm_agent(agents_dir / "content-agent.md", "Content Agent")
        self._write_mpm_agent(agents_dir / "tmux.md", "Tmux")  # new name

        with patch(
            "claude_mpm.cli.startup_migrations.Path.cwd",
            return_value=agents_dir.parent.parent,
        ):
            result = _migrate_agent_naming_standardization()

        assert result is True
        assert not (agents_dir / "tmux-agent.md").exists()
        assert not (agents_dir / "content-agent.md").exists()
        assert (agents_dir / "tmux.md").exists()  # new file preserved

    def test_migrate_preserves_user_agents_with_stale_names(self, agents_dir):
        """Migration preserves user agents even if they have stale names."""
        from claude_mpm.cli.startup_migrations import (
            _migrate_agent_naming_standardization,
        )

        self._write_user_agent(agents_dir / "tmux-agent.md", "My Tmux Agent")

        with patch(
            "claude_mpm.cli.startup_migrations.Path.cwd",
            return_value=agents_dir.parent.parent,
        ):
            result = _migrate_agent_naming_standardization()

        assert result is True
        assert (agents_dir / "tmux-agent.md").exists()  # preserved

    def test_migrate_handles_missing_files_gracefully(self, agents_dir):
        """Migration succeeds even if no stale files exist."""
        from claude_mpm.cli.startup_migrations import (
            _migrate_agent_naming_standardization,
        )

        with patch(
            "claude_mpm.cli.startup_migrations.Path.cwd",
            return_value=agents_dir.parent.parent,
        ):
            result = _migrate_agent_naming_standardization()

        assert result is True

    def test_migrate_handles_all_four_renames(self, agents_dir):
        """Migration handles all 4 known filename renames."""
        from claude_mpm.cli.startup_migrations import (
            _STALE_AGENT_FILES,
            _migrate_agent_naming_standardization,
        )

        for filename in _STALE_AGENT_FILES:
            name = filename.replace(".md", "").replace("-", " ").title()
            self._write_mpm_agent(agents_dir / filename, name)

        with patch(
            "claude_mpm.cli.startup_migrations.Path.cwd",
            return_value=agents_dir.parent.parent,
        ):
            result = _migrate_agent_naming_standardization()

        assert result is True
        for filename in _STALE_AGENT_FILES:
            assert not (agents_dir / filename).exists()

    def test_web_ui_rename_handled(self, agents_dir):
        """The web-ui.md → web-ui-engineer.md rename is handled."""
        from claude_mpm.cli.startup_migrations import (
            _migrate_agent_naming_standardization,
        )

        self._write_mpm_agent(agents_dir / "web-ui.md", "Web UI")

        with patch(
            "claude_mpm.cli.startup_migrations.Path.cwd",
            return_value=agents_dir.parent.parent,
        ):
            result = _migrate_agent_naming_standardization()

        assert result is True
        assert not (agents_dir / "web-ui.md").exists()
