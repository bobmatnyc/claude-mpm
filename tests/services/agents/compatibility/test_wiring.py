"""Wiring tests: ManifestCache and DeploymentVersionGate integration.

Tests cover three areas:
  1. Sync-time cache population (W-1 through W-5)
  2. Deploy-time gate in DeploymentReconciler (W-6 through W-16, W-20)
  3. WAL mode and SQLite concurrency (W-17 through W-19)
"""

import contextlib
import logging
import sqlite3
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from claude_mpm.services.agents.compatibility import CompatibilityResult
from claude_mpm.services.agents.compatibility.deploy_gate import DeploymentVersionGate
from claude_mpm.services.agents.compatibility.manifest_cache import ManifestCache
from claude_mpm.services.agents.compatibility.manifest_checker import (
    ManifestChecker,
    ManifestCheckResult,
)
from tests.services.agents.compatibility.conftest import make_manifest_yaml

# ===========================================================================
# 1. Sync-Time Cache Population (W-1 through W-5)
# ===========================================================================


class TestSyncTimeCachePopulation:
    """Verify that _check_manifest_compatibility() stores results in ManifestCache."""

    def _make_sync_service(self, tmp_path, manifest_cache=None):
        """Create a GitSourceSyncService with mocked externals.

        Returns (service, manifest_cache) tuple.
        """
        cache = manifest_cache
        with contextlib.ExitStack() as stack:
            stack.enter_context(
                patch(
                    "claude_mpm.services.agents.sources.git_source_sync_service.AgentSyncState"
                )
            )
            stack.enter_context(
                patch(
                    "claude_mpm.services.agents.sources.git_source_sync_service.ETagCache"
                )
            )
            stack.enter_context(
                patch("claude_mpm.services.agents.cache_git_manager.CacheGitManager")
            )
            if cache is not None:
                stack.enter_context(
                    patch(
                        "claude_mpm.services.agents.sources.git_source_sync_service.ManifestCache",
                        return_value=cache,
                    )
                )
            else:
                stack.enter_context(
                    patch(
                        "claude_mpm.services.agents.sources.git_source_sync_service.ManifestCache",
                        side_effect=lambda: ManifestCache(
                            db_path=tmp_path / "manifest.db"
                        ),
                    )
                )
            from claude_mpm.services.agents.sources.git_source_sync_service import (
                GitSourceSyncService,
            )

            svc = GitSourceSyncService(
                source_url="https://raw.githubusercontent.com/test/repo/main/agents",
                cache_dir=tmp_path / "cache",
                source_id="test-source",
            )

        if cache is None:
            cache = svc._manifest_cache
        return svc, cache

    # W-1: Compatible manifest stored after sync check
    def test_w1_compatible_manifest_stored(self, tmp_path):
        """After a compatible manifest check, cache entry has correct fields."""
        svc, cache = self._make_sync_service(tmp_path)

        manifest_content = make_manifest_yaml(
            repo_format_version=1, min_cli_version="5.0.0"
        )

        with patch(
            "claude_mpm.services.agents.sources.git_source_sync_service.ManifestFetcher"
        ) as mock_fetcher_cls, patch(
            "claude_mpm.services.agents.sources.git_source_sync_service.ManifestChecker"
        ) as mock_checker_cls, patch("claude_mpm.__version__", "5.10.0"):
            mock_fetcher_cls.return_value.fetch.return_value = manifest_content
            mock_checker_cls.return_value.check.return_value = ManifestCheckResult(
                status=CompatibilityResult.COMPATIBLE,
                repo_format_version=1,
                min_cli_version="5.0.0",
                cli_version="5.10.0",
                message="Compatible",
            )

            result = svc._check_manifest_compatibility()

        assert result.status == CompatibilityResult.COMPATIBLE
        entry = cache.get("test-source")
        assert entry is not None
        assert entry["repo_format_version"] == 1
        assert entry["min_cli_version"] == "5.0.0"
        assert entry["raw_content"] == manifest_content

    # W-2: Incompatible manifest also stored
    def test_w2_incompatible_manifest_also_stored(self, tmp_path):
        """Cache entry exists even for INCOMPATIBLE_HARD (before the raise)."""
        svc, cache = self._make_sync_service(tmp_path)

        manifest_content = make_manifest_yaml(
            repo_format_version=99, min_cli_version="5.0.0"
        )

        with patch(
            "claude_mpm.services.agents.sources.git_source_sync_service.ManifestFetcher"
        ) as mock_fetcher_cls, patch(
            "claude_mpm.services.agents.sources.git_source_sync_service.ManifestChecker"
        ) as mock_checker_cls, patch("claude_mpm.__version__", "5.10.0"):
            mock_fetcher_cls.return_value.fetch.return_value = manifest_content
            mock_checker_cls.return_value.check.return_value = ManifestCheckResult(
                status=CompatibilityResult.INCOMPATIBLE_HARD,
                repo_format_version=99,
                min_cli_version="5.0.0",
                cli_version="5.10.0",
                message="Unsupported format",
            )

            from claude_mpm.services.agents.sources.git_source_sync_service import (
                IncompatibleRepoError,
            )

            with pytest.raises(IncompatibleRepoError):
                svc._check_manifest_compatibility()

        # Cache entry should still be written BEFORE the raise
        entry = cache.get("test-source")
        assert entry is not None
        assert entry["repo_format_version"] == 99

    # W-3: Cache write failure doesn't break sync
    def test_w3_cache_write_failure_doesnt_break_sync(self, tmp_path):
        """Mock ManifestCache.store to raise; sync check still returns result."""
        broken_cache = MagicMock()
        broken_cache.store.side_effect = RuntimeError("disk full")

        svc, _ = self._make_sync_service(tmp_path, manifest_cache=broken_cache)

        manifest_content = make_manifest_yaml(
            repo_format_version=1, min_cli_version="5.0.0"
        )

        with patch(
            "claude_mpm.services.agents.sources.git_source_sync_service.ManifestFetcher"
        ) as mock_fetcher_cls, patch(
            "claude_mpm.services.agents.sources.git_source_sync_service.ManifestChecker"
        ) as mock_checker_cls, patch("claude_mpm.__version__", "5.10.0"):
            mock_fetcher_cls.return_value.fetch.return_value = manifest_content
            mock_checker_cls.return_value.check.return_value = ManifestCheckResult(
                status=CompatibilityResult.COMPATIBLE,
                repo_format_version=1,
                min_cli_version="5.0.0",
                cli_version="5.10.0",
                message="Compatible",
            )

            result = svc._check_manifest_compatibility()

        assert result.status == CompatibilityResult.COMPATIBLE

    # W-4: No-manifest scenario doesn't write to cache
    def test_w4_no_manifest_does_not_write_to_cache(self, tmp_path):
        """When manifest_content is None, cache remains empty."""
        svc, cache = self._make_sync_service(tmp_path)

        with patch(
            "claude_mpm.services.agents.sources.git_source_sync_service.ManifestFetcher"
        ) as mock_fetcher_cls, patch(
            "claude_mpm.services.agents.sources.git_source_sync_service.ManifestChecker"
        ) as mock_checker_cls, patch("claude_mpm.__version__", "5.10.0"):
            mock_fetcher_cls.return_value.fetch.return_value = None
            mock_checker_cls.return_value.check.return_value = ManifestCheckResult(
                status=CompatibilityResult.NO_MANIFEST,
                repo_format_version=None,
                min_cli_version=None,
                cli_version="5.10.0",
                message="No manifest",
            )

            result = svc._check_manifest_compatibility()

        assert result.status == CompatibilityResult.NO_MANIFEST
        assert cache.get("test-source") is None

    # W-5: Successive syncs update cache entry
    def test_w5_successive_syncs_update_cache_entry(self, tmp_path):
        """last_checked timestamp advances on re-sync."""
        svc, cache = self._make_sync_service(tmp_path)

        manifest_content = make_manifest_yaml(
            repo_format_version=1, min_cli_version="5.0.0"
        )

        def run_check():
            with patch(
                "claude_mpm.services.agents.sources.git_source_sync_service.ManifestFetcher"
            ) as mock_fetcher_cls, patch(
                "claude_mpm.services.agents.sources.git_source_sync_service.ManifestChecker"
            ) as mock_checker_cls, patch("claude_mpm.__version__", "5.10.0"):
                mock_fetcher_cls.return_value.fetch.return_value = manifest_content
                mock_checker_cls.return_value.check.return_value = ManifestCheckResult(
                    status=CompatibilityResult.COMPATIBLE,
                    repo_format_version=1,
                    min_cli_version="5.0.0",
                    cli_version="5.10.0",
                    message="Compatible",
                )
                svc._check_manifest_compatibility()

        run_check()
        first_ts = cache.get("test-source")["last_checked"]

        time.sleep(0.05)  # Small delay for timestamp difference
        run_check()
        second_ts = cache.get("test-source")["last_checked"]

        assert second_ts > first_ts


# ===========================================================================
# 2. Deploy-Time Gate (W-6 through W-16)
# ===========================================================================


class TestDeployTimeGate:
    """Verify DeploymentReconciler uses DeploymentVersionGate at deploy time."""

    def _make_reconciler(
        self, tmp_path, config=None, manifest_cache=None, deploy_gate=None
    ):
        """Create a DeploymentReconciler with controllable internals.

        Patches ManifestCache construction to use tmp_path-based DB,
        and allows overriding individual components.
        """
        with patch(
            "claude_mpm.services.agents.deployment.deployment_reconciler.ManifestCache",
            return_value=manifest_cache or ManifestCache(db_path=tmp_path / "mc.db"),
        ), patch(
            "claude_mpm.services.agents.deployment.deployment_reconciler.DeploymentVersionGate",
            return_value=deploy_gate or DeploymentVersionGate(),
        ):
            from claude_mpm.services.agents.deployment.deployment_reconciler import (
                DeploymentReconciler,
            )

            reconciler = DeploymentReconciler(config=config)

        return reconciler

    def _make_config(self, agents_enabled=None, auto_discover=True):
        """Create a mock UnifiedConfig."""
        config = MagicMock()
        config.agents.enabled = agents_enabled or []
        config.agents.auto_discover = auto_discover
        config.agents.required = []
        config.agents.include_universal = False
        return config

    # W-6: Compatible cache entry allows deployment
    def test_w6_compatible_cache_allows_deployment(self, tmp_path):
        """reconcile_agents deploys normally when cache shows COMPATIBLE."""
        mc = ManifestCache(db_path=tmp_path / "mc.db")
        mc.store(
            source_id="github-remote",
            repo_format_version=1,
            min_cli_version="5.0.0",
            raw_content=make_manifest_yaml(
                repo_format_version=1, min_cli_version="5.0.0"
            ),
        )

        config = self._make_config(auto_discover=True)
        reconciler = self._make_reconciler(tmp_path, config=config, manifest_cache=mc)

        with patch("claude_mpm.__version__", "5.10.0"):
            result = reconciler.reconcile_agents(project_path=tmp_path)

        assert result.errors == []

    # W-7: INCOMPATIBLE_HARD blocks all deployments
    def test_w7_hard_incompatible_blocks_deployment(self, tmp_path):
        """reconcile_agents returns error, no agents deployed."""
        mc = ManifestCache(db_path=tmp_path / "mc.db")
        # Store manifest with unsupported format version
        mc.store(
            source_id="github-remote",
            repo_format_version=99,
            min_cli_version="5.0.0",
            raw_content=make_manifest_yaml(
                repo_format_version=99, min_cli_version="5.0.0"
            ),
        )

        config = self._make_config(auto_discover=True)
        reconciler = self._make_reconciler(tmp_path, config=config, manifest_cache=mc)

        with patch("claude_mpm.__version__", "5.10.0"):
            result = reconciler.reconcile_agents(project_path=tmp_path)

        assert len(result.errors) > 0
        assert any("blocked" in e.lower() for e in result.errors)
        assert result.deployed == []

    # W-8: INCOMPATIBLE_WARN logs warning, deploys proceed
    def test_w8_warn_incompatible_logs_but_deploys(self, tmp_path, caplog):
        """Warning logged, agents deployed."""
        mc = ManifestCache(db_path=tmp_path / "mc.db")
        mc.store(
            source_id="github-remote",
            repo_format_version=1,
            min_cli_version="6.0.0",
            raw_content=make_manifest_yaml(
                repo_format_version=1, min_cli_version="6.0.0"
            ),
        )

        config = self._make_config(auto_discover=True)
        reconciler = self._make_reconciler(tmp_path, config=config, manifest_cache=mc)

        with patch("claude_mpm.__version__", "5.10.0"), caplog.at_level(
            logging.WARNING, logger="claude_mpm"
        ):
            result = reconciler.reconcile_agents(project_path=tmp_path)

        # Should NOT be blocked (warn only)
        assert result.errors == []
        # Warning should be logged by DeploymentVersionGate
        assert any(
            "compatibility warning" in r.message.lower() or "github-remote" in r.message
            for r in caplog.records
        )

    # W-9: Empty cache deploys normally (fail-open)
    def test_w9_empty_cache_deploys_normally(self, tmp_path):
        """No entries in ManifestCache -> deployment proceeds."""
        mc = ManifestCache(db_path=tmp_path / "mc.db")
        config = self._make_config(auto_discover=True)
        reconciler = self._make_reconciler(tmp_path, config=config, manifest_cache=mc)

        with patch("claude_mpm.__version__", "5.10.0"):
            result = reconciler.reconcile_agents(project_path=tmp_path)

        assert result.errors == []

    # W-10: Multiple sources, one blocked -> all agents blocked
    def test_w10_multiple_sources_one_blocked(self, tmp_path):
        """All agents blocked if any source is INCOMPATIBLE_HARD (Option A)."""
        mc = ManifestCache(db_path=tmp_path / "mc.db")
        mc.store(
            source_id="source-ok",
            repo_format_version=1,
            min_cli_version="5.0.0",
            raw_content=make_manifest_yaml(
                repo_format_version=1, min_cli_version="5.0.0"
            ),
        )
        mc.store(
            source_id="source-bad",
            repo_format_version=99,
            min_cli_version="5.0.0",
            raw_content=make_manifest_yaml(
                repo_format_version=99, min_cli_version="5.0.0"
            ),
        )

        config = self._make_config(auto_discover=True)
        reconciler = self._make_reconciler(tmp_path, config=config, manifest_cache=mc)

        with patch("claude_mpm.__version__", "5.10.0"):
            result = reconciler.reconcile_agents(project_path=tmp_path)

        assert len(result.errors) > 0
        assert result.deployed == []

    # W-11: CLI downgrade triggers re-validation
    def test_w11_cli_downgrade_triggers_revalidation(self, tmp_path):
        """Synced with v6.0.0, deploy with v5.10.0: gate detects WARN."""
        mc = ManifestCache(db_path=tmp_path / "mc.db")
        mc.store(
            source_id="github-remote",
            repo_format_version=1,
            min_cli_version="6.0.0",
            raw_content=make_manifest_yaml(
                repo_format_version=1, min_cli_version="6.0.0"
            ),
        )

        config = self._make_config(auto_discover=True)
        reconciler = self._make_reconciler(tmp_path, config=config, manifest_cache=mc)

        with patch("claude_mpm.__version__", "5.10.0"):
            result = reconciler.reconcile_agents(project_path=tmp_path)

        # INCOMPATIBLE_WARN should not block
        assert result.errors == []

    # W-12: CLI downgrade hard-stop
    def test_w12_cli_downgrade_hard_stop(self, tmp_path):
        """rfv bumped to 2 in cache, deploy with older CLI -> hard stop."""
        mc = ManifestCache(db_path=tmp_path / "mc.db")
        mc.store(
            source_id="github-remote",
            repo_format_version=2,
            min_cli_version="5.0.0",
            raw_content=make_manifest_yaml(
                repo_format_version=2, min_cli_version="5.0.0"
            ),
        )

        config = self._make_config(auto_discover=True)
        reconciler = self._make_reconciler(tmp_path, config=config, manifest_cache=mc)

        with patch("claude_mpm.__version__", "5.10.0"):
            result = reconciler.reconcile_agents(project_path=tmp_path)

        assert len(result.errors) > 0
        assert result.deployed == []

    # W-13: DeploymentVersionGate.check_before_deploy reads from cache
    def test_w13_gate_reads_raw_content_from_cache(self, tmp_path):
        """Verify raw_content stored in cache is used for re-check."""
        mc = ManifestCache(db_path=tmp_path / "mc.db")
        manifest_content = make_manifest_yaml(
            repo_format_version=1, min_cli_version="5.0.0"
        )
        mc.store(
            source_id="my-source",
            repo_format_version=1,
            min_cli_version="5.0.0",
            raw_content=manifest_content,
        )

        gate = DeploymentVersionGate(manifest_cache=mc)
        result = gate.check_before_deploy(
            source_id="my-source",
            cli_version="5.10.0",
        )

        assert result.status == CompatibilityResult.COMPATIBLE

    # W-14: [DA-1] Auto-discover mode still runs deploy gate
    def test_w14_auto_discover_still_runs_gate(self, tmp_path):
        """Gate blocks even with enabled=[], auto_discover=True."""
        mc = ManifestCache(db_path=tmp_path / "mc.db")
        mc.store(
            source_id="github-remote",
            repo_format_version=99,
            min_cli_version="5.0.0",
            raw_content=make_manifest_yaml(
                repo_format_version=99, min_cli_version="5.0.0"
            ),
        )

        # Default config: agents.enabled=[], agents.auto_discover=True
        config = self._make_config(agents_enabled=[], auto_discover=True)
        reconciler = self._make_reconciler(tmp_path, config=config, manifest_cache=mc)

        with patch("claude_mpm.__version__", "5.10.0"):
            result = reconciler.reconcile_agents(project_path=tmp_path)

        # Gate should have blocked deployment BEFORE auto-discover early return
        assert len(result.errors) > 0
        assert any("blocked" in e.lower() for e in result.errors)

    # W-15: [DA-2] ManifestCache init failure -> deploy proceeds (fail-open)
    def test_w15_cache_init_failure_deploys_normally(self, tmp_path):
        """ManifestCache() raises -> reconcile_agents deploys normally."""
        config = self._make_config(auto_discover=True)

        with patch(
            "claude_mpm.services.agents.deployment.deployment_reconciler.ManifestCache",
            side_effect=RuntimeError("permission denied"),
        ), patch(
            "claude_mpm.services.agents.deployment.deployment_reconciler.DeploymentVersionGate",
        ):
            from claude_mpm.services.agents.deployment.deployment_reconciler import (
                DeploymentReconciler,
            )

            reconciler = DeploymentReconciler(config=config)

        # _manifest_cache and _deploy_gate should be None
        assert reconciler._manifest_cache is None
        assert reconciler._deploy_gate is None

        result = reconciler.reconcile_agents(project_path=tmp_path)
        assert result.errors == []

    # W-16: [DA-7] __version__ is None or empty -> fail-open
    def test_w16_empty_version_deploys_normally(self, tmp_path):
        """Mock __version__ to None; deploy proceeds."""
        mc = ManifestCache(db_path=tmp_path / "mc.db")
        mc.store(
            source_id="github-remote",
            repo_format_version=99,
            min_cli_version="5.0.0",
            raw_content=make_manifest_yaml(
                repo_format_version=99, min_cli_version="5.0.0"
            ),
        )

        config = self._make_config(auto_discover=True)
        reconciler = self._make_reconciler(tmp_path, config=config, manifest_cache=mc)

        with patch("claude_mpm.__version__", None):
            result = reconciler.reconcile_agents(project_path=tmp_path)

        # Should fail-open: no errors despite incompatible cache
        assert result.errors == []

    # W-20: CLAUDE_MPM_SKIP_COMPAT_CHECK env var bypasses deploy gate
    def test_w20_skip_compat_check_env_var_bypasses_gate(self, tmp_path):
        """Setting CLAUDE_MPM_SKIP_COMPAT_CHECK=1 skips deploy-time check."""
        mc = ManifestCache(db_path=tmp_path / "mc.db")
        # Store manifest that would normally cause hard stop
        mc.store(
            source_id="github-remote",
            repo_format_version=99,
            min_cli_version="5.0.0",
            raw_content=make_manifest_yaml(
                repo_format_version=99, min_cli_version="5.0.0"
            ),
        )

        config = self._make_config(auto_discover=True)
        reconciler = self._make_reconciler(tmp_path, config=config, manifest_cache=mc)

        with patch("claude_mpm.__version__", "5.10.0"), patch.dict(
            "os.environ", {"CLAUDE_MPM_SKIP_COMPAT_CHECK": "1"}
        ):
            result = reconciler.reconcile_agents(project_path=tmp_path)

        # Should pass despite incompatible manifest because env var skips check
        assert result.errors == []


# ===========================================================================
# 3. WAL Mode and Concurrency (W-17 through W-19)
# ===========================================================================


class TestWALModeAndConcurrency:
    """Verify SQLite WAL mode and concurrent access patterns."""

    # W-17: WAL mode is set on init
    def test_w17_wal_mode_set_on_init(self, tmp_path):
        """PRAGMA journal_mode returns 'wal' after ManifestCache init."""
        cache = ManifestCache(db_path=tmp_path / "test.db")
        db_path = tmp_path / "test.db"

        with sqlite3.connect(str(db_path)) as conn:
            result = conn.execute("PRAGMA journal_mode").fetchone()

        assert result[0].lower() == "wal"

    # W-18: Concurrent reads during write
    def test_w18_concurrent_reads_during_write(self, tmp_path):
        """Two threads read while one writes; no errors."""
        db_path = tmp_path / "concurrent.db"
        cache = ManifestCache(db_path=db_path)

        # Pre-populate with data
        cache.store(
            source_id="pre-existing",
            repo_format_version=1,
            min_cli_version="5.0.0",
        )

        errors = []
        read_results = []

        def writer():
            """Write many entries to simulate concurrent writes."""
            try:
                for i in range(20):
                    cache.store(
                        source_id=f"writer-{i}",
                        repo_format_version=1,
                        min_cli_version="5.0.0",
                    )
                    time.sleep(0.001)
            except Exception as e:
                errors.append(f"writer: {e}")

        def reader(reader_id):
            """Read repeatedly during writes."""
            try:
                for _ in range(20):
                    entries = cache.get_all()
                    read_results.append((reader_id, len(entries)))
                    time.sleep(0.001)
            except Exception as e:
                errors.append(f"reader-{reader_id}: {e}")

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader, args=(1,)),
            threading.Thread(target=reader, args=(2,)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert errors == [], f"Concurrent access errors: {errors}"
        assert len(read_results) > 0

    # W-19: Busy timeout handles lock contention
    def test_w19_busy_timeout_handles_contention(self, tmp_path):
        """No 'database is locked' error under brief contention."""
        db_path = tmp_path / "contention.db"
        cache = ManifestCache(db_path=db_path)

        errors = []

        def exclusive_writer():
            """Hold an exclusive lock briefly."""
            try:
                conn = sqlite3.connect(str(db_path))
                conn.execute("PRAGMA busy_timeout=5000")
                conn.execute("BEGIN EXCLUSIVE")
                time.sleep(0.1)  # Hold lock for 100ms
                conn.execute("COMMIT")
                conn.close()
            except Exception as e:
                errors.append(f"exclusive_writer: {e}")

        def cache_writer():
            """Try to write via ManifestCache while lock is held."""
            try:
                time.sleep(0.02)  # Start slightly after exclusive writer
                cache.store(
                    source_id="contention-test",
                    repo_format_version=1,
                    min_cli_version="5.0.0",
                )
            except Exception as e:
                errors.append(f"cache_writer: {e}")

        threads = [
            threading.Thread(target=exclusive_writer),
            threading.Thread(target=cache_writer),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert errors == [], f"Lock contention errors: {errors}"
        entry = cache.get("contention-test")
        assert entry is not None
