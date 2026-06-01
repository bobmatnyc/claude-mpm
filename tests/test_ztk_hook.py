"""Tests for the ztk PreToolUse hook (src/claude_mpm/hooks/ztk_hook.py).

Focus: the #573/#587 "Bash stdout-drop" root cause and its fix.

The bundled ztk binary ships as a 0-byte placeholder (gitignored, populated
only at release). The old resolver gated only on is_file() + exec-bit, so a
0-byte binary was accepted and every Bash command was rewritten to
``<ztk> run <cmd>`` — running an empty binary that exits 0 with EMPTY stdout,
silently swallowing all command output.

These tests assert the hardened behaviour:
  * 0-byte / missing / non-functional binary -> resolver returns None ->
    build_ztk_response passes the command through UNCHANGED (no rewrite).
  * A functional ztk stub (echoes its args back) -> verified True -> command
    rewritten to ``<stub> run <cmd>``.
  * A broken ztk stub (exit 0, empty stdout) -> verified False -> passthrough.
  * Compound / piped commands (&&, ||, ;, |, newline) -> passthrough.
  * The functional self-test is cached by binary mtime/size and not re-run when
    the binary is unchanged.
"""

from __future__ import annotations

import os
import stat
from typing import TYPE_CHECKING

import pytest

from claude_mpm.hooks import ztk_hook

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    """Redirect the verify cache to a temp dir and clear process-local memo.

    Also ensures CLAUDE_MPM_DISABLE_ZTK is unset so we exercise the real path.
    """
    cache = tmp_path / "ztk-verify-cache.json"
    monkeypatch.setattr(ztk_hook, "_MPM_LOG_DIR", tmp_path)
    monkeypatch.setattr(ztk_hook, "_VERIFY_CACHE", cache)
    monkeypatch.setattr(ztk_hook, "_MPM_ZTK_LOG", tmp_path / "ztk-savings.log")
    ztk_hook._RESOLVE_MEMO.clear()
    ztk_hook._WARNED_NONFUNCTIONAL = False
    monkeypatch.delenv("CLAUDE_MPM_DISABLE_ZTK", raising=False)
    yield


def _make_exec(path: Path, body: str) -> Path:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def _working_ztk(path: Path) -> Path:
    """A stub that round-trips output: ``ztk run echo X`` prints X.

    Implemented as a shell script that drops the leading ``run`` arg and execs
    the remaining command, so stdout passes through (the real ztk contract).
    """
    return _make_exec(
        path,
        '#!/bin/sh\nshift\nexec "$@"\n',  # drop "run", exec the wrapped command
    )


def _broken_ztk(path: Path) -> Path:
    """A stub that mimics the failure mode: exit 0 with EMPTY stdout."""
    return _make_exec(path, "#!/bin/sh\nexit 0\n")


def _bash_event(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def _force_candidate(monkeypatch, path: Path | None) -> None:
    """Make _resolve_ztk consider exactly `path` (no system/bundled lookup)."""
    monkeypatch.setattr(ztk_hook.shutil, "which", lambda _name: None)

    class _Bundled:
        def joinpath(self, *_parts):
            # Point the bundled lookup at our stub (or a nonexistent path).
            return str(path) if path is not None else "/nonexistent/ztk"

    monkeypatch.setattr(ztk_hook.resources, "files", lambda _pkg: _Bundled())


# ---------------------------------------------------------------------------
# verify_ztk_binary
# ---------------------------------------------------------------------------
def test_verify_working_binary_true(tmp_path):
    ztk = _working_ztk(tmp_path / "ztk")
    assert ztk_hook.verify_ztk_binary(str(ztk)) is True


def test_verify_broken_binary_false(tmp_path):
    ztk = _broken_ztk(tmp_path / "ztk")
    assert ztk_hook.verify_ztk_binary(str(ztk)) is False


def test_verify_zero_byte_binary_false(tmp_path):
    empty = tmp_path / "ztk"
    empty.touch()
    empty.chmod(empty.stat().st_mode | stat.S_IXUSR)
    # 0-byte cannot exec meaningfully -> self-test fails.
    assert ztk_hook.verify_ztk_binary(str(empty)) is False


# ---------------------------------------------------------------------------
# _resolve_ztk gating
# ---------------------------------------------------------------------------
def test_resolve_zero_byte_bundled_returns_none(tmp_path, monkeypatch):
    """0-byte bundled binary -> None (the core #573 fix)."""
    empty = tmp_path / "ztk"
    empty.touch()
    empty.chmod(empty.stat().st_mode | stat.S_IXUSR)
    _force_candidate(monkeypatch, empty)
    assert ztk_hook._resolve_ztk() is None


def test_resolve_missing_returns_none(tmp_path, monkeypatch):
    _force_candidate(monkeypatch, None)
    assert ztk_hook._resolve_ztk() is None


def test_resolve_working_binary_returns_path(tmp_path, monkeypatch):
    ztk = _working_ztk(tmp_path / "ztk")
    _force_candidate(monkeypatch, ztk)
    assert ztk_hook._resolve_ztk() == str(ztk)


def test_resolve_broken_binary_returns_none(tmp_path, monkeypatch):
    ztk = _broken_ztk(tmp_path / "ztk")
    _force_candidate(monkeypatch, ztk)
    assert ztk_hook._resolve_ztk() is None


# ---------------------------------------------------------------------------
# build_ztk_response: passthrough vs rewrite
# ---------------------------------------------------------------------------
def test_zero_byte_passthrough_no_rewrite(tmp_path, monkeypatch):
    empty = tmp_path / "ztk"
    empty.touch()
    empty.chmod(empty.stat().st_mode | stat.S_IXUSR)
    _force_candidate(monkeypatch, empty)
    resp = ztk_hook.build_ztk_response(_bash_event("git status"))
    assert resp == {"continue": True}
    assert "hookSpecificOutput" not in resp


def test_working_binary_rewrites_command(tmp_path, monkeypatch):
    ztk = _working_ztk(tmp_path / "ztk")
    _force_candidate(monkeypatch, ztk)
    resp = ztk_hook.build_ztk_response(_bash_event("git status"))
    assert "hookSpecificOutput" in resp
    rewritten = resp["hookSpecificOutput"]["updatedInput"]["command"]
    assert rewritten == f"{ztk} run git status"


def test_broken_binary_passthrough(tmp_path, monkeypatch):
    ztk = _broken_ztk(tmp_path / "ztk")
    _force_candidate(monkeypatch, ztk)
    resp = ztk_hook.build_ztk_response(_bash_event("ls -la"))
    assert resp == {"continue": True}


# ---------------------------------------------------------------------------
# Compound / piped commands -> passthrough (partial-output bug fix)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "command",
    [
        "echo a && echo b",
        "echo a || echo b",
        "echo a; echo b",
        "cat file | grep x",
        "echo a\necho b",
    ],
)
def test_compound_commands_passthrough(tmp_path, monkeypatch, command):
    ztk = _working_ztk(tmp_path / "ztk")
    _force_candidate(monkeypatch, ztk)
    resp = ztk_hook.build_ztk_response(_bash_event(command))
    assert resp == {"continue": True}, f"compound command was rewritten: {command!r}"


def test_simple_command_still_rewritten(tmp_path, monkeypatch):
    """Sanity: a single simple command IS still wrapped."""
    ztk = _working_ztk(tmp_path / "ztk")
    _force_candidate(monkeypatch, ztk)
    resp = ztk_hook.build_ztk_response(_bash_event("git diff"))
    assert "hookSpecificOutput" in resp


# ---------------------------------------------------------------------------
# Caching: self-test not re-run when binary unchanged
# ---------------------------------------------------------------------------
def test_verification_cached_not_rerun(tmp_path, monkeypatch):
    ztk = _working_ztk(tmp_path / "ztk")
    calls = {"n": 0}
    real = ztk_hook._run_ztk_selftest

    def _counting(path):
        calls["n"] += 1
        return real(path)

    monkeypatch.setattr(ztk_hook, "_run_ztk_selftest", _counting)

    assert ztk_hook.verify_ztk_binary(str(ztk)) is True
    assert calls["n"] == 1
    # Second call with unchanged binary -> cache hit, no new self-test.
    assert ztk_hook.verify_ztk_binary(str(ztk)) is True
    assert calls["n"] == 1


def test_verification_rerun_when_binary_changes(tmp_path, monkeypatch):
    ztk = _working_ztk(tmp_path / "ztk")
    calls = {"n": 0}
    real = ztk_hook._run_ztk_selftest

    def _counting(path):
        calls["n"] += 1
        return real(path)

    monkeypatch.setattr(ztk_hook, "_run_ztk_selftest", _counting)

    assert ztk_hook.verify_ztk_binary(str(ztk)) is True
    assert calls["n"] == 1
    # Mutate the binary (new size + mtime) -> fingerprint changes -> re-verify.
    ztk.write_text('#!/bin/sh\nshift\nexec "$@"\n# changed\n')
    os.utime(ztk, None)
    assert ztk_hook.verify_ztk_binary(str(ztk)) is True
    assert calls["n"] == 2


# ---------------------------------------------------------------------------
# ztk_status: truthful on/off
# ---------------------------------------------------------------------------
def test_status_off_when_broken(tmp_path, monkeypatch):
    ztk = _broken_ztk(tmp_path / "ztk")
    _force_candidate(monkeypatch, ztk)
    active, reason = ztk_hook.ztk_status()
    assert active is False
    assert reason == "binary present but non-functional"


def test_status_on_when_functional(tmp_path, monkeypatch):
    ztk = _working_ztk(tmp_path / "ztk")
    _force_candidate(monkeypatch, ztk)
    active, reason = ztk_hook.ztk_status()
    assert active is True
    assert reason == "verified functional"


def test_status_off_when_disabled(tmp_path, monkeypatch):
    ztk = _working_ztk(tmp_path / "ztk")
    _force_candidate(monkeypatch, ztk)
    monkeypatch.setenv("CLAUDE_MPM_DISABLE_ZTK", "1")
    active, reason = ztk_hook.ztk_status()
    assert active is False
    assert reason == "disabled via --no-ztk"
