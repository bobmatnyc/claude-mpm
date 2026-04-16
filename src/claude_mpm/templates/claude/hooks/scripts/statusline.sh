#!/bin/bash
# claude-mpm status line — deployed by claude-mpm on startup
# Shows: user | model | branch ↑N↓N | context% remaining
input=$(cat)
USER=$(whoami)
MODEL=$(echo "$input" | jq -r '.model.display_name // .model.id // "unknown"' 2>/dev/null || echo "unknown")
REMAINING=$(echo "$input" | jq -r '.context_window.remaining_percentage // 0' 2>/dev/null | cut -d. -f1 || echo "0")
if [ "$REMAINING" -lt 20 ] 2>/dev/null; then
    CTX_COLOR="\033[31m"
elif [ "$REMAINING" -lt 40 ] 2>/dev/null; then
    CTX_COLOR="\033[33m"
else
    CTX_COLOR="\033[32m"
fi
RESET="\033[0m"
CYAN="\033[36m"
YELLOW="\033[33m"

# Git branch and ahead/behind info (fast, silent on failure)
GIT_INFO=""
if command -v git >/dev/null 2>&1; then
    BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null)
    if [ -n "$BRANCH" ]; then
        UPSTREAM=$(git rev-parse --abbrev-ref "@{upstream}" 2>/dev/null)
        if [ -n "$UPSTREAM" ]; then
            COUNTS=$(git rev-list --left-right --count "HEAD...${UPSTREAM}" 2>/dev/null)
            AHEAD=$(echo "$COUNTS" | awk '{print $1}')
            BEHIND=$(echo "$COUNTS" | awk '{print $2}')
            if [ "$AHEAD" -gt 0 ] 2>/dev/null; then
                AHEAD_STR="${YELLOW}↑${AHEAD}${RESET}"
            else
                AHEAD_STR="↑${AHEAD}"
            fi
            BEHIND_STR="↓${BEHIND}"
            GIT_INFO=" | ${CYAN}${BRANCH}${RESET} ${AHEAD_STR}${BEHIND_STR}"
        else
            GIT_INFO=" | ${CYAN}${BRANCH}${RESET}"
        fi
    fi
fi

printf "claude-mpm: %s | %s${GIT_INFO} | ${CTX_COLOR}%s%% remaining${RESET}\n" "$USER" "$MODEL" "$REMAINING"
