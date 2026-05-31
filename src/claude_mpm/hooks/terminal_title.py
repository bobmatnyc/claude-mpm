"""Terminal title generation for Claude MPM hook events.

Provides the following public API:

1. ``distill_title(event, max_length)`` — extracts a short human-readable
   title from a PostToolUse (or Stop) hook event payload.

2. ``build_osc_sequence(title)`` — wraps the title in an OSC 0 escape
   sequence (sets both icon name and window/tab title) suitable for the
   ``terminalSequence`` field of a Claude Code hook response.

3. ``is_enabled()`` — returns True when ``CLAUDE_MPM_TERMINAL_TITLE`` is
   set to a truthy value (``true``, ``1``, ``yes``, ``on``).

4. ``get_max_length()`` — returns the configured maximum title length from
   ``CLAUDE_MPM_TERMINAL_TITLE_MAX_LEN`` (default 60).

5. ``get_trigger_tools()`` — returns the frozenset of tool names that
   should trigger a title update, read from
   ``CLAUDE_MPM_TERMINAL_TITLE_EVENTS`` (default ``TodoWrite,ExitPlanMode``).

WHY OSC 0:
- OSC 0  ``\\033]0;<text>\\007``  sets both the *icon name* and the
  *window title*, which is what most terminal emulators display as the
  tab label.  It is on the Claude Code allowlist.
- We could emit OSC 2 (window title only) but OSC 0 gives broader
  terminal support with no downside.

WHY distillation over raw text:
- Hook event payloads can be large; we only want 1-2 meaningful words in
  the tab title so it is scannable at a glance.
- The distillation heuristic uses the tool name and a brief excerpt from
  the first active todo (or the plan description) — enough to answer
  "what is Claude doing right now?" without reading the full payload.

Environment variables:

  CLAUDE_MPM_TERMINAL_TITLE
      Enable the feature (``true`` / ``1`` / ``yes`` / ``on``).
      Default: disabled.

  CLAUDE_MPM_TERMINAL_TITLE_MAX_LEN
      Maximum characters for the distilled title.  Default: 60.

  CLAUDE_MPM_TERMINAL_TITLE_EVENTS
      Comma-separated list of tool names that trigger a title update.
      Default: ``TodoWrite,ExitPlanMode``.

No external dependencies — only stdlib.  Safe to import in hot-path hook
subprocesses.
"""

from __future__ import annotations

import os
import re

# ---------------------------------------------------------------------------
# Environment variable names
# ---------------------------------------------------------------------------

_ENV_ENABLE = "CLAUDE_MPM_TERMINAL_TITLE"
_ENV_MAX_LEN = "CLAUDE_MPM_TERMINAL_TITLE_MAX_LEN"
_ENV_EVENTS = "CLAUDE_MPM_TERMINAL_TITLE_EVENTS"

# Default trigger tools when CLAUDE_MPM_TERMINAL_TITLE_EVENTS is not set.
_DEFAULT_TRIGGER_TOOLS: frozenset[str] = frozenset({"TodoWrite", "ExitPlanMode"})

# Default maximum title length.
_DEFAULT_MAX_LEN: int = 60

# Truthy values that enable the feature.
_TRUTHY = frozenset({"1", "true", "yes", "on"})


# ---------------------------------------------------------------------------
# Config helpers — read env vars each call (hot-path safe, no state)
# ---------------------------------------------------------------------------


def is_enabled() -> bool:
    """Return True when ``CLAUDE_MPM_TERMINAL_TITLE`` is set to a truthy value.

    Truthy values: ``true``, ``1``, ``yes``, ``on`` (case-insensitive).
    Default (unset): False.
    """
    return os.environ.get(_ENV_ENABLE, "").strip().lower() in _TRUTHY


def get_max_length() -> int:
    """Return the configured maximum title length.

    Read from ``CLAUDE_MPM_TERMINAL_TITLE_MAX_LEN``; defaults to 60.
    Invalid (non-integer) values fall back to the default.
    """
    raw = os.environ.get(_ENV_MAX_LEN, "").strip()
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    return _DEFAULT_MAX_LEN


def get_trigger_tools() -> frozenset[str]:
    """Return the frozenset of tool names that trigger a title update.

    Read from ``CLAUDE_MPM_TERMINAL_TITLE_EVENTS`` as a comma-separated list.
    Default when unset: ``frozenset({"TodoWrite", "ExitPlanMode"})``.
    """
    raw = os.environ.get(_ENV_EVENTS, "").strip()
    if raw:
        return frozenset(t.strip() for t in raw.split(",") if t.strip())
    return _DEFAULT_TRIGGER_TOOLS


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def distill_title(event: dict, max_length: int = _DEFAULT_MAX_LEN) -> str:
    """Derive a short display title from a Claude Code hook event.

    Preference order (first non-empty result wins):

    1. ``tool_input.plan_description`` — set by TodoWrite when exiting plan
       mode (ExitPlanMode matcher).
    2. First in-progress todo title from ``tool_input.todos``.
    3. First todo title from ``tool_input.todos`` (any status).
    4. The tool name combined with a brief excerpt from the first todo
       content or tool-input path/command.
    5. Plain tool name.

    The result is truncated to *max_length* characters (ellipsis appended).

    Args:
        event: Raw Claude Code PostToolUse hook event dict.
        max_length: Maximum characters in the returned title.  Default 60.

    Returns:
        A non-empty string suitable for use as a terminal tab title.
    """
    tool_name: str = event.get("tool_name", "")
    tool_input: object = event.get("tool_input", {})
    if not isinstance(tool_input, dict):
        tool_input = {}

    # --- Candidate 1: explicit plan_description field ---
    plan_desc: str = str(tool_input.get("plan_description", "") or "").strip()
    if plan_desc:
        return _truncate(plan_desc, max_length)

    # --- Candidate 2 & 3: todos list ---
    todos: object = tool_input.get("todos")
    if isinstance(todos, list) and todos:
        # Prefer in-progress todos
        for todo in todos:
            if isinstance(todo, dict) and todo.get("status") == "in_progress":
                title = _extract_todo_title(todo)
                if title:
                    return _truncate(title, max_length)

        # Fall back to first todo regardless of status
        for todo in todos:
            if isinstance(todo, dict):
                title = _extract_todo_title(todo)
                if title:
                    return _truncate(title, max_length)

    # --- Candidate 4: tool name + brief context ---
    if tool_name:
        context = _extract_tool_context(tool_name, tool_input)
        if context:
            combined = f"{tool_name}: {context}"
            return _truncate(combined, max_length)

    # --- Candidate 5: bare tool name ---
    if tool_name:
        return _truncate(tool_name, max_length)

    return "Claude"


def build_osc_sequence(title: str) -> str:
    """Wrap *title* in an OSC 0 terminal escape sequence.

    The sequence is:  ESC ] 0 ; <title> BEL

    This sets both the *icon name* and *window/tab title* in ANSI-compatible
    terminals (xterm, iTerm2, WezTerm, Ghostty, Windows Terminal, …).

    The title is sanitised before embedding: control characters and the OSC
    string-terminator characters (``\\007`` / ``\\033\\\\``) are stripped.

    Args:
        title: Human-readable title string.

    Returns:
        A string containing the full OSC 0 escape sequence ready to place in
        the ``terminalSequence`` JSON field of a Claude Code hook response.
    """
    safe = _sanitise_title(title)
    # ESC ] 0 ; <title> BEL
    return f"\033]0;{safe}\007"


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _extract_todo_title(todo: dict) -> str:
    """Extract the most useful label from a single todo item dict."""
    # Prefer a dedicated ``title`` field
    title: str = str(todo.get("title", "") or "").strip()
    if title:
        return title

    # Fall back to the ``content`` field (first sentence / line)
    content: str = str(todo.get("content", "") or "").strip()
    if content:
        # Take only the first line / sentence
        first_line = content.split("\n", maxsplit=1)[0].split(".")[0].strip()
        return first_line or content

    return ""


def _extract_tool_context(tool_name: str, tool_input: dict) -> str:
    """Extract a brief context string from the tool_input for common tools."""
    if tool_name in ("Write", "Edit", "MultiEdit", "Read", "Glob", "LS"):
        path: str = str(tool_input.get("path", "") or "").strip()
        if path:
            # Show only the last two path components
            parts = path.replace("\\", "/").rstrip("/").split("/")
            return "/".join(parts[-2:]) if len(parts) >= 2 else parts[-1]

    if tool_name == "Bash":
        cmd: str = str(tool_input.get("command", "") or "").strip()
        if cmd:
            # First word (the executable) is most meaningful
            first_word = cmd.split(maxsplit=1)[0] if cmd.split() else cmd
            return first_word[:40]

    if tool_name == "Task":
        desc: str = str(
            tool_input.get("description", "") or tool_input.get("prompt", "") or ""
        ).strip()
        if desc:
            return desc[:50]

    return ""


def _sanitise_title(title: str) -> str:
    """Remove characters unsafe to embed in an OSC sequence."""
    # Strip control characters (U+0000-U+001F, U+007F) that could terminate
    # the sequence prematurely or alter terminal state.
    return re.sub(r"[\x00-\x1f\x7f]", "", title)


def _truncate(text: str, max_length: int) -> str:
    """Truncate *text* to *max_length* chars, appending '…' when cut."""
    text = text.strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - 1] + "…"  # U+2026 HORIZONTAL ELLIPSIS
