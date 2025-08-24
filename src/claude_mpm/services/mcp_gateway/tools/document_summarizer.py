"""
Document Summarizer Tool
========================

Intelligent document processing tool for solving Claude Code memory issues.
Supports multiple file formats and summarization strategies.

Part of ISS-0037: Document Summarizer Tool - Intelligent Document Processing
"""

import hashlib
import mimetypes
import os
import re
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from claude_mpm.services.mcp_gateway.core.interfaces import (
    MCPToolDefinition,
    MCPToolInvocation,
    MCPToolResult,
)
from claude_mpm.services.mcp_gateway.tools.base_adapter import BaseToolAdapter


class LRUCache:
    """
    Simple LRU cache implementation for document summaries.

    WHY: We need a memory-efficient cache to avoid re-processing documents
    that are accessed repeatedly, which is common in Claude Code sessions.
    """

    def __init__(self, max_size: int = 100, max_memory_mb: int = 100):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of entries
            max_memory_mb: Maximum memory usage in MB
        """
        self.cache = OrderedDict()
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.current_memory = 0
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get item from cache, updating LRU order."""
        if key in self.cache:
            self.hits += 1
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        self.misses += 1
        return None

    def put(self, key: str, value: Dict[str, Any], size_bytes: int) -> None:
        """Add item to cache, evicting LRU items if necessary."""
        # Remove item if it already exists
        if key in self.cache:
            old_size = self.cache[key].get("size_bytes", 0)
            self.current_memory -= old_size
            del self.cache[key]

        # Evict items if necessary
        while (
            len(self.cache) >= self.max_size
            or self.current_memory + size_bytes > self.max_memory_bytes
        ):
            if not self.cache:
                break
            # Remove least recently used item
            removed_key, removed_value = self.cache.popitem(last=False)
            self.current_memory -= removed_value.get("size_bytes", 0)

        # Add new item
        value["size_bytes"] = size_bytes
        self.cache[key] = value
        self.current_memory += size_bytes

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        hit_rate = (
            self.hits / (self.hits + self.misses)
            if (self.hits + self.misses) > 0
            else 0
        )
        return {
            "size": len(self.cache),
            "memory_mb": self.current_memory / (1024 * 1024),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
        }


class DocumentSummarizerTool(BaseToolAdapter):
    """
    Document summarizer tool for intelligent document processing.

    WHY: Claude Code accumulates massive memory from reading full files,
    leading to context overflow. This tool reduces document size by 60%+
    while preserving essential information through intelligent summarization.

    DESIGN DECISIONS:
    - Use sentence boundary detection to preserve readability
    - Implement multiple summarization modes for different use cases
    - Cache summaries to avoid re-processing frequently accessed files
    - Support common file formats used in development
    """

    # File size limits (in bytes)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    CHUNK_SIZE = 50000  # Characters per chunk for large files

    # Token estimation (rough approximation)
    CHARS_PER_TOKEN = 4  # Approximate for Claude's tokenizer

    def __init__(self):
        """Initialize the document summarizer tool."""
        definition = MCPToolDefinition(
            name="document_summarizer",
            description="Intelligently summarizes documents to reduce memory usage while preserving key information",
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the document file",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["brief", "detailed", "key_points", "technical"],
                        "description": "Summarization mode",
                        "default": "brief",
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens in summary (optional)",
                        "minimum": 100,
                        "maximum": 10000,
                    },
                    "max_percentage": {
                        "type": "integer",
                        "description": "Maximum percentage of original to keep (1-100)",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 40,
                    },
                    "preserve_code": {
                        "type": "boolean",
                        "description": "Whether to preserve code blocks intact",
                        "default": True,
                    },
                    "use_cache": {
                        "type": "boolean",
                        "description": "Whether to use cached summaries",
                        "default": True,
                    },
                },
                "required": ["file_path"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "The summarized content",
                    },
                    "original_size": {
                        "type": "integer",
                        "description": "Original document size in bytes",
                    },
                    "summary_size": {
                        "type": "integer",
                        "description": "Summary size in bytes",
                    },
                    "reduction_percentage": {
                        "type": "number",
                        "description": "Percentage reduction achieved",
                    },
                    "token_estimate": {
                        "type": "object",
                        "properties": {
                            "original": {"type": "integer"},
                            "summary": {"type": "integer"},
                            "saved": {"type": "integer"},
                        },
                    },
                    "chunks_processed": {
                        "type": "integer",
                        "description": "Number of chunks processed for large files",
                    },
                    "cache_hit": {
                        "type": "boolean",
                        "description": "Whether summary was retrieved from cache",
                    },
                },
            },
            version="1.0.0",
            metadata={
                "category": "document_processing",
                "supported_formats": [
                    "txt",
                    "md",
                    "pdf",
                    "docx",
                    "json",
                    "yaml",
                    "csv",
                    "py",
                    "js",
                    "ts",
                    "java",
                    "cpp",
                    "c",
                    "h",
                    "hpp",
                ],
            },
        )
        super().__init__(definition)

        # Initialize cache
        self._cache = LRUCache(max_size=100, max_memory_mb=50)

        # Sentence boundary patterns
        self._sentence_endings = re.compile(r"[.!?]\s+")

        # Code block patterns for different formats
        self._code_patterns = {
            "markdown": re.compile(r"```[\s\S]*?```", re.MULTILINE),
            "inline": re.compile(r"`[^`]+`"),
            "indent": re.compile(r"^(    |\t).*$", re.MULTILINE),
        }

    def _get_file_hash(self, file_path: str) -> str:
        """Generate hash for file caching."""
        stat = os.stat(file_path)
        hash_input = f"{file_path}:{stat.st_size}:{stat.st_mtime}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        return len(text) // self.CHARS_PER_TOKEN

    def _validate_file(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate file for processing.

        Returns:
            Tuple of (is_valid, error_message)
        """
        path = Path(file_path)

        # Check if file exists
        if not path.exists():
            return False, f"File not found: {file_path}"

        # Check if it's a file (not directory)
        if not path.is_file():
            return False, f"Path is not a file: {file_path}"

        # Check file size
        file_size = path.stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            return (
                False,
                f"File too large: {file_size} bytes (max: {self.MAX_FILE_SIZE})",
            )

        # Check file extension
        extension = path.suffix.lower().lstrip(".")
        supported = self._definition.metadata.get("supported_formats", [])
        if extension and extension not in supported:
            # Try to detect by mime type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type or not mime_type.startswith("text/"):
                return False, f"Unsupported file format: {extension}"

        return True, None

    def _read_file(self, file_path: str) -> str:
        """
        Read file content with appropriate encoding.

        Args:
            file_path: Path to file

        Returns:
            File content as string
        """
        path = Path(file_path)

        # Try different encodings
        encodings = ["utf-8", "latin-1", "cp1252"]

        for encoding in encodings:
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue

        # If all fail, read as binary and decode with errors='ignore'
        with open(file_path, "rb") as f:
            content = f.read()
            return content.decode("utf-8", errors="ignore")

    def _extract_code_blocks(self, text: str) -> Tuple[List[str], str]:
        """
        Extract code blocks from text for preservation.

        Returns:
            Tuple of (code_blocks, text_without_code)
        """
        code_blocks = []
        placeholder_template = "[[CODE_BLOCK_{}]]"

        # Extract markdown code blocks
        for match in self._code_patterns["markdown"].finditer(text):
            code_blocks.append(match.group(0))
            text = text.replace(
                match.group(0), placeholder_template.format(len(code_blocks) - 1)
            )

        return code_blocks, text

    def _restore_code_blocks(self, text: str, code_blocks: List[str]) -> str:
        """Restore code blocks to summarized text."""
        for i, block in enumerate(code_blocks):
            placeholder = f"[[CODE_BLOCK_{i}]]"
            text = text.replace(placeholder, block)
        return text

    def _truncate_at_sentence(self, text: str, max_chars: int) -> str:
        """
        Truncate text at sentence boundary.

        WHY: Truncating mid-sentence makes summaries harder to read and
        can lose important context. Sentence boundaries preserve meaning.
        """
        if len(text) <= max_chars:
            return text

        # Find sentence boundaries
        sentences = self._sentence_endings.split(text)

        result = []
        current_length = 0

        for i, sentence in enumerate(sentences):
            # Add sentence ending back if not last sentence
            if i < len(sentences) - 1:
                sentence += ". "

            if current_length + len(sentence) <= max_chars:
                result.append(sentence)
                current_length += len(sentence)
            else:
                # Add partial sentence if we haven't added anything yet
                if not result and sentence:
                    result.append(sentence[: max_chars - 3] + "...")
                break

        return "".join(result)

    def _summarize_brief(self, text: str, max_chars: int) -> str:
        """
        Brief summarization - first and last portions.

        WHY: For quick overview, showing beginning and end gives context
        about what the document covers and its conclusions.
        """
        if len(text) <= max_chars:
            return text

        # Split available space between beginning and end
        half_chars = max_chars // 2 - 20  # Reserve space for separator

        beginning = self._truncate_at_sentence(text, half_chars)
        ending = self._truncate_at_sentence(text[-half_chars * 2 :], half_chars)

        return f"{beginning}\n\n[... content omitted for brevity ...]\n\n{ending}"

    def _summarize_detailed(self, text: str, max_chars: int) -> str:
        """
        Detailed summarization - extract key paragraphs.

        WHY: For technical documents, we want to preserve more structure
        and include middle sections that might contain important details.
        """
        if len(text) <= max_chars:
            return text

        # Split into paragraphs
        paragraphs = text.split("\n\n")

        # Calculate importance scores (based on length and position)
        scored_paragraphs = []
        for i, para in enumerate(paragraphs):
            # Skip empty paragraphs
            if not para.strip():
                continue

            # Score based on position (beginning and end are important)
            position_score = 1.0
            if i < 3:  # First 3 paragraphs
                position_score = 2.0
            elif i >= len(paragraphs) - 3:  # Last 3 paragraphs
                position_score = 1.5

            # Score based on content indicators
            content_score = 1.0
            if any(
                keyword in para.lower()
                for keyword in ["summary", "conclusion", "important", "note", "warning"]
            ):
                content_score = 1.5

            score = position_score * content_score * (1 + len(para) / 1000)
            scored_paragraphs.append((score, i, para))

        # Sort by score and select top paragraphs
        scored_paragraphs.sort(reverse=True)

        selected = []
        current_length = 0

        for score, original_index, para in scored_paragraphs:
            truncated_para = self._truncate_at_sentence(
                para, max_chars - current_length
            )
            if current_length + len(truncated_para) <= max_chars:
                selected.append((original_index, truncated_para))
                current_length += len(truncated_para) + 2  # Account for newlines

            if current_length >= max_chars * 0.9:  # Stop at 90% to leave some buffer
                break

        # Sort selected paragraphs by original order
        selected.sort()

        return "\n\n".join(para for _, para in selected)

    def _summarize_key_points(self, text: str, max_chars: int) -> str:
        """
        Extract key points and bullet points.

        WHY: Many documents have lists, bullet points, or numbered items
        that contain the most important information in condensed form.
        """
        if len(text) <= max_chars:
            return text

        lines = text.split("\n")
        key_lines = []

        # Patterns for identifying key points
        list_patterns = [
            re.compile(r"^\s*[-*•]\s+"),  # Bullet points
            re.compile(r"^\s*\d+[.)]\s+"),  # Numbered lists
            re.compile(r"^\s*[A-Z][.)]\s+"),  # Letter lists
            re.compile(r"^#+\s+"),  # Markdown headers
            re.compile(r"^[A-Z][^.!?]*:"),  # Definition lists
        ]

        # Extract lines that match key point patterns
        for line in lines:
            if any(pattern.match(line) for pattern in list_patterns):
                key_lines.append(line)

        # If we found key points, use them
        if key_lines:
            result = "\n".join(key_lines)
            if len(result) <= max_chars:
                return result
            return self._truncate_at_sentence(result, max_chars)

        # Fallback to brief summary if no key points found
        return self._summarize_brief(text, max_chars)

    def _summarize_technical(
        self, text: str, max_chars: int, preserve_code: bool
    ) -> str:
        """
        Technical summarization - preserve code and technical details.

        WHY: For code files and technical documentation, we need to
        preserve function signatures, class definitions, and important code.
        """
        if len(text) <= max_chars:
            return text

        # Extract and preserve code blocks if requested
        code_blocks = []
        text_without_code = text

        if preserve_code:
            code_blocks, text_without_code = self._extract_code_blocks(text)

        # Extract technical patterns
        tech_patterns = [
            re.compile(
                r"^(class|def|function|interface|struct)\s+\w+.*$", re.MULTILINE
            ),  # Definitions
            re.compile(
                r"^(import|from|require|include|using)\s+.*$", re.MULTILINE
            ),  # Imports
            re.compile(r"^\s*@\w+.*$", re.MULTILINE),  # Decorators/Annotations
            re.compile(
                r"^(public|private|protected|static).*\{?$", re.MULTILINE
            ),  # Method signatures
        ]

        important_lines = []
        for pattern in tech_patterns:
            important_lines.extend(pattern.findall(text_without_code))

        # Build technical summary
        result_parts = []

        # Add imports/includes first
        imports = [
            line
            for line in important_lines
            if any(
                keyword in line
                for keyword in ["import", "from", "require", "include", "using"]
            )
        ]
        if imports:
            result_parts.append("# Imports/Dependencies\n" + "\n".join(imports[:10]))

        # Add class/function definitions
        definitions = [
            line
            for line in important_lines
            if any(
                keyword in line
                for keyword in ["class", "def", "function", "interface", "struct"]
            )
        ]
        if definitions:
            result_parts.append("# Key Definitions\n" + "\n".join(definitions[:20]))

        # Add some code blocks if space allows
        if preserve_code and code_blocks:
            result_parts.append("# Code Samples")
            for _i, block in enumerate(code_blocks[:3]):  # Limit to first 3 blocks
                if len("\n".join(result_parts)) + len(block) < max_chars * 0.8:
                    result_parts.append(block)

        result = "\n\n".join(result_parts)

        # If still too long, truncate
        if len(result) > max_chars:
            result = self._truncate_at_sentence(result, max_chars)

        return result

    def _process_chunks(
        self, text: str, mode: str, max_chars_per_chunk: int, preserve_code: bool
    ) -> str:
        """
        Process large documents in chunks.

        WHY: Very large documents need to be processed in chunks to
        avoid memory issues and maintain performance.
        """
        chunks = []
        chunk_size = self.CHUNK_SIZE

        for i in range(0, len(text), chunk_size):
            chunk = text[i : i + chunk_size]

            # Summarize chunk based on mode
            if mode == "brief":
                summarized = self._summarize_brief(chunk, max_chars_per_chunk)
            elif mode == "detailed":
                summarized = self._summarize_detailed(chunk, max_chars_per_chunk)
            elif mode == "key_points":
                summarized = self._summarize_key_points(chunk, max_chars_per_chunk)
            elif mode == "technical":
                summarized = self._summarize_technical(
                    chunk, max_chars_per_chunk, preserve_code
                )
            else:
                summarized = self._summarize_brief(chunk, max_chars_per_chunk)

            chunks.append(summarized)

        return "\n\n[--- Next Section ---]\n\n".join(chunks)

    async def invoke(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """
        Invoke the document summarizer tool.

        Args:
            invocation: Tool invocation request

        Returns:
            Tool execution result with summary
        """
        start_time = datetime.now()

        try:
            # Get parameters
            file_path = invocation.parameters["file_path"]
            mode = invocation.parameters.get("mode", "brief")
            max_tokens = invocation.parameters.get("max_tokens")
            max_percentage = invocation.parameters.get("max_percentage", 40)
            preserve_code = invocation.parameters.get("preserve_code", True)
            use_cache = invocation.parameters.get("use_cache", True)

            # Validate file
            is_valid, error_msg = self._validate_file(file_path)
            if not is_valid:
                raise ValueError(error_msg)

            # Check cache if enabled
            cache_hit = False
            if use_cache:
                cache_key = f"{self._get_file_hash(file_path)}:{mode}:{max_percentage}"
                cached_result = self._cache.get(cache_key)
                if cached_result:
                    cache_hit = True
                    execution_time = (datetime.now() - start_time).total_seconds()
                    self._update_metrics(True, execution_time)

                    return MCPToolResult(
                        success=True,
                        data={
                            **cached_result,
                            "cache_hit": True,
                            "cache_stats": self._cache.get_stats(),
                        },
                        execution_time=execution_time,
                        metadata={
                            "tool": "document_summarizer",
                            "mode": mode,
                            "cached": True,
                        },
                    )

            # Read file content
            content = self._read_file(file_path)
            original_size = len(content)

            # Calculate target size
            if max_tokens:
                max_chars = max_tokens * self.CHARS_PER_TOKEN
            else:
                max_chars = int(original_size * (max_percentage / 100))

            # Process based on file size
            chunks_processed = 1
            if original_size > self.CHUNK_SIZE:
                # Process in chunks for large files
                chunks_processed = (original_size // self.CHUNK_SIZE) + 1
                max_chars_per_chunk = max_chars // chunks_processed
                summary = self._process_chunks(
                    content, mode, max_chars_per_chunk, preserve_code
                )
            # Process entire file
            elif mode == "brief":
                summary = self._summarize_brief(content, max_chars)
            elif mode == "detailed":
                summary = self._summarize_detailed(content, max_chars)
            elif mode == "key_points":
                summary = self._summarize_key_points(content, max_chars)
            elif mode == "technical":
                summary = self._summarize_technical(content, max_chars, preserve_code)
            else:
                summary = self._summarize_brief(content, max_chars)

            # Calculate metrics
            summary_size = len(summary)
            reduction_percentage = (
                (original_size - summary_size) / original_size
            ) * 100

            # Token estimates
            original_tokens = self._estimate_tokens(content)
            summary_tokens = self._estimate_tokens(summary)
            saved_tokens = original_tokens - summary_tokens

            # Prepare result
            result = {
                "summary": summary,
                "original_size": original_size,
                "summary_size": summary_size,
                "reduction_percentage": round(reduction_percentage, 2),
                "token_estimate": {
                    "original": original_tokens,
                    "summary": summary_tokens,
                    "saved": saved_tokens,
                },
                "chunks_processed": chunks_processed,
                "cache_hit": cache_hit,
            }

            # Cache result if enabled
            if use_cache and not cache_hit:
                cache_key = f"{self._get_file_hash(file_path)}:{mode}:{max_percentage}"
                self._cache.put(cache_key, result.copy(), summary_size)

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Update metrics
            self._update_metrics(True, execution_time)

            # Add cache stats to result
            result["cache_stats"] = self._cache.get_stats()

            return MCPToolResult(
                success=True,
                data=result,
                execution_time=execution_time,
                metadata={
                    "tool": "document_summarizer",
                    "mode": mode,
                    "file_path": file_path,
                    "reduction_achieved": reduction_percentage >= 60,
                },
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_metrics(False, execution_time)
            self._metrics["last_error"] = str(e)

            self.log_error(f"Document summarizer failed: {e}")

            return MCPToolResult(
                success=False,
                error=f"Document summarizer failed: {e!s}",
                execution_time=execution_time,
                metadata={
                    "tool": "document_summarizer",
                    "error_type": type(e).__name__,
                },
            )

    async def initialize(self) -> bool:
        """
        Initialize the document summarizer tool.

        Returns:
            True if initialization successful
        """
        try:
            self.log_info("Initializing document summarizer tool")

            # Clear cache on initialization
            self._cache = LRUCache(max_size=100, max_memory_mb=50)

            self._initialized = True
            self.log_info("Document summarizer tool initialized successfully")
            return True

        except Exception as e:
            self.log_error(f"Failed to initialize document summarizer: {e}")
            return False

    async def shutdown(self) -> None:
        """
        Shutdown the document summarizer tool and clean up resources.
        """
        try:
            self.log_info("Shutting down document summarizer tool")

            # Log final cache stats
            cache_stats = self._cache.get_stats()
            self.log_info(f"Final cache stats: {cache_stats}")

            # Clear cache
            self._cache = None

            self._initialized = False
            self.log_info("Document summarizer tool shutdown complete")

        except Exception as e:
            self.log_error(f"Error during document summarizer shutdown: {e}")
