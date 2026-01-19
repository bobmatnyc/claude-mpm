"""Conversation memory system for Commander.

This module provides semantic search, storage, and context compression
for all Claude Code instance conversations.

Key Components:
    - ConversationStore: CRUD operations for conversations
    - EmbeddingService: Generate vector embeddings
    - SemanticSearch: Query conversations semantically
    - ContextCompressor: Summarize conversations for context
    - EntityExtractor: Extract files, functions, errors

Example:
    >>> from claude_mpm.commander.memory import (
    ...     ConversationStore,
    ...     EmbeddingService,
    ...     SemanticSearch,
    ...     ContextCompressor,
    ... )
    >>> store = ConversationStore()
    >>> embeddings = EmbeddingService()
    >>> search = SemanticSearch(store, embeddings)
    >>> results = await search.search("how did we fix the login bug?")
"""

from .compression import ContextCompressor
from .embeddings import EmbeddingService
from .entities import Entity, EntityExtractor, EntityType
from .integration import MemoryIntegration
from .search import SearchResult, SemanticSearch
from .store import Conversation, ConversationMessage, ConversationStore

__all__ = [
    "ContextCompressor",
    "Conversation",
    "ConversationMessage",
    "ConversationStore",
    "EmbeddingService",
    "Entity",
    "EntityExtractor",
    "EntityType",
    "MemoryIntegration",
    "SearchResult",
    "SemanticSearch",
]
