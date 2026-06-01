"""Tests for the ``claude-mpm ztk`` command family (cli/commands/ztk.py).

Focus: the version-currency update path. Network access is mocked — these
tests never hit GitHub and never require a real ztk binary.
"""

from __future__ import annotations

import json
import urllib.error
from datetime import UTC, datetime, timedelta

import pytest

from claude_mpm.cli.commands import ztk as ztk_cmd


@pytest.fixture(autouse=True)
def _isolated_latest_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(ztk_cmd, "_LATEST_CACHE", tmp_path / "ztk-latest-cache.json")
    yield


def test_fetch_latest_network_failure_returns_none(monkeypatch):
    """GitHub unreachable -> None, never raises (failure-tolerant)."""

    def _boom(*_a, **_k):
        raise urllib.error.URLError("no network")

    monkeypatch.setattr(ztk_cmd.urllib.request, "urlopen", _boom)
    assert ztk_cmd._fetch_latest_release_tag(use_cache=False) is None


def test_fetch_latest_parses_tag(monkeypatch):
    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"tag_name": "v0.3.0"}).encode("utf-8")

    monkeypatch.setattr(ztk_cmd.urllib.request, "urlopen", lambda *_a, **_k: _Resp())
    assert ztk_cmd._fetch_latest_release_tag(use_cache=False) == "v0.3.0"


def test_latest_cache_roundtrip_and_ttl(monkeypatch):
    ztk_cmd._write_latest_cache("v0.2.1")
    # Fresh cache served without any network call.
    monkeypatch.setattr(
        ztk_cmd.urllib.request,
        "urlopen",
        lambda *_a, **_k: pytest.fail("should not hit network on fresh cache"),
    )
    assert ztk_cmd._fetch_latest_release_tag() == "v0.2.1"


def test_latest_cache_expired_ignored(monkeypatch):
    stale = {
        "tag": "v0.0.1",
        "fetched_at": (datetime.now(UTC) - timedelta(hours=48)).isoformat(),
    }
    ztk_cmd._LATEST_CACHE.parent.mkdir(parents=True, exist_ok=True)
    ztk_cmd._LATEST_CACHE.write_text(json.dumps(stale), encoding="utf-8")
    assert ztk_cmd._read_latest_cache() is None


def test_check_subcommand_network_tolerant(monkeypatch, capsys):
    """`ztk check` prints 'unavailable' (non-fatal) when GitHub is down."""
    monkeypatch.setattr(ztk_cmd, "_fetch_latest_release_tag", lambda **_k: None)
    args = _Args(ztk_command="check")
    rc = ztk_cmd.run_ztk(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "unavailable" in out


def test_update_missing_script_reports_error(monkeypatch, capsys):
    monkeypatch.setattr(ztk_cmd, "_download_script", lambda: _FakePath(exists=False))
    args = _Args(ztk_command="update", latest=False)
    rc = ztk_cmd.run_ztk(args)
    assert rc == 1


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _FakePath:
    def __init__(self, *, exists):
        self._exists = exists
        self.name = "download_ztk_binaries.sh"

    def is_file(self):
        return self._exists

    def __str__(self):
        return "/nonexistent/scripts/download_ztk_binaries.sh"
