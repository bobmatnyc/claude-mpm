"""Scope-based path resolution for Claude Code deployment directories.

WHY: Centralizes the mapping from configuration scope (project vs user)
to file system paths for agents, skills, and archives. Replaces hardcoded
paths scattered across API handlers.

DESIGN: Pure functions + str-based enum for backward compatibility.
The str base on ConfigScope ensures existing CLI code that compares
against raw "project"/"user" strings continues working unchanged.

NOTE: This module resolves CLAUDE CODE deployment directories (.claude/agents/,
~/.claude/skills/). For MPM configuration directories (.claude-mpm/agents/,
.claude-mpm/behaviors/), see cli/commands/configure_paths.py.
"""

from enum import Enum
from pathlib import Path


class ConfigScope(str, Enum):
    """Storage scope for configuration and deployment paths.

    The str base class ensures backward compatibility with existing
    CLI string comparisons (e.g., scope == "project" still works).
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


def resolve_skills_dir(scope: ConfigScope = ConfigScope.USER) -> Path:
    """Resolve the Claude Code skills directory.

    Currently always returns ~/.claude/skills/ regardless of scope,
    because Claude Code loads skills from the user home directory at
    startup. The scope parameter exists for future extensibility.

    Args:
        scope: Currently ignored (skills are always user-scoped)

    Returns:
        Path to the skills directory (~/.claude/skills/)
    """
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
