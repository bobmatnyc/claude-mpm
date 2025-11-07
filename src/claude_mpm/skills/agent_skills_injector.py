"""Agent Skills Injector - Dynamically inject skills into agent templates.

This module implements dynamic skill injection into agent templates and frontmatter.
It reads skill assignments from the registry and enhances agent definitions at runtime
without modifying template files on disk.

Design Principles:
- Dynamic injection (no template file modifications)
- Registry is source of truth (not templates)
- Return enhanced templates as dicts
- Generate clean YAML frontmatter
- Inject skills docs after frontmatter

References:
- Design: docs/design/claude-mpm-skills-integration-design.md (lines 632-711)
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import yaml

from claude_mpm.core.mixins import LoggerMixin

from .skills_service import SkillsService


class AgentSkillsInjector(LoggerMixin):
    """Injects skill references into agent templates and frontmatter.

    This class provides methods to:
    - Enhance agent JSON templates with skills field
    - Generate YAML frontmatter with skills included
    - Inject skills documentation into agent markdown content

    The injector reads from the skills registry (not template files) to determine
    which skills should be assigned to each agent, then dynamically injects this
    information when agents are loaded.

    Example:
        >>> service = SkillsService()
        >>> injector = AgentSkillsInjector(service)
        >>>
        >>> # Enhance template
        >>> template = injector.enhance_agent_template(Path('engineer.json'))
        >>> print(template['skills'])  # {'required': [...], 'optional': [...]}
        >>>
        >>> # Generate frontmatter
        >>> frontmatter = injector.generate_frontmatter_with_skills(template)
        >>> print(frontmatter)  # ---\nname: engineer\nskills:\n  - ...\n---
    """

    def __init__(self, skills_service: SkillsService) -> None:
        """Initialize Agent Skills Injector.

        Args:
            skills_service: SkillsService instance for accessing registry
        """
        super().__init__()
        self.skills_service: SkillsService = skills_service

    def enhance_agent_template(self, template_path: Path) -> Dict[str, Any]:
        """Add skills field to agent template JSON.

        Reads an agent JSON template, determines which skills should be assigned
        from the registry, and adds a 'skills' field to the template dict.

        The skills field structure:
        {
            "required": [skill1, skill2],  # First 2 skills
            "optional": [skill3, skill4],  # Remaining skills
            "auto_load": true
        }

        Args:
            template_path: Path to agent JSON template file

        Returns:
            Enhanced template dict with 'skills' field added

        Example:
            >>> template = injector.enhance_agent_template(
            ...     Path('src/claude_mpm/agents/templates/engineer.json')
            ... )
            >>> assert 'skills' in template
            >>> assert 'required' in template['skills']
        """
        try:
            with open(template_path, encoding="utf-8") as f:
                template = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to load template {template_path}: {e}")
            raise ValueError(f"Cannot load template {template_path}") from e

        agent_id = template.get("agent_id")
        if not agent_id:
            self.logger.error(f"Template missing agent_id: {template_path}")
            return template

        # Get skills for this agent from registry
        skills = self.skills_service.get_skills_for_agent(agent_id)

        if skills:
            # Split into required (first 2) and optional (rest)
            required = skills[:2] if len(skills) > 2 else skills
            optional = skills[2:] if len(skills) > 2 else []

            template["skills"] = {
                "required": required,
                "optional": optional,
                "auto_load": True,
            }

            self.logger.info(f"Enhanced {agent_id} with {len(skills)} skills")
        else:
            self.logger.debug(f"No skills assigned to {agent_id}")

        return template

    def generate_frontmatter_with_skills(self, agent_config: Dict[str, Any]) -> str:
        """Generate YAML frontmatter including skills field.

        Creates clean YAML frontmatter for agent markdown files, including:
        - name: Agent ID
        - description: Agent description
        - version: Agent version
        - tools: List of tools
        - skills: List of all skills (required + optional)

        Args:
            agent_config: Agent configuration dict (from JSON template)

        Returns:
            YAML frontmatter string with delimiters (---\n...yaml...\n---)

        Example:
            >>> config = {
            ...     'agent_id': 'engineer',
            ...     'metadata': {'description': 'Software development'},
            ...     'version': '2.1.0',
            ...     'capabilities': {'tools': ['Read', 'Write']},
            ...     'skills': {
            ...         'required': ['test-driven-development'],
            ...         'optional': ['code-review']
            ...     }
            ... }
            >>> frontmatter = injector.generate_frontmatter_with_skills(config)
            >>> assert 'skills:' in frontmatter
            >>> assert 'test-driven-development' in frontmatter
        """
        # Build frontmatter dict
        frontmatter = {
            "name": agent_config.get("agent_id"),
            "description": agent_config.get("metadata", {}).get("description"),
            "version": agent_config.get("version"),
            "tools": agent_config.get("capabilities", {}).get("tools", []),
        }

        # Add skills if present
        if "skills" in agent_config:
            skills_config = agent_config["skills"]
            required = skills_config.get("required", [])
            optional = skills_config.get("optional", [])
            all_skills = required + optional

            if all_skills:
                frontmatter["skills"] = all_skills

        # Convert to YAML with clean formatting
        yaml_str = yaml.dump(
            frontmatter, default_flow_style=False, sort_keys=False, allow_unicode=True
        )

        return f"---\n{yaml_str}---\n"

    def inject_skills_documentation(self, agent_content: str, skills: List[str]) -> str:
        """Inject skills documentation reference into agent instructions.

        Adds a "## Available Skills" section after the YAML frontmatter that
        lists all skills available to this agent. This section informs the agent
        about its skills and explains that Claude will auto-load them when relevant.

        Args:
            agent_content: Original agent markdown content (with frontmatter)
            skills: List of skill names to document

        Returns:
            Agent content with skills section injected after frontmatter

        Example:
            >>> content = '''---
            ... name: engineer
            ... ---
            ...
            ... # Software Engineer Agent
            ...
            ... You are a software development specialist...
            ... '''
            >>> skills = ['test-driven-development', 'systematic-debugging']
            >>> enhanced = injector.inject_skills_documentation(content, skills)
            >>> assert '## Available Skills' in enhanced
            >>> assert 'test-driven-development' in enhanced
        """
        if not skills:
            return agent_content

        # Build skills section
        skills_section = "\n\n## Available Skills\n\n"
        skills_section += "You have access to the following skills that will be loaded when relevant:\n\n"

        for skill in skills:
            skills_section += f"- **{skill}**: Automatically activated when needed\n"

        skills_section += "\nClaude will automatically read these skills when your task matches their descriptions.\n"

        # Insert after frontmatter
        if "---" in agent_content:
            parts = agent_content.split("---", 2)
            if len(parts) >= 3:
                # Reconstruct: frontmatter + skills section + rest
                return f"{parts[0]}---{parts[1]}---{skills_section}{parts[2]}"

        # If no frontmatter, append at end
        return agent_content + skills_section

    def enhance_agent_with_skills(
        self, agent_id: str, template_content: str
    ) -> Dict[str, Any]:
        """Convenience method to fully enhance an agent with skills.

        Combines all enhancement steps:
        1. Gets skills from registry
        2. Generates enhanced frontmatter
        3. Injects skills documentation

        Args:
            agent_id: Agent identifier
            template_content: Original agent template markdown content

        Returns:
            Dict containing:
            - agent_id: Agent identifier
            - skills: List of skill names
            - frontmatter: YAML frontmatter with skills
            - content: Full enhanced markdown content

        Example:
            >>> result = injector.enhance_agent_with_skills(
            ...     'engineer',
            ...     '---\nname: engineer\n---\n\n# Engineer\n...'
            ... )
            >>> print(result['skills'])  # ['test-driven-development', ...]
            >>> print(result['content'])  # Enhanced markdown with skills section
        """
        # Get skills for agent
        skills = self.skills_service.get_skills_for_agent(agent_id)

        if not skills:
            return {
                "agent_id": agent_id,
                "skills": [],
                "frontmatter": "",
                "content": template_content,
            }

        # Create config dict for frontmatter generation
        agent_config = {
            "agent_id": agent_id,
            "skills": {
                "required": skills[:2] if len(skills) > 2 else skills,
                "optional": skills[2:] if len(skills) > 2 else [],
            },
        }

        # Generate frontmatter
        frontmatter = self.generate_frontmatter_with_skills(agent_config)

        # Inject skills documentation
        enhanced_content = self.inject_skills_documentation(template_content, skills)

        return {
            "agent_id": agent_id,
            "skills": skills,
            "frontmatter": frontmatter,
            "content": enhanced_content,
        }

    def get_skills_references_for_agent(self, agent_id: str) -> List[Dict[str, str]]:
        """Get skill references with metadata for an agent.

        Returns detailed information about each skill assigned to an agent,
        including name, category, and description from the registry.

        Args:
            agent_id: Agent identifier

        Returns:
            List of dicts containing skill reference information:
            - name: Skill name
            - category: Skill category (from metadata)
            - description: Brief description

        Example:
            >>> refs = injector.get_skills_references_for_agent('engineer')
            >>> for ref in refs:
            ...     print(f"{ref['name']}: {ref['description']}")
        """
        skills = self.skills_service.get_skills_for_agent(agent_id)
        registry = self.skills_service.registry

        skill_refs = []
        for skill_name in skills:
            metadata = registry.get("skills_metadata", {}).get(skill_name, {})

            skill_refs.append(
                {
                    "name": skill_name,
                    "category": metadata.get("category", "unknown"),
                    "description": metadata.get("description", ""),
                }
            )

        return skill_refs
