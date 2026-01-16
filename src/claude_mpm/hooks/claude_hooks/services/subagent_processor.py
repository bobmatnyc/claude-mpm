"""Subagent response processing service for Claude hook handler.

This service handles:
- SubagentStop event processing
- Structured response extraction
- Response tracking and correlation
- Memory field processing
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Optional, Tuple

# Try to import _log from hook_handler, fall back to no-op
try:
    from claude_mpm.hooks.claude_hooks.hook_handler import _log
except ImportError:

    def _log(msg: str) -> None:
        pass  # Silent fallback


# Debug mode is enabled by default for better visibility into hook processing
DEBUG = os.environ.get("CLAUDE_MPM_HOOK_DEBUG", "true").lower() != "false"


class SubagentResponseProcessor:
    """Processes subagent responses and extracts structured data."""

    def __init__(self, state_manager, response_tracking_manager, connection_manager):
        """Initialize the subagent response processor.

        Args:
            state_manager: StateManagerService instance
            response_tracking_manager: ResponseTrackingManager instance
            connection_manager: ConnectionManagerService instance
        """
        self.state_manager = state_manager
        self.response_tracking_manager = response_tracking_manager
        self.connection_manager = connection_manager

    def process_subagent_stop(self, event: dict):
        """Handle subagent stop events with improved agent type detection.

        WHY comprehensive subagent stop capture:
        - Provides visibility into subagent lifecycle and delegation patterns
        - Captures agent type, ID, reason, and results for analysis
        - Enables tracking of delegation success/failure patterns
        - Useful for understanding subagent performance and reliability
        """
        # Enhanced debug logging for session correlation
        session_id = event.get("session_id", "")
        if DEBUG:
            _log(f"  - session_id: {session_id[:16] if session_id else 'None'}...")
            _log(f"  - event keys: {list(event.keys())}")
            _log(
                f"  - delegation_requests size: {len(self.state_manager.delegation_requests)}"
            )
            # Show all stored session IDs for comparison
            all_sessions = list(self.state_manager.delegation_requests.keys())
            if all_sessions:
                _log("  - Stored sessions (first 16 chars):")
                for sid in all_sessions[:10]:  # Show up to 10
                    _log(
                        f"    - {sid[:16]}... (agent: {self.state_manager.delegation_requests[sid].get('agent_type', 'unknown')})"
                    )
            else:
                _log("  - No stored sessions in delegation_requests!")

        # Get agent type and other basic info
        agent_type, agent_id, reason, agent_type_inferred = self._extract_basic_info(
            event, session_id
        )

        # Always log SubagentStop events for debugging
        if DEBUG or agent_type != "unknown":
            _log(
                f"Hook handler: Processing SubagentStop - agent: '{agent_type}', session: '{session_id}', reason: '{reason}'"
            )

        # Get working directory and git branch
        working_dir = event.get("cwd", "")
        git_branch = (
            self.state_manager.get_git_branch(working_dir) if working_dir else "Unknown"
        )

        # Try to extract structured response from output if available
        output = event.get("output", "")
        structured_response = self._extract_structured_response(output, agent_type)

        # Track agent response
        self._track_response(
            event,
            session_id,
            agent_type,
            reason,
            working_dir,
            git_branch,
            output,
            structured_response,
        )

        # Build subagent stop data for event emission
        subagent_stop_data = self._build_subagent_stop_data(
            event,
            session_id,
            agent_type,
            agent_id,
            reason,
            working_dir,
            git_branch,
            structured_response,
            agent_type_inferred,
        )

        # Debug log the processed data
        if DEBUG:
            _log(
                f"SubagentStop processed data: agent_type='{agent_type}', session_id='{session_id}'"
            )

        # Emit to default namespace (consistent with subagent_start)
        self.connection_manager.emit_event("", "subagent_stop", subagent_stop_data)

    def _extract_basic_info(
        self, event: dict, session_id: str
    ) -> Tuple[str, str, str, bool]:
        """Extract basic info from the event.

        Returns:
            Tuple of (agent_type, agent_id, reason, agent_type_inferred)
            - agent_type_inferred is True when defaulted to "pm"
        """
        agent_type_inferred = False

        # First try to get agent type from our tracking
        agent_type = (
            self.state_manager.get_delegation_agent_type(session_id)
            if session_id
            else "unknown"
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

        # Default to "pm" if still unknown (main conversation doesn't use Task tool)
        if agent_type == "unknown":
            agent_type = "pm"
            agent_type_inferred = True
            if DEBUG:
                _log("  - Inferred agent_type='pm' (no explicit type found)")

        return agent_type, agent_id, reason, agent_type_inferred

    def _extract_structured_response(
        self, output: str, agent_type: str
    ) -> Optional[dict]:
        """Extract structured JSON response from output."""
        if not output:
            return None

        try:
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", str(output), re.DOTALL)
            if json_match:
                structured_response = json.loads(json_match.group(1))
                if DEBUG:
                    _log(
                        f"Extracted structured response from {agent_type} agent in SubagentStop"
                    )

                # Log if MEMORIES field is present
                if structured_response.get("MEMORIES") and DEBUG:
                    memories_count = len(structured_response["MEMORIES"])
                    _log(
                        f"Agent {agent_type} returned MEMORIES field with {memories_count} items"
                    )

                return structured_response
        except (json.JSONDecodeError, AttributeError):
            pass  # No structured response, that's okay

        return None

    def _track_response(
        self,
        event: dict,
        session_id: str,
        agent_type: str,
        reason: str,
        working_dir: str,
        git_branch: str,
        output: str,
        structured_response: Optional[dict],
    ):
        """Track the agent response if response tracking is enabled."""
        if DEBUG:
            _log(
                f"  - response_tracking_enabled: {self.response_tracking_manager.response_tracking_enabled}"
            )
            _log(
                f"  - response_tracker exists: {self.response_tracking_manager.response_tracker is not None}"
            )
            _log(f"  - session_id: {session_id[:16] if session_id else 'None'}...")
            _log(f"  - agent_type: {agent_type}")
            _log(f"  - reason: {reason}")

        if (
            self.response_tracking_manager.response_tracking_enabled
            and self.response_tracking_manager.response_tracker
        ):
            try:
                # Get the original request data (with fuzzy matching fallback)
                request_info = self.state_manager.find_matching_request(session_id)

                if DEBUG:
                    _log(f"  - request_info present: {bool(request_info)}")
                    if request_info:
                        _log("  - ✅ Found request data for response tracking")
                        _log(f"  - stored agent_type: {request_info.get('agent_type')}")
                        _log(
                            f"  - request keys: {list(request_info.get('request', {}).keys())}"
                        )
                    else:
                        _log(
                            f"  - ❌ No request data found for session {session_id[:16]}..."
                        )

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
                        "exit_code": event.get("exit_code", 0),
                        "success": reason in ["completed", "finished", "done"],
                        "has_error": reason
                        in ["error", "timeout", "failed", "blocked"],
                        "duration_ms": event.get("duration_ms"),
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

                        # Check for MEMORIES field and process if present
                        if structured_response.get("MEMORIES") and DEBUG:
                            memories = structured_response["MEMORIES"]
                            _log(
                                f"Found MEMORIES field in {agent_type} response with {len(memories)} items"
                            )
                            # The memory will be processed by extract_and_update_memory
                            # which is called by the memory hook service

                    # Track the response
                    file_path = (
                        self.response_tracking_manager.response_tracker.track_response(
                            agent_name=agent_type,
                            request=full_request,
                            response=response_text,
                            session_id=session_id,
                            metadata=metadata,
                        )
                    )

                    if file_path and DEBUG:
                        _log(
                            f"✅ Tracked {agent_type} agent response on SubagentStop: {file_path.name}"
                        )

                    # Clean up the request data
                    self.state_manager.remove_request(session_id)

                elif DEBUG:
                    _log(
                        f"No request data for SubagentStop session {session_id[:8]}..., agent: {agent_type}"
                    )

            except Exception as e:
                if DEBUG:
                    _log(f"❌ Failed to track response on SubagentStop: {e}")

    def _build_subagent_stop_data(
        self,
        event: dict,
        session_id: str,
        agent_type: str,
        agent_id: str,
        reason: str,
        working_dir: str,
        git_branch: str,
        structured_response: Optional[dict],
        agent_type_inferred: bool,
    ) -> dict:
        """Build the subagent stop data for event emission."""
        subagent_stop_data = {
            "agent_type": agent_type,
            "agent_type_inferred": agent_type_inferred,
            "agent_id": agent_id,
            "reason": reason,
            "session_id": session_id,
            "working_directory": working_dir,
            "git_branch": git_branch,
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
                "MEMORIES": structured_response.get(
                    "MEMORIES"
                ),  # Complete memory replacement
            }

        return subagent_stop_data
