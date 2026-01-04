"""
Deployment Reconciliation Service - Simplified Deployment Model

This service implements the simplified deployment model where:
1. Configuration has explicit lists: agents.enabled and skills.enabled
2. On startup/sync, reconcile deployed state with configured state
3. Deploy agents from cache to project .claude/ directories
4. Remove agents/skills NOT in enabled lists

Key Principles:
- Explicit configuration over auto-discovery
- Clear reconciliation view (configured vs deployed)
- Simple cleanup of unneeded agents/skills
- Backward compatibility with empty enabled lists
"""

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

from claude_mpm.core.logging_utils import get_logger
from claude_mpm.core.unified_config import UnifiedConfig
from claude_mpm.core.unified_paths import get_path_manager

logger = get_logger(__name__)


@dataclass
class DeploymentResult:
    """Result of deployment reconciliation."""

    deployed: List[str]  # Newly deployed
    removed: List[str]  # Removed (not in config)
    unchanged: List[str]  # Already deployed and still needed
    errors: List[str]  # Errors during reconciliation

    @property
    def success(self) -> bool:
        """Whether reconciliation succeeded (no errors)."""
        return len(self.errors) == 0


@dataclass
class ReconciliationState:
    """Current state of agent/skill deployment."""

    configured: Set[str]  # IDs in config enabled list
    deployed: Set[str]  # IDs currently deployed
    cached: Set[str]  # IDs available in cache

    @property
    def to_deploy(self) -> Set[str]:
        """Agents/skills that need deployment (in config but not deployed)."""
        return self.configured - self.deployed

    @property
    def to_remove(self) -> Set[str]:
        """Agents/skills that should be removed (deployed but not in config)."""
        return self.deployed - self.configured

    @property
    def unchanged(self) -> Set[str]:
        """Agents/skills already deployed and still needed."""
        return self.configured & self.deployed


class DeploymentReconciler:
    """
    Reconciles configured agents/skills with deployed state.

    This service implements the simplified deployment model:
    1. Read agents.enabled and skills.enabled from config
    2. Discover what's currently deployed in .claude/agents and .claude/skills
    3. Deploy missing agents/skills from cache
    4. Remove agents/skills not in enabled lists
    """

    def __init__(self, config: Optional[UnifiedConfig] = None):
        """
        Initialize reconciler.

        Args:
            config: UnifiedConfig instance (auto-loads if None)
        """
        self.config = config or self._load_config()
        self.path_manager = get_path_manager()

    def _load_config(self) -> UnifiedConfig:
        """Load configuration from standard location."""
        # For now, return default config
        # TODO: Load from .claude-mpm/configuration.yaml
        return UnifiedConfig()

    def reconcile_agents(self, project_path: Optional[Path] = None) -> DeploymentResult:
        """
        Reconcile agent deployment with configuration.

        Args:
            project_path: Project directory (default: current directory)

        Returns:
            DeploymentResult with reconciliation summary
        """
        project_path = project_path or Path.cwd()
        cache_dir = self.path_manager.get_cache_dir() / "agents"
        deploy_dir = project_path / ".claude" / "agents"

        # Get current state
        state = self._get_agent_state(cache_dir, deploy_dir)

        # Check backward compatibility
        if not self.config.agents.enabled and self.config.agents.auto_discover:
            logger.warning(
                "agents.enabled is empty and auto_discover is True. "
                "Consider migrating to explicit agent list. "
                "Falling back to auto-discovery mode."
            )
            # In auto-discovery mode, don't remove anything
            return DeploymentResult(
                deployed=[], removed=[], unchanged=list(state.deployed), errors=[]
            )

        result = DeploymentResult(deployed=[], removed=[], unchanged=[], errors=[])

        # Deploy missing agents
        for agent_id in state.to_deploy:
            if agent_id not in state.cached:
                error_msg = f"Agent '{agent_id}' not found in cache. Run 'claude-mpm agents sync' first."
                logger.warning(error_msg)
                result.errors.append(error_msg)
                continue

            try:
                self._deploy_agent(agent_id, cache_dir, deploy_dir)
                result.deployed.append(agent_id)
                logger.info(f"Deployed agent: {agent_id}")
            except Exception as e:
                error_msg = f"Failed to deploy agent '{agent_id}': {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)

        # Remove unneeded agents (only MPM agents, not user-created)
        for agent_id in state.to_remove:
            try:
                if self._is_mpm_agent(deploy_dir, agent_id):
                    self._remove_agent(agent_id, deploy_dir)
                    result.removed.append(agent_id)
                    logger.info(f"Removed agent: {agent_id}")
                else:
                    logger.debug(f"Skipping removal of user agent: {agent_id}")
                    result.unchanged.append(agent_id)
            except Exception as e:
                error_msg = f"Failed to remove agent '{agent_id}': {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)

        # Track unchanged agents
        result.unchanged.extend(list(state.unchanged))

        return result

    def reconcile_skills(self, project_path: Optional[Path] = None) -> DeploymentResult:
        """
        Reconcile skill deployment with configuration.

        This includes:
        1. Skills in skills.enabled list
        2. Skills required by enabled agents (if auto_detect_dependencies=True)

        Args:
            project_path: Project directory (default: current directory)

        Returns:
            DeploymentResult with reconciliation summary
        """
        project_path = project_path or Path.cwd()
        cache_dir = self.path_manager.get_cache_dir() / "skills"
        deploy_dir = project_path / ".claude" / "skills"

        # Get configured skills (explicit + agent dependencies)
        configured_skills = set(self.config.skills.enabled)

        if self.config.skills.auto_detect_dependencies:
            # Add skills required by enabled agents
            agent_skill_deps = self._get_agent_skill_dependencies(
                self.config.agents.enabled
            )
            configured_skills.update(agent_skill_deps)

        # Get current state
        state = ReconciliationState(
            configured=configured_skills,
            deployed=self._list_deployed_skills(deploy_dir),
            cached=self._list_cached_skills(cache_dir),
        )

        result = DeploymentResult(deployed=[], removed=[], unchanged=[], errors=[])

        # Deploy missing skills
        for skill_id in state.to_deploy:
            if skill_id not in state.cached:
                error_msg = (
                    f"Skill '{skill_id}' not found in cache. Check skill sources."
                )
                logger.warning(error_msg)
                result.errors.append(error_msg)
                continue

            try:
                self._deploy_skill(skill_id, cache_dir, deploy_dir)
                result.deployed.append(skill_id)
                logger.info(f"Deployed skill: {skill_id}")
            except Exception as e:
                error_msg = f"Failed to deploy skill '{skill_id}': {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)

        # Remove unneeded skills (only MPM skills)
        for skill_id in state.to_remove:
            try:
                if self._is_mpm_skill(deploy_dir, skill_id):
                    self._remove_skill(skill_id, deploy_dir)
                    result.removed.append(skill_id)
                    logger.info(f"Removed skill: {skill_id}")
                else:
                    logger.debug(f"Skipping removal of user skill: {skill_id}")
                    result.unchanged.append(skill_id)
            except Exception as e:
                error_msg = f"Failed to remove skill '{skill_id}': {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)

        # Track unchanged skills
        result.unchanged.extend(list(state.unchanged))

        return result

    def _get_agent_state(
        self, cache_dir: Path, deploy_dir: Path
    ) -> ReconciliationState:
        """Get current agent deployment state."""
        # Start with enabled agents
        configured_agents = set(self.config.agents.enabled)

        # Add required agents (cannot be disabled)
        configured_agents.update(self.config.agents.required)

        # Add universal agents if enabled
        if self.config.agents.include_universal:
            universal_agents = self._get_universal_agents(cache_dir)
            configured_agents.update(universal_agents)

        return ReconciliationState(
            configured=configured_agents,
            deployed=self._list_deployed_agents(deploy_dir),
            cached=self._list_cached_agents(cache_dir),
        )

    def _get_universal_agents(self, cache_dir: Path) -> Set[str]:
        """Get all agents with 'universal' toolchain/category."""
        universal_agents = set()
        if not cache_dir.exists():
            return universal_agents

        for agent_file in cache_dir.glob("**/*.md"):
            try:
                # Read frontmatter to check toolchain/category
                content = agent_file.read_text(encoding="utf-8")

                # Check for universal markers in frontmatter (within first 1000 chars)
                frontmatter_section = content[:1000].lower()
                if (
                    "toolchain: universal" in frontmatter_section
                    or "category: universal" in frontmatter_section
                    or "toolchain:\n  - universal" in frontmatter_section
                ):
                    universal_agents.add(agent_file.stem)
            except Exception as e:
                logger.debug(
                    f"Failed to check universal marker for {agent_file.name}: {e}"
                )
                continue

        return universal_agents

    def _list_deployed_agents(self, deploy_dir: Path) -> Set[str]:
        """List agent IDs currently deployed."""
        if not deploy_dir.exists():
            return set()

        agent_ids = set()
        for agent_file in deploy_dir.glob("*.md"):
            # Extract agent ID from filename (remove .md extension)
            agent_id = agent_file.stem
            agent_ids.add(agent_id)

        return agent_ids

    def _list_cached_agents(self, cache_dir: Path) -> Set[str]:
        """List agent IDs available in cache."""
        if not cache_dir.exists():
            return set()

        agent_ids = set()
        for agent_file in cache_dir.glob("**/*.md"):
            # Extract agent ID from filename
            agent_id = agent_file.stem
            agent_ids.add(agent_id)

        return agent_ids

    def _list_deployed_skills(self, deploy_dir: Path) -> Set[str]:
        """List skill IDs currently deployed."""
        if not deploy_dir.exists():
            return set()

        skill_ids = set()
        for skill_file in deploy_dir.glob("*.md"):
            skill_id = skill_file.stem
            skill_ids.add(skill_id)

        return skill_ids

    def _list_cached_skills(self, cache_dir: Path) -> Set[str]:
        """List skill IDs available in cache."""
        if not cache_dir.exists():
            return set()

        skill_ids = set()
        for skill_file in cache_dir.glob("**/*.md"):
            skill_id = skill_file.stem
            skill_ids.add(skill_id)

        return skill_ids

    def _deploy_agent(self, agent_id: str, cache_dir: Path, deploy_dir: Path) -> None:
        """Deploy agent from cache to project directory."""
        # Find agent file in cache
        agent_file = self._find_file_in_cache(agent_id, cache_dir, "*.md")
        if not agent_file:
            raise FileNotFoundError(f"Agent file for '{agent_id}' not found in cache")

        # Ensure deploy directory exists
        deploy_dir.mkdir(parents=True, exist_ok=True)

        # Copy agent file to deployment directory
        dest_file = deploy_dir / agent_file.name
        shutil.copy2(agent_file, dest_file)

    def _deploy_skill(self, skill_id: str, cache_dir: Path, deploy_dir: Path) -> None:
        """Deploy skill from cache to project directory."""
        # Find skill file in cache
        skill_file = self._find_file_in_cache(skill_id, cache_dir, "*.md")
        if not skill_file:
            raise FileNotFoundError(f"Skill file for '{skill_id}' not found in cache")

        # Ensure deploy directory exists
        deploy_dir.mkdir(parents=True, exist_ok=True)

        # Copy skill file to deployment directory
        dest_file = deploy_dir / skill_file.name
        shutil.copy2(skill_file, dest_file)

    def _remove_agent(self, agent_id: str, deploy_dir: Path) -> None:
        """Remove deployed agent."""
        agent_file = deploy_dir / f"{agent_id}.md"
        if agent_file.exists():
            agent_file.unlink()

    def _remove_skill(self, skill_id: str, deploy_dir: Path) -> None:
        """Remove deployed skill."""
        skill_file = deploy_dir / f"{skill_id}.md"
        if skill_file.exists():
            skill_file.unlink()

    def _is_mpm_agent(self, deploy_dir: Path, agent_id: str) -> bool:
        """Check if agent is managed by MPM (not user-created)."""
        agent_file = deploy_dir / f"{agent_id}.md"
        if not agent_file.exists():
            return False

        try:
            content = agent_file.read_text(encoding="utf-8")
            # Check for MPM author markers
            mpm_markers = [
                "author: claude-mpm",
                "author: 'claude-mpm'",
                "author: anthropic",
            ]
            return any(marker in content.lower() for marker in mpm_markers)
        except Exception as e:
            logger.warning(f"Failed to check MPM marker for {agent_id}: {e}")
            return False

    def _is_mpm_skill(self, deploy_dir: Path, skill_id: str) -> bool:
        """Check if skill is managed by MPM (not user-created)."""
        skill_file = deploy_dir / f"{skill_id}.md"
        if not skill_file.exists():
            return False

        try:
            content = skill_file.read_text(encoding="utf-8")
            # Check for MPM author markers
            mpm_markers = [
                "author: claude-mpm",
                "author: 'claude-mpm'",
                "author: anthropic",
            ]
            return any(marker in content.lower() for marker in mpm_markers)
        except Exception as e:
            logger.warning(f"Failed to check MPM marker for {skill_id}: {e}")
            return False

    def _find_file_in_cache(
        self, item_id: str, cache_dir: Path, pattern: str
    ) -> Optional[Path]:
        """Find file in cache directory by ID pattern."""
        # Try exact match first
        exact_match = cache_dir / f"{item_id}.md"
        if exact_match.exists():
            return exact_match

        # Search recursively
        for file_path in cache_dir.glob(f"**/{item_id}.md"):
            return file_path

        return None

    def _get_agent_skill_dependencies(self, agent_ids: List[str]) -> Set[str]:
        """
        Get skill dependencies for enabled agents.

        This reads agent frontmatter to find required skills.

        Args:
            agent_ids: List of enabled agent IDs

        Returns:
            Set of skill IDs required by these agents
        """
        skill_deps = set()

        # Get deployed agents directory
        project_path = Path.cwd()
        agents_dir = project_path / ".claude" / "agents"

        if not agents_dir.exists():
            logger.debug("No agents directory found, cannot extract skill dependencies")
            return skill_deps

        for agent_id in agent_ids:
            agent_file = agents_dir / f"{agent_id}.md"
            if not agent_file.exists():
                logger.debug(
                    f"Agent file not found for {agent_id}, skipping skill dependency extraction"
                )
                continue

            try:
                # Parse frontmatter to get skills list
                skills = self._parse_agent_skills_from_frontmatter(agent_file)
                if skills:
                    logger.debug(f"Agent {agent_id} requires skills: {skills}")
                    skill_deps.update(skills)
            except Exception as e:
                logger.warning(f"Failed to parse skills from {agent_id}: {e}")

        return skill_deps

    def _parse_agent_skills_from_frontmatter(self, agent_file: Path) -> List[str]:
        """
        Parse skills list from agent frontmatter.

        Expected frontmatter format:
        ---
        name: Python Engineer
        skills:
          - pytest
          - git-workflow
        ---

        Args:
            agent_file: Path to agent .md file

        Returns:
            List of skill IDs from frontmatter (empty if none found)
        """
        try:
            import yaml
        except ImportError:
            logger.warning("PyYAML not installed, cannot parse agent frontmatter")
            return []

        try:
            content = agent_file.read_text(encoding="utf-8")

            # Check for frontmatter delimiters
            if not content.startswith("---"):
                return []

            # Find end of frontmatter
            end_marker = content.find("\n---\n", 4)
            if end_marker == -1:
                end_marker = content.find("\n---\r\n", 4)

            if end_marker == -1:
                logger.debug(
                    f"No valid frontmatter end marker found in {agent_file.name}"
                )
                return []

            # Extract frontmatter YAML
            frontmatter_yaml = content[4:end_marker]

            # Parse YAML
            frontmatter = yaml.safe_load(frontmatter_yaml)

            if not frontmatter or not isinstance(frontmatter, dict):
                return []

            # Get skills list
            skills = frontmatter.get("skills", [])
            if isinstance(skills, list):
                return [str(skill) for skill in skills]
            logger.debug(
                f"Skills field in {agent_file.name} is not a list: {type(skills)}"
            )
            return []

        except yaml.YAMLError as e:
            logger.warning(
                f"Failed to parse YAML frontmatter in {agent_file.name}: {e}"
            )
            return []
        except Exception as e:
            logger.warning(
                f"Unexpected error parsing frontmatter in {agent_file.name}: {e}"
            )
            return []

    def get_reconciliation_view(
        self, project_path: Optional[Path] = None
    ) -> Dict[str, ReconciliationState]:
        """
        Get reconciliation view for agents and skills.

        Args:
            project_path: Project directory

        Returns:
            Dictionary with 'agents' and 'skills' reconciliation states
        """
        project_path = project_path or Path.cwd()

        # Get agent state
        agent_cache = self.path_manager.get_cache_dir() / "agents"
        agent_deploy = project_path / ".claude" / "agents"
        agent_state = self._get_agent_state(agent_cache, agent_deploy)

        # Get skill state
        skill_cache = self.path_manager.get_cache_dir() / "skills"
        skill_deploy = project_path / ".claude" / "skills"

        configured_skills = set(self.config.skills.enabled)
        if self.config.skills.auto_detect_dependencies:
            configured_skills.update(
                self._get_agent_skill_dependencies(self.config.agents.enabled)
            )

        skill_state = ReconciliationState(
            configured=configured_skills,
            deployed=self._list_deployed_skills(skill_deploy),
            cached=self._list_cached_skills(skill_cache),
        )

        return {"agents": agent_state, "skills": skill_state}
