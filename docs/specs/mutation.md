# Mutation Testing Subsystem — Spec-Linked Documentation

This spec governs the mutation-testing framework: the standalone mutmut runner
(Phase 1, PR #854) and the advisory `claude-mpm mutate` CLI command that wraps
it (Phase 1b). It establishes the behavior contracts that the implementing
modules link back to via `SPEC-MUTATION-NN~1` references in their docstrings.

The IDs below use the `{#SPEC-MUTATION-NN~1}` anchor form that the traceability
checker (`tests/test_spec_traceability.py`) parses.

## Table of Contents

| ID | Section | Implementing function(s) |
|----|---------|--------------------------|
| SPEC-MUTATION-01~1 | [Standalone mutmut runner](#standalone-mutmut-runner-spec-mutation-011) | `run_mutation`, `_read_cache`, `_parse_show_diff`, `_classify_mutation`, `_restore_target` |
| SPEC-MUTATION-02~1 | [Advisory mutate CLI command](#advisory-mutate-cli-command-spec-mutation-021) | `manage_mutate`, `is_eligible_for_mutation`, `get_changed_files_vs_main`, `infer_tests_file`, `MutateParser` |

## Implementing Modules

| Module | Spec | Role |
|--------|------|------|
| `src/claude_mpm/services/mutation/runner.py` | SPEC-MUTATION-01~1 | mutmut runner: safe, importable entry point hiding mutmut 2.5.1 Py3.13 bugs |
| `src/claude_mpm/cli/commands/mutate.py` | SPEC-MUTATION-02~1 | CLI handler: eligibility, scoping, output, advisory threshold |
| `src/claude_mpm/cli/parsers/mutate_parser.py` | SPEC-MUTATION-02~1 | CLI argument surface and validation |

---

## Standalone mutmut runner {#SPEC-MUTATION-01~1}

**Status:** Active

### Behavior Contract (WHAT)

- **Inputs:** a target `.py` module `Path`, a paired test-file `Path`, and an
  optional pytest `-k` `exclude_tests` expression.

- **Scoping:** mutation is scoped purely via mutmut CLI flags
  (`--paths-to-mutate`, `--tests-dir`, `--runner`) — never by editing
  `setup.cfg`.

- **Result reading:** survivor ids and killed/survived counts are read directly
  from the `.mutmut-cache` SQLite DB (the `Mutant` table's `status` column),
  because mutmut 2.5.1's `mutmut results` crashes on Python 3.13. A schema guard
  raises if the `Mutant` table or its `id`/`status` columns are absent.

- **Per-survivor detail:** each survivor is fetched with a single
  `mutmut show <id>` call (2.5.1 accepts only one id per call) and its unified
  diff is parsed into a `MutantSurvivor` (file, line, original, mutant, and a
  coarse `mutation_type` of boundary | predicate | string | removal |
  arithmetic | other).

- **Run-scope guard:** the cache mtime must be newer than the run-start
  timestamp (minus a small filesystem-granularity tolerance); a stale cache is
  refused rather than reported, so counts never describe the wrong target.

- **Safety restore:** mutmut mutates source in place. The whole run is wrapped
  in try/finally; on exit `git checkout HEAD -- <target>` restores the file if a
  mutant was left on disk, so a crash never corrupts the working tree.

- **Shell-injection guard:** `exclude_tests` is embedded into a shell `--runner`
  string, so it is validated against a strict pytest `-k` allowlist
  (identifiers, whitespace, `and`/`or`/`not`, parens, `.`, `-`, `:`); any shell
  metacharacter raises `ValueError`.

- **Outputs:** a frozen `MutationResult` (target, tests, total/killed/survived
  counts, kill rate, survivor list, optional `error`). `error` is set only when
  mutmut itself failed — a clean run *with* survivors is the expected, useful
  signal, not an error.

### Rationale (WHY)

This is the de-risking slice: a single, safe, importable API that proves the
mutmut interface works in isolation before any CLI, eligibility heuristic, or
agent wiring is built on top of it. It absorbs mutmut 2.5.1's three load-bearing
Python 3.13 bugs (crashing `results`, one-id-per-call `show`, in-place mutation)
so callers never have to.

---

## Advisory mutate CLI command {#SPEC-MUTATION-02~1}

**Status:** Active

### Behavior Contract (WHAT)

- **Target resolution:** an explicit `TARGET` (an existing `.py` file under
  `src/`) is used directly; otherwise targets are auto-discovered from files
  changed vs `--base` (default `origin/main`) via
  `git diff --name-only <base>...HEAD`, filtered to existing `.py` files under
  `src/`, filtered by the eligibility heuristic, and truncated to `--max-files`
  (default 1). Truncation is always reported — never a silent cap.

- **Eligibility heuristic:** a file is ineligible if it is `__init__.py`; lives
  under `tests/`, `cli/`, `scripts/`, `migrations/`, or any dashboard path; or
  has any top-level import in the I/O-heavy set (`subprocess`, `asyncio`,
  `aiohttp`, `httpx`, `sqlalchemy`, `fastapi`, `click`, `socket`, `paramiko`,
  `boto3`). The rejection reason names the triggering import so the engineer can
  judge a `--force` override. Ineligible targets are reported informationally
  (exit 0), not as errors.

- **Test-file inference:** when `--tests-file` is omitted, a unique
  `tests/**/test_<stem>.py` match for the target's module stem is used; zero or
  ambiguous matches produce a clear error telling the user to pass
  `--tests-file`.

- **Dry-run:** `--dry-run` prints the resolved targets, inferred test files, and
  the exact `uv run mutmut run …` command that would execute, then exits 0
  without invoking mutmut.

- **Execution:** for each resolved (target, tests-file) pair, the command calls
  `run_mutation(target, tests_file, exclude_tests)` — the runner is imported and
  used, never reimplemented.

- **Output:** `--output text` renders a readable per-target summary (kill rate,
  killed/survived counts, and one line per survivor as
  `file:line  original→mutant  [type]`); `--output json` emits
  `json.dumps([dataclasses.asdict(r) for r in results], indent=2)`.

- **Exit code:** advisory by default — with no `--threshold` the command always
  exits 0. With `--threshold N` it exits 1 when any result's survivor count
  exceeds N. A non-`None` `MutationResult.error` always yields a non-zero exit,
  regardless of threshold.

### Rationale (WHY)

Mutation testing is expensive and only produces actionable survivors on
pure-logic modules, so the command gatekeeps cost with the eligibility
heuristic and changed-file scoping, and keeps the engineer in control (explicit
truncation reporting, `--force` override, `--dry-run` preview). Advisory-by-
default lets it run in CI as pure signal until a team opts into a `--threshold`
gate.
