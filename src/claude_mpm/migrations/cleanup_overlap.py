"""Non-destructive cleanup of agent/skill overlap between user-level and project-level.

WHY: After the 6.1.0 and 6.2.0 migrations that split CORE agents/skills into
user-level storage, some projects may still have stale copies at the project
level.  Additionally, early versions of claude-mpm deployed agents with a
redundant "-agent" suffix (e.g. "research-agent" instead of "research") which
should be cleaned up at the user level.

WHAT THIS MODULE DOES:
1. cleanup_agent_overlap: Archives project-level copies of USER_LEVEL_AGENTS
   when the user-level copy already exists.
2. cleanup_skill_overlap: Same for USER_LEVEL_SKILLS (directories, not files).
3. cleanup_stale_agent_names: Archives user-level agents that have a redundant
   "-agent" suffix when the correct (non-suffixed) name already exists.

All operations are non-destructive: files are archived before removal, and a
manifest is written to each archive directory documenting what happened.

IDEMPOTENCY: Running this multiple times is safe -- if the archive already
contains the file, the item is skipped.
"""

import json
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# Lazy imports to avoid circular dependencies at module load time.


def _get_user_level_agents() -> frozenset[str]:
    """Return USER_LEVEL_AGENTS, importing lazily to avoid circular imports."""
    from claude_mpm.services.agents.deployment.agent_deployment import (
        USER_LEVEL_AGENTS,
    )

    return USER_LEVEL_AGENTS


def _get_user_level_skills() -> frozenset[str]:
    """Return USER_LEVEL_SKILLS, importing lazily to avoid circular imports."""
    from claude_mpm.services.skills.selective_skill_deployer import (
        USER_LEVEL_SKILLS,
    )

    return USER_LEVEL_SKILLS


# Stale agent names that had a redundant "-agent" suffix in early versions.
STALE_AGENT_NAMES: frozenset[str] = frozenset(
    {
        "documentation-agent",
        "javascript-engineer-agent",
        "local-ops-agent",
        "memory-manager-agent",
        "qa-agent",
        "research-agent",
        "security-agent",
    }
)


def _write_manifest(
    archive_dir: Path,
    reason: str,
    source_level: str,
    superseded_by: str,
    files: list[str],
) -> None:
    """Write a cleanup manifest to the archive directory.

    Args:
        archive_dir: Directory where archived files live.
        reason: Human-readable reason for the cleanup.
        source_level: Where the originals came from (e.g. "project" or "user").
        superseded_by: What replaced the archived files.
        files: List of archived filenames.
    """
    manifest = {
        "cleanup_date": datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S"),
        "reason": reason,
        "source_level": source_level,
        "superseded_by": superseded_by,
        "archived_files": files,
    }
    manifest_path = archive_dir / "_cleanup_manifest.json"
    try:
        manifest_path.write_text(json.dumps(manifest, indent=2))
        logger.debug("Wrote manifest to %s", manifest_path)
    except OSError as exc:
        logger.warning("Failed to write manifest at %s: %s", manifest_path, exc)


def cleanup_agent_overlap(
    project_dir: Path,
    dry_run: bool = False,
) -> dict:
    """Archive and remove project-level copies of USER_LEVEL_AGENTS.

    For each agent in USER_LEVEL_AGENTS, if both the user-level copy
    (~/.claude/agents/{name}.md) and the project-level copy
    ({project_dir}/.claude/agents/{name}.md) exist, the project copy is
    archived and removed.

    Args:
        project_dir: Root of the project to clean up.
        dry_run: If True, log what would happen without modifying files.

    Returns:
        Dict with keys "archived", "skipped", "errors" (lists of agent names).
    """
    user_level_agents = _get_user_level_agents()
    user_agents_base = Path.home() / ".claude" / "agents"
    project_agents_base = project_dir / ".claude" / "agents"

    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    archive_dir = project_agents_base / "archived" / f"{date_str}_overlap_cleanup"

    result: dict[str, list[str]] = {"archived": [], "skipped": [], "errors": []}

    if not project_agents_base.exists():
        logger.debug("No project agents directory at %s", project_agents_base)
        return result

    archived_files: list[str] = []

    for agent_name in sorted(user_level_agents):
        user_file = user_agents_base / f"{agent_name}.md"
        project_file = project_agents_base / f"{agent_name}.md"

        # Both must exist to be considered overlap
        if not project_file.exists():
            logger.debug("No project copy of agent %s, skipping", agent_name)
            result["skipped"].append(agent_name)
            continue

        if not user_file.exists():
            logger.debug(
                "No user-level copy of agent %s, skipping (not overlap)", agent_name
            )
            result["skipped"].append(agent_name)
            continue

        # Check if already archived (idempotent)
        archived_dest = archive_dir / f"{agent_name}.md"
        if archived_dest.exists():
            logger.debug("Already archived: %s", agent_name)
            result["skipped"].append(agent_name)
            continue

        if dry_run:
            logger.info(
                "[DRY RUN] Would archive project agent %s to %s",
                agent_name,
                archive_dir,
            )
            result["archived"].append(agent_name)
            continue

        try:
            archive_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(project_file, archived_dest)
            project_file.unlink()
            archived_files.append(f"{agent_name}.md")
            result["archived"].append(agent_name)
            logger.info(
                "Archived project agent %s (user copy at %s)",
                agent_name,
                user_file,
            )
        except OSError as exc:
            logger.error("Failed to archive agent %s: %s", agent_name, exc)
            result["errors"].append(agent_name)

    # Write manifest if we archived anything
    if archived_files:
        _write_manifest(
            archive_dir=archive_dir,
            reason="Project-level agent duplicates user-level agent",
            source_level="project",
            superseded_by="~/.claude/agents/",
            files=archived_files,
        )

    return result


def cleanup_skill_overlap(
    project_dir: Path,
    dry_run: bool = False,
) -> dict:
    """Archive and remove project-level copies of USER_LEVEL_SKILLS.

    Skills are directories (not single files), so this uses shutil.copytree
    for archiving and shutil.rmtree for removal.

    Args:
        project_dir: Root of the project to clean up.
        dry_run: If True, log what would happen without modifying files.

    Returns:
        Dict with keys "archived", "skipped", "errors" (lists of skill names).
    """
    user_level_skills = _get_user_level_skills()
    user_skills_base = Path.home() / ".claude" / "skills"
    project_skills_base = project_dir / ".claude" / "skills"

    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    archive_dir = project_skills_base / "archived" / f"{date_str}_overlap_cleanup"

    result: dict[str, list[str]] = {"archived": [], "skipped": [], "errors": []}

    if not project_skills_base.exists():
        logger.debug("No project skills directory at %s", project_skills_base)
        return result

    archived_files: list[str] = []

    for skill_name in sorted(user_level_skills):
        user_skill_dir = user_skills_base / skill_name
        project_skill_dir = project_skills_base / skill_name

        # Both must exist to be considered overlap
        if not project_skill_dir.exists():
            logger.debug("No project copy of skill %s, skipping", skill_name)
            result["skipped"].append(skill_name)
            continue

        if not (user_skill_dir / "SKILL.md").exists():
            logger.debug(
                "No user-level copy of skill %s, skipping (not overlap)", skill_name
            )
            result["skipped"].append(skill_name)
            continue

        # Check if already archived (idempotent)
        archived_dest = archive_dir / skill_name
        if archived_dest.exists():
            logger.debug("Already archived: %s", skill_name)
            result["skipped"].append(skill_name)
            continue

        if dry_run:
            logger.info(
                "[DRY RUN] Would archive project skill %s to %s",
                skill_name,
                archive_dir,
            )
            result["archived"].append(skill_name)
            continue

        try:
            archive_dir.mkdir(parents=True, exist_ok=True)
            shutil.copytree(project_skill_dir, archived_dest)
            shutil.rmtree(project_skill_dir)
            archived_files.append(skill_name)
            result["archived"].append(skill_name)
            logger.info(
                "Archived project skill %s (user copy at %s)",
                skill_name,
                user_skill_dir,
            )
        except OSError as exc:
            logger.error("Failed to archive skill %s: %s", skill_name, exc)
            result["errors"].append(skill_name)

    # Write manifest if we archived anything
    if archived_files:
        _write_manifest(
            archive_dir=archive_dir,
            reason="Project-level skill duplicates user-level skill",
            source_level="project",
            superseded_by="~/.claude/skills/",
            files=archived_files,
        )

    return result


def cleanup_stale_agent_names(dry_run: bool = False) -> dict:
    """Archive user-level agents with stale '-agent' suffix.

    For each name in STALE_AGENT_NAMES (e.g. "research-agent"), if BOTH the
    stale file (~/.claude/agents/research-agent.md) AND the correct file
    (~/.claude/agents/research.md) exist, the stale file is archived.

    Args:
        dry_run: If True, log what would happen without modifying files.

    Returns:
        Dict with keys "archived", "skipped", "errors" (lists of stale names).
    """
    user_agents_base = Path.home() / ".claude" / "agents"

    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    archive_dir = user_agents_base / "archived" / f"{date_str}_stale_naming"

    result: dict[str, list[str]] = {"archived": [], "skipped": [], "errors": []}

    archived_files: list[str] = []

    for stale_name in sorted(STALE_AGENT_NAMES):
        # Derive the correct name by removing "-agent" suffix
        correct_name = stale_name.removesuffix("-agent")

        stale_file = user_agents_base / f"{stale_name}.md"
        correct_file = user_agents_base / f"{correct_name}.md"

        if not stale_file.exists():
            logger.debug("No stale file for %s, skipping", stale_name)
            result["skipped"].append(stale_name)
            continue

        if not correct_file.exists():
            logger.debug(
                "No correct replacement for %s (%s.md missing), skipping",
                stale_name,
                correct_name,
            )
            result["skipped"].append(stale_name)
            continue

        # Check if already archived (idempotent)
        archived_dest = archive_dir / f"{stale_name}.md"
        if archived_dest.exists():
            logger.debug("Already archived: %s", stale_name)
            result["skipped"].append(stale_name)
            continue

        if dry_run:
            logger.info(
                "[DRY RUN] Would archive stale agent %s (replaced by %s)",
                stale_name,
                correct_name,
            )
            result["archived"].append(stale_name)
            continue

        try:
            archive_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(stale_file, archived_dest)
            stale_file.unlink()
            archived_files.append(f"{stale_name}.md")
            result["archived"].append(stale_name)
            logger.info(
                "Archived stale agent %s (replaced by %s)",
                stale_name,
                correct_name,
            )
        except OSError as exc:
            logger.error("Failed to archive stale agent %s: %s", stale_name, exc)
            result["errors"].append(stale_name)

    # Write manifest if we archived anything
    if archived_files:
        _write_manifest(
            archive_dir=archive_dir,
            reason="Agent with stale '-agent' suffix replaced by canonical name",
            source_level="user",
            superseded_by="~/.claude/agents/ (canonical names without -agent suffix)",
            files=archived_files,
        )

    return result


def run_overlap_cleanup(
    project_dir: Path,
    dry_run: bool = False,
) -> dict:
    """Orchestrator: run all overlap cleanup operations.

    Args:
        project_dir: Root of the project to clean up.
        dry_run: If True, log what would happen without modifying files.

    Returns:
        Combined results dict with keys "agents", "skills", "stale_agents",
        each containing {"archived": [...], "skipped": [...], "errors": [...]}.
    """
    logger.info(
        "Starting overlap cleanup for project %s (dry_run=%s)", project_dir, dry_run
    )

    agents_result = cleanup_agent_overlap(project_dir, dry_run=dry_run)
    skills_result = cleanup_skill_overlap(project_dir, dry_run=dry_run)
    stale_result = cleanup_stale_agent_names(dry_run=dry_run)

    total_archived = (
        len(agents_result["archived"])
        + len(skills_result["archived"])
        + len(stale_result["archived"])
    )
    total_errors = (
        len(agents_result["errors"])
        + len(skills_result["errors"])
        + len(stale_result["errors"])
    )

    logger.info(
        "Overlap cleanup complete: archived=%d, errors=%d",
        total_archived,
        total_errors,
    )

    return {
        "agents": agents_result,
        "skills": skills_result,
        "stale_agents": stale_result,
    }
