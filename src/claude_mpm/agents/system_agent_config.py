"""
System Agent Configuration with Model Assignments
================================================

Configures system agents with default model assignments and settings.
Integrates with the ModelSelector and default model configuration system.

Key Features:
- System agent metadata with model preferences
- Model capability validation
- Configuration inheritance
- Performance optimization settings
- Agent-specific customization

Created: 2025-07-16
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from claude_mpm.core.logging_utils import get_logger

from ..config.default_model_config import (
    DefaultModelConfigManager,
    get_default_model_for_agent_type,
)
from ..config.model_env_defaults import (
    ModelEnvironmentLoader,
    get_model_for_agent_from_env,
)
from ..services.model_selector import ModelSelector, ModelType

logger = get_logger(__name__)


@dataclass
class SystemAgentConfig:
    """Configuration for a system agent"""

    agent_type: str
    agent_name: str
    description: str
    default_model: str
    capabilities: List[str] = field(default_factory=list)
    specializations: List[str] = field(default_factory=list)
    performance_requirements: Dict[str, Any] = field(default_factory=dict)
    model_preferences: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    priority: int = 100  # Lower number = higher priority

    def get_effective_model(self) -> str:
        """Get the effective model considering environment overrides."""
        # Check environment override
        env_model = get_model_for_agent_from_env(self.agent_type)
        if env_model:
            return env_model

        # Use default model
        return self.default_model


class SystemAgentConfigManager:
    """
    Manager for system agent configurations with model integration.
    """

    def __init__(self):
        """Initialize system agent configuration manager."""
        self.model_config_manager = DefaultModelConfigManager()
        self.model_selector = ModelSelector()
        self.env_loader = ModelEnvironmentLoader()
        self._agents: Dict[str, SystemAgentConfig] = {}
        self._initialize_system_agents()

        logger.info("SystemAgentConfigManager initialized with model integration")

    def _initialize_system_agents(self) -> None:
        """Initialize all system agent configurations."""

        # Core Orchestrator/Engineering Agents (Opus models)
        self._agents["orchestrator"] = SystemAgentConfig(
            agent_type="orchestrator",
            agent_name="Project Orchestrator",
            description="Multi-agent project orchestration and coordination",
            default_model=ModelType.OPUS.value,
            capabilities=[
                "project_management",
                "task_delegation",
                "workflow_coordination",
                "strategic_planning",
                "multi_agent_communication",
                "decision_making",
            ],
            specializations=["orchestration", "coordination", "planning"],
            performance_requirements={
                "reasoning_depth": "expert",
                "task_complexity": "expert",
                "creativity_required": True,
                "speed_priority": False,
            },
            model_preferences={
                "preferred_models": [ModelType.OPUS.value, ModelType.SONNET_4.value],
                "minimum_reasoning_tier": "expert",
                "context_requirements": "high",
            },
            priority=1,
        )

        self._agents["engineer"] = SystemAgentConfig(
            agent_type="engineer",
            agent_name="Software Engineer",
            description="Code implementation, development, and inline documentation",
            default_model=ModelType.OPUS.value,
            capabilities=[
                "code_generation",
                "system_design",
                "architecture_planning",
                "debugging",
                "refactoring",
                "technical_implementation",
            ],
            specializations=["engineering", "development", "implementation"],
            performance_requirements={
                "reasoning_depth": "expert",
                "task_complexity": "high",
                "creativity_required": True,
                "speed_priority": False,
            },
            model_preferences={
                "preferred_models": [ModelType.OPUS.value, ModelType.SONNET_4.value],
                "minimum_reasoning_tier": "expert",
                "context_requirements": "high",
            },
            priority=10,
        )

        self._agents["architecture"] = SystemAgentConfig(
            agent_type="architecture",
            agent_name="Software Architect",
            description="System architecture design and technical planning",
            default_model=ModelType.OPUS.value,
            capabilities=[
                "system_architecture",
                "design_patterns",
                "scalability_planning",
                "technology_selection",
                "architectural_decision_making",
            ],
            specializations=["architecture", "design", "planning"],
            performance_requirements={
                "reasoning_depth": "expert",
                "task_complexity": "expert",
                "creativity_required": True,
                "speed_priority": False,
            },
            model_preferences={
                "preferred_models": [ModelType.OPUS.value],
                "minimum_reasoning_tier": "expert",
                "context_requirements": "high",
            },
            priority=5,
        )

        # Core Support Agents (Sonnet models)
        self._agents["documentation"] = SystemAgentConfig(
            agent_type="documentation",
            agent_name="Documentation Agent",
            description="Project documentation pattern analysis and operational understanding",
            default_model=ModelType.SONNET.value,
            capabilities=[
                "documentation_analysis",
                "technical_writing",
                "changelog_generation",
                "version_documentation",
                "pattern_recognition",
            ],
            specializations=["documentation", "analysis", "writing"],
            performance_requirements={
                "reasoning_depth": "advanced",
                "task_complexity": "medium",
                "creativity_required": False,
                "speed_priority": True,
            },
            model_preferences={
                "preferred_models": [ModelType.SONNET.value, ModelType.SONNET_4.value],
                "minimum_reasoning_tier": "advanced",
                "context_requirements": "medium",
            },
            priority=20,
        )

        self._agents["qa"] = SystemAgentConfig(
            agent_type="qa",
            agent_name="Quality Assurance Agent",
            description="Quality assurance, testing, and validation",
            default_model=ModelType.SONNET.value,
            capabilities=[
                "test_planning",
                "quality_validation",
                "testing_automation",
                "bug_detection",
                "performance_testing",
            ],
            specializations=["qa", "testing", "validation"],
            performance_requirements={
                "reasoning_depth": "advanced",
                "task_complexity": "medium",
                "creativity_required": False,
                "speed_priority": True,
            },
            model_preferences={
                "preferred_models": [ModelType.SONNET.value, ModelType.SONNET_4.value],
                "minimum_reasoning_tier": "advanced",
                "context_requirements": "medium",
            },
            priority=30,
        )

        self._agents["research"] = SystemAgentConfig(
            agent_type="research",
            agent_name="Research Agent",
            description="Investigation, analysis, and information gathering",
            default_model=ModelType.SONNET.value,
            capabilities=[
                "research_methodology",
                "data_analysis",
                "information_synthesis",
                "market_research",
                "technical_investigation",
            ],
            specializations=["research", "analysis", "investigation"],
            performance_requirements={
                "reasoning_depth": "advanced",
                "task_complexity": "medium",
                "creativity_required": False,
                "speed_priority": False,
            },
            model_preferences={
                "preferred_models": [ModelType.SONNET.value, ModelType.SONNET_4.value],
                "minimum_reasoning_tier": "advanced",
                "context_requirements": "high",
            },
            priority=40,
        )

        self._agents["ops"] = SystemAgentConfig(
            agent_type="ops",
            agent_name="Operations Agent",
            description="Deployment, operations, and infrastructure management",
            default_model=ModelType.SONNET.value,
            capabilities=[
                "deployment_automation",
                "infrastructure_management",
                "monitoring_setup",
                "devops_workflows",
                "system_administration",
            ],
            specializations=["ops", "deployment", "infrastructure"],
            performance_requirements={
                "reasoning_depth": "advanced",
                "task_complexity": "medium",
                "creativity_required": False,
                "speed_priority": True,
            },
            model_preferences={
                "preferred_models": [ModelType.SONNET.value, ModelType.SONNET_4.value],
                "minimum_reasoning_tier": "advanced",
                "context_requirements": "medium",
            },
            priority=50,
        )

        self._agents["security"] = SystemAgentConfig(
            agent_type="security",
            agent_name="Security Agent",
            description="Security analysis, vulnerability assessment, and protection",
            default_model=ModelType.SONNET.value,
            capabilities=[
                "security_analysis",
                "vulnerability_assessment",
                "threat_modeling",
                "security_auditing",
                "compliance_checking",
            ],
            specializations=["security", "compliance", "auditing"],
            performance_requirements={
                "reasoning_depth": "advanced",
                "task_complexity": "high",
                "creativity_required": False,
                "speed_priority": False,
            },
            model_preferences={
                "preferred_models": [ModelType.SONNET.value, ModelType.SONNET_4.value],
                "minimum_reasoning_tier": "advanced",
                "context_requirements": "high",
            },
            priority=35,
        )

        self._agents["data_engineer"] = SystemAgentConfig(
            agent_type="data_engineer",
            agent_name="Data Engineer Agent",
            description="Data store management and AI API integrations",
            default_model=ModelType.SONNET.value,
            capabilities=[
                "database_management",
                "data_pipeline_design",
                "api_integration",
                "data_modeling",
                "performance_optimization",
            ],
            specializations=["data_engineering", "database", "api"],
            performance_requirements={
                "reasoning_depth": "advanced",
                "task_complexity": "medium",
                "creativity_required": False,
                "speed_priority": True,
            },
            model_preferences={
                "preferred_models": [ModelType.SONNET.value, ModelType.SONNET_4.value],
                "minimum_reasoning_tier": "advanced",
                "context_requirements": "medium",
            },
            priority=45,
        )

        self._agents["version_control"] = SystemAgentConfig(
            agent_type="version_control",
            agent_name="Version Control Agent",
            description="Git operations, branch management, and version control",
            default_model=ModelType.SONNET.value,
            capabilities=[
                "git_operations",
                "branch_management",
                "version_tagging",
                "merge_management",
                "repository_administration",
            ],
            specializations=["version_control", "git", "branching"],
            performance_requirements={
                "reasoning_depth": "standard",
                "task_complexity": "medium",
                "creativity_required": False,
                "speed_priority": True,
            },
            model_preferences={
                "preferred_models": [ModelType.SONNET.value],
                "minimum_reasoning_tier": "advanced",
                "context_requirements": "medium",
            },
            priority=55,
        )

        # Apply environment-based model defaults
        self._apply_environment_defaults()

        logger.info(
            f"Initialized {len(self._agents)} system agents with model assignments"
        )

    def _apply_environment_defaults(self) -> None:
        """Apply environment-based default model assignments."""
        for agent_type, agent_config in self._agents.items():
            default_model = get_default_model_for_agent_type(agent_type)
            if default_model != agent_config.default_model:
                logger.debug(
                    f"Updated {agent_type} default model: {agent_config.default_model} -> {default_model}"
                )
                agent_config.default_model = default_model

    def get_agent_config(self, agent_type: str) -> Optional[SystemAgentConfig]:
        """Get configuration for a specific agent type."""
        return self._agents.get(agent_type)

    def get_all_agents(self) -> Dict[str, SystemAgentConfig]:
        """Get all agent configurations."""
        return self._agents.copy()

    def get_agents_by_model(self, model_id: str) -> List[SystemAgentConfig]:
        """Get all agents configured to use a specific model."""
        return [
            agent
            for agent in self._agents.values()
            if agent.get_effective_model() == model_id
        ]

    def get_agents_by_specialization(
        self, specialization: str
    ) -> List[SystemAgentConfig]:
        """Get agents with a specific specialization."""
        return [
            agent
            for agent in self._agents.values()
            if specialization in agent.specializations
        ]

    def get_model_distribution(self) -> Dict[str, int]:
        """Get distribution of models across agents."""
        distribution = {}
        for agent in self._agents.values():
            if agent.enabled:
                model = agent.get_effective_model()
                distribution[model] = distribution.get(model, 0) + 1
        return distribution

    def validate_agent_model_assignments(self) -> Dict[str, Any]:
        """
        Validate all agent model assignments.

        Returns:
            Validation results with issues and recommendations
        """
        validation = {
            "valid": True,
            "issues": [],
            "warnings": [],
            "recommendations": [],
            "agent_validations": {},
        }

        for agent_type, agent_config in self._agents.items():
            if not agent_config.enabled:
                continue

            effective_model = agent_config.get_effective_model()

            # Validate with ModelSelector
            model_validation = self.model_selector.validate_model_selection(
                agent_type, effective_model
            )

            validation["agent_validations"][agent_type] = model_validation

            if not model_validation["valid"]:
                validation["valid"] = False
                validation["issues"].append(
                    {
                        "agent_type": agent_type,
                        "model": effective_model,
                        "error": model_validation.get(
                            "error", "Invalid model assignment"
                        ),
                    }
                )

            # Check warnings
            if model_validation.get("warnings"):
                validation["warnings"].extend(
                    [
                        {
                            "agent_type": agent_type,
                            "model": effective_model,
                            "warning": warning,
                        }
                        for warning in model_validation["warnings"]
                    ]
                )

            # Check suggestions
            if model_validation.get("suggestions"):
                validation["recommendations"].extend(
                    [
                        {
                            "agent_type": agent_type,
                            "model": effective_model,
                            "suggestion": suggestion,
                        }
                        for suggestion in model_validation["suggestions"]
                    ]
                )

        return validation

    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive configuration summary.

        Returns:
            Summary of agent configurations and model assignments
        """
        enabled_agents = [agent for agent in self._agents.values() if agent.enabled]

        # Model distribution
        model_distribution = self.get_model_distribution()

        # Environment overrides
        env_overrides = {}
        for agent_type, agent_config in self._agents.items():
            env_model = get_model_for_agent_from_env(agent_type)
            if env_model and env_model != agent_config.default_model:
                env_overrides[agent_type] = {
                    "default": agent_config.default_model,
                    "override": env_model,
                }

        # Agent priorities
        agents_by_priority = sorted(enabled_agents, key=lambda a: a.priority)

        # Capability analysis
        all_capabilities = set()
        all_specializations = set()
        for agent in enabled_agents:
            all_capabilities.update(agent.capabilities)
            all_specializations.update(agent.specializations)

        return {
            "total_agents": len(self._agents),
            "enabled_agents": len(enabled_agents),
            "model_distribution": model_distribution,
            "environment_overrides": env_overrides,
            "agent_priorities": [
                {
                    "type": agent.agent_type,
                    "name": agent.agent_name,
                    "priority": agent.priority,
                }
                for agent in agents_by_priority
            ],
            "capabilities_coverage": {
                "total_capabilities": len(all_capabilities),
                "total_specializations": len(all_specializations),
                "unique_capabilities": sorted(all_capabilities),
                "unique_specializations": sorted(all_specializations),
            },
            "configuration_health": self.validate_agent_model_assignments(),
        }

    def update_agent_model(self, agent_type: str, model_id: str) -> bool:
        """
        Update model assignment for an agent.

        Args:
            agent_type: Type of agent
            model_id: New model ID

        Returns:
            True if update successful, False otherwise
        """
        if agent_type not in self._agents:
            logger.error(f"Agent type not found: {agent_type}")
            return False

        # Validate model
        validation = self.model_selector.validate_model_selection(agent_type, model_id)
        if not validation["valid"]:
            logger.error(
                f"Invalid model assignment for {agent_type}: {validation.get('error')}"
            )
            return False

        # Update configuration
        self._agents[agent_type].default_model = model_id
        logger.info(f"Updated {agent_type} model assignment to {model_id}")

        return True

    def get_agent_model_recommendation(
        self, agent_type: str, task_description: str = ""
    ) -> Dict[str, Any]:
        """
        Get model recommendation for an agent and task.

        Args:
            agent_type: Type of agent
            task_description: Description of the task

        Returns:
            Model recommendation with analysis
        """
        agent_config = self.get_agent_config(agent_type)
        if not agent_config:
            return {"error": f"Agent type not found: {agent_type}"}

        # Use ModelSelector for recommendation
        recommendation = self.model_selector.get_model_recommendation(
            agent_type, task_description, agent_config.performance_requirements
        )

        # Add agent-specific context
        recommendation["agent_config"] = {
            "current_model": agent_config.get_effective_model(),
            "default_model": agent_config.default_model,
            "capabilities": agent_config.capabilities,
            "specializations": agent_config.specializations,
            "performance_requirements": agent_config.performance_requirements,
            "model_preferences": agent_config.model_preferences,
        }

        return recommendation


# Helper functions for easy integration
def get_system_agent_config() -> SystemAgentConfigManager:
    """Get system agent configuration manager instance."""
    return SystemAgentConfigManager()


def get_agent_model_assignment(agent_type: str) -> Optional[str]:
    """Get model assignment for a system agent."""
    manager = get_system_agent_config()
    agent_config = manager.get_agent_config(agent_type)
    return agent_config.get_effective_model() if agent_config else None


def validate_system_agent_models() -> Dict[str, Any]:
    """Validate all system agent model assignments."""
    manager = get_system_agent_config()
    return manager.validate_agent_model_assignments()


if __name__ == "__main__":
    # Test the system agent configuration
    print("System Agent Configuration Test")
    print("=" * 50)

    manager = SystemAgentConfigManager()

    # Show all agents
    agents = manager.get_all_agents()
    print(f"Total System Agents: {len(agents)}")

    # Show model distribution
    distribution = manager.get_model_distribution()
    print("\nModel Distribution:")
    for model_id, count in distribution.items():
        print(f"  {model_id}: {count} agents")

    # Show agents by model
    print("\nAgents by Model:")
    for model_id in distribution:
        agents_with_model = manager.get_agents_by_model(model_id)
        print(f"  {model_id}:")
        for agent in agents_with_model:
            print(f"    - {agent.agent_name} ({agent.agent_type})")

    # Validation
    validation = manager.validate_agent_model_assignments()
    print("\nValidation Results:")
    print(f"  Valid: {validation['valid']}")
    print(f"  Issues: {len(validation['issues'])}")
    print(f"  Warnings: {len(validation['warnings'])}")
    print(f"  Recommendations: {len(validation['recommendations'])}")

    # Configuration summary
    summary = manager.get_configuration_summary()
    print("\nConfiguration Summary:")
    print(f"  Enabled Agents: {summary['enabled_agents']}")
    print(f"  Environment Overrides: {len(summary['environment_overrides'])}")
    print(
        f"  Total Capabilities: {summary['capabilities_coverage']['total_capabilities']}"
    )
    print(
        f"  Total Specializations: {summary['capabilities_coverage']['total_specializations']}"
    )
