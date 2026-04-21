"""
Migration: Auto-configure MPM statusline in .claude/settings.json (v6.2.35).

Ensures that:
1. The statusline script is present at .claude/hooks/scripts/statusline.sh
   (creates it if missing; makes it executable).
2. A `statusLine` entry pointing to that script is present in
   .claude/settings.json (adds it if missing; leaves existing config
   untouched).
3. A Stop hook entry that calls `statusline.sh --clear` is present in
   .claude/settings.json so the bar disappears when Claude Code exits.

Idempotent: safe to run multiple times.  If the script, the statusLine
entry, and the Stop hook are already present the migration is a no-op and
returns True.

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

# Relative path of the script inside .claude/
_SCRIPT_REL = Path("hooks") / "scripts" / "statusline.sh"

# Marker line that identifies an MPM-managed statusline.sh.
# Any file containing this string will be treated as an official MPM-owned
# copy and will be overwritten when the template has been updated (force mode).
_MPM_MARKER = "# claude-mpm-managed:"

# Command string used in the Stop hook. Matched substring-wise so existing
# variations (e.g. an absolute path) are still detected as "already wired".
_STOP_HOOK_COMMAND = ".claude/hooks/scripts/statusline.sh --clear"
_STOP_HOOK_MATCH = "statusline.sh --clear"

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
    REMAINING=$(printf '%s' "$input" | jq -r '.context_window.remaining_percentage // 0' 2>/dev/null | cut -d. -f1)
    CWD=$(printf '%s' "$input" | jq -r '.workspace.current_dir // .cwd // ""' 2>/dev/null)
else
    MODEL="unknown"
    REMAINING="0"
    CWD=""
fi

# Normalise REMAINING to an integer (jq occasionally emits "null").
case "$REMAINING" in
    ''|*[!0-9]*) REMAINING=0 ;;
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
if [ "$REMAINING" -lt 20 ] 2>/dev/null; then
    CTX_COLOR="$RED"
else
    CTX_COLOR="$AMBER"
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
STATUS=$(printf "%b◆ %s%b%b%s%b%b%s%%%b ctx" \
    "" \
    "${USER_NAME}" \
    "${SEP}" \
    "${ORANGE}" "${MODEL}" "${RESET}" \
    "${SEP}${CTX_COLOR}" "${REMAINING}" "${RESET}")

STATUS="${STATUS}${CWD_SEGMENT}"

if [ -n "$GIT_SEGMENT" ]; then
    STATUS="${STATUS}${SEP}${GIT_SEGMENT}"
fi

STATUS="${STATUS}${STYLE_SEGMENT}"

printf '%b\n' "$STATUS"
exit 0
"""

# Default statusLine settings block to add when missing.
_DEFAULT_STATUS_LINE: dict = {
    "type": "command",
    "command": ".claude/hooks/scripts/statusline.sh",
    "padding": 1,
    "refreshInterval": 10,
}

# Default Stop hook group (matcher "*") with the --clear command.
_DEFAULT_STOP_HOOK_ENTRY: dict = {
    "type": "command",
    "command": _STOP_HOOK_COMMAND,
    "timeout": 5,
}


def _ensure_script(claude_dir: Path, force: bool = False) -> bool:
    """Ensure the statusline script exists and is executable.

    Args:
        claude_dir: Path to the .claude/ directory.
        force: If True, overwrite the existing script when it is MPM-managed
            (i.e. contains the ``_MPM_MARKER`` line).  User-customised scripts
            are still preserved even in force mode.

    Returns:
        True on success, False on error.
    """
    script_path = claude_dir / _SCRIPT_REL

    if script_path.exists():
        if force:
            try:
                existing = script_path.read_text(encoding="utf-8")
            except Exception:
                logger.exception(
                    "Failed to read existing statusline.sh at %s", script_path
                )
                return False

            if _MPM_MARKER in existing:
                if existing == _SCRIPT_CONTENT:
                    logger.debug(
                        "statusline.sh at %s is already up to date — no rewrite needed",
                        script_path,
                    )
                else:
                    try:
                        script_path.write_text(_SCRIPT_CONTENT, encoding="utf-8")
                        logger.info(
                            "Upgraded MPM-managed statusline.sh at %s", script_path
                        )
                    except Exception:
                        logger.exception(
                            "Failed to upgrade statusline.sh at %s", script_path
                        )
                        return False
            else:
                logger.info(
                    "statusline.sh at %s is user-customized — preserving (force mode respects user edits)",
                    script_path,
                )
        else:
            logger.debug(
                "statusline.sh already exists at %s — skipping script deploy",
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
    """Ensure the statusLine entry is present in settings.json.

    If the file doesn't exist it is created with just the statusLine entry.
    If it already contains a `statusLine` key the file is left unchanged.

    Args:
        settings_path: Path to .claude/settings.json.

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

    if "statusLine" in settings:
        logger.debug("statusLine already present in %s — skipping", settings_path)
        return True

    settings["statusLine"] = _DEFAULT_STATUS_LINE

    try:
        settings_path.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        logger.info("Added statusLine entry to %s", settings_path)
    except Exception:
        logger.exception("Failed to write settings.json at %s", settings_path)
        return False

    return True


def _stop_hook_already_wired(settings: dict) -> bool:
    """Return True if the Stop hook list already contains a --clear entry.

    Matches substring-wise so both relative and absolute invocations of
    statusline.sh --clear count as "already wired".
    """
    stop_groups = settings.get("hooks", {}).get("Stop", [])
    if not isinstance(stop_groups, list):
        return False

    for group in stop_groups:
        if not isinstance(group, dict):
            continue
        for hook in group.get("hooks", []) or []:
            if not isinstance(hook, dict):
                continue
            cmd = hook.get("command", "")
            if isinstance(cmd, str) and _STOP_HOOK_MATCH in cmd:
                return True
    return False


def _ensure_stop_hook(settings_path: Path) -> bool:
    """Ensure a Stop hook calling statusline.sh --clear is present.

    Idempotent: if an existing Stop hook already invokes `statusline.sh
    --clear` (matched substring-wise) the settings file is left unchanged.
    Otherwise a new hook is appended — either to the existing matcher "*"
    group if present, or as a new group.

    Args:
        settings_path: Path to .claude/settings.json.

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

    if _stop_hook_already_wired(settings):
        logger.debug(
            "Stop hook for statusline --clear already present in %s — skipping",
            settings_path,
        )
        return True

    # Ensure nested structure: settings["hooks"]["Stop"] is a list of groups.
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        settings["hooks"] = hooks
    stop_groups = hooks.setdefault("Stop", [])
    if not isinstance(stop_groups, list):
        stop_groups = []
        hooks["Stop"] = stop_groups

    # Prefer to append to an existing matcher="*" group so we don't fragment
    # the Stop configuration.
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

    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        logger.info("Added Stop hook for statusline --clear to %s", settings_path)
    except Exception:
        logger.exception("Failed to write settings.json at %s", settings_path)
        return False

    return True


def run_migration(installation_dir: Path | None = None, force: bool = False) -> bool:
    """Auto-configure the MPM statusline for the current project.

    Args:
        installation_dir: Root of the project (default: cwd).
        force: If True, overwrite an existing MPM-managed ``statusline.sh``
            with the bundled canonical version (user-customised scripts are
            still preserved).  Settings/hook wiring remains idempotent
            regardless of this flag.

    Returns:
        True if migration completed successfully (including no-op), False on error.
    """
    project_root = installation_dir or Path.cwd()
    claude_dir = project_root / ".claude"
    settings_path = claude_dir / "settings.json"

    script_ok = _ensure_script(claude_dir, force=force)
    settings_ok = _ensure_settings_entry(settings_path)
    stop_hook_ok = _ensure_stop_hook(settings_path) if settings_ok else False

    return script_ok and settings_ok and stop_hook_ok
