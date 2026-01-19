"""Semantic search for conversations.

Provides vector-based and text-based search across all stored conversations
with filtering by project, date range, and entity types.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from .embeddings import EmbeddingService
from .entities import EntityType
from .store import Conversation, ConversationStore

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result with relevance score.

    Attributes:
        conversation: Matched conversation
        score: Relevance score (0-1, higher is more relevant)
        matched_entities: Entities that matched the query
        snippet: Relevant text snippet

    Example:
        >>> result = search_results[0]
        >>> print(f"Score: {result.score:.3f}")
        >>> print(f"Conversation: {result.conversation.id}")
    """

    conversation: Conversation
    score: float
    matched_entities: List[str] = None
    snippet: str = ""

    def __post_init__(self) -> None:
        """Initialize matched_entities if not provided."""
        if self.matched_entities is None:
            self.matched_entities = []


class SemanticSearch:
    """Semantic search across conversations.

    Combines vector similarity search with text search and entity filtering
    for comprehensive conversation retrieval.

    Attributes:
        store: ConversationStore for persistence
        embeddings: EmbeddingService for vector generation

    Example:
        >>> search = SemanticSearch(store, embeddings)
        >>> results = await search.search(
        ...     "how did we fix the login bug?",
        ...     project_id="proj-xyz",
        ...     limit=5
        ... )
    """

    def __init__(self, store: ConversationStore, embeddings: EmbeddingService):
        """Initialize semantic search.

        Args:
            store: ConversationStore for conversation persistence
            embeddings: EmbeddingService for vector generation
        """
        self.store = store
        self.embeddings = embeddings

        logger.info("SemanticSearch initialized (vector: %s)", store.enable_vector)

    async def search(
        self,
        query: str,
        project_id: Optional[str] = None,
        limit: int = 10,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        entity_types: Optional[List[EntityType]] = None,
    ) -> List[SearchResult]:
        """Search conversations semantically.

        Uses vector similarity if available, falls back to text search.
        Results are ranked by relevance score.

        Args:
            query: Natural language search query
            project_id: Optional project ID filter
            limit: Maximum number of results
            date_range: Optional (start, end) datetime filter
            entity_types: Optional list of entity types to filter by

        Returns:
            List of SearchResult ordered by relevance (highest first)

        Example:
            >>> results = await search.search(
            ...     "login bug fix",
            ...     project_id="proj-xyz",
            ...     limit=5
            ... )
            >>> print(f"Found {len(results)} results")
            >>> print(f"Top result: {results[0].conversation.summary}")
        """
        logger.debug(
            "Searching conversations (query: %s, project: %s, limit: %d)",
            query[:50],
            project_id or "all",
            limit,
        )

        if self.store.enable_vector:
            # Use vector search
            results = await self._vector_search(query, project_id, limit)
        else:
            # Fall back to text search
            conversations = await self.store.search_by_text(query, project_id, limit)
            results = [
                SearchResult(conversation=conv, score=0.5) for conv in conversations
            ]

        # Apply date range filter
        if date_range:
            start, end = date_range
            results = [r for r in results if start <= r.conversation.updated_at <= end]

        # Apply entity type filter
        if entity_types:
            results = self._filter_by_entities(results, entity_types)

        # Generate snippets for top results
        for result in results[:limit]:
            result.snippet = self._generate_snippet(result.conversation, query)

        logger.info("Search returned %d results", len(results))
        return results[:limit]

    async def _vector_search(
        self,
        query: str,
        project_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[SearchResult]:
        """Perform vector similarity search.

        Args:
            query: Search query
            project_id: Optional project filter
            limit: Maximum results

        Returns:
            List of SearchResult with similarity scores
        """
        # Generate query embedding
        query_embedding = await self.embeddings.embed(query)

        # Get all conversations (TODO: optimize with vector DB query)
        if project_id:
            conversations = await self.store.list_by_project(project_id, limit=100)
        else:
            # For now, we'll search recent conversations across all projects
            # In production, you'd want to implement proper vector search in SQL
            conversations = []
            logger.warning(
                "Vector search without project_id not fully optimized. "
                "Consider implementing KNN query in SQL."
            )

        # Calculate similarities
        results = []
        for conv in conversations:
            if not conv.embedding:
                # Generate embedding if missing
                text = conv.summary or conv.get_full_text()[:1000]
                conv.embedding = await self.embeddings.embed(text)
                await self.store.save(conv)

            # Calculate cosine similarity
            score = self.embeddings.cosine_similarity(query_embedding, conv.embedding)
            results.append(SearchResult(conversation=conv, score=score))

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)

        return results[:limit]

    def _filter_by_entities(
        self, results: List[SearchResult], entity_types: List[EntityType]
    ) -> List[SearchResult]:
        """Filter results by entity types.

        Args:
            results: Search results to filter
            entity_types: Entity types to require

        Returns:
            Filtered results
        """
        filtered = []
        for result in results:
            # Check if conversation has any messages with matching entities
            has_entity = False
            for msg in result.conversation.messages:
                for entity in msg.entities:
                    if EntityType(entity["type"]) in entity_types:
                        has_entity = True
                        if "matched_entities" not in result.matched_entities:
                            result.matched_entities.append(entity["value"])

            if has_entity:
                filtered.append(result)

        return filtered

    def _generate_snippet(self, conversation: Conversation, query: str) -> str:
        """Generate relevant text snippet from conversation.

        Args:
            conversation: Conversation to extract snippet from
            query: Search query for context

        Returns:
            Relevant snippet (max 200 chars)
        """
        # Try to find message containing query terms
        query_terms = query.lower().split()

        for msg in conversation.messages:
            content_lower = msg.content.lower()
            if any(term in content_lower for term in query_terms):
                # Found relevant message, extract snippet
                start_idx = 0
                for term in query_terms:
                    if term in content_lower:
                        start_idx = content_lower.index(term)
                        break

                # Extract context around match
                snippet_start = max(0, start_idx - 50)
                snippet_end = min(len(msg.content), start_idx + 150)
                snippet = msg.content[snippet_start:snippet_end]

                # Add ellipsis if truncated
                if snippet_start > 0:
                    snippet = "..." + snippet
                if snippet_end < len(msg.content):
                    snippet = snippet + "..."

                return snippet.strip()

        # No match found, use summary or first message
        if conversation.summary:
            return conversation.summary[:200]
        if conversation.messages:
            return conversation.messages[0].content[:200] + "..."

        return ""

    async def find_similar(
        self,
        conversation_id: str,
        limit: int = 5,
    ) -> List[SearchResult]:
        """Find conversations similar to a given conversation.

        Args:
            conversation_id: Reference conversation ID
            limit: Maximum number of similar conversations

        Returns:
            List of similar conversations ordered by similarity

        Example:
            >>> similar = await search.find_similar("conv-abc123", limit=5)
        """
        # Load reference conversation
        ref_conv = await self.store.load(conversation_id)
        if not ref_conv:
            logger.warning("Conversation %s not found", conversation_id)
            return []

        # Ensure embedding exists
        if not ref_conv.embedding:
            text = ref_conv.summary or ref_conv.get_full_text()[:1000]
            ref_conv.embedding = await self.embeddings.embed(text)
            await self.store.save(ref_conv)

        # Get all conversations from same project
        all_convs = await self.store.list_by_project(ref_conv.project_id, limit=100)

        # Calculate similarities
        results = []
        for conv in all_convs:
            # Skip the reference conversation itself
            if conv.id == conversation_id:
                continue

            if not conv.embedding:
                text = conv.summary or conv.get_full_text()[:1000]
                conv.embedding = await self.embeddings.embed(text)
                await self.store.save(conv)

            score = self.embeddings.cosine_similarity(
                ref_conv.embedding, conv.embedding
            )
            results.append(SearchResult(conversation=conv, score=score))

        # Sort by similarity
        results.sort(key=lambda r: r.score, reverse=True)

        logger.info(
            "Found %d similar conversations to %s",
            len(results[:limit]),
            conversation_id,
        )
        return results[:limit]

    async def search_by_entities(
        self,
        entity_type: EntityType,
        entity_value: str,
        project_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[SearchResult]:
        """Search conversations by specific entity.

        Args:
            entity_type: Type of entity to search for
            entity_value: Entity value (e.g., "src/auth.py")
            project_id: Optional project filter
            limit: Maximum results

        Returns:
            List of conversations containing the entity

        Example:
            >>> results = await search.search_by_entities(
            ...     EntityType.FILE,
            ...     "src/auth.py",
            ...     project_id="proj-xyz"
            ... )
        """
        # Get conversations from project
        if project_id:
            conversations = await self.store.list_by_project(project_id, limit=100)
        else:
            conversations = []
            logger.warning("Entity search without project_id requires full scan")

        # Filter by entity
        results = []
        for conv in conversations:
            for msg in conv.messages:
                for entity in msg.entities:
                    if (
                        entity.get("type") == entity_type.value
                        and entity.get("value") == entity_value
                    ):
                        results.append(
                            SearchResult(
                                conversation=conv,
                                score=1.0,  # Exact match
                                matched_entities=[entity_value],
                            )
                        )
                        break

            if len(results) >= limit:
                break

        logger.info(
            "Found %d conversations with entity %s:%s",
            len(results),
            entity_type.value,
            entity_value,
        )
        return results[:limit]
