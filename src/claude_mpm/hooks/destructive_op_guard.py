"""PreToolUse guard that denies destructive git/file operations.

WHAT: Inspects ``Bash`` tool calls during ``PreToolUse`` and returns a ``deny``
decision for a small set of irreversible/dangerous operations (force pushes,
hard resets, broad working-tree discards, ``rm -rf`` of project paths, destructive
branch deletion of ``main``/``master``, and ``git clean -f``).

WHY: Issue #420 research (docs/research/defer-hook-evaluation-2026-04-02.md)
concluded that Claude Code's ``defer`` decision does not work in interactive
sessions, so Phase 1 uses ``deny`` to provide real tool-level enforcement for the
highest-blast-radius destructive commands. These operations can silently destroy
uncommitted work or delete source trees with no undo path.

The engine is pure (``evaluate`` returns a simple dict and never raises on bad
input) so it is cheap to unit test; ``main`` renders the Claude Code wire format
and ``tool_handler`` calls ``evaluate`` directly on the hot path.

Fail-open policy
----------------
Anything that is not confidently destructive returns an empty dict (pass-through).
A guard crash or ambiguous parse must never block legitimate work — false denials
are worse than the rare missed denial, since the existing permission policy and
PM-level circuit breakers provide additional layers.

References
----------
SPEC-HOOKS-11~1 : docs/specs/hooks.md#SPEC-HOOKS-11~1
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from typing import Any

# ---------------------------------------------------------------------------
# Override hint shared across all denial messages.
# ---------------------------------------------------------------------------
_OVERRIDE_HINT = (
    "If this is truly intended, run it yourself in a terminal outside the MPM "
    "session (the guard only governs agent-issued tool calls)."
)

# Branch names whose destructive deletion is always blocked.
_PROTECTED_BRANCHES: frozenset[str] = frozenset({"main", "master"})

# rm -rf targets that are blocked: project-critical dirs, project root, and any
# absolute path. Comparison is done on the normalized argument string.
_PROTECTED_RM_TARGETS: frozenset[str] = frozenset(
    {".", "./", "src", "src/", "tests", "tests/", "*"}
)


def _split_commands(command: str) -> list[list[str]]:
    """Tokenize a shell command and split it into separate pipeline segments.

    Why: ``git push ... && git reset --hard`` packs several commands into one
    Bash call; each segment must be inspected independently. We split on the
    common separators (``;``, ``&&``, ``||``, ``|``) at the token level so a
    destructive segment is not hidden behind a benign leading command.

    Returns a list of token lists. Returns ``[]`` when the command cannot be
    tokenized (unbalanced quotes, etc.) so callers fail open.
    """
    # ``shlex`` with ``punctuation_chars`` treats ``;``, ``&``, ``|`` as
    # standalone operator tokens (so ``cmd;next`` splits into ``cmd``, ``;``,
    # ``next``) while still honouring quotes (so separators inside quoted
    # strings stay literal). This is more robust than pre-spacing the raw
    # string, which would corrupt quoted separators.
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return []
    segments: list[list[str]] = []
    current: list[str] = []
    for tok in tokens:
        # punctuation_chars collapses runs, so ``&&`` / ``||`` arrive as one
        # token; single ``;`` ``&`` ``|`` also separate pipeline segments.
        if set(tok) <= {";", "&", "|"} and tok:
            if current:
                segments.append(current)
                current = []
            continue
        current.append(tok)
    if current:
        segments.append(current)
    return segments


def _strip_git_prefix(tokens: list[str]) -> list[str] | None:
    """Return the git sub-command tokens, skipping ``git`` and global flags.

    Why: ``git -C /repo push`` and ``git push`` must be treated identically.
    Returns ``None`` when the segment is not a git invocation.
    """
    if not tokens or tokens[0] != "git":
        return None
    i = 1
    # Skip git global options that take a value (-C <path>, -c <cfg>).
    while i < len(tokens):
        tok = tokens[i]
        if tok in ("-C", "-c", "--namespace", "--git-dir", "--work-tree"):
            i += 2
            continue
        if tok.startswith("-"):
            i += 1
            continue
        break
    return tokens[i:]


def _check_git(tokens: list[str]) -> str | None:
    """Return a denial reason if a git segment is destructive, else ``None``."""
    sub = _strip_git_prefix(tokens)
    if not sub:
        return None
    cmd = sub[0]
    args = sub[1:]

    # git push --force / -f / --force-with-lease
    if cmd == "push":
        for a in args:
            if a in ("--force", "-f") or a.startswith("--force-with-lease"):
                return (
                    "Blocked: 'git push --force' can overwrite remote history and "
                    f"destroy others' commits. {_OVERRIDE_HINT}"
                )
            # Bundled short flags such as -fu.
            if re.fullmatch(r"-[a-eg-zA-Z]*f[a-eg-zA-Z]*", a):
                return (
                    "Blocked: 'git push -f' (force) can overwrite remote history "
                    f"and destroy others' commits. {_OVERRIDE_HINT}"
                )
        return None

    # git reset --hard
    if cmd == "reset" and "--hard" in args:
        return (
            "Blocked: 'git reset --hard' permanently discards uncommitted changes "
            f"and resets the working tree. {_OVERRIDE_HINT}"
        )

    # git checkout -- .  (broad working-tree discard)
    if cmd == "checkout" and "--" in args:
        targets = args[args.index("--") + 1 :]
        if any(t in (".", "./", "*") for t in targets):
            return (
                "Blocked: 'git checkout -- .' discards ALL uncommitted changes in "
                f"the working tree. {_OVERRIDE_HINT}"
            )
        return None

    # git restore .  (broad working-tree discard)
    if cmd == "restore":
        positionals = [a for a in args if not a.startswith("-")]
        if any(p in (".", "./", "*") for p in positionals):
            return (
                "Blocked: 'git restore .' discards ALL uncommitted changes in the "
                f"working tree. {_OVERRIDE_HINT}"
            )
        return None

    # git branch -D main/master  (force-delete protected branch)
    if cmd == "branch":
        force_delete = any(
            a == "-D" or (a.startswith("-") and "D" in a and not a.startswith("--"))
            for a in args
        )
        if force_delete:
            positionals = [a for a in args if not a.startswith("-")]
            if any(b in _PROTECTED_BRANCHES for b in positionals):
                return (
                    "Blocked: force-deleting a protected branch (main/master) with "
                    f"'git branch -D' is destructive. {_OVERRIDE_HINT}"
                )
        return None

    # git clean -f / -fd  (deletes untracked files irreversibly)
    if cmd == "clean":
        for a in args:
            if a.startswith("--force"):
                return (
                    "Blocked: 'git clean --force' permanently deletes untracked "
                    f"files. {_OVERRIDE_HINT}"
                )
            # -f, -fd, -df, -fdx, etc.
            if re.fullmatch(r"-[a-zA-Z]*f[a-zA-Z]*", a):
                return (
                    "Blocked: 'git clean -f' permanently deletes untracked files. "
                    f"{_OVERRIDE_HINT}"
                )
        return None

    return None


def _check_rm(tokens: list[str]) -> str | None:
    """Return a denial reason if an ``rm`` segment is a recursive-force on a
    protected path, else ``None``.

    Blocks ``rm -rf`` (recursive AND force) targeting ``src/``, ``tests/``, the
    project root (``.``), the glob ``*``, or any absolute path. A single-file
    ``rm file.txt`` or non-recursive ``rm`` is allowed.
    """
    if not tokens or tokens[0] != "rm":
        return None
    has_recursive = False
    has_force = False
    targets: list[str] = []
    for a in tokens[1:]:
        if a == "--recursive":
            has_recursive = True
        elif a == "--force":
            has_force = True
        elif a.startswith("--"):
            continue
        elif a.startswith("-"):
            flags = a[1:]
            if "r" in flags or "R" in flags:
                has_recursive = True
            if "f" in flags:
                has_force = True
        else:
            targets.append(a)
    if not (has_recursive and has_force):
        return None
    for t in targets:
        normalized = t.rstrip("/") + "/" if t not in (".", "*") else t
        if (
            t in _PROTECTED_RM_TARGETS
            or normalized in _PROTECTED_RM_TARGETS
            or t.startswith("/")
        ):
            return (
                f"Blocked: 'rm -rf {t}' can irreversibly delete source trees or "
                f"system paths. {_OVERRIDE_HINT}"
            )
    return None


def evaluate(event: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a PreToolUse event and return a deny dict, or ``{}`` to allow.

    Why: Provides the importable hot-path entry called by ``tool_handler`` so no
    extra subprocess is spawned per Bash call.
    What: For ``Bash`` tool calls, tokenizes the command, splits compound
    pipelines, and checks each segment against the git/rm destructive matchers.
    Returns ``{"permissionDecision": "deny", "permissionDecisionReason": ...}``
    on the first match; otherwise ``{}`` (pass-through / fail-open).
    Test: ``evaluate({"tool_name": "Bash", "tool_input": {"command": "git push -f"}})``
    must return a dict whose ``permissionDecision`` is ``"deny"``; a benign
    command like ``"git status"`` must return ``{}``.

    :spec: SPEC-HOOKS-11~1
    """
    if str(event.get("tool_name") or "") != "Bash":
        return {}
    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return {}
    command = str(tool_input.get("command") or "")
    if not command.strip():
        return {}

    for segment in _split_commands(command):
        reason = _check_git(segment) or _check_rm(segment)
        if reason:
            return {"permissionDecision": "deny", "permissionDecisionReason": reason}
    return {}


def main() -> None:
    """Entry point for ``python3 -m claude_mpm.hooks.destructive_op_guard``.

    Why: Allows the guard to be registered as a standalone settings.json hook in
    addition to being called inline by ``tool_handler``.
    What: Reads a hook event from stdin, evaluates it, and prints either a deny
    envelope or a ``{"continue": true}`` pass-through. Any failure fails open.
    Test: Pipe ``{"tool_name":"Bash","tool_input":{"command":"git reset --hard"}}``
    on stdin and assert stdout contains ``"permissionDecision": "deny"``.
    """
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            event = {}
    except Exception:
        print(json.dumps({"continue": True}))
        return

    decision = evaluate(event)
    if decision.get("permissionDecision") == "deny":
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": decision.get(
                            "permissionDecisionReason", ""
                        ),
                    }
                }
            )
        )
        return

    print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
