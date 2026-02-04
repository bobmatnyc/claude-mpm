"""NDJSON stream parsing utilities for Claude Code output."""

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from typing import Any


def extract_session_id(ndjson_line: str) -> str | None:
    """Extract session_id from a single NDJSON line."""
    try:
        data: dict[str, Any] = json.loads(ndjson_line.strip())
        session_id = data.get("session_id") or data.get("sessionId")
        return str(session_id) if session_id else None
    except json.JSONDecodeError:
        return None


async def extract_session_id_from_stream(
    stream: asyncio.StreamReader,
) -> str | None:
    """Extract session_id from the first message in stream."""
    while True:
        line = await stream.readline()
        if not line:
            return None
        session_id = extract_session_id(line.decode())
        if session_id:
            return session_id


class NDJSONStreamParser:
    """Async parser for NDJSON streams from Claude Code."""

    def __init__(self) -> None:
        self.session_id: str | None = None
        self.messages: list[dict[str, Any]] = []
        self.final_result: dict[str, Any] | None = None

    async def parse_stream(
        self,
        stream: asyncio.StreamReader,
        on_message: Callable[[dict[str, Any]], None] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Parse NDJSON stream and yield messages."""
        while True:
            line = await stream.readline()
            if not line:
                break

            line_str = line.decode().strip()
            if not line_str:
                continue

            try:
                data = json.loads(line_str)
            except json.JSONDecodeError:
                continue

            # Capture session_id from first message
            if not self.session_id:
                self.session_id = data.get("session_id") or data.get("sessionId")

            self.messages.append(data)

            # Capture final result
            if data.get("type") == "result":
                self.final_result = data

            if on_message:
                on_message(data)

            yield data

    def get_assistant_messages(self) -> list[dict[str, Any]]:
        """Get all assistant messages from the parsed stream."""
        return [m for m in self.messages if m.get("type") == "assistant"]

    def get_tool_calls(self) -> list[dict[str, Any]]:
        """Get all tool execution events."""
        return [m for m in self.messages if m.get("type") == "tool"]

    def is_success(self) -> bool:
        """Check if session completed successfully."""
        return (
            self.final_result is not None
            and self.final_result.get("subtype") == "success"
        )

    def get_error(self) -> str | None:
        """Get error message if session failed."""
        if self.final_result and self.final_result.get("subtype") == "error":
            return self.final_result.get("error")
        return None
