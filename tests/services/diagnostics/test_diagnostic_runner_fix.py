"""Tests covering ``DiagnosticRunner --fix`` execution paths.

WHY: ``claude-mpm doctor --fix`` previously was a no-op (TODO in the
source). These tests pin down the new behavior:
  * fixable issues actually get fixed (with a ``✓ Fixed:`` log line),
  * unfixable issues emit a clear ``⚠ Manual fix required:`` message.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from claude_mpm.core.enums import ValidationSeverity
from claude_mpm.services.diagnostics.diagnostic_runner import DiagnosticRunner
from claude_mpm.services.diagnostics.models import DiagnosticResult

if TYPE_CHECKING:
    from pathlib import Path


class _LogCapture:
    """Tiny helper to capture logger calls for assertions."""

    def __init__(self) -> None:
        self.info: list[str] = []
        self.warning: list[str] = []
        self.error: list[str] = []

    def install(self, runner: DiagnosticRunner) -> None:
        def _info(msg, *args, **_kwargs):
            self.info.append(msg % args if args else str(msg))

        def _warning(msg, *args, **_kwargs):
            self.warning.append(msg % args if args else str(msg))

        def _error(msg, *args, **_kwargs):
            self.error.append(msg % args if args else str(msg))

        runner.logger.info = _info  # type: ignore[assignment]
        runner.logger.warning = _warning  # type: ignore[assignment]
        runner.logger.error = _error  # type: ignore[assignment]


def test_attempt_fix_creates_missing_directory(tmp_path: Path) -> None:
    """A fixable mkdir issue should actually create the directory."""
    runner = DiagnosticRunner(fix=True)
    capture = _LogCapture()
    capture.install(runner)

    target = tmp_path / "newdir"
    result = DiagnosticResult(
        category="Filesystem",
        status=ValidationSeverity.WARNING,
        message="Missing directory",
        fix_command=f"mkdir -p {target}",
    )

    applied = runner._attempt_fix(result)

    assert applied is True
    assert target.exists() and target.is_dir()
    assert any("✓ Fixed:" in msg for msg in capture.info), capture.info


def test_attempt_fix_unfixable_emits_manual_message() -> None:
    """A fix command we cannot run safely must surface a clear manual message."""
    runner = DiagnosticRunner(fix=True)
    capture = _LogCapture()
    capture.install(runner)

    result = DiagnosticResult(
        category="Authentication",
        status=ValidationSeverity.ERROR,
        message="Not authenticated with Anthropic",
        fix_command="claude auth login",  # unknown handler
    )

    applied = runner._attempt_fix(result)

    assert applied is False
    assert any("⚠ Manual fix required" in msg for msg in capture.warning), (
        capture.warning
    )


def test_attempt_fix_placeholder_command_is_manual() -> None:
    """Fix commands containing ``<placeholder>`` should never be executed."""
    runner = DiagnosticRunner(fix=True)
    capture = _LogCapture()
    capture.install(runner)

    result = DiagnosticResult(
        category="Sources",
        status=ValidationSeverity.WARNING,
        message="Configure agent source",
        fix_command="claude-mpm sources add <source-id>",
    )

    applied = runner._attempt_fix(result)

    assert applied is False
    assert any("⚠ Manual fix required" in msg for msg in capture.warning), (
        capture.warning
    )


def test_attempt_fix_no_fix_command_emits_manual_message() -> None:
    """Issues without a fix command should still tell users what to do."""
    runner = DiagnosticRunner(fix=True)
    capture = _LogCapture()
    capture.install(runner)

    result = DiagnosticResult(
        category="Network",
        status=ValidationSeverity.ERROR,
        message="Could not reach PyPI",
        fix_description="Check your internet connection or proxy settings.",
        fix_command=None,
    )

    applied = runner._attempt_fix(result)

    assert applied is False
    assert any("⚠ Manual fix required" in msg for msg in capture.warning), (
        capture.warning
    )


def test_attempt_fix_pip_command_is_not_executed() -> None:
    """``pip install`` style suggestions must not be auto-run."""
    runner = DiagnosticRunner(fix=True)
    capture = _LogCapture()
    capture.install(runner)

    result = DiagnosticResult(
        category="Installation",
        status=ValidationSeverity.WARNING,
        message="Missing dependency",
        fix_command="pip install some-package",
    )

    with patch("subprocess.run") as mock_run:
        applied = runner._attempt_fix(result)

    assert applied is False
    mock_run.assert_not_called()
    assert any("⚠ Manual fix required" in msg for msg in capture.warning), (
        capture.warning
    )


def test_attempt_fix_disabled_does_not_run_anything(tmp_path: Path) -> None:
    """Without ``--fix``, _attempt_fix must be a no-op."""
    runner = DiagnosticRunner(fix=False)
    target = tmp_path / "should-not-exist"
    result = DiagnosticResult(
        category="Filesystem",
        status=ValidationSeverity.WARNING,
        message="Missing directory",
        fix_command=f"mkdir -p {target}",
    )

    assert runner._attempt_fix(result) is False
    assert not target.exists()


if __name__ == "__main__":  # pragma: no cover - manual debugging hook
    pytest.main([__file__, "-v"])
