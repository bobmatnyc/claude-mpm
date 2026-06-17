"""Unit tests for the ``claude-mpm mutate`` command handler.

WHAT: Exercise the eligibility heuristic, changed-file scanner, test-file
      inference, dry-run, JSON output, threshold semantics, and --max-files
      truncation in :mod:`claude_mpm.cli.commands.mutate`, with the real mutmut
      runner, git, and subprocess calls fully stubbed.
WHY:  The command is the cost gatekeeper and exit-code contract for mutation
      testing; its decisions (skip/run, advisory vs gate) must be verified
      without ever invoking real mutmut, which is slow and mutates source.

References
----------
LINK: SPEC-MUTATION-02~1 : docs/specs/mutation.md#SPEC-MUTATION-02~1
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from claude_mpm.cli.commands import mutate as mutate_mod
from claude_mpm.cli.commands.mutate import (
    get_changed_files_vs_main,
    infer_tests_file,
    is_eligible_for_mutation,
    manage_mutate,
)
from claude_mpm.services.mutation.runner import MutantSurvivor, MutationResult


def _args(**overrides) -> Namespace:
    """Build a mutate Namespace with sensible defaults, overridable per test."""
    defaults = {
        "target": None,
        "tests_file": None,
        "base": "origin/main",
        "exclude_tests": None,
        "max_files": 1,
        "force": False,
        "threshold": None,
        "dry_run": False,
        "output": "text",
    }
    defaults.update(overrides)
    return Namespace(**defaults)


def _result(survived: int = 0, error: str | None = None) -> MutationResult:
    """Build a MutationResult with a controllable survivor count / error."""
    survivors = [
        MutantSurvivor(
            id=i,
            file="src/claude_mpm/foo.py",
            line=10 + i,
            original="x == 1",
            mutant="x != 1",
            mutation_type="boundary",
        )
        for i in range(survived)
    ]
    killed = 7
    total = killed + survived
    return MutationResult(
        target_file="src/claude_mpm/foo.py",
        tests_file="tests/test_foo.py",
        total_mutants=total,
        killed=killed,
        survived=survived,
        kill_rate=(killed / total) if total else 0.0,
        survivors=survivors,
        error=error,
    )


# --------------------------------------------------------------------------- #
# Eligibility heuristic
# --------------------------------------------------------------------------- #


def test_eligibility_rejects_init_py(tmp_path):
    init = tmp_path / "__init__.py"
    init.write_text("x = 1\n")
    eligible, reason = is_eligible_for_mutation(init)
    assert eligible is False
    assert "__init__" in reason


def test_eligibility_rejects_cli_path(tmp_path):
    cli_file = tmp_path / "cli" / "thing.py"
    cli_file.parent.mkdir(parents=True)
    cli_file.write_text("def f():\n    return 1\n")
    eligible, reason = is_eligible_for_mutation(cli_file)
    assert eligible is False
    assert "cli" in reason


def test_eligibility_rejects_asyncio_import_and_names_it(tmp_path):
    mod = tmp_path / "service.py"
    mod.write_text("import asyncio\n\n\ndef f():\n    return 1\n")
    eligible, reason = is_eligible_for_mutation(mod)
    assert eligible is False
    # The rejection reason must NAME the triggering import.
    assert "asyncio" in reason


def test_eligibility_accepts_pure_logic_file(tmp_path):
    mod = tmp_path / "pure.py"
    mod.write_text(
        "def classify(x):\n    if x > 0:\n        return 'pos'\n    return 'nonpos'\n"
    )
    eligible, reason = is_eligible_for_mutation(mod)
    assert eligible is True
    assert reason == "eligible"


# --------------------------------------------------------------------------- #
# Changed-file scanner
# --------------------------------------------------------------------------- #


def test_changed_file_scanner_filters_to_existing_src_py(monkeypatch, tmp_path):
    # git diff emits repo-root-relative paths; existence is checked against the
    # repo root (here stubbed to tmp_path), NOT the CWD.
    monkeypatch.setattr(mutate_mod, "_repo_root", lambda: tmp_path)

    existing = tmp_path / "src" / "pkg" / "real.py"
    existing.parent.mkdir(parents=True)
    existing.write_text("x = 1\n")

    diff_output = "\n".join(
        [
            "src/pkg/real.py",  # src + .py + exists  -> kept
            "src/pkg/missing.py",  # src + .py + NOT exists -> dropped
            "docs/notes.py",  # .py but not under src/ -> dropped
            "src/pkg/data.txt",  # not .py -> dropped
        ]
    )

    class _Proc:
        returncode = 0
        stdout = diff_output
        stderr = ""

    monkeypatch.setattr(mutate_mod.subprocess, "run", lambda *a, **k: _Proc())

    result = get_changed_files_vs_main("origin/main")
    assert result == [Path("src/pkg/real.py")]


def test_changed_file_scanner_returns_empty_on_git_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(mutate_mod, "_repo_root", lambda: tmp_path)

    class _Proc:
        returncode = 1
        stdout = ""
        stderr = "fatal: bad revision"

    monkeypatch.setattr(mutate_mod.subprocess, "run", lambda *a, **k: _Proc())
    assert get_changed_files_vs_main("origin/main") == []


# --------------------------------------------------------------------------- #
# Test-file inference
# --------------------------------------------------------------------------- #


def test_infer_tests_file_single_match(monkeypatch, tmp_path):
    monkeypatch.setattr(mutate_mod, "_repo_root", lambda: tmp_path)
    tests_dir = tmp_path / "tests" / "services"
    tests_dir.mkdir(parents=True)
    test_file = tests_dir / "test_widget.py"
    test_file.write_text("def test_x():\n    pass\n")

    target = Path("src/pkg/widget.py")
    inferred, err = infer_tests_file(target)
    assert err is None
    assert inferred == Path("tests/services/test_widget.py")


def test_infer_tests_file_no_match_errors(monkeypatch, tmp_path):
    monkeypatch.setattr(mutate_mod, "_repo_root", lambda: tmp_path)
    (tmp_path / "tests").mkdir()
    target = Path("src/pkg/widget.py")
    inferred, err = infer_tests_file(target)
    assert inferred is None
    assert "--tests-file" in err


def test_infer_tests_file_ambiguous_errors(monkeypatch, tmp_path):
    monkeypatch.setattr(mutate_mod, "_repo_root", lambda: tmp_path)
    a = tmp_path / "tests" / "a"
    b = tmp_path / "tests" / "b"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    (a / "test_widget.py").write_text("")
    (b / "test_widget.py").write_text("")

    target = Path("src/pkg/widget.py")
    inferred, err = infer_tests_file(target)
    assert inferred is None
    assert "ambiguous" in err.lower()
    assert "--tests-file" in err


# --------------------------------------------------------------------------- #
# --dry-run
# --------------------------------------------------------------------------- #


def test_dry_run_prints_command_and_does_not_invoke_runner(
    monkeypatch, tmp_path, capsys
):
    target = tmp_path / "src" / "pkg" / "pure.py"
    target.parent.mkdir(parents=True)
    target.write_text("def f(x):\n    return x + 1\n")
    tests_file = tmp_path / "tests" / "test_pure.py"
    tests_file.parent.mkdir(parents=True)
    tests_file.write_text("def test_f():\n    pass\n")

    called = {"run": False}

    def _boom(*a, **k):
        called["run"] = True
        raise AssertionError("run_mutation must NOT be called on --dry-run")

    monkeypatch.setattr(mutate_mod, "run_mutation", _boom)

    rc = manage_mutate(
        _args(target=str(target), tests_file=str(tests_file), dry_run=True)
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert called["run"] is False
    assert "mutmut run" in out
    assert "--paths-to-mutate" in out


# --------------------------------------------------------------------------- #
# --output json
# --------------------------------------------------------------------------- #


def test_output_json_is_valid_and_has_result_fields(monkeypatch, tmp_path, capsys):
    target = tmp_path / "src" / "pkg" / "pure.py"
    target.parent.mkdir(parents=True)
    target.write_text("def f(x):\n    return x + 1\n")
    tests_file = tmp_path / "tests" / "test_pure.py"
    tests_file.parent.mkdir(parents=True)
    tests_file.write_text("def test_f():\n    pass\n")

    monkeypatch.setattr(mutate_mod, "run_mutation", lambda *a, **k: _result(survived=2))

    rc = manage_mutate(
        _args(target=str(target), tests_file=str(tests_file), output="json")
    )
    out = capsys.readouterr().out
    assert rc == 0  # advisory: no threshold
    payload = json.loads(out)
    assert isinstance(payload, list)
    entry = payload[0]
    for field in (
        "target_file",
        "tests_file",
        "total_mutants",
        "killed",
        "survived",
        "kill_rate",
        "survivors",
        "error",
    ):
        assert field in entry
    assert entry["survived"] == 2
    assert entry["survivors"][0]["mutation_type"] == "boundary"


# --------------------------------------------------------------------------- #
# Threshold semantics
# --------------------------------------------------------------------------- #


def _run_with_survivors(monkeypatch, tmp_path, *, survived, threshold):
    target = tmp_path / "src" / "pkg" / "pure.py"
    target.parent.mkdir(parents=True)
    target.write_text("def f(x):\n    return x + 1\n")
    tests_file = tmp_path / "tests" / "test_pure.py"
    tests_file.parent.mkdir(parents=True)
    tests_file.write_text("def test_f():\n    pass\n")

    monkeypatch.setattr(
        mutate_mod, "run_mutation", lambda *a, **k: _result(survived=survived)
    )
    return manage_mutate(
        _args(
            target=str(target),
            tests_file=str(tests_file),
            threshold=threshold,
        )
    )


def test_threshold_unset_is_advisory_exit_zero(monkeypatch, tmp_path):
    rc = _run_with_survivors(monkeypatch, tmp_path, survived=3, threshold=None)
    assert rc == 0


def test_threshold_zero_with_survivors_exits_one(monkeypatch, tmp_path):
    rc = _run_with_survivors(monkeypatch, tmp_path, survived=2, threshold=0)
    assert rc == 1


def test_threshold_above_survivors_exits_zero(monkeypatch, tmp_path):
    rc = _run_with_survivors(monkeypatch, tmp_path, survived=3, threshold=5)
    assert rc == 0


def test_runner_error_exits_nonzero_even_when_advisory(monkeypatch, tmp_path):
    target = tmp_path / "src" / "pkg" / "pure.py"
    target.parent.mkdir(parents=True)
    target.write_text("def f(x):\n    return x + 1\n")
    tests_file = tmp_path / "tests" / "test_pure.py"
    tests_file.parent.mkdir(parents=True)
    tests_file.write_text("def test_f():\n    pass\n")

    monkeypatch.setattr(
        mutate_mod,
        "run_mutation",
        lambda *a, **k: _result(error="mutmut blew up"),
    )
    rc = manage_mutate(
        _args(target=str(target), tests_file=str(tests_file), threshold=None)
    )
    assert rc == 1


# --------------------------------------------------------------------------- #
# --max-files truncation
# --------------------------------------------------------------------------- #


def test_max_files_truncation_is_reported(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mutate_mod, "_repo_root", lambda: tmp_path)
    # Three eligible changed files, max_files=1 -> 2 dropped, must be noted.
    files = []
    for i in range(3):
        f = tmp_path / "src" / "pkg" / f"mod{i}.py"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("def f(x):\n    return x + 1\n")
        files.append(f)

    monkeypatch.setattr(
        mutate_mod, "get_changed_files_vs_main", lambda base: list(files)
    )
    # Provide a matching test file so inference succeeds for the single target.
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "test_mod0.py").write_text("def test():\n    pass\n")

    monkeypatch.setattr(mutate_mod, "run_mutation", lambda *a, **k: _result(survived=0))

    rc = manage_mutate(_args(target=None, max_files=1))
    out = capsys.readouterr().out
    assert rc == 0
    # 3 eligible - 1 cap = 2 dropped, surfaced (no silent capping).
    assert "2 additional eligible" in out
    assert "--max-files" in out


# --------------------------------------------------------------------------- #
# Argument validation (validate_args is wired into manage_mutate)
# --------------------------------------------------------------------------- #


def test_validation_nonexistent_target_errors(monkeypatch, tmp_path, capsys):
    # A target under src/ that does not exist must be rejected up front with a
    # non-zero exit code, never silently accepted.
    missing = tmp_path / "src" / "pkg" / "ghost.py"

    def _boom(*a, **k):
        raise AssertionError("run_mutation must NOT run on a validation failure")

    monkeypatch.setattr(mutate_mod, "run_mutation", _boom)

    rc = manage_mutate(_args(target=str(missing)))
    out = capsys.readouterr().out
    assert rc != 0
    assert "does not exist" in out.lower()


def test_validation_max_files_zero_errors(monkeypatch, capsys):
    # --max-files 0 is invalid (must be >= 1) and must fail, not silently cap.
    def _boom(*a, **k):
        raise AssertionError("run_mutation must NOT run on a validation failure")

    monkeypatch.setattr(mutate_mod, "run_mutation", _boom)

    rc = manage_mutate(_args(target=None, max_files=0))
    out = capsys.readouterr().out
    assert rc != 0
    assert "--max-files" in out


# --------------------------------------------------------------------------- #
# Repo-root anchoring (works from a subdirectory, not just the repo root)
# --------------------------------------------------------------------------- #


def test_resolution_anchored_to_repo_root_from_subdir(monkeypatch, tmp_path):
    # Lay out a fake repo: src file changed vs base + its paired test file.
    src_file = tmp_path / "src" / "pkg" / "widget.py"
    src_file.parent.mkdir(parents=True)
    src_file.write_text("def f(x):\n    return x + 1\n")
    test_file = tmp_path / "tests" / "pkg" / "test_widget.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_f():\n    pass\n")

    # The repo root is tmp_path; the CLI is invoked from a DEEP subdirectory.
    monkeypatch.setattr(mutate_mod, "_repo_root", lambda: tmp_path)
    subdir = tmp_path / "src" / "pkg" / "deep" / "nested"
    subdir.mkdir(parents=True)
    monkeypatch.chdir(subdir)

    # git diff emits repo-root-relative paths regardless of CWD.
    class _Proc:
        returncode = 0
        stdout = "src/pkg/widget.py\n"
        stderr = ""

    monkeypatch.setattr(mutate_mod.subprocess, "run", lambda *a, **k: _Proc())

    # Changed-file resolution still finds the file (existence anchored to root).
    changed = get_changed_files_vs_main("origin/main")
    assert changed == [Path("src/pkg/widget.py")]

    # Test-file inference still finds the paired test (search anchored to root).
    inferred, err = infer_tests_file(Path("src/pkg/widget.py"))
    assert err is None
    assert inferred == Path("tests/pkg/test_widget.py")


def test_repo_root_raises_when_not_in_git_repo(monkeypatch):
    # _repo_root must raise a clear RuntimeError when git can't find a repo.
    class _Proc:
        returncode = 128
        stdout = ""
        stderr = "fatal: not a git repository"

    monkeypatch.setattr(mutate_mod.subprocess, "run", lambda *a, **k: _Proc())
    try:
        mutate_mod._repo_root()
    except RuntimeError as exc:
        assert "git" in str(exc).lower()
    else:
        raise AssertionError("_repo_root must raise RuntimeError on git failure")
