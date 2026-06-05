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

## Policy

Mutation testing is **advisory and on-demand**.  It is NOT a blocking CI gate.

Rationale: mutmut 2.x runtime is ~30 s for this scoped target but would scale to
minutes on larger modules.  Requiring green mutation scores in CI would make the suite
fragile and slow.  Instead, run it manually when strengthening a test module or
reviewing test coverage confidence.
