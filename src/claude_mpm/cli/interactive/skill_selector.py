"""Interactive Skill Selector for Claude MPM.

This module provides a two-tier interactive skill selection wizard:
1. Select topic groups (toolchains) to explore
2. Multi-select skills within each topic group

Features:
- Groups skills by toolchain (universal, python, typescript, etc.)
- Shows skills auto-included by agent dependencies
- Displays token counts for each skill
- Uses questionary with cyan style for consistency
"""

import json
from dataclasses import dataclass
from typing import Dict, List, Optional

import questionary

from claude_mpm.cli.interactive.questionary_styles import (
    BANNER_WIDTH,
    MPM_STYLE,
    print_banner,
)
from claude_mpm.core.logging_utils import get_logger
from claude_mpm.core.unified_config import UnifiedConfig
from claude_mpm.core.unified_paths import get_path_manager

logger = get_logger(__name__)

# Topic/toolchain icons
TOPIC_ICONS = {
    "universal": "🌐",
    "python": "🐍",
    "typescript": "📘",
    "javascript": "📒",
    "rust": "⚙️",
    "go": "🔷",
    "java": "☕",
    "ruby": "💎",
    "php": "🐘",
    "csharp": "🔷",
    "cpp": "⚙️",
    "swift": "🍎",
    None: "🌐",  # Default for null toolchain (universal)
}


@dataclass
class SkillInfo:
    """Information about a skill from manifest."""

    name: str
    toolchain: Optional[str]
    framework: Optional[str]
    tags: List[str]
    full_tokens: int
    description: str = ""

    @property
    def display_name(self) -> str:
        """Get display name with token count."""
        tokens_k = self.full_tokens // 1000
        return f"{self.name} ({tokens_k}K tokens)"


class SkillSelector:
    """Interactive skill selector with topic grouping."""

    def __init__(
        self, skills_manifest: Dict, agent_skill_deps: Optional[List[str]] = None
    ):
        """Initialize skill selector.

        Args:
            skills_manifest: Full manifest dict with all skills
            agent_skill_deps: Skills required by deployed agents (auto-included)
        """
        self.manifest = skills_manifest
        self.agent_skill_deps = set(agent_skill_deps or [])
        self.skills_by_toolchain: Dict[str, List[SkillInfo]] = {}
        self._parse_manifest()

    def _parse_manifest(self) -> None:
        """Parse manifest and group skills by toolchain."""
        # Handle both old and new manifest formats
        skills_data = self.manifest.get("skills", {})

        # Flatten skills from grouped format to flat list
        all_skills = []
        if isinstance(skills_data, dict):
            for toolchain, skills_list in skills_data.items():
                all_skills.extend(skills_list)
        elif isinstance(skills_data, list):
            all_skills = skills_data

        # Group by toolchain
        for skill_data in all_skills:
            try:
                skill = SkillInfo(
                    name=skill_data.get("name", ""),
                    toolchain=skill_data.get("toolchain"),
                    framework=skill_data.get("framework"),
                    tags=skill_data.get("tags", []),
                    full_tokens=skill_data.get("full_tokens", 0),
                    description=skill_data.get("description", ""),
                )

                # Group by toolchain (null -> universal)
                toolchain_key = skill.toolchain or "universal"

                if toolchain_key not in self.skills_by_toolchain:
                    self.skills_by_toolchain[toolchain_key] = []

                self.skills_by_toolchain[toolchain_key].append(skill)
            except Exception as e:
                logger.warning(
                    f"Failed to parse skill: {skill_data.get('name', 'unknown')}: {e}"
                )

        # Sort skills within each toolchain by name
        for toolchain in self.skills_by_toolchain:
            self.skills_by_toolchain[toolchain].sort(key=lambda s: s.name)

    def select_skills(self) -> List[str]:
        """Run interactive selection and return selected skill IDs.

        Returns:
            List of selected skill IDs (names)
        """
        print_banner("SKILL CONFIGURATION", width=BANNER_WIDTH)

        # Show agent-required skills (auto-included)
        if self.agent_skill_deps:
            self._show_agent_required_skills()

        # Select topic groups to explore
        selected_groups = self._select_topic_groups()

        if not selected_groups:
            print("\n⚠️  No topic groups selected. Using only agent-required skills.")
            return list(self.agent_skill_deps)

        # Multi-select skills from each group
        selected_skills = set(self.agent_skill_deps)  # Start with auto-included

        for group in selected_groups:
            group_skills = self._select_skills_from_group(group)
            selected_skills.update(group_skills)

        # Confirm selection
        print(f"\n✅ Total skills selected: {len(selected_skills)}")
        print(f"   - Auto-included (from agents): {len(self.agent_skill_deps)}")
        print(f"   - Manually selected: {len(selected_skills - self.agent_skill_deps)}")

        return list(selected_skills)

    def _show_agent_required_skills(self) -> None:
        """Display skills that are auto-included from agent dependencies."""
        print("\n📦 Agent-Required Skills (auto-included):")
        for skill_name in sorted(self.agent_skill_deps):
            print(f"  ✓ {skill_name}")
        print()

    def _select_topic_groups(self) -> List[str]:
        """First tier: Select which toolchain groups to browse.

        Returns:
            List of selected toolchain keys
        """
        # Build choices with counts
        choices = []
        for toolchain in sorted(self.skills_by_toolchain.keys()):
            skills = self.skills_by_toolchain[toolchain]
            icon = TOPIC_ICONS.get(toolchain, "📦")
            display_name = toolchain.capitalize() if toolchain else "Universal"
            choice_text = f"{icon} {display_name} ({len(skills)} skills)"
            choices.append(questionary.Choice(title=choice_text, value=toolchain))

        if not choices:
            print("\n⚠️  No skills available in manifest.")
            return []

        # Multi-select groups
        selected = questionary.checkbox(
            "📂 Select Topic Groups to Add Skills From:",
            choices=choices,
            style=MPM_STYLE,
        ).ask()

        if selected is None:  # User cancelled
            return []

        return selected

    def _select_skills_from_group(self, toolchain: str) -> List[str]:
        """Second tier: Multi-select skills within a toolchain group.

        Args:
            toolchain: Toolchain key to select from

        Returns:
            List of selected skill names
        """
        skills = self.skills_by_toolchain.get(toolchain, [])
        if not skills:
            return []

        icon = TOPIC_ICONS.get(toolchain, "📦")
        display_name = toolchain.capitalize() if toolchain else "Universal"

        print(f"\n{icon} {display_name} Skills:")

        # Build choices
        choices = []
        for skill in skills:
            # Mark if already selected (from agent deps)
            already_selected = skill.name in self.agent_skill_deps
            prefix = "[auto] " if already_selected else ""
            choice = questionary.Choice(
                title=f"{prefix}{skill.display_name}",
                value=skill.name,
                checked=already_selected,
            )
            choices.append(choice)

        # Multi-select skills
        selected = questionary.checkbox(
            f"Select {display_name} skills to include:",
            choices=choices,
            style=MPM_STYLE,
        ).ask()

        if selected is None:  # User cancelled
            return []

        return selected


def load_skills_manifest() -> Optional[Dict]:
    """Load skills manifest from cache.

    Returns:
        Manifest dict or None if not found
    """
    try:
        path_manager = get_path_manager()
        manifest_path = (
            path_manager.get_cache_dir() / "skills" / "system" / "manifest.json"
        )

        if not manifest_path.exists():
            logger.error(f"Skills manifest not found at {manifest_path}")
            print("\n❌ Skills manifest not found. Run 'claude-mpm skills sync' first.")
            return None

        with open(manifest_path, encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        logger.error(f"Failed to load skills manifest: {e}")
        print(f"\n❌ Failed to load skills manifest: {e}")
        return None


def get_agent_skill_dependencies(config: UnifiedConfig) -> List[str]:
    """Get skill dependencies from deployed agents.

    Args:
        config: UnifiedConfig instance

    Returns:
        List of skill IDs required by enabled agents
    """
    try:
        from claude_mpm.services.agents.deployment.deployment_reconciler import (
            DeploymentReconciler,
        )

        reconciler = DeploymentReconciler(config)
        enabled_agents = config.agents.enabled

        if not enabled_agents:
            logger.debug("No enabled agents, no skill dependencies")
            return []

        # Get skill dependencies
        skill_deps = reconciler._get_agent_skill_dependencies(enabled_agents)
        return list(skill_deps)

    except Exception as e:
        logger.warning(f"Failed to get agent skill dependencies: {e}")
        return []


def run_skill_selector() -> Optional[List[str]]:
    """Main entry point for skill selector.

    Returns:
        List of selected skill IDs, or None if cancelled
    """
    try:
        # Load config
        config = UnifiedConfig()

        # Load manifest
        manifest = load_skills_manifest()
        if not manifest:
            return None

        # Get agent skill dependencies
        agent_deps = get_agent_skill_dependencies(config)

        # Run selector
        selector = SkillSelector(manifest, agent_deps)
        return selector.select_skills()

    except KeyboardInterrupt:
        print("\n\n❌ Skill selection cancelled")
        return None
    except Exception as e:
        logger.error(f"Skill selection error: {e}", exc_info=True)
        print(f"\n❌ Skill selection error: {e}")
        return None
