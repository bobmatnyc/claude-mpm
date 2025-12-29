"""
Profile Manager Service
======================

Manages agent and skill filtering based on deployment profiles.

A profile defines which agents and skills should be deployed, reducing
context usage by limiting available agents to only what's needed for
a specific project or workflow.

Profile Structure:
    profile:
      name: framework-development
      description: Python backend + TypeScript/Svelte dashboard

    agents:
      enabled:
        - python-engineer
        - typescript-engineer
      disabled:
        - java-engineer
        - dart-engineer

    skills:
      enabled:
        - flask
        - pytest
      disabled_categories:
        - wordpress-*
        - react-*

Usage:
    # Auto-detect project directory (searches for .claude-mpm in cwd and parents)
    profile_manager = ProfileManager()

    # Or explicitly specify project directory
    profile_manager = ProfileManager(project_dir=Path("/path/to/project"))

    profile_manager.load_profile("framework-development")

    if profile_manager.is_agent_enabled("python-engineer"):
        # Deploy agent
        pass

    if profile_manager.is_skill_enabled("flask"):
        # Deploy skill
        pass
"""

import fnmatch
from pathlib import Path
from typing import Optional, Set, Dict, Any

import yaml

from ..core.logger import get_logger

logger = get_logger(__name__)


class ProfileManager:
    """
    Manages deployment profiles for agent and skill filtering.

    Provides methods to:
    - Load profiles from YAML files
    - Check if agents are enabled/disabled
    - Check if skills are enabled/disabled (with glob pattern support)
    - Get lists of enabled/disabled entities
    """

    def __init__(self, project_dir: Optional[Path] = None, profiles_dir: Optional[Path] = None):
        """
        Initialize ProfileManager.

        Args:
            project_dir: Project root directory. If not provided, tries to find
                         .claude-mpm directory in current or parent directories.
            profiles_dir: Directory containing profile YAML files. If provided,
                         takes precedence over project_dir.
        """
        if profiles_dir:
            self.profiles_dir = profiles_dir
        elif project_dir:
            self.profiles_dir = Path(project_dir) / ".claude-mpm" / "profiles"
        else:
            # Try to find .claude-mpm directory automatically
            self.profiles_dir = self._find_profiles_dir()

        self.active_profile: Optional[str] = None
        self._profile_data: Dict[str, Any] = {}

        # Cached sets for performance
        self._enabled_agents: Set[str] = set()
        self._disabled_agents: Set[str] = set()
        self._enabled_skills: Set[str] = set()
        self._disabled_skill_patterns: list[str] = []

    def _find_profiles_dir(self) -> Path:
        """Find profiles directory by searching for .claude-mpm in cwd and parents.

        Returns:
            Path to profiles directory (may not exist yet)
        """
        current = Path.cwd()

        # Search current directory and up to 5 parent directories
        for _ in range(6):
            profiles_dir = current / ".claude-mpm" / "profiles"
            if profiles_dir.exists():
                logger.debug(f"Found profiles directory at: {profiles_dir}")
                return profiles_dir
            if current.parent == current:  # Reached filesystem root
                break
            current = current.parent

        # Fallback to cwd (directory may not exist yet, which is fine)
        fallback = Path.cwd() / ".claude-mpm" / "profiles"
        logger.debug(f"Profiles directory not found, using fallback: {fallback}")
        return fallback

    def load_profile(self, profile_name: str) -> bool:
        """
        Load profile from YAML file.

        Args:
            profile_name: Name of profile (without .yaml extension)

        Returns:
            bool: True if profile loaded successfully, False otherwise
        """
        profile_path = self.profiles_dir / f"{profile_name}.yaml"

        logger.debug(f"Looking for profile at: {profile_path}")

        if not profile_path.exists():
            logger.warning(f"Profile not found: {profile_path}")
            return False

        try:
            with profile_path.open("r") as f:
                self._profile_data = yaml.safe_load(f) or {}

            # Extract profile metadata
            profile_info = self._profile_data.get("profile", {})
            self.active_profile = profile_info.get("name", profile_name)

            # Parse agents
            agents_config = self._profile_data.get("agents", {})
            self._enabled_agents = set(agents_config.get("enabled", []))
            self._disabled_agents = set(agents_config.get("disabled", []))

            # Parse skills
            skills_config = self._profile_data.get("skills", {})
            self._enabled_skills = set(skills_config.get("enabled", []))
            self._disabled_skill_patterns = skills_config.get("disabled_categories", [])

            logger.info(
                f"Loaded profile '{self.active_profile}': "
                f"{len(self._enabled_agents)} agents, "
                f"{len(self._enabled_skills)} skills enabled"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to load profile {profile_name}: {e}")
            return False

    def is_agent_enabled(self, agent_name: str) -> bool:
        """
        Check if agent is enabled in active profile.

        If no profile is loaded, all agents are enabled by default.

        Args:
            agent_name: Name of agent to check

        Returns:
            bool: True if agent should be deployed
        """
        if not self.active_profile:
            # No profile active - all agents enabled
            return True

        # If enabled list exists, agent must be in it
        if self._enabled_agents:
            return agent_name in self._enabled_agents

        # Otherwise, agent must NOT be in disabled list
        return agent_name not in self._disabled_agents

    def is_skill_enabled(self, skill_name: str) -> bool:
        """
        Check if skill is enabled in active profile.

        Supports both short names (flask) and full names (toolchains-python-frameworks-flask).
        Supports glob pattern matching for disabled_categories.

        If no profile is loaded, all skills are enabled by default.

        Args:
            skill_name: Name of skill to check (e.g., "flask", "toolchains-python-frameworks-flask")

        Returns:
            bool: True if skill should be deployed
        """
        if not self.active_profile:
            # No profile active - all skills enabled
            return True

        # Check if skill is explicitly disabled by pattern
        for pattern in self._disabled_skill_patterns:
            if fnmatch.fnmatch(skill_name, pattern):
                logger.debug(f"Skill '{skill_name}' matched disabled pattern '{pattern}'")
                return False

        # If enabled list exists, check for match
        if self._enabled_skills:
            # Exact match
            if skill_name in self._enabled_skills:
                return True

            # Check if full skill name ends with short name from enabled list
            # Example: "toolchains-python-frameworks-flask" matches "flask"
            for short_name in self._enabled_skills:
                if skill_name.endswith(f"-{short_name}"):
                    return True
                # Also check if short name is contained as a segment
                if f"-{short_name}-" in skill_name or skill_name.startswith(f"{short_name}-"):
                    return True

            return False

        # No enabled list and didn't match disabled pattern - allow it
        return True

    def get_enabled_agents(self) -> Set[str]:
        """
        Get set of enabled agent names.

        Returns:
            Set[str]: Agent names that should be deployed
        """
        return self._enabled_agents.copy()

    def get_disabled_agents(self) -> Set[str]:
        """
        Get set of disabled agent names.

        Returns:
            Set[str]: Agent names that should NOT be deployed
        """
        return self._disabled_agents.copy()

    def get_enabled_skills(self) -> Set[str]:
        """
        Get set of explicitly enabled skill names.

        Returns:
            Set[str]: Skill names that should be deployed
        """
        return self._enabled_skills.copy()

    def get_disabled_skill_patterns(self) -> list[str]:
        """
        Get list of disabled skill glob patterns.

        Returns:
            list[str]: Glob patterns for skills that should NOT be deployed
        """
        return self._disabled_skill_patterns.copy()

    def get_filtering_summary(self) -> Dict[str, Any]:
        """
        Get summary of current profile filtering.

        Returns:
            Dict containing:
            - active_profile: Name of active profile (or None)
            - enabled_agents_count: Number of explicitly enabled agents
            - disabled_agents_count: Number of explicitly disabled agents
            - enabled_skills_count: Number of explicitly enabled skills
            - disabled_patterns_count: Number of disabled skill patterns
        """
        return {
            "active_profile": self.active_profile,
            "enabled_agents_count": len(self._enabled_agents),
            "disabled_agents_count": len(self._disabled_agents),
            "enabled_skills_count": len(self._enabled_skills),
            "disabled_patterns_count": len(self._disabled_skill_patterns),
        }

    def list_available_profiles(self) -> list[str]:
        """
        List all available profile names in profiles directory.

        Returns:
            list[str]: Profile names (without .yaml extension)
        """
        if not self.profiles_dir.exists():
            return []

        profiles = []
        for profile_path in self.profiles_dir.glob("*.yaml"):
            profiles.append(profile_path.stem)

        return sorted(profiles)

    def get_profile_description(self, profile_name: str) -> Optional[str]:
        """
        Get description of a profile without loading it fully.

        Args:
            profile_name: Name of profile

        Returns:
            Optional[str]: Profile description or None if not found
        """
        profile_path = self.profiles_dir / f"{profile_name}.yaml"

        if not profile_path.exists():
            return None

        try:
            with profile_path.open("r") as f:
                data = yaml.safe_load(f) or {}
                profile_info = data.get("profile", {})
                return profile_info.get("description")
        except Exception:
            return None
