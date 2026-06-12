"""
tests/quality/test_wwl_checker_init_exemption.py — __init__.py WWL exemption tests.

WHAT: Verifies that :func:`claude_mpm.quality.wwl_checker._is_pure_reexport_module`
and :func:`analyze_file` exempt pure re-export ``__init__.py`` files (imports,
``__all__`` assignments, string literals, ``pass``) from the MISSING_FILE_WWL
requirement, while still flagging ``__init__.py`` files that contain real logic
and ordinary ``.py`` files that lack module-level WWL.

WHY: Issue #799 — the docs standard (#798) exempts pure re-export modules from
the module-level WHAT/WHY requirement.  These tests pin that behaviour so a
regression cannot silently re-introduce false-positive MISSING_FILE_WWL
violations on barrel ``__init__.py`` files.

References
----------
Issue #799: exempt pure re-export __init__.py from MISSING_FILE_WWL
Checker: src/claude_mpm/quality/wwl_checker.py
"""

from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

from claude_mpm.quality.wwl_checker import (
    MISSING_FILE_WWL,
    _is_pure_reexport_module,
    analyze_file,
)

if TYPE_CHECKING:
    from pathlib import Path


def _write(tmp_path: Path, name: str, content: str) -> Path:
    """Write a dedented snippet to *name* under tmp_path and return its path."""
    f = tmp_path / name
    f.write_text(textwrap.dedent(content), encoding="utf-8")
    return f


def _has_file_wwl_violation(path: Path, repo_root: Path) -> bool:
    """Return True if analyze_file emits a MISSING_FILE_WWL violation for *path*."""
    violations = analyze_file(path, repo_root=repo_root)
    return any(v.violation_type == MISSING_FILE_WWL for v in violations)


# ===========================================================================
# Exempt cases — no MISSING_FILE_WWL violation
# ===========================================================================


class TestExemptInitModules:
    """Pure re-export ``__init__.py`` files must be exempt."""

    def test_only_relative_import(self, tmp_path):
        f = _write(tmp_path, "__init__.py", "from . import foo\n")
        assert _is_pure_reexport_module(f) is True
        assert not _has_file_wwl_violation(f, tmp_path)

    def test_all_assignment_and_imports(self, tmp_path):
        f = _write(
            tmp_path,
            "__init__.py",
            """
            from .a import foo
            from .b import bar

            __all__ = ["foo", "bar"]
            """,
        )
        assert _is_pure_reexport_module(f) is True
        assert not _has_file_wwl_violation(f, tmp_path)

    def test_docstring_plus_imports(self, tmp_path):
        f = _write(
            tmp_path,
            "__init__.py",
            '''
            """A plain summary docstring with no WHAT/WHY."""

            from . import foo
            ''',
        )
        assert _is_pure_reexport_module(f) is True
        assert not _has_file_wwl_violation(f, tmp_path)

    def test_empty_init(self, tmp_path):
        f = _write(tmp_path, "__init__.py", "")
        assert _is_pure_reexport_module(f) is True
        assert not _has_file_wwl_violation(f, tmp_path)

    def test_all_augassign(self, tmp_path):
        f = _write(
            tmp_path,
            "__init__.py",
            """
            from .a import foo

            __all__ = ["foo"]
            __all__ += ["bar"]
            """,
        )
        assert _is_pure_reexport_module(f) is True
        assert not _has_file_wwl_violation(f, tmp_path)

    def test_pass_statement(self, tmp_path):
        f = _write(tmp_path, "__init__.py", "pass\n")
        assert _is_pure_reexport_module(f) is True
        assert not _has_file_wwl_violation(f, tmp_path)


# ===========================================================================
# Non-exempt cases — MISSING_FILE_WWL IS raised
# ===========================================================================


class TestNonExemptModules:
    """Files with real logic or non-__init__ names must NOT be exempted."""

    def test_init_with_function_def(self, tmp_path):
        f = _write(
            tmp_path,
            "__init__.py",
            """
            from . import foo


            def helper():
                return foo
            """,
        )
        assert _is_pure_reexport_module(f) is False
        assert _has_file_wwl_violation(f, tmp_path)

    def test_init_with_class_def(self, tmp_path):
        f = _write(
            tmp_path,
            "__init__.py",
            """
            from . import foo


            class Thing:
                pass
            """,
        )
        assert _is_pure_reexport_module(f) is False
        assert _has_file_wwl_violation(f, tmp_path)

    def test_init_with_real_assignment(self, tmp_path):
        f = _write(
            tmp_path,
            "__init__.py",
            """
            from . import foo

            VERSION = "1.0.0"
            """,
        )
        assert _is_pure_reexport_module(f) is False
        assert _has_file_wwl_violation(f, tmp_path)

    def test_regular_module_not_named_init(self, tmp_path):
        f = _write(tmp_path, "regular.py", "from . import foo\n")
        assert _is_pure_reexport_module(f) is False
        assert _has_file_wwl_violation(f, tmp_path)

    def test_regular_module_with_only_constant(self, tmp_path):
        # Same body as an exempt __init__.py, but the filename is not __init__.py
        # so the exemption must not apply.
        f = _write(tmp_path, "shim.py", "x = 1\n")
        assert _is_pure_reexport_module(f) is False
        assert _has_file_wwl_violation(f, tmp_path)


# ===========================================================================
# Edge cases
# ===========================================================================


class TestEdgeCases:
    """Broken or unusual inputs must degrade gracefully."""

    def test_syntax_error_init_returns_false(self, tmp_path):
        f = _write(tmp_path, "__init__.py", "from . import (\n")
        # SyntaxError → not classified as pure re-export.
        assert _is_pure_reexport_module(f) is False

    def test_syntax_error_init_does_not_crash_analyze_file(self, tmp_path):
        f = _write(tmp_path, "__init__.py", "from . import (\n")
        # analyze_file silently skips unparseable files (returns []).
        assert analyze_file(f, repo_root=tmp_path) == []
