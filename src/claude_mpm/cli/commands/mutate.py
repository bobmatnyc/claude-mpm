"""Advisory ``claude-mpm mutate`` command — a thin CLI over the mutmut runner.

WHAT: Resolve one (or a capped set of) eligible source target(s), infer the
      paired test file, and invoke the merged ``run_mutation`` runner, then
      render a readable or JSON summary. Default behaviour is advisory: with no
      ``--threshold`` the command always exits 0; survivors are signal, not
      failure.
WHY:  Mutation testing is expensive and only meaningful on pure-logic modules,
      so the command gatekeeps with an eligibility heuristic (skips I/O-heavy
      and infra files), scopes auto-discovery to files changed vs a base ref,
      and never silently caps — keeping engineers in control of cost. The
      runner itself (counts, survivor parsing, safety-restore, shell-injection
      validation of ``--exclude-tests``) is imported, never reimplemented.

References
----------
LINK: SPEC-MUTATION-02~1 : docs/specs/mutation.md#SPEC-MUTATION-02~1
"""

from __future__ import annotations

import ast
import dataclasses
import json
import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from ...services.mutation.runner import run_mutation

if TYPE_CHECKING:
    from argparse import Namespace

    from ...services.mutation.runner import MutationResult

logger = logging.getLogger(__name__)

# Top-level imports that mark a module as I/O-heavy / infra-bound and therefore
# a poor mutation-testing candidate (mutants here are dominated by environment,
# not by the test suite's assertions).
_IO_HEAVY_IMPORTS = frozenset(
    {
        "subprocess",
        "asyncio",
        "aiohttp",
        "httpx",
        "sqlalchemy",
        "fastapi",
        "click",
        "socket",
        "paramiko",
        "boto3",
    }
)

# Path components that disqualify a file outright (infra, tooling, generated,
# or test code — none are worthwhile mutation targets).
_REJECTED_PATH_PARTS = frozenset({"tests", "cli", "scripts", "migrations"})


def is_eligible_for_mutation(path: Path) -> tuple[bool, str]:
    """Decide whether a source file is a worthwhile mutation-testing target.

    WHAT: Reject ``__init__.py``; reject paths under tests/cli/scripts/
          migrations or anything dashboard-flavoured; AST-parse the file and
          reject when any top-level import is in :data:`_IO_HEAVY_IMPORTS`,
          naming the triggering import(s) in the reason. Otherwise accept.
    WHY:  Mutation testing only yields actionable survivors on pure-logic code;
          I/O-heavy and infra modules produce noise and slow runs. Naming the
          offending import in the rejection lets the engineer judge whether a
          ``--force`` override is justified.

    Args:
        path: Source file to evaluate (need not be resolved).

    Returns:
        ``(True, "eligible")`` or ``(False, reason)``.

    :spec: SPEC-MUTATION-02~1
    """
    name = path.name
    if name == "__init__.py":
        return False, "skipped: __init__.py (no meaningful logic to mutate)"

    parts = set(path.parts)
    rejected = parts & _REJECTED_PATH_PARTS
    if rejected:
        part = sorted(rejected)[0]
        return False, f"skipped: path under {part}/ (infra/test/tooling code)"

    if any("dashboard" in part.lower() for part in path.parts):
        return False, "skipped: dashboard code (UI, not unit-testable logic)"

    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        return False, f"skipped: could not read file ({exc})"

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return False, f"skipped: file did not parse ({exc})"

    found: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _IO_HEAVY_IMPORTS:
                    found.add(root)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                if root in _IO_HEAVY_IMPORTS:
                    found.add(root)

    if found:
        names = ", ".join(sorted(found))
        return (
            False,
            f"skipped: I/O-heavy top-level import(s): {names} "
            f"(use --force to override)",
        )

    return True, "eligible"


def get_changed_files_vs_main(base: str) -> list[Path]:
    """Return source files changed vs ``base`` that exist as ``.py`` under src/.

    WHAT: Run ``git diff --name-only <base>...HEAD`` and return the existing
          ``.py`` paths that live under a ``src/`` component.
    WHY:  Auto-discovery should only consider real, mutatable source files.
          The ``...`` (merge-base) form scopes to changes introduced on this
          branch. This is the repo's only branch-diff helper — the existing
          ``enhanced_analyzer._get_changed_files`` is time-based, not a
          substitute.

    Args:
        base: Base git ref (e.g. ``origin/main``).

    Returns:
        List of changed source ``Path`` objects (may be empty).

    :spec: SPEC-MUTATION-02~1
    """
    proc = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        logger.warning(
            "git diff vs %s failed (rc=%s): %s",
            base,
            proc.returncode,
            proc.stderr.strip(),
        )
        return []

    results: list[Path] = []
    for line in proc.stdout.splitlines():
        rel = line.strip()
        if not rel.endswith(".py"):
            continue
        path = Path(rel)
        if "src" not in path.parts:
            continue
        if not path.exists():
            continue
        results.append(path)
    return results


def infer_tests_file(target: Path) -> tuple[Path | None, str | None]:
    """Infer the unit test file paired with a target module.

    WHAT: Search ``tests/**/test_<stem>.py`` for the target's module stem;
          return the single match, or ``(None, error)`` when there are zero or
          multiple matches.
    WHY:  Convenience for the common case (one obvious test file) while
          refusing to guess when ambiguous — an ambiguous guess could mutate
          against the wrong suite and report a misleading kill rate.

    Args:
        target: The source module whose test file we want.

    Returns:
        ``(test_path, None)`` on a unique match, else ``(None, error_message)``.

    :spec: SPEC-MUTATION-02~1
    """
    tests_root = Path("tests")
    if not tests_root.exists():
        return None, (
            "no tests/ directory found; pass --tests-file explicitly "
            f"for target {target}"
        )

    pattern = f"test_{target.stem}.py"
    matches = sorted(tests_root.rglob(pattern))
    if len(matches) == 1:
        return matches[0], None
    if not matches:
        return None, (
            f"could not infer a test file for {target} "
            f"(no tests/**/{pattern}); pass --tests-file explicitly"
        )
    listed = ", ".join(str(m) for m in matches)
    return None, (
        f"ambiguous test files for {target} (found {len(matches)}: {listed}); "
        "pass --tests-file explicitly"
    )


def _build_dry_run_command(target: Path, tests_file: Path) -> str:
    """Render the mutmut command the runner would execute, for ``--dry-run``.

    WHAT: Compose the human-readable ``uv run mutmut run`` invocation showing
          ``--paths-to-mutate`` / ``--tests-dir`` so the engineer can preview
          scope without running anything.
    WHY:  Dry-run must show concrete, copy-pasteable scope rather than a vague
          "would run mutmut" so the preview is trustworthy.
    """
    return (
        f"uv run mutmut run --paths-to-mutate={target} --tests-dir={tests_file.parent}"
    )


def _render_text(results: list[MutationResult]) -> None:
    """Print a readable per-target summary table and survivor list.

    WHAT: For each result print target, kill rate, killed/survived counts, any
          runner error, and one line per survivor
          (``file:line  original→mutant  [type]``).
    WHY:  Survivors are the actionable output; a flat, greppable line format is
          friendlier for terminals and CI logs than a nested structure.
    """
    for result in results:
        print(f"\nTarget: {result.target_file}")
        print(f"  Tests: {result.tests_file}")
        if result.error:
            print(f"  ERROR: {result.error}")
            continue
        print(
            f"  Mutants: {result.total_mutants}  "
            f"killed={result.killed}  survived={result.survived}  "
            f"kill_rate={result.kill_rate:.1%}"
        )
        if result.survivors:
            print("  Survivors:")
            for s in result.survivors:
                print(
                    f"    {s.file}:{s.line}  "
                    f"{s.original} → {s.mutant}  [{s.mutation_type}]"
                )


def _resolve_targets(args: Namespace) -> tuple[list[Path], int]:
    """Resolve the list of target files to mutate from the parsed args.

    WHAT: Use an explicit ``TARGET`` if given; otherwise auto-discover changed
          eligible files vs ``--base``, truncated to ``--max-files`` (returning
          the dropped count so the caller can log the truncation).
    WHY:  Auto-discovery must never silently cap — the dropped count is
          surfaced to the user so they know more candidates existed.

    Returns:
        ``(targets, dropped_count)``.

    :spec: SPEC-MUTATION-02~1
    """
    if args.target is not None:
        return [Path(args.target)], 0

    changed = get_changed_files_vs_main(args.base)
    eligible = [p for p in changed if is_eligible_for_mutation(p)[0]]
    max_files = args.max_files or 1
    dropped = max(0, len(eligible) - max_files)
    return eligible[:max_files], dropped


def manage_mutate(args: Namespace) -> int:
    """Entry point for ``claude-mpm mutate``.

    WHAT: Resolve targets, gate them through the eligibility heuristic (unless
          ``--force``), infer/validate test files, and either preview
          (``--dry-run``) or invoke ``run_mutation`` per target, then render
          text/JSON output and compute the exit code.
    WHY:  Advisory by default — with no ``--threshold`` the command always
          returns 0 so it can run in CI as pure signal. A set ``--threshold``
          turns survivors into a gate; a genuine runner ``error`` is always a
          non-zero failure regardless of threshold.

    Args:
        args: Parsed CLI namespace from :class:`MutateParser`.

    Returns:
        Process exit code (0 advisory/pass, 1 on threshold breach or error).

    :spec: SPEC-MUTATION-02~1
    """
    targets, dropped = _resolve_targets(args)

    if dropped:
        print(
            f"Note: {dropped} additional eligible file(s) not shown "
            f"(capped by --max-files {args.max_files}). "
            "Raise --max-files to include them."
        )

    if not targets:
        print(
            "No eligible mutation targets found "
            f"(checked changes vs {args.base}). Nothing to do."
        )
        return 0

    # Eligibility gate (skipped under --force). Ineligible targets are
    # informational, not errors.
    runnable: list[Path] = []
    for target in targets:
        if args.force:
            runnable.append(target)
            continue
        eligible, reason = is_eligible_for_mutation(target)
        if eligible:
            runnable.append(target)
        else:
            print(f"{target}: {reason}")

    if not runnable:
        print("No eligible targets after the eligibility check. Nothing to do.")
        return 0

    # Resolve each target's test file (inference or the explicit --tests-file).
    planned: list[tuple[Path, Path]] = []
    for target in runnable:
        if args.tests_file is not None:
            tests_file = Path(args.tests_file)
            if not tests_file.exists():
                print(f"ERROR: --tests-file does not exist: {tests_file}")
                return 1
        else:
            tests_file, err = infer_tests_file(target)
            if tests_file is None:
                print(f"ERROR: {err}")
                return 1
        planned.append((target, tests_file))

    if args.dry_run:
        print("Dry run — resolved scope (mutmut NOT executed):")
        for target, tests_file in planned:
            print(f"\nTarget: {target}")
            print(f"  Tests: {tests_file}")
            print(f"  Would run: {_build_dry_run_command(target, tests_file)}")
        return 0

    results: list[MutationResult] = [
        run_mutation(target, tests_file, args.exclude_tests)
        for target, tests_file in planned
    ]

    if args.output == "json":
        print(
            json.dumps(
                [dataclasses.asdict(r) for r in results],
                indent=2,
            )
        )
    else:
        _render_text(results)

    # Exit code: runner errors are always failures; threshold gates survivors.
    if any(r.error is not None for r in results):
        return 1

    if args.threshold is None:
        return 0

    if any(r.survived > args.threshold for r in results):
        return 1
    return 0
