#!/usr/bin/env python3
"""Tool event handlers (PreToolUse, PostToolUse, Task delegation).

Extracted from ``event_handlers.EventHandlers`` as part of the #509 refactor.
Behavior is preserved verbatim; only the surrounding structure has changed.
"""

import asyncio
import uuid
from datetime import UTC, datetime

# Import tool analysis with fallback for direct execution
try:
    from ..tool_analysis import (
        assess_security_risk,
        calculate_duration,
        classify_tool_operation,
        extract_tool_parameters,
        extract_tool_results,
    )
except ImportError:
    # Pyright cannot resolve this fallback path; it is intentional for direct execution.
    from tool_analysis import (  # type: ignore[import-not-found]
        assess_security_risk,
        calculate_duration,
        classify_tool_operation,
        extract_tool_parameters,
        extract_tool_results,
    )

# Import correlation manager with fallback for direct execution
try:
    from ..correlation_manager import CorrelationManager
except ImportError:
    # Pyright cannot resolve this fallback path; it is intentional for direct execution.
    from correlation_manager import CorrelationManager  # type: ignore[import-not-found]

from .base import DEBUG, BaseEventHandler, _log


class ToolHandler:
    """Handle PreToolUse and PostToolUse events."""

    def __init__(self, base: BaseEventHandler):
        self.base = base
        self.hook_handler = base.hook_handler

    def handle_pre_tool_fast(self, event):
        """Handle pre-tool use with comprehensive data capture.

        WHY comprehensive capture:
        - Captures tool parameters for debugging and security analysis
        - Provides context about what Claude is about to do
        - Enables pattern analysis and security monitoring
        """
        # Context circuit-breaker: deny tool calls when context >= 95% (issue
        # #420).  Run BEFORE any other PreToolUse work so a critical-context
        # session aborts cleanly instead of doing extra observability work
        # that pushes us further over the limit.  Failures here must fail
        # open -- the breaker module already swallows errors internally, but
        # we wrap the import too in case the module itself is unavailable.
        try:
            from claude_mpm.hooks import context_circuit_breaker

            cb_decision = context_circuit_breaker.evaluate(event)
        except Exception:
            cb_decision = {}
        if cb_decision.get("permissionDecision") == "deny":
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": cb_decision.get(
                        "permissionDecisionReason", ""
                    ),
                }
            }

        # Enhanced debug logging for session correlation
        session_id = event.get("session_id", "")
        if DEBUG:
            _log(f"  - session_id: {session_id[:16] if session_id else 'None'}...")
            _log(f"  - event keys: {list(event.keys())}")

        tool_name = event.get("tool_name", "")
        tool_input = event.get("tool_input", {})

        # Generate unique tool call ID for correlation with post_tool event
        tool_call_id = str(uuid.uuid4())

        # Extract key parameters based on tool type
        tool_params = extract_tool_parameters(tool_name, tool_input)

        # Classify tool operation
        operation_type = classify_tool_operation(tool_name, tool_input)

        # Get working directory and git branch
        working_dir = event.get("cwd", "")
        git_branch = (
            self.base._get_git_branch(working_dir) if working_dir else "Unknown"
        )

        timestamp = datetime.now(UTC).isoformat()

        pre_tool_data = {
            "tool_name": tool_name,
            "operation_type": operation_type,
            "tool_parameters": tool_params,
            "session_id": event.get("session_id", ""),
            "working_directory": working_dir,
            "git_branch": git_branch,
            "timestamp": timestamp,
            "parameter_count": len(tool_input) if isinstance(tool_input, dict) else 0,
            "is_file_operation": tool_name
            in ["Write", "Edit", "MultiEdit", "Read", "LS", "Glob"],
            "is_execution": tool_name in ["Bash", "NotebookEdit"],
            "is_delegation": tool_name == "Task",
            "security_risk": assess_security_risk(tool_name, tool_input),
            "correlation_id": tool_call_id,  # Add correlation_id for pre/post correlation
        }

        # Store tool_call_id using CorrelationManager for cross-process retrieval
        if session_id:
            CorrelationManager.store(session_id, tool_call_id, tool_name)
            if DEBUG:
                _log(
                    f"  - Generated tool_call_id: {tool_call_id[:8]}... for session {session_id[:8]}..."
                )

        # Add delegation-specific data if this is a Task tool
        if tool_name == "Task" and isinstance(tool_input, dict):
            self._handle_task_delegation(tool_input, pre_tool_data, session_id)

        # Record tool call for auto-pause if active
        auto_pause = getattr(self.hook_handler, "auto_pause_handler", None)
        if auto_pause and auto_pause.is_pause_active():
            try:
                auto_pause.on_tool_call(tool_name, tool_input)
            except Exception as e:
                if DEBUG:
                    _log(f"Auto-pause tool recording error: {e}")

        self.hook_handler._emit_socketio_event("", "pre_tool", pre_tool_data)

        # Handle TodoWrite specially - emit dedicated todo_updated event
        # WHY: Frontend expects todo_updated events for dashboard display
        # The broadcaster.todo_updated() method exists but was never called
        if tool_name == "TodoWrite" and tool_params.get("todos"):
            todo_data = {
                "todos": tool_params["todos"],
                "total_count": len(tool_params["todos"]),
                "session_id": session_id,
                "timestamp": timestamp,
            }
            self.hook_handler._emit_socketio_event("", "todo_updated", todo_data)
            if DEBUG:
                _log(
                    f"  - Emitted todo_updated event with {len(tool_params['todos'])} todos for session {session_id[:8]}..."
                )

        # Normal path: no input modification, no deny -- caller treats this
        # as a plain "continue" (see hook_handler._route_event return logic).
        return None

    def _handle_task_delegation(
        self, tool_input: dict, pre_tool_data: dict, session_id: str
    ):
        """Handle Task delegation specific processing."""
        # Normalize agent type to handle capitalized names like "Research", "Engineer", etc.
        raw_agent_type = tool_input.get("subagent_type", "unknown")

        # Use AgentNameNormalizer if available, otherwise simple lowercase normalization
        try:
            from claude_mpm.core.agent_name_normalizer import AgentNameNormalizer

            normalizer = AgentNameNormalizer()
            # Convert to Task format (lowercase with hyphens)
            agent_type = (
                normalizer.to_task_format(raw_agent_type)
                if raw_agent_type != "unknown"
                else "unknown"
            )
        except ImportError:
            # Fallback to shared normalizer when AgentNameNormalizer is unavailable
            from claude_mpm.utils.agent_filters import normalize_agent_id

            agent_type = (
                normalize_agent_id(raw_agent_type)
                if raw_agent_type != "unknown"
                else "unknown"
            )

        pre_tool_data["delegation_details"] = {
            "agent_type": agent_type,
            "original_agent_type": raw_agent_type,  # Keep original for debugging
            "prompt": tool_input.get("prompt", ""),
            "description": tool_input.get("description", ""),
            "task_preview": (
                tool_input.get("prompt", "") or tool_input.get("description", "")
            )[:100],
        }

        # Track this delegation for SubagentStop correlation and response tracking
        if DEBUG:
            _log(f"  - session_id: {session_id[:16] if session_id else 'None'}...")
            _log(f"  - agent_type: {agent_type}")
            _log(f"  - raw_agent_type: {raw_agent_type}")

        if session_id and agent_type != "unknown":
            # Prepare request data for response tracking correlation
            request_data = {
                "prompt": tool_input.get("prompt", ""),
                "description": tool_input.get("description", ""),
                "agent_type": agent_type,
            }
            self.hook_handler._track_delegation(session_id, agent_type, request_data)

            if DEBUG:
                _log("  - Delegation tracked successfully")
                _log(f"  - Request data keys: {list(request_data.keys())}")
                delegation_requests = getattr(
                    self.hook_handler, "delegation_requests", {}
                )
                _log(f"  - delegation_requests size: {len(delegation_requests)}")

            # Log important delegations for debugging
            if DEBUG or agent_type in ["research", "engineer", "qa", "documentation"]:
                _log(
                    f"Hook handler: Task delegation started - agent: '{agent_type}', session: '{session_id}'"
                )

        # Trigger memory pre-delegation hook
        try:
            mhm = getattr(self.hook_handler, "memory_hook_manager", None)
            if mhm and hasattr(mhm, "trigger_pre_delegation_hook"):
                mhm.trigger_pre_delegation_hook(agent_type, tool_input, session_id)
        except Exception:  # nosec B110
            # Memory hooks are optional
            pass

        # Emit a subagent_start event for better tracking
        subagent_start_data = {
            "agent_type": agent_type,
            "agent_id": f"{agent_type}_{session_id}",
            "session_id": session_id,
            "prompt": tool_input.get("prompt", ""),
            "description": tool_input.get("description", ""),
            "timestamp": datetime.now(UTC).isoformat(),
            "hook_event_name": "SubagentStart",  # For dashboard compatibility
        }
        self.hook_handler._emit_socketio_event(
            "", "subagent_start", subagent_start_data
        )

        # Log agent prompt if LogManager is available
        # Uses injected log_manager or lazy-loaded module-level instance
        log_manager = self.base.log_manager
        if log_manager is not None:
            try:
                # Prepare prompt content
                prompt_content = tool_input.get("prompt", "")
                if not prompt_content:
                    prompt_content = tool_input.get("description", "")

                if prompt_content:
                    # Prepare metadata
                    metadata = {
                        "agent_type": agent_type,
                        "agent_id": f"{agent_type}_{session_id}",
                        "session_id": session_id,
                        "delegation_context": {
                            "description": tool_input.get("description", ""),
                            "timestamp": datetime.now(UTC).isoformat(),
                        },
                    }

                    # Log the agent prompt asynchronously
                    try:
                        loop = asyncio.get_running_loop()
                        # Fire-and-forget logging (ephemeral hook process); task
                        # reference intentionally unused.
                        asyncio.create_task(
                            log_manager.log_prompt(
                                f"agent_{agent_type}", prompt_content, metadata
                            )
                        )
                    except RuntimeError:
                        # No running loop, create one
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(
                            log_manager.log_prompt(
                                f"agent_{agent_type}", prompt_content, metadata
                            )
                        )

                    if DEBUG:
                        _log(f"  - Agent prompt logged for {agent_type}")
            except Exception as e:
                if DEBUG:
                    _log(f"  - Could not log agent prompt: {e}")

    def handle_post_tool_fast(self, event):
        """Handle post-tool use with comprehensive data capture.

        WHY comprehensive capture:
        - Captures execution results and success/failure status
        - Provides duration and performance metrics
        - Enables pattern analysis of tool usage and success rates
        """
        tool_name = event.get("tool_name", "")
        exit_code = event.get("exit_code", 0)
        session_id = event.get("session_id", "")

        # Extract result data
        result_data = extract_tool_results(event)

        # Calculate duration if timestamps are available
        duration = calculate_duration(event)

        # Get working directory and git branch
        working_dir = event.get("cwd", "")
        git_branch = (
            self.base._get_git_branch(working_dir) if working_dir else "Unknown"
        )

        # Retrieve tool_call_id using CorrelationManager for cross-process correlation
        tool_call_id = CorrelationManager.retrieve(session_id) if session_id else None
        if DEBUG and tool_call_id:
            _log(
                f"  - Retrieved tool_call_id: {tool_call_id[:8]}... for session {session_id[:8]}..."
            )

        post_tool_data = {
            "tool_name": tool_name,
            "exit_code": exit_code,
            "success": exit_code == 0,
            "status": (
                "success"
                if exit_code == 0
                else "blocked"
                if exit_code == 2
                else "error"
            ),
            "duration_ms": duration,
            "result_summary": result_data,
            "session_id": session_id,
            "working_directory": working_dir,
            "git_branch": git_branch,
            "timestamp": datetime.now(UTC).isoformat(),
            "has_output": bool(result_data.get("output")),
            "has_error": bool(result_data.get("error")),
            "output_size": (
                len(str(result_data.get("output", "")))
                if result_data.get("output")
                else 0
            ),
        }

        # Include full output for file operations (Read, Edit, Write)
        # so frontend can display file content
        if tool_name in ("Read", "Edit", "Write", "Grep", "Glob") and "output" in event:
            post_tool_data["output"] = event["output"]

        # Add correlation_id if available for correlation with pre_tool
        if tool_call_id:
            post_tool_data["correlation_id"] = tool_call_id

        # Handle Task delegation completion for memory hooks and response tracking
        if tool_name == "Task":
            session_id = event.get("session_id", "")
            agent_type = self.hook_handler._get_delegation_agent_type(session_id)

            # Trigger memory post-delegation hook
            try:
                mhm = getattr(self.hook_handler, "memory_hook_manager", None)
                if mhm and hasattr(mhm, "trigger_post_delegation_hook"):
                    mhm.trigger_post_delegation_hook(agent_type, event, session_id)
            except Exception:  # nosec B110
                # Memory hooks are optional
                pass

            # Track agent response if response tracking is enabled
            try:
                rtm = getattr(self.hook_handler, "response_tracking_manager", None)
                if rtm and hasattr(rtm, "track_agent_response"):
                    delegation_requests = getattr(
                        self.hook_handler, "delegation_requests", {}
                    )
                    rtm.track_agent_response(
                        session_id, agent_type, event, delegation_requests
                    )
            except Exception:  # nosec B110
                # Response tracking is optional
                pass

        self.hook_handler._emit_socketio_event("", "post_tool", post_tool_data)
