"""Selective skill deployment based on agent requirements.

WHY: Agents now have a skills field in their frontmatter. We should only deploy
skills that agents actually reference, reducing deployed skills from ~78 to ~20
for a typical project.

DESIGN DECISIONS:
- Dual-source skill discovery:
  1. Explicit frontmatter declarations (skills: field)
  2. SkillToAgentMapper inference (pattern-based)
- Support both legacy flat list and new required/optional dict formats
- Parse YAML frontmatter from agent markdown files
- Combine explicit + inferred skills for comprehensive coverage
- Return set of unique skill names for filtering

FORMATS SUPPORTED:
1. Legacy: skills: [skill-a, skill-b, ...]
2. New: skills: {required: [...], optional: [...]}

SKILL DISCOVERY FLOW:
1. Scan deployed agents (.claude/agents/*.md)
2. Extract frontmatter skills (explicit declarations)
3. Query SkillToAgentMapper for pattern-based skills
4. Combine both sources into unified set

References:
- Feature: Progressive skills discovery (#117)
- Service: SkillToAgentMapper (skill_to_agent_mapper.py)
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Set

import yaml

from claude_mpm.core.logging_config import get_logger
from claude_mpm.services.skills.skill_to_agent_mapper import SkillToAgentMapper

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


def get_skills_from_mapping(agent_ids: List[str]) -> Set[str]:
    """Get skills for agents using SkillToAgentMapper inference.

    Uses SkillToAgentMapper to find all skills associated with given agent IDs.
    This provides pattern-based skill discovery beyond explicit frontmatter declarations.

    Args:
        agent_ids: List of agent identifiers (e.g., ["python-engineer", "typescript-engineer"])

    Returns:
        Set of unique skill names inferred from mapping configuration

    Example:
        >>> agent_ids = ["python-engineer", "typescript-engineer"]
        >>> skills = get_skills_from_mapping(agent_ids)
        >>> print(f"Found {len(skills)} skills from mapping")
    """
    try:
        mapper = SkillToAgentMapper()
        all_skills = set()

        for agent_id in agent_ids:
            agent_skills = mapper.get_skills_for_agent(agent_id)
            if agent_skills:
                all_skills.update(agent_skills)
                logger.debug(f"Mapped {len(agent_skills)} skills to {agent_id}")

        logger.info(
            f"Mapped {len(all_skills)} unique skills for {len(agent_ids)} agents"
        )
        return all_skills

    except Exception as e:
        logger.warning(f"Failed to load SkillToAgentMapper: {e}")
        logger.info("Falling back to frontmatter-only skill discovery")
        return set()


def get_required_skills_from_agents(agents_dir: Path) -> Set[str]:
    """Extract all skills referenced by deployed agents.

    Combines skills from two sources:
    1. Explicit frontmatter declarations (skills: field in agent .md files)
    2. SkillToAgentMapper inference (pattern-based skill discovery)

    This dual-source approach ensures agents get both explicitly declared skills
    and skills inferred from their domain/toolchain patterns.

    Args:
        agents_dir: Path to deployed agents directory (e.g., .claude/agents/)

    Returns:
        Set of unique skill names referenced across all agents

    Example:
        >>> agents_dir = Path(".claude/agents")
        >>> required_skills = get_required_skills_from_agents(agents_dir)
        >>> print(f"Found {len(required_skills)} unique skills")
    """
    if not agents_dir.exists():
        logger.warning(f"Agents directory not found: {agents_dir}")
        return set()

    # Scan all agent markdown files
    agent_files = list(agents_dir.glob("*.md"))
    logger.debug(f"Scanning {len(agent_files)} agent files in {agents_dir}")

    # Source 1: Extract skills from frontmatter
    frontmatter_skills = set()
    agent_ids = []

    for agent_file in agent_files:
        agent_id = agent_file.stem
        agent_ids.append(agent_id)

        frontmatter = parse_agent_frontmatter(agent_file)
        agent_skills = get_skills_from_agent(frontmatter)

        if agent_skills:
            frontmatter_skills.update(agent_skills)
            logger.debug(
                f"Agent {agent_id}: {len(agent_skills)} skills from frontmatter"
            )

    logger.info(f"Found {len(frontmatter_skills)} unique skills from frontmatter")

    # Source 2: Get skills from SkillToAgentMapper
    mapped_skills = get_skills_from_mapping(agent_ids)

    # Combine both sources
    required_skills = frontmatter_skills | mapped_skills

    logger.info(
        f"Combined {len(frontmatter_skills)} frontmatter + {len(mapped_skills)} mapped "
        f"= {len(required_skills)} total unique skills"
    )

    return required_skills
