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
from typing import Any

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
    description: str | None = None
    version: str | None = None
    capabilities: list[str] = None
    specializations: list[str] = None
    frameworks: list[str] = None
    domains: list[str] = None
    roles: list[str] = None
    is_hybrid: bool = False
    validation_score: float = 0.0
    last_modified: float | None = None
    # Model configuration fields
    preferred_model: str | None = None
    model_config: dict[str, Any] | None = None

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
    ) -> dict[str, AgentMetadata]:
        """Discover all available agents"""

    @abstractmethod
    async def get_agent(self, agent_name: str) -> AgentMetadata | None:
        """Get specific agent metadata"""

    @abstractmethod
    async def list_agents(
        self, agent_type: str | None = None, tier: str | None = None
    ) -> list[AgentMetadata]:
        """List agents with optional filtering"""

    @abstractmethod
    async def get_specialized_agents(self, agent_type: str) -> list[AgentMetadata]:
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
    ) -> dict[str, Any]:
        """Deploy agents to target environment.

        Args:
            force: Force deployment even if agents already exist
            include_all: Include all agents, ignoring exclusion lists

        Returns:
            Dictionary with deployment results and status
        """

    @abstractmethod
    def validate_agent(self, agent_path: Path) -> tuple[bool, list[str]]:
        """Validate agent configuration and structure.

        Args:
            agent_path: Path to agent configuration file

        Returns:
            Tuple of (is_valid, list_of_errors)
        """

    @abstractmethod
    def get_deployment_status(self, agent_name: str) -> dict[str, Any]:
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
    def get_available_instruction_types(self) -> list[str]:
        """Get list of available instruction types.

        Returns:
            List of available instruction type names
        """

    @abstractmethod
    def validate_instructions(self, instructions: str) -> tuple[bool, list[str]]:
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
    def launch_subprocess(self, command: list[str], **kwargs) -> dict[str, Any]:
        """Launch a subprocess with PTY support.

        Args:
            command: Command and arguments to execute
            **kwargs: Additional subprocess options

        Returns:
            Dictionary with subprocess information and handles
        """

    @abstractmethod
    async def launch_subprocess_async(
        self, command: list[str], **kwargs
    ) -> dict[str, Any]:
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
    def get_subprocess_status(self, process_id: str) -> dict[str, Any]:
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
    def initialize_runner(self, config: dict[str, Any]) -> dict[str, Any]:
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
    def load_configuration(self, config_path: Path | None = None) -> dict[str, Any]:
        """Load configuration from file or defaults.

        Args:
            config_path: Optional path to configuration file

        Returns:
            Loaded configuration dictionary
        """

    @abstractmethod
    def validate_configuration(self, config: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate configuration structure and values.

        Args:
            config: Configuration to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """

    @abstractmethod
    def setup_logging(self, config: dict[str, Any]) -> None:
        """Setup logging configuration.

        Args:
            config: Logging configuration
        """

    @abstractmethod
    def initialize_configuration(self, **kwargs: Any) -> dict[str, Any]:
        """Initialize configuration from keyword arguments.

        Args:
            **kwargs: Configuration parameters

        Returns:
            Dictionary containing initialized configuration data
        """

    @abstractmethod
    def initialize_project_logger(self, log_level: str) -> Any:
        """Initialize project logger for session logging.

        Args:
            log_level: Logging level

        Returns:
            Initialized project logger or None if disabled/failed
        """

    @abstractmethod
    def initialize_response_logger(
        self, config: Any, project_logger: Any = None
    ) -> Any:
        """Initialize response logger if enabled in configuration.

        Args:
            config: Configuration object
            project_logger: Optional project logger for system events

        Returns:
            Initialized response logger or None if disabled/failed
        """

    @abstractmethod
    def get_user_working_directory(self) -> Path | None:
        """Get user working directory from environment.

        Returns:
            Path to user working directory or None if not set
        """

    @abstractmethod
    def register_core_services(
        self, container: Any, user_working_dir: Path | None = None
    ) -> None:
        """Register core services in the DI container.

        Args:
            container: DI container instance
            user_working_dir: Optional user working directory
        """

    @abstractmethod
    def register_ticket_manager(
        self, container: Any, enable_tickets: bool
    ) -> tuple[Any, bool]:
        """Register ticket manager service if enabled.

        Args:
            container: DI container instance
            enable_tickets: Whether to enable ticket management

        Returns:
            Tuple of (ticket_manager, actual_enable_tickets_flag)
        """

    @abstractmethod
    def register_hook_service(self, container: Any, config: Any) -> Any:
        """Register hook service in the DI container.

        Args:
            container: DI container instance
            config: Configuration object

        Returns:
            Initialized hook service or None if failed
        """

    @abstractmethod
    def register_agent_capabilities_service(self, container: Any) -> Any:
        """Register agent capabilities service in the DI container.

        Args:
            container: DI container instance

        Returns:
            Initialized agent capabilities service or None if failed
        """

    @abstractmethod
    def register_system_instructions_service(
        self, container: Any, agent_capabilities_service: Any
    ) -> Any:
        """Register system instructions service in the DI container.

        Args:
            container: DI container instance
            agent_capabilities_service: Agent capabilities service dependency

        Returns:
            Initialized system instructions service or None if failed
        """

    @abstractmethod
    def register_subprocess_launcher_service(
        self, container: Any, project_logger: Any, websocket_server: Any
    ) -> Any:
        """Register subprocess launcher service in the DI container.

        Args:
            container: DI container instance
            project_logger: Project logger dependency
            websocket_server: WebSocket server dependency

        Returns:
            Initialized subprocess launcher service or None if failed
        """

    @abstractmethod
    def register_version_service(self, container: Any) -> Any:
        """Register version service in the DI container.

        Args:
            container: DI container instance

        Returns:
            Initialized version service or None if failed
        """

    @abstractmethod
    def register_command_handler_service(
        self, container: Any, project_logger: Any
    ) -> Any:
        """Register command handler service in the DI container.

        Args:
            container: DI container instance
            project_logger: Project logger dependency

        Returns:
            Initialized command handler service or None if failed
        """

    @abstractmethod
    def register_memory_hook_service(self, container: Any, hook_service: Any) -> Any:
        """Register memory hook service in the DI container.

        Args:
            container: DI container instance
            hook_service: Hook service dependency

        Returns:
            Initialized memory hook service or None if failed
        """

    @abstractmethod
    def register_session_management_service(self, container: Any, runner: Any) -> Any:
        """Register session management service in the DI container.

        Args:
            container: DI container instance
            runner: ClaudeRunner instance

        Returns:
            Initialized session management service or None if failed
        """

    @abstractmethod
    def register_utility_service(self, container: Any) -> Any:
        """Register utility service in the DI container.

        Args:
            container: DI container instance

        Returns:
            Initialized utility service or None if failed
        """

    @abstractmethod
    def create_session_log_file(
        self, project_logger: Any, log_level: str, config_data: dict[str, Any]
    ) -> Path | None:
        """Create session log file and log session start event.

        Args:
            project_logger: Project logger instance
            log_level: Logging level
            config_data: Configuration data for logging

        Returns:
            Path to session log file or None if failed
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
        constraints: dict[str, Any] | None = None,
    ) -> list[AgentRecommendation]:
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
        self, recommendations: list[AgentRecommendation]
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
