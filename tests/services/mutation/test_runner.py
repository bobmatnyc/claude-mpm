"""Tests for the standalone mutmut runner.

WHAT: Unit tests (subprocess + sqlite stubbed) for the diff parser, the cache
      reader, the safety-restore-in-finally guarantee, kill-rate math, and the
      schema-mismatch error path; plus one on-demand integration test that runs
      real mutmut against the pilot module.
WHY:  The runner is the Phase 1 de-risking slice — its correctness is the
      go/no-go gate for the rest of the mutation testing service, so the parser
      and SQLite contract are pinned by fast, hermetic unit tests, and the real
      mutmut behaviour is validated once by a skippable integration test.

References
----------
LINK: none  (feature introduced in this PR, tracked in GitHub issue #853)
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
from pathlib import Path

import pytest

from claude_mpm.services.mutation import runner as runner_mod
from claude_mpm.services.mutation.runner import (
    MutantSurvivor,
    MutationResult,
    _build_runner_command,
    _classify_mutation,
    _parse_show_diff,
    _read_cache,
    run_mutation,
)

# ---------------------------------------------------------------------------
# Fixtures: a fake mutmut show diff, identical in shape to real 2.5.1 output.
# ---------------------------------------------------------------------------

BOUNDARY_DIFF = """\
--- src/pkg/mod.py
+++ src/pkg/mod.py
@@ -1,5 +1,5 @@
 def add(a, b):
-    if a > 0:
+    if a >= 0:
         return a + b
     return b
"""

ARITHMETIC_DIFF = """\
--- src/pkg/mod.py
+++ src/pkg/mod.py
@@ -1,5 +1,5 @@
 def add(a, b):
     if a > 0:
-        return a + b
+        return a - b
     return b
"""

STRING_DIFF = """\
--- src/pkg/mod.py
+++ src/pkg/mod.py
@@ -10,3 +10,3 @@
 def greet():
-    return "hello"
+    return "XXhelloXX"
"""

PREDICATE_DIFF = """\
--- src/pkg/mod.py
+++ src/pkg/mod.py
@@ -3,3 +3,3 @@
 def check(a, b):
-    return a and b
+    return a or b
"""

REMOVAL_DIFF = """\
--- src/pkg/mod.py
+++ src/pkg/mod.py
@@ -7,3 +7,3 @@
 def side_effect():
-    log_it()
+    pass
"""

# An ARITHMETIC mutation on a line that *contains* a ``<`` (unchanged). The
# ``<`` belongs to a comparison that is identical on both sides, so the only
# thing that changed is the ``+``→``-`` arithmetic operator. This must classify
# as "arithmetic", NOT "boundary" — the prior classifier misfired here because
# it flagged boundary whenever ``<``/``>`` merely appeared on the line.
ARITHMETIC_WITH_LT_DIFF = """\
--- src/pkg/mod.py
+++ src/pkg/mod.py
@@ -1,3 +1,3 @@
 def scaled(a, b):
-    return (a + b) if a < 10 else 0
+    return (a - b) if a < 10 else 0
"""


# ---------------------------------------------------------------------------
# Diff parser
# ---------------------------------------------------------------------------


def test_parse_show_diff_extracts_all_fields():
    survivor = _parse_show_diff(42, BOUNDARY_DIFF)
    assert survivor is not None
    assert survivor.id == 42
    assert survivor.file == "src/pkg/mod.py"
    # Hunk starts at line 1; the changed `-` line is the 2nd line of the hunk.
    assert survivor.line == 2
    assert survivor.original == "if a > 0:"
    assert survivor.mutant == "if a >= 0:"
    assert survivor.mutation_type == "boundary"


def test_parse_show_diff_line_number_uses_hunk_offset():
    # STRING_DIFF hunk starts at line 10; the `-` line is the 2nd hunk line.
    survivor = _parse_show_diff(1, STRING_DIFF)
    assert survivor is not None
    assert survivor.line == 11


def test_parse_show_diff_returns_none_on_garbage():
    assert _parse_show_diff(1, "not a diff at all") is None


def test_parse_show_diff_normalizes_absolute_path_to_repo_relative(tmp_path):
    # mutmut echoes back whatever path we passed (often absolute); the parser
    # must normalize it to repo-relative when given a repo_root.
    abs_target = tmp_path / "src" / "pkg" / "mod.py"
    abs_diff = (
        f"--- {abs_target}\n"
        f"+++ {abs_target}\n"
        "@@ -1,5 +1,5 @@\n"
        " def add(a, b):\n"
        "-    if a > 0:\n"
        "+    if a >= 0:\n"
        "         return a + b\n"
        "     return b\n"
    )
    survivor = _parse_show_diff(1, abs_diff, repo_root=tmp_path)
    assert survivor is not None
    assert survivor.file == "src/pkg/mod.py"


@pytest.mark.parametrize(
    ("diff", "expected_type"),
    [
        (BOUNDARY_DIFF, "boundary"),
        (ARITHMETIC_DIFF, "arithmetic"),
        # Arithmetic edit on a line containing an UNCHANGED ``<`` must NOT be
        # misclassified as boundary (finding #2 regression guard).
        (ARITHMETIC_WITH_LT_DIFF, "arithmetic"),
        (STRING_DIFF, "string"),
        (PREDICATE_DIFF, "predicate"),
        (REMOVAL_DIFF, "removal"),
    ],
)
def test_mutation_type_inference(diff, expected_type):
    survivor = _parse_show_diff(1, diff)
    assert survivor is not None
    assert survivor.mutation_type == expected_type


@pytest.mark.parametrize(
    ("original", "mutant"),
    [
        ("if a < 0:", "if a <= 0:"),  # < -> <=
        ("if a > 0:", "if a >= 0:"),  # > -> >=
        ("if a < 0:", "if a > 0:"),  # < -> >
        ("while x <= n:", "while x < n:"),  # <= -> <
    ],
)
def test_classify_mutation_boundary_only_on_operator_change(original, mutant):
    """A real comparison-operator flip classifies as boundary."""
    assert _classify_mutation(original, mutant) == "boundary"


def test_classify_mutation_unchanged_comparison_is_not_boundary():
    """A line carrying ``<``/``>`` that did NOT change is not boundary.

    Finding #2: arithmetic/predicate/string edits on a line that merely
    *contains* a comparison operator must reach their own branch.
    """
    # Arithmetic edit, comparison ``<`` identical on both sides.
    assert (
        _classify_mutation(
            "y = (a + b) if a < 10 else 0", "y = (a - b) if a < 10 else 0"
        )
        == "arithmetic"
    )
    # Type subscript ``dict[str, int]`` contains ``<``-free brackets but a
    # string edit on a line with a comparison must still classify as string.
    assert (
        _classify_mutation('x = "v" if a < 1 else "w"', 'x = "XX" if a < 1 else "w"')
        == "string"
    )


def test_classify_mutation_other_fallback():
    assert _classify_mutation("foo = bar", "foo = baz") == "other"


# ---------------------------------------------------------------------------
# Runner command construction
# ---------------------------------------------------------------------------


def test_build_runner_command_basic():
    cmd = _build_runner_command(Path("tests/test_x.py"), None)
    assert "uv run python -m pytest tests/test_x.py" in cmd
    assert "-p no:xdist" in cmd
    assert "-x" in cmd
    assert "-k" not in cmd


def test_build_runner_command_with_exclude():
    cmd = _build_runner_command(Path("tests/test_x.py"), "slow or flaky")
    assert "-k 'not (slow or flaky)'" in cmd


def test_build_runner_command_allows_realistic_k_expressions():
    """Benign pytest -k expressions (dots, colons, parens, hyphens) are kept."""
    expr = "TestFoo and (not slow) or test_bar.py::test_baz-fast"
    cmd = _build_runner_command(Path("tests/test_x.py"), expr)
    assert f"-k 'not ({expr})'" in cmd


@pytest.mark.parametrize(
    "evil",
    [
        "slow; rm -rf /",  # command separator
        "slow && curl evil",  # logical-and shell op
        "slow | tee out",  # pipe (vs the word 'or')
        "$(whoami)",  # command substitution
        "`id`",  # backtick substitution
        "slow > /etc/passwd",  # redirect
        "slow' ; echo pwned ; '",  # quote breakout
        "slow\nrm -rf /",  # newline injection
    ],
)
def test_build_runner_command_rejects_shell_metacharacters(evil):
    """exclude_tests with shell metacharacters must raise ValueError.

    mutmut runs the --runner string through a shell, so this is a shell-injection
    guard (finding #1).
    """
    with pytest.raises(ValueError, match="exclude_tests"):
        _build_runner_command(Path("tests/test_x.py"), evil)


# ---------------------------------------------------------------------------
# SQLite cache reader
# ---------------------------------------------------------------------------


def _make_cache(tmp_path: Path, mutants: list[tuple[int, str]]) -> Path:
    """Build a temp .mutmut-cache with the real 2.5.1 Mutant-table schema."""
    cache = tmp_path / ".mutmut-cache"
    con = sqlite3.connect(str(cache))
    con.execute(
        'CREATE TABLE "Mutant" ('
        '"id" INTEGER PRIMARY KEY, "line" INTEGER NOT NULL, '
        '"index" INTEGER NOT NULL, "tested_against_hash" TEXT NOT NULL, '
        '"status" TEXT NOT NULL)'
    )
    for mid, status in mutants:
        con.execute(
            'INSERT INTO "Mutant" VALUES (?, 1, 0, ?, ?)',
            (mid, "hash", status),
        )
    con.commit()
    con.close()
    return cache


def test_read_cache_returns_only_survivor_ids(tmp_path):
    cache = _make_cache(
        tmp_path,
        [
            (1, "bad_survived"),
            (2, "ok_killed"),
            (3, "bad_survived"),
            (4, "ok_killed"),
            (5, "ok_killed"),
        ],
    )
    survivor_ids, killed, survived = _read_cache(cache)
    assert survivor_ids == [1, 3]
    assert killed == 3
    assert survived == 2


def test_read_cache_schema_mismatch_raises(tmp_path):
    # A cache with the wrong table name must raise (guards against silent 100%).
    cache = tmp_path / ".mutmut-cache"
    con = sqlite3.connect(str(cache))
    con.execute('CREATE TABLE "Wrong" ("id" INTEGER PRIMARY KEY)')
    con.commit()
    con.close()
    with pytest.raises(ValueError, match="schema mismatch"):
        _read_cache(cache)


def test_read_cache_schema_mismatch_propagates_into_error(tmp_path, monkeypatch):
    """A schema mismatch surfaces in MutationResult.error, not as a crash."""
    cache = tmp_path / ".mutmut-cache"
    con = sqlite3.connect(str(cache))
    con.execute('CREATE TABLE "Wrong" ("id" INTEGER PRIMARY KEY)')
    con.commit()
    con.close()

    monkeypatch.setattr(runner_mod, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        runner_mod.subprocess,
        "run",
        _fake_subprocess_run(show_output="", fresh_cache=cache),
    )

    target = tmp_path / "src" / "mod.py"
    target.parent.mkdir(parents=True)
    target.write_text("x = 1\n")

    result = run_mutation(target, tmp_path / "tests" / "test_mod.py")
    assert result.error is not None
    assert "schema mismatch" in result.error
    assert result.kill_rate == 0.0


# ---------------------------------------------------------------------------
# run_mutation: stubbed subprocess + sqlite end to end
# ---------------------------------------------------------------------------


def _fake_subprocess_run(
    show_output: str = "",
    run_raises: bool = False,
    fresh_cache: Path | None = None,
):
    """Return a fake subprocess.run that mimics mutmut/git calls.

    If ``fresh_cache`` is given, the simulated ``mutmut run`` touches that cache
    file so its mtime is current — mirroring real mutmut, which rewrites the
    ``.mutmut-cache`` on every run. The runner's run-scope freshness guard
    requires the cache to be newer than run-start, so happy-path tests mark the
    cache fresh; the stale-cache test deliberately omits this.
    """

    def _fake(cmd, *args, **kwargs):
        # Identify which command this is by its mutmut SUBCOMMAND (the token
        # right after "mutmut"). Checking "run"/"show" membership directly is
        # wrong: every command starts with "uv run", so "run" is always present.
        if isinstance(cmd, list) and "mutmut" in cmd:
            sub = (
                cmd[cmd.index("mutmut") + 1]
                if cmd.index("mutmut") + 1 < len(cmd)
                else ""
            )
            if sub == "show":
                return subprocess.CompletedProcess(cmd, 0, show_output, "")
            if sub == "run":
                if run_raises:
                    raise RuntimeError("mutmut exploded")
                if fresh_cache is not None and fresh_cache.exists():
                    fresh_cache.touch()  # mutmut rewrites the cache each run
                return subprocess.CompletedProcess(cmd, 1, "", "")
        if isinstance(cmd, list) and "git" in cmd:
            if "diff" in cmd:
                return subprocess.CompletedProcess(cmd, 0, "", "")
            if "checkout" in cmd:
                return subprocess.CompletedProcess(cmd, 0, "", "")
            if "rev-parse" in cmd:
                return subprocess.CompletedProcess(cmd, 0, "", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    return _fake


def test_run_mutation_happy_path(tmp_path, monkeypatch):
    cache_dir = tmp_path
    _make_cache(
        cache_dir,
        [(1, "bad_survived"), (2, "ok_killed"), (3, "ok_killed")],
    )
    target = tmp_path / "src" / "mod.py"
    target.parent.mkdir(parents=True)
    target.write_text("x = 1\n")

    monkeypatch.setattr(runner_mod, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        runner_mod.subprocess,
        "run",
        _fake_subprocess_run(
            show_output=BOUNDARY_DIFF, fresh_cache=tmp_path / ".mutmut-cache"
        ),
    )

    result = run_mutation(target, tmp_path / "tests" / "test_mod.py")
    assert isinstance(result, MutationResult)
    assert result.error is None
    assert result.total_mutants == 3
    assert result.killed == 2
    assert result.survived == 1
    assert result.kill_rate == pytest.approx(2 / 3)
    assert len(result.survivors) == 1
    assert isinstance(result.survivors[0], MutantSurvivor)
    assert result.survivors[0].mutation_type == "boundary"


def test_run_mutation_kill_rate_zero_when_no_mutants(tmp_path, monkeypatch):
    _make_cache(tmp_path, [])  # empty Mutant table
    target = tmp_path / "src" / "mod.py"
    target.parent.mkdir(parents=True)
    target.write_text("x = 1\n")

    monkeypatch.setattr(runner_mod, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        runner_mod.subprocess,
        "run",
        _fake_subprocess_run(fresh_cache=tmp_path / ".mutmut-cache"),
    )

    result = run_mutation(target, tmp_path / "tests" / "test_mod.py")
    assert result.total_mutants == 0
    assert result.kill_rate == 0.0
    assert result.error is None


def test_run_mutation_missing_cache_sets_error(tmp_path, monkeypatch):
    # No cache file created → mutmut never produced results.
    target = tmp_path / "src" / "mod.py"
    target.parent.mkdir(parents=True)
    target.write_text("x = 1\n")

    monkeypatch.setattr(runner_mod, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(runner_mod.subprocess, "run", _fake_subprocess_run())

    result = run_mutation(target, tmp_path / "tests" / "test_mod.py")
    assert result.error is not None
    assert "no cache" in result.error


def test_run_mutation_stale_cache_sets_error(tmp_path, monkeypatch):
    """A pre-existing cache NOT rewritten by this run yields a stale error.

    Finding #3: a leftover ``.mutmut-cache`` from a prior run would report
    counts/survivors for the WRONG target. The run-scope freshness guard must
    refuse it instead of returning possibly-wrong results.
    """
    cache = _make_cache(tmp_path, [(1, "bad_survived"), (2, "ok_killed")])
    # Backdate the cache far into the past so it predates the run-start
    # timestamp (and the mtime tolerance window) — i.e. it is unambiguously
    # stale. The fake ``mutmut run`` does NOT touch it (no fresh_cache).
    stale_time = cache.stat().st_mtime - 3600
    os.utime(cache, (stale_time, stale_time))

    target = tmp_path / "src" / "mod.py"
    target.parent.mkdir(parents=True)
    target.write_text("x = 1\n")

    monkeypatch.setattr(runner_mod, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(runner_mod.subprocess, "run", _fake_subprocess_run())

    result = run_mutation(target, tmp_path / "tests" / "test_mod.py")
    assert result.error is not None
    assert "stale" in result.error
    assert result.kill_rate == 0.0
    assert result.total_mutants == 0


def test_repo_root_raises_when_git_fails(monkeypatch):
    """_repo_root raises RuntimeError when git is unavailable (finding #4).

    The runner REQUIRES git for safety-restore and cache pathing; a silent
    cwd fallback would point them at the wrong tree.
    """

    def _fake_git_fail(cmd, *args, **kwargs):
        return subprocess.CompletedProcess(cmd, 128, "", "not a git repository")

    monkeypatch.setattr(runner_mod.subprocess, "run", _fake_git_fail)
    with pytest.raises(RuntimeError, match="git is required"):
        runner_mod._repo_root()


def test_safety_restore_called_in_finally_even_on_exception(tmp_path, monkeypatch):
    """If the mutmut subprocess raises, the restore must still run."""
    _make_cache(tmp_path, [(1, "bad_survived")])
    target = tmp_path / "src" / "mod.py"
    target.parent.mkdir(parents=True)
    target.write_text("x = 1\n")

    restore_calls: list[Path] = []

    def _spy_restore(t, repo_root):
        restore_calls.append(t)

    monkeypatch.setattr(runner_mod, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(runner_mod, "_restore_target", _spy_restore)
    monkeypatch.setattr(
        runner_mod.subprocess,
        "run",
        _fake_subprocess_run(run_raises=True),
    )

    result = run_mutation(target, tmp_path / "tests" / "test_mod.py")
    # Restore was invoked exactly once despite the exception.
    assert len(restore_calls) == 1
    # And the failure was captured into error, not propagated.
    assert result.error is not None
    assert "mutmut exploded" in result.error


def test_restore_target_runs_checkout_when_dirty(tmp_path, monkeypatch):
    """_restore_target issues git checkout only when git diff reports changes."""
    calls: list[list[str]] = []

    def _fake(cmd, *args, **kwargs):
        calls.append(cmd)
        if "diff" in cmd:
            # Non-zero exit = dirty (mutant left on disk).
            return subprocess.CompletedProcess(cmd, 1, "mutated", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(runner_mod.subprocess, "run", _fake)
    target = tmp_path / "src" / "mod.py"
    target.parent.mkdir(parents=True)
    target.write_text("x = 1\n")

    runner_mod._restore_target(target, tmp_path)
    # A checkout call must have been issued.
    assert any("checkout" in c for c in calls)


def test_restore_target_skips_checkout_when_clean(tmp_path, monkeypatch):
    calls: list[list[str]] = []

    def _fake(cmd, *args, **kwargs):
        calls.append(cmd)
        # diff exit 0 = clean.
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(runner_mod.subprocess, "run", _fake)
    target = tmp_path / "src" / "mod.py"
    target.parent.mkdir(parents=True)
    target.write_text("x = 1\n")

    runner_mod._restore_target(target, tmp_path)
    assert not any("checkout" in c for c in calls)


# ---------------------------------------------------------------------------
# Integration test: real mutmut against the pilot module (on demand only).
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.timeout(0)  # real mutmut over the full module takes minutes; the
# default 120s pytest-timeout would SIGALRM-kill the process mid-run, bypassing
# the runner's finally-block restore and leaving a mutant on disk.
@pytest.mark.skipif(
    not Path("src/claude_mpm/services/trusty_search_allowlist.py").exists(),
    reason="pilot module not present (run from repo root)",
)
def test_integration_real_mutmut_against_pilot():
    """Decision-checkpoint: run real mutmut on the pilot module.

    WHAT: Invoke run_mutation against trusty_search_allowlist.py and assert a
          healthy kill rate, non-empty parsed survivors, and a clean error.
    WHY:  This is the go/no-go evidence that the runner works end to end with
          real mutmut 2.5.1 on Python 3.13 before we build the CLI/agent slices.
    """
    target = Path("src/claude_mpm/services/trusty_search_allowlist.py").resolve()
    tests_file = Path("tests/services/test_trusty_search_allowlist.py").resolve()

    result = run_mutation(target, tests_file)

    # Baseline kill rate measured on the pilot during the Phase-1 experiment was
    # ~0.615. We assert a conservative floor (default 0.5) rather than the exact
    # baseline so that legitimate future test-suite changes (which shift the kill
    # rate) do not cause spurious failures. The floor is overridable via the
    # MUTATION_PILOT_MIN_KILL_RATE env var for tuning/CI without editing code.
    min_kill_rate = float(os.environ.get("MUTATION_PILOT_MIN_KILL_RATE", "0.5"))

    assert result.error is None, f"mutmut errored: {result.error}"
    assert result.total_mutants > 0
    assert result.kill_rate > min_kill_rate, (
        f"kill rate {result.kill_rate} below floor {min_kill_rate} "
        "(baseline ~0.615); set MUTATION_PILOT_MIN_KILL_RATE to adjust"
    )
    assert result.survivors, "expected at least one survivor to inspect"

    sample = result.survivors[0]
    assert sample.file
    # File must be repo-relative, not an absolute path.
    assert not sample.file.startswith("/")
    assert sample.file.endswith("trusty_search_allowlist.py")
    assert sample.line > 0
    assert sample.original
    assert sample.mutant
