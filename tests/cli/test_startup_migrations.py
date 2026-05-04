"""
Tests for startup migrations module.
"""

import json
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


class TestDeploySpinnerGlobalMigration:
    """Tests for the v6.3.2-deploy-spinner-global migration (issue #465).

    Ensures spinner verbs/tips are deployed to ~/.claude/settings.json so
    they apply globally, not just inside MPM projects.
    """

    @pytest.fixture
    def fake_template_dir(self, tmp_path):
        """Create a fake bundled template directory with a settings.json."""
        templates = tmp_path / "templates_pkg"
        templates.mkdir()
        (templates / "settings.json").write_text(
            "{\n"
            '  "_mpm_managed": true,\n'
            '  "_mpm_version": "6.3.3",\n'
            '  "spinnerVerbs": {\n'
            '    "mode": "replace",\n'
            '    "verbs": ["Orchestrating agents", "Thinking"]\n'
            "  },\n"
            '  "spinnerTipsEnabled": true,\n'
            '  "spinnerTipsOverride": {\n'
            '    "tips": ["Tip 1", "Tip 2"],\n'
            '    "excludeDefault": true\n'
            "  },\n"
            '  "statusLine": {"type": "command", "command": "x"}\n'
            "}\n"
        )
        return templates

    @pytest.fixture
    def patched_env(self, tmp_path, fake_template_dir):
        """Patch Path.home() and the bundled template lookup."""
        home = tmp_path / "home"
        home.mkdir()
        with patch.object(Path, "home", return_value=home):
            with patch(
                "claude_mpm.cli.startup_migrations._get_claude_assets_templates_dir",
                return_value=fake_template_dir,
            ):
                yield home

    def test_check_returns_true_when_user_settings_missing(self, patched_env):
        """If ~/.claude/settings.json doesn't exist, migration is needed."""
        from claude_mpm.cli.startup_migrations import _check_spinner_global_needed

        assert _check_spinner_global_needed() is True

    def test_check_returns_true_when_spinner_keys_missing(self, patched_env):
        """If user settings exists but lacks spinner keys, migration is needed."""
        from claude_mpm.cli.startup_migrations import _check_spinner_global_needed

        user_settings = patched_env / ".claude" / "settings.json"
        user_settings.parent.mkdir(parents=True)
        user_settings.write_text('{"theme": "dark"}\n')

        assert _check_spinner_global_needed() is True

    def test_check_returns_false_when_already_deployed(self, patched_env):
        """If spinner keys present and version current, migration is NOT needed."""
        from claude_mpm.cli.startup_migrations import _check_spinner_global_needed

        user_settings = patched_env / ".claude" / "settings.json"
        user_settings.parent.mkdir(parents=True)
        user_settings.write_text(
            "{\n"
            '  "spinnerVerbs": {"mode": "replace", "verbs": ["x"]},\n'
            '  "spinnerTipsEnabled": true,\n'
            '  "spinnerTipsOverride": {"tips": ["y"], "excludeDefault": true},\n'
            '  "_mpm_spinner_version": "6.3.3"\n'
            "}\n"
        )

        assert _check_spinner_global_needed() is False

    def test_check_returns_true_when_version_outdated(self, patched_env):
        """Older _mpm_spinner_version triggers redeploy."""
        from claude_mpm.cli.startup_migrations import _check_spinner_global_needed

        user_settings = patched_env / ".claude" / "settings.json"
        user_settings.parent.mkdir(parents=True)
        user_settings.write_text(
            "{\n"
            '  "spinnerVerbs": {"mode": "replace", "verbs": ["old"]},\n'
            '  "spinnerTipsEnabled": false,\n'
            '  "spinnerTipsOverride": {"tips": [], "excludeDefault": false},\n'
            '  "_mpm_spinner_version": "6.3.0"\n'
            "}\n"
        )

        assert _check_spinner_global_needed() is True

    def test_deploy_creates_settings_when_missing(self, patched_env):
        """Migration creates ~/.claude/settings.json when it doesn't exist."""
        from claude_mpm.cli.startup_migrations import _deploy_spinner_global

        user_settings = patched_env / ".claude" / "settings.json"
        assert not user_settings.exists()

        result = _deploy_spinner_global()

        assert result is True
        assert user_settings.exists()
        data = json.loads(user_settings.read_text())
        assert "spinnerVerbs" in data
        assert "spinnerTipsEnabled" in data
        assert "spinnerTipsOverride" in data
        assert data["_mpm_spinner_version"] == "6.3.3"

    def test_deploy_preserves_other_user_settings(self, patched_env):
        """Migration must NOT remove or overwrite unrelated user keys."""
        from claude_mpm.cli.startup_migrations import _deploy_spinner_global

        user_settings = patched_env / ".claude" / "settings.json"
        user_settings.parent.mkdir(parents=True)
        user_settings.write_text(
            "{\n"
            '  "theme": "dark",\n'
            '  "model": "claude-opus-4-7",\n'
            '  "permissions": {"allow": ["Read"]}\n'
            "}\n"
        )

        result = _deploy_spinner_global()

        assert result is True
        data = json.loads(user_settings.read_text())
        # Unrelated keys preserved
        assert data["theme"] == "dark"
        assert data["model"] == "claude-opus-4-7"
        assert data["permissions"] == {"allow": ["Read"]}
        # Spinner keys added
        assert "spinnerVerbs" in data
        assert data["spinnerTipsEnabled"] is True
        # Version stamp written
        assert data["_mpm_spinner_version"] == "6.3.3"

    def test_deploy_does_not_overwrite_user_spinner_customisation(self, patched_env):
        """When spinner keys exist and version is current, nothing changes."""
        from claude_mpm.cli.startup_migrations import _deploy_spinner_global

        user_settings = patched_env / ".claude" / "settings.json"
        user_settings.parent.mkdir(parents=True)
        custom_payload = {
            "spinnerVerbs": {"mode": "append", "verbs": ["Custom Verb"]},
            "spinnerTipsEnabled": False,
            "spinnerTipsOverride": {"tips": ["My tip"], "excludeDefault": False},
            "_mpm_spinner_version": "6.3.3",
            "theme": "light",
        }
        user_settings.write_text(json.dumps(custom_payload, indent=2) + "\n")

        result = _deploy_spinner_global()

        assert result is True
        data = json.loads(user_settings.read_text())
        # User customisations preserved at the up-to-date version
        assert data["spinnerVerbs"]["mode"] == "append"
        assert data["spinnerVerbs"]["verbs"] == ["Custom Verb"]
        assert data["spinnerTipsEnabled"] is False
        assert data["theme"] == "light"

    def test_deploy_updates_when_template_version_newer(self, patched_env):
        """Older _mpm_spinner_version causes spinner keys to be refreshed."""
        from claude_mpm.cli.startup_migrations import _deploy_spinner_global

        user_settings = patched_env / ".claude" / "settings.json"
        user_settings.parent.mkdir(parents=True)
        user_settings.write_text(
            json.dumps(
                {
                    "spinnerVerbs": {"mode": "replace", "verbs": ["Old"]},
                    "spinnerTipsEnabled": True,
                    "spinnerTipsOverride": {
                        "tips": ["Old tip"],
                        "excludeDefault": True,
                    },
                    "_mpm_spinner_version": "6.3.0",
                    "user_key": "kept",
                },
                indent=2,
            )
            + "\n"
        )

        result = _deploy_spinner_global()

        assert result is True
        data = json.loads(user_settings.read_text())
        # Spinner verbs refreshed from template
        assert data["spinnerVerbs"]["verbs"] == ["Orchestrating agents", "Thinking"]
        # Version bumped
        assert data["_mpm_spinner_version"] == "6.3.3"
        # Unrelated user key preserved
        assert data["user_key"] == "kept"

    def test_deploy_idempotent_on_second_run(self, patched_env):
        """Running the migration twice produces the same file content."""
        from claude_mpm.cli.startup_migrations import _deploy_spinner_global

        result1 = _deploy_spinner_global()
        assert result1 is True
        first_content = (patched_env / ".claude" / "settings.json").read_text()

        result2 = _deploy_spinner_global()
        assert result2 is True
        second_content = (patched_env / ".claude" / "settings.json").read_text()

        assert first_content == second_content

    def test_deploy_refuses_to_overwrite_malformed_json(self, patched_env):
        """Malformed user settings.json is left alone (no data loss)."""
        from claude_mpm.cli.startup_migrations import _deploy_spinner_global

        user_settings = patched_env / ".claude" / "settings.json"
        user_settings.parent.mkdir(parents=True)
        malformed = "{ this is not valid json }"
        user_settings.write_text(malformed)

        result = _deploy_spinner_global()

        assert result is False
        # File preserved verbatim
        assert user_settings.read_text() == malformed

    def test_migration_registered_in_registry(self):
        """The new migration must be registered in MIGRATIONS list."""
        from claude_mpm.cli.startup_migrations import MIGRATIONS

        ids = [m.id for m in MIGRATIONS]
        assert "v6.3.2-deploy-spinner-global" in ids
