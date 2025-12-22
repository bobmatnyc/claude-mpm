#!/usr/bin/env python3
"""Event handlers for Claude Code hook handler.

This module provides individual event handlers for different types of
Claude Code hook events.
"""

import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Import tool analysis with fallback for direct execution
try:
    # Try relative import first (when imported as module)
    from .tool_analysis import (
        assess_security_risk,
        calculate_duration,
        classify_tool_operation,
        extract_tool_parameters,
        extract_tool_results,
    )
except ImportError:
    # Fall back to direct import (when parent script is run directly)
    from tool_analysis import (
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "is_command": prompt.startswith("/"),
            "contains_code": "```" in prompt
            or "python" in prompt.lower()
            or "javascript" in prompt.lower(),
            "urgency": (
                "high"
                if any(
                    word in prompt.lower()
                    for word in ["urgent", "error", "bug", "fix", "broken"]
                )
                else "normal"
            ),
        }

        # Store prompt for comprehensive response tracking if enabled
        try:
            rtm = getattr(self.hook_handler, "response_tracking_manager", None)
            if (
                rtm
                and getattr(rtm, "response_tracking_enabled", False)
                and getattr(rtm, "track_all_interactions", False)
            ):
                session_id = event.get("session_id", "")
                if session_id:
                    pending_prompts = getattr(self.hook_handler, "pending_prompts", {})
                    pending_prompts[session_id] = {
                        "prompt": prompt,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "working_directory": working_dir,
                    }
                    if DEBUG:
                        print(
                            f"Stored prompt for comprehensive tracking: session {session_id[:8]}...",
                            file=sys.stderr,
                        )
        except Exception:
            # Response tracking is optional - silently continue if it fails
            pass

        # Emit normalized event (namespace no longer needed with normalized events)
        self.hook_handler._emit_socketio_event("", "user_prompt", prompt_data)

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
                f"  - session_id: {session_id[:16] if session_id else 'None'}...",
                file=sys.stderr,
            )
            print(f"  - event keys: {list(event.keys())}", file=sys.stderr)

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
        git_branch = self._get_git_branch(working_dir) if working_dir else "Unknown"

        timestamp = datetime.now(timezone.utc).isoformat()

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
            from .correlation_manager import CorrelationManager

            CorrelationManager.store(session_id, tool_call_id, tool_name)
            if DEBUG:
                print(
                    f"  - Generated tool_call_id: {tool_call_id[:8]}... for session {session_id[:8]}...",
                    file=sys.stderr,
                )

        # Add delegation-specific data if this is a Task tool
        if tool_name == "Task" and isinstance(tool_input, dict):
            self._handle_task_delegation(tool_input, pre_tool_data, session_id)

        self.hook_handler._emit_socketio_event("", "pre_tool", pre_tool_data)

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
            "task_preview": (
                tool_input.get("prompt", "") or tool_input.get("description", "")
            )[:100],
        }

        # Track this delegation for SubagentStop correlation and response tracking
        if DEBUG:
            print(
                f"  - session_id: {session_id[:16] if session_id else 'None'}...",
                file=sys.stderr,
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
                print("  - Delegation tracked successfully", file=sys.stderr)
                print(
                    f"  - Request data keys: {list(request_data.keys())}",
                    file=sys.stderr,
                )
                delegation_requests = getattr(
                    self.hook_handler, "delegation_requests", {}
                )
                print(
                    f"  - delegation_requests size: {len(delegation_requests)}",
                    file=sys.stderr,
                )

            # Log important delegations for debugging
            if DEBUG or agent_type in ["research", "engineer", "qa", "documentation"]:
                print(
                    f"Hook handler: Task delegation started - agent: '{agent_type}', session: '{session_id}'",
                    file=sys.stderr,
                )

        # Trigger memory pre-delegation hook
        try:
            mhm = getattr(self.hook_handler, "memory_hook_manager", None)
            if mhm and hasattr(mhm, "trigger_pre_delegation_hook"):
                mhm.trigger_pre_delegation_hook(agent_type, tool_input, session_id)
        except Exception:
            # Memory hooks are optional
            pass

        # Emit a subagent_start event for better tracking
        subagent_start_data = {
            "agent_type": agent_type,
            "agent_id": f"{agent_type}_{session_id}",
            "session_id": session_id,
            "prompt": tool_input.get("prompt", ""),
            "description": tool_input.get("description", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hook_event_name": "SubagentStart",  # For dashboard compatibility
        }
        self.hook_handler._emit_socketio_event(
            "", "subagent_start", subagent_start_data
        )

        # Log agent prompt if LogManager is available
        try:
            from claude_mpm.core.log_manager import get_log_manager

            log_manager = get_log_manager()

            # Prepare prompt content
            prompt_content = tool_input.get("prompt", "")
            if not prompt_content:
                prompt_content = tool_input.get("description", "")

            if prompt_content:
                import asyncio

                # Prepare metadata
                metadata = {
                    "agent_type": agent_type,
                    "agent_id": f"{agent_type}_{session_id}",
                    "session_id": session_id,
                    "delegation_context": {
                        "description": tool_input.get("description", ""),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                }

                # Log the agent prompt asynchronously
                try:
                    loop = asyncio.get_running_loop()
                    _task = asyncio.create_task(
                        log_manager.log_prompt(
                            f"agent_{agent_type}", prompt_content, metadata
                        )
                    )  # Fire-and-forget logging (ephemeral hook process)
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
                    print(f"  - Agent prompt logged for {agent_type}", file=sys.stderr)
        except Exception as e:
            if DEBUG:
                print(f"  - Could not log agent prompt: {e}", file=sys.stderr)

    def _get_git_branch(self, working_dir: Optional[str] = None) -> str:
        """Get git branch for the given directory with caching."""
        # Use current working directory if not specified
        if not working_dir:
            working_dir = Path.cwd()

        # Check cache first (cache for 300 seconds = 5 minutes)
        # WHY 5 minutes: Git branches rarely change during development sessions,
        # reducing subprocess overhead significantly without staleness issues
        current_time = datetime.now(timezone.utc).timestamp()
        cache_key = working_dir

        if (
            cache_key in self.hook_handler._git_branch_cache
            and cache_key in self.hook_handler._git_branch_cache_time
            and current_time - self.hook_handler._git_branch_cache_time[cache_key] < 300
        ):
            return self.hook_handler._git_branch_cache[cache_key]

        # Try to get git branch
        try:
            # Change to the working directory temporarily
            original_cwd = Path.cwd()
            os.chdir(working_dir)

            # Run git command to get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=TimeoutConfig.QUICK_TIMEOUT,
                check=False,  # Quick timeout to avoid hanging
            )

            # Restore original directory
            os.chdir(original_cwd)

            if result.returncode == 0 and result.stdout.strip():
                branch = result.stdout.strip()
                # Cache the result
                self.hook_handler._git_branch_cache[cache_key] = branch
                self.hook_handler._git_branch_cache_time[cache_key] = current_time
                return branch
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
        session_id = event.get("session_id", "")

        # Extract result data
        result_data = extract_tool_results(event)

        # Calculate duration if timestamps are available
        duration = calculate_duration(event)

        # Get working directory and git branch
        working_dir = event.get("cwd", "")
        git_branch = self._get_git_branch(working_dir) if working_dir else "Unknown"

        # Retrieve tool_call_id using CorrelationManager for cross-process correlation
        from .correlation_manager import CorrelationManager

        tool_call_id = CorrelationManager.retrieve(session_id) if session_id else None
        if DEBUG and tool_call_id:
            print(
                f"  - Retrieved tool_call_id: {tool_call_id[:8]}... for session {session_id[:8]}...",
                file=sys.stderr,
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
            except Exception:
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
            except Exception:
                # Response tracking is optional
                pass

        self.hook_handler._emit_socketio_event("", "post_tool", post_tool_data)

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
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "is_user_input_request": "input" in message.lower()
            or "waiting" in message.lower(),
            "is_error_notification": "error" in message.lower()
            or "failed" in message.lower(),
            "is_status_update": any(
                word in message.lower()
                for word in ["processing", "analyzing", "working", "thinking"]
            ),
        }

        # Emit normalized event
        self.hook_handler._emit_socketio_event("", "notification", notification_data)

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
        try:
            rtm = getattr(self.hook_handler, "response_tracking_manager", None)
            if rtm and hasattr(rtm, "track_stop_response"):
                pending_prompts = getattr(self.hook_handler, "pending_prompts", {})
                rtm.track_stop_response(event, session_id, metadata, pending_prompts)
        except Exception:
            # Response tracking is optional
            pass

        # Emit stop event to Socket.IO
        self._emit_stop_event(event, session_id, metadata)

    def _extract_stop_metadata(self, event: dict) -> dict:
        """Extract metadata from stop event."""
        working_dir = event.get("cwd", "")
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "working_directory": working_dir,
            "git_branch": (
                self._get_git_branch(working_dir) if working_dir else "Unknown"
            ),
            "event_type": "stop",
            "reason": event.get("reason", "unknown"),
            "stop_type": event.get("stop_type", "normal"),
        }

    def _log_stop_event_debug(
        self, event: dict, session_id: str, metadata: dict
    ) -> None:
        """Log debug information for stop events."""
        try:
            rtm = getattr(self.hook_handler, "response_tracking_manager", None)
            tracking_enabled = (
                getattr(rtm, "response_tracking_enabled", False) if rtm else False
            )
            tracker_exists = (
                getattr(rtm, "response_tracker", None) is not None if rtm else False
            )

            print(
                f"  - response_tracking_enabled: {tracking_enabled}",
                file=sys.stderr,
            )
            print(
                f"  - response_tracker exists: {tracker_exists}",
                file=sys.stderr,
            )
        except Exception:
            # If debug logging fails, just skip it
            pass

        print(
            f"  - session_id: {session_id[:8] if session_id else 'None'}...",
            file=sys.stderr,
        )
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
            "is_user_initiated": metadata["reason"]
            in ["user_stop", "user_cancel", "interrupt"],
            "is_error_stop": metadata["reason"] in ["error", "timeout", "failed"],
            "is_completion_stop": metadata["reason"]
            in ["completed", "finished", "done"],
            "has_output": bool(event.get("final_output")),
        }

        # Emit normalized event
        self.hook_handler._emit_socketio_event("", "stop", stop_data)

    def handle_subagent_stop_fast(self, event):
        """Handle subagent stop events by delegating to the specialized processor."""
        # Delegate to the specialized subagent processor
        if hasattr(self.hook_handler, "subagent_processor"):
            self.hook_handler.subagent_processor.process_subagent_stop(event)
        else:
            # Fallback to handle_subagent_stop if processor not available
            self.hook_handler.handle_subagent_stop(event)

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
        try:
            rtm = getattr(self.hook_handler, "response_tracking_manager", None)
            if not (
                rtm
                and getattr(rtm, "response_tracking_enabled", False)
                and getattr(rtm, "response_tracker", None)
            ):
                return
        except Exception:
            # Response tracking is optional
            return

        try:
            # Get the original request data (with fuzzy matching fallback)
            delegation_requests = getattr(self.hook_handler, "delegation_requests", {})
            request_info = delegation_requests.get(session_id)

            # If exact match fails, try partial matching
            if not request_info and session_id:
                if DEBUG:
                    print(
                        f"  - Trying fuzzy match for session {session_id[:16]}...",
                        file=sys.stderr,
                    )
                # Try to find a session that matches the first 8-16 characters
                for stored_sid in list(delegation_requests.keys()):
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
                                f"  - ✅ Fuzzy match found: {stored_sid[:16]}...",
                                file=sys.stderr,
                            )
                        request_info = delegation_requests.get(stored_sid)
                        # Update the key to use the current session_id for consistency
                        if request_info:
                            delegation_requests[session_id] = request_info
                            # Optionally remove the old key to avoid duplicates
                            if stored_sid != session_id:
                                del delegation_requests[stored_sid]
                        break

            if request_info:
                # Use the output as the response
                response_text = (
                    str(output)
                    if output
                    else f"Agent {agent_type} completed with reason: {reason}"
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
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "event_type": "subagent_stop",
                    "reason": reason,
                    "original_request_timestamp": request_info.get("timestamp"),
                }

                # Add structured response if available
                if structured_response:
                    metadata["structured_response"] = structured_response
                    metadata["task_completed"] = structured_response.get(
                        "task_completed", False
                    )

                # Track the response
                rtm = getattr(self.hook_handler, "response_tracking_manager", None)
                response_tracker = (
                    getattr(rtm, "response_tracker", None) if rtm else None
                )
                if response_tracker and hasattr(response_tracker, "track_response"):
                    file_path = response_tracker.track_response(
                        agent_name=agent_type,
                        request=full_request,
                        response=response_text,
                        session_id=session_id,
                        metadata=metadata,
                    )

                    if file_path and DEBUG:
                        print(
                            f"✅ Tracked {agent_type} agent response on SubagentStop: {file_path.name}",
                            file=sys.stderr,
                        )

                # Clean up the request data
                delegation_requests = getattr(
                    self.hook_handler, "delegation_requests", {}
                )
                if session_id in delegation_requests:
                    del delegation_requests[session_id]

            elif DEBUG:
                print(
                    f"No request data for SubagentStop session {session_id[:8]}..., agent: {agent_type}",
                    file=sys.stderr,
                )

        except Exception as e:
            if DEBUG:
                print(
                    f"❌ Failed to track response on SubagentStop: {e}", file=sys.stderr
                )

    def handle_assistant_response(self, event):
        """Handle assistant response events for comprehensive response tracking.

        WHY emit assistant response events:
        - Provides visibility into Claude's responses to user prompts
        - Captures response content and metadata for analysis
        - Enables tracking of conversation flow and response patterns
        - Essential for comprehensive monitoring of Claude interactions
        """
        # Track the response for logging
        try:
            rtm = getattr(self.hook_handler, "response_tracking_manager", None)
            if rtm and hasattr(rtm, "track_assistant_response"):
                pending_prompts = getattr(self.hook_handler, "pending_prompts", {})
                rtm.track_assistant_response(event, pending_prompts)
        except Exception:
            # Response tracking is optional
            pass

        # Get working directory and git branch
        working_dir = event.get("cwd", "")
        git_branch = self._get_git_branch(working_dir) if working_dir else "Unknown"

        # Extract response data
        response_text = event.get("response", "")
        session_id = event.get("session_id", "")

        # Prepare assistant response data for Socket.IO emission
        assistant_response_data = {
            "response_text": response_text,
            "response_preview": (
                response_text[:500] if len(response_text) > 500 else response_text
            ),
            "response_length": len(response_text),
            "session_id": session_id,
            "working_directory": working_dir,
            "git_branch": git_branch,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "contains_code": "```" in response_text,
            "contains_json": "```json" in response_text,
            "hook_event_name": "AssistantResponse",  # Explicitly set for dashboard
            "has_structured_response": bool(
                re.search(r"```json\s*\{.*?\}\s*```", response_text, re.DOTALL)
            ),
        }

        # Check if this is a response to a tracked prompt
        try:
            pending_prompts = getattr(self.hook_handler, "pending_prompts", {})
            if session_id in pending_prompts:
                prompt_data = pending_prompts[session_id]
                assistant_response_data["original_prompt"] = prompt_data.get(
                    "prompt", ""
                )[:200]
                assistant_response_data["prompt_timestamp"] = prompt_data.get(
                    "timestamp", ""
                )
                assistant_response_data["is_tracked_response"] = True
            else:
                assistant_response_data["is_tracked_response"] = False
        except Exception:
            # If prompt lookup fails, just mark as not tracked
            assistant_response_data["is_tracked_response"] = False

        # Debug logging
        if DEBUG:
            print(
                f"Hook handler: Processing AssistantResponse - session: '{session_id}', response_length: {len(response_text)}",
                file=sys.stderr,
            )

        # Emit normalized event
        self.hook_handler._emit_socketio_event(
            "", "assistant_response", assistant_response_data
        )

    def handle_session_start_fast(self, event):
        """Handle session start events for tracking conversation sessions.

        WHY track session starts:
        - Provides visibility into new conversation sessions
        - Enables tracking of session lifecycle and duration
        - Useful for monitoring concurrent sessions and resource usage
        """
        session_id = event.get("session_id", "")
        working_dir = event.get("cwd", "")
        git_branch = self._get_git_branch(working_dir) if working_dir else "Unknown"

        session_start_data = {
            "session_id": session_id,
            "working_directory": working_dir,
            "git_branch": git_branch,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hook_event_name": "SessionStart",
        }

        # Debug logging
        if DEBUG:
            print(
                f"Hook handler: Processing SessionStart - session: '{session_id}'",
                file=sys.stderr,
            )

        # Emit normalized event
        self.hook_handler._emit_socketio_event("", "session_start", session_start_data)
