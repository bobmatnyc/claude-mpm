# Mutation Testing

## What is mutation testing?

Mutation testing automatically introduces small code changes ("mutants") — flipping
a `<` to `<=`, removing a list entry, swapping `and` for `or` — then runs the test
suite against each mutant.  A mutant that causes at least one test to fail is "killed".
A mutant that passes all tests "survived", which means the test suite does not verify
that particular behaviour.

It is a second-order quality signal: rather than asking "do the tests run?", it asks
"do the tests actually detect regressions?".

## Tool

**mutmut 2.5.1** (pinned in `pyproject.toml` `[dependency-groups.dev]`).

Why 2.x and not 3.x?  mutmut 3.x introduced a fork-based sandbox for isolation, but
it segfaults on this project's test environment.  2.x uses simpler in-place mutation
which works reliably here.  The pin keeps the behaviour deterministic across machines.

## How to run

```bash
make mutation-test
```

This:
1. Runs `mutmut run` (config read from `setup.cfg`).
2. Prints `mutmut results`.
3. Runs `git diff --exit-code -- src/` as a safety check; if any mutant was
   accidentally left in the source tree the target prints an error, restores
   the file, and exits non-zero.

You can also run the steps individually:

```bash
uv run mutmut run      # generate and test mutants
uv run mutmut results  # print kill/survive counts
uv run mutmut show <id>  # inspect a specific surviving mutant
```

## In-place mutation safety caveat

mutmut 2.x mutates source files **in place**, then restores them.  If the process is
killed mid-run (Ctrl-C, OOM, segfault) a mutant may be left on disk.

**After any mutmut invocation:**

```bash
git diff -- src/
```

If the diff is non-empty a mutant is present.  Restore immediately:

```bash
git checkout HEAD -- src/claude_mpm/services/trusty_search_allowlist.py
```

The `make mutation-test` target runs this check automatically, but when invoking
`uv run mutmut run` directly you must do it yourself.

**Never commit a file that shows a diff in `src/`.**

## Pilot scope

The initial pilot (issue #683) targets a single module:

- `paths_to_mutate = src/claude_mpm/services/trusty_search_allowlist.py`
- `tests_dir = tests/services`
- runner: `pytest tests/services/test_trusty_search_allowlist.py -p no:xdist -x -q`

Config lives in `setup.cfg` under `[mutmut]`.

### Pilot results (2026-06-05)

| Mutants | Killed | Survived | Kill rate |
|---------|--------|----------|-----------|
| 161     | 99     | 62       | 61.5%     |

Survivor categories:
- String-literal mutations inside denylist entries (e.g. `".ssh"` → `".Xsh"`) — these
  require tests that assert the exact string value, not just "something is refused".
- Windows/Linux-specific path branches — not exercised on macOS CI.
- `_DENYLIST_ROOTS` legacy union (unused by `_check_denylist` directly).
- Logger initialisation line (cosmetic).

These are known gaps; the new tests added in this PR close the
_presence/absence_ gaps (each entry is asserted to exist and to actually
block access).

## Next target

`src/claude_mpm/hooks/hook_dedup.py` (issue #677, now merged to main) is the
recommended next candidate: small module, high-value logic, easy to scope.

---

## The framework service (current tooling)

The single-module `make mutation-test` pilot above proved mutmut works in this
environment. The mutation **framework service** generalizes it: instead of a
hand-maintained `setup.cfg` block per module, a runner and CLI scope mutmut to a
single eligible file on demand, hide mutmut's Python 3.13 bugs, and emit a
structured result an agent can act on.

- Runner: `src/claude_mpm/services/mutation/runner.py` (issue #854, merged)
- CLI: `claude-mpm mutate` — `src/claude_mpm/cli/commands/mutate.py` +
  `src/claude_mpm/cli/parsers/mutate_parser.py` (issue #856, merged)

`claude-mpm mutate` is the preferred entry point. It hides every mutmut
workaround documented below — **do not call `mutmut run` / `mutmut results`
directly** unless you are debugging the runner itself.

## Using `claude-mpm mutate`

```text
claude-mpm mutate [TARGET]
                  [--tests-file PATH] [--base BRANCH] [--exclude-tests EXPR]
                  [--max-files N] [--force]
                  [--threshold N] [--dry-run] [--output {text,json}]
```

`TARGET` is **optional**. When given it must be an existing `.py` file under a
`src/` path. When omitted, the command **auto-discovers** the source files
changed versus `--base` (via `git diff --name-only <base>...HEAD`), filters them
through the eligibility heuristic, and mutates up to `--max-files` of them.

| Flag | Default | Meaning |
|------|---------|---------|
| `--tests-file PATH` | inferred | Paired unit test file. If omitted, inferred from the target's module stem (`tests/**/test_<stem>.py`); refuses to guess on zero or multiple matches. |
| `--base BRANCH` | `origin/main` | Base ref for auto-discovery. |
| `--exclude-tests EXPR` | none | pytest `-k` expression to drop slow suites. The runner validates it against a strict shell-injection allowlist before embedding it. |
| `--max-files N` | `1` | Cap on auto-discovered targets. If more eligible files exist, the command prints how many it dropped (it never silently caps). |
| `--force` | off | Bypass the eligibility heuristic (human override) for an explicitly-named `TARGET`. |
| `--threshold N` | unset | Survivor gate — see below. |
| `--dry-run` | off | Print resolved scope + the would-run command, then exit 0. mutmut is **not** executed. |
| `--output {text,json}` | `text` | `json` emits `dataclasses.asdict(MutationResult)` per target. |

### Advisory-by-default threshold

- `--threshold` **unset** (default): the command is purely advisory and
  **always exits 0**. Survivors are signal, not failure — safe to run in CI as
  pure information.
- `--threshold 0`: zero survivors tolerated — **any** survivor fails (exit 1).
- `--threshold N`: exits 1 when a target's survivor count is **greater than N**.

A genuine runner *error* (mutmut failed to start, stale cache, schema mismatch)
is **always** a non-zero failure, regardless of `--threshold`.

### `--dry-run` example

```bash
claude-mpm mutate src/claude_mpm/services/foo.py --dry-run
```

```text
Dry run — resolved scope (mutmut NOT executed):

Target: src/claude_mpm/services/foo.py
  Tests: tests/services/test_foo.py
  Would run: uv run mutmut run --paths-to-mutate=src/claude_mpm/services/foo.py --tests-dir=tests/services
```

### `--output json` example

```bash
claude-mpm mutate src/claude_mpm/services/foo.py --output json
```

```json
[
  {
    "target_file": "src/claude_mpm/services/foo.py",
    "tests_file": "tests/services/test_foo.py",
    "total_mutants": 42,
    "killed": 38,
    "survived": 4,
    "kill_rate": 0.9047619047619048,
    "survivors": [
      {
        "id": 17,
        "file": "src/claude_mpm/services/foo.py",
        "line": 88,
        "original": "if count <= limit:",
        "mutant": "if count < limit:",
        "mutation_type": "boundary"
      }
    ],
    "error": null
  }
]
```

The CLI emits a JSON **list** (one `MutationResult` object per target), so
multi-file auto-discovery runs are handled uniformly.

## mutmut 2.5.1 / Python 3.13 bug workarounds

mutmut is pinned to **2.5.1** (`pyproject.toml` `[dependency-groups.dev]`). On
Python 3.13 that release has two load-bearing bugs that make the naive
`mutmut run` + `mutmut results` workflow unusable. The runner
(`src/claude_mpm/services/mutation/runner.py`) hides all of this:

1. **`mutmut results` crashes** with a pony-orm `QueryResultIterator not
   iterable` error. The runner does **not** call `mutmut results`. Instead it
   reads survivors and counts directly from the `.mutmut-cache` SQLite database
   at the repo root, querying the `Mutant` table by `status`:
   - `bad_survived` → survived
   - `ok_killed` → killed

   The runner asserts the `Mutant` table and its `id`/`status` columns exist
   first, raising a clear schema-mismatch error rather than silently reporting a
   bogus 100% kill rate if mutmut's cache layout ever changes.

2. **`mutmut show` accepts only one mutant id per call** in 2.5.1, so the runner
   queries per survivor — one `mutmut show <id>` subprocess per surviving mutant
   — and parses each unified diff into a survivor record.

Additional runner safeguards:

- **Scope via CLI flags, never `setup.cfg`.** The runner passes
  `--paths-to-mutate`, `--tests-dir`, and `--runner` on the mutmut command line.
  It does not read or edit `setup.cfg` (that file's `[mutmut]` block is the old
  pilot's config and is independent of the service).
- **In-place mutation → `finally`-block restore.** mutmut mutates source on
  disk in place. The runner wraps the whole run in `try/finally` and, in the
  `finally`, checks `git diff --exit-code -- <target>` and runs
  `git checkout HEAD -- <target>` if a mutant was left behind — so a crash mid-run
  never corrupts the working tree.
- **Stale-cache guard.** The runner timestamps the run start and refuses a
  `.mutmut-cache` whose mtime predates it, rather than reporting a prior run's
  counts for the wrong target.

> Warning: do not call `mutmut results` directly on this project under Python
> 3.13 — it will crash. Use `claude-mpm mutate`, which reads the SQLite cache
> for you.

## Eligibility heuristic

Mutation testing only produces actionable survivors on **pure-logic modules
that have a dedicated unit test**. The CLI gates targets through
`is_eligible_for_mutation()` (`src/claude_mpm/cli/commands/mutate.py`) before
running mutmut. A file is **rejected** when:

- it is `__init__.py` (no meaningful logic), or
- it lives under a `tests/`, `cli/`, `scripts/`, or `migrations/` path
  component, or contains a `dashboard` path component (UI, not unit-testable
  logic), or
- any **top-level import** is I/O-heavy / infra-bound — currently
  `subprocess`, `asyncio`, `aiohttp`, `httpx`, `sqlalchemy`, `fastapi`,
  `click`, `socket`, `paramiko`, `boto3`. Mutants in such modules are dominated
  by the environment, not by the test suite's assertions.

The rejection reason names the offending import or path so you can judge whether
an override is warranted. `--force` bypasses the heuristic for an
explicitly-named `TARGET` (auto-discovered targets are always pre-filtered).

This is deliberately **targeted, not blanket**: in the validation experiment only
~4.9% of changed modules were eligible. The point is to mutate the few
pure-logic files where survivors are real test gaps, not to mutate everything.

## Structured survivor schema (`--output json`)

`--output json` serializes the runner's frozen dataclasses
(`src/claude_mpm/services/mutation/runner.py`):

**`MutationResult`** — one per target:

| Field | Type | Meaning |
|-------|------|---------|
| `target_file` | `str` | Repo-relative path of the mutated source file. |
| `tests_file` | `str` | Repo-relative path of the test file used as the runner. |
| `total_mutants` | `int` | `killed + survived`. |
| `killed` | `int` | Mutants caught by the tests (`ok_killed`). |
| `survived` | `int` | Mutants the tests missed (`bad_survived`). |
| `kill_rate` | `float` | `killed / total`, or `0.0` when `total == 0`. |
| `survivors` | `list[MutantSurvivor]` | One entry per surviving mutant. |
| `error` | `str \| null` | Set **only** when mutmut itself failed. A clean run with survivors is **not** an error. |

**`MutantSurvivor`** — one per surviving mutant:

| Field | Type | Meaning |
|-------|------|---------|
| `id` | `int` | mutmut's mutant id (usable with `mutmut show <id>`). |
| `file` | `str` | Repo-relative path of the mutated file. |
| `line` | `int` | Line number of the mutated source line. |
| `original` | `str` | The original source line (stripped). |
| `mutant` | `str` | The mutated source line (stripped). |
| `mutation_type` | `str` | One of `boundary`, `predicate`, `string`, `removal`, `arithmetic`, `other`. |

## QA closed-loop

The QA agent has a **Mutation Testing Sub-Loop** that consumes this service:
run `claude-mpm mutate` on the changed pure-logic modules → triage the
structured survivors → write killing tests for genuine gaps → have `code-critic`
run a gaming-check on those tests (so the new tests strengthen behavior rather
than merely silencing the survivor). The loop is **advisory**, mirroring the
policy below, and ships via the external agents repo rather than the bundled
agent templates.

## Policy

Mutation testing is **advisory and on-demand**.  It is NOT a blocking CI gate.

Rationale: mutmut 2.x runtime is ~30 s for this scoped target but would scale to
minutes on larger modules.  Requiring green mutation scores in CI would make the suite
fragile and slow.  Instead, run it manually when strengthening a test module or
reviewing test coverage confidence.

The advisory policy is enforced at the CLI level by `--threshold` being
**unset by default**: with no threshold, `claude-mpm mutate` always exits 0, so
it can run in pipelines as pure signal. Opting into a gate is explicit —
`--threshold 0` fails on any survivor, `--threshold N` fails above N — and is the
caller's deliberate choice, not the default.
