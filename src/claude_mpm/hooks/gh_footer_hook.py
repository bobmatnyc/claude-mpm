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
- File body (``--body-file``/``-F``): **read-only**.  The hook NEVER writes to
  a caller-owned file; it emits an ``additionalContext`` advisory naming the
  file and the canonical footer so the agent can fix it with its own
  Edit/Write tools (which keeps the harness' file bookkeeping consistent).
- Idempotent: already-canonical MPM footer → no change, no advisory.
- Opt-out: ``{"gh_footer_hook": {"disabled": true}}`` in the settings cascade,
  or the ``CLAUDE_MPM_DISABLE_GH_FOOTER`` environment variable.
- Fail-safe: any parse error, I/O error, or unexpected exception → degrade
  gracefully to ``{"continue": True}`` (NEVER blocks the gh command).
- Only rewrites the single footer line; never touches other body content.

References
----------
LINK: none
"""

from __future__ import annotations

import json
import logging
import os
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
# Opt-out switch (mirrors context_circuit_breaker's settings cascade)
# ---------------------------------------------------------------------------

# Environment variable name for the disable switch (secondary).
_DISABLE_ENV_VAR = "CLAUDE_MPM_DISABLE_GH_FOOTER"

# Config key path inside .claude/settings.json (primary).
# JSON path: {"gh_footer_hook": {"disabled": true}}
_CONFIG_KEY = "gh_footer_hook"
_CONFIG_DISABLED_FIELD = "disabled"

# Values accepted as "truthy" for both the env var and the settings field.
_TRUTHY = ("1", "true", "yes", "on")


def _settings_candidates(cwd: str) -> list[Path]:
    """Return ordered list of settings files to check (highest-priority first)."""
    candidates: list[Path] = []
    if cwd:
        candidates.extend(
            [
                Path(cwd) / ".claude" / "settings.local.json",
                Path(cwd) / ".claude" / "settings.json",
            ]
        )
    candidates.append(Path.home() / ".claude" / "settings.json")
    return candidates


def _is_disabled(cwd: str) -> bool:
    """Return True if the gh footer hook has been explicitly disabled.

    WHAT: Resolves the opt-out switch by consulting the
          ``CLAUDE_MPM_DISABLE_GH_FOOTER`` env var followed by the
          ``gh_footer_hook.disabled`` field in the standard settings cascade
          (.claude/settings.local.json → .claude/settings.json →
          ~/.claude/settings.json).
    WHY:  gh_footer_hook silently rewrites agent-authored PR/issue bodies.
          Every other hook in the live PreToolUse chain has an off-switch;
          without one, a project that legitimately wants Claude Code
          attribution has no way to keep it.

    Checks, in order:
    1. ``CLAUDE_MPM_DISABLE_GH_FOOTER`` env var (any truthy value).
    2. ``gh_footer_hook.disabled`` in .claude/settings.local.json.
    3. ``gh_footer_hook.disabled`` in .claude/settings.json.
    4. ``gh_footer_hook.disabled`` in ~/.claude/settings.json.
    """
    env_val = os.environ.get(_DISABLE_ENV_VAR, "").strip().lower()
    if env_val in _TRUTHY:
        return True

    for settings_path in _settings_candidates(cwd):
        try:
            if not settings_path.is_file():
                continue
            with settings_path.open(encoding="utf-8") as fh:
                data = json.load(fh)
            hook_config = data.get(_CONFIG_KEY)
            if isinstance(hook_config, dict):
                disabled_val = hook_config.get(_CONFIG_DISABLED_FIELD, False)
                if disabled_val is True or str(disabled_val).lower() in _TRUTHY:
                    return True
        except (OSError, json.JSONDecodeError, ValueError):
            continue

    return False


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

# Attribution emoji that may decorate a footer.  ``🤖`` is what Claude Code
# emits; ``👥`` appears in the MPM canonical footer and therefore shows up in
# half-migrated bodies (e.g. someone hand-edited the emoji but not the text).
_ATTRIBUTION_EMOJI = "🤖👥"

# A "run" of attribution emoji: one or more of them in any order/repetition,
# with optional horizontal whitespace between/after them.  ``[^\S\r\n]``
# deliberately excludes newlines so a run can never span a line break.
_EMOJI_RUN = r"(?:[" + _ATTRIBUTION_EMOJI + r"][^\S\r\n]*)+"

# Compiled pattern that matches either old footer together with any stale
# attribution emoji attached to it.
#
# Two — and ONLY two — emoji placements are consumed:
#   (a) an emoji run immediately preceding the footer text on the SAME line
#       (``🤖👥 Generated with ...``, ``👥 Generated with ...``);
#   (b) a whole preceding line whose entire non-newline content is an emoji
#       run (``🤖\nGenerated with ...``, ``🤖👥\nGenerated with ...``).
#
# Why the shape is this narrow
# ----------------------------
# The previous pattern only consumed a bare adjacent ``🤖``.  Anything else —
# ``👥``, ``🤖👥``, or an emoji on the preceding line — was left behind, so the
# canonical replacement (which starts with ``🤖👥``) produced a DUPLICATED
# prefix such as ``🤖👥🤖👥 Generated with [Claude MPM](...)``.
#
# The obvious "just strip across the preceding line break" fix is WRONG: a body
# containing prose such as ``🤖 indicates an automated build step\nGenerated
# with [Claude Code](...)`` would lose the entire sentence.  Requiring the
# preceding line to consist *solely* of an emoji run (anchored with ``^`` under
# re.MULTILINE and terminated by ``\r?\n``) keeps that prose intact.
_FOOTER_LINE_RE = re.compile(
    r"(?:^[^\S\r\n]*" + _EMOJI_RUN + r"\r?\n)?"  # (b) emoji-only preceding line
    r"[^\S\r\n]*"  # leading whitespace on the footer line
    r"(?:" + _EMOJI_RUN + r")?"  # (a) same-line emoji run
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
#
# Flag-form coverage (fix 3B)
# ---------------------------
# ``--body VALUE``, ``--body=VALUE``, ``-b VALUE`` and ``-b=VALUE`` are all
# matched via the ``(\s*=\s*|\s+)`` separator group.
#
# The GLUED short form ``-bVALUE`` is deliberately NOT supported.  ``gh pr
# create`` accepts single-dash long-ish tokens in the wild (e.g. a user typing
# ``-base main``), and allowing a glued ``-b`` would parse ``-base`` as
# ``-b`` + ``ase`` and corrupt the command.  The false-positive risk outweighs
# the coverage gain, so ``-b`` keeps its ``(?=[\s=]|$)`` boundary assertion.
_BODY_FLAG_RE = re.compile(
    r"""((?:--body(?!-file)|(?:(?:^|\s))-b(?=[\s=]|$)))"""  # group 1: flag token
    r"""(\s*=\s*|\s+)"""  # group 2: separator
    r"""("((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)'|(\S+))""",  # groups 3-6: quoted or bare value
    re.MULTILINE,
)

# Regex to extract the value of --body-file / -F.
#
# Flag-form coverage (fix 3B)
# ---------------------------
# Previously this required ``\s+`` between the flag and its value, so
# ``--body-file=path``, ``-F=path`` and ``-Fpath`` bypassed the hook entirely
# even though ``gh`` (pflag) accepts all three.  The separator is now
# ``(?:\s*=\s*|\s+)`` for the long form and ``(?:\s*=\s*|\s*)`` for ``-F``,
# the trailing ``\s*`` branch covering the glued ``-Fpath`` spelling.
#
# Unlike ``-b`` (see above) the glued ``-F`` form is safe to support: ``gh``
# has no other single-dash flag beginning with ``F``, so ``-Fxxx`` is
# unambiguous.  The leading ``(?:^|\s)`` keeps ``-F`` from matching inside a
# longer token such as ``--body-file``.
_BODY_FILE_FLAG_RE = re.compile(
    r"""(?:^|\s)"""
    r"""(?:--body-file(?:\s*=\s*|\s+)|-F(?:\s*=\s*|\s*))"""
    r"""(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)'|(\S+))"""
)

# ``--body-file -`` / ``-F -`` means "read the body from stdin".  There is no
# file on disk to inspect, and treating it as a path is actively dangerous:
# ``Path('-')`` resolves to a real file named ``-`` if one happens to exist in
# the working directory.  Recognised and skipped explicitly, before any read.
_STDIN_BODY_FILE = "-"


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
    """Extract the file path from a ``--body-file``/``-F`` flag, or None.

    Returns None when the flag is absent, when no value could be parsed, or
    when the value is ``-`` (stdin) — see ``_STDIN_BODY_FILE``.
    """
    m = _BODY_FILE_FLAG_RE.search(command)
    if not m:
        return None
    value = m.group(1) or m.group(2) or m.group(3) or None
    if value is None:
        return None
    if value == _STDIN_BODY_FILE:
        # "read the body from stdin" — not a path.  Bail out BEFORE any
        # filesystem access so a stray file literally named "-" in the working
        # directory can never be read or reported on.
        logger.debug("gh_footer_hook: --body-file - (stdin) — skipping")
        return None
    return value


# Characters that are safe to leave completely unquoted in a POSIX shell word.
# Mirrors the conservative set used by shlex.quote.
_BARE_SAFE_RE = re.compile(r"^[\w@%+=:,./-]+$", re.ASCII)


def _single_quote(value: str) -> str:
    r"""Wrap *value* in single quotes using the POSIX ``'\''`` splice idiom.

    Inside single quotes the shell performs NO expansion at all, so ``$``,
    backticks, ``\``, ``"`` and newlines are all inert.  A literal single quote
    cannot appear inside single quotes, so it is spliced out and back in as
    ``'\''`` (close quote, escaped quote, reopen quote) — the standard,
    universally portable idiom.
    """
    return "'" + value.replace("'", r"'\''") + "'"


def _requote(value: str, quote_char: str) -> str:
    """Re-wrap *value* using the quoting style captured from the original flag.

    *quote_char* is the opening quote character found in the original command
    (``"`` for double-quoted, ``'`` for single-quoted, ``""`` for bare/unquoted).
    This is read directly from the regex match group — it is never inferred by
    searching the old value string inside the flag text, which avoids false
    matches when the old body appears elsewhere in the command.

    Rules:
    - Double-quoted → keep double-quoted, escaping backslashes and embedded ``"``.
      ``$`` and backticks are deliberately NOT escaped here: they were already
      live in the caller's original double-quoted argument, so escaping them
      would silently change the command's meaning.
    - Single-quoted → STAY single-quoted, always, using the ``'\\''`` splice
      idiom (fix 3C).  The previous implementation downgraded values containing
      a literal ``'`` to double quotes, which turned inert ``$VAR`` and
      ``` `cmd` ``` text inside the body into live shell expansion/command
      substitution.  Single quotes never expand anything, so no shell
      metacharacter can ever escape.
    - Bare / unquoted → stay bare only when every character is in the
      conservative shell-safe set; otherwise single-quote it (again, never
      double quotes, so ``$``/backticks stay inert).
    """
    if quote_char == '"':
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if quote_char == "'":
        return _single_quote(value)
    # Bare / no quote char — stay bare only when unambiguously safe.
    if value and _BARE_SAFE_RE.match(value):
        return value
    return _single_quote(value)


def rewrite_bash_command(command: str) -> str | None:
    """Rewrite a Bash command string so any old footer in the body is canonical.

    WHAT: Parses the ``--body``/``-b`` (inline) flag from a ``gh pr/issue
          create/edit`` command, rewrites any old Claude Code footer in the
          body to the MPM canonical footer, and returns the modified command
          string.  File-based bodies (``--body-file``/``-F``) are NOT handled
          here — see ``build_body_file_advisory``.
    WHY:  This function is the single point where Bash-command bodies are
          normalised; it must be robust against edge cases (empty values,
          multi-line bodies, the old footer text appearing in other flags such
          as ``--title``) so that the hook never corrupts legitimate commands.
          Reconstruction uses regex match groups exclusively — never string
          search on the old value — to avoid false matches.

    Returns the rewritten command string, or None if no rewrite was needed
    (already canonical, no footer found, not a gh body command, or the
    quoting could not be parsed with confidence).
    Fail-safe: any unexpected exception is caught; None is returned so the
    original command is used unmodified.
    """
    try:
        if not _is_gh_body_command(command):
            return None

        # Try inline --body / -b.
        extracted = _extract_body_inline(command)
        if extracted is not None:
            body_value, match = extracted

            # Parser-confidence guard (fix 3C, related gap).
            #
            # ``_BODY_FLAG_RE`` models a quoted value as a single balanced
            # quote pair.  A shell word may instead be a CONCATENATION of
            # adjacent quoted/bare chunks — most commonly the POSIX splice
            # idiom ``'It'\''s'`` used to embed a literal apostrophe inside a
            # single-quoted string.  In that case the regex stops at the first
            # closing quote and captures only a PREFIX of the real body.
            #
            # Rewriting from a prefix would splice the canonical footer into
            # the middle of a shell word and leave the tail (``\''s'``)
            # dangling — a corrupted command.  We cannot parse the full word
            # without replacing the whole regex approach with a shell
            # tokeniser (see "Why not shlex.split" above), so instead we detect
            # the situation and stand down: if the value token is not followed
            # by whitespace or end-of-string, the parse is untrustworthy and we
            # return None, leaving the command exactly as the agent wrote it.
            #
            # KNOWN LIMITATION: a body that uses the ``'\''`` idiom AND carries
            # a stale Claude Code footer is therefore left un-normalised rather
            # than corrupted.  This is a deliberate correctness-over-coverage
            # tradeoff; see ``test_splice_quoted_body_is_left_alone``.
            trailing = command[match.end() : match.end() + 1]
            if trailing and not trailing.isspace():
                logger.debug(
                    "gh_footer_hook: body value token not followed by whitespace "
                    "(concatenated shell word?) — standing down"
                )
                return None

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

        # --body-file / -F is intentionally NOT handled here: the hook must
        # never mutate a caller-owned file.  See build_body_file_advisory.
        return None  # no inline --body flag found
    except Exception as exc:
        logger.debug("gh_footer_hook: rewrite_bash_command error (degrading): %s", exc)
        return None


# Template for the advisory surfaced to the agent when a ``--body-file``
# target still carries a stale Claude Code footer.
_BODY_FILE_ADVISORY = (
    "[claude-mpm] The body file '{path}' passed to this gh command still "
    "contains a Claude Code attribution footer. claude-mpm does not edit "
    "agent-owned files, so please update it yourself with Edit/Write before "
    "(re-)running the command, replacing the footer line with exactly:\n"
    "{footer}"
)


def build_body_file_advisory(command: str) -> str | None:
    """Return an advisory message if a ``--body-file`` target has a stale footer.

    WHAT: Reads (read-only!) the file named by ``--body-file``/``-F`` and, if
          its contents would be changed by ``rewrite_footer``, returns a
          human-readable advisory naming the file and the canonical footer.
          Returns None in every other case.
    WHY:  The previous implementation rewrote the body file IN PLACE from
          inside a PreToolUse hook.  That silently mutated a file the calling
          agent owns, outside all Edit/Write tool bookkeeping — the agent's
          view of the file diverged from disk, and the change was invisible in
          the transcript.  Surfacing an advisory instead keeps the hook
          side-effect-free and lets the agent make the edit through its own
          tools, so the mutation stays visible and attributable.

    Fail-safe: any I/O error or unexpected exception yields None.
    """
    try:
        if not _is_gh_body_command(command):
            return None
        file_path_str = _extract_body_file(command)
        if file_path_str is None:
            return None
        file_path = Path(file_path_str)
        try:
            original_body = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            logger.debug("gh_footer_hook: cannot read body file %s: %s", file_path, exc)
            return None
        if rewrite_footer(original_body) == original_body:
            return None
        return _BODY_FILE_ADVISORY.format(
            path=file_path_str, footer=MPM_FOOTER_CANONICAL
        )
    except Exception as exc:
        logger.debug(
            "gh_footer_hook: build_body_file_advisory error (degrading): %s", exc
        )
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

    WHAT: Wraps rewrite_bash_command / build_body_file_advisory /
          rewrite_mcp_body and formats the result as a Claude Code PreToolUse
          wire-format response dict.
    WHY:  Single callable that the pretooluse_dispatcher and tool_handler can
          both call without duplicating the response-envelope logic.  It is
          also the single choke point for the opt-out switch, so disabling the
          hook is guaranteed to short-circuit EVERY tool path.

    Returns:
        ``{"hookSpecificOutput": {"hookEventName": "PreToolUse",
            "updatedInput": <modified tool_input>}}``  when a rewrite occurs.
        ``{"hookSpecificOutput": {"hookEventName": "PreToolUse",
            "additionalContext": <advisory>}}``  when a ``--body-file`` target
            carries a stale footer (advisory only — nothing is written).
        ``{"continue": True}``  when no rewrite is needed.
        ``{"continue": True}``  on any error (fail-safe).
    """
    try:
        if _is_disabled(event.get("cwd", "") or ""):
            return {"continue": True}

        tool_name: str = event.get("tool_name", "")
        tool_input: dict[str, Any] = event.get("tool_input", {}) or {}

        if tool_name == "Bash":
            command: str = tool_input.get("command", "")
            if not isinstance(command, str) or not command.strip():
                return {"continue": True}
            new_command = rewrite_bash_command(command)
            # Only emit updatedInput when the command text ACTUALLY changed —
            # a byte-identical "update" is pure bookkeeping noise for the
            # harness and misrepresents the hook as having rewritten something.
            if new_command is not None and new_command != command:
                updated_input = dict(tool_input)
                updated_input["command"] = new_command
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "updatedInput": updated_input,
                    }
                }
            # No inline rewrite — check for a stale footer in a --body-file
            # target and surface it as advice.  Read-only: the hook never
            # touches a file the calling agent owns.
            advisory = build_body_file_advisory(command)
            if advisory is not None:
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "additionalContext": advisory,
                    }
                }
            return {"continue": True}

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
