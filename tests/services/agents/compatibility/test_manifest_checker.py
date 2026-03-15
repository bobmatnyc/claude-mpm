"""Unit tests for ManifestChecker.

Tests the compatibility decision matrix:
  1. Compatible manifests
  2. Incompatible format (hard stop)
  3. CLI too old (soft warn)
  4. Missing or empty manifests
  5. Malformed manifests
  6. Default values and edge cases
  7. Version boundary behaviour
"""

import pytest

from claude_mpm.services.agents.compatibility.manifest_checker import (
    CompatibilityResult,
    ManifestChecker,
    ManifestCheckResult,
)
from tests.services.agents.compatibility.conftest import make_manifest_yaml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _checker() -> ManifestChecker:
    return ManifestChecker()


# ---------------------------------------------------------------------------
# Category 1.1 - 1.16 : parametrized core decision-matrix tests
# ---------------------------------------------------------------------------


class TestManifestCheckerDecisionMatrix:
    """Parametrized tests covering the complete decision matrix."""

    @pytest.mark.parametrize(
        "rfv,min_v,cli_v,expected_status",
        [
            # 1.1 compatible: all fields present, cli satisfies min
            (1, "5.8.0", "5.10.0", CompatibilityResult.COMPATIBLE),
            # 1.2 incompatible hard: rfv > MAX_SUPPORTED (1)
            (2, "5.8.0", "5.10.0", CompatibilityResult.INCOMPATIBLE_HARD),
            # 1.3 cli too old: min > cli
            (1, "5.12.0", "5.10.0", CompatibilityResult.INCOMPATIBLE_WARN),
            # 1.16 equal version boundary: min == cli (>= comparison should pass)
            (1, "5.10.0", "5.10.0", CompatibilityResult.COMPATIBLE),
        ],
        ids=[
            "1.1-compatible",
            "1.2-hard-stop",
            "1.3-cli-too-old",
            "1.16-equal-boundary",
        ],
    )
    def test_basic_matrix(self, rfv, min_v, cli_v, expected_status):
        content = make_manifest_yaml(repo_format_version=rfv, min_cli_version=min_v)
        result = _checker().check(content, cli_version=cli_v)
        assert result.status == expected_status

    # 1.4 - None input
    def test_none_manifest_returns_no_manifest(self):
        result = _checker().check(None, cli_version="5.10.0")
        assert result.status == CompatibilityResult.NO_MANIFEST

    # 1.5 - empty string
    def test_empty_string_returns_no_manifest(self):
        result = _checker().check("", cli_version="5.10.0")
        assert result.status == CompatibilityResult.NO_MANIFEST

    # 1.5 - whitespace only
    def test_whitespace_only_returns_no_manifest(self):
        result = _checker().check("   \n\t  ", cli_version="5.10.0")
        assert result.status == CompatibilityResult.NO_MANIFEST

    # 1.6 - malformed YAML
    def test_malformed_yaml_returns_no_manifest(self):
        bad_yaml = "not: valid: yaml: {["
        result = _checker().check(bad_yaml, cli_version="5.10.0")
        assert result.status == CompatibilityResult.NO_MANIFEST

    # 1.7 - missing repo_format_version defaults to 1 (COMPATIBLE)
    def test_missing_rfv_defaults_to_1(self):
        content = "min_cli_version: '5.8.0'\n"
        result = _checker().check(content, cli_version="5.10.0")
        assert result.status == CompatibilityResult.COMPATIBLE
        assert result.repo_format_version == 1

    # 1.8 - missing min_cli_version defaults to 0.0.0 (COMPATIBLE, skip check)
    def test_missing_min_cli_version_defaults_to_zero(self):
        content = "repo_format_version: 1\n"
        result = _checker().check(content, cli_version="5.10.0")
        assert result.status == CompatibilityResult.COMPATIBLE
        assert result.min_cli_version == "0.0.0"

    # 1.9 - both fields missing: all defaults, COMPATIBLE
    def test_empty_mapping_compatible_with_all_defaults(self):
        content = "{}\n"
        result = _checker().check(content, cli_version="5.10.0")
        assert result.status == CompatibilityResult.COMPATIBLE
        assert result.repo_format_version == 1
        assert result.min_cli_version == "0.0.0"

    # 1.10 - non-integer rfv defaults to 1
    def test_non_integer_rfv_defaults_to_1(self):
        content = "repo_format_version: 'abc'\nmin_cli_version: '5.8.0'\n"
        result = _checker().check(content, cli_version="5.10.0")
        assert result.status == CompatibilityResult.COMPATIBLE
        assert result.repo_format_version == 1

    # 1.11 - invalid min_cli_version string: PEP 440 validation defaults to "0.0.0"
    # The invalid string is caught by _extract_min_cli_version which now validates
    # PEP 440 format and returns "0.0.0" for invalid strings.  Since "0.0.0"
    # triggers the skip guard (if min_cli_version != "0.0.0"), the check is
    # effectively bypassed → COMPATIBLE (fail-open).
    def test_invalid_min_cli_version_string_is_fail_open(self):
        content = "repo_format_version: 1\nmin_cli_version: 'not-semver'\n"
        result = _checker().check(content, cli_version="5.10.0")
        assert result.status == CompatibilityResult.COMPATIBLE
        # The invalid version was defaulted to "0.0.0"
        assert result.min_cli_version == "0.0.0"

    # 1.12 - suspiciously high min_cli_version still triggers INCOMPATIBLE_WARN
    def test_suspiciously_high_min_cli_version_is_incompatible_warn(self):
        content = make_manifest_yaml(repo_format_version=1, min_cli_version="999.0.0")
        result = _checker().check(content, cli_version="5.10.0")
        assert result.status == CompatibilityResult.INCOMPATIBLE_WARN

    # 1.13 - max_cli_version is advisory only: COMPATIBLE even when cli > max
    def test_max_cli_version_exceeded_is_advisory_only(self):
        content = make_manifest_yaml(
            repo_format_version=1,
            min_cli_version="5.0.0",
            max_cli_version="5.9.0",
        )
        result = _checker().check(content, cli_version="5.10.0")
        assert result.status == CompatibilityResult.COMPATIBLE

    # 1.14 - unknown extra fields are ignored
    def test_unknown_extra_fields_are_ignored(self):
        content = make_manifest_yaml(
            repo_format_version=1,
            min_cli_version="5.0.0",
            extra_fields={"some_future_field": "value", "another": 42},
        )
        result = _checker().check(content, cli_version="5.10.0")
        assert result.status == CompatibilityResult.COMPATIBLE

    # 1.15 - CLI version with build metadata suffix (PEP 440 local version)
    # packaging.version.Version("5.10.0+build.275") > Version("5.10.0"), so
    # cli >= min → COMPATIBLE.
    def test_cli_version_with_build_suffix_is_compatible(self):
        content = make_manifest_yaml(repo_format_version=1, min_cli_version="5.10.0")
        result = _checker().check(content, cli_version="5.10.0+build.275")
        assert result.status == CompatibilityResult.COMPATIBLE


# ---------------------------------------------------------------------------
# ManifestCheckResult field validation
# ---------------------------------------------------------------------------


class TestManifestCheckResultFields:
    """Verify ManifestCheckResult fields are populated correctly."""

    def test_compatible_result_fields(self):
        content = make_manifest_yaml(repo_format_version=1, min_cli_version="5.8.0")
        result = _checker().check(content, cli_version="5.10.0")

        assert result.status == CompatibilityResult.COMPATIBLE
        assert result.repo_format_version == 1
        assert result.min_cli_version == "5.8.0"
        assert result.cli_version == "5.10.0"
        assert isinstance(result.message, str)
        assert len(result.message) > 0

    def test_no_manifest_result_has_none_fields(self):
        result = _checker().check(None, cli_version="5.10.0")

        assert result.status == CompatibilityResult.NO_MANIFEST
        assert result.repo_format_version is None
        assert result.min_cli_version is None
        assert result.cli_version == "5.10.0"

    def test_incompatible_hard_result_fields(self):
        content = make_manifest_yaml(repo_format_version=2, min_cli_version="5.8.0")
        result = _checker().check(content, cli_version="5.10.0")

        assert result.status == CompatibilityResult.INCOMPATIBLE_HARD
        assert result.repo_format_version == 2
        assert result.cli_version == "5.10.0"

    def test_incompatible_warn_result_fields(self):
        content = make_manifest_yaml(repo_format_version=1, min_cli_version="5.12.0")
        result = _checker().check(content, cli_version="5.10.0")

        assert result.status == CompatibilityResult.INCOMPATIBLE_WARN
        assert result.repo_format_version == 1
        assert result.min_cli_version == "5.12.0"
        assert result.cli_version == "5.10.0"

    def test_migration_notes_included_in_hard_stop_message(self):
        content = make_manifest_yaml(
            repo_format_version=2,
            min_cli_version="5.8.0",
            migration_notes="Run: pip install --upgrade claude-mpm",
        )
        result = _checker().check(content, cli_version="5.10.0")

        assert result.status == CompatibilityResult.INCOMPATIBLE_HARD
        assert result.migration_notes == "Run: pip install --upgrade claude-mpm"
        assert "Migration notes" in result.message

    def test_migration_notes_included_in_warn_message(self):
        content = make_manifest_yaml(
            repo_format_version=1,
            min_cli_version="5.12.0",
            migration_notes="Please upgrade for new agent features.",
        )
        result = _checker().check(content, cli_version="5.10.0")

        assert result.status == CompatibilityResult.INCOMPATIBLE_WARN
        assert result.migration_notes == "Please upgrade for new agent features."
        assert "Migration notes" in result.message

    def test_no_migration_notes_when_absent(self):
        content = make_manifest_yaml(repo_format_version=1, min_cli_version="5.8.0")
        result = _checker().check(content, cli_version="5.10.0")

        assert result.migration_notes is None


# ---------------------------------------------------------------------------
# Hard-stop message quality assertions
# ---------------------------------------------------------------------------


class TestHardStopMessageQuality:
    """Verify INCOMPATIBLE_HARD messages contain actionable guidance."""

    def test_hard_stop_message_includes_pip_upgrade(self):
        content = make_manifest_yaml(repo_format_version=2, min_cli_version="5.8.0")
        result = _checker().check(content, cli_version="5.10.0")

        assert "pip install --upgrade claude-mpm" in result.message

    def test_hard_stop_message_includes_repo_format_version(self):
        content = make_manifest_yaml(repo_format_version=2, min_cli_version="5.8.0")
        result = _checker().check(content, cli_version="5.10.0")

        assert "2" in result.message

    def test_warn_message_includes_min_cli_version(self):
        content = make_manifest_yaml(repo_format_version=1, min_cli_version="5.12.0")
        result = _checker().check(content, cli_version="5.10.0")

        assert "5.12.0" in result.message

    def test_hard_stop_message_includes_max_supported(self):
        content = make_manifest_yaml(repo_format_version=3, min_cli_version="5.8.0")
        result = _checker().check(content, cli_version="5.10.0")

        # Should mention the max supported format version
        assert str(ManifestChecker.MAX_SUPPORTED_REPO_FORMAT) in result.message


# ---------------------------------------------------------------------------
# _compare_versions internal helper tests
# ---------------------------------------------------------------------------


class TestCompareVersions:
    """Tests for the _compare_versions helper directly."""

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            ("5.9.0", "5.10.0", "less"),
            ("5.10.0", "5.10.0", "equal"),
            ("5.11.0", "5.10.0", "greater"),
            ("5.10.0", "not-semver", "equal"),  # fail-open on invalid b
            ("not-semver", "5.10.0", "equal"),  # fail-open on invalid a
            ("abc", "xyz", "equal"),  # both invalid → equal
        ],
        ids=["less", "equal", "greater", "invalid-b", "invalid-a", "both-invalid"],
    )
    def test_compare_versions(self, a, b, expected):
        result = _checker()._compare_versions(a, b)
        assert result == expected


# ---------------------------------------------------------------------------
# _extract_repo_format_version helper tests
# ---------------------------------------------------------------------------


class TestExtractRepoFormatVersion:
    """Tests for the _extract_repo_format_version helper."""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ({"repo_format_version": 1}, 1),
            ({"repo_format_version": 2}, 2),
            ({}, 1),  # missing → default 1
            ({"repo_format_version": None}, 1),  # None → default 1
            ({"repo_format_version": "abc"}, 1),  # non-int → default 1
            ({"repo_format_version": "2"}, 2),  # stringified int → parsed
        ],
        ids=["v1", "v2", "missing", "none", "non-int-str", "stringified-int"],
    )
    def test_extract_repo_format_version(self, raw, expected):
        result = _checker()._extract_repo_format_version(raw)
        assert result == expected


# ---------------------------------------------------------------------------
# _extract_min_cli_version helper tests
# ---------------------------------------------------------------------------


class TestExtractMinCliVersion:
    """Tests for the _extract_min_cli_version helper."""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ({"min_cli_version": "5.10.0"}, "5.10.0"),
            ({}, "0.0.0"),  # missing → default
            ({"min_cli_version": None}, "0.0.0"),  # None → default
            ({"min_cli_version": ""}, "0.0.0"),  # empty → default
            ({"min_cli_version": "  "}, "0.0.0"),  # whitespace → default
            ({"min_cli_version": "  5.9.0  "}, "5.9.0"),  # strips whitespace
            # Invalid PEP 440 version string defaults to "0.0.0"
            ({"min_cli_version": "not-semver"}, "0.0.0"),
        ],
        ids=[
            "present",
            "missing",
            "none",
            "empty",
            "whitespace",
            "strips-whitespace",
            "invalid-passthrough",
        ],
    )
    def test_extract_min_cli_version(self, raw, expected):
        result = _checker()._extract_min_cli_version(raw)
        assert result == expected


# ---------------------------------------------------------------------------
# YAML that is valid but not a dict (e.g. a bare string or list)
# ---------------------------------------------------------------------------


class TestNonDictYAML:
    """Manifests that parse as non-dict YAML structures."""

    @pytest.mark.parametrize(
        "content",
        [
            "just a string\n",
            "- item1\n- item2\n",
            "42\n",
            "null\n",
        ],
        ids=["bare-string", "list", "integer", "null"],
    )
    def test_non_dict_yaml_returns_no_manifest(self, content):
        result = _checker().check(content, cli_version="5.10.0")
        assert result.status == CompatibilityResult.NO_MANIFEST
