"""Handles output from Claude Code instances."""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime

from claude_mpm.commander.llm.summarizer import OutputSummarizer
from claude_mpm.commander.tmux_orchestrator import TmuxOrchestrator

logger = logging.getLogger(__name__)


@dataclass
class OutputChunk:
    """Represents a chunk of output from an instance."""

    instance_name: str
    raw_output: str
    summary: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    is_complete: bool = False


class OutputHandler:
    """Captures and summarizes output from Claude Code instances."""

    # Patterns that indicate Claude Code has finished responding
    COMPLETION_PATTERNS = [
        "> ",  # Default prompt
        "$ ",  # Shell prompt
        "\n> ",  # Prompt on new line
    ]

    def __init__(
        self,
        orchestrator: TmuxOrchestrator,
        summarizer: OutputSummarizer | None = None,
    ):
        """Initialize OutputHandler.

        Args:
            orchestrator: TmuxOrchestrator for capturing output from panes.
            summarizer: Optional OutputSummarizer for long output.
        """
        self.orchestrator = orchestrator
        self.summarizer = summarizer
        self._output_buffers: dict[str, str] = {}
        self._last_output_hash: dict[str, str] = {}

    async def capture_output(self, pane_target: str, lines: int = 100) -> str:
        """Capture raw output from a pane.

        Args:
            pane_target: Tmux pane target.
            lines: Number of lines to capture from history.

        Returns:
            Captured output as string.
        """
        logger.debug(f"Capturing {lines} lines from pane {pane_target}")
        return self.orchestrator.capture_output(pane_target, lines=lines)

    def _hash_output(self, output: str) -> str:
        """Generate hash of output for change detection.

        Args:
            output: Output text to hash.

        Returns:
            MD5 hash of the output.
        """
        # MD5 is sufficient for non-security change detection
        return hashlib.md5(output.encode(), usedforsecurity=False).hexdigest()  # nosec B324

    async def get_new_output(self, instance_name: str, pane_target: str) -> str | None:
        """Get only new output since last capture (diff-based).

        Args:
            instance_name: Name of the instance.
            pane_target: Tmux pane target.

        Returns:
            New output since last capture, or None if no change.
        """
        current_output = await self.capture_output(pane_target)
        current_hash = self._hash_output(current_output)

        # Check if output has changed
        last_hash = self._last_output_hash.get(instance_name)
        if last_hash == current_hash:
            logger.debug(f"No new output for {instance_name}")
            return None

        # Update hash
        self._last_output_hash[instance_name] = current_hash

        # For first capture, return full output
        if last_hash is None:
            logger.debug(f"First capture for {instance_name}")
            return current_output

        # Extract new lines by comparing with buffered output
        last_output = self._output_buffers.get(instance_name, "")

        # Simple diff: if current output contains last output as prefix,
        # return the difference
        if current_output.startswith(last_output):
            new_output = current_output[len(last_output) :]
            logger.debug(f"New output for {instance_name}: {len(new_output)} chars")
            return new_output

        # If not a simple append, return full current output
        # (pane may have been cleared or output wrapped)
        logger.debug(f"Output changed significantly for {instance_name}")
        return current_output

    async def process_output(
        self, instance_name: str, pane_target: str, context: str | None = None
    ) -> OutputChunk | None:
        """Capture new output and optionally summarize.

        Args:
            instance_name: Name of the instance.
            pane_target: Tmux pane target.
            context: Optional context (e.g., what command was sent).

        Returns:
            OutputChunk with raw and summarized output, or None if no new output.
        """
        # Get new output
        new_output = await self.get_new_output(instance_name, pane_target)
        if new_output is None:
            return None

        # Update buffer with full current output
        current_output = await self.capture_output(pane_target)
        self._output_buffers[instance_name] = current_output

        # Create chunk
        chunk = OutputChunk(
            instance_name=instance_name,
            raw_output=new_output,
            is_complete=self.detect_completion(new_output),
        )

        # Summarize if needed and summarizer is available
        if self.summarizer and self.summarizer.needs_summarization(new_output):
            try:
                logger.debug(f"Summarizing output for {instance_name}")
                chunk.summary = await self.summarizer.summarize(new_output, context)
            except Exception as e:
                logger.error(f"Failed to summarize output: {e}")
                # Continue without summary

        return chunk

    def detect_completion(self, output: str) -> bool:
        """Detect if Claude Code has finished responding (prompt returned).

        Args:
            output: Output text to check.

        Returns:
            True if output ends with a completion pattern.
        """
        if not output:
            return False

        # Strip only trailing newlines/tabs/carriage returns, keep spaces
        output_check = output.rstrip("\n\t\r")

        for pattern in self.COMPLETION_PATTERNS:
            # Check if output ends with the exact pattern
            if output_check.endswith(pattern):
                return True

            # Special handling for trailing whitespace:
            # If pattern has trailing space and output has extra trailing spaces,
            # still match (e.g., ">  " should match "> " pattern)
            if pattern.endswith(" "):
                pattern_base = pattern.rstrip(" ")
                # Check if after stripping spaces, we have pattern_base followed by at least one space
                output_stripped_spaces = output_check.rstrip(" ")
                # Check: output must end with pattern_base + at least one space
                if output_stripped_spaces.endswith(pattern_base) and len(
                    output_check
                ) > len(output_stripped_spaces):
                    return True

        return False
