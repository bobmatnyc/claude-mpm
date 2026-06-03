#!/usr/bin/env python3
"""Subagent event handlers (SubagentStop, SubagentStart, response tracking).

Extracted from ``event_handlers.EventHandlers`` as part of the #509 refactor.
Behavior is preserved verbatim; only the surrounding structure has changed.

References
----------
SPEC-HOOKS-09~1 : docs/specs/hooks.md#SPEC-HOOKS-09~1
"""

from datetime import UTC, datetime

from .base import DEBUG, BaseEventHandler, _log


class SubagentHandler:
    """Handle SubagentStop and SubagentStart events.

    :spec: SPEC-HOOKS-09~1
    """

    def __init__(self, base: BaseEventHandler):
        self.base = base
        self.hook_handler = base.hook_handler

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
            request_info = delegation_requests.get(session_id)  # nosec B113

            # If exact match fails, try partial matching
            if not request_info and session_id:
                if DEBUG:
                    _log(f"  - Trying fuzzy match for session {session_id[:16]}...")
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
                            _log(f"  - ✅ Fuzzy match found: {stored_sid[:16]}...")
                        request_info = delegation_requests.get(stored_sid)  # nosec B113
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
                    "timestamp": datetime.now(UTC).isoformat(),
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
                        _log(
                            f"✅ Tracked {agent_type} agent response on SubagentStop: {file_path.name}"
                        )

                # Clean up the request data
                delegation_requests = getattr(
                    self.hook_handler, "delegation_requests", {}
                )
                if session_id in delegation_requests:
                    del delegation_requests[session_id]

            elif DEBUG:
                _log(
                    f"No request data for SubagentStop session {session_id[:8]}..., agent: {agent_type}"
                )

        except Exception as e:
            if DEBUG:
                _log(f"❌ Failed to track response on SubagentStop: {e}")

    def handle_subagent_start_fast(self, event):
        """Handle SubagentStart events with proper agent type extraction.

        WHY separate from SessionStart:
        - SubagentStart contains agent-specific information
        - Frontend needs agent_type to create distinct agent nodes
        - Multiple engineers should show as separate nodes in hierarchy
        - Research agents must appear in the agent hierarchy

        Unlike SessionStart, SubagentStart events contain agent-specific
        information that must be preserved and emitted to the dashboard.
        """
        session_id = event.get("session_id", "")

        # Extract agent type from event - Claude provides this in SubagentStart
        # Try multiple possible field names for compatibility
        agent_type = event.get("agent_type") or event.get("subagent_type") or "unknown"

        # Generate unique agent ID combining type and session
        agent_id = event.get("agent_id", f"{agent_type}_{session_id[:8]}")

        # Get working directory and git branch
        working_dir = event.get("cwd", "")
        git_branch = (
            self.base._get_git_branch(working_dir) if working_dir else "Unknown"
        )

        # Build subagent start data with all required fields
        subagent_start_data = {
            "session_id": session_id,
            "agent_type": agent_type,
            "agent_id": agent_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "hook_event_name": "SubagentStart",  # Preserve correct hook name
            "working_directory": working_dir,
            "git_branch": git_branch,
        }

        # Debug logging
        if DEBUG:
            _log(
                f"Hook handler: SubagentStart - agent_type='{agent_type}', agent_id='{agent_id}', session_id='{session_id[:16]}...'"
            )

        # Emit to /hook namespace as subagent_start (NOT session_start!)
        self.hook_handler._emit_socketio_event(
            "", "subagent_start", subagent_start_data
        )
