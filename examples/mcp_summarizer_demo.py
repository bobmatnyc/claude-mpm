#!/usr/bin/env python3
"""
Demonstration of the MCP Document Summarizer Tool

This script shows how the summarize_document tool works with different
styles and content types.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.mcp_gateway.server.stdio_server import SimpleMCPServer


async def demo_summarizer():
    """Demonstrate the document summarizer capabilities."""

    server = SimpleMCPServer()

    # Sample documents for demonstration
    documents = {
        "Technical Documentation": """
        The Claude MPM framework provides a sophisticated multi-agent orchestration system
        designed to extend Claude Code's capabilities. The architecture follows a
        service-oriented design pattern with explicit interface contracts and dependency
        injection for maximum flexibility and maintainability.

        Key architectural components include:
        - Service Layer: Provides core functionality through well-defined interfaces
        - Agent System: Manages specialized agents for different tasks
        - Communication Layer: Handles real-time WebSocket and SocketIO connections
        - Infrastructure: Logging, monitoring, and error handling utilities

        The framework supports both synchronous and asynchronous operations, with
        comprehensive error handling and recovery mechanisms. Performance optimizations
        include lazy loading, multi-level caching, and connection pooling to ensure
        efficient resource utilization.

        Security features include input validation, path traversal prevention, and
        secure credential management. The system maintains backward compatibility while
        providing migration paths for legacy code.
        """,
        "Research Paper Abstract": """
        Recent advances in large language models have demonstrated remarkable capabilities
        in understanding and generating human-like text. This paper presents a novel
        approach to document summarization using adaptive compression techniques that
        preserve semantic meaning while reducing token consumption by up to 60%.

        Our methodology employs a multi-stage pipeline consisting of sentence importance
        scoring, structural analysis, and context-aware extraction. Experimental results
        on standard benchmarks show significant improvements over baseline methods in
        both ROUGE scores and human evaluation metrics.

        The proposed system achieves state-of-the-art performance on the CNN/DailyMail
        dataset with a ROUGE-L score of 45.2, while maintaining computational efficiency
        suitable for real-time applications. Furthermore, our approach demonstrates
        strong generalization capabilities across different domains and languages.

        We conclude that adaptive summarization techniques offer a promising direction
        for managing context limitations in modern language models. Future work will
        explore integration with retrieval-augmented generation systems.
        """,
        "Meeting Notes": """
        Project Status Meeting - Q4 2024
        Date: December 15, 2024
        Attendees: Engineering Team, Product Management, QA

        Agenda Items Discussed:
        • Feature development progress: On track for January release
        • Bug fixes completed: 45 critical issues resolved
        • Performance improvements: 30% reduction in response time
        • Customer feedback integration: Implemented top 5 requested features
        • Testing status: 85% code coverage achieved

        Action Items:
        - John: Complete API documentation by December 20
        - Sarah: Finalize performance benchmarks by December 18
        - Mike: Review and approve security audit findings
        - Team: Prepare for sprint planning session next week

        Next Steps:
        The team will focus on final polish and bug fixes before the holiday break.
        All critical path items must be completed by December 22. Regular daily
        standups will continue through the release cycle.

        Risk Assessment:
        One potential blocker identified in third-party integration. Mitigation plan
        in place with fallback option if needed. Overall project health is green.
        """,
    }

    print("=" * 80)
    print("MCP DOCUMENT SUMMARIZER DEMONSTRATION")
    print("=" * 80)

    for doc_title, content in documents.items():
        print(f"\n{'=' * 80}")
        print(f"DOCUMENT: {doc_title}")
        print(f"Original length: {len(content.split())} words")
        print("=" * 80)

        # Test each summarization style
        styles = {"brief": 50, "detailed": 100, "bullet_points": 75, "executive": 100}

        for style, max_words in styles.items():
            print(f"\n{style.upper()} SUMMARY ({max_words} words max):")
            print("-" * 40)

            result = await server._summarize_content(
                content=content, style=style, max_length=max_words
            )

            print(result)
            print(
                f"\n[Summary: {len(result.split())} words | "
                f"Reduction: {round(100 - (len(result.split()) / len(content.split()) * 100), 1)}%]"
            )

    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)

    # Show how it would be called via MCP protocol
    print("\n" + "=" * 80)
    print("MCP PROTOCOL EXAMPLE")
    print("=" * 80)
    print("\nTo use via MCP protocol, send:")
    print(
        json.dumps(
            {
                "tool": "summarize_document",
                "arguments": {
                    "content": "Your document text here...",
                    "style": "brief",  # or "detailed", "bullet_points", "executive"
                    "max_length": 150,  # maximum words in summary
                },
            },
            indent=2,
        )
    )

    print("\nThe tool will return a summary that:")
    print("• Preserves key information")
    print("• Respects the word limit")
    print("• Maintains readability")
    print("• Reduces memory usage by 50-70%")


if __name__ == "__main__":
    asyncio.run(demo_summarizer())
