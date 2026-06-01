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

# Regex to extract the short SHA from a successful `git commit` output.
# Example: "[main abc1234] Add feature"
_SHA_RE = re.compile(r"\[.*?\s+([a-f0-9]{7,40})\]")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_token_delta(cwd: str) -> dict[str, int]:
    """Return per-commit token delta and update the running baseline.

    Reads the current cumulative totals from context-usage.json, computes the
    difference against the last-recorded baseline, then writes the new baseline
    so subsequent commits get the correct incremental numbers.

    Args:
        cwd: Working directory of the repository (used to locate .claude-mpm/).

    Returns:
        Dict with keys: input_tokens, output_tokens, cache_read_tokens,
        cache_write_tokens.  All values are non-negative integers.
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
    # (e.g. "summary-test") and token counts are absurdly high relative to what
    # a single session could realistically produce, treat the file as empty so
    # we get zero-delta rather than fraudulent large deltas.
    _STALE_THRESHOLD = 500_000  # 500k tokens is implausible in one session
    session_id = current.get("session_id", "")
    raw_input = int(current.get("cumulative_input_tokens", 0))
    raw_output = int(current.get("cumulative_output_tokens", 0))
    if (raw_input + raw_output) > _STALE_THRESHOLD or session_id == "summary-test":
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
    _debug(f"  cumulative={cumulative}")

    # Read previous baseline (zeros if this is the first commit).
    prev = _read_json_safe(baseline_file)
    baseline = {
        "input_tokens": int(prev.get("input_tokens", 0)),
        "output_tokens": int(prev.get("output_tokens", 0)),
        "cache_read_tokens": int(prev.get("cache_read_tokens", 0)),
        "cache_write_tokens": int(prev.get("cache_write_tokens", 0)),
    }
    _debug(f"  baseline={baseline}")

    # Delta = current minus previous (floor at zero to guard against resets).
    delta: dict[str, int] = {
        key: max(0, cumulative[key] - baseline[key]) for key in cumulative
    }
    _debug(f"  delta={delta}")

    # Persist new baseline atomically.
    _write_json_atomic(baseline_file, cumulative)

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


def amend_commit_message(
    commit_sha: str, delta: dict[str, int], cost: float, cwd: str
) -> None:
    """Amend the latest commit to add token trailers and normalise Co-Authored-By.

    Steps:
    1. Retrieve current commit message via ``git log``.
    2. Strip any generic Co-Authored-By: Claude (not MPM) lines.
    3. Ensure exactly one canonical Co-Authored-By: Claude MPM trailer.
    4. Append X-AI-* trailers with token counts and cost.
    5. Amend commit with ``git commit --amend --no-edit -m <msg> --no-verify``.

    Args:
        commit_sha: Short or full SHA of the commit to amend.
        delta: Token delta dict from get_token_delta().
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

        # 2. Strip generic Co-Authored-By: Claude lines (replace with empty string,
        #    then clean up double blank lines).
        cleaned_msg = _COAUTHORED_GENERIC_RE.sub("", original_msg)

        # 3. Remove any existing canonical trailer so we add exactly one.
        cleaned_msg = _COAUTHORED_CANONICAL_RE.sub("", cleaned_msg)

        # Strip trailing whitespace from each line and remove consecutive blank lines.
        lines = cleaned_msg.splitlines()
        normalised_lines: list[str] = []
        prev_blank = False
        for line in lines:
            stripped = line.rstrip()
            is_blank = stripped == ""
            if is_blank and prev_blank:
                continue  # Skip consecutive blank lines
            normalised_lines.append(stripped)
            prev_blank = is_blank

        # Remove leading / trailing blank lines.
        while normalised_lines and normalised_lines[0] == "":
            normalised_lines.pop(0)
        while normalised_lines and normalised_lines[-1] == "":
            normalised_lines.pop()

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

        new_msg = "\n".join(normalised_lines + trailers)

        # 5. Amend commit --no-verify to avoid recursive hook triggers.
        amend_result = subprocess.run(
            ["git", "commit", "--amend", "--no-edit", "-m", new_msg, "--no-verify"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if amend_result.returncode != 0:
            _debug(
                f"  amend FAILED (rc={amend_result.returncode}): {amend_result.stderr.strip()}"
            )
            logger.warning(
                "commit_cost_tracker: amend failed for %s: %s",
                commit_sha,
                amend_result.stderr.strip(),
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
    6. Amend HEAD with the enriched message (--no-verify to avoid recursion).
    7. Append a JSONL record to ~/.claude-mpm/commit-costs.jsonl.

    All failures are logged to the debug log and suppressed so the commit is
    never broken by hook errors.
    """
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
