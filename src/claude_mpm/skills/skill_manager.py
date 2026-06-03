"""Skills manager - integrates skills with agents.

References
----------
SPEC-SKILLS-06~1 : docs/specs/skills.md#SPEC-SKILLS-06~1
"""

import json
from pathlib import Path
from typing import Any

import yaml

from claude_mpm.core.logging_utils import get_logger
from claude_mpm.utils.agent_filters import normalize_agent_id

from .registry import Skill, get_registry

logger = get_logger(__name__)


class SkillManager:
    """Manages skills and their integration with agents.

    :spec: SPEC-SKILLS-06~1
    """

    def __init__(self):
        """Initialize the skill manager."""
        self.registry = get_registry()
        self.agent_skill_mapping: dict[str, list[str]] = {}
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
                normalized = normalize_agent_id(agent_id)

                # Extract skills list if present
                skills = agent_data.get("skills", [])
                if skills:
                    self.agent_skill_mapping[agent_id] = skills
                    if normalized and normalized != agent_id:
                        self.agent_skill_mapping[normalized] = skills
                    mapping_count += 1
                    logger.debug(
                        f"Agent '{agent_id}' mapped to {len(skills)} skills: {', '.join(skills)}"
                    )

            except Exception as e:
                logger.error(f"Error loading agent mapping from {template_file}: {e}")

        if mapping_count > 0:
            logger.info(f"Loaded skill mappings for {mapping_count} agents")

    def _get_pm_skills(self, project_dir: Path | None = None) -> list[dict[str, Any]]:
        """Load PM skills from project's .claude/skills/ directory.

        PM skills are special framework management skills (mpm-*) deployed
        per-project to .claude/skills/, NOT fetched from the skills repository.

        Args:
            project_dir: Project directory. Defaults to current working directory.

        Returns:
            List of PM skill dictionaries with metadata
        """
        if project_dir is None:
            project_dir = Path.cwd()

        pm_skills_dir = project_dir / ".claude" / "skills"

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

    def _load_pm_skill(self, skill_file: Path) -> dict[str, Any] | None:
        """Load a single PM skill from SKILL.md file.

        Recognizes ``type: migration`` frontmatter and extracts migration skill
        fields (``state_key``, ``services``, ``recommended``, ``check_commands``)
        when present. Migration skills are still returned as regular PM skill
        dicts so existing prompt-injection code keeps working; the additional
        fields are surfaced under ``is_migration`` / ``state_key`` / etc.

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
                    metadata = yaml.safe_load(parts[1]) or {}
                    body = parts[2].strip()

                    skill_dict: dict[str, Any] = {
                        "name": metadata.get("name", skill_file.parent.name),
                        "version": metadata.get("version", "1.0.0"),
                        "description": metadata.get("description", ""),
                        "when_to_use": metadata.get("when_to_use", ""),
                        "content": body,
                        "is_pm_skill": True,
                    }

                    # Migration skill extension: parse additional fields when
                    # ``type: migration`` is declared.
                    if metadata.get("type") == "migration":
                        skill_dict["is_migration"] = True
                        skill_dict["state_key"] = metadata.get(
                            "state_key", skill_dict["name"]
                        )
                        # Parent protocol reference (e.g. "migration-wizard").
                        # Optional: subskills without an explicit protocol
                        # inherit the default wizard behaviour.
                        skill_dict["protocol"] = metadata.get("protocol")

                        services = metadata.get("services", [])
                        skill_dict["services"] = (
                            list(services) if isinstance(services, list) else []
                        )
                        skill_dict["recommended"] = bool(
                            metadata.get("recommended", True)
                        )

                        # Phase 1 detection commands.
                        check_commands = metadata.get("check_commands", [])
                        skill_dict["check_commands"] = (
                            list(check_commands)
                            if isinstance(check_commands, list)
                            else []
                        )

                        # Phase 1 health checks (list of {url, service} dicts).
                        health_checks = metadata.get("health_checks", [])
                        skill_dict["health_checks"] = (
                            list(health_checks)
                            if isinstance(health_checks, list)
                            else []
                        )

                        # Phase 2 system requirements.
                        system_requirements = metadata.get("system_requirements")
                        skill_dict["system_requirements"] = (
                            dict(system_requirements)
                            if isinstance(system_requirements, dict)
                            else {}
                        )

                        # Phase 3 installation.
                        install_commands = metadata.get("install_commands", [])
                        skill_dict["install_commands"] = (
                            list(install_commands)
                            if isinstance(install_commands, list)
                            else []
                        )
                        skill_dict["install_script"] = metadata.get("install_script")

                        # Phase 4 verification.
                        verify_commands = metadata.get("verify_commands", [])
                        skill_dict["verify_commands"] = (
                            list(verify_commands)
                            if isinstance(verify_commands, list)
                            else []
                        )
                        verify_scripts = metadata.get("verify_scripts", [])
                        skill_dict["verify_scripts"] = (
                            list(verify_scripts)
                            if isinstance(verify_scripts, list)
                            else []
                        )

                        # Phase 5 completion notes (free-form text).
                        skill_dict["post_install_notes"] = metadata.get(
                            "post_install_notes", ""
                        )

                    return skill_dict
        except Exception as e:
            logger.warning(f"Failed to load PM skill {skill_file}: {e}")

        return None

    def get_migration_skills(
        self, project_dir: Path | None = None
    ) -> list[dict[str, Any]]:
        """Return all migration-type skills (project + user level).

        Args:
            project_dir: Override project directory. Defaults to ``Path.cwd()``.

        Returns:
            List of migration skill dicts with ``is_migration=True``,
            deduplicated by ``state_key`` (project-level wins over user-level).
        """
        search_dirs: list[Path] = []
        if project_dir is None:
            project_dir = Path.cwd()
        search_dirs.append(project_dir / ".claude" / "skills")
        search_dirs.append(Path.home() / ".claude-mpm" / "skills")
        search_dirs.append(Path.home() / ".claude" / "skills")

        seen: dict[str, dict[str, Any]] = {}
        for search_dir in search_dirs:
            if not search_dir.exists() or not search_dir.is_dir():
                continue
            try:
                iterator = list(search_dir.iterdir())
            except OSError:
                continue
            for skill_dir in iterator:
                if not skill_dir.is_dir():
                    continue
                skill_file = skill_dir / "SKILL.md"
                if not skill_file.exists():
                    continue
                skill = self._load_pm_skill(skill_file)
                if not skill or not skill.get("is_migration"):
                    continue
                state_key = skill.get("state_key") or skill.get("name")
                if state_key in seen:
                    continue
                seen[state_key] = skill

        return list(seen.values())

    def get_pending_migration_skills(
        self, project_dir: Path | None = None
    ) -> list[dict[str, Any]]:
        """Return migration skills that are pending (not declined/completed).

        Cross-references discovered migration skills against
        :class:`UserChoicesManager` and the on-disk pending notification file
        produced by the ``check_migration_skills`` startup migration.
        """
        # Local import to avoid circular dependency at module load time.
        try:
            from claude_mpm.migrations.user_choices import UserChoicesManager
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("UserChoicesManager unavailable: %s", exc)
            return []

        manager = UserChoicesManager()
        all_migrations = self.get_migration_skills(project_dir=project_dir)
        pending = []
        for skill in all_migrations:
            state_key = skill.get("state_key") or skill.get("name")
            if not isinstance(state_key, str):
                continue
            if manager.is_pending(state_key):
                pending.append(skill)
        return pending

    def get_agent_skills(self, agent_type: str) -> list[Skill]:
        """
        Get all skills for an agent (bundled + discovered + PM skills if PM agent).

        Args:
            agent_type: Agent type/ID (e.g., 'engineer', 'python_engineer', 'pm')

        Returns:
            List of Skill objects for this agent
        """
        skill_names = self.agent_skill_mapping.get(agent_type)
        if skill_names is None:
            normalized_type = normalize_agent_id(agent_type)
            skill_names = self.agent_skill_mapping.get(normalized_type, [])

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

        # Build pending migration recommendations section (PM agent only).
        migration_section = ""
        if agent_type.lower() in ("pm", "project-manager", "project_manager"):
            try:
                pending = self.get_pending_migration_skills()
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Could not load pending migration skills: %s", exc)
                pending = []
            if pending:
                migration_section = self._format_pending_migrations(pending)

        if not skills and not migration_section:
            return base_prompt

        # Build skills section
        sections: list[str] = []
        if skills:
            skills_section = "\n\n" + "=" * 80 + "\n"
            skills_section += "## Available Skills\n\n"
            skills_section += (
                f"You have access to {len(skills)} specialized skills:\n\n"
            )

            for skill in skills:
                skills_section += f"### {skill.name.replace('-', ' ').title()}\n\n"
                skills_section += f"**Source:** {skill.source}\n"
                if skill.description:
                    skills_section += f"**Description:** {skill.description}\n"
                skills_section += "\n```\n"
                skills_section += skill.content
                skills_section += "\n```\n\n"

            skills_section += "=" * 80 + "\n"
            sections.append(skills_section)

        if migration_section:
            sections.append(migration_section)

        return base_prompt + "".join(sections)

    def _format_pending_migrations(self, pending: list[dict[str, Any]]) -> str:
        """Render pending migration skills as a PM prompt section."""
        lines = ["\n\n" + "=" * 80 + "\n"]
        lines.append("## Pending Setup Recommendations\n\n")
        lines.append(
            "The following optional services are recommended but not yet installed:\n\n"
        )
        for skill in pending:
            name = skill.get("name", "unknown")
            state_key = skill.get("state_key", name)
            services = skill.get("services") or []
            description = skill.get("description", "")

            if services:
                service_label = " + ".join(services)
                header = f"- **{state_key}** ({service_label})"
            else:
                header = f"- **{state_key}**"
            if description:
                header += f": {description}"
            lines.append(header + "\n")
            lines.append(
                f"  Run `/mpm-migrate {state_key}` to install, or tell me "
                f'"decline {state_key}" to stop showing this.\n'
            )
        lines.append(
            "\nThese enhance your workflow significantly. Use the migration "
            "skill to walk through installation.\n"
        )
        lines.append("=" * 80 + "\n")
        return "".join(lines)

    def list_agent_skill_mappings(self) -> dict[str, list[str]]:
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

    def infer_agents_for_skill(self, skill) -> list[str]:
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

    def save_mappings_to_config(self, config_path: Path | None = None):
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

    def load_mappings_from_config(self, config_path: Path | None = None):
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
_manager: SkillManager | None = None


def get_manager() -> SkillManager:
    """Get the global skill manager (singleton)."""
    global _manager
    if _manager is None:
        _manager = SkillManager()
    return _manager
