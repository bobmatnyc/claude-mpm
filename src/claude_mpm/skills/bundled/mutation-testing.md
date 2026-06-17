---
skill_id: mutation-testing
skill_version: 0.3.0
name: mutation-testing
when_to_use: when auditing test suite effectiveness on a critical module, evaluating whether green tests actually protect behavior, or deciding whether to invest more in test coverage
description: Audit whether a test suite actually detects regressions (not just whether it runs) by introducing small code mutations and measuring how many your tests catch. Apply when hardening a critical, logic-dense module's tests, evaluating coverage confidence after a near-miss bug, or deciding if "green tests" really mean "protected behavior". Advisory and on-demand — not a blocking CI gate.
updated_at: 2026-06-17T00:00:00Z
tags: [testing, quality-assurance, mutation-testing, test-effectiveness, advisory]
effort: high
---

# Mutation Testing

A second-order test-quality signal: instead of asking "do my tests run?", it asks
"do my tests actually detect regressions?". Use it to audit the strength of an
existing test suite — most valuable on logic-dense code, applied on-demand, never as
a default blocking CI gate.

## What mutation testing is

A mutation tool makes small, automatic edits to your source code — each a "mutant":

- `<` → `<=` (off-by-one / boundary)
- `and` → `or` (predicate logic)
- `==` → `!=` (negated condition)
- removing a list/dict entry (allowlist/denylist coverage)
- `return x` → `return None`, `+` → `-`, deleting a statement

For each mutant it re-runs your test suite:

- **Killed** — at least one test fails. Good: your tests detect that change.
- **Survived** — all tests still pass. Bad: no test verifies that behavior. The
  mutant models a real bug your suite would not catch.

The **kill rate** (killed / total mutants) measures *test effectiveness*, not code
execution.

**Contrast with line coverage.** Line coverage tells you a line *executed* during
tests. It says nothing about whether any assertion would *fail* if that line were
wrong. You can have 100% line coverage with a 40% kill rate: every line runs, but
half of the logic changes go undetected because the tests assert too little (or
nothing) about the result. Mutation testing closes exactly that blind spot.

## When to use it (and when NOT to)

**Use it to:**

- Audit a critical module's test strength before relying on it (payment math, auth
  predicates, an allowlist that gates filesystem or network access).
- Harden tests after a near-miss bug — a regression that *should* have been caught
  by tests but wasn't. Mutation testing finds the sibling gaps.
- Evaluate coverage confidence: turn "we have 90% coverage" into "and here are the
  specific behaviors no test actually pins down".

**Do NOT use it as:**

- A blocking CI gate by default. Runtime is `N mutants × full suite`, which scales
  from seconds to many minutes; gating merges on it makes CI slow and fragile.
- A metric to chase to 100%. Some mutants are *equivalent* (semantically identical
  to the original) and can never be killed. A rising kill rate on a critical module
  is the goal — not a perfect score.

## Why it's especially valuable for logic-dense / data-heavy code

Mutation testing shines on **deterministic, branch-heavy code with exact
correctness criteria** — the transform core of data pipelines and validation layers:

- filter / join / dedup predicates
- boundary conditions (`>=` vs `>`, inclusive/exclusive ranges)
- validation / allowlist / denylist logic
- aggregation and grouping rules

Here a `<` → `<=` or `and` → `or` mutation models **real silent data corruption**:
the pipeline still runs, emits no error, and produces subtly wrong rows. If your
tests can't tell the mutated version from the correct one, neither can your CI when
someone introduces that bug for real.

**The honest caveat — it is a poor fit for:**

- **(a) I/O-heavy glue code.** The suite reruns once per mutant, so slow tests
  (network, DB, filesystem, subprocess) make a run take hours. Mutate the pure logic,
  not the plumbing.
- **(b) Statistical / ML code.** Tolerance-based assertions (`assert abs(a - b) <
  1e-3`) let many mutants slip through as misleading "survivors," and such code is
  riddled with *equivalent* mutants (e.g. reordering a commutative sum). The
  survivor list becomes noise.

**Rule:** scope to pure functions, mock out I/O, and keep statistical/ML code out of
the mutated set entirely.

## Tool selection by language

| Language          | Tool(s)                                   | Notes |
|-------------------|-------------------------------------------|-------|
| Python            | `mutmut`, or `cosmic-ray`                 | Pin `mutmut` 2.x if 3.x's fork-based sandbox segfaults in your env; 2.x uses simpler in-place mutation. |
| JavaScript / TS   | Stryker (`@stryker-mutator/core`)         | Config in `stryker.conf.json`; fork/sandbox isolation, no in-place risk. |
| Java              | PIT (`pitest`)                            | Maven/Gradle plugin; bytecode mutation, very fast. |
| Go                | `go-mutesting`, or `gremlins`             | `gremlins` is the more actively maintained choice. |
| Ruby              | `mutant`                                  | Tight RSpec integration; subject-scoped runs. |
| Rust              | `cargo-mutants`                           | First-class Cargo subcommand. |
| .NET              | Stryker.NET (`dotnet-stryker`)            | Same family as JS Stryker. |

## How to deploy it into a project

A repeatable recipe, generalizable across tools:

1. **Add the mutation tool as a PINNED dev dependency.** Exact version pin keeps
   results deterministic across machines and CI (e.g. `mutmut==2.5.1`,
   `"@stryker-mutator/core": "8.2.6"`, `pitest` `<version>` in the POM).

2. **Scope it to ONE high-value module first (a pilot).** Set `paths-to-mutate` to a
   single pure-logic file and point the runner at *that file's* tests only. Run the
   suite **serially** — for pytest pass `-p no:xdist` — because in-place mutators
   modify source on disk, and parallel workers racing on the same file corrupt
   results.

3. **Put config in the tool's config file**, not ad-hoc CLI flags: `setup.cfg`
   `[mutmut]`, `stryker.conf.json`, the `pitest` plugin block in `pom.xml`. This
   keeps the scope reviewable and reproducible.

4. **Add a single task/target** (`make mutation-test`, an npm script) that runs the
   tool, prints results, and — **critical for in-place mutators like mutmut** — runs
   a post-run safety check that restores the source file if a mutant was left on disk
   after a crash or Ctrl-C, on **any** exit code.

5. **Gitignore the tool's cache/working dirs**: `.mutmut-cache`, `mutants/`,
   `.stryker-tmp`, `reports/mutation/`.

6. **Write a short developer doc** explaining the advisory policy and how to read
   survivors, so the next person knows the run is on-demand and what a "survivor"
   obliges them to do (or not).

### Concrete example — Python / mutmut Make target with safety check

`setup.cfg`:

```ini
[mutmut]
paths_to_mutate=src/yourpkg/core/transform.py
tests_dir=tests/core
runner=uv run python -m pytest tests/core/test_transform.py -p no:xdist -x -q
```

`Makefile` — note the safety check runs regardless of mutmut's exit code:

```make
mutation-test: ## Run mutation tests against the pilot module (advisory, on-demand)
	@echo "Running mutation tests (scope: core/transform.py)..."
	@mutmut_rc=0; uv run mutmut run || mutmut_rc=$$?; \
	echo "Mutation run complete (exit code: $$mutmut_rc). Results:"; \
	uv run mutmut results; \
	echo "SAFETY CHECK: verifying no mutant left in pilot file ..."; \
	if ! git diff --exit-code -- src/yourpkg/core/transform.py; then \
		echo "MUTANT LEFT IN SOURCE — restoring..."; \
		git checkout HEAD -- src/yourpkg/core/transform.py; \
		echo "transform.py had uncommitted changes after mutmut — restored."; \
		exit 1; \
	fi; \
	echo "pilot file is clean"; \
	if [ $$mutmut_rc -ne 0 ]; then \
		echo "mutmut exited $$mutmut_rc (survivors exist — see results above)"; \
		exit $$mutmut_rc; \
	fi; \
	echo "Mutation tests complete — all mutants killed"
```

The `git diff --exit-code` / `git checkout HEAD --` pair is the load-bearing safety
net: even if `mutmut run` segfaults mid-mutation and leaves a corrupted source file,
the target detects and restores it before you can accidentally commit it.

## In-place mutation safety caveat

Some tools (notably **mutmut 2.x**) mutate source files **in place**, then restore
them. A killed process — Ctrl-C, OOM, segfault — can leave a mutant on disk.

- After any *manual* run (`uv run mutmut run` directly), always check:

  ```bash
  git diff -- src/
  ```

  Non-empty diff means a mutant is present. Restore it:

  ```bash
  git checkout HEAD -- src/yourpkg/core/transform.py
  ```

- **Never commit a file that shows a diff in your source tree after a mutation run.**
- Fork/sandbox-based tools (**Stryker, PIT, cargo-mutants**) mutate in an isolated
  copy and never touch your working tree, so they avoid this hazard entirely.

## Reading the results

Triage every survivor into one of three buckets:

- **Equivalent mutant** — the mutated code is semantically identical to the original
  (e.g. reordering a commutative operation, an unreachable defensive branch). It can
  *never* be killed. Acceptable; note it and move on.
- **Genuine test gap** — a real behavior no test pins down. Fix it by adding an
  assertion on the **exact** value or behavior, not a vague "it didn't crash" check.
  Example: an allowlist test that asserts "some path is refused" lets a string-literal
  mutation (`".ssh"` → `".Xsh"`) survive; assert that *that specific entry* blocks
  access.
- **Platform-specific branch** — Windows/Linux/macOS-only code paths not exercised on
  this CI runner. Document it; optionally cover with a parametrized/skipped test.

A 100% kill rate is neither achievable (equivalent mutants exist) nor the goal. The
signal that matters is a **rising kill rate on a critical module** over time, and a
shrinking list of *genuine* gaps.

## Policy recommendation

Mutation testing is **advisory and on-demand** — NOT a blocking CI gate by default.

Rationale: runtime is `N mutants × full suite`, which scales from seconds on a tiny
pilot to many minutes on a real module. Requiring green mutation scores in CI makes
the pipeline slow and fragile, and tempts teams to chase an unreachable 100%. Instead:

- Run it manually (`make mutation-test`) when **strengthening a specific test
  module**, after a near-miss bug, or when auditing a critical module's coverage
  confidence.
- Keep it scoped to high-value pure-logic modules; expand the mutated set one pilot
  at a time.
- Track kill rate per critical module as a trend, not a gate.

## Tool bugs & workarounds (mutmut 2.5.1 / Python 3.13)

If you run **mutmut 2.5.1 on Python 3.13 manually**, two bugs will bite you. They
are load-bearing — without the workarounds you cannot read survivors at all:

1. **`mutmut results` crashes** with a pony-orm `QueryResultIterator not
   iterable` error. Do not call it. Read survivors and counts directly from the
   `.mutmut-cache` **SQLite database** written at the repo root after a run. Query
   the `Mutant` table by `status`:
   - `bad_survived` → the mutant **survived** (a test gap)
   - `ok_killed` → the mutant was **killed**

   ```sql
   -- survivor ids (feed each to `mutmut show <id>`)
   SELECT id FROM Mutant WHERE status = 'bad_survived' ORDER BY id;
   -- counts
   SELECT status, COUNT(*) FROM Mutant GROUP BY status;
   ```

   Guard for a schema change: if the `Mutant` table or its `id`/`status` columns
   are absent, fail loudly rather than reporting a bogus 100% kill rate.

2. **`mutmut show` accepts only ONE mutant id per call** in 2.5.1. Loop over the
   survivor ids and call `mutmut show <id>` once per id, parsing each unified diff
   (`--- file` / `@@ -start,n @@` / `-original` / `+mutant`) for the location and
   the before/after source.

Scope the run via mutmut **CLI flags** (`--paths-to-mutate`, `--tests-dir`,
`--runner`) rather than editing `setup.cfg`, and because mutmut mutates source
**in place**, always restore in a `finally` (`git diff --exit-code -- <target>`
then `git checkout HEAD -- <target>`) so a crash never leaves a mutant on disk.

## Preferred interface in this project: `claude-mpm mutate`

In **claude-mpm**, do not invoke mutmut by hand — use the `claude-mpm mutate`
command. It hides every workaround above (SQLite survivor read, per-id
`mutmut show`, CLI-flag scoping, in-place restore, stale-cache guard) and gates
targets through an eligibility heuristic (pure-logic modules with a dedicated
unit test only; I/O-heavy / infra files are skipped).

```bash
# Auto-discover changed eligible files vs origin/main, structured output:
claude-mpm mutate --output json

# Mutate one explicit file:
claude-mpm mutate src/claude_mpm/services/foo.py --output json
```

It is **advisory by default** (no `--threshold` → always exits 0; survivors are
signal). Opt into a gate with `--threshold 0` (any survivor fails) or
`--threshold N` (fails above N).

`--output json` emits a list of structured results an agent can triage directly:

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

Schema — `MutationResult`: `target_file`, `tests_file`, `total_mutants`,
`killed`, `survived`, `kill_rate` (`killed/total`, `0.0` when empty),
`survivors[]`, `error` (set only on a genuine mutmut failure — survivors are
**not** an error). Each `MutantSurvivor`: `id`, `file`, `line`, `original`,
`mutant`, `mutation_type` (one of `boundary`, `predicate`, `string`, `removal`,
`arithmetic`, `other`).
