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


class TestRewriteBakedHookPathsMigration:
    """Tests for the v6.4.15-rewrite-baked-hook-paths migration (issue #552).

    Earlier versions of ``HookInstaller.get_hook_command()`` baked an
    absolute path to ``claude-hook-fast.sh`` under
    ``~/.local/share/uv/tools/claude-mpm/...`` into project settings files.
    When the uv tools environment is rebuilt that path becomes stale and
    every hook event fails.  This migration rewrites such commands to the
    PATH-based ``claude-hook`` entry point.
    """

    @pytest.fixture
    def project_dir(self, tmp_path):
        """Create an isolated project directory with a .claude subdir."""
        project = tmp_path / "project"
        (project / ".claude").mkdir(parents=True)
        return project

    @pytest.fixture
    def patch_cwd(self, project_dir):
        """Patch Path.cwd() to return the isolated project dir."""
        with patch.object(Path, "cwd", return_value=project_dir):
            yield project_dir

    @staticmethod
    def _baked_fast_path() -> str:
        """A representative baked uv-tools path to claude-hook-fast.sh."""
        return (
            "/Users/example/.local/share/uv/tools/claude-mpm/lib/python3.13/"
            "site-packages/claude_mpm/scripts/claude-hook-fast.sh"
        )

    @staticmethod
    def _baked_uv_path() -> str:
        """A baked uv-tools path that does NOT mention claude-hook-fast.sh."""
        return (
            "/home/user/.local/share/uv/tools/claude-mpm/lib/python3.13/"
            "site-packages/claude_mpm/scripts/some-other-script.sh"
        )

    def _write_settings(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2))

    def _settings_with_command(self, command: str) -> dict:
        return {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": command,
                                "_mpm": True,
                            }
                        ],
                    }
                ]
            }
        }

    # ----- check() -----

    def test_check_true_when_settings_local_has_fast_sh_path(self, patch_cwd):
        """check() returns True when settings.local.json has a stale fast.sh path."""
        from claude_mpm.cli.startup_migrations import (
            _check_baked_hook_paths_exist,
        )

        self._write_settings(
            patch_cwd / ".claude" / "settings.local.json",
            self._settings_with_command(self._baked_fast_path()),
        )

        assert _check_baked_hook_paths_exist() is True

    def test_check_true_when_settings_json_has_uv_tools_path(self, patch_cwd):
        """check() returns True for the broader uv/tools/claude-mpm/ pattern."""
        from claude_mpm.cli.startup_migrations import (
            _check_baked_hook_paths_exist,
        )

        self._write_settings(
            patch_cwd / ".claude" / "settings.json",
            self._settings_with_command(self._baked_uv_path()),
        )

        assert _check_baked_hook_paths_exist() is True

    def test_check_false_when_no_hooks_match_patterns(self, patch_cwd):
        """check() returns False when no hook commands match either pattern."""
        from claude_mpm.cli.startup_migrations import (
            _check_baked_hook_paths_exist,
        )

        self._write_settings(
            patch_cwd / ".claude" / "settings.local.json",
            self._settings_with_command("/usr/local/bin/some-unrelated-tool"),
        )

        assert _check_baked_hook_paths_exist() is False

    def test_check_false_when_already_claude_hook(self, patch_cwd):
        """check() returns False when all hooks are already 'claude-hook'."""
        from claude_mpm.cli.startup_migrations import (
            _check_baked_hook_paths_exist,
        )

        self._write_settings(
            patch_cwd / ".claude" / "settings.json",
            self._settings_with_command("claude-hook"),
        )
        self._write_settings(
            patch_cwd / ".claude" / "settings.local.json",
            self._settings_with_command("claude-hook"),
        )

        assert _check_baked_hook_paths_exist() is False

    def test_check_false_when_no_settings_files_exist(self, patch_cwd):
        """check() returns False when no .claude/settings*.json files exist."""
        from claude_mpm.cli.startup_migrations import (
            _check_baked_hook_paths_exist,
        )

        assert _check_baked_hook_paths_exist() is False

    # ----- run() -----

    def test_run_rewrites_command_and_preserves_sibling_fields(self, patch_cwd):
        """run() rewrites command to 'claude-hook' and keeps siblings intact."""
        from claude_mpm.cli.startup_migrations import (
            _migrate_baked_hook_paths,
        )

        baked = self._baked_fast_path()
        settings_path = patch_cwd / ".claude" / "settings.local.json"
        payload = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [
                            {
                                "type": "command",
                                "command": baked,
                                "args": ["--session", "abc"],
                                "disable": False,
                                "_mpm": True,
                            }
                        ],
                    }
                ]
            }
        }
        self._write_settings(settings_path, payload)

        assert _migrate_baked_hook_paths() is True

        rewritten = json.loads(settings_path.read_text())
        cmd_entry = rewritten["hooks"]["PreToolUse"][0]["hooks"][0]

        # Command rewritten to the PATH-based entry point.
        assert cmd_entry["command"] == "claude-hook"
        # All sibling fields preserved verbatim.
        assert cmd_entry["type"] == "command"
        assert cmd_entry["args"] == ["--session", "abc"]
        assert cmd_entry["disable"] is False
        assert cmd_entry["_mpm"] is True
        # The hook entry's matcher is also preserved.
        assert rewritten["hooks"]["PreToolUse"][0]["matcher"] == "Bash"

    def test_run_is_idempotent(self, patch_cwd):
        """Running the migration twice produces identical output."""
        from claude_mpm.cli.startup_migrations import (
            _migrate_baked_hook_paths,
        )

        settings_path = patch_cwd / ".claude" / "settings.local.json"
        self._write_settings(
            settings_path,
            self._settings_with_command(self._baked_fast_path()),
        )

        assert _migrate_baked_hook_paths() is True
        first = settings_path.read_text()

        assert _migrate_baked_hook_paths() is True
        second = settings_path.read_text()

        assert first == second
        # And the file is definitely on the cleaned-up form.
        assert "claude-hook-fast.sh" not in second
        data = json.loads(second)
        assert data["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == "claude-hook"

    def test_run_does_not_touch_unrelated_commands(self, patch_cwd):
        """Commands that don't match the patterns are left untouched."""
        from claude_mpm.cli.startup_migrations import (
            _migrate_baked_hook_paths,
        )

        unrelated = "/usr/local/bin/my-custom-hook --flag"
        settings_path = patch_cwd / ".claude" / "settings.local.json"
        self._write_settings(settings_path, self._settings_with_command(unrelated))

        assert _migrate_baked_hook_paths() is True

        data = json.loads(settings_path.read_text())
        # Unchanged.
        assert data["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == unrelated

    # ----- user-global settings (issue #552 devil's advocate gap) -----

    @pytest.fixture
    def patch_cwd_and_home(self, tmp_path):
        """Patch both ``Path.cwd()`` and ``Path.home()`` to isolated tmp dirs.

        Required for tests that exercise the user-global settings paths
        ``~/.claude/settings.json`` and ``~/.claude/settings.local.json``,
        because :func:`_all_claude_settings_files` derives them from
        ``Path.home()``.
        """
        home = tmp_path / "home"
        project = tmp_path / "project"
        (home / ".claude").mkdir(parents=True)
        (project / ".claude").mkdir(parents=True)
        with patch.object(Path, "home", return_value=home):
            with patch.object(Path, "cwd", return_value=project):
                yield home, project

    def test_check_true_when_user_global_settings_has_baked_path(
        self, patch_cwd_and_home
    ):
        """check() must inspect ~/.claude/settings.json, not just project dir.

        Reproduces the gap identified by the devil's advocate review of
        v6.4.15: ``pip install --user`` installs cause
        ``HookInstaller._update_claude_settings`` to write hook commands
        into ``~/.claude/settings.json``.  Without this scan, the baked
        path stays there forever.
        """
        from claude_mpm.cli.startup_migrations import (
            _check_baked_hook_paths_exist,
        )

        home, _project = patch_cwd_and_home
        user_global = home / ".claude" / "settings.json"
        self._write_settings(
            user_global, self._settings_with_command(self._baked_fast_path())
        )

        assert _check_baked_hook_paths_exist() is True

    def test_run_rewrites_user_global_settings(self, patch_cwd_and_home):
        """run() must rewrite the baked path in ~/.claude/settings.json too."""
        from claude_mpm.cli.startup_migrations import (
            _migrate_baked_hook_paths,
        )

        home, _project = patch_cwd_and_home
        user_global = home / ".claude" / "settings.json"
        baked = self._baked_uv_path()
        self._write_settings(user_global, self._settings_with_command(baked))

        assert _migrate_baked_hook_paths() is True

        data = json.loads(user_global.read_text())
        assert data["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == "claude-hook"
        # And the file no longer contains the baked path substring.
        assert "uv/tools/claude-mpm/" not in user_global.read_text()


class TestGetHookCommandPathBased:
    """Integration-style test for ``HookInstaller.get_hook_command()``.

    After the fix for issue #552 the method must return the literal
    ``"claude-hook"`` unconditionally, regardless of whether
    ``claude-hook-fast.sh`` is discoverable on disk.
    """

    def test_get_hook_command_returns_claude_hook_unconditionally(self):
        """Returns the literal 'claude-hook' with no script-on-disk dependency."""
        from claude_mpm.hooks.claude_hooks.installer import HookInstaller

        installer = HookInstaller()

        # Even if every legacy path resolution mechanism is broken, the
        # method must return "claude-hook".  Force the fast-hook path
        # lookup to fail to prove no fallback happens.
        with patch.object(
            HookInstaller,
            "_get_fast_hook_script_path",
            side_effect=FileNotFoundError("simulated stale uv tools install"),
        ):
            assert installer.get_hook_command() == "claude-hook"
            assert installer.get_hook_command(use_fast_hook=True) == "claude-hook"
            assert installer.get_hook_command(use_fast_hook=False) == "claude-hook"
