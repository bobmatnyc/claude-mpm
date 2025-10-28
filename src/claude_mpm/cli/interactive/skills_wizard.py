"""Interactive Skills Selection Wizard for Claude MPM.

This module provides a step-by-step interactive wizard for selecting and configuring
skills for agents with user-friendly prompts and intelligent auto-linking.
"""

from typing import Dict, List, Optional, Tuple

from claude_mpm.core.logging_config import get_logger
from claude_mpm.skills.registry import get_registry
from claude_mpm.skills.skill_manager import get_manager

logger = get_logger(__name__)


# Agent-to-skills auto-linking mappings
ENGINEER_CORE_SKILLS = [
    "test-driven-development",
    "systematic-debugging",
    "code-review",
    "refactoring-patterns",
    "git-workflow",
]

PYTHON_SKILLS = ENGINEER_CORE_SKILLS + ["async-testing"]
TYPESCRIPT_SKILLS = ENGINEER_CORE_SKILLS + ["async-testing"]
GOLANG_SKILLS = ENGINEER_CORE_SKILLS + ["async-testing"]
REACT_SKILLS = TYPESCRIPT_SKILLS + ["performance-profiling"]
NEXTJS_SKILLS = REACT_SKILLS
VUE_SKILLS = TYPESCRIPT_SKILLS + ["performance-profiling"]

OPS_SKILLS = [
    "docker-containerization",
    "database-migration",
    "security-scanning",
    "systematic-debugging",
]

DOCUMENTATION_SKILLS = [
    "api-documentation",
    "code-review",
]

QA_SKILLS = [
    "test-driven-development",
    "systematic-debugging",
    "async-testing",
    "performance-profiling",
]

# Mapping of agent types to their recommended skills
AGENT_SKILL_MAPPING = {
    # Engineer agents
    "engineer": ENGINEER_CORE_SKILLS,
    "python-engineer": PYTHON_SKILLS,
    "typescript-engineer": TYPESCRIPT_SKILLS,
    "golang-engineer": GOLANG_SKILLS,
    "react-engineer": REACT_SKILLS,
    "nextjs-engineer": NEXTJS_SKILLS,
    "vue-engineer": VUE_SKILLS,
    # Ops agents
    "ops": OPS_SKILLS,
    "devops": OPS_SKILLS,
    "local-ops": OPS_SKILLS,
    # Documentation agents
    "docs": DOCUMENTATION_SKILLS,
    "documentation": DOCUMENTATION_SKILLS,
    "technical-writer": DOCUMENTATION_SKILLS,
    # QA agents
    "qa": QA_SKILLS,
    "web-qa": QA_SKILLS,
    "api-qa": QA_SKILLS,
    "tester": QA_SKILLS,
}


class SkillsWizard:
    """Interactive wizard for skills selection and configuration."""

    def __init__(self):
        """Initialize the skills wizard."""
        self.registry = get_registry()
        self.manager = get_manager()
        self.logger = logger

    def run_interactive_selection(
        self, selected_agents: Optional[List[str]] = None
    ) -> Tuple[bool, Dict[str, List[str]]]:
        """Run interactive skills selection wizard.

        Args:
            selected_agents: List of agent IDs that were selected in agent wizard

        Returns:
            Tuple of (success, agent_skills_mapping)
            - success: Boolean indicating if selection was successful
            - agent_skills_mapping: Dict mapping agent IDs to lists of skill names
        """
        try:
            print("\n" + "=" * 60)
            print("🎯  Skills Selection Wizard")
            print("=" * 60)
            print("\nI'll help you select skills for your agents.")
            print("Press Ctrl+C anytime to cancel.\n")

            # Auto-link skills based on selected agents
            agent_skills_mapping = {}
            if selected_agents:
                print("📋 Auto-linking skills based on selected agents...\n")
                agent_skills_mapping = self._auto_link_skills(selected_agents)
                self._display_auto_linked_skills(agent_skills_mapping)

            # Ask if user wants to customize
            customize = (
                input("\nWould you like to customize skill selections? [y/N]: ")
                .strip()
                .lower()
            )

            if customize in ["y", "yes"]:
                agent_skills_mapping = self._run_custom_selection(
                    selected_agents, agent_skills_mapping
                )

            # Preview final configuration
            self._preview_final_configuration(agent_skills_mapping)

            # Confirm
            confirm = (
                input("\nApply this skills configuration? [Y/n]: ").strip().lower()
            )
            if confirm in ["n", "no"]:
                return False, {}

            # Apply configuration
            self._apply_skills_configuration(agent_skills_mapping)

            print("\n✅ Skills configuration complete!")
            return True, agent_skills_mapping

        except KeyboardInterrupt:
            print("\n\n❌ Skills selection cancelled")
            return False, {}
        except Exception as e:
            error_msg = f"Skills selection error: {e}"
            self.logger.error(error_msg, exc_info=True)
            print(f"\n❌ {error_msg}")
            return False, {}

    def _auto_link_skills(self, agent_ids: List[str]) -> Dict[str, List[str]]:
        """Auto-link skills to agents based on agent types.

        Args:
            agent_ids: List of agent IDs

        Returns:
            Dictionary mapping agent IDs to skill names
        """
        mapping = {}
        for agent_id in agent_ids:
            # Try to match against known patterns
            skills = self._get_recommended_skills_for_agent(agent_id)
            if skills:
                mapping[agent_id] = skills
            else:
                # Default to core engineer skills if no match
                mapping[agent_id] = ENGINEER_CORE_SKILLS.copy()

        return mapping

    def _get_recommended_skills_for_agent(self, agent_id: str) -> List[str]:
        """Get recommended skills for an agent based on its ID.

        Args:
            agent_id: Agent identifier

        Returns:
            List of recommended skill names
        """
        agent_id_lower = agent_id.lower()

        # Direct match
        if agent_id_lower in AGENT_SKILL_MAPPING:
            return AGENT_SKILL_MAPPING[agent_id_lower].copy()

        # Fuzzy matching for common patterns
        if "python" in agent_id_lower:
            return PYTHON_SKILLS.copy()
        if any(js in agent_id_lower for js in ["typescript", "ts", "javascript", "js"]):
            return TYPESCRIPT_SKILLS.copy()
        if "react" in agent_id_lower:
            return REACT_SKILLS.copy()
        if "next" in agent_id_lower:
            return NEXTJS_SKILLS.copy()
        if "vue" in agent_id_lower:
            return VUE_SKILLS.copy()
        if "go" in agent_id_lower or "golang" in agent_id_lower:
            return GOLANG_SKILLS.copy()
        if any(ops in agent_id_lower for ops in ["ops", "devops", "deploy"]):
            return OPS_SKILLS.copy()
        if any(qa in agent_id_lower for qa in ["qa", "test", "quality"]):
            return QA_SKILLS.copy()
        if any(doc in agent_id_lower for doc in ["doc", "writer", "technical"]):
            return DOCUMENTATION_SKILLS.copy()
        if "engineer" in agent_id_lower:
            return ENGINEER_CORE_SKILLS.copy()

        # Default
        return []

    def _display_auto_linked_skills(self, mapping: Dict[str, List[str]]):
        """Display auto-linked skills configuration.

        Args:
            mapping: Agent-to-skills mapping
        """
        for agent_id, skills in mapping.items():
            print(f"  • {agent_id}:")
            for skill in skills:
                print(f"    - {skill}")
        print()

    def _run_custom_selection(
        self, agent_ids: Optional[List[str]], initial_mapping: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """Run custom skills selection for each agent.

        Args:
            agent_ids: List of agent IDs
            initial_mapping: Initial auto-linked mapping

        Returns:
            Updated agent-to-skills mapping
        """
        mapping = initial_mapping.copy()

        # Get all available bundled skills
        bundled_skills = self.registry.list_skills(source="bundled")
        skill_list = sorted([skill.name for skill in bundled_skills])

        print("\n" + "=" * 60)
        print("Available Bundled Skills:")
        print("=" * 60)
        for i, skill in enumerate(bundled_skills, 1):
            description = (
                skill.description[:60] + "..."
                if len(skill.description) > 60
                else skill.description
            )
            print(f"  [{i:2d}] {skill.name}")
            print(f"       {description}")
        print()

        # If no agents provided, ask which agents to configure
        if not agent_ids:
            agent_ids = self._get_agents_to_configure()

        # Configure each agent
        for agent_id in agent_ids:
            print(f"\n🔧 Configuring skills for: {agent_id}")
            current_skills = mapping.get(agent_id, [])

            print(f"   Current skills ({len(current_skills)}):")
            for skill in current_skills:
                print(f"    - {skill}")

            modify = (
                input(f"\n   Modify skills for {agent_id}? [y/N]: ").strip().lower()
            )
            if modify not in ["y", "yes"]:
                continue

            # Let user select skills
            print("\n   Enter skill numbers (comma-separated), or:")
            print("     'all' - Select all skills")
            print("     'none' - Clear all skills")
            print("     'keep' - Keep current selection")
            selection = input("   Selection: ").strip().lower()

            if selection == "keep":
                continue
            if selection == "none":
                mapping[agent_id] = []
            elif selection == "all":
                mapping[agent_id] = skill_list.copy()
            else:
                # Parse comma-separated numbers
                try:
                    selected_indices = [
                        int(idx.strip()) for idx in selection.split(",")
                    ]
                    selected_skills = [
                        skill_list[idx - 1]
                        for idx in selected_indices
                        if 1 <= idx <= len(skill_list)
                    ]
                    mapping[agent_id] = selected_skills
                except (ValueError, IndexError) as e:
                    print(f"   ⚠️  Invalid selection, keeping current: {e}")

        return mapping

    def _get_agents_to_configure(self) -> List[str]:
        """Ask user which agents to configure.

        Returns:
            List of agent IDs
        """
        agent_ids_input = input("\nEnter agent IDs (comma-separated): ").strip()
        return [aid.strip() for aid in agent_ids_input.split(",") if aid.strip()]

    def _preview_final_configuration(self, mapping: Dict[str, List[str]]):
        """Display final skills configuration preview.

        Args:
            mapping: Agent-to-skills mapping
        """
        print("\n" + "=" * 60)
        print("📋 Final Skills Configuration:")
        print("=" * 60)

        if not mapping:
            print("  (No skills configured)")
            return

        for agent_id, skills in mapping.items():
            print(f"\n  {agent_id} ({len(skills)} skills):")
            if skills:
                for skill in skills:
                    print(f"    ✓ {skill}")
            else:
                print("    (no skills)")

    def _apply_skills_configuration(self, mapping: Dict[str, List[str]]):
        """Apply skills configuration to skill manager.

        Args:
            mapping: Agent-to-skills mapping
        """
        for agent_id, skills in mapping.items():
            # Clear existing mappings for this agent
            if agent_id in self.manager.agent_skill_mapping:
                self.manager.agent_skill_mapping[agent_id] = []

            # Add each skill
            for skill_name in skills:
                self.manager.add_skill_to_agent(agent_id, skill_name)

        self.logger.info(f"Applied skills configuration for {len(mapping)} agents")

    def list_available_skills(self):
        """Display all available skills."""
        print("\n" + "=" * 60)
        print("📚 Available Skills")
        print("=" * 60)

        # Bundled skills
        bundled_skills = self.registry.list_skills(source="bundled")
        if bundled_skills:
            print(f"\n🔹 Bundled Skills ({len(bundled_skills)}):")
            for skill in sorted(bundled_skills, key=lambda s: s.name):
                print(f"   • {skill.name}")
                if skill.description:
                    desc = (
                        skill.description[:80] + "..."
                        if len(skill.description) > 80
                        else skill.description
                    )
                    print(f"     {desc}")

        # User skills
        user_skills = self.registry.list_skills(source="user")
        if user_skills:
            print(f"\n👤 User Skills ({len(user_skills)}):")
            for skill in sorted(user_skills, key=lambda s: s.name):
                print(f"   • {skill.name}")
                if skill.description:
                    desc = (
                        skill.description[:80] + "..."
                        if len(skill.description) > 80
                        else skill.description
                    )
                    print(f"     {desc}")

        # Project skills
        project_skills = self.registry.list_skills(source="project")
        if project_skills:
            print(f"\n📂 Project Skills ({len(project_skills)}):")
            for skill in sorted(project_skills, key=lambda s: s.name):
                print(f"   • {skill.name}")
                if skill.description:
                    desc = (
                        skill.description[:80] + "..."
                        if len(skill.description) > 80
                        else skill.description
                    )
                    print(f"     {desc}")

        print()


def discover_and_link_runtime_skills():
    """Discover user/project skills and auto-link to agents at runtime.

    This function is called during startup to:
    1. Reload the skills registry (picks up new skills from .claude/skills/)
    2. Auto-link discovered skills to agents based on tags/naming conventions
    """
    try:
        registry = get_registry()
        manager = get_manager()

        # Reload registry to pick up new skills
        registry.reload()

        # Get discovered skills (user and project)
        discovered_skills = registry.list_skills(source="user") + registry.list_skills(
            source="project"
        )

        if not discovered_skills:
            logger.debug("No runtime skills discovered")
            return

        logger.info(f"Discovered {len(discovered_skills)} runtime skills")

        # Auto-link based on skill content and naming
        for skill in discovered_skills:
            agents = _infer_agents_for_skill(skill)
            for agent_id in agents:
                manager.add_skill_to_agent(agent_id, skill.name)
                logger.debug(f"Auto-linked skill '{skill.name}' to agent '{agent_id}'")

    except Exception as e:
        logger.error(f"Error during runtime skills discovery: {e}", exc_info=True)


def _infer_agents_for_skill(skill) -> List[str]:
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
