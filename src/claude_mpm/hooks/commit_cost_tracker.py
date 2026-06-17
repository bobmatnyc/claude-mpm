"""Commit cost tracker: embed token trailers in every git commit.

WHY: Every git commit made through Claude Code should automatically record the
AI token usage so teams can track activity per commit. Normalises the
Co-Authored-By trailer to the canonical Claude MPM form and appends structured
JSONL records to ~/.claude-mpm/commit-costs.jsonl for offline analysis.

DESIGN DECISIONS:
- run_as_git_hook() is invoked by the .git/hooks/post-commit shell script so
  it fires for ALL commits, including those made by Claude Code subagents.  The
  PostToolUse approach (detecting "git commit" Bash calls) only saw the parent
  session's Bash calls; subagent commits were invisible to it.
- Per-commit delta = cumulative snapshot at run time minus last-recorded
  baseline. The baseline is stored in .claude-mpm/state/commit-token-baseline.json
  inside the project directory (found by walking upward from cwd).
- LIVE TRANSCRIPT LOOKUP (fix for #601): At commit time, context-usage.json may
  be stale (it is only updated when a Stop event fires, but git commit runs
  mid-turn as a tool call before Stop).  get_token_delta() now parses the active
  session transcript directly (the most-recently-modified JSONL in
  ~/.claude/projects/{encoded_cwd}/) to obtain live cumulative token counts.
  Falls back to context-usage.json when no transcript is found.
- WORKTREE / SUBAGENT FALLBACK (fix for #696): When a subagent commit runs in a
  linked worktree, git's cwd is the worktree root (e.g.
  .claude/worktrees/agent-XXXX), NOT the main working tree. The parent session
  transcript lives under the main tree's encoded path. resolve_main_working_tree()
  finds the main tree via ``git worktree list --porcelain`` (or the parent of
  ``git rev-parse --git-common-dir`` as fallback), then get_token_delta() retries
  the lookup with that canonical cwd. Baseline reads and writes also use the
  canonical cwd so the delta is always consistent.
- Atomic file I/O (write-to-temp, then rename) prevents corruption when hooks
  run concurrently across worktrees.
- All subprocess calls use stdlib only; no new dependencies.
- If any step fails we log a warning and return without raising so the commit
  itself is never broken.
- The amend uses --no-verify to avoid triggering hooks recursively.
- Trailers emitted: X-AI-Tokens-In, X-AI-Tokens-Out, and conditionally
  X-AI-Model / X-AI-Models.  Cost and cache trailers have been removed.
- ZERO-SKIP (fix for #696): When the resolved delta is still 0/0 after all
  fallbacks, the X-AI-Tokens-In / X-AI-Tokens-Out trailers are omitted entirely
  rather than emitting useless zeros.
- VERSION STAMP (issue #859): X-MPM-Version records the installed claude-mpm
  version on EVERY commit the hook processes, including zero-delta commits.
  Unlike the token trailers it is NOT gated on a non-empty delta, so a commit
  with no token activity is still stamped.  The value comes from
  claude_mpm.__version__ (the VERSION-file single source of truth); if it cannot
  be resolved the trailer is omitted rather than crashing the hook.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from claude_mpm.hooks.transcript_usage import (
    find_latest_transcript,
    parse_transcript_usage,
)

# Module-level resolution of the installed claude-mpm version (issue #859).
# Resolved once at import time so the code path that reads it is explicit and
# directly patchable in tests (patch commit_cost_tracker._MPM_VERSION).  No
# circular-import risk: this module is a submodule of claude_mpm, so the package
# __init__ (which defines __version__) is already fully loaded by the time this
# import runs.  Any failure degrades to None → the trailer is omitted, never a
# crash.
try:
    from claude_mpm import __version__ as _MPM_VERSION
except Exception:  # pragma: no cover - defensive
    _MPM_VERSION = None

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Debug log helper — always writes to ~/.claude-mpm/logs/commit-cost-debug.log
# regardless of Python logging configuration so hook invocations are visible.
# ---------------------------------------------------------------------------
_DEBUG_LOG: Path = Path.home() / ".claude-mpm" / "logs" / "commit-cost-debug.log"
_ENABLE_DEBUG: bool = os.environ.get("CLAUDE_MPM_COMMIT_COST_DEBUG", "").lower() in (
    "1",
    "true",
    "yes",
)


def _debug(message: str) -> None:
    """Append *message* to the debug log file (always, unconditionally).

    This persists across hook invocations (which run in ephemeral subprocesses)
    so we can see whether the hook fires, what data it reads, and why it may
    produce zero-delta results.
    """
    try:
        _DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
        with _DEBUG_LOG.open("a") as fh:
            fh.write(f"[{ts}] {message}\n")
    except Exception:
        pass  # Never raise from a debug helper


# ---------------------------------------------------------------------------
# Canonical Co-Authored-By trailer
# ---------------------------------------------------------------------------
_COAUTHORED_CANONICAL = (
    "Co-Authored-By: Claude MPM <https://github.com/bobmatnyc/claude-mpm>"
)

# Patterns that should be normalised to the canonical form.
# Matches "Co-Authored-By: Claude ..." (where "..." is NOT "MPM").
_COAUTHORED_GENERIC_RE = re.compile(
    r"^Co-Authored-By:\s+Claude(?!\s+MPM)\b.*$",
    re.IGNORECASE | re.MULTILINE,
)

# Matches the canonical form so we can deduplicate.
_COAUTHORED_CANONICAL_RE = re.compile(
    r"^Co-Authored-By:\s+Claude MPM\s+<https://github\.com/bobmatnyc/claude-mpm>",
    re.IGNORECASE | re.MULTILINE,
)

# Regex to strip X-AI-* trailers that already exist so we never duplicate them.
# Matches lines like "X-AI-Tokens-In: 123" or "X-AI-Model: claude-opus-4-8".
# The pattern anchors at line start (MULTILINE) and matches any content on the
# line.  Using .*  rather than [^\n]+ to ensure blank-value lines are stripped.
#
# NOTE: This regex covers ONLY the X-AI-* trailers.  The other two trailer
# families this hook manages — X-MPM-Version and Co-Authored-By — are NOT
# stripped here; they are stripped line-by-line inside amend_commit_message()'s
# normalisation loop (see the re.match guards there).  All trailer-stripping for
# idempotent re-amend therefore lives in that loop, not in this regex.
_XAI_TRAILER_RE = re.compile(r"^X-AI-[A-Za-z-]+:.*$", re.MULTILINE)

# Git trailer key recording the installed claude-mpm version (issue #859).
# Stamped on EVERY commit the hook processes, decoupled from the token-delta
# gate.  Stripped on re-amend (alongside the X-AI-* / Co-Authored-By lines) so
# it is never duplicated.
_MPM_VERSION_TRAILER_KEY = "X-MPM-Version"

# Regex to extract the short SHA from a successful `git commit` output.
# Example: "[main abc1234] Add feature"
_SHA_RE = re.compile(r"\[.*?\s+([a-f0-9]{7,40})\]")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_main_working_tree(cwd: str) -> str:
    """Return the main git working tree path for *cwd*, handling linked worktrees.

    WHY: When a subagent commit runs inside a linked worktree (e.g.
    ``.claude/worktrees/agent-XXXX``), the parent session transcript lives under
    the MAIN working tree's encoded path in ``~/.claude/projects/``.  Using the
    worktree cwd as-is yields no transcript match (issue #696).

    WHAT: Short-circuits immediately when ``git rev-parse --git-dir`` equals
    ``--git-common-dir`` (cwd is already the main tree) to avoid spawning
    ``git worktree list`` on every non-worktree commit.  Otherwise runs
    ``git worktree list --porcelain`` and returns the ``worktree`` path from
    the FIRST entry.  Falls back to deriving the parent of
    ``git rev-parse --git-common-dir`` (which points to ``.git`` inside the
    main tree).  Relative paths from ``--git-common-dir`` are resolved relative
    to *cwd* (not the process cwd) so ``../.git`` resolves correctly.  If all
    git calls fail, returns *cwd* unchanged.

    TEST: In a temp repo with one linked worktree, call from the worktree dir
    and assert the returned path equals the main repo root, not the worktree.
    Call from the main repo dir itself and assert it is returned unchanged.
    Pass a mocked relative path (``../.git``) as ``--git-common-dir`` output and
    assert it resolves relative to *cwd*, not the process cwd.

    Args:
        cwd: Absolute path string for the commit's working directory.

    Returns:
        Absolute path string of the main working tree, or *cwd* on failure.
    """
    _debug(f"resolve_main_working_tree: cwd={cwd}")

    # --- Fast path: if git-dir == git-common-dir, cwd is already the main tree.
    # This avoids spawning git worktree list on every normal (non-worktree) commit.
    try:
        r_dir = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        r_common = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if r_dir.returncode == 0 and r_common.returncode == 0:
            git_dir_path = (Path(cwd) / r_dir.stdout.strip()).resolve()
            git_common_path = (Path(cwd) / r_common.stdout.strip()).resolve()
            if git_dir_path == git_common_path:
                # Already in the main working tree — no worktree lookup needed.
                _debug(
                    f"  resolve_main_working_tree: fast-path — "
                    f"git-dir == git-common-dir ({git_common_path}), returning cwd"
                )
                return cwd
    except Exception as exc_fast:
        _debug(f"  resolve_main_working_tree: fast-path check failed: {exc_fast}")

    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith("worktree "):
                    main_tree = line[len("worktree ") :]
                    _debug(f"  resolve_main_working_tree: first entry = {main_tree!r}")
                    return main_tree
    except Exception as exc:
        _debug(f"  resolve_main_working_tree: worktree list failed: {exc}")

    # Fallback: parent of git-common-dir (works even without porcelain support).
    # Resolve relative to *cwd* (not the process cwd) so a relative output like
    # ``../.git`` resolves correctly inside the worktree directory.
    try:
        result2 = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result2.returncode == 0:
            git_common = (Path(cwd) / result2.stdout.strip()).resolve()
            # git-common-dir is the shared .git dir; its parent is the main tree.
            main_tree = str(git_common.parent)
            _debug(f"  resolve_main_working_tree: from git-common-dir => {main_tree}")
            return main_tree
    except Exception as exc2:
        _debug(f"  resolve_main_working_tree: git-common-dir failed: {exc2}")

    _debug(f"  resolve_main_working_tree: fallback to cwd={cwd}")
    return cwd


def _read_live_cumulative(cwd: str) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
    """Read live cumulative token counts, preferring the active transcript.

    WHY: context-usage.json is only updated when a Stop event fires (end of
    agent turn), but ``git commit`` runs mid-turn as a tool call BEFORE Stop.
    At commit time the snapshot is therefore stale and any delta against the
    baseline reads 0 (issue #601).  Parsing the live transcript directly gives
    accurate counts regardless of whether Stop has fired yet.

    WHAT: Tries to locate the most recently modified JSONL in
    ``~/.claude/projects/{encoded_cwd}/`` and parse it with
    ``parse_transcript_usage()``.  If that succeeds, maps the transcript totals
    to the same keys used by context-usage.json.  Falls back to reading
    context-usage.json when no transcript is found or parsing yields nothing.

    TEST: Seed a stale context-usage.json with zeros, create a transcript JSONL
    fixture with known token counts, call ``_read_live_cumulative(cwd)``, and
    assert the returned counts match the transcript (not the stale file).

    Args:
        cwd: Repository working directory (absolute path string).

    Returns:
        Tuple of (cumulative_totals_dict, per_model_dict) where
        cumulative_totals_dict has keys: input_tokens, output_tokens,
        cache_read_tokens, cache_write_tokens (all non-negative integers).
    """
    # --- Attempt 1: parse the live session transcript ---
    latest = find_latest_transcript(cwd)
    if latest is not None:
        _debug(f"_read_live_cumulative: trying transcript {latest.name}")
        parsed = parse_transcript_usage(latest)
        if parsed is not None:
            cumulative = {
                "input_tokens": parsed["input_tokens"],
                "output_tokens": parsed["output_tokens"],
                # transcript uses cache_creation_input_tokens / cache_read_input_tokens
                "cache_read_tokens": parsed["cache_read_input_tokens"],
                "cache_write_tokens": parsed["cache_creation_input_tokens"],
            }
            cumulative_models: dict[str, dict[str, int]] = (
                parsed.get("models", {}) or {}
            )
            _debug(
                f"_read_live_cumulative: from transcript — "
                f"in={cumulative['input_tokens']} out={cumulative['output_tokens']} "
                f"models={list(cumulative_models.keys())}"
            )
            return cumulative, cumulative_models
        _debug(
            "_read_live_cumulative: transcript parse returned None; falling back to snapshot"
        )
    else:
        _debug("_read_live_cumulative: no transcript found; falling back to snapshot")

    # --- Fallback: read context-usage.json snapshot ---
    project_root = Path(cwd).resolve()
    usage_file = project_root / ".claude-mpm" / "state" / "context-usage.json"
    current = _read_json_safe(usage_file)
    _debug(f"_read_live_cumulative: snapshot raw keys={list(current.keys())}")

    # Guard against stale test data.
    session_id = current.get("session_id", "")
    if session_id == "summary-test":
        _debug(
            f"_read_live_cumulative: WARNING stale sentinel session_id={session_id!r} — treating as empty"
        )
        current = {}

    cumulative_fallback = {
        "input_tokens": int(current.get("cumulative_input_tokens", 0)),
        "output_tokens": int(current.get("cumulative_output_tokens", 0)),
        "cache_read_tokens": int(current.get("cache_read_tokens", 0)),
        "cache_write_tokens": int(current.get("cache_creation_tokens", 0)),
    }
    fallback_models: dict[str, dict[str, int]] = current.get("models", {}) or {}
    return cumulative_fallback, fallback_models


def get_token_delta(cwd: str) -> dict[str, Any]:
    """Return per-commit token delta and update the running baseline.

    Reads live cumulative totals (from the active transcript or context-usage.json
    as a fallback), computes the difference against the last-recorded baseline,
    then writes the new baseline so subsequent commits get correct incremental
    numbers.

    WHY: Every commit needs the incremental token usage since the previous commit
    so that X-AI-* trailers reflect only the work done for that commit.  The
    live transcript lookup (see _read_live_cumulative) fixes issue #601 where
    stale context-usage.json caused all-zero deltas.  The main-working-tree
    fallback (see resolve_main_working_tree) fixes issue #696 where subagent
    commits in linked worktrees always produced zero deltas because the transcript
    was stored under the main tree's path, not the worktree path.

    WHAT: Resolves the canonical project cwd ONCE via resolve_main_working_tree(),
    then uses that canonical path consistently for transcript lookup, baseline
    read, and baseline write — preventing any baseline/transcript cwd mismatch.
    Reads live cumulative + baseline files, returns delta dict with integer token
    fields plus a per-model ``models`` dict for the same delta window.  The
    per-model delta is computed independently for each model: if a model appears
    in the snapshot but not the baseline it gets its full snapshot value; if it
    only appears in the baseline it contributes zero (clamped).

    TEST: Seed a stale context-usage.json with zeros, provide a transcript JSONL
    fixture with known token counts, call get_token_delta(), and assert the delta
    matches the transcript counts (not the stale snapshot).

    Args:
        cwd: Working directory of the repository (used to locate .claude-mpm/).

    Returns:
        Dict with keys: input_tokens, output_tokens, cache_read_tokens,
        cache_write_tokens (all non-negative integers) plus ``models`` — a dict
        mapping model name to per-model token delta (same four keys).
    """
    # Resolve the canonical project cwd ONCE.  For a linked-worktree subagent
    # commit, this maps the worktree path back to the main working tree so the
    # transcript lookup, baseline read, AND baseline write all use the same path.
    canonical_cwd = resolve_main_working_tree(cwd)
    _debug(f"get_token_delta: cwd={cwd} canonical_cwd={canonical_cwd}")

    project_root = Path(canonical_cwd).resolve()
    baseline_file = (
        project_root / ".claude-mpm" / "state" / "commit-token-baseline.json"
    )

    _debug(f"  baseline_file={baseline_file} exists={baseline_file.exists()}")

    # Read live cumulative totals using the CANONICAL cwd (transcript preferred,
    # snapshot as fallback).
    cumulative, cumulative_models = _read_live_cumulative(canonical_cwd)
    _debug(f"  cumulative={cumulative}")
    _debug(f"  cumulative_models keys={list(cumulative_models.keys())}")

    # Read previous baseline (zeros if this is the first commit).
    prev = _read_json_safe(baseline_file)
    baseline = {
        "input_tokens": int(prev.get("input_tokens", 0)),
        "output_tokens": int(prev.get("output_tokens", 0)),
        "cache_read_tokens": int(prev.get("cache_read_tokens", 0)),
        "cache_write_tokens": int(prev.get("cache_write_tokens", 0)),
    }
    baseline_models: dict[str, dict[str, int]] = prev.get("models", {}) or {}
    _debug(f"  baseline={baseline}")

    # Aggregate delta = current minus previous (floor at zero).
    delta: dict[str, Any] = {
        key: max(0, cumulative[key] - baseline[key]) for key in cumulative
    }

    # Per-model delta: for each model in the snapshot compute the increment.
    model_delta: dict[str, dict[str, int]] = {}
    token_keys = (
        "input_tokens",
        "output_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
    )
    for model, snap_counts in cumulative_models.items():
        prev_counts = baseline_models.get(model, {})
        model_delta[model] = {
            k: max(0, int(snap_counts.get(k, 0)) - int(prev_counts.get(k, 0)))
            for k in token_keys
        }
    delta["models"] = model_delta
    _debug(f"  delta={delta}")

    # Persist new baseline atomically — include per-model snapshot.
    new_baseline: dict[str, Any] = {**cumulative, "models": cumulative_models}
    _write_json_atomic(baseline_file, new_baseline)

    return delta


def _primary_model(model_delta: dict[str, dict[str, int]]) -> str | None:
    """Return the model name with the most output tokens in the delta window.

    WHY: When a session mixes models (e.g. main-loop opus + subagent sonnet),
    the primary model is the one that produced the most output tokens in this
    commit's delta window.

    WHAT: Iterates model_delta and returns the key whose ``output_tokens`` value
    is highest.  Returns None when model_delta is empty.

    TEST: Pass {\"a\": {\"output_tokens\": 10}, \"b\": {\"output_tokens\": 50}} and assert
    \"b\" is returned.

    :spec: N/A
    """
    # Only consider models that actually produced tokens in this delta window.
    active = {
        m: c
        for m, c in model_delta.items()
        if c.get("input_tokens", 0) > 0 or c.get("output_tokens", 0) > 0
    }
    if not active:
        return None
    return max(active, key=lambda m: active[m].get("output_tokens", 0))


def _format_models_trailer(model_delta: dict[str, dict[str, int]]) -> str | None:
    """Format the X-AI-Models trailer value for a multi-model delta window.

    WHY: Provides a compact, single-line, git-trailer-safe summary of each
    model's contribution to the delta window so commit messages are self-
    documenting.

    WHAT: Returns a semicolon-separated string such as
    ``claude-opus-4-8 (in=8954,out=572998); claude-sonnet-4-6 (in=100,out=50)``
    sorted by descending output tokens, including only models with non-zero
    tokens.  Returns None when fewer than two such models exist (caller emits
    only X-AI-Model in that case).

    TEST: Pass a two-model dict and assert the result contains both model names,
    the correct token counts in ``in=...,out=...`` format, separated by ``; ``.

    :spec: N/A
    """
    # Only include models that actually produced tokens in this delta window.
    active = {
        m: c
        for m, c in model_delta.items()
        if c.get("input_tokens", 0) > 0 or c.get("output_tokens", 0) > 0
    }
    if len(active) < 2:
        return None
    parts = []
    for model in sorted(
        active, key=lambda m: active[m].get("output_tokens", 0), reverse=True
    ):
        counts = active[model]
        parts.append(
            f"{model} (in={counts.get('input_tokens', 0)},"
            f"out={counts.get('output_tokens', 0)})"
        )
    return "; ".join(parts)


def _get_mpm_version() -> str | None:
    """Return the installed claude-mpm version string, or None on failure.

    WHY: Every commit the hook processes should record which claude-mpm version
    produced it (issue #859) so commits are self-documenting for provenance and
    so behavior changes can be correlated with MPM releases.  Resolution must
    never crash the hook: on any failure we return None and the caller omits the
    trailer rather than emitting a malformed line.

    WHAT: Reads the module-level ``_MPM_VERSION`` (resolved once at import time
    from ``claude_mpm.__version__`` — the VERSION-file single source of truth,
    the same source ``cli/startup._get_package_version`` uses).  Returns the
    stripped version string, or None when the value is unset or empty.

    TEST: Patch ``_MPM_VERSION`` to a known value and assert the trailer equals
    it; patch it to None/empty and assert no X-MPM-Version line appears and the
    hook does not raise.

    :spec: N/A
    """
    version = (_MPM_VERSION or "").strip()
    return version or None


def amend_commit_message(commit_sha: str, delta: dict[str, Any], cwd: str) -> None:
    """Amend the latest commit to add token trailers and normalise Co-Authored-By.

    Steps:
    1. Retrieve current commit message via ``git log``.
    2. Strip any generic Co-Authored-By: Claude (not MPM) lines.
    3. Ensure exactly one canonical Co-Authored-By: Claude MPM trailer.
    4. Append X-AI-Tokens-In, X-AI-Tokens-Out, and model trailers (token trailers
       gated on a non-empty delta), then ALWAYS append X-MPM-Version (issue #859).
    5. Amend commit with ``git commit --amend --no-edit -m <msg> --no-verify``.

    WHY: Decorates every commit with token usage so teams can audit AI cost per
    commit without separate tooling, and records the installed claude-mpm
    version on every commit (including zero-delta commits) for provenance.

    WHAT: Retrieves the commit message, strips old X-AI-*, X-MPM-Version, and
    Co-Authored-By trailers, then appends fresh trailers from *delta* plus the
    resolved claude-mpm version.

    TEST: Mock subprocess.run to return a known commit message, call
    amend_commit_message(), assert the amended message contains X-AI-Tokens-In
    and X-AI-Tokens-Out with the delta values.

    Args:
        commit_sha: Short or full SHA of the commit to amend.
        delta: Token delta dict from get_token_delta() — includes ``models`` key.
        cwd: Working directory for git commands.
    """
    _debug(f"amend_commit_message: sha={commit_sha} delta={delta} cwd={cwd}")
    try:
        # 1. Retrieve current commit message.
        result = subprocess.run(
            ["git", "log", "-1", "--format=%B", commit_sha],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            logger.warning(
                "commit_cost_tracker: could not retrieve commit message for %s: %s",
                commit_sha,
                result.stderr.strip(),
            )
            return

        original_msg = result.stdout

        # Strip ALL X-AI-* and Co-Authored-By trailer lines from the current
        # message using a line-by-line pass so that no existing trailer block
        # is ever left in place.  This is the primary idempotency guard: it
        # ensures that even if the hook fires multiple times on the same commit
        # (due to the recursion-guard env var not propagating through the shell
        # layer on some systems), the final message contains exactly ONE block.
        raw_lines = original_msg.splitlines()
        body_lines: list[str] = []
        for line in raw_lines:
            stripped_line = line.rstrip()
            # Skip any line that is an X-AI-* trailer.
            if re.match(r"^X-AI-[A-Za-z-]+:", stripped_line):
                continue
            # Skip any existing X-MPM-Version trailer (idempotency for re-amend).
            if re.match(rf"^{re.escape(_MPM_VERSION_TRAILER_KEY)}:", stripped_line):
                continue
            # Skip any Co-Authored-By: Claude ... trailer (canonical or generic).
            if re.match(r"^Co-Authored-By:\s+Claude\b", stripped_line, re.IGNORECASE):
                continue
            body_lines.append(stripped_line)

        # Remove trailing blank lines from what remains.
        while body_lines and body_lines[-1] == "":
            body_lines.pop()

        # Remove leading blank lines.
        while body_lines and body_lines[0] == "":
            body_lines.pop(0)

        normalised_lines = body_lines

        # 4. Build trailers block.
        # Determine primary model and multi-model summary.
        model_delta: dict[str, dict[str, int]] = delta.get("models") or {}
        primary_model = _primary_model(model_delta)
        models_trailer = _format_models_trailer(model_delta)

        tokens_in = delta.get("input_tokens", 0)
        tokens_out = delta.get("output_tokens", 0)
        has_token_data = tokens_in > 0 or tokens_out > 0

        trailers: list[str] = [
            "",  # blank line before trailers
            _COAUTHORED_CANONICAL,
        ]

        if has_token_data:
            trailers.append(f"X-AI-Tokens-In: {tokens_in}")
            trailers.append(f"X-AI-Tokens-Out: {tokens_out}")
        else:
            _debug(
                "amend_commit_message: skipping X-AI-Tokens-In/Out trailers "
                "— no token data resolved (delta is 0/0 after all fallbacks)"
            )

        if primary_model:
            trailers.append(f"X-AI-Model: {primary_model}")
        if models_trailer:
            trailers.append(f"X-AI-Models: {models_trailer}")

        # X-MPM-Version (issue #859): stamped on EVERY commit, decoupled from the
        # token-delta gate above — present even when the X-AI-* trailers are
        # omitted (zero-delta commit).  Omitted only when the version cannot be
        # resolved, so the trailer is never malformed.
        mpm_version = _get_mpm_version()
        if mpm_version:
            trailers.append(f"{_MPM_VERSION_TRAILER_KEY}: {mpm_version}")
        else:
            _debug(
                "amend_commit_message: skipping X-MPM-Version trailer "
                "— claude-mpm version could not be resolved"
            )

        new_msg = "\n".join(normalised_lines + trailers)

        # 5. Amend commit.
        # Pass _RECURSION_GUARD_ENV so the post-commit hook that fires after
        # the amend sees the sentinel and exits immediately without re-entering.
        # Retry up to 3 times with a brief delay because git may still hold a
        # ref lock immediately after the post-commit hook fires (the original
        # commit write and the hook run slightly overlap on some systems).
        amend_env = os.environ.copy()
        amend_env[_RECURSION_GUARD_ENV] = "1"
        amend_result = None
        for _attempt in range(3):
            amend_result = subprocess.run(
                [
                    "git",
                    "commit",
                    "--amend",
                    "--no-edit",
                    "--allow-empty",
                    "-m",
                    new_msg,
                    "--no-verify",
                ],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
                env=amend_env,
            )
            if amend_result.returncode == 0:
                break
            # "cannot lock ref" or "index.lock" means git is still busy
            if "lock" in amend_result.stderr.lower():
                _debug(f"  amend attempt {_attempt + 1} hit lock, retrying after 0.3s")
                time.sleep(0.3)
            else:
                break  # Non-lock error; no point retrying

        if amend_result is None or amend_result.returncode != 0:
            stderr = amend_result.stderr.strip() if amend_result else "no result"
            _debug(f"  amend FAILED: {stderr}")
            logger.warning(
                "commit_cost_tracker: amend failed for %s: %s",
                commit_sha,
                stderr,
            )
        else:
            _debug(f"  amend OK for {commit_sha}")
    except Exception as exc:
        _debug(f"  amend_commit_message exception: {exc}")
        logger.warning("commit_cost_tracker: amend_commit_message error: %s", exc)


def write_cost_log(
    commit_sha: str,
    delta: dict[str, int],
    cwd: str,
    output: str,
) -> None:
    """Append a JSONL record to ~/.claude-mpm/commit-costs.jsonl.

    WHY: Provides a machine-readable per-commit token log for offline analysis
    without needing to parse git commit messages.

    WHAT: Appends one JSON line with timestamp, SHA, cwd, token counts, and
    model info to ~/.claude-mpm/commit-costs.jsonl.

    TEST: Call write_cost_log(), assert the file exists and the parsed record
    contains the correct commit_sha, tokens_in, and tokens_out values.

    Args:
        commit_sha: Short SHA of the commit.
        delta: Token delta dict from get_token_delta().
        cwd: Working directory of the repository.
        output: Raw stdout from the git commit command.
    """
    _debug(f"write_cost_log: sha={commit_sha}")
    try:
        log_path = Path.home() / ".claude-mpm" / "commit-costs.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        record: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "commit_sha": commit_sha,
            "cwd": cwd,
            "tokens_in": delta.get("input_tokens", 0),
            "tokens_out": delta.get("output_tokens", 0),
            "git_output": output.strip(),
        }

        # Append atomically: write to temp in same dir, then rename.
        _append_jsonl_atomic(log_path, record)

    except Exception as exc:
        logger.warning("commit_cost_tracker: write_cost_log error: %s", exc)


def extract_commit_sha(git_output: str) -> str | None:
    """Extract the short SHA from a successful git commit stdout.

    Example input: "[main abc1234] Add feature\\n 1 file changed, 1 insertion(+)"
    Returns: "abc1234"

    Args:
        git_output: stdout from a git commit command.

    Returns:
        Short SHA string or None if not found.
    """
    match = _SHA_RE.search(git_output)
    return match.group(1) if match else None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_json_safe(path: Path) -> dict[str, Any]:
    """Read a JSON file, returning an empty dict on any failure."""
    try:
        if path.exists():
            with path.open() as fh:
                return json.load(fh)
    except Exception as exc:
        logger.debug("commit_cost_tracker: could not read %s: %s", path, exc)
    return {}


def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    """Write *data* to *path* atomically (temp-then-rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".baseline_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(data, fh, indent=2)
        Path(tmp).replace(path)
    except Exception as exc:
        logger.warning(
            "commit_cost_tracker: could not write baseline %s: %s", path, exc
        )
        try:
            Path(tmp).unlink(missing_ok=True)
        except Exception:
            pass


def _append_jsonl_atomic(path: Path, record: dict[str, Any]) -> None:
    """Append a JSONL record to *path* atomically.

    Reads the existing file (if present), appends the new line, and writes back
    via temp-then-rename to avoid partial writes.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # Read existing content.
    existing = ""
    if path.exists():
        try:
            existing = path.read_text()
        except Exception:
            existing = ""

    new_line = json.dumps(record, separators=(",", ":"))
    combined = (
        (existing.rstrip("\n") + "\n" + new_line + "\n")
        if existing.strip()
        else (new_line + "\n")
    )

    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".commitlog_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(combined)
        Path(tmp).replace(path)
    except Exception as exc:
        logger.warning("commit_cost_tracker: could not append to %s: %s", path, exc)
        try:
            Path(tmp).unlink(missing_ok=True)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Git post-commit hook entry point
# ---------------------------------------------------------------------------


def _find_project_root(start: Path) -> Path | None:
    """Walk upward from *start* until we find a directory containing .claude-mpm/.

    Returns the project root Path, or None if not found before the filesystem
    root.
    """
    current = start.resolve()
    while True:
        if (current / ".claude-mpm").is_dir():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


# Environment variable used to break recursion.  git post-commit hooks fire
# even after `git commit --amend --no-verify`, so we must guard against
# the amend triggering this hook a second time.
_RECURSION_GUARD_ENV = "CLAUDE_MPM_COMMIT_COST_RUNNING"


def run_as_git_hook() -> None:
    """Entry point for the git post-commit hook.

    Called by .git/hooks/post-commit after every commit (including subagent
    commits that are invisible to the parent session's PostToolUse hook).

    Steps:
    1. Locate the project root by walking upward from cwd.
    2. Read context-usage.json and compute the per-commit token delta.
    3. Get the HEAD SHA and commit message.
    4. Strip generic Co-Authored-By: Claude lines, ensure exactly one canonical
       Co-Authored-By: Claude MPM trailer.
    5. Append X-AI-* trailers.
    6. Amend HEAD with the enriched message.
    7. Append a JSONL record to ~/.claude-mpm/commit-costs.jsonl.

    All failures are logged to the debug log and suppressed so the commit is
    never broken by hook errors.

    RECURSION: git always fires post-commit after every commit/amend, even
    with --no-verify.  We use an environment variable sentinel so the amend
    we perform does not re-enter this function.
    """
    # Guard: skip if we are already running (i.e. this invocation is triggered
    # by our own amend inside step 6).
    if os.environ.get(_RECURSION_GUARD_ENV):
        _debug("run_as_git_hook: skipping (recursion guard set)")
        return

    _debug("run_as_git_hook: invoked")

    try:
        cwd = Path.cwd()
        _debug(f"  cwd={cwd}")

        # 1. Find project root.
        project_root = _find_project_root(cwd)
        _debug(f"  project_root={project_root}")
        if project_root is None:
            # No .claude-mpm/ found (e.g. repo never ran mpm-init). Resolve the
            # main working tree so baseline/transcript lookups use the canonical
            # main-tree path rather than a linked-worktree path.
            working_dir = resolve_main_working_tree(str(cwd))
            _debug(
                f"  no .claude-mpm dir found; resolved main working tree => {working_dir}"
            )
        else:
            working_dir = str(project_root)

        # 2. Compute token delta.
        delta = get_token_delta(working_dir)
        _debug(f"  delta={delta}")

        # 3. Get HEAD SHA.
        sha_result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if sha_result.returncode != 0:
            _debug(f"  git rev-parse failed: {sha_result.stderr.strip()}")
            return
        commit_sha = sha_result.stdout.strip()
        _debug(f"  commit_sha={commit_sha!r}")

        # 4-6. Amend the commit message to include trailers.
        amend_commit_message(commit_sha, delta, working_dir)

        # 7. Write cost log.
        # Re-read the amended SHA (amend rewrites the commit hash).
        amended_sha_result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        final_sha = (
            amended_sha_result.stdout.strip()
            if amended_sha_result.returncode == 0
            else commit_sha
        )
        write_cost_log(final_sha, delta, working_dir, f"[hook] {final_sha}")
        _debug(f"  run_as_git_hook: complete for sha={final_sha}")

    except Exception as exc:
        _debug(f"  run_as_git_hook EXCEPTION: {exc}")
        logger.warning("commit_cost_tracker.run_as_git_hook error: %s", exc)
