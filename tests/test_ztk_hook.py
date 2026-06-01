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


# ---------------------------------------------------------------------------
# GOAL 1 fail-safe: timeout / hang -> passthrough
# ---------------------------------------------------------------------------
def test_verify_timeout_is_nonfunctional(tmp_path, monkeypatch):
    """A hanging/unreachable binary (TimeoutExpired) -> verify False."""
    import subprocess

    ztk = _working_ztk(tmp_path / "ztk")

    def _raise_timeout(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd="ztk", timeout=ztk_hook._VERIFY_TIMEOUT_S)

    monkeypatch.setattr(ztk_hook.subprocess, "run", _raise_timeout)
    assert ztk_hook.verify_ztk_binary(str(ztk), use_cache=False) is False


def test_verify_oserror_is_nonfunctional(tmp_path, monkeypatch):
    """Any OSError while probing -> verify False (degrade safely)."""
    ztk = _working_ztk(tmp_path / "ztk")

    def _raise_oserror(*_a, **_k):
        raise OSError("exec format error")  # e.g. wrong-arch binary

    monkeypatch.setattr(ztk_hook.subprocess, "run", _raise_oserror)
    assert ztk_hook.verify_ztk_binary(str(ztk), use_cache=False) is False


def test_timeout_binary_passthrough(tmp_path, monkeypatch):
    """End-to-end: a timing-out binary must yield a clean passthrough."""
    import subprocess

    ztk = _working_ztk(tmp_path / "ztk")
    _force_candidate(monkeypatch, ztk)

    def _raise_timeout(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd="ztk", timeout=3.0)

    monkeypatch.setattr(ztk_hook.subprocess, "run", _raise_timeout)
    resp = ztk_hook.build_ztk_response(_bash_event("git status"))
    assert resp == {"continue": True}


def test_build_response_exception_passthrough(tmp_path, monkeypatch):
    """If the impl raises for ANY reason, the guard returns continue=True."""

    def _boom(_event):
        raise RuntimeError("unexpected bug on the hot path")

    monkeypatch.setattr(ztk_hook, "_build_ztk_response_impl", _boom)
    resp = ztk_hook.build_ztk_response(_bash_event("git status"))
    assert resp == {"continue": True}
    assert "hookSpecificOutput" not in resp


# ---------------------------------------------------------------------------
# GOAL 2: version detection + currency
# ---------------------------------------------------------------------------
def _versioned_ztk(path: Path, version: str) -> Path:
    """A working stub that also answers ``--version`` with ``ztk <version>``.

    Round-trips ``run`` like _working_ztk, but prints a version line when the
    first arg is a version flag/subcommand.
    """
    body = (
        "#!/bin/sh\n"
        'case "$1" in\n'
        f'  --version|version|-V|-v) echo "ztk {version}"; exit 0;;\n'
        "esac\n"
        'shift\nexec "$@"\n'
    )
    return _make_exec(path, body)


def test_detect_version_parses_semver(tmp_path):
    ztk = _versioned_ztk(tmp_path / "ztk", "v0.2.1")
    assert ztk_hook.detect_ztk_version(str(ztk), use_cache=False) == "v0.2.1"


def test_detect_version_unparseable_returns_none(tmp_path):
    """A binary with no parseable version -> None (graceful, not an error)."""
    # _working_ztk has no version flag; --version just runs `--version` which
    # the shell stub execs (errors), producing no semver.
    ztk = _working_ztk(tmp_path / "ztk")
    assert ztk_hook.detect_ztk_version(str(ztk), use_cache=False) is None


def test_detect_version_cached(tmp_path, monkeypatch):
    ztk = _versioned_ztk(tmp_path / "ztk", "v0.2.0")
    calls = {"n": 0}
    real = ztk_hook._run_ztk_version_probe

    def _counting(path):
        calls["n"] += 1
        return real(path)

    monkeypatch.setattr(ztk_hook, "_run_ztk_version_probe", _counting)
    assert ztk_hook.detect_ztk_version(str(ztk)) == "v0.2.0"
    assert ztk_hook.detect_ztk_version(str(ztk)) == "v0.2.0"
    assert calls["n"] == 1  # second call served from cache


def test_currency_current_outdated_unknown():
    assert ztk_hook._compute_currency("v0.2.1", "v0.2.1") == "current"
    assert ztk_hook._compute_currency("v0.2.2", "v0.2.1") == "current"
    assert ztk_hook._compute_currency("v0.2.0", "v0.2.1") == "outdated"
    assert ztk_hook._compute_currency(None, "v0.2.1") == "unknown"
    assert ztk_hook._compute_currency("v0.2.1", None) == "unknown"


def test_status_detail_current(tmp_path, monkeypatch):
    ztk = _versioned_ztk(tmp_path / "ztk", "v0.2.1")
    _force_candidate(monkeypatch, ztk)
    monkeypatch.setattr(ztk_hook, "_read_required_version", lambda: "v0.2.1")
    detail = ztk_hook.ztk_status_detail()
    assert detail["active"] is True
    assert detail["installed_version"] == "v0.2.1"
    assert detail["currency"] == "current"


def test_status_detail_outdated_still_active(tmp_path, monkeypatch):
    """An OLD but functional binary stays active; only currency flags outdated."""
    ztk = _versioned_ztk(tmp_path / "ztk", "v0.2.0")
    _force_candidate(monkeypatch, ztk)
    monkeypatch.setattr(ztk_hook, "_read_required_version", lambda: "v0.2.1")
    detail = ztk_hook.ztk_status_detail()
    assert detail["active"] is True  # NEVER disabled over version mismatch
    assert detail["currency"] == "outdated"
    assert detail["installed_version"] == "v0.2.0"
    assert detail["required_version"] == "v0.2.1"


def test_status_detail_unparseable_version(tmp_path, monkeypatch):
    """Functional binary with unknown version -> active, currency unknown."""
    ztk = _working_ztk(tmp_path / "ztk")  # no --version
    _force_candidate(monkeypatch, ztk)
    monkeypatch.setattr(ztk_hook, "_read_required_version", lambda: "v0.2.1")
    detail = ztk_hook.ztk_status_detail()
    assert detail["active"] is True
    assert detail["installed_version"] is None
    assert detail["currency"] == "unknown"


def test_status_detail_never_raises(monkeypatch):
    """ztk_status_detail must fail-safe to a dict, never raise."""
    monkeypatch.setattr(
        ztk_hook, "ztk_status", lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    detail = ztk_hook.ztk_status_detail()
    assert detail["active"] is False
    assert detail["currency"] == "unknown"
