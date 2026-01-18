"""Embedding service for semantic search.

Generates vector embeddings using sentence-transformers (local) or
OpenAI API (cloud). Defaults to local model for zero-cost operation.
"""

import asyncio
import logging
from typing import List, Literal, Optional

logger = logging.getLogger(__name__)

EmbeddingProvider = Literal["sentence-transformers", "openai"]


class EmbeddingService:
    """Generate vector embeddings for semantic search.

    Supports multiple providers:
    - sentence-transformers: Local, free, good quality (default)
    - openai: Cloud API, best quality, costs money

    Attributes:
        provider: Embedding provider to use
        model: Model name for the provider
        dimension: Embedding vector dimension

    Example:
        >>> embeddings = EmbeddingService(provider="sentence-transformers")
        >>> vector = await embeddings.embed("Fix the login bug")
        >>> len(vector)
        384
    """

    def __init__(
        self,
        provider: EmbeddingProvider = "sentence-transformers",
        model: Optional[str] = None,
    ):
        """Initialize embedding service.

        Args:
            provider: Embedding provider ('sentence-transformers' or 'openai')
            model: Model name (provider-specific default if None)
        """
        self.provider = provider
        self._encoder = None
        self._client = None

        if provider == "sentence-transformers":
            self.model = model or "all-MiniLM-L6-v2"
            self.dimension = 384
            self._init_sentence_transformers()
        elif provider == "openai":
            self.model = model or "text-embedding-3-small"
            self.dimension = 1536
            self._init_openai()
        else:
            raise ValueError(f"Unknown provider: {provider}")

        logger.info(
            "EmbeddingService initialized (provider: %s, model: %s, dim: %d)",
            provider,
            self.model,
            self.dimension,
        )

    def _init_sentence_transformers(self) -> None:
        """Initialize sentence-transformers encoder.

        Lazy loads on first use to avoid startup delay.
        """
        # Lazy import to avoid dependency if not used
        try:
            from sentence_transformers import SentenceTransformer

            self._encoder = SentenceTransformer(self.model)
            logger.info("Loaded sentence-transformers model: %s", self.model)
        except ImportError:
            logger.error(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
            raise

    def _init_openai(self) -> None:
        """Initialize OpenAI client.

        Requires OPENAI_API_KEY environment variable.
        """
        try:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI()
            logger.info("Initialized OpenAI client")
        except ImportError:
            logger.error("openai not installed. Install with: pip install openai")
            raise

    async def embed(self, text: str) -> List[float]:
        """Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats

        Example:
            >>> vector = await embeddings.embed("Fix the login bug")
            >>> len(vector)
            384
        """
        if self.provider == "sentence-transformers":
            return await self._embed_sentence_transformers(text)
        if self.provider == "openai":
            return await self._embed_openai(text)
        raise ValueError(f"Unknown provider: {self.provider}")

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        More efficient than calling embed() in a loop.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Example:
            >>> vectors = await embeddings.embed_batch([
            ...     "Fix the login bug",
            ...     "Update the README"
            ... ])
            >>> len(vectors)
            2
        """
        if self.provider == "sentence-transformers":
            return await self._embed_batch_sentence_transformers(texts)
        if self.provider == "openai":
            return await self._embed_batch_openai(texts)
        raise ValueError(f"Unknown provider: {self.provider}")

    async def _embed_sentence_transformers(self, text: str) -> List[float]:
        """Generate embedding using sentence-transformers.

        Runs in executor to avoid blocking event loop.
        """
        if self._encoder is None:
            raise RuntimeError("Encoder not initialized")

        # Run encoding in executor (CPU-bound operation)
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None, lambda: self._encoder.encode(text, convert_to_numpy=True)
        )

        return embedding.tolist()

    async def _embed_batch_sentence_transformers(
        self, texts: List[str]
    ) -> List[List[float]]:
        """Generate batch embeddings using sentence-transformers."""
        if self._encoder is None:
            raise RuntimeError("Encoder not initialized")

        # Run batch encoding in executor
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: self._encoder.encode(
                texts, convert_to_numpy=True, show_progress_bar=False
            ),
        )

        return [emb.tolist() for emb in embeddings]

    async def _embed_openai(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API."""
        if self._client is None:
            raise RuntimeError("OpenAI client not initialized")

        response = await self._client.embeddings.create(
            model=self.model,
            input=text,
        )

        return response.data[0].embedding

    async def _embed_batch_openai(self, texts: List[str]) -> List[List[float]]:
        """Generate batch embeddings using OpenAI API."""
        if self._client is None:
            raise RuntimeError("OpenAI client not initialized")

        response = await self._client.embeddings.create(
            model=self.model,
            input=texts,
        )

        return [item.embedding for item in response.data]

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score in range [-1, 1] (1 = identical, -1 = opposite)

        Example:
            >>> sim = embeddings.cosine_similarity(vec1, vec2)
            >>> print(f"Similarity: {sim:.3f}")
        """
        import math

        # Dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # Magnitudes
        mag1 = math.sqrt(sum(a * a for a in vec1))
        mag2 = math.sqrt(sum(b * b for b in vec2))

        # Avoid division by zero
        if mag1 == 0 or mag2 == 0:
            return 0.0

        return dot_product / (mag1 * mag2)
