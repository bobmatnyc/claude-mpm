"""Strategy selector for choosing the appropriate deployment strategy."""

from typing import List, Optional

from claude_mpm.core.logger import get_logger

from .base_strategy import BaseDeploymentStrategy, DeploymentContext
from .project_strategy import ProjectAgentDeploymentStrategy
from .system_strategy import SystemAgentDeploymentStrategy
from .user_strategy import UserAgentDeploymentStrategy


class DeploymentStrategySelector:
    """Selects the appropriate deployment strategy based on context.

    This class manages all available deployment strategies and selects
    the most appropriate one based on the deployment context.
    """

    def __init__(self):
        """Initialize the strategy selector with all available strategies."""
        self.logger = get_logger(__name__)
        self._strategies: List[BaseDeploymentStrategy] = [
            UserAgentDeploymentStrategy(),
            ProjectAgentDeploymentStrategy(),
            SystemAgentDeploymentStrategy(),
        ]

        # Sort strategies by priority (lower number = higher priority)
        self._strategies.sort(key=lambda s: s.get_deployment_priority())

        self.logger.debug(
            f"Initialized with {len(self._strategies)} deployment strategies"
        )
        for strategy in self._strategies:
            self.logger.debug(f"  - {strategy}")

    def select_strategy(self, context: DeploymentContext) -> BaseDeploymentStrategy:
        """Select the most appropriate deployment strategy.

        Iterates through strategies in priority order and returns the first
        one that can handle the given context.

        Args:
            context: Deployment context with parameters

        Returns:
            The selected deployment strategy

        Raises:
            RuntimeError: If no strategy can handle the context
        """
        self.logger.debug(f"Selecting deployment strategy for context: {context}")

        for strategy in self._strategies:
            if strategy.can_handle(context):
                self.logger.info(f"Selected deployment strategy: {strategy.name}")
                return strategy

        # This should never happen as SystemAgentDeploymentStrategy
        # should handle any context as a fallback
        raise RuntimeError(f"No deployment strategy can handle context: {context}")

    def get_available_strategies(self) -> List[BaseDeploymentStrategy]:
        """Get list of all available strategies.

        Returns:
            List of all registered deployment strategies
        """
        return self._strategies.copy()

    def add_strategy(self, strategy: BaseDeploymentStrategy) -> None:
        """Add a new deployment strategy.

        Args:
            strategy: The strategy to add
        """
        self._strategies.append(strategy)
        # Re-sort by priority
        self._strategies.sort(key=lambda s: s.get_deployment_priority())
        self.logger.debug(f"Added strategy: {strategy}")

    def remove_strategy(self, strategy_class: type) -> bool:
        """Remove a deployment strategy by class type.

        Args:
            strategy_class: The class type of strategy to remove

        Returns:
            True if strategy was removed, False if not found
        """
        original_count = len(self._strategies)
        self._strategies = [
            s for s in self._strategies if not isinstance(s, strategy_class)
        ]
        removed = len(self._strategies) < original_count

        if removed:
            self.logger.debug(f"Removed strategy of type: {strategy_class.__name__}")

        return removed

    def get_strategy_for_context(
        self, context: DeploymentContext
    ) -> Optional[BaseDeploymentStrategy]:
        """Get strategy for context without raising exceptions.

        Args:
            context: Deployment context

        Returns:
            Selected strategy or None if no strategy can handle the context
        """
        try:
            return self.select_strategy(context)
        except RuntimeError:
            return None
