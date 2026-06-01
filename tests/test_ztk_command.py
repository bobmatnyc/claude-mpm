"""Tests for the ``claude-mpm ztk`` command family (cli/commands/ztk.py).

Focus: the version-currency update path. Network access is mocked — these
tests never hit GitHub and never require a real ztk binary.
"""

from __future__ import annotations

import io
import json
import stat
import tarfile
import urllib.error
from datetime import UTC, datetime, timedelta
from pathlib import Path

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


def test_update_missing_script_falls_back_to_python_downloader(monkeypatch, capsys):
    """When shell script missing, _run_update falls back to Python downloader."""
    monkeypatch.setattr(ztk_cmd, "_download_script", lambda: _FakePath(exists=False))

    called_with: list[str] = []

    def _mock_python_download(tag, dest=None):
        called_with.append(tag)
        return 0

    monkeypatch.setattr(ztk_cmd, "_python_download_ztk", _mock_python_download)
    rc = ztk_cmd._run_update("v0.3.0")
    assert rc == 0
    assert called_with == ["v0.3.0"]


def test_update_missing_script_python_downloader_failure(monkeypatch, capsys):
    """When shell script missing and Python downloader fails, returns non-zero."""
    monkeypatch.setattr(ztk_cmd, "_download_script", lambda: _FakePath(exists=False))

    def _mock_fail(tag, dest=None):
        return 1

    monkeypatch.setattr(ztk_cmd, "_python_download_ztk", _mock_fail)
    rc = ztk_cmd._run_update("v0.3.0")
    assert rc == 1


def test_update_missing_script_reports_error(monkeypatch, capsys):
    """Original test: missing script triggers fallback (not immediate error)."""
    monkeypatch.setattr(ztk_cmd, "_download_script", lambda: _FakePath(exists=False))
    # Make Python downloader fail too so we still get rc=1
    monkeypatch.setattr(ztk_cmd, "_python_download_ztk", lambda *_a, **_k: 1)
    args = _Args(ztk_command="update", latest=False)
    rc = ztk_cmd.run_ztk(args)
    assert rc == 1


def _make_ztk_tarball(binary_content: bytes = b"#!/bin/sh\necho ok\n") -> bytes:
    """Build a minimal in-memory tar.gz containing a ``ztk`` binary."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        info = tarfile.TarInfo(name="ztk")
        info.size = len(binary_content)
        info.mode = 0o755
        tf.addfile(info, io.BytesIO(binary_content))
    return buf.getvalue()


def test_python_download_ztk_success(monkeypatch, tmp_path):
    """Pure-Python downloader writes ztk binary when tarball download succeeds."""
    tarball_bytes = _make_ztk_tarball(b'#!/bin/sh\nshift\nexec "$@"\n')

    class _MockResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return tarball_bytes

    monkeypatch.setattr(
        ztk_cmd.urllib.request, "urlopen", lambda *_a, **_k: _MockResp()
    )

    dest = tmp_path / "ztk"
    rc = ztk_cmd._python_download_ztk("v0.3.0", dest=dest)

    assert rc == 0
    assert dest.exists()
    assert dest.stat().st_size > 0
    # Check exec bit
    assert dest.stat().st_mode & stat.S_IXUSR


def test_python_download_ztk_network_failure(monkeypatch, tmp_path):
    """Network failure returns exit code 1, no exception."""

    def _boom(*_a, **_k):
        raise urllib.error.URLError("no network")

    monkeypatch.setattr(ztk_cmd.urllib.request, "urlopen", _boom)
    dest = tmp_path / "ztk"
    rc = ztk_cmd._python_download_ztk("v0.3.0", dest=dest)
    assert rc == 1
    assert not dest.exists()


def test_python_download_ztk_empty_tarball(monkeypatch, tmp_path):
    """Tarball without ztk binary returns exit code 1."""
    # Build a tarball with a differently-named file
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        data = b"not-ztk"
        info = tarfile.TarInfo(name="other_binary")
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    tarball_bytes = buf.getvalue()

    class _MockResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return tarball_bytes

    monkeypatch.setattr(
        ztk_cmd.urllib.request, "urlopen", lambda *_a, **_k: _MockResp()
    )
    dest = tmp_path / "ztk"
    rc = ztk_cmd._python_download_ztk("v0.3.0", dest=dest)
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
