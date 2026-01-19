"""Codex CLI runtime adapter.

This module implements the RuntimeAdapter interface for Codex,
an AI coding assistant (limited support currently).
"""

import logging
import re
import shlex
from typing import List, Optional, Set

from .base import (
    Capability,
    ParsedResponse,
    RuntimeAdapter,
    RuntimeCapability,
    RuntimeInfo,
)

logger = logging.getLogger(__name__)


class CodexAdapter(RuntimeAdapter):
    """Adapter for Codex CLI.

    Codex is an AI coding assistant. This adapter provides basic support,
    with limited capabilities compared to Claude Code or MPM.

    Note:
        Agent delegation and advanced features not yet supported.

    Example:
        >>> adapter = CodexAdapter()
        >>> cmd = adapter.build_launch_command("/home/user/project")
        >>> print(cmd)
        cd '/home/user/project' && codex
    """

    # Idle detection patterns
    IDLE_PATTERNS = [
        r"^>\s*$",  # Simple prompt
        r"codex>\s*$",  # Named prompt
        r"Ready",
        r"Waiting for input",
    ]

    # Error patterns
    ERROR_PATTERNS = [
        r"Error:",
        r"Failed:",
        r"Exception:",
        r"Permission denied",
        r"not found",
        r"Traceback",
        r"FATAL:",
    ]

    # Question patterns
    QUESTION_PATTERNS = [
        r"Which option",
        r"Should I proceed",
        r"Please choose",
        r"\(y/n\)\?",
        r"Are you sure",
        r"\[Y/n\]",
    ]

    # ANSI escape code pattern
    ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    @property
    def name(self) -> str:
        """Return the runtime identifier."""
        return "codex"

    @property
    def capabilities(self) -> Set[Capability]:
        """Return the set of capabilities supported by Codex."""
        return {
            Capability.TOOL_USE,
            Capability.FILE_EDIT,
            Capability.FILE_CREATE,
            Capability.SHELL_COMMANDS,
            Capability.COMPLEX_REASONING,
        }

    @property
    def runtime_info(self) -> RuntimeInfo:
        """Return detailed runtime information."""
        return RuntimeInfo(
            name="codex",
            version=None,  # Version detection could be added
            capabilities={
                RuntimeCapability.FILE_READ,
                RuntimeCapability.FILE_EDIT,
                RuntimeCapability.FILE_CREATE,
                RuntimeCapability.BASH_EXECUTION,
                RuntimeCapability.TOOL_USE,
                RuntimeCapability.COMPLEX_REASONING,
            },
            command="codex",
            supports_agents=False,  # No agent support
            instruction_file=None,  # No custom instructions support
        )

    def build_launch_command(
        self, project_path: str, agent_prompt: Optional[str] = None
    ) -> str:
        """Generate shell command to start Codex.

        Args:
            project_path: Absolute path to the project directory
            agent_prompt: Optional system prompt (may not be supported)

        Returns:
            Shell command string ready to execute

        Example:
            >>> adapter = CodexAdapter()
            >>> adapter.build_launch_command("/home/user/project")
            "cd '/home/user/project' && codex"
        """
        quoted_path = shlex.quote(project_path)
        cmd = f"cd {quoted_path} && codex"

        # Note: Codex may not support custom prompts
        # Adjust based on actual Codex CLI capabilities
        if agent_prompt:
            logger.warning("Codex may not support custom prompts")

        logger.debug(f"Built Codex launch command: {cmd}")
        return cmd

    def format_input(self, message: str) -> str:
        """Prepare message for Codex's input format."""
        formatted = message.strip()
        logger.debug(f"Formatted input: {formatted[:100]}...")
        return formatted

    def strip_ansi(self, text: str) -> str:
        """Remove ANSI escape codes from text."""
        return self.ANSI_ESCAPE.sub("", text)

    def detect_idle(self, output: str) -> bool:
        """Recognize when Codex is waiting for input."""
        if not output:
            return False

        clean = self.strip_ansi(output)
        lines = clean.strip().split("\n")

        if not lines:
            return False

        last_line = lines[-1].strip()

        for pattern in self.IDLE_PATTERNS:
            if re.search(pattern, last_line):
                logger.debug(f"Detected idle state with pattern: {pattern}")
                return True

        return False

    def detect_error(self, output: str) -> Optional[str]:
        """Recognize error states and extract error message."""
        clean = self.strip_ansi(output)

        for pattern in self.ERROR_PATTERNS:
            match = re.search(pattern, clean, re.IGNORECASE)
            if match:
                for line in clean.split("\n"):
                    if re.search(pattern, line, re.IGNORECASE):
                        error_msg = line.strip()
                        logger.warning(f"Detected error: {error_msg}")
                        return error_msg

        return None

    def detect_question(
        self, output: str
    ) -> tuple[bool, Optional[str], Optional[List[str]]]:
        """Detect if Codex is asking a question."""
        clean = self.strip_ansi(output)

        for pattern in self.QUESTION_PATTERNS:
            if re.search(pattern, clean, re.IGNORECASE):
                lines = clean.strip().split("\n")
                question = None
                options = []

                for line in lines:
                    if re.search(pattern, line, re.IGNORECASE):
                        question = line.strip()

                    # Look for numbered options
                    opt_match = re.match(r"^\s*(\d+)[.):]\s*(.+)$", line)
                    if opt_match:
                        options.append(opt_match.group(2).strip())

                logger.debug(
                    f"Detected question: {question}, options: {options if options else 'none'}"
                )
                return True, question, options if options else None

        return False, None, None

    def parse_response(self, output: str) -> ParsedResponse:
        """Extract meaningful content from Codex output."""
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
