"""Dispatch-path tests for the terminal-title feature (issue #554).

The OLD test import ``from claude_mpm.hooks.claude_hooks.hook_handler import
handle_post_tool_use`` raised an ImportError because the function is private
(``_handle_post_tool_use``) and was never public.  This file fixes that by
exercising the REAL dispatch path:

    ClaudeHookHandler._route_event(event)
        → EventHandlers.handle_post_tool_fast(event)
        → ToolHandler.handle_post_tool_fast(event)
        → _build_terminal_title_sequence(event)   [when ExitPlanMode + enabled]

Tests assert on the JSON printed to stdout by ``_continue_execution``, which is
exactly what Claude Code reads from the hook subprocess.

Sections
--------
1. Unit tests for ``_distill_plan_title`` (title extraction).
2. Unit tests for ``_build_terminal_title_sequence`` (OSC sequence builder).
3. Integration: ``ToolHandler.handle_post_tool_fast`` called directly.
4. End-to-end: ``ClaudeHookHandler._route_event`` + ``_continue_execution``
   drives the full in-process dispatch chain without spawning a subprocess or
   touching stdin.
5. Regression: non-ExitPlanMode PostToolUse events are unaffected.
"""

from __future__ import annotations

import json
import os
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Path setup: ensure src/ is importable when pytest runs from project root
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

# ---------------------------------------------------------------------------
# Module-level imports under test
# ---------------------------------------------------------------------------
from claude_mpm.hooks.claude_hooks.handlers.tool_handler import (  # noqa: E402
    _build_terminal_title_sequence,
    _distill_plan_title,
)

# OSC escape constants that all tests share
# Implementation uses OSC 0 (sets both icon name and window title in one sequence)
# which is on the Claude Code terminalSequence allowlist.
_ESC = "\x1b"
_BEL = "\x07"
_OSC0_PREFIX = f"{_ESC}]0;"
# Keep aliases so tests that previously checked OSC1/OSC2 can be updated incrementally
_OSC1_PREFIX = _OSC0_PREFIX  # Redirected: implementation uses OSC 0
_OSC2_PREFIX = _OSC0_PREFIX  # Redirected: implementation uses OSC 0


# ===========================================================================
# 1. Unit tests for _distill_plan_title
# ===========================================================================


class TestDistillPlanTitle:
    """Verify the title-extraction helper works on various plan texts."""

    def test_plain_first_line(self):
        text = "Build the authentication layer\nMore details here"
        assert _distill_plan_title(text) == "Build the authentication layer"

    def test_markdown_header_stripped(self):
        text = "# Add OAuth support\nDetails follow"
        result = _distill_plan_title(text)
        assert result == "Add OAuth support"

    def test_markdown_subheader_stripped(self):
        text = "## Phase 2: Database migration\nStep 1: ..."
        result = _distill_plan_title(text)
        assert result == "Phase 2: Database migration"

    def test_bullet_stripped(self):
        text = "- Refactor the logging module\n- Step 2"
        result = _distill_plan_title(text)
        assert result == "Refactor the logging module"

    def test_truncation_at_40_chars(self):
        long_text = "A" * 50
        result = _distill_plan_title(long_text, max_chars=40)
        assert len(result) <= 40
        assert result.endswith("…")

    def test_short_text_unchanged(self):
        text = "Fix the import bug"
        assert _distill_plan_title(text) == "Fix the import bug"

    def test_empty_string_returns_empty(self):
        assert _distill_plan_title("") == ""

    def test_whitespace_only_returns_empty(self):
        assert _distill_plan_title("   \n  \t  ") == ""

    def test_skips_blank_lines(self):
        text = "\n\n\nFirst real line\nSecond line"
        assert _distill_plan_title(text) == "First real line"

    def test_custom_max_chars(self):
        text = "B" * 20
        result = _distill_plan_title(text, max_chars=10)
        assert len(result) <= 10
        assert result.endswith("…")

    def test_exactly_max_chars_not_truncated(self):
        text = "A" * 40
        result = _distill_plan_title(text, max_chars=40)
        assert result == "A" * 40
        assert "…" not in result


# ===========================================================================
# 2. Unit tests for _build_terminal_title_sequence
# ===========================================================================


class TestBuildTerminalTitleSequence:
    """Verify the OSC 1+2 sequence builder produces the right output."""

    def _event_with_output(self, plan_text: str) -> dict:
        return {
            "hook_event_name": "PostToolUse",
            "tool_name": "ExitPlanMode",
            "output": plan_text,
            "session_id": "test-session",
            "cwd": "/tmp/project",
            "exit_code": 0,
        }

    def _event_with_tool_input_plan(self, plan_text: str) -> dict:
        return {
            "hook_event_name": "PostToolUse",
            "tool_name": "ExitPlanMode",
            "tool_input": {"plan": plan_text},
            "session_id": "test-session",
            "cwd": "/tmp/project",
            "exit_code": 0,
        }

    def test_returns_empty_when_feature_disabled(self):
        """Default (no env var): should produce an empty string."""
        event = self._event_with_output("Build auth layer")
        with patch.dict(os.environ, {}, clear=True):
            # Ensure CLAUDE_MPM_TERMINAL_TITLE is absent
            os.environ.pop("CLAUDE_MPM_TERMINAL_TITLE", None)
            result = _build_terminal_title_sequence(event)
        assert result == ""

    def test_returns_empty_when_feature_set_to_zero(self):
        event = self._event_with_output("Build auth layer")
        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "0"}, clear=False):
            result = _build_terminal_title_sequence(event)
        assert result == ""

    def test_returns_sequence_when_enabled_via_1(self):
        event = self._event_with_output("Implement login flow")
        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "1"}, clear=False):
            result = _build_terminal_title_sequence(event)
        assert result != ""
        # Must start with OSC 0 sequence (sets both icon and window title)
        assert result.startswith(_OSC0_PREFIX)
        # Must end with BEL
        assert result.endswith(_BEL)

    def test_returns_sequence_when_enabled_via_true(self):
        event = self._event_with_output("Deploy to production")
        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "true"}, clear=False):
            result = _build_terminal_title_sequence(event)
        assert result.startswith(_OSC0_PREFIX)

    def test_title_content_present_in_sequence(self):
        event = self._event_with_output("## Refactor database layer\nDetails follow")
        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "1"}, clear=False):
            result = _build_terminal_title_sequence(event)
        # The distilled title ("Refactor database layer") should appear in both
        # the OSC 1 and OSC 2 parts of the sequence.
        assert "Refactor database layer" in result

    def test_falls_back_to_tool_input_plan(self):
        """When 'output' is absent, fall back to tool_input['plan']."""
        event = self._event_with_tool_input_plan("Write unit tests for core module")
        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "1"}, clear=False):
            result = _build_terminal_title_sequence(event)
        assert "Write unit tests" in result

    def test_returns_empty_when_no_text_available(self):
        """With no output and no tool_input.plan, should return empty string."""
        event = {
            "hook_event_name": "PostToolUse",
            "tool_name": "ExitPlanMode",
            "session_id": "test-session",
            "exit_code": 0,
        }
        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "1"}, clear=False):
            result = _build_terminal_title_sequence(event)
        assert result == ""

    def test_osc_format_uses_osc0(self):
        """OSC 0 (sets both icon name and window title) must be used.

        OSC 0 is on the Claude Code terminalSequence allowlist and handles
        both tab and window title in a single sequence, which is the
        preferred approach.
        """
        event = self._event_with_output("Fix bug in scheduler")
        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "1"}, clear=False):
            result = _build_terminal_title_sequence(event)
        assert result.startswith(_OSC0_PREFIX), "Must use OSC 0 prefix (\\033]0;)"
        assert result.endswith(_BEL), "Must end with BEL (\\007)"
        assert "Fix bug in scheduler" in result


# ===========================================================================
# Helper: build a minimal ClaudeHookHandler for integration tests
# ===========================================================================


def _make_hook_handler():
    """Build a ClaudeHookHandler with network I/O and external calls mocked.

    WHY: We want to exercise the real dispatch path (route_event → EventHandlers
    → ToolHandler) without hitting the network, the socket.io server, or git.
    """
    from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

    handler = ClaudeHookHandler()
    # Silence all outbound socket/HTTP events
    handler.connection_manager = MagicMock()
    handler.connection_manager.emit_event = MagicMock(return_value=None)
    return handler


def _route_and_capture(handler, event: dict) -> dict:
    """Run _route_event and then _continue_execution, return parsed JSON.

    This mirrors what ClaudeHookHandler.handle() does in production, but
    without touching stdin/signals.  Only the final JSON printed to stdout
    is returned so callers can assert on hook response fields.
    """
    return_value = handler._route_event(event)

    out = StringIO()
    with patch("sys.stdout", out):
        if isinstance(return_value, dict) and "terminalSequence" in return_value:
            handler._continue_execution(
                terminal_sequence=return_value["terminalSequence"]
            )
        elif (isinstance(return_value, dict) and "decision" in return_value) or (
            isinstance(return_value, dict) and "hookSpecificOutput" in return_value
        ):
            import json as _json

            print(_json.dumps(return_value))
        else:
            handler._continue_execution(return_value)

    return json.loads(out.getvalue().strip())


def _exit_plan_mode_event(plan_text: str = "## Build the auth layer\nDetails") -> dict:
    """Construct a realistic PostToolUse/ExitPlanMode event payload."""
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "ExitPlanMode",
        "output": plan_text,
        "tool_input": {},
        "session_id": "dispatch-test-session",
        "cwd": "/tmp/test-project",
        "exit_code": 0,
    }


# ===========================================================================
# 3. Integration: ToolHandler.handle_post_tool_fast called directly
# ===========================================================================


class TestToolHandlerDirectCall:
    """Call ToolHandler.handle_post_tool_fast without going through the full
    ClaudeHookHandler stack, so we can isolate the handler logic cleanly."""

    def _make_tool_handler(self):
        from claude_mpm.hooks.claude_hooks.handlers.base import BaseEventHandler
        from claude_mpm.hooks.claude_hooks.handlers.tool_handler import ToolHandler

        # Minimal mock for hook_handler (only the interfaces ToolHandler uses)
        mock_hh = MagicMock()
        mock_hh._emit_socketio_event = MagicMock(return_value=None)
        mock_hh._get_delegation_agent_type = MagicMock(return_value="unknown")

        # BaseEventHandler requires hook_handler; use a mock base
        base = MagicMock(spec=BaseEventHandler)
        base.hook_handler = mock_hh
        base._get_git_branch = MagicMock(return_value="main")
        base.log_manager = None

        return ToolHandler(base)

    def test_exit_plan_mode_enabled_returns_terminal_sequence(self):
        handler = self._make_tool_handler()
        event = _exit_plan_mode_event("Implement OAuth2 login")
        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "1"}, clear=False):
            result = handler.handle_post_tool_fast(event)
        assert isinstance(result, dict)
        assert "terminalSequence" in result
        seq = result["terminalSequence"]
        assert seq.startswith(_OSC0_PREFIX)
        assert "Implement OAuth2 login" in seq

    def test_exit_plan_mode_disabled_returns_none(self):
        handler = self._make_tool_handler()
        event = _exit_plan_mode_event("Implement OAuth2 login")
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("CLAUDE_MPM_TERMINAL_TITLE", None)
            result = handler.handle_post_tool_fast(event)
        assert result is None

    def test_non_exit_plan_mode_never_returns_terminal_sequence(self):
        handler = self._make_tool_handler()
        event = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "output": "ok",
            "tool_input": {"command": "pytest tests/"},
            "session_id": "test",
            "cwd": "/tmp",
            "exit_code": 0,
        }
        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "1"}, clear=False):
            result = handler.handle_post_tool_fast(event)
        # Bash PostToolUse must never inject a terminal sequence
        assert result is None or (
            isinstance(result, dict) and "terminalSequence" not in result
        )


# ===========================================================================
# 4. End-to-end: full dispatch chain through ClaudeHookHandler
# ===========================================================================


class TestDispatchPath:
    """Simulate PostToolUse events through the complete in-process dispatch.

    Drives ClaudeHookHandler._route_event → EventHandlers → ToolHandler and
    then _continue_execution, asserting on the JSON Claude Code would read from
    stdout.
    """

    def test_enabled_produces_terminal_sequence_in_response(self):
        """Feature ON: the hook response must contain terminalSequence with a
        correct OSC 1;2 escape for the distilled title."""
        handler = _make_hook_handler()
        event = _exit_plan_mode_event("## Build the authentication service\nPhase 1")

        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "1"}, clear=False):
            response = _route_and_capture(handler, event)

        assert response.get("continue") is True, "must always continue"
        assert "terminalSequence" in response, (
            "terminalSequence must be present when CLAUDE_MPM_TERMINAL_TITLE=1"
        )
        seq = response["terminalSequence"]
        # Check OSC 0 (sets both icon/tab name and window title)
        assert seq.startswith(_OSC0_PREFIX), f"expected OSC 0 prefix, got: {seq!r}"
        # Check BEL terminator
        assert seq.endswith(_BEL), f"expected BEL at end, got: {seq!r}"
        # Check distilled title content appears in sequence
        assert "Build the authentication service" in seq, (
            f"distilled title not found in sequence: {seq!r}"
        )

    def test_disabled_produces_plain_continue_no_terminal_sequence(self):
        """Feature OFF (default): the hook response must be the plain
        {\"continue\": true} without any terminalSequence field."""
        handler = _make_hook_handler()
        event = _exit_plan_mode_event("Deploy microservices to production")

        with patch.dict(os.environ, {}, clear=True):
            # Explicitly unset the feature flag
            os.environ.pop("CLAUDE_MPM_TERMINAL_TITLE", None)
            response = _route_and_capture(handler, event)

        assert response.get("continue") is True
        assert "terminalSequence" not in response, (
            "terminalSequence must NOT appear when feature is disabled"
        )

    def test_disabled_via_false_produces_plain_continue(self):
        """CLAUDE_MPM_TERMINAL_TITLE=false should behave like disabled."""
        handler = _make_hook_handler()
        event = _exit_plan_mode_event("Some plan text")

        with patch.dict(
            os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "false"}, clear=False
        ):
            response = _route_and_capture(handler, event)

        assert response.get("continue") is True
        assert "terminalSequence" not in response

    def test_other_post_tool_use_events_unaffected_when_enabled(self):
        """A Bash PostToolUse must NEVER inject terminalSequence even when the
        feature is enabled — only ExitPlanMode triggers it."""
        handler = _make_hook_handler()
        event = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "output": "test output",
            "tool_input": {"command": "pytest tests/ -v"},
            "session_id": "dispatch-test-session",
            "cwd": "/tmp/test-project",
            "exit_code": 0,
        }

        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "1"}, clear=False):
            response = _route_and_capture(handler, event)

        assert response.get("continue") is True
        assert "terminalSequence" not in response

    def test_pre_tool_use_events_unaffected(self):
        """PreToolUse events must continue to behave as before (plain continue
        for a non-Agent, non-Bash, non-deny tool call)."""
        handler = _make_hook_handler()
        event = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/file.txt"},
            "session_id": "dispatch-test-session",
            "cwd": "/tmp",
        }

        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "1"}, clear=False):
            response = _route_and_capture(handler, event)

        assert response.get("continue") is True
        assert "terminalSequence" not in response

    def test_title_derived_from_markdown_plan_text(self):
        """The title shown in the terminal sequence must be distilled from the
        plan markdown - header markers stripped, first meaningful line used."""
        handler = _make_hook_handler()
        plan_text = (
            "# Quarterly Refactor\n\n"
            "## Phase 1: Extract service layer\n"
            "Details about the phase..."
        )
        event = _exit_plan_mode_event(plan_text)

        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "1"}, clear=False):
            response = _route_and_capture(handler, event)

        assert "terminalSequence" in response
        seq = response["terminalSequence"]
        # "Quarterly Refactor" is the first non-empty line after header stripping
        assert "Quarterly Refactor" in seq, (
            f"Expected 'Quarterly Refactor' in sequence, got: {seq!r}"
        )


# ===========================================================================
# 5. Regression: _continue_execution signature
# ===========================================================================


class TestContinueExecution:
    """Verify the _continue_execution helper produces correct JSON in all modes."""

    def _make_handler(self):
        return _make_hook_handler()

    def test_plain_continue(self):
        handler = self._make_handler()
        out = StringIO()
        with patch("sys.stdout", out):
            handler._continue_execution()
        assert json.loads(out.getvalue()) == {"continue": True}

    def test_with_terminal_sequence(self):
        handler = self._make_handler()
        out = StringIO()
        seq = f"{_OSC0_PREFIX}Hello{_BEL}"
        with patch("sys.stdout", out):
            handler._continue_execution(terminal_sequence=seq)
        result = json.loads(out.getvalue())
        assert result["continue"] is True
        assert result["terminalSequence"] == seq

    def test_with_modified_input_and_terminal_sequence(self):
        handler = self._make_handler()
        out = StringIO()
        seq = f"{_OSC0_PREFIX}Test{_BEL}"
        with patch("sys.stdout", out):
            handler._continue_execution({"key": "val"}, terminal_sequence=seq)
        result = json.loads(out.getvalue())
        assert result["continue"] is True
        assert result["tool_input"] == {"key": "val"}
        assert result["terminalSequence"] == seq

    def test_terminal_sequence_none_gives_plain(self):
        handler = self._make_handler()
        out = StringIO()
        with patch("sys.stdout", out):
            handler._continue_execution(terminal_sequence=None)
        assert json.loads(out.getvalue()) == {"continue": True}
