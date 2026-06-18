"""Tests for scripts/squash_merge_trailers.py (issue #863).

WHAT: Verifies that merge-time trailer normalization produces a squash-commit
body whose LAST paragraph is recoverable by ``git interpret-trailers --parse``,
and documents (via a failing-recovery assertion) the burial bug that GitHub's
naive squash concatenation causes.

WHY: Squash-merge concatenates branch commit bodies, burying interior commits'
trailer blocks as mid-body prose so only the last commit's trailers survive
``git interpret-trailers --parse``.  These tests pin the aggregation behaviour
that restores parseable provenance on ``main``.

The "documents the bug" test runs the REAL ``git interpret-trailers --parse``
against a GitHub-style squash body to prove the interior trailers are lost.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Make scripts/ importable.
_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from squash_merge_trailers import (  # noqa: E402
    aggregate_messages,
    build_trailer_block,
    compose_squash_body,
)

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None, reason="git binary required"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _interpret_trailers_parse(message: str) -> dict[str, list[str]]:
    """Run real ``git interpret-trailers --parse`` and return parsed trailers.

    Returns a dict mapping trailer key -> list of values (a key may repeat).
    """
    result = subprocess.run(
        ["git", "interpret-trailers", "--parse"],
        input=message,
        capture_output=True,
        text=True,
        check=True,
    )
    parsed: dict[str, list[str]] = {}
    for line in result.stdout.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        parsed.setdefault(key.strip(), []).append(value.strip())
    return parsed


def _commit_with_trailers(
    subject: str,
    *,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    model: str | None = None,
    version: str | None = None,
) -> str:
    """Build a single commit message with a trailing trailer block."""
    lines = [subject, "", "Some body prose explaining the change."]
    trailer: list[str] = [
        "",
        "Co-Authored-By: Claude MPM <https://github.com/bobmatnyc/claude-mpm>",
    ]
    if tokens_in is not None:
        trailer.append(f"X-AI-Tokens-In: {tokens_in}")
    if tokens_out is not None:
        trailer.append(f"X-AI-Tokens-Out: {tokens_out}")
    if model is not None:
        trailer.append(f"X-AI-Model: {model}")
    if version is not None:
        trailer.append(f"X-MPM-Version: {version}")
    return "\n".join(lines + trailer)


# ---------------------------------------------------------------------------
# 1. Document the burial bug with REAL git interpret-trailers
# ---------------------------------------------------------------------------


def test_squash_burial_documents_problem() -> None:
    """A GitHub-style squash body buries interior trailers (the #863 bug).

    GitHub squash concatenates each commit as ``* subject`` + body + trailer
    block.  Only the FINAL commit's trailer block is the trailing paragraph, so
    ``git interpret-trailers --parse`` cannot recover the interior commit's
    X-AI-Tokens-In.
    """
    commit_a = (
        "* feat: first change\n\n"
        "Body of first.\n\n"
        "Co-Authored-By: Claude MPM <https://github.com/bobmatnyc/claude-mpm>\n"
        "X-AI-Tokens-In: 1111\n"
        "X-AI-Tokens-Out: 222\n"
        "X-MPM-Version: 6.5.40\n"
    )
    commit_b = (
        "* feat: second change\n\n"
        "Body of second.\n\n"
        "Co-Authored-By: Claude MPM <https://github.com/bobmatnyc/claude-mpm>\n"
        "X-AI-Tokens-In: 3333\n"
        "X-AI-Tokens-Out: 444\n"
        "X-MPM-Version: 6.5.45\n"
    )
    # Naive squash: concatenate bodies (GitHub's default behaviour).
    squash_body = commit_a + "\n" + commit_b

    parsed = _interpret_trailers_parse(squash_body)

    # The interior commit's token value (1111) is buried mid-body and NOT
    # recovered as a trailer — this is exactly the bug #863 reports.
    tokens_in_values = parsed.get("X-AI-Tokens-In", [])
    assert "1111" not in tokens_in_values, (
        "Interior X-AI-Tokens-In should be buried (bug) but was recovered: "
        f"{tokens_in_values}"
    )
    # At most the LAST commit's value survives as a trailer.
    assert tokens_in_values in ([], ["3333"]), (
        f"Only the last commit's trailer should survive, got {tokens_in_values}"
    )


# ---------------------------------------------------------------------------
# 2. Normalized body is fully parseable
# ---------------------------------------------------------------------------


def test_normalized_body_is_parseable() -> None:
    """The composed squash body's LAST paragraph is interpret-trailers-parseable."""
    messages = [
        _commit_with_trailers(
            "feat: first",
            tokens_in=1000,
            tokens_out=200,
            model="claude-opus-4-8",
            version="6.5.40",
        ),
        _commit_with_trailers(
            "feat: second",
            tokens_in=500,
            tokens_out=100,
            model="claude-sonnet-4-6",
            version="6.5.45",
        ),
    ]
    body = compose_squash_body(summary="My PR\n\nSummary prose.", messages=messages)

    parsed = _interpret_trailers_parse(body)

    assert parsed.get("X-AI-Tokens-In") == ["1500"], parsed
    assert parsed.get("X-AI-Tokens-Out") == ["300"], parsed
    assert parsed.get("X-AI-Models") == ["claude-opus-4-8, claude-sonnet-4-6"], parsed
    assert parsed.get("X-MPM-Version") == ["6.5.45"], parsed
    assert parsed.get("Co-Authored-By") == [
        "Claude MPM <https://github.com/bobmatnyc/claude-mpm>"
    ], parsed


# ---------------------------------------------------------------------------
# 3. Aggregation: sum tokens, union models, latest version
# ---------------------------------------------------------------------------


def test_aggregation_sums_tokens_and_unions_models() -> None:
    """2+ commits -> summed tokens, unioned (dedup, stable) models, latest version."""
    messages = [
        _commit_with_trailers(
            "feat: a",
            tokens_in=100,
            tokens_out=10,
            model="claude-opus-4-8",
            version="6.5.40",
        ),
        _commit_with_trailers(
            "feat: b",
            tokens_in=200,
            tokens_out=20,
            model="claude-sonnet-4-6",
            version="6.5.42",
        ),
        _commit_with_trailers(
            "feat: c",
            tokens_in=300,
            tokens_out=30,
            model="claude-opus-4-8",  # duplicate model -> deduped
            version="6.5.45",
        ),
    ]
    agg = aggregate_messages(messages)

    assert agg.tokens_in == 600
    assert agg.tokens_out == 60
    assert agg.models == ["claude-opus-4-8", "claude-sonnet-4-6"]
    assert agg.version == "6.5.45"


def test_aggregation_unions_models_from_models_summary_line() -> None:
    """X-AI-Models summary lines contribute their bare model names to the union."""
    msg = (
        "feat: multi-model\n\n"
        "Body.\n\n"
        "Co-Authored-By: Claude MPM <https://github.com/bobmatnyc/claude-mpm>\n"
        "X-AI-Tokens-In: 50\n"
        "X-AI-Tokens-Out: 5\n"
        "X-AI-Models: claude-opus-4-8 (in=40,out=4); claude-haiku-4-5 (in=10,out=1)\n"
        "X-MPM-Version: 6.5.45\n"
    )
    agg = aggregate_messages([msg])
    assert agg.models == ["claude-opus-4-8", "claude-haiku-4-5"]


# ---------------------------------------------------------------------------
# 4. No token data -> omit X-AI-Tokens lines, keep version + coauthor
# ---------------------------------------------------------------------------


def test_no_token_data_omits_xai_lines() -> None:
    """Commits without token data -> no X-AI-Tokens-* lines, version still parseable."""
    messages = [
        _commit_with_trailers("docs: tweak", version="6.5.45"),
        _commit_with_trailers("chore: bump", version="6.5.45"),
    ]
    block = build_trailer_block(aggregate_messages(messages))
    joined = "\n".join(block)

    assert "X-AI-Tokens-In" not in joined
    assert "X-AI-Tokens-Out" not in joined

    body = compose_squash_body(summary="Docs PR", messages=messages)
    parsed = _interpret_trailers_parse(body)

    assert "X-AI-Tokens-In" not in parsed
    assert parsed.get("X-MPM-Version") == ["6.5.45"], parsed
    assert parsed.get("Co-Authored-By") == [
        "Claude MPM <https://github.com/bobmatnyc/claude-mpm>"
    ], parsed


def test_commits_without_any_trailers_yield_only_coauthor() -> None:
    """Robustness: commits with no trailers at all -> just the canonical coauthor."""
    messages = ["feat: bare commit\n\nNo trailers here.", "fix: another bare one"]
    block = build_trailer_block(aggregate_messages(messages))
    assert block == [
        "Co-Authored-By: Claude MPM <https://github.com/bobmatnyc/claude-mpm>"
    ]
    # Still parseable as a (single-trailer) block.
    body = compose_squash_body(summary="Bare PR", messages=messages)
    parsed = _interpret_trailers_parse(body)
    assert parsed.get("Co-Authored-By") == [
        "Claude MPM <https://github.com/bobmatnyc/claude-mpm>"
    ]


# ---------------------------------------------------------------------------
# 5. End-to-end against a real temp git repo (no global identity required)
# ---------------------------------------------------------------------------


def test_local_enumeration_against_temp_repo(tmp_path: Path) -> None:
    """git log enumeration + normalization round-trips through a real repo.

    Builds a temp repo (with its own identity so CI without a global git identity
    still passes — learned from tests/test_commit_cost_tracker.py), creates a
    base commit and two feature commits carrying trailers, then verifies the
    composed body recovers aggregated trailers via interpret-trailers --parse.
    """
    import squash_merge_trailers as smt

    def git(*args: str) -> str:
        r = subprocess.run(
            ["git", "-C", str(tmp_path), *args],
            capture_output=True,
            text=True,
            check=True,
        )
        return r.stdout

    git("init", "-q")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test User")
    git("config", "commit.gpgsign", "false")

    (tmp_path / "f.txt").write_text("base\n")
    git("add", "f.txt")
    git("commit", "-q", "-m", "chore: base")
    base_sha = git("rev-parse", "HEAD").strip()

    (tmp_path / "f.txt").write_text("one\n")
    git("add", "f.txt")
    git(
        "commit",
        "-q",
        "-m",
        _commit_with_trailers(
            "feat: one", tokens_in=700, tokens_out=70, model="m-a", version="6.5.44"
        ),
    )

    (tmp_path / "f.txt").write_text("two\n")
    git("add", "f.txt")
    git(
        "commit",
        "-q",
        "-m",
        _commit_with_trailers(
            "feat: two", tokens_in=300, tokens_out=30, model="m-b", version="6.5.45"
        ),
    )

    # Enumerate base..HEAD from inside the temp repo.
    cwd_before = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)
        summary, messages = smt.fetch_local_commit_messages(base_sha, "HEAD")
    finally:
        import os

        os.chdir(cwd_before)

    assert len(messages) == 2
    body = compose_squash_body(summary=summary, messages=messages)
    parsed = _interpret_trailers_parse(body)

    assert parsed.get("X-AI-Tokens-In") == ["1000"], parsed
    assert parsed.get("X-AI-Tokens-Out") == ["100"], parsed
    assert parsed.get("X-AI-Models") == ["m-a, m-b"], parsed
    assert parsed.get("X-MPM-Version") == ["6.5.45"], parsed
