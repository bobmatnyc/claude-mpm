"""
Strategy Pattern Framework for Service Consolidation
====================================================

This module implements the strategy pattern framework that enables pluggable behavior
in unified services. It provides base strategy classes and a plugin registry system
for dynamic strategy registration and selection.

Design Goals:
1. Enable runtime strategy selection based on context
2. Support plugin-based extensibility
3. Maintain strong typing and interface contracts
4. Allow graceful fallback to default strategies
5. Support both sync and async operations

Architecture:
- Base strategy classes define common operations
- Concrete strategies implement specific behaviors
- Registry system manages strategy discovery and selection
- Context objects carry strategy selection criteria
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type, TypeVar, Union

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)

# Type variables for generic strategies
T = TypeVar("T")
StrategyType = TypeVar("StrategyType", bound="BaseStrategy")


class StrategyPriority(Enum):
    """Priority levels for strategy selection."""

    CRITICAL = 100
    HIGH = 75
    NORMAL = 50
    LOW = 25
    FALLBACK = 0


@dataclass
class StrategyContext:
    """
    Context information for strategy selection.

    Attributes:
        target_type: Type of target being processed
        operation: Operation being performed
        parameters: Additional parameters for strategy selection
        constraints: Constraints that strategies must satisfy
        preferences: Preferred strategy characteristics
    """

    target_type: str
    operation: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyMetadata:
    """
    Metadata for registered strategies.

    Attributes:
        name: Strategy identifier
        description: Human-readable description
        supported_types: List of supported target types
        supported_operations: List of supported operations
        priority: Strategy priority for selection
        tags: Additional categorization tags
        version: Strategy version
    """

    name: str
    description: str = ""
    supported_types: List[str] = field(default_factory=list)
    supported_operations: List[str] = field(default_factory=list)
    priority: StrategyPriority = StrategyPriority.NORMAL
    tags: Set[str] = field(default_factory=set)
    version: str = "1.0.0"


class BaseStrategy(ABC):
    """
    Base class for all strategies providing common functionality.

    Subclasses should implement the abstract methods for specific behaviors
    while inheriting common functionality like validation and logging.
    """

    def __init__(self, metadata: Optional[StrategyMetadata] = None):
        """
        Initialize base strategy.

        Args:
            metadata: Strategy metadata
        """
        self.metadata = metadata or StrategyMetadata(name=self.__class__.__name__)
        self._logger = get_logger(f"{__name__}.{self.metadata.name}")

    @abstractmethod
    def can_handle(self, context: StrategyContext) -> bool:
        """
        Check if strategy can handle the given context.

        Args:
            context: Strategy context

        Returns:
            bool: True if strategy can handle context
        """

    @abstractmethod
    def validate_input(self, input_data: Any) -> List[str]:
        """
        Validate input data for strategy.

        Args:
            input_data: Input to validate

        Returns:
            List[str]: List of validation errors (empty if valid)
        """

    def pre_execute(self, input_data: Any) -> Any:
        """
        Pre-processing hook before execution.

        Args:
            input_data: Input data

        Returns:
            Any: Processed input data
        """
        return input_data

    def post_execute(self, result: Any) -> Any:
        """
        Post-processing hook after execution.

        Args:
            result: Execution result

        Returns:
            Any: Processed result
        """
        return result


class DeploymentStrategy(BaseStrategy):
    """
    Base strategy for deployment operations.

    Concrete deployment strategies should extend this class and implement
    the deploy method for specific deployment types (agent, config, resource, etc.).
    """

    @abstractmethod
    def deploy(
        self,
        source: Union[str, Path],
        target: Union[str, Path],
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute deployment strategy.

        Args:
            source: Deployment source
            target: Deployment target
            config: Deployment configuration

        Returns:
            Dict[str, Any]: Deployment result
        """

    @abstractmethod
    def prepare_rollback(self, deployment_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare rollback information for deployment.

        Args:
            deployment_info: Current deployment information

        Returns:
            Dict[str, Any]: Rollback information
        """

    @abstractmethod
    def cleanup(self, target: Union[str, Path]) -> bool:
        """
        Clean up deployment artifacts.

        Args:
            target: Deployment target to clean

        Returns:
            bool: True if cleanup successful
        """


class AnalyzerStrategy(BaseStrategy):
    """
    Base strategy for analysis operations.

    Concrete analyzer strategies should extend this class and implement
    the analyze method for specific analysis types (code, complexity, dependency, etc.).
    """

    @abstractmethod
    def analyze(
        self, target: Any, options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute analysis strategy.

        Args:
            target: Analysis target
            options: Analysis options

        Returns:
            Dict[str, Any]: Analysis results
        """

    @abstractmethod
    def extract_metrics(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metrics from analysis results.

        Args:
            analysis_result: Raw analysis results

        Returns:
            Dict[str, Any]: Extracted metrics
        """

    @abstractmethod
    def generate_report(
        self, analysis_result: Dict[str, Any], format: str = "json"
    ) -> Union[str, Dict[str, Any]]:
        """
        Generate report from analysis results.

        Args:
            analysis_result: Analysis results
            format: Report format (json, markdown, html)

        Returns:
            Union[str, Dict[str, Any]]: Generated report
        """


class ConfigStrategy(BaseStrategy):
    """
    Base strategy for configuration operations.

    Concrete config strategies should extend this class and implement
    the process method for specific configuration types (project, agent, environment, etc.).
    """

    @abstractmethod
    def load(self, source: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Load configuration using strategy.

        Args:
            source: Configuration source

        Returns:
            Dict[str, Any]: Loaded configuration
        """

    @abstractmethod
    def validate(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate configuration using strategy schema.

        Args:
            config: Configuration to validate

        Returns:
            List[str]: Validation errors (empty if valid)
        """

    @abstractmethod
    def transform(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform configuration to required format.

        Args:
            config: Configuration to transform

        Returns:
            Dict[str, Any]: Transformed configuration
        """

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        Get configuration schema for this strategy.

        Returns:
            Dict[str, Any]: Configuration schema
        """


class StrategyRegistry:
    """
    Registry for managing strategy registration and selection.

    The registry provides a centralized location for registering strategies
    and selecting appropriate strategies based on context.
    """

    def __init__(self):
        """Initialize strategy registry."""
        self._strategies: Dict[Type[BaseStrategy], List[BaseStrategy]] = {}
        self._strategy_metadata: Dict[str, StrategyMetadata] = {}
        self._logger = get_logger(f"{__name__}.StrategyRegistry")

    def register(
        self,
        strategy_class: Type[StrategyType],
        strategy: StrategyType,
        override: bool = False,
    ) -> None:
        """
        Register a strategy implementation.

        Args:
            strategy_class: Base strategy class type
            strategy: Strategy instance
            override: Whether to override existing strategy with same name

        Raises:
            ValueError: If strategy already registered and override is False
        """
        if strategy_class not in self._strategies:
            self._strategies[strategy_class] = []

        strategy_name = strategy.metadata.name

        if strategy_name in self._strategy_metadata and not override:
            raise ValueError(
                f"Strategy '{strategy_name}' already registered. "
                "Set override=True to replace."
            )

        # Remove old strategy if overriding
        if override and strategy_name in self._strategy_metadata:
            self._strategies[strategy_class] = [
                s
                for s in self._strategies[strategy_class]
                if s.metadata.name != strategy_name
            ]

        self._strategies[strategy_class].append(strategy)
        self._strategy_metadata[strategy_name] = strategy.metadata

        self._logger.debug(
            f"Registered strategy '{strategy_name}' for {strategy_class.__name__}"
        )

    def unregister(self, strategy_name: str) -> bool:
        """
        Unregister a strategy by name.

        Args:
            strategy_name: Name of strategy to unregister

        Returns:
            bool: True if strategy was unregistered
        """
        if strategy_name not in self._strategy_metadata:
            return False

        # Remove from all strategy lists
        for strategy_class in self._strategies:
            self._strategies[strategy_class] = [
                s
                for s in self._strategies[strategy_class]
                if s.metadata.name != strategy_name
            ]

        del self._strategy_metadata[strategy_name]
        self._logger.debug(f"Unregistered strategy '{strategy_name}'")
        return True

    def select_strategy(
        self,
        strategy_class: Type[StrategyType],
        context: StrategyContext,
    ) -> Optional[StrategyType]:
        """
        Select best strategy for given context.

        Args:
            strategy_class: Base strategy class type
            context: Strategy selection context

        Returns:
            Optional[StrategyType]: Selected strategy or None
        """
        if strategy_class not in self._strategies:
            self._logger.warning(
                f"No strategies registered for {strategy_class.__name__}"
            )
            return None

        candidates = []

        for strategy in self._strategies[strategy_class]:
            if strategy.can_handle(context):
                candidates.append(strategy)

        if not candidates:
            self._logger.warning(f"No suitable strategy found for context: {context}")
            return None

        # Sort by priority (highest first)
        candidates.sort(key=lambda s: s.metadata.priority.value, reverse=True)

        selected = candidates[0]
        self._logger.debug(
            f"Selected strategy '{selected.metadata.name}' "
            f"for {strategy_class.__name__}"
        )

        return selected

    def get_strategy(
        self,
        strategy_class: Type[StrategyType],
        name: str,
    ) -> Optional[StrategyType]:
        """
        Get specific strategy by name.

        Args:
            strategy_class: Base strategy class type
            name: Strategy name

        Returns:
            Optional[StrategyType]: Strategy instance or None
        """
        if strategy_class not in self._strategies:
            return None

        for strategy in self._strategies[strategy_class]:
            if strategy.metadata.name == name:
                return strategy

        return None

    def list_strategies(
        self, strategy_class: Optional[Type[BaseStrategy]] = None
    ) -> List[StrategyMetadata]:
        """
        List registered strategies.

        Args:
            strategy_class: Optional filter by strategy class

        Returns:
            List[StrategyMetadata]: List of strategy metadata
        """
        if strategy_class:
            if strategy_class not in self._strategies:
                return []
            return [s.metadata for s in self._strategies[strategy_class]]

        return list(self._strategy_metadata.values())

    def clear(self) -> None:
        """Clear all registered strategies."""
        self._strategies.clear()
        self._strategy_metadata.clear()
        self._logger.debug("Cleared all registered strategies")


# Global strategy registry instance
_global_registry = StrategyRegistry()


def get_strategy_registry() -> StrategyRegistry:
    """
    Get the global strategy registry instance.

    Returns:
        StrategyRegistry: Global registry instance
    """
    return _global_registry


def register_strategy(
    strategy_class: Type[BaseStrategy],
    strategy: BaseStrategy,
    override: bool = False,
) -> None:
    """
    Register a strategy in the global registry.

    Args:
        strategy_class: Base strategy class type
        strategy: Strategy instance
        override: Whether to override existing strategy
    """
    _global_registry.register(strategy_class, strategy, override)


def select_strategy(
    strategy_class: Type[BaseStrategy],
    context: StrategyContext,
) -> Optional[BaseStrategy]:
    """
    Select best strategy from global registry.

    Args:
        strategy_class: Base strategy class type
        context: Strategy selection context

    Returns:
        Optional[BaseStrategy]: Selected strategy or None
    """
    return _global_registry.select_strategy(strategy_class, context)
