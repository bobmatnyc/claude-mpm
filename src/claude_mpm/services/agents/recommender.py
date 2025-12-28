"""
Agent Recommender Service for Claude MPM Framework
===================================================

WHY: Automated agent recommendation is critical for the auto-configuration feature.
This service analyzes project toolchains and recommends appropriate specialized agents
using configuration-driven mappings and intelligent scoring algorithms.

DESIGN DECISION: Configuration-driven approach using YAML for flexibility and
maintainability. Scoring algorithm weighs language, framework, and deployment matches
with configurable weights. Returns ranked recommendations with detailed reasoning.

Part of TSK-0054: Auto-Configuration Feature - Phase 3
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from claude_mpm.core.base_service import BaseService
from claude_mpm.services.core.interfaces.agent import IAgentRecommender
from claude_mpm.services.core.models.agent_config import (
    AgentCapabilities,
    AgentRecommendation,
    AgentSpecialization,
)
from claude_mpm.services.core.models.toolchain import ToolchainAnalysis


class AgentRecommenderService(BaseService, IAgentRecommender):
    """
    Service for recommending agents based on toolchain analysis.

    This service:
    - Loads agent capabilities from YAML configuration
    - Calculates match scores between toolchains and agents
    - Returns ranked recommendations with confidence scores
    - Provides detailed reasoning for each recommendation

    Matching Algorithm:
    - Primary language match (50% weight)
    - Framework match (30% weight)
    - Deployment target match (20% weight)
    - Apply agent-specific confidence weights
    - Framework-specific agents override language agents
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
        container: Optional[Any] = None,
    ):
        """
        Initialize the Agent Recommender Service.

        Args:
            config_path: Optional path to agent_capabilities.yaml
            config: Optional configuration dictionary
            container: Optional service container for dependency injection
        """
        super().__init__(
            name="AgentRecommenderService",
            config=config,
            enable_enhanced_features=False,
            container=container,
        )

        # Determine config file path
        if config_path is None:
            # Default to config directory in the package
            package_config_dir = Path(__file__).parent.parent.parent / "config"
            config_path = package_config_dir / "agent_capabilities.yaml"

        self.config_path = config_path
        self._capabilities_config: Dict[str, Any] = {}
        self._agent_capabilities_cache: Dict[str, AgentCapabilities] = {}
        self._load_configuration()

        self.logger.info(
            f"AgentRecommenderService initialized with config: {self.config_path}"
        )

    async def _initialize(self) -> None:
        """Initialize the service (required by BaseService)."""
        # Configuration is loaded in __init__, no additional initialization needed

    async def _cleanup(self) -> None:
        """Cleanup service resources (required by BaseService)."""
        # Clear caches
        self._agent_capabilities_cache.clear()
        self._capabilities_config.clear()

    def _load_configuration(self) -> None:
        """
        Load agent capabilities configuration from YAML file.

        Raises:
            FileNotFoundError: If configuration file does not exist
            yaml.YAMLError: If configuration file is invalid YAML
        """
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Agent capabilities config not found: {self.config_path}"
            )

        try:
            with self.config_path.open(encoding="utf-8") as f:
                self._capabilities_config = yaml.safe_load(f)

            if (
                not self._capabilities_config
                or "agent_capabilities" not in self._capabilities_config
            ):
                raise ValueError(
                    "Invalid configuration: missing 'agent_capabilities' section"
                )

            self.logger.info(
                f"Loaded {len(self._capabilities_config['agent_capabilities'])} "
                f"agent capability definitions"
            )

        except yaml.YAMLError as e:
            self.logger.error(f"Failed to parse YAML configuration: {e}")
            raise

    def recommend_agents(
        self,
        toolchain: ToolchainAnalysis,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> List[AgentRecommendation]:
        """
        Recommend agents based on toolchain analysis.

        Analyzes the toolchain and recommends agents that best match the
        project's technical requirements. Considers:
        - Language compatibility
        - Framework expertise
        - Deployment environment requirements
        - Optional user-defined constraints

        Args:
            toolchain: Complete toolchain analysis results
            constraints: Optional constraints for recommendations:
                - max_agents: Maximum number of agents to recommend
                - required_capabilities: List of required agent capabilities
                - excluded_agents: List of agent IDs to exclude
                - min_confidence: Minimum confidence score threshold

        Returns:
            List[AgentRecommendation]: Ordered list of recommended agents
                with confidence scores and reasoning

        Raises:
            ValueError: If constraints are invalid or contradictory
        """
        constraints = constraints or {}
        min_confidence = constraints.get(
            "min_confidence",
            self._capabilities_config.get("recommendation_rules", {}).get(
                "min_confidence_threshold", 0.5
            ),
        )
        excluded_agents = set(constraints.get("excluded_agents", []))
        max_agents = constraints.get("max_agents")

        recommendations: List[AgentRecommendation] = []
        agent_configs = self._capabilities_config.get("agent_capabilities", {})

        # Calculate scores for all agents
        for agent_id, agent_config in agent_configs.items():
            # Skip excluded agents
            if agent_id in excluded_agents:
                continue

            # Skip agents that shouldn't auto-deploy unless explicitly allowed
            if not agent_config.get("auto_deploy", True) and not constraints.get(
                "include_non_auto_deploy", False
            ):
                continue

            # Calculate match score
            score = self.match_score(agent_id, toolchain)

            # Filter by minimum confidence
            if score < min_confidence:
                continue

            # Get agent capabilities
            capabilities = self.get_agent_capabilities(agent_id)

            # Generate match reasons and concerns
            match_reasons, concerns = self._generate_reasoning(
                agent_id, agent_config, toolchain, score
            )

            # Determine deployment priority
            deployment_priority = self._calculate_deployment_priority(
                agent_config, toolchain
            )

            recommendation = AgentRecommendation(
                agent_id=agent_id,
                agent_name=agent_config.get("name", agent_id),
                confidence_score=score,
                match_reasons=match_reasons,
                concerns=concerns,
                capabilities=capabilities,
                deployment_priority=deployment_priority,
                configuration_hints=self._generate_config_hints(
                    agent_config, toolchain
                ),
                metadata={
                    "specialization": agent_config.get("specialization"),
                    "auto_deploy": agent_config.get("auto_deploy", True),
                },
            )
            recommendations.append(recommendation)

        # Sort by confidence score (descending), then by deployment priority (ascending)
        recommendations.sort(key=lambda r: (-r.confidence_score, r.deployment_priority))

        # Apply max agents limit if specified
        if max_agents is not None:
            recommendations = recommendations[:max_agents]

        # Check if we have no recommendations (any reason: unknown language, low scores, etc.)
        if not recommendations:
            self.logger.info(
                f"No agents scored above threshold for {toolchain.primary_language}; using defaults"
            )

            # Get default configuration
            default_config = self._capabilities_config.get("default_configuration", {})
            if default_config.get("enabled", False):
                default_agents = default_config.get("agents", [])
                default_confidence = default_config.get("min_confidence", 0.7)

                for default_agent in default_agents:
                    agent_id = default_agent.get("agent_id")

                    # Skip if agent doesn't exist in capabilities
                    if agent_id not in agent_configs:
                        self.logger.warning(f"Default agent not found: {agent_id}")
                        continue

                    agent_config = agent_configs[agent_id]
                    capabilities = self.get_agent_capabilities(agent_id)

                    recommendation = AgentRecommendation(
                        agent_id=agent_id,
                        agent_name=agent_config.get("name", agent_id),
                        confidence_score=default_confidence,
                        match_reasons=[
                            "Default configuration applied - toolchain detection unsuccessful",
                            default_agent.get("reasoning", "General-purpose agent"),
                        ],
                        concerns=[
                            "Consider manually selecting specialized agents for better results"
                        ],
                        capabilities=capabilities,
                        deployment_priority=default_agent.get("priority", 10),
                        configuration_hints={"default_deployment": True},
                        metadata={
                            "is_default": True,
                            "specialization": agent_config.get("specialization"),
                            "auto_deploy": agent_config.get("auto_deploy", True),
                        },
                    )
                    recommendations.append(recommendation)

                self.logger.info(
                    f"Applied {len(recommendations)} default agent recommendations"
                )

        self.logger.info(
            f"Generated {len(recommendations)} agent recommendations "
            f"for project: {toolchain.project_path}"
        )

        return recommendations

    def get_agent_capabilities(self, agent_id: str) -> AgentCapabilities:
        """
        Get detailed capabilities for an agent.

        Retrieves comprehensive capability information for a specific agent:
        - Supported languages and frameworks
        - Specialization areas
        - Required toolchain components
        - Performance characteristics

        Args:
            agent_id: Unique identifier of the agent

        Returns:
            AgentCapabilities: Complete capability information

        Raises:
            KeyError: If agent_id does not exist
        """
        # Check cache first
        if agent_id in self._agent_capabilities_cache:
            return self._agent_capabilities_cache[agent_id]

        # Get from config
        agent_configs = self._capabilities_config.get("agent_capabilities", {})
        if agent_id not in agent_configs:
            raise KeyError(f"Agent not found: {agent_id}")

        agent_config = agent_configs[agent_id]
        supports = agent_config.get("supports", {})

        # Determine specializations
        specializations = []
        spec_type = agent_config.get("specialization", "general")
        if spec_type == "engineering":
            specializations.append(AgentSpecialization.LANGUAGE_SPECIFIC)
        elif spec_type == "devops":
            specializations.append(AgentSpecialization.DEVOPS)

        # Create capabilities object
        capabilities = AgentCapabilities(
            agent_id=agent_id,
            agent_name=agent_config.get("name", agent_id),
            specializations=specializations,
            supported_languages=supports.get("languages", []),
            supported_frameworks=supports.get("frameworks", []),
            required_tools=supports.get("build_tools", []),
            deployment_targets=supports.get("deployment", []),
            description=agent_config.get("description", ""),
            metadata=agent_config.get("metadata", {}),
        )

        # Cache for future use
        self._agent_capabilities_cache[agent_id] = capabilities

        return capabilities

    def match_score(self, agent_id: str, toolchain: ToolchainAnalysis) -> float:
        """
        Calculate match score between agent and toolchain.

        Computes a numerical score (0.0 to 1.0) indicating how well an agent
        matches the project's toolchain. Higher scores indicate better matches.
        Considers:
        - Language compatibility (50% weight)
        - Framework experience (30% weight)
        - Deployment target alignment (20% weight)
        - Toolchain component coverage

        Args:
            agent_id: Unique identifier of the agent
            toolchain: Complete toolchain analysis

        Returns:
            float: Match score between 0.0 (no match) and 1.0 (perfect match)

        Raises:
            KeyError: If agent_id does not exist
        """
        agent_configs = self._capabilities_config.get("agent_capabilities", {})
        if agent_id not in agent_configs:
            raise KeyError(f"Agent not found: {agent_id}")

        agent_config = agent_configs[agent_id]
        supports = agent_config.get("supports", {})

        # Get scoring weights
        scoring_weights = self._capabilities_config.get("recommendation_rules", {}).get(
            "scoring_weights", {}
        )
        language_weight = scoring_weights.get("language_match", 0.5)
        framework_weight = scoring_weights.get("framework_match", 0.3)
        deployment_weight = scoring_weights.get("deployment_match", 0.2)

        # Calculate language match score
        language_score = self._calculate_language_score(
            supports.get("languages", []), toolchain
        )

        # Calculate framework match score
        framework_score = self._calculate_framework_score(
            supports.get("frameworks", []), toolchain
        )

        # Calculate deployment match score
        deployment_score = self._calculate_deployment_score(
            supports.get("deployment", []), toolchain
        )

        # Calculate base score
        base_score = (
            language_score * language_weight
            + framework_score * framework_weight
            + deployment_score * deployment_weight
        )

        # Apply agent confidence weight
        agent_confidence_weight = agent_config.get("confidence_weight", 1.0)
        final_score = base_score * agent_confidence_weight

        # Apply framework priority boost if applicable
        if framework_score > 0.5:  # Strong framework match
            framework_boost = self._capabilities_config.get(
                "recommendation_rules", {}
            ).get("framework_priority_boost", 0.15)
            final_score = min(1.0, final_score + framework_boost)

        # Apply deployment match boost if applicable
        if deployment_score > 0.5:  # Strong deployment match
            deployment_boost = self._capabilities_config.get(
                "recommendation_rules", {}
            ).get("deployment_match_boost", 0.1)
            final_score = min(1.0, final_score + deployment_boost)

        # Ensure score is in valid range and return
        return max(0.0, min(1.0, final_score))

    def _calculate_language_score(
        self, supported_languages: List[str], toolchain: ToolchainAnalysis
    ) -> float:
        """Calculate language match score."""
        if not supported_languages:
            return 0.0

        primary_language = toolchain.primary_language.lower()
        all_languages = [lang.lower() for lang in toolchain.all_languages]

        # Check for primary language match
        for lang in supported_languages:
            if lang.lower() == primary_language:
                return 1.0  # Perfect match on primary language

        # Check for secondary language match
        for lang in supported_languages:
            if lang.lower() in all_languages:
                return 0.6  # Partial match on secondary language

        return 0.0

    def _calculate_framework_score(
        self, supported_frameworks: List[str], toolchain: ToolchainAnalysis
    ) -> float:
        """Calculate framework match score."""
        if not supported_frameworks:
            return 0.0

        detected_frameworks = [fw.name.lower() for fw in toolchain.frameworks]
        if not detected_frameworks:
            return 0.0

        # Check for exact framework matches
        matches = 0
        for fw in supported_frameworks:
            fw_lower = fw.lower()
            # Normalize common variants (next.js vs nextjs, etc.)
            fw_normalized = fw_lower.replace(".", "").replace("-", "")
            for detected_fw in detected_frameworks:
                detected_normalized = detected_fw.replace(".", "").replace("-", "")
                if fw_normalized == detected_normalized:
                    matches += 1
                    break

        if matches == 0:
            return 0.0

        # Calculate score based on match proportion
        match_ratio = matches / len(detected_frameworks)
        return min(1.0, match_ratio * 1.2)  # Boost for framework matches

    def _calculate_deployment_score(
        self, supported_deployments: List[str], toolchain: ToolchainAnalysis
    ) -> float:
        """Calculate deployment target match score."""
        if not supported_deployments or not toolchain.deployment_target:
            return 0.0

        target_platform = toolchain.deployment_target.platform
        target_type = toolchain.deployment_target.target_type

        # Check for exact platform match
        for deployment in supported_deployments:
            deployment_lower = deployment.lower()
            if target_platform and deployment_lower == target_platform.lower():
                return 1.0  # Perfect match on platform
            if deployment_lower == target_type.lower():
                return 0.8  # Good match on target type

        # Check for container/cloud general matches
        if any(d.lower() in ["docker", "kubernetes"] for d in supported_deployments):
            if target_type in ["container", "cloud"]:
                return 0.5  # General container/cloud match

        return 0.0

    def _generate_reasoning(
        self,
        agent_id: str,
        agent_config: Dict[str, Any],
        toolchain: ToolchainAnalysis,
        score: float,
    ) -> tuple[List[str], List[str]]:
        """
        Generate match reasons and concerns for recommendation.

        Returns:
            Tuple of (match_reasons, concerns)
        """
        match_reasons = []
        concerns = []
        supports = agent_config.get("supports", {})

        # Check language match
        primary_language = toolchain.primary_language.lower()
        supported_languages = [lang.lower() for lang in supports.get("languages", [])]
        if primary_language in supported_languages:
            match_reasons.append(
                f"Primary language match: {toolchain.primary_language}"
            )

        # Check framework matches
        detected_frameworks = [fw.name for fw in toolchain.frameworks]
        supported_frameworks = supports.get("frameworks", [])
        framework_matches = []
        for fw in detected_frameworks:
            for supported_fw in supported_frameworks:
                if fw.lower().replace("-", "").replace(
                    ".", ""
                ) == supported_fw.lower().replace("-", "").replace(".", ""):
                    framework_matches.append(fw)
                    break

        if framework_matches:
            match_reasons.append(f"Framework expertise: {', '.join(framework_matches)}")

        # Check deployment target match
        if toolchain.deployment_target:
            supported_deployments = supports.get("deployment", [])
            platform = toolchain.deployment_target.platform
            if platform and any(
                d.lower() == platform.lower() for d in supported_deployments
            ):
                match_reasons.append(f"Deployment platform match: {platform}")

        # Add concerns for low/medium confidence
        if score < 0.6:
            concerns.append(
                "Moderate confidence - consider reviewing agent capabilities"
            )
        elif score < 0.8:
            concerns.append("Good match but may benefit from additional configuration")

        # If no specific matches found but score > 0, add general reason
        if not match_reasons and score > 0:
            match_reasons.append(
                f"General {agent_config.get('specialization', 'agent')} capabilities"
            )

        return match_reasons, concerns

    def _calculate_deployment_priority(
        self, agent_config: Dict[str, Any], toolchain: ToolchainAnalysis
    ) -> int:
        """
        Calculate deployment priority (lower = higher priority).

        Priority rules:
        - Framework-specific agents: Priority 1
        - Language-specific engineers: Priority 2
        - DevOps agents: Priority 3
        - General agents: Priority 4
        """
        specialization = agent_config.get("specialization", "general")
        supports = agent_config.get("supports", {})

        # Check if this is a framework-specific agent
        framework_matches = False
        if toolchain.frameworks:
            detected_frameworks = [fw.name.lower() for fw in toolchain.frameworks]
            supported_frameworks = [fw.lower() for fw in supports.get("frameworks", [])]
            framework_matches = any(
                fw in supported_frameworks for fw in detected_frameworks
            )

        if framework_matches and specialization == "engineering":
            return 1  # Highest priority for framework-specific engineers

        if specialization == "engineering":
            return 2  # Language-specific engineers

        if specialization == "devops":
            return 3  # DevOps agents

        return 4  # General agents (lowest priority)

    def _generate_config_hints(
        self, agent_config: Dict[str, Any], toolchain: ToolchainAnalysis
    ) -> Dict[str, Any]:
        """Generate configuration hints for the agent."""
        hints = {}

        # Add framework-specific hints
        if toolchain.frameworks:
            hints["detected_frameworks"] = [fw.name for fw in toolchain.frameworks]

        # Add deployment hints
        if toolchain.deployment_target:
            hints["deployment_target"] = toolchain.deployment_target.platform

        # Add build tool hints
        if toolchain.build_tools:
            hints["build_tools"] = [tool.name for tool in toolchain.build_tools]

        return hints
