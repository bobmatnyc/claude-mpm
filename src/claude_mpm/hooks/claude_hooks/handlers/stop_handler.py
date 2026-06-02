#!/usr/bin/env python3
"""Stop event handler.

Extracted from ``event_handlers.EventHandlers`` as part of the #509 refactor.
Behavior is preserved verbatim; only the surrounding structure has changed.

References
----------
Stop event payload (real): only ``hook_event_name``, ``session_id``, ``cwd``,
``reason``, ``stop_hook_active`` are reliably present.  There is NO ``usage``
field on real Claude Code Stop events (confirmed by hook log inspection:
``Received event with keys: ['hook_event_name']``).  Token usage is obtained
by parsing the transcript JSONL at
``~/.claude/projects/{cwd_encoded}/{session_id}.jsonl``.
"""

from datetime import UTC, datetime
from pathlib import Path

from claude_mpm.hooks.transcript_usage import (
    derive_transcript_path as _derive_transcript_path_shared,
    parse_transcript_usage as _parse_transcript_usage_shared,
)

from .base import DEBUG, BaseEventHandler, _log

# ---------------------------------------------------------------------------
# Always-on debug log helper — mirrors the pattern in commit_cost_tracker.py.
# Writes unconditionally to ~/.claude-mpm/logs/stop-handler-debug.log so
# failures in the Stop handler are visible without setting CLAUDE_MPM_HOOK_DEBUG.
# ---------------------------------------------------------------------------
_STOP_DEBUG_LOG: Path = Path.home() / ".claude-mpm" / "logs" / "stop-handler-debug.log"


def _stop_debug(message: str) -> None:
    """Append *message* to the stop-handler debug log, always, unconditionally.

    WHY: The Stop handler uses fail-open (never raises), which means all errors
    are silently swallowed.  Without an unconditional log the only way to see
    failures is to set CLAUDE_MPM_HOOK_DEBUG=true, which requires knowing in
    advance that something is wrong.  This function writes regardless of the
    DEBUG flag so we always have a paper trail.

    WHAT: Creates the log directory if needed, timestamps the message, and
    appends one line to stop-handler-debug.log.

    TEST: Call with any string and assert the log file exists and contains the
    message.  Call when the directory does not exist and assert no exception is
    raised (directory is created automatically).
    """
    try:
        _STOP_DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
        with _STOP_DEBUG_LOG.open("a") as fh:
            fh.write(f"[{ts}] {message}\n")
    except Exception:
        pass  # Never raise from a debug helper


def _parse_transcript_usage(
    transcript_path: Path,
) -> dict | None:
    """Parse cumulative token usage from a Claude Code session transcript JSONL.

    WHY: Thin wrapper around the shared ``transcript_usage.parse_transcript_usage``
    that preserves the original function signature for backward compatibility and
    adds stop-handler-specific DEBUG logging.

    WHAT: Delegates to the shared implementation and emits DEBUG log lines so
    the stop-handler-debug.log captures parse results without changing stop_handler
    callers.

    TEST: See ``tests/test_commit_cost_tracker.py::TestParseTranscriptUsage`` for
    the shared implementation tests.  This wrapper adds no new logic.

    Args:
        transcript_path: Absolute path to the ``.jsonl`` session transcript.

    Returns:
        Same dict as ``parse_transcript_usage()``, or None.
    """
    result = _parse_transcript_usage_shared(transcript_path)
    if result is None:
        _stop_debug(f"_parse_transcript_usage: no data from: {transcript_path}")
        if DEBUG:
            _log(f"  - transcript returned no data: {transcript_path}")
    else:
        _stop_debug(
            f"_parse_transcript_usage: totals "
            f"in={result['input_tokens']} out={result['output_tokens']} "
            f"cc={result['cache_creation_input_tokens']} "
            f"cr={result['cache_read_input_tokens']} "
            f"models={list(result['models'].keys())}"
        )
        if DEBUG:
            _log(
                f"  - transcript parsed: "
                f"in={result['input_tokens']} out={result['output_tokens']}"
            )
    return result


def _derive_transcript_path(session_id: str, cwd: str) -> Path | None:
    """Derive the Claude Code transcript JSONL path from session_id and cwd.

    WHY: Thin wrapper around the shared ``transcript_usage.derive_transcript_path``
    that preserves the original function signature used by existing tests and the
    handle_stop_fast method.

    WHAT: Delegates to the shared implementation.  Does NOT check existence.

    TEST: Call with cwd='/foo/bar' and session_id='abc' and assert the result
    equals ``Path.home() / '.claude/projects/-foo-bar/abc.jsonl'``.

    Args:
        session_id: The Claude Code session UUID (from the Stop event).
        cwd: The working directory string (from the Stop event).

    Returns:
        A Path object, or None if session_id or cwd is empty.
    """
    return _derive_transcript_path_shared(session_id, cwd)


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
        _stop_debug(
            f"handle_stop_fast: session_id={session_id!r} cwd={event.get('cwd', '')!r}"
        )

        # Extract metadata for this stop event
        metadata = self._extract_stop_metadata(event)

        # Debug logging
        if DEBUG:
            self._log_stop_event_debug(event, session_id, metadata)

        # ---------------------------------------------------------------------------
        # Token usage capture — ALWAYS attempt, regardless of event["usage"].
        #
        # WHY: Real Claude Code Stop events do NOT include a "usage" field.  The
        # previous implementation gated the entire snapshot path on
        # ``if "usage" in event:``, which never fired, so context-usage.json was
        # only ever written by the "session-real-test" test fixture.
        #
        # AUTHORITATIVE SOURCE: The session transcript JSONL at
        # ~/.claude/projects/{cwd_encoded}/{session_id}.jsonl contains per-message
        # usage objects on every assistant record.  Summing them gives the true
        # cumulative session total.
        #
        # FALLBACK: If the event *does* include a "usage" key (possible in future
        # Claude Code versions), use it directly so we don't depend on file I/O.
        # ---------------------------------------------------------------------------
        usage_data: dict[str, int] | None = None

        # Fast path: event-level usage (future-proofing; not present today).
        if "usage" in event:
            ev_usage = event["usage"]
            usage_data = {
                "input_tokens": int(ev_usage.get("input_tokens", 0) or 0),
                "output_tokens": int(ev_usage.get("output_tokens", 0) or 0),
                "cache_creation_input_tokens": int(
                    ev_usage.get("cache_creation_input_tokens", 0) or 0
                ),
                "cache_read_input_tokens": int(
                    ev_usage.get("cache_read_input_tokens", 0) or 0
                ),
            }
            if DEBUG:
                _log("  - usage source: event field")

        # Slow path: parse transcript JSONL (the real, always-available source).
        if usage_data is None:
            cwd = event.get("cwd", "")
            # Fallback: if the event did not carry a cwd, use the process cwd.
            if not cwd:
                cwd = str(Path.cwd())
                _stop_debug(
                    f"handle_stop_fast: cwd missing from event, fell back to process cwd: {cwd!r}"
                )
            else:
                _stop_debug(f"handle_stop_fast: cwd from event: {cwd!r}")
            transcript_path = _derive_transcript_path(session_id, cwd)
            _stop_debug(
                f"handle_stop_fast: transcript_path={transcript_path} "
                f"exists={transcript_path.exists() if transcript_path else False}"
            )
            if DEBUG:
                _log(f"  - transcript_path: {transcript_path}")
            if transcript_path is not None:
                usage_data = _parse_transcript_usage(transcript_path)
                if usage_data is None:
                    _stop_debug(
                        "handle_stop_fast: _parse_transcript_usage returned None"
                    )
                else:
                    _stop_debug(
                        f"handle_stop_fast: usage from transcript "
                        f"in={usage_data['input_tokens']} "
                        f"out={usage_data['output_tokens']}"
                    )
                if DEBUG and usage_data is not None:
                    _log(
                        f"  - usage source: transcript "
                        f"in={usage_data['input_tokens']} "
                        f"out={usage_data['output_tokens']}"
                    )

        if usage_data is None:
            _stop_debug(
                "handle_stop_fast: skipping set_session_snapshot — usage_data is None"
            )
        else:
            _stop_debug(
                f"handle_stop_fast: writing snapshot "
                f"in={usage_data['input_tokens']} out={usage_data['output_tokens']}"
            )

        if usage_data is not None:
            metadata["usage"] = {
                "input_tokens": usage_data["input_tokens"],
                "output_tokens": usage_data["output_tokens"],
                "cache_creation_input_tokens": usage_data[
                    "cache_creation_input_tokens"
                ],
                "cache_read_input_tokens": usage_data["cache_read_input_tokens"],
            }

            # Persist the cumulative snapshot so the git post-commit hook reads
            # accurate token counts.
            #
            # WHY set_session_snapshot() and NOT update_usage():
            # The transcript sum is already cumulative for the entire session.
            # update_usage() *adds* to existing values, causing double-count
            # across turns.  set_session_snapshot() REPLACES stored state so the
            # file always reflects the true cumulative total.
            #
            # TIMING NOTE: Stop fires after Claude finishes responding.  A commit
            # made via a Bash tool during that turn triggers post-commit between
            # tool calls—before Stop—so it reads the previous turn's snapshot.
            # That is the most accurate data available at commit time.
            try:
                from claude_mpm.services.infrastructure.context_usage_tracker import (
                    ContextUsageTracker,
                )

                cwd = event.get("cwd", "")
                _tracker = ContextUsageTracker(project_path=Path(cwd) if cwd else None)
                _tracker.set_session_snapshot(
                    session_id=session_id or "unknown",
                    input_tokens=usage_data["input_tokens"],
                    output_tokens=usage_data["output_tokens"],
                    cache_creation=usage_data["cache_creation_input_tokens"],
                    cache_read=usage_data["cache_read_input_tokens"],
                    models=usage_data.get("models"),
                )
                if DEBUG:
                    _log(
                        f"  - Stop snapshot saved: "
                        f"in={usage_data['input_tokens']} "
                        f"out={usage_data['output_tokens']}"
                    )
            except Exception as _snap_exc:
                _stop_debug(
                    f"handle_stop_fast: set_session_snapshot FAILED (fail-open): {_snap_exc}"
                )
                if DEBUG:
                    _log(
                        f"  - context-usage snapshot from Stop failed (fail-open): {_snap_exc}"
                    )

            auto_pause = getattr(self.hook_handler, "auto_pause_handler", None)
            if auto_pause:
                try:
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
