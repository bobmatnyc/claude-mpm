"""
tests/test_spec_traceability.py — Spec-Linked Documentation (SLD) traceability checker.

WHAT: Parses declared spec IDs from docs/specs/*.md and docstring references
from src/claude_mpm/**/*.py, then asserts that no ORPHANED (code ref with no
matching spec) and no OUTDATED (revision mismatch) IDs exist. UNCOVERED specs
(declared but unreferenced) are also asserted, unless a section carries
``**Status:** draft`` in its body, in which case it is exempt from the UNCOVERED
check (it is allowed to have no code References yet).

WHY: Enforces the bidirectional completeness required by the SLD convention
(docs/specs/README.md). Zero runtime dependencies; only re, pathlib, and ast
from the Python standard library are used. This is a Python-idiomatic adaptation
of the OpenFastTrace (github.com/itsallcode/openfasttrace) four-status model —
COVERED, UNCOVERED, ORPHANED, OUTDATED — without requiring OFT's Java runtime.

Draft-status exemption (UNCOVERED only):
    A spec section may carry ``**Status:** draft`` on a line immediately below
    its heading anchor. Draft sections are excluded from the UNCOVERED check,
    allowing parallel authoring of spec text before implementing code is
    backfilled. ORPHANED and OUTDATED enforcement still applies to draft IDs —
    if code references a draft spec ID the revision must still match.

IMPORTANT — what this checker does NOT prove:
    The CI check is a necessary condition, not a sufficient one. Passing this test
    proves that every code reference resolves to a declared spec ID and that
    revisions match. It does NOT prove that the function actually implements the
    behavior described by the spec, that the docstring is semantically accurate, or
    that an AI agent did not accidentally copy a reference from another function.
    Human review of the spec-to-code mapping is required in every PR that modifies
    a governed module. See docs/specs/README.md, section 8.

Convention reference: docs/specs/README.md
Lineage: OpenFastTrace (OFT) convention; RTM discipline since the 1970s.
"""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent
_SPEC_DIR = _REPO_ROOT / "docs" / "specs"
_SRC_DIR = _REPO_ROOT / "src" / "claude_mpm"

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Matches a full spec ID with revision: SPEC-SUBSYSTEM-NN~rev
# Examples: SPEC-HOOKS-01~1, SPEC-AGENTS-12~3
_SPEC_ID_RE = re.compile(r"\bSPEC-[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+~\d+\b")

# Matches a declaration heading anchor in spec Markdown files.
# Declaration form: ## Anything {#SPEC-HOOKS-01~1}
# Only IDs in named anchors on headings are treated as declarations.
# This prevents example IDs in prose, tables, and this README from being
# counted as declarations.
_DECL_ANCHOR_RE = re.compile(r"\{#(SPEC-[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+~\d+)\}")

# Files to exclude from spec scanning (contain example IDs that are not
# authoritative declarations).
_SPEC_EXCLUDE_GLOBS = [
    "research/**/*.md",  # Research documents
    "README.md",  # This convention document
    "AUTHORING.md",  # Authoring-standard guide (contains example IDs, not declarations)
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class SpecLocation:
    """A declared spec ID with its source file and draft status.

    Why: Tracks whether a section carries ``**Status:** draft`` so the
    UNCOVERED check can exempt it.
    What: Holds the spec ID, source file path, line number, and a flag that
    is True when the section body contains ``**Status:** draft``.
    Test: Construct with is_draft=True, assert the section is absent from
    TraceabilityReport.uncovered even when no code references exist.
    """

    spec_id: str
    file: Path
    line: int
    is_draft: bool = False


@dataclass
class CodeReference:
    """A spec ID referenced in a docstring with its source file."""

    spec_id: str
    file: Path
    # qualname of the containing module/class/function whose docstring
    # carries the reference, or "<module>" for module-level docstrings.
    qualname: str


@dataclass
class TraceabilityReport:
    """Aggregated traceability state for assertion."""

    declared: dict[str, SpecLocation] = field(default_factory=dict)
    referenced: list[CodeReference] = field(default_factory=list)

    @property
    def declared_ids(self) -> set[str]:
        return set(self.declared)

    @property
    def referenced_ids(self) -> set[str]:
        return {ref.spec_id for ref in self.referenced}

    @property
    def orphaned(self) -> list[CodeReference]:
        """Code references with no matching declared spec ID."""
        return [r for r in self.referenced if r.spec_id not in self.declared_ids]

    @property
    def uncovered(self) -> list[SpecLocation]:
        """Declared spec IDs with no code reference, excluding draft sections.

        Why: Draft sections are explicitly allowed to have no code references
        yet — they are authored ahead of the implementing backfill. Exempting
        them prevents CI from blocking parallel spec authoring.
        What: Returns every non-draft declared spec ID that has no matching
        code reference. Draft sections (is_draft=True) are always excluded
        regardless of coverage state.
        Test: A draft section with no references must not appear here; a
        non-draft section with no references must appear here.
        """
        return [
            loc
            for spec_id, loc in self.declared.items()
            if spec_id not in self.referenced_ids and not loc.is_draft
        ]

    @property
    def outdated(self) -> list[tuple[CodeReference, SpecLocation]]:
        """
        Code references whose revision differs from the declared spec revision.

        OFT calls this OUTDATED: the code was written against an older (or
        hypothetically newer) revision of the spec and has not been updated.

        Because spec IDs include the revision (e.g., SPEC-HOOKS-01~1), a
        mismatch manifests as a reference to SPEC-HOOKS-01~1 when the spec
        declares SPEC-HOOKS-01~2. The base (without revision) is the key.

        Note: In the current implementation, OUTDATED is a subset of ORPHANED
        — a mismatched-revision reference will not resolve to a declared ID and
        will therefore appear as ORPHANED. This is reported separately for
        clarity, but the orphaned assertion already catches it.
        """
        # Build base-id → declared entries mapping
        base_to_declared: dict[str, SpecLocation] = {}
        for spec_id, loc in self.declared.items():
            base = _strip_revision(spec_id)
            base_to_declared[base] = loc

        results = []
        for ref in self.referenced:
            base = _strip_revision(ref.spec_id)
            if (
                base in base_to_declared
                and ref.spec_id != base_to_declared[base].spec_id
            ):
                results.append((ref, base_to_declared[base]))
        return results


def _strip_revision(spec_id: str) -> str:
    """Return the spec ID without its ~rev suffix.

    Example: 'SPEC-HOOKS-01~3' -> 'SPEC-HOOKS-01'
    """
    return spec_id.rsplit("~", 1)[0]


# ---------------------------------------------------------------------------
# Spec-file parser
# ---------------------------------------------------------------------------


def _is_excluded_spec_file(path: Path, spec_dir: Path) -> bool:
    """Return True if this path matches one of the exclusion globs.

    Exclusion rule (documented in docs/specs/README.md, section 4):
    - docs/specs/research/**  — research documents
    - docs/specs/README.md    — the convention guide itself (contains example IDs)
    - docs/specs/AUTHORING.md — the authoring-standard guide (contains example IDs
      in templates and a filled mini-example; these are illustrative, not declarations)
    """
    try:
        rel = path.relative_to(spec_dir)
    except ValueError:
        return False

    for glob_pattern in _SPEC_EXCLUDE_GLOBS:
        # Convert glob to a match against the relative path string.
        # We handle simple cases: leading "research/**" and exact filenames.
        if glob_pattern.endswith("/**/*.md"):
            prefix = glob_pattern[: -len("/**/*.md")]
            if str(rel).startswith(prefix + "/"):
                return True
        elif glob_pattern == str(rel):
            return True
    return False


# Matches the draft-status marker in a spec section body.
# Canonical form: **Status:** draft (pending backfill)
# The check is case-insensitive on "draft" and accepts any trailing text.
_DRAFT_STATUS_RE = re.compile(r"\*\*Status:\*\*\s+draft\b", re.IGNORECASE)


def parse_declared_spec_ids(spec_dir: Path) -> dict[str, SpecLocation]:
    """
    Parse all declared spec IDs from Markdown files in spec_dir.

    Declaration rule: An ID is declared when it appears in a named anchor
    on a Markdown heading, in the form ``## Title {#SPEC-SUBSYSTEM-NN~rev}``.

    IDs that appear only in prose, tables, or code blocks are NOT declarations.
    This prevents example IDs in docs/specs/README.md and research documents
    from being treated as authoritative spec entries.

    Draft-status detection: After finding a declaration, the parser scans the
    lines that follow the heading (until the next heading) for a line matching
    ``**Status:** draft``. If found, ``SpecLocation.is_draft`` is set to True
    and the ID is exempt from the UNCOVERED check. ORPHANED and OUTDATED
    enforcement remain active for draft IDs.

    Args:
        spec_dir: Path to the docs/specs directory.

    Returns:
        Mapping from spec_id string to SpecLocation.
    """
    declared: dict[str, SpecLocation] = {}

    if not spec_dir.exists():
        return declared

    for md_file in sorted(spec_dir.rglob("*.md")):
        if _is_excluded_spec_file(md_file, spec_dir):
            continue

        text = md_file.read_text(encoding="utf-8")
        lines = text.splitlines()

        # First pass: collect (lineno, spec_id) for all heading-anchor declarations.
        heading_decls: list[tuple[int, str]] = []
        for lineno, line in enumerate(lines, start=1):
            stripped = line.lstrip()
            if not stripped.startswith("#"):
                continue
            for match in _DECL_ANCHOR_RE.finditer(line):
                spec_id = match.group(1)
                if spec_id not in declared:
                    heading_decls.append((lineno, spec_id))

        # Second pass: for each declaration, scan its section body (lines between
        # this heading and the next heading) to detect ``**Status:** draft``.
        for idx, (lineno, spec_id) in enumerate(heading_decls):
            # Section body starts right after the heading line (lineno is 1-based).
            body_start = lineno  # lines[lineno] is the first line after the heading
            # Section body ends at the next heading or end-of-file.
            if idx + 1 < len(heading_decls):
                next_heading_lineno = heading_decls[idx + 1][0]
                body_lines = lines[body_start : next_heading_lineno - 1]
            else:
                body_lines = lines[body_start:]

            is_draft = any(_DRAFT_STATUS_RE.search(bl) for bl in body_lines)
            declared[spec_id] = SpecLocation(
                spec_id=spec_id,
                file=md_file,
                line=lineno,
                is_draft=is_draft,
            )

    return declared


# ---------------------------------------------------------------------------
# Source-file parser
# ---------------------------------------------------------------------------


def _extract_docstrings_from_ast(source_text: str, file: Path) -> list[tuple[str, str]]:
    """
    Extract all docstrings from module, class, and function definitions.

    Returns a list of (qualname, docstring_text) tuples. The qualname is
    "<module>" for module-level docstrings.

    Uses ast to find only genuine docstrings — string literals that are the
    first statement of a module, class, or function body. This avoids false
    positives from string constants elsewhere in the code.

    Args:
        source_text: Python source code as a string.
        file: Path to the source file (used only for error context).

    Returns:
        List of (qualname, docstring_text) tuples.
    """
    try:
        tree = ast.parse(source_text, filename=str(file))
    except SyntaxError:
        return []

    results: list[tuple[str, str]] = []

    def _get_docstring(node: ast.AST) -> str | None:
        """Return the docstring if the first statement is a string literal."""
        body = getattr(node, "body", [])
        if body and isinstance(body[0], ast.Expr):
            value = body[0].value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                return value.value
        return None

    # Module-level docstring
    module_doc = _get_docstring(tree)
    if module_doc:
        results.append(("<module>", module_doc))

    # Class and function docstrings with their qualnames
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = _get_docstring(node)
            if doc:
                results.append((node.name, doc))

    return results


def parse_code_references(src_dir: Path) -> list[CodeReference]:
    """
    Parse all spec ID references from docstrings in src_dir.

    Scans every .py file under src_dir. For each file, uses the ast module
    to extract genuine docstrings (module, class, function level). Then
    applies the spec ID regex to find SPEC-SUBSYSTEM-NN~rev patterns.

    Args:
        src_dir: Root of the Python source tree to scan.

    Returns:
        List of CodeReference instances, one per (file, qualname, spec_id) triple.
    """
    references: list[CodeReference] = []

    if not src_dir.exists():
        return references

    for py_file in sorted(src_dir.rglob("*.py")):
        source_text = py_file.read_text(encoding="utf-8")
        docstrings = _extract_docstrings_from_ast(source_text, py_file)

        for qualname, docstring in docstrings:
            # Deduplicate within one docstring: a spec ID that appears multiple
            # times in the same docstring string (e.g., once in the References
            # label and again in the URL portion) counts as a single reference.
            seen_in_docstring: set[str] = set()
            for match in _SPEC_ID_RE.finditer(docstring):
                spec_id = match.group(0)
                if spec_id in seen_in_docstring:
                    continue
                seen_in_docstring.add(spec_id)
                references.append(
                    CodeReference(
                        spec_id=spec_id,
                        file=py_file,
                        qualname=qualname,
                    )
                )

    return references


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------


def build_report(
    spec_dir: Path = _SPEC_DIR,
    src_dir: Path = _SRC_DIR,
) -> TraceabilityReport:
    """
    Build a TraceabilityReport from spec files and source files.

    This is the main entry point for the checker. It parses both sides of the
    traceability graph and returns a report whose properties (orphaned,
    uncovered, outdated) drive the test assertions.

    Args:
        spec_dir: Path to the docs/specs directory.
        src_dir: Path to the Python source tree.

    Returns:
        TraceabilityReport with declared IDs and code references.
    """
    declared = parse_declared_spec_ids(spec_dir)
    referenced = parse_code_references(src_dir)
    return TraceabilityReport(declared=declared, referenced=referenced)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_no_orphaned_spec_refs() -> None:
    """
    ORPHANED check: every SPEC-* ID in a docstring must resolve to a declared
    spec ID in docs/specs/*.md.

    Failure means code claims a spec that does not exist. This may indicate:
    - A typo in the spec ID.
    - A spec section that was deleted or renamed without updating code.
    - An AI agent that copied a reference from another function without updating it.

    Status on empty state: PASS. When no spec files and no source references
    exist, the orphaned set is empty and this assertion trivially holds.
    """
    report = build_report()

    if not report.orphaned:
        return  # All references resolve — nothing to report.

    lines = [
        f"ORPHANED spec references found ({len(report.orphaned)} total).",
        "Each code docstring below references a SPEC-* ID that has no matching",
        "declaration in docs/specs/*.md. Fix by either:",
        "  (a) correcting the spec ID in the docstring, or",
        "  (b) adding the spec section to docs/specs/{subsystem}.md.",
        "",
    ]
    for ref in sorted(report.orphaned, key=lambda r: (str(r.file), r.qualname)):
        lines.append(f"  {ref.spec_id}")
        lines.append(f"    in {ref.file.relative_to(_REPO_ROOT)}")
        lines.append(f"    docstring of: {ref.qualname}")

    assert not report.orphaned, "\n".join(lines)


def test_no_outdated_spec_refs() -> None:
    """
    OUTDATED check: every SPEC-* ID in a docstring must have the same revision
    as the currently declared spec.

    Example: code says SPEC-HOOKS-01~1 but the spec file now declares
    SPEC-HOOKS-01~2. The code was written against an old revision of the
    contract and must be reviewed and updated.

    Note: OUTDATED references also appear in the ORPHANED set because the
    old-revision ID does not match the new declaration. This test reports them
    separately for diagnostic clarity.

    Status on empty state: PASS. No references means no mismatches.
    """
    report = build_report()

    if not report.outdated:
        return

    lines = [
        f"OUTDATED spec references found ({len(report.outdated)} total).",
        "Code docstrings below reference an old revision of a spec ID.",
        "Update the docstring to use the current revision and verify the",
        "implementing code still satisfies the updated contract.",
        "",
    ]
    for ref, loc in sorted(
        report.outdated, key=lambda t: (str(t[0].file), t[0].qualname)
    ):
        lines.append(f"  Code has:    {ref.spec_id}")
        lines.append(f"  Spec has:    {loc.spec_id}")
        lines.append(f"  Code file:   {ref.file.relative_to(_REPO_ROOT)}")
        lines.append(f"  Docstring:   {ref.qualname}")
        lines.append(f"  Spec file:   {loc.file.relative_to(_REPO_ROOT)}")
        lines.append("")

    assert not report.outdated, "\n".join(lines)


def test_no_uncovered_specs() -> None:
    """
    UNCOVERED check: every declared SPEC-* ID in docs/specs/*.md must be
    referenced in at least one docstring in src/claude_mpm/.

    Failure means a spec section has been written but no implementing module
    has claimed it. This usually indicates:
    - The implementing module has not yet added a References block.
    - The spec section was written speculatively and needs a corresponding impl.
    - A module was deleted or renamed without updating the spec.

    Status on empty state: PASS. When no spec files declare any IDs, the
    uncovered set is empty. This test becomes meaningful as subsystem specs
    are added to docs/specs/.
    """
    report = build_report()

    if not report.uncovered:
        return

    lines = [
        f"UNCOVERED spec IDs found ({len(report.uncovered)} total).",
        "Each spec section below is declared in docs/specs/*.md but has no",
        "matching References block in any docstring under src/claude_mpm/.",
        "Fix by adding:",
        "  References",
        "  ----------",
        "  SPEC-{SUBSYSTEM}-{NN}~{rev} : docs/specs/{subsystem}.md#...",
        "to the module-level docstring of the implementing module.",
        "",
    ]
    for loc in sorted(report.uncovered, key=lambda l: (str(l.file), l.spec_id)):
        lines.append(f"  {loc.spec_id}")
        lines.append(f"    declared in {loc.file.relative_to(_REPO_ROOT)}:{loc.line}")

    assert not report.uncovered, "\n".join(lines)


# ---------------------------------------------------------------------------
# Unit tests for parser functions
# ---------------------------------------------------------------------------


def test_parse_declared_spec_ids_basic(tmp_path: Path) -> None:
    """
    Unit test: parse_declared_spec_ids finds IDs in heading anchors and
    ignores IDs that appear only in prose or code blocks.
    """
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()

    hooks_md = spec_dir / "hooks.md"
    hooks_md.write_text(
        """\
# Hooks Specification

## Hook Dispatch Subsystem {#SPEC-HOOKS-01~1}

**ID:** SPEC-HOOKS-01~1

### Behavior Contract (WHAT)

The dispatcher accepts a JSON event dict and routes it to a handler.

This prose mentions SPEC-HOOKS-01~1 again but that should not create a duplicate.

### Rationale (WHY)

Centralizes routing so handlers remain testable in isolation.

## Hook Validation {#SPEC-HOOKS-02~2}

**ID:** SPEC-HOOKS-02~2

An ID in a code block should not be declared:

```
SPEC-HOOKS-03~1
```
""",
        encoding="utf-8",
    )

    # The research directory should be excluded
    research_dir = spec_dir / "research"
    research_dir.mkdir()
    research_md = research_dir / "05-research.md"
    research_md.write_text(
        """\
## Research section {#SPEC-RESEARCH-01~1}

This should be excluded from declarations.
""",
        encoding="utf-8",
    )

    # README.md should also be excluded
    readme = spec_dir / "README.md"
    readme.write_text(
        """\
# SLD Convention

## Example heading {#SPEC-EXAMPLE-01~1}

Example IDs in the convention guide are not real declarations.
""",
        encoding="utf-8",
    )

    declared = parse_declared_spec_ids(spec_dir)

    # Should find exactly the two heading anchors from hooks.md
    assert "SPEC-HOOKS-01~1" in declared, "Expected SPEC-HOOKS-01~1 to be declared"
    assert "SPEC-HOOKS-02~2" in declared, "Expected SPEC-HOOKS-02~2 to be declared"

    # Prose repetition should not create extra entries
    assert len([k for k in declared if k.startswith("SPEC-HOOKS-01")]) == 1

    # Code block ID should not be declared
    assert "SPEC-HOOKS-03~1" not in declared, "Code block IDs should not be declared"

    # Research directory should be excluded
    assert "SPEC-RESEARCH-01~1" not in declared, "Research IDs should be excluded"

    # README example IDs should be excluded
    assert "SPEC-EXAMPLE-01~1" not in declared, "README example IDs should be excluded"

    # File location should be correct
    assert declared["SPEC-HOOKS-01~1"].file == hooks_md
    assert declared["SPEC-HOOKS-01~1"].line == 3  # "## Hook Dispatch..." is line 3


def test_parse_code_references_basic(tmp_path: Path) -> None:
    """
    Unit test: parse_code_references finds spec IDs in module, class, and
    function docstrings, and ignores IDs in inline comments and string literals
    outside docstrings.
    """
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    # Module with various docstring locations
    py_file = src_dir / "dispatcher.py"
    py_file.write_text(
        '''\
"""
Hook dispatcher module.

WHAT: Routes hook events to registered handlers.

WHY: Centralizes routing logic.

References
----------
SPEC-HOOKS-01~1 : docs/specs/hooks.md#SPEC-HOOKS-01~1
"""

# A comment with SPEC-HOOKS-99~1 should NOT be picked up as a reference.

NOT_A_DOCSTRING = "SPEC-HOOKS-88~1"  # Also should be ignored.


class HookDispatcher:
    """
    Dispatches hook events.

    References
    ----------
    SPEC-HOOKS-01~1 : docs/specs/hooks.md#SPEC-HOOKS-01~1
    """

    def dispatch(self, event: dict) -> dict:
        """
        Route event to the correct handler.

        :spec: SPEC-HOOKS-02~1
        """
        return {}

    def validate(self, event: dict) -> bool:
        """Validate event structure. No spec reference here."""
        return True
''',
        encoding="utf-8",
    )

    references = parse_code_references(src_dir)

    # Extract just the spec IDs
    ref_ids = [r.spec_id for r in references]

    # Module docstring reference
    assert "SPEC-HOOKS-01~1" in ref_ids, "Expected module-level reference"

    # Class docstring reference (same ID, separate reference object)
    module_refs = [r for r in references if r.spec_id == "SPEC-HOOKS-01~1"]
    assert len(module_refs) >= 2, (
        "Expected at least two references to SPEC-HOOKS-01~1 "
        "(module docstring + class docstring)"
    )

    # Function :spec: field reference
    assert "SPEC-HOOKS-02~1" in ref_ids, "Expected function :spec: reference"

    # Inline comment reference should NOT be picked up
    assert not any(r.spec_id == "SPEC-HOOKS-99~1" for r in references), (
        "Inline comment IDs should not be treated as references"
    )

    # String constant reference should NOT be picked up
    assert not any(r.spec_id == "SPEC-HOOKS-88~1" for r in references), (
        "String constant IDs outside docstrings should not be treated as references"
    )

    # validate() has no spec reference
    validate_refs = [r for r in references if r.qualname == "validate"]
    assert not validate_refs, "validate() docstring has no spec reference"


def test_empty_state_all_pass(tmp_path: Path) -> None:
    """
    Integration unit test: with no spec files and no source references,
    all three checks (orphaned, uncovered, outdated) pass with empty sets.

    This validates the green-on-empty-state requirement: the checker must
    pass on the current repository state where no subsystem specs exist yet.
    """
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    report = build_report(spec_dir=spec_dir, src_dir=src_dir)

    assert report.declared_ids == set(), "Expected no declared IDs"
    assert report.referenced_ids == set(), "Expected no referenced IDs"
    assert not report.orphaned, "Expected no orphaned references"
    assert not report.uncovered, "Expected no uncovered specs"
    assert not report.outdated, "Expected no outdated references"


def test_outdated_detection(tmp_path: Path) -> None:
    """
    Unit test: detect OUTDATED references where code uses an old revision.

    Scenario: spec declares SPEC-HOOKS-01~2 but code still references
    SPEC-HOOKS-01~1. The reference is ORPHANED (no exact match) and also
    OUTDATED (base ID exists at a different revision).
    """
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    # Spec declares revision 2
    (spec_dir / "hooks.md").write_text(
        """\
## Hook Dispatch {#SPEC-HOOKS-01~2}

**ID:** SPEC-HOOKS-01~2
""",
        encoding="utf-8",
    )

    # Code still references revision 1
    (src_dir / "handler.py").write_text(
        '''\
"""
Handler module.

References
----------
SPEC-HOOKS-01~1 : docs/specs/hooks.md#SPEC-HOOKS-01~1
"""
''',
        encoding="utf-8",
    )

    report = build_report(spec_dir=spec_dir, src_dir=src_dir)

    # The old-revision reference is orphaned (SPEC-HOOKS-01~1 is not declared)
    assert len(report.orphaned) == 1
    assert report.orphaned[0].spec_id == "SPEC-HOOKS-01~1"

    # It is also detected as outdated
    assert len(report.outdated) == 1
    ref, loc = report.outdated[0]
    assert ref.spec_id == "SPEC-HOOKS-01~1"
    assert loc.spec_id == "SPEC-HOOKS-01~2"

    # SPEC-HOOKS-01~2 is uncovered (code refs old revision, not new)
    assert len(report.uncovered) == 1
    assert report.uncovered[0].spec_id == "SPEC-HOOKS-01~2"


# ---------------------------------------------------------------------------
# Unit tests for draft-status exemption
# ---------------------------------------------------------------------------


def test_draft_section_no_refs_no_uncovered_failure(tmp_path: Path) -> None:
    """
    (a) A draft section with no code references must NOT appear in uncovered.

    Why: Draft specs are authored before their implementing backfill lands.
    Blocking CI on an unreferenced draft would prevent parallel spec authoring.

    What this test proves: is_draft=True keeps the ID out of uncovered even
    when no code references exist anywhere.

    How to verify: Build a report with one draft declaration and an empty src
    directory; assert report.uncovered is empty.
    """
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    (spec_dir / "agents.md").write_text(
        """\
## Agent Loading {#SPEC-AGENTS-01~1}

**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

Accepts an agent name, returns an AgentConfig or raises AgentNotFound.
""",
        encoding="utf-8",
    )

    report = build_report(spec_dir=spec_dir, src_dir=src_dir)

    assert "SPEC-AGENTS-01~1" in report.declared_ids, "Draft ID must still be declared"
    assert report.declared["SPEC-AGENTS-01~1"].is_draft, (
        "Section must be detected as draft"
    )
    assert not report.uncovered, (
        "Draft section with no code refs must not appear in uncovered"
    )
    assert not report.orphaned, "No code refs means no orphans"
    assert not report.outdated, "No code refs means no outdated"


def test_non_draft_section_no_refs_triggers_uncovered(tmp_path: Path) -> None:
    """
    (b) A non-draft section with no code references MUST appear in uncovered.

    Why: Normal (active) spec sections require implementing code; missing refs
    indicate an incomplete backfill that CI must catch.

    What this test proves: Absence of ``**Status:** draft`` leaves UNCOVERED
    enforcement active for the section.

    How to verify: Build a report with one active declaration and empty src;
    assert report.uncovered contains that ID.
    """
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    (spec_dir / "agents.md").write_text(
        """\
## Agent Loading {#SPEC-AGENTS-01~1}

**Status:** active

### Behavior Contract (WHAT)

Accepts an agent name, returns an AgentConfig or raises AgentNotFound.
""",
        encoding="utf-8",
    )

    report = build_report(spec_dir=spec_dir, src_dir=src_dir)

    assert "SPEC-AGENTS-01~1" in report.declared_ids
    assert not report.declared["SPEC-AGENTS-01~1"].is_draft, (
        "Active section is not draft"
    )
    assert len(report.uncovered) == 1, "Active section with no refs must be UNCOVERED"
    assert report.uncovered[0].spec_id == "SPEC-AGENTS-01~1"


def test_draft_section_referenced_wrong_revision_still_flagged(tmp_path: Path) -> None:
    """
    (c) A draft section referenced with a WRONG revision is still ORPHANED/OUTDATED.

    Why: Draft status only exempts UNCOVERED. ORPHANED and OUTDATED must still
    be enforced so revision mismatches cannot slip through under draft cover.

    What this test proves: Code that references a draft spec ID at a stale
    revision (~1 while spec declares ~2) is flagged ORPHANED and OUTDATED even
    though the section carries ``**Status:** draft``.

    How to verify: Draft spec at ~2; code refs ~1; assert orphaned and outdated
    are non-empty; assert uncovered is empty (draft exemption still applies).
    """
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    # Draft spec at revision 2
    (spec_dir / "hooks.md").write_text(
        """\
## Hook Dispatch {#SPEC-HOOKS-01~2}

**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

Dispatches hook events to registered handlers.
""",
        encoding="utf-8",
    )

    # Code references old revision 1 of the draft spec
    (src_dir / "handler.py").write_text(
        '''\
"""
Handler module.

References
----------
SPEC-HOOKS-01~1 : docs/specs/hooks.md#SPEC-HOOKS-01~1
"""
''',
        encoding="utf-8",
    )

    report = build_report(spec_dir=spec_dir, src_dir=src_dir)

    # Draft exemption: SPEC-HOOKS-01~2 is draft → not in uncovered
    assert not report.uncovered, (
        "Draft section must not appear in uncovered even with wrong-revision ref"
    )

    # ORPHANED: code refs SPEC-HOOKS-01~1, which is not declared (draft is ~2)
    assert len(report.orphaned) == 1, "Wrong-revision ref to draft must be ORPHANED"
    assert report.orphaned[0].spec_id == "SPEC-HOOKS-01~1"

    # OUTDATED: base ID exists at ~2, code refs ~1
    assert len(report.outdated) == 1, "Wrong-revision ref to draft must be OUTDATED"
    ref, loc = report.outdated[0]
    assert ref.spec_id == "SPEC-HOOKS-01~1"
    assert loc.spec_id == "SPEC-HOOKS-01~2"


def test_flipping_draft_to_active_reenables_uncovered(tmp_path: Path) -> None:
    """
    (d) Removing ``**Status:** draft`` from a section re-enables UNCOVERED.

    Why: Once a spec is backfilled and promoted to active, its code refs must
    be present. The draft exemption must be strictly tied to the status marker.

    What this test proves: The same spec ID triggers UNCOVERED after its
    ``**Status:** draft`` line is changed to ``**Status:** active``.

    How to verify: Build two reports — one with draft, one with active — and
    assert uncovered switches from empty to non-empty.
    """
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    spec_file = spec_dir / "agents.md"

    # Phase 1: section is draft — uncovered must be empty
    spec_file.write_text(
        """\
## Agent Loading {#SPEC-AGENTS-01~1}

**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

Accepts an agent name, returns an AgentConfig or raises AgentNotFound.
""",
        encoding="utf-8",
    )
    report_draft = build_report(spec_dir=spec_dir, src_dir=src_dir)
    assert not report_draft.uncovered, "Draft: uncovered must be empty"
    assert report_draft.declared["SPEC-AGENTS-01~1"].is_draft

    # Phase 2: flip to active — uncovered must now contain the ID
    spec_file.write_text(
        """\
## Agent Loading {#SPEC-AGENTS-01~1}

**Status:** active

### Behavior Contract (WHAT)

Accepts an agent name, returns an AgentConfig or raises AgentNotFound.
""",
        encoding="utf-8",
    )
    report_active = build_report(spec_dir=spec_dir, src_dir=src_dir)
    assert not report_active.declared["SPEC-AGENTS-01~1"].is_draft
    assert len(report_active.uncovered) == 1, "Active: uncovered must contain the ID"
    assert report_active.uncovered[0].spec_id == "SPEC-AGENTS-01~1"
