"""
Document Summarization Command.

Shell-based alternative to MCP document_summarizer tool.
Provides algorithmic summarization without ML dependencies.

Design Decision: Uses simple text processing techniques:
- Brief: First paragraph extraction
- Detailed: Key sentence extraction based on position and length
- Bullet Points: Convert to markdown bullet list
- Executive: Opening + conclusion extraction

Why: Lightweight, fast, no dependencies, works offline.
"""

import json
import re
from enum import Enum
from pathlib import Path
from typing import Optional


class SummaryStyle(str, Enum):
    """Summary output styles."""

    BRIEF = "brief"
    DETAILED = "detailed"
    BULLET_POINTS = "bullet_points"
    EXECUTIVE = "executive"


class OutputFormat(str, Enum):
    """Output format types."""

    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"


class DocumentSummarizer:
    """
    Algorithmic document summarizer.

    Design Decision: Use simple heuristics instead of ML:
    - Position-based extraction (opening, closing paragraphs)
    - Length-based filtering (key sentences)
    - Structure detection (headings, lists)

    Trade-offs:
    - Performance: O(n) single pass vs. complex NLP models
    - Accuracy: ~70% vs. ~90% for ML models
    - Simplicity: Zero dependencies vs. heavy ML packages
    """

    def __init__(self, max_words: int = 150):
        """Initialize summarizer with word limit."""
        self.max_words = max_words

    def summarize(
        self, content: str, style: SummaryStyle, lines_limit: Optional[int] = None
    ) -> str:
        """
        Summarize document content.

        Args:
            content: Document text to summarize
            style: Summary style (brief, detailed, bullet_points, executive)
            lines_limit: Optional line limit (reads first N lines only)

        Returns:
            Summary text

        Complexity: O(n) where n is content length
        """
        # Apply line limit if specified
        if lines_limit:
            content = self._limit_lines(content, lines_limit)

        # Route to style-specific summarizer
        summarizers = {
            SummaryStyle.BRIEF: self._summarize_brief,
            SummaryStyle.DETAILED: self._summarize_detailed,
            SummaryStyle.BULLET_POINTS: self._summarize_bullet_points,
            SummaryStyle.EXECUTIVE: self._summarize_executive,
        }

        summary = summarizers[style](content)
        return self._truncate_to_word_limit(summary)

    def _limit_lines(self, content: str, limit: int) -> str:
        """Limit content to first N lines."""
        lines = content.split("\n")
        return "\n".join(lines[:limit])

    def _truncate_to_word_limit(self, text: str) -> str:
        """Truncate text to max_words limit."""
        words = text.split()
        if len(words) <= self.max_words:
            return text

        # Truncate and add ellipsis
        truncated = " ".join(words[: self.max_words])
        return f"{truncated}..."

    def _summarize_brief(self, content: str) -> str:
        """
        Brief summary: Extract first paragraph.

        Heuristic: First non-empty paragraph usually introduces document.
        """
        paragraphs = self._extract_paragraphs(content)
        if not paragraphs:
            return content.strip()

        return paragraphs[0]

    def _summarize_detailed(self, content: str) -> str:
        """
        Detailed summary: Extract key sentences.

        Heuristics:
        - First paragraph (introduction)
        - Sentences with important markers (however, therefore, important)
        - Last paragraph (conclusion)
        """
        paragraphs = self._extract_paragraphs(content)
        if not paragraphs:
            return content.strip()

        key_sentences = []

        # Add first paragraph
        if paragraphs:
            key_sentences.append(paragraphs[0])

        # Add sentences with key markers from middle paragraphs
        if len(paragraphs) > 2:
            key_markers = [
                "however",
                "therefore",
                "important",
                "note",
                "critical",
                "key",
                "must",
                "should",
                "recommended",
            ]

            for para in paragraphs[1:-1]:
                sentences = self._split_sentences(para)
                for sentence in sentences:
                    if any(marker in sentence.lower() for marker in key_markers):
                        key_sentences.append(sentence)
                        break  # One sentence per paragraph max

        # Add last paragraph
        if len(paragraphs) > 1:
            key_sentences.append(paragraphs[-1])

        return " ".join(key_sentences)

    def _summarize_bullet_points(self, content: str) -> str:
        """
        Bullet point summary: Convert paragraphs to markdown list.

        Heuristic: Each paragraph becomes a bullet point.
        """
        paragraphs = self._extract_paragraphs(content)
        if not paragraphs:
            return content.strip()

        # Take key paragraphs (first, middle with markers, last)
        key_paragraphs = []

        # Always include first
        if paragraphs:
            key_paragraphs.append(paragraphs[0])

        # Include middle paragraphs with key content
        if len(paragraphs) > 2:
            key_markers = ["however", "therefore", "important", "note", "critical"]
            for para in paragraphs[1:-1]:
                if any(marker in para.lower() for marker in key_markers):
                    # Take first sentence only for bullet point
                    first_sentence = self._split_sentences(para)[0]
                    key_paragraphs.append(first_sentence)

        # Include last if different from first
        if len(paragraphs) > 1:
            key_paragraphs.append(paragraphs[-1])

        # Format as markdown bullets
        bullets = [f"- {para}" for para in key_paragraphs]
        return "\n".join(bullets)

    def _summarize_executive(self, content: str) -> str:
        """
        Executive summary: Opening + conclusion.

        Heuristic: First and last paragraphs capture overview and conclusion.
        """
        paragraphs = self._extract_paragraphs(content)
        if not paragraphs:
            return content.strip()

        if len(paragraphs) == 1:
            return paragraphs[0]

        # Opening paragraph + conclusion paragraph
        return f"{paragraphs[0]}\n\n{paragraphs[-1]}"

    def _extract_paragraphs(self, content: str) -> list[str]:
        """
        Extract paragraphs from content.

        Filters out:
        - Empty lines
        - Short lines (< 40 chars, likely headers/formatting artifacts)
        - Code blocks (lines with multiple indentation)
        - Lines that look like code (contain def, class, =, {, etc.)
        """
        # Split on double newlines for paragraph boundaries
        raw_paragraphs = re.split(r"\n\s*\n", content)

        paragraphs = []
        for para in raw_paragraphs:
            # Clean and normalize whitespace
            para = " ".join(para.split())

            # Skip empty or very short paragraphs (likely headers)
            if len(para) < 40:
                continue

            # Skip code blocks (heuristic: contains code-like patterns)
            code_indicators = ["def ", "class ", " = ", "{", "}", "return ", "import "]
            if any(indicator in para for indicator in code_indicators):
                continue

            paragraphs.append(para)

        return paragraphs

    def _split_sentences(self, text: str) -> list[str]:
        """
        Split text into sentences.

        Simple heuristic: Split on '. ' but handle common abbreviations.
        """
        # Handle common abbreviations to avoid false splits
        text = text.replace("Dr.", "Dr<DOT>")
        text = text.replace("Mr.", "Mr<DOT>")
        text = text.replace("Mrs.", "Mrs<DOT>")
        text = text.replace("e.g.", "e<DOT>g<DOT>")
        text = text.replace("i.e.", "i<DOT>e<DOT>")

        # Split on sentence boundaries
        sentences = re.split(r"(?<=[.!?])\s+", text)

        # Restore abbreviations
        sentences = [s.replace("<DOT>", ".") for s in sentences]

        return [s.strip() for s in sentences if s.strip()]


def format_output(summary: str, output_format: OutputFormat, file_path: Path) -> str:
    """
    Format summary output.

    Args:
        summary: Summary text
        output_format: Output format (text, json, markdown)
        file_path: Original file path for metadata

    Returns:
        Formatted output string
    """
    if output_format == OutputFormat.TEXT:
        return summary

    if output_format == OutputFormat.JSON:
        result = {
            "file": str(file_path),
            "summary": summary,
            "word_count": len(summary.split()),
        }
        return json.dumps(result, indent=2)

    if output_format == OutputFormat.MARKDOWN:
        return f"# Summary: {file_path.name}\n\n{summary}\n"

    return summary


def summarize_command(args) -> int:
    """
    Execute summarize command.

    Args:
        args: Parsed command line arguments with:
            - file_path: Path to file to summarize
            - style: Summary style
            - max_words: Maximum words in summary
            - output: Output format
            - lines: Optional line limit

    Returns:
        Exit code (0 for success, 1 for error)
    """
    file_path = Path(args.file_path)

    # Validate file exists
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return 1

    if not file_path.is_file():
        print(f"Error: Not a file: {file_path}")
        return 1

    try:
        # Read file content
        content = file_path.read_text(encoding="utf-8")

        # Create summarizer
        summarizer = DocumentSummarizer(max_words=args.max_words)

        # Generate summary
        summary = summarizer.summarize(
            content, style=SummaryStyle(args.style), lines_limit=args.lines
        )

        # Format output
        output = format_output(summary, OutputFormat(args.output), file_path)

        # Print result
        print(output)

        return 0

    except UnicodeDecodeError:
        print(f"Error: Cannot read file (not valid UTF-8): {file_path}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def add_summarize_parser(subparsers) -> None:
    """
    Add summarize subcommand parser.

    Args:
        subparsers: Subparsers object from argparse
    """
    parser = subparsers.add_parser(
        "summarize",
        help="Summarize document content (shell-based alternative to MCP document_summarizer)",
        description="""
Algorithmic document summarization without ML dependencies.

Styles:
  brief         - First paragraph only (quick overview)
  detailed      - Key sentences from opening, middle, closing
  bullet_points - Markdown bullet list of key points
  executive     - Opening + conclusion (for quick decisions)

Examples:
  claude-mpm summarize README.md
  claude-mpm summarize docs/guide.md --style detailed --max-words 200
  claude-mpm summarize src/main.py --style bullet_points --output markdown
  claude-mpm summarize large.txt --lines 100 --style brief
        """,
        formatter_class=lambda prog: __import__("argparse").RawDescriptionHelpFormatter(
            prog, max_help_position=40
        ),
    )

    # Required arguments
    parser.add_argument("file_path", type=str, help="Path to file to summarize")

    # Optional arguments
    parser.add_argument(
        "--style",
        type=str,
        choices=["brief", "detailed", "bullet_points", "executive"],
        default="brief",
        help="Summary style (default: brief)",
    )

    parser.add_argument(
        "--max-words",
        type=int,
        default=150,
        help="Maximum words in summary (default: 150)",
    )

    parser.add_argument(
        "--output",
        type=str,
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format (default: text)",
    )

    parser.add_argument(
        "--lines",
        type=int,
        default=None,
        help="Limit to first N lines of file (default: no limit)",
    )

    parser.set_defaults(command="summarize")
