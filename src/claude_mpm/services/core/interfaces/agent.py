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
