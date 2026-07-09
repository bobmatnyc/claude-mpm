"""Tests for stdio-MCP cleanup in SessionPauseManager (issue #927).

WHAT: Exercises ``SessionPauseManager._terminate_mcp_servers()`` and its
integration into ``create_pause_session()`` — recorded PIDs are SIGTERM'd only
when the live command line still matches, recycled PIDs are skipped, failures
never propagate, and pause always succeeds.

WHY: Killing the wrong process (a recycled PID, or the shared HTTP daemon) is a
correctness/safety hazard.  These tests mock the process table + signal path so
the validation gates are verified deterministically.

    uv run pytest -p no:xdist tests/test_session_pause_mcp_cleanup.py -v
"""

from __future__ import annotations

import json
import os
import signal
from pathlib import Path  # noqa: TC003 - used at runtime in signatures

import pytest  # noqa: TC002 - used at runtime as fixture type annotation

from claude_mpm.services.cli import mcp_process_tracker as tracker
from claude_mpm.services.cli.session_pause_manager import SessionPauseManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_pid_record(
    project_dir: Path, session_id: str, processes: list[dict]
) -> Path:
    """Write an mcp-pids record file directly (bypassing discovery)."""
    pid_dir = project_dir / ".claude-mpm"
    pid_dir.mkdir(parents=True, exist_ok=True)
    path = pid_dir / f"mcp-pids-{session_id}.json"
    path.write_text(
        json.dumps(
            {
                "session_id": session_id,
                "project_dir": str(project_dir),
                "captured_at": "2026-01-01T00:00:00+00:00",
                "processes": processes,
            }
        )
    )
    return path


class _KillRecorder:
    """Captures os.kill(pid, sig) calls in place of the real signal."""

    def __init__(self) -> None:
        self.calls: list[tuple[int, int]] = []

    def __call__(self, pid: int, sig: int) -> None:
        self.calls.append((pid, sig))


# ---------------------------------------------------------------------------
# Termination gates
# ---------------------------------------------------------------------------


def test_terminate_signals_matching_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pid_record(
        tmp_path,
        "s1",
        [
            {
                "pid": 4242,
                "cmdline": "trusty-memory serve --stdio",
                "signature": "trusty-memory serve --stdio",
            }
        ],
    )

    monkeypatch.setattr(tracker, "process_is_alive", lambda _pid: True)
    monkeypatch.setattr(
        tracker, "get_process_cmdline", lambda _pid: "trusty-memory serve --stdio"
    )
    killer = _KillRecorder()
    monkeypatch.setattr(os, "kill", killer)

    mgr = SessionPauseManager(project_path=tmp_path)
    summary = mgr._terminate_mcp_servers()

    assert summary["terminated"] == 1
    assert summary["skipped"] == 0
    # Exactly one SIGTERM (never SIGKILL) to the recorded PID.
    assert killer.calls == [(4242, signal.SIGTERM)]
    # Record file consumed.
    assert tracker.iter_pid_files(tmp_path) == []


def test_terminate_uses_sigterm_not_sigkill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pid_record(
        tmp_path,
        "s1",
        [
            {
                "pid": 55,
                "cmdline": "trusty-memory serve --stdio",
                "signature": "trusty-memory serve --stdio",
            }
        ],
    )
    monkeypatch.setattr(tracker, "process_is_alive", lambda _pid: True)
    monkeypatch.setattr(
        tracker, "get_process_cmdline", lambda _pid: "trusty-memory serve --stdio"
    )
    killer = _KillRecorder()
    monkeypatch.setattr(os, "kill", killer)

    SessionPauseManager(project_path=tmp_path)._terminate_mcp_servers()

    assert all(sig == signal.SIGTERM for _pid, sig in killer.calls)
    assert all(sig != signal.SIGKILL for _pid, sig in killer.calls)


def test_terminate_skips_recycled_pid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pid_record(
        tmp_path,
        "s1",
        [
            {
                "pid": 4242,
                "cmdline": "trusty-memory serve --stdio",
                "signature": "trusty-memory serve --stdio",
            }
        ],
    )

    monkeypatch.setattr(tracker, "process_is_alive", lambda _pid: True)
    # PID is alive but now belongs to something unrelated (recycled).
    monkeypatch.setattr(
        tracker, "get_process_cmdline", lambda _pid: "/usr/bin/python somethingelse"
    )
    killer = _KillRecorder()
    monkeypatch.setattr(os, "kill", killer)

    summary = SessionPauseManager(project_path=tmp_path)._terminate_mcp_servers()

    assert summary["terminated"] == 0
    assert summary["skipped"] == 1
    # Critically: no signal sent to the recycled PID.
    assert killer.calls == []


def test_terminate_skips_dead_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pid_record(
        tmp_path,
        "s1",
        [
            {
                "pid": 999,
                "cmdline": "trusty-memory serve --stdio",
                "signature": "trusty-memory serve --stdio",
            }
        ],
    )
    monkeypatch.setattr(tracker, "process_is_alive", lambda _pid: False)
    killer = _KillRecorder()
    monkeypatch.setattr(os, "kill", killer)

    summary = SessionPauseManager(project_path=tmp_path)._terminate_mcp_servers()

    assert summary["terminated"] == 0
    assert summary["skipped"] == 1
    assert killer.calls == []


def test_terminate_no_records_is_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    killer = _KillRecorder()
    monkeypatch.setattr(os, "kill", killer)
    summary = SessionPauseManager(project_path=tmp_path)._terminate_mcp_servers()
    assert summary == {
        "terminated": 0,
        "skipped": 0,
        "files_processed": 0,
        "processes": [],
    }
    assert killer.calls == []


def test_terminate_removes_corrupt_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid_dir = tmp_path / ".claude-mpm"
    pid_dir.mkdir(parents=True)
    bad = pid_dir / "mcp-pids-bad.json"
    bad.write_text("{not valid json")

    summary = SessionPauseManager(project_path=tmp_path)._terminate_mcp_servers()
    assert summary["files_processed"] == 1
    # Corrupt record cleaned up so it does not accumulate.
    assert not bad.exists()


# ---------------------------------------------------------------------------
# Integration: pause must succeed even if MCP cleanup blows up
# ---------------------------------------------------------------------------


def test_create_pause_session_survives_mcp_cleanup_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mgr = SessionPauseManager(project_path=tmp_path)

    def _boom() -> dict:
        raise RuntimeError("simulated MCP cleanup failure")

    monkeypatch.setattr(mgr, "_terminate_mcp_servers", _boom)

    # prune_worktrees=False keeps the test hermetic (no git needed).
    session_id = mgr.create_pause_session(message="test", prune_worktrees=False)

    assert session_id.startswith("session-")
    # Session artifacts were still written despite the cleanup blowing up.
    assert (mgr.pause_dir / f"{session_id}.json").exists()
    assert (mgr.pause_dir / f"{session_id}.md").exists()


def test_create_pause_session_invokes_mcp_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mgr = SessionPauseManager(project_path=tmp_path)

    called = {"hit": False}

    def _fake() -> dict:
        called["hit"] = True
        return {"terminated": 0, "skipped": 0, "files_processed": 0, "processes": []}

    monkeypatch.setattr(mgr, "_terminate_mcp_servers", _fake)

    mgr.create_pause_session(message="test", prune_worktrees=False)
    assert called["hit"] is True
