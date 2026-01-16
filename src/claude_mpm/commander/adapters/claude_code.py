"""Claude Code CLI runtime adapter.

This module implements the RuntimeAdapter interface for the Claude Code CLI tool.
It handles launching Claude Code, detecting its various states, and parsing its output.
"""

import logging
import re
import shlex
from typing import List, Optional, Set

from .base import Capability, ParsedResponse, RuntimeAdapter

logger = logging.getLogger(__name__)


class ClaudeCodeAdapter(RuntimeAdapter):
    """Adapter for Claude Code CLI.

    This adapter provides integration with the Claude Code command-line interface,
    handling its unique prompt formats, error messages, and interactive behaviors.

    Example:
        >>> adapter = ClaudeCodeAdapter()
        >>> cmd = adapter.build_launch_command("/home/user/project")
        >>> print(cmd)
        cd '/home/user/project' && claude --dangerously-skip-permissions
    """

    # Idle detection patterns (Claude Code prompt indicators)
    IDLE_PATTERNS = [
        r"^>\s*$",  # Simple prompt
        r"claude>\s*$",  # Named prompt
        r"╭─+╮",  # Box drawing (Claude's UI)
        r"What would you like",  # Claude asking for input
        r"How can I help",  # Alternative greeting
    ]

    # Error patterns - detect various error conditions
    ERROR_PATTERNS = [
        r"Error:",
        r"Failed:",
        r"Exception:",
        r"Permission denied",
        r"not found",
        r"Traceback \(most recent call last\)",
        r"FATAL:",
        r"✗",  # Claude's error indicator
        r"command not found",
        r"cannot access",
    ]

    # Question patterns - detect when Claude is asking for confirmation
    QUESTION_PATTERNS = [
        r"Which option",
        r"Should I proceed",
        r"Please choose",
        r"\(y/n\)\?",
        r"Are you sure",
        r"Do you want",
        r"\[Y/n\]",
        r"\[yes/no\]",
        r"Select an option",
        r"Choose from",
    ]

    # ANSI escape code pattern for stripping color/formatting codes
    ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    @property
    def name(self) -> str:
        """Return the runtime identifier.

        Returns:
            The string "claude-code"
        """
        return "claude-code"

    @property
    def capabilities(self) -> Set[Capability]:
        """Return the set of capabilities supported by Claude Code.

        Claude Code is a full-featured AI coding assistant with comprehensive
        tool use, file operations, git integration, and reasoning capabilities.

        Returns:
            Set of all supported Capability enums
        """
        return {
            Capability.TOOL_USE,
            Capability.FILE_EDIT,
            Capability.FILE_CREATE,
            Capability.GIT_OPERATIONS,
            Capability.SHELL_COMMANDS,
            Capability.WEB_SEARCH,
            Capability.COMPLEX_REASONING,
        }

    def build_launch_command(
        self, project_path: str, agent_prompt: Optional[str] = None
    ) -> str:
        """Generate shell command to start Claude Code.

        Args:
            project_path: Absolute path to the project directory
            agent_prompt: Optional system prompt to configure Claude's behavior

        Returns:
            Shell command string ready to execute in bash

        Example:
            >>> adapter = ClaudeCodeAdapter()
            >>> adapter.build_launch_command("/home/user/project")
            "cd '/home/user/project' && claude --dangerously-skip-permissions"
            >>> adapter.build_launch_command("/home/user/project", "You are a Python expert")
            "cd '/home/user/project' && claude --system-prompt 'You are a Python expert' --dangerously-skip-permissions"

        Note:
            Uses --dangerously-skip-permissions for automated operation.
            This is appropriate for MPM Commander's controlled environment.
        """
        # shlex.quote prevents shell injection
        quoted_path = shlex.quote(project_path)  # nosec B604
        cmd = f"cd {quoted_path} && claude"

        if agent_prompt:
            quoted_prompt = shlex.quote(agent_prompt)  # nosec B604
            cmd += f" --system-prompt {quoted_prompt}"

        # Skip permissions for automated operation
        cmd += " --dangerously-skip-permissions"

        logger.debug(f"Built launch command: {cmd}")
        return cmd

    def format_input(self, message: str) -> str:
        """Prepare message for Claude Code's input format.

        Claude Code accepts plain text input, so this method simply
        strips leading/trailing whitespace.

        Args:
            message: The user message to send

        Returns:
            Formatted message (whitespace-trimmed)

        Example:
            >>> adapter = ClaudeCodeAdapter()
            >>> adapter.format_input("  Fix the bug in main.py  ")
            'Fix the bug in main.py'
        """
        formatted = message.strip()
        logger.debug(f"Formatted input: {formatted[:100]}...")
        return formatted

    def strip_ansi(self, text: str) -> str:
        """Remove ANSI escape codes from text.

        Args:
            text: Text potentially containing ANSI escape sequences

        Returns:
            Clean text with ANSI codes removed

        Example:
            >>> adapter = ClaudeCodeAdapter()
            >>> adapter.strip_ansi("\\x1b[32mSuccess\\x1b[0m")
            'Success'
        """
        return self.ANSI_ESCAPE.sub("", text)

    def detect_idle(self, output: str) -> bool:
        """Recognize when Claude Code is waiting for input.

        Checks the last line of output against known idle patterns
        such as the prompt indicator or greeting messages.

        Args:
            output: Raw output from Claude Code (may contain ANSI codes)

        Returns:
            True if Claude is in an idle state awaiting input

        Example:
            >>> adapter = ClaudeCodeAdapter()
            >>> adapter.detect_idle("Done editing file.\\n> ")
            True
            >>> adapter.detect_idle("Processing request...")
            False
            >>> adapter.detect_idle("╭─────────────────╮\\nWhat would you like me to help with?")
            True
        """
        if not output:
            return False

        clean = self.strip_ansi(output)
        lines = clean.strip().split("\n")

        if not lines:
            return False

        last_line = lines[-1].strip()

        # Check against all idle patterns
        for pattern in self.IDLE_PATTERNS:
            if re.search(pattern, last_line):
                logger.debug(f"Detected idle state with pattern: {pattern}")
                return True

        return False

    def detect_error(self, output: str) -> Optional[str]:
        """Recognize error states and extract error message.

        Searches the output for known error patterns and returns
        the line containing the error for context.

        Args:
            output: Raw output from Claude Code

        Returns:
            Error message string if error detected, None otherwise

        Example:
            >>> adapter = ClaudeCodeAdapter()
            >>> adapter.detect_error("Error: File not found: config.py")
            'Error: File not found: config.py'
            >>> adapter.detect_error("File edited successfully")
            None
            >>> adapter.detect_error("Traceback (most recent call last):\\n  File...")
            'Traceback (most recent call last):'
        """
        clean = self.strip_ansi(output)

        for pattern in self.ERROR_PATTERNS:
            match = re.search(pattern, clean, re.IGNORECASE)
            if match:
                # Extract the line containing the error for context
                for line in clean.split("\n"):
                    if re.search(pattern, line, re.IGNORECASE):
                        error_msg = line.strip()
                        logger.warning(f"Detected error: {error_msg}")
                        return error_msg

        return None

    def detect_question(
        self, output: str
    ) -> tuple[bool, Optional[str], Optional[List[str]]]:
        """Detect if Claude is asking a question and extract options.

        Searches for question patterns and attempts to extract the question
        text along with any numbered options presented.

        Args:
            output: Raw output from Claude Code

        Returns:
            Tuple of (is_question, question_text, options)
            - is_question: True if a question was detected
            - question_text: The question text if found
            - options: List of option strings if numbered options found

        Example:
            >>> adapter = ClaudeCodeAdapter()
            >>> is_q, text, opts = adapter.detect_question("Should I proceed? (y/n)?")
            >>> is_q
            True
            >>> text
            'Should I proceed? (y/n)?'
            >>> is_q, text, opts = adapter.detect_question(
            ...     "Which option:\\n1. Create new file\\n2. Edit existing"
            ... )
            >>> opts
            ['Create new file', 'Edit existing']
        """
        clean = self.strip_ansi(output)

        for pattern in self.QUESTION_PATTERNS:
            if re.search(pattern, clean, re.IGNORECASE):
                # Try to extract question and options
                lines = clean.strip().split("\n")
                question = None
                options = []

                for line in lines:
                    if re.search(pattern, line, re.IGNORECASE):
                        question = line.strip()

                    # Look for numbered options (1., 2., 1), 2), etc.)
                    opt_match = re.match(r"^\s*(\d+)[.):]\s*(.+)$", line)
                    if opt_match:
                        options.append(opt_match.group(2).strip())

                logger.debug(
                    f"Detected question: {question}, options: {options if options else 'none'}"
                )
                return True, question, options if options else None

        return False, None, None

    def parse_response(self, output: str) -> ParsedResponse:
        """Extract meaningful content from Claude Code output.

        Combines all detection logic (idle, error, questions) into a
        single structured response object.

        Args:
            output: Raw output from Claude Code

        Returns:
            ParsedResponse with all detected states and content

        Example:
            >>> adapter = ClaudeCodeAdapter()
            >>> response = adapter.parse_response("Error: Invalid input\\n> ")
            >>> response.is_error
            True
            >>> response.is_complete
            True
            >>> response.error_message
            'Error: Invalid input'

            >>> response = adapter.parse_response("File created: test.py\\n> ")
            >>> response.content
            'File created: test.py\\n> '
            >>> response.is_complete
            True
            >>> response.is_error
            False
        """
        if not output:
            return ParsedResponse(
                content="",
                is_complete=False,
                is_error=False,
                is_question=False,
            )

        clean = self.strip_ansi(output)
        error_msg = self.detect_error(output)
        is_question, question_text, options = self.detect_question(output)
        is_complete = self.detect_idle(output)

        response = ParsedResponse(
            content=clean,
            is_complete=is_complete,
            is_error=error_msg is not None,
            error_message=error_msg,
            is_question=is_question,
            question_text=question_text,
            options=options,
        )

        logger.debug(
            f"Parsed response: complete={is_complete}, error={error_msg is not None}, "
            f"question={is_question}"
        )

        return response
