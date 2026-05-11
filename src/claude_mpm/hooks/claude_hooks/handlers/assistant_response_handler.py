#!/usr/bin/env python3
"""Assistant response event handler.

Extracted from ``event_handlers.EventHandlers`` as part of the #509 refactor.
Behavior is preserved verbatim; only the surrounding structure has changed.
"""

import re
from datetime import UTC, datetime

from .base import DEBUG, BaseEventHandler, _log


class AssistantResponseHandler:
    """Handle AssistantResponse events."""

    def __init__(self, base: BaseEventHandler):
        self.base = base
        self.hook_handler = base.hook_handler

    def handle_assistant_response(self, event):
        """Handle assistant response events for comprehensive response tracking.

        WHY emit assistant response events:
        - Provides visibility into Claude's responses to user prompts
        - Captures response content and metadata for analysis
        - Enables tracking of conversation flow and response patterns
        - Essential for comprehensive monitoring of Claude interactions
        - Scans for delegation anti-patterns and creates autotodos
        """
        # Track the response for logging
        try:
            rtm = getattr(self.hook_handler, "response_tracking_manager", None)
            if rtm and hasattr(rtm, "track_assistant_response"):
                pending_prompts = getattr(self.hook_handler, "pending_prompts", {})
                rtm.track_assistant_response(event, pending_prompts)
        except Exception:  # nosec B110
            # Response tracking is optional
            pass

        # Scan response for delegation anti-patterns and create autotodos
        try:
            self._scan_for_delegation_patterns(event)
        except Exception as e:  # nosec B110
            if DEBUG:
                _log(f"Delegation scanning error: {e}")

        # Get working directory and git branch
        working_dir = event.get("cwd", "")
        git_branch = (
            self.base._get_git_branch(working_dir) if working_dir else "Unknown"
        )

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
            "timestamp": datetime.now(UTC).isoformat(),
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
            _log(
                f"Hook handler: Processing AssistantResponse - session: '{session_id}', response_length: {len(response_text)}"
            )

        # Record assistant response for auto-pause if active
        auto_pause = getattr(self.hook_handler, "auto_pause_handler", None)
        if auto_pause and auto_pause.is_pause_active():
            try:
                # Summarize response to first 200 chars
                summary = (
                    response_text[:200] + "..."
                    if len(response_text) > 200
                    else response_text
                )
                auto_pause.on_assistant_response(summary)
            except Exception as e:
                if DEBUG:
                    _log(f"Auto-pause response recording error: {e}")

        # Emit normalized event
        self.hook_handler._emit_socketio_event(
            "", "assistant_response", assistant_response_data
        )

    def _scan_for_delegation_patterns(self, event):
        """Scan assistant response for delegation anti-patterns.

        WHY this is needed:
        - Detect when PM asks user to do something manually instead of delegating
        - Flag PM behavior violations for immediate correction
        - Enforce delegation principle in PM workflow
        - Help PM recognize delegation opportunities

        This method scans the assistant's response text for patterns like:
        - "Make sure .env.local is in your .gitignore"
        - "You'll need to run npm install"
        - "Please run the tests manually"

        When patterns are detected, PM violations are logged as errors/warnings
        that should be corrected immediately, NOT as todos to delegate.

        DESIGN DECISION: pm.violation vs autotodo.delegation
        - Delegation patterns = PM doing something WRONG → pm.violation (error)
        - Script failures = Something BROKEN → autotodo.error (todo)
        """
        # Only scan if delegation detector and event log are available
        # Uses injected services or lazy-loaded module-level instances
        detector = self.base.delegation_detector
        event_log_service = self.base.event_log

        if detector is None or event_log_service is None:
            if DEBUG:
                _log("Delegation detector or event log not available")
            return

        response_text = event.get("response", "")
        if not response_text:
            return

        # Detect delegation patterns
        detections = detector.detect_user_delegation(response_text)

        if not detections:
            return  # No patterns detected

        # Create PM violation events (NOT autotodos)
        for detection in detections:
            # Create event log entry as pm.violation
            event_log_service.append_event(
                event_type="pm.violation",
                payload={
                    "violation_type": "delegation_anti_pattern",
                    "pattern_type": detection["pattern_type"],
                    "original_text": detection["original_text"],
                    "suggested_action": detection["suggested_todo"],
                    "action": detection["action"],
                    "session_id": event.get("session_id", ""),
                    "timestamp": datetime.now(UTC).isoformat(),
                    "severity": "warning",  # Not critical, but should be fixed
                    "message": f"PM asked user to do something manually: {detection['original_text'][:80]}...",
                },
                status="pending",
            )

            if DEBUG:
                _log(f"⚠️  PM violation detected: {detection['original_text'][:60]}...")
