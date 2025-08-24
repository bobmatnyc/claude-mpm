#!/usr/bin/env python3
"""Response tracking utilities for Claude Code hook handler.

This module provides utilities for tracking and correlating agent responses
with their original requests.
"""

import json
import os
import re
import sys
from datetime import datetime
from typing import Optional

# Debug mode
DEBUG = os.environ.get("CLAUDE_MPM_HOOK_DEBUG", "true").lower() != "false"

# Response tracking integration
RESPONSE_TRACKING_AVAILABLE = False
try:
    from claude_mpm.services.response_tracker import ResponseTracker

    RESPONSE_TRACKING_AVAILABLE = True
except Exception as e:
    if DEBUG:
        print(f"Response tracking not available: {e}", file=sys.stderr)
    RESPONSE_TRACKING_AVAILABLE = False


class ResponseTrackingManager:
    """Manager for response tracking functionality."""

    def __init__(self):
        self.response_tracker: Optional[ResponseTracker] = None
        self.response_tracking_enabled = False
        self.track_all_interactions = (
            False  # Track all Claude interactions, not just delegations
        )

        if RESPONSE_TRACKING_AVAILABLE:
            self._initialize_response_tracking()

    def _initialize_response_tracking(self):
        """Initialize response tracking if enabled in configuration.

        WHY: This enables automatic capture and storage of agent responses
        for analysis, debugging, and learning purposes. Integration into the
        existing hook handler avoids duplicate event capture.

        DESIGN DECISION: Check configuration to allow enabling/disabling
        response tracking without code changes.
        """
        try:
            # Create configuration with optional config file using ConfigLoader
            config_file = os.environ.get("CLAUDE_PM_CONFIG_FILE")
            from claude_mpm.core.shared.config_loader import ConfigLoader, ConfigPattern

            config_loader = ConfigLoader()
            if config_file:
                # Use specific config file with ConfigLoader
                pattern = ConfigPattern(
                    filenames=[os.path.basename(config_file)],
                    search_paths=[os.path.dirname(config_file)],
                    env_prefix="CLAUDE_MPM_",
                )
                config = config_loader.load_config(
                    pattern, cache_key=f"response_tracking_{config_file}"
                )
            else:
                config = config_loader.load_main_config()

            # Check if response tracking is enabled (check both sections for compatibility)
            response_tracking_enabled = config.get("response_tracking.enabled", False)
            response_logging_enabled = config.get("response_logging.enabled", False)

            if not (response_tracking_enabled or response_logging_enabled):
                if DEBUG:
                    print(
                        "Response tracking disabled - skipping initialization",
                        file=sys.stderr,
                    )
                return

            # Initialize response tracker with config
            self.response_tracker = ResponseTracker(config=config)
            self.response_tracking_enabled = self.response_tracker.is_enabled()

            # Check if we should track all interactions (not just delegations)
            self.track_all_interactions = config.get(
                "response_tracking.track_all_interactions", False
            ) or config.get("response_logging.track_all_interactions", False)

            if DEBUG:
                mode = (
                    "all interactions"
                    if self.track_all_interactions
                    else "Task delegations only"
                )
                print(
                    f"✅ Response tracking initialized (mode: {mode})", file=sys.stderr
                )

        except Exception as e:
            if DEBUG:
                print(
                    f"❌ Failed to initialize response tracking: {e}", file=sys.stderr
                )
            # Don't fail the entire handler - response tracking is optional

    def track_agent_response(
        self, session_id: str, agent_type: str, event: dict, delegation_requests: dict
    ):
        """Track agent response by correlating with original request and saving response.

        WHY: This integrates response tracking into the existing hook flow,
        capturing agent responses when Task delegations complete. It correlates
        the response with the original request stored during pre-tool processing.

        DESIGN DECISION: Only track responses if response tracking is enabled
        and we have the original request data. Graceful error handling ensures
        response tracking failures don't break hook processing.
        """
        if not self.response_tracking_enabled or not self.response_tracker:
            return

        try:
            # Get the original request data stored during pre-tool
            request_info = delegation_requests.get(session_id)
            if not request_info:
                if DEBUG:
                    print(
                        f"No request data found for session {session_id}, skipping response tracking",
                        file=sys.stderr,
                    )
                return

            # Extract response from event output
            response = event.get("output", "")
            if not response:
                # If no output, use error or construct a basic response
                error = event.get("error", "")
                exit_code = event.get("exit_code", 0)
                if error:
                    response = f"Error: {error}"
                else:
                    response = f"Task completed with exit code: {exit_code}"

            # Convert response to string if it's not already
            response_text = str(response)

            # Try to extract structured JSON response from agent output
            structured_response = None
            try:
                # Look for JSON block in the response (agents should return JSON at the end)
                json_match = re.search(
                    r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL
                )
                if json_match:
                    structured_response = json.loads(json_match.group(1))
                    if DEBUG:
                        print(
                            f"Extracted structured response from {agent_type} agent",
                            file=sys.stderr,
                        )
            except (json.JSONDecodeError, AttributeError) as e:
                if DEBUG:
                    print(
                        f"No structured JSON response found in {agent_type} agent output: {e}",
                        file=sys.stderr,
                    )

            # Get the original request (prompt + description)
            original_request = request_info.get("request", {})
            prompt = original_request.get("prompt", "")
            description = original_request.get("description", "")

            # Combine prompt and description for the full request
            full_request = prompt
            if description and description != prompt:
                if full_request:
                    full_request += f"\n\nDescription: {description}"
                else:
                    full_request = description

            if not full_request:
                full_request = f"Task delegation to {agent_type} agent"

            # Prepare metadata with structured response data if available
            metadata = {
                "exit_code": event.get("exit_code", 0),
                "success": event.get("exit_code", 0) == 0,
                "has_error": bool(event.get("error")),
                "duration_ms": event.get("duration_ms"),
                "working_directory": event.get("cwd", ""),
                "timestamp": datetime.now().isoformat(),
                "tool_name": "Task",
                "original_request_timestamp": request_info.get("timestamp"),
            }

            # Add structured response data to metadata if available
            if structured_response:
                metadata["structured_response"] = {
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

                # Log if MEMORIES field is present
                if structured_response.get("MEMORIES"):
                    if DEBUG:
                        memories_count = len(structured_response["MEMORIES"])
                        print(
                            f"Agent {agent_type} returned MEMORIES field with {memories_count} items",
                            file=sys.stderr,
                        )

                # Check if task was completed for logging purposes
                if structured_response.get("task_completed"):
                    metadata["task_completed"] = True

                # Log files modified for debugging
                if DEBUG and structured_response.get("files_modified"):
                    files = [f["file"] for f in structured_response["files_modified"]]
                    print(
                        f"Agent {agent_type} modified files: {files}", file=sys.stderr
                    )

            # Track the response
            file_path = self.response_tracker.track_response(
                agent_name=agent_type,
                request=full_request,
                response=response_text,
                session_id=session_id,
                metadata=metadata,
            )

            if file_path and DEBUG:
                print(
                    f"✅ Tracked response for {agent_type} agent in session {session_id}: {file_path.name}",
                    file=sys.stderr,
                )
            elif DEBUG and not file_path:
                print(
                    f"Response tracking returned None for {agent_type} agent (might be excluded or disabled)",
                    file=sys.stderr,
                )

            # Clean up the request data after successful tracking
            delegation_requests.pop(session_id, None)

        except Exception as e:
            if DEBUG:
                print(f"❌ Failed to track agent response: {e}", file=sys.stderr)
            # Don't fail the hook processing - response tracking is optional

    def track_stop_response(
        self, event: dict, session_id: str, metadata: dict, pending_prompts: dict
    ):
        """Track response for stop events."""
        if not (self.response_tracking_enabled and self.response_tracker):
            return

        try:
            # Extract output from event
            output = (
                event.get("output", "")
                or event.get("final_output", "")
                or event.get("response", "")
            )

            # Check if we have a pending prompt for this session
            prompt_data = pending_prompts.get(session_id)

            if DEBUG:
                print(
                    f"  - output present: {bool(output)} (length: {len(str(output)) if output else 0})",
                    file=sys.stderr,
                )
                print(f"  - prompt_data present: {bool(prompt_data)}", file=sys.stderr)

            if output and prompt_data:
                # Add prompt timestamp to metadata
                metadata["prompt_timestamp"] = prompt_data.get("timestamp")

                # Track the main Claude response
                file_path = self.response_tracker.track_response(
                    agent_name="claude_main",
                    request=prompt_data["prompt"],
                    response=str(output),
                    session_id=session_id,
                    metadata=metadata,
                )

                if file_path and DEBUG:
                    print(f"  - Response tracked to: {file_path}", file=sys.stderr)

                # Clean up pending prompt
                del pending_prompts[session_id]

        except Exception as e:
            if DEBUG:
                print(f"Error tracking stop response: {e}", file=sys.stderr)

    def track_assistant_response(self, event: dict, pending_prompts: dict):
        """Handle assistant response events for comprehensive response tracking."""
        if not self.response_tracking_enabled or not self.track_all_interactions:
            return

        session_id = event.get("session_id", "")
        if not session_id:
            return

        # Get the stored prompt for this session
        prompt_data = pending_prompts.get(session_id)
        if not prompt_data:
            if DEBUG:
                print(
                    f"No stored prompt for session {session_id[:8]}..., skipping response tracking",
                    file=sys.stderr,
                )
            return

        try:
            # Extract response content from event
            response_content = (
                event.get("response", "")
                or event.get("content", "")
                or event.get("text", "")
            )

            if not response_content:
                if DEBUG:
                    print(
                        f"No response content in event for session {session_id[:8]}...",
                        file=sys.stderr,
                    )
                return

            # Track the response
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "prompt_timestamp": prompt_data.get("timestamp"),
                "working_directory": prompt_data.get("working_directory", ""),
                "event_type": "assistant_response",
                "session_type": "interactive",
            }

            file_path = self.response_tracker.track_response(
                agent_name="claude",
                request=prompt_data["prompt"],
                response=response_content,
                session_id=session_id,
                metadata=metadata,
            )

            if file_path and DEBUG:
                print(
                    f"✅ Tracked Claude response for session {session_id[:8]}...: {file_path.name}",
                    file=sys.stderr,
                )

            # Clean up the stored prompt
            del pending_prompts[session_id]

        except Exception as e:
            if DEBUG:
                print(f"❌ Failed to track assistant response: {e}", file=sys.stderr)
