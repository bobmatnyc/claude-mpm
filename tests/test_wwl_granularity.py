"""
tests/test_wwl_granularity.py — WWL granularity sanity-check for the SLD feature.

WHAT: Runs the WWL checker (:mod:`claude_mpm.quality.wwl_checker`) against the
live ``src/claude_mpm`` source tree in ``baseline`` enforcement mode and asserts
zero non-baseline violations.  Also contains targeted unit tests for the
analyzer sub-functions (LOC counter, complexity counter, WWL detector, baseline
filtering) using ``tmp_path`` sample files.

WHY: The integration test enforces the WWL ratchet: new code above the LOC or
complexity thresholds must carry a WWL doc-comment.  The unit tests give fast
feedback during local development without scanning the entire source tree.

References
----------
WWL convention: docs/specs/README.md
Checker: src/claude_mpm/quality/wwl_checker.py
Baseline: docs/specs/.wwl-baseline.json
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths — resolved relative to this file so they work from any cwd
# ---------------------------------------------------------------------------

_TESTS_DIR = Path(__file__).parent
_REPO_ROOT = _TESTS_DIR.parent
_SRC_ROOT = _REPO_ROOT / "src" / "claude_mpm"
_BASELINE_PATH = _REPO_ROOT / "docs" / "specs" / ".wwl-baseline.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_py(tmp_path: Path, name: str, content: str) -> Path:
    """Write a .py snippet to tmp_path and return the file path."""
    f = tmp_path / name
    f.write_text(textwrap.dedent(content), encoding="utf-8")
    return f


# ===========================================================================
# INTEGRATION TEST: baseline mode on the live source tree
# ===========================================================================


class TestWWLBaseline:
    """Integration tests — run the checker on the real source tree."""

    def test_no_new_violations_in_baseline_mode(self):
        """Zero non-baseline violations must be reported under the live source tree.

        WHAT: Invokes :func:`check_source_tree` with the production thresholds
        (LOC=50, CC=10) in ``baseline`` enforcement mode against
        ``src/claude_mpm``.  The test asserts that
        :attr:`CheckResult.new_violations` is empty and that the result is not
        failed.

        WHY: This is the ratchet gate: every PR that introduces a function or
        class exceeding either threshold must include a WWL doc-comment.
        Existing violations are captured in ``.wwl-baseline.json`` and are
        tolerated; only genuinely new code above the threshold is blocked.
        """
        from claude_mpm.quality.wwl_checker import (
            DEFAULT_COMPLEXITY_THRESHOLD,
            DEFAULT_LINE_THRESHOLD,
            check_source_tree,
        )

        result = check_source_tree(
            src_root=_SRC_ROOT,
            baseline_path=_BASELINE_PATH,
            line_threshold=DEFAULT_LINE_THRESHOLD,
            complexity_threshold=DEFAULT_COMPLEXITY_THRESHOLD,
            enforcement="baseline",
        )

        if result.new_violations:
            lines = [
                "WWL ratchet: the following units exceed thresholds but have no "
                "WWL doc-comment and are NOT in the baseline.",
                "Add a WHAT: + WHY: block to their docstrings, or run "
                "`python -m claude_mpm.quality.wwl_checker --regenerate` to "
                "update the baseline (only after review).",
                "",
            ]
            for v in result.new_violations:
                lines.append(f"  [{v.violation_type}] {v.key}")
                lines.append(f"    {v.description}")
            pytest.fail("\n".join(lines))

        assert not result.failed, (
            "CheckResult.failed must be False in baseline mode with no new violations"
        )

    def test_baseline_file_exists(self):
        """The baseline JSON file must exist in docs/specs/.

        WHAT: Asserts that ``docs/specs/.wwl-baseline.json`` is present and is
        valid JSON.

        WHY: A missing baseline file causes :func:`load_baseline` to return an
        empty frozenset, making every violation appear new and breaking the CI
        gate immediately after adoption.
        """
        assert _BASELINE_PATH.exists(), (
            f"Baseline file missing: {_BASELINE_PATH}. "
            "Run `python -m claude_mpm.quality.wwl_checker --regenerate` to generate it."
        )
        data = json.loads(_BASELINE_PATH.read_text(encoding="utf-8"))
        assert isinstance(data, list), "Baseline file must be a JSON array"
        assert len(data) > 0, (
            "Baseline must be non-empty (legacy violations should be captured)"
        )

    def test_baseline_entries_have_required_fields(self):
        """Each baseline entry must have relpath, qualname, violation_type, description.

        WHAT: Reads the baseline JSON and checks that every entry contains the
        four fields used by :func:`load_baseline` and :func:`save_baseline`.

        WHY: Missing fields would cause :func:`load_baseline` to silently drop
        entries, treating them as new violations on the next CI run.
        """
        data = json.loads(_BASELINE_PATH.read_text(encoding="utf-8"))
        required = {"relpath", "qualname", "violation_type", "description"}
        for i, entry in enumerate(data):
            missing = required - entry.keys()
            assert not missing, f"Baseline entry {i} missing fields: {missing}"

    def test_violations_exist_in_source_tree(self):
        """The checker must find at least some violations in the live source tree.

        WHAT: Runs the checker in ``off`` mode (no enforcement) and asserts
        that the total violation count is > 0.

        WHY: A zero-violation count could mean the checker is broken or the
        thresholds are set unrealistically high.  This test guards against silent
        checker failure.
        """
        from claude_mpm.quality.wwl_checker import check_source_tree

        result = check_source_tree(
            src_root=_SRC_ROOT,
            baseline_path=None,
            enforcement="off",
        )
        assert len(result.violations) > 0, (
            "Expected at least some violations in the live source tree "
            "(either the checker is broken or the thresholds are too high)"
        )


# ===========================================================================
# UNIT TESTS: individual analyzer functions
# ===========================================================================


class TestHasWWLDocstring:
    """Tests for :func:`_has_wwl_docstring`."""

    def _parse_func(self, src: str):
        import ast as _ast

        return _ast.parse(textwrap.dedent(src))

    def test_detects_what_and_why(self):
        from claude_mpm.quality.wwl_checker import _has_wwl_docstring

        tree = self._parse_func("""
            def foo():
                \"\"\"
                WHAT: does something.
                WHY: because of reasons.
                \"\"\"
                pass
        """)
        # The function node
        import ast

        fn = tree.body[0]
        assert _has_wwl_docstring(fn) is True

    def test_missing_why_is_not_wwl(self):
        import ast

        from claude_mpm.quality.wwl_checker import _has_wwl_docstring

        tree = ast.parse(
            textwrap.dedent("""
            def foo():
                \"\"\"WHAT: does something.\"\"\"
                pass
        """)
        )
        fn = tree.body[0]
        assert _has_wwl_docstring(fn) is False

    def test_missing_what_is_not_wwl(self):
        import ast

        from claude_mpm.quality.wwl_checker import _has_wwl_docstring

        tree = ast.parse(
            textwrap.dedent("""
            def foo():
                \"\"\"WHY: rationale only.\"\"\"
                pass
        """)
        )
        fn = tree.body[0]
        assert _has_wwl_docstring(fn) is False

    def test_empty_docstring_is_not_wwl(self):
        import ast

        from claude_mpm.quality.wwl_checker import _has_wwl_docstring

        tree = ast.parse(
            textwrap.dedent("""
            def foo():
                \"\"\"Just a regular docstring.\"\"\"
                pass
        """)
        )
        fn = tree.body[0]
        assert _has_wwl_docstring(fn) is False

    def test_no_docstring_is_not_wwl(self):
        import ast

        from claude_mpm.quality.wwl_checker import _has_wwl_docstring

        tree = ast.parse(
            textwrap.dedent("""
            def foo():
                pass
        """)
        )
        fn = tree.body[0]
        assert _has_wwl_docstring(fn) is False

    def test_case_insensitive_detection(self):
        import ast

        from claude_mpm.quality.wwl_checker import _has_wwl_docstring

        tree = ast.parse(
            textwrap.dedent("""
            def foo():
                \"\"\"
                what: observable.
                why: rationale.
                \"\"\"
                pass
        """)
        )
        fn = tree.body[0]
        assert _has_wwl_docstring(fn) is True

    def test_module_level_wwl(self):
        import ast

        from claude_mpm.quality.wwl_checker import _has_wwl_docstring

        tree = ast.parse(
            textwrap.dedent("""
            \"\"\"
            Module summary.

            WHAT: This module does X.
            WHY: Because of Y.
            \"\"\"
        """)
        )
        assert _has_wwl_docstring(tree) is True


class TestCountBranches:
    """Tests for :func:`_count_branches` (cyclomatic complexity)."""

    def _parse_func(self, src: str):
        import ast

        return ast.parse(textwrap.dedent(src))

    def test_simple_function_zero_branches(self):
        import ast

        from claude_mpm.quality.wwl_checker import _count_branches

        tree = ast.parse("def foo(): pass")
        fn = tree.body[0]
        assert _count_branches(fn) == 0  # CC = 1 (caller adds 1)

    def test_if_adds_one_branch(self):
        import ast

        from claude_mpm.quality.wwl_checker import _count_branches

        tree = ast.parse(
            textwrap.dedent("""
            def foo(x):
                if x:
                    return 1
                return 0
        """)
        )
        fn = tree.body[0]
        assert _count_branches(fn) == 1  # CC = 2

    def test_for_while_each_add_one(self):
        import ast

        from claude_mpm.quality.wwl_checker import _count_branches

        tree = ast.parse(
            textwrap.dedent("""
            def foo(xs):
                for x in xs:
                    while x:
                        pass
        """)
        )
        fn = tree.body[0]
        assert _count_branches(fn) == 2  # CC = 3

    def test_bool_and_adds_branches(self):
        import ast

        from claude_mpm.quality.wwl_checker import _count_branches

        tree = ast.parse(
            textwrap.dedent("""
            def foo(a, b, c):
                return a and b and c
        """)
        )
        fn = tree.body[0]
        # 'a and b and c' → BoolOp with 3 values → 2 extra branches
        assert _count_branches(fn) == 2

    def test_nested_function_not_counted(self):
        """Nested function branches should NOT be counted in the outer function."""
        import ast

        from claude_mpm.quality.wwl_checker import _count_branches

        tree = ast.parse(
            textwrap.dedent("""
            def outer():
                def inner(x):
                    if x:
                        return 1
                return inner
        """)
        )
        outer = tree.body[0]
        # The if inside inner() should NOT be counted for outer()
        assert _count_branches(outer) == 0

    def test_except_handler_adds_branch(self):
        import ast

        from claude_mpm.quality.wwl_checker import _count_branches

        tree = ast.parse(
            textwrap.dedent("""
            def foo():
                try:
                    pass
                except ValueError:
                    pass
        """)
        )
        fn = tree.body[0]
        assert _count_branches(fn) == 1

    def test_ternary_adds_branch(self):
        import ast

        from claude_mpm.quality.wwl_checker import _count_branches

        tree = ast.parse(
            textwrap.dedent("""
            def foo(x):
                return 1 if x else 0
        """)
        )
        fn = tree.body[0]
        assert _count_branches(fn) == 1


class TestNodeLoc:
    """Tests for :func:`_node_loc`."""

    def test_single_line_function(self):
        import ast

        from claude_mpm.quality.wwl_checker import _node_loc

        tree = ast.parse("def foo(): pass")
        fn = tree.body[0]
        assert _node_loc(fn) == 1

    def test_multiline_function(self):
        import ast

        from claude_mpm.quality.wwl_checker import _node_loc

        tree = ast.parse(
            textwrap.dedent("""
            def foo():
                a = 1
                b = 2
                return a + b
        """).strip()
        )
        fn = tree.body[0]
        assert _node_loc(fn) == 4


class TestAnalyzeFile:
    """Tests for :func:`analyze_file`."""

    def test_file_with_module_wwl_and_no_large_units(self, tmp_path):
        from claude_mpm.quality.wwl_checker import analyze_file

        f = _write_py(
            tmp_path,
            "good.py",
            """
            \"\"\"
            Module summary.

            WHAT: does X.
            WHY: because Y.
            \"\"\"

            def small():
                return 1
        """,
        )
        violations = analyze_file(f, repo_root=tmp_path)
        assert violations == []

    def test_missing_module_wwl_produces_violation(self, tmp_path):
        from claude_mpm.quality.wwl_checker import MISSING_FILE_WWL, analyze_file

        f = _write_py(
            tmp_path,
            "bad.py",
            """
            \"\"\"No WHAT or WHY here.\"\"\"

            def small():
                return 1
        """,
        )
        violations = analyze_file(f, repo_root=tmp_path)
        assert any(v.violation_type == MISSING_FILE_WWL for v in violations)

    def test_large_function_without_wwl_produces_violation(self, tmp_path):
        from claude_mpm.quality.wwl_checker import MISSING_UNIT_WWL, analyze_file

        # Generate a function with >50 LOC, no WHAT/WHY
        body_lines = "\n".join(f"    x{i} = {i}" for i in range(60))
        src = f'''
"""
WHAT: module.
WHY: module.
"""

def big_func():
{body_lines}
    return x0
'''
        f = tmp_path / "big.py"
        f.write_text(textwrap.dedent(src), encoding="utf-8")
        violations = analyze_file(f, repo_root=tmp_path, line_threshold=50)
        assert any(
            v.violation_type == MISSING_UNIT_WWL and "big_func" in v.qualname
            for v in violations
        )

    def test_large_function_with_wwl_no_violation(self, tmp_path):
        from claude_mpm.quality.wwl_checker import analyze_file

        body_lines = "\n".join(f"    x{i} = {i}" for i in range(60))
        src = f'''
"""
WHAT: module.
WHY: module.
"""

def big_func():
    """
    WHAT: does lots of stuff.
    WHY: necessary.
    """
{body_lines}
    return x0
'''
        f = tmp_path / "big_good.py"
        f.write_text(textwrap.dedent(src), encoding="utf-8")
        violations = analyze_file(f, repo_root=tmp_path, line_threshold=50)
        unit_violations = [v for v in violations if v.qualname == "big_func"]
        assert unit_violations == []

    def test_high_complexity_function_without_wwl_produces_violation(self, tmp_path):
        from claude_mpm.quality.wwl_checker import MISSING_UNIT_WWL, analyze_file

        # Build a function with CC > 10 using many if statements
        ifs = "\n".join(f"    if x == {i}:\n        return {i}" for i in range(12))
        src = f'''
"""
WHAT: module.
WHY: module.
"""

def complex_func(x):
{ifs}
    return -1
'''
        f = tmp_path / "complex.py"
        f.write_text(src, encoding="utf-8")
        violations = analyze_file(
            f, repo_root=tmp_path, line_threshold=1000, complexity_threshold=10
        )
        assert any(
            v.violation_type == MISSING_UNIT_WWL and "complex_func" in v.qualname
            for v in violations
        )

    def test_syntax_error_file_returns_no_violations(self, tmp_path):
        from claude_mpm.quality.wwl_checker import analyze_file

        f = tmp_path / "broken.py"
        f.write_text("def foo(:\n    pass", encoding="utf-8")
        violations = analyze_file(f, repo_root=tmp_path)
        assert violations == []

    def test_relpath_uses_forward_slashes(self, tmp_path):
        from claude_mpm.quality.wwl_checker import analyze_file

        f = _write_py(tmp_path, "slashes.py", "x = 1")
        violations = analyze_file(f, repo_root=tmp_path)
        for v in violations:
            assert "\\" not in v.relpath, "relpaths must use forward slashes"


class TestBaselineIO:
    """Tests for :func:`load_baseline` and :func:`save_baseline`."""

    def test_load_nonexistent_baseline_returns_empty(self, tmp_path):
        from claude_mpm.quality.wwl_checker import load_baseline

        keys = load_baseline(tmp_path / "nonexistent.json")
        assert keys == frozenset()

    def test_save_and_reload(self, tmp_path):
        from claude_mpm.quality.wwl_checker import (
            MISSING_FILE_WWL,
            Violation,
            load_baseline,
            save_baseline,
        )

        violations = [
            Violation(
                relpath="src/foo.py",
                qualname="",
                violation_type=MISSING_FILE_WWL,
                description="desc",
            ),
            Violation(
                relpath="src/bar.py",
                qualname="MyClass.method",
                violation_type="MISSING_UNIT_WWL",
                description="desc2",
            ),
        ]
        path = tmp_path / ".wwl-baseline.json"
        save_baseline(violations, path)
        keys = load_baseline(path)
        assert "src/foo.py::" in keys
        assert "src/bar.py::MyClass.method" in keys

    def test_save_is_sorted(self, tmp_path):
        from claude_mpm.quality.wwl_checker import (
            MISSING_FILE_WWL,
            Violation,
            save_baseline,
        )

        violations = [
            Violation("zzz.py", "z", MISSING_FILE_WWL, "d"),
            Violation("aaa.py", "a", MISSING_FILE_WWL, "d"),
        ]
        path = tmp_path / "sorted.json"
        save_baseline(violations, path)
        data = json.loads(path.read_text())
        keys = [f"{d['relpath']}::{d['qualname']}" for d in data]
        assert keys == sorted(keys)

    def test_load_invalid_json_returns_empty(self, tmp_path):
        from claude_mpm.quality.wwl_checker import load_baseline

        path = tmp_path / "bad.json"
        path.write_text("{not valid json", encoding="utf-8")
        keys = load_baseline(path)
        assert keys == frozenset()


class TestCheckSourceTree:
    """Tests for :func:`check_source_tree` — enforcement modes."""

    def _make_violating_tree(self, tmp_path: Path) -> Path:
        """Create a minimal source tree with one MISSING_FILE_WWL violation."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("x = 1", encoding="utf-8")
        return src

    def test_enforcement_off_never_fails(self, tmp_path):
        from claude_mpm.quality.wwl_checker import check_source_tree

        src = self._make_violating_tree(tmp_path)
        result = check_source_tree(src_root=src, enforcement="off")
        assert not result.failed
        assert len(result.violations) > 0

    def test_enforcement_strict_fails_on_any_violation(self, tmp_path):
        from claude_mpm.quality.wwl_checker import check_source_tree

        src = self._make_violating_tree(tmp_path)
        result = check_source_tree(src_root=src, enforcement="strict")
        assert result.failed

    def test_enforcement_baseline_passes_when_all_in_baseline(self, tmp_path):
        from claude_mpm.quality.wwl_checker import (
            check_source_tree,
            generate_baseline,
        )

        src = self._make_violating_tree(tmp_path)
        baseline_path = tmp_path / ".wwl-baseline.json"
        # Generate baseline first
        generate_baseline(src, baseline_path)
        # Now run in baseline mode — should be green
        result = check_source_tree(
            src_root=src,
            baseline_path=baseline_path,
            enforcement="baseline",
        )
        assert not result.failed
        assert result.new_violations == []

    def test_enforcement_baseline_fails_on_new_violation(self, tmp_path):
        from claude_mpm.quality.wwl_checker import (
            check_source_tree,
            generate_baseline,
        )

        src = self._make_violating_tree(tmp_path)
        baseline_path = tmp_path / ".wwl-baseline.json"
        generate_baseline(src, baseline_path)

        # Add a new file without WWL after baseline was captured
        (src / "new_mod.py").write_text("y = 2", encoding="utf-8")

        result = check_source_tree(
            src_root=src,
            baseline_path=baseline_path,
            enforcement="baseline",
        )
        # new_mod.py is not in baseline → new violation → should fail
        assert result.failed
        new_relpaths = {v.relpath for v in result.new_violations}
        assert any("new_mod" in rp for rp in new_relpaths)

    def test_generate_baseline_makes_run_green(self, tmp_path):
        from claude_mpm.quality.wwl_checker import (
            check_source_tree,
            generate_baseline,
        )

        src = self._make_violating_tree(tmp_path)
        baseline_path = tmp_path / "baseline.json"
        captured = generate_baseline(src, baseline_path)
        assert len(captured) > 0

        result = check_source_tree(
            src_root=src,
            baseline_path=baseline_path,
            enforcement="baseline",
        )
        assert not result.failed


# ===========================================================================
# UNIT TESTS: configuration integration
# ===========================================================================


class TestWWLConfig:
    """Tests for WWL-related configuration keys in sld_config and core.config."""

    def test_sld_config_has_wwl_defaults(self):
        """get_sld_default_config() must include wwl sub-dict with expected keys."""
        from claude_mpm.config.sld_config import get_sld_default_config

        cfg = get_sld_default_config()
        assert "spec_linked_docs" in cfg
        sld = cfg["spec_linked_docs"]
        assert "wwl" in sld, "wwl sub-dict missing from sld default config"
        wwl = sld["wwl"]
        assert "file_level_required" in wwl
        assert "function_line_threshold" in wwl
        assert "complexity_threshold" in wwl
        assert "enforcement" in wwl
        assert wwl["function_line_threshold"] == 50
        assert wwl["complexity_threshold"] == 10
        assert wwl["enforcement"] == "baseline"

    def test_sld_instruction_mentions_wwl(self):
        """The SLD instruction block injected into agent prompts must mention WWL."""
        from claude_mpm.config.sld_config import get_sld_instruction_block

        block = get_sld_instruction_block()
        assert "WWL" in block, (
            "SLD instruction block must mention WWL for agents to know about it"
        )
