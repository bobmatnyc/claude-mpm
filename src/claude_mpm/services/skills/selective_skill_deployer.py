"""Selective skill deployment based on agent requirements.

WHY: Agents now have a skills field in their frontmatter. We should only deploy
skills that agents actually reference, reducing deployed skills from ~78 to ~20
for a typical project.

DESIGN DECISIONS:
- Support both legacy flat list and new required/optional dict formats
- Parse YAML frontmatter from agent markdown files
- Extract all skill references from deployed agents
- Return set of unique skill names for filtering

FORMATS SUPPORTED:
1. Legacy: skills: [skill-a, skill-b, ...]
2. New: skills: {required: [...], optional: [...]}

References:
- Feature: Progressive skills discovery (#117)
"""

import re
from pathlib import Path
from typing import Any, Dict, Set

import yaml

from claude_mpm.core.logging_config import get_logger

logger = get_logger(__name__)


def parse_agent_frontmatter(agent_file: Path) -> Dict[str, Any]:
    """Parse YAML frontmatter from agent markdown file.

    Args:
        agent_file: Path to agent markdown file

    Returns:
        Parsed frontmatter as dictionary, or empty dict if parsing fails

    Example:
        >>> frontmatter = parse_agent_frontmatter(Path("agent.md"))
        >>> skills = frontmatter.get('skills', [])
    """
    try:
        content = agent_file.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to read {agent_file}: {e}")
        return {}

    # Match YAML frontmatter between --- delimiters
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        logger.debug(f"No frontmatter found in {agent_file}")
        return {}

    try:
        frontmatter = yaml.safe_load(match.group(1))
        return frontmatter or {}
    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse frontmatter in {agent_file}: {e}")
        return {}


def get_skills_from_agent(frontmatter: Dict[str, Any]) -> Set[str]:
    """Extract skill names from agent frontmatter (handles both formats).

    Supports both legacy and new formats:
    - Legacy: skills: [skill-a, skill-b, ...]
    - New: skills: {required: [...], optional: [...]}

    Args:
        frontmatter: Parsed agent frontmatter

    Returns:
        Set of unique skill names

    Example:
        >>> # Legacy format
        >>> frontmatter = {'skills': ['skill-a', 'skill-b']}
        >>> get_skills_from_agent(frontmatter)
        {'skill-a', 'skill-b'}

        >>> # New format
        >>> frontmatter = {'skills': {'required': ['skill-a'], 'optional': ['skill-b']}}
        >>> get_skills_from_agent(frontmatter)
        {'skill-a', 'skill-b'}
    """
    skills_field = frontmatter.get("skills")

    # Handle None or missing skills field
    if skills_field is None:
        return set()

    # New format: {required: [...], optional: [...]}
    if isinstance(skills_field, dict):
        required = skills_field.get("required") or []
        optional = skills_field.get("optional") or []

        # Ensure both are lists
        if not isinstance(required, list):
            required = []
        if not isinstance(optional, list):
            optional = []

        return set(required + optional)

    # Legacy format: [skill1, skill2, ...]
    if isinstance(skills_field, list):
        return set(skills_field)

    # Unsupported format
    logger.warning(f"Unexpected skills field type: {type(skills_field)}")
    return set()


def get_required_skills_from_agents(agents_dir: Path) -> Set[str]:
    """Extract all skills referenced by deployed agents.

    Scans all agent markdown files in agents_dir and collects unique skill names.
    Supports both legacy and new skills field formats.

    Args:
        agents_dir: Path to deployed agents directory (e.g., .claude/agents/)

    Returns:
        Set of unique skill names referenced across all agents

    Example:
        >>> agents_dir = Path(".claude/agents")
        >>> required_skills = get_required_skills_from_agents(agents_dir)
        >>> print(f"Found {len(required_skills)} unique skills")
    """
    required_skills = set()

    if not agents_dir.exists():
        logger.warning(f"Agents directory not found: {agents_dir}")
        return required_skills

    # Scan all agent markdown files
    agent_files = list(agents_dir.glob("*.md"))
    logger.debug(f"Scanning {len(agent_files)} agent files in {agents_dir}")

    for agent_file in agent_files:
        frontmatter = parse_agent_frontmatter(agent_file)
        agent_skills = get_skills_from_agent(frontmatter)

        if agent_skills:
            required_skills.update(agent_skills)
            logger.debug(f"Agent {agent_file.stem}: {len(agent_skills)} skills")

    logger.info(f"Found {len(required_skills)} unique skills across all agents")
    return required_skills
