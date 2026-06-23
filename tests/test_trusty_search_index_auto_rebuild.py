"""Unit tests for trusty-search index auto-rebuild wait/background logic (#899).

Why: The index auto-rebuild feature must estimate file count and decide whether
to BLOCK (wait for rebuild, small repo) or BACKGROUND (fire-and-forget, large
repo or disabled). These tests cover all new helpers and the framework_loader
decision wiring without real network calls or a running daemon.

What: Exercises:
- ``estimate_index_file_count``: git path, fallback scandir, early-exit cap,
  total failure → 0.
- ``wait_for_index_ready``: returns True when status becomes ready; returns
  False on deadline timeout; never exceeds deadline.
- ``get_auto_rebuild_config``: defaults when config absent; overrides present.
- Decision logic in ``_trusty_search_index_note``: small repo → waits; large
  repo → backgrounds; disabled → backgrounds.

Test: ``uv run pytest tests/test_trusty_search_index_auto_rebuild.py``.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader
from claude_mpm.services import trusty_status
from claude_mpm.services.trusty_status import (
    estimate_index_file_count,
    get_auto_rebuild_config,
    wait_for_index_ready,
)

# ---------------------------------------------------------------------------
# Helpers shared by multiple test classes
# ---------------------------------------------------------------------------


def _stub_loader():
    """Minimal stand-in exposing what the freshness methods touch."""
    return SimpleNamespace(
        logger=logging.getLogger("test_auto_rebuild"),
        _resolve_reindex_id=FrameworkLoader._resolve_reindex_id,
    )


def _fresh_status(index_id: str = "claude-mpm", chunk_count: int = 65225) -> dict:
    return {
        "index_id": index_id,
        "chunk_count": chunk_count,
        "root_path": "/Volumes/SSD1/Projects/claude-mpm",
        "last_walk_error": None,
        "status": "ready",
    }


# ---------------------------------------------------------------------------
# TestGetAutoRebuildConfig
# ---------------------------------------------------------------------------


class TestGetAutoRebuildConfig:
    def test_defaults_when_config_absent(self, monkeypatch):
        """No config file → all defaults returned."""
        monkeypatch.setattr(trusty_status, "_load_config", dict)
        cfg = get_auto_rebuild_config()
        assert cfg["enabled"] is True
        assert cfg["max_wait_seconds"] == 5.0
        assert cfg["wait_threshold_files"] == 1500

    def test_overrides_from_config(self, monkeypatch):
        """Config values override defaults."""
        monkeypatch.setattr(
            trusty_status,
            "_load_config",
            lambda: {
                "trusty_search": {
                    "auto_rebuild": {
                        "enabled": False,
                        "max_wait_seconds": 10.0,
                        "wait_threshold_files": 500,
                    }
                }
            },
        )
        cfg = get_auto_rebuild_config()
        assert cfg["enabled"] is False
        assert cfg["max_wait_seconds"] == 10.0
        assert cfg["wait_threshold_files"] == 500

    def test_partial_override(self, monkeypatch):
        """Only some knobs specified → missing ones stay at defaults."""
        monkeypatch.setattr(
            trusty_status,
            "_load_config",
            lambda: {"trusty_search": {"auto_rebuild": {"max_wait_seconds": 2.0}}},
        )
        cfg = get_auto_rebuild_config()
        assert cfg["enabled"] is True
        assert cfg["max_wait_seconds"] == 2.0
        assert cfg["wait_threshold_files"] == 1500

    def test_missing_trusty_search_section(self, monkeypatch):
        """Config has no trusty_search key → full defaults."""
        monkeypatch.setattr(
            trusty_status, "_load_config", lambda: {"other_section": {}}
        )
        cfg = get_auto_rebuild_config()
        assert cfg["enabled"] is True

    def test_non_positive_wait_seconds_defaults(self, monkeypatch):
        """max_wait_seconds <= 0 → falls back to default."""
        monkeypatch.setattr(
            trusty_status,
            "_load_config",
            lambda: {"trusty_search": {"auto_rebuild": {"max_wait_seconds": -1}}},
        )
        cfg = get_auto_rebuild_config()
        assert cfg["max_wait_seconds"] == 5.0

    def test_bad_type_falls_back(self, monkeypatch):
        """Non-dict auto_rebuild → full defaults."""
        monkeypatch.setattr(
            trusty_status,
            "_load_config",
            lambda: {"trusty_search": {"auto_rebuild": "broken"}},
        )
        cfg = get_auto_rebuild_config()
        assert cfg["enabled"] is True
        assert cfg["max_wait_seconds"] == 5.0
        assert cfg["wait_threshold_files"] == 1500

    def test_load_config_raises(self, monkeypatch):
        """Exception from _load_config → all defaults (fail-safe)."""

        def _boom():
            raise RuntimeError("disk error")

        monkeypatch.setattr(trusty_status, "_load_config", _boom)
        cfg = get_auto_rebuild_config()
        assert cfg["enabled"] is True


# ---------------------------------------------------------------------------
# TestEstimateIndexFileCount
# ---------------------------------------------------------------------------


class TestEstimateIndexFileCount:
    def test_git_path_success(self, tmp_path):
        """Git ls-files success → line count returned."""
        file_list = "a.py\nb.py\nc.py\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=file_list, stderr="")
            count = estimate_index_file_count(tmp_path)
        assert count == 3
        # Verify git -C was used (no chdir)
        args = mock_run.call_args[0][0]
        assert args[0] == "git"
        assert args[1] == "-C"
        assert str(tmp_path) in args

    def test_git_nonzero_falls_back_to_scandir(self, tmp_path):
        """Non-zero git exit → scandir fallback; file count matches files created."""
        # Create 3 files directly in tmp_path (no subdirs to confuse the walk)
        for i in range(3):
            (tmp_path / f"file{i}.txt").write_text("x")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="")
            count = estimate_index_file_count(tmp_path)
        assert count == 3

    def test_git_timeout_falls_back_to_scandir(self, tmp_path):
        """Subprocess timeout → scandir fallback."""
        import subprocess

        (tmp_path / "file.py").write_text("x")
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 2)):
            count = estimate_index_file_count(tmp_path)
        assert count == 1

    def test_skips_heavy_dirs(self, tmp_path):
        """node_modules, .venv, .git, etc. are skipped."""
        (tmp_path / "src.py").write_text("x")
        for skip_dir in ("node_modules", ".venv", ".git", "__pycache__"):
            d = tmp_path / skip_dir
            d.mkdir()
            (d / "heavy_file.js").write_text("x")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
            count = estimate_index_file_count(tmp_path)
        # Only src.py should be counted
        assert count == 1

    def test_early_exit_cap(self, tmp_path, monkeypatch):
        """Early-exit cap: stops counting once count > threshold."""
        # Create many files — more than the cap
        num_files = 20
        for i in range(num_files):
            (tmp_path / f"f{i}.py").write_text("x")

        # Set threshold very low via config mock
        monkeypatch.setattr(
            trusty_status,
            "_load_config",
            lambda: {"trusty_search": {"auto_rebuild": {"wait_threshold_files": 5}}},
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
            count = estimate_index_file_count(tmp_path)

        # Should have stopped at cap (threshold + 1 = 6)
        assert count <= 6  # early exit at cap

    def test_total_failure_returns_zero(self):
        """Non-existent path and subprocess exception → 0."""
        with patch("subprocess.run", side_effect=Exception("boom")):
            count = estimate_index_file_count(Path("/nonexistent/path/xyz"))
        assert count == 0

    def test_empty_git_output_returns_zero(self, tmp_path):
        """Empty git ls-files output (new repo with no committed files) → 0."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            count = estimate_index_file_count(tmp_path)
        assert count == 0


# ---------------------------------------------------------------------------
# TestWaitForIndexReady
# ---------------------------------------------------------------------------


class TestWaitForIndexReady:
    def test_returns_true_when_index_becomes_ready(self, monkeypatch):
        """Status flips from missing to ready on the 2nd poll → True."""
        call_count = [0]

        def _status(cwd=None):
            call_count[0] += 1
            if call_count[0] < 2:
                return None  # still indexing
            return _fresh_status()

        monkeypatch.setattr(trusty_status, "get_trusty_search_index_status", _status)
        monkeypatch.setattr(
            trusty_status, "_post_reindex_sync", lambda index_id, base_url: None
        )

        result = wait_for_index_ready("claude-mpm", max_wait_seconds=5.0)
        assert result is True

    def test_returns_false_on_timeout(self, monkeypatch):
        """Status never becomes ready → returns False without raising."""
        monkeypatch.setattr(
            trusty_status, "get_trusty_search_index_status", lambda cwd=None: None
        )
        monkeypatch.setattr(
            trusty_status, "_post_reindex_sync", lambda index_id, base_url: None
        )

        start = time.monotonic()
        result = wait_for_index_ready("claude-mpm", max_wait_seconds=0.3)
        elapsed = time.monotonic() - start

        assert result is False
        # Should not block significantly beyond the deadline (1s tolerance for CI)
        assert elapsed < 1.5

    def test_never_exceeds_deadline(self, monkeypatch):
        """Deadline is wall-clock bounded (monotonic), not a sum of sleeps."""
        status_calls = [0]

        def _slow_status(cwd=None):
            status_calls[0] += 1

        monkeypatch.setattr(
            trusty_status, "get_trusty_search_index_status", _slow_status
        )
        monkeypatch.setattr(
            trusty_status, "_post_reindex_sync", lambda index_id, base_url: None
        )

        deadline = 0.4
        start = time.monotonic()
        result = wait_for_index_ready("claude-mpm", max_wait_seconds=deadline)
        elapsed = time.monotonic() - start

        assert result is False
        # At most 1.5s grace over the deadline (accounting for slow CI)
        assert elapsed < deadline + 1.5

    def test_exception_returns_false(self, monkeypatch):
        """Any exception inside the function → False, no raise."""
        monkeypatch.setattr(
            trusty_status,
            "get_trusty_search_index_status",
            lambda cwd=None: (_ for _ in ()).throw(OSError("daemon down")),
        )
        result = wait_for_index_ready("claude-mpm", max_wait_seconds=1.0)
        assert result is False

    def test_triggers_reindex_post(self, monkeypatch):
        """wait_for_index_ready issues a reindex POST before polling."""
        posted = []

        def _mock_post(index_id, base_url):
            posted.append(index_id)

        monkeypatch.setattr(trusty_status, "_post_reindex_sync", _mock_post)
        monkeypatch.setattr(
            trusty_status,
            "get_trusty_search_index_status",
            lambda cwd=None: _fresh_status(),
        )

        wait_for_index_ready("my-index", max_wait_seconds=2.0)
        assert posted == ["my-index"]


# ---------------------------------------------------------------------------
# TestDecisionLogicInNote
# ---------------------------------------------------------------------------


class TestDecisionLogicInNote:
    """Verify _trusty_search_index_note makes the right wait/background decision."""

    def _patch_all(
        self,
        monkeypatch,
        *,
        status,
        missing: bool,
        stale: bool,
        file_count: int,
        wait_result: bool,
        auto_link_disabled: bool = False,
        auto_rebuild_enabled: bool = True,
        threshold: int = 1500,
        max_wait: float = 5.0,
    ):
        """Patch all trusty_status helpers so no real daemon/network is touched."""
        triggered_bg: list[str] = []
        waited: list[str] = []

        monkeypatch.setattr(
            trusty_status, "get_trusty_search_index_status", lambda cwd=None: status
        )
        monkeypatch.setattr(
            trusty_status, "is_index_missing_or_empty", lambda s: missing
        )
        monkeypatch.setattr(trusty_status, "is_index_stale", lambda s: stale)
        monkeypatch.setattr(
            trusty_status,
            "trigger_trusty_search_reindex",
            lambda index_id, cwd=None: triggered_bg.append(index_id) or True,
        )
        monkeypatch.setattr(
            trusty_status,
            "estimate_index_file_count",
            lambda cwd: file_count,
        )
        monkeypatch.setattr(
            trusty_status,
            "wait_for_index_ready",
            lambda index_id, cwd=None, max_wait_seconds=5.0: (
                waited.append(index_id) or wait_result
            ),
        )
        monkeypatch.setattr(
            trusty_status,
            "get_auto_rebuild_config",
            lambda: {
                "enabled": auto_rebuild_enabled,
                "max_wait_seconds": max_wait,
                "wait_threshold_files": threshold,
            },
        )
        monkeypatch.setattr(
            trusty_status,
            "_is_auto_link_disabled",
            lambda: auto_link_disabled,
        )
        return triggered_bg, waited

    def test_small_repo_waits_and_ready(self, monkeypatch):
        """Small repo + wait returns True → 'was rebuilt and is ready'."""
        triggered, waited = self._patch_all(
            monkeypatch,
            status={"index_id": "proj", "chunk_count": 0},
            missing=True,
            stale=False,
            file_count=100,
            wait_result=True,
            threshold=1500,
        )
        note = FrameworkLoader._trusty_search_index_note(_stub_loader())
        assert "was rebuilt and is ready" in note
        assert waited == ["proj"]
        assert triggered == []  # blocking wait was used, not background

    def test_small_repo_waits_but_times_out(self, monkeypatch):
        """Small repo + wait returns False → 'rebuilding in the background'."""
        _triggered, waited = self._patch_all(
            monkeypatch,
            status={"index_id": "proj", "chunk_count": 0},
            missing=True,
            stale=False,
            file_count=100,
            wait_result=False,
        )
        note = FrameworkLoader._trusty_search_index_note(_stub_loader())
        assert "rebuilding in the background" in note
        assert "incomplete this turn" in note
        assert waited == ["proj"]

    def test_large_repo_backgrounds(self, monkeypatch):
        """Large repo (count > threshold) → background + '(large repo)' note."""
        triggered, waited = self._patch_all(
            monkeypatch,
            status={"index_id": "proj", "chunk_count": 0},
            missing=True,
            stale=False,
            file_count=5000,
            wait_result=False,
            threshold=1500,
        )
        note = FrameworkLoader._trusty_search_index_note(_stub_loader())
        assert "large repo" in note
        assert "background" in note
        assert triggered == ["proj"]
        assert waited == []  # no wait for large repo

    def test_stale_large_repo_backgrounds(self, monkeypatch):
        """Stale index + large repo → background with large repo note."""
        triggered, waited = self._patch_all(
            monkeypatch,
            status={"index_id": "proj", "chunk_count": 100, "status": "error"},
            missing=False,
            stale=True,
            file_count=9999,
            wait_result=False,
            threshold=1500,
        )
        note = FrameworkLoader._trusty_search_index_note(_stub_loader())
        assert "large repo" in note
        assert triggered == ["proj"]
        assert waited == []

    def test_auto_link_disabled_backgrounds(self, monkeypatch):
        """Auto-link disabled → always backgrounds (no wait)."""
        triggered, waited = self._patch_all(
            monkeypatch,
            status={"index_id": "proj", "chunk_count": 0},
            missing=True,
            stale=False,
            file_count=50,
            wait_result=True,
            auto_link_disabled=True,
        )
        note = FrameworkLoader._trusty_search_index_note(_stub_loader())
        # Should background, not wait
        assert "background" in note
        assert triggered == ["proj"]
        assert waited == []

    def test_auto_rebuild_disabled_backgrounds(self, monkeypatch):
        """auto_rebuild.enabled=False → always backgrounds."""
        triggered, waited = self._patch_all(
            monkeypatch,
            status={"index_id": "proj", "chunk_count": 0},
            missing=True,
            stale=False,
            file_count=50,
            wait_result=True,
            auto_rebuild_enabled=False,
        )
        note = FrameworkLoader._trusty_search_index_note(_stub_loader())
        assert "background" in note
        assert triggered == ["proj"]
        assert waited == []

    def test_fresh_index_no_note(self, monkeypatch):
        """Fresh index → empty note, no rebuild triggered."""
        triggered, waited = self._patch_all(
            monkeypatch,
            status=_fresh_status(),
            missing=False,
            stale=False,
            file_count=100,
            wait_result=False,
        )
        note = FrameworkLoader._trusty_search_index_note(_stub_loader())
        assert note == ""
        assert triggered == []
        assert waited == []

    def test_exception_fails_open(self, monkeypatch):
        """Any exception in the freshness path → empty note, no raise."""

        def _boom(cwd=None):
            raise OSError("daemon unreachable")

        monkeypatch.setattr(trusty_status, "get_trusty_search_index_status", _boom)
        note = FrameworkLoader._trusty_search_index_note(_stub_loader())
        assert note == ""
