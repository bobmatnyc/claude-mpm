#!/usr/bin/env python3
"""Memory auto-capture hook for trusty-memory / kuzu-memory.

Implements GitHub issues #536 (trusty-memory backend) and #537 (kuzu-memory
fallback). This hook reads a Claude Code hook event from stdin and stores
small, meaningful facts about the session into whichever memory backend is
available — trusty-memory first (HTTP daemon), kuzu-memory second (CLI),
otherwise it is a no-op.

Design goals
------------
* **Zero overhead when no backend installed** — backend detection runs once
  at import time and is cached for the lifetime of the process; if neither
  backend is available the hook returns immediately with `{"continue": true}`.
* **Never block Claude Code** — every external call is bounded by a short
  timeout (HTTP ≤200ms, subprocess ≤2s); all errors are swallowed and the
  hook always exits 0 with a continue payload.
* **Stdin guarded** — `select.select(timeout=1.0)` prevents the hook from
  hanging when invoked with no piped input (CLAUDE.md stability pattern).
* **Captures minimal facts** — file paths, git commit messages, session
  start/end metadata. We deliberately do NOT store full tool JSON, file
  contents, or assistant reasoning.

Invocation: ``python3 -m claude_mpm.hooks.memory_capture`` from
``.claude/settings.json`` (PostToolUse, Stop, SubagentStop, SessionStart).

References
----------
SPEC-INTEGRATIONS-06~1 : docs/specs/integrations.md#SPEC-INTEGRATIONS-06~1
SPEC-INTEGRATIONS-07~1 : docs/specs/integrations.md#SPEC-INTEGRATIONS-07~1
"""

from __future__ import annotations

import json
import logging
import os
import re
import select
import shutil
import subprocess  # nosec B404
import sys
import threading
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    from claude_mpm.hooks.transcript_usage import (
        derive_transcript_path as _derive_transcript_path,
    )
except ImportError:
    _derive_transcript_path = None  # type: ignore[assignment]
    logger.debug(
        "Q&A-pair PM-turn capture disabled: claude_mpm.hooks.transcript_usage"
        " could not be imported."
    )

# Timeouts — kept short so the hook never blocks Claude Code's event loop.
_HTTP_TIMEOUT_S = 0.2
_SUBPROCESS_TIMEOUT_S = 2.0
_STDIN_WAIT_S = 1.0

# Recall-specific timeouts — slightly more generous since recall is the
# primary value-add of the UserPromptSubmit handler, but still strictly
# bounded so the prompt never stalls.
_RECALL_HTTP_TIMEOUT_S = 0.8
_RECALL_SUBPROCESS_TIMEOUT_S = 2.0

# UserPromptSubmit thresholds.
_PROMPT_MIN_WORDS = 10
_PROMPT_QUERY_MAX_CHARS = 200
_PROMPT_CAPTURE_MAX_CHARS = 100
_ENRICH_MAX_CHARS = 2000
_RECALL_LIMIT = 5

# Q&A pair capture — state persisted between Stop and UserPromptSubmit.
# State dir: ~/.claude-mpm/state/{session_id}_last_response.txt
_QA_STATE_DIR = Path.home() / ".claude-mpm" / "state"
_QA_PM_SNIPPET_MAX_CHARS = 500  # cap PM text stored to disk
_QA_REPLY_SNIPPET_MAX_CHARS = 200  # cap user-reply snippet stored to memory
# State files older than this are pruned on write to avoid unbounded disk growth
# from sessions that ended without a follow-up UserPromptSubmit.
_QA_STATE_TTL_SECONDS = 24 * 3600  # 24 hours
# Maximum age (seconds) of a state file for it to be treated as a Q&A reply.
# A state file written by Stop but not consumed within this window is stale —
# the next UserPromptSubmit is treated as a new standalone prompt, not a reply.
# This bounds mis-pairing when the user starts an unrelated session much later
# or when the store failed and left the file behind.
_QA_PAIR_MAX_AGE_SECONDS = 600  # 10 minutes
# Project-name values that carry no signal and add tag noise — computed once at
# module load time so we pay no per-call cost.  We do NOT include the home-dir
# basename here because a project legitimately named the same as the home-dir
# basename (e.g. /projects/alice when home is /home/alice) should still be
# tagged.  The actual home-dir path is handled by an explicit `cwd != Path.home()`
# guard in handle_user_prompt_submit.
_QA_NOISY_NAMES: frozenset[str] = frozenset({"", "tmp", "workspace", "~"})

# Default ports / addresses for backends.
_DEFAULT_TRUSTY_PORT = 7070
_TRUSTY_ADDR_FILE = Path.home() / ".trusty-memory" / "http_addr"


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> dict[str, Any]:
    """Best-effort YAML load. Returns ``{}`` on any failure.

    PyYAML is an optional dep; if it's missing or the file is malformed we
    silently return an empty dict so the hook can still fall back to defaults.
    """
    if not path.is_file():
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _load_config() -> dict[str, Any]:
    """Load ``~/.claude-mpm/config.yaml`` if present.

    Looked-up keys (all optional):
        trusty_memory.enabled: bool (default True)
        trusty_memory.port: int (default 7070)
        trusty_memory.palace: str (default basename of cwd)
        trusty_memory.capture.{session_start,file_changes,git_commits,session_end}: bool
        trusty_memory.capture.qa_pairs: bool — capture Q&A pairs from the PM turn
            (Stop) and user reply (UserPromptSubmit). **Default: True** (capture is
            enabled whenever the key is absent; set explicitly to false to disable).
        kuzu_memory.enabled: bool (default True)
        kuzu_memory.palace: str (unused, kuzu has no palace concept)
        kuzu_memory.capture.*: same shape as trusty_memory.capture (including
            qa_pairs, which also defaults to True)
    """
    return _load_yaml(Path.home() / ".claude-mpm" / "config.yaml")


_CONFIG: dict[str, Any] = _load_config()


def _capture_enabled(backend: str, event: str) -> bool:
    """Check whether a backend should capture a given event type.

    Defaults to True for everything when no config is present.
    """
    section = _CONFIG.get(backend, {})
    if not isinstance(section, dict):
        return True
    capture = section.get("capture", {})
    if not isinstance(capture, dict):
        return True
    return bool(capture.get(event, True))


def _backend_enabled(backend: str) -> bool:
    """Whether the given backend is enabled in config (default True)."""
    section = _CONFIG.get(backend, {})
    if not isinstance(section, dict):
        return True
    return bool(section.get("enabled", True))


def _enrich_enabled(backend: str) -> bool:
    """Whether enrichment (recall + context injection) is enabled for backend.

    Reads ``<backend>.enrich.enabled`` from config; defaults to True.
    """
    section = _CONFIG.get(backend, {})
    if not isinstance(section, dict):
        return True
    enrich = section.get("enrich", {})
    if not isinstance(enrich, dict):
        return True
    return bool(enrich.get("enabled", True))


def _enrich_max_chars(backend: str) -> int:
    """Max chars of injected context for backend (default ``_ENRICH_MAX_CHARS``)."""
    section = _CONFIG.get(backend, {})
    if not isinstance(section, dict):
        return _ENRICH_MAX_CHARS
    enrich = section.get("enrich", {})
    if not isinstance(enrich, dict):
        return _ENRICH_MAX_CHARS
    # Config key historically named ``max_tokens`` per the task spec; treat
    # it as a character cap (rough approximation, ~4 chars/token).
    raw = enrich.get("max_tokens", enrich.get("max_chars", _ENRICH_MAX_CHARS))
    if raw is None:
        return _ENRICH_MAX_CHARS
    try:
        value = int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return _ENRICH_MAX_CHARS
    return max(100, value)


# ---------------------------------------------------------------------------
# Backend abstract base
# ---------------------------------------------------------------------------


class AbstractMemoryCaptureBackend(ABC):
    """Pluggable memory backend interface.

    Implementations MUST never raise from ``store`` — any failure is swallowed
    so the hook can keep flowing through Claude Code's event pipeline.
    """

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def store(self, fact: str, tags: list[str] | None = None) -> None: ...

    @abstractmethod
    def recall(self, query: str) -> list[str]:
        """Return relevant memory strings for query.

        Returns an empty list if no results, the backend is unreachable, or on
        any other error. Implementations MUST never raise — recall failures
        are non-fatal.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str: ...


# ---------------------------------------------------------------------------
# Trusty memory backend (HTTP daemon)
# ---------------------------------------------------------------------------


def _trusty_base_url() -> str:
    """Discover the trusty-memory daemon address.

    Mirrors the pattern in ``handlers/trusty.py``: reads
    ``~/.trusty-memory/http_addr`` (single ``host:port`` line) and falls back
    to the default port when missing.
    """
    port = _CONFIG.get("trusty_memory", {}).get("port", _DEFAULT_TRUSTY_PORT)
    try:
        addr = _TRUSTY_ADDR_FILE.read_text(encoding="utf-8").strip()
        if addr:
            return f"http://{addr}"
    except OSError:
        pass
    return f"http://127.0.0.1:{port}"


def _trusty_palace_name() -> str:
    """Palace name: config override, else basename of cwd."""
    configured = _CONFIG.get("trusty_memory", {}).get("palace") or ""
    if configured.strip():
        return configured.strip()
    return Path.cwd().name


def _parse_recall_payload(raw: str) -> list[str]:
    """Parse a recall response into a list of strings.

    Accepts (in order):
      * JSON array of strings → returned as-is
      * JSON array of objects with ``content``/``fact``/``memory``/``text`` keys
      * JSON object with a ``memories``/``results``/``data``/``items`` key
      * Newline-separated plain text (one fact per line)

    Always returns at most ``_RECALL_LIMIT`` non-empty stripped strings.
    """
    raw = (raw or "").strip()
    if not raw:
        return []

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        data = None

    items: list[Any] | None = None
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for key in ("memories", "results", "data", "items", "recalled"):
            value = data.get(key)
            if isinstance(value, list):
                items = value
                break

    results: list[str] = []
    if items is not None:
        for entry in items:
            if isinstance(entry, str):
                text = entry.strip()
            elif isinstance(entry, dict):
                text = ""
                # Unwrap recall response's `drawer` wrapper if present —
                # /api/v1/palaces/<palace>/recall returns entries shaped as
                # {"drawer": {"content": ..., "tags": [...]}, "layer": N, "score": F}
                # so the content keys live one level down.
                raw_entry = (
                    entry.get("drawer")
                    if isinstance(entry.get("drawer"), dict)
                    else entry
                )
                for key in ("content", "fact", "memory", "text", "value"):
                    candidate = raw_entry.get(key)
                    if isinstance(candidate, str) and candidate.strip():
                        text = candidate.strip()
                        break
            else:
                text = str(entry).strip()
            if text:
                results.append(text)
            if len(results) >= _RECALL_LIMIT:
                break
        return results

    # Fall back: treat as newline-separated text.
    for line in raw.splitlines():
        line = line.strip().lstrip("-•* ").strip()
        if line:
            results.append(line)
        if len(results) >= _RECALL_LIMIT:
            break
    return results


class TrustyMemoryBackend(AbstractMemoryCaptureBackend):
    """HTTP-based trusty-memory daemon backend.

    Availability requires both the ``trusty-memory`` binary on PATH AND a
    reachable ``/health`` endpoint on the discovered base URL (≤200ms).
    Store path attempts a POST to ``/api/v1/palaces/<palace>/drawers``;
    if that returns 404/405 (older daemon) the implementation falls back to
    a subprocess ``trusty-memory remember`` call.
    """

    @property
    def name(self) -> str:
        return "trusty-memory"

    def is_available(self) -> bool:
        if not _backend_enabled("trusty_memory"):
            return False
        if not shutil.which("trusty-memory"):
            return False
        health_url = f"{_trusty_base_url()}/health"
        try:
            req = urllib.request.Request(health_url, method="GET")  # nosec B310
            with urllib.request.urlopen(  # nosec B310
                req, timeout=_HTTP_TIMEOUT_S
            ) as resp:
                return bool(200 <= resp.status < 300)
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    def store(self, fact: str, tags: list[str] | None = None) -> None:
        try:
            base = _trusty_base_url()
            palace = _trusty_palace_name()
            url = f"{base}/api/v1/palaces/{palace}/drawers"
            body = json.dumps(
                {
                    "content": fact,
                    "tags": tags or [],
                    "source": "claude-mpm-hook",
                }
            ).encode("utf-8")
            req = urllib.request.Request(  # nosec B310
                url,
                data=body,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(  # nosec B310
                    req, timeout=_HTTP_TIMEOUT_S
                ) as resp:
                    if 200 <= resp.status < 300:
                        return
                    # Older daemons may not expose this endpoint; fall through
                    # to the CLI fallback below.
            except urllib.error.HTTPError as e:
                if e.code not in (404, 405):
                    return  # other HTTP errors: give up silently
                # else fall through to CLI fallback
            # CLI fallback — `trusty-memory remember` is the documented verb.
            self._cli_store(fact, palace)
        except Exception:
            # Never propagate — hook MUST stay non-fatal.
            return

    @staticmethod
    def _cli_store(fact: str, palace: str) -> None:
        try:
            subprocess.run(  # nosec B603 B607
                ["trusty-memory", "remember", "--palace", palace, fact],
                check=False,
                capture_output=True,
                timeout=_SUBPROCESS_TIMEOUT_S,
            )
        except (subprocess.SubprocessError, OSError):
            return

    def recall(self, query: str) -> list[str]:
        """Recall via HTTP first, fall back to ``trusty-memory recall`` CLI.

        Returns up to ``_RECALL_LIMIT`` memory strings. Empty list on any
        error so callers can use the result unconditionally.
        """
        if not query:
            return []
        try:
            palace = _trusty_palace_name()
            results = self._http_recall(query, palace)
            if results is not None:
                return results
            return self._cli_recall(query, palace)
        except Exception:
            return []

    @staticmethod
    def _http_recall(query: str, palace: str) -> list[str] | None:
        """Try HTTP recall endpoint. Returns None to signal CLI fallback."""
        from urllib.parse import quote, urlencode

        base = _trusty_base_url()
        params = urlencode({"q": query, "limit": _RECALL_LIMIT})
        url = f"{base}/api/v1/palaces/{quote(palace, safe='')}/recall?{params}"
        try:
            req = urllib.request.Request(url, method="GET")  # nosec B310
            with urllib.request.urlopen(  # nosec B310
                req, timeout=_RECALL_HTTP_TIMEOUT_S
            ) as resp:
                if not (200 <= resp.status < 300):
                    return None
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None  # endpoint missing → fall back to CLI
            return []
        except (urllib.error.URLError, TimeoutError, OSError):
            return []

        return _parse_recall_payload(raw)

    @staticmethod
    def _cli_recall(query: str, palace: str) -> list[str]:
        try:
            proc = subprocess.run(  # nosec B603 B607
                ["trusty-memory", "recall", "--palace", palace, query],
                check=False,
                capture_output=True,
                timeout=_RECALL_SUBPROCESS_TIMEOUT_S,
            )
        except (subprocess.SubprocessError, OSError):
            return []
        if proc.returncode != 0:
            return []
        try:
            text = proc.stdout.decode("utf-8", errors="replace")
        except Exception:
            return []
        return _parse_recall_payload(text)


# ---------------------------------------------------------------------------
# Kuzu memory backend (subprocess CLI)
# ---------------------------------------------------------------------------


class KuzuMemoryBackend(AbstractMemoryCaptureBackend):
    """Fallback backend that shells out to ``kuzu-memory memory learn``.

    Matches the existing CLI shape used by
    ``claude_mpm.hooks.kuzu_memory_hook`` (``memory learn <content>
    --no-wait``). Availability is just a PATH lookup — no daemon required.
    """

    @property
    def name(self) -> str:
        return "kuzu-memory"

    def is_available(self) -> bool:
        if not _backend_enabled("kuzu_memory"):
            return False
        return shutil.which("kuzu-memory") is not None

    def store(self, fact: str, tags: list[str] | None = None) -> None:
        try:
            # ``--no-wait`` makes the CLI return immediately while the actual
            # write happens in the background; perfect for hooks.
            subprocess.run(  # nosec B603 B607
                ["kuzu-memory", "memory", "learn", fact, "--no-wait"],
                check=False,
                capture_output=True,
                timeout=_SUBPROCESS_TIMEOUT_S,
            )
        except (subprocess.SubprocessError, OSError):
            return

    def recall(self, query: str) -> list[str]:
        """Shell out to ``kuzu-memory recall <query>`` and parse the output."""
        if not query:
            return []
        try:
            proc = subprocess.run(  # nosec B603 B607
                ["kuzu-memory", "recall", query],
                check=False,
                capture_output=True,
                timeout=_RECALL_SUBPROCESS_TIMEOUT_S,
            )
        except (subprocess.SubprocessError, OSError):
            return []
        if proc.returncode != 0:
            return []
        try:
            text = proc.stdout.decode("utf-8", errors="replace")
        except Exception:
            return []
        return _parse_recall_payload(text)


# ---------------------------------------------------------------------------
# Backend selection (cached at import time)
# ---------------------------------------------------------------------------


def _select_backend() -> AbstractMemoryCaptureBackend | None:
    """Pick the first available backend in priority order.

    Order: trusty-memory (preferred) → kuzu-memory (fallback) → None.
    Selection runs once and is cached so subsequent hook invocations skip
    the availability probes entirely.
    """
    trusty = TrustyMemoryBackend()
    if trusty.is_available():
        return trusty
    kuzu = KuzuMemoryBackend()
    if kuzu.is_available():
        return kuzu
    return None


_BACKEND: AbstractMemoryCaptureBackend | None = _select_backend()


# ---------------------------------------------------------------------------
# Project context detection
# ---------------------------------------------------------------------------


_STACK_MARKERS: list[tuple[str, str]] = [
    ("pyproject.toml", "Python"),
    ("setup.py", "Python"),
    ("requirements.txt", "Python"),
    ("package.json", "Node"),
    ("go.mod", "Go"),
    ("Cargo.toml", "Rust"),
    ("pom.xml", "Java"),
    ("build.gradle", "Java"),
    ("Gemfile", "Ruby"),
    ("composer.json", "PHP"),
]


def _detect_stack(cwd: Path) -> str:
    """Return the first detected language stack, or ``"unknown"``."""
    for marker, name in _STACK_MARKERS:
        if (cwd / marker).is_file():
            return name
    return "unknown"


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------


def _handle_session_start(
    event: dict[str, Any], backend: AbstractMemoryCaptureBackend
) -> None:
    if not _capture_enabled(backend.name.replace("-", "_"), "session_start"):
        return
    cwd_raw = event.get("cwd")
    cwd = Path(cwd_raw) if cwd_raw else Path.cwd()
    project = cwd.name
    stack = _detect_stack(cwd)
    backend.store(
        f"Session started in {cwd} (project: {project}, stack: {stack})",
        tags=["session-start", project],
    )


def _handle_post_tool_use(
    event: dict[str, Any], backend: AbstractMemoryCaptureBackend
) -> None:
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}

    # Write / Edit / NotebookEdit / MultiEdit — capture path only.
    if tool_name in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        if not _capture_enabled(backend.name.replace("-", "_"), "file_changes"):
            return
        path = (
            tool_input.get("file_path")
            or tool_input.get("notebook_path")
            or tool_input.get("path")
            or ""
        )
        if path:
            backend.store(f"File modified: {path}", tags=["file-change", tool_name])
        return

    # Bash — only interested in git commit messages.
    if tool_name == "Bash":
        if not _capture_enabled(backend.name.replace("-", "_"), "git_commits"):
            return
        command = tool_input.get("command", "")
        if "git commit" not in command:
            return
        message = _extract_commit_message(command, event)
        if message:
            backend.store(f"Git commit: {message}", tags=["git-commit"])


_COMMIT_MSG_PATTERNS = [
    # -m "message" or -m 'message'
    re.compile(r"""-m\s+(['"])(.+?)\1"""),
    # --message="message"
    re.compile(r"""--message[= ]+(['"])(.+?)\1"""),
]


def _extract_commit_message(command: str, event: dict[str, Any]) -> str:
    """Pull a commit message out of the bash command (best-effort).

    Falls back to scanning the tool output for the first ``[branch hash]``
    style git status line.
    """
    for pattern in _COMMIT_MSG_PATTERNS:
        match = pattern.search(command)
        if match:
            return match.group(2).strip().splitlines()[0][:200]

    # Fallback: scan stdout for first non-empty line after a ``[main abc1234]``-style line.
    tool_response = event.get("tool_response") or event.get("tool_output") or {}
    if isinstance(tool_response, dict):
        text = tool_response.get("stdout") or tool_response.get("output") or ""
    else:
        text = str(tool_response)
    if not text:
        return ""
    for line in text.splitlines():
        # git commit success line: "[branch hash] commit message"
        m = re.match(r"^\[[^\]]+\]\s+(.+)$", line.strip())
        if m:
            return m.group(1)[:200]
    return ""


def _extract_last_assistant_text(transcript_path: Path) -> str:
    """Extract the last assistant turn's concatenated text blocks from a transcript.

    WHAT: Reads a Claude Code session JSONL transcript, finds the last record
    with ``type == "assistant"``, and concatenates all ``{type: "text", text: ...}``
    content blocks into a single string.

    WHY: The Stop hook needs to persist the most-recent PM response so the next
    UserPromptSubmit can form a Q&A pair.  We only want the textual prose — not
    tool calls or other block types.

    Returns an empty string when the file is missing, unreadable, or contains no
    assistant records.  Never raises.
    """
    last_text = ""
    try:
        with transcript_path.open(encoding="utf-8", errors="replace") as fh:
            for raw_line in fh:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    rec = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                if rec.get("type") != "assistant":
                    continue
                msg = rec.get("message") or {}
                content = msg.get("content") or []
                if not isinstance(content, list):
                    continue
                parts: list[str] = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text") or ""
                        if text:
                            parts.append(text)
                if parts:
                    last_text = " ".join(parts)
    except Exception:
        return ""
    return last_text


def _qa_state_path(session_id: str) -> Path | None:
    """Return the path for the Q&A state file for ``session_id``, or None if invalid.

    Rejects empty session IDs and any that contain path-separator characters
    (``/``, ``\\``) or the parent-directory sequence ``..``.  After constructing
    the candidate path it resolves both sides and verifies the result is still
    a direct child of the state directory, preventing path-traversal attacks.
    Returns None on any invalid input or resolution failure; callers treat None
    as "no state".  Never raises.
    """
    if not session_id or "/" in session_id or "\\" in session_id or ".." in session_id:
        return None
    try:
        candidate = _QA_STATE_DIR / f"{session_id}_last_response.txt"
        if candidate.resolve().parent != _QA_STATE_DIR.resolve():
            return None
        return candidate
    except Exception:
        return None


def _prune_stale_qa_state() -> None:
    """Delete Q&A state files older than ``_QA_STATE_TTL_SECONDS``.

    Deliberately best-effort: any error is silently swallowed.  Called from
    ``_write_qa_state`` so that state files from abandoned sessions (i.e.
    sessions that ended without a follow-up UserPromptSubmit) do not
    accumulate on disk indefinitely.
    """
    try:
        if not _QA_STATE_DIR.is_dir():
            return
        cutoff = time.time() - _QA_STATE_TTL_SECONDS
        for candidate in _QA_STATE_DIR.glob("*_last_response.txt"):
            try:
                if candidate.stat().st_mtime < cutoff:
                    candidate.unlink(missing_ok=True)
            except Exception:
                # Best-effort: skip files we cannot stat or unlink.
                pass
    except Exception:
        return


def _write_qa_state(session_id: str, pm_text: str) -> None:
    """Persist the PM turn snippet to the session state file.

    Creates the state directory if absent.  Truncates to
    ``_QA_PM_SNIPPET_MAX_CHARS``.  Prunes stale state files (TTL-based)
    before writing.  Returns silently when session_id fails sanitization.
    Never raises.
    """
    if not session_id or not pm_text:
        return
    path = _qa_state_path(session_id)
    if path is None:
        return
    try:
        _QA_STATE_DIR.mkdir(parents=True, exist_ok=True)
        _prune_stale_qa_state()
        snippet = pm_text[:_QA_PM_SNIPPET_MAX_CHARS].strip()
        path.write_text(snippet, encoding="utf-8")
    except Exception:
        return


def _read_qa_state(session_id: str) -> str:
    """Read the persisted PM snippet for ``session_id``.

    Returns an empty string when the file is missing, the session_id fails
    sanitization, or the file is unreadable.  Never raises.
    """
    if not session_id:
        return ""
    path = _qa_state_path(session_id)
    if path is None:
        return ""
    try:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def _read_qa_state_with_mtime(session_id: str) -> tuple[str, float] | None:
    """Open the Q&A state file ONCE, returning (content, mtime) or None.

    WHAT: Reads both the file content and its mtime from a single ``open``
    call using ``os.fstat`` on the open file handle, eliminating the TOCTOU
    race between a separate ``stat()`` freshness check and a second ``open``
    for the content.

    WHY: The previous code did ``state_path.stat().st_mtime`` and then
    separately called ``_read_qa_state(session_id)``  — two filesystem
    operations on the same file.  Between them the file could be replaced or
    deleted by a concurrent invocation, leading to inconsistent freshness
    decisions.  A single ``open`` + ``os.fstat`` collapses both into one
    atomic read.

    Returns:
        ``(content_str, mtime_float)`` when the file exists and is readable,
        or ``None`` when the session_id fails sanitization, the file is
        absent, or any read error occurs.  Never raises.
    """
    if not session_id:
        return None
    path = _qa_state_path(session_id)
    if path is None:
        return None
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            content = fh.read().strip()
            mtime = os.fstat(fh.fileno()).st_mtime
        return (content, mtime)
    except Exception:
        # Covers FileNotFoundError (file absent), PermissionError (unreadable),
        # and any other OS-level failure — all map to the same "no state" result.
        return None


def _delete_qa_state(session_id: str) -> None:
    """Delete the Q&A state file for ``session_id`` (one-shot consumption).

    No-op when the file does not exist or session_id fails sanitization.
    Never raises.
    """
    if not session_id:
        return
    path = _qa_state_path(session_id)
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except Exception:
        return


def _capture_pm_turn_on_stop(event: dict[str, Any], backend_key: str) -> None:
    """Read the last PM response from the session transcript and persist it.

    WHAT: Derives the transcript path from ``session_id`` + ``cwd`` in the Stop
    event, extracts the last assistant text, and writes a snippet to the Q&A
    state dir so the next UserPromptSubmit can form a paired fact.

    WHY: Hook invocations are separate subprocesses — the only cross-invocation
    channel is the filesystem.  Writing state here on Stop and reading it on
    UserPromptSubmit is the lightest-weight cross-process bridge available.

    Never raises: all errors are swallowed so the Stop handler keeps flowing.
    """
    if not _capture_enabled(backend_key, "qa_pairs"):
        return
    if _derive_transcript_path is None:
        return
    try:
        session_id = event.get("session_id") or ""
        cwd_raw = event.get("cwd") or ""
        if not session_id or not cwd_raw:
            return
        transcript_path = _derive_transcript_path(session_id, cwd_raw)
        if transcript_path is None or not transcript_path.exists():
            return
        pm_text = _extract_last_assistant_text(transcript_path)
        if not pm_text:
            return
        _write_qa_state(session_id, pm_text)
    except Exception:
        return


def _handle_session_end(
    event: dict[str, Any], backend: AbstractMemoryCaptureBackend
) -> None:
    # NOTE: _capture_pm_turn_on_stop is intentionally NOT called here.
    # It is called once per Stop/SubagentStop event from main() — before the
    # per-backend loop — so it runs exactly once regardless of how many active
    # backends are configured.  Calling it here would write the state file once
    # per backend (e.g. twice with trusty + kuzu both enabled).
    backend_key = backend.name.replace("-", "_")
    if not _capture_enabled(backend_key, "session_end"):
        return
    cwd_raw = event.get("cwd")
    cwd = Path(cwd_raw) if cwd_raw else Path.cwd()
    project = cwd.name
    backend.store(f"Session ended in {project}", tags=["session-end", project])


def _format_memory_context(recalled: list[str], max_chars: int) -> str:
    """Format recalled memory facts as a bracketed context block.

    Truncates the joined block (after header/footer accounting) to ``max_chars``
    total. Returns an empty string if nothing fits.
    """
    if not recalled:
        return ""

    header = "[Memory context]\n"
    footer = "\n[End memory context]"
    budget = max_chars - len(header) - len(footer)
    if budget <= 0:
        return ""

    bullets: list[str] = []
    used = 0
    for fact in recalled:
        line = f"- {fact}"
        # +1 for newline between bullets.
        cost = len(line) + (1 if bullets else 0)
        if used + cost > budget:
            break
        bullets.append(line)
        used += cost

    if not bullets:
        return ""
    return f"{header}{chr(10).join(bullets)}{footer}"


def handle_user_prompt_submit(
    event: dict[str, Any],
) -> dict[str, Any]:
    """Capture the prompt and enrich Claude's context with recalled memory.

    Returns a Claude Code hook response dict. Always returns
    ``{"continue": True}`` (possibly with ``hookSpecificOutput`` for
    enrichment). Never raises.

    Behaviour:
      * **Q&A pair mode** (state file exists for this session_id): a prior PM
        turn was captured at Stop.  This prompt is a reply — lower/skip the
        ``_PROMPT_MIN_WORDS`` gate and store a paired ``"PM: ...\\nUser: ..."``
        fact tagged ``["qa-pair", "prompt", project]``.  Consumes and deletes
        the state file (one-shot).
      * **Standalone mode** (no state file): existing behaviour — skip short
        prompts (< ``_PROMPT_MIN_WORDS`` words), store ``"User prompt: ..."``
        tagged ``["prompt"]``.
      * Skip when no backend is selected.
      * Recall using the first ``_PROMPT_QUERY_MAX_CHARS`` chars of the prompt
        (unchanged, always attempted for non-empty prompts when enrichment is
        enabled — even short replies benefit from memory context).
      * Capture is fire-and-forget on a daemon thread so the hook returns
        immediately.
      * Inject recalled context as ``additionalContext`` via
        ``hookSpecificOutput`` when there are any results.

    :spec: SPEC-INTEGRATIONS-06~1
    """
    result: dict[str, Any] = {"continue": True}

    if _BACKEND is None:
        return result

    prompt = event.get("prompt") or ""
    if not isinstance(prompt, str):
        return result
    prompt = prompt.strip()
    if not prompt:
        return result

    backend = _BACKEND
    backend_key = backend.name.replace("-", "_")

    # --- Q&A pair detection ---------------------------------------------------
    # Check for a persisted PM turn from the most-recent Stop event.
    session_id = event.get("session_id") or ""
    cwd_raw = event.get("cwd") or ""
    cwd = Path(cwd_raw) if cwd_raw else Path.cwd()

    # Only include the project tag when the directory name is meaningful.
    # Values like "~", "tmp", or "workspace" add no signal and create noise.
    # _QA_NOISY_NAMES is a module-level frozenset computed once at import time.
    # The explicit `cwd != Path.home()` check handles the actual home directory;
    # we do not put Path.home().name in _QA_NOISY_NAMES because a project
    # coincidentally named the same as the home-dir basename (e.g. /projects/alice)
    # should still receive the project tag.
    project_name = cwd.name
    qa_tags: list[str] = ["qa-pair", "prompt"]
    if project_name and project_name not in _QA_NOISY_NAMES and cwd != Path.home():
        qa_tags.append(project_name)

    # Read the state file and apply the freshness window in a SINGLE filesystem
    # operation (TOCTOU fix): _read_qa_state_with_mtime opens the file once and
    # returns both content and mtime via os.fstat on the open handle.
    #
    # Consume-once semantics: the state file is deleted here, in the synchronous
    # path, immediately after reading — regardless of whether backend.store()
    # later succeeds.  This prevents mis-pairing: if we kept the file until a
    # successful store, a backend outage would leave it in place and every
    # subsequent UserPromptSubmit within the 600s window would pair a NEW user
    # reply with the SAME stale PM turn.  Losing one pair on a transient failure
    # is strictly preferable to fabricating incorrect paired facts.
    pm_snippet = ""
    if session_id:
        state_result = _read_qa_state_with_mtime(session_id)
        if state_result is not None:
            content, mtime = state_result
            age = time.time() - mtime
            if age <= _QA_PAIR_MAX_AGE_SECONDS:
                pm_snippet = content
                # Consume-once: delete synchronously before spawning the thread.
                _delete_qa_state(session_id)
            else:
                # Stale file: delete it and fall through to standalone path.
                _delete_qa_state(session_id)

    is_qa_reply = bool(pm_snippet)

    # Apply the minimum-words gate only for standalone prompts.
    if not is_qa_reply and len(prompt.split()) < _PROMPT_MIN_WORDS:
        return result

    # 1) Recall (synchronous, bounded). Result drives both enrichment and
    # whether we bother with the additionalContext payload.
    recalled: list[str] = []
    if _enrich_enabled(backend_key):
        try:
            query = prompt[:_PROMPT_QUERY_MAX_CHARS]
            recalled = backend.recall(query) or []
        except Exception:
            recalled = []

    # 2) Capture (fire-and-forget). Never blocks the return.
    try:
        if is_qa_reply and _capture_enabled(backend_key, "qa_pairs"):
            # Paired Q&A fact.  The state file was already deleted synchronously
            # (consume-once) before this branch — _bg_store_qa just stores the
            # fact.  A store failure loses this one pair, which is acceptable for
            # a best-effort memory system; it is strictly better than keeping the
            # file and mis-pairing future prompts.
            reply_snippet = prompt[:_QA_REPLY_SNIPPET_MAX_CHARS].strip()
            qa_fact = f"PM: {pm_snippet}\nUser: {reply_snippet}"

            def _bg_store_qa() -> None:
                try:
                    backend.store(qa_fact, tags=qa_tags)
                except Exception:
                    # Store failed — pair is lost for this invocation.
                    # The state file was already consumed (deleted synchronously),
                    # so no mis-pairing will occur on the next UserPromptSubmit.
                    return

            threading.Thread(target=_bg_store_qa, daemon=True).start()
        elif is_qa_reply:
            # qa_pairs capture is disabled.  State file was already deleted
            # synchronously (consume-once) above — nothing left to do here.
            pass
        else:
            # Standalone prompt — existing behaviour.
            snippet = prompt[:_PROMPT_CAPTURE_MAX_CHARS].strip()
            fact = f"User prompt: {snippet}"

            def _bg_store() -> None:
                try:
                    backend.store(fact, tags=["prompt"])
                except Exception:
                    return

            threading.Thread(target=_bg_store, daemon=True).start()
    except Exception:
        # Even thread spawn failure must not break the hook.
        pass

    # 3) Build hookSpecificOutput if we got recall results.
    if recalled:
        try:
            context = _format_memory_context(recalled, _enrich_max_chars(backend_key))
            if context:
                result["hookSpecificOutput"] = {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": context,
                }
        except Exception:
            pass

    return result


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def _emit_continue() -> None:
    """Always emit a non-blocking continue response, even on errors."""
    print(json.dumps({"continue": True}))


def _read_event() -> dict[str, Any] | None:
    """Read JSON from stdin with a timeout guard.

    Per CLAUDE.md stability patterns: use ``select`` to avoid blocking on
    stdin when the hook is invoked with no piped input.
    """
    try:
        ready, _, _ = select.select([sys.stdin], [], [], _STDIN_WAIT_S)
    except (ValueError, OSError):
        return None
    if not ready:
        return None
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def main() -> None:
    """Read one Claude Code hook event from stdin and dispatch to backend.

    :spec: SPEC-INTEGRATIONS-07~1
    """
    event = _read_event()
    if event is None:
        _emit_continue()
        return

    hook_event = (
        event.get("hook_event_name")
        or event.get("event")
        or event.get("hook_event_type")
        or ""
    )

    # UserPromptSubmit returns a richer response (additionalContext) — handle
    # it before the backend-required branches so the hook still produces a
    # valid no-op response when no backend is available.
    if hook_event == "UserPromptSubmit":
        try:
            response = handle_user_prompt_submit(event)
        except Exception:
            response = {"continue": True}
        print(json.dumps(response))
        return

    # Fast path: no backend → no work to do for capture-only events.
    if _BACKEND is None:
        _emit_continue()
        return

    try:
        if hook_event == "SessionStart":
            _handle_session_start(event, _BACKEND)
        elif hook_event == "PostToolUse":
            _handle_post_tool_use(event, _BACKEND)
        elif hook_event in ("Stop", "SubagentStop"):
            # Capture the last PM turn exactly ONCE per Stop event, before the
            # per-backend loop in _handle_session_end.  _capture_pm_turn_on_stop
            # was previously called inside _handle_session_end, which meant it
            # ran once per active backend — writing the state file N times on
            # Stop events when N backends (e.g. trusty + kuzu) are both enabled.
            # We use _BACKEND's key here because _BACKEND is the single selected
            # backend (the first available one), and qa_pairs capture is gated on
            # that backend's config.  If the user disables qa_pairs for that
            # backend, capture is skipped — consistent with how it worked before.
            _capture_pm_turn_on_stop(event, _BACKEND.name.replace("-", "_"))
            _handle_session_end(event, _BACKEND)
        # All other events: no-op
    except Exception:
        # Defense in depth — never let an unhandled exception break Claude.
        pass

    _emit_continue()


def get_active_backend_name() -> str:
    """Public helper for the doctor command: returns active backend or 'none'."""
    return _BACKEND.name if _BACKEND is not None else "none"


if __name__ == "__main__":
    main()
