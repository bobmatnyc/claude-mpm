"""Project configuration loading for MPM Commander.

This module handles loading configuration from a project's .claude-mpm/
directory, including YAML config files and directory structure validation.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


def load_project_config(project_path: str) -> Optional[Dict[str, Any]]:
    """Load configuration from project's .claude-mpm/ directory.

    Looks for:
    - .claude-mpm/configuration.yaml (main config file)
    - .claude-mpm/agents/ (directory exists check)
    - .claude-mpm/skills/ (directory exists check)
    - .claude-mpm/memories/ (directory exists check)

    Args:
        project_path: Absolute path to project directory

    Returns:
        Dict with config data and directory flags, or None if no config found.
        Example structure:
        {
            'configuration': {...},  # Parsed YAML config
            'has_agents': True,
            'has_skills': False,
            'has_memories': True,
        }

    Raises:
        yaml.YAMLError: If configuration.yaml is malformed

    Example:
        >>> config = load_project_config("/Users/masa/Projects/my-app")
        >>> if config:
        ...     print(f"Agents dir: {config['has_agents']}")
        ...     print(f"Config: {config.get('configuration', {})}")
        Agents dir: True
        Config: {'default_adapter': 'linear', ...}
    """
    proj_path = Path(project_path)
    config_dir = proj_path / ".claude-mpm"

    # Check if .claude-mpm/ directory exists
    if not config_dir.exists() or not config_dir.is_dir():
        logger.debug("No .claude-mpm/ directory found in project: %s", project_path)
        return None

    logger.info("Loading configuration from %s", config_dir)

    result: Dict[str, Any] = {
        "configuration": {},
        "has_agents": False,
        "has_skills": False,
        "has_memories": False,
    }

    # Load configuration.yaml if present
    config_file = config_dir / "configuration.yaml"
    if config_file.exists() and config_file.is_file():
        try:
            with open(config_file, encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
                result["configuration"] = config_data or {}
            logger.info(
                "Loaded configuration.yaml with %d top-level keys",
                len(result["configuration"]),
            )
        except yaml.YAMLError as e:
            logger.error(
                "Failed to parse configuration.yaml in %s: %s",
                config_dir,
                e,
            )
            raise
        except Exception as e:
            logger.warning(
                "Failed to read configuration.yaml in %s: %s",
                config_dir,
                e,
            )
            # Continue with empty config

    # Check for subdirectories
    agents_dir = config_dir / "agents"
    result["has_agents"] = agents_dir.exists() and agents_dir.is_dir()
    if result["has_agents"]:
        logger.debug("Found agents directory: %s", agents_dir)

    skills_dir = config_dir / "skills"
    result["has_skills"] = skills_dir.exists() and skills_dir.is_dir()
    if result["has_skills"]:
        logger.debug("Found skills directory: %s", skills_dir)

    memories_dir = config_dir / "memories"
    result["has_memories"] = memories_dir.exists() and memories_dir.is_dir()
    if result["has_memories"]:
        logger.debug("Found memories directory: %s", memories_dir)

    logger.info(
        "Project config loaded: agents=%s, skills=%s, memories=%s",
        result["has_agents"],
        result["has_skills"],
        result["has_memories"],
    )

    return result
