#!/usr/bin/env python3
"""Normalize squash-merge commit trailers so X-AI-*/X-MPM-Version survive squash.

WHAT: Enumerates a PR's branch commits, parses each commit message for the
``X-AI-Tokens-In/Out``, ``X-AI-Model``/``X-AI-Models``, ``X-MPM-Version`` and
``Co-Authored-By: Claude MPM`` trailer families, AGGREGATES them (sum tokens,
union models, take the latest version), and composes a squash-commit body whose
LAST paragraph is a single git-trailer-parseable block.  Side-effect free: it
NEVER performs the merge — its output is meant to be piped into
``gh pr merge <pr> --squash --body-file <file>``.

WHY: GitHub squash-merge concatenates every branch commit's body into one
message.  Interior commits' trailer blocks become mid-body prose, so
``git interpret-trailers --parse`` only recovers the LAST commit's trailers and
all token/model/version provenance from earlier commits is lost on merge
(issue #863).  Emitting one aggregated trailer block as the final paragraph
restores parseable provenance on ``main``.

The trailer constants are imported from
``claude_mpm.hooks.commit_cost_tracker`` (the same source the post-commit hook
uses) so the parse rules can never drift between hook-time and merge-time.

References
----------
issue #863 : https://github.com/bobmatnyc/claude-mpm/issues/863

Usage
-----
    python scripts/squash_merge_trailers.py --pr 870 [--repo bobmatnyc/claude-mpm]
    python scripts/squash_merge_trailers.py --pr 870 --body-file /tmp/body.txt
    python scripts/squash_merge_trailers.py --pr 870 --print-trailers-only

    # Then merge (the script never merges itself):
    gh pr merge 870 --squash --body-file /tmp/body.txt
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# Make src/ importable when run directly from a checkout (mirrors how the test
# suite bootstraps imports) so the shared trailer constants resolve.
_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from claude_mpm.hooks.commit_cost_tracker import (
    _COAUTHORED_CANONICAL,
    _MPM_VERSION_TRAILER_KEY,
)

# ---------------------------------------------------------------------------
# Trailer-key parse patterns.
#
# These reuse the SAME key names the post-commit hook emits (X-AI-Tokens-In,
# X-AI-Tokens-Out, X-AI-Model, X-AI-Models, X-MPM-Version) so the merge-time
# parser can never diverge from the hook-time emitter.  We match per-key here
# (rather than reusing the hook's broad _XAI_TRAILER_RE strip-pattern) because
# at merge time we must EXTRACT values, not just detect/strip lines.
# ---------------------------------------------------------------------------
_TOKENS_IN_RE = re.compile(r"^X-AI-Tokens-In:\s*(\d+)\s*$", re.MULTILINE)
_TOKENS_OUT_RE = re.compile(r"^X-AI-Tokens-Out:\s*(\d+)\s*$", re.MULTILINE)
_MODEL_RE = re.compile(r"^X-AI-Model:\s*(.+?)\s*$", re.MULTILINE)
_MODELS_RE = re.compile(r"^X-AI-Models:\s*(.+?)\s*$", re.MULTILINE)
_VERSION_RE = re.compile(
    rf"^{re.escape(_MPM_VERSION_TRAILER_KEY)}:\s*(.+?)\s*$", re.MULTILINE
)


class AggregatedTrailers:
    """Accumulator for the trailer families summed/unioned across commits.

    WHAT: Holds running totals for ``X-AI-Tokens-In/Out``, a stable-order set of
    model names, and the latest ``X-MPM-Version`` seen.
    WHY: A simple typed container keeps the aggregation logic readable and makes
    the "omit empty families" rules explicit at compose time (issue #863).
    """

    __slots__ = ("_have_tokens", "models", "tokens_in", "tokens_out", "version")

    def __init__(self) -> None:
        self.tokens_in: int = 0
        self.tokens_out: int = 0
        self.models: list[str] = []
        self.version: str | None = None
        self._have_tokens: bool = False

    @property
    def has_token_data(self) -> bool:
        """True when at least one commit contributed an X-AI-Tokens-* trailer."""
        return self._have_tokens

    def add_model(self, name: str) -> None:
        """Union a model name into ``models`` preserving first-seen order."""
        name = name.strip()
        if name and name not in self.models:
            self.models.append(name)


def parse_commit_trailers(message: str, agg: AggregatedTrailers) -> None:
    """Parse one commit *message* and fold its trailers into *agg*.

    WHAT: Sums any ``X-AI-Tokens-In/Out`` values, unions ``X-AI-Model`` plus
    the model names embedded in any ``X-AI-Models`` summary line, and records the
    last-seen ``X-MPM-Version``.  Commits with no trailers contribute nothing.
    WHY: Squash buries these per-commit blocks; folding every commit's values
    into a single accumulator lets us re-emit one parseable block (issue #863).

    Args:
        message: Full raw commit message (subject + body) for one commit.
        agg: Accumulator mutated in place.
    """
    for m in _TOKENS_IN_RE.finditer(message):
        agg.tokens_in += int(m.group(1))
        agg._have_tokens = True
    for m in _TOKENS_OUT_RE.finditer(message):
        agg.tokens_out += int(m.group(1))
        agg._have_tokens = True

    for m in _MODEL_RE.finditer(message):
        agg.add_model(m.group(1))

    # X-AI-Models holds a summary like
    #   "claude-opus-4-8 (in=8954,out=572998); claude-sonnet-4-6 (in=100,out=50)"
    # Union just the bare model names (strip the "(...)" detail).
    for m in _MODELS_RE.finditer(message):
        for part in m.group(1).split(";"):
            name = part.split("(", 1)[0].strip()
            agg.add_model(name)

    # Latest version wins: every match overwrites, so the last commit's value
    # (which is also the highest in a linear branch history) is kept.
    for m in _VERSION_RE.finditer(message):
        agg.version = m.group(1).strip()


def build_trailer_block(agg: AggregatedTrailers) -> list[str]:
    """Return the aggregated trailer lines (no surrounding blank lines).

    WHAT: Always emits the canonical ``Co-Authored-By`` exactly once; emits
    ``X-AI-Tokens-In/Out`` only when token data exists; emits a single
    ``X-AI-Models`` line when any models were seen; emits ``X-MPM-Version`` when
    a version was found.  Every line is ``Key: value`` with no trailing prose so
    the whole block is recoverable by ``git interpret-trailers --parse``.
    WHY: An empty/partial family would either emit malformed lines or break the
    parser's trailing-block detection; omitting empties keeps the block clean
    (issue #863).

    Args:
        agg: Populated accumulator.

    Returns:
        Ordered list of trailer lines (the LAST paragraph of the squash body).
    """
    lines: list[str] = [_COAUTHORED_CANONICAL]
    if agg.has_token_data:
        lines.append(f"X-AI-Tokens-In: {agg.tokens_in}")
        lines.append(f"X-AI-Tokens-Out: {agg.tokens_out}")
    if agg.models:
        lines.append(f"X-AI-Models: {', '.join(agg.models)}")
    if agg.version:
        lines.append(f"{_MPM_VERSION_TRAILER_KEY}: {agg.version}")
    return lines


def aggregate_messages(messages: list[str]) -> AggregatedTrailers:
    """Fold every commit in *messages* into a single :class:`AggregatedTrailers`.

    Args:
        messages: One full commit message per branch commit.

    Returns:
        The populated accumulator.
    """
    agg = AggregatedTrailers()
    for msg in messages:
        parse_commit_trailers(msg, agg)
    return agg


def compose_squash_body(
    *,
    summary: str,
    messages: list[str],
) -> str:
    """Compose the full squash-commit body with the aggregated trailer block last.

    WHAT: Emits the human-readable *summary*, a blank line, then the aggregated
    trailer block as the final paragraph.
    WHY: ``git interpret-trailers --parse`` only reads the LAST paragraph as
    trailers; placing the aggregated block there is what makes provenance
    survive squash-merge (issue #863).

    Args:
        summary: Human-readable summary paragraph (PR title/body or subjects).
        messages: All branch commit messages to aggregate trailers from.

    Returns:
        The full squash commit body string (no trailing newline).
    """
    agg = aggregate_messages(messages)
    trailer_lines = build_trailer_block(agg)
    body = summary.rstrip()
    return f"{body}\n\n" + "\n".join(trailer_lines)


# ---------------------------------------------------------------------------
# Commit enumeration (gh primary, git fallback)
# ---------------------------------------------------------------------------


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run *cmd* capturing text output (no raise; caller inspects returncode)."""
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def fetch_pr_commit_messages(pr: int, repo: str | None) -> tuple[str, list[str]]:
    """Return (summary, [commit messages]) for *pr* via ``gh pr view``.

    WHAT: Reads the PR title/body for the summary and each commit's full
    message (headline + body) for trailer parsing.
    WHY: ``gh`` is the source of truth for what GitHub will squash; using it
    avoids needing the branch fetched locally (issue #863).

    Args:
        pr: PR number.
        repo: ``owner/name`` slug, or None to use the current repo.

    Returns:
        Tuple of summary paragraph and list of full commit messages.

    Raises:
        RuntimeError: when the ``gh`` call fails.
    """
    cmd = ["gh", "pr", "view", str(pr), "--json", "title,body,commits"]
    if repo:
        cmd += ["--repo", repo]
    result = _run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"gh pr view failed: {result.stderr.strip()}")
    data = json.loads(result.stdout)

    title = (data.get("title") or "").strip()
    body = (data.get("body") or "").strip()
    summary = f"{title}\n\n{body}".strip() if body else title

    messages: list[str] = []
    for c in data.get("commits", []):
        headline = (c.get("messageHeadline") or "").strip()
        cbody = (c.get("messageBody") or "").strip()
        full = f"{headline}\n\n{cbody}" if cbody else headline
        messages.append(full)
    return summary, messages


def fetch_local_commit_messages(base: str, head: str = "HEAD") -> tuple[str, list[str]]:
    """Return (summary, [commit messages]) for ``base..head`` via ``git log``.

    Used for smoke-testing and as a no-network fallback when ``gh`` is
    unavailable.  The summary is a bullet list of commit subjects.

    Args:
        base: Base ref (e.g. ``main``).
        head: Head ref (default ``HEAD``).

    Returns:
        Tuple of summary paragraph and list of full commit messages.

    Raises:
        RuntimeError: when the ``git log`` call fails.
    """
    # %B = raw body (subject + body); use a record separator git won't emit.
    # --reverse yields chronological (oldest-first) order so model-union order
    # and "latest version wins" match gh's chronological commit ordering.
    sep = "\x1e"
    result = _run(["git", "log", "--reverse", f"{base}..{head}", f"--format=%B{sep}"])
    if result.returncode != 0:
        raise RuntimeError(f"git log failed: {result.stderr.strip()}")
    messages = [chunk.strip() for chunk in result.stdout.split(sep) if chunk.strip()]
    subjects = [msg.splitlines()[0] for msg in messages if msg.splitlines()]
    summary = "\n".join(f"* {s}" for s in subjects)
    return summary, messages


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code.

    WHAT: Parses args, enumerates commits (gh by PR, or local git range),
    composes the normalized squash body, and emits it to stdout or a file.
    WHY: A thin CLI keeps the aggregation logic library-importable for tests
    while giving the merge workflow a pipe-able command (issue #863).
    """
    parser = argparse.ArgumentParser(
        description=(
            "Compose a squash-merge commit body with a single aggregated "
            "X-AI-*/X-MPM-Version trailer block as its last paragraph "
            "(issue #863). Side-effect free: never performs the merge."
        )
    )
    parser.add_argument("--pr", type=int, help="Pull request number (uses gh).")
    parser.add_argument("--base", default="main", help="Base ref (default: main).")
    parser.add_argument(
        "--head",
        default="HEAD",
        help="Head ref for --local mode (default: HEAD).",
    )
    parser.add_argument("--repo", help="owner/name slug (default: current repo).")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Enumerate commits from base..head via git instead of gh.",
    )
    parser.add_argument(
        "--body-file",
        type=Path,
        help="Write the composed body to this file instead of stdout.",
    )
    parser.add_argument(
        "--print-trailers-only",
        action="store_true",
        help="Print only the aggregated trailer block (for testing).",
    )
    args = parser.parse_args(argv)

    try:
        if args.local or args.pr is None:
            summary, messages = fetch_local_commit_messages(args.base, args.head)
        else:
            summary, messages = fetch_pr_commit_messages(args.pr, args.repo)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.print_trailers_only:
        agg = aggregate_messages(messages)
        output = "\n".join(build_trailer_block(agg))
    else:
        output = compose_squash_body(summary=summary, messages=messages)

    if args.body_file:
        args.body_file.write_text(output + "\n", encoding="utf-8")
        print(f"wrote {args.body_file}", file=sys.stderr)
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
