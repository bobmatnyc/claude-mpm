"""
STDIO Communication Handler for MCP
====================================

Handles stdio-based communication for the MCP server.
Manages JSON-RPC message exchange over stdin/stdout.

Part of ISS-0035: MCP Server Implementation - Core Server and Tool Registry
"""

import asyncio
import json
import sys
from typing import TYPE_CHECKING, Any, Dict, Optional

from claude_mpm.services.mcp_gateway.core.base import BaseMCPService
from claude_mpm.services.mcp_gateway.core.interfaces import IMCPCommunication

if TYPE_CHECKING:
    from asyncio import StreamReader, StreamWriter


class StdioHandler(BaseMCPService, IMCPCommunication):
    """
    STDIO-based communication handler for MCP.

    WHY: The MCP protocol uses stdio (stdin/stdout) for communication between
    Claude Code and MCP servers. This handler manages the low-level
    message exchange, ensuring proper JSON-RPC formatting and error handling.

    DESIGN DECISIONS:
    - Use asyncio streams for non-blocking I/O
    - Implement message framing with Content-Length headers (LSP-style)
    - Handle both notification and request/response patterns
    - Provide robust error recovery and logging
    """

    def __init__(self):
        """Initialize the STDIO handler."""
        super().__init__("StdioHandler")

        # Async streams
        self._reader: Optional[StreamReader] = None
        self._writer: Optional[StreamWriter] = None

        # Connection state
        self._connected = False

        # Message buffer for partial reads
        self._buffer = b""

        # Metrics
        self._metrics = {
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0,
            "bytes_sent": 0,
            "bytes_received": 0,
        }

    async def _do_initialize(self) -> bool:
        """
        Initialize the STDIO handler.

        Returns:
            True if initialization successful
        """
        try:
            self.log_info("Initializing STDIO handler")

            # Create async streams for stdin/stdout
            loop = asyncio.get_event_loop()

            # For stdin
            self._reader = asyncio.StreamReader()
            stdin_protocol = asyncio.StreamReaderProtocol(self._reader)
            await loop.connect_read_pipe(lambda: stdin_protocol, sys.stdin)

            # For stdout (we'll write directly to sys.stdout)
            # Note: stdout doesn't need async handling for writes

            self._connected = True
            self.log_info("STDIO handler initialized")
            return True

        except Exception as e:
            self.log_error(f"Failed to initialize STDIO handler: {e}")
            return False

    async def _do_shutdown(self) -> None:
        """Shutdown the STDIO handler."""
        self.log_info("Shutting down STDIO handler")

        self._connected = False

        # Close streams if needed
        if self._reader:
            self._reader = None

        self.log_info("STDIO handler shutdown complete")

    async def send_message(self, message: Dict[str, Any]) -> None:
        """
        Send a message to the MCP client via stdout.

        Uses Content-Length header for message framing (LSP-style).

        Args:
            message: Message to send
        """
        try:
            if not self._connected:
                raise RuntimeError("STDIO handler not connected")

            # Convert message to JSON
            json_str = json.dumps(message, separators=(",", ":"))
            json_bytes = json_str.encode("utf-8")

            # Create Content-Length header
            content_length = len(json_bytes)
            header = f"Content-Length: {content_length}\r\n\r\n"
            header_bytes = header.encode("ascii")

            # Write header and content to stdout
            sys.stdout.buffer.write(header_bytes)
            sys.stdout.buffer.write(json_bytes)
            sys.stdout.buffer.flush()

            # Update metrics
            self._metrics["messages_sent"] += 1
            self._metrics["bytes_sent"] += len(header_bytes) + len(json_bytes)

            self.log_debug(
                f"Sent message: {message.get('method', message.get('id', 'unknown'))}"
            )

        except Exception as e:
            self.log_error(f"Error sending message: {e}")
            self._metrics["errors"] += 1
            raise

    async def receive_message(self) -> Optional[Dict[str, Any]]:
        """
        Receive a message from the MCP client via stdin.

        Handles Content-Length based message framing.

        Returns:
            Received message or None if no message available
        """
        try:
            if not self._connected or not self._reader:
                return None

            # Read header to get content length
            headers = {}
            while True:
                line_bytes = await self._reader.readline()
                if not line_bytes:
                    # EOF reached
                    self._connected = False
                    return None

                line = line_bytes.decode("utf-8").rstrip("\r\n")

                if not line:
                    # Empty line indicates end of headers
                    break

                # Parse header
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip()] = value.strip()

            # Get content length
            content_length = headers.get("Content-Length")
            if not content_length:
                self.log_warning("No Content-Length header found")
                return None

            content_length = int(content_length)

            # Read content
            content_bytes = await self._reader.readexactly(content_length)

            # Parse JSON
            message = json.loads(content_bytes.decode("utf-8"))

            # Update metrics
            self._metrics["messages_received"] += 1
            self._metrics["bytes_received"] += len(line_bytes) + content_length

            self.log_debug(
                f"Received message: {message.get('method', message.get('id', 'unknown'))}"
            )

            return message

        except asyncio.IncompleteReadError:
            self.log_warning("Incomplete read - client may have disconnected")
            self._connected = False
            return None
        except json.JSONDecodeError as e:
            self.log_error(f"Invalid JSON received: {e}")
            self._metrics["errors"] += 1
            return None
        except Exception as e:
            self.log_error(f"Error receiving message: {e}")
            self._metrics["errors"] += 1
            return None

    async def send_response(self, request_id: str, result: Any) -> None:
        """
        Send a response to a request.

        Args:
            request_id: ID of the request being responded to
            result: Result data
        """
        response = {"jsonrpc": "2.0", "id": request_id, "result": result}
        await self.send_message(response)

    async def send_error(self, request_id: str, error: str, code: int = -1) -> None:
        """
        Send an error response.

        Args:
            request_id: ID of the request that caused the error
            error: Error message
            code: Error code (default -1 for generic error)
        """
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": error},
        }
        await self.send_message(response)

    async def send_notification(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send a notification (no response expected).

        Args:
            method: Notification method
            params: Optional parameters
        """
        notification = {"jsonrpc": "2.0", "method": method}
        if params:
            notification["params"] = params

        await self.send_message(notification)

    def is_connected(self) -> bool:
        """
        Check if communication channel is connected.

        Returns:
            True if connected
        """
        return self._connected

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get communication metrics.

        Returns:
            Metrics dictionary
        """
        return self._metrics.copy()


class AlternativeStdioHandler(StdioHandler):
    """
    Alternative STDIO handler using direct sys.stdin/stdout.

    This implementation doesn't use asyncio streams but instead
    reads directly from sys.stdin in a blocking manner, which
    can be simpler for some use cases.

    WHY: Some MCP implementations may work better with simpler
    blocking I/O, especially when running as a subprocess.
    """

    async def _do_initialize(self) -> bool:
        """
        Initialize the alternative STDIO handler.

        Returns:
            True if initialization successful
        """
        try:
            self.log_info("Initializing alternative STDIO handler")
            self._connected = True
            self.log_info("Alternative STDIO handler initialized")
            return True

        except Exception as e:
            self.log_error(f"Failed to initialize alternative STDIO handler: {e}")
            return False

    async def receive_message(self) -> Optional[Dict[str, Any]]:
        """
        Receive a message using blocking I/O with asyncio executor.

        Returns:
            Received message or None if no message available
        """
        try:
            if not self._connected:
                return None

            # Run blocking I/O in executor
            loop = asyncio.get_event_loop()
            message = await loop.run_in_executor(None, self._blocking_receive)

            if message:
                self._metrics["messages_received"] += 1
                self.log_debug(
                    f"Received message: {message.get('method', message.get('id', 'unknown'))}"
                )

            return message

        except Exception as e:
            self.log_error(f"Error receiving message: {e}")
            self._metrics["errors"] += 1
            return None

    def _blocking_receive(self) -> Optional[Dict[str, Any]]:
        """
        Blocking receive implementation.

        Returns:
            Received message or None
        """
        try:
            # Read headers
            headers = {}
            while True:
                line = sys.stdin.readline()
                if not line:
                    # EOF
                    self._connected = False
                    return None

                line = line.rstrip("\r\n")
                if not line:
                    # End of headers
                    break

                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip()] = value.strip()

            # Get content length
            content_length = headers.get("Content-Length")
            if not content_length:
                return None

            content_length = int(content_length)

            # Read content
            content = sys.stdin.read(content_length)

            # Parse JSON
            return json.loads(content)

        except Exception as e:
            self.log_error(f"Error in blocking receive: {e}")
            return None
