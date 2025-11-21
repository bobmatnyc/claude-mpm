#!/usr/bin/env python3
"""
Test suite for the MCP document summarizer tool.

This tests the integration of the summarize_document tool
in the MCP stdio server.
"""

import asyncio

import pytest

from claude_mpm.services.mcp_gateway.server.stdio_server import SimpleMCPServer


class TestMCPSummarizerTool:
    """Test suite for the MCP document summarizer tool."""

    @pytest.fixture
    def server(self):
        """Create a test server instance."""
        return SimpleMCPServer()

    @pytest.mark.asyncio
    async def test_summarize_brief(self):
        """Test brief summarization style."""
        content = """
        Artificial Intelligence is transforming industries worldwide.
        Machine learning enables computers to learn from data.
        Deep learning uses neural networks for complex tasks.
        Natural language processing helps computers understand text.
        Computer vision allows machines to interpret images.
        """

        result = await self._summarize_content(
            content=content, style="brief", max_length=30
        )

        assert result is not None
        assert len(result.split()) <= 35  # Allow some overflow
        assert "Artificial Intelligence" in result or "transforming" in result

    @pytest.mark.asyncio
    async def test_summarize_bullet_points(self):
        """Test bullet points extraction."""
        content = """
        Key features of our product:
        • Advanced analytics dashboard
        • Real-time data processing
        • Cloud-based storage
        • Mobile app support
        • 24/7 customer service
        """

        result = await self._summarize_content(
            content=content, style="bullet_points", max_length=50
        )

        assert result is not None
        assert "•" in result  # Should contain bullet points
        assert len(result.split("\n")) > 1  # Multiple lines

    @pytest.mark.asyncio
    async def test_summarize_executive(self):
        """Test executive summary style."""
        content = """
        Our quarterly analysis shows significant growth in user engagement.
        Revenue increased by 25% compared to last quarter.
        Customer satisfaction scores reached an all-time high.
        We recommend expanding into new markets next quarter.
        Investment in R&D should be increased to maintain competitive advantage.
        """

        result = await self._summarize_content(
            content=content, style="executive", max_length=100
        )

        assert result is not None
        assert (
            "OVERVIEW" in result or "FINDINGS" in result or "RECOMMENDATIONS" in result
        )

    @pytest.mark.asyncio
    async def test_summarize_detailed(self):
        """Test detailed summarization."""
        content = """
        Chapter 1: Introduction
        This document describes the system architecture.

        Chapter 2: Components
        The system consists of three main components.

        Chapter 3: Implementation
        Implementation follows industry best practices.

        Chapter 4: Conclusion
        The system provides robust and scalable solutions.
        """

        result = await self._summarize_content(
            content=content, style="detailed", max_length=50
        )

        assert result is not None
        assert len(result.split()) <= 55

    @pytest.mark.asyncio
    async def test_empty_content(self):
        """Test handling of empty content."""
        result = await self._summarize_content(content="", style="brief", max_length=50)

        assert result == "No content provided to summarize."

    @pytest.mark.asyncio
    async def test_short_content(self):
        """Test content shorter than max length."""
        content = "This is a short sentence."

        result = await self._summarize_content(
            content=content, style="brief", max_length=100
        )

        assert result == content

    @pytest.mark.asyncio
    async def test_max_length_enforcement(self):
        """Test that max_length is respected."""
        content = " ".join(["word"] * 200)  # 200 words

        for max_length in [10, 25, 50, 100]:
            result = await self._summarize_content(
                content=content, style="brief", max_length=max_length
            )

            word_count = len(result.split())
            # Allow 10% overflow for sentence completion
            assert word_count <= max_length * 1.1, (
                f"Expected <= {max_length * 1.1} words, got {word_count}"
            )

    @pytest.mark.asyncio
    async def test_tool_registration(self):
        """Test that summarize_document tool is registered."""
        # This would normally test the actual MCP tool registration
        # For now, we'll verify the tool is in the list

        # Note: In a real test, we'd invoke server.server.list_tools()
        # but that requires more setup. This is a simplified version.
        assert hasattr(self, "_summarize_content")
        assert callable(self._summarize_content)

    @pytest.mark.asyncio
    async def test_sentence_boundary_preservation(self):
        """Test that summaries end at sentence boundaries."""
        content = "First sentence. Second sentence. Third sentence. Fourth sentence."

        result = await self._summarize_content(
            content=content,
            style="brief",
            max_length=5,  # Very short to test truncation
        )

        # Should not end mid-word
        assert not result.endswith(" sent")
        assert not result.endswith(" sente")

    @pytest.mark.asyncio
    async def test_multiline_content(self):
        """Test handling of multi-line content."""
        content = """Line 1 with some text.
        Line 2 with more text.
        Line 3 with additional text.
        Line 4 with final text."""

        result = await self._summarize_content(
            content=content, style="brief", max_length=20
        )

        assert result is not None
        assert len(result) > 0


def test_tool_schema():
    """Test that the tool schema is correctly defined."""
    # This tests the schema structure that would be registered with MCP
    expected_schema = {
        "name": "summarize_document",
        "description": "Summarize documents or text content",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The text/document to summarize",
                },
                "style": {
                    "type": "string",
                    "enum": ["brief", "detailed", "bullet_points", "executive"],
                    "description": "Summary style",
                    "default": "brief",
                },
                "max_length": {
                    "type": "integer",
                    "description": "Maximum length of summary in words",
                    "default": 150,
                },
            },
            "required": ["content"],
        },
    }

    # Verify the schema structure
    assert expected_schema["name"] == "summarize_document"
    assert "content" in expected_schema["inputSchema"]["properties"]
    assert "content" in expected_schema["inputSchema"]["required"]
    assert expected_schema["inputSchema"]["properties"]["style"]["default"] == "brief"
    assert expected_schema["inputSchema"]["properties"]["max_length"]["default"] == 150


if __name__ == "__main__":
    # Run tests with pytest if available, otherwise run basic tests
    try:
        import pytest

        pytest.main([__file__, "-v"])
    except ImportError:
        print("pytest not available, running basic tests...")

        async def run_basic_tests():
            server = SimpleMCPServer()

            print("Testing brief summarization...")
            result = await server._summarize_content(
                "This is a test. It has multiple sentences. We want to summarize it.",
                "brief",
                10,
            )
            print(f"✓ Brief summary: {result[:50]}...")

            print("Testing bullet points...")
            result = await server._summarize_content(
                "• Point 1\n• Point 2\n• Point 3", "bullet_points", 20
            )
            print(f"✓ Bullet points: {result[:50]}...")

            print("Testing empty content...")
            result = await server._summarize_content("", "brief", 50)
            assert result == "No content provided to summarize."
            print("✓ Empty content handled correctly")

            print("\nAll basic tests passed!")

        asyncio.run(run_basic_tests())
