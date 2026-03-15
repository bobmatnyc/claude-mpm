"""Phase 2 tests for the compatibility module extensions.

Tests cover:
  1. Compatibility Ranges in ManifestChecker
  2. DeploymentVersionGate
  3. ManifestCache (SQLite)
  4. Per-Agent min_cli_version Overrides
  5. Non-GitHub Repo Support in ManifestFetcher
  6. Deprecation Warning Lifecycle
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from claude_mpm.services.agents.compatibility import (
    DeploymentVersionGate as ImportedGate,
    ManifestCache as ImportedCache,
)
from claude_mpm.services.agents.compatibility.deploy_gate import DeploymentVersionGate
from claude_mpm.services.agents.compatibility.manifest_cache import ManifestCache
from claude_mpm.services.agents.compatibility.manifest_checker import (
    CompatibilityResult,
    ManifestChecker,
    ManifestCheckResult,
)
from claude_mpm.services.agents.compatibility.manifest_fetcher import ManifestFetcher
from tests.services.agents.compatibility.conftest import (
    make_manifest_response,
    make_manifest_yaml,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _checker() -> ManifestChecker:
    return ManifestChecker()


def _make_ranges_manifest(
    ranges,
    repo_format_version=1,
    min_cli_version="5.0.0",
    migration_notes=None,
    extra=None,
):
    """Build a manifest YAML that includes compatibility_ranges."""
    data = {
        "repo_format_version": repo_format_version,
        "min_cli_version": min_cli_version,
        "compatibility_ranges": ranges,
    }
    if migration_notes:
        data["migration_notes"] = migration_notes
    if extra:
        data.update(extra)
    return yaml.dump(data)


def _make_deprecation_manifest(warnings_list, min_cli_version="5.0.0"):
    """Build a manifest YAML with deprecation_warnings."""
    data = {
        "repo_format_version": 1,
        "min_cli_version": min_cli_version,
        "deprecation_warnings": warnings_list,
    }
    return yaml.dump(data)


def _make_agents_manifest(agents_dict, min_cli_version="5.0.0"):
    """Build a manifest YAML with per-agent overrides."""
    data = {
        "repo_format_version": 1,
        "min_cli_version": min_cli_version,
        "agents": agents_dict,
    }
    return yaml.dump(data)


# ===========================================================================
# 1. Compatibility Ranges
# ===========================================================================


class TestCompatibilityRanges:
    """Tests for the compatibility_ranges feature in ManifestChecker."""

    # ── 1.1 Full match → COMPATIBLE ────────────────────────────────────────

    def test_full_range_match_returns_compatible(self):
        content = _make_ranges_manifest([{"cli": ">=5.10.0 <6.0.0", "status": "full"}])
        result = _checker().check(content, "5.11.0")
        assert result.status == CompatibilityResult.COMPATIBLE

    def test_full_range_exact_lower_bound_returns_compatible(self):
        content = _make_ranges_manifest([{"cli": ">=5.10.0 <6.0.0", "status": "full"}])
        result = _checker().check(content, "5.10.0")
        assert result.status == CompatibilityResult.COMPATIBLE

    def test_multiple_full_ranges_first_match_wins(self):
        """Two non-overlapping full ranges; CLI matches the second."""
        content = _make_ranges_manifest(
            [
                {"cli": ">=5.10.0 <6.0.0", "status": "full"},
                {"cli": ">=6.0.0 <7.0.0", "status": "full"},
            ]
        )
        result = _checker().check(content, "6.5.0")
        assert result.status == CompatibilityResult.COMPATIBLE

    # ── 1.2 Degraded match → INCOMPATIBLE_WARN ─────────────────────────────

    def test_degraded_range_match_returns_incompatible_warn(self):
        content = _make_ranges_manifest(
            [
                {
                    "cli": ">=5.8.0 <5.10.0",
                    "status": "degraded",
                    "notes": "Dependencies field not supported",
                }
            ]
        )
        result = _checker().check(content, "5.9.0")
        assert result.status == CompatibilityResult.INCOMPATIBLE_WARN

    def test_degraded_range_includes_notes_in_message(self):
        content = _make_ranges_manifest(
            [
                {
                    "cli": ">=5.8.0 <5.10.0",
                    "status": "degraded",
                    "notes": "Dependencies field not supported",
                }
            ]
        )
        result = _checker().check(content, "5.9.0")
        assert "Dependencies field not supported" in result.message

    def test_degraded_range_sets_migration_notes(self):
        content = _make_ranges_manifest(
            [{"cli": ">=5.8.0 <5.10.0", "status": "degraded", "notes": "Use v2 format"}]
        )
        result = _checker().check(content, "5.9.0")
        assert result.migration_notes == "Use v2 format"

    # ── 1.3 No match → fall through to min_cli_version ─────────────────────

    def test_no_range_match_falls_through_to_min_cli_version(self):
        """CLI is outside all ranges, falls through to min_cli_version warn."""
        content = _make_ranges_manifest(
            [{"cli": ">=5.10.0 <6.0.0", "status": "full"}],
            min_cli_version="5.8.0",
        )
        # CLI 5.7.0 is below min AND outside ranges → INCOMPATIBLE_WARN via min check
        result = _checker().check(content, "5.7.0")
        assert result.status == CompatibilityResult.INCOMPATIBLE_WARN

    def test_no_range_match_and_satisfies_min_cli_version_returns_compatible(self):
        """CLI is outside all defined ranges but still >= min_cli_version."""
        content = _make_ranges_manifest(
            [{"cli": ">=5.10.0 <6.0.0", "status": "full"}],
            min_cli_version="5.0.0",
        )
        # CLI 7.0.0 is above all ranges but >= min → COMPATIBLE
        result = _checker().check(content, "7.0.0")
        assert result.status == CompatibilityResult.COMPATIBLE

    # ── 1.4 Invalid specifier skipped gracefully ────────────────────────────

    def test_invalid_specifier_is_skipped_gracefully(self):
        """Invalid specifier string logged and skipped; next range used."""
        content = _make_ranges_manifest(
            [
                {"cli": "not-a-specifier!!!", "status": "full"},
                {"cli": ">=5.10.0 <6.0.0", "status": "full"},
            ]
        )
        result = _checker().check(content, "5.11.0")
        assert result.status == CompatibilityResult.COMPATIBLE

    def test_all_invalid_specifiers_fall_through(self):
        """All invalid specifiers → fall through to min_cli_version logic."""
        content = _make_ranges_manifest(
            [{"cli": "!!invalid!!", "status": "full"}],
            min_cli_version="5.0.0",
        )
        result = _checker().check(content, "5.10.0")
        assert result.status == CompatibilityResult.COMPATIBLE

    # ── 1.5 Empty ranges list falls through ────────────────────────────────

    def test_empty_ranges_list_falls_through(self):
        content = _make_ranges_manifest([], min_cli_version="5.0.0")
        result = _checker().check(content, "5.10.0")
        assert result.status == CompatibilityResult.COMPATIBLE

    # ── 1.6 Ranges take precedence over min_cli_version ────────────────────

    def test_ranges_take_precedence_over_min_cli_version(self):
        """CLI is below min_cli_version but matches a 'full' range → COMPATIBLE."""
        content = _make_ranges_manifest(
            [{"cli": ">=5.8.0 <5.10.0", "status": "full"}],
            min_cli_version="5.10.0",  # Would normally block
        )
        result = _checker().check(content, "5.9.0")
        # Ranges matched first → COMPATIBLE despite min_cli_version=5.10.0
        assert result.status == CompatibilityResult.COMPATIBLE

    # ── 1.7 Hard stop still takes precedence over ranges ───────────────────

    def test_hard_stop_format_version_still_blocks_before_ranges(self):
        """repo_format_version hard stop evaluated before compatibility_ranges."""
        content = _make_ranges_manifest(
            [{"cli": ">=5.0.0", "status": "full"}],
            repo_format_version=99,  # Unsupported → hard stop
        )
        result = _checker().check(content, "5.10.0")
        assert result.status == CompatibilityResult.INCOMPATIBLE_HARD

    # ── 1.8 Non-list ranges value falls through ─────────────────────────────

    def test_non_list_ranges_value_falls_through(self):
        content = yaml.dump(
            {
                "repo_format_version": 1,
                "min_cli_version": "5.0.0",
                "compatibility_ranges": "not-a-list",
            }
        )
        result = _checker().check(content, "5.10.0")
        assert result.status == CompatibilityResult.COMPATIBLE


# ===========================================================================
# 2. DeploymentVersionGate
# ===========================================================================


class TestDeploymentVersionGate:
    """Tests for DeploymentVersionGate."""

    def test_compatible_deploy_proceeds(self):
        content = make_manifest_yaml(repo_format_version=1, min_cli_version="5.8.0")
        gate = DeploymentVersionGate()
        result = gate.check_before_deploy(
            source_id="test-repo",
            cli_version="5.10.0",
            cached_manifest_content=content,
        )
        assert result.status == CompatibilityResult.COMPATIBLE

    def test_incompatible_warn_is_returned(self):
        content = make_manifest_yaml(repo_format_version=1, min_cli_version="5.12.0")
        gate = DeploymentVersionGate()
        result = gate.check_before_deploy(
            source_id="test-repo",
            cli_version="5.10.0",
            cached_manifest_content=content,
        )
        assert result.status == CompatibilityResult.INCOMPATIBLE_WARN

    def test_incompatible_warn_is_logged(self, caplog):
        import logging

        content = make_manifest_yaml(repo_format_version=1, min_cli_version="5.12.0")
        gate = DeploymentVersionGate()
        with caplog.at_level(logging.WARNING, logger="claude_mpm"):
            gate.check_before_deploy(
                source_id="my-source",
                cli_version="5.10.0",
                cached_manifest_content=content,
            )
        assert any("my-source" in r.message for r in caplog.records)

    def test_no_cached_manifest_is_fail_open(self):
        """No manifest content → NO_MANIFEST (fail-open), deploy proceeds."""
        gate = DeploymentVersionGate()
        result = gate.check_before_deploy(
            source_id="test-repo",
            cli_version="5.10.0",
            cached_manifest_content=None,
        )
        assert result.status == CompatibilityResult.NO_MANIFEST

    def test_reads_raw_content_from_manifest_cache(self, tmp_path):
        """If no direct content, fall back to ManifestCache raw_content."""
        cache = ManifestCache(db_path=tmp_path / "test.db")
        content = make_manifest_yaml(repo_format_version=1, min_cli_version="5.8.0")
        cache.store(
            source_id="cached-repo",
            repo_format_version=1,
            min_cli_version="5.8.0",
            raw_content=content,
        )
        gate = DeploymentVersionGate(manifest_cache=cache)
        result = gate.check_before_deploy(
            source_id="cached-repo",
            cli_version="5.10.0",
        )
        assert result.status == CompatibilityResult.COMPATIBLE

    def test_cache_miss_is_fail_open(self, tmp_path):
        """Cache exists but entry absent → fail-open NO_MANIFEST."""
        cache = ManifestCache(db_path=tmp_path / "test.db")
        gate = DeploymentVersionGate(manifest_cache=cache)
        result = gate.check_before_deploy(
            source_id="nonexistent-repo",
            cli_version="5.10.0",
        )
        assert result.status == CompatibilityResult.NO_MANIFEST

    def test_explicit_content_takes_priority_over_cache(self, tmp_path):
        """Explicit cached_manifest_content overrides what's in ManifestCache."""
        cache = ManifestCache(db_path=tmp_path / "test.db")
        stale_content = make_manifest_yaml(
            repo_format_version=1, min_cli_version="5.12.0"
        )
        cache.store(
            source_id="repo",
            repo_format_version=1,
            min_cli_version="5.12.0",
            raw_content=stale_content,
        )
        fresh_content = make_manifest_yaml(
            repo_format_version=1, min_cli_version="5.8.0"
        )
        gate = DeploymentVersionGate(manifest_cache=cache)
        result = gate.check_before_deploy(
            source_id="repo",
            cli_version="5.10.0",
            cached_manifest_content=fresh_content,
        )
        assert result.status == CompatibilityResult.COMPATIBLE

    # ── __init__.py export check ──────────────────────────────────────────

    def test_deployment_gate_exported_from_package(self):
        assert ImportedGate is DeploymentVersionGate


# ===========================================================================
# 3. ManifestCache (SQLite)
# ===========================================================================


class TestManifestCache:
    """Tests for ManifestCache SQLite-backed storage."""

    def test_store_and_retrieve(self, tmp_path):
        cache = ManifestCache(db_path=tmp_path / "test.db")
        cache.store(
            source_id="repo-1",
            repo_format_version=1,
            min_cli_version="5.10.0",
        )
        entry = cache.get("repo-1")
        assert entry is not None
        assert entry["source_id"] == "repo-1"
        assert entry["repo_format_version"] == 1
        assert entry["min_cli_version"] == "5.10.0"

    def test_update_existing_entry(self, tmp_path):
        cache = ManifestCache(db_path=tmp_path / "test.db")
        cache.store(source_id="repo-1", repo_format_version=1, min_cli_version="5.0.0")
        cache.store(source_id="repo-1", repo_format_version=1, min_cli_version="5.10.0")
        entry = cache.get("repo-1")
        assert entry["min_cli_version"] == "5.10.0"

    def test_get_nonexistent_returns_none(self, tmp_path):
        cache = ManifestCache(db_path=tmp_path / "test.db")
        assert cache.get("nonexistent") is None

    def test_delete_existing_entry_returns_true(self, tmp_path):
        cache = ManifestCache(db_path=tmp_path / "test.db")
        cache.store(source_id="repo-1", repo_format_version=1, min_cli_version="5.0.0")
        result = cache.delete("repo-1")
        assert result is True
        assert cache.get("repo-1") is None

    def test_delete_nonexistent_returns_false(self, tmp_path):
        cache = ManifestCache(db_path=tmp_path / "test.db")
        assert cache.delete("nonexistent") is False

    def test_clear_all_entries(self, tmp_path):
        cache = ManifestCache(db_path=tmp_path / "test.db")
        cache.store(source_id="r1", repo_format_version=1, min_cli_version="5.0.0")
        cache.store(source_id="r2", repo_format_version=1, min_cli_version="5.0.0")
        count = cache.clear()
        assert count == 2
        assert cache.get("r1") is None
        assert cache.get("r2") is None

    def test_clear_empty_returns_zero(self, tmp_path):
        cache = ManifestCache(db_path=tmp_path / "test.db")
        assert cache.clear() == 0

    def test_compatibility_ranges_serialized_and_deserialized(self, tmp_path):
        ranges = [
            {"cli": ">=5.10.0 <6.0.0", "status": "full"},
            {"cli": ">=5.8.0 <5.10.0", "status": "degraded", "notes": "Legacy"},
        ]
        cache = ManifestCache(db_path=tmp_path / "test.db")
        cache.store(
            source_id="r1",
            repo_format_version=1,
            min_cli_version="5.0.0",
            compatibility_ranges=ranges,
        )
        entry = cache.get("r1")
        assert entry["compatibility_ranges"] == ranges

    def test_agent_overrides_serialized_and_deserialized(self, tmp_path):
        overrides = {
            "security-auditor": {
                "min_cli_version": "5.12.0",
                "notes": "Requires new API",
            }
        }
        cache = ManifestCache(db_path=tmp_path / "test.db")
        cache.store(
            source_id="r1",
            repo_format_version=1,
            min_cli_version="5.0.0",
            agent_overrides=overrides,
        )
        entry = cache.get("r1")
        assert entry["agent_overrides"] == overrides

    def test_multiple_sources_stored_independently(self, tmp_path):
        cache = ManifestCache(db_path=tmp_path / "test.db")
        cache.store(source_id="r1", repo_format_version=1, min_cli_version="5.0.0")
        cache.store(source_id="r2", repo_format_version=1, min_cli_version="5.10.0")
        assert cache.get("r1")["min_cli_version"] == "5.0.0"
        assert cache.get("r2")["min_cli_version"] == "5.10.0"

    def test_get_all_returns_all_entries(self, tmp_path):
        cache = ManifestCache(db_path=tmp_path / "test.db")
        cache.store(source_id="r1", repo_format_version=1, min_cli_version="5.0.0")
        cache.store(source_id="r2", repo_format_version=1, min_cli_version="5.10.0")
        entries = cache.get_all()
        assert len(entries) == 2
        source_ids = {e["source_id"] for e in entries}
        assert source_ids == {"r1", "r2"}

    def test_last_checked_is_set(self, tmp_path):
        cache = ManifestCache(db_path=tmp_path / "test.db")
        cache.store(source_id="r1", repo_format_version=1, min_cli_version="5.0.0")
        entry = cache.get("r1")
        assert entry["last_checked"] is not None
        assert len(entry["last_checked"]) > 0

    def test_raw_content_stored_and_retrieved(self, tmp_path):
        content = make_manifest_yaml(repo_format_version=1, min_cli_version="5.8.0")
        cache = ManifestCache(db_path=tmp_path / "test.db")
        cache.store(
            source_id="r1",
            repo_format_version=1,
            min_cli_version="5.8.0",
            raw_content=content,
        )
        entry = cache.get("r1")
        assert entry["raw_content"] == content

    def test_manifest_cache_exported_from_package(self):
        assert ImportedCache is ManifestCache


# ===========================================================================
# 4. Per-Agent min_cli_version Overrides
# ===========================================================================


class TestPerAgentOverrides:
    """Tests for ManifestChecker.check_agent() per-agent version overrides."""

    def test_agent_with_override_and_old_cli_returns_incompatible_warn(self):
        content = _make_agents_manifest(
            {
                "security-auditor": {
                    "min_cli_version": "5.12.0",
                    "notes": "Uses advanced scanning",
                }
            },
            min_cli_version="5.0.0",
        )
        result = _checker().check_agent(content, "5.10.0", "security-auditor")
        assert result.status == CompatibilityResult.INCOMPATIBLE_WARN
        assert "security-auditor" in result.message
        assert "5.12.0" in result.message

    def test_agent_with_override_includes_notes_in_message(self):
        content = _make_agents_manifest(
            {
                "security-auditor": {
                    "min_cli_version": "5.12.0",
                    "notes": "Uses advanced scanning features",
                }
            },
            min_cli_version="5.0.0",
        )
        result = _checker().check_agent(content, "5.10.0", "security-auditor")
        assert "Uses advanced scanning features" in result.message

    def test_agent_without_override_inherits_repo_level_compatible(self):
        content = _make_agents_manifest(
            {"security-auditor": {"min_cli_version": "5.12.0"}},
            min_cli_version="5.0.0",
        )
        result = _checker().check_agent(content, "5.10.0", "other-agent")
        assert result.status == CompatibilityResult.COMPATIBLE

    def test_agent_with_override_and_current_cli_returns_compatible(self):
        content = _make_agents_manifest(
            {"security-auditor": {"min_cli_version": "5.10.0"}},
            min_cli_version="5.0.0",
        )
        result = _checker().check_agent(content, "5.10.0", "security-auditor")
        assert result.status == CompatibilityResult.COMPATIBLE

    def test_agent_with_override_cli_newer_than_override_returns_compatible(self):
        content = _make_agents_manifest(
            {"security-auditor": {"min_cli_version": "5.10.0"}},
            min_cli_version="5.0.0",
        )
        result = _checker().check_agent(content, "5.15.0", "security-auditor")
        assert result.status == CompatibilityResult.COMPATIBLE

    def test_agents_section_not_a_dict_is_ignored(self):
        """Non-dict agents section falls back to repo-level result."""
        content = yaml.dump(
            {
                "repo_format_version": 1,
                "min_cli_version": "5.0.0",
                "agents": ["not", "a", "dict"],
            }
        )
        result = _checker().check_agent(content, "5.10.0", "security-auditor")
        assert result.status == CompatibilityResult.COMPATIBLE

    def test_hard_stop_at_repo_level_overrides_per_agent(self):
        """Repo-level INCOMPATIBLE_HARD is returned even for known agents."""
        content = _make_agents_manifest(
            {"security-auditor": {"min_cli_version": "5.0.0"}},
            min_cli_version="5.0.0",
        )
        # Inject unsupported format version
        data = yaml.safe_load(content)
        data["repo_format_version"] = 99
        content = yaml.dump(data)

        result = _checker().check_agent(content, "5.10.0", "security-auditor")
        assert result.status == CompatibilityResult.INCOMPATIBLE_HARD

    def test_no_manifest_returns_no_manifest_not_per_agent(self):
        result = _checker().check_agent(None, "5.10.0", "security-auditor")
        assert result.status == CompatibilityResult.NO_MANIFEST

    def test_per_agent_result_has_correct_min_cli_version(self):
        content = _make_agents_manifest(
            {"security-auditor": {"min_cli_version": "5.12.0"}},
            min_cli_version="5.0.0",
        )
        result = _checker().check_agent(content, "5.10.0", "security-auditor")
        assert result.min_cli_version == "5.12.0"


# ===========================================================================
# 5. Non-GitHub URL Support in ManifestFetcher
# ===========================================================================


class TestNonGitHubURLSupport:
    """Tests for GitLab, Bitbucket, and local filesystem URL support."""

    @pytest.fixture
    def fetcher(self) -> ManifestFetcher:
        return ManifestFetcher()

    @pytest.fixture
    def session(self):
        return MagicMock()

    # ── GitLab URL computation ──────────────────────────────────────────────

    def test_gitlab_url_computation(self, fetcher):
        url = fetcher._compute_manifest_url(
            "https://gitlab.com/owner/repo/-/raw/main/agents"
        )
        assert url == "https://gitlab.com/owner/repo/-/raw/main/agents-manifest.yaml"

    def test_gitlab_url_nested_subdir_stripped(self, fetcher):
        url = fetcher._compute_manifest_url(
            "https://gitlab.com/owner/repo/-/raw/main/path/to/agents"
        )
        assert url == "https://gitlab.com/owner/repo/-/raw/main/agents-manifest.yaml"

    def test_gitlab_url_no_subdir(self, fetcher):
        url = fetcher._compute_manifest_url("https://gitlab.com/owner/repo/-/raw/main")
        assert url == "https://gitlab.com/owner/repo/-/raw/main/agents-manifest.yaml"

    def test_gitlab_custom_branch(self, fetcher):
        url = fetcher._compute_manifest_url(
            "https://gitlab.com/owner/repo/-/raw/develop/agents"
        )
        assert url == "https://gitlab.com/owner/repo/-/raw/develop/agents-manifest.yaml"

    # ── Bitbucket URL computation ───────────────────────────────────────────

    def test_bitbucket_url_computation(self, fetcher):
        url = fetcher._compute_manifest_url(
            "https://bitbucket.org/owner/repo/raw/main/agents"
        )
        assert url == "https://bitbucket.org/owner/repo/raw/main/agents-manifest.yaml"

    def test_bitbucket_url_nested_subdir_stripped(self, fetcher):
        url = fetcher._compute_manifest_url(
            "https://bitbucket.org/owner/repo/raw/main/path/to/agents"
        )
        assert url == "https://bitbucket.org/owner/repo/raw/main/agents-manifest.yaml"

    def test_bitbucket_url_no_subdir(self, fetcher):
        url = fetcher._compute_manifest_url("https://bitbucket.org/owner/repo/raw/main")
        assert url == "https://bitbucket.org/owner/repo/raw/main/agents-manifest.yaml"

    def test_bitbucket_custom_branch(self, fetcher):
        url = fetcher._compute_manifest_url(
            "https://bitbucket.org/owner/repo/raw/develop/agents"
        )
        assert (
            url == "https://bitbucket.org/owner/repo/raw/develop/agents-manifest.yaml"
        )

    # ── Local filesystem path ──────────────────────────────────────────────

    def test_local_absolute_path_fetch(self, fetcher, tmp_path):
        manifest_file = tmp_path / ManifestFetcher.MANIFEST_FILENAME
        content = make_manifest_yaml(repo_format_version=1, min_cli_version="5.10.0")
        manifest_file.write_text(content, encoding="utf-8")
        session = MagicMock()
        result = fetcher.fetch(str(tmp_path), session)
        assert result == content
        session.get.assert_not_called()

    def test_local_file_uri_fetch(self, fetcher, tmp_path):
        manifest_file = tmp_path / ManifestFetcher.MANIFEST_FILENAME
        content = make_manifest_yaml(repo_format_version=1, min_cli_version="5.10.0")
        manifest_file.write_text(content, encoding="utf-8")
        session = MagicMock()
        result = fetcher.fetch(f"file://{tmp_path}", session)
        assert result == content

    def test_local_file_not_found_returns_none(self, fetcher, tmp_path):
        session = MagicMock()
        result = fetcher.fetch(str(tmp_path / "nonexistent_dir"), session)
        assert result is None

    def test_fetch_local_directly_returns_content(self, fetcher, tmp_path):
        manifest_file = tmp_path / ManifestFetcher.MANIFEST_FILENAME
        content = make_manifest_yaml(repo_format_version=1, min_cli_version="5.0.0")
        manifest_file.write_text(content, encoding="utf-8")
        result = fetcher.fetch_local(str(tmp_path))
        assert result == content

    def test_fetch_local_missing_file_returns_none(self, fetcher, tmp_path):
        result = fetcher.fetch_local(str(tmp_path / "no_dir"))
        assert result is None

    def test_fetch_local_file_uri_prefix_stripped(self, fetcher, tmp_path):
        manifest_file = tmp_path / ManifestFetcher.MANIFEST_FILENAME
        content = make_manifest_yaml()
        manifest_file.write_text(content, encoding="utf-8")
        result = fetcher.fetch_local(f"file://{tmp_path}")
        assert result == content

    # ── Unsupported URL returns None ────────────────────────────────────────

    def test_unsupported_url_returns_none(self, fetcher):
        url = fetcher._compute_manifest_url("https://example.com/agents")
        assert url is None

    def test_unsupported_url_no_network_call(self, fetcher, session):
        result = fetcher.fetch("https://example.com/agents", session)
        assert result is None
        session.get.assert_not_called()

    # ── Backward compatibility: GitHub URLs still work ─────────────────────

    def test_github_raw_url_still_works(self, fetcher):
        url = fetcher._compute_manifest_url(
            "https://raw.githubusercontent.com/owner/repo/main/agents"
        )
        assert url == (
            "https://raw.githubusercontent.com/owner/repo/main/agents-manifest.yaml"
        )


# ===========================================================================
# 6. Deprecation Warning Lifecycle
# ===========================================================================


class TestDeprecationWarnings:
    """Tests for deprecation_warnings support in ManifestChecker."""

    def test_warnings_parsed_and_returned_in_result(self):
        content = _make_deprecation_manifest(
            [
                {
                    "feature": "persona_field",
                    "removed_in": "9.0.0",
                    "replacement": "system_prompt",
                    "deadline": "2026-06-01",
                },
            ]
        )
        result = _checker().check(content, "5.10.0")
        assert result.deprecation_warnings is not None
        assert len(result.deprecation_warnings) == 1
        assert "persona_field" in result.deprecation_warnings[0]

    def test_no_deprecation_warnings_section_returns_none(self):
        content = make_manifest_yaml(repo_format_version=1, min_cli_version="5.0.0")
        result = _checker().check(content, "5.10.0")
        assert result.deprecation_warnings is None

    def test_malformed_warning_entries_ignored(self):
        """Non-dict entries in the warnings list are skipped."""
        content = _make_deprecation_manifest(
            [
                "not-a-dict",
                42,
                {"feature": "persona_field", "removed_in": "9.0.0"},
            ]
        )
        result = _checker().check(content, "5.10.0")
        # Only the valid dict entry should be in the list
        assert result.deprecation_warnings is not None
        assert len(result.deprecation_warnings) == 1
        assert "persona_field" in result.deprecation_warnings[0]

    def test_warnings_do_not_affect_compatibility_status(self):
        """Deprecation warnings are informational and never block."""
        content = _make_deprecation_manifest(
            [
                {
                    "feature": "old_field",
                    "removed_in": "9.0.0",
                    "replacement": "new_field",
                },
            ]
        )
        result = _checker().check(content, "5.10.0")
        assert result.status == CompatibilityResult.COMPATIBLE

    def test_already_removed_warning_excluded(self):
        """Warning with removed_in <= cli_version is excluded (already removed)."""
        content = _make_deprecation_manifest(
            [
                {"feature": "old_field", "removed_in": "5.0.0"},  # Already removed
            ]
        )
        result = _checker().check(content, "5.10.0")
        # Warning should be excluded since it's already been removed
        assert (
            result.deprecation_warnings is None or len(result.deprecation_warnings) == 0
        )

    def test_not_yet_removed_warning_included(self):
        """Warning with removed_in > cli_version is included."""
        content = _make_deprecation_manifest(
            [
                {"feature": "old_field", "removed_in": "9.0.0"},
            ]
        )
        result = _checker().check(content, "5.10.0")
        assert result.deprecation_warnings is not None
        assert len(result.deprecation_warnings) == 1

    def test_warning_includes_replacement_when_provided(self):
        content = _make_deprecation_manifest(
            [
                {
                    "feature": "persona_field",
                    "removed_in": "9.0.0",
                    "replacement": "system_prompt",
                },
            ]
        )
        result = _checker().check(content, "5.10.0")
        assert result.deprecation_warnings is not None
        assert "system_prompt" in result.deprecation_warnings[0]

    def test_warning_includes_deadline_when_provided(self):
        content = _make_deprecation_manifest(
            [
                {"feature": "old_api", "removed_in": "9.0.0", "deadline": "2026-06-01"},
            ]
        )
        result = _checker().check(content, "5.10.0")
        assert result.deprecation_warnings is not None
        assert "2026-06-01" in result.deprecation_warnings[0]

    def test_multiple_warnings_all_returned(self):
        content = _make_deprecation_manifest(
            [
                {"feature": "feature_a", "removed_in": "9.0.0"},
                {"feature": "feature_b", "removed_in": "8.0.0"},
            ]
        )
        result = _checker().check(content, "5.10.0")
        assert result.deprecation_warnings is not None
        assert len(result.deprecation_warnings) == 2

    def test_warnings_present_on_incompatible_warn_result(self):
        """Deprecation warnings are attached even when status is INCOMPATIBLE_WARN."""
        data = {
            "repo_format_version": 1,
            "min_cli_version": "5.12.0",
            "deprecation_warnings": [
                {"feature": "old_field", "removed_in": "9.0.0"},
            ],
        }
        content = yaml.dump(data)
        result = _checker().check(content, "5.10.0")
        assert result.status == CompatibilityResult.INCOMPATIBLE_WARN
        assert result.deprecation_warnings is not None

    def test_empty_warnings_list_returns_none(self):
        content = _make_deprecation_manifest([])
        result = _checker().check(content, "5.10.0")
        assert result.deprecation_warnings is None

    def test_warning_without_removed_in_always_included(self):
        """Warning with no removed_in field is always applicable."""
        content = _make_deprecation_manifest(
            [
                {"feature": "old_field"},
            ]
        )
        result = _checker().check(content, "5.10.0")
        assert result.deprecation_warnings is not None
        assert len(result.deprecation_warnings) == 1
