#!/bin/bash
# claude-mpm status line — deployed by claude-mpm on startup
# Shows: user | model | context% remaining
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
printf "claude-mpm: %s | %s | ${CTX_COLOR}%s%% remaining${RESET}\n" "$USER" "$MODEL" "$REMAINING"
