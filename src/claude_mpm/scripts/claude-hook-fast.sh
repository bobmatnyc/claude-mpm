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

# Skip hook processing in MPM sub-agent sessions
if [[ -n "${CLAUDE_MPM_SUB_AGENT}" ]]; then
  echo '{"continue": true}'
  exit 0
fi

# =============================================================================
# Extract event type (try hook_event_name first, fallback to event)
# Claude Code sends: {"hook_event_name": "PreToolUse", ...}
# =============================================================================
EVENT=""

# Try hook_event_name first (Claude Code's primary field).
# Claude Code serialises JSON with a space after ':', e.g.:
#   {"hook_event_name": "PreToolUse", ...}
# Strip everything up to (and including) the opening quote of the value,
# accounting for an optional space between ':' and '"'.
if [[ "$INPUT" == *'"hook_event_name":'* ]]; then
    # Remove the prefix up to and including 'hook_event_name": ' (with space)
    TEMP=${INPUT#*\"hook_event_name\": \"}
    if [[ "$TEMP" == "$INPUT" ]]; then
        # No space variant: 'hook_event_name":"'
        TEMP=${INPUT#*\"hook_event_name\":\"}
    fi
    EVENT=${TEMP%%\"*}
fi

# Fallback to "event" field if hook_event_name not found
if [[ -z "$EVENT" ]] && [[ "$INPUT" == *'"event":'* ]]; then
    TEMP=${INPUT#*\"event\": \"}
    if [[ "$TEMP" == "$INPUT" ]]; then
        TEMP=${INPUT#*\"event\":\"}
    fi
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
                \"hook_event_name\": \"$EVENT\",
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
# Return the correct response shape for each event type.
#
# IMPORTANT: Claude Code's hook contract differs by event:
#
#   PreToolUse, PermissionRequest — these are DECISION events.  Claude Code
#     expects a synchronous response that includes a "continue" or "block"
#     decision.  Returning {"async": true} here is contractually wrong: it
#     silently breaks model-tier injection (model_tier_hook.py) and the
#     context circuit-breaker, and would hang PermissionRequest.
#     We emit {"continue": true} — a safe pass-through no-op decision.
#     The dedicated full Python handler (model_tier_hook.py / claude-hook
#     entry point) is separately wired in settings.json for these events
#     and handles the actual decision injection.
#
#   All other events (PostToolUse, Stop, SubagentStop, UserPromptSubmit,
#     SessionStart, Notification, AssistantResponse, WorktreeCreate,
#     WorktreeRemove, etc.) — pure fire-and-forget observability events.
#     {"async": true} is correct: it lets the background dashboard curl
#     complete without blocking Claude Code's hot path.
# =============================================================================
case "$EVENT" in
    PreToolUse|PermissionRequest)
        # Decision events require synchronous "continue" (safe pass-through).
        # The full Python handler is wired separately for actual logic.
        echo '{"continue": true}'
        ;;
    *)
        # Observability events: fire-and-forget async is safe and fast.
        echo '{"async": true, "asyncTimeout": 60000}'
        ;;
esac
