"""Tests for ``claude_mpm.utils.interpreter_resolver`` (Bug #735).

Proves the resolver finds an interpreter that can import ``claude_mpm`` across
install layouts — in particular a *simulated pipx install* where the system
``python3`` cannot import the package but the venv python beside the
``claude-mpm`` console script can.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from claude_mpm.utils import interpreter_resolver as ir


@pytest.fixture(autouse=True)
def _clear_override(monkeypatch):
    """Ensure CLAUDE_MPM_PYTHON does not leak in from the real environment."""
    monkeypatch.delenv(ir.ENV_OVERRIDE, raising=False)


def test_env_override_wins_when_importable(monkeypatch):
    """An explicit CLAUDE_MPM_PYTHON that can import wins immediately."""
    monkeypatch.setenv(ir.ENV_OVERRIDE, "/opt/venv/bin/python")
    monkeypatch.setattr(
        ir, "_can_import_claude_mpm", lambda p: p == "/opt/venv/bin/python"
    )
    assert ir.resolve_claude_mpm_python() == "/opt/venv/bin/python"


def test_env_override_ignored_when_not_importable(monkeypatch):
    """A bad override is skipped and resolution falls through to sys.executable."""
    monkeypatch.setenv(ir.ENV_OVERRIDE, "/bogus/python")
    # Only sys.executable can import.
    monkeypatch.setattr(ir.sys, "executable", "/real/venv/bin/python")
    monkeypatch.setattr(
        ir, "_can_import_claude_mpm", lambda p: p == "/real/venv/bin/python"
    )
    assert ir.resolve_claude_mpm_python() == "/real/venv/bin/python"


def test_current_interpreter_used_when_importable(monkeypatch):
    """sys.executable is returned when it can already import claude_mpm."""
    monkeypatch.setattr(ir.sys, "executable", "/cur/python")
    monkeypatch.setattr(ir, "_can_import_claude_mpm", lambda p: p == "/cur/python")
    assert ir.resolve_claude_mpm_python() == "/cur/python"


def test_simulated_pipx_resolves_venv_python(monkeypatch, tmp_path):
    """Simulated pipx: system python3 fails, venv python beside script works.

    Layout:
        ~/.local/bin/claude-mpm        (symlink/shim)  -> <venv>/bin/claude-mpm
        <venv>/bin/python              (the importable interpreter)

    The current interpreter and bare python3 must NOT be able to import
    claude_mpm; only the venv python next to the console script can.
    """
    # Build a fake pipx venv layout.
    venv_bin = tmp_path / "pipx" / "venvs" / "claude-mpm" / "bin"
    venv_bin.mkdir(parents=True)
    venv_python = venv_bin / "python"
    venv_python.write_text("#!/bin/sh\n")
    venv_python.chmod(0o755)
    real_script = venv_bin / "claude-mpm"
    real_script.write_text("#!/bin/sh\n")
    real_script.chmod(0o755)

    # The shim on PATH is a symlink to the real venv script.
    shim_dir = tmp_path / ".local" / "bin"
    shim_dir.mkdir(parents=True)
    shim = shim_dir / "claude-mpm"
    shim.symlink_to(real_script)

    # sys.executable is the SYSTEM python — cannot import claude_mpm.
    monkeypatch.setattr(ir.sys, "executable", "/usr/bin/python3")

    # which("claude-mpm") -> the shim; which("python3") -> system python.
    def fake_which(name):
        if name == ir.CONSOLE_SCRIPT:
            return str(shim)
        if name in ("python3", "python"):
            return "/usr/bin/python3"
        return None

    monkeypatch.setattr(ir.shutil, "which", fake_which)

    # Only the venv python can import claude_mpm.
    def fake_can_import(p):
        return str(Path(p)) == str(venv_python.resolve())

    monkeypatch.setattr(ir, "_can_import_claude_mpm", fake_can_import)

    resolved = ir.resolve_claude_mpm_python()
    assert Path(resolved) == venv_python.resolve()
    # Critically, it did NOT return the failing system python3.
    assert resolved != "/usr/bin/python3"


def test_fallback_to_python3_for_system_install(monkeypatch):
    """When only system python3 can import, it is returned as the fallback."""
    monkeypatch.setattr(ir.sys, "executable", "/usr/bin/python3-nope")
    monkeypatch.setattr(
        ir.shutil,
        "which",
        lambda name: "/usr/bin/python3" if name == "python3" else None,
    )
    monkeypatch.setattr(ir, "_can_import_claude_mpm", lambda p: p == "/usr/bin/python3")
    assert ir.resolve_claude_mpm_python() == "/usr/bin/python3"


def test_resolver_never_raises_when_nothing_works(monkeypatch):
    """If nothing can import, return sys.executable (clear error downstream)."""
    monkeypatch.setattr(ir.sys, "executable", "/some/python")
    monkeypatch.setattr(ir.shutil, "which", lambda name: None)
    monkeypatch.setattr(ir, "_can_import_claude_mpm", lambda p: False)
    assert ir.resolve_claude_mpm_python() == "/some/python"


def test_venv_python_for_executable_finds_sibling(tmp_path):
    """The venv python sibling is found next to a (resolved) console script."""
    bin_dir = tmp_path / "venv" / "bin"
    bin_dir.mkdir(parents=True)
    py = bin_dir / "python3"
    py.write_text("")
    script = bin_dir / "claude-mpm"
    script.write_text("")
    found = ir._venv_python_for_executable(script)
    assert found == py


def test_can_import_uses_candidate_interpreter():
    """A real probe: the current interpreter can import claude_mpm.

    This is an end-to-end sanity check that the subprocess probe works against
    a genuinely-importable interpreter (the one running the test suite).
    """
    import sys

    assert ir._can_import_claude_mpm(sys.executable) is True


def test_main_prints_resolution(monkeypatch, capsys):
    """``main()`` prints the resolved interpreter and exits 0."""
    monkeypatch.setattr(ir, "resolve_claude_mpm_python", lambda: "/x/python")
    rc = ir.main()
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "/x/python"


def test_real_environment_resolves_importable_interpreter():
    """Integration: in the real test environment the resolver returns an
    interpreter that genuinely imports claude_mpm (no mocks)."""
    # Make sure no override is active for this real run.
    os.environ.pop(ir.ENV_OVERRIDE, None)
    resolved = ir.resolve_claude_mpm_python()
    assert ir._can_import_claude_mpm(resolved)
