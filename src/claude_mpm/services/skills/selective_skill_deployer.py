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
- Track deployed skills in .mpm-deployed-skills.json index
- Remove orphaned skills (deployed by mpm but no longer referenced)

FORMATS SUPPORTED:
1. Legacy: skills: [skill-a, skill-b, ...]
2. New: skills: {required: [...], optional: [...]}

SKILL DISCOVERY FLOW:
1. Scan deployed agents (.claude/agents/*.md)
2. Extract frontmatter skills (explicit declarations)
3. Query SkillToAgentMapper for pattern-based skills
4. Combine both sources into unified set

DEPLOYMENT TRACKING:
1. Track which skills were deployed by claude-mpm in index file
2. Update index after each deployment operation
3. Clean up orphaned skills no longer referenced by agents

References:
- Feature: Progressive skills discovery (#117)
- Service: SkillToAgentMapper (skill_to_agent_mapper.py)
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set

import yaml

from claude_mpm.core.logging_config import get_logger
from claude_mpm.services.skills.skill_to_agent_mapper import SkillToAgentMapper

logger = get_logger(__name__)

# Deployment tracking index file
DEPLOYED_INDEX_FILE = ".mpm-deployed-skills.json"


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

    # Normalize skill paths: convert slashes to dashes for compatibility with deployment
    # SkillToAgentMapper returns paths like "toolchains/python/frameworks/django"
    # but deployment expects "toolchains-python-frameworks-django"
    normalized_skills = {skill.replace("/", "-") for skill in required_skills}

    logger.info(
        f"Combined {len(frontmatter_skills)} frontmatter + {len(mapped_skills)} mapped "
        f"= {len(required_skills)} total unique skills (normalized to {len(normalized_skills)})"
    )

    return normalized_skills


# === Deployment Tracking Functions ===


def load_deployment_index(claude_skills_dir: Path) -> Dict[str, Any]:
    """Load deployment tracking index from ~/.claude/skills/.

    Args:
        claude_skills_dir: Path to Claude skills directory (~/.claude/skills/)

    Returns:
        Dict containing:
        - deployed_skills: Dict mapping skill name to deployment metadata
        - last_sync: ISO timestamp of last sync operation

    Example:
        >>> index = load_deployment_index(Path.home() / ".claude" / "skills")
        >>> print(f"Tracked skills: {len(index['deployed_skills'])}")
    """
    index_path = claude_skills_dir / DEPLOYED_INDEX_FILE

    if not index_path.exists():
        logger.debug(f"No deployment index found at {index_path}, creating new")
        return {"deployed_skills": {}, "last_sync": None}

    try:
        with open(index_path, encoding="utf-8") as f:
            index = json.load(f)

        # Ensure required keys exist
        if "deployed_skills" not in index:
            index["deployed_skills"] = {}
        if "last_sync" not in index:
            index["last_sync"] = None

        logger.debug(
            f"Loaded deployment index: {len(index['deployed_skills'])} tracked skills"
        )
        return index

    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load deployment index: {e}, creating new")
        return {"deployed_skills": {}, "last_sync": None}


def save_deployment_index(claude_skills_dir: Path, index: Dict[str, Any]) -> None:
    """Save deployment tracking index to ~/.claude/skills/.

    Args:
        claude_skills_dir: Path to Claude skills directory (~/.claude/skills/)
        index: Index data to save

    Example:
        >>> index = {"deployed_skills": {...}, "last_sync": "2025-12-22T10:30:00Z"}
        >>> save_deployment_index(Path.home() / ".claude" / "skills", index)
    """
    index_path = claude_skills_dir / DEPLOYED_INDEX_FILE

    try:
        # Ensure directory exists
        claude_skills_dir.mkdir(parents=True, exist_ok=True)

        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

        logger.debug(f"Saved deployment index: {len(index['deployed_skills'])} skills")

    except OSError as e:
        logger.error(f"Failed to save deployment index: {e}")
        raise


def track_deployed_skill(
    claude_skills_dir: Path, skill_name: str, collection: str
) -> None:
    """Track a newly deployed skill in the deployment index.

    Args:
        claude_skills_dir: Path to Claude skills directory (~/.claude/skills/)
        skill_name: Name of deployed skill
        collection: Collection name skill was deployed from

    Example:
        >>> track_deployed_skill(
        ...     Path.home() / ".claude" / "skills",
        ...     "systematic-debugging",
        ...     "claude-mpm-skills"
        ... )
    """
    index = load_deployment_index(claude_skills_dir)

    # Add skill to deployed_skills
    index["deployed_skills"][skill_name] = {
        "collection": collection,
        "deployed_at": datetime.utcnow().isoformat() + "Z",
    }

    # Update last_sync timestamp
    index["last_sync"] = datetime.utcnow().isoformat() + "Z"

    save_deployment_index(claude_skills_dir, index)
    logger.debug(f"Tracked deployment: {skill_name} from {collection}")


def untrack_skill(claude_skills_dir: Path, skill_name: str) -> None:
    """Remove skill from deployment tracking index.

    Args:
        claude_skills_dir: Path to Claude skills directory (~/.claude/skills/)
        skill_name: Name of skill to untrack

    Example:
        >>> untrack_skill(
        ...     Path.home() / ".claude" / "skills",
        ...     "old-skill"
        ... )
    """
    index = load_deployment_index(claude_skills_dir)

    if skill_name in index["deployed_skills"]:
        del index["deployed_skills"][skill_name]
        index["last_sync"] = datetime.utcnow().isoformat() + "Z"
        save_deployment_index(claude_skills_dir, index)
        logger.debug(f"Untracked skill: {skill_name}")


def cleanup_orphan_skills(
    claude_skills_dir: Path, required_skills: Set[str]
) -> Dict[str, Any]:
    """Remove skills deployed by claude-mpm but no longer referenced by agents.

    This function:
    1. Loads deployment tracking index
    2. Identifies orphaned skills (tracked but not in required_skills)
    3. Removes orphaned skill directories from ~/.claude/skills/
    4. Updates deployment index

    Args:
        claude_skills_dir: Path to Claude skills directory (~/.claude/skills/)
        required_skills: Set of skill names currently required by agents

    Returns:
        Dict containing:
        - removed_count: Number of skills removed
        - removed_skills: List of removed skill names
        - kept_count: Number of skills kept
        - errors: List of error messages

    Example:
        >>> required = {"skill-a", "skill-b"}
        >>> result = cleanup_orphan_skills(
        ...     Path.home() / ".claude" / "skills",
        ...     required
        ... )
        >>> print(f"Removed {result['removed_count']} orphaned skills")
    """
    import shutil

    index = load_deployment_index(claude_skills_dir)
    tracked_skills = set(index["deployed_skills"].keys())

    # Find orphaned skills: tracked by mpm but not in required_skills
    orphaned = tracked_skills - required_skills

    if not orphaned:
        logger.info("No orphaned skills to remove")
        return {
            "removed_count": 0,
            "removed_skills": [],
            "kept_count": len(tracked_skills),
            "errors": [],
        }

    logger.info(
        f"Found {len(orphaned)} orphaned skills (tracked but not required by agents)"
    )

    removed = []
    errors = []

    for skill_name in orphaned:
        skill_dir = claude_skills_dir / skill_name

        # Remove skill directory if it exists
        if skill_dir.exists():
            try:
                # Validate path is within claude_skills_dir (security)
                skill_dir.resolve().relative_to(claude_skills_dir.resolve())

                # Remove directory
                if skill_dir.is_symlink():
                    logger.debug(f"Removing symlink: {skill_dir}")
                    skill_dir.unlink()
                else:
                    shutil.rmtree(skill_dir)

                removed.append(skill_name)
                logger.info(f"Removed orphaned skill: {skill_name}")

            except ValueError as e:
                error_msg = f"Path traversal attempt detected: {skill_dir}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue
            except Exception as e:
                error_msg = f"Failed to remove {skill_name}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue

        # Remove from tracking index
        untrack_skill(claude_skills_dir, skill_name)

    kept_count = len(tracked_skills) - len(removed)

    logger.info(
        f"Cleanup complete: removed {len(removed)} skills, kept {kept_count} skills"
    )

    return {
        "removed_count": len(removed),
        "removed_skills": removed,
        "kept_count": kept_count,
        "errors": errors,
    }
