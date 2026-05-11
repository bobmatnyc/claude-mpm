#!/usr/bin/env python3
"""Stop event handler.

Extracted from ``event_handlers.EventHandlers`` as part of the #509 refactor.
Behavior is preserved verbatim; only the surrounding structure has changed.
"""

from datetime import UTC, datetime
from pathlib import Path

from .base import DEBUG, BaseEventHandler, _log


class StopHandler:
    """Handle Stop events when Claude processing stops."""

    def __init__(self, base: BaseEventHandler):
        self.base = base
        self.hook_handler = base.hook_handler

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

        # Auto-pause integration (independent of response tracking)
        # WHY HERE: Auto-pause must work even when response_tracking is disabled
        # Extract usage data directly from event and trigger auto-pause if thresholds crossed
        if "usage" in event:
            auto_pause = getattr(self.hook_handler, "auto_pause_handler", None)
            if auto_pause:
                try:
                    usage_data = event["usage"]
                    metadata["usage"] = {
                        "input_tokens": usage_data.get("input_tokens", 0),
                        "output_tokens": usage_data.get("output_tokens", 0),
                        "cache_creation_input_tokens": usage_data.get(
                            "cache_creation_input_tokens", 0
                        ),
                        "cache_read_input_tokens": usage_data.get(
                            "cache_read_input_tokens", 0
                        ),
                    }

                    threshold_crossed = auto_pause.on_usage_update(metadata["usage"])
                    if threshold_crossed:
                        warning = auto_pause.emit_threshold_warning(threshold_crossed)
                        # CRITICAL: Never write to stderr unconditionally - causes hook errors
                        # Use _log() instead which only writes to file if DEBUG=true
                        _log(f"⚠️  Auto-pause threshold crossed: {warning}")

                        if DEBUG:
                            _log(
                                f"  - Auto-pause threshold crossed: {threshold_crossed}"
                            )
                except Exception as e:
                    if DEBUG:
                        _log(f"Auto-pause error in handle_stop_fast: {e}")

                # Finalize pause session if active
                try:
                    if auto_pause.is_pause_active():
                        session_file = auto_pause.on_session_end()
                        if session_file:
                            if DEBUG:
                                _log(
                                    f"✅ Auto-pause session finalized: {session_file.name}"
                                )
                except Exception as e:
                    if DEBUG:
                        _log(f"❌ Failed to finalize auto-pause session: {e}")

        # Track response if enabled
        try:
            rtm = getattr(self.hook_handler, "response_tracking_manager", None)
            if rtm and hasattr(rtm, "track_stop_response"):
                pending_prompts = getattr(self.hook_handler, "pending_prompts", {})
                rtm.track_stop_response(event, session_id, metadata, pending_prompts)
        except Exception:  # nosec B110
            # Response tracking is optional
            pass

        # Check for unread cross-project messages
        # If unread messages exist AND this isn't a re-triggered stop (stop_hook_active),
        # block the stop so Claude sees the unread messages and can act on them.
        try:
            from claude_mpm.core.unified_paths import UnifiedPathManager
            from claude_mpm.services.communication.message_service import MessageService

            # Always get a fresh count (never use cached values)
            project_root = UnifiedPathManager().project_root
            service = MessageService(project_root)
            unread = service.list_messages(status="unread")

            # Don't block if this stop was already triggered by a previous block
            # (stop_hook_active prevents infinite loop)
            stop_hook_active = event.get("stop_hook_active", False)

            if unread and not stop_hook_active:
                _log(f"📬 {len(unread)} unread cross-project message(s) at session end")

                # Build per-message preview (up to 3 messages)
                preview_lines = []
                for msg in unread[:3]:
                    sender = (
                        Path(msg.from_project).name if msg.from_project else "unknown"
                    )
                    subject = getattr(msg, "subject", None) or "No subject"
                    priority = getattr(msg, "priority", "normal") or "normal"
                    if priority in ("high", "urgent"):
                        preview_lines.append(
                            f'  • [{priority}] from {sender}: "{subject}"'
                        )
                    else:
                        preview_lines.append(f'  • from {sender}: "{subject}"')
                if len(unread) > 3:
                    preview_lines.append(f"  • ... and {len(unread) - 3} more")
                preview = "\n".join(preview_lines)

                reason = (
                    f"📬 {len(unread)} unread message(s):\n{preview}\n"
                    f"Read with: claude-mpm message list --status unread"
                )

                # Mark notified messages as read so they are not recounted
                # on subsequent session stops (fixes #413)
                try:
                    for msg in unread:
                        service.read_message(msg.id)
                except Exception as mark_err:
                    if DEBUG:
                        _log(
                            f"Failed to mark stop-notified messages as read: {mark_err}"
                        )

                # Reset the message check throttle so the next UserPromptSubmit
                # gets a fresh notification (fixes stale count after block)
                try:
                    from claude_mpm.hooks.message_check_hook import (
                        MessageCheckState,
                    )

                    state_file = (
                        project_root / ".claude-mpm" / "message_check_state.json"
                    )
                    state_mgr = MessageCheckState(state_file)
                    state = state_mgr.load()
                    state["last_check"] = None
                    state_mgr.save(state)
                except Exception:
                    pass

                return {"continue": True, "stopReason": reason}
        except Exception as e:
            if DEBUG:
                _log(f"Message check on stop error: {e}")

        # Emit stop event to Socket.IO
        self._emit_stop_event(event, session_id, metadata)

        # Generate rich resume log from live session state (fixes #462).
        # Without this call, generate_resume_log() is never invoked and the
        # /mpm-session-resume command falls back to the empty stub at
        # session_manager.py:315-328. Build a session_state dict from the
        # data we have on the Stop event so the generator produces a
        # meaningful log instead of the placeholder.
        try:
            self._generate_resume_log_on_stop(event, session_id, metadata)
        except Exception as e:
            # Resume log generation is best-effort; never block Stop handling.
            if DEBUG:
                _log(f"Resume log generation on stop failed: {e}")

        return None

    def _generate_resume_log_on_stop(
        self, event: dict, session_id: str, metadata: dict
    ) -> None:
        """Build session_state from stop event and trigger resume log generation.

        Pulls token usage from SessionManager (which has been accumulating
        across the session via update_token_usage), captures the working
        directory, stop reason, and any final output, and asks the
        SessionManager to persist a resume log via ResumeLogGenerator.

        This is the wiring that #462 reports missing: previously the Stop
        handler exited after _emit_stop_event without ever invoking
        generate_resume_log(), so users running /mpm-session-resume only
        ever saw the "Session ended - resume log auto-generated." stub.
        """
        del (
            session_id
        )  # Intentionally unused; session is tracked inside SessionManager.
        from claude_mpm.services.session_manager import get_session_manager

        manager = get_session_manager()

        # Update SessionManager with this stop's token usage so the
        # context_metrics reflect the latest API call before we snapshot.
        usage = metadata.get("usage") or {}
        stop_reason = event.get("stop_reason") or metadata.get("reason")
        if usage or stop_reason:
            try:
                manager.update_token_usage(
                    input_tokens=int(usage.get("input_tokens", 0) or 0),
                    output_tokens=int(usage.get("output_tokens", 0) or 0),
                    stop_reason=stop_reason,
                )
            except Exception as e:
                if DEBUG:
                    _log(f"Failed to update token usage before resume log: {e}")

        context_metrics = manager.get_context_metrics()

        # Capture final output from the stop event when present.
        final_output = (
            event.get("final_output")
            or event.get("output")
            or event.get("response")
            or ""
        )
        if isinstance(final_output, (dict, list)):
            try:
                import json as _json

                final_output = _json.dumps(final_output)[:4000]
            except Exception:
                final_output = str(final_output)[:4000]
        elif isinstance(final_output, str) and len(final_output) > 4000:
            final_output = final_output[:4000]

        # Build a session_state the generator understands.
        session_state: dict = {
            "context_metrics": context_metrics,
            "mission_summary": (
                f"Session stopped (reason={metadata.get('reason', 'unknown')}, "
                f"stop_reason={stop_reason or 'unknown'})."
            ),
            "critical_context": {
                "working_directory": metadata.get("working_directory", ""),
                "git_branch": metadata.get("git_branch", "Unknown"),
                "stop_type": metadata.get("stop_type", "normal"),
                "timestamp": metadata.get("timestamp"),
            },
        }
        if final_output:
            session_state["accomplishments"] = [
                f"Final assistant output captured ({len(final_output)} chars)."
            ]
            session_state["critical_context"]["final_output_preview"] = final_output

        file_path = manager.generate_resume_log(session_state=session_state)
        if DEBUG:
            if file_path:
                _log(f"✅ Resume log written: {file_path}")
            else:
                _log("⚠️  Resume log generation returned None")

    def _extract_stop_metadata(self, event: dict) -> dict:
        """Extract metadata from stop event."""
        working_dir = event.get("cwd", "")
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "working_directory": working_dir,
            "git_branch": (
                self.base._get_git_branch(working_dir) if working_dir else "Unknown"
            ),
            "event_type": "stop",
            "reason": event.get("reason", "unknown"),
            "stop_type": event.get("stop_type", "normal"),
        }

    def _log_stop_event_debug(
        self, _event: dict, session_id: str, metadata: dict
    ) -> None:
        """Log debug information for stop events."""
        del _event  # Intentionally unused; only metadata and session_id are logged.
        try:
            rtm = getattr(self.hook_handler, "response_tracking_manager", None)
            tracking_enabled = (
                getattr(rtm, "response_tracking_enabled", False) if rtm else False
            )
            tracker_exists = (
                getattr(rtm, "response_tracker", None) is not None if rtm else False
            )

            _log(f"  - response_tracking_enabled: {tracking_enabled}")
            _log(f"  - response_tracker exists: {tracker_exists}")
        except Exception:  # nosec B110
            # If debug logging fails, just skip it
            pass

        _log(f"  - session_id: {session_id[:8] if session_id else 'None'}...")
        _log(f"  - reason: {metadata['reason']}")
        _log(f"  - stop_type: {metadata['stop_type']}")

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
            "usage": metadata.get("usage"),  # Add token usage data
        }

        # Emit normalized event
        self.hook_handler._emit_socketio_event("", "stop", stop_data)

        # Emit dedicated token usage event if usage data is available
        if metadata.get("usage"):
            usage_data = metadata["usage"]
            token_usage_data = {
                "session_id": session_id,
                "input_tokens": usage_data.get("input_tokens", 0),
                "output_tokens": usage_data.get("output_tokens", 0),
                "cache_creation_tokens": usage_data.get(
                    "cache_creation_input_tokens", 0
                ),
                "cache_read_tokens": usage_data.get("cache_read_input_tokens", 0),
                "total_tokens": (
                    usage_data.get("input_tokens", 0)
                    + usage_data.get("output_tokens", 0)
                    + usage_data.get("cache_creation_input_tokens", 0)
                    + usage_data.get("cache_read_input_tokens", 0)
                ),
                "timestamp": metadata["timestamp"],
            }
            self.hook_handler._emit_socketio_event(
                "", "token_usage_updated", token_usage_data
            )
