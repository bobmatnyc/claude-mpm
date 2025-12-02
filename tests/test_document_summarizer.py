"""
Unit tests for Document Summarizer Tool
========================================

Tests the document summarizer tool implementation for ISS-0037.
"""

import contextlib
import os
import tempfile

import pytest

from claude_mpm.services.mcp_gateway.core.interfaces import MCPToolInvocation
from claude_mpm.services.mcp_gateway.tools.document_summarizer import (
    DocumentSummarizerTool,
    LRUCache,
)


class TestLRUCache:
    """Test the LRU cache implementation."""

    def test_cache_initialization():
        """Test cache initialization with size and memory limits."""
        cache = LRUCache(max_size=10, max_memory_mb=1)
        assert cache.max_size == 10
        assert cache.max_memory_bytes == 1024 * 1024
        assert len(cache.cache) == 0
        assert cache.hits == 0
        assert cache.misses == 0

    def test_cache_put_and_get():
        """Test basic cache put and get operations."""
        cache = LRUCache(max_size=3)

        # Put items
        cache.put("key1", {"data": "value1"}, 100)
        cache.put("key2", {"data": "value2"}, 100)

        # Get items
        assert cache.get("key1")["data"] == "value1"
        assert cache.get("key2")["data"] == "value2"
        assert cache.get("key3") is None

        # Check stats
        assert cache.hits == 2
        assert cache.misses == 1

    def test_cache_lru_eviction():
        """Test LRU eviction when cache is full."""
        cache = LRUCache(max_size=2)

        # Fill cache
        cache.put("key1", {"data": "value1"}, 100)
        cache.put("key2", {"data": "value2"}, 100)

        # Access key1 to make it more recently used
        cache.get("key1")

        # Add new item, should evict key2
        cache.put("key3", {"data": "value3"}, 100)

        assert cache.get("key1") is not None  # Still in cache
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") is not None  # New item

    def test_cache_memory_limit():
        """Test cache eviction based on memory limit."""
        cache = LRUCache(max_size=100, max_memory_mb=1)

        # Add items that exceed memory limit
        large_size = 512 * 1024  # 512KB
        cache.put("key1", {"data": "large1"}, large_size)
        cache.put("key2", {"data": "large2"}, large_size)
        cache.put("key3", {"data": "large3"}, large_size)

        # Should have evicted oldest items to stay under 1MB
        assert cache.current_memory <= cache.max_memory_bytes
        assert len(cache.cache) <= 2  # Should keep only 2 items

    def test_cache_stats():
        """Test cache statistics reporting."""
        cache = LRUCache(max_size=10)

        # Generate some activity
        cache.put("key1", {"data": "value1"}, 100)
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss
        cache.get("key1")  # Hit

        stats = cache.get_stats()
        assert stats["size"] == 1
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 2 / 3


class TestDocumentSummarizerTool:
    """Test the DocumentSummarizerTool implementation."""

    @pytest.fixture
    def tool(self):
        """Create a DocumentSummarizerTool instance."""
        return DocumentSummarizerTool()

    @pytest.fixture
    def temp_file(self):
        """Create a temporary test file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("This is a test document. " * 100)
            f.write("\n\n")
            f.write("This is the second paragraph. " * 50)
            f.write("\n\n")
            f.write("This is the final paragraph with conclusions. " * 30)
            temp_path = f.name

        yield temp_path

        # Cleanup
        with contextlib.suppress(Exception):
            os.unlink(temp_path)

    def test_tool_initialization(self):
        """Test tool initialization and definition."""
        definition = self.get_definition()
        assert definition.name == "document_summarizer"
        assert "file_path" in definition.input_schema["properties"]
        assert "mode" in definition.input_schema["properties"]
        assert definition.metadata["category"] == "document_processing"

    def test_file_validation_exists(self, temp_file):
        """Test file validation for existing file."""
        is_valid, error = self._validate_file(temp_file)
        assert is_valid
        assert error is None

    def test_file_validation_not_exists(self):
        """Test file validation for non-existent file."""
        is_valid, error = self._validate_file("/nonexistent/file.txt")
        assert not is_valid
        assert "not found" in error.lower()

    def test_file_validation_directory(self):
        """Test file validation rejects directories."""
        is_valid, error = self._validate_file(tempfile.gettempdir())
        assert not is_valid
        assert "not a file" in error.lower()

    def test_file_validation_size_limit(self):
        """Test file size validation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            # Write more than 10MB
            f.write("x" * (11 * 1024 * 1024))
            large_file = f.name

        try:
            is_valid, error = self._validate_file(large_file)
            assert not is_valid
            assert "too large" in error.lower()
        finally:
            os.unlink(large_file)

    def test_token_estimation(self):
        """Test token estimation calculation."""
        text = "This is a test sentence with several words."
        estimated = self._estimate_tokens(text)
        # Rough estimate: ~4 chars per token
        expected = len(text) // 4
        assert estimated == expected

    def test_sentence_truncation(self):
        """Test truncation at sentence boundaries."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        truncated = self._truncate_at_sentence(text, 30)

        # Should truncate at sentence boundary
        assert truncated.endswith((". ", "..."))
        assert len(truncated) <= 30
        assert "First sentence" in truncated

    def test_code_block_extraction(self):
        """Test extraction and restoration of code blocks."""
        text = """
        Some text before code.

        ```python
        def hello():
            print("Hello, world!")
        ```

        Some text after code.
        """

        blocks, text_without = self._extract_code_blocks(text)

        # Should extract code block
        assert len(blocks) == 1
        assert "def hello():" in blocks[0]
        assert "[[CODE_BLOCK_0]]" in text_without

        # Should restore code block
        restored = self._restore_code_blocks(text_without, blocks)
        assert "def hello():" in restored

    def test_summarize_brief_mode(self):
        """Test brief summarization mode."""
        text = "Beginning of document. " * 50
        text += "\n\nMiddle section. " * 100
        text += "\n\nEnd of document. " * 50

        summary = self._summarize_brief(text, 500)

        assert len(summary) <= 500
        assert "Beginning of document" in summary
        assert "End of document" in summary
        assert "content omitted" in summary or len(text) <= 500

    def test_summarize_key_points_mode(self):
        """Test key points extraction mode."""
        text = """
        Introduction paragraph.

        Key points:
        - First important point
        - Second important point
        - Third important point

        Some regular text.

        1. Numbered item one
        2. Numbered item two

        Conclusion paragraph.
        """

        summary = self._summarize_key_points(text, 1000)

        # Should extract bullet points and numbered lists
        assert "First important point" in summary
        assert "Numbered item one" in summary

    def test_summarize_technical_mode(self):
        """Test technical summarization mode."""
        text = """
        import os
        import sys
        from typing import List

        class MyClass:
            def __init__(self):
                pass

        def my_function(param: str) -> str:
            return param.upper()

        # Some implementation details
        for i in range(100):
            print(i)
        """

        summary = self._summarize_technical(text, 500, preserve_code=True)

        # Should preserve imports and definitions
        assert "import" in summary
        assert "class MyClass" in summary or "def my_function" in summary

    @pytest.mark.asyncio
    async def test_invoke_success(self, temp_file):
        """Test successful tool invocation."""
        invocation = MCPToolInvocation(
            tool_name="document_summarizer",
            parameters={"file_path": temp_file, "mode": "brief", "max_percentage": 30},
        )

        result = await self.invoke(invocation)

        assert result.success
        assert result.data is not None
        assert "summary" in result.data
        assert "reduction_percentage" in result.data
        assert result.data["reduction_percentage"] > 0
        assert result.data["original_size"] > result.data["summary_size"]

    @pytest.mark.asyncio
    async def test_invoke_with_cache(self, temp_file):
        """Test tool invocation with caching."""
        invocation = MCPToolInvocation(
            tool_name="document_summarizer",
            parameters={"file_path": temp_file, "mode": "brief", "use_cache": True},
        )

        # First invocation - cache miss
        result1 = await self.invoke(invocation)
        assert result1.success
        assert not result1.data["cache_hit"]

        # Second invocation - cache hit
        result2 = await self.invoke(invocation)
        assert result2.success
        assert result2.data["cache_hit"]

        # Results should be the same
        assert result1.data["summary"] == result2.data["summary"]

    @pytest.mark.asyncio
    async def test_invoke_invalid_file(self):
        """Test tool invocation with invalid file."""
        invocation = MCPToolInvocation(
            tool_name="document_summarizer",
            parameters={"file_path": "/nonexistent/file.txt"},
        )

        result = await self.invoke(invocation)

        assert not result.success
        assert result.error is not None
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invoke_all_modes(self, temp_file):
        """Test all summarization modes."""
        modes = ["brief", "detailed", "key_points", "technical"]

        for mode in modes:
            invocation = MCPToolInvocation(
                tool_name="document_summarizer",
                parameters={"file_path": temp_file, "mode": mode},
            )

            result = await self.invoke(invocation)
            assert result.success, f"Mode {mode} failed"
            assert result.data["summary"] is not None
            assert result.data["reduction_percentage"] > 0

    @pytest.mark.asyncio
    async def test_chunk_processing(self):
        """Test processing of large documents in chunks."""
        # Create a large temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            # Write more than CHUNK_SIZE characters
            f.write("Large document content. " * 5000)
            large_file = f.name

        try:
            invocation = MCPToolInvocation(
                tool_name="document_summarizer",
                parameters={"file_path": large_file, "mode": "brief"},
            )

            result = await self.invoke(invocation)

            assert result.success
            assert result.data["chunks_processed"] > 1
            assert "[--- Next Section ---]" in result.data["summary"]
        finally:
            os.unlink(large_file)

    @pytest.mark.asyncio
    async def test_metrics_tracking(self, temp_file):
        """Test metrics tracking."""
        # Successful invocation
        invocation = MCPToolInvocation(
            tool_name="document_summarizer", parameters={"file_path": temp_file}
        )
        await self.invoke(invocation)

        # Failed invocation
        bad_invocation = MCPToolInvocation(
            tool_name="document_summarizer",
            parameters={"file_path": "/nonexistent.txt"},
        )
        await self.invoke(bad_invocation)

        metrics = self.get_metrics()
        assert metrics["invocations"] == 2
        assert metrics["successes"] == 1
        assert metrics["failures"] == 1
        assert metrics["average_execution_time"] > 0

    @pytest.mark.asyncio
    async def test_initialization_and_shutdown(self):
        """Test tool initialization and shutdown."""
        # Initialize
        success = await self.initialize()
        assert success
        assert self._initialized

        # Shutdown
        await self.shutdown()
        assert not self._initialized


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def tool(self):
        return DocumentSummarizerTool()

    def test_empty_file(self):
        """Test handling of empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("")
            empty_file = f.name

        try:
            content = self._read_file(empty_file)
            assert content == ""

            summary = self._summarize_brief(content, 100)
            assert summary == ""
        finally:
            os.unlink(empty_file)

    def test_unicode_handling(self):
        """Test handling of unicode content."""
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".txt", delete=False
        ) as f:
            f.write("Unicode test: 你好世界 🌍 Émojis work! ñáéíóú")
            unicode_file = f.name

        try:
            content = self._read_file(unicode_file)
            assert "你好世界" in content
            assert "🌍" in content
            assert "ñáéíóú" in content
        finally:
            os.unlink(unicode_file)

    def test_binary_file_handling(self):
        """Test handling of binary files."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".bin", delete=False) as f:
            f.write(b"\x00\x01\x02\x03")
            binary_file = f.name

        try:
            # Should handle binary file gracefully
            content = self._read_file(binary_file)
            assert isinstance(content, str)
        finally:
            os.unlink(binary_file)

    def test_malformed_code_blocks(self):
        """Test handling of malformed code blocks."""
        text = """
        Incomplete code block:
        ```python
        def incomplete():
            # Missing closing backticks

        Another section
        """

        # Should handle gracefully without crashing
        blocks, text_without = self._extract_code_blocks(text)
        # Malformed block might not be extracted properly
        assert isinstance(blocks, list)
        assert isinstance(text_without, str)
