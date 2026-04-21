#!/bin/bash
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
