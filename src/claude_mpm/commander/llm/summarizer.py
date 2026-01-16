"""Summarizes Claude Code output for user display."""

from .openrouter_client import OpenRouterClient


class OutputSummarizer:
    """Summarizes long output from Claude Code instances."""

    def __init__(self, client: OpenRouterClient):
        """Initialize with OpenRouter client.

        Args:
            client: OpenRouterClient instance for LLM requests.
        """
        self.client = client

    async def summarize(self, output: str, context: str | None = None) -> str:
        """Summarize Claude Code output.

        Args:
            output: Raw output from Claude Code.
            context: Optional context about what was requested.

        Returns:
            Concise summary of the output.
        """
        # Build summarization prompt
        if context:
            prompt = f"""Summarize the following Claude Code output.

Context: {context}

Output:
{output}

Provide a concise summary (2-3 sentences) that captures:
1. What action was taken
2. The key result or outcome
3. Any important warnings or next steps

Summary:"""
        else:
            prompt = f"""Summarize the following Claude Code output in 2-3 sentences.

Output:
{output}

Summary:"""

        messages = [{"role": "user", "content": prompt}]

        system = (
            "You are a technical summarization assistant. "
            "Provide clear, concise summaries of command output and code execution results. "
            "Focus on actionable information and key outcomes."
        )

        return await self.client.chat(messages, system=system)

    def needs_summarization(self, output: str, threshold: int = 500) -> bool:
        """Check if output is long enough to warrant summarization.

        Args:
            output: Output text to check.
            threshold: Character count threshold for summarization.

        Returns:
            True if output exceeds threshold, False otherwise.
        """
        return len(output) > threshold
