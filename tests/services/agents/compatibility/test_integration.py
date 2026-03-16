"""Integration tests for manifest compatibility wiring.

Category 4: GitSourceSyncService._check_manifest_compatibility
Category 5: Regression - existing sync behaviour unchanged
Category 6: Error message quality assertions
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.agents.compatibility.manifest_checker import (
    CompatibilityResult,
    ManifestChecker,
    ManifestCheckResult,
)
from claude_mpm.services.agents.compatibility.manifest_fetcher import ManifestFetcher
from claude_mpm.services.agents.sources.git_source_sync_service import (
    GitSourceSyncService,
    IncompatibleRepoError,
)
from tests.services.agents.compatibility.conftest import make_manifest_yaml

# ---------------------------------------------------------------------------
# Shared helper - build a GitSourceSyncService with a tmp cache dir and all
# heavy __init__ side-effects (real DB, git-manager, etc.) kept local.
# ---------------------------------------------------------------------------


@pytest.fixture
def service(tmp_path) -> GitSourceSyncService:
    """GitSourceSyncService wired to a temporary cache directory."""
    return GitSourceSyncService(
        source_url=("https://raw.githubusercontent.com/owner/repo/main/agents"),
        cache_dir=tmp_path,
        source_id="test-source",
    )


# ---------------------------------------------------------------------------
# Category 4: _check_manifest_compatibility integration
# ---------------------------------------------------------------------------


class TestCheckManifestCompatibilityIntegration:
    """Verify that _check_manifest_compatibility behaves correctly end-to-end."""

    # 4.1 - Compatible source proceeds normally (no exception raised)
    def test_4_1_compatible_manifest_proceeds(self, service):
        compatible_yaml = make_manifest_yaml(
            repo_format_version=1, min_cli_version="5.0.0"
        )
        with patch.object(ManifestFetcher, "fetch", return_value=compatible_yaml):
            with patch("claude_mpm.__version__", "5.10.0"):
                result = service._check_manifest_compatibility()

        assert result.status == CompatibilityResult.COMPATIBLE

    # 4.2 - Incompatible (hard) raises IncompatibleRepoError
    def test_4_2_incompatible_hard_raises_error(self, service):
        hard_yaml = make_manifest_yaml(repo_format_version=2, min_cli_version="5.0.0")
        with patch.object(ManifestFetcher, "fetch", return_value=hard_yaml):
            with patch("claude_mpm.__version__", "5.10.0"):
                with pytest.raises(IncompatibleRepoError) as exc_info:
                    service._check_manifest_compatibility()

        err = exc_info.value
        assert err.repo_format_version == 2

    # 4.3 - Missing manifest (None) treated as compatible (no exception)
    def test_4_3_missing_manifest_is_fail_open(self, service):
        with patch.object(ManifestFetcher, "fetch", return_value=None):
            with patch("claude_mpm.__version__", "5.10.0"):
                result = service._check_manifest_compatibility()

        assert result.status == CompatibilityResult.NO_MANIFEST

    # 4.4 - INCOMPATIBLE_WARN does NOT raise, returns result with warn status
    def test_4_4_warn_does_not_raise(self, service):
        warn_yaml = make_manifest_yaml(repo_format_version=1, min_cli_version="5.99.0")
        with patch.object(ManifestFetcher, "fetch", return_value=warn_yaml):
            with patch("claude_mpm.__version__", "5.10.0"):
                result = service._check_manifest_compatibility()

        assert result.status == CompatibilityResult.INCOMPATIBLE_WARN

    # 4.5 - skip_check=True bypasses network and check
    def test_4_5_skip_check_bypasses_fetch(self, service):
        with patch.object(ManifestFetcher, "fetch") as mock_fetch:
            result = service._check_manifest_compatibility(skip_check=True)

        mock_fetch.assert_not_called()
        assert result.status == CompatibilityResult.NO_MANIFEST

    # 4.6 - Env var CLAUDE_MPM_SKIP_COMPAT_CHECK="1" bypasses check
    def test_4_6_env_var_skips_check(self, service, monkeypatch):
        monkeypatch.setenv("CLAUDE_MPM_SKIP_COMPAT_CHECK", "1")
        with patch.object(ManifestFetcher, "fetch") as mock_fetch:
            result = service._check_manifest_compatibility()

        mock_fetch.assert_not_called()
        assert result.status == CompatibilityResult.NO_MANIFEST

    # 4.7 - Env var with "true" value also triggers skip
    def test_4_7_env_var_true_string_skips_check(self, service, monkeypatch):
        monkeypatch.setenv("CLAUDE_MPM_SKIP_COMPAT_CHECK", "true")
        with patch.object(ManifestFetcher, "fetch") as mock_fetch:
            result = service._check_manifest_compatibility()

        mock_fetch.assert_not_called()
        assert result.status == CompatibilityResult.NO_MANIFEST

    # 4.8 - Env var with "yes" value also triggers skip
    def test_4_8_env_var_yes_skips_check(self, service, monkeypatch):
        monkeypatch.setenv("CLAUDE_MPM_SKIP_COMPAT_CHECK", "yes")
        with patch.object(ManifestFetcher, "fetch") as mock_fetch:
            result = service._check_manifest_compatibility()

        mock_fetch.assert_not_called()
        assert result.status == CompatibilityResult.NO_MANIFEST

    # 4.9 - IncompatibleRepoError captures min_cli_version from result
    def test_4_9_incompatible_error_captures_min_cli_version(self, service):
        hard_yaml = make_manifest_yaml(repo_format_version=2, min_cli_version="6.0.0")
        with patch.object(ManifestFetcher, "fetch", return_value=hard_yaml):
            with patch("claude_mpm.__version__", "5.10.0"):
                with pytest.raises(IncompatibleRepoError) as exc_info:
                    service._check_manifest_compatibility()

        assert exc_info.value.min_cli_version == "6.0.0"

    # 4.10 - The fetcher receives the service source_url
    def test_4_10_fetcher_receives_service_source_url(self, service):
        compatible_yaml = make_manifest_yaml(
            repo_format_version=1, min_cli_version="5.0.0"
        )
        with patch.object(
            ManifestFetcher, "fetch", return_value=compatible_yaml
        ) as mock_fetch:
            with patch("claude_mpm.__version__", "5.10.0"):
                service._check_manifest_compatibility()

        # fetch was called with source_url equal to the service's url
        call_kwargs = mock_fetch.call_args
        called_url = call_kwargs[1].get("source_url") or call_kwargs[0][0]
        assert called_url == service.source_url


# ---------------------------------------------------------------------------
# Category 5: Regression - existing sync behaviour unchanged
# ---------------------------------------------------------------------------


class TestRegressionExistingSyncUnchanged:
    """Ensure manifest check integrates without breaking pre-existing behaviour."""

    def test_5_1_no_manifest_does_not_abort_sync_pipeline(self, service):
        """When there is no manifest, sync should still be able to proceed.

        We test _check_manifest_compatibility in isolation here - it must
        return NO_MANIFEST rather than raising, so the caller can decide.
        """
        with patch.object(ManifestFetcher, "fetch", return_value=None):
            with patch("claude_mpm.__version__", "5.10.0"):
                result = service._check_manifest_compatibility()

        # NO_MANIFEST means fail-open - sync pipeline should not be blocked
        assert result.status == CompatibilityResult.NO_MANIFEST
        assert result.repo_format_version is None

    def test_5_2_source_url_set_correctly_on_service(self, tmp_path):
        """Service strips trailing slash from source_url as before."""
        svc = GitSourceSyncService(
            source_url=("https://raw.githubusercontent.com/owner/repo/main/agents/"),
            cache_dir=tmp_path,
        )
        assert not svc.source_url.endswith("/")

    def test_5_3_check_does_not_mutate_service_state(self, service):
        """Calling _check_manifest_compatibility does not change source_url."""
        original_url = service.source_url
        with patch.object(ManifestFetcher, "fetch", return_value=None):
            with patch("claude_mpm.__version__", "5.10.0"):
                service._check_manifest_compatibility()

        assert service.source_url == original_url

    def test_5_4_agent_frontmatter_parsing_unaffected(self):
        """The manifest YAML does not contain agent frontmatter fields.

        This regression test ensures that make_manifest_yaml() produces YAML
        that is structurally distinct from agent frontmatter, preventing
        accidental cross-contamination in parsers that might see both.
        """
        manifest_yaml = make_manifest_yaml(
            repo_format_version=1, min_cli_version="5.0.0"
        )
        import yaml

        parsed = yaml.safe_load(manifest_yaml)

        # Manifest should NOT have typical agent frontmatter keys
        agent_frontmatter_keys = {"name", "role", "tools", "description", "version"}
        intersection = set(parsed.keys()) & agent_frontmatter_keys
        assert not intersection, (
            f"Manifest YAML unexpectedly contains agent frontmatter keys: {intersection}"
        )

    def test_5_5_manifest_check_is_independent_per_call(self, service):
        """Multiple calls to _check_manifest_compatibility are independent."""
        compatible_yaml = make_manifest_yaml(
            repo_format_version=1, min_cli_version="5.0.0"
        )
        hard_yaml = make_manifest_yaml(repo_format_version=2, min_cli_version="5.0.0")

        with patch("claude_mpm.__version__", "5.10.0"):
            with patch.object(ManifestFetcher, "fetch", return_value=compatible_yaml):
                result1 = service._check_manifest_compatibility()
            assert result1.status == CompatibilityResult.COMPATIBLE

            with patch.object(ManifestFetcher, "fetch", return_value=hard_yaml):
                with pytest.raises(IncompatibleRepoError):
                    service._check_manifest_compatibility()

            # Back to compatible
            with patch.object(ManifestFetcher, "fetch", return_value=compatible_yaml):
                result3 = service._check_manifest_compatibility()
            assert result3.status == CompatibilityResult.COMPATIBLE


# ---------------------------------------------------------------------------
# Category 6: Error message quality
# ---------------------------------------------------------------------------


class TestErrorMessageQuality:
    """Verify that error messages contain actionable, human-readable guidance."""

    def test_6_1_hard_stop_message_includes_pip_upgrade(self):
        """INCOMPATIBLE_HARD message tells the user how to upgrade."""
        checker = ManifestChecker()
        content = make_manifest_yaml(repo_format_version=2, min_cli_version="5.0.0")
        result = checker.check(content, cli_version="5.10.0")

        assert result.status == CompatibilityResult.INCOMPATIBLE_HARD
        assert "pip install --upgrade claude-mpm" in result.message

    def test_6_2_hard_stop_message_includes_version_numbers(self):
        """INCOMPATIBLE_HARD message includes the offending format version."""
        checker = ManifestChecker()
        content = make_manifest_yaml(repo_format_version=3, min_cli_version="5.0.0")
        result = checker.check(content, cli_version="5.10.0")

        assert "3" in result.message  # repo format version
        assert str(ManifestChecker.MAX_SUPPORTED_REPO_FORMAT) in result.message

    def test_6_3_warn_message_includes_min_cli_version(self):
        """INCOMPATIBLE_WARN message tells the user which version they need."""
        checker = ManifestChecker()
        content = make_manifest_yaml(repo_format_version=1, min_cli_version="5.15.0")
        result = checker.check(content, cli_version="5.10.0")

        assert result.status == CompatibilityResult.INCOMPATIBLE_WARN
        assert "5.15.0" in result.message

    def test_6_4_migration_notes_displayed_in_hard_stop(self):
        """Migration notes from manifest appear in the hard-stop message."""
        checker = ManifestChecker()
        notes = "Run `pip install --upgrade claude-mpm` and re-run sync."
        content = make_manifest_yaml(
            repo_format_version=2,
            min_cli_version="5.0.0",
            migration_notes=notes,
        )
        result = checker.check(content, cli_version="5.10.0")

        assert result.status == CompatibilityResult.INCOMPATIBLE_HARD
        assert notes in result.message

    def test_6_5_migration_notes_displayed_in_warn(self):
        """Migration notes from manifest appear in the warn message."""
        checker = ManifestChecker()
        notes = "Agent format changed; please upgrade to use new tool declarations."
        content = make_manifest_yaml(
            repo_format_version=1,
            min_cli_version="5.15.0",
            migration_notes=notes,
        )
        result = checker.check(content, cli_version="5.10.0")

        assert result.status == CompatibilityResult.INCOMPATIBLE_WARN
        assert notes in result.message

    def test_6_6_no_manifest_message_is_informative(self):
        """NO_MANIFEST message explains that no constraints are enforced."""
        checker = ManifestChecker()
        result = checker.check(None, cli_version="5.10.0")

        assert result.status == CompatibilityResult.NO_MANIFEST
        assert len(result.message) > 10  # must have some content
        # Should mention proceeding without constraints
        msg_lower = result.message.lower()
        assert "proceed" in msg_lower or "no " in msg_lower

    def test_6_7_incompatible_error_message_preserved_on_exception(self, service):
        """IncompatibleRepoError message matches ManifestCheckResult.message."""
        hard_yaml = make_manifest_yaml(
            repo_format_version=2,
            min_cli_version="5.0.0",
            migration_notes="See CHANGELOG for migration steps.",
        )
        with patch.object(ManifestFetcher, "fetch", return_value=hard_yaml):
            with patch("claude_mpm.__version__", "5.10.0"):
                with pytest.raises(IncompatibleRepoError) as exc_info:
                    service._check_manifest_compatibility()

        # The exception message should include the checker's message text
        error_str = str(exc_info.value)
        assert "pip install --upgrade claude-mpm" in error_str

    def test_6_8_warn_message_includes_current_cli_version(self):
        """INCOMPATIBLE_WARN message includes the user's current CLI version."""
        checker = ManifestChecker()
        content = make_manifest_yaml(repo_format_version=1, min_cli_version="5.15.0")
        result = checker.check(content, cli_version="5.10.0")

        assert result.status == CompatibilityResult.INCOMPATIBLE_WARN
        assert "5.10.0" in result.message
