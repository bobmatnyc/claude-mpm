"""
Agent Management Interfaces for Claude MPM Framework
===================================================

WHY: This module contains all interfaces related to agent management, deployment,
capabilities, and discovery. These interfaces are grouped together because they
all deal with agent lifecycle and operations.

DESIGN DECISION: Agent-related interfaces are separated from infrastructure
because they represent domain-specific functionality rather than foundational
framework services.

EXTRACTED FROM: services/core/interfaces.py (lines 198-875)
- Agent registry and metadata
- Agent deployment and capabilities
- Agent system instructions and subprocess management
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..models.agent_config import (
    AgentCapabilities,
    AgentRecommendation,
    ConfigurationPreview,
    ConfigurationResult,
    ValidationResult,
)
from ..models.toolchain import ToolchainAnalysis


# Agent registry interface
@dataclass
class AgentMetadata:
    """Enhanced agent metadata with specialization and model configuration support"""

    name: str
    type: str
    path: str
    tier: str
    description: Optional[str] = None
    version: Optional[str] = None
    capabilities: List[str] = None
    specializations: List[str] = None
    frameworks: List[str] = None
    domains: List[str] = None
    roles: List[str] = None
    is_hybrid: bool = False
    validation_score: float = 0.0
    last_modified: Optional[float] = None
    # Model configuration fields
    preferred_model: Optional[str] = None
    model_config: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.specializations is None:
            self.specializations = []
        if self.frameworks is None:
            self.frameworks = []
        if self.domains is None:
            self.domains = []
        if self.roles is None:
            self.roles = []
        if self.model_config is None:
            self.model_config = {}


class IAgentRegistry(ABC):
    """Interface for agent discovery and management"""

    @abstractmethod
    async def discover_agents(
        self, force_refresh: bool = False
    ) -> Dict[str, AgentMetadata]:
        """Discover all available agents"""

    @abstractmethod
    async def get_agent(self, agent_name: str) -> Optional[AgentMetadata]:
        """Get specific agent metadata"""

    @abstractmethod
    async def list_agents(
        self, agent_type: Optional[str] = None, tier: Optional[str] = None
    ) -> List[AgentMetadata]:
        """List agents with optional filtering"""

    @abstractmethod
    async def get_specialized_agents(self, agent_type: str) -> List[AgentMetadata]:
        """Get agents of a specific specialized type"""

    @abstractmethod
    async def refresh_agent_cache(self) -> None:
        """Refresh the agent metadata cache"""


# Agent deployment interface
class AgentDeploymentInterface(ABC):
    """Interface for agent deployment operations.

    WHY: Agent deployment needs to be decoupled from concrete implementations
    to enable different deployment strategies (local, remote, containerized).
    This interface ensures consistency across different deployment backends.

    DESIGN DECISION: Methods return deployment status/results to enable
    proper error handling and rollback operations when deployments fail.
    """

    @abstractmethod
    def deploy_agents(
        self, force: bool = False, include_all: bool = False
    ) -> Dict[str, Any]:
        """Deploy agents to target environment.

        Args:
            force: Force deployment even if agents already exist
            include_all: Include all agents, ignoring exclusion lists

        Returns:
            Dictionary with deployment results and status
        """

    @abstractmethod
    def validate_agent(self, agent_path: Path) -> Tuple[bool, List[str]]:
        """Validate agent configuration and structure.

        Args:
            agent_path: Path to agent configuration file

        Returns:
            Tuple of (is_valid, list_of_errors)
        """

    @abstractmethod
    def get_deployment_status(self, agent_name: str) -> Dict[str, Any]:
        """Get deployment status for a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Dictionary with deployment status information
        """


# Agent capabilities interface
class AgentCapabilitiesInterface(ABC):
    """Interface for agent capabilities discovery and generation.

    WHY: Agent capabilities need to be discovered from multiple sources
    (system, user, project) and formatted for Claude. This interface
    abstracts the discovery and formatting logic to enable different
    agent discovery strategies and capability formats.

    DESIGN DECISION: Returns formatted strings ready for Claude consumption
    to minimize processing overhead in the main execution path.
    """

    @abstractmethod
    def generate_agent_capabilities(self, agent_type: str = "general") -> str:
        """Generate formatted agent capabilities for Claude.

        Args:
            agent_type: Type of agent to generate capabilities for

        Returns:
            Formatted capabilities string for Claude consumption
        """


# System instructions interface
class SystemInstructionsInterface(ABC):
    """Interface for system instructions loading and processing.

    WHY: System instructions need to be loaded from multiple sources
    (project, framework) with template processing and metadata stripping.
    This interface abstracts the loading and processing logic to enable
    different instruction sources and processing strategies.

    DESIGN DECISION: Provides both raw and processed instruction methods
    to support different use cases and enable caching of processed results.
    """

    @abstractmethod
    def load_system_instructions(self, instruction_type: str = "default") -> str:
        """Load and process system instructions.

        Args:
            instruction_type: Type of instructions to load

        Returns:
            Processed system instructions string
        """

    @abstractmethod
    def get_available_instruction_types(self) -> List[str]:
        """Get list of available instruction types.

        Returns:
            List of available instruction type names
        """

    @abstractmethod
    def validate_instructions(self, instructions: str) -> Tuple[bool, List[str]]:
        """Validate system instructions format and content.

        Args:
            instructions: Instructions content to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """


# Subprocess launcher interface
class SubprocessLauncherInterface(ABC):
    """Interface for subprocess launching and PTY management.

    WHY: Subprocess launching involves complex PTY management, signal handling,
    and I/O coordination. This interface abstracts the subprocess launching
    logic to enable different launching strategies and improve testability.

    DESIGN DECISION: Provides both synchronous and asynchronous launch methods
    to support different execution contexts and performance requirements.
    """

    @abstractmethod
    def launch_subprocess(self, command: List[str], **kwargs) -> Dict[str, Any]:
        """Launch a subprocess with PTY support.

        Args:
            command: Command and arguments to execute
            **kwargs: Additional subprocess options

        Returns:
            Dictionary with subprocess information and handles
        """

    @abstractmethod
    async def launch_subprocess_async(
        self, command: List[str], **kwargs
    ) -> Dict[str, Any]:
        """Launch a subprocess asynchronously with PTY support.

        Args:
            command: Command and arguments to execute
            **kwargs: Additional subprocess options

        Returns:
            Dictionary with subprocess information and handles
        """

    @abstractmethod
    def terminate_subprocess(self, process_id: str) -> bool:
        """Terminate a running subprocess.

        Args:
            process_id: ID of the process to terminate

        Returns:
            True if termination successful
        """

    @abstractmethod
    def get_subprocess_status(self, process_id: str) -> Dict[str, Any]:
        """Get status of a running subprocess.

        Args:
            process_id: ID of the process

        Returns:
            Dictionary with process status information
        """


# Runner configuration interface
class RunnerConfigurationInterface(ABC):
    """Interface for runner configuration and initialization.

    WHY: ClaudeRunner initialization involves complex service registration,
    configuration loading, and logger setup. This interface abstracts the
    configuration logic to enable different configuration strategies and
    improve testability.

    DESIGN DECISION: Separates configuration loading from service registration
    to enable independent testing and different configuration sources.
    """

    @abstractmethod
    def initialize_runner(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize runner with configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Dictionary with initialization results
        """

    @abstractmethod
    def register_services(self, service_container) -> None:
        """Register services with the dependency injection container.

        Args:
            service_container: Service container for registration
        """

    @abstractmethod
    def load_configuration(self, config_path: Optional[Path] = None) -> Dict[str, Any]:
        """Load configuration from file or defaults.

        Args:
            config_path: Optional path to configuration file

        Returns:
            Loaded configuration dictionary
        """

    @abstractmethod
    def validate_configuration(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate configuration structure and values.

        Args:
            config: Configuration to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """

    @abstractmethod
    def setup_logging(self, config: Dict[str, Any]) -> None:
        """Setup logging configuration.

        Args:
            config: Logging configuration
        """


# Agent recommender interface
class IAgentRecommender(ABC):
    """Interface for agent recommendation operations.

    WHY: Automated agent recommendation is critical for the auto-configuration
    feature. This interface abstracts the recommendation logic to enable different
    scoring algorithms, rule-based systems, and ML-based approaches.

    DESIGN DECISION: Separates recommendation from configuration to enable
    independent testing and different recommendation strategies (rule-based,
    ML-based, hybrid). Returns structured recommendations with confidence scores.
    """

    @abstractmethod
    def recommend_agents(
        self,
        toolchain: ToolchainAnalysis,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> List[AgentRecommendation]:
        """Recommend agents based on toolchain analysis.

        Analyzes the toolchain and recommends agents that best match the
        project's technical requirements. Considers:
        - Language compatibility
        - Framework expertise
        - Deployment environment requirements
        - Optional user-defined constraints (max agents, required capabilities)

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

    @abstractmethod
    def get_agent_capabilities(self, agent_id: str) -> AgentCapabilities:
        """Get detailed capabilities for an agent.

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

    @abstractmethod
    def match_score(self, agent_id: str, toolchain: ToolchainAnalysis) -> float:
        """Calculate match score between agent and toolchain.

        Computes a numerical score (0.0 to 1.0) indicating how well an agent
        matches the project's toolchain. Higher scores indicate better matches.
        Considers:
        - Language compatibility
        - Framework experience
        - Deployment target alignment
        - Toolchain component coverage

        Args:
            agent_id: Unique identifier of the agent
            toolchain: Complete toolchain analysis

        Returns:
            float: Match score between 0.0 (no match) and 1.0 (perfect match)

        Raises:
            KeyError: If agent_id does not exist
        """


# Auto-configuration manager interface
class IAutoConfigManager(ABC):
    """Interface for automated configuration management.

    WHY: Auto-configuration orchestrates the entire process of analyzing,
    recommending, validating, and deploying agents. This interface abstracts
    the orchestration logic to enable different workflows and approval processes.

    DESIGN DECISION: Provides both preview and apply modes to enable user review
    before deployment. Includes validation to catch configuration issues early.
    Supports both interactive (confirmation required) and automated modes.
    """

    @abstractmethod
    async def auto_configure(
        self, project_path: Path, confirmation_required: bool = True
    ) -> ConfigurationResult:
        """Perform automated agent configuration.

        Complete end-to-end configuration workflow:
        1. Analyze project toolchain
        2. Generate agent recommendations
        3. Validate proposed configuration
        4. Request user confirmation (if required)
        5. Deploy approved agents
        6. Verify deployment success

        Args:
            project_path: Path to the project root directory
            confirmation_required: Whether to require user approval before deployment

        Returns:
            ConfigurationResult: Complete configuration results including
                deployed agents, validation results, and any errors

        Raises:
            FileNotFoundError: If project_path does not exist
            PermissionError: If unable to write to project directory
            ValidationError: If configuration validation fails critically
        """

    @abstractmethod
    def validate_configuration(
        self, recommendations: List[AgentRecommendation]
    ) -> ValidationResult:
        """Validate proposed configuration before deployment.

        Performs comprehensive validation of recommended agents:
        - Checks for conflicting agent capabilities
        - Verifies resource requirements are met
        - Validates agent compatibility with project
        - Identifies potential configuration issues

        Args:
            recommendations: List of agent recommendations to validate

        Returns:
            ValidationResult: Validation result with any warnings or errors

        Raises:
            ValueError: If recommendations list is empty or invalid
        """

    @abstractmethod
    def preview_configuration(self, project_path: Path) -> ConfigurationPreview:
        """Preview what would be configured without applying changes.

        Performs analysis and recommendation without making any changes:
        - Analyzes project toolchain
        - Generates recommendations
        - Validates configuration
        - Returns preview of what would be deployed

        Useful for testing and showing users what would happen before
        committing to changes.

        Args:
            project_path: Path to the project root directory

        Returns:
            ConfigurationPreview: Preview of configuration that would be applied

        Raises:
            FileNotFoundError: If project_path does not exist
        """
