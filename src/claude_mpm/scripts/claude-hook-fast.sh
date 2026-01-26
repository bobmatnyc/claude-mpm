#!/bin/bash
# =============================================================================
# Ultra-fast hook handler for Claude MPM (~15ms vs ~450ms Python)
#
# OVERVIEW:
# This script provides a lightweight, fast-path hook handler that:
# 1. Extracts event type and tool name using pure bash string manipulation
# 2. Sends event to dashboard via fire-and-forget HTTP POST
# 3. Returns immediately to avoid blocking Claude Code
#
# PERFORMANCE:
# - ~15ms total execution (vs ~450ms for Python handler)
# - No Python interpreter startup overhead
# - No module imports
# - Background curl for non-blocking network
#
# ARCHITECTURE:
# Claude Code -> This Script -> curl (background) -> Dashboard API
#                           -> stdout: {"continue": true}
#
# WHEN TO USE:
# - Default hook for all events (PreToolUse, PostToolUse, etc.)
# - Dashboard event streaming and monitoring
# - Real-time activity visualization
#
# WHEN TO USE FULL PYTHON HANDLER:
# - Complex event processing requiring Python logic
# - Memory/KuzuDB integration
# - Auto-pause functionality
# - Response tracking
#
# @author Claude MPM Development Team
# @version 2.0
# @since v5.6.x
# =============================================================================

# Read input from stdin (Claude Code passes event data here)
INPUT=$(cat)

# Early exit if no input
[[ -z "$INPUT" ]] && { echo '{"continue": true}'; exit 0; }

# =============================================================================
# Extract event type (try hook_event_name first, fallback to event)
# Claude Code sends: {"hook_event_name": "PreToolUse", ...}
# =============================================================================
EVENT=""

# Try hook_event_name first (Claude Code's primary field)
if [[ "$INPUT" == *'"hook_event_name":'* ]]; then
    TEMP=${INPUT#*\"hook_event_name\":\"}
    EVENT=${TEMP%%\"*}
fi

# Fallback to "event" field if hook_event_name not found
if [[ -z "$EVENT" ]] && [[ "$INPUT" == *'"event":'* ]]; then
    TEMP=${INPUT#*\"event\":\"}
    EVENT=${TEMP%%\"*}
fi

# Default to unknown if neither field found
[[ -z "$EVENT" ]] && EVENT="unknown"

# =============================================================================
# Map event type to subtype for dashboard compatibility
# =============================================================================
case "$EVENT" in
    PreToolUse)         SUBTYPE="pre_tool" ;;
    PostToolUse)        SUBTYPE="post_tool" ;;
    UserPromptSubmit)   SUBTYPE="user_prompt" ;;
    SessionStart)       SUBTYPE="session_start" ;;
    Stop)               SUBTYPE="stop" ;;
    SubagentStop)       SUBTYPE="subagent_stop" ;;
    Notification)       SUBTYPE="notification" ;;
    AssistantResponse)  SUBTYPE="assistant_response" ;;
    *)                  SUBTYPE="$EVENT" ;;
esac

# =============================================================================
# Extract tool_name for tool-related events
# =============================================================================
TOOL_NAME=""
if [[ "$INPUT" == *'"tool_name":'* ]]; then
    TEMP=${INPUT#*\"tool_name\":\"}
    TOOL_NAME=${TEMP%%\"*}
fi

# =============================================================================
# Extract session_id if present
# =============================================================================
SESSION_ID=""
if [[ "$INPUT" == *'"session_id":'* ]]; then
    TEMP=${INPUT#*\"session_id\":\"}
    SESSION_ID=${TEMP%%\"*}
fi

# =============================================================================
# Generate correlation_id for event tracking
# Format: tool_timestamp or event_timestamp
# =============================================================================
TIMESTAMP_MS=$(date +%s%3N 2>/dev/null || date +%s)000
if [[ -n "$TOOL_NAME" ]]; then
    CORRELATION_ID="${TOOL_NAME}_${TIMESTAMP_MS}"
else
    CORRELATION_ID="${EVENT}_${TIMESTAMP_MS}"
fi

# =============================================================================
# Get port from environment (default: 8765)
# =============================================================================
PORT="${CLAUDE_MPM_SOCKETIO_PORT:-8765}"

# =============================================================================
# Fire HTTP POST to dashboard in background (fire-and-forget)
# - connect-timeout: 0.2s - fast fail if server not running
# - max-time: 0.3s - don't block on slow responses
# - Runs in background (&) to not block hook response
# =============================================================================
{
    curl -s -X POST "http://localhost:${PORT}/api/events" \
        -H "Content-Type: application/json" \
        -d "{
            \"namespace\": \"/\",
            \"event\": \"claude_event\",
            \"data\": {
                \"type\": \"hook\",
                \"subtype\": \"$SUBTYPE\",
                \"hook_event_type\": \"$EVENT\",
                \"tool_name\": \"$TOOL_NAME\",
                \"session_id\": \"$SESSION_ID\",
                \"correlation_id\": \"$CORRELATION_ID\",
                \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%S.000Z 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)\",
                \"source\": \"fast_hook\",
                \"data\": $INPUT
            }
        }" \
        --connect-timeout 0.2 --max-time 0.3 2>/dev/null
} &

# =============================================================================
# Return async response immediately
# async: true tells Claude Code this hook runs in background (non-blocking)
# asyncTimeout: 60000ms (60s) - maximum time for background operations
# This is the critical path - must be fast to not block Claude Code
# =============================================================================
echo '{"async": true, "asyncTimeout": 60000}'
