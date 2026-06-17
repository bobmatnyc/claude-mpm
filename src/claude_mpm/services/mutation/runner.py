"""Standalone mutmut runner that hides mutmut 2.5.1's Python 3.13 bugs.

WHAT: Run mutmut against a single target module + test file and return a
      structured :class:`MutationResult` (counts, kill rate, parsed survivors),
      reading results from the ``.mutmut-cache`` SQLite DB and restoring the
      source on disk after every run.
WHY:  mutmut 2.5.1 on Python 3.13 has two load-bearing bugs that make the
      naive ``mutmut run`` + ``mutmut results`` workflow unusable:
        1. ``mutmut results`` crashes (pony-orm ``QueryResultIterator not
           iterable``) — so we read the SQLite cache directly instead.
        2. ``mutmut show`` accepts only ONE mutant id per call — so we query
           per survivor.
      mutmut also mutates source IN PLACE; a crash mid-run can leave a mutant
      on disk. We wrap the whole run in try/finally with a git-checkout restore
      so a failure never corrupts the working tree. This is the Phase 1
      de-risking slice: it proves the mutmut interface works in isolation
      before any CLI command, parser, eligibility heuristic, or agent wiring.

References
----------
LINK: none  (feature introduced in this PR, tracked in GitHub issue #853)
"""

from __future__ import annotations

import logging
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Name of the mutmut SQLite cache file (lives at repo root after a run).
CACHE_FILENAME = ".mutmut-cache"

# mutmut status strings (confirmed by inspecting a real 2.5.1 cache on Py3.13).
_STATUS_SURVIVED = "bad_survived"
_STATUS_KILLED = "ok_killed"


@dataclass(frozen=True)
class MutantSurvivor:
    """A single mutation that survived (the tests did not catch it).

    WHAT: Holds the parsed location and before/after source of one survivor.
    WHY:  Survivors are the actionable output of mutation testing — each names
          a behaviour the test suite fails to assert.
    """

    id: int
    file: str  # repo-relative path
    line: int
    original: str  # stripped original source line
    mutant: str  # stripped mutated source line
    mutation_type: str  # boundary | predicate | string | removal | arithmetic | other


@dataclass(frozen=True)
class MutationResult:
    """Aggregate outcome of one mutation run over a single target file.

    WHAT: Counts, kill rate, the list of survivors, and an optional error.
    WHY:  Gives callers a single structured value to act on; ``error`` is set
          only when mutmut itself failed (a clean run with survivors is NOT an
          error — survivors are the expected, useful signal).
    """

    target_file: str
    tests_file: str
    total_mutants: int
    killed: int
    survived: int
    kill_rate: float  # killed / total, 0.0 if total == 0
    survivors: list[MutantSurvivor]
    error: str | None  # set only if mutmut itself errored


def _build_runner_command(tests_file: Path, exclude_tests: str | None) -> str:
    """Build the pytest runner command string mutmut invokes per mutant.

    WHAT: Compose ``uv run python -m pytest <tests_file> -p no:xdist -x -q``
          plus an optional ``-k 'not (<exclude_tests>)'`` filter.
    WHY:  ``-p no:xdist`` avoids parallel-test flakiness under mutation;
          ``-x`` stops at the first failure (fastest kill detection); ``-q``
          keeps output small. exclude_tests lets callers skip slow/irrelevant
          tests by pattern.
    """
    cmd = f"uv run python -m pytest {tests_file} -p no:xdist -x -q"
    if exclude_tests:
        cmd += f" -k 'not ({exclude_tests})'"
    return cmd


def _classify_mutation(original: str, mutant: str) -> str:
    """Infer a mutation category from the original/mutant source pair.

    WHAT: Map a before/after line pair to one of boundary | predicate | string
          | removal | arithmetic | other.
    WHY:  A coarse category helps callers triage survivors without re-reading
          the diff. Ordering matters: a deletion ("removal") is checked first
          because an empty mutant has no operators to inspect.

    :spec: SPEC-MUTATION-01~1
    """
    orig = original.strip()
    mut = mutant.strip()

    # Removal: the mutant blanked the line (mutmut's statement deletion).
    if mut in {"", "pass"}:
        return "removal"

    # Compare the symmetric difference of tokens to see what actually changed.
    changed = f"{orig} {mut}"

    # Boundary: comparison-operator flips (<= >= < >).
    boundary_ops = ("<=", ">=", "<", ">")
    if any(op in orig or op in mut for op in boundary_ops) and orig != mut:
        # Distinguish from arithmetic: only treat as boundary if a comparison
        # operator is present (arithmetic handled below otherwise).
        if any(op in changed for op in ("<", ">")):
            return "boundary"

    # Predicate: boolean-logic operators.
    for token in ("and", "or", "not"):
        if f" {token} " in f" {orig} " or f" {token} " in f" {mut} ":
            return "predicate"

    # String: a quoted literal appears on either side.
    if ('"' in orig or "'" in orig) and ('"' in mut or "'" in mut):
        return "string"

    # Arithmetic: binary arithmetic operators.
    if any(op in changed for op in ("+", "-", "*", "/")):
        return "arithmetic"

    return "other"


def _parse_show_diff(
    mutant_id: int, diff_text: str, repo_root: Path | None = None
) -> MutantSurvivor | None:
    """Parse one ``mutmut show <id>`` unified diff into a MutantSurvivor.

    WHAT: Extract file (from the ``--- <file>`` header, normalized to a
          repo-relative path when ``repo_root`` is given), the changed line
          number (from the ``@@`` hunk header plus the offset of the removed
          line), and the original/mutant source lines.
    WHY:  ``mutmut show`` is the only Py3.13-safe way to get per-mutant detail
          in 2.5.1 (``mutmut results`` crashes). The diff is a stable unified
          format: ``--- file`` / ``+++ file`` / ``@@ -start,n +start,n @@`` /
          context lines, with ``-`` = original and ``+`` = mutant. mutmut
          echoes back whatever path we passed to ``--paths-to-mutate`` (often
          absolute), so we normalize to repo-relative to honor the
          :class:`MutantSurvivor` contract.

    :spec: SPEC-MUTATION-01~1
    """
    file_name: str | None = None
    hunk_start: int | None = None
    pos_in_hunk = 0  # 0-based offset of the next old/context line within hunk
    removed_line: str | None = None
    removed_offset: int | None = None
    added_line: str | None = None

    for raw in diff_text.splitlines():
        if raw.startswith("--- "):
            file_name = raw[4:].strip()
            continue
        if raw.startswith("+++ "):
            continue
        if raw.startswith("@@"):
            # Format: @@ -old_start,old_count +new_start,new_count @@
            try:
                old_part = raw.split(" ")[1]  # e.g. "-1,5"
                hunk_start = int(old_part.lstrip("-").split(",")[0])
            except (IndexError, ValueError):
                hunk_start = None
            pos_in_hunk = 0
            continue
        if hunk_start is None:
            continue
        if raw.startswith("-"):
            if removed_line is None:
                removed_line = raw[1:]
                removed_offset = pos_in_hunk
            pos_in_hunk += 1  # removed lines exist in the OLD file
        elif raw.startswith("+"):
            if added_line is None:
                added_line = raw[1:]
            # added lines do NOT advance the OLD-file position
        else:
            # context line (leading space) — exists in both files
            pos_in_hunk += 1

    if file_name is None or removed_line is None or added_line is None:
        logger.warning("Could not parse mutmut show diff for id=%s", mutant_id)
        return None

    line_number = 0
    if hunk_start is not None and removed_offset is not None:
        line_number = hunk_start + removed_offset

    # Normalize an absolute path back to repo-relative (the dataclass contract).
    if repo_root is not None:
        try:
            file_name = str(Path(file_name).resolve().relative_to(repo_root.resolve()))
        except ValueError:
            pass  # already relative or outside the repo — leave as-is

    original = removed_line.strip()
    mutant = added_line.strip()
    return MutantSurvivor(
        id=mutant_id,
        file=file_name,
        line=line_number,
        original=original,
        mutant=mutant,
        mutation_type=_classify_mutation(original, mutant),
    )


def _read_cache(cache_path: Path) -> tuple[list[int], int, int]:
    """Read survivor ids and killed/survived counts from the mutmut SQLite cache.

    WHAT: Return (survivor_ids, killed_count, survived_count) by querying the
          ``Mutant`` table for ``bad_survived`` / ``ok_killed`` statuses.
    WHY:  ``mutmut results`` crashes on Py3.13, so the SQLite cache is the
          authoritative source. We assert the ``Mutant`` table exists and has a
          ``status`` column first, raising a clear error if the schema differs —
          this guards against silently reporting a 100% kill rate when the
          schema has changed under us.

    :spec: SPEC-MUTATION-01~1
    """
    con = sqlite3.connect(str(cache_path), timeout=5.0)
    try:
        cur = con.cursor()
        # Schema guard: the Mutant table with a status column must exist.
        tables = {
            row[0]
            for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "Mutant" not in tables:
            raise ValueError(
                "mutmut cache schema mismatch: expected a 'Mutant' table, "
                f"found tables={sorted(tables)}"
            )
        columns = {row[1] for row in cur.execute("PRAGMA table_info(Mutant)")}
        if "status" not in columns or "id" not in columns:
            raise ValueError(
                "mutmut cache schema mismatch: 'Mutant' table missing "
                f"'id'/'status' columns, found columns={sorted(columns)}"
            )

        survivor_ids = [
            row[0]
            for row in cur.execute(
                "SELECT id FROM Mutant WHERE status = ? ORDER BY id",
                (_STATUS_SURVIVED,),
            )
        ]
        survived = len(survivor_ids)
        killed = next(
            cur.execute(
                "SELECT COUNT(*) FROM Mutant WHERE status = ?",
                (_STATUS_KILLED,),
            )
        )[0]
        return survivor_ids, killed, survived
    finally:
        con.close()


def _show_survivor(mutant_id: int, repo_root: Path) -> MutantSurvivor | None:
    """Run ``mutmut show <id>`` for one survivor and parse its diff.

    WHAT: Invoke mutmut show for a single id (2.5.1 takes one id per call) and
          delegate parsing to :func:`_parse_show_diff`.
    WHY:  Isolated here so the per-survivor subprocess call is easy to stub in
          tests and so a single bad diff degrades to a skipped survivor rather
          than failing the whole run.
    """
    proc = subprocess.run(
        ["uv", "run", "mutmut", "show", str(mutant_id)],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(repo_root),
    )
    return _parse_show_diff(mutant_id, proc.stdout, repo_root=repo_root)


def _restore_target(target: Path, repo_root: Path) -> None:
    """Restore the target file if mutmut left a mutant on disk.

    WHAT: If ``git diff --exit-code -- <target>`` reports changes, run
          ``git checkout HEAD -- <target>`` to restore the original source.
    WHY:  mutmut mutates in place; a crash must never leave a mutant on disk.
          ``git -C`` isolates the subprocess to the repo so cwd state cannot
          leak. We log whether a restore was actually needed.

    :spec: SPEC-MUTATION-01~1
    """
    rel = target
    try:
        rel = target.relative_to(repo_root)
    except ValueError:
        rel = target

    diff = subprocess.run(
        ["git", "-C", str(repo_root), "diff", "--exit-code", "--", str(rel)],
        capture_output=True,
        text=True,
        check=False,
    )
    if diff.returncode == 0:
        logger.debug("Safety restore: target clean, no restore needed (%s)", rel)
        return

    logger.warning("Safety restore: mutant left on disk, restoring %s", rel)
    subprocess.run(
        ["git", "-C", str(repo_root), "checkout", "HEAD", "--", str(rel)],
        capture_output=True,
        text=True,
        check=False,
    )


def _repo_root() -> Path:
    """Return the repo root (where ``.mutmut-cache`` lives).

    WHAT: Resolve the git top-level directory.
    WHY:  Everything must run from the repo root because mutmut writes its
          cache there; we never rely on the caller's cwd.
    """
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0 and proc.stdout.strip():
        return Path(proc.stdout.strip())
    return Path.cwd()


def run_mutation(
    target: Path,
    tests_file: Path,
    exclude_tests: str | None = None,
) -> MutationResult:
    """Run mutmut against ``target`` using ``tests_file`` and return results.

    WHAT: Scope mutation via mutmut CLI flags (never editing setup.cfg), read
          counts and survivor ids from the SQLite cache, fetch per-survivor
          diffs via ``mutmut show``, and ALWAYS restore the target source in a
          finally block. Returns a structured :class:`MutationResult`.
    WHY:  This is the de-risking slice — a single, safe, importable entry point
          that hides mutmut 2.5.1's Py3.13 bugs (crashing ``results``,
          one-id-per-call ``show``, in-place mutation) behind a clean API.
          mutmut exits non-zero when survivors exist; that is NORMAL and not an
          error. ``error`` is set only on a genuine mutmut/schema failure.

    :spec: SPEC-MUTATION-01~1
    """
    repo_root = _repo_root()
    target = target.resolve()
    tests_file = tests_file.resolve()
    cache_path = repo_root / CACHE_FILENAME

    try:
        rel_target = str(target.relative_to(repo_root))
    except ValueError:
        rel_target = str(target)
    try:
        rel_tests = str(tests_file.relative_to(repo_root))
    except ValueError:
        rel_tests = str(tests_file)

    runner_cmd = _build_runner_command(tests_file, exclude_tests)

    error: str | None = None
    survivors: list[MutantSurvivor] = []
    killed = 0
    survived = 0

    try:
        # 1. Run mutmut. Non-zero exit means survivors exist — NOT an error.
        subprocess.run(
            [
                "uv",
                "run",
                "mutmut",
                "run",
                f"--paths-to-mutate={target}",
                f"--tests-dir={tests_file.parent}",
                f"--runner={runner_cmd}",
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(repo_root),
        )

        # 2. The cache must exist after a run; if not, mutmut never ran.
        if not cache_path.exists():
            error = (
                f"mutmut produced no cache at {cache_path}; mutmut likely "
                "failed to start (check that target and tests exist)"
            )
            return MutationResult(
                target_file=rel_target,
                tests_file=rel_tests,
                total_mutants=0,
                killed=0,
                survived=0,
                kill_rate=0.0,
                survivors=[],
                error=error,
            )

        # 3. Read authoritative counts + survivor ids from the SQLite cache.
        survivor_ids, killed, survived = _read_cache(cache_path)

        # 4. Per-survivor detail (one mutmut show call per id in 2.5.1).
        for sid in survivor_ids:
            survivor = _show_survivor(sid, repo_root)
            if survivor is not None:
                survivors.append(survivor)

    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        logger.error("Mutation run failed: %s", error)
    finally:
        # 5. Safety restore (load-bearing): never leave a mutant on disk.
        _restore_target(target, repo_root)

    total = killed + survived
    kill_rate = (killed / total) if total else 0.0

    return MutationResult(
        target_file=rel_target,
        tests_file=rel_tests,
        total_mutants=total,
        killed=killed,
        survived=survived,
        kill_rate=kill_rate,
        survivors=survivors,
        error=error,
    )


if __name__ == "__main__":  # pragma: no cover - manual smoke entry point
    _target = Path(sys.argv[1])
    _tests = Path(sys.argv[2])
    _excl = sys.argv[3] if len(sys.argv) > 3 else None
    result = run_mutation(_target, _tests, _excl)
    print(result)
