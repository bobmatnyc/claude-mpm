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
import tempfile
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
      one canonical footer line (the first occurrence is rewritten to the
      canonical footer; all subsequent matches are removed).
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

# Regex to extract the --body / -b flag and its value from a shell command.
#
# Design notes
# ------------
# Group 1 (flag):  the flag token — ``--body`` or ``-b``.
# Group 2 (sep):   separator between flag and value — ``=`` or one-or-more spaces.
# Group 3 (quote): the opening quote character (``"`` or ``'``), or empty string
#                  when the value is bare/unquoted.
# Group 4 (dq):    double-quoted value (group 3 == ``"``).
# Group 5 (sq):    single-quoted value (group 3 == ``'``).
# Group 6 (bare):  bare unquoted value (group 3 == ``""``).
#
# Correctness constraints
# -----------------------
# * ``--body-file`` must NOT match as ``--body``:  the ``(?!-file)``
#   look-ahead on ``--body`` prevents this.
# * ``-b`` must only match as a standalone flag, NOT as a prefix of longer
#   tokens such as ``-base`` or ``-branch``:
#     - Requires a preceding word boundary (start-of-string or whitespace).
#     - Requires the character after ``-b`` to be ``=``, whitespace, or
#       end-of-string — i.e. ``(?=\s|=|$)``.
# * Reconstruction (see _requote / rewrite_bash_command) rebuilds the flag
#   text purely from the captured groups so it never relies on searching for
#   the old value string inside the original flag text.
#
# Why not shlex.split (item 3 evaluation)
# ----------------------------------------
# shlex.split correctly tokenises the shell command but loses byte-position
# information, making it impossible to perform a targeted substitution back
# into the original string without re-quoting and reconstructing the entire
# command from scratch — which risks losing formatting, multi-line literals,
# and heredoc constructs that the regex approach preserves.  For the one
# realistic failure mode (``--body`` text appearing in *another* flag's
# value), the existing ``count=1`` constraint already prevents accidental
# re-matching after the first substitution.  A shlex-based path would be
# safer in pathological edge cases but would regress on the quoting
# round-trip tests (``TestRewriteBashCommandFix3``).  Tradeoff accepted.
_BODY_FLAG_RE = re.compile(
    r"""((?:--body(?!-file)|(?:(?:^|\s))-b(?=[\s=]|$)))"""  # group 1: flag token
    r"""(\s*=\s*|\s+)"""  # group 2: separator
    r"""("((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)'|(\S+))""",  # groups 3-6: quoted or bare value
    re.MULTILINE,
)

# Regex to extract the value of --body-file / -F.
_BODY_FILE_FLAG_RE = re.compile(
    r"""(?:--body-file|-F)\s+(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)'|(\S+))"""
)


def _is_gh_body_command(command: str) -> bool:
    """Return True if *command* is a gh pr/issue create/edit invocation."""
    return bool(_GH_BODY_CMD_RE.search(command))


def _extract_body_inline(
    command: str,
) -> tuple[str, re.Match] | None:  # type: ignore[type-arg]
    """Extract the inline body value from a ``--body``/``-b`` flag.

    Returns ``(decoded_value, match)`` where *decoded_value* is the unquoted
    body string and *match* is the regex ``re.Match`` object (used for
    precise, group-based reconstruction), or None if no inline body flag
    was found.

    The match groups are:
      group(1)  — flag token (``--body`` or ``-b`` with surrounding whitespace)
      group(2)  — separator (``=`` or spaces)
      group(3)  — full quoted-or-bare value token including quotes
      group(4)  — inner text when double-quoted (or None)
      group(5)  — inner text when single-quoted (or None)
      group(6)  — bare unquoted value (or None)
    """
    m = _BODY_FLAG_RE.search(command)
    if not m:
        return None
    # Exactly one of groups 4, 5, 6 is set.
    value = (
        m.group(4)
        if m.group(4) is not None
        else (m.group(5) if m.group(5) is not None else (m.group(6) or ""))
    )
    return value, m


def _extract_body_file(command: str) -> str | None:
    """Extract the file path from a ``--body-file``/``-F`` flag, or None."""
    m = _BODY_FILE_FLAG_RE.search(command)
    if not m:
        return None
    return m.group(1) or m.group(2) or m.group(3) or None


def _requote(value: str, quote_char: str) -> str:
    """Re-wrap *value* using the quoting style captured from the original flag.

    *quote_char* is the opening quote character found in the original command
    (``"`` for double-quoted, ``'`` for single-quoted, ``""`` for bare/unquoted).
    This is read directly from the regex match group — it is never inferred by
    searching the old value string inside the flag text, which avoids false
    matches when the old body appears elsewhere in the command.

    Rules:
    - Double-quoted → keep double-quoted, escaping backslashes and embedded ``"``.
    - Single-quoted → keep single-quoted (shell semantics: no escaping inside
      single quotes, but we must ensure the value contains no literal ``'``; if
      it does, fall back to double-quoting to avoid shell syntax breakage).
    - Bare / unquoted → stay bare if safe (no spaces, newlines, or ``"``);
      otherwise wrap in double quotes.
    """
    if quote_char == '"':
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if quote_char == "'":
        if "'" not in value:
            return f"'{value}'"
        # Value contains a single quote — cannot stay single-quoted safely;
        # fall back to double quotes with proper escaping.
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    # Bare / no quote char — add double quotes only if value requires them.
    if " " in value or "\n" in value or '"' in value or "'" in value:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def rewrite_bash_command(command: str) -> str | None:
    """Rewrite a Bash command string so any old footer in the body is canonical.

    WHAT: Parses ``--body``/``-b`` (inline) and ``--body-file``/``-F`` (file)
          flags from a ``gh pr/issue create/edit`` command, rewrites any old
          Claude Code footer in the body to the MPM canonical footer, and
          returns the modified command string.  For file-based bodies, the file
          is rewritten in place and the command string is returned unchanged.
    WHY:  This function is the single point where Bash-command bodies are
          normalised; it must be robust against edge cases (empty values,
          multi-line bodies, the old footer text appearing in other flags such
          as ``--title``) so that the hook never corrupts legitimate commands.
          Reconstruction uses regex match groups exclusively — never string
          search on the old value — to avoid false matches.

    Returns the rewritten command string, or None if no rewrite was needed
    (already canonical, no footer found, or not a gh body command).
    Fail-safe: any unexpected exception is caught; None is returned so the
    original command is used unmodified.
    """
    try:
        if not _is_gh_body_command(command):
            return None

        # Try inline --body / -b first.
        extracted = _extract_body_inline(command)
        if extracted is not None:
            body_value, match = extracted
            new_body = rewrite_footer(body_value)
            if new_body == body_value:
                return None  # already canonical or no footer

            # Determine the quote char from the original flag's structure.
            # group(3) is the full value token (with quotes); the first char
            # of group(3) is the opening quote (``"`` or ``'``) or the first
            # char of a bare value (no quote).
            value_token = match.group(3) or ""
            opening_char = value_token[:1] if value_token else ""
            quote_char = opening_char if opening_char in ('"', "'") else ""

            # Build the replacement text from match groups so the substitution
            # is anchored to exactly this match position.  We preserve group(1)
            # (the flag token, including any leading whitespace captured by the
            # ``(?:^|\s)`` prefix in -b branches) and group(2) (separator).
            flag_tok = match.group(1)  # e.g. " -b" or "--body"
            sep_tok = match.group(2)  # e.g. "=" or " "
            new_quoted = _requote(new_body, quote_char)
            replacement = flag_tok + sep_tok + new_quoted

            # re.sub with count=1 replaces the first (and only) match at the
            # precise position found — never accidentally hits the old footer
            # text that may appear elsewhere in the command (e.g. in --title).
            return _BODY_FLAG_RE.sub(replacement, command, count=1)

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
                # Write atomically: write to a temp file in the same directory
                # (guarantees same filesystem so Path.replace is atomic), then
                # rename over the target.  Path.write_text is not atomic —
                # a crash mid-write would corrupt the body file.
                #
                # Leak-safety: tmp_path is tracked from the moment the file is
                # created.  A try/finally ensures the temp file is unlinked on
                # any failure path (write error or rename error), so orphaned
                # temp files cannot accumulate.
                dir_path = file_path.parent
                tmp_path: str | None = None
                try:
                    with tempfile.NamedTemporaryFile(
                        mode="w",
                        encoding="utf-8",
                        dir=dir_path,
                        delete=False,
                        suffix=".tmp",
                    ) as tmp:
                        tmp_path = tmp.name
                        tmp.write(new_body)
                    Path(tmp_path).replace(file_path)
                    tmp_path = None  # rename succeeded; nothing to clean up
                finally:
                    if tmp_path is not None:
                        Path(tmp_path).unlink(missing_ok=True)
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
