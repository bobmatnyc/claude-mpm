"""MPM (Multi-agent Project Manager) runtime adapter.

This module implements the RuntimeAdapter interface for MPM,
providing full support for agent delegation, hooks, skills, and monitoring.
"""

import json
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


class MPMAdapter(RuntimeAdapter):
    """Adapter for MPM (Multi-agent Project Manager).

    MPM extends Claude Code with multi-agent orchestration, lifecycle hooks,
    skills, real-time monitoring, and advanced project management capabilities.

    Features:
        - Agent delegation and sub-agent spawning
        - Lifecycle hooks (pre/post task, pre/post commit, etc.)
        - Loadable skills for specialized tasks
        - Real-time monitoring dashboard
        - Custom instructions via CLAUDE.md
        - MCP server integration
        - Git workflow automation

    Example:
        >>> adapter = MPMAdapter()
        >>> cmd = adapter.build_launch_command("/home/user/project")
        >>> # Inject agent context
        >>> ctx_cmd = adapter.inject_agent_context("eng-001", {"role": "Engineer"})
        >>> # Check capabilities
        >>> info = adapter.runtime_info
        >>> if RuntimeCapability.AGENT_DELEGATION in info.capabilities:
        ...     print("Supports agent delegation")
    """

    # Idle detection patterns (inherits from Claude Code)
    IDLE_PATTERNS = [
        r"^>\s*$",  # Simple prompt
        r"claude>\s*$",  # Named prompt
        r"╭─+╮",  # Box drawing
        r"What would you like",
        r"How can I help",
    ]

    # MPM-specific patterns
    MPM_PATTERNS = [
        r"\[MPM\]",  # MPM prefix
        r"Agent spawned:",
        r"Delegating to agent:",
        r"Hook triggered:",
        r"Skill loaded:",
    ]

    # Error patterns
    ERROR_PATTERNS = [
        r"Error:",
        r"Failed:",
        r"Exception:",
        r"Permission denied",
        r"not found",
        r"Traceback \(most recent call last\)",
        r"FATAL:",
        r"✗",
        r"command not found",
        r"cannot access",
        r"Agent error:",
        r"Hook failed:",
    ]

    # Question patterns
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
        r"Delegate to which agent",
    ]

    # ANSI escape code pattern
    ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    @property
    def name(self) -> str:
        """Return the runtime identifier."""
        return "mpm"

    @property
    def capabilities(self) -> Set[Capability]:
        """Return the set of capabilities supported by MPM."""
        return {
            Capability.TOOL_USE,
            Capability.FILE_EDIT,
            Capability.FILE_CREATE,
            Capability.GIT_OPERATIONS,
            Capability.SHELL_COMMANDS,
            Capability.WEB_SEARCH,
            Capability.COMPLEX_REASONING,
        }

    @property
    def runtime_info(self) -> RuntimeInfo:
        """Return detailed runtime information.

        MPM has the most comprehensive capabilities of all runtimes.
        """
        return RuntimeInfo(
            name="mpm",
            version=None,  # Could parse from mpm --version
            capabilities={
                RuntimeCapability.FILE_READ,
                RuntimeCapability.FILE_EDIT,
                RuntimeCapability.FILE_CREATE,
                RuntimeCapability.BASH_EXECUTION,
                RuntimeCapability.GIT_OPERATIONS,
                RuntimeCapability.TOOL_USE,
                RuntimeCapability.AGENT_DELEGATION,  # Key MPM feature
                RuntimeCapability.HOOKS,  # Lifecycle hooks
                RuntimeCapability.INSTRUCTIONS,  # CLAUDE.md
                RuntimeCapability.MCP_TOOLS,  # MCP integration
                RuntimeCapability.SKILLS,  # Loadable skills
                RuntimeCapability.MONITOR,  # Real-time monitoring
                RuntimeCapability.WEB_SEARCH,
                RuntimeCapability.COMPLEX_REASONING,
            },
            command="claude",  # MPM uses claude CLI with MPM config
            supports_agents=True,  # Full agent support
            instruction_file="CLAUDE.md",
        )

    def build_launch_command(
        self, project_path: str, agent_prompt: Optional[str] = None
    ) -> str:
        """Generate shell command to start MPM.

        Args:
            project_path: Absolute path to the project directory
            agent_prompt: Optional system prompt to configure agent

        Returns:
            Shell command string ready to execute

        Example:
            >>> adapter = MPMAdapter()
            >>> adapter.build_launch_command("/home/user/project")
            "cd '/home/user/project' && claude --dangerously-skip-permissions"
        """
        quoted_path = shlex.quote(project_path)
        cmd = f"cd {quoted_path} && claude"

        if agent_prompt:
            quoted_prompt = shlex.quote(agent_prompt)
            cmd += f" --system-prompt {quoted_prompt}"

        # Skip permissions for automated operation
        cmd += " --dangerously-skip-permissions"

        logger.debug(f"Built MPM launch command: {cmd}")
        return cmd

    def format_input(self, message: str) -> str:
        """Prepare message for MPM's input format."""
        formatted = message.strip()
        logger.debug(f"Formatted input: {formatted[:100]}...")
        return formatted

    def strip_ansi(self, text: str) -> str:
        """Remove ANSI escape codes from text."""
        return self.ANSI_ESCAPE.sub("", text)

    def detect_idle(self, output: str) -> bool:
        """Recognize when MPM is waiting for input."""
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
        """Detect if MPM is asking a question."""
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
        """Extract meaningful content from MPM output."""
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

    def inject_instructions(self, instructions: str) -> Optional[str]:
        """Return command to inject custom instructions.

        MPM uses CLAUDE.md for custom instructions.

        Args:
            instructions: Instructions text to inject

        Returns:
            Command to write CLAUDE.md file

        Example:
            >>> adapter = MPMAdapter()
            >>> cmd = adapter.inject_instructions("You are a Python expert")
            >>> print(cmd)
            echo '...' > CLAUDE.md
        """
        # Write to CLAUDE.md
        escaped = instructions.replace("'", "'\\''")
        return f"echo '{escaped}' > CLAUDE.md"

    def inject_agent_context(self, agent_id: str, context: dict) -> Optional[str]:
        """Return command to inject agent context.

        MPM supports agent context injection via special command.

        Args:
            agent_id: Unique identifier for agent
            context: Context dictionary with agent metadata

        Returns:
            Command to inject agent context

        Example:
            >>> adapter = MPMAdapter()
            >>> cmd = adapter.inject_agent_context("eng-001", {"role": "Engineer"})
            >>> # Command would set MPM_AGENT_ID and MPM_AGENT_CONTEXT env vars
        """
        # Serialize context to JSON
        context_json = json.dumps(context)
        escaped_json = context_json.replace("'", "'\\''")

        # Set environment variables for MPM agent context
        # MPM runtime can read these to understand agent identity
        cmd = f"export MPM_AGENT_ID='{agent_id}' && export MPM_AGENT_CONTEXT='{escaped_json}'"

        logger.debug(f"Built agent context injection command for {agent_id}")
        return cmd

    def detect_agent_spawn(self, output: str) -> Optional[dict]:
        """Detect if MPM has spawned a new agent.

        Args:
            output: Raw output from MPM

        Returns:
            Dict with agent info if spawn detected, None otherwise

        Example:
            >>> adapter = MPMAdapter()
            >>> info = adapter.detect_agent_spawn("[MPM] Agent spawned: eng-001 (Engineer)")
            >>> if info:
            ...     print(info['agent_id'])
            'eng-001'
        """
        clean = self.strip_ansi(output)

        # Pattern: [MPM] Agent spawned: <agent_id> (<role>)
        match = re.search(r"\[MPM\] Agent spawned: (\S+) \(([^)]+)\)", clean)
        if match:
            agent_id = match.group(1)
            role = match.group(2)

            logger.info(f"Detected agent spawn: {agent_id} ({role})")
            return {"agent_id": agent_id, "role": role}

        return None

    def detect_hook_trigger(self, output: str) -> Optional[dict]:
        """Detect if a lifecycle hook was triggered.

        Args:
            output: Raw output from MPM

        Returns:
            Dict with hook info if trigger detected, None otherwise

        Example:
            >>> adapter = MPMAdapter()
            >>> info = adapter.detect_hook_trigger("[MPM] Hook triggered: pre-commit")
            >>> if info:
            ...     print(info['hook_name'])
            'pre-commit'
        """
        clean = self.strip_ansi(output)

        # Pattern: [MPM] Hook triggered: <hook_name>
        match = re.search(r"\[MPM\] Hook triggered: (\S+)", clean)
        if match:
            hook_name = match.group(1)

            logger.info(f"Detected hook trigger: {hook_name}")
            return {"hook_name": hook_name}

        return None
