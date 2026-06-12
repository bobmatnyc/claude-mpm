"""
claude_mpm.quality.wwl_checker — WWL granularity sanity-checker for the SLD feature.

WHAT: Walks ``src/claude_mpm/**/*.py``, computes per-file and per-unit metrics
(module WWL present, function/method/class LOC, cyclomatic complexity), and
produces a list of violations (MISSING_FILE_WWL, MISSING_UNIT_WWL) for units
that exceed configurable thresholds.  Supports three enforcement modes via a
baseline/ratchet mechanism: ``off`` (report only), ``baseline`` (fail only on
violations absent from a saved baseline), and ``strict`` (fail on any violation).
Provides ``generate_baseline()`` to capture the repo's current violation set so
adoption does not break the build.

WHY: The WWL model (WHAT / WHY / LINK) extends SLD traceability to code
granularity.  Without an automated check, large or complex units accumulate
without documentation.  The baseline/ratchet approach lets the team adopt the
check immediately without a big-bang backfill: legacy gaps go into the baseline
and are tolerated; new code above the thresholds is flagged on the first PR.
Complexity threshold follows McCabe 1976 / NIST SP 500-235 (CC > 10 = high risk);
LOC threshold of 50 mirrors common linter defaults.  Both are configurable.

References
----------
McCabe, T.J. (1976). A complexity measure. IEEE Trans. Software Eng., SE-2(4).
NIST SP 500-235 (1996). Structured testing: a testing methodology using the
    cyclomatic complexity metric.
SLD convention: docs/specs/README.md
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

# ---------------------------------------------------------------------------
# Constants / defaults
# ---------------------------------------------------------------------------

#: Default LOC threshold — units exceeding this require a WWL doc-comment.
DEFAULT_LINE_THRESHOLD: int = 50

#: Default cyclomatic complexity threshold.
DEFAULT_COMPLEXITY_THRESHOLD: int = 10

#: Default enforcement mode.
DEFAULT_ENFORCEMENT: str = "baseline"

#: Violation type codes.
MISSING_FILE_WWL = "MISSING_FILE_WWL"
MISSING_UNIT_WWL = "MISSING_UNIT_WWL"

#: Regex that matches any SPEC-* ID (used to detect LINK satisfaction).
_SPEC_ID_RE = re.compile(r"SPEC-[A-Z]+-\d+~\d+")

#: Regex patterns that identify WWL components in a docstring.
#: WHAT: or WHY: on their own line (case-insensitive leading whitespace allowed).
_WWL_WHAT_RE = re.compile(r"^\s*WHAT\s*:", re.MULTILINE | re.IGNORECASE)
_WWL_WHY_RE = re.compile(r"^\s*WHY\s*:", re.MULTILINE | re.IGNORECASE)

# ---------------------------------------------------------------------------
# Branch-node AST types for cyclomatic complexity (McCabe 1976)
# ---------------------------------------------------------------------------
# Count: if, for, while, and (BoolOp), or (BoolOp), ExceptHandler, with,
# comprehension if-clause, ternary (IfExp), match case arm.
_BRANCH_TYPES = (
    ast.If,
    ast.For,
    ast.While,
    ast.ExceptHandler,
    ast.With,
    ast.AsyncWith,
    ast.AsyncFor,
    ast.IfExp,  # ternary
    ast.comprehension,
    ast.match_case,  # Python 3.10+
)

# BoolOp with And/Or adds one branch per extra operand
_BOOL_OP_TYPES = (ast.And, ast.Or)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Violation:
    """A single WWL violation.

    WHAT: Represents one missing-WWL finding: the file it came from, the stable
    key used for baseline comparisons, the violation type code, and a human
    description.

    WHY: Immutable dataclass keeps violations hashable and serialisable to JSON
    without extra code.
    """

    relpath: str
    """Relative path from the repo root (forward-slash normalised)."""

    qualname: str
    """Fully-qualified name of the violating unit, or '' for file-level."""

    violation_type: str
    """MISSING_FILE_WWL or MISSING_UNIT_WWL."""

    description: str
    """Human-readable detail."""

    @property
    def key(self) -> str:
        """Stable key used in the baseline JSON (relpath::qualname)."""
        return f"{self.relpath}::{self.qualname}"

    def to_dict(self) -> dict:
        """Serialise to a JSON-compatible dict."""
        return {
            "relpath": self.relpath,
            "qualname": self.qualname,
            "violation_type": self.violation_type,
            "description": self.description,
        }


@dataclass
class CheckResult:
    """Aggregated result from :func:`check_source_tree`.

    WHAT: Bundles all violations found, the subset that are new (not in the
    baseline), and whether the enforcement run is considered a failure.

    WHY: Returning a structured object lets callers (tests, CLI) inspect
    individual violation lists without re-parsing the raw output.
    """

    violations: list[Violation] = field(default_factory=list)
    new_violations: list[Violation] = field(default_factory=list)
    enforcement: str = DEFAULT_ENFORCEMENT
    baseline_keys: frozenset[str] = field(default_factory=frozenset)

    @property
    def failed(self) -> bool:
        """True when the result represents a CI failure under the chosen mode."""
        if self.enforcement == "off":
            return False
        if self.enforcement == "strict":
            return len(self.violations) > 0
        # baseline mode: fail only on new violations
        return len(self.new_violations) > 0


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _count_branches(node: ast.AST) -> int:
    """Count branch nodes under *node* (inclusive) for cyclomatic complexity.

    WHAT: Traverses the AST of a function/method body and returns the number of
    branch-inducing nodes: if, for, while, and/or operands, except handlers,
    with statements, async variants, ternary expressions, comprehension if-
    clauses, and match-case arms.  Does NOT recurse into nested function or
    class definitions (those are separate units with their own complexity).

    WHY: McCabe's formula CC = E - N + 2P simplifies to 1 + #branch-nodes for
    a single-entry single-exit function.  Counting branch nodes directly (rather
    than edges/nodes in the CFG) is the standard approximation used by radon,
    flake8-mccabe, and similar tools.  Excluding nested defs prevents double-
    counting: each nested function is checked independently.

    Parameters
    ----------
    node : ast.AST
        Typically an ``ast.FunctionDef`` or ``ast.AsyncFunctionDef``.

    Returns
    -------
    int
        Branch count (add 1 in the caller to get CC).
    """
    # Use an explicit DFS stack so we can stop descending into nested
    # function/class defs.  ast.walk does not support early cut-off of
    # subtrees, so we must drive the traversal manually.
    count = 0
    stack: list[ast.AST] = list(ast.iter_child_nodes(node))
    while stack:
        child = stack.pop()
        # Do not descend into nested function/class defs — they are
        # separate units, each analysed independently.
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(child, _BRANCH_TYPES):
            if isinstance(child, ast.comprehension):
                # Each 'if' clause in a comprehension adds a branch
                count += len(child.ifs)
            else:
                count += 1
        elif isinstance(child, ast.BoolOp):
            if isinstance(child.op, _BOOL_OP_TYPES):
                # Each extra operand beyond the first adds a branch
                count += len(child.values) - 1
        # Push children of this node (they are NOT a nested def boundary)
        stack.extend(ast.iter_child_nodes(child))
    return count


def _node_loc(node: ast.AST) -> int:
    """Return the physical line count of an AST node.

    WHAT: Computes ``end_lineno - lineno + 1`` for the node.  Returns 0 when
    lineno information is absent (e.g., synthetic nodes).

    WHY: ast.get_source_segment is not used because it requires the raw source
    string; lineno arithmetic is sufficient for LOC counting and avoids passing
    source text everywhere.
    """
    start = getattr(node, "lineno", None)
    end = getattr(node, "end_lineno", None)
    if start is None or end is None:
        return 0
    return end - start + 1


def _has_wwl_docstring(node: ast.AST) -> bool:
    """Return True when *node* has a docstring containing WHAT: and WHY: lines.

    WHAT: Checks the first statement of a module, function, or class body for a
    string constant (the docstring convention).  Accepts the docstring if it
    contains both ``WHAT:`` and ``WHY:`` markers (case-insensitive, any
    indentation).  A ``References:`` block containing a ``SPEC-*`` ID also
    satisfies the LINK part but is not required for this check.

    WHY: WHAT + WHY are the mandatory parts of WWL at the granularity level.
    LINK is required at the spec level (docs/specs/) but optional at the code
    level when the unit is not governed by a specific spec section; ``LINK:
    none`` is the explicit flag for a backfill gap.
    """
    body = getattr(node, "body", [])
    if not body:
        return False
    first = body[0]
    if not isinstance(first, ast.Expr):
        return False
    val = first.value
    if not isinstance(val, ast.Constant) or not isinstance(val.value, str):
        return False
    doc = val.value
    return bool(_WWL_WHAT_RE.search(doc) and _WWL_WHY_RE.search(doc))


def _qualname_of(node: ast.AST, parent_qualname: str) -> str:
    """Build a dotted qualname string for a function or class node."""
    name = getattr(node, "name", "<anonymous>")
    if parent_qualname:
        return f"{parent_qualname}.{name}"
    return name


def _is_pure_reexport_module(filepath: Path) -> bool:
    """Return True if this file is a pure re-export module exempt from module-level WWL.

    WHAT: Detects ``__init__.py`` files that contain only imports, ``__all__``
          assignments, and string literals / pass statements — no real logic.
    WHY:  The WWL docs standard (#798) exempts these modules from the
          module-level WHAT/WHY requirement since they carry no logic worth
          documenting.

    Parameters
    ----------
    filepath : Path
        Absolute path to the ``.py`` file under inspection.

    Returns
    -------
    bool
        True only when the file is named ``__init__.py`` AND every top-level
        statement is an import, an ``__all__`` (Aug)Assign, a string/constant
        expression, or ``pass``.  False otherwise (including on SyntaxError,
        so broken files fall through to the normal checker).
    """
    if filepath.name != "__init__.py":
        return False
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return False

    for stmt in tree.body:
        if isinstance(stmt, (ast.Import, ast.ImportFrom, ast.Pass)):
            continue
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            # String literals / docstrings / other bare constants.
            continue
        if isinstance(stmt, ast.Assign) and all(
            isinstance(t, ast.Name) and t.id == "__all__" for t in stmt.targets
        ):
            continue
        if (
            isinstance(stmt, ast.AugAssign)
            and isinstance(stmt.target, ast.Name)
            and stmt.target.id == "__all__"
        ):
            continue
        # Anything else (function/class def, real assignment, etc.) → not pure.
        return False
    return True


# ---------------------------------------------------------------------------
# Per-file analysis
# ---------------------------------------------------------------------------


def _iter_units(
    tree: ast.Module,
    line_threshold: int,
    complexity_threshold: int,
) -> Iterator[tuple[ast.AST, str, int, int, bool]]:
    """Yield (node, qualname, loc, complexity, has_wwl) for over-threshold units.

    WHAT: Performs a depth-first walk of the module AST, visiting every
    FunctionDef, AsyncFunctionDef, and ClassDef.  For each unit, computes LOC
    and cyclomatic complexity (CC).  Yields the unit only when it exceeds EITHER
    the LOC threshold OR the CC threshold.

    WHY: Yielding only over-threshold units keeps the violation list focused on
    units that benefit from documentation.  Units under both thresholds are
    intentionally skipped; they may still carry WWL doc-comments voluntarily.
    """

    def _walk(
        node: ast.AST, parent_qn: str
    ) -> Iterator[tuple[ast.AST, str, int, int, bool]]:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qn = _qualname_of(child, parent_qn)
                loc = _node_loc(child)
                cc = 1 + _count_branches(child)
                has_wwl = _has_wwl_docstring(child)
                if loc > line_threshold or cc > complexity_threshold:
                    yield child, qn, loc, cc, has_wwl
                # Recurse into nested functions / methods
                yield from _walk(child, qn)
            elif isinstance(child, ast.ClassDef):
                qn = _qualname_of(child, parent_qn)
                loc = _node_loc(child)
                # Classes: count methods' branch-nodes for a rough class CC
                cc = 1 + _count_branches(child)
                has_wwl = _has_wwl_docstring(child)
                if loc > line_threshold or cc > complexity_threshold:
                    yield child, qn, loc, cc, has_wwl
                yield from _walk(child, qn)

    yield from _walk(tree, "")


def analyze_file(
    path: Path,
    repo_root: Path,
    line_threshold: int = DEFAULT_LINE_THRESHOLD,
    complexity_threshold: int = DEFAULT_COMPLEXITY_THRESHOLD,
) -> list[Violation]:
    """Analyze one Python file and return its WWL violations.

    WHAT: Reads *path*, parses it with the stdlib ``ast`` module, checks the
    module-level docstring for WHAT+WHY markers, and checks every over-threshold
    function/method/class for a WWL doc-comment.  Returns a (possibly empty)
    list of :class:`Violation` instances.  Returns an empty list if the file
    cannot be parsed (parse errors are silently skipped so the checker does not
    break on generated or intentionally invalid files).

    WHY: A single-file entry point makes unit testing straightforward (tests can
    call this with a tmp_path file) and lets the tree walker stay thin.

    Parameters
    ----------
    path : Path
        Absolute path to the ``.py`` file.
    repo_root : Path
        Repo root used to compute :attr:`Violation.relpath`.
    line_threshold : int
        LOC threshold above which a WWL doc-comment is required.
    complexity_threshold : int
        Cyclomatic complexity threshold above which a WWL doc-comment is required.

    Returns
    -------
    list[Violation]
        All violations found in the file.
    """
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    relpath = path.relative_to(repo_root).as_posix()
    violations: list[Violation] = []

    # --- Module-level WWL check ---
    has_module_wwl = _has_wwl_docstring(tree)
    if not has_module_wwl and not _is_pure_reexport_module(path):
        violations.append(
            Violation(
                relpath=relpath,
                qualname="",
                violation_type=MISSING_FILE_WWL,
                description=f"Module-level WWL (WHAT: + WHY:) missing in {relpath}",
            )
        )

    # --- Per-unit WWL check ---
    for _node, qn, loc, cc, has_wwl in _iter_units(
        tree, line_threshold, complexity_threshold
    ):
        if not has_wwl:
            violations.append(
                Violation(
                    relpath=relpath,
                    qualname=qn,
                    violation_type=MISSING_UNIT_WWL,
                    description=(
                        f"{qn} in {relpath} exceeds thresholds "
                        f"(LOC={loc}, CC={cc}) but has no WWL doc-comment"
                    ),
                )
            )

    return violations


# ---------------------------------------------------------------------------
# Baseline I/O
# ---------------------------------------------------------------------------


def load_baseline(baseline_path: Path) -> frozenset[str]:
    """Load a baseline JSON file and return a frozenset of violation keys.

    WHAT: Reads *baseline_path* (a JSON array of violation dicts), extracts the
    ``relpath::qualname`` key from each entry, and returns the result as an
    immutable frozenset.  Returns an empty frozenset when the file does not
    exist.

    WHY: An empty frozenset is the safe default: if there is no baseline every
    violation is treated as new, which is correct for the strict mode and for
    fresh repositories.
    """
    if not baseline_path.exists():
        return frozenset()
    try:
        data = json.loads(baseline_path.read_text(encoding="utf-8"))
        return frozenset(
            f"{entry['relpath']}::{entry['qualname']}"
            for entry in data
            if "relpath" in entry and "qualname" in entry
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        return frozenset()


def save_baseline(violations: list[Violation], baseline_path: Path) -> None:
    """Write *violations* to *baseline_path* as a JSON array.

    WHAT: Serialises the list of :class:`Violation` objects to a stable,
    sorted JSON array and writes it to *baseline_path*.  Creates parent
    directories as needed.

    WHY: Sorting by key ensures the baseline file has a deterministic diff,
    making code-review and git history useful.
    """
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    entries = sorted(
        (v.to_dict() for v in violations),
        key=lambda d: f"{d['relpath']}::{d['qualname']}",
    )
    baseline_path.write_text(
        json.dumps(entries, indent=2) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Tree walker
# ---------------------------------------------------------------------------


def check_source_tree(
    src_root: Path,
    baseline_path: Path | None = None,
    line_threshold: int = DEFAULT_LINE_THRESHOLD,
    complexity_threshold: int = DEFAULT_COMPLEXITY_THRESHOLD,
    enforcement: str = DEFAULT_ENFORCEMENT,
) -> CheckResult:
    """Walk *src_root* and return a :class:`CheckResult` with all WWL violations.

    WHAT: Recursively finds every ``*.py`` file under *src_root*, calls
    :func:`analyze_file` on each, aggregates violations, loads the baseline
    (if *baseline_path* is provided and the file exists), computes the subset
    of new violations not in the baseline, and returns a :class:`CheckResult`.

    WHY: Centralising the tree walk here keeps :func:`analyze_file` pure
    (single-file, no I/O beyond reading the file) and lets tests exercise the
    walk logic separately.

    Parameters
    ----------
    src_root : Path
        Root of the Python source tree to scan (e.g. ``src/claude_mpm``).
    baseline_path : Path or None
        Path to the ``.wwl-baseline.json`` file.  If None or non-existent,
        all violations are treated as new in baseline mode.
    line_threshold : int
        Forwarded to :func:`analyze_file`.
    complexity_threshold : int
        Forwarded to :func:`analyze_file`.
    enforcement : str
        One of ``"off"``, ``"baseline"``, ``"strict"``.

    Returns
    -------
    CheckResult
    """
    repo_root = src_root
    # The src_root might be e.g. src/claude_mpm; use the grandparent as repo root
    # so relpaths are e.g. "src/claude_mpm/foo.py" — but callers may pass the
    # actual repo root directly.  We accept whatever is passed and compute relpaths
    # relative to it.

    all_violations: list[Violation] = []
    for py_file in sorted(src_root.rglob("*.py")):
        file_violations = analyze_file(
            py_file,
            repo_root=repo_root,
            line_threshold=line_threshold,
            complexity_threshold=complexity_threshold,
        )
        all_violations.extend(file_violations)

    baseline_keys = frozenset()
    if baseline_path is not None:
        baseline_keys = load_baseline(baseline_path)

    new_violations = [v for v in all_violations if v.key not in baseline_keys]

    return CheckResult(
        violations=all_violations,
        new_violations=new_violations,
        enforcement=enforcement,
        baseline_keys=baseline_keys,
    )


# ---------------------------------------------------------------------------
# Baseline generation helper
# ---------------------------------------------------------------------------


def generate_baseline(
    src_root: Path,
    baseline_path: Path,
    line_threshold: int = DEFAULT_LINE_THRESHOLD,
    complexity_threshold: int = DEFAULT_COMPLEXITY_THRESHOLD,
) -> list[Violation]:
    """Generate (or regenerate) the WWL baseline from the current source tree.

    WHAT: Runs :func:`check_source_tree` in ``"off"`` mode (no enforcement),
    writes all violations to *baseline_path* via :func:`save_baseline`, and
    returns the list of violations.  Calling this function makes the next
    ``baseline``-mode run green: all existing violations are known, and only
    new violations (added after this call) will be flagged.

    WHY: The baseline/ratchet approach lets the team adopt WWL checking without
    requiring a big-bang backfill of thousands of legacy files.  Violations
    captured in the baseline are tolerated; new code above the thresholds is
    flagged on the first PR.

    Parameters
    ----------
    src_root : Path
        Root of the Python source tree.
    baseline_path : Path
        Where to write the ``.wwl-baseline.json`` file.
    line_threshold : int
        LOC threshold to use when collecting current violations.
    complexity_threshold : int
        CC threshold to use when collecting current violations.

    Returns
    -------
    list[Violation]
        The full list of violations captured in the baseline.
    """
    result = check_source_tree(
        src_root=src_root,
        baseline_path=None,  # no existing baseline — capture everything
        line_threshold=line_threshold,
        complexity_threshold=complexity_threshold,
        enforcement="off",
    )
    save_baseline(result.violations, baseline_path)
    return result.violations
