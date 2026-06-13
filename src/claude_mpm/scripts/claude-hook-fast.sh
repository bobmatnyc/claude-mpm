#!/bin/bash
# References: SPEC-HOOKS-01~1 docs/specs/hooks.md#SPEC-HOOKS-01~1
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
# @version 2.1
# @since v5.6.x
# =============================================================================

# Read input from stdin (Claude Code passes event data here)
INPUT=$(cat)

# Early exit if no input
[[ -z "$INPUT" ]] && { echo '{"continue": true}'; exit 0; }

# =============================================================================
# Extract event type (try hook_event_name first, fallback to event)
# Claude Code sends: {"hook_event_name": "PreToolUse", ...}
#
# The extraction must handle both compact JSON ("key":"value") and
# pretty-printed JSON ("key": "value" with a space after the colon).
# Strategy: strip prefix up to and including the key colon, then strip
# optional whitespace, then strip the opening quote.
#
# Event extraction is done BEFORE the sub-agent early-exit check so that
# WorktreeCreate (and WorktreeRemove) are handled correctly regardless of
# whether CLAUDE_MPM_SUB_AGENT is set.
# =============================================================================
EVENT=""

# Helper: extract the string value of a JSON key from $INPUT.
# Handles both  "key":"value"  and  "key": "value"  forms.
# Usage: _extract_json_str "key_name"  → sets TEMP to the value.
_extract_json_str() {
    local key="$1"
    # Strip everything up to and including  "key":
    TEMP="${INPUT#*\"${key}\":}"
    # Strip optional leading whitespace (space or tab)
    TEMP="${TEMP#" "}"
    TEMP="${TEMP#"	"}"
    # Strip the leading quote
    TEMP="${TEMP#\"}"
    # Trim at the next unescaped quote
    TEMP="${TEMP%%\"*}"
}

# Try hook_event_name first (Claude Code's primary field)
if [[ "$INPUT" == *'"hook_event_name":'* ]]; then
    _extract_json_str "hook_event_name"
    EVENT="$TEMP"
fi

# Fallback to "event" field if hook_event_name not found
if [[ -z "$EVENT" ]] && [[ "$INPUT" == *'"event":'* ]]; then
    _extract_json_str "event"
    EVENT="$TEMP"
fi

# Default to unknown if neither field found
[[ -z "$EVENT" ]] && EVENT="unknown"

# =============================================================================
# WorktreeCreate: Claude Code isolation:"worktree" contract
#
# Contract (Claude Code spec):
#   Input (stdin JSON): name (suggested slug), cwd (repo root)
#   Hook must: run `git worktree add` and print the ABSOLUTE PATH to stdout
#   Exit 0 on success, non-zero on failure
#
# Placement note: This branch runs BEFORE the CLAUDE_MPM_SUB_AGENT early-exit
# so that worktrees requested for sub-agent isolation are also created.
# INPUT is already fully read above — no double-consume of stdin.
# =============================================================================
if [[ "$EVENT" == "WorktreeCreate" ]]; then
    # Extract name (suggested slug) and cwd (repo root) from already-read $INPUT.
    # Use _extract_json_str to handle both compact and spaced JSON colon syntax.
    NAME=""
    CWD=""

    if [[ "$INPUT" == *'"name":'* ]]; then
        _extract_json_str "name"
        NAME="$TEMP"
    fi
    if [[ "$INPUT" == *'"cwd":'* ]]; then
        _extract_json_str "cwd"
        CWD="$TEMP"
    fi

    # Security note: `name` is a user-supplied slug and is sanitized below
    # (lowercase, non-alnum replaced with '-').  `cwd` and `path` are
    # Claude-supplied inputs that represent trusted filesystem paths; they are
    # safely double-quoted in all shell expansions below and never eval'd.
    SAFE_NAME=""
    if [[ -n "$NAME" ]]; then
        SAFE_NAME=$(printf '%s' "$NAME" \
            | tr '[:upper:]' '[:lower:]' \
            | tr -cs 'a-z0-9-' '-' \
            | sed 's/--*/-/g; s/^-//; s/-$//')
    fi

    # Fall back to a short unique slug when name is empty or sanitizes to empty
    if [[ -z "$SAFE_NAME" ]]; then
        SAFE_NAME="worktree-$(date +%s | tr -d '\n' | tail -c 6)"
    fi

    # Determine repo root: prefer cwd from JSON input, fall back to git detection
    REPO_ROOT="${CWD:-}"
    if [[ -z "$REPO_ROOT" ]]; then
        REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
    fi
    # Canonicalize to an absolute path (resolves symlinks, trailing slashes, etc.)
    REPO_ROOT=$(cd "$REPO_ROOT" 2>/dev/null && pwd) || REPO_ROOT="${CWD:-$(pwd)}"

    # Worktrees live in a sibling directory: <parent>/<repo-name>-worktrees/<slug>
    PARENT_DIR=$(dirname "$REPO_ROOT")
    REPO_BASENAME=$(basename "$REPO_ROOT")
    WORKTREE_DIR="$PARENT_DIR/${REPO_BASENAME}-worktrees"
    WORKTREE_PATH="$WORKTREE_DIR/$SAFE_NAME"

    # Ensure the parent directory for worktrees exists
    mkdir -p "$WORKTREE_DIR"

    # Attempt 1: create worktree and a new branch named $SAFE_NAME.
    # Redirect both stdout and stderr to suppress "HEAD is now at..." and
    # "Preparing worktree..." messages that git prints to stdout/stderr.
    # The echo below is the ONLY output: the absolute worktree path.
    if git -C "$REPO_ROOT" worktree add "$WORKTREE_PATH" -b "$SAFE_NAME" >/dev/null 2>&1; then
        echo "$WORKTREE_PATH"
        exit 0
    fi

    # Attempt 2: create worktree without a new branch.
    # (branch already exists, detached HEAD, or any other branch situation)
    if git -C "$REPO_ROOT" worktree add "$WORKTREE_PATH" >/dev/null 2>&1; then
        echo "$WORKTREE_PATH"
        exit 0
    fi

    # Attempt 3: path already exists as a registered worktree — re-use it.
    if [[ -d "$WORKTREE_PATH" ]] && git -C "$REPO_ROOT" worktree list 2>/dev/null | grep -qF "$WORKTREE_PATH"; then
        echo "$WORKTREE_PATH"
        exit 0
    fi

    # All attempts failed — signal failure to Claude Code
    exit 1
fi

# =============================================================================
# WorktreeRemove: cleanup companion to WorktreeCreate
#
# Contract (Claude Code spec, status: not yet publicly confirmed as of 2025-05):
#   Input (stdin JSON): path (absolute path of worktree to remove)
#   Hook must: cleanly remove the worktree
#   Exit 0 expected; stdout not inspected by Claude Code for this event
#
# NOTE: If Claude Code does not emit this event the branch is a harmless no-op.
# Follow-up ticket: confirm WorktreeRemove in Claude Code release notes.
# =============================================================================
if [[ "$EVENT" == "WorktreeRemove" ]]; then
    WORKTREE_PATH=""
    if [[ "$INPUT" == *'"path":'* ]]; then
        _extract_json_str "path"
        WORKTREE_PATH="$TEMP"
    fi

    if [[ -n "$WORKTREE_PATH" ]]; then
        # Detect repo root from input cwd, or fall back to git detection
        REPO_ROOT=""
        if [[ "$INPUT" == *'"cwd":'* ]]; then
            _extract_json_str "cwd"
            REPO_ROOT="$TEMP"
        fi
        if [[ -z "$REPO_ROOT" ]]; then
            REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
        fi
        REPO_ROOT=$(cd "$REPO_ROOT" 2>/dev/null && pwd) || true

        git -C "$REPO_ROOT" worktree remove --force "$WORKTREE_PATH" 2>/dev/null || true
    fi

    echo '{"continue": true}'
    exit 0
fi

# =============================================================================
# Skip hook processing in MPM sub-agent sessions (non-worktree events only)
# WorktreeCreate/WorktreeRemove have already been handled and exited above.
# =============================================================================
if [[ -n "${CLAUDE_MPM_SUB_AGENT}" ]]; then
  echo '{"continue": true}'
  exit 0
fi

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
    _extract_json_str "tool_name"
    TOOL_NAME="$TEMP"
fi

# =============================================================================
# Extract session_id if present
# =============================================================================
SESSION_ID=""
if [[ "$INPUT" == *'"session_id":'* ]]; then
    _extract_json_str "session_id"
    SESSION_ID="$TEMP"
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
        --connect-timeout 0.2 --max-time 0.3 >/dev/null 2>&1
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
