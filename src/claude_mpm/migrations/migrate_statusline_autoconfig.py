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
"""

import json
import logging
import stat
from pathlib import Path

logger = logging.getLogger(__name__)

# Relative path of the script inside .claude/
_SCRIPT_REL = Path("hooks") / "scripts" / "statusline.sh"

# Command string used in the Stop hook. Matched substring-wise so existing
# variations (e.g. an absolute path) are still detected as "already wired".
_STOP_HOOK_COMMAND = ".claude/hooks/scripts/statusline.sh --clear"
_STOP_HOOK_MATCH = "statusline.sh --clear"

# Statusline script content (byte-identical to .claude/hooks/scripts/statusline.sh
# in this repo so fresh projects receive the same canonical version).
_SCRIPT_CONTENT = r"""#!/bin/bash
# claude-mpm floating bottom status bar
#
# Draws a persistent status bar on the last line of the terminal using
# ANSI/VT100 escape sequences. Receives JSON on stdin from Claude Code's
# statusLine hook and is re-invoked periodically (refreshInterval in
# .claude/settings.json). On exit (Stop hook), invoke with --clear to erase
# the bar so the shell prompt returns to its normal position.
#
# Approach (no .zshrc/.bashrc changes required):
#   1. Save cursor position          : \033[s
#   2. Move to last row, column 1    : \033[<row>;1H
#   3. Clear entire line             : \033[2K
#   4. Write styled status bar       : \033[48;5;234m ... \033[0m
#   5. Restore cursor position       : \033[u
#
# Palette is derived from the Claude brand:
#   - Background #1a1a1a             : \033[48;5;234m
#   - Text / cream #fbf0df           : \033[38;5;230m
#   - Orange / rust #CC785C          : \033[38;5;174m
#   - Amber #f3d5a3                  : \033[38;5;223m
#
# Layout:
#   ◆ <user> │ <model> │ <ctx%> ctx │ <cwd> │ <branch> [↑N][↓N] │ style:<outputStyle>

set -u

# ---------------------------------------------------------------------------
# Guards: refuse to draw on non-interactive / dumb terminals.
# ---------------------------------------------------------------------------

# If there is no controlling terminal we can't draw anything — exit silently.
# We must actually be able to *open* /dev/tty (not just stat it) to draw.
if ! (: >/dev/tty) 2>/dev/null; then
    exit 0
fi

# Respect TERM=dumb (e.g. inside CI, cron, pipes) and unset TERM.
case "${TERM:-dumb}" in
    ""|dumb) exit 0 ;;
esac

# tput must be available for row/col detection. If not, bail silently.
if ! command -v tput >/dev/null 2>&1; then
    exit 0
fi

# Query terminal size via the TTY device so it works even when stdout is
# piped (Claude Code captures stdout for its own statusline area).
LINES=$(tput lines </dev/tty 2>/dev/null || echo 0)
COLS=$(tput cols  </dev/tty 2>/dev/null || echo 0)

# If size lookup failed, silently abort.
if [ "$LINES" -lt 2 ] 2>/dev/null || [ "$COLS" -lt 10 ] 2>/dev/null; then
    exit 0
fi

LAST_ROW="$LINES"

# ---------------------------------------------------------------------------
# --clear mode: erase the bar and return cursor to normal position.
# Invoked from the Stop hook so the bar disappears when Claude Code exits.
# ---------------------------------------------------------------------------
if [ "${1:-}" = "--clear" ]; then
    # Save cursor, move to last line, clear whole line, reset attrs, restore.
    printf '\033[s\033[%d;1H\033[2K\033[0m\033[u' "$LAST_ROW" >/dev/tty 2>/dev/null || true
    exit 0
fi

# ---------------------------------------------------------------------------
# Parse JSON payload from stdin (if any).
# ---------------------------------------------------------------------------
input=""
# Only read stdin if it's not a TTY (i.e. Claude Code piped JSON in).
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
    # Guard against jq emitting "null" literal.
    [ "$OUTPUT_STYLE" = "null" ] && OUTPUT_STYLE="default"
fi

# ---------------------------------------------------------------------------
# Claude brand palette.
# ---------------------------------------------------------------------------
BG="\033[48;5;234m"          # background #1a1a1a
CREAM="\033[38;5;230m"       # text       #fbf0df
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

# Separator (orange vertical bar) with surrounding spaces.
SEP=" ${ORANGE}│${RESET}${BG}${CREAM} "

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
        GIT_SEGMENT="${AMBER}${BRANCH}${AHEAD_STR}${BEHIND_STR}${RESET}${BG}${CREAM}"
    fi
fi

# ---------------------------------------------------------------------------
# CWD segment: shorten path and colour amber. Omitted on narrow terminals.
# ---------------------------------------------------------------------------
CWD_SEGMENT=""
if [ "$COLS" -ge 100 ]; then
    # Prefer the path from the JSON payload; fall back to shell pwd.
    RAW_CWD="${CWD:-$(pwd 2>/dev/null || echo "")}"
    # Replace $HOME prefix with ~.
    case "$RAW_CWD" in
        "$HOME"*) SHORT_CWD="~${RAW_CWD#"$HOME"}" ;;
        *)        SHORT_CWD="$RAW_CWD" ;;
    esac
    # If still longer than 40 chars, truncate from the left with … prefix.
    if [ "${#SHORT_CWD}" -gt 40 ]; then
        SHORT_CWD="…$(printf '%s' "$SHORT_CWD" | awk '{ print substr($0, length($0)-38) }')"
    fi
    if [ -n "$SHORT_CWD" ]; then
        CWD_SEGMENT="${SEP}${AMBER}${SHORT_CWD}${RESET}${BG}${CREAM}"
    fi
fi

# ---------------------------------------------------------------------------
# outputStyle segment (cream dimmed). Omitted entirely when jq unavailable.
# ---------------------------------------------------------------------------
STYLE_SEGMENT=""
if [ -n "$OUTPUT_STYLE" ]; then
    STYLE_SEGMENT="${SEP}${DIM}${CREAM}style:${OUTPUT_STYLE}${RESET}${BG}${CREAM}"
fi

# ---------------------------------------------------------------------------
# Compose the bar content.
#
# Prefixed with a single space; \033[K (clear to EOL) after writing extends
# the background across the full terminal width.
# ---------------------------------------------------------------------------
CONTENT=$(printf "%b ◆ %s%b%s%b%s%b%b%s%%%b ctx%b" \
    "${CREAM}" \
    "${USER_NAME}" \
    "${SEP}" \
    "${ORANGE}${MODEL}${RESET}${BG}${CREAM}" \
    "${SEP}" \
    "" \
    "${CTX_COLOR}" "${REMAINING}" "${RESET}${BG}${CREAM}" \
    "")

CONTENT="${CONTENT}${CWD_SEGMENT}"

if [ -n "$GIT_SEGMENT" ]; then
    CONTENT="${CONTENT}${SEP}${GIT_SEGMENT}"
fi

CONTENT="${CONTENT}${STYLE_SEGMENT} "

# ---------------------------------------------------------------------------
# Draw the bar.
#
# Sequence:
#   \033[s              save cursor
#   \033[<row>;1H       move to last row, column 1
#   \033[2K             erase the whole line (so stale text is wiped even if
#                       the new bar is shorter than the old one)
#   <BG><content>\033[K apply background, print content, extend bg to EOL
#   \033[0m             reset attributes
#   \033[u              restore cursor
#
# All output goes directly to /dev/tty so Claude Code's stdout capture for
# its built-in statusline area isn't polluted and we don't interfere with
# the normal scrollback.
# ---------------------------------------------------------------------------
{
    printf '\033[s'
    printf '\033[%d;1H' "$LAST_ROW"
    printf '\033[2K'
    printf '%b' "${BG}${CREAM}${CONTENT}"
    printf '\033[K'
    printf '\033[0m'
    printf '\033[u'
} >/dev/tty 2>/dev/null || true

# stdout stays empty on purpose: the floating bar is the statusline, and we
# don't want Claude Code to render a duplicate in its own capture area.
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


def _ensure_script(claude_dir: Path) -> bool:
    """Ensure the statusline script exists and is executable.

    Args:
        claude_dir: Path to the .claude/ directory.

    Returns:
        True on success, False on error.
    """
    script_path = claude_dir / _SCRIPT_REL

    if script_path.exists():
        logger.debug(
            "statusline.sh already exists at %s — skipping script deploy", script_path
        )
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


def run_migration(installation_dir: Path | None = None) -> bool:
    """Auto-configure the MPM statusline for the current project.

    Args:
        installation_dir: Root of the project (default: cwd).

    Returns:
        True if migration completed successfully (including no-op), False on error.
    """
    project_root = installation_dir or Path.cwd()
    claude_dir = project_root / ".claude"
    settings_path = claude_dir / "settings.json"

    script_ok = _ensure_script(claude_dir)
    settings_ok = _ensure_settings_entry(settings_path)
    stop_hook_ok = _ensure_stop_hook(settings_path) if settings_ok else False

    return script_ok and settings_ok and stop_hook_ok
