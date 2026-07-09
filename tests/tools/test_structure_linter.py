#!/usr/bin/env python3
"""Tests for tools/dev/structure_linter.py.

Focus: the linter must never walk into nested git worktrees (the
``.worktrees/`` location documented in CLAUDE.md) and flag their test files
as misplaced. Regression test for the release-blocking false positives that
reported 1000+ "Test Files Misplaced" violations under
``.worktrees/<name>/tests/...``.
"""

import importlib.util
from pathlib import Path

import pytest

# Load the linter module directly by path (it lives under tools/, not the
# installed package).
_LINTER_PATH = (
    Path(__file__).resolve().parents[2] / "tools" / "dev" / "structure_linter.py"
)


def _load_linter_module():
    spec = importlib.util.spec_from_file_location("structure_linter", _LINTER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def linter_module():
    return _load_linter_module()


@pytest.fixture
def fake_root(tmp_path, linter_module, monkeypatch):
    """Create a minimal project tree with a nested worktree and point the
    module's PROJECT_ROOT at it."""
    # Real, correctly-placed test file.
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_real.py").write_text("def test_x():\n    pass\n")

    # Nested worktree at the CLAUDE.md-documented location, with a misplaced
    # test file that MUST be ignored.
    nested = tmp_path / ".worktrees" / "wt-1" / "tests"
    nested.mkdir(parents=True)
    (nested / "test_nested.py").write_text("def test_y():\n    pass\n")

    # Legacy worktree location that was already handled.
    legacy = tmp_path / ".claude" / "worktrees" / "wt-legacy" / "tests"
    legacy.mkdir(parents=True)
    (legacy / "test_legacy.py").write_text("def test_z():\n    pass\n")

    # trusty-mpm worktree marker directory.
    marker = tmp_path / ".trusty-mpm-worktree" / "tests"
    marker.mkdir(parents=True)
    (marker / "test_marker.py").write_text("def test_w():\n    pass\n")

    monkeypatch.setattr(linter_module, "PROJECT_ROOT", tmp_path)
    return tmp_path


def _ignored(linter_module, root, rel_path):
    linter = linter_module.StructureLinter(verbose=False)
    return linter._should_ignore(root / rel_path)


def test_nested_worktree_test_files_are_ignored(linter_module, fake_root):
    assert _ignored(linter_module, fake_root, ".worktrees/wt-1/tests/test_nested.py")
    assert _ignored(
        linter_module, fake_root, ".claude/worktrees/wt-legacy/tests/test_legacy.py"
    )
    assert _ignored(
        linter_module, fake_root, ".trusty-mpm-worktree/tests/test_marker.py"
    )


def test_real_test_file_is_not_ignored(linter_module, fake_root):
    assert not _ignored(linter_module, fake_root, "tests/test_real.py")


def test_lint_reports_no_worktree_violations(linter_module, fake_root):
    """End-to-end walk: nested-worktree test files must not appear as
    violations even though they sit outside /tests/."""
    linter = linter_module.StructureLinter(verbose=False)
    # Only exercise the file-walk portion, not changelog/version checks which
    # require project files absent from the fake root.
    linter.violations = []
    for file_path in fake_root.rglob("*"):
        if file_path.is_file() and not linter._should_ignore(file_path):
            linter._check_file(file_path)

    worktree_violations = [
        v
        for v in linter.violations
        if ".worktrees" in v["file"]
        or ".claude/worktrees" in v["file"]
        or ".trusty-mpm-worktree" in v["file"]
    ]
    assert worktree_violations == [], worktree_violations
