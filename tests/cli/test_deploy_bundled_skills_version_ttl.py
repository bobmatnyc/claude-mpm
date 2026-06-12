"""Tests for version-aware TTL gate in deploy_bundled_skills() — issue #802.

Verifies that newly-added bundled skills are deployed after a package upgrade
instead of being blocked for up to 24 h by the global sync TTL.

Scenarios:
(a) Same version + fresh TTL  → deployment SKIPPED (early return).
(b) Changed version + fresh TTL → deployment RUNS (TTL bypassed by version mismatch).
(c) Fresh install / no sync-state → deployment RUNS (no prior timestamp).
(d) Sync-state missing the version field (legacy) → deployment RUNS once,
    then version is recorded.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers — keep all module-level state isolated per test
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def no_env_killswitch(monkeypatch):
    """Ensure the env-var kill-switch does not interfere."""
    monkeypatch.delenv("CLAUDE_MPM_DISABLE_AUTO_DEPLOY_PM_SKILLS", raising=False)


@pytest.fixture(autouse=True)
def no_plugin_installed():
    """Prevent the plugin-detection path from short-circuiting tests."""
    with patch(
        "claude_mpm.cli.startup._is_claude_mpm_plugin_installed", return_value=False
    ):
        yield


@pytest.fixture(autouse=True)
def auto_deploy_enabled():
    """Return auto_deploy=True from config loader so that path is not a blocker."""
    mock_loader_cls = MagicMock()
    mock_config = MagicMock()
    mock_config.get.return_value = {}  # auto_deploy defaults to True
    mock_loader_cls.return_value.load_main_config.return_value = mock_config

    with patch("claude_mpm.core.shared.config_loader.ConfigLoader", mock_loader_cls):
        yield


@pytest.fixture()
def mock_skills_service():
    """Return a mock SkillsService that records deployment calls."""
    instance = MagicMock()
    instance.deploy_bundled_skills.return_value = {
        "deployed": ["skill-a"],
        "errors": [],
    }
    with patch("claude_mpm.skills.skills_service.SkillsService", return_value=instance):
        yield instance


# ---------------------------------------------------------------------------
# Tests for the low-level helpers
# ---------------------------------------------------------------------------


class TestGetPackageVersion:
    """_get_package_version() delegates to claude_mpm.__version__."""

    def test_returns_version_string(self):
        import claude_mpm
        from claude_mpm.cli.startup import _get_package_version

        # Use patch.object so the helper's `from claude_mpm import __version__`
        # picks up the patched attribute without any redundant manual mutation.
        with patch.object(claude_mpm, "__version__", "9.9.9"):
            assert _get_package_version() == "9.9.9"

    def test_returns_none_on_import_error(self):
        from claude_mpm.cli.startup import _get_package_version

        with patch.dict("sys.modules", {"claude_mpm": None}):
            # Simulate missing module: the helper should swallow the error
            # and return None so callers treat the version as a cache miss.
            result = _get_package_version()
            assert result is None


class TestIsBundledSkillsSyncFresh:
    """_is_bundled_skills_sync_fresh() requires fresh TTL AND matching version."""

    def test_returns_false_when_ttl_stale(self):
        from claude_mpm.cli.startup import _is_bundled_skills_sync_fresh

        # The refactored function loads state directly, so simulate a stale
        # TTL by providing a last-sync timestamp older than the TTL window.
        with patch(
            "claude_mpm.cli.startup._load_sync_state",
            return_value={"bundled_skills": 0},  # epoch → definitely stale
        ):
            assert _is_bundled_skills_sync_fresh() is False

    def test_returns_false_when_version_missing_from_state(self):
        from claude_mpm.cli.startup import _is_bundled_skills_sync_fresh

        # TTL is fresh but no version recorded (legacy state)
        with (
            patch("claude_mpm.cli.startup._is_sync_fresh", return_value=True),
            patch(
                "claude_mpm.cli.startup._load_sync_state",
                return_value={"bundled_skills": time.time()},  # no version key
            ),
        ):
            assert _is_bundled_skills_sync_fresh() is False

    def test_returns_false_when_version_changed(self):
        from claude_mpm.cli.startup import (
            _BUNDLED_SKILLS_VERSION_KEY,
            _is_bundled_skills_sync_fresh,
        )

        with (
            patch("claude_mpm.cli.startup._is_sync_fresh", return_value=True),
            patch(
                "claude_mpm.cli.startup._load_sync_state",
                return_value={
                    "bundled_skills": time.time(),
                    _BUNDLED_SKILLS_VERSION_KEY: "1.0.0",
                },
            ),
            patch("claude_mpm.cli.startup._get_package_version", return_value="2.0.0"),
        ):
            assert _is_bundled_skills_sync_fresh() is False

    def test_returns_false_when_current_version_unknown(self):
        """When _get_package_version() returns None, treat cache as not fresh."""
        from claude_mpm.cli.startup import (
            _BUNDLED_SKILLS_VERSION_KEY,
            _is_bundled_skills_sync_fresh,
        )

        with (
            patch("claude_mpm.cli.startup._is_sync_fresh", return_value=True),
            patch(
                "claude_mpm.cli.startup._load_sync_state",
                return_value={
                    "bundled_skills": time.time(),
                    _BUNDLED_SKILLS_VERSION_KEY: "3.1.4",
                },
            ),
            patch("claude_mpm.cli.startup._get_package_version", return_value=None),
        ):
            assert _is_bundled_skills_sync_fresh() is False

    def test_returns_true_when_ttl_fresh_and_version_matches(self):
        from claude_mpm.cli.startup import (
            _BUNDLED_SKILLS_VERSION_KEY,
            _is_bundled_skills_sync_fresh,
        )

        with (
            patch("claude_mpm.cli.startup._is_sync_fresh", return_value=True),
            patch(
                "claude_mpm.cli.startup._load_sync_state",
                return_value={
                    "bundled_skills": time.time(),
                    _BUNDLED_SKILLS_VERSION_KEY: "3.1.4",
                },
            ),
            patch("claude_mpm.cli.startup._get_package_version", return_value="3.1.4"),
        ):
            assert _is_bundled_skills_sync_fresh() is True


class TestMarkBundledSkillsSyncDone:
    """_mark_bundled_skills_sync_done() persists both timestamp and version."""

    def test_writes_timestamp_and_version(self, tmp_path, monkeypatch):
        from claude_mpm.cli.startup import (
            _BUNDLED_SKILLS_VERSION_KEY,
            _mark_bundled_skills_sync_done,
        )

        monkeypatch.setenv("HOME", str(tmp_path))
        with patch("claude_mpm.cli.startup._get_package_version", return_value="5.5.5"):
            _mark_bundled_skills_sync_done()

        # Read back the saved state
        import json

        state_file = tmp_path / ".claude-mpm" / "cache" / "sync-state.json"
        assert state_file.exists(), "sync-state.json was not created"
        state = json.loads(state_file.read_text())

        assert "bundled_skills" in state, "timestamp key missing"
        assert state[_BUNDLED_SKILLS_VERSION_KEY] == "5.5.5", "version not persisted"
        assert state["bundled_skills"] <= time.time(), "timestamp is in the future"


# ---------------------------------------------------------------------------
# End-to-end scenarios for deploy_bundled_skills()
# ---------------------------------------------------------------------------


class TestDeployBundledSkillsVersionAwareTTL:
    """Scenario tests for the version-aware TTL gate in deploy_bundled_skills()."""

    # (a) Same version + fresh TTL → SKIPPED
    def test_same_version_fresh_ttl_skips_deployment(self, mock_skills_service):
        """When TTL is fresh AND stored version == current version, deployment is skipped."""
        from claude_mpm.cli.startup import deploy_bundled_skills

        with patch(
            "claude_mpm.cli.startup._is_bundled_skills_sync_fresh", return_value=True
        ):
            deploy_bundled_skills(force_deploy=False)

        mock_skills_service.deploy_bundled_skills.assert_not_called()

    # (b) Changed version + fresh TTL → RUNS
    def test_changed_version_fresh_ttl_runs_deployment(self, mock_skills_service):
        """When TTL is fresh but version changed, deployment runs."""
        from claude_mpm.cli.startup import deploy_bundled_skills

        with patch(
            "claude_mpm.cli.startup._is_bundled_skills_sync_fresh", return_value=False
        ):
            deploy_bundled_skills(force_deploy=False)

        mock_skills_service.deploy_bundled_skills.assert_called_once()

    # (c) No sync-state (fresh install) → RUNS
    def test_no_sync_state_runs_deployment(
        self, mock_skills_service, tmp_path, monkeypatch
    ):
        """On a fresh install with no sync-state file, deployment runs."""
        monkeypatch.setenv("HOME", str(tmp_path))
        # Nothing in ~/.claude-mpm/cache/ so _is_sync_fresh returns False.
        from claude_mpm.cli.startup import deploy_bundled_skills

        # Don't patch _is_bundled_skills_sync_fresh — let it call _is_sync_fresh
        # which reads the (non-existent) state file and returns False.
        with patch("claude_mpm.cli.startup._get_package_version", return_value="6.0.0"):
            deploy_bundled_skills(force_deploy=False)

        mock_skills_service.deploy_bundled_skills.assert_called_once()

    # (d) Legacy state (no version field) → RUNS once, then version recorded
    def test_legacy_state_missing_version_runs_once_then_records_version(
        self, mock_skills_service, tmp_path, monkeypatch
    ):
        """Legacy sync-state (no bundled_skills_version) causes one redeploy."""
        import json

        monkeypatch.setenv("HOME", str(tmp_path))

        # Write a legacy sync-state with a fresh timestamp but NO version key.
        state_dir = tmp_path / ".claude-mpm" / "cache"
        state_dir.mkdir(parents=True)
        legacy_state = {"bundled_skills": time.time() - 60}  # 1 minute ago (fresh TTL)
        (state_dir / "sync-state.json").write_text(json.dumps(legacy_state))

        from claude_mpm.cli.startup import (
            _BUNDLED_SKILLS_VERSION_KEY,
            deploy_bundled_skills,
        )

        with patch("claude_mpm.cli.startup._get_package_version", return_value="7.0.0"):
            deploy_bundled_skills(force_deploy=False)

        # Deployment must have run despite fresh TTL
        mock_skills_service.deploy_bundled_skills.assert_called_once()

        # After deployment, version must be recorded in sync-state
        updated_state = json.loads((state_dir / "sync-state.json").read_text())
        assert updated_state.get(_BUNDLED_SKILLS_VERSION_KEY) == "7.0.0", (
            "Version was not recorded after legacy-state deploy"
        )

    # (e) Unknown version (None) + fresh TTL → RUNS (must not suppress via self-match)
    def test_unknown_version_fresh_ttl_runs_deployment(
        self, mock_skills_service, tmp_path, monkeypatch
    ):
        """When version cannot be determined, deployment runs even if TTL is fresh.

        Regression guard: before this fix, _get_package_version() returned
        "unknown", which meant stored=="unknown" == current=="unknown" caused
        _is_bundled_skills_sync_fresh() to return True and permanently suppress
        deployment when the version was unavailable.
        """
        import json

        monkeypatch.setenv("HOME", str(tmp_path))

        # Write a sync-state with a fresh timestamp AND a stored None-equivalent
        # entry (simulate the old "unknown" sentinel now omitted on write).
        state_dir = tmp_path / ".claude-mpm" / "cache"
        state_dir.mkdir(parents=True)
        # State has fresh TTL but NO bundled_skills_version (as _mark_bundled_skills_sync_done
        # now omits the key when version is None).
        fresh_state = {"bundled_skills": time.time() - 60}  # 1 minute ago
        (state_dir / "sync-state.json").write_text(json.dumps(fresh_state))

        from claude_mpm.cli.startup import deploy_bundled_skills

        with patch("claude_mpm.cli.startup._get_package_version", return_value=None):
            deploy_bundled_skills(force_deploy=False)

        # Deployment must run — unknown version must not suppress it.
        mock_skills_service.deploy_bundled_skills.assert_called_once()

    # force_deploy=True must always run regardless of TTL/version
    def test_force_deploy_bypasses_version_ttl_gate(self, mock_skills_service):
        """force_deploy=True always deploys regardless of TTL or version state."""
        from claude_mpm.cli.startup import deploy_bundled_skills

        # Even with a "fresh" sync, force_deploy overrides.
        with patch(
            "claude_mpm.cli.startup._is_bundled_skills_sync_fresh", return_value=True
        ):
            deploy_bundled_skills(force_deploy=True)

        mock_skills_service.deploy_bundled_skills.assert_called_once()
