"""Path resolution utilities for configure command.

WHY: Centralizes path resolution logic for agent templates, configs, and system files.
Separates file system concerns from business logic.

DESIGN: Pure functions for path resolution without side effects (except mkdir).
"""

from pathlib import Path


def get_agent_template_path(
    agent_name: str,
    scope: str,
    project_dir: Path,
    templates_dir: Path,
) -> Path:
    """Get the path to an agent's template file.

    Args:
        agent_name: Name of the agent
        scope: Configuration scope ("project" or "user")
        project_dir: Project directory path
        templates_dir: System templates directory

    Returns:
        Path to the agent template file
    """
    # First check for custom template in project/user config
    if scope == "project":
        config_dir = project_dir / ".claude-mpm" / "agents"
    else:
        config_dir = Path.home() / ".claude-mpm" / "agents"

    config_dir.mkdir(parents=True, exist_ok=True)
    custom_template = config_dir / f"{agent_name}.json"

    # If custom template exists, return it
    if custom_template.exists():
        return custom_template

    # Otherwise, look for the system template
    # Handle various naming conventions
    possible_names = [
        f"{agent_name}.json",
        f"{agent_name.replace('-', '_')}.json",
        f"{agent_name}-agent.json",
        f"{agent_name.replace('-', '_')}_agent.json",
    ]

    for name in possible_names:
        system_template = templates_dir / name
        if system_template.exists():
            return system_template

    # Return the custom template path for new templates
    return custom_template


def get_config_directory(scope: str, project_dir: Path) -> Path:
    """Get configuration directory based on scope.

    Args:
        scope: Configuration scope ("project" or "user")
        project_dir: Project directory path

    Returns:
        Path to configuration directory
    """
    if scope == "project":
        return project_dir / ".claude-mpm"
    return Path.home() / ".claude-mpm"


def get_agents_directory(scope: str, project_dir: Path) -> Path:
    """Get agents directory based on scope.

    Args:
        scope: Configuration scope ("project" or "user")
        project_dir: Project directory path

    Returns:
        Path to agents directory
    """
    config_dir = get_config_directory(scope, project_dir)
    agents_dir = config_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    return agents_dir


def get_behaviors_directory(scope: str, project_dir: Path) -> Path:
    """Get behaviors directory based on scope.

    Args:
        scope: Configuration scope ("project" or "user")
        project_dir: Project directory path

    Returns:
        Path to behaviors directory
    """
    config_dir = get_config_directory(scope, project_dir)
    behaviors_dir = config_dir / "behaviors"
    behaviors_dir.mkdir(parents=True, exist_ok=True)
    return behaviors_dir
