"""
Migration: Auto-configure MPM statusline in .claude/settings.json (v6.2.35).

Ensures that:
1. The statusline script is present at .claude/hooks/scripts/statusline.sh
   (creates it if missing; makes it executable).
2. A `statusLine` entry pointing to that script is present in
   .claude/settings.json (adds it if missing; leaves existing config
   untouched).

Idempotent: safe to run multiple times.  If both the script and the
settings entry already exist the migration is a no-op and returns True.
"""

import json
import logging
import stat
from pathlib import Path

logger = logging.getLogger(__name__)

# Relative path of the script inside .claude/
_SCRIPT_REL = Path("hooks") / "scripts" / "statusline.sh"

# Statusline script content (identical to the project's existing script so
# that projects that don't yet have it receive the same canonical version).
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
# Status content (same info as before): user | model | context % | git branch + ahead/behind

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
# Style palette.
#   - Bar background: 256-colour 234 (near-black grey).
#   - Foreground:     256-colour 250 (light grey) for the base text.
# ---------------------------------------------------------------------------
BG="\033[48;5;234m"
FG="\033[38;5;250m"
RESET="\033[0m"
DIM="\033[2m"
CYAN="\033[38;5;81m"

# Context remaining colour (applied on top of the bar background).
if [ "$REMAINING" -lt 20 ] 2>/dev/null; then
    CTX_COLOR="\033[38;5;203m"   # soft red
elif [ "$REMAINING" -lt 40 ] 2>/dev/null; then
    CTX_COLOR="\033[38;5;221m"   # amber
else
    CTX_COLOR="\033[38;5;114m"   # green
fi

# ---------------------------------------------------------------------------
# Git info (branch + ahead/behind) if we're inside a repo.
# ---------------------------------------------------------------------------
GIT_INFO=""
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
            [ "${AHEAD:-0}"  -gt 0 ] 2>/dev/null && AHEAD_STR="↑${AHEAD}"
            [ "${BEHIND:-0}" -gt 0 ] 2>/dev/null && BEHIND_STR="↓${BEHIND}"
        fi

        if [ -n "$AHEAD_STR" ] || [ -n "$BEHIND_STR" ]; then
            GIT_INFO=" ${DIM}|${RESET}${BG} ${CYAN}${BRANCH}${RESET}${BG} ${AHEAD_STR}${BEHIND_STR:+ }${BEHIND_STR}"
        else
            GIT_INFO=" ${DIM}|${RESET}${BG} ${CYAN}${BRANCH}${RESET}${BG}"
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Compose the bar content.
#
# We prefix with a single space and use \033[K (clear to end of line) after
# writing so the bar background extends across the full terminal width.
# ---------------------------------------------------------------------------
CONTENT=$(printf "%b claude-mpm %b|%b %s %b|%b %s %b|%b %b%s%%%b remaining%b" \
    "${FG}" \
    "${DIM}" "${RESET}${BG}${FG}" "${USER_NAME}" \
    "${DIM}" "${RESET}${BG}${FG}" "${MODEL}" \
    "${DIM}" "${RESET}${BG}${FG}" \
    "${CTX_COLOR}" "${REMAINING}" "${RESET}${BG}${FG}" \
    "${GIT_INFO}")

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
    printf '%b' "${BG}${CONTENT}"
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

    return script_ok and settings_ok
