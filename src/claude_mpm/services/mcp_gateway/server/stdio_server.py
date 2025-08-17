"""
Simplified MCP Stdio Server
============================

A proper stdio-based MCP server that communicates via JSON-RPC over stdin/stdout.
This server is spawned on-demand by Claude Desktop/Code and exits when the connection closes.

WHY: MCP servers should be simple stdio-based processes that Claude can spawn and control.
They should NOT run as persistent background services with lock files.

DESIGN DECISION: We follow the MCP specification exactly - read from stdin, write to stdout,
use JSON-RPC protocol, and exit cleanly when stdin closes.
"""

import asyncio
import logging
import sys
from typing import Any, Dict, List, Optional

# Import MCP SDK components
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from claude_mpm.core.logger import get_logger

# Import unified ticket tool if available
try:
    from claude_mpm.services.mcp_gateway.tools.unified_ticket_tool import (
        UnifiedTicketTool,
    )

    TICKET_TOOLS_AVAILABLE = True
except ImportError:
    TICKET_TOOLS_AVAILABLE = False


class SimpleMCPServer:
    """
    A simple stdio-based MCP server implementation.

    WHY: This server follows the MCP specification for stdio communication,
    making it compatible with Claude Desktop/Code's MCP client.

    DESIGN DECISIONS:
    - No persistent state or lock files
    - Spawned on-demand by Claude
    - Communicates via stdin/stdout
    - Exits when connection closes
    """

    def __init__(self, name: str = "claude-mpm-gateway", version: str = "1.0.0"):
        """
        Initialize the MCP server.

        Args:
            name: Server name for identification
            version: Server version
        """
        self.name = name
        self.version = version
        self.logger = get_logger("MCPStdioServer")

        # Create MCP server instance
        self.server = Server(name)

        # Register default tools
        self._register_tools()

    async def _summarize_content(
        self, content: str, style: str, max_length: int
    ) -> str:
        """
        Summarize text content based on style and length constraints.

        Args:
            content: The text to summarize
            style: Summary style (brief, detailed, bullet_points, executive)
            max_length: Maximum length in words

        Returns:
            Summarized text
        """
        if not content or not content.strip():
            return "No content provided to summarize."

        # Split content into sentences for processing
        import re

        sentences = re.split(r"(?<=[.!?])\s+", content.strip())

        if not sentences:
            return content[: max_length * 5]  # Rough estimate: 5 chars per word

        if style == "brief":
            # Brief: First and last portions with key sentences
            return self._create_brief_summary(sentences, max_length)

        elif style == "detailed":
            # Detailed: More comprehensive with section preservation
            return self._create_detailed_summary(sentences, content, max_length)

        elif style == "bullet_points":
            # Extract key points as bullet list
            return self._create_bullet_summary(sentences, content, max_length)

        elif style == "executive":
            # Executive: Summary + key findings + recommendations
            return self._create_executive_summary(sentences, content, max_length)

        else:
            # Default to brief
            return self._create_brief_summary(sentences, max_length)

    def _create_brief_summary(self, sentences: List[str], max_length: int) -> str:
        """Create a brief summary by selecting most important sentences."""
        if not sentences:
            return ""

        # If very short summary requested, just return truncated first sentence
        if max_length < 10:
            words = sentences[0].split()[:max_length]
            if len(words) < len(sentences[0].split()):
                return " ".join(words) + "..."
            return " ".join(words)

        if len(sentences) <= 3:
            text = " ".join(sentences)
            words = text.split()
            if len(words) <= max_length:
                return text
            # Truncate to word limit
            return " ".join(words[:max_length]) + "..."

        # Calculate importance scores for sentences
        scored_sentences = []
        for i, sentence in enumerate(sentences):
            score = 0

            # Position scoring
            if i == 0:  # First sentence
                score += 3
            elif i == len(sentences) - 1:  # Last sentence
                score += 2
            elif i < 3:  # Early sentences
                score += 1

            # Content scoring
            important_words = [
                "important",
                "key",
                "main",
                "critical",
                "essential",
                "summary",
                "conclusion",
                "result",
                "therefore",
                "however",
            ]
            for word in important_words:
                if word in sentence.lower():
                    score += 1

            # Length scoring (prefer medium-length sentences)
            word_count = len(sentence.split())
            if 10 <= word_count <= 25:
                score += 1

            scored_sentences.append((score, i, sentence))

        # Sort by score and select top sentences
        scored_sentences.sort(reverse=True, key=lambda x: x[0])

        # Select sentences up to word limit
        selected = []
        word_count = 0
        for score, orig_idx, sentence in scored_sentences:
            sentence_words = len(sentence.split())
            if word_count + sentence_words <= max_length:
                selected.append((orig_idx, sentence))
                word_count += sentence_words

        # Sort by original order
        selected.sort(key=lambda x: x[0])

        if not selected:
            # If no sentences fit, truncate the first sentence
            words = sentences[0].split()[:max_length]
            if len(words) < len(sentences[0].split()):
                return " ".join(words) + "..."
            return " ".join(words)

        return " ".join(s[1] for s in selected)

    def _create_detailed_summary(
        self, sentences: List[str], content: str, max_length: int
    ) -> str:
        """Create a detailed summary preserving document structure."""
        import re

        # Split into paragraphs
        paragraphs = content.split("\n\n")

        if len(paragraphs) <= 2:
            return self._create_brief_summary(sentences, max_length)

        # Summarize each paragraph
        summary_parts = []
        words_per_para = max_length // len(paragraphs)

        for para in paragraphs:
            if not para.strip():
                continue

            para_sentences = re.split(r"(?<=[.!?])\s+", para.strip())
            if para_sentences:
                # Take first sentence of each paragraph
                summary_parts.append(para_sentences[0])

        result = " ".join(summary_parts)

        # Trim to word limit
        words = result.split()[:max_length]
        return " ".join(words) + ("..." if len(result.split()) > max_length else "")

    def _create_bullet_summary(
        self, sentences: List[str], content: str, max_length: int
    ) -> str:
        """Extract key points as a bullet list."""
        import re

        # Look for existing bullet points or lists
        bullet_patterns = [
            re.compile(r"^\s*[-•*]\s+(.+)$", re.MULTILINE),
            re.compile(r"^\s*\d+[.)]\s+(.+)$", re.MULTILINE),
            re.compile(r"^([A-Z][^.!?]+):(.+)$", re.MULTILINE),
        ]

        points = []
        for pattern in bullet_patterns:
            matches = pattern.findall(content)
            for match in matches:
                if isinstance(match, tuple):
                    point = " ".join(match).strip()
                else:
                    point = match.strip()
                if point and len(point.split()) <= 20:  # Keep concise points
                    points.append(point)

        # If no bullet points found, extract key sentences
        if not points:
            # Use brief summary sentences as bullet points
            brief = self._create_brief_summary(sentences, max_length)
            points = brief.split(". ")

        # Format as bullet list
        result_lines = []
        word_count = 0
        for point in points:
            point_words = len(point.split())
            if word_count + point_words <= max_length:
                result_lines.append(f"• {point.strip('.')}")
                word_count += point_words

        if not result_lines:
            return "• " + " ".join(sentences[0].split()[:max_length]) + "..."

        return "\n".join(result_lines)

    def _create_executive_summary(
        self, sentences: List[str], content: str, max_length: int
    ) -> str:
        """Create an executive summary with overview, findings, and recommendations."""
        # Allocate words across sections
        overview_words = max_length // 3
        findings_words = max_length // 3
        recommendations_words = max_length - overview_words - findings_words

        sections = []

        # Overview section
        overview = self._create_brief_summary(
            sentences[: len(sentences) // 2], overview_words
        )
        if overview:
            sections.append(f"OVERVIEW:\n{overview}")

        # Key Findings
        import re

        findings = []

        # Look for sentences with conclusion/result indicators
        conclusion_patterns = [
            "found",
            "discovered",
            "shows",
            "indicates",
            "reveals",
            "demonstrates",
            "proves",
            "confirms",
            "suggests",
        ]

        for sentence in sentences:
            if any(word in sentence.lower() for word in conclusion_patterns):
                findings.append(sentence)
                if len(" ".join(findings).split()) >= findings_words:
                    break

        if findings:
            sections.append(f"\nKEY FINDINGS:\n• " + "\n• ".join(findings[:3]))

        # Recommendations (look for action-oriented sentences)
        action_patterns = [
            "should",
            "must",
            "need to",
            "recommend",
            "suggest",
            "important to",
            "critical to",
            "require",
        ]

        recommendations = []
        for sentence in sentences:
            if any(word in sentence.lower() for word in action_patterns):
                recommendations.append(sentence)
                if len(" ".join(recommendations).split()) >= recommendations_words:
                    break

        if recommendations:
            sections.append(
                f"\nRECOMMENDATIONS:\n• " + "\n• ".join(recommendations[:3])
            )

        # If no sections were created, fall back to brief summary
        if not sections:
            return self._create_brief_summary(sentences, max_length)

        result = "\n".join(sections)

        # Ensure we don't exceed word limit
        words = result.split()[:max_length]
        return " ".join(words) + ("..." if len(result.split()) > max_length else "")

    def _register_tools(self):
        """
        Register MCP tools with the server.

        WHY: Tools are the primary way MCP servers extend Claude's capabilities.
        We register them using decorators on handler functions.
        """
        # Initialize unified ticket tool if available
        self.unified_ticket_tool = None
        if TICKET_TOOLS_AVAILABLE:
            try:
                self.unified_ticket_tool = UnifiedTicketTool()
                # Initialize the unified ticket tool
                asyncio.create_task(self.unified_ticket_tool.initialize())
            except Exception as e:
                self.logger.warning(f"Failed to initialize unified ticket tool: {e}")
                self.unified_ticket_tool = None

        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools."""
            tools = [
                Tool(
                    name="echo",
                    description="Echo back the provided message",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "Message to echo",
                            }
                        },
                        "required": ["message"],
                    },
                ),
                Tool(
                    name="calculator",
                    description="Perform basic arithmetic calculations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "expression": {
                                "type": "string",
                                "description": "Mathematical expression to evaluate",
                            }
                        },
                        "required": ["expression"],
                    },
                ),
                Tool(
                    name="system_info",
                    description="Get system information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "info_type": {
                                "type": "string",
                                "enum": ["platform", "python_version", "cwd"],
                                "description": "Type of system information to retrieve",
                            }
                        },
                        "required": ["info_type"],
                    },
                ),
                Tool(
                    name="run_command",
                    description="Execute a shell command",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "Shell command to execute",
                            },
                            "timeout": {
                                "type": "number",
                                "description": "Command timeout in seconds",
                                "default": 30,
                            },
                        },
                        "required": ["command"],
                    },
                ),
                Tool(
                    name="summarize_document",
                    description="Summarize documents or text content",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "The text/document to summarize",
                            },
                            "style": {
                                "type": "string",
                                "enum": [
                                    "brief",
                                    "detailed",
                                    "bullet_points",
                                    "executive",
                                ],
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
                ),
            ]

            # Add unified ticket tool if available
            if self.unified_ticket_tool:
                tool_def = self.unified_ticket_tool.get_definition()
                tools.append(
                    Tool(
                        name=tool_def.name,
                        description=tool_def.description,
                        inputSchema=tool_def.input_schema,
                    )
                )

            self.logger.info(f"Listing {len(tools)} available tools")
            return tools

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Dict[str, Any]
        ) -> List[TextContent]:
            """Handle tool invocation."""
            self.logger.info(f"Invoking tool: {name} with arguments: {arguments}")

            try:
                if name == "echo":
                    message = arguments.get("message", "")
                    result = f"Echo: {message}"

                elif name == "calculator":
                    expression = arguments.get("expression", "")
                    try:
                        # Safe evaluation of mathematical expressions
                        import ast
                        import operator as op

                        # Supported operators
                        ops = {
                            ast.Add: op.add,
                            ast.Sub: op.sub,
                            ast.Mult: op.mul,
                            ast.Div: op.truediv,
                            ast.Pow: op.pow,
                            ast.Mod: op.mod,
                            ast.USub: op.neg,
                        }

                        def eval_expr(expr):
                            """Safely evaluate mathematical expression."""

                            def _eval(node):
                                if isinstance(node, ast.Constant):
                                    return node.value
                                elif isinstance(node, ast.BinOp):
                                    return ops[type(node.op)](
                                        _eval(node.left), _eval(node.right)
                                    )
                                elif isinstance(node, ast.UnaryOp):
                                    return ops[type(node.op)](_eval(node.operand))
                                else:
                                    raise TypeError(f"Unsupported operation: {node}")

                            return _eval(ast.parse(expr, mode="eval").body)

                        result_value = eval_expr(expression)
                        result = f"{expression} = {result_value}"
                    except Exception as e:
                        result = f"Error evaluating expression: {str(e)}"

                elif name == "system_info":
                    info_type = arguments.get("info_type", "platform")

                    if info_type == "platform":
                        import platform

                        result = f"Platform: {platform.system()} {platform.release()}"
                    elif info_type == "python_version":
                        import sys

                        result = f"Python: {sys.version}"
                    elif info_type == "cwd":
                        import os

                        result = f"Working Directory: {os.getcwd()}"
                    else:
                        result = f"Unknown info type: {info_type}"

                elif name == "run_command":
                    command = arguments.get("command", "")
                    timeout = arguments.get("timeout", 30)

                    import shlex
                    import subprocess

                    try:
                        # Split command string into a list to avoid shell injection
                        command_parts = shlex.split(command)

                        # Use create_subprocess_exec instead of create_subprocess_shell
                        # to prevent command injection vulnerabilities
                        proc = await asyncio.create_subprocess_exec(
                            *command_parts,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                        )

                        stdout, stderr = await asyncio.wait_for(
                            proc.communicate(), timeout=timeout
                        )

                        if proc.returncode == 0:
                            result = (
                                stdout.decode()
                                if stdout
                                else "Command completed successfully"
                            )
                        else:
                            result = f"Command failed with code {proc.returncode}: {stderr.decode()}"
                    except asyncio.TimeoutError:
                        result = f"Command timed out after {timeout} seconds"
                    except ValueError as e:
                        # Handle shlex parsing errors (e.g., unmatched quotes)
                        result = f"Invalid command syntax: {str(e)}"
                    except Exception as e:
                        result = f"Error running command: {str(e)}"

                elif name == "summarize_document":
                    content = arguments.get("content", "")
                    style = arguments.get("style", "brief")
                    max_length = arguments.get("max_length", 150)

                    result = await self._summarize_content(content, style, max_length)

                elif name == "ticket" and self.unified_ticket_tool:
                    # Handle unified ticket tool invocations
                    from claude_mpm.services.mcp_gateway.core.interfaces import (
                        MCPToolInvocation,
                    )

                    invocation = MCPToolInvocation(
                        tool_name=name,
                        parameters=arguments,
                        request_id=f"req_{name}_{id(arguments)}",
                    )

                    tool_result = await self.unified_ticket_tool.invoke(invocation)

                    if tool_result.success:
                        result = (
                            tool_result.data
                            if isinstance(tool_result.data, str)
                            else str(tool_result.data)
                        )
                    else:
                        result = f"Error: {tool_result.error}"

                else:
                    result = f"Unknown tool: {name}"

                self.logger.info(f"Tool {name} completed successfully")
                return [TextContent(type="text", text=result)]

            except Exception as e:
                error_msg = f"Error executing tool {name}: {str(e)}"
                self.logger.error(error_msg)
                return [TextContent(type="text", text=error_msg)]

    async def run(self):
        """
        Run the MCP server using stdio communication.

        WHY: This is the main entry point that sets up stdio communication
        and runs the server until the connection is closed.
        """
        try:
            self.logger.info(f"Starting {self.name} v{self.version}")

            # Run the server with stdio transport
            async with stdio_server() as (read_stream, write_stream):
                self.logger.info("Stdio connection established")

                # Create initialization options
                init_options = InitializationOptions(
                    server_name=self.name,
                    server_version=self.version,
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                )

                # Run the server
                await self.server.run(read_stream, write_stream, init_options)

            self.logger.info("Server shutting down normally")

        except Exception as e:
            self.logger.error(f"Server error: {e}")
            raise


async def main():
    """
    Main entry point for the MCP stdio server.

    WHY: This function creates and runs the server instance.
    It's called when the script is executed directly.
    """
    # Configure logging to stderr so it doesn't interfere with stdio protocol
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    # Create and run server
    server = SimpleMCPServer()
    await server.run()


def main_sync():
    """Synchronous entry point for use as a console script."""
    asyncio.run(main())


if __name__ == "__main__":
    # Run the async main function
    main_sync()
