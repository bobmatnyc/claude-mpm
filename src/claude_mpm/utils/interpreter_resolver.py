"""Resolve the Python interpreter that can import ``claude_mpm``.

WHAT: Provides ``resolve_claude_mpm_python()`` which returns the path to a
Python interpreter capable of ``import claude_mpm``, working across pipx,
``pip --user``, ``uv tool``, and editable/dev installs.
WHY: Bug #735 — the session skills told the harness to run
``python3 -c "from claude_mpm..."``. On pipx (and ``uv tool``) installs,
``claude_mpm`` lives in an isolated virtualenv that the *system* ``python3``
cannot import, producing ``ModuleNotFoundError``. The skill must locate the
interpreter that owns the installed ``claude-mpm`` executable instead of
assuming bare ``python3`` works.

Resolution order (first that works wins):
1. ``$CLAUDE_MPM_PYTHON`` env override (explicit escape hatch).
2. ``sys.executable`` — if this very process can already import claude_mpm,
   that interpreter is correct (covers ``python -m claude_mpm`` and editable
   installs running inside the right venv).
3. The venv ``python`` next to the resolved ``claude-mpm`` executable on PATH
   (covers pipx, ``uv tool``, ``pip --user`` console-script installs).
4. Bare ``python3`` / ``python`` as a last resort.

This module deliberately has NO dependency on the rest of ``claude_mpm`` so it
can be imported (or run via ``python -m``) by the lightest possible runtime.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 - used only to probe candidate interpreters
import sys
from pathlib import Path

#: Environment variable users can set to force a specific interpreter.
ENV_OVERRIDE = "CLAUDE_MPM_PYTHON"

#: Console-script name installed by the claude-mpm package.
CONSOLE_SCRIPT = "claude-mpm"


def _can_import_claude_mpm(python_path: str | Path) -> bool:
    """Return True if ``python_path`` can ``import claude_mpm``.

    Runs a tiny subprocess so we test the *candidate* interpreter, not the
    current one. Failures (missing interpreter, import error, timeout) all
    resolve to ``False`` so the caller simply moves to the next candidate.

    Args:
        python_path: Path to a Python interpreter to probe.

    Returns:
        True if the interpreter exists and can import ``claude_mpm``.
    """
    python_path = str(python_path)
    if not python_path:
        return False
    try:
        result = subprocess.run(  # nosec B603 - fixed args, no shell
            [python_path, "-c", "import claude_mpm"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _venv_python_for_executable(executable: str | Path) -> Path | None:
    """Given a console-script path, return the venv ``python`` beside it.

    Console scripts (pipx, uv tool, pip) live in ``<venv>/bin/`` next to the
    interpreter that runs them. We resolve symlinks first so a pipx shim in
    ``~/.local/bin`` points at the real venv ``bin`` directory.

    Args:
        executable: Path to the ``claude-mpm`` console script.

    Returns:
        Path to the sibling ``python``/``python3`` if it exists, else ``None``.
    """
    try:
        real = Path(executable).resolve()
    except OSError:
        return None

    bin_dir = real.parent
    # Windows venvs put python.exe in the same Scripts/ dir; POSIX uses bin/.
    candidates = [
        bin_dir / "python",
        bin_dir / "python3",
        bin_dir / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def resolve_claude_mpm_python() -> str:
    """Resolve a Python interpreter that can import ``claude_mpm``.

    WHAT: Returns the path/name of an interpreter able to ``import claude_mpm``.
    WHY: Bug #735 — see module docstring. Bare ``python3`` fails on isolated
    installs (pipx/uv tool); we must find the interpreter that owns the
    installed ``claude-mpm`` executable.

    Returns:
        A string usable as the interpreter argument to ``subprocess`` or shell
        (an absolute path when resolved, or a bare name as a last-resort
        fallback).
    """
    # 1. Explicit override always wins.
    override = os.environ.get(ENV_OVERRIDE)
    if override and _can_import_claude_mpm(override):
        return override

    # 2. The current interpreter, if it can already import claude_mpm.
    if sys.executable and _can_import_claude_mpm(sys.executable):
        return sys.executable

    # 3. The venv python beside the installed claude-mpm console script.
    executable = shutil.which(CONSOLE_SCRIPT)
    if executable:
        venv_python = _venv_python_for_executable(executable)
        if venv_python and _can_import_claude_mpm(venv_python):
            return str(venv_python)

    # 4. Last resort: bare python3 / python (works for system installs).
    for fallback in ("python3", "python"):
        resolved = shutil.which(fallback)
        if resolved and _can_import_claude_mpm(resolved):
            return resolved

    # Nothing worked — return sys.executable so the caller gets a real path and
    # a clear ModuleNotFoundError rather than a confusing "python3 not found".
    return sys.executable or "python3"


def main() -> int:
    """Print the resolved interpreter path to stdout (for shell capture).

    Usage from a skill::

        MPM_PY="$(python3 -m claude_mpm.utils.interpreter_resolver \\
                    2>/dev/null || command -v python3)"

    Returns:
        Process exit code (0 always; resolution never hard-fails).
    """
    print(resolve_claude_mpm_python())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
