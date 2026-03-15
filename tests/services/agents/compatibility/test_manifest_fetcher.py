"""Unit tests for ManifestFetcher.

Category 2: Fetcher HTTP behaviour (mock session.get)
Category 3: URL computation logic (_compute_manifest_url)
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from claude_mpm.services.agents.compatibility.manifest_fetcher import ManifestFetcher
from tests.services.agents.compatibility.conftest import (
    make_manifest_response,
    make_manifest_yaml,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fetcher() -> ManifestFetcher:
    return ManifestFetcher()


@pytest.fixture
def session(mock_session):
    return mock_session


# ---------------------------------------------------------------------------
# Category 2: Fetcher HTTP behaviour
# ---------------------------------------------------------------------------


class TestManifestFetcherHTTP:
    """Tests for ManifestFetcher.fetch() - mock HTTP responses."""

    BASE_URL = "https://raw.githubusercontent.com/owner/repo/main/agents"

    def test_2_1_successful_fetch_returns_content(self, fetcher, mock_session):
        """HTTP 200 returns the YAML text."""
        yaml_text = make_manifest_yaml(repo_format_version=1, min_cli_version="5.8.0")
        mock_session.get.return_value = make_manifest_response(200, yaml_text)

        result = fetcher.fetch(self.BASE_URL, mock_session)

        assert result == yaml_text

    def test_2_2_404_returns_none(self, fetcher, mock_session):
        """HTTP 404 (manifest absent) returns None."""
        mock_session.get.return_value = make_manifest_response(404)

        result = fetcher.fetch(self.BASE_URL, mock_session)

        assert result is None

    def test_2_3_304_not_modified_returns_none(self, fetcher, mock_session):
        """HTTP 304 (not modified) returns None."""
        mock_session.get.return_value = make_manifest_response(304)

        result = fetcher.fetch(self.BASE_URL, mock_session)

        assert result is None

    def test_2_4_403_rate_limited_returns_none(self, fetcher, mock_session):
        """HTTP 403 returns None (treated as unavailable)."""
        mock_session.get.return_value = make_manifest_response(403)

        result = fetcher.fetch(self.BASE_URL, mock_session)

        assert result is None

    def test_2_5_500_server_error_returns_none(self, fetcher, mock_session):
        """HTTP 500 returns None (fail-open)."""
        mock_session.get.return_value = make_manifest_response(500)

        result = fetcher.fetch(self.BASE_URL, mock_session)

        assert result is None

    def test_2_6_network_timeout_returns_none(self, fetcher, mock_session):
        """requests.Timeout raises → fetch returns None."""
        mock_session.get.side_effect = requests.Timeout("Connection timed out")

        result = fetcher.fetch(self.BASE_URL, mock_session)

        assert result is None

    def test_2_7_connection_refused_returns_none(self, fetcher, mock_session):
        """requests.ConnectionError raises → fetch returns None."""
        mock_session.get.side_effect = requests.ConnectionError("Connection refused")

        result = fetcher.fetch(self.BASE_URL, mock_session)

        assert result is None

    def test_generic_request_exception_returns_none(self, fetcher, mock_session):
        """Any other requests.RequestException → returns None."""
        mock_session.get.side_effect = requests.RequestException("Unknown error")

        result = fetcher.fetch(self.BASE_URL, mock_session)

        assert result is None

    def test_oversized_manifest_returns_none(self, fetcher, mock_session):
        """Manifests exceeding MAX_MANIFEST_SIZE (1 MiB) are rejected."""
        from claude_mpm.services.agents.compatibility.manifest_fetcher import (
            MAX_MANIFEST_SIZE,
        )

        oversized_content = "x" * (MAX_MANIFEST_SIZE + 1)
        mock_session.get.return_value = make_manifest_response(200, oversized_content)

        result = fetcher.fetch(self.BASE_URL, mock_session)

        assert result is None

    def test_manifest_at_exact_size_limit_is_accepted(self, fetcher, mock_session):
        """Manifests exactly at the limit boundary should be accepted."""
        from claude_mpm.services.agents.compatibility.manifest_fetcher import (
            MAX_MANIFEST_SIZE,
        )

        exact_content = "x" * MAX_MANIFEST_SIZE
        mock_session.get.return_value = make_manifest_response(200, exact_content)

        result = fetcher.fetch(self.BASE_URL, mock_session)

        assert result == exact_content

    def test_non_github_raw_url_returns_none_without_network_call(
        self, fetcher, mock_session
    ):
        """Non-GitHub-raw URLs are silently skipped (no HTTP request made)."""
        result = fetcher.fetch("https://example.com/agents", mock_session)

        assert result is None
        mock_session.get.assert_not_called()

    def test_200_response_uses_correct_manifest_url(self, fetcher, mock_session):
        """Verify the computed URL is passed to session.get."""
        yaml_text = make_manifest_yaml()
        mock_session.get.return_value = make_manifest_response(200, yaml_text)

        fetcher.fetch(self.BASE_URL, mock_session)

        expected_url = (
            "https://raw.githubusercontent.com/owner/repo/main/agents-manifest.yaml"
        )
        mock_session.get.assert_called_once_with(expected_url, timeout=5, stream=True)


# ---------------------------------------------------------------------------
# Category 3: URL computation
# ---------------------------------------------------------------------------


class TestComputeManifestUrl:
    """Tests for ManifestFetcher._compute_manifest_url."""

    @pytest.fixture
    def fetcher(self) -> ManifestFetcher:
        return ManifestFetcher()

    def test_3_1_standard_layout_with_agents_subdir(self, fetcher):
        """Standard .../main/agents → .../main/agents-manifest.yaml"""
        url = fetcher._compute_manifest_url(
            "https://raw.githubusercontent.com/owner/repo/main/agents"
        )
        assert url == (
            "https://raw.githubusercontent.com/owner/repo/main/agents-manifest.yaml"
        )

    def test_3_2_custom_branch(self, fetcher):
        """Develop branch → manifest at develop root."""
        url = fetcher._compute_manifest_url(
            "https://raw.githubusercontent.com/owner/repo/develop/agents"
        )
        assert url == (
            "https://raw.githubusercontent.com/owner/repo/develop/agents-manifest.yaml"
        )

    def test_3_3_nested_subdirectory_is_stripped(self, fetcher):
        """Nested subdirs are stripped: .../main/path/to/agents → .../main/agents-manifest.yaml"""
        url = fetcher._compute_manifest_url(
            "https://raw.githubusercontent.com/owner/repo/main/path/to/agents"
        )
        assert url == (
            "https://raw.githubusercontent.com/owner/repo/main/agents-manifest.yaml"
        )

    def test_3_4_no_subdirectory_gets_manifest_appended(self, fetcher):
        """.../main (no subdir) → .../main/agents-manifest.yaml"""
        url = fetcher._compute_manifest_url(
            "https://raw.githubusercontent.com/owner/repo/main"
        )
        assert url == (
            "https://raw.githubusercontent.com/owner/repo/main/agents-manifest.yaml"
        )

    def test_3_5_trailing_slash_is_handled(self, fetcher):
        """Trailing slash is stripped before path processing."""
        url = fetcher._compute_manifest_url(
            "https://raw.githubusercontent.com/owner/repo/main/agents/"
        )
        assert url == (
            "https://raw.githubusercontent.com/owner/repo/main/agents-manifest.yaml"
        )

    def test_non_github_raw_url_returns_none(self, fetcher):
        """Non-GitHub-raw URL returns None."""
        assert fetcher._compute_manifest_url("https://example.com/agents") is None

    def test_http_not_https_also_not_supported(self, fetcher):
        """plain-http URL for raw.githubusercontent.com is not matched by Phase 1."""
        # The check is string membership of 'raw.githubusercontent.com/', so
        # even an http:// URL would pass; this documents that behaviour.
        url = fetcher._compute_manifest_url(
            "http://raw.githubusercontent.com/owner/repo/main/agents"
        )
        # Should still compute (check is on host string, not scheme)
        assert url is not None
        assert "agents-manifest.yaml" in url

    def test_incomplete_path_fewer_than_3_segments_returns_none(self, fetcher):
        """URL with < 3 path segments (missing branch) returns None."""
        url = fetcher._compute_manifest_url(
            "https://raw.githubusercontent.com/owner/repo"
        )
        assert url is None

    def test_manifest_filename_constant_is_used(self, fetcher):
        """The computed URL ends with MANIFEST_FILENAME."""
        url = fetcher._compute_manifest_url(
            "https://raw.githubusercontent.com/owner/repo/main/agents"
        )
        assert url is not None
        assert url.endswith(ManifestFetcher.MANIFEST_FILENAME)

    def test_branch_name_preserved_exactly(self, fetcher):
        """Branch names with special characters are preserved."""
        url = fetcher._compute_manifest_url(
            "https://raw.githubusercontent.com/owner/repo/feature-v2/agents"
        )
        assert url == (
            "https://raw.githubusercontent.com/owner/repo/feature-v2/agents-manifest.yaml"
        )
