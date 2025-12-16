"""Service for mapping skills to agents based on YAML configuration.

WHY: Progressive skills discovery requires knowing which agents need which skills.
This service uses a YAML configuration to map skill paths to agent IDs, enabling
selective skill deployment based on agent requirements.

DESIGN DECISIONS:
- Load YAML configuration with skill_path -> [agent_ids] mappings
- Handle ALL_AGENTS marker expansion from YAML anchor
- Build inverse index (agent_id -> [skill_paths]) for efficient lookup
- Support pattern-based inference for unmatched skill paths
- Cache configuration to avoid repeated file I/O

YAML Configuration Format:
    skill_mappings:
      toolchains/python/frameworks/django:
        - python-engineer
        - data-engineer
        - engineer

      universal/collaboration/git-workflow: *all_agents

    inference_rules:
      language_patterns:
        python: [python-engineer, data-engineer, engineer]
      framework_patterns:
        django: [python-engineer, engineer]

    all_agents_list:
      - engineer
      - python-engineer
      - typescript-engineer
      ...

References:
- Feature: Progressive skills discovery (#117)
- Research: docs/research/skill-path-to-agent-mapping-2025-12-16.md
- Config: src/claude_mpm/config/skill_to_agent_mapping.yaml
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from claude_mpm.core.logging_config import get_logger

logger = get_logger(__name__)


class SkillToAgentMapper:
    """Maps skills to agents using YAML configuration.

    This service provides bidirectional mapping between skill paths and agent IDs:
    - Forward: skill_path -> [agent_ids]
    - Inverse: agent_id -> [skill_paths]

    The service uses a YAML configuration file with explicit mappings and
    pattern-based inference rules for skill paths not explicitly mapped.

    Example:
        >>> mapper = SkillToAgentMapper()
        >>> agents = mapper.get_agents_for_skill('toolchains/python/frameworks/django')
        >>> print(agents)
        ['python-engineer', 'data-engineer', 'engineer', 'api-qa']

        >>> skills = mapper.get_skills_for_agent('python-engineer')
        >>> print(f"Found {len(skills)} skills for python-engineer")
    """

    # Default configuration path (relative to package root)
    DEFAULT_CONFIG_PATH = (
        Path(__file__).parent.parent.parent / "config" / "skill_to_agent_mapping.yaml"
    )

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize skill-to-agent mapper.

        Args:
            config_path: Optional path to YAML config file.
                        If None, uses default config from package.

        Raises:
            FileNotFoundError: If config file not found
            yaml.YAMLError: If config file is invalid YAML
            ValueError: If config file is missing required sections
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.logger = get_logger(__name__)

        # Load and validate configuration
        self._config = self._load_config()

        # Build forward and inverse indexes
        self._skill_to_agents: Dict[str, List[str]] = {}
        self._agent_to_skills: Dict[str, List[str]] = {}
        self._build_indexes()

        self.logger.info(
            f"SkillToAgentMapper initialized: {len(self._skill_to_agents)} skill mappings, "
            f"{len(self._agent_to_skills)} agents"
        )

    def _load_config(self) -> Dict[str, Any]:
        """Load and validate YAML configuration.

        Returns:
            Parsed YAML configuration

        Raises:
            FileNotFoundError: If config file not found
            yaml.YAMLError: If config file is invalid YAML
            ValueError: If config file is missing required sections
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        try:
            with open(self.config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in {self.config_path}: {e}") from e

        # Validate required sections
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a YAML dictionary")

        if "skill_mappings" not in config:
            raise ValueError("Configuration missing required section: skill_mappings")

        if "all_agents_list" not in config:
            raise ValueError("Configuration missing required section: all_agents_list")

        self.logger.debug(f"Loaded configuration from {self.config_path}")
        return config

    def _build_indexes(self) -> None:
        """Build forward and inverse mapping indexes.

        Processes skill_mappings from config and expands ALL_AGENTS markers.
        Builds bidirectional indexes for efficient lookup.

        Index Structure:
            _skill_to_agents: {"skill/path": ["agent1", "agent2", ...]}
            _agent_to_skills: {"agent1": ["skill/path1", "skill/path2", ...]}
        """
        skill_mappings = self._config["skill_mappings"]
        all_agents = self._config["all_agents_list"]

        for skill_path, agent_list in skill_mappings.items():
            # Handle ALL_AGENTS marker expansion
            if (
                isinstance(agent_list, list)
                and len(agent_list) == 1
                and agent_list[0] == "ALL_AGENTS"
            ):
                expanded_agents = all_agents.copy()
                self.logger.debug(
                    f"Expanded ALL_AGENTS for {skill_path}: {len(expanded_agents)} agents"
                )
            else:
                expanded_agents = agent_list

            # Ensure agent_list is actually a list
            if not isinstance(expanded_agents, list):
                self.logger.warning(
                    f"Invalid agent list for {skill_path}: {type(expanded_agents)}. Skipping."
                )
                continue

            # Build forward index: skill -> agents
            self._skill_to_agents[skill_path] = expanded_agents

            # Build inverse index: agent -> skills
            for agent_id in expanded_agents:
                if agent_id not in self._agent_to_skills:
                    self._agent_to_skills[agent_id] = []
                self._agent_to_skills[agent_id].append(skill_path)

        self.logger.debug(
            f"Built indexes: {len(self._skill_to_agents)} skills, {len(self._agent_to_skills)} agents"
        )

    def get_agents_for_skill(self, skill_path: str) -> List[str]:
        """Get list of agent IDs for a skill path.

        Looks up skill path in configuration. If not found, attempts to infer
        agents using pattern-based rules.

        Args:
            skill_path: Skill path (e.g., "toolchains/python/frameworks/django")

        Returns:
            List of agent IDs that should receive this skill.
            Empty list if no mapping found and inference fails.

        Example:
            >>> agents = mapper.get_agents_for_skill('toolchains/python/frameworks/django')
            >>> print(agents)
            ['python-engineer', 'data-engineer', 'engineer', 'api-qa']

            >>> # Fallback to inference
            >>> agents = mapper.get_agents_for_skill('toolchains/python/new-framework')
            >>> print(agents)
            ['python-engineer', 'data-engineer', 'engineer']
        """
        # Try exact match first
        if skill_path in self._skill_to_agents:
            return self._skill_to_agents[skill_path].copy()

        # Fallback to pattern-based inference
        inferred_agents = self.infer_agents_from_pattern(skill_path)
        if inferred_agents:
            self.logger.debug(
                f"Inferred {len(inferred_agents)} agents for unmapped skill: {skill_path}"
            )
            return inferred_agents

        # No mapping or inference available
        self.logger.debug(f"No mapping or inference available for skill: {skill_path}")
        return []

    def get_skills_for_agent(self, agent_id: str) -> List[str]:
        """Get list of skill paths for an agent (inverse lookup).

        Args:
            agent_id: Agent identifier (e.g., "python-engineer")

        Returns:
            List of skill paths assigned to this agent.
            Empty list if agent not found in configuration.

        Example:
            >>> skills = mapper.get_skills_for_agent('python-engineer')
            >>> print(f"Found {len(skills)} skills")
            >>> for skill in skills[:5]:
            ...     print(f"  - {skill}")
        """
        if agent_id not in self._agent_to_skills:
            self.logger.debug(f"No skills found for agent: {agent_id}")
            return []

        return self._agent_to_skills[agent_id].copy()

    def infer_agents_from_pattern(self, skill_path: str) -> List[str]:
        """Infer agents for a skill path using pattern matching.

        Uses inference_rules from configuration to match skill paths against
        language, framework, and domain patterns.

        Pattern Matching Algorithm:
        1. Extract path components (language, framework, domain)
        2. Match against language_patterns (e.g., "python" -> python-engineer)
        3. Match against framework_patterns (e.g., "django" -> django agents)
        4. Match against domain_patterns (e.g., "testing" -> qa agents)
        5. Combine and deduplicate results

        Args:
            skill_path: Skill path to infer agents for

        Returns:
            List of inferred agent IDs, or empty list if no patterns match

        Example:
            >>> # Infer from language pattern
            >>> agents = mapper.infer_agents_from_pattern('toolchains/python/new-lib')
            >>> 'python-engineer' in agents
            True

            >>> # Infer from framework pattern
            >>> agents = mapper.infer_agents_from_pattern('toolchains/typescript/frameworks/nextjs-advanced')
            >>> 'nextjs-engineer' in agents
            True
        """
        if "inference_rules" not in self._config:
            return []

        inference_rules = self._config["inference_rules"]
        inferred_agents: Set[str] = set()

        # Normalize skill path for matching (lowercase, split on /)
        path_parts = skill_path.lower().split("/")

        # Match language patterns
        if "language_patterns" in inference_rules:
            for language, agents in inference_rules["language_patterns"].items():
                if language in path_parts:
                    inferred_agents.update(agents)
                    self.logger.debug(
                        f"Matched language pattern '{language}' in {skill_path}"
                    )

        # Match framework patterns
        if "framework_patterns" in inference_rules:
            for framework, agents in inference_rules["framework_patterns"].items():
                # Match framework name anywhere in path (e.g., "nextjs" in path)
                if any(framework in part for part in path_parts):
                    inferred_agents.update(agents)
                    self.logger.debug(
                        f"Matched framework pattern '{framework}' in {skill_path}"
                    )

        # Match domain patterns
        if "domain_patterns" in inference_rules:
            for domain, agents in inference_rules["domain_patterns"].items():
                if domain in path_parts:
                    inferred_agents.update(agents)
                    self.logger.debug(
                        f"Matched domain pattern '{domain}' in {skill_path}"
                    )

        return sorted(inferred_agents)

    def get_all_mapped_skills(self) -> List[str]:
        """Get all skill paths with explicit mappings.

        Returns:
            List of all skill paths in configuration (sorted)

        Example:
            >>> skills = mapper.get_all_mapped_skills()
            >>> print(f"Total mapped skills: {len(skills)}")
        """
        return sorted(self._skill_to_agents.keys())

    def get_all_agents(self) -> List[str]:
        """Get all agent IDs referenced in mappings.

        Returns:
            List of all agent IDs in configuration (sorted)

        Example:
            >>> agents = mapper.get_all_agents()
            >>> print(f"Total agents: {len(agents)}")
        """
        return sorted(self._agent_to_skills.keys())

    def is_skill_mapped(self, skill_path: str) -> bool:
        """Check if skill path has an explicit mapping.

        Args:
            skill_path: Skill path to check

        Returns:
            True if skill has explicit mapping, False otherwise

        Example:
            >>> mapper.is_skill_mapped('toolchains/python/frameworks/django')
            True
            >>> mapper.is_skill_mapped('toolchains/python/unknown')
            False
        """
        return skill_path in self._skill_to_agents

    def get_mapping_stats(self) -> Dict[str, Any]:
        """Get statistics about skill-to-agent mappings.

        Returns:
            Dictionary with mapping statistics:
            {
                "total_skills": int,
                "total_agents": int,
                "avg_agents_per_skill": float,
                "avg_skills_per_agent": float,
                "config_path": str,
                "config_version": str
            }

        Example:
            >>> stats = mapper.get_mapping_stats()
            >>> print(f"Total skills: {stats['total_skills']}")
            >>> print(f"Total agents: {stats['total_agents']}")
        """
        total_skills = len(self._skill_to_agents)
        total_agents = len(self._agent_to_skills)

        # Calculate averages
        avg_agents_per_skill = (
            sum(len(agents) for agents in self._skill_to_agents.values()) / total_skills
            if total_skills > 0
            else 0.0
        )

        avg_skills_per_agent = (
            sum(len(skills) for skills in self._agent_to_skills.values()) / total_agents
            if total_agents > 0
            else 0.0
        )

        return {
            "total_skills": total_skills,
            "total_agents": total_agents,
            "avg_agents_per_skill": round(avg_agents_per_skill, 2),
            "avg_skills_per_agent": round(avg_skills_per_agent, 2),
            "config_path": str(self.config_path),
            "config_version": self._config.get("metadata", {}).get(
                "version", "unknown"
            ),
        }

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"SkillToAgentMapper(skills={len(self._skill_to_agents)}, "
            f"agents={len(self._agent_to_skills)})"
        )
