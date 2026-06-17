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


# ===========================================================================
# MUTATION-HARDENING TESTS (target specific surviving mutants)
# ===========================================================================


class TestModuleConstants:
    """Pin the public constant values that flow into the baseline JSON schema
    and the default thresholds/enforcement mode.  Targets the literal/number/
    None mutants on lines 45, 48, 51, 54, 55."""

    def test_default_thresholds_have_documented_values(self):
        """DEFAULT_LINE_THRESHOLD == 50 and DEFAULT_COMPLEXITY_THRESHOLD == 10.

        Targets the numeric off-by-one mutants on the threshold constants
        (lines 45, 48). These values are the documented WWL contract (LOC 50,
        McCabe CC 10); a silent drift to 51/11 would shift every CI decision.
        """
        from claude_mpm.quality.wwl_checker import (
            DEFAULT_COMPLEXITY_THRESHOLD,
            DEFAULT_LINE_THRESHOLD,
        )

        assert DEFAULT_LINE_THRESHOLD == 50
        assert DEFAULT_COMPLEXITY_THRESHOLD == 10

    def test_default_enforcement_is_baseline(self):
        """DEFAULT_ENFORCEMENT is exactly the string "baseline".

        Targets the string-literal and None mutants on line 51. The default
        enforcement mode must be the ratchet mode "baseline"; a None or mangled
        value would change the meaning of CheckResult.failed for every default
        run.
        """
        from claude_mpm.quality.wwl_checker import DEFAULT_ENFORCEMENT

        assert DEFAULT_ENFORCEMENT == "baseline"
        assert isinstance(DEFAULT_ENFORCEMENT, str)

    def test_violation_type_codes_have_exact_values(self):
        """The violation-type codes are exactly their documented strings.

        Targets the string-literal and None mutants on lines 54-55. These codes
        are serialised into .wwl-baseline.json (the `violation_type` field) and
        compared by load/save; renaming them silently invalidates every baseline
        entry written with the old name.
        """
        from claude_mpm.quality.wwl_checker import (
            MISSING_FILE_WWL,
            MISSING_UNIT_WWL,
        )

        assert MISSING_FILE_WWL == "MISSING_FILE_WWL"
        assert MISSING_UNIT_WWL == "MISSING_UNIT_WWL"


class TestViolationDataclass:
    """Pin immutability and the to_dict serialisation schema of Violation.
    Targets frozen=True (line 92) and the to_dict key literals (lines 126-127)."""

    def test_violation_is_frozen(self):
        """Violation instances are immutable (frozen dataclass).

        Targets `@dataclass(frozen=True)` -> `frozen=False` (line 92). Violations
        are stored in frozensets (CheckResult.baseline_keys) and used as stable
        baseline keys; mutating one would corrupt set membership. Frozen must
        raise on attribute assignment.
        """
        import dataclasses

        from claude_mpm.quality.wwl_checker import MISSING_FILE_WWL, Violation

        v = Violation("src/x.py", "", MISSING_FILE_WWL, "desc")
        with pytest.raises(dataclasses.FrozenInstanceError):
            v.relpath = "mutated"  # type: ignore[misc]

    def test_to_dict_has_exact_schema_keys(self):
        """to_dict() emits exactly relpath/qualname/violation_type/description.

        Targets the mangled key-literal mutants on lines 126-127. load_baseline
        and the baseline-schema test read these exact keys; a renamed key would
        produce baseline entries that load_baseline silently drops.
        """
        from claude_mpm.quality.wwl_checker import MISSING_UNIT_WWL, Violation

        v = Violation("src/x.py", "Cls.method", MISSING_UNIT_WWL, "detail")
        d = v.to_dict()

        assert set(d.keys()) == {
            "relpath",
            "qualname",
            "violation_type",
            "description",
        }
        assert d["violation_type"] == MISSING_UNIT_WWL
        assert d["description"] == "detail"


class TestCheckResultFailedPredicate:
    """Pin the strict-vs-baseline failure predicate. Targets the "strict"
    literal and the `> 0` comparison on lines 152-153."""

    def test_strict_mode_uses_total_violations_not_new(self):
        """strict mode fails on ANY violation, even when new_violations is empty.

        Targets the `== "strict"` literal mutant (line 152). We build a result in
        strict mode that has a violation but an EMPTY new_violations list (as if
        every violation were already in the baseline). Real code: the strict
        branch keys off `violations`, so failed is True. Mutant ("strict" mangled
        to a non-matching string): falls through to the baseline branch, which
        keys off the empty new_violations, so failed would be False.
        """
        from claude_mpm.quality.wwl_checker import (
            MISSING_FILE_WWL,
            CheckResult,
            Violation,
        )

        v = Violation("src/x.py", "", MISSING_FILE_WWL, "d")
        result = CheckResult(
            violations=[v],
            new_violations=[],  # nothing "new", but strict ignores that
            enforcement="strict",
        )
        assert result.failed is True

    def test_strict_mode_with_zero_violations_does_not_fail(self):
        """strict mode with zero violations is NOT a failure.

        Targets the `len(self.violations) > 0` -> `>= 0` mutant (line 153). With
        an empty violation list, real `0 > 0` is False (pass); the mutant
        `0 >= 0` is True and would wrongly fail a clean strict run.
        """
        from claude_mpm.quality.wwl_checker import CheckResult

        result = CheckResult(
            violations=[],
            new_violations=[],
            enforcement="strict",
        )
        assert result.failed is False


class TestCountBranchesNestedAndAccumulation:
    """Pin the DFS skip-into-nested-defs and the accumulation operators in
    _count_branches.  Targets the continue->break (line 198) and the
    comprehension/BoolOp count operators (lines 202, 208)."""

    def _fn(self, src: str):
        import ast

        return ast.parse(textwrap.dedent(src)).body[0]

    def test_branches_after_nested_def_are_still_counted(self):
        """An outer branch following a nested def must still be counted.

        Targets the `continue` -> `break` mutant (line 198). Source order places
        the outer `if` FIRST and the nested `def` LAST, so the nested def is
        popped from the DFS stack before the `if` is counted. Real code uses
        `continue` (skip just the nested def, keep walking) -> count 1. The
        `break` mutant aborts the whole walk at the nested def -> count 0.
        """
        from claude_mpm.quality.wwl_checker import _count_branches

        fn = self._fn(
            """
            def outer(x):
                if x:
                    return 2
                def inner(y):
                    if y:
                        return 1
            """
        )
        assert _count_branches(fn) == 1

    def test_comprehension_if_count_accumulates(self):
        """Comprehension if-clauses ADD to the running branch count.

        Targets the `count += len(child.ifs)` mutants (line 202): `=` (reset) and
        `-=` (subtract). Source places the comprehension FIRST and an `if`
        statement LAST so the comprehension is processed before the `if` is
        counted; reset/subtract therefore diverge from accumulate. Real total:
        2 (comp ifs) + 1 (if) = 3. `=` mutant -> 2, `-=` mutant -> -1.
        """
        from claude_mpm.quality.wwl_checker import _count_branches

        fn = self._fn(
            """
            def f(xs):
                r = [v for v in xs if v if v]
                if xs:
                    pass
            """
        )
        assert _count_branches(fn) == 3

    def test_boolop_count_accumulates(self):
        """BoolOp operands ADD to the running branch count.

        Targets the `count += len(child.values) - 1` -> `count =` mutant
        (line 208). Source places the `and` expression FIRST and an `if` LAST.
        Real total: 2 (a and b and c -> 3 values -> +2) + 1 (if) = 3; the reset
        mutant yields 2.
        """
        from claude_mpm.quality.wwl_checker import _count_branches

        fn = self._fn(
            """
            def f(a, b, c):
                r = a and b and c
                if a:
                    pass
            """
        )
        assert _count_branches(fn) == 3


class TestNodeLocGuard:
    """Pin the missing-lineno guard in _node_loc. Targets the `or`->`and`
    guard and the `return 0` literal on lines 226-227, using synthetic nodes
    that real Python ASTs never produce (only one of lineno/end_lineno set)."""

    def test_partial_lineno_returns_zero(self):
        """A node with lineno set but end_lineno missing returns 0.

        Targets the `start is None or end is None` -> `and` mutant (line 226).
        With start=5, end=None: real `or` is True -> return 0. The `and` mutant
        is False -> falls through to `end - start` (None - 5) and would raise
        TypeError.
        """
        from types import SimpleNamespace

        from claude_mpm.quality.wwl_checker import _node_loc

        node = SimpleNamespace(lineno=5, end_lineno=None)
        assert _node_loc(node) == 0


class TestHasWWLDocstringGuards:
    """Pin the empty-body and non-string-docstring guards in
    _has_wwl_docstring. Targets the `return False` literals on lines 247, 253."""

    def test_empty_body_is_not_wwl(self):
        """A node with an empty body has no WWL docstring (returns False).

        Targets the `if not body: return False` -> `return True` mutant
        (line 247). An empty module body must NOT be reported as having a WWL
        docstring.
        """
        import ast

        from claude_mpm.quality.wwl_checker import _has_wwl_docstring

        empty_module = ast.parse("")  # body == []
        assert _has_wwl_docstring(empty_module) is False

    def test_non_string_first_expr_is_not_wwl(self):
        """A first statement that is a non-string constant is not a docstring.

        Targets the `return False` -> `return True` mutant on line 253 (the
        guard for `not isinstance(val.value, str)`). Here the function's first
        statement is the integer constant 42 (an Expr whose value is a numeric
        Constant), which is not a docstring and must not satisfy WWL.
        """
        import ast

        from claude_mpm.quality.wwl_checker import _has_wwl_docstring

        fn = ast.parse(
            textwrap.dedent(
                """
                def f():
                    42
                """
            )
        ).body[0]
        assert _has_wwl_docstring(fn) is False


class TestPureReexportScanContinues:
    """Pin that the re-export scan keeps inspecting statements after each
    exempt one (it must not stop early). Targets the three continue->break
    mutants on lines 301, 305, 311."""

    def _write(self, tmp_path, body: str):
        f = tmp_path / "__init__.py"
        f.write_text(textwrap.dedent(body), encoding="utf-8")
        return f

    def test_constant_then_real_logic_is_not_pure(self, tmp_path):
        """A docstring/constant followed by a function def is NOT pure re-export.

        Targets the `continue` -> `break` mutant on the string/constant arm
        (line 301). The first statement is a docstring (exempt); the second is a
        real `def` (non-exempt). Real `continue` keeps scanning and reaches the
        def -> returns False. The `break` mutant stops after the docstring and
        never sees the def -> would wrongly return True (pure).
        """
        from claude_mpm.quality.wwl_checker import _is_pure_reexport_module

        f = self._write(
            tmp_path,
            '''
            """just a summary"""

            def helper():
                return 1
            ''',
        )
        assert _is_pure_reexport_module(f) is False

    def test_all_assign_then_real_logic_is_not_pure(self, tmp_path):
        """An __all__ = [...] followed by real logic is NOT pure re-export.

        Targets the `continue` -> `break` mutant on the `__all__` Assign arm
        (line 305).
        """
        from claude_mpm.quality.wwl_checker import _is_pure_reexport_module

        f = self._write(
            tmp_path,
            """
            __all__ = ["foo"]

            def helper():
                return 1
            """,
        )
        assert _is_pure_reexport_module(f) is False

    def test_all_augassign_then_real_logic_is_not_pure(self, tmp_path):
        """An __all__ += [...] followed by real logic is NOT pure re-export.

        Targets the `continue` -> `break` mutant on the `__all__` AugAssign arm
        (line 311).
        """
        from claude_mpm.quality.wwl_checker import _is_pure_reexport_module

        f = self._write(
            tmp_path,
            """
            __all__ = ["foo"]
            __all__ += ["bar"]

            def helper():
                return 1
            """,
        )
        assert _is_pure_reexport_module(f) is False


class TestClassUnitThresholds:
    """Pin the class cyclomatic-complexity base (1 + branches) and the
    over-threshold predicate in _iter_units.  Targets lines 356 and 358.

    A class's CC counts only class-body-level branch nodes (method bodies are
    skipped as separate units), so N body-level `if` statements give CC = 1 + N.
    """

    def _class_with_ifs(self, n: int) -> str:
        ifs = "\n".join("    if True:\n        pass" for _ in range(n))
        return "class C:\n" + ifs + "\n"

    def _units(self, src: str, line_threshold: int, complexity_threshold: int):
        import ast

        from claude_mpm.quality.wwl_checker import _iter_units

        tree = ast.parse(textwrap.dedent(src))
        return list(_iter_units(tree, line_threshold, complexity_threshold))

    def test_class_cc_base_is_one_plus_branches(self, tmp_path):
        """A class with CC exactly == threshold is NOT over-threshold.

        9 body-level ifs -> CC = 1 + 9 = 10. With complexity_threshold=10 and a
        large line_threshold, `10 > 10` is False, so the class yields no unit.

        Targets two mutants on line 356/358 at once:
          - `cc = 1 + ...` -> `cc = 2 + ...` (id 121): CC would be 11 > 10 ->
            wrongly flagged.
          - `cc >` -> `cc >=` (id 126, line 358): `10 >= 10` True -> wrongly
            flagged.
        Real behaviour yields no unit for this class.
        """
        src = self._class_with_ifs(9)  # CC = 10, LOC = 19
        units = self._units(src, line_threshold=1000, complexity_threshold=10)
        names = [qn for (_n, qn, _loc, _cc, _w) in units]
        assert "C" not in names, (
            "a class whose CC equals the threshold must not be over-threshold"
        )

    def test_class_cc_base_not_inverted(self, tmp_path):
        """A class with CC above the threshold IS flagged (base term not negated).

        10 body-level ifs -> CC = 1 + 10 = 11 > 10 -> the class is a unit.
        Targets the `1 + branches` -> `1 - branches` mutant (id 122, line 356),
        which would make CC = 1 - 10 = -9 (never over threshold).
        """
        src = self._class_with_ifs(10)  # CC = 11, LOC = 21
        units = self._units(src, line_threshold=1000, complexity_threshold=10)
        flagged = [(qn, cc) for (_n, qn, _loc, cc, _w) in units]
        assert ("C", 11) in flagged, (
            "a class with CC 11 must be reported over a threshold of 10"
        )

    def test_loc_boundary_is_strict_greater_than(self, tmp_path):
        """LOC exactly equal to the threshold is NOT over-threshold.

        The 9-if class has LOC 19 and CC 10. With line_threshold=19 and
        complexity_threshold=10, neither `19 > 19` nor `10 > 10` is True, so the
        class yields no unit. Targets the `loc >` -> `loc >=` mutant (id 125,
        line 358), which would flag it via `19 >= 19`.
        """
        src = self._class_with_ifs(9)  # LOC = 19, CC = 10
        units = self._units(src, line_threshold=19, complexity_threshold=10)
        names = [qn for (_n, qn, _loc, _cc, _w) in units]
        assert "C" not in names, "LOC equal to the threshold must use strict > (not >=)"

    def test_loc_or_complexity_either_triggers(self, tmp_path):
        """A large but simple class is flagged via LOC alone (OR, not AND).

        A class with many simple statements (CC = 1) but LOC above the line
        threshold must be flagged. Targets the `loc > lt or cc > ct` -> `and`
        mutant (id 127, line 358): under `and` the low CC would veto the LOC
        trigger and the class would be missed.
        """
        # 20 plain assignments -> CC = 1, LOC well above 10.
        body = "\n".join(f"    x{i} = {i}" for i in range(20))
        src = "class Big:\n" + body + "\n"
        units = self._units(src, line_threshold=10, complexity_threshold=10)
        names = [qn for (_n, qn, _loc, _cc, _w) in units]
        assert "Big" in names, (
            "a large, low-complexity class must be flagged by LOC alone (OR semantics)"
        )


class TestLoadBaselineFieldGuard:
    """Pin the both-fields-required guard in load_baseline and the parents=True
    in save_baseline. Targets lines 464 and 480."""

    def test_entry_missing_qualname_is_skipped_not_fatal(self, tmp_path):
        """An entry missing `qualname` is skipped; valid entries still load.

        Targets the `"relpath" in entry and "qualname" in entry` -> `or` mutant
        (line 464). The baseline has one complete entry plus one entry missing
        `qualname`. Real `and`: the incomplete entry is skipped (its key is never
        built), so the good key loads. The `or` mutant: the incomplete entry
        passes the filter, then `entry['qualname']` raises KeyError, which the
        except clause turns into an empty frozenset -> the good key is LOST.
        """
        import json

        from claude_mpm.quality.wwl_checker import load_baseline

        path = tmp_path / ".wwl-baseline.json"
        path.write_text(
            json.dumps(
                [
                    {
                        "relpath": "src/good.py",
                        "qualname": "Good.method",
                        "violation_type": "MISSING_UNIT_WWL",
                        "description": "d",
                    },
                    {"relpath": "src/incomplete.py"},  # missing qualname
                ]
            ),
            encoding="utf-8",
        )

        keys = load_baseline(path)
        assert "src/good.py::Good.method" in keys, (
            "a valid entry must still load when another entry is incomplete"
        )

    def test_save_baseline_creates_missing_parent_dirs(self, tmp_path):
        """save_baseline creates missing parent directories (parents=True).

        Targets the `mkdir(parents=True, ...)` -> `parents=False` mutant
        (line 480). Writing to a path whose grandparent does not yet exist must
        succeed; with parents=False, mkdir raises FileNotFoundError.
        """
        from claude_mpm.quality.wwl_checker import (
            MISSING_FILE_WWL,
            Violation,
            load_baseline,
            save_baseline,
        )

        nested = tmp_path / "a" / "b" / "c" / ".wwl-baseline.json"
        assert not nested.parent.exists()

        violations = [Violation("src/x.py", "", MISSING_FILE_WWL, "d")]
        save_baseline(violations, nested)  # must create a/b/c

        assert nested.exists()
        assert "src/x.py::" in load_baseline(nested)
