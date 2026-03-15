"""
Agent provenance detection utilities.

Provides a single canonical function to determine whether an agent file
is managed by claude-mpm (system agent) or user-created.
"""

from pathlib import Path

from claude_mpm.core.logging_config import get_logger

logger = get_logger(__name__)

# Canonical list of author patterns that identify MPM-managed agents
MPM_AUTHOR_PATTERNS = frozenset(
    [
        "claude-mpm",
        "claude mpm",
        "anthropic",
        "claude-mpm@anthropic.com",
    ]
)


def is_mpm_managed_agent(content: str) -> bool:
    """Check if an agent file is managed by claude-mpm via frontmatter author field.

    This is the CANONICAL function for provenance detection. All other
    implementations should delegate to this function.

    The check is restricted to the YAML frontmatter section only (between
    the opening and closing '---' markers). Body content is never inspected.

    Args:
        content: Full text content of the agent .md file

    Returns:
        True if the agent has an MPM author marker in its frontmatter
    """
    # Must start with frontmatter delimiter
    if not content.startswith("---"):
        return False

    # Extract frontmatter section (between first and second '---')
    parts = content.split("---", 2)
    if len(parts) < 3:
        return False

    frontmatter = parts[1].lower()

    # Check for author field with MPM patterns
    # Match "author: value" where value contains an MPM pattern
    for line in frontmatter.split("\n"):
        line = line.strip()
        if line.startswith("author:"):
            author_value = line[7:].strip().strip("'\"")
            return any(pattern in author_value for pattern in MPM_AUTHOR_PATTERNS)

    return False


def is_mpm_managed_file(file_path: Path) -> bool:
    """Check if an agent file on disk is managed by claude-mpm.

    Convenience wrapper that reads the file and calls is_mpm_managed_agent().

    Args:
        file_path: Path to the agent .md file

    Returns:
        True if the agent is MPM-managed, False otherwise (including on errors)
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        return is_mpm_managed_agent(content)
    except Exception as e:
        logger.debug(f"Failed to check provenance for {file_path}: {e}")
        return False
