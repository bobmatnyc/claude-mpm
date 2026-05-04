"""Tests for ``VersionService.check_for_updates``.

WHY: Issue #471 replaced the placeholder implementation with a real PyPI
lookup. These tests pin down the new contract:
  * an update is detected when PyPI reports a newer version,
  * we report up-to-date when versions match,
  * network failures degrade gracefully,
  * results are cached for 1 hour to avoid hammering PyPI.
"""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING
from unittest.mock import patch
from urllib.error import URLError

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

from claude_mpm.services import version_service as version_service_module
from claude_mpm.services.version_service import VersionService


@pytest.fixture(autouse=True)
def reset_update_cache() -> Generator[None, None, None]:
    """Clear the module-level cache between tests so they stay isolated."""
    version_service_module._UPDATE_CHECK_CACHE.clear()
    yield
    version_service_module._UPDATE_CHECK_CACHE.clear()


def _fake_pypi_response(version: str) -> io.BytesIO:
    payload = {
        "info": {
            "version": version,
            "package_url": "https://pypi.org/project/claude-mpm/",
            "project_urls": {"Homepage": "https://github.com/bobmatnyc/claude-mpm"},
        }
    }

    class _Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_: object) -> None:
            self.close()

    return _Resp(json.dumps(payload).encode("utf-8"))


def test_update_available_when_pypi_has_newer_version() -> None:
    service = VersionService()

    with (
        patch.object(service, "get_base_version", return_value="1.0.0"),
        patch(
            "urllib.request.urlopen",
            return_value=_fake_pypi_response("2.0.0"),
        ),
    ):
        result = service.check_for_updates()

    assert result["update_available"] is True
    assert result["latest_version"] == "2.0.0"
    assert result["current_version"] == "1.0.0"
    assert "Update available" in result["message"]


def test_up_to_date_when_versions_match() -> None:
    service = VersionService()

    with (
        patch.object(service, "get_base_version", return_value="1.0.0"),
        patch(
            "urllib.request.urlopen",
            return_value=_fake_pypi_response("1.0.0"),
        ),
    ):
        result = service.check_for_updates()

    assert result["update_available"] is False
    assert result["latest_version"] == "1.0.0"
    assert result["current_version"] == "1.0.0"
    assert "latest version" in result["message"].lower()


def test_network_failure_returns_graceful_fallback() -> None:
    service = VersionService()

    with (
        patch.object(service, "get_base_version", return_value="1.0.0"),
        patch(
            "urllib.request.urlopen",
            side_effect=URLError("name resolution failed"),
        ),
    ):
        result = service.check_for_updates()

    assert result["update_available"] is False
    assert result["latest_version"] is None
    assert result["current_version"] == "1.0.0"
    assert "Version check failed" in result["message"]


def test_result_is_cached_for_one_hour() -> None:
    """Subsequent calls within the TTL should not hit PyPI again."""
    service = VersionService()

    with (
        patch.object(service, "get_base_version", return_value="1.0.0"),
        patch(
            "urllib.request.urlopen",
            return_value=_fake_pypi_response("2.0.0"),
        ) as mock_urlopen,
    ):
        first = service.check_for_updates()
        # Second call should be served from cache.
        second = service.check_for_updates()

    assert mock_urlopen.call_count == 1
    assert first["update_available"] is True
    assert second["update_available"] is True
    assert first == second


def test_cache_invalidates_when_local_version_changes() -> None:
    """Upgrading the installed version should bypass the cached result."""
    service = VersionService()

    # First call: stale entry from a previous install.
    with (
        patch.object(service, "get_base_version", return_value="1.0.0"),
        patch(
            "urllib.request.urlopen",
            return_value=_fake_pypi_response("2.0.0"),
        ),
    ):
        first = service.check_for_updates()
    assert first["update_available"] is True

    # Now the user has upgraded to 2.0.0; cache must NOT report an update.
    with (
        patch.object(service, "get_base_version", return_value="2.0.0"),
        patch(
            "urllib.request.urlopen",
            return_value=_fake_pypi_response("2.0.0"),
        ) as mock_urlopen,
    ):
        second = service.check_for_updates()
    assert mock_urlopen.call_count == 1  # cache miss for new version
    assert second["update_available"] is False


def test_cache_expires_after_ttl() -> None:
    """Once the TTL elapses, a fresh PyPI lookup must occur."""
    service = VersionService()

    # Drive ``time.monotonic`` from a list so we can simulate a jump
    # past the 1-hour TTL between the two calls. The list is generous
    # enough to cover any reasonable number of ``time.monotonic`` calls
    # inside ``check_for_updates``.
    # ``time.monotonic`` is invoked twice per ``check_for_updates`` call:
    # once when storing the cache entry and once on the next call's cache
    # check. We provide enough values to cover both calls, jumping past
    # the 1-hour TTL between them.
    base_time = 100.0
    far_future = base_time + 60 * 60 + 5
    times = [base_time, far_future, far_future, far_future]

    def fake_monotonic() -> float:
        return times.pop(0) if len(times) > 1 else times[0]

    with (
        patch.object(service, "get_base_version", return_value="1.0.0"),
        patch(
            "urllib.request.urlopen",
            side_effect=lambda *_: _fake_pypi_response("2.0.0"),
        ) as mock_urlopen,
        patch(
            "claude_mpm.services.version_service.time.monotonic",
            side_effect=fake_monotonic,
        ),
    ):
        service.check_for_updates()
        service.check_for_updates()

    assert mock_urlopen.call_count == 2


if __name__ == "__main__":  # pragma: no cover - manual debug hook
    pytest.main([__file__, "-v"])
