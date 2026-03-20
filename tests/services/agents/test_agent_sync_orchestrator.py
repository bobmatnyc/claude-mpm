"""Tests for AgentSyncOrchestrator (Phase 3 agent pipeline unification).

Verifies that AgentSyncOrchestrator correctly:
- Delegates to GitSourceManager.sync_all_repositories
- Propagates the force flag
- Handles empty repo lists gracefully
- Catches network/config errors without raising
- Resolves default repos from AgentSourceConfiguration when no repos given
- Allows callers to override repos
- Aggregates per-repo results into a SyncResult dataclass
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.agents.sync_orchestrator import (
    AgentSyncOrchestrator,
    SyncResult,
)

# The orchestrator uses lazy imports inside sync(), so we patch the source
# modules rather than attributes on the orchestrator module.
_PATCH_CONFIG = "claude_mpm.config.agent_sources.AgentSourceConfiguration"
_PATCH_MANAGER = "claude_mpm.services.agents.git_source_manager.GitSourceManager"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_sync_result(
    synced: bool, files_updated: int = 0, files_cached: int = 0, error: str = ""
) -> dict:
    """Helper to build a per-repo sync result dict matching GitSourceManager format."""
    result: dict = {"synced": synced}
    if synced:
        result["files_updated"] = files_updated
        result["files_cached"] = files_cached
    else:
        result["error"] = error or "Unknown error"
    return result


def _make_repo(
    identifier: str = "owner/repo/agents", enabled: bool = True
) -> MagicMock:
    """Create a mock GitRepository."""
    repo = MagicMock()
    repo.identifier = identifier
    repo.enabled = enabled
    repo.priority = 100
    return repo


# ---------------------------------------------------------------------------
# SyncResult dataclass defaults
# ---------------------------------------------------------------------------


class TestSyncResultDefaults:
    """Verify SyncResult dataclass has sensible defaults."""

    def test_default_values(self):
        result = SyncResult()
        assert result.enabled is False
        assert result.sources_synced == 0
        assert result.sources_failed == 0
        assert result.total_downloaded == 0
        assert result.cache_hits == 0
        assert result.errors == []
        assert result.duration_ms == 0
        assert result.raw_results == {}

    def test_errors_list_is_independent_per_instance(self):
        """Verify each SyncResult gets its own errors list (no mutable default sharing)."""
        r1 = SyncResult()
        r2 = SyncResult()
        r1.errors.append("oops")
        assert r2.errors == []


# ---------------------------------------------------------------------------
# Delegation to GitSourceManager
# ---------------------------------------------------------------------------


class TestSyncDelegation:
    """Verify sync() delegates to GitSourceManager.sync_all_repositories."""

    @patch(_PATCH_MANAGER)
    @patch(_PATCH_CONFIG)
    def test_delegates_to_git_source_manager(self, mock_config_cls, mock_manager_cls):
        """sync() should call sync_all_repositories with the correct args."""
        repo = _make_repo()
        mock_config = MagicMock()
        mock_config.get_enabled_repositories.return_value = [repo]
        mock_config_cls.load.return_value = mock_config

        mock_manager = MagicMock()
        mock_manager.sync_all_repositories.return_value = {
            repo.identifier: _make_sync_result(
                synced=True, files_updated=3, files_cached=7
            )
        }
        mock_manager_cls.return_value = mock_manager

        orch = AgentSyncOrchestrator(show_progress=False)
        result = orch.sync(force=True)

        mock_manager.sync_all_repositories.assert_called_once_with(
            repos=[repo],
            force=True,
            show_progress=False,
        )

        assert result.enabled is True
        assert result.sources_synced == 1
        assert result.sources_failed == 0
        assert result.total_downloaded == 3
        assert result.cache_hits == 7
        assert result.errors == []
        assert result.duration_ms >= 0

    @patch(_PATCH_MANAGER)
    @patch(_PATCH_CONFIG)
    def test_force_flag_propagation(self, mock_config_cls, mock_manager_cls):
        """force=False should propagate through to sync_all_repositories."""
        repo = _make_repo()
        mock_config = MagicMock()
        mock_config.get_enabled_repositories.return_value = [repo]
        mock_config_cls.load.return_value = mock_config

        mock_manager = MagicMock()
        mock_manager.sync_all_repositories.return_value = {}
        mock_manager_cls.return_value = mock_manager

        orch = AgentSyncOrchestrator(show_progress=True)
        orch.sync(force=False)

        call_kwargs = mock_manager.sync_all_repositories.call_args[1]
        assert call_kwargs["force"] is False
        assert call_kwargs["show_progress"] is True


# ---------------------------------------------------------------------------
# Empty repos / no config
# ---------------------------------------------------------------------------


class TestEmptyRepos:
    """Verify behaviour when no repositories are configured."""

    @patch(_PATCH_MANAGER)
    @patch(_PATCH_CONFIG)
    def test_no_enabled_repos_returns_disabled(self, mock_config_cls, mock_manager_cls):
        mock_config = MagicMock()
        mock_config.get_enabled_repositories.return_value = []
        mock_config_cls.load.return_value = mock_config

        orch = AgentSyncOrchestrator()
        result = orch.sync()

        assert result.enabled is False
        assert result.sources_synced == 0
        assert result.errors == []
        # GitSourceManager should never be instantiated
        mock_manager_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Network / config error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Verify that errors are captured in SyncResult, never raised."""

    @patch(_PATCH_CONFIG)
    def test_config_load_failure_captured(self, mock_config_cls):
        """If AgentSourceConfiguration.load() raises, error is captured."""
        mock_config_cls.load.side_effect = RuntimeError("YAML corrupt")

        orch = AgentSyncOrchestrator()
        result = orch.sync()

        assert result.enabled is False
        assert len(result.errors) == 1
        assert "YAML corrupt" in result.errors[0]

    @patch(_PATCH_MANAGER)
    @patch(_PATCH_CONFIG)
    def test_sync_all_repos_failure_captured(self, mock_config_cls, mock_manager_cls):
        """If sync_all_repositories raises, error is captured."""
        repo = _make_repo()
        mock_config = MagicMock()
        mock_config.get_enabled_repositories.return_value = [repo]
        mock_config_cls.load.return_value = mock_config

        mock_manager = MagicMock()
        mock_manager.sync_all_repositories.side_effect = ConnectionError("Network down")
        mock_manager_cls.return_value = mock_manager

        orch = AgentSyncOrchestrator()
        result = orch.sync()

        assert len(result.errors) == 1
        assert "Network down" in result.errors[0]

    @patch(_PATCH_MANAGER)
    @patch(_PATCH_CONFIG)
    def test_partial_repo_failure_aggregated(self, mock_config_cls, mock_manager_cls):
        """When one repo succeeds and another fails, both are aggregated."""
        repo_ok = _make_repo("owner/ok-repo/agents")
        repo_fail = _make_repo("owner/fail-repo/agents")

        mock_config = MagicMock()
        mock_config.get_enabled_repositories.return_value = [repo_ok, repo_fail]
        mock_config_cls.load.return_value = mock_config

        mock_manager = MagicMock()
        mock_manager.sync_all_repositories.return_value = {
            repo_ok.identifier: _make_sync_result(
                synced=True, files_updated=5, files_cached=2
            ),
            repo_fail.identifier: _make_sync_result(
                synced=False, error="404 Not Found"
            ),
        }
        mock_manager_cls.return_value = mock_manager

        orch = AgentSyncOrchestrator()
        result = orch.sync()

        assert result.enabled is True
        assert result.sources_synced == 1
        assert result.sources_failed == 1
        assert result.total_downloaded == 5
        assert result.cache_hits == 2
        assert len(result.errors) == 1
        assert "404 Not Found" in result.errors[0]


# ---------------------------------------------------------------------------
# Custom repos override
# ---------------------------------------------------------------------------


class TestCustomReposOverride:
    """Verify that passing explicit repos bypasses config loading."""

    @patch(_PATCH_MANAGER)
    def test_explicit_repos_skip_config_load(self, mock_manager_cls):
        """When repos are passed explicitly, AgentSourceConfiguration is NOT loaded."""
        repo = _make_repo("custom/repo/agents")
        mock_manager = MagicMock()
        mock_manager.sync_all_repositories.return_value = {
            repo.identifier: _make_sync_result(synced=True, files_updated=1)
        }
        mock_manager_cls.return_value = mock_manager

        orch = AgentSyncOrchestrator()
        result = orch.sync(repos=[repo])

        assert result.enabled is True
        assert result.sources_synced == 1

    @patch(_PATCH_MANAGER)
    def test_explicit_empty_repos_returns_disabled(self, mock_manager_cls):
        """Passing an explicit empty list means no sync."""
        orch = AgentSyncOrchestrator()
        result = orch.sync(repos=[])

        assert result.enabled is False
        mock_manager_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Raw results passthrough
# ---------------------------------------------------------------------------


class TestRawResultsPassthrough:
    """Verify raw_results contains the per-repo dicts from GitSourceManager."""

    @patch(_PATCH_MANAGER)
    @patch(_PATCH_CONFIG)
    def test_raw_results_populated(self, mock_config_cls, mock_manager_cls):
        repo = _make_repo()
        mock_config = MagicMock()
        mock_config.get_enabled_repositories.return_value = [repo]
        mock_config_cls.load.return_value = mock_config

        expected_raw = {
            repo.identifier: _make_sync_result(
                synced=True, files_updated=10, files_cached=20
            )
        }
        mock_manager = MagicMock()
        mock_manager.sync_all_repositories.return_value = expected_raw
        mock_manager_cls.return_value = mock_manager

        orch = AgentSyncOrchestrator()
        result = orch.sync()

        assert result.raw_results == expected_raw
