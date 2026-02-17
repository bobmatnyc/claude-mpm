"""Notion integration utilities - markdown to Notion blocks conversion."""

import re
from typing import Any


def md_to_notion_blocks(markdown: str) -> list[dict[str, Any]]:
    """Convert markdown to Notion block array.

    Handles: headers, paragraphs, lists, code blocks, quotes.

    Args:
        markdown: Markdown content string

    Returns:
        List of Notion block objects
    """
    blocks: list[dict[str, Any]] = []
    lines = markdown.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Skip empty lines at start
        if not line.strip() and not blocks:
            i += 1
            continue

        # Code block
        if line.strip().startswith("```"):
            block, i = _parse_code_block(lines, i)
            if block:
                blocks.append(block)
            continue

        # Headers
        if line.startswith("# "):
            blocks.append(_text_block("heading_1", line[2:].strip()))
            i += 1
            continue
        if line.startswith("## "):
            blocks.append(_text_block("heading_2", line[3:].strip()))
            i += 1
            continue
        if line.startswith("### "):
            blocks.append(_text_block("heading_3", line[4:].strip()))
            i += 1
            continue

        # Bullet list
        if line.strip().startswith(("- ", "* ")):
            list_items, i = _parse_list(lines, i, bullet=True)
            blocks.extend(list_items)
            continue

        # Numbered list
        if re.match(r"^\d+\.\s", line.strip()):
            list_items, i = _parse_list(lines, i, bullet=False)
            blocks.extend(list_items)
            continue

        # Quote
        if line.strip().startswith("> "):
            quote_block, i = _parse_quote(lines, i)
            if quote_block:
                blocks.append(quote_block)
            continue

        # Paragraph
        if line.strip():
            para_text, i = _parse_paragraph(lines, i)
            if para_text.strip():
                blocks.append(_text_block("paragraph", para_text))
            continue

        i += 1

    return blocks


def _text_block(block_type: str, text: str) -> dict[str, Any]:
    """Create a text-based block."""
    return {
        "type": block_type,
        block_type: {
            "rich_text": _rich_text(text),
        },
    }


def _rich_text(text: str) -> list[dict[str, Any]]:
    """Convert text to Notion rich_text array with inline formatting."""
    if not text:
        return []

    segments: list[dict[str, Any]] = []
    pattern = r"(\*\*.*?\*\*|\*.*?\*|`.*?`|\[.*?\]\(.*?\))"
    parts = re.split(pattern, text)

    for part in parts:
        if not part:
            continue

        # Bold
        if part.startswith("**") and part.endswith("**"):
            segments.append(
                {
                    "type": "text",
                    "text": {"content": part[2:-2]},
                    "annotations": {"bold": True},
                }
            )
        # Italic
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            segments.append(
                {
                    "type": "text",
                    "text": {"content": part[1:-1]},
                    "annotations": {"italic": True},
                }
            )
        # Code
        elif part.startswith("`") and part.endswith("`"):
            segments.append(
                {
                    "type": "text",
                    "text": {"content": part[1:-1]},
                    "annotations": {"code": True},
                }
            )
        # Link
        elif part.startswith("[") and "](" in part and part.endswith(")"):
            match = re.match(r"\[(.*?)\]\((.*?)\)", part)
            if match:
                segments.append(
                    {
                        "type": "text",
                        "text": {
                            "content": match.group(1),
                            "link": {"url": match.group(2)},
                        },
                    }
                )
        # Plain text
        else:
            segments.append(
                {
                    "type": "text",
                    "text": {"content": part},
                }
            )

    return segments if segments else [{"type": "text", "text": {"content": text}}]


def _parse_code_block(
    lines: list[str], start_idx: int
) -> tuple[dict[str, Any] | None, int]:
    """Parse a fenced code block."""
    first_line = lines[start_idx].strip()
    if not first_line.startswith("```"):
        return None, start_idx + 1

    language = first_line[3:].strip() or "plain text"

    code_lines = []
    i = start_idx + 1
    while i < len(lines):
        if lines[i].strip() == "```":
            i += 1
            break
        code_lines.append(lines[i])
        i += 1

    code_content = "\n".join(code_lines)

    # Notion limits code blocks to 2000 chars
    if len(code_content) > 2000:
        code_content = code_content[:1997] + "..."

    return {
        "type": "code",
        "code": {
            "language": language.lower(),
            "rich_text": [{"type": "text", "text": {"content": code_content}}],
        },
    }, i


def _parse_list(
    lines: list[str], start_idx: int, bullet: bool = True
) -> tuple[list[dict[str, Any]], int]:
    """Parse a bullet or numbered list."""
    items = []
    i = start_idx

    pattern = r"^[\s]*[-*]\s" if bullet else r"^[\s]*\d+\.\s"
    block_type = "bulleted_list_item" if bullet else "numbered_list_item"

    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            break

        if not re.match(pattern, line):
            break

        text = re.sub(pattern, "", line).strip()

        items.append(
            {
                "type": block_type,
                block_type: {
                    "rich_text": _rich_text(text),
                },
            }
        )
        i += 1

    return items, i


def _parse_quote(lines: list[str], start_idx: int) -> tuple[dict[str, Any] | None, int]:
    """Parse a block quote."""
    quote_lines = []
    i = start_idx

    while i < len(lines) and lines[i].strip().startswith(">"):
        text = lines[i].strip()[1:].strip()
        quote_lines.append(text)
        i += 1

    if not quote_lines:
        return None, start_idx + 1

    return {
        "type": "quote",
        "quote": {
            "rich_text": _rich_text("\n".join(quote_lines)),
        },
    }, i


def _parse_paragraph(lines: list[str], start_idx: int) -> tuple[str, int]:
    """Parse a paragraph."""
    para_lines = []
    i = start_idx

    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            break

        if (
            line.startswith("#")
            or line.startswith("```")
            or line.strip().startswith("> ")
            or line.strip().startswith(("- ", "* "))
            or re.match(r"^\d+\.\s", line.strip())
        ):
            break

        para_lines.append(line)
        i += 1

    return " ".join(para_lines), i
