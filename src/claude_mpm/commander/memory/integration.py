"""Integration helpers for memory system with Commander.

Provides high-level functions to integrate conversation memory with
RuntimeMonitor, Chat CLI, and session resumption workflows.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from ..llm.openrouter_client import OpenRouterClient
from ..models.project import Project, ThreadMessage
from .compression import ContextCompressor
from .embeddings import EmbeddingService
from .entities import EntityExtractor
from .search import SemanticSearch
from .store import Conversation, ConversationMessage, ConversationStore

logger = logging.getLogger(__name__)


class MemoryIntegration:
    """High-level memory integration for Commander.

    Provides simple API for common memory operations:
    - Capture conversation from Project
    - Search across all conversations
    - Load context for session resume

    Attributes:
        store: ConversationStore for persistence
        embeddings: EmbeddingService for vectors
        search: SemanticSearch for queries
        compressor: ContextCompressor for summaries
        extractor: EntityExtractor for entity extraction

    Example:
        >>> memory = MemoryIntegration.create()
        >>> await memory.capture_project_conversation(project)
        >>> results = await memory.search("login bug fix", project_id="proj-xyz")
    """

    def __init__(
        self,
        store: ConversationStore,
        embeddings: EmbeddingService,
        search: SemanticSearch,
        compressor: ContextCompressor,
        extractor: EntityExtractor,
    ):
        """Initialize memory integration.

        Args:
            store: ConversationStore instance
            embeddings: EmbeddingService instance
            search: SemanticSearch instance
            compressor: ContextCompressor instance
            extractor: EntityExtractor instance
        """
        self.store = store
        self.embeddings = embeddings
        self.search = search
        self.compressor = compressor
        self.extractor = extractor

        logger.info("MemoryIntegration initialized")

    @classmethod
    def create(
        cls,
        openrouter_client: Optional[OpenRouterClient] = None,
        embedding_provider: str = "sentence-transformers",
    ) -> "MemoryIntegration":
        """Create MemoryIntegration with default configuration.

        Args:
            openrouter_client: Optional OpenRouterClient for summarization
            embedding_provider: Embedding provider ("sentence-transformers" or "openai")

        Returns:
            Configured MemoryIntegration instance

        Example:
            >>> from claude_mpm.commander.llm import OpenRouterClient
            >>> client = OpenRouterClient()
            >>> memory = MemoryIntegration.create(openrouter_client=client)
        """
        store = ConversationStore()
        embeddings = EmbeddingService(provider=embedding_provider)
        search = SemanticSearch(store, embeddings)

        # Create OpenRouter client if not provided
        if openrouter_client is None:
            openrouter_client = OpenRouterClient()

        compressor = ContextCompressor(openrouter_client)
        extractor = EntityExtractor()

        return cls(store, embeddings, search, compressor, extractor)

    async def capture_project_conversation(
        self,
        project: Project,
        instance_name: str = "unknown",
        session_id: Optional[str] = None,
    ) -> Conversation:
        """Capture conversation from Project thread.

        Converts Project.thread (List[ThreadMessage]) into a Conversation
        with entity extraction and optional summarization.

        Args:
            project: Project with conversation thread
            instance_name: Instance name (e.g., "claude-code-1")
            session_id: Optional session ID

        Returns:
            Captured and saved Conversation

        Example:
            >>> conv = await memory.capture_project_conversation(project)
            >>> print(f"Captured conversation {conv.id} with {len(conv.messages)} messages")
        """
        if not project.thread:
            logger.warning("Project %s has no conversation thread", project.id)
            return None

        # Convert ThreadMessages to ConversationMessages
        messages = []
        for thread_msg in project.thread:
            conv_msg = ConversationMessage.from_thread_message(thread_msg)

            # Extract entities
            entities = self.extractor.extract(conv_msg.content)
            conv_msg.entities = [e.to_dict() for e in entities]

            messages.append(conv_msg)

        # Create conversation
        conversation = Conversation(
            id=f"conv-{uuid.uuid4().hex[:12]}",
            project_id=project.id,
            instance_name=instance_name,
            session_id=session_id or f"sess-{uuid.uuid4().hex[:8]}",
            messages=messages,
        )

        # Auto-summarize if needed
        if self.compressor.needs_summarization(messages):
            conversation.summary = await self.compressor.summarize(messages)
            logger.info("Auto-generated summary for conversation %s", conversation.id)

        # Generate embedding for semantic search
        text_for_embedding = conversation.summary or conversation.get_full_text()[:1000]
        conversation.embedding = await self.embeddings.embed(text_for_embedding)

        # Save to store
        await self.store.save(conversation)

        logger.info(
            "Captured conversation %s (%d messages) from project %s",
            conversation.id,
            len(messages),
            project.id,
        )

        return conversation

    async def search_conversations(
        self,
        query: str,
        project_id: Optional[str] = None,
        limit: int = 10,
    ) -> List:
        """Search conversations by natural language query.

        Args:
            query: Natural language search query
            project_id: Optional project filter
            limit: Maximum results

        Returns:
            List of SearchResult with conversations

        Example:
            >>> results = await memory.search_conversations(
            ...     "how did we fix the authentication bug?",
            ...     project_id="proj-xyz",
            ...     limit=5
            ... )
            >>> for result in results:
            ...     print(f"{result.score:.2f}: {result.snippet}")
        """
        return await self.search.search(query, project_id=project_id, limit=limit)

    async def load_context_for_session(
        self,
        project_id: str,
        max_tokens: int = 4000,
        limit_conversations: int = 10,
    ) -> str:
        """Load compressed context for session resumption.

        Retrieves recent conversations from project and compresses them
        into a context string suitable for LLM input.

        Args:
            project_id: Project ID to load context for
            max_tokens: Maximum tokens for context
            limit_conversations: Maximum conversations to consider

        Returns:
            Compressed context string

        Example:
            >>> context = await memory.load_context_for_session("proj-xyz")
            >>> print(f"Loaded context: {len(context)} chars")
        """
        # Get recent conversations from project
        conversations = await self.store.list_by_project(
            project_id, limit=limit_conversations
        )

        if not conversations:
            logger.info("No conversations found for project %s", project_id)
            return ""

        # Compress into context
        context = await self.compressor.compress_for_context(
            conversations, max_tokens=max_tokens
        )

        logger.info(
            "Loaded context for project %s: %d conversations, %d chars",
            project_id,
            len(conversations),
            len(context),
        )

        return context

    async def update_conversation(
        self,
        conversation_id: str,
        new_messages: List[ThreadMessage],
    ) -> Optional[Conversation]:
        """Update existing conversation with new messages.

        Args:
            conversation_id: Conversation to update
            new_messages: New messages to append

        Returns:
            Updated conversation if found, None otherwise

        Example:
            >>> updated = await memory.update_conversation(
            ...     "conv-abc123",
            ...     [new_message1, new_message2]
            ... )
        """
        # Load existing conversation
        conversation = await self.store.load(conversation_id)
        if not conversation:
            logger.warning("Conversation %s not found", conversation_id)
            return None

        # Convert and append new messages
        for thread_msg in new_messages:
            conv_msg = ConversationMessage.from_thread_message(thread_msg)

            # Extract entities
            entities = self.extractor.extract(conv_msg.content)
            conv_msg.entities = [e.to_dict() for e in entities]

            conversation.messages.append(conv_msg)

        # Update timestamp
        conversation.updated_at = datetime.now(timezone.utc)

        # Regenerate summary if needed
        updated_summary = await self.compressor.update_summary_if_stale(
            conversation, message_threshold=5
        )
        if updated_summary:
            conversation.summary = updated_summary

        # Regenerate embedding
        text_for_embedding = conversation.summary or conversation.get_full_text()[:1000]
        conversation.embedding = await self.embeddings.embed(text_for_embedding)

        # Save
        await self.store.save(conversation)

        logger.info(
            "Updated conversation %s (now %d messages)",
            conversation_id,
            len(conversation.messages),
        )

        return conversation

    async def get_conversation_by_session(
        self, session_id: str
    ) -> Optional[Conversation]:
        """Get conversation by session ID.

        Args:
            session_id: Session ID from ToolSession

        Returns:
            Conversation if found, None otherwise

        Example:
            >>> conv = await memory.get_conversation_by_session("sess-abc123")
        """
        # For now, this requires loading and checking
        # In production, you'd add an index on session_id
        # This is a placeholder - implement proper query in store
        logger.warning(
            "get_conversation_by_session requires optimization - "
            "add session_id index to store"
        )
        return None
