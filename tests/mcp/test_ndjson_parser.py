"""Tests for NDJSON stream parsing utilities.

Tests extract_session_id, extract_session_id_from_stream, and NDJSONStreamParser class.
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from claude_mpm.mcp.ndjson_parser import (
    NDJSONStreamParser,
    extract_session_id,
    extract_session_id_from_stream,
)


class TestExtractSessionId:
    """Tests for extract_session_id() function."""

    def test_valid_json_with_session_id(self):
        """extract_session_id should extract session_id from valid JSON."""
        line = '{"session_id": "test-123", "type": "message"}'

        result = extract_session_id(line)

        assert result == "test-123"

    def test_valid_json_with_sessionId_camelCase(self):
        """extract_session_id should extract sessionId (camelCase) from JSON."""
        line = '{"sessionId": "camel-456", "type": "message"}'

        result = extract_session_id(line)

        assert result == "camel-456"

    def test_prefers_session_id_over_sessionId(self):
        """extract_session_id should prefer session_id over sessionId."""
        line = '{"session_id": "snake", "sessionId": "camel"}'

        result = extract_session_id(line)

        assert result == "snake"

    def test_valid_json_without_session_id(self):
        """extract_session_id should return None if no session_id field."""
        line = '{"type": "message", "content": "Hello"}'

        result = extract_session_id(line)

        assert result is None

    def test_invalid_json(self):
        """extract_session_id should return None for invalid JSON."""
        line = "not valid json {"

        result = extract_session_id(line)

        assert result is None

    def test_empty_string(self):
        """extract_session_id should return None for empty string."""
        result = extract_session_id("")

        assert result is None

    def test_whitespace_only(self):
        """extract_session_id should return None for whitespace."""
        result = extract_session_id("   \n\t   ")

        assert result is None

    def test_null_session_id(self):
        """extract_session_id should return None for null session_id."""
        line = '{"session_id": null}'

        result = extract_session_id(line)

        assert result is None

    def test_empty_session_id(self):
        """extract_session_id should return None for empty session_id."""
        line = '{"session_id": ""}'

        result = extract_session_id(line)

        assert result is None

    def test_numeric_session_id(self):
        """extract_session_id should convert numeric session_id to string."""
        line = '{"session_id": 12345}'

        result = extract_session_id(line)

        assert result == "12345"

    def test_strips_whitespace(self):
        """extract_session_id should handle leading/trailing whitespace."""
        line = '  {"session_id": "test"}  \n'

        result = extract_session_id(line)

        assert result == "test"


class TestExtractSessionIdFromStream:
    """Tests for extract_session_id_from_stream() async function."""

    @pytest.mark.asyncio
    async def test_extracts_session_id_from_first_line(self):
        """extract_session_id_from_stream should get session_id from first valid line."""
        mock_reader = AsyncMock()
        mock_reader.readline = AsyncMock(
            side_effect=[
                b'{"session_id": "stream-123", "type": "init"}\n',
                b"",  # EOF
            ]
        )

        result = await extract_session_id_from_stream(mock_reader)

        assert result == "stream-123"

    @pytest.mark.asyncio
    async def test_skips_lines_without_session_id(self):
        """extract_session_id_from_stream should skip lines until finding session_id."""
        mock_reader = AsyncMock()
        mock_reader.readline = AsyncMock(
            side_effect=[
                b'{"type": "message"}\n',  # No session_id
                b'{"content": "hello"}\n',  # No session_id
                b'{"session_id": "found-456"}\n',  # Has session_id
                b"",  # EOF
            ]
        )

        result = await extract_session_id_from_stream(mock_reader)

        assert result == "found-456"
        # Should have called readline 3 times before finding it
        assert mock_reader.readline.call_count == 3

    @pytest.mark.asyncio
    async def test_returns_none_on_empty_stream(self):
        """extract_session_id_from_stream should return None for empty stream."""
        mock_reader = AsyncMock()
        mock_reader.readline = AsyncMock(return_value=b"")

        result = await extract_session_id_from_stream(mock_reader)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_session_id_in_stream(self):
        """extract_session_id_from_stream should return None if no session_id found."""
        mock_reader = AsyncMock()
        mock_reader.readline = AsyncMock(
            side_effect=[
                b'{"type": "message"}\n',
                b'{"content": "data"}\n',
                b"",  # EOF
            ]
        )

        result = await extract_session_id_from_stream(mock_reader)

        assert result is None


class TestNDJSONStreamParser:
    """Tests for NDJSONStreamParser class."""

    def test_initial_state(self):
        """NDJSONStreamParser should initialize with empty state."""
        parser = NDJSONStreamParser()

        assert parser.session_id is None
        assert parser.messages == []
        assert parser.final_result is None

    @pytest.mark.asyncio
    async def test_parse_stream_yields_messages(self):
        """parse_stream should yield parsed JSON messages."""
        parser = NDJSONStreamParser()
        mock_reader = AsyncMock()
        mock_reader.readline = AsyncMock(
            side_effect=[
                b'{"type": "message", "content": "hello"}\n',
                b'{"type": "message", "content": "world"}\n',
                b"",  # EOF
            ]
        )

        messages = []
        async for msg in parser.parse_stream(mock_reader):
            messages.append(msg)

        assert len(messages) == 2
        assert messages[0]["content"] == "hello"
        assert messages[1]["content"] == "world"

    @pytest.mark.asyncio
    async def test_parse_stream_captures_session_id(self):
        """parse_stream should capture session_id from first message."""
        parser = NDJSONStreamParser()
        mock_reader = AsyncMock()
        mock_reader.readline = AsyncMock(
            side_effect=[
                b'{"session_id": "parsed-123", "type": "init"}\n',
                b'{"type": "message"}\n',
                b"",  # EOF
            ]
        )

        async for _ in parser.parse_stream(mock_reader):
            pass

        assert parser.session_id == "parsed-123"

    @pytest.mark.asyncio
    async def test_parse_stream_captures_sessionId_camelCase(self):
        """parse_stream should capture sessionId (camelCase)."""
        parser = NDJSONStreamParser()
        mock_reader = AsyncMock()
        mock_reader.readline = AsyncMock(
            side_effect=[
                b'{"sessionId": "camel-789"}\n',
                b"",
            ]
        )

        async for _ in parser.parse_stream(mock_reader):
            pass

        assert parser.session_id == "camel-789"

    @pytest.mark.asyncio
    async def test_parse_stream_stores_messages(self):
        """parse_stream should store all messages internally."""
        parser = NDJSONStreamParser()
        mock_reader = AsyncMock()
        mock_reader.readline = AsyncMock(
            side_effect=[
                b'{"type": "a"}\n',
                b'{"type": "b"}\n',
                b'{"type": "c"}\n',
                b"",
            ]
        )

        async for _ in parser.parse_stream(mock_reader):
            pass

        assert len(parser.messages) == 3
        assert parser.messages[0]["type"] == "a"
        assert parser.messages[2]["type"] == "c"

    @pytest.mark.asyncio
    async def test_parse_stream_captures_final_result(self):
        """parse_stream should capture message with type='result'."""
        parser = NDJSONStreamParser()
        mock_reader = AsyncMock()
        mock_reader.readline = AsyncMock(
            side_effect=[
                b'{"type": "message"}\n',
                b'{"type": "result", "subtype": "success"}\n',
                b"",
            ]
        )

        async for _ in parser.parse_stream(mock_reader):
            pass

        assert parser.final_result is not None
        assert parser.final_result["type"] == "result"
        assert parser.final_result["subtype"] == "success"

    @pytest.mark.asyncio
    async def test_parse_stream_skips_invalid_json(self):
        """parse_stream should skip lines that are not valid JSON."""
        parser = NDJSONStreamParser()
        mock_reader = AsyncMock()
        mock_reader.readline = AsyncMock(
            side_effect=[
                b"not json\n",
                b'{"type": "valid"}\n',
                b"also not json",
                b"",
            ]
        )

        messages = []
        async for msg in parser.parse_stream(mock_reader):
            messages.append(msg)

        assert len(messages) == 1
        assert messages[0]["type"] == "valid"

    @pytest.mark.asyncio
    async def test_parse_stream_skips_empty_lines(self):
        """parse_stream should skip empty lines."""
        parser = NDJSONStreamParser()
        mock_reader = AsyncMock()
        mock_reader.readline = AsyncMock(
            side_effect=[
                b"\n",
                b"   \n",
                b'{"type": "data"}\n',
                b"\n",
                b"",
            ]
        )

        messages = []
        async for msg in parser.parse_stream(mock_reader):
            messages.append(msg)

        assert len(messages) == 1

    @pytest.mark.asyncio
    async def test_parse_stream_on_message_callback(self):
        """parse_stream should call on_message callback for each message."""
        parser = NDJSONStreamParser()
        mock_reader = AsyncMock()
        mock_reader.readline = AsyncMock(
            side_effect=[
                b'{"type": "a"}\n',
                b'{"type": "b"}\n',
                b"",
            ]
        )

        callback_calls = []

        def on_message(msg):
            callback_calls.append(msg)

        async for _ in parser.parse_stream(mock_reader, on_message=on_message):
            pass

        assert len(callback_calls) == 2
        assert callback_calls[0]["type"] == "a"
        assert callback_calls[1]["type"] == "b"


class TestNDJSONStreamParserGetters:
    """Tests for NDJSONStreamParser getter methods."""

    def test_get_assistant_messages_empty(self):
        """get_assistant_messages should return empty list when no messages."""
        parser = NDJSONStreamParser()

        result = parser.get_assistant_messages()

        assert result == []

    def test_get_assistant_messages_filters_correctly(self):
        """get_assistant_messages should return only assistant type messages."""
        parser = NDJSONStreamParser()
        parser.messages = [
            {"type": "assistant", "content": "Hello"},
            {"type": "tool", "name": "read_file"},
            {"type": "assistant", "content": "Done"},
            {"type": "result", "subtype": "success"},
        ]

        result = parser.get_assistant_messages()

        assert len(result) == 2
        assert result[0]["content"] == "Hello"
        assert result[1]["content"] == "Done"

    def test_get_tool_calls_empty(self):
        """get_tool_calls should return empty list when no tool messages."""
        parser = NDJSONStreamParser()

        result = parser.get_tool_calls()

        assert result == []

    def test_get_tool_calls_filters_correctly(self):
        """get_tool_calls should return only tool type messages."""
        parser = NDJSONStreamParser()
        parser.messages = [
            {"type": "assistant", "content": "Reading file"},
            {"type": "tool", "name": "read_file", "path": "/test.py"},
            {"type": "tool", "name": "write_file", "path": "/out.py"},
            {"type": "result", "subtype": "success"},
        ]

        result = parser.get_tool_calls()

        assert len(result) == 2
        assert result[0]["name"] == "read_file"
        assert result[1]["name"] == "write_file"

    def test_is_success_true(self):
        """is_success should return True when result subtype is success."""
        parser = NDJSONStreamParser()
        parser.final_result = {"type": "result", "subtype": "success"}

        assert parser.is_success() is True

    def test_is_success_false_error_subtype(self):
        """is_success should return False when result subtype is error."""
        parser = NDJSONStreamParser()
        parser.final_result = {"type": "result", "subtype": "error"}

        assert parser.is_success() is False

    def test_is_success_false_no_result(self):
        """is_success should return False when no final_result."""
        parser = NDJSONStreamParser()

        assert parser.is_success() is False

    def test_is_success_false_no_subtype(self):
        """is_success should return False when result has no subtype."""
        parser = NDJSONStreamParser()
        parser.final_result = {"type": "result"}

        assert parser.is_success() is False

    def test_get_error_returns_error_message(self):
        """get_error should return error message when subtype is error."""
        parser = NDJSONStreamParser()
        parser.final_result = {
            "type": "result",
            "subtype": "error",
            "error": "Something went wrong",
        }

        result = parser.get_error()

        assert result == "Something went wrong"

    def test_get_error_returns_none_on_success(self):
        """get_error should return None when subtype is success."""
        parser = NDJSONStreamParser()
        parser.final_result = {"type": "result", "subtype": "success"}

        result = parser.get_error()

        assert result is None

    def test_get_error_returns_none_no_result(self):
        """get_error should return None when no final_result."""
        parser = NDJSONStreamParser()

        result = parser.get_error()

        assert result is None

    def test_get_error_returns_none_missing_error_field(self):
        """get_error should return None when error field is missing."""
        parser = NDJSONStreamParser()
        parser.final_result = {"type": "result", "subtype": "error"}

        result = parser.get_error()

        assert result is None
