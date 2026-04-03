"""
Tests for the skill_scope_v1 startup migration.

Verifies that check_plugin_scope_v1 correctly identifies user-scoped Claude
Code plugins that are foreign to the current project, and that
migrate_plugin_scope_v1 moves them to project scope when the user confirms.
"""

import json
from pathlib import Path
from unittest.mock import patch


class TestCheckPluginScopeV1:
    """Tests for check_plugin_scope_v1."""

    def _write_plugins_json(self, home: Path, content: dict) -> None:
        """Write a mock installed_plugins.json to the temp home directory."""
        plugins_dir = home / ".claude" / "plugins"
        plugins_dir.mkdir(parents=True, exist_ok=True)
        (plugins_dir / "installed_plugins.json").write_text(json.dumps(content))

    def test_returns_true_when_foreign_user_scoped_plugin_exists(self, tmp_path):
        """Foreign user-scoped plugin triggers migration needed."""
        from claude_mpm.cli.startup_migrations import check_plugin_scope_v1

        self._write_plugins_json(
            tmp_path,
            {
                "version": 2,
                "plugins": {
                    "duetto@duetto-marketplace": [
                        {
                            "scope": "user",
                            "installPath": "/Users/masa/.claude/plugins/cache/duetto-marketplace/duetto/1.0.0",
                            "version": "1.0.0",
                            "installedAt": "2026-03-26T22:09:52.606Z",
                            "lastUpdated": "2026-03-26T22:09:52.606Z",
                            "gitCommitSha": "abc123",
                        }
                    ]
                },
            },
        )

        with (
            patch.object(Path, "home", return_value=tmp_path),
            patch.object(
                Path, "cwd", return_value=Path("/Users/masa/Projects/claude-mpm")
            ),
        ):
            result = check_plugin_scope_v1()

        assert result is True

    def test_foreign_plugins_stored_in_cache(self, tmp_path):
        """Check populates _plugin_scope_check_result with foreign plugin details."""
        import claude_mpm.cli.startup_migrations as m

        self._write_plugins_json(
            tmp_path,
            {
                "version": 2,
                "plugins": {
                    "duetto@duetto-marketplace": [
                        {
                            "scope": "user",
                            "installPath": "/some/path",
                            "version": "1.0.0",
                            "installedAt": "2026-03-26T22:09:52.606Z",
                            "lastUpdated": "2026-03-26T22:09:52.606Z",
                            "gitCommitSha": "abc123",
                        }
                    ]
                },
            },
        )

        with (
            patch.object(Path, "home", return_value=tmp_path),
            patch.object(
                Path, "cwd", return_value=Path("/Users/masa/Projects/claude-mpm")
            ),
        ):
            m.check_plugin_scope_v1()

        cache = m._plugin_scope_check_result
        assert "foreign_plugins" in cache
        assert len(cache["foreign_plugins"]) == 1
        assert cache["foreign_plugins"][0]["name"] == "duetto"
        assert cache["foreign_plugins"][0]["key"] == "duetto@duetto-marketplace"

    def test_returns_false_when_no_user_scoped_plugins(self, tmp_path):
        """No user-scoped plugins means migration is not needed."""
        from claude_mpm.cli.startup_migrations import check_plugin_scope_v1

        self._write_plugins_json(
            tmp_path,
            {
                "version": 2,
                "plugins": {
                    "frontend-design@claude-plugins-official": [
                        {
                            "scope": "project",
                            "projectPath": "/Users/masa/Duetto/repos/apex-companion",
                            "installPath": "/some/path",
                            "version": "unknown",
                            "installedAt": "2026-03-11T03:26:00.245Z",
                            "lastUpdated": "2026-03-30T20:26:50.653Z",
                            "gitCommitSha": "bd041495",
                        }
                    ]
                },
            },
        )

        with (
            patch.object(Path, "home", return_value=tmp_path),
            patch.object(
                Path, "cwd", return_value=Path("/Users/masa/Projects/claude-mpm")
            ),
        ):
            result = check_plugin_scope_v1()

        assert result is False

    def test_returns_false_when_user_scoped_plugin_matches_project(self, tmp_path):
        """User-scoped plugin whose name matches the project is not foreign."""
        from claude_mpm.cli.startup_migrations import check_plugin_scope_v1

        self._write_plugins_json(
            tmp_path,
            {
                "version": 2,
                "plugins": {
                    "claude-mpm@claude-mpm-marketplace": [
                        {
                            "scope": "user",
                            "installPath": "/some/path",
                            "version": "5.11.4",
                            "installedAt": "2026-03-25T12:58:03.216Z",
                            "lastUpdated": "2026-03-25T12:58:03.216Z",
                            "gitCommitSha": "9546fb9f",
                        }
                    ]
                },
            },
        )

        with (
            patch.object(Path, "home", return_value=tmp_path),
            # CWD name is 'claude-mpm', matching the plugin name
            patch.object(
                Path, "cwd", return_value=Path("/Users/masa/Projects/claude-mpm")
            ),
        ):
            result = check_plugin_scope_v1()

        assert result is False

    def test_returns_false_when_plugins_file_missing(self, tmp_path):
        """No installed_plugins.json means nothing to migrate."""
        from claude_mpm.cli.startup_migrations import check_plugin_scope_v1

        with (
            patch.object(Path, "home", return_value=tmp_path),
            patch.object(Path, "cwd", return_value=Path("/Users/masa/Projects/my-app")),
        ):
            result = check_plugin_scope_v1()

        assert result is False

    def test_multiple_foreign_plugins_all_detected(self, tmp_path):
        """All foreign user-scoped plugins are captured in the cache."""
        import claude_mpm.cli.startup_migrations as m

        self._write_plugins_json(
            tmp_path,
            {
                "version": 2,
                "plugins": {
                    "duetto@duetto-marketplace": [
                        {
                            "scope": "user",
                            "installPath": "/path/duetto",
                            "version": "1.0.0",
                            "installedAt": "2026-03-26T22:09:52.606Z",
                            "lastUpdated": "2026-03-26T22:09:52.606Z",
                            "gitCommitSha": "abc",
                        }
                    ],
                    "rust-analyzer-lsp@claude-plugins-official": [
                        {
                            "scope": "user",
                            "installPath": "/path/rust",
                            "version": "1.0.0",
                            "installedAt": "2026-02-28T23:32:56.684Z",
                            "lastUpdated": "2026-02-28T23:32:56.684Z",
                            "gitCommitSha": "def",
                        }
                    ],
                },
            },
        )

        with (
            patch.object(Path, "home", return_value=tmp_path),
            patch.object(
                Path, "cwd", return_value=Path("/Users/masa/Projects/claude-mpm")
            ),
        ):
            result = m.check_plugin_scope_v1()

        assert result is True
        foreign = m._plugin_scope_check_result["foreign_plugins"]
        assert len(foreign) == 2
        names = {p["name"] for p in foreign}
        assert names == {"duetto", "rust-analyzer-lsp"}


class TestMigratePluginScopeV1:
    """Tests for migrate_plugin_scope_v1."""

    def _write_plugins_json(self, home: Path, content: dict) -> None:
        plugins_dir = home / ".claude" / "plugins"
        plugins_dir.mkdir(parents=True, exist_ok=True)
        (plugins_dir / "installed_plugins.json").write_text(json.dumps(content))

    def _read_plugins_json(self, path: Path) -> dict:
        with open(path) as f:
            return json.load(f)

    def test_moves_plugin_to_project_scope_on_confirm(self, tmp_path):
        """Confirming 'y' moves the plugin to project scope."""
        import claude_mpm.cli.startup_migrations as m

        plugin_content = {
            "version": 2,
            "plugins": {
                "duetto@duetto-marketplace": [
                    {
                        "scope": "user",
                        "installPath": "/path/duetto",
                        "version": "1.0.0",
                        "installedAt": "2026-03-26T22:09:52.606Z",
                        "lastUpdated": "2026-03-26T22:09:52.606Z",
                        "gitCommitSha": "abc",
                    }
                ]
            },
        }
        self._write_plugins_json(tmp_path, plugin_content)

        project_dir = tmp_path / "myproject"
        project_dir.mkdir()

        with (
            patch.object(Path, "home", return_value=tmp_path),
            patch.object(Path, "cwd", return_value=project_dir),
            patch("builtins.input", return_value="y"),
        ):
            m.check_plugin_scope_v1()
            result = m.migrate_plugin_scope_v1()

        assert result is True

        # Global registry should no longer have the user-scoped entry
        global_data = self._read_plugins_json(
            tmp_path / ".claude" / "plugins" / "installed_plugins.json"
        )
        assert "duetto@duetto-marketplace" not in global_data.get("plugins", {})

        # Project registry should have the project-scoped entry
        project_plugins_file = (
            project_dir / ".claude" / "plugins" / "installed_plugins.json"
        )
        assert project_plugins_file.exists()
        proj_data = self._read_plugins_json(project_plugins_file)
        entries = proj_data["plugins"]["duetto@duetto-marketplace"]
        assert len(entries) == 1
        assert entries[0]["scope"] == "project"
        assert entries[0]["projectPath"] == str(project_dir)

    def test_skips_plugin_on_no_answer(self, tmp_path):
        """Pressing enter (no) keeps the plugin in user scope."""
        import claude_mpm.cli.startup_migrations as m

        plugin_content = {
            "version": 2,
            "plugins": {
                "duetto@duetto-marketplace": [
                    {
                        "scope": "user",
                        "installPath": "/path/duetto",
                        "version": "1.0.0",
                        "installedAt": "2026-03-26T22:09:52.606Z",
                        "lastUpdated": "2026-03-26T22:09:52.606Z",
                        "gitCommitSha": "abc",
                    }
                ]
            },
        }
        self._write_plugins_json(tmp_path, plugin_content)
        project_dir = tmp_path / "myproject"
        project_dir.mkdir()

        with (
            patch.object(Path, "home", return_value=tmp_path),
            patch.object(Path, "cwd", return_value=project_dir),
            patch("builtins.input", return_value=""),
        ):
            m.check_plugin_scope_v1()
            result = m.migrate_plugin_scope_v1()

        assert result is True

        # Global registry should be unchanged
        global_data = self._read_plugins_json(
            tmp_path / ".claude" / "plugins" / "installed_plugins.json"
        )
        assert "duetto@duetto-marketplace" in global_data["plugins"]
        assert global_data["plugins"]["duetto@duetto-marketplace"][0]["scope"] == "user"

        # No project registry should be created
        assert not (
            project_dir / ".claude" / "plugins" / "installed_plugins.json"
        ).exists()

    def test_returns_true_in_non_interactive_environment(self, tmp_path):
        """EOFError (non-interactive) is handled gracefully."""
        import claude_mpm.cli.startup_migrations as m

        plugin_content = {
            "version": 2,
            "plugins": {
                "duetto@duetto-marketplace": [
                    {
                        "scope": "user",
                        "installPath": "/path/duetto",
                        "version": "1.0.0",
                        "installedAt": "2026-03-26T22:09:52.606Z",
                        "lastUpdated": "2026-03-26T22:09:52.606Z",
                        "gitCommitSha": "abc",
                    }
                ]
            },
        }
        self._write_plugins_json(tmp_path, plugin_content)
        project_dir = tmp_path / "myproject"
        project_dir.mkdir()

        with (
            patch.object(Path, "home", return_value=tmp_path),
            patch.object(Path, "cwd", return_value=project_dir),
            patch("builtins.input", side_effect=EOFError),
        ):
            m.check_plugin_scope_v1()
            result = m.migrate_plugin_scope_v1()

        assert result is True

    def test_returns_true_when_no_foreign_plugins(self):
        """Migrate returns True immediately when cache has no foreign plugins."""
        import claude_mpm.cli.startup_migrations as m

        m._plugin_scope_check_result = {
            "project_name": "myproject",
            "foreign_plugins": [],
        }

        result = m.migrate_plugin_scope_v1()
        assert result is True
