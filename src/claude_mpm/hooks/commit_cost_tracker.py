"""Commit cost tracker: embed token cost trailers in every git commit.

WHY: Every git commit made through Claude Code should automatically record the
AI token cost so teams can track spend per commit. Normalises the Co-Authored-By
trailer to the canonical Claude MPM form and appends structured JSONL records
to ~/.claude-mpm/commit-costs.jsonl for offline analysis.

DESIGN DECISIONS:
- run_as_git_hook() is invoked by the .git/hooks/post-commit shell script so
  it fires for ALL commits, including those made by Claude Code subagents.  The
  PostToolUse approach (detecting "git commit" Bash calls) only saw the parent
  session's Bash calls; subagent commits were invisible to it.
- Per-commit delta = cumulative snapshot at run time minus last-recorded
  baseline. The baseline is stored in .claude-mpm/state/commit-token-baseline.json
  inside the project directory (found by walking upward from cwd).
- Atomic file I/O (write-to-temp, then rename) prevents corruption when hooks
  run concurrently across worktrees.
- All subprocess calls use stdlib only; no new dependencies.
- If any step fails we log a warning and return without raising so the commit
  itself is never broken.
- The amend uses --no-verify to avoid triggering hooks recursively.
- Configurable pricing via env vars CLAUDE_MPM_PRICE_INPUT,
  CLAUDE_MPM_PRICE_OUTPUT, CLAUDE_MPM_PRICE_CACHE_READ,
  CLAUDE_MPM_PRICE_CACHE_WRITE (all in $/MTok).
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
# Pricing constants ($/MTok = dollars per million tokens)
# ---------------------------------------------------------------------------
_DEFAULT_PRICE_INPUT: float = 3.00
_DEFAULT_PRICE_OUTPUT: float = 15.00
_DEFAULT_PRICE_CACHE_READ: float = 0.30
_DEFAULT_PRICE_CACHE_WRITE: float = 3.75

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
# Matches lines like "X-AI-Tokens-In: 123" or "X-AI-Est-Cost-USD: 0.000012".
# The pattern anchors at line start (MULTILINE) and matches any content on the
# line.  Using .*  rather than [^\n]+ to ensure blank-value lines are stripped.
_XAI_TRAILER_RE = re.compile(r"^X-AI-[A-Za-z-]+:.*$", re.MULTILINE)

# Regex to extract the short SHA from a successful `git commit` output.
# Example: "[main abc1234] Add feature"
_SHA_RE = re.compile(r"\[.*?\s+([a-f0-9]{7,40})\]")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_token_delta(cwd: str) -> dict[str, Any]:
    """Return per-commit token delta and update the running baseline.

    Reads the current cumulative totals from context-usage.json, computes the
    difference against the last-recorded baseline, then writes the new baseline
    so subsequent commits get the correct incremental numbers.

    WHY: Every commit needs the incremental token cost since the previous commit
    so that X-AI-* trailers reflect only the work done for that commit.

    WHAT: Reads snapshot + baseline files, returns delta dict with integer token
    fields plus a per-model ``models`` dict for the same delta window.  The
    per-model delta is computed independently for each model: if a model appears
    in the snapshot but not the baseline it gets its full snapshot value; if it
    only appears in the baseline it contributes zero (clamped).

    TEST: Seed snapshot with two models, seed baseline with one of those models,
    call get_token_delta(), assert the model absent from baseline has its full
    count, the shared model has the incremental delta, and the other model has
    zero (clamped).

    Args:
        cwd: Working directory of the repository (used to locate .claude-mpm/).

    Returns:
        Dict with keys: input_tokens, output_tokens, cache_read_tokens,
        cache_write_tokens (all non-negative integers) plus ``models`` — a dict
        mapping model name to per-model token delta (same four keys).
    """
    project_root = Path(cwd).resolve()
    usage_file = project_root / ".claude-mpm" / "state" / "context-usage.json"
    baseline_file = (
        project_root / ".claude-mpm" / "state" / "commit-token-baseline.json"
    )

    _debug(f"get_token_delta: cwd={cwd}")
    _debug(f"  usage_file={usage_file} exists={usage_file.exists()}")
    _debug(f"  baseline_file={baseline_file} exists={baseline_file.exists()}")

    # Read current cumulative totals (graceful degradation if missing).
    current = _read_json_safe(usage_file)
    _debug(f"  context-usage.json raw: {json.dumps(current)}")

    # Guard against stale test data: if session_id looks like a test artifact
    # (e.g. "summary-test") treat the file as empty so we get zero-delta rather
    # than fraudulent large deltas.  We do NOT apply a numeric threshold here
    # because heavy caching sessions can legitimately accumulate millions of
    # cache-read tokens; only the sentinel session_id signals stale test state.
    session_id = current.get("session_id", "")
    if session_id == "summary-test":
        raw_input = int(current.get("cumulative_input_tokens", 0))
        raw_output = int(current.get("cumulative_output_tokens", 0))
        _debug(
            f"  WARNING: context-usage.json appears stale (session_id={session_id!r}, "
            f"input={raw_input}, output={raw_output}) — treating as empty"
        )
        current = {}

    cumulative = {
        "input_tokens": int(current.get("cumulative_input_tokens", 0)),
        "output_tokens": int(current.get("cumulative_output_tokens", 0)),
        "cache_read_tokens": int(current.get("cache_read_tokens", 0)),
        "cache_write_tokens": int(current.get("cache_creation_tokens", 0)),
    }
    # Per-model cumulative snapshot (may be empty for old state files).
    cumulative_models: dict[str, dict[str, int]] = current.get("models", {}) or {}
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


def compute_cost(delta: dict[str, int]) -> float:
    """Estimate USD cost from a token delta dict.

    Uses configurable per-MTok prices loaded from environment variables with
    sensible Anthropic defaults.

    Args:
        delta: Dict returned by get_token_delta().

    Returns:
        Estimated cost in USD (may be 0.0 if all counts are zero).
    """
    price_input = float(os.environ.get("CLAUDE_MPM_PRICE_INPUT", _DEFAULT_PRICE_INPUT))
    price_output = float(
        os.environ.get("CLAUDE_MPM_PRICE_OUTPUT", _DEFAULT_PRICE_OUTPUT)
    )
    price_cache_read = float(
        os.environ.get("CLAUDE_MPM_PRICE_CACHE_READ", _DEFAULT_PRICE_CACHE_READ)
    )
    price_cache_write = float(
        os.environ.get("CLAUDE_MPM_PRICE_CACHE_WRITE", _DEFAULT_PRICE_CACHE_WRITE)
    )

    cost = (
        delta.get("input_tokens", 0) / 1_000_000 * price_input
        + delta.get("output_tokens", 0) / 1_000_000 * price_output
        + delta.get("cache_read_tokens", 0) / 1_000_000 * price_cache_read
        + delta.get("cache_write_tokens", 0) / 1_000_000 * price_cache_write
    )
    return round(cost, 6)


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


def amend_commit_message(
    commit_sha: str, delta: dict[str, Any], cost: float, cwd: str
) -> None:
    """Amend the latest commit to add token trailers and normalise Co-Authored-By.

    Steps:
    1. Retrieve current commit message via ``git log``.
    2. Strip any generic Co-Authored-By: Claude (not MPM) lines.
    3. Ensure exactly one canonical Co-Authored-By: Claude MPM trailer.
    4. Append X-AI-* trailers with token counts, cost, and model info.
    5. Amend commit with ``git commit --amend --no-edit -m <msg> --no-verify``.

    Args:
        commit_sha: Short or full SHA of the commit to amend.
        delta: Token delta dict from get_token_delta() — includes ``models`` key.
        cost: Estimated cost from compute_cost().
        cwd: Working directory for git commands.
    """
    _debug(
        f"amend_commit_message: sha={commit_sha} delta={delta} cost={cost:.6f} cwd={cwd}"
    )
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
        # Compute cache ratio as integer percentage.
        total_cache = delta.get("cache_read_tokens", 0) + delta.get(
            "cache_write_tokens", 0
        )
        cache_ratio = int(
            round(delta.get("cache_read_tokens", 0) / total_cache * 100)
            if total_cache > 0
            else 0
        )

        # Determine primary model and multi-model summary.
        model_delta: dict[str, dict[str, int]] = delta.get("models") or {}
        primary_model = _primary_model(model_delta)
        models_trailer = _format_models_trailer(model_delta)

        trailers = [
            "",  # blank line before trailers
            _COAUTHORED_CANONICAL,
            f"X-AI-Tokens-In: {delta.get('input_tokens', 0)}",
            f"X-AI-Tokens-Out: {delta.get('output_tokens', 0)}",
            f"X-AI-Cache-Read: {delta.get('cache_read_tokens', 0)}",
            f"X-AI-Cache-Write: {delta.get('cache_write_tokens', 0)}",
            f"X-AI-Cache-Ratio: {cache_ratio}%",
            f"X-AI-Est-Cost-USD: {cost:.6f}",
        ]
        if primary_model:
            trailers.append(f"X-AI-Model: {primary_model}")
        if models_trailer:
            trailers.append(f"X-AI-Models: {models_trailer}")

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
    cost: float,
    cwd: str,
    output: str,
) -> None:
    """Append a JSONL record to ~/.claude-mpm/commit-costs.jsonl.

    Args:
        commit_sha: Short SHA of the commit.
        delta: Token delta dict from get_token_delta().
        cost: Estimated cost from compute_cost().
        cwd: Working directory of the repository.
        output: Raw stdout from the git commit command.
    """
    _debug(f"write_cost_log: sha={commit_sha} cost={cost:.6f}")
    try:
        log_path = Path.home() / ".claude-mpm" / "commit-costs.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        record: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "commit_sha": commit_sha,
            "cwd": cwd,
            "tokens_in": delta.get("input_tokens", 0),
            "tokens_out": delta.get("output_tokens", 0),
            "cache_read": delta.get("cache_read_tokens", 0),
            "cache_write": delta.get("cache_write_tokens", 0),
            "est_cost_usd": cost,
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
            _debug("  no .claude-mpm dir found; using cwd as project_root")
            project_root = cwd

        working_dir = str(project_root)

        # 2. Compute token delta and cost.
        delta = get_token_delta(working_dir)
        cost = compute_cost(delta)
        _debug(f"  delta={delta} cost={cost:.6f}")

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
        amend_commit_message(commit_sha, delta, cost, working_dir)

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
        write_cost_log(final_sha, delta, cost, working_dir, f"[hook] {final_sha}")
        _debug(f"  run_as_git_hook: complete for sha={final_sha}")

    except Exception as exc:
        _debug(f"  run_as_git_hook EXCEPTION: {exc}")
        logger.warning("commit_cost_tracker.run_as_git_hook error: %s", exc)
