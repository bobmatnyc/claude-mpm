"""PreToolUse hook: rewrite Claude Code attribution footers to Claude MPM in GitHub PR/issue bodies.

WHAT: Intercepts ``gh pr create``, ``gh pr edit``, ``gh issue create``, and
      ``gh issue edit`` Bash commands (and their MCP equivalents) and normalises
      any "Generated with [Claude Code]" footer in the body to the canonical
      "🤖👥 Generated with [Claude MPM]" footer before the command is executed.
WHY:  The version_control agent and other subagents default to the Claude Code
      footer because they have no explicit footer directive.  Without a live
      hook, vanilla Claude Code attribution leaks onto every PR and issue body
      created by a claude-mpm session.

Behaviour contract
------------------
- Intercepts: ``gh pr create``, ``gh pr edit``, ``gh issue create``,
  ``gh issue edit`` Bash commands, plus MCP tool calls
  ``mcp__github__create_pull_request`` and ``mcp__github__create_issue``.
- Inline body (``--body``/``-b``): rewrites in the parsed argument value.
- File body (``--body-file``/``-F``): reads the file, rewrites, writes back.
- Idempotent: already-canonical MPM footer → no change, no spurious write.
- Fail-safe: any parse error, I/O error, or unexpected exception → degrade
  gracefully to ``{"continue": True}`` (NEVER blocks the gh command).
- Only rewrites the single footer line; never touches other body content.

References
----------
LINK: none
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from claude_mpm.hooks.footer_constants import (
    CLAUDE_CODE_FOOTER_OLD,
    CLAUDE_CODE_FOOTER_OLD_ALT,
    MPM_FOOTER_CANONICAL,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Footer rewrite helpers
# ---------------------------------------------------------------------------

# All old-footer patterns we need to catch, ordered longest-first so the
# regex engine matches greedily.  Each pattern is the bare text WITHOUT the
# leading emoji/whitespace — we strip that with a prefix-aware regex below.
_OLD_FOOTER_BARE = [
    CLAUDE_CODE_FOOTER_OLD,
    CLAUDE_CODE_FOOTER_OLD_ALT,
]

# Compiled pattern that matches either old footer, optionally preceded by
# the Claude Code robot emoji and arbitrary surrounding whitespace.
# Group 0 = the full match (emoji + text), stripped and replaced wholesale.
_FOOTER_LINE_RE = re.compile(
    r"[^\S\r\n]*(?:🤖[^\S\r\n]*)?"  # optional leading whitespace + robot emoji
    r"(?:" + "|".join(re.escape(f) for f in _OLD_FOOTER_BARE) + r")"
    r"[^\S\r\n]*",  # trailing whitespace on the line
    re.MULTILINE,
)


def _needs_rewrite(body: str) -> bool:
    """Return True if *body* contains any old Claude Code footer pattern."""
    return bool(_FOOTER_LINE_RE.search(body))


def _already_canonical(body: str) -> bool:
    """Return True if *body* already contains the canonical MPM footer."""
    return MPM_FOOTER_CANONICAL in body


def rewrite_footer(body: str) -> str:
    """Rewrite any old Claude Code footer line(s) to the canonical MPM footer.

    WHAT: Pure string transformation — replaces the old footer line with
          the canonical MPM footer.
    WHY:  Keeping this as a pure function makes it trivially testable and
          reusable outside the hook dispatch path.

    Rules:
    - If the body already contains the canonical MPM footer → return unchanged
      (idempotent, even if an old footer is also present — avoids duplication).
    - If the body contains one or more old-footer lines → replace with exactly
      one canonical footer line (the last occurrence position is used for
      replacement; all additional matches are removed).
    - If neither → return unchanged.
    """
    if _already_canonical(body):
        return body
    if not _needs_rewrite(body):
        return body

    # Replace all old footer occurrences.  The first occurrence becomes the
    # canonical footer; subsequent ones are removed.
    first = True

    def _replacer(m: re.Match) -> str:  # type: ignore[type-arg]
        nonlocal first
        if first:
            first = False
            return MPM_FOOTER_CANONICAL
        return ""

    # Collapse any double blank lines introduced by removing secondary matches.
    return re.sub(r"\n{3,}", "\n\n", _FOOTER_LINE_RE.sub(_replacer, body))


# ---------------------------------------------------------------------------
# Bash command parsing helpers
# ---------------------------------------------------------------------------

# Regex that matches gh commands that operate on PR/issue bodies.
# Deliberately matches across extra whitespace between tokens.
_GH_BODY_CMD_RE = re.compile(
    r"\bgh\s+"
    r"(pr\s+(?:create|edit)|issue\s+(?:create|edit))"
    r"\b",
    re.IGNORECASE,
)

# Regex to extract the value of --body / -b from a shell command string.
# Handles both --body="..." and --body "..." forms (with single or double
# quotes, or bare unquoted values without spaces).
# NOTE: (?!-file) prevents --body-file from being matched as --body.
_BODY_FLAG_RE = re.compile(
    r"""(?:--body(?!-file)|-b(?!ody))\s*=?\s*(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)'|(\S+))"""
)

# Regex to extract the value of --body-file / -F.
_BODY_FILE_FLAG_RE = re.compile(
    r"""(?:--body-file|-F)\s+(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)'|(\S+))"""
)


def _is_gh_body_command(command: str) -> bool:
    """Return True if *command* is a gh pr/issue create/edit invocation."""
    return bool(_GH_BODY_CMD_RE.search(command))


def _extract_body_inline(command: str) -> tuple[str, str] | None:
    """Extract the inline body value from a ``--body``/``-b`` flag.

    Returns ``(raw_value, flag_form)`` where *flag_form* is the matched
    substring (used for replacement), or None if no inline body flag found.
    """
    m = _BODY_FLAG_RE.search(command)
    if not m:
        return None
    # One of the three capture groups will be set.
    value = m.group(1) or m.group(2) or m.group(3) or ""
    return value, m.group(0)


def _extract_body_file(command: str) -> str | None:
    """Extract the file path from a ``--body-file``/``-F`` flag, or None."""
    m = _BODY_FILE_FLAG_RE.search(command)
    if not m:
        return None
    return m.group(1) or m.group(2) or m.group(3) or None


def _requote(value: str, original_flag: str) -> str:
    """Re-wrap *value* in the same quoting style as *original_flag*."""
    if original_flag.endswith(f'"{value}"') or '="' in original_flag:
        return f'"{value}"'
    if original_flag.endswith(f"'{value}'") or "='" in original_flag:
        return f"'{value}'"
    # bare or --body= form — use double quotes if the value needs it
    if " " in value or "\n" in value or '"' in value:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def rewrite_bash_command(command: str) -> str | None:
    """Rewrite a Bash command string so any old footer in the body is canonical.

    Returns the rewritten command string, or None if no rewrite was needed
    (already canonical, no footer found, or not a gh body command).
    Fail-safe: any unexpected exception is caught; None is returned.
    """
    try:
        if not _is_gh_body_command(command):
            return None

        # Try inline --body / -b first.
        extracted = _extract_body_inline(command)
        if extracted is not None:
            body_value, flag_match = extracted
            new_body = rewrite_footer(body_value)
            if new_body == body_value:
                return None  # already canonical or no footer
            # Rebuild the flag with the new body value.
            new_flag = flag_match[: flag_match.index(body_value)] + _requote(
                new_body, flag_match
            )
            # If requote wrapped differently, reconstruct more carefully.
            # Simple approach: replace the first occurrence of the old flag.
            return command.replace(flag_match, new_flag, 1)

        # Try --body-file / -F.
        file_path_str = _extract_body_file(command)
        if file_path_str is not None:
            file_path = Path(file_path_str)
            try:
                original_body = file_path.read_text(encoding="utf-8")
            except OSError as exc:
                logger.debug(
                    "gh_footer_hook: cannot read body file %s: %s", file_path, exc
                )
                return None
            new_body = rewrite_footer(original_body)
            if new_body == original_body:
                return None
            try:
                file_path.write_text(new_body, encoding="utf-8")
            except OSError as exc:
                logger.debug(
                    "gh_footer_hook: cannot write body file %s: %s", file_path, exc
                )
                return None
            # Command string itself is unchanged (file path is the same).
            return command

        return None  # no --body or --body-file flag found
    except Exception as exc:
        logger.debug("gh_footer_hook: rewrite_bash_command error (degrading): %s", exc)
        return None


# ---------------------------------------------------------------------------
# MCP tool helpers
# ---------------------------------------------------------------------------

# MCP tool names that carry a PR/issue body field.
_MCP_BODY_TOOLS = frozenset(
    {
        "mcp__github__create_pull_request",
        "mcp__github__create_issue",
        "mcp__github__update_pull_request",
        "mcp__github__update_issue",
    }
)


def rewrite_mcp_body(
    tool_name: str, tool_input: dict[str, Any]
) -> dict[str, Any] | None:
    """Rewrite the ``body`` field of a GitHub MCP tool call if needed.

    Returns the updated *tool_input* dict with the body rewritten, or None if
    no rewrite was needed or the tool is not a recognised body-carrying MCP
    call.  Fail-safe: returns None on any error.
    """
    try:
        if tool_name not in _MCP_BODY_TOOLS:
            return None
        body = tool_input.get("body")
        if not isinstance(body, str):
            return None
        new_body = rewrite_footer(body)
        if new_body == body:
            return None
        updated = dict(tool_input)
        updated["body"] = new_body
        return updated
    except Exception as exc:
        logger.debug("gh_footer_hook: rewrite_mcp_body error (degrading): %s", exc)
        return None


# ---------------------------------------------------------------------------
# Top-level hook entry point
# ---------------------------------------------------------------------------


def build_gh_footer_response(event: dict[str, Any]) -> dict[str, Any]:
    """Build a PreToolUse hook response that normalises PR/issue body footers.

    WHAT: Wraps rewrite_bash_command / rewrite_mcp_body and formats the result
          as a Claude Code PreToolUse wire-format response dict.
    WHY:  Single callable that the pretooluse_dispatcher and tool_handler can
          both call without duplicating the response-envelope logic.

    Returns:
        ``{"hookSpecificOutput": {"hookEventName": "PreToolUse",
            "updatedInput": <modified tool_input>}}``  when a rewrite occurs.
        ``{"continue": True}``  when no rewrite is needed.
        ``{"continue": True}``  on any error (fail-safe).
    """
    try:
        tool_name: str = event.get("tool_name", "")
        tool_input: dict[str, Any] = event.get("tool_input", {}) or {}

        if tool_name == "Bash":
            command: str = tool_input.get("command", "")
            if not isinstance(command, str) or not command.strip():
                return {"continue": True}
            new_command = rewrite_bash_command(command)
            if new_command is None:
                return {"continue": True}
            updated_input = dict(tool_input)
            updated_input["command"] = new_command
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "updatedInput": updated_input,
                }
            }

        # MCP GitHub tool path
        updated_input = rewrite_mcp_body(tool_name, tool_input)
        if updated_input is None:
            return {"continue": True}
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "updatedInput": updated_input,
            }
        }
    except Exception as exc:
        logger.debug(
            "gh_footer_hook: build_gh_footer_response error (degrading): %s", exc
        )
        return {"continue": True}
