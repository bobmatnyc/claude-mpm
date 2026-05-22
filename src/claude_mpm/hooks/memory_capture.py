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
"""

from __future__ import annotations

import json
import re
import select
import shutil
import subprocess  # nosec B404
import sys
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

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
        kuzu_memory.enabled: bool (default True)
        kuzu_memory.palace: str (unused, kuzu has no palace concept)
        kuzu_memory.capture.*: same shape as trusty_memory.capture
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
                for key in ("content", "fact", "memory", "text", "value"):
                    candidate = entry.get(key)
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
    Store path attempts a POST to ``/api/v1/palaces/<palace>/memories``;
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
            url = f"{base}/api/v1/palaces/{palace}/memories"
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


def _handle_session_end(
    event: dict[str, Any], backend: AbstractMemoryCaptureBackend
) -> None:
    if not _capture_enabled(backend.name.replace("-", "_"), "session_end"):
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
      * Skip short prompts (< ``_PROMPT_MIN_WORDS`` words) — likely
        clarifications, not real intents worth remembering.
      * Skip when no backend is selected.
      * Recall using the first ``_PROMPT_QUERY_MAX_CHARS`` chars of the prompt.
      * Capture is fire-and-forget on a daemon thread so the hook returns
        immediately (recall result is the user-visible value).
      * Inject recalled context as ``additionalContext`` via
        ``hookSpecificOutput`` when there are any results.
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
    if len(prompt.split()) < _PROMPT_MIN_WORDS:
        return result

    backend = _BACKEND
    backend_key = backend.name.replace("-", "_")

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
        import threading

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
    """Read one Claude Code hook event from stdin and dispatch to backend."""
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
