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
    monkeypatch.setattr(
        ztk_hook,
        "_ZTK_AUTOINSTALL_SENTINEL_BASE",
        tmp_path / ".ztk-autoinstall-attempted",
    )
    ztk_hook._RESOLVE_MEMO.clear()
    ztk_hook._WARNED_NONFUNCTIONAL = False
    ztk_hook._AUTOINSTALL_LOCK = False
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


# ---------------------------------------------------------------------------
# Fix 3: user-local candidate (~/.claude-mpm/bin/ztk)
# ---------------------------------------------------------------------------
def test_resolve_finds_user_local_binary(tmp_path, monkeypatch):
    """_resolve_ztk picks up a working binary at ~/.claude-mpm/bin/ztk."""
    # Suppress auto-install so it doesn't interfere.
    monkeypatch.setattr(ztk_hook, "_auto_install_ztk", lambda: None)

    # Disable system PATH and bundled binary lookups.
    monkeypatch.setattr(ztk_hook.shutil, "which", lambda _name: None)

    class _NoBundled:
        def joinpath(self, *_parts):
            return "/nonexistent/ztk"

    monkeypatch.setattr(ztk_hook.resources, "files", lambda _pkg: _NoBundled())

    # Place a working ztk in the user-local location.
    user_bin = tmp_path / "bin"
    user_bin.mkdir()
    ztk_path = user_bin / "ztk"
    _working_ztk(ztk_path)

    # Point _MPM_LOG_DIR at our tmp_path so user_local resolves correctly.
    # (Already set by _isolated_state fixture)

    result = ztk_hook._resolve_ztk()
    assert result == str(ztk_path)


def test_resolve_user_local_zero_byte_rejected(tmp_path, monkeypatch):
    """A 0-byte user-local binary is rejected (same gating as bundled)."""
    monkeypatch.setattr(ztk_hook, "_auto_install_ztk", lambda: None)
    monkeypatch.setattr(ztk_hook.shutil, "which", lambda _name: None)

    class _NoBundled:
        def joinpath(self, *_parts):
            return "/nonexistent/ztk"

    monkeypatch.setattr(ztk_hook.resources, "files", lambda _pkg: _NoBundled())

    user_bin = tmp_path / "bin"
    user_bin.mkdir()
    ztk_path = user_bin / "ztk"
    ztk_path.touch()  # 0-byte

    result = ztk_hook._resolve_ztk()
    assert result is None


# ---------------------------------------------------------------------------
# Fix 2: auto-install sentinel gates retries
# ---------------------------------------------------------------------------
def test_auto_install_runs_once_per_version(tmp_path, monkeypatch):
    """Auto-install is only attempted once per required version (sentinel file)."""
    monkeypatch.setattr(ztk_hook, "_read_required_version", lambda: "v0.3.0")

    download_calls: list[str] = []

    def _mock_inline(tag):
        download_calls.append(tag)

    monkeypatch.setattr(ztk_hook, "_inline_download_ztk", _mock_inline)

    # First call: should attempt install.
    ztk_hook._AUTOINSTALL_LOCK = False
    ztk_hook._auto_install_ztk()
    assert len(download_calls) == 1

    # Reset process lock to simulate a second process / second call.
    ztk_hook._AUTOINSTALL_LOCK = False
    ztk_hook._auto_install_ztk()
    # Sentinel file exists → no second attempt.
    assert len(download_calls) == 1


def test_auto_install_skipped_when_disabled(tmp_path, monkeypatch):
    """Auto-install does nothing when CLAUDE_MPM_DISABLE_ZTK is set."""
    monkeypatch.setenv("CLAUDE_MPM_DISABLE_ZTK", "1")
    monkeypatch.setattr(ztk_hook, "_read_required_version", lambda: "v0.3.0")

    download_calls: list[str] = []

    def _mock_inline(tag):
        download_calls.append(tag)

    monkeypatch.setattr(ztk_hook, "_inline_download_ztk", _mock_inline)
    ztk_hook._AUTOINSTALL_LOCK = False
    ztk_hook._auto_install_ztk()
    assert download_calls == []


def test_auto_install_skipped_when_no_required_version(tmp_path, monkeypatch):
    """Auto-install skips when required version is unknown (no manifest)."""
    monkeypatch.setattr(ztk_hook, "_read_required_version", lambda: None)

    download_calls: list[str] = []
    monkeypatch.setattr(ztk_hook, "_inline_download_ztk", download_calls.append)
    ztk_hook._AUTOINSTALL_LOCK = False
    ztk_hook._auto_install_ztk()
    assert download_calls == []


def test_auto_install_failure_does_not_raise(tmp_path, monkeypatch):
    """A failing auto-install prints a warning but never raises."""
    monkeypatch.setattr(ztk_hook, "_read_required_version", lambda: "v0.3.0")

    def _boom(tag):
        raise RuntimeError("network down")

    monkeypatch.setattr(ztk_hook, "_inline_download_ztk", _boom)
    ztk_hook._AUTOINSTALL_LOCK = False
    # Must not raise.
    ztk_hook._auto_install_ztk()


def test_auto_install_different_versions_each_get_attempt(tmp_path, monkeypatch):
    """Sentinel is keyed by version — a new version triggers a new install."""
    download_calls: list[str] = []

    def _mock_inline(tag):
        download_calls.append(tag)

    monkeypatch.setattr(ztk_hook, "_inline_download_ztk", _mock_inline)

    # First version
    monkeypatch.setattr(ztk_hook, "_read_required_version", lambda: "v0.3.0")
    ztk_hook._AUTOINSTALL_LOCK = False
    ztk_hook._auto_install_ztk()
    assert download_calls == ["v0.3.0"]

    # New version — different sentinel file key
    monkeypatch.setattr(ztk_hook, "_read_required_version", lambda: "v0.4.0")
    ztk_hook._AUTOINSTALL_LOCK = False
    ztk_hook._auto_install_ztk()
    assert download_calls == ["v0.3.0", "v0.4.0"]


def test_resolve_ztk_triggers_auto_install_when_no_binary(tmp_path, monkeypatch):
    """_resolve_ztk with verify=True calls _auto_install_ztk when no binary found."""
    install_calls: list[int] = []

    def _mock_install():
        install_calls.append(1)

    monkeypatch.setattr(ztk_hook, "_auto_install_ztk", _mock_install)
    monkeypatch.setattr(ztk_hook.shutil, "which", lambda _name: None)

    class _NoBundled:
        def joinpath(self, *_parts):
            return "/nonexistent/ztk"

    monkeypatch.setattr(ztk_hook.resources, "files", lambda _pkg: _NoBundled())

    # No user-local binary either
    ztk_hook._resolve_ztk(verify=True)
    assert len(install_calls) == 1


def test_resolve_ztk_no_auto_install_when_verify_false(tmp_path, monkeypatch):
    """_resolve_ztk with verify=False skips auto-install (status-only path)."""
    install_calls: list[int] = []

    def _mock_install():
        install_calls.append(1)

    monkeypatch.setattr(ztk_hook, "_auto_install_ztk", _mock_install)
    monkeypatch.setattr(ztk_hook.shutil, "which", lambda _name: None)

    class _NoBundled:
        def joinpath(self, *_parts):
            return "/nonexistent/ztk"

    monkeypatch.setattr(ztk_hook.resources, "files", lambda _pkg: _NoBundled())

    ztk_hook._resolve_ztk(verify=False)
    assert install_calls == []
