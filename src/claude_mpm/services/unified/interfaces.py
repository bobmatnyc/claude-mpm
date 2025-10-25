"""
Base Service Interfaces for Unified Services
============================================

This module provides the foundational interfaces for the Phase 2 service consolidation
effort. These interfaces establish common contracts for consolidated service categories,
enabling the reduction of 314 service files to approximately 180 more maintainable services.

Design Principles:
1. Common operations are standardized across service types
2. Strategy pattern support for pluggable implementations
3. Backward compatibility with existing service interfaces
4. Rich metadata for service discovery and management
5. Support for async operations where appropriate

Service Categories:
- Deployment Services: Agent deployment, configuration deployment, etc.
- Analyzer Services: Code analysis, complexity analysis, dependency analysis, etc.
- Configuration Services: Project config, agent config, environment config, etc.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, TypeVar, Union

from claude_mpm.core.enums import ValidationSeverity

# Type variables for generic interfaces
T = TypeVar("T")
ConfigType = TypeVar("ConfigType", bound=Dict[str, Any])


class ServiceCapability(Enum):
    """Enumeration of service capabilities for feature discovery."""

    ASYNC_OPERATIONS = "async_operations"
    BATCH_PROCESSING = "batch_processing"
    CACHING = "caching"
    VALIDATION = "validation"
    MONITORING = "monitoring"
    HEALTH_CHECK = "health_check"
    HOT_RELOAD = "hot_reload"
    VERSIONING = "versioning"
    ROLLBACK = "rollback"
    METRICS = "metrics"


@dataclass
class ServiceMetadata:
    """
    Metadata for unified services providing rich service information.

    Attributes:
        name: Service identifier name
        version: Service implementation version
        capabilities: Set of supported capabilities
        dependencies: List of required service dependencies
        description: Human-readable service description
        tags: Additional categorization tags
        deprecated_services: List of legacy services this replaces
    """

    name: str
    version: str
    capabilities: Set[ServiceCapability] = field(default_factory=set)
    dependencies: List[str] = field(default_factory=list)
    description: str = ""
    tags: Set[str] = field(default_factory=set)
    deprecated_services: List[str] = field(default_factory=list)


@dataclass
class DeploymentResult:
    """Result of a deployment operation."""

    success: bool
    deployed_path: Optional[Path] = None
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    rollback_info: Optional[Dict[str, Any]] = None


@dataclass
class AnalysisResult:
    """Result of an analysis operation."""

    success: bool
    findings: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    severity: str = ValidationSeverity.INFO
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ConfigurationResult:
    """Result of a configuration operation."""

    success: bool
    config: Dict[str, Any] = field(default_factory=dict)
    validation_errors: List[str] = field(default_factory=list)
    applied_defaults: Dict[str, Any] = field(default_factory=dict)
    source: str = ""  # file, environment, default, etc.


class IDeploymentService(ABC):
    """
    Common interface for all deployment services.

    This interface consolidates deployment operations across various service types
    including agent deployment, configuration deployment, and resource deployment.
    Implementations should use the strategy pattern for specific deployment types.
    """

    @abstractmethod
    def get_metadata(self) -> ServiceMetadata:
        """
        Get service metadata including capabilities and dependencies.

        Returns:
            ServiceMetadata: Complete service metadata
        """

    @abstractmethod
    def validate_deployment(
        self, target: Union[str, Path], config: Dict[str, Any]
    ) -> List[str]:
        """
        Validate deployment configuration before execution.

        Args:
            target: Deployment target (path, identifier, etc.)
            config: Deployment configuration

        Returns:
            List[str]: List of validation errors (empty if valid)
        """

    @abstractmethod
    def deploy(
        self,
        source: Union[str, Path],
        target: Union[str, Path],
        config: Optional[Dict[str, Any]] = None,
        force: bool = False,
    ) -> DeploymentResult:
        """
        Execute deployment operation.

        Args:
            source: Source to deploy from
            target: Target to deploy to
            config: Optional deployment configuration
            force: Force deployment even if target exists

        Returns:
            DeploymentResult: Result of the deployment operation
        """

    @abstractmethod
    def rollback(
        self, deployment_id: str, rollback_info: Dict[str, Any]
    ) -> DeploymentResult:
        """
        Rollback a previous deployment.

        Args:
            deployment_id: Identifier of deployment to rollback
            rollback_info: Information needed for rollback

        Returns:
            DeploymentResult: Result of the rollback operation
        """

    @abstractmethod
    def list_deployments(
        self, target: Optional[Union[str, Path]] = None
    ) -> List[Dict[str, Any]]:
        """
        List existing deployments.

        Args:
            target: Optional target to filter deployments

        Returns:
            List[Dict[str, Any]]: List of deployment information
        """

    @abstractmethod
    def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """
        Get status of a specific deployment.

        Args:
            deployment_id: Identifier of deployment

        Returns:
            Dict[str, Any]: Deployment status information
        """


class IAnalyzerService(ABC):
    """
    Common interface for all analyzer services.

    This interface consolidates analysis operations across various service types
    including code analysis, complexity analysis, dependency analysis, and performance analysis.
    Implementations should use the strategy pattern for specific analysis types.
    """

    @abstractmethod
    def get_metadata(self) -> ServiceMetadata:
        """
        Get service metadata including capabilities and dependencies.

        Returns:
            ServiceMetadata: Complete service metadata
        """

    @abstractmethod
    def analyze(
        self,
        target: Union[str, Path, Any],
        options: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        """
        Perform analysis on the target.

        Args:
            target: Target to analyze (file, directory, object, etc.)
            options: Analysis options and parameters

        Returns:
            AnalysisResult: Result of the analysis
        """

    @abstractmethod
    def batch_analyze(
        self,
        targets: List[Union[str, Path, Any]],
        options: Optional[Dict[str, Any]] = None,
    ) -> List[AnalysisResult]:
        """
        Perform batch analysis on multiple targets.

        Args:
            targets: List of targets to analyze
            options: Analysis options and parameters

        Returns:
            List[AnalysisResult]: Results for each target
        """

    @abstractmethod
    def get_metrics(self, target: Union[str, Path, Any]) -> Dict[str, Any]:
        """
        Get analysis metrics for a target.

        Args:
            target: Target to get metrics for

        Returns:
            Dict[str, Any]: Analysis metrics
        """

    @abstractmethod
    def compare(
        self,
        target1: Union[str, Path, Any],
        target2: Union[str, Path, Any],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Compare two targets and analyze differences.

        Args:
            target1: First target
            target2: Second target
            options: Comparison options

        Returns:
            Dict[str, Any]: Comparison results
        """

    @abstractmethod
    def get_recommendations(
        self, analysis_result: AnalysisResult
    ) -> List[Dict[str, Any]]:
        """
        Get recommendations based on analysis results.

        Args:
            analysis_result: Previous analysis result

        Returns:
            List[Dict[str, Any]]: List of recommendations
        """


class IConfigurationService(ABC):
    """
    Common interface for configuration services.

    This interface consolidates configuration management operations across various
    service types including project configuration, agent configuration, and environment configuration.
    Implementations should use the strategy pattern for specific configuration types.
    """

    @abstractmethod
    def get_metadata(self) -> ServiceMetadata:
        """
        Get service metadata including capabilities and dependencies.

        Returns:
            ServiceMetadata: Complete service metadata
        """

    @abstractmethod
    def load_config(
        self, source: Union[str, Path, Dict[str, Any]]
    ) -> ConfigurationResult:
        """
        Load configuration from source.

        Args:
            source: Configuration source (file path, dict, etc.)

        Returns:
            ConfigurationResult: Loaded configuration result
        """

    @abstractmethod
    def save_config(
        self, config: Dict[str, Any], target: Union[str, Path]
    ) -> ConfigurationResult:
        """
        Save configuration to target.

        Args:
            config: Configuration to save
            target: Target location

        Returns:
            ConfigurationResult: Save operation result
        """

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate configuration against schema.

        Args:
            config: Configuration to validate

        Returns:
            List[str]: List of validation errors (empty if valid)
        """

    @abstractmethod
    def merge_configs(
        self, *configs: Dict[str, Any], strategy: str = "deep"
    ) -> Dict[str, Any]:
        """
        Merge multiple configurations.

        Args:
            *configs: Configurations to merge
            strategy: Merge strategy ('deep', 'shallow', 'override')

        Returns:
            Dict[str, Any]: Merged configuration
        """

    @abstractmethod
    def get_config_value(
        self, key: str, default: Any = None, config: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Get configuration value by key with optional default.

        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
            config: Optional config dict (uses loaded config if None)

        Returns:
            Any: Configuration value
        """

    @abstractmethod
    def set_config_value(
        self, key: str, value: Any, config: Optional[Dict[str, Any]] = None
    ) -> ConfigurationResult:
        """
        Set configuration value by key.

        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
            config: Optional config dict to modify

        Returns:
            ConfigurationResult: Result of set operation
        """

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        Get configuration schema definition.

        Returns:
            Dict[str, Any]: Configuration schema
        """

    @abstractmethod
    def apply_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply default values to configuration.

        Args:
            config: Configuration to apply defaults to

        Returns:
            Dict[str, Any]: Configuration with defaults applied
        """


class IUnifiedService(ABC):
    """
    Base interface for all unified services providing common lifecycle operations.

    This interface ensures all unified services support basic lifecycle management,
    health checking, and service discovery capabilities.
    """

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the service and its dependencies.

        Returns:
            bool: True if initialization successful
        """

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Gracefully shutdown the service.
        """

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the service.

        Returns:
            Dict[str, Any]: Health status information
        """

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get service metrics.

        Returns:
            Dict[str, Any]: Service metrics
        """

    @abstractmethod
    def reset(self) -> None:
        """
        Reset service to initial state.
        """
