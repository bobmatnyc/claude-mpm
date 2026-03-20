"""Scope-based path resolution for Claude Code deployment directories.

WHY: Centralizes the mapping from configuration scope (project vs user)
to file system paths for agents, skills, and archives. Replaces hardcoded
paths scattered across API handlers.

DESIGN: Pure functions + str-based enum for backward compatibility.
The str base on ConfigScope ensures existing CLI code that compares
against raw "project"/"user" strings continues working unchanged.

NOTE: This module resolves CLAUDE CODE deployment directories (.claude/agents/,
~/.claude/skills/). For MPM configuration directories (.claude-mpm/agents/,
.claude-mpm/behaviors/), see configure_template_editor.py.
"""

from enum import StrEnum
from pathlib import Path


class ConfigScope(StrEnum):
    """Storage scope for configuration and deployment paths.

    The str base class ensures backward compatibility with existing
    CLI string comparisons (e.g., scope == "project" still works).

    Scope Semantics:
        PROJECT: All paths are rooted under the project directory.
            - agents:  {project}/.claude/agents/
            - skills:  {project}/.claude/skills/
            - archive: {project}/.claude/agents/unused/
            - config:  {project}/.claude-mpm/

        USER: All paths are rooted under the user home directory.
            - agents:  ~/.claude/agents/
            - skills:  ~/.claude/skills/
            - archive: ~/.claude/agents/unused/
            - config:  ~/.claude-mpm/

    Note:
        The CLI currently defaults to PROJECT scope. Several CLI methods
        (e.g., _deploy_single_agent, _install_skill_from_dict) do NOT
        yet respect the scope setting — they hardcode project_dir or
        Path.cwd() as the deployment target. The resolve_* functions in
        this module provide the CORRECT scope-aware path resolution, but
        callers must be updated to use them.
    """

    PROJECT = "project"
    USER = "user"


def resolve_agents_dir(scope: ConfigScope, project_path: Path) -> Path:
    """Resolve the Claude Code agents deployment directory.

    Args:
        scope: PROJECT deploys to <project>/.claude/agents/,
               USER deploys to ~/.claude/agents/
        project_path: Root directory of the project (used for PROJECT scope)

    Returns:
        Path to the agents directory
    """
    if scope == ConfigScope.PROJECT:
        return project_path / ".claude" / "agents"
    return Path.home() / ".claude" / "agents"


def resolve_skills_dir(
    scope: ConfigScope = ConfigScope.PROJECT,
    project_path: Path | None = None,
) -> Path:
    """Resolve the Claude Code skills directory.

    Claude Code reads skills from both project-level and user-level
    directories. The project uses project-scoped deployment by default
    to keep skills isolated per project.

    Args:
        scope: PROJECT deploys to <project>/.claude/skills/,
               USER deploys to ~/.claude/skills/
        project_path: Root directory of the project (used for PROJECT scope).
                      Defaults to Path.cwd() if not provided.

    Returns:
        Path to the skills directory
    """
    if scope == ConfigScope.PROJECT:
        return (project_path or Path.cwd()) / ".claude" / "skills"
    return Path.home() / ".claude" / "skills"


def resolve_archive_dir(scope: ConfigScope, project_path: Path) -> Path:
    """Resolve the agent archive directory.

    Archived agents are moved to an 'unused/' subdirectory within the
    agents directory for the given scope.

    Args:
        scope: PROJECT archives to <project>/.claude/agents/unused/,
               USER archives to ~/.claude/agents/unused/
        project_path: Root directory of the project (used for PROJECT scope)

    Returns:
        Path to the archive directory
    """
    return resolve_agents_dir(scope, project_path) / "unused"


def resolve_config_dir(scope: ConfigScope, project_path: Path) -> Path:
    """Resolve the MPM configuration directory.

    Args:
        scope: PROJECT resolves to <project>/.claude-mpm/,
               USER resolves to ~/.claude-mpm/
        project_path: Root directory of the project (used for PROJECT scope)

    Returns:
        Path to the MPM configuration directory
    """
    if scope == ConfigScope.PROJECT:
        return project_path / ".claude-mpm"
    return Path.home() / ".claude-mpm"
