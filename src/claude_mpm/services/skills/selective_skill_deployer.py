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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

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

    CRITICAL DESIGN DECISION: This function ONLY returns skills for the DEPLOYED agents
    provided in agent_ids. It does NOT return skills for all agents in the mapping
    configuration (skill_to_agent_mapping.yaml lists 41 agents, but only 33 may be deployed).

    GENERIC AGENT HANDLING: The generic "engineer" agent is mapped to 100+ skills in the
    configuration because it's designed as a fallback. To prevent over-deployment when
    specialized agents exist, we skip "engineer" if specialized agents are present.

    WHY THIS MATTERS:
    - skill_to_agent_mapping.yaml lists ALL possible agents (41 total)
    - User may only have 33 agents deployed in ~/.claude/agents/
    - Without filtering, we'd deploy skills for all 41 agents (over-deployment)
    - Solution: Only query skills for DEPLOYED agents (passed in agent_ids)

    Args:
        agent_ids: List of DEPLOYED agent identifiers (e.g., ["python-engineer", "typescript-engineer"])
                  These should be extracted from ~/.claude/agents/*.md files only.

    Returns:
        Set of unique skill names inferred from mapping configuration for DEPLOYED agents only

    Example:
        >>> # DEPLOYED agents only (from ~/.claude/agents/)
        >>> deployed_agent_ids = ["python-engineer", "typescript-engineer", "qa"]
        >>> skills = get_skills_from_mapping(deployed_agent_ids)
        >>> print(f"Found {len(skills)} skills for {len(deployed_agent_ids)} deployed agents")
    """
    try:
        mapper = SkillToAgentMapper()
        all_skills = set()

        # CRITICAL FIX: Skip generic "engineer" agent if specialized agents exist
        # The "engineer" agent is mapped to ~107 skills (almost all skills) because
        # it's a fallback agent. This causes over-deployment when you have specialized
        # agents like "python-engineer", "typescript-engineer", etc.
        #
        # Solution: Filter out "engineer" from agent_ids if specialized agents exist
        specialized_engineers = [
            aid for aid in agent_ids if aid.endswith("-engineer") and aid != "engineer"
        ]

        # If specialized engineers exist, exclude generic "engineer" from skill mapping
        # This prevents deploying 100+ skills when only a subset is needed
        agents_to_query = agent_ids
        if specialized_engineers and "engineer" in agent_ids:
            agents_to_query = [aid for aid in agent_ids if aid != "engineer"]
            logger.info(
                f"Excluding generic 'engineer' agent from skill mapping "
                f"(found {len(specialized_engineers)} specialized engineers: "
                f"{', '.join(specialized_engineers[:5])}{'...' if len(specialized_engineers) > 5 else ''})"
            )

        # IMPORTANT: Only query skills for DEPLOYED agents (those in agent_ids)
        # Do NOT query all agents from skill_to_agent_mapping.yaml (that's 41 agents)
        for agent_id in agents_to_query:
            agent_skills = mapper.get_skills_for_agent(agent_id)
            if agent_skills:
                all_skills.update(agent_skills)
                logger.debug(f"Mapped {len(agent_skills)} skills to {agent_id}")

        logger.info(
            f"Mapped {len(all_skills)} unique skills for {len(agents_to_query)} deployed agents "
            f"(out of {len(agent_ids)} total deployed, excluding generic 'engineer' if specialized exist)"
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
        - user_requested_skills: List of skill names manually requested by user
        - last_sync: ISO timestamp of last sync operation

    Example:
        >>> index = load_deployment_index(Path.home() / ".claude" / "skills")
        >>> print(f"Tracked skills: {len(index['deployed_skills'])}")
    """
    index_path = claude_skills_dir / DEPLOYED_INDEX_FILE

    if not index_path.exists():
        logger.debug(f"No deployment index found at {index_path}, creating new")
        return {"deployed_skills": {}, "user_requested_skills": [], "last_sync": None}

    try:
        with open(index_path, encoding="utf-8") as f:
            index = json.load(f)

        # Ensure required keys exist
        if "deployed_skills" not in index:
            index["deployed_skills"] = {}
        if "user_requested_skills" not in index:
            index["user_requested_skills"] = []
        if "last_sync" not in index:
            index["last_sync"] = None

        logger.debug(
            f"Loaded deployment index: {len(index['deployed_skills'])} tracked skills, "
            f"{len(index['user_requested_skills'])} user-requested"
        )
        return index

    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load deployment index: {e}, creating new")
        return {"deployed_skills": {}, "user_requested_skills": [], "last_sync": None}


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
        "deployed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    # Update last_sync timestamp
    index["last_sync"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

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
        index["last_sync"] = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        save_deployment_index(claude_skills_dir, index)
        logger.debug(f"Untracked skill: {skill_name}")


def cleanup_orphan_skills(
    claude_skills_dir: Path, required_skills: Set[str]
) -> Dict[str, Any]:
    """Remove skills deployed by claude-mpm but no longer referenced by agents.

    This function:
    1. Loads deployment tracking index
    2. Identifies orphaned skills (tracked but not in required_skills AND not user-requested)
    3. Removes orphaned skill directories from ~/.claude/skills/
    4. Updates deployment index

    User-requested skills are NEVER cleaned up as orphans - they are treated as required.

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
    user_requested = set(index.get("user_requested_skills", []))

    # Find orphaned skills: tracked by mpm but not in required_skills AND not user-requested
    # User-requested skills are treated as required and NEVER cleaned up
    all_required = required_skills | user_requested
    orphaned = tracked_skills - all_required

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

            except ValueError:
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


# === Configuration Management Functions ===


def save_agent_skills_to_config(skills: List[str], config_path: Path) -> None:
    """Save agent-scanned skills to configuration.yaml under skills.agent_referenced.

    Args:
        skills: List of skill names scanned from deployed agents
        config_path: Path to configuration.yaml file

    Example:
        >>> skills = ["systematic-debugging", "typescript-core"]
        >>> save_agent_skills_to_config(skills, Path(".claude-mpm/configuration.yaml"))
    """
    import yaml

    try:
        # Load existing configuration (or create empty dict)
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}

        # Ensure skills section exists
        if "skills" not in config:
            config["skills"] = {}

        # Update agent_referenced skills (sorted for consistency)
        config["skills"]["agent_referenced"] = sorted(skills)

        # Ensure user_defined exists (but don't overwrite if set)
        if "user_defined" not in config["skills"]:
            config["skills"]["user_defined"] = []

        # Save configuration
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        logger.info(
            f"Saved {len(skills)} agent-referenced skills to configuration.yaml"
        )

    except Exception as e:
        logger.error(f"Failed to save agent skills to config: {e}")
        raise


def get_skills_to_deploy(config_path: Path) -> Tuple[List[str], str]:
    """Resolve which skills to deploy based on configuration priority.

    Returns (skills_list, source) where source is 'user_defined' or 'agent_referenced'.

    Logic:
    - If config.skills.user_defined is non-empty → return (user_defined, 'user_defined')
    - Otherwise → return (agent_referenced, 'agent_referenced')

    Args:
        config_path: Path to configuration.yaml file

    Returns:
        Tuple of (skills list, source string)

    Example:
        >>> skills, source = get_skills_to_deploy(Path(".claude-mpm/configuration.yaml"))
        >>> print(f"Deploy {len(skills)} skills from {source}")
    """
    import yaml

    try:
        # Load configuration
        if not config_path.exists():
            logger.warning(f"Configuration file not found: {config_path}")
            return ([], "agent_referenced")

        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        skills_config = config.get("skills", {})
        user_defined = skills_config.get("user_defined", [])
        agent_referenced = skills_config.get("agent_referenced", [])

        # Priority: user_defined if non-empty, otherwise agent_referenced
        if user_defined:
            logger.info(
                f"Using {len(user_defined)} user-defined skills from configuration"
            )
            return (user_defined, "user_defined")
        logger.info(
            f"Using {len(agent_referenced)} agent-referenced skills from configuration"
        )
        return (agent_referenced, "agent_referenced")

    except Exception as e:
        logger.error(f"Failed to load skills from config: {e}")
        return ([], "agent_referenced")


# === User-Requested Skills Management ===


def get_user_requested_skills(claude_skills_dir: Path) -> List[str]:
    """Get list of user-requested skills.

    Args:
        claude_skills_dir: Path to Claude skills directory (~/.claude/skills/)

    Returns:
        List of skill names manually requested by user

    Example:
        >>> skills = get_user_requested_skills(Path.home() / ".claude" / "skills")
        >>> print(f"User requested {len(skills)} skills")
    """
    index = load_deployment_index(claude_skills_dir)
    return index.get("user_requested_skills", [])


def add_user_requested_skill(skill_name: str, claude_skills_dir: Path) -> bool:
    """Add a skill to user_requested_skills list.

    This function:
    1. Loads deployment index
    2. Adds skill name to user_requested_skills (if not already present)
    3. Saves updated index
    4. Returns success status

    Note: This function does NOT deploy the skill, it only marks it as user-requested.
    Use this in conjunction with skill deployment functions.

    Args:
        skill_name: Name of skill to mark as user-requested
        claude_skills_dir: Path to Claude skills directory (~/.claude/skills/)

    Returns:
        True if skill was added, False if already present

    Example:
        >>> added = add_user_requested_skill(
        ...     "django-framework",
        ...     Path.home() / ".claude" / "skills"
        ... )
        >>> print(f"Skill added: {added}")
    """
    index = load_deployment_index(claude_skills_dir)
    user_requested = index.get("user_requested_skills", [])

    if skill_name in user_requested:
        logger.debug(f"Skill {skill_name} already in user_requested_skills")
        return False

    user_requested.append(skill_name)
    index["user_requested_skills"] = user_requested
    index["last_sync"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    save_deployment_index(claude_skills_dir, index)
    logger.info(f"Added {skill_name} to user_requested_skills")
    return True


def remove_user_requested_skill(skill_name: str, claude_skills_dir: Path) -> bool:
    """Remove a skill from user_requested_skills list.

    This function:
    1. Loads deployment index
    2. Removes skill name from user_requested_skills
    3. Saves updated index
    4. Returns success status

    Note: This function does NOT remove the deployed skill directory.
    It only removes the skill from user_requested_skills, making it eligible
    for cleanup during orphan removal.

    Args:
        skill_name: Name of skill to remove from user_requested_skills
        claude_skills_dir: Path to Claude skills directory (~/.claude/skills/)

    Returns:
        True if skill was removed, False if not present

    Example:
        >>> removed = remove_user_requested_skill(
        ...     "django-framework",
        ...     Path.home() / ".claude" / "skills"
        ... )
        >>> print(f"Skill removed: {removed}")
    """
    index = load_deployment_index(claude_skills_dir)
    user_requested = index.get("user_requested_skills", [])

    if skill_name not in user_requested:
        logger.debug(f"Skill {skill_name} not in user_requested_skills")
        return False

    user_requested.remove(skill_name)
    index["user_requested_skills"] = user_requested
    index["last_sync"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    save_deployment_index(claude_skills_dir, index)
    logger.info(f"Removed {skill_name} from user_requested_skills")
    return True


def is_user_requested_skill(skill_name: str, claude_skills_dir: Path) -> bool:
    """Check if a skill is in the user_requested_skills list.

    Args:
        skill_name: Name of skill to check
        claude_skills_dir: Path to Claude skills directory (~/.claude/skills/)

    Returns:
        True if skill is user-requested, False otherwise

    Example:
        >>> is_requested = is_user_requested_skill(
        ...     "django-framework",
        ...     Path.home() / ".claude" / "skills"
        ... )
        >>> print(f"User requested: {is_requested}")
    """
    user_requested = get_user_requested_skills(claude_skills_dir)
    return skill_name in user_requested
