"""
Migration: Auto-configure MPM statusline at the USER level (v6.2.35, updated v6.3.2).

Operates at ``~/.claude/`` (user-global), NOT ``<project>/.claude/`` (project-scoped).

Ensures that:
1. The statusline script is present at ``~/.claude/hooks/scripts/statusline.sh``
   (creates it if missing; makes it executable; respects user customisation).
2. A ``statusLine`` entry pointing to that script (absolute path) is present in
   ``~/.claude/settings.json`` (adds it if missing; updates an existing
   MPM-owned entry to the new absolute path; leaves user-owned entries alone).
3. A Stop hook entry that calls ``statusline.sh --clear`` is present in
   ``~/.claude/settings.json`` so the bar disappears when Claude Code exits.

Ownership detection for settings entries uses a substring heuristic on the
command field: if the command contains ``statusline.sh`` we treat it as the
MPM-managed entry (whether it points at the old project-relative path or the
new user-level absolute path) and update it; otherwise we leave it alone.

Project-level ``.claude/settings.json`` and ``.claude/hooks/scripts/statusline.sh``
are NEVER written by this migration.  Legacy project-level installs are left
in place — Claude Code's project-overrides-user precedence handles that
correctly — and are cleaned up by the dedicated
``migrate_statusline_user_level`` migration.

Idempotent: safe to run multiple times.

Note (v6.2.36 fix): The script was rewritten to print plain text to stdout
instead of painting via /dev/tty escape sequences.  Claude Code's statusLine
hook renders whatever the script prints to stdout in its built-in status bar;
no cursor positioning is needed or desired.
"""

import json
import logging
import stat
from pathlib import Path

logger = logging.getLogger(__name__)

# Marker line that identifies an MPM-managed statusline.sh.
# Any file containing this string will be treated as an official MPM-owned
# copy and will be overwritten when the template has been updated (force mode).
_MPM_MARKER = "# claude-mpm-managed:"

# Absolute path to the user-level statusline script.  Computed once at import
# time so all defaults reference the same canonical location.
_USER_SCRIPT_PATH = Path.home() / ".claude" / "hooks" / "scripts" / "statusline.sh"

# Command string used in the Stop hook (absolute user-level path).  Matched
# substring-wise via ``_STOP_HOOK_MATCH`` so legacy project-relative
# invocations are still detected as "MPM-owned".
_STOP_HOOK_COMMAND = f"{_USER_SCRIPT_PATH} --clear"
_STOP_HOOK_MATCH = "statusline.sh --clear"

# Substring used to identify an MPM-managed statusLine.command in
# ``settings.json`` regardless of whether the path is relative
# (``.claude/hooks/scripts/statusline.sh`` — legacy project-level installs)
# or absolute (``~/.claude/hooks/scripts/statusline.sh`` — current default).
_STATUSLINE_COMMAND_MATCH = "statusline.sh"

# Statusline script content (byte-identical to .claude/hooks/scripts/statusline.sh
# in this repo so fresh projects receive the same canonical version).
_SCRIPT_CONTENT = r"""#!/bin/bash
# claude-mpm-managed: do not remove this line (used for auto-upgrades)
# claude-mpm status line
#
# Claude Code calls this script periodically via the statusLine hook and
# renders whatever this script prints to stdout in its own built-in status
# bar area at the bottom of the UI.  The script must NOT do any cursor
# positioning or /dev/tty painting — Claude Code owns that rendering.
#
# Usage:
#   statusline.sh           — print status string to stdout
#   statusline.sh --clear   — print empty string (Stop hook, bar goes blank)
#
# JSON context is provided on stdin when Claude Code invokes the script.
#
# Layout:
#   ◆ <user> │ <model> │ <ctx%> ctx │ <cwd> │ <branch> [↑N][↓N] │ style:<outputStyle>

set -u

# --clear mode: output an empty string so Claude Code blanks its status bar.
if [ "${1:-}" = "--clear" ]; then
    printf ''
    exit 0
fi

# ---------------------------------------------------------------------------
# Parse JSON payload from stdin (if any).
# ---------------------------------------------------------------------------
input=""
if [ ! -t 0 ]; then
    input=$(cat)
fi

USER_NAME=$(whoami 2>/dev/null || echo "user")

if [ -n "$input" ] && command -v jq >/dev/null 2>&1; then
    MODEL=$(printf '%s' "$input" | jq -r '.model.display_name // .model.id // "unknown"' 2>/dev/null || echo "unknown")
    # Use // empty so missing fields yield an empty string (not "0"). Claude Code
    # only sends context_window once a session has warmed up, so at session
    # start this field is absent and we want to omit the segment entirely
    # rather than display a misleading "0% ctx".
    REMAINING=$(printf '%s' "$input" | jq -r '.context_window.remaining_percentage // empty' 2>/dev/null | cut -d. -f1)
    CWD=$(printf '%s' "$input" | jq -r '.workspace.current_dir // .workspace.path // .cwd // .session_dir // .project_root // ""' 2>/dev/null)
else
    MODEL="unknown"
    REMAINING=""
    CWD=""
fi

# If JSON didn't provide a CWD, fall back to $PWD env var then pwd command.
if [ -z "$CWD" ]; then
    CWD="${PWD:-$(pwd 2>/dev/null || echo "")}"
fi

# Normalise REMAINING: must be a non-empty, non-negative integer to be shown.
# Empty/null/non-numeric values mean "context info not available" — we'll
# omit the segment entirely below.
case "$REMAINING" in
    ''|*[!0-9]*) REMAINING="" ;;
esac

# ---------------------------------------------------------------------------
# Read outputStyle from ~/.claude/settings.json (requires jq).
# ---------------------------------------------------------------------------
OUTPUT_STYLE=""
if command -v jq >/dev/null 2>&1; then
    OUTPUT_STYLE=$(jq -r '.outputStyle // "default"' "$HOME/.claude/settings.json" 2>/dev/null || echo "default")
    [ "$OUTPUT_STYLE" = "null" ] && OUTPUT_STYLE="default"
fi

# ---------------------------------------------------------------------------
# Claude brand palette (ANSI — Claude Code passes these through).
# ---------------------------------------------------------------------------
ORANGE="\033[38;5;174m"      # accent     #CC785C
AMBER="\033[38;5;223m"       # amber      #f3d5a3
RED="\033[38;5;196m"         # low-context warning
RESET="\033[0m"
DIM="\033[2m"

# Context remaining colour: amber above 20%, red below.
# Only used when REMAINING is a numeric value (segment is otherwise omitted).
CTX_COLOR="$AMBER"
if [ -n "$REMAINING" ] && [ "$REMAINING" -lt 20 ] 2>/dev/null; then
    CTX_COLOR="$RED"
fi

# Separator: orange vertical bar with surrounding spaces.
SEP=" ${ORANGE}│${RESET} "

# ---------------------------------------------------------------------------
# Git info (branch + ahead/behind) if we're inside a repo.
# ---------------------------------------------------------------------------
GIT_SEGMENT=""
if [ -n "$CWD" ] && command -v git >/dev/null 2>&1 \
   && git -C "$CWD" rev-parse --git-dir >/dev/null 2>&1; then
    BRANCH=$(git -C "$CWD" rev-parse --abbrev-ref HEAD 2>/dev/null)
    if [ -n "$BRANCH" ]; then
        AHEAD_BEHIND=$(git -C "$CWD" rev-list --left-right --count @{upstream}...HEAD 2>/dev/null)
        AHEAD_STR=""
        BEHIND_STR=""
        if [ -n "$AHEAD_BEHIND" ]; then
            BEHIND=$(echo "$AHEAD_BEHIND" | awk '{print $1}')
            AHEAD=$(echo "$AHEAD_BEHIND"  | awk '{print $2}')
            [ "${AHEAD:-0}"  -gt 0 ] 2>/dev/null && AHEAD_STR=" ↑${AHEAD}"
            [ "${BEHIND:-0}" -gt 0 ] 2>/dev/null && BEHIND_STR=" ↓${BEHIND}"
        fi
        GIT_SEGMENT="${AMBER}${BRANCH}${AHEAD_STR}${BEHIND_STR}${RESET}"
    fi
fi

# ---------------------------------------------------------------------------
# CWD segment: shorten path, colour amber.
# ---------------------------------------------------------------------------
CWD_SEGMENT=""
RAW_CWD="${CWD:-$(pwd 2>/dev/null || echo "")}"
case "$RAW_CWD" in
    "$HOME"*) SHORT_CWD="~${RAW_CWD#"$HOME"}" ;;
    *)        SHORT_CWD="$RAW_CWD" ;;
esac
if [ "${#SHORT_CWD}" -gt 40 ]; then
    SHORT_CWD="…$(printf '%s' "$SHORT_CWD" | awk '{ print substr($0, length($0)-38) }')"
fi
if [ -n "$SHORT_CWD" ]; then
    CWD_SEGMENT="${SEP}${AMBER}${SHORT_CWD}${RESET}"
fi

# ---------------------------------------------------------------------------
# outputStyle segment (dimmed). Omitted when jq unavailable.
# ---------------------------------------------------------------------------
STYLE_SEGMENT=""
if [ -n "$OUTPUT_STYLE" ]; then
    STYLE_SEGMENT="${SEP}${DIM}style:${OUTPUT_STYLE}${RESET}"
fi

# ---------------------------------------------------------------------------
# Compose and print the status string to stdout.
# Claude Code renders this in its built-in status bar — no cursor escapes.
# ---------------------------------------------------------------------------
# Base: ◆ <user> │ <model>
STATUS=$(printf "◆ %s%b%b%s%b" \
    "${USER_NAME}" \
    "${SEP}" \
    "${ORANGE}" "${MODEL}" "${RESET}")

# Context segment: only included when we have an actual numeric value.
# At session start Claude Code doesn't send context_window info, so we omit
# the segment rather than rendering a misleading "0% ctx".
if [ -n "$REMAINING" ]; then
    CTX_SEGMENT=$(printf "%b%b%s%%%b ctx" \
        "${SEP}" "${CTX_COLOR}" "${REMAINING}" "${RESET}")
    STATUS="${STATUS}${CTX_SEGMENT}"
fi

STATUS="${STATUS}${CWD_SEGMENT}"

if [ -n "$GIT_SEGMENT" ]; then
    STATUS="${STATUS}${SEP}${GIT_SEGMENT}"
fi

STATUS="${STATUS}${STYLE_SEGMENT}"

printf '%b\n' "$STATUS"
exit 0
"""

# Default statusLine settings block to add when missing.  Uses the absolute
# user-level script path because this entry now lives in ``~/.claude/settings.json``
# and is not project-relative.
_DEFAULT_STATUS_LINE: dict = {
    "type": "command",
    "command": str(_USER_SCRIPT_PATH),
    "padding": 1,
    "refreshInterval": 10,
}

# Default Stop hook group (matcher "*") with the --clear command.
_DEFAULT_STOP_HOOK_ENTRY: dict = {
    "type": "command",
    "command": _STOP_HOOK_COMMAND,
    "timeout": 5,
}


def _ensure_script(script_path: Path, force: bool = False) -> bool:
    """Ensure the statusline script exists at ``script_path`` and is executable.

    Args:
        script_path: Absolute path to the desired statusline.sh location
            (typically ``~/.claude/hooks/scripts/statusline.sh``).
        force: If True, overwrite the existing script with the bundled
            canonical version regardless of whether it carries the
            ``_MPM_MARKER`` line.  This is the semantic of an explicit user
            action like ``claude-mpm update-statusline``: the user has asked
            for the official version, so we give them the official version.
            (Pre-marker installs and user-customised variants alike are
            overwritten.)  When False, we update if the file has the MPM
            marker, otherwise leave it alone.

    Returns:
        True on success, False on error.
    """
    if script_path.exists():
        try:
            existing = script_path.read_text(encoding="utf-8")
        except Exception:
            logger.exception("Failed to read existing statusline.sh at %s", script_path)
            return False

        is_mpm_owned = _MPM_MARKER in existing
        # Update if: (a) we own it and content differs, or (b) force is set.
        should_update = (is_mpm_owned and existing != _SCRIPT_CONTENT) or (
            force and existing != _SCRIPT_CONTENT
        )

        if should_update:
            try:
                script_path.write_text(_SCRIPT_CONTENT, encoding="utf-8")
                if is_mpm_owned:
                    logger.info("Upgraded MPM-managed statusline.sh at %s", script_path)
                else:
                    logger.info(
                        "Replaced statusline.sh at %s with canonical MPM version "
                        "(force mode; previous file lacked the MPM marker)",
                        script_path,
                    )
            except Exception:
                logger.exception("Failed to overwrite statusline.sh at %s", script_path)
                return False
        elif is_mpm_owned:
            logger.debug(
                "MPM-managed statusline.sh at %s is already up to date", script_path
            )
        else:
            logger.debug(
                "statusline.sh at %s lacks MPM marker — leaving user copy alone",
                script_path,
            )
        # Always re-chmod to ensure executable bit is set.
        try:
            current_mode = script_path.stat().st_mode
            script_path.chmod(
                current_mode
                | stat.S_IRWXU
                | stat.S_IRGRP
                | stat.S_IXGRP
                | stat.S_IROTH
                | stat.S_IXOTH
            )
        except Exception:
            logger.exception("Failed to chmod statusline.sh at %s", script_path)
            return False
        return True

    try:
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(_SCRIPT_CONTENT, encoding="utf-8")
        # chmod 755
        current_mode = script_path.stat().st_mode
        script_path.chmod(
            current_mode
            | stat.S_IRWXU
            | stat.S_IRGRP
            | stat.S_IXGRP
            | stat.S_IROTH
            | stat.S_IXOTH
        )
        logger.info("Created statusline.sh at %s (executable)", script_path)
    except Exception:
        logger.exception("Failed to create statusline.sh at %s", script_path)
        return False

    return True


def _ensure_settings_entry(settings_path: Path) -> bool:
    """Ensure the statusLine entry is present and current in settings.json.

    Ownership rules:
    - File absent → create with default statusLine entry.
    - No ``statusLine`` key → add default entry.
    - Existing ``statusLine.command`` contains ``statusline.sh`` (MPM-owned,
      legacy or current) → update the entry to the current default (absolute
      user-level path).
    - Existing ``statusLine.command`` is something else (user-owned) → leave
      it alone.

    Args:
        settings_path: Path to ``~/.claude/settings.json``.

    Returns:
        True on success, False on error.
    """
    if not settings_path.exists():
        # Create a minimal settings.json with the statusLine entry.
        try:
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            settings_path.write_text(
                json.dumps(
                    {"statusLine": _DEFAULT_STATUS_LINE}, indent=2, ensure_ascii=False
                )
                + "\n",
                encoding="utf-8",
            )
            logger.info(
                "Created settings.json with statusLine entry at %s", settings_path
            )
        except Exception:
            logger.exception("Failed to create settings.json at %s", settings_path)
            return False
        return True

    # File exists — read, check, maybe update.
    try:
        settings: dict = json.loads(settings_path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to parse settings.json at %s", settings_path)
        return False

    if not isinstance(settings, dict):
        logger.warning(
            "settings.json at %s is not a JSON object — refusing to modify",
            settings_path,
        )
        return False

    existing = settings.get("statusLine")
    if existing is None:
        # No statusLine entry at all → add ours.
        settings["statusLine"] = _DEFAULT_STATUS_LINE
        action = "Added statusLine entry to %s"
    else:
        # Inspect the existing entry's command.  If it's MPM-owned (matches
        # our substring), update it to the current default; otherwise leave it.
        cmd = ""
        if isinstance(existing, dict):
            raw_cmd = existing.get("command", "")
            if isinstance(raw_cmd, str):
                cmd = raw_cmd

        if _STATUSLINE_COMMAND_MATCH in cmd:
            if existing == _DEFAULT_STATUS_LINE:
                logger.debug(
                    "statusLine in %s already matches default — skipping",
                    settings_path,
                )
                return True
            settings["statusLine"] = _DEFAULT_STATUS_LINE
            action = (
                "Updated MPM-managed statusLine entry in %s to absolute user-level path"
            )
        else:
            logger.debug(
                "statusLine in %s points elsewhere (user-customised) — leaving alone",
                settings_path,
            )
            return True

    try:
        settings_path.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        logger.info(action, settings_path)
    except Exception:
        logger.exception("Failed to write settings.json at %s", settings_path)
        return False

    return True


def _find_mpm_stop_hook(settings: dict) -> dict | None:
    """Return the MPM-owned Stop hook entry if present, else None.

    Matches substring-wise so both relative and absolute invocations of
    ``statusline.sh --clear`` count as "MPM-owned".  Returns the hook dict
    itself (mutable reference) so callers can update it in place.
    """
    stop_groups = settings.get("hooks", {}).get("Stop", [])
    if not isinstance(stop_groups, list):
        return None

    for group in stop_groups:
        if not isinstance(group, dict):
            continue
        for hook in group.get("hooks", []) or []:
            if not isinstance(hook, dict):
                continue
            cmd = hook.get("command", "")
            if isinstance(cmd, str) and _STOP_HOOK_MATCH in cmd:
                return hook
    return None


def _ensure_stop_hook(settings_path: Path) -> bool:
    """Ensure a Stop hook calling statusline.sh --clear is present and current.

    Ownership rules:
    - If an existing Stop hook command contains ``statusline.sh --clear``
      (substring match — covers legacy relative paths and current absolute
      path), update its ``command`` to the absolute user-level path.
    - Otherwise, append a new MPM-owned hook to the existing matcher="*"
      group (or create one).
    - Stop hooks owned by the user (no ``statusline.sh --clear`` substring)
      are left in place.

    Args:
        settings_path: Path to ``~/.claude/settings.json``.

    Returns:
        True on success, False on error.
    """
    # Starting state: read existing settings, or start with {}.
    if settings_path.exists():
        try:
            raw = json.loads(settings_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                logger.warning(
                    "settings.json at %s is not a JSON object — overwriting",
                    settings_path,
                )
                raw = {}
            settings: dict = raw
        except Exception:
            logger.exception("Failed to parse settings.json at %s", settings_path)
            return False
    else:
        settings = {}

    existing_hook = _find_mpm_stop_hook(settings)
    if existing_hook is not None:
        if existing_hook.get("command") == _STOP_HOOK_COMMAND:
            logger.debug(
                "MPM-owned Stop hook in %s already uses absolute path — skipping",
                settings_path,
            )
            return True
        # Update in place to the absolute user-level path.
        existing_hook["command"] = _STOP_HOOK_COMMAND
        action = "Updated MPM-owned Stop hook command in %s to absolute user-level path"
    else:
        # Ensure nested structure: settings["hooks"]["Stop"] is a list of groups.
        hooks = settings.setdefault("hooks", {})
        if not isinstance(hooks, dict):
            hooks = {}
            settings["hooks"] = hooks
        stop_groups = hooks.setdefault("Stop", [])
        if not isinstance(stop_groups, list):
            stop_groups = []
            hooks["Stop"] = stop_groups

        # Prefer to append to an existing matcher="*" group so we don't
        # fragment the Stop configuration.
        wildcard_group: dict | None = None
        for group in stop_groups:
            if isinstance(group, dict) and group.get("matcher") == "*":
                wildcard_group = group
                break

        if wildcard_group is not None:
            group_hooks = wildcard_group.setdefault("hooks", [])
            if not isinstance(group_hooks, list):
                group_hooks = []
                wildcard_group["hooks"] = group_hooks
            group_hooks.append(_DEFAULT_STOP_HOOK_ENTRY)
        else:
            stop_groups.append(
                {
                    "matcher": "*",
                    "hooks": [_DEFAULT_STOP_HOOK_ENTRY],
                }
            )
        action = "Added Stop hook for statusline --clear to %s"

    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        logger.info(action, settings_path)
    except Exception:
        logger.exception("Failed to write settings.json at %s", settings_path)
        return False

    return True


def run_migration(installation_dir: Path | None = None, force: bool = False) -> bool:
    """Auto-configure the MPM statusline at the user level (~/.claude/).

    Args:
        installation_dir: Accepted for backwards compatibility but ignored —
            this migration always targets ``~/.claude/`` regardless of the
            project from which it is invoked.  The user-level statusline is
            shared across all projects.
        force: If True, overwrite an existing ``statusline.sh`` even when it
            lacks the MPM marker (i.e. user-customised).  When False (default),
            user-customised scripts are preserved; MPM-managed scripts are
            still upgraded if the bundled content has changed.

    Returns:
        True if migration completed successfully (including no-op), False on error.
    """
    # Note: ``installation_dir`` is intentionally ignored.  Earlier versions of
    # this migration wrote to ``<project>/.claude/``; we now operate at the
    # user level so that one statusline configuration applies to every
    # project.
    _ = installation_dir
    user_claude_dir = Path.home() / ".claude"
    script_path = user_claude_dir / "hooks" / "scripts" / "statusline.sh"
    settings_path = user_claude_dir / "settings.json"

    script_ok = _ensure_script(script_path, force=force)
    settings_ok = _ensure_settings_entry(settings_path)
    stop_hook_ok = _ensure_stop_hook(settings_path) if settings_ok else False

    return script_ok and settings_ok and stop_hook_ok
