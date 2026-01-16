"""Communication adapters for managing async I/O with AI coding assistants.

This module provides the async communication layer that sits between
InstanceManager and TmuxOrchestrator, using RuntimeAdapter for parsing.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, AsyncIterator, Optional

from claude_mpm.commander.tmux_orchestrator import TmuxOrchestrator

from .base import RuntimeAdapter

if TYPE_CHECKING:
    from .base import ParsedResponse

logger = logging.getLogger(__name__)


class AdapterState(Enum):
    """States that a communication adapter can be in."""

    IDLE = "idle"  # Ready for input
    PROCESSING = "processing"  # Working on request
    WAITING = "waiting"  # Waiting for user input (e.g., permission)
    ERROR = "error"  # Error state


@dataclass
class AdapterResponse:
    """Response from a communication adapter.

    Attributes:
        content: The response content
        state: Current adapter state
        tool_uses: List of tools used in response
        files_modified: List of files edited
        is_complete: True if response is complete (prompt returned)

    Example:
        >>> response = AdapterResponse(
        ...     content="File created: test.py",
        ...     state=AdapterState.IDLE,
        ...     tool_uses=["Write"],
        ...     files_modified=["test.py"],
        ...     is_complete=True
        ... )
    """

    content: str
    state: AdapterState
    tool_uses: Optional[list[str]] = None
    files_modified: Optional[list[str]] = None
    is_complete: bool = False


class BaseCommunicationAdapter(ABC):
    """Abstract base class for communication adapters.

    A communication adapter manages the async I/O with an AI coding assistant
    via TmuxOrchestrator, maintaining state and handling streaming responses.

    Example:
        >>> orchestrator = TmuxOrchestrator()
        >>> adapter = ClaudeCodeCommunicationAdapter(orchestrator, "%0")
        >>> await adapter.send("Fix the bug in main.py")
        >>> response = await adapter.receive()
        >>> print(response.content)
    """

    @abstractmethod
    async def send(self, message: str) -> None:
        """Send a message to the assistant.

        Args:
            message: The message to send

        Example:
            >>> await adapter.send("Fix the bug in main.py")
        """

    @abstractmethod
    async def receive(self, timeout: float = 30.0) -> AdapterResponse:
        """Wait for and return response.

        Args:
            timeout: Maximum time to wait for response

        Returns:
            AdapterResponse with parsed content and state

        Example:
            >>> response = await adapter.receive(timeout=60.0)
            >>> print(response.content)
        """

    @abstractmethod
    async def interrupt(self) -> bool:
        """Send interrupt signal (Ctrl+C).

        Returns:
            True if interrupt was successful

        Example:
            >>> success = await adapter.interrupt()
        """

    @abstractmethod
    def is_ready(self) -> bool:
        """Check if adapter is ready for input.

        Returns:
            True if adapter is in IDLE state

        Example:
            >>> if adapter.is_ready():
            ...     await adapter.send("Next task")
        """

    @abstractmethod
    async def stream_response(self) -> AsyncIterator[str]:
        """Stream response chunks as they arrive.

        Yields:
            Response chunks as they become available

        Example:
            >>> async for chunk in adapter.stream_response():
            ...     print(chunk, end='')
        """


class ClaudeCodeCommunicationAdapter(BaseCommunicationAdapter):
    """Communication adapter for Claude Code CLI.

    This adapter manages async I/O with Claude Code via TmuxOrchestrator,
    using ClaudeCodeAdapter (RuntimeAdapter) for output parsing.

    Attributes:
        orchestrator: TmuxOrchestrator for tmux operations
        pane_target: Tmux pane target (e.g., "%0")
        poll_interval: Polling interval for output capture (seconds)

    Example:
        >>> orchestrator = TmuxOrchestrator()
        >>> adapter = ClaudeCodeCommunicationAdapter(orchestrator, "%0")
        >>> await adapter.send("Create a new Python file")
        >>> response = await adapter.receive()
        >>> print(response.files_modified)
        ['new_file.py']
    """

    def __init__(
        self,
        orchestrator: TmuxOrchestrator,
        pane_target: str,
        runtime_adapter: RuntimeAdapter,
        poll_interval: float = 0.2,
    ):
        """Initialize the communication adapter.

        Args:
            orchestrator: TmuxOrchestrator for tmux operations
            pane_target: Tmux pane target (e.g., "%0")
            runtime_adapter: RuntimeAdapter for parsing output
            poll_interval: Polling interval for output capture (seconds)
        """
        self.orchestrator = orchestrator
        self.pane_target = pane_target
        self.runtime_adapter = runtime_adapter
        self.poll_interval = poll_interval
        self._state = AdapterState.IDLE
        self._last_output = ""
        self._output_buffer = ""

    async def send(self, message: str) -> None:
        """Send message to Claude Code.

        Args:
            message: The message to send

        Example:
            >>> await adapter.send("Fix the bug in main.py")
        """
        logger.debug(f"Sending message to {self.pane_target}: {message[:50]}...")
        self._state = AdapterState.PROCESSING
        self._output_buffer = ""

        # Format message using RuntimeAdapter
        formatted = self.runtime_adapter.format_input(message)

        # Send via tmux
        self.orchestrator.send_keys(self.pane_target, formatted, enter=True)

    async def receive(self, timeout: float = 30.0) -> AdapterResponse:
        """Wait for complete response from Claude Code.

        Args:
            timeout: Maximum time to wait for response

        Returns:
            AdapterResponse with parsed content and state

        Example:
            >>> response = await adapter.receive(timeout=60.0)
            >>> if response.is_complete:
            ...     print("Task complete!")
        """
        start = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start < timeout:
            # Capture output from tmux pane
            output = self.orchestrator.capture_output(self.pane_target, lines=100)

            # Get only new output
            new_output = self._get_new_output(output)
            if new_output:
                self._output_buffer += new_output

            # Parse response using RuntimeAdapter
            parsed = self.runtime_adapter.parse_response(output)

            # Check if error occurred (prioritize error state)
            if parsed.is_error:
                self._state = AdapterState.ERROR
                logger.warning(f"Error detected: {parsed.error_message}")
                return self._build_response(parsed, is_complete=True)

            # Check if waiting for user input (question)
            if parsed.is_question:
                self._state = AdapterState.WAITING
                logger.debug(f"Question detected: {parsed.question_text}")
                return self._build_response(parsed, is_complete=False)

            # Check if response is complete (idle state)
            if parsed.is_complete:
                self._state = AdapterState.IDLE
                logger.debug("Response complete (idle detected)")
                return self._build_response(parsed, is_complete=True)

            # Continue polling
            await asyncio.sleep(self.poll_interval)

        # Timeout - return partial response
        logger.warning(f"Timeout after {timeout}s")
        parsed = self.runtime_adapter.parse_response(self._output_buffer)
        return self._build_response(parsed, is_complete=False)

    async def interrupt(self) -> bool:
        """Send Ctrl+C to interrupt Claude Code.

        Returns:
            True if interrupt was successful

        Example:
            >>> success = await adapter.interrupt()
            >>> if success:
            ...     print("Interrupted successfully")
        """
        try:
            logger.info(f"Sending interrupt to {self.pane_target}")
            self.orchestrator.send_keys(self.pane_target, "C-c", enter=False)
            self._state = AdapterState.IDLE
            return True
        except Exception as e:
            logger.error(f"Failed to interrupt: {e}")
            return False

    def is_ready(self) -> bool:
        """Check if adapter is ready for input.

        Returns:
            True if adapter is in IDLE state

        Example:
            >>> if adapter.is_ready():
            ...     await adapter.send("Next task")
        """
        return self._state == AdapterState.IDLE

    async def stream_response(self) -> AsyncIterator[str]:
        """Stream response chunks from Claude Code.

        Yields:
            Response chunks as they become available

        Example:
            >>> async for chunk in adapter.stream_response():
            ...     print(chunk, end='', flush=True)
        """
        last_len = 0

        while self._state == AdapterState.PROCESSING:
            # Capture current output
            output = self.orchestrator.capture_output(self.pane_target, lines=100)

            # Get new output since last check and add to buffer
            new_output = self._get_new_output(output)
            if new_output:
                self._output_buffer += new_output

            # Yield new chunk if buffer grew
            if len(self._output_buffer) > last_len:
                chunk = self._output_buffer[last_len:]
                last_len = len(self._output_buffer)
                yield chunk

            # Check if complete using RuntimeAdapter
            parsed = self.runtime_adapter.parse_response(output)
            if parsed.is_complete:
                self._state = AdapterState.IDLE
                logger.debug("Streaming complete (idle detected)")
                break

            await asyncio.sleep(self.poll_interval)

    def _get_new_output(self, current: str) -> str:
        """Get only new output since last capture.

        Args:
            current: Current output from tmux pane

        Returns:
            New output that hasn't been seen before
        """
        if current == self._last_output:
            return ""

        # Find where new content starts
        if self._last_output and current.startswith(self._last_output):
            new = current[len(self._last_output) :]
        else:
            new = current

        self._last_output = current
        return new

    def _build_response(
        self,
        parsed: "ParsedResponse",
        is_complete: bool,
    ) -> AdapterResponse:
        """Build AdapterResponse from ParsedResponse.

        Args:
            parsed: ParsedResponse from RuntimeAdapter
            is_complete: Whether response is complete

        Returns:
            AdapterResponse with metadata
        """
        # TODO: Extract tool uses and files modified from content
        # This would require additional parsing patterns in RuntimeAdapter
        # For now, return basic response

        return AdapterResponse(
            content=parsed.content,
            state=self._state,
            tool_uses=None,  # Future: extract from content
            files_modified=None,  # Future: extract from content
            is_complete=is_complete,
        )
