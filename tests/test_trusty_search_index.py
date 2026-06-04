"""Unit tests for trusty-search index freshness helpers (GitHub #649).

Why: At startup we want the daemon's OWN view of this project's index so we can
fire a BACKGROUND reindex when it is missing/empty/stale — without git/mtime
scanning. These tests pin the resolution, freshness classification, and the
non-blocking reindex trigger, all of which must be fail-open and never block.

What: Exercises ``_index_id_candidates``, ``_fetch_index_status``,
``get_trusty_search_index_status``, ``is_index_missing_or_empty``,
``is_index_stale`` and ``trigger_trusty_search_reindex`` against a mocked daemon
HTTP layer.

Test: ``uv run pytest tests/test_trusty_search_index.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.claude_mpm.services import trusty_status
from src.claude_mpm.services.trusty_status import (
    _index_id_candidates,
    get_trusty_search_index_status,
    is_index_missing_or_empty,
    is_index_stale,
    trigger_trusty_search_reindex,
)

CWD = Path("/Volumes/SSD1/Projects/claude-mpm")


def _fresh_status(index_id: str = "claude-mpm", root: str = str(CWD)) -> dict:
    """A healthy, populated index status payload (mirrors the daemon shape)."""
    return {
        "index_id": index_id,
        "chunk_count": 65225,
        "root_path": root,
        "last_walk_error": None,
        "status": "ready",
    }


class TestIndexIdCandidates:
    """Why: ID resolution drives every probe; the override must win and the two
    derived forms must both be tried without duplicates."""

    def test_basename_and_path_derived(self):
        cands = _index_id_candidates(CWD)
        assert cands == ["claude-mpm", "Volumes_SSD1_Projects_claude-mpm"]

    def test_config_override_leads(self, monkeypatch):
        monkeypatch.setattr(
            trusty_status,
            "_load_config",
            lambda: {"trusty_search": {"index_id": "my-custom-id"}},
        )
        cands = _index_id_candidates(CWD)
        assert cands[0] == "my-custom-id"
        assert "claude-mpm" in cands

    def test_dedup_when_basename_equals_override(self, monkeypatch):
        monkeypatch.setattr(
            trusty_status,
            "_load_config",
            lambda: {"trusty_search": {"index_id": "claude-mpm"}},
        )
        cands = _index_id_candidates(CWD)
        assert cands.count("claude-mpm") == 1


class _FakeResp:
    """Minimal context-manager stand-in for urlopen's HTTPResponse."""

    def __init__(self, status: int, body: dict | None):
        self.status = status
        self._body = json.dumps(body).encode() if body is not None else b""

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _patch_urlopen(monkeypatch, handler):
    """Patch urllib.request.urlopen with ``handler(url, method) -> _FakeResp``."""
    import urllib.request

    def _fake(req, timeout=None):
        return handler(req.full_url, req.get_method())

    monkeypatch.setattr(urllib.request, "urlopen", _fake)


class TestFetchAndResolve:
    """Why: Resolution must confirm root_path matches CWD and fail-safe to None."""

    def test_first_candidate_matches(self, monkeypatch):
        monkeypatch.setattr(Path, "cwd", lambda: CWD)
        monkeypatch.setattr(trusty_status, "_load_config", dict)

        def handler(url, method):
            assert method == "GET"
            assert url.endswith("/indexes/claude-mpm/status")
            return _FakeResp(200, _fresh_status())

        _patch_urlopen(monkeypatch, handler)
        status = get_trusty_search_index_status()
        assert status is not None
        assert status["index_id"] == "claude-mpm"

    def test_root_path_mismatch_skipped(self, monkeypatch):
        monkeypatch.setattr(Path, "cwd", lambda: CWD)
        monkeypatch.setattr(trusty_status, "_load_config", dict)
        # Both candidates resolve, but only the SECOND has the matching root_path.
        responses = {
            "claude-mpm": _fresh_status(root="/some/other/project"),
            "Volumes_SSD1_Projects_claude-mpm": _fresh_status(
                index_id="Volumes_SSD1_Projects_claude-mpm"
            ),
        }

        def handler(url, method):
            cid = url.split("/indexes/")[1].split("/status")[0]
            return _FakeResp(200, responses[cid])

        _patch_urlopen(monkeypatch, handler)
        status = get_trusty_search_index_status()
        assert status is not None
        assert status["index_id"] == "Volumes_SSD1_Projects_claude-mpm"

    def test_all_miss_returns_none(self, monkeypatch):
        monkeypatch.setattr(Path, "cwd", lambda: CWD)
        monkeypatch.setattr(trusty_status, "_load_config", dict)
        _patch_urlopen(monkeypatch, lambda url, method: _FakeResp(404, None))
        assert get_trusty_search_index_status() is None

    def test_daemon_error_returns_none(self, monkeypatch):
        monkeypatch.setattr(Path, "cwd", lambda: CWD)
        monkeypatch.setattr(trusty_status, "_load_config", dict)

        def boom(req, timeout=None):
            raise OSError("connection refused")

        import urllib.request

        monkeypatch.setattr(urllib.request, "urlopen", boom)
        assert get_trusty_search_index_status() is None  # fail-safe, no raise


class TestFreshnessClassification:
    """Why: The note/reindex decision hinges on correct missing/empty/stale
    classification from the daemon's OWN signals (no git scanning)."""

    def test_missing_or_empty(self):
        assert is_index_missing_or_empty(None) is True
        assert is_index_missing_or_empty({"chunk_count": 0}) is True
        assert is_index_missing_or_empty({}) is True
        assert is_index_missing_or_empty(_fresh_status()) is False

    def test_stale_signals(self):
        # Healthy populated index → not stale.
        assert is_index_stale(_fresh_status()) is False
        # Daemon reported a walk error → stale.
        st = _fresh_status()
        st["last_walk_error"] = "permission denied"
        assert is_index_stale(st) is True
        # Non-terminal/unhealthy status field → stale.
        st = _fresh_status()
        st["status"] = "error"
        assert is_index_stale(st) is True
        # Empty index is NOT double-counted as stale (deferred to missing/empty).
        assert is_index_stale({"chunk_count": 0}) is False
        assert is_index_stale(None) is False


class TestReindexTrigger:
    """Why: The reindex MUST be non-blocking and fail-open — it can never delay
    or crash startup."""

    def test_dispatches_thread_and_returns_immediately(self, monkeypatch):
        captured: dict = {}

        class _FakeThread:
            def __init__(self, target=None, daemon=None):
                captured["target"] = target
                captured["daemon"] = daemon

            def start(self):
                captured["started"] = True

        import threading

        monkeypatch.setattr(threading, "Thread", _FakeThread)
        ok = trigger_trusty_search_reindex("claude-mpm")
        assert ok is True
        assert captured["started"] is True
        assert captured["daemon"] is True  # detached, never joins startup

    def test_posts_correct_url_inside_thread(self, monkeypatch):
        calls: list = []

        def handler(url, method):
            calls.append((url, method))
            return _FakeResp(200, {"queued": True})

        _patch_urlopen(monkeypatch, handler)
        # Run synchronously by making Thread.start() call the target immediately.
        import threading

        class _ImmediateThread:
            def __init__(self, target=None, daemon=None):
                self._target = target

            def start(self):
                self._target()

        monkeypatch.setattr(threading, "Thread", _ImmediateThread)
        ok = trigger_trusty_search_reindex("claude-mpm")
        assert ok is True
        assert len(calls) == 1
        url, method = calls[0]
        assert url.endswith("/indexes/claude-mpm/reindex")
        assert method == "POST"

    def test_thread_error_does_not_propagate(self, monkeypatch):
        def boom(req, timeout=None):
            raise OSError("daemon busy")

        import threading
        import urllib.request

        monkeypatch.setattr(urllib.request, "urlopen", boom)

        class _ImmediateThread:
            def __init__(self, target=None, daemon=None):
                self._target = target

            def start(self):
                self._target()  # would raise if the inner POST were unguarded

        monkeypatch.setattr(threading, "Thread", _ImmediateThread)
        # Must not raise: the inner _post swallows everything.
        assert trigger_trusty_search_reindex("claude-mpm") is True

    def test_dispatch_failure_returns_false(self, monkeypatch):
        import threading

        class _BadThread:
            def __init__(self, *a, **k):
                pass

            def start(self):
                raise RuntimeError("cannot start thread")

        monkeypatch.setattr(threading, "Thread", _BadThread)
        assert trigger_trusty_search_reindex("claude-mpm") is False


def test_resolve_latency_bounded(monkeypatch):
    """Why: Startup-path budget — resolution must probe at most ONE request per
    candidate and never loop unboundedly. A flat wall-clock assertion is fragile
    (CI machines vary widely and the mock has zero latency). Instead we assert
    that the number of urlopen calls is exactly bounded by the number of
    candidates, which directly guards against accidentally-added unbounded loops
    or O(n²) probing strategies.

    What: With two candidates (basename + path-derived) the mock should be called
    at most twice; the call count is a deterministic, fast, and stable guard.

    Test: monkeypatch records every urlopen call; assert count <= len(candidates).
    """
    monkeypatch.setattr(Path, "cwd", lambda: CWD)
    monkeypatch.setattr(trusty_status, "_load_config", dict)

    call_count = 0

    def counting_handler(url, method):
        nonlocal call_count
        call_count += 1
        return _FakeResp(404, None)

    _patch_urlopen(monkeypatch, counting_handler)

    result = get_trusty_search_index_status()
    assert result is None

    expected_candidates = len(_index_id_candidates(CWD))
    assert expected_candidates > 0, "test invariant: CWD must have ≥1 candidate"
    assert call_count <= expected_candidates, (
        f"probed {call_count} times but only {expected_candidates} candidates exist — "
        "unbounded probing detected"
    )
