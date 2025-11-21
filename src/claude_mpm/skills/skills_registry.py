"""Skills Registry - Helper class for registry operations.

This module provides a helper class for working with the skills registry YAML file.
It offers convenient methods for loading, querying, and validating the registry.

The skills registry (config/skills_registry.yaml) is the source of truth for:
- Skill-to-agent mappings
- Skill metadata (descriptions, categories, sources)
- Skill source repositories
- Version information

Design:
- Read-only registry operations (no modifications)
- Structured access to registry data
- Validation of registry structure
- Error handling with fallback to empty results
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from claude_mpm.core.mixins import LoggerMixin


class SkillsRegistry(LoggerMixin):
    """Helper class for skills registry operations.

    Provides structured access to the skills registry YAML file with
    methods for querying agent skills, skill metadata, and validation.

    Example:
        >>> registry = SkillsRegistry()
        >>> skills = registry.get_agent_skills('engineer')
        >>> print(skills)  # ['test-driven-development', 'systematic-debugging', ...]
        >>>
        >>> metadata = registry.get_skill_metadata('test-driven-development')
        >>> print(metadata['category'])  # 'testing'
    """

    def __init__(self, registry_path: Optional[Path] = None) -> None:
        """Initialize Skills Registry.

        Args:
            registry_path: Optional path to registry YAML file.
                         If None, uses default config/skills_registry.yaml
        """
        super().__init__()

        if registry_path is None:
            # Default to config/skills_registry.yaml
            registry_path = (
                Path(__file__).parent.parent.parent.parent
                / "config"
                / "skills_registry.yaml"
            )

        self.registry_path: Path = registry_path
        self.data: Dict[str, Any] = self.load_registry(registry_path)

    @staticmethod
    def load_registry(registry_path: Path) -> Dict[str, Any]:
        """Load and parse registry YAML file.

        Args:
            registry_path: Path to skills_registry.yaml

        Returns:
            Dict containing parsed registry data, or empty dict on error

        Example:
            >>> data = SkillsRegistry.load_registry(Path('config/skills_registry.yaml'))
            >>> print(data['version'])  # '1.0.0'
        """
        if not registry_path.exists():
            return {}

        try:
            with open(registry_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data if data is not None else {}
        except (OSError, yaml.YAMLError):
            # Graceful degradation - return empty dict
            return {}

    def get_agent_skills(self, agent_id: str) -> List[str]:
        """Get skills for a specific agent.

        Reads from registry['agent_skills'][agent_id] and combines
        'required' and 'optional' skill lists.

        Args:
            agent_id: Agent identifier (e.g., 'engineer', 'python_engineer')

        Returns:
            List of skill names assigned to this agent (required + optional)

        Example:
            >>> registry = SkillsRegistry()
            >>> skills = registry.get_agent_skills('engineer')
            >>> print(skills)
            ['test-driven-development', 'systematic-debugging', 'code-review', 'git-worktrees']
        """
        agent_skills = self.data.get("agent_skills", {}).get(agent_id, {})

        required = agent_skills.get("required", [])
        optional = agent_skills.get("optional", [])

        return required + optional

    def get_skill_metadata(self, skill_name: str) -> Dict[str, Any]:
        """Get metadata for a specific skill.

        Retrieves skill information from registry['skills_metadata'][skill_name].

        Args:
            skill_name: Skill identifier (e.g., 'test-driven-development')

        Returns:
            Dict containing skill metadata:
            - category: Skill category
            - source: Source repository name
            - url: Source URL
            - description: Brief description

        Example:
            >>> registry = SkillsRegistry()
            >>> metadata = registry.get_skill_metadata('test-driven-development')
            >>> print(f"{metadata['category']}: {metadata['description']}")
            testing: Enforces RED/GREEN/REFACTOR TDD cycle
        """
        return self.data.get("skills_metadata", {}).get(skill_name, {})

    def list_all_skills(self) -> List[str]:
        """List all skills in the registry.

        Returns:
            List of all skill names defined in skills_metadata

        Example:
            >>> registry = SkillsRegistry()
            >>> all_skills = registry.list_all_skills()
            >>> print(f"Total skills: {len(all_skills)}")
            Total skills: 15
        """
        return list(self.data.get("skills_metadata", {}).keys())

    def list_all_agents(self) -> List[str]:
        """List all agents in the registry.

        Returns:
            List of all agent IDs with skill assignments

        Example:
            >>> registry = SkillsRegistry()
            >>> agents = registry.list_all_agents()
            >>> print(f"Agents with skills: {len(agents)}")
        """
        return list(self.data.get("agent_skills", {}).keys())

    def get_skills_by_category(self, category: str) -> List[str]:
        """Get all skills in a specific category.

        Args:
            category: Category name (e.g., 'testing', 'debugging', 'development')

        Returns:
            List of skill names in this category

        Example:
            >>> registry = SkillsRegistry()
            >>> testing_skills = registry.get_skills_by_category('testing')
            >>> print(testing_skills)
            ['test-driven-development', 'webapp-testing', 'async-testing', ...]
        """
        skills = []
        for skill_name, metadata in self.data.get("skills_metadata", {}).items():
            if metadata.get("category") == category:
                skills.append(skill_name)

        return skills

    def get_skills_by_source(self, source: str) -> List[str]:
        """Get all skills from a specific source repository.

        Args:
            source: Source repository name (e.g., 'superpowers', 'anthropic', 'community')

        Returns:
            List of skill names from this source

        Example:
            >>> registry = SkillsRegistry()
            >>> superpowers_skills = registry.get_skills_by_source('superpowers')
            >>> print(f"Skills from superpowers: {len(superpowers_skills)}")
        """
        skills = []
        for skill_name, metadata in self.data.get("skills_metadata", {}).items():
            if metadata.get("source") == source:
                skills.append(skill_name)

        return skills

    def validate_registry(self) -> Dict[str, Any]:
        """Validate registry structure and content.

        Checks:
        - Required top-level keys present
        - Version format valid
        - Agent skills references valid
        - Skill metadata complete
        - No orphaned references

        Returns:
            Dict containing:
            - valid: True if all checks pass
            - errors: List of error messages
            - warnings: List of warning messages

        Example:
            >>> registry = SkillsRegistry()
            >>> result = registry.validate_registry()
            >>> if not result['valid']:
            ...     print(f"Registry errors: {result['errors']}")
        """
        errors = []
        warnings = []

        # Check required top-level keys
        required_keys = ["version", "last_updated", "agent_skills", "skills_metadata"]
        for key in required_keys:
            if key not in self.data:
                errors.append(f"Missing required key: {key}")

        # Validate version format
        version = self.data.get("version", "")
        if not version or not isinstance(version, str):
            errors.append("Invalid or missing version field")

        # Check agent skill references
        agent_skills = self.data.get("agent_skills", {})
        skills_metadata = self.data.get("skills_metadata", {})

        for agent_id, agent_data in agent_skills.items():
            # Validate structure
            if not isinstance(agent_data, dict):
                errors.append(f"Agent '{agent_id}' has invalid structure")
                continue

            # Check skill references
            all_skills = agent_data.get("required", []) + agent_data.get("optional", [])

            for skill in all_skills:
                if skill not in skills_metadata:
                    warnings.append(
                        f"Agent '{agent_id}' references undefined skill: {skill}"
                    )

        # Check for orphaned skills (in metadata but not assigned to any agent)
        assigned_skills = set()
        for agent_data in agent_skills.values():
            assigned_skills.update(agent_data.get("required", []))
            assigned_skills.update(agent_data.get("optional", []))

        for skill_name in skills_metadata:
            if skill_name not in assigned_skills:
                warnings.append(f"Skill '{skill_name}' not assigned to any agent")

        # Validate skill metadata completeness
        required_metadata_fields = ["category", "source", "description"]
        for skill_name, metadata in skills_metadata.items():
            for field in required_metadata_fields:
                if field not in metadata or not metadata[field]:
                    warnings.append(f"Skill '{skill_name}' missing {field} in metadata")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def get_registry_info(self) -> Dict[str, Any]:
        """Get summary information about the registry.

        Returns:
            Dict containing:
            - version: Registry version
            - last_updated: Last update timestamp
            - total_skills: Count of skills
            - total_agents: Count of agents with skills
            - categories: List of skill categories
            - sources: List of skill sources

        Example:
            >>> registry = SkillsRegistry()
            >>> info = registry.get_registry_info()
            >>> print(f"Registry v{info['version']}")
            >>> print(f"Total skills: {info['total_skills']}")
        """
        skills_metadata = self.data.get("skills_metadata", {})
        agent_skills = self.data.get("agent_skills", {})

        # Get unique categories
        categories = set()
        for metadata in skills_metadata.values():
            if "category" in metadata:
                categories.add(metadata["category"])

        # Get unique sources
        sources = set()
        for metadata in skills_metadata.values():
            if "source" in metadata:
                sources.add(metadata["source"])

        return {
            "version": self.data.get("version", "unknown"),
            "last_updated": self.data.get("last_updated", "unknown"),
            "total_skills": len(skills_metadata),
            "total_agents": len(agent_skills),
            "categories": sorted(categories),
            "sources": sorted(sources),
        }

    def search_skills(self, query: str) -> List[Dict[str, Any]]:
        """Search skills by name or description.

        Args:
            query: Search query string

        Returns:
            List of matching skills with their metadata

        Example:
            >>> registry = SkillsRegistry()
            >>> results = registry.search_skills('debug')
            >>> for skill in results:
            ...     print(f"{skill['name']}: {skill['description']}")
        """
        query_lower = query.lower()
        results = []

        for skill_name, metadata in self.data.get("skills_metadata", {}).items():
            # Search in name and description
            if (
                query_lower in skill_name.lower()
                or query_lower in metadata.get("description", "").lower()
            ):
                results.append({"name": skill_name, **metadata})

        return results
