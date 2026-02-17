"""Confluence integration utilities - markdown to Confluence storage format conversion."""

import re


def md_to_confluence_storage(markdown: str) -> str:
    """Convert markdown to Confluence storage format (HTML-like).

    Handles: headers, paragraphs, lists, code blocks, inline formatting.

    Args:
        markdown: Markdown content string

    Returns:
        Confluence storage format HTML string
    """
    lines = markdown.split("\n")
    html_parts = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Skip empty lines at start
        if not line.strip() and not html_parts:
            i += 1
            continue

        # Code block
        if line.strip().startswith("```"):
            html, i = _convert_code_block(lines, i)
            html_parts.append(html)
            continue

        # Headers
        if line.startswith("# "):
            html_parts.append(f"<h1>{_convert_inline(line[2:].strip())}</h1>")
            i += 1
            continue
        if line.startswith("## "):
            html_parts.append(f"<h2>{_convert_inline(line[3:].strip())}</h2>")
            i += 1
            continue
        if line.startswith("### "):
            html_parts.append(f"<h3>{_convert_inline(line[4:].strip())}</h3>")
            i += 1
            continue

        # Bullet list
        if line.strip().startswith(("- ", "* ")):
            html, i = _convert_list(lines, i, ordered=False)
            html_parts.append(html)
            continue

        # Numbered list
        if re.match(r"^\d+\.\s", line.strip()):
            html, i = _convert_list(lines, i, ordered=True)
            html_parts.append(html)
            continue

        # Quote
        if line.strip().startswith("> "):
            html, i = _convert_quote(lines, i)
            html_parts.append(html)
            continue

        # Paragraph
        if line.strip():
            para, i = _convert_paragraph(lines, i)
            html_parts.append(f"<p>{_convert_inline(para)}</p>")
            continue

        i += 1

    return "".join(html_parts)


def _convert_inline(text: str) -> str:
    """Convert inline markdown formatting to HTML."""
    # Bold
    text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)

    # Italic
    text = re.sub(r"\*(.*?)\*", r"<em>\1</em>", text)

    # Code
    text = re.sub(r"`(.*?)`", r"<code>\1</code>", text)

    # Links
    return re.sub(
        r"\[(.*?)\]\((.*?)\)",
        r'<a href="\2">\1</a>',
        text,
    )


def _convert_code_block(lines: list[str], start_idx: int) -> tuple[str, int]:
    """Convert code block to Confluence macro."""
    first_line = lines[start_idx].strip()
    language = first_line[3:].strip() or "none"

    code_lines = []
    i = start_idx + 1
    while i < len(lines):
        if lines[i].strip() == "```":
            i += 1
            break
        code_lines.append(lines[i])
        i += 1

    code_content = "\n".join(code_lines)

    # Confluence code macro
    html = f'<ac:structured-macro ac:name="code"><ac:parameter ac:name="language">{language}</ac:parameter><ac:plain-text-body><![CDATA[{code_content}]]></ac:plain-text-body></ac:structured-macro>'

    return html, i


def _convert_list(
    lines: list[str], start_idx: int, ordered: bool = False
) -> tuple[str, int]:
    """Convert markdown list to HTML."""
    tag = "ol" if ordered else "ul"
    pattern = r"^\d+\.\s" if ordered else r"^[-*]\s"

    items = []
    i = start_idx

    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            break

        if not re.match(pattern, line):
            break

        text = re.sub(pattern, "", line)
        items.append(f"<li>{_convert_inline(text)}</li>")
        i += 1

    html = f"<{tag}>{''.join(items)}</{tag}>"
    return html, i


def _convert_quote(lines: list[str], start_idx: int) -> tuple[str, int]:
    """Convert blockquote to Confluence panel."""
    quote_lines = []
    i = start_idx

    while i < len(lines) and lines[i].strip().startswith(">"):
        text = lines[i].strip()[1:].strip()
        quote_lines.append(text)
        i += 1

    content = " ".join(quote_lines)

    # Confluence info panel for quotes
    html = f'<ac:structured-macro ac:name="info"><ac:rich-text-body><p>{_convert_inline(content)}</p></ac:rich-text-body></ac:structured-macro>'

    return html, i


def _convert_paragraph(lines: list[str], start_idx: int) -> tuple[str, int]:
    """Convert paragraph."""
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
            or line.strip().startswith(("> ", "- ", "* "))
            or re.match(r"^\d+\.\s", line.strip())
        ):
            break

        para_lines.append(line)
        i += 1

    return " ".join(para_lines), i
