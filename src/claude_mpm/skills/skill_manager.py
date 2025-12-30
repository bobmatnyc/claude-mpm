"""Skills manager - integrates skills with agents."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from claude_mpm.core.logging_utils import get_logger

from .registry import Skill, get_registry

logger = get_logger(__name__)


class SkillManager:
    """Manages skills and their integration with agents."""

    def __init__(self):
        """Initialize the skill manager."""
        self.registry = get_registry()
        self.agent_skill_mapping: Dict[str, List[str]] = {}
        self._load_agent_mappings()

    def _load_agent_mappings(self):
        """Load skill mappings from agent templates."""
        # Load mappings from agent JSON templates that have 'skills' field
        agent_templates_dir = Path(__file__).parent.parent / "agents" / "templates"

        if not agent_templates_dir.exists():
            logger.warning(
                f"Agent templates directory not found: {agent_templates_dir}"
            )
            return

        mapping_count = 0
        for template_file in agent_templates_dir.glob("*.json"):
            try:
                with open(template_file, encoding="utf-8") as f:
                    agent_data = json.load(f)

                agent_id = agent_data.get("agent_id") or agent_data.get("agent_type")
                if not agent_id:
                    continue

                # Extract skills list if present
                skills = agent_data.get("skills", [])
                if skills:
                    self.agent_skill_mapping[agent_id] = skills
                    mapping_count += 1
                    logger.debug(
                        f"Agent '{agent_id}' mapped to {len(skills)} skills: {', '.join(skills)}"
                    )

            except Exception as e:
                logger.error(f"Error loading agent mapping from {template_file}: {e}")

        if mapping_count > 0:
            logger.info(f"Loaded skill mappings for {mapping_count} agents")

    def _get_pm_skills(
        self, project_dir: Optional[Path] = None
    ) -> List[Dict[str, Any]]:
        """Load PM skills from project's .claude-mpm/skills/pm/ directory.

        PM skills are special required skills deployed per-project,
        NOT fetched from the skills repository.

        Args:
            project_dir: Project directory. Defaults to current working directory.

        Returns:
            List of PM skill dictionaries with metadata
        """
        if project_dir is None:
            project_dir = Path.cwd()

        pm_skills_dir = project_dir / ".claude-mpm" / "skills" / "pm"

        if not pm_skills_dir.exists():
            logger.debug("PM skills directory not found")
            return []

        skills = []
        for skill_dir in pm_skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    skill = self._load_pm_skill(skill_file)
                    if skill:
                        skills.append(skill)

        if skills:
            logger.debug(f"Loaded {len(skills)} PM skills from {pm_skills_dir}")

        return skills

    def _load_pm_skill(self, skill_file: Path) -> Optional[Dict[str, Any]]:
        """Load a single PM skill from SKILL.md file.

        Args:
            skill_file: Path to SKILL.md file

        Returns:
            Dictionary with skill metadata and content, or None if failed
        """
        try:
            content = skill_file.read_text(encoding="utf-8")

            # Parse YAML frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    metadata = yaml.safe_load(parts[1])
                    body = parts[2].strip()

                    return {
                        "name": metadata.get("name", skill_file.parent.name),
                        "version": metadata.get("version", "1.0.0"),
                        "description": metadata.get("description", ""),
                        "when_to_use": metadata.get("when_to_use", ""),
                        "content": body,
                        "is_pm_skill": True,
                    }
        except Exception as e:
            logger.warning(f"Failed to load PM skill {skill_file}: {e}")

        return None

    def get_agent_skills(self, agent_type: str) -> List[Skill]:
        """
        Get all skills for an agent (bundled + discovered + PM skills if PM agent).

        Args:
            agent_type: Agent type/ID (e.g., 'engineer', 'python_engineer', 'pm')

        Returns:
            List of Skill objects for this agent
        """
        skill_names = self.agent_skill_mapping.get(agent_type, [])

        # Get skills from registry
        skills = []
        for name in skill_names:
            skill = self.registry.get_skill(name)
            if skill:
                skills.append(skill)
            else:
                logger.warning(
                    f"Skill '{name}' referenced by agent '{agent_type}' not found"
                )

        # Also include skills that have no agent restriction
        # or explicitly list this agent type
        additional_skills = self.registry.get_skills_for_agent(agent_type)
        for skill in additional_skills:
            if skill not in skills:
                skills.append(skill)

        # Add PM skills for PM agent only
        if agent_type.lower() in ("pm", "project-manager", "project_manager"):
            pm_skill_dicts = self._get_pm_skills()
            for pm_skill_dict in pm_skill_dicts:
                # Convert PM skill dict to Skill object
                pm_skill = Skill(
                    name=pm_skill_dict["name"],
                    path=Path.cwd()
                    / ".claude-mpm"
                    / "skills"
                    / "pm"
                    / pm_skill_dict["name"],
                    content=pm_skill_dict["content"],
                    source="pm",  # Special source type for PM skills
                    version=pm_skill_dict["version"],
                    skill_id=pm_skill_dict["name"],
                    description=pm_skill_dict["description"],
                    agent_types=["pm", "project-manager", "project_manager"],
                )
                skills.append(pm_skill)

            if pm_skill_dicts:
                logger.debug(f"Added {len(pm_skill_dicts)} PM skills for PM agent")

        return skills

    def enhance_agent_prompt(
        self, agent_type: str, base_prompt: str, include_all: bool = False
    ) -> str:
        """
        Enhance agent prompt with available skills.

        Args:
            agent_type: Agent type/ID
            base_prompt: Original agent prompt
            include_all: If True, include all available skills regardless of mapping

        Returns:
            Enhanced prompt with skills section appended
        """
        if include_all:
            skills = self.registry.list_skills()
        else:
            skills = self.get_agent_skills(agent_type)

        if not skills:
            return base_prompt

        # Build skills section
        skills_section = "\n\n" + "=" * 80 + "\n"
        skills_section += "## 🎯 Available Skills\n\n"
        skills_section += f"You have access to {len(skills)} specialized skills:\n\n"

        for skill in skills:
            skills_section += f"### 📚 {skill.name.replace('-', ' ').title()}\n\n"
            skills_section += f"**Source:** {skill.source}\n"
            if skill.description:
                skills_section += f"**Description:** {skill.description}\n"
            skills_section += "\n```\n"
            skills_section += skill.content
            skills_section += "\n```\n\n"

        skills_section += "=" * 80 + "\n"

        return base_prompt + skills_section

    def list_agent_skill_mappings(self) -> Dict[str, List[str]]:
        """
        Get all agent-to-skill mappings.

        Returns:
            Dictionary mapping agent IDs to lists of skill names
        """
        return self.agent_skill_mapping.copy()

    def add_skill_to_agent(self, agent_type: str, skill_name: str) -> bool:
        """
        Add a skill to an agent's mapping.

        Args:
            agent_type: Agent type/ID
            skill_name: Name of the skill to add

        Returns:
            True if successful, False if skill not found
        """
        skill = self.registry.get_skill(skill_name)
        if not skill:
            logger.error(f"Cannot add skill '{skill_name}': skill not found")
            return False

        if agent_type not in self.agent_skill_mapping:
            self.agent_skill_mapping[agent_type] = []

        if skill_name not in self.agent_skill_mapping[agent_type]:
            self.agent_skill_mapping[agent_type].append(skill_name)
            logger.info(f"Added skill '{skill_name}' to agent '{agent_type}'")

        return True

    def remove_skill_from_agent(self, agent_type: str, skill_name: str) -> bool:
        """
        Remove a skill from an agent's mapping.

        Args:
            agent_type: Agent type/ID
            skill_name: Name of the skill to remove

        Returns:
            True if successful, False if not found
        """
        if agent_type not in self.agent_skill_mapping:
            return False

        if skill_name in self.agent_skill_mapping[agent_type]:
            self.agent_skill_mapping[agent_type].remove(skill_name)
            logger.info(f"Removed skill '{skill_name}' from agent '{agent_type}'")
            return True

        return False

    def reload(self):
        """Reload skills and agent mappings."""
        logger.info("Reloading skill manager...")
        self.registry.reload()
        self.agent_skill_mapping.clear()
        self._load_agent_mappings()
        logger.info("Skill manager reloaded")

    def infer_agents_for_skill(self, skill) -> List[str]:
        """Infer which agents should have this skill based on tags/name.

        Args:
            skill: Skill object to analyze

        Returns:
            List of agent IDs that should have this skill
        """
        agents = []
        content_lower = skill.content.lower()
        name_lower = skill.name.lower()

        # Python-related
        if any(
            tag in content_lower or tag in name_lower
            for tag in ["python", "django", "flask", "fastapi"]
        ):
            agents.append("python-engineer")

        # TypeScript/JavaScript-related
        if any(
            tag in content_lower or tag in name_lower
            for tag in ["typescript", "javascript", "react", "next", "vue", "node"]
        ):
            agents.extend(["typescript-engineer", "react-engineer", "nextjs-engineer"])

        # Go-related
        if any(tag in content_lower or tag in name_lower for tag in ["golang", "go "]):
            agents.append("golang-engineer")

        # Ops-related
        if any(
            tag in content_lower or tag in name_lower
            for tag in ["docker", "kubernetes", "deploy", "devops", "ops"]
        ):
            agents.extend(["ops", "devops", "local-ops"])

        # Testing/QA-related
        if any(
            tag in content_lower or tag in name_lower
            for tag in ["test", "qa", "quality", "assert"]
        ):
            agents.extend(["qa", "web-qa", "api-qa"])

        # Documentation-related
        if any(
            tag in content_lower or tag in name_lower
            for tag in ["documentation", "docs", "api doc", "openapi"]
        ):
            agents.extend(["docs", "documentation", "technical-writer"])

        # Remove duplicates
        return list(set(agents))

    def save_mappings_to_config(self, config_path: Optional[Path] = None):
        """Save current agent-skill mappings to configuration file.

        Args:
            config_path: Path to configuration file. If None, uses default.
        """
        import json

        if config_path is None:
            config_path = Path.cwd() / ".claude-mpm" / "skills_config.json"

        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Save mappings
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(self.agent_skill_mapping, f, indent=2)

        logger.info(f"Saved skill mappings to {config_path}")

    def load_mappings_from_config(self, config_path: Optional[Path] = None):
        """Load agent-skill mappings from configuration file.

        Args:
            config_path: Path to configuration file. If None, uses default.
        """
        import json

        if config_path is None:
            config_path = Path.cwd() / ".claude-mpm" / "skills_config.json"

        if not config_path.exists():
            logger.debug(f"No skill mappings config found at {config_path}")
            return

        try:
            with open(config_path, encoding="utf-8") as f:
                loaded_mappings = json.load(f)

            # Merge with existing mappings
            for agent_id, skills in loaded_mappings.items():
                if agent_id not in self.agent_skill_mapping:
                    self.agent_skill_mapping[agent_id] = []
                for skill in skills:
                    if skill not in self.agent_skill_mapping[agent_id]:
                        self.agent_skill_mapping[agent_id].append(skill)

            logger.info(f"Loaded skill mappings from {config_path}")
        except Exception as e:
            logger.error(f"Error loading skill mappings from {config_path}: {e}")


# Global manager instance (singleton pattern)
_manager: Optional[SkillManager] = None


def get_manager() -> SkillManager:
    """Get the global skill manager (singleton)."""
    global _manager
    if _manager is None:
        _manager = SkillManager()
    return _manager
