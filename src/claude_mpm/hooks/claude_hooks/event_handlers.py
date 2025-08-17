#!/usr/bin/env python3
"""Event handlers for Claude Code hook handler.

This module provides individual event handlers for different types of
Claude Code hook events.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from .tool_analysis import (
    assess_security_risk,
    calculate_duration,
    classify_tool_operation,
    extract_tool_parameters,
    extract_tool_results,
)

# Debug mode
DEBUG = os.environ.get("CLAUDE_MPM_HOOK_DEBUG", "true").lower() != "false"

# Import constants for configuration
try:
    from claude_mpm.core.constants import TimeoutConfig
except ImportError:
    # Fallback values if constants module not available
    class TimeoutConfig:
        QUICK_TIMEOUT = 2.0


class EventHandlers:
    """Collection of event handlers for different Claude Code hook events."""

    def __init__(self, hook_handler):
        """Initialize with reference to the main hook handler."""
        self.hook_handler = hook_handler

    def handle_user_prompt_fast(self, event):
        """Handle user prompt with comprehensive data capture.

        WHY enhanced data capture:
        - Provides full context for debugging and monitoring
        - Captures prompt text, working directory, and session context
        - Enables better filtering and analysis in dashboard
        """
        prompt = event.get("prompt", "")

        # Skip /mpm commands to reduce noise unless debug is enabled
        if prompt.startswith("/mpm") and not DEBUG:
            return

        # Get working directory and git branch
        working_dir = event.get("cwd", "")
        git_branch = self._get_git_branch(working_dir) if working_dir else "Unknown"

        # Extract comprehensive prompt data
        prompt_data = {
            "prompt_text": prompt,
            "prompt_preview": prompt[:200] if len(prompt) > 200 else prompt,
            "prompt_length": len(prompt),
            "session_id": event.get("session_id", ""),
            "working_directory": working_dir,
            "git_branch": git_branch,
            "timestamp": datetime.now().isoformat(),
            "is_command": prompt.startswith("/"),
            "contains_code": "```" in prompt
            or "python" in prompt.lower()
            or "javascript" in prompt.lower(),
            "urgency": (
                "high"
                if any(
                    word in prompt.lower() for word in ["urgent", "error", "bug", "fix", "broken"]
                )
                else "normal"
            ),
        }

        # Store prompt for comprehensive response tracking if enabled
        if (
            self.hook_handler.response_tracking_manager.response_tracking_enabled
            and self.hook_handler.response_tracking_manager.track_all_interactions
        ):
            session_id = event.get("session_id", "")
            if session_id:
                self.hook_handler.pending_prompts[session_id] = {
                    "prompt": prompt,
                    "timestamp": datetime.now().isoformat(),
                    "working_directory": working_dir,
                }
                if DEBUG:
                    print(
                        f"Stored prompt for comprehensive tracking: session {session_id[:8]}...",
                        file=sys.stderr,
                    )

        # Emit to /hook namespace
        self.hook_handler._emit_socketio_event("/hook", "user_prompt", prompt_data)

    def handle_pre_tool_fast(self, event):
        """Handle pre-tool use with comprehensive data capture.

        WHY comprehensive capture:
        - Captures tool parameters for debugging and security analysis
        - Provides context about what Claude is about to do
        - Enables pattern analysis and security monitoring
        """
        # Enhanced debug logging for session correlation
        session_id = event.get("session_id", "")
        if DEBUG:

            print(
                f"  - session_id: {session_id[:16] if session_id else 'None'}...", file=sys.stderr
            )
            print(f"  - event keys: {list(event.keys())}", file=sys.stderr)

        tool_name = event.get("tool_name", "")
        tool_input = event.get("tool_input", {})

        # Extract key parameters based on tool type
        tool_params = extract_tool_parameters(tool_name, tool_input)

        # Classify tool operation
        operation_type = classify_tool_operation(tool_name, tool_input)

        # Get working directory and git branch
        working_dir = event.get("cwd", "")
        git_branch = self._get_git_branch(working_dir) if working_dir else "Unknown"

        pre_tool_data = {
            "tool_name": tool_name,
            "operation_type": operation_type,
            "tool_parameters": tool_params,
            "session_id": event.get("session_id", ""),
            "working_directory": working_dir,
            "git_branch": git_branch,
            "timestamp": datetime.now().isoformat(),
            "parameter_count": len(tool_input) if isinstance(tool_input, dict) else 0,
            "is_file_operation": tool_name in ["Write", "Edit", "MultiEdit", "Read", "LS", "Glob"],
            "is_execution": tool_name in ["Bash", "NotebookEdit"],
            "is_delegation": tool_name == "Task",
            "security_risk": assess_security_risk(tool_name, tool_input),
        }

        # Add delegation-specific data if this is a Task tool
        if tool_name == "Task" and isinstance(tool_input, dict):
            self._handle_task_delegation(tool_input, pre_tool_data, session_id)

        self.hook_handler._emit_socketio_event("/hook", "pre_tool", pre_tool_data)

    def _handle_task_delegation(self, tool_input: dict, pre_tool_data: dict, session_id: str):
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
            # Fallback to simple normalization
            agent_type = (
                raw_agent_type.lower().replace("_", "-")
                if raw_agent_type != "unknown"
                else "unknown"
            )

        pre_tool_data["delegation_details"] = {
            "agent_type": agent_type,
            "original_agent_type": raw_agent_type,  # Keep original for debugging
            "prompt": tool_input.get("prompt", ""),
            "description": tool_input.get("description", ""),
            "task_preview": (tool_input.get("prompt", "") or tool_input.get("description", ""))[
                :100
            ],
        }

        # Track this delegation for SubagentStop correlation and response tracking
        if DEBUG:

            print(
                f"  - session_id: {session_id[:16] if session_id else 'None'}...", file=sys.stderr
            )
            print(f"  - agent_type: {agent_type}", file=sys.stderr)
            print(f"  - raw_agent_type: {raw_agent_type}", file=sys.stderr)

        if session_id and agent_type != "unknown":
            # Prepare request data for response tracking correlation
            request_data = {
                "prompt": tool_input.get("prompt", ""),
                "description": tool_input.get("description", ""),
                "agent_type": agent_type,
            }
            self.hook_handler._track_delegation(session_id, agent_type, request_data)

            if DEBUG:
                print(f"  - Delegation tracked successfully", file=sys.stderr)
                print(f"  - Request data keys: {list(request_data.keys())}", file=sys.stderr)
                print(
                    f"  - delegation_requests size: {len(self.hook_handler.delegation_requests)}",
                    file=sys.stderr,
                )

            # Log important delegations for debugging
            if DEBUG or agent_type in ["research", "engineer", "qa", "documentation"]:
                print(
                    f"Hook handler: Task delegation started - agent: '{agent_type}', session: '{session_id}'",
                    file=sys.stderr,
                )

        # Trigger memory pre-delegation hook
        self.hook_handler.memory_hook_manager.trigger_pre_delegation_hook(
            agent_type, tool_input, session_id
        )

        # Emit a subagent_start event for better tracking
        subagent_start_data = {
            "agent_type": agent_type,
            "agent_id": f"{agent_type}_{session_id}",
            "session_id": session_id,
            "prompt": tool_input.get("prompt", ""),
            "description": tool_input.get("description", ""),
            "timestamp": datetime.now().isoformat(),
            "hook_event_name": "SubagentStart",  # For dashboard compatibility
        }
        self.hook_handler._emit_socketio_event("/hook", "subagent_start", subagent_start_data)

    def _get_git_branch(self, working_dir: str = None) -> str:
        """Get git branch for the given directory with caching."""
        # Use current working directory if not specified
        if not working_dir:
            working_dir = os.getcwd()

        # Check cache first (cache for 30 seconds)
        current_time = datetime.now().timestamp()
        cache_key = working_dir

        if (
            cache_key in self.hook_handler._git_branch_cache
            and cache_key in self.hook_handler._git_branch_cache_time
            and current_time - self.hook_handler._git_branch_cache_time[cache_key] < 30
        ):
            return self.hook_handler._git_branch_cache[cache_key]

        # Try to get git branch
        try:
            # Change to the working directory temporarily
            original_cwd = os.getcwd()
            os.chdir(working_dir)

            # Run git command to get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=TimeoutConfig.QUICK_TIMEOUT,  # Quick timeout to avoid hanging
            )

            # Restore original directory
            os.chdir(original_cwd)

            if result.returncode == 0 and result.stdout.strip():
                branch = result.stdout.strip()
                # Cache the result
                self.hook_handler._git_branch_cache[cache_key] = branch
                self.hook_handler._git_branch_cache_time[cache_key] = current_time
                return branch
            else:
                # Not a git repository or no branch
                self.hook_handler._git_branch_cache[cache_key] = "Unknown"
                self.hook_handler._git_branch_cache_time[cache_key] = current_time
                return "Unknown"

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
            OSError,
        ):
            # Git not available or command failed
            self.hook_handler._git_branch_cache[cache_key] = "Unknown"
            self.hook_handler._git_branch_cache_time[cache_key] = current_time
            return "Unknown"

    def handle_post_tool_fast(self, event):
        """Handle post-tool use with comprehensive data capture.

        WHY comprehensive capture:
        - Captures execution results and success/failure status
        - Provides duration and performance metrics
        - Enables pattern analysis of tool usage and success rates
        """
        tool_name = event.get("tool_name", "")
        exit_code = event.get("exit_code", 0)

        # Extract result data
        result_data = extract_tool_results(event)

        # Calculate duration if timestamps are available
        duration = calculate_duration(event)

        # Get working directory and git branch
        working_dir = event.get("cwd", "")
        git_branch = self._get_git_branch(working_dir) if working_dir else "Unknown"

        post_tool_data = {
            "tool_name": tool_name,
            "exit_code": exit_code,
            "success": exit_code == 0,
            "status": "success" if exit_code == 0 else "blocked" if exit_code == 2 else "error",
            "duration_ms": duration,
            "result_summary": result_data,
            "session_id": event.get("session_id", ""),
            "working_directory": working_dir,
            "git_branch": git_branch,
            "timestamp": datetime.now().isoformat(),
            "has_output": bool(result_data.get("output")),
            "has_error": bool(result_data.get("error")),
            "output_size": (
                len(str(result_data.get("output", ""))) if result_data.get("output") else 0
            ),
        }

        # Handle Task delegation completion for memory hooks and response tracking
        if tool_name == "Task":
            session_id = event.get("session_id", "")
            agent_type = self.hook_handler._get_delegation_agent_type(session_id)

            # Trigger memory post-delegation hook
            self.hook_handler.memory_hook_manager.trigger_post_delegation_hook(
                agent_type, event, session_id
            )

            # Track agent response if response tracking is enabled
            self.hook_handler.response_tracking_manager.track_agent_response(
                session_id, agent_type, event, self.hook_handler.delegation_requests
            )

        self.hook_handler._emit_socketio_event("/hook", "post_tool", post_tool_data)

    def handle_notification_fast(self, event):
        """Handle notification events from Claude.

        WHY enhanced notification capture:
        - Provides visibility into Claude's status and communication flow
        - Captures notification type, content, and context for monitoring
        - Enables pattern analysis of Claude's notification behavior
        - Useful for debugging communication issues and user experience
        """
        notification_type = event.get("notification_type", "unknown")
        message = event.get("message", "")

        # Get working directory and git branch
        working_dir = event.get("cwd", "")
        git_branch = self._get_git_branch(working_dir) if working_dir else "Unknown"

        notification_data = {
            "notification_type": notification_type,
            "message": message,
            "message_preview": message[:200] if len(message) > 200 else message,
            "message_length": len(message),
            "session_id": event.get("session_id", ""),
            "working_directory": working_dir,
            "git_branch": git_branch,
            "timestamp": datetime.now().isoformat(),
            "is_user_input_request": "input" in message.lower() or "waiting" in message.lower(),
            "is_error_notification": "error" in message.lower() or "failed" in message.lower(),
            "is_status_update": any(
                word in message.lower()
                for word in ["processing", "analyzing", "working", "thinking"]
            ),
        }

        # Emit to /hook namespace
        self.hook_handler._emit_socketio_event("/hook", "notification", notification_data)

    def handle_stop_fast(self, event):
        """Handle stop events when Claude processing stops.

        WHY comprehensive stop capture:
        - Provides visibility into Claude's session lifecycle
        - Captures stop reason and context for analysis
        - Enables tracking of session completion patterns
        - Useful for understanding when and why Claude stops responding
        """
        session_id = event.get("session_id", "")

        # Extract metadata for this stop event
        metadata = self._extract_stop_metadata(event)

        # Debug logging
        if DEBUG:
            self._log_stop_event_debug(event, session_id, metadata)

        # Track response if enabled
        self.hook_handler.response_tracking_manager.track_stop_response(
            event, session_id, metadata, self.hook_handler.pending_prompts
        )

        # Emit stop event to Socket.IO
        self._emit_stop_event(event, session_id, metadata)

    def _extract_stop_metadata(self, event: dict) -> dict:
        """Extract metadata from stop event."""
        working_dir = event.get("cwd", "")
        return {
            "timestamp": datetime.now().isoformat(),
            "working_directory": working_dir,
            "git_branch": self._get_git_branch(working_dir) if working_dir else "Unknown",
            "event_type": "stop",
            "reason": event.get("reason", "unknown"),
            "stop_type": event.get("stop_type", "normal"),
        }

    def _log_stop_event_debug(self, event: dict, session_id: str, metadata: dict) -> None:
        """Log debug information for stop events."""

        print(
            f"  - response_tracking_enabled: {self.hook_handler.response_tracking_manager.response_tracking_enabled}",
            file=sys.stderr,
        )
        print(
            f"  - response_tracker exists: {self.hook_handler.response_tracking_manager.response_tracker is not None}",
            file=sys.stderr,
        )
        print(f"  - session_id: {session_id[:8] if session_id else 'None'}...", file=sys.stderr)
        print(f"  - reason: {metadata['reason']}", file=sys.stderr)
        print(f"  - stop_type: {metadata['stop_type']}", file=sys.stderr)

    def _emit_stop_event(self, event: dict, session_id: str, metadata: dict) -> None:
        """Emit stop event data to Socket.IO."""
        stop_data = {
            "reason": metadata["reason"],
            "stop_type": metadata["stop_type"],
            "session_id": session_id,
            "working_directory": metadata["working_directory"],
            "git_branch": metadata["git_branch"],
            "timestamp": metadata["timestamp"],
            "is_user_initiated": metadata["reason"] in ["user_stop", "user_cancel", "interrupt"],
            "is_error_stop": metadata["reason"] in ["error", "timeout", "failed"],
            "is_completion_stop": metadata["reason"] in ["completed", "finished", "done"],
            "has_output": bool(event.get("final_output")),
        }

        # Emit to /hook namespace
        self.hook_handler._emit_socketio_event("/hook", "stop", stop_data)

    def handle_subagent_stop_fast(self, event):
        """Handle subagent stop events with improved agent type detection."""
        # Enhanced debug logging for session correlation
        session_id = event.get("session_id", "")
        if DEBUG:

            print(
                f"  - session_id: {session_id[:16] if session_id else 'None'}...", file=sys.stderr
            )
            print(f"  - event keys: {list(event.keys())}", file=sys.stderr)
            print(
                f"  - delegation_requests size: {len(self.hook_handler.delegation_requests)}",
                file=sys.stderr,
            )

        # First try to get agent type from our tracking
        agent_type = (
            self.hook_handler._get_delegation_agent_type(session_id) if session_id else "unknown"
        )

        # Fall back to event data if tracking didn't have it
        if agent_type == "unknown":
            agent_type = event.get("agent_type", event.get("subagent_type", "unknown"))

        agent_id = event.get("agent_id", event.get("subagent_id", ""))
        reason = event.get("reason", event.get("stop_reason", "unknown"))

        # Try to infer agent type from other fields if still unknown
        if agent_type == "unknown" and "task" in event:
            task_desc = str(event.get("task", "")).lower()
            if "research" in task_desc:
                agent_type = "research"
            elif "engineer" in task_desc or "code" in task_desc:
                agent_type = "engineer"
            elif "pm" in task_desc or "project" in task_desc:
                agent_type = "pm"

        # Always log SubagentStop events for debugging
        if DEBUG or agent_type != "unknown":
            print(
                f"Hook handler: Processing SubagentStop - agent: '{agent_type}', session: '{session_id}', reason: '{reason}'",
                file=sys.stderr,
            )

        # Get working directory and git branch
        working_dir = event.get("cwd", "")
        git_branch = self._get_git_branch(working_dir) if working_dir else "Unknown"

        # Try to extract structured response from output if available
        output = event.get("output", "")
        structured_response = None
        if output:
            try:
                json_match = re.search(r"```json\s*(\{.*?\})\s*```", str(output), re.DOTALL)
                if json_match:
                    structured_response = json.loads(json_match.group(1))
                    if DEBUG:
                        print(
                            f"Extracted structured response from {agent_type} agent in SubagentStop",
                            file=sys.stderr,
                        )
            except (json.JSONDecodeError, AttributeError):
                pass  # No structured response, that's okay

        # Handle response tracking with fuzzy matching
        self._handle_subagent_response_tracking(
            session_id, agent_type, reason, output, structured_response, working_dir, git_branch
        )

        # Prepare subagent stop data
        subagent_stop_data = {
            "agent_type": agent_type,
            "agent_id": agent_id,
            "reason": reason,
            "session_id": session_id,
            "working_directory": working_dir,
            "git_branch": git_branch,
            "timestamp": datetime.now().isoformat(),
            "is_successful_completion": reason in ["completed", "finished", "done"],
            "is_error_termination": reason in ["error", "timeout", "failed", "blocked"],
            "is_delegation_related": agent_type
            in ["research", "engineer", "pm", "ops", "qa", "documentation", "security"],
            "has_results": bool(event.get("results") or event.get("output")),
            "duration_context": event.get("duration_ms"),
            "hook_event_name": "SubagentStop",  # Explicitly set for dashboard
        }

        # Add structured response data if available
        if structured_response:
            subagent_stop_data["structured_response"] = {
                "task_completed": structured_response.get("task_completed", False),
                "instructions": structured_response.get("instructions", ""),
                "results": structured_response.get("results", ""),
                "files_modified": structured_response.get("files_modified", []),
                "tools_used": structured_response.get("tools_used", []),
                "remember": structured_response.get("remember"),
            }

        # Debug log the processed data
        if DEBUG:
            print(
                f"SubagentStop processed data: agent_type='{agent_type}', session_id='{session_id}'",
                file=sys.stderr,
            )

        # Emit to /hook namespace with high priority
        self.hook_handler._emit_socketio_event("/hook", "subagent_stop", subagent_stop_data)

    def _handle_subagent_response_tracking(
        self,
        session_id: str,
        agent_type: str,
        reason: str,
        output: str,
        structured_response: dict,
        working_dir: str,
        git_branch: str,
    ):
        """Handle response tracking for subagent stop events with fuzzy matching."""
        if not (
            self.hook_handler.response_tracking_manager.response_tracking_enabled
            and self.hook_handler.response_tracking_manager.response_tracker
        ):
            return

        try:
            # Get the original request data (with fuzzy matching fallback)
            request_info = self.hook_handler.delegation_requests.get(session_id)

            # If exact match fails, try partial matching
            if not request_info and session_id:
                if DEBUG:
                    print(
                        f"  - Trying fuzzy match for session {session_id[:16]}...", file=sys.stderr
                    )
                # Try to find a session that matches the first 8-16 characters
                for stored_sid in list(self.hook_handler.delegation_requests.keys()):
                    if (
                        stored_sid.startswith(session_id[:8])
                        or session_id.startswith(stored_sid[:8])
                        or (
                            len(session_id) >= 16
                            and len(stored_sid) >= 16
                            and stored_sid[:16] == session_id[:16]
                        )
                    ):
                        if DEBUG:
                            print(
                                f"  - ✅ Fuzzy match found: {stored_sid[:16]}...", file=sys.stderr
                            )
                        request_info = self.hook_handler.delegation_requests.get(stored_sid)
                        # Update the key to use the current session_id for consistency
                        if request_info:
                            self.hook_handler.delegation_requests[session_id] = request_info
                            # Optionally remove the old key to avoid duplicates
                            if stored_sid != session_id:
                                del self.hook_handler.delegation_requests[stored_sid]
                        break

            if request_info:
                # Use the output as the response
                response_text = (
                    str(output) if output else f"Agent {agent_type} completed with reason: {reason}"
                )

                # Get the original request
                original_request = request_info.get("request", {})
                prompt = original_request.get("prompt", "")
                description = original_request.get("description", "")

                # Combine prompt and description
                full_request = prompt
                if description and description != prompt:
                    if full_request:
                        full_request += f"\n\nDescription: {description}"
                    else:
                        full_request = description

                if not full_request:
                    full_request = f"Task delegation to {agent_type} agent"

                # Prepare metadata
                metadata = {
                    "exit_code": 0,  # SubagentStop doesn't have exit_code
                    "success": reason in ["completed", "finished", "done"],
                    "has_error": reason in ["error", "timeout", "failed", "blocked"],
                    "working_directory": working_dir,
                    "git_branch": git_branch,
                    "timestamp": datetime.now().isoformat(),
                    "event_type": "subagent_stop",
                    "reason": reason,
                    "original_request_timestamp": request_info.get("timestamp"),
                }

                # Add structured response if available
                if structured_response:
                    metadata["structured_response"] = structured_response
                    metadata["task_completed"] = structured_response.get("task_completed", False)

                # Track the response
                file_path = (
                    self.hook_handler.response_tracking_manager.response_tracker.track_response(
                        agent_name=agent_type,
                        request=full_request,
                        response=response_text,
                        session_id=session_id,
                        metadata=metadata,
                    )
                )

                if file_path and DEBUG:
                    print(
                        f"✅ Tracked {agent_type} agent response on SubagentStop: {file_path.name}",
                        file=sys.stderr,
                    )

                # Clean up the request data
                if session_id in self.hook_handler.delegation_requests:
                    del self.hook_handler.delegation_requests[session_id]

            elif DEBUG:
                print(
                    f"No request data for SubagentStop session {session_id[:8]}..., agent: {agent_type}",
                    file=sys.stderr,
                )

        except Exception as e:
            if DEBUG:
                print(f"❌ Failed to track response on SubagentStop: {e}", file=sys.stderr)

    def handle_assistant_response(self, event):
        """Handle assistant response events for comprehensive response tracking."""
        self.hook_handler.response_tracking_manager.track_assistant_response(
            event, self.hook_handler.pending_prompts
        )
