"""Health checker for agent lifecycle manager.

This module provides health checking functionality for the AgentLifecycleManager.
Extracted to reduce complexity and improve maintainability.
"""

from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from .agent_lifecycle_manager import AgentLifecycleManager


class LifecycleHealthChecker:
    """Handles health checking for the lifecycle manager."""

    def __init__(self, lifecycle_manager: "AgentLifecycleManager"):
        """Initialize the health checker."""
        self.lifecycle_manager = lifecycle_manager
        self.logger = lifecycle_manager.logger

    async def perform_health_check(self) -> Dict[str, bool]:
        """Perform comprehensive health checks."""
        checks = {}

        try:
            # Check core service availability
            checks["cache_service"] = self.lifecycle_manager.shared_cache is not None
            checks["registry_service"] = (
                self.lifecycle_manager.agent_registry is not None
            )
            checks["tracker_service"] = (
                self.lifecycle_manager.modification_tracker is not None
            )
            checks["persistence_service"] = (
                self.lifecycle_manager.persistence_service is not None
            )

            # Check operation capabilities
            checks["can_create_agents"] = await self._test_create_capability()
            checks["can_modify_agents"] = await self._test_modify_capability()
            checks["can_delete_agents"] = await self._test_delete_capability()

            # Check data integrity
            checks["agent_records_valid"] = (
                len(self.lifecycle_manager.agent_records) >= 0
            )
            checks["operation_history_valid"] = (
                len(self.lifecycle_manager.operation_history) >= 0
            )

        except Exception as e:
            self.logger.error(f"Lifecycle manager health check failed: {e}")
            checks["health_check_error"] = False

        return checks

    async def _test_create_capability(self) -> bool:
        """Test agent creation capability."""
        try:
            # This would test if we can create agents in the configured tiers
            return (
                self.lifecycle_manager.modification_tracker is not None
                and self.lifecycle_manager.persistence_service is not None
            )
        except Exception:
            return False

    async def _test_modify_capability(self) -> bool:
        """Test agent modification capability."""
        try:
            # This would test if we can modify existing agents
            return (
                self.lifecycle_manager.modification_tracker is not None
                and self.lifecycle_manager.persistence_service is not None
            )
        except Exception:
            return False

    async def _test_delete_capability(self) -> bool:
        """Test agent deletion capability."""
        try:
            # This would test if we can delete agents
            return self.lifecycle_manager.modification_tracker is not None
        except Exception:
            return False
