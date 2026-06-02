"""Shared transcript-usage parsing utilities for Claude Code session JSONL files.

WHY: Both the Stop event handler and the git post-commit hook need to read
cumulative token usage from the session transcript.  Extracting the parsing
logic here avoids duplication and ensures both callers stay in sync when the
transcript format changes.

WHAT: Provides ``parse_transcript_usage()`` (sum all assistant-message usage
records in a JSONL file) and ``find_latest_transcript()`` (locate the
most-recently-modified JSONL for a given project cwd, without knowing the
session_id).

HOW TO TEST:
  - Call ``parse_transcript_usage()`` with a fixture JSONL and assert totals.
  - Call ``find_latest_transcript()`` with a tmp dir containing two JSONL files
    with different mtimes and assert the newer one is returned.

References
----------
(no spec section governs this helper module)
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Always-on debug log helper — writes unconditionally so failures are visible
# without needing CLAUDE_MPM_HOOK_DEBUG=true.
# ---------------------------------------------------------------------------
_TRANSCRIPT_DEBUG_LOG: Path = (
    Path.home() / ".claude-mpm" / "logs" / "commit-cost-debug.log"
)


def _debug(message: str) -> None:
    """Append *message* to the debug log file, unconditionally.

    WHY: Transcript parsing is called from a git post-commit hook subprocess
    that has no attached terminal.  Silent failures are invisible without a
    persistent log.

    WHAT: Creates the log directory, timestamps the message, and appends one
    line to commit-cost-debug.log.

    TEST: Call with any string and assert the log file exists and contains the
    message.  Call when the directory does not exist and verify no exception.
    """
    try:
        _TRANSCRIPT_DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
        with _TRANSCRIPT_DEBUG_LOG.open("a") as fh:
            fh.write(f"[{ts}] [transcript_usage] {message}\n")
    except Exception:
        pass  # Never raise from a debug helper


def _encode_cwd(cwd: str) -> str:
    """Encode a cwd path into Claude Code's project-dir naming convention.

    WHY: Claude Code stores transcripts at
    ``~/.claude/projects/{cwd_encoded}/{session_id}.jsonl`` where
    ``cwd_encoded`` replaces every ``/`` with ``-``.

    WHAT: Returns cwd with every forward-slash replaced by a hyphen.

    TEST: ``_encode_cwd('/foo/bar')`` == ``'-foo-bar'``.

    :spec: N/A
    """
    return cwd.replace("/", "-")


def derive_transcript_path(session_id: str, cwd: str) -> Path | None:
    """Derive the Claude Code transcript JSONL path from session_id and cwd.

    WHY: Claude Code stores transcripts at
    ``~/.claude/projects/{cwd_encoded}/{session_id}.jsonl`` where
    ``cwd_encoded`` is the cwd with every ``/`` replaced by ``-``.

    WHAT: Constructs and returns the expected path.  Does NOT check existence.

    TEST: Call with cwd='/foo/bar' and session_id='abc' and assert the result
    equals ``Path.home() / '.claude/projects/-foo-bar/abc.jsonl'``.

    Args:
        session_id: The Claude Code session UUID.
        cwd: The working directory string.

    Returns:
        A Path object, or None if session_id or cwd is empty.
    """
    if not session_id or not cwd:
        return None
    encoded = _encode_cwd(cwd)
    return Path.home() / ".claude" / "projects" / encoded / f"{session_id}.jsonl"


def find_latest_transcript(cwd: str) -> Path | None:
    """Find the most recently modified JSONL transcript for the given project cwd.

    WHY: The git post-commit hook does not have access to the session_id (it
    fires in a subprocess detached from the Claude Code event loop).  The
    workaround is to pick the most recently modified ``*.jsonl`` in the project
    transcript directory — that file belongs to the active session.

    WHAT: Resolves ``~/.claude/projects/{cwd_encoded}/``, lists all ``*.jsonl``
    files, and returns the one with the highest mtime.  Returns None if the
    directory does not exist or contains no JSONL files.

    TEST: Create a tmp dir with two JSONL files (touch the second one later so
    its mtime is higher), call find_latest_transcript(), and assert the second
    file is returned.

    Args:
        cwd: The working directory of the repository (absolute path string).

    Returns:
        Path to the most recently modified JSONL, or None.
    """
    if not cwd:
        return None
    encoded = _encode_cwd(cwd)
    transcript_dir = Path.home() / ".claude" / "projects" / encoded
    _debug(
        f"find_latest_transcript: dir={transcript_dir} exists={transcript_dir.exists()}"
    )
    if not transcript_dir.exists():
        return None
    candidates = list(transcript_dir.glob("*.jsonl"))
    if not candidates:
        _debug("find_latest_transcript: no JSONL files found")
        return None
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    _debug(
        f"find_latest_transcript: selected {latest.name} (mtime={latest.stat().st_mtime})"
    )
    return latest


def parse_transcript_usage(transcript_path: Path) -> dict | None:
    """Parse cumulative token usage from a Claude Code session transcript JSONL.

    WHY: Real Claude Code Stop events do NOT include a ``usage`` field.  The
    authoritative token counts live inside the session transcript as per-message
    ``usage`` objects on ``assistant`` records.  Summing them gives the session
    cumulative total.

    WHAT: Reads ``transcript_path`` line-by-line, filters to ``type=="assistant"``
    records that contain ``message.usage``, sums the four token fields across all
    such messages, and also collects a per-model breakdown keyed by
    ``message.model`` (e.g. ``"claude-opus-4-8"``).

    TEST: Call with a path containing assistant records from two different models
    with known usage dicts and assert (a) the totals equal the element-wise sum,
    (b) ``result["models"]`` contains exactly those two model keys with the correct
    per-model counts.  Returns None if the file is missing, unreadable, or contains
    no usage data.

    Args:
        transcript_path: Absolute path to the ``.jsonl`` session transcript.

    Returns:
        Dict with keys ``input_tokens``, ``output_tokens``,
        ``cache_creation_input_tokens``, ``cache_read_input_tokens`` (all int)
        **plus** ``models`` — a nested dict mapping model name to the same four
        token-count keys for that model only.  Returns None on failure / empty
        transcript.
    """
    if not transcript_path.exists():
        _debug(f"parse_transcript_usage: transcript not found: {transcript_path}")
        return None

    totals: dict = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "models": {},
    }
    found_any = False

    try:
        with transcript_path.open(encoding="utf-8", errors="replace") as fh:
            for raw_line in fh:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    rec = json.loads(raw_line)
                except json.JSONDecodeError:
                    _debug(
                        f"parse_transcript_usage: skipping invalid JSON line: "
                        f"{raw_line[:80]!r}"
                    )
                    continue

                if rec.get("type") != "assistant":
                    continue

                msg = rec.get("message", {})
                usage = msg.get("usage")
                if not usage:
                    continue

                inp = int(usage.get("input_tokens", 0) or 0)
                out = int(usage.get("output_tokens", 0) or 0)
                cc = int(usage.get("cache_creation_input_tokens", 0) or 0)
                cr = int(usage.get("cache_read_input_tokens", 0) or 0)

                totals["input_tokens"] += inp
                totals["output_tokens"] += out
                totals["cache_creation_input_tokens"] += cc
                totals["cache_read_input_tokens"] += cr

                # Per-model breakdown — use "unknown" when model field is absent.
                model = msg.get("model") or "unknown"
                if model not in totals["models"]:
                    totals["models"][model] = {
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 0,
                    }
                totals["models"][model]["input_tokens"] += inp
                totals["models"][model]["output_tokens"] += out
                totals["models"][model]["cache_creation_input_tokens"] += cc
                totals["models"][model]["cache_read_input_tokens"] += cr

                found_any = True

    except Exception as exc:
        _debug(f"parse_transcript_usage: parse error: {exc}")
        logger.debug("transcript_usage: parse error for %s: %s", transcript_path, exc)
        return None

    if not found_any:
        _debug(
            f"parse_transcript_usage: no assistant usage records in: {transcript_path}"
        )
        return None

    _debug(
        f"parse_transcript_usage: totals "
        f"in={totals['input_tokens']} out={totals['output_tokens']} "
        f"cc={totals['cache_creation_input_tokens']} "
        f"cr={totals['cache_read_input_tokens']} "
        f"models={list(totals['models'].keys())}"
    )
    return totals
