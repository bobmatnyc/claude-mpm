"""Shared utilities for agent deployment filename normalization.

This module provides consistent filename handling for agent deployment
across different services (SingleTierDeploymentService, GitSourceSyncService).

Design Decision: Dash-based filenames as standard

Rationale: Git repositories use dash-based naming (python-engineer.md),
which is the cache convention. YAML frontmatter may have underscore-based
agent_id fields (python_engineer). This module ensures all deployed files
use dash-based naming to avoid duplicates and maintain consistency.

Priority order for deriving deployment filename:
1. Source filename if it's dash-based (matches cache convention)
2. agent_id from YAML frontmatter, converted underscores to dashes
3. Derive from source filename, converting underscores to dashes
"""

import re
from pathlib import Path
from typing import Optional

import yaml


def normalize_deployment_filename(
    source_filename: str, agent_id: Optional[str] = None
) -> str:
    """Normalize filename for deployment.

    Ensures consistent dash-based filenames for deployed agents.

    Priority:
    1. Use source filename if dash-based (matches cache convention)
    2. Convert underscore to dash in source filename
    3. If agent_id provided and differs from source, use source (already normalized)

    Args:
        source_filename: Original filename (e.g., "python-engineer.md")
        agent_id: Optional agent_id from YAML frontmatter (e.g., "python_engineer")

    Returns:
        Dash-based filename with .md extension (e.g., "python-engineer.md")

    Examples:
        >>> normalize_deployment_filename("python-engineer.md")
        'python-engineer.md'

        >>> normalize_deployment_filename("python_engineer.md")
        'python-engineer.md'

        >>> normalize_deployment_filename("engineer.md", "python_engineer")
        'engineer.md'  # Source filename takes precedence

        >>> normalize_deployment_filename("QA.md")
        'qa.md'
    """
    # Get stem (filename without extension)
    path = Path(source_filename)
    stem = path.stem

    # Normalize: lowercase, replace underscores with dashes
    normalized_stem = stem.lower().replace("_", "-")

    # Strip -agent suffix for consistency (e.g., "qa-agent" -> "qa")
    if normalized_stem.endswith("-agent"):
        normalized_stem = normalized_stem[:-6]  # Remove "-agent"

    # Always use .md extension
    return f"{normalized_stem}.md"


def ensure_agent_id_in_frontmatter(content: str, filename: str) -> str:
    """Ensure YAML frontmatter has agent_id field.

    If the content has YAML frontmatter but no agent_id, derive one from filename.
    If no frontmatter exists, add one with agent_id.

    Args:
        content: Markdown file content (may have YAML frontmatter)
        filename: Source filename to derive agent_id from

    Returns:
        Content with agent_id in frontmatter (may be unchanged if already present)

    Examples:
        >>> content = "---\\nname: Python Engineer\\n---\\n# Content"
        >>> ensure_agent_id_in_frontmatter(content, "python-engineer.md")
        '---\\nagent_id: python-engineer\\nname: Python Engineer\\n---\\n# Content'
    """
    # Derive agent_id from filename (dash-based, no extension)
    derived_agent_id = Path(filename).stem.lower().replace("_", "-")
    if derived_agent_id.endswith("-agent"):
        derived_agent_id = derived_agent_id[:-6]

    # Check if content has YAML frontmatter
    if not content.startswith("---"):
        # No frontmatter, add one with agent_id
        return f"---\nagent_id: {derived_agent_id}\n---\n{content}"

    # Extract frontmatter
    frontmatter_match = re.match(r"^---\n(.*?)\n---(\s*\n)", content, re.DOTALL)
    if not frontmatter_match:
        # Malformed frontmatter, return unchanged
        return content

    yaml_content = frontmatter_match.group(1)
    rest_of_content = content[frontmatter_match.end() :]

    # Parse YAML to check for agent_id
    try:
        parsed = yaml.safe_load(yaml_content)
        if isinstance(parsed, dict) and "agent_id" in parsed:
            # agent_id already exists, return unchanged
            return content
    except yaml.YAMLError:
        # YAML parse error, try to add agent_id anyway
        pass

    # Add agent_id to the beginning of frontmatter
    new_yaml_content = f"agent_id: {derived_agent_id}\n{yaml_content}"
    return f"---\n{new_yaml_content}\n---{frontmatter_match.group(2)}{rest_of_content}"


def get_underscore_variant_filename(normalized_filename: str) -> Optional[str]:
    """Get underscore variant of a dash-based filename.

    Used to detect and clean up duplicate files where the same agent
    might exist with both dash and underscore naming.

    Args:
        normalized_filename: Dash-based filename (e.g., "python-engineer.md")

    Returns:
        Underscore variant filename, or None if no dashes to convert

    Examples:
        >>> get_underscore_variant_filename("python-engineer.md")
        'python_engineer.md'

        >>> get_underscore_variant_filename("engineer.md")
        None
    """
    path = Path(normalized_filename)
    stem = path.stem

    if "-" not in stem:
        return None

    underscore_stem = stem.replace("-", "_")
    return f"{underscore_stem}.md"
