"""Unit tests for agent startup synchronization service.

Tests the startup integration using AgentSourceConfiguration and
GitSourceManager to ensure agent templates are synchronized correctly
on Claude MPM initialization.
"""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.models.git_repository import GitRepository
from claude_mpm.services.agents.startup_sync import (
    get_sync_status,
    sync_agents_on_startup,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_repo(
    url: str = "https://github.com/test/repo",
    subdirectory: str = "agents",
    branch: str = "main",
    enabled: bool = True,
    priority: int = 100,
) -> GitRepository:
    """Create a GitRepository for testing."""
    return GitRepository(
        url=url,
        subdirectory=subdirectory,
        branch=branch,
        enabled=enabled,
        priority=priority,
    )


def _make_mock_config(repos: list[GitRepository] | None = None, no_repos: bool = False):
    """Create a mock AgentSourceConfiguration."""
    mock_config = MagicMock()
    if no_repos:
        mock_config.get_enabled_repositories.return_value = []
    else:
        mock_config.get_enabled_repositories.return_value = repos or []
    return mock_config


# ---------------------------------------------------------------------------
# TestSyncAgentsOnStartup
# ---------------------------------------------------------------------------


class TestSyncAgentsOnStartup:
    """Test suite for sync_agents_on_startup function."""

    @patch("claude_mpm.services.agents.git_source_manager.GitSourceManager")
    @patch("claude_mpm.config.agent_sources.AgentSourceConfiguration.load")
    def test_reads_from_agent_source_configuration(self, mock_load, MockManager):
        """Verify AgentSourceConfiguration.load() is called (not Config())."""
        mock_load.return_value = _make_mock_config(no_repos=True)

        sync_agents_on_startup()

        mock_load.assert_called_once()

    @patch("claude_mpm.services.agents.git_source_manager.GitSourceManager")
    @patch("claude_mpm.config.agent_sources.AgentSourceConfiguration.load")
    def test_no_enabled_repos_returns_disabled(self, mock_load, MockManager):
        """When get_enabled_repositories() returns [], result has enabled=False."""
        mock_load.return_value = _make_mock_config(no_repos=True)

        result = sync_agents_on_startup()

        assert result["enabled"] is False
        assert result["sources_synced"] == 0
        assert result["total_downloaded"] == 0
        assert result["cache_hits"] == 0
        assert len(result["errors"]) == 0
        # GitSourceManager should NOT have been instantiated
        MockManager.assert_not_called()

    @patch("claude_mpm.services.agents.git_source_manager.GitSourceManager")
    @patch("claude_mpm.config.agent_sources.AgentSourceConfiguration.load")
    def test_syncs_all_enabled_repos(self, mock_load, MockManager):
        """With 2 enabled repos, both appear in sync results."""
        repo1 = _make_repo(url="https://github.com/org/repo1")
        repo2 = _make_repo(url="https://github.com/org/repo2")
        mock_load.return_value = _make_mock_config(repos=[repo1, repo2])

        mock_manager_instance = MagicMock()
        mock_manager_instance.sync_all_repositories.return_value = {
            repo1.identifier: {
                "synced": True,
                "files_updated": 3,
                "files_cached": 1,
            },
            repo2.identifier: {
                "synced": True,
                "files_updated": 2,
                "files_cached": 0,
            },
        }
        MockManager.return_value = mock_manager_instance

        result = sync_agents_on_startup()

        assert result["enabled"] is True
        assert result["sources_synced"] == 2
        assert result["total_downloaded"] == 5  # 3 + 2
        assert result["cache_hits"] == 1  # 1 + 0
        assert len(result["errors"]) == 0

        # Verify sync_all_repositories was called with both repos
        mock_manager_instance.sync_all_repositories.assert_called_once_with(
            repos=[repo1, repo2],
            force=False,
            show_progress=True,
        )

    @patch("claude_mpm.services.agents.git_source_manager.GitSourceManager")
    @patch("claude_mpm.config.agent_sources.AgentSourceConfiguration.load")
    def test_successful_single_source_sync(self, mock_load, MockManager):
        """Mock one repo syncing successfully, verify counts."""
        repo = _make_repo()
        mock_load.return_value = _make_mock_config(repos=[repo])

        mock_manager_instance = MagicMock()
        mock_manager_instance.sync_all_repositories.return_value = {
            repo.identifier: {
                "synced": True,
                "files_updated": 4,
                "files_cached": 2,
            },
        }
        MockManager.return_value = mock_manager_instance

        result = sync_agents_on_startup()

        assert result["enabled"] is True
        assert result["sources_synced"] == 1
        assert result["total_downloaded"] == 4
        assert result["cache_hits"] == 2
        assert len(result["errors"]) == 0
        assert result["duration_ms"] >= 0

    @patch("claude_mpm.services.agents.git_source_manager.GitSourceManager")
    @patch("claude_mpm.config.agent_sources.AgentSourceConfiguration.load")
    def test_partial_failure_continues(self, mock_load, MockManager):
        """First repo fails, second succeeds; result has 1 synced + 1 error."""
        repo1 = _make_repo(url="https://github.com/org/repo-bad")
        repo2 = _make_repo(url="https://github.com/org/repo-good")
        mock_load.return_value = _make_mock_config(repos=[repo1, repo2])

        mock_manager_instance = MagicMock()
        mock_manager_instance.sync_all_repositories.return_value = {
            repo1.identifier: {
                "synced": False,
                "error": "Network error",
            },
            repo2.identifier: {
                "synced": True,
                "files_updated": 1,
                "files_cached": 0,
            },
        }
        MockManager.return_value = mock_manager_instance

        result = sync_agents_on_startup()

        assert result["enabled"] is True
        assert result["sources_synced"] == 1
        assert result["total_downloaded"] == 1
        assert len(result["errors"]) == 1
        assert "Network error" in result["errors"][0]

    @patch("claude_mpm.services.agents.git_source_manager.GitSourceManager")
    @patch("claude_mpm.config.agent_sources.AgentSourceConfiguration.load")
    def test_exception_in_sync_doesnt_crash(self, mock_load, MockManager):
        """sync_all_repositories raises Exception; caught, error recorded."""
        repo = _make_repo()
        mock_load.return_value = _make_mock_config(repos=[repo])

        mock_manager_instance = MagicMock()
        mock_manager_instance.sync_all_repositories.side_effect = RuntimeError(
            "Unexpected failure"
        )
        MockManager.return_value = mock_manager_instance

        # Should NOT raise
        result = sync_agents_on_startup()

        assert len(result["errors"]) >= 1
        assert "Unexpected failure" in result["errors"][0]
        assert result["duration_ms"] >= 0

    @patch("claude_mpm.services.agents.git_source_manager.GitSourceManager")
    @patch("claude_mpm.config.agent_sources.AgentSourceConfiguration.load")
    def test_return_format_has_all_keys(self, mock_load, MockManager):
        """Verify all expected keys exist in the return dict."""
        mock_load.return_value = _make_mock_config(no_repos=True)

        result = sync_agents_on_startup()

        expected_keys = {
            "enabled",
            "sources_synced",
            "total_downloaded",
            "cache_hits",
            "errors",
            "duration_ms",
        }
        assert expected_keys.issubset(result.keys())

    @patch("claude_mpm.services.agents.git_source_manager.GitSourceManager")
    @patch("claude_mpm.config.agent_sources.AgentSourceConfiguration.load")
    def test_force_refresh_passed_to_manager(self, mock_load, MockManager):
        """Verify force=True is passed when force_refresh=True."""
        repo = _make_repo()
        mock_load.return_value = _make_mock_config(repos=[repo])

        mock_manager_instance = MagicMock()
        mock_manager_instance.sync_all_repositories.return_value = {
            repo.identifier: {
                "synced": True,
                "files_updated": 0,
                "files_cached": 0,
            },
        }
        MockManager.return_value = mock_manager_instance

        sync_agents_on_startup(force_refresh=True)

        mock_manager_instance.sync_all_repositories.assert_called_once_with(
            repos=[repo],
            force=True,
            show_progress=True,
        )

    @patch("claude_mpm.services.agents.git_source_manager.GitSourceManager")
    @patch("claude_mpm.config.agent_sources.AgentSourceConfiguration.load")
    def test_deprecated_config_param_emits_warning(self, mock_load, MockManager):
        """Passing config={} emits DeprecationWarning."""
        mock_load.return_value = _make_mock_config(no_repos=True)

        with pytest.warns(DeprecationWarning, match="deprecated"):
            sync_agents_on_startup(config={})

    @patch("claude_mpm.services.agents.git_source_manager.GitSourceManager")
    @patch("claude_mpm.config.agent_sources.AgentSourceConfiguration.load")
    def test_manifest_check_happens_via_sync_chain(self, mock_load, MockManager):
        """Verify sync_all_repositories is called (it internally triggers manifest checks)."""
        repo = _make_repo()
        mock_load.return_value = _make_mock_config(repos=[repo])

        mock_manager_instance = MagicMock()
        mock_manager_instance.sync_all_repositories.return_value = {
            repo.identifier: {
                "synced": True,
                "files_updated": 0,
                "files_cached": 0,
            },
        }
        MockManager.return_value = mock_manager_instance

        sync_agents_on_startup()

        # sync_all_repositories is the entry point that triggers the full
        # sync chain: GitSourceManager.sync_repository -> GitSourceSyncService.sync_agents
        # -> _check_manifest_compatibility
        mock_manager_instance.sync_all_repositories.assert_called_once()


# ---------------------------------------------------------------------------
# TestGetSyncStatus
# ---------------------------------------------------------------------------


class TestGetSyncStatus:
    """Test suite for get_sync_status function."""

    @patch("claude_mpm.config.agent_sources.AgentSourceConfiguration.load")
    def test_status_with_enabled_repos(self, mock_load):
        """Returns enabled=True and correct count."""
        repo1 = _make_repo(url="https://github.com/org/repo1")
        repo2 = _make_repo(url="https://github.com/org/repo2")
        mock_load.return_value = _make_mock_config(repos=[repo1, repo2])

        status = get_sync_status()

        assert status["enabled"] is True
        assert status["sources_configured"] == 2
        assert "cache_dir" in status
        assert "last_sync" in status

    @patch("claude_mpm.config.agent_sources.AgentSourceConfiguration.load")
    def test_status_with_no_repos(self, mock_load):
        """Returns enabled=False when no repos configured."""
        mock_load.return_value = _make_mock_config(no_repos=True)

        status = get_sync_status()

        assert status["enabled"] is False
        assert status["sources_configured"] == 0

    @patch("claude_mpm.config.agent_sources.AgentSourceConfiguration.load")
    def test_status_handles_exceptions(self, mock_load):
        """On exception, returns error dict."""
        mock_load.side_effect = Exception("Config error")

        status = get_sync_status()

        assert status["enabled"] is False
        assert "error" in status
        assert status["error"] == "Config error"

    @patch("claude_mpm.config.agent_sources.AgentSourceConfiguration.load")
    def test_cache_dir_is_resolved_path(self, mock_load):
        """cache_dir doesn't contain ~."""
        repo = _make_repo()
        mock_load.return_value = _make_mock_config(repos=[repo])

        status = get_sync_status()

        assert "~" not in status["cache_dir"]
        # Should be an absolute path produced by Path.home() / ...
        assert status["cache_dir"].startswith("/")


# ---------------------------------------------------------------------------
# TestAgentSourcesChangedSinceLastSync
# ---------------------------------------------------------------------------


class TestAgentSourcesChangedSinceLastSync:
    """Test suite for _agent_sources_changed_since_last_sync from cli.startup."""

    def _import_func(self):
        """Import the private function under test."""
        from claude_mpm.cli.startup import _agent_sources_changed_since_last_sync

        return _agent_sources_changed_since_last_sync

    def test_returns_false_when_no_config_file(self, tmp_path, monkeypatch):
        """Config file doesn't exist -> False."""
        # Point Path.home() at a temp dir so the config file doesn't exist
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

        func = self._import_func()
        assert func() is False

    def test_returns_true_when_config_newer_than_sync(self, tmp_path, monkeypatch):
        """Config mtime > last sync -> True."""
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

        # Create config file
        config_dir = tmp_path / ".claude-mpm" / "config"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "agent_sources.yaml"
        config_file.write_text("repositories: []\n")

        # Create sync-state with an old timestamp (config is newer)
        cache_dir = tmp_path / ".claude-mpm" / "cache"
        cache_dir.mkdir(parents=True)
        state_file = cache_dir / "sync-state.json"
        # Use a timestamp well in the past
        old_timestamp = time.time() - 3600
        state_file.write_text(json.dumps({"agents": old_timestamp}))

        func = self._import_func()
        assert func() is True

    def test_returns_false_when_sync_newer_than_config(self, tmp_path, monkeypatch):
        """Last sync > config mtime -> False."""
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

        # Create config file
        config_dir = tmp_path / ".claude-mpm" / "config"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "agent_sources.yaml"
        config_file.write_text("repositories: []\n")

        # Create sync-state with a future timestamp (sync is newer)
        cache_dir = tmp_path / ".claude-mpm" / "cache"
        cache_dir.mkdir(parents=True)
        state_file = cache_dir / "sync-state.json"
        future_timestamp = time.time() + 3600
        state_file.write_text(json.dumps({"agents": future_timestamp}))

        func = self._import_func()
        assert func() is False

    def test_returns_false_on_os_error(self, tmp_path, monkeypatch):
        """stat() raises OSError -> False."""
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

        # Create config file so it exists
        config_dir = tmp_path / ".claude-mpm" / "config"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "agent_sources.yaml"
        config_file.write_text("repositories: []\n")

        # Create sync-state so _load_sync_state doesn't return empty
        cache_dir = tmp_path / ".claude-mpm" / "cache"
        cache_dir.mkdir(parents=True)
        state_file = cache_dir / "sync-state.json"
        state_file.write_text(json.dumps({"agents": 0}))

        # Monkeypatch stat to raise OSError only on the explicit stat()
        # call (not on the exists() check which also calls stat internally).
        # We use a call counter: exists() triggers the first stat, and the
        # explicit config_path.stat() in the function body is the second.
        original_stat = Path.stat
        call_count = {"n": 0}

        def broken_stat(self, *args, **kwargs):
            if "agent_sources.yaml" in str(self):
                call_count["n"] += 1
                if call_count["n"] > 1:
                    raise OSError("Permission denied")
            return original_stat(self, *args, **kwargs)

        monkeypatch.setattr(Path, "stat", broken_stat)

        func = self._import_func()
        assert func() is False


# ---------------------------------------------------------------------------
# TestDisplayManifestCompatibilityWarnings
# ---------------------------------------------------------------------------


class TestDisplayManifestCompatibilityWarnings:
    """Test suite for _display_manifest_compatibility_warnings from cli.startup."""

    def _import_func(self):
        """Import the private function under test."""
        from claude_mpm.cli.startup import _display_manifest_compatibility_warnings

        return _display_manifest_compatibility_warnings

    # Patch ManifestCache at its source-module location so the lazy import resolves.
    _CACHE_PATCH = (
        "claude_mpm.services.agents.compatibility.manifest_cache.ManifestCache"
    )

    def test_warning_printed_when_cli_version_too_low(self, capsys):
        """When min_cli_version > current CLI version, prints warning to stdout."""
        mock_cache_instance = MagicMock()
        mock_cache_instance.get_all.return_value = [
            {
                "source_id": "org/my-agents",
                "min_cli_version": "99.0.0",
                "raw_content": "",
            }
        ]

        with (
            patch(self._CACHE_PATCH, return_value=mock_cache_instance),
            patch("claude_mpm.__version__", "5.9.69"),
        ):
            self._import_func()()

        captured = capsys.readouterr()
        assert "org/my-agents" in captured.out
        assert "requires claude-mpm >= 99.0.0" in captured.out
        assert "you have 5.9.69" in captured.out
        assert "Use your installation method to upgrade claude-mpm" in captured.out

    def test_no_warning_when_cli_version_satisfies(self, capsys):
        """When current CLI version >= min_cli_version, no output."""
        mock_cache_instance = MagicMock()
        mock_cache_instance.get_all.return_value = [
            {
                "source_id": "org/my-agents",
                "min_cli_version": "1.0.0",
                "raw_content": "",
            }
        ]

        with (
            patch(self._CACHE_PATCH, return_value=mock_cache_instance),
            patch("claude_mpm.__version__", "5.9.69"),
        ):
            self._import_func()()

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_no_warning_when_cache_empty(self, capsys):
        """Empty cache -> no output, no error."""
        mock_cache_instance = MagicMock()
        mock_cache_instance.get_all.return_value = []

        with patch(self._CACHE_PATCH, return_value=mock_cache_instance):
            self._import_func()()

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_no_warning_when_min_cli_version_is_zero(self, capsys):
        """min_cli_version == '0.0.0' is treated as unset -> no warning."""
        mock_cache_instance = MagicMock()
        mock_cache_instance.get_all.return_value = [
            {
                "source_id": "org/agents",
                "min_cli_version": "0.0.0",
                "raw_content": "",
            }
        ]

        with (
            patch(self._CACHE_PATCH, return_value=mock_cache_instance),
            patch("claude_mpm.__version__", "5.9.69"),
        ):
            self._import_func()()

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_no_warning_when_min_cli_version_is_none(self, capsys):
        """min_cli_version is None -> no warning."""
        mock_cache_instance = MagicMock()
        mock_cache_instance.get_all.return_value = [
            {
                "source_id": "org/agents",
                "min_cli_version": None,
                "raw_content": "",
            }
        ]

        with (
            patch(self._CACHE_PATCH, return_value=mock_cache_instance),
            patch("claude_mpm.__version__", "5.9.69"),
        ):
            self._import_func()()

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_migration_notes_displayed(self, capsys):
        """When raw_content has migration_notes, they are printed."""
        import yaml

        raw_manifest = yaml.dump(
            {
                "repo_format_version": "1.0.0",
                "min_cli_version": "99.0.0",
                "migration_notes": "Upgrade to v99 for new agent format support.",
            }
        )

        mock_cache_instance = MagicMock()
        mock_cache_instance.get_all.return_value = [
            {
                "source_id": "org/agents",
                "min_cli_version": "99.0.0",
                "raw_content": raw_manifest,
            }
        ]

        with (
            patch(self._CACHE_PATCH, return_value=mock_cache_instance),
            patch("claude_mpm.__version__", "5.9.69"),
        ):
            self._import_func()()

        captured = capsys.readouterr()
        assert "Migration notes:" in captured.out
        assert "Upgrade to v99" in captured.out

    def test_no_migration_notes_when_absent(self, capsys):
        """When raw_content has no migration_notes, only the warning is printed."""
        import yaml

        raw_manifest = yaml.dump(
            {
                "repo_format_version": "1.0.0",
                "min_cli_version": "99.0.0",
            }
        )

        mock_cache_instance = MagicMock()
        mock_cache_instance.get_all.return_value = [
            {
                "source_id": "org/agents",
                "min_cli_version": "99.0.0",
                "raw_content": raw_manifest,
            }
        ]

        with (
            patch(self._CACHE_PATCH, return_value=mock_cache_instance),
            patch("claude_mpm.__version__", "5.9.69"),
        ):
            self._import_func()()

        captured = capsys.readouterr()
        assert "org/agents" in captured.out
        assert "Migration notes:" not in captured.out

    def test_graceful_on_manifest_cache_exception(self, capsys):
        """If ManifestCache raises, function returns silently (never blocks startup)."""
        with patch(self._CACHE_PATCH, side_effect=RuntimeError("DB locked")):
            self._import_func()()

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_multiple_sources_only_warns_for_incompatible(self, capsys):
        """With 3 sources, only the 2 with too-high min_cli_version get warnings."""
        mock_cache_instance = MagicMock()
        mock_cache_instance.get_all.return_value = [
            {
                "source_id": "org/agents-ok",
                "min_cli_version": "1.0.0",
                "raw_content": "",
            },
            {
                "source_id": "org/agents-warn1",
                "min_cli_version": "99.0.0",
                "raw_content": "",
            },
            {
                "source_id": "org/agents-warn2",
                "min_cli_version": "100.0.0",
                "raw_content": "",
            },
        ]

        with (
            patch(self._CACHE_PATCH, return_value=mock_cache_instance),
            patch("claude_mpm.__version__", "5.9.69"),
        ):
            self._import_func()()

        captured = capsys.readouterr()
        assert "org/agents-ok" not in captured.out
        assert "org/agents-warn1" in captured.out
        assert "org/agents-warn2" in captured.out

    def test_invalid_min_cli_version_string_skipped(self, capsys):
        """If min_cli_version is garbage, that entry is skipped (no crash)."""
        mock_cache_instance = MagicMock()
        mock_cache_instance.get_all.return_value = [
            {
                "source_id": "org/agents",
                "min_cli_version": "not-a-version",
                "raw_content": "",
            }
        ]

        with (
            patch(self._CACHE_PATCH, return_value=mock_cache_instance),
            patch("claude_mpm.__version__", "5.9.69"),
        ):
            self._import_func()()

        captured = capsys.readouterr()
        # Should not crash and should not print a warning
        assert "org/agents" not in captured.out
