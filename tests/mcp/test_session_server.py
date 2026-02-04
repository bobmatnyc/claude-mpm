"""Tests for MCP SessionServer.

Tests MCP tool handlers, input validation, error handling, and serialization.
All SessionManager operations are mocked.
"""

import json
from dataclasses import asdict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.mcp.errors import SessionError
from claude_mpm.mcp.models import SessionInfo, SessionResult, SessionStatus
from claude_mpm.mcp.session_server import (
    SessionServer,
    _session_info_to_dict,
    _session_result_to_dict,
)


class TestSessionInfoToDict:
    """Tests for _session_info_to_dict() helper function."""

    def test_converts_session_info(self):
        """Should convert SessionInfo to dict."""
        info = SessionInfo(
            session_id="test-123",
            status=SessionStatus.ACTIVE,
            start_time="2025-01-01T00:00:00Z",
            working_directory="/test",
            message_count=5,
        )

        result = _session_info_to_dict(info)

        assert result["session_id"] == "test-123"
        assert result["start_time"] == "2025-01-01T00:00:00Z"
        assert result["working_directory"] == "/test"
        assert result["message_count"] == 5

    def test_converts_status_to_string(self):
        """Should convert SessionStatus enum to string value."""
        info = SessionInfo(
            session_id="test",
            status=SessionStatus.COMPLETED,
            start_time="2025-01-01T00:00:00Z",
            working_directory="/test",
        )

        result = _session_info_to_dict(info)

        assert result["status"] == "completed"
        assert isinstance(result["status"], str)

    def test_all_status_values(self):
        """Should convert all status enum values correctly."""
        for status in SessionStatus:
            info = SessionInfo(
                session_id=f"test-{status.value}",
                status=status,
                start_time="2025-01-01T00:00:00Z",
                working_directory="/test",
            )

            result = _session_info_to_dict(info)

            assert result["status"] == status.value


class TestSessionResultToDict:
    """Tests for _session_result_to_dict() helper function."""

    def test_converts_session_result(self):
        """Should convert SessionResult to dict."""
        result_obj = SessionResult(
            success=True,
            session_id="result-123",
            output="Hello, world!",
            messages=[{"type": "message"}],
        )

        result = _session_result_to_dict(result_obj)

        assert result["success"] is True
        assert result["session_id"] == "result-123"
        assert result["output"] == "Hello, world!"
        assert result["messages"] == [{"type": "message"}]

    def test_handles_none_values(self):
        """Should handle None values correctly."""
        result_obj = SessionResult(
            success=False,
            error="Failed",
        )

        result = _session_result_to_dict(result_obj)

        assert result["success"] is False
        assert result["session_id"] is None
        assert result["output"] is None
        assert result["error"] == "Failed"


class TestSessionServerInit:
    """Tests for SessionServer initialization."""

    def test_default_initialization(self):
        """Should initialize with defaults."""
        with patch("claude_mpm.mcp.session_server.SessionManager") as MockManager:
            server = SessionServer()

            assert server.server is not None
            MockManager.assert_called_once_with(
                max_concurrent=5,
                default_timeout=None,
            )

    def test_custom_initialization(self):
        """Should accept custom parameters."""
        with patch("claude_mpm.mcp.session_server.SessionManager") as MockManager:
            server = SessionServer(max_concurrent=10, default_timeout=60.0)

            MockManager.assert_called_once_with(
                max_concurrent=10,
                default_timeout=60.0,
            )


class TestDispatchTool:
    """Tests for _dispatch_tool() method."""

    @pytest.mark.asyncio
    async def test_dispatches_to_start_handler(self):
        """Should dispatch mpm_session_start to _handle_start."""
        with patch("claude_mpm.mcp.session_server.SessionManager"):
            server = SessionServer()
            server._handle_start = AsyncMock(return_value={"success": True})

            result = await server._dispatch_tool(
                "mpm_session_start", {"prompt": "Hello"}
            )

            server._handle_start.assert_called_once_with({"prompt": "Hello"})
            assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_dispatches_to_continue_handler(self):
        """Should dispatch mpm_session_continue to _handle_continue."""
        with patch("claude_mpm.mcp.session_server.SessionManager"):
            server = SessionServer()
            server._handle_continue = AsyncMock(return_value={"continued": True})

            result = await server._dispatch_tool(
                "mpm_session_continue",
                {"session_id": "test", "prompt": "Continue"},
            )

            server._handle_continue.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatches_to_status_handler(self):
        """Should dispatch mpm_session_status to _handle_status."""
        with patch("claude_mpm.mcp.session_server.SessionManager"):
            server = SessionServer()
            server._handle_status = AsyncMock(return_value={"status": "active"})

            result = await server._dispatch_tool(
                "mpm_session_status", {"session_id": "test"}
            )

            server._handle_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatches_to_list_handler(self):
        """Should dispatch mpm_session_list to _handle_list."""
        with patch("claude_mpm.mcp.session_server.SessionManager"):
            server = SessionServer()
            server._handle_list = AsyncMock(return_value={"sessions": []})

            result = await server._dispatch_tool("mpm_session_list", {})

            server._handle_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatches_to_stop_handler(self):
        """Should dispatch mpm_session_stop to _handle_stop."""
        with patch("claude_mpm.mcp.session_server.SessionManager"):
            server = SessionServer()
            server._handle_stop = AsyncMock(return_value={"stopped": True})

            result = await server._dispatch_tool(
                "mpm_session_stop", {"session_id": "test"}
            )

            server._handle_stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_for_unknown_tool(self):
        """Should raise ValueError for unknown tool name."""
        with patch("claude_mpm.mcp.session_server.SessionManager"):
            server = SessionServer()

            with pytest.raises(ValueError) as exc_info:
                await server._dispatch_tool("unknown_tool", {})

            assert "Unknown tool" in str(exc_info.value)


class TestHandleStart:
    """Tests for _handle_start() tool handler."""

    @pytest.mark.asyncio
    async def test_calls_manager_start_session(self):
        """Should call manager.start_session with arguments."""
        mock_manager = MagicMock()
        mock_manager.start_session = AsyncMock(
            return_value=SessionResult(
                success=True,
                session_id="new-123",
                output="Started",
            )
        )

        with patch(
            "claude_mpm.mcp.session_server.SessionManager",
            return_value=mock_manager,
        ):
            server = SessionServer()

            result = await server._handle_start(
                {
                    "prompt": "Hello",
                    "working_directory": "/test",
                    "no_hooks": True,
                    "no_tickets": True,
                    "timeout": 30.0,
                }
            )

        mock_manager.start_session.assert_called_once_with(
            prompt="Hello",
            working_directory="/test",
            no_hooks=True,
            no_tickets=True,
            timeout=30.0,
        )

    @pytest.mark.asyncio
    async def test_returns_session_result_dict(self):
        """Should return SessionResult as dictionary."""
        mock_manager = MagicMock()
        mock_manager.start_session = AsyncMock(
            return_value=SessionResult(
                success=True,
                session_id="result-456",
                output="Hello output",
                messages=[{"type": "assistant"}],
            )
        )

        with patch(
            "claude_mpm.mcp.session_server.SessionManager",
            return_value=mock_manager,
        ):
            server = SessionServer()

            result = await server._handle_start({"prompt": "Test"})

        assert result["success"] is True
        assert result["session_id"] == "result-456"
        assert result["output"] == "Hello output"

    @pytest.mark.asyncio
    async def test_uses_defaults_for_optional_args(self):
        """Should use defaults when optional arguments not provided."""
        mock_manager = MagicMock()
        mock_manager.start_session = AsyncMock(
            return_value=SessionResult(success=True, session_id="def-789")
        )

        with patch(
            "claude_mpm.mcp.session_server.SessionManager",
            return_value=mock_manager,
        ):
            server = SessionServer()

            await server._handle_start({"prompt": "Test"})

        mock_manager.start_session.assert_called_once_with(
            prompt="Test",
            working_directory=None,
            no_hooks=False,
            no_tickets=False,
            timeout=None,
        )


class TestHandleContinue:
    """Tests for _handle_continue() tool handler."""

    @pytest.mark.asyncio
    async def test_calls_manager_continue_session(self):
        """Should call manager.continue_session with arguments."""
        mock_manager = MagicMock()
        mock_manager.continue_session = AsyncMock(
            return_value=SessionResult(
                success=True,
                session_id="cont-123",
                output="Continued",
            )
        )

        with patch(
            "claude_mpm.mcp.session_server.SessionManager",
            return_value=mock_manager,
        ):
            server = SessionServer()

            result = await server._handle_continue(
                {
                    "session_id": "cont-123",
                    "prompt": "Continue please",
                    "fork": True,
                    "timeout": 60.0,
                }
            )

        mock_manager.continue_session.assert_called_once_with(
            session_id="cont-123",
            prompt="Continue please",
            fork=True,
            timeout=60.0,
        )

    @pytest.mark.asyncio
    async def test_uses_defaults_for_optional_args(self):
        """Should use defaults when optional arguments not provided."""
        mock_manager = MagicMock()
        mock_manager.continue_session = AsyncMock(
            return_value=SessionResult(success=True)
        )

        with patch(
            "claude_mpm.mcp.session_server.SessionManager",
            return_value=mock_manager,
        ):
            server = SessionServer()

            await server._handle_continue({"session_id": "test", "prompt": "Next"})

        mock_manager.continue_session.assert_called_once_with(
            session_id="test",
            prompt="Next",
            fork=False,
            timeout=None,
        )


class TestHandleStatus:
    """Tests for _handle_status() tool handler."""

    @pytest.mark.asyncio
    async def test_returns_session_info(self):
        """Should return SessionInfo when session found."""
        mock_manager = MagicMock()
        mock_manager.get_session_status = AsyncMock(
            return_value=SessionInfo(
                session_id="status-123",
                status=SessionStatus.ACTIVE,
                start_time="2025-01-01T00:00:00Z",
                working_directory="/test",
                message_count=3,
            )
        )

        with patch(
            "claude_mpm.mcp.session_server.SessionManager",
            return_value=mock_manager,
        ):
            server = SessionServer()

            result = await server._handle_status({"session_id": "status-123"})

        assert result["session_id"] == "status-123"
        assert result["status"] == "active"
        assert result["found"] is True

    @pytest.mark.asyncio
    async def test_returns_error_when_not_found(self):
        """Should return error when session not found."""
        mock_manager = MagicMock()
        mock_manager.get_session_status = AsyncMock(return_value=None)

        with patch(
            "claude_mpm.mcp.session_server.SessionManager",
            return_value=mock_manager,
        ):
            server = SessionServer()

            result = await server._handle_status({"session_id": "nonexistent"})

        assert result["found"] is False
        assert "error" in result
        assert result["session_id"] == "nonexistent"


class TestHandleList:
    """Tests for _handle_list() tool handler."""

    @pytest.mark.asyncio
    async def test_returns_all_sessions(self):
        """Should return all sessions when no filter."""
        mock_manager = MagicMock()
        mock_manager.list_sessions = AsyncMock(
            return_value=[
                SessionInfo(
                    session_id="s1",
                    status=SessionStatus.ACTIVE,
                    start_time="2025-01-01T00:00:00Z",
                    working_directory="/test",
                ),
                SessionInfo(
                    session_id="s2",
                    status=SessionStatus.COMPLETED,
                    start_time="2025-01-01T00:00:00Z",
                    working_directory="/test",
                ),
            ]
        )
        mock_manager.get_active_count = AsyncMock(return_value=1)

        with patch(
            "claude_mpm.mcp.session_server.SessionManager",
            return_value=mock_manager,
        ):
            server = SessionServer()

            result = await server._handle_list({})

        assert result["count"] == 2
        assert result["active_count"] == 1
        assert len(result["sessions"]) == 2

    @pytest.mark.asyncio
    async def test_filters_by_status(self):
        """Should filter sessions by status when provided."""
        mock_manager = MagicMock()
        mock_manager.list_sessions = AsyncMock(
            return_value=[
                SessionInfo(
                    session_id="s1",
                    status=SessionStatus.ACTIVE,
                    start_time="2025-01-01T00:00:00Z",
                    working_directory="/test",
                ),
            ]
        )
        mock_manager.get_active_count = AsyncMock(return_value=1)

        with patch(
            "claude_mpm.mcp.session_server.SessionManager",
            return_value=mock_manager,
        ):
            server = SessionServer()

            result = await server._handle_list({"status": "active"})

        mock_manager.list_sessions.assert_called_once_with(status=SessionStatus.ACTIVE)

    @pytest.mark.asyncio
    async def test_returns_error_for_invalid_status(self):
        """Should return error for invalid status filter."""
        mock_manager = MagicMock()

        with patch(
            "claude_mpm.mcp.session_server.SessionManager",
            return_value=mock_manager,
        ):
            server = SessionServer()

            result = await server._handle_list({"status": "invalid_status"})

        assert "error" in result
        assert "Invalid status filter" in result["error"]
        assert "valid_statuses" in result


class TestHandleStop:
    """Tests for _handle_stop() tool handler."""

    @pytest.mark.asyncio
    async def test_stops_session(self):
        """Should stop session and return result."""
        mock_manager = MagicMock()
        mock_manager.stop_session = AsyncMock(return_value=True)

        with patch(
            "claude_mpm.mcp.session_server.SessionManager",
            return_value=mock_manager,
        ):
            server = SessionServer()

            result = await server._handle_stop(
                {"session_id": "stop-123", "force": False}
            )

        assert result["session_id"] == "stop-123"
        assert result["stopped"] is True
        assert result["force"] is False
        mock_manager.stop_session.assert_called_once_with(
            session_id="stop-123",
            force=False,
        )

    @pytest.mark.asyncio
    async def test_force_stop(self):
        """Should force stop when force=True."""
        mock_manager = MagicMock()
        mock_manager.stop_session = AsyncMock(return_value=True)

        with patch(
            "claude_mpm.mcp.session_server.SessionManager",
            return_value=mock_manager,
        ):
            server = SessionServer()

            result = await server._handle_stop(
                {"session_id": "force-456", "force": True}
            )

        assert result["force"] is True
        mock_manager.stop_session.assert_called_once_with(
            session_id="force-456",
            force=True,
        )

    @pytest.mark.asyncio
    async def test_returns_false_when_session_not_found(self):
        """Should return stopped=False when session not found."""
        mock_manager = MagicMock()
        mock_manager.stop_session = AsyncMock(return_value=False)

        with patch(
            "claude_mpm.mcp.session_server.SessionManager",
            return_value=mock_manager,
        ):
            server = SessionServer()

            result = await server._handle_stop({"session_id": "nonexistent"})

        assert result["stopped"] is False


class TestToolCallErrorHandling:
    """Tests for error handling in tool call dispatch."""

    @pytest.mark.asyncio
    async def test_handles_session_error(self):
        """Should return error response for SessionError."""
        mock_manager = MagicMock()
        mock_manager.start_session = AsyncMock(
            side_effect=SessionError("Test error", session_id="err-123")
        )

        with patch(
            "claude_mpm.mcp.session_server.SessionManager",
            return_value=mock_manager,
        ):
            server = SessionServer()

            # Call tool through the server's call_tool handler
            # We need to extract the handler from _setup_handlers
            # Instead, test _dispatch_tool and error catching in call_tool

            # Test that _dispatch_tool propagates the error
            with pytest.raises(SessionError):
                await server._dispatch_tool("mpm_session_start", {"prompt": "Test"})

    @pytest.mark.asyncio
    async def test_handles_unknown_tool_error(self):
        """Should raise ValueError for unknown tool."""
        with patch("claude_mpm.mcp.session_server.SessionManager"):
            server = SessionServer()

            with pytest.raises(ValueError) as exc_info:
                await server._dispatch_tool("invalid_tool", {})

            assert "Unknown tool: invalid_tool" in str(exc_info.value)


class TestListTools:
    """Tests for list_tools functionality."""

    def test_server_has_five_tools(self):
        """SessionServer should register 5 tools."""
        # We can't easily test the decorator-based registration,
        # but we can verify the dispatch handlers exist
        with patch("claude_mpm.mcp.session_server.SessionManager"):
            server = SessionServer()

            handlers = {
                "mpm_session_start": server._handle_start,
                "mpm_session_continue": server._handle_continue,
                "mpm_session_status": server._handle_status,
                "mpm_session_list": server._handle_list,
                "mpm_session_stop": server._handle_stop,
            }

            assert len(handlers) == 5
            for name, handler in handlers.items():
                assert callable(handler), f"{name} should be callable"


class TestSessionInfoSerialization:
    """Tests for session info serialization edge cases."""

    def test_handles_all_optional_fields(self):
        """Should serialize all optional fields correctly."""
        info = SessionInfo(
            session_id="full-test",
            status=SessionStatus.COMPLETED,
            start_time="2025-01-01T00:00:00Z",
            working_directory="/full/test",
            last_activity="2025-01-01T01:00:00Z",
            message_count=10,
            last_output="Final output text",
        )

        result = _session_info_to_dict(info)

        assert result["last_activity"] == "2025-01-01T01:00:00Z"
        assert result["message_count"] == 10
        assert result["last_output"] == "Final output text"

    def test_handles_none_optional_fields(self):
        """Should serialize None optional fields correctly."""
        info = SessionInfo(
            session_id="minimal",
            status=SessionStatus.STARTING,
            start_time="2025-01-01T00:00:00Z",
            working_directory="/test",
        )

        result = _session_info_to_dict(info)

        assert result["last_activity"] is None
        assert result["message_count"] == 0
        assert result["last_output"] is None

    def test_result_is_json_serializable(self):
        """Session info dict should be JSON serializable."""
        info = SessionInfo(
            session_id="json-test",
            status=SessionStatus.ACTIVE,
            start_time="2025-01-01T00:00:00Z",
            working_directory="/test",
            message_count=5,
        )

        result = _session_info_to_dict(info)

        # Should not raise
        json_str = json.dumps(result)
        assert "json-test" in json_str
        assert "active" in json_str


class TestSessionResultSerialization:
    """Tests for session result serialization edge cases."""

    def test_handles_empty_messages(self):
        """Should serialize empty messages list correctly."""
        result_obj = SessionResult(success=True)

        result = _session_result_to_dict(result_obj)

        assert result["messages"] == []
        assert isinstance(result["messages"], list)

    def test_handles_complex_messages(self):
        """Should serialize complex message structures."""
        result_obj = SessionResult(
            success=True,
            session_id="complex",
            messages=[
                {"type": "assistant", "content": {"text": "Hello"}},
                {"type": "tool", "name": "read", "args": {"path": "/test"}},
            ],
        )

        result = _session_result_to_dict(result_obj)

        assert len(result["messages"]) == 2
        assert result["messages"][0]["content"] == {"text": "Hello"}

    def test_result_is_json_serializable(self):
        """Session result dict should be JSON serializable."""
        result_obj = SessionResult(
            success=True,
            session_id="json-result",
            output="Test output",
            messages=[{"type": "message"}],
        )

        result = _session_result_to_dict(result_obj)

        # Should not raise
        json_str = json.dumps(result)
        assert "json-result" in json_str
        assert "Test output" in json_str
