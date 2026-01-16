"""Base runtime adapter interface for MPM Commander.

This module defines the abstract interface for runtime adapters that bridge
between the TmuxOrchestrator and various AI coding tools (Claude Code, Cursor, etc.).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Set


class Capability(Enum):
    """Capabilities that a runtime adapter can provide."""

    TOOL_USE = "tool_use"
    FILE_EDIT = "file_edit"
    FILE_CREATE = "file_create"
    GIT_OPERATIONS = "git_operations"
    SHELL_COMMANDS = "shell_commands"
    WEB_SEARCH = "web_search"
    COMPLEX_REASONING = "complex_reasoning"


@dataclass
class ParsedResponse:
    """Parsed output from a runtime tool.

    Attributes:
        content: The extracted text content, with ANSI codes removed
        is_complete: True if tool is waiting for input (idle state)
        is_error: True if an error was detected in the output
        error_message: The error message if is_error is True
        is_question: True if tool is asking a question
        question_text: The question text if is_question is True
        options: List of options if presenting a choice

    Example:
        >>> response = ParsedResponse(
        ...     content="File created successfully",
        ...     is_complete=True,
        ...     is_error=False,
        ...     error_message=None,
        ...     is_question=False,
        ...     question_text=None,
        ...     options=None
        ... )
    """

    content: str
    is_complete: bool
    is_error: bool
    error_message: Optional[str] = None
    is_question: bool = False
    question_text: Optional[str] = None
    options: Optional[List[str]] = None


class RuntimeAdapter(ABC):
    """Abstract base class for runtime adapters.

    A runtime adapter provides the interface between the TmuxOrchestrator
    and a specific AI coding tool. It handles:
    - Launching the tool with appropriate settings
    - Formatting input messages
    - Detecting tool states (idle, error, questioning)
    - Parsing tool output into structured responses

    Example:
        >>> class MyAdapter(RuntimeAdapter):
        ...     @property
        ...     def name(self) -> str:
        ...         return "my-tool"
        ...
        ...     def build_launch_command(self, project_path: str) -> str:
        ...         return f"cd {project_path} && my-tool --interactive"
    """

    @abstractmethod
    def build_launch_command(
        self, project_path: str, agent_prompt: Optional[str] = None
    ) -> str:
        """Generate shell command to start the tool.

        Args:
            project_path: Absolute path to the project directory
            agent_prompt: Optional system prompt to configure the agent

        Returns:
            Shell command string ready to execute

        Example:
            >>> adapter.build_launch_command("/home/user/project", "You are a Python expert")
            'cd /home/user/project && claude --system-prompt "You are a Python expert"'
        """

    @abstractmethod
    def format_input(self, message: str) -> str:
        """Prepare message for tool's input format.

        Args:
            message: The user message to send

        Returns:
            Formatted message ready to send to the tool

        Example:
            >>> adapter.format_input("Fix the bug in main.py")
            'Fix the bug in main.py'
        """

    @abstractmethod
    def detect_idle(self, output: str) -> bool:
        """Recognize when tool is waiting for input.

        Args:
            output: Raw output from the tool (may contain ANSI codes)

        Returns:
            True if the tool is in an idle state awaiting input

        Example:
            >>> adapter.detect_idle("Done editing file.\\n> ")
            True
            >>> adapter.detect_idle("Processing request...")
            False
        """

    @abstractmethod
    def detect_error(self, output: str) -> Optional[str]:
        """Recognize error states, return error message if found.

        Args:
            output: Raw output from the tool

        Returns:
            Error message string if error detected, None otherwise

        Example:
            >>> adapter.detect_error("Error: File not found: config.py")
            'Error: File not found: config.py'
            >>> adapter.detect_error("File edited successfully")
            None
        """

    @abstractmethod
    def parse_response(self, output: str) -> ParsedResponse:
        """Extract meaningful content from output.

        This method combines all detection logic (idle, error, questions)
        into a single structured response.

        Args:
            output: Raw output from the tool

        Returns:
            ParsedResponse with all detected states and content

        Example:
            >>> response = adapter.parse_response("Error: Invalid input\\n> ")
            >>> response.is_error
            True
            >>> response.is_complete
            True
        """

    @property
    @abstractmethod
    def capabilities(self) -> Set[Capability]:
        """What this tool can do.

        Returns:
            Set of Capability enums indicating supported features

        Example:
            >>> adapter.capabilities
            {Capability.FILE_EDIT, Capability.TOOL_USE}
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Runtime identifier.

        Returns:
            Unique name for this runtime adapter

        Example:
            >>> adapter.name
            'claude-code'
        """
