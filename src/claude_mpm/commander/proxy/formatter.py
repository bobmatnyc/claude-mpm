"""Formats output for Commander chat display."""

from .output_handler import OutputChunk


class OutputFormatter:
    """Formats Claude Code output for user display."""

    def __init__(self, max_raw_display: int = 500):
        """Initialize OutputFormatter.

        Args:
            max_raw_display: Maximum characters of raw output to display.
        """
        self.max_raw_display = max_raw_display

    def format_summary(self, chunk: OutputChunk) -> str:
        """Format a summarized output chunk for display.

        Args:
            chunk: OutputChunk with summary.

        Returns:
            Formatted output with summary and optionally truncated raw output.
        """
        lines = []

        # Instance header
        status = "✓" if chunk.is_complete else "⋯"
        lines.append(f"[{chunk.instance_name}] {status}")

        # Summary if available
        if chunk.summary:
            lines.append(f"\n📝 Summary: {chunk.summary}")

        # Show truncated raw output if it's short enough
        if len(chunk.raw_output) <= self.max_raw_display:
            lines.append(f"\n```\n{chunk.raw_output}\n```")
        else:
            # Show truncated preview
            preview = chunk.raw_output[: self.max_raw_display]
            lines.append(
                f"\n```\n{preview}...\n(truncated, {len(chunk.raw_output)} chars total)\n```"
            )

        return "".join(lines)

    def format_raw(self, chunk: OutputChunk, truncate: bool = True) -> str:
        """Format raw output, optionally truncated.

        Args:
            chunk: OutputChunk to format.
            truncate: Whether to truncate long output.

        Returns:
            Formatted raw output.
        """
        status = "✓" if chunk.is_complete else "⋯"
        header = f"[{chunk.instance_name}] {status}"

        raw = chunk.raw_output
        if truncate and len(raw) > self.max_raw_display:
            raw = raw[: self.max_raw_display] + "...\n(truncated)"

        return f"{header}\n```\n{raw}\n```"

    def format_status(self, instance_name: str, status: str) -> str:
        """Format a status message.

        Args:
            instance_name: Name of the instance.
            status: Status message.

        Returns:
            Formatted status message.
        """
        return f"[{instance_name}] ℹ️  {status}"

    def format_error(self, instance_name: str, error: str) -> str:
        """Format an error message.

        Args:
            instance_name: Name of the instance.
            error: Error message.

        Returns:
            Formatted error message.
        """
        return f"[{instance_name}] ❌ Error: {error}"
