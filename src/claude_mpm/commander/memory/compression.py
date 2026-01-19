"""Context compression and conversation summarization.

Compresses long conversations into concise summaries for efficient context
loading when resuming sessions or searching past work.
"""

import logging
from typing import List, Optional

from ..llm.openrouter_client import OpenRouterClient
from .store import Conversation, ConversationMessage

logger = logging.getLogger(__name__)


class ContextCompressor:
    """Compress conversations into summaries for context loading.

    Uses cheap LLM (mistral-small) to generate summaries of conversations
    and compress multiple conversations into context strings.

    Attributes:
        client: OpenRouterClient for LLM requests
        summary_threshold: Minimum messages to trigger summarization
        max_context_tokens: Maximum tokens for compressed context

    Example:
        >>> compressor = ContextCompressor(client)
        >>> summary = await compressor.summarize(messages)
        >>> context = await compressor.compress_for_context(
        ...     conversations,
        ...     max_tokens=4000
        ... )
    """

    def __init__(
        self,
        client: OpenRouterClient,
        summary_threshold: int = 10,
        max_context_tokens: int = 4000,
    ):
        """Initialize context compressor.

        Args:
            client: OpenRouterClient for LLM requests
            summary_threshold: Minimum messages to summarize
            max_context_tokens: Maximum tokens for context string
        """
        self.client = client
        self.summary_threshold = summary_threshold
        self.max_context_tokens = max_context_tokens

        logger.info(
            "ContextCompressor initialized (threshold: %d msgs, max_tokens: %d)",
            summary_threshold,
            max_context_tokens,
        )

    async def summarize(
        self,
        messages: List[ConversationMessage],
        focus: Optional[str] = None,
    ) -> str:
        """Generate summary of conversation messages.

        Args:
            messages: List of messages to summarize
            focus: Optional focus area (e.g., "bug fixes", "API changes")

        Returns:
            Concise summary (2-4 sentences)

        Example:
            >>> summary = await compressor.summarize(messages)
            >>> print(summary)
            "Fixed login authentication bug in src/auth.py by updating token validation..."
        """
        if len(messages) < 2:
            # Too short to summarize
            return messages[0].content if messages else ""

        # Build conversation text
        conversation_text = self._format_messages(messages)

        # Build summarization prompt
        if focus:
            prompt = f"""Summarize the following conversation, focusing on: {focus}

Conversation:
{conversation_text}

Provide a concise summary (2-4 sentences) that captures:
1. What was the main task or problem
2. What actions were taken
3. What was the outcome or current status
4. Any important files, functions, or errors mentioned

Summary:"""
        else:
            prompt = f"""Summarize the following conversation in 2-4 sentences.

Conversation:
{conversation_text}

Focus on:
1. What was the main task or problem
2. What actions were taken
3. What was the outcome or current status

Summary:"""

        messages_for_llm = [{"role": "user", "content": prompt}]

        system = (
            "You are a technical summarization assistant. "
            "Provide clear, concise summaries of development conversations. "
            "Focus on actionable information and key outcomes."
        )

        summary = await self.client.chat(messages_for_llm, system=system)
        logger.debug(
            "Generated summary (%d chars) from %d messages", len(summary), len(messages)
        )

        return summary.strip()

    async def compress_for_context(
        self,
        conversations: List[Conversation],
        max_tokens: Optional[int] = None,
        prioritize_recent: bool = True,
    ) -> str:
        """Compress multiple conversations into context string.

        Prioritizes recent conversations and uses summaries for older ones
        to fit within token budget.

        Args:
            conversations: List of conversations to compress
            max_tokens: Maximum tokens (default: self.max_context_tokens)
            prioritize_recent: Whether to prioritize recent conversations

        Returns:
            Compressed context string ready for LLM input

        Example:
            >>> context = await compressor.compress_for_context(
            ...     conversations,
            ...     max_tokens=4000
            ... )
            >>> print(f"Context: {len(context)} chars")
        """
        if max_tokens is None:
            max_tokens = self.max_context_tokens

        # Sort by recency if prioritizing
        if prioritize_recent:
            conversations = sorted(
                conversations, key=lambda c: c.updated_at, reverse=True
            )

        # Build context incrementally
        context_parts = []
        current_tokens = 0

        for conv in conversations:
            # Use summary if available, else generate one
            if conv.summary:
                summary_text = conv.summary
            elif len(conv.messages) >= self.summary_threshold:
                # Generate summary on-the-fly
                summary_text = await self.summarize(conv.messages)
            else:
                # Use full conversation for short ones
                summary_text = conv.get_full_text()

            # Format conversation section
            section = self._format_conversation_section(conv, summary_text)
            section_tokens = len(section) // 4  # Rough approximation

            # Check if adding this would exceed budget
            if current_tokens + section_tokens > max_tokens:
                # Try to fit summary only
                short_summary = summary_text.split(". ")[0] + "."
                short_section = self._format_conversation_section(conv, short_summary)
                short_tokens = len(short_section) // 4

                if current_tokens + short_tokens <= max_tokens:
                    context_parts.append(short_section)
                    current_tokens += short_tokens
                else:
                    # Can't fit any more, stop
                    break
            else:
                context_parts.append(section)
                current_tokens += section_tokens

        context = "\n\n---\n\n".join(context_parts)

        logger.info(
            "Compressed %d conversations into context (%d chars, ~%d tokens)",
            len(context_parts),
            len(context),
            current_tokens,
        )

        return context

    def needs_summarization(self, messages: List[ConversationMessage]) -> bool:
        """Check if conversation needs summarization.

        Args:
            messages: List of messages to check

        Returns:
            True if message count exceeds threshold

        Example:
            >>> if compressor.needs_summarization(messages):
            ...     summary = await compressor.summarize(messages)
        """
        return len(messages) >= self.summary_threshold

    def _format_messages(
        self,
        messages: List[ConversationMessage],
        max_messages: Optional[int] = None,
    ) -> str:
        """Format messages as text for summarization.

        Args:
            messages: Messages to format
            max_messages: Maximum messages to include

        Returns:
            Formatted conversation text
        """
        if max_messages:
            messages = messages[:max_messages]

        lines = []
        for msg in messages:
            # Format: ROLE: content
            lines.append(f"{msg.role.upper()}: {msg.content}")

        return "\n\n".join(lines)

    def _format_conversation_section(
        self, conversation: Conversation, summary: str
    ) -> str:
        """Format conversation section for context string.

        Args:
            conversation: Conversation to format
            summary: Summary or full text

        Returns:
            Formatted section with metadata
        """
        # Format timestamp
        timestamp = conversation.updated_at.strftime("%Y-%m-%d %H:%M")

        # Build section
        return f"""## Conversation: {conversation.id}
**Project:** {conversation.project_id}
**Instance:** {conversation.instance_name}
**Updated:** {timestamp}
**Messages:** {conversation.message_count}

{summary}"""

    async def auto_summarize_conversation(
        self, conversation: Conversation
    ) -> Optional[str]:
        """Automatically summarize conversation if needed.

        Checks if conversation needs summarization and generates one if so.
        Updates the conversation's summary field but does NOT save to store.

        Args:
            conversation: Conversation to summarize

        Returns:
            Summary if generated, None if not needed

        Example:
            >>> summary = await compressor.auto_summarize_conversation(conv)
            >>> if summary:
            ...     conv.summary = summary
            ...     await store.save(conv)
        """
        if not self.needs_summarization(conversation.messages):
            logger.debug(
                "Conversation %s too short to summarize (%d messages)",
                conversation.id,
                len(conversation.messages),
            )
            return None

        if conversation.summary:
            logger.debug("Conversation %s already has summary", conversation.id)
            return conversation.summary

        # Generate summary
        summary = await self.summarize(conversation.messages)
        logger.info("Auto-generated summary for conversation %s", conversation.id)

        return summary

    async def update_summary_if_stale(
        self,
        conversation: Conversation,
        message_threshold: int = 5,
    ) -> Optional[str]:
        """Update summary if conversation has grown significantly.

        Args:
            conversation: Conversation to check
            message_threshold: New messages required to trigger update

        Returns:
            Updated summary if regenerated, None otherwise

        Example:
            >>> updated = await compressor.update_summary_if_stale(conv)
            >>> if updated:
            ...     conv.summary = updated
            ...     await store.save(conv)
        """
        if not conversation.summary:
            # No existing summary, generate one
            return await self.auto_summarize_conversation(conversation)

        # Check if conversation has grown significantly
        # (Simple heuristic: if more than threshold messages since last summarization)
        # In practice, you'd track when summary was generated
        if len(conversation.messages) < self.summary_threshold + message_threshold:
            return None

        # Regenerate summary
        logger.info(
            "Regenerating stale summary for conversation %s (%d messages)",
            conversation.id,
            len(conversation.messages),
        )

        return await self.summarize(conversation.messages)
