"""Tests for the terminal-title feature (#554).

Tests the wired implementation in ``terminal_title.py``:

1. ``distill_title()``        — title extraction from hook events.
2. ``build_osc_sequence()``   — OSC 0 escape sequence construction.
3. ``is_enabled()``           — feature-flag env-var helper.
4. ``get_max_length()``       — max-length env-var helper.
5. ``get_trigger_tools()``    — trigger-tools env-var helper.
6. Integration: ``_build_terminal_title_sequence`` in ``tool_handler.py``
   returns the right sequence (or empty string) based on env vars.
7. End-to-end dispatch: ``ClaudeHookHandler._route_event`` → ``_continue_execution``
   produces the correct JSON for Claude Code.
"""

from __future__ import annotations

import json
import os
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# 1. distill_title()
# ---------------------------------------------------------------------------


class TestDistillTitle:
    """Unit tests for the title-distillation helper."""

    def _fn(self):
        from claude_mpm.hooks.terminal_title import distill_title

        return distill_title

    def test_plan_description_wins(self):
        fn = self._fn()
        event = {
            "tool_name": "TodoWrite",
            "tool_input": {"plan_description": "Build the auth layer", "todos": []},
        }
        assert fn(event) == "Build the auth layer"

    def test_in_progress_todo_preferred(self):
        fn = self._fn()
        event = {
            "tool_name": "TodoWrite",
            "tool_input": {
                "todos": [
                    {"title": "Pending task", "status": "pending"},
                    {"title": "Active task", "status": "in_progress"},
                    {"title": "Done task", "status": "completed"},
                ]
            },
        }
        assert fn(event) == "Active task"

    def test_first_todo_fallback_when_no_in_progress(self):
        fn = self._fn()
        event = {
            "tool_name": "TodoWrite",
            "tool_input": {
                "todos": [
                    {"title": "First task", "status": "pending"},
                    {"title": "Second task", "status": "pending"},
                ]
            },
        }
        assert fn(event) == "First task"

    def test_todo_content_used_when_no_title(self):
        fn = self._fn()
        event = {
            "tool_name": "TodoWrite",
            "tool_input": {
                "todos": [
                    {
                        "content": "Write unit tests for the auth module",
                        "status": "pending",
                    },
                ]
            },
        }
        result = fn(event)
        assert "unit tests" in result or "Write" in result

    def test_tool_name_context_bash(self):
        fn = self._fn()
        event = {
            "tool_name": "Bash",
            "tool_input": {"command": "pytest tests/ -v"},
        }
        result = fn(event)
        assert "Bash" in result
        assert "pytest" in result

    def test_tool_name_context_write(self):
        fn = self._fn()
        event = {
            "tool_name": "Write",
            "tool_input": {"path": "/home/user/project/src/auth.py"},
        }
        result = fn(event)
        assert "Write" in result
        assert "auth.py" in result

    def test_bare_tool_name_fallback(self):
        fn = self._fn()
        event = {"tool_name": "SomeTool", "tool_input": {}}
        assert fn(event) == "SomeTool"

    def test_empty_event_returns_claude(self):
        fn = self._fn()
        assert fn({}) == "Claude"

    def test_truncation(self):
        fn = self._fn()
        long_title = "A" * 200
        event = {
            "tool_name": "TodoWrite",
            "tool_input": {"plan_description": long_title},
        }
        result = fn(event, max_length=60)
        assert len(result) <= 60
        assert result.endswith("…")

    def test_max_length_respected(self):
        fn = self._fn()
        event = {
            "tool_name": "TodoWrite",
            "tool_input": {"plan_description": "Short"},
        }
        result = fn(event, max_length=60)
        assert result == "Short"


# ---------------------------------------------------------------------------
# 2. build_osc_sequence()
# ---------------------------------------------------------------------------


class TestBuildOscSequence:
    """Unit tests for OSC escape sequence generation."""

    def _fn(self):
        from claude_mpm.hooks.terminal_title import build_osc_sequence

        return build_osc_sequence

    def test_format(self):
        fn = self._fn()
        result = fn("My Title")
        assert result == "\033]0;My Title\007"

    def test_control_chars_stripped(self):
        fn = self._fn()
        result = fn("Title\x1bWith\x00Control")
        # ESC and NUL must be stripped from the embedded title
        inner = result[len("\033]0;") : -len("\007")]
        assert "\x1b" not in inner
        assert "\x00" not in inner

    def test_empty_string(self):
        fn = self._fn()
        result = fn("")
        assert result == "\033]0;\007"


# ---------------------------------------------------------------------------
# 3. is_enabled()
# ---------------------------------------------------------------------------


class TestIsEnabled:
    """Unit tests for the is_enabled() feature-flag helper."""

    def _fn(self):
        from claude_mpm.hooks.terminal_title import is_enabled

        return is_enabled

    def test_disabled_by_default(self):
        fn = self._fn()
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("CLAUDE_MPM_TERMINAL_TITLE", None)
            assert fn() is False

    def test_enabled_via_true(self):
        fn = self._fn()
        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "true"}, clear=False):
            assert fn() is True

    def test_enabled_via_1(self):
        fn = self._fn()
        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "1"}, clear=False):
            assert fn() is True

    def test_enabled_via_yes(self):
        fn = self._fn()
        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "yes"}, clear=False):
            assert fn() is True

    def test_enabled_via_on(self):
        fn = self._fn()
        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "on"}, clear=False):
            assert fn() is True

    def test_disabled_via_false(self):
        fn = self._fn()
        with patch.dict(
            os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "false"}, clear=False
        ):
            assert fn() is False

    def test_disabled_via_0(self):
        fn = self._fn()
        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "0"}, clear=False):
            assert fn() is False

    def test_case_insensitive(self):
        fn = self._fn()
        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "TRUE"}, clear=False):
            assert fn() is True


# ---------------------------------------------------------------------------
# 4. get_max_length()
# ---------------------------------------------------------------------------


class TestGetMaxLength:
    """Unit tests for the get_max_length() env-var helper."""

    def _fn(self):
        from claude_mpm.hooks.terminal_title import get_max_length

        return get_max_length

    def test_default_is_60(self):
        fn = self._fn()
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("CLAUDE_MPM_TERMINAL_TITLE_MAX_LEN", None)
            assert fn() == 60

    def test_custom_value(self):
        fn = self._fn()
        with patch.dict(
            os.environ,
            {"CLAUDE_MPM_TERMINAL_TITLE_MAX_LEN": "80"},
            clear=False,
        ):
            assert fn() == 80

    def test_invalid_value_falls_back_to_default(self):
        fn = self._fn()
        with patch.dict(
            os.environ,
            {"CLAUDE_MPM_TERMINAL_TITLE_MAX_LEN": "not-a-number"},
            clear=False,
        ):
            assert fn() == 60

    def test_empty_value_falls_back_to_default(self):
        fn = self._fn()
        with patch.dict(
            os.environ,
            {"CLAUDE_MPM_TERMINAL_TITLE_MAX_LEN": ""},
            clear=False,
        ):
            assert fn() == 60


# ---------------------------------------------------------------------------
# 5. get_trigger_tools()
# ---------------------------------------------------------------------------


class TestGetTriggerTools:
    """Unit tests for the get_trigger_tools() env-var helper."""

    def _fn(self):
        from claude_mpm.hooks.terminal_title import get_trigger_tools

        return get_trigger_tools

    def test_default_includes_todo_write_and_exit_plan_mode(self):
        fn = self._fn()
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("CLAUDE_MPM_TERMINAL_TITLE_EVENTS", None)
            result = fn()
            assert "TodoWrite" in result
            assert "ExitPlanMode" in result

    def test_custom_single_tool(self):
        fn = self._fn()
        with patch.dict(
            os.environ,
            {"CLAUDE_MPM_TERMINAL_TITLE_EVENTS": "TodoWrite"},
            clear=False,
        ):
            result = fn()
            assert result == frozenset({"TodoWrite"})

    def test_custom_multiple_tools(self):
        fn = self._fn()
        with patch.dict(
            os.environ,
            {"CLAUDE_MPM_TERMINAL_TITLE_EVENTS": "TodoWrite,MyTool"},
            clear=False,
        ):
            result = fn()
            assert "TodoWrite" in result
            assert "MyTool" in result

    def test_empty_value_returns_default(self):
        fn = self._fn()
        with patch.dict(
            os.environ,
            {"CLAUDE_MPM_TERMINAL_TITLE_EVENTS": ""},
            clear=False,
        ):
            result = fn()
            # Should fall back to default
            assert "TodoWrite" in result
            assert "ExitPlanMode" in result

    def test_whitespace_stripped(self):
        fn = self._fn()
        with patch.dict(
            os.environ,
            {"CLAUDE_MPM_TERMINAL_TITLE_EVENTS": " TodoWrite , ExitPlanMode "},
            clear=False,
        ):
            result = fn()
            assert "TodoWrite" in result
            assert "ExitPlanMode" in result


# ---------------------------------------------------------------------------
# 6. Integration: _build_terminal_title_sequence in tool_handler.py
# ---------------------------------------------------------------------------


class TestBuildTerminalTitleSequence:
    """Integration tests for the OSC sequence builder in tool_handler.py."""

    def _fn(self):
        from claude_mpm.hooks.claude_hooks.handlers.tool_handler import (
            _build_terminal_title_sequence,
        )

        return _build_terminal_title_sequence

    def _todo_write_event(self, plan_description="Build the auth layer"):
        return {
            "hook_event_name": "PostToolUse",
            "tool_name": "TodoWrite",
            "tool_input": {"plan_description": plan_description},
            "session_id": "test-session",
            "cwd": "/tmp/project",
            "exit_code": 0,
        }

    def test_returns_empty_when_feature_disabled(self):
        fn = self._fn()
        event = self._todo_write_event()
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("CLAUDE_MPM_TERMINAL_TITLE", None)
            result = fn(event)
        assert result == ""

    def test_returns_sequence_when_enabled_via_true(self):
        fn = self._fn()
        event = self._todo_write_event("Implement login flow")
        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "true"}, clear=False):
            result = fn(event)
        assert result.startswith("\033]0;")
        assert result.endswith("\007")
        assert "Implement login flow" in result

    def test_returns_empty_for_non_trigger_tool(self):
        fn = self._fn()
        event = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "exit_code": 0,
        }
        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "true"}, clear=False):
            result = fn(event)
        assert result == ""

    def test_custom_trigger_tool_fires(self):
        fn = self._fn()
        event = {
            "hook_event_name": "PostToolUse",
            "tool_name": "MyCustomTool",
            "tool_input": {"plan_description": "Custom action"},
            "exit_code": 0,
        }
        with patch.dict(
            os.environ,
            {
                "CLAUDE_MPM_TERMINAL_TITLE": "true",
                "CLAUDE_MPM_TERMINAL_TITLE_EVENTS": "MyCustomTool",
            },
            clear=False,
        ):
            result = fn(event)
        assert result != ""
        assert "Custom action" in result

    def test_respects_max_len_env_var(self):
        fn = self._fn()
        long_plan = "A very long plan description that exceeds twenty chars"
        event = self._todo_write_event(long_plan)
        with patch.dict(
            os.environ,
            {
                "CLAUDE_MPM_TERMINAL_TITLE": "true",
                "CLAUDE_MPM_TERMINAL_TITLE_MAX_LEN": "20",
            },
            clear=False,
        ):
            result = fn(event)
        # Strip OSC prefix/suffix to get the title
        inner = result[len("\033]0;") : -len("\007")]
        assert len(inner) <= 20


# ---------------------------------------------------------------------------
# 7. End-to-end dispatch path tests
# ---------------------------------------------------------------------------


class TestDispatchPath:
    """Simulate a real PostToolUse hook event through the dispatch chain.

    Uses real ClaudeHookHandler + mocked connection_manager to avoid network
    calls, and captures stdout to assert on the final JSON response.
    """

    def _make_handler(self):
        """Create a ClaudeHookHandler with all network I/O mocked out."""
        from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        # Prevent any actual socket/HTTP emission
        handler.connection_manager = MagicMock()
        handler.connection_manager.emit_event = MagicMock()
        return handler

    def _run_route_event(self, handler, event: dict):
        """Call _route_event and return (return_value, captured_stdout)."""
        return_value = handler._route_event(event)
        captured = StringIO()
        with patch("sys.stdout", captured):
            if isinstance(return_value, dict) and "terminalSequence" in return_value:
                handler._continue_execution(
                    terminal_sequence=return_value["terminalSequence"]
                )
            elif isinstance(return_value, dict) and (
                "decision" in return_value or "hookSpecificOutput" in return_value
            ):
                print(json.dumps(return_value), file=captured)
            else:
                handler._continue_execution(return_value)
        return return_value, captured.getvalue()

    def _todo_write_post_event(self, plan_description="Implement the auth layer"):
        return {
            "hook_event_name": "PostToolUse",
            "tool_name": "TodoWrite",
            "tool_input": {"plan_description": plan_description},
            "session_id": "e2e-test-session",
            "cwd": "/tmp/test-project",
            "exit_code": 0,
        }

    def test_enabled_feature_injects_terminal_sequence(self):
        """With CLAUDE_MPM_TERMINAL_TITLE=true, a TodoWrite PostToolUse should
        include terminalSequence in the hook response."""
        handler = self._make_handler()
        event = self._todo_write_post_event("Implement auth layer")

        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "true"}, clear=False):
            _, stdout = self._run_route_event(handler, event)

        response = json.loads(stdout.strip())
        assert response.get("continue") is True
        assert "terminalSequence" in response
        seq = response["terminalSequence"]
        assert seq.startswith("\033]0;")
        assert seq.endswith("\007")
        assert "Implement auth layer" in seq

    def test_disabled_feature_produces_plain_continue(self):
        """With CLAUDE_MPM_TERMINAL_TITLE unset/false, PostToolUse should return
        the plain {\"continue\": true} without any terminalSequence."""
        handler = self._make_handler()
        event = self._todo_write_post_event("Implement auth layer")

        with patch.dict(
            os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "false"}, clear=False
        ):
            _, stdout = self._run_route_event(handler, event)

        response = json.loads(stdout.strip())
        assert response.get("continue") is True
        assert "terminalSequence" not in response

    def test_non_todo_write_tool_unaffected(self):
        """A PostToolUse for a Bash tool must never inject terminalSequence,
        even when the feature is enabled."""
        handler = self._make_handler()
        event = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "pytest tests/"},
            "session_id": "e2e-test-session",
            "cwd": "/tmp",
            "exit_code": 0,
        }

        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "true"}, clear=False):
            _, stdout = self._run_route_event(handler, event)

        response = json.loads(stdout.strip())
        assert response.get("continue") is True
        assert "terminalSequence" not in response

    def test_existing_pre_tool_behaviour_unchanged(self):
        """PreToolUse events must still return {\"continue\": true} unmodified."""
        handler = self._make_handler()
        event = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"path": "/tmp/file.txt"},
            "session_id": "e2e-test-session",
            "cwd": "/tmp",
        }

        with patch.dict(os.environ, {"CLAUDE_MPM_TERMINAL_TITLE": "true"}, clear=False):
            _, stdout = self._run_route_event(handler, event)

        response = json.loads(stdout.strip())
        assert response.get("continue") is True
        assert "terminalSequence" not in response


# ---------------------------------------------------------------------------
# 8. _continue_execution signature tests
# ---------------------------------------------------------------------------


class TestContinueExecution:
    """Verify the _continue_execution signature."""

    def _make_handler(self):
        from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        handler.connection_manager = MagicMock()
        return handler

    def test_plain_continue(self):
        handler = self._make_handler()
        out = StringIO()
        with patch("sys.stdout", out):
            handler._continue_execution()
        assert json.loads(out.getvalue()) == {"continue": True}

    def test_with_terminal_sequence(self):
        handler = self._make_handler()
        out = StringIO()
        with patch("sys.stdout", out):
            handler._continue_execution(terminal_sequence="\033]0;Hello\007")
        result = json.loads(out.getvalue())
        assert result == {"continue": True, "terminalSequence": "\033]0;Hello\007"}

    def test_with_modified_input_and_terminal_sequence(self):
        handler = self._make_handler()
        out = StringIO()
        with patch("sys.stdout", out):
            handler._continue_execution(
                {"key": "value"}, terminal_sequence="\033]0;Test\007"
            )
        result = json.loads(out.getvalue())
        assert result["continue"] is True
        assert result["tool_input"] == {"key": "value"}
        assert result["terminalSequence"] == "\033]0;Test\007"

    def test_terminal_sequence_none_produces_plain(self):
        handler = self._make_handler()
        out = StringIO()
        with patch("sys.stdout", out):
            handler._continue_execution(terminal_sequence=None)
        assert json.loads(out.getvalue()) == {"continue": True}
