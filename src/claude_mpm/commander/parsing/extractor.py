"""Extract options and context from matched patterns."""

import re
from typing import Any, Dict, List, Optional


def extract_options(content: str) -> Optional[List[str]]:
    """Extract options from decision content.

    Supports multiple formats:
    - Numbered lists: "1. Option A\n2. Option B"
    - Bullet lists: "• Option A\n- Option B"
    - Inline options: "(option1/option2/option3)"
    - Y/n style: "[Y/n]", "[yes/no]"

    Args:
        content: Content to extract options from

    Returns:
        List of option strings if found, None otherwise
    """
    # Numbered list: "1. Option A\n2. Option B"
    numbered = re.findall(r"^\s*\d+[\.\)]\s*(.+)$", content, re.MULTILINE)
    if numbered:
        return [opt.strip() for opt in numbered]

    # Bullet list: "• Option A\n- Option B"
    bullets = re.findall(r"^\s*[-•*]\s*(.+)$", content, re.MULTILINE)
    if bullets:
        return [opt.strip() for opt in bullets]

    # Inline options: "(option1/option2/option3)"
    inline = re.search(r"\(([^)]+/[^)]+)\)", content)
    if inline:
        return [o.strip() for o in inline.group(1).split("/")]

    # Y/n style
    yn = re.search(r"\[(Y/n|y/N|yes/no|Yes/No)\]", content, re.I)
    if yn:
        parts = yn.group(1).split("/")
        return [p.strip() for p in parts]

    return None


def extract_error_context(
    content: str, match_start: int, match_end: int, context_lines: int = 5
) -> Dict[str, Any]:
    """Extract surrounding context for error.

    Args:
        content: Full content text
        match_start: Character position where match starts
        match_end: Character position where match ends
        context_lines: Number of lines to include before/after error

    Returns:
        Dict with surrounding lines and error position info
    """
    lines = content.split("\n")

    # Find which line the match is on
    char_count = 0
    match_line = 0
    for i, line in enumerate(lines):
        char_count += len(line) + 1  # +1 for newline
        if char_count > match_start:
            match_line = i
            break

    # Get context lines
    start = max(0, match_line - context_lines)
    end = min(len(lines), match_line + context_lines + 1)

    return {
        "surrounding_lines": lines[start:end],
        "error_line_index": match_line - start,
        "total_lines": len(lines),
        "match_line": match_line,
    }


def extract_action_details(content: str, match: re.Match) -> Dict[str, Any]:
    """Extract details about an action from approval match.

    Args:
        content: Full content text
        match: Regex match object for the approval pattern

    Returns:
        Dict with action type, target, and reversibility info
    """
    groups = match.groups()
    # Use the first captured group if available, otherwise the full match
    action_text = groups[0] if groups else match.group(0)

    # Try to identify the action type from the full matched text
    full_match = match.group(0)
    action_type = "unknown"
    if re.search(r"delete|remove", full_match, re.I):
        action_type = "delete"
    elif re.search(r"overwrite|modify|change", full_match, re.I):
        action_type = "modify"
    elif re.search(r"create|add", full_match, re.I):
        action_type = "create"

    # Check if reversible
    reversible = "cannot be undone" not in content.lower()

    return {
        "action": action_type,
        "target": action_text.strip(),
        "reversible": reversible,
    }


def strip_code_blocks(content: str) -> str:
    """Remove code blocks to avoid false positives.

    Replaces fenced code blocks and inline code with placeholders
    to prevent pattern matching inside code.

    Args:
        content: Content to strip code blocks from

    Returns:
        Content with code blocks replaced by placeholders
    """
    # Remove fenced code blocks
    content = re.sub(r"```[\s\S]*?```", "[CODE_BLOCK]", content)
    # Remove inline code and return
    return re.sub(r"`[^`]+`", "[INLINE_CODE]", content)
