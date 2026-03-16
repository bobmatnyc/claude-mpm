"""Shared fixtures and helpers for compatibility test suite."""

from unittest.mock import MagicMock

import pytest
import yaml


@pytest.fixture
def mock_session():
    """Mock requests.Session for HTTP testing."""
    session = MagicMock()
    return session


def make_manifest_response(status_code=200, content="", content_length=None):
    """Factory for mock HTTP responses supporting streaming (iter_content).

    Args:
        status_code: HTTP status code to return.
        content: Text body of the response.
        content_length: Optional explicit content-length (unused; actual length
            is derived from encoded content).

    Returns:
        A MagicMock with .status_code, .text, .content, and .iter_content
        attributes set. iter_content yields the content in a single chunk,
        matching the streaming download pattern used by ManifestFetcher.
    """
    response = MagicMock()
    response.status_code = status_code
    response.text = content
    content_bytes = content.encode("utf-8") if isinstance(content, str) else content
    response.content = content_bytes

    def iter_content_fn(chunk_size=8192):
        """Yield content in chunks to simulate streaming."""
        for i in range(0, len(content_bytes), chunk_size):
            yield content_bytes[i : i + chunk_size]

    response.iter_content = iter_content_fn
    return response


def make_manifest_yaml(
    repo_format_version=1,
    min_cli_version="5.10.0",
    max_cli_version=None,
    migration_notes=None,
    extra_fields=None,
):
    """Generate a manifest YAML string from parameters.

    Args:
        repo_format_version: Integer format version to embed.
        min_cli_version: Minimum CLI version string.
        max_cli_version: Optional maximum CLI version string.
        migration_notes: Optional migration guidance string.
        extra_fields: Optional dict of additional top-level fields to include.

    Returns:
        A YAML-formatted string suitable for passing to ManifestChecker.check().
    """
    data = {
        "repo_format_version": repo_format_version,
        "min_cli_version": min_cli_version,
    }
    if max_cli_version is not None:
        data["max_cli_version"] = max_cli_version
    if migration_notes is not None:
        data["migration_notes"] = migration_notes
    if extra_fields:
        data.update(extra_fields)
    return yaml.dump(data)
