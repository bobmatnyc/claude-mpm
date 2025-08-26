#!/usr/bin/env python3
"""
Agent Lifecycle Manager - Refactored Version
============================================

This is the refactored version of AgentLifecycleManager that delegates
responsibilities to specialized services following SOLID principles.

Line count reduction: From 1,020 lines to ~600 lines (40% reduction)
"""

import asyncio
from typing import Any, Dict, List, Optional

from claude_mpm.core.base_service import BaseService
from claude_mpm.services.agents.management import AgentManager
from claude_mpm.services.agents.memory import (
    AgentPersistenceService,
    PersistenceStrategy,
)
from claude_mpm.services.agents.registry import AgentRegistry
from claude_mpm.services.agents.registry.modification_tracker import (
    AgentModification,
    AgentModificationTracker,
    ModificationTier,
    ModificationType,
)
from claude_mpm.services.memory.cache.shared_prompt_cache import SharedPromptCache

# Import extracted services
from .agent_operation_service import (
    AgentOperationService,
    LifecycleOperation,
    LifecycleOperationResult,
)
from .agent_record_service import AgentRecordService
from .agent_state_service import (
    AgentLifecycleRecord,
    AgentStateService,
    LifecycleState,
)

# Re-export for backward compatibility
__all__ = [
    "AgentLifecycleManager",
    "AgentLifecycleRecord",
    "LifecycleOperation",
    "LifecycleOperationResult",
    "LifecycleState",
]


class AgentLifecycleManager(BaseService):
    """
    Agent Lifecycle Manager - Orchestrates agent lifecycle through specialized services.

    Refactored Architecture:
    - AgentStateService: Manages agent states and transitions
    - AgentOperationService: Handles CRUD operations
    - AgentRecordService: Manages persistence and history
    - LifecycleHealthChecker: Monitors system health

    This manager now acts as a facade/orchestrator, delegating specific
    responsibilities to appropriate services while maintaining backward
    compatibility with existing interfaces.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the lifecycle manager with configuration."""
        super().__init__("agent_lifecycle_manager", config)

        # Configuration
        self.enable_auto_backup = self.get_config("enable_auto_backup", True)
        self.enable_auto_validation = self.get_config("enable_auto_validation", True)
        self.enable_cache_invalidation = self.get_config(
            "enable_cache_invalidation", True
        )
        self.enable_registry_sync = self.get_config("enable_registry_sync", True)
        self.default_persistence_strategy = PersistenceStrategy(
            self.get_config(
                "default_persistence_strategy", PersistenceStrategy.USER_OVERRIDE.value
            )
        )

        # Core external services
        self.shared_cache: Optional[SharedPromptCache] = None
        self.agent_registry: Optional[AgentRegistry] = None
        self.modification_tracker: Optional[AgentModificationTracker] = None
        self.persistence_service: Optional[AgentPersistenceService] = None
        self.agent_manager: Optional[AgentManager] = None

        # Extracted internal services (composition over inheritance)
        self.state_service = AgentStateService()
        self.operation_service = AgentOperationService()
        self.record_service = AgentRecordService()

        # Performance metrics (maintained for compatibility)
        self.performance_metrics = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "average_duration_ms": 0.0,
            "cache_hit_rate": 0.0,
        }

        self.logger.info("AgentLifecycleManager initialized (refactored)")

    # Backward compatibility properties
    @property
    def agent_records(self) -> Dict[str, AgentLifecycleRecord]:
        """Get agent records from state service."""
        return self.state_service.agent_records

    @property
    def operation_history(self) -> List[LifecycleOperationResult]:
        """Get operation history from operation service."""
        return self.operation_service.operation_history

    @property
    def active_operations(self) -> Dict[str, LifecycleOperation]:
        """Get active operations from operation service."""
        return self.operation_service.active_operations

    async def _initialize(self) -> None:
        """Initialize the lifecycle manager and its services."""
        self.logger.info("Initializing AgentLifecycleManager...")

        # Initialize core external services
        await self._initialize_core_services()

        # Initialize extracted services
        await self.state_service.start()
        await self.operation_service.start()
        await self.record_service.start()

        # Wire up service dependencies
        self.operation_service.agent_manager = self.agent_manager
        self.operation_service.set_modification_tracker(self.modification_tracker)

        # Load persisted data
        records = await self.record_service.load_records()
        self.state_service.agent_records = records

        await self.record_service.load_history()
        # Convert history back to operation results if needed
        # For now, we'll start with empty history

        # Setup service integrations
        await self._setup_service_integrations()

        # Perform initial registry sync
        if self.enable_registry_sync:
            await self._sync_with_registry()

        self.logger.info("AgentLifecycleManager initialized successfully")

    async def _cleanup(self) -> None:
        """Cleanup lifecycle manager and its services."""
        self.logger.info("Cleaning up AgentLifecycleManager...")

        # Save current state
        await self.record_service.save_records(self.state_service.agent_records)
        await self.record_service.save_history(self.operation_service.operation_history)

        # Stop extracted services
        await self.state_service.stop()
        await self.operation_service.stop()
        await self.record_service.stop()

        # Stop core services if we own them
        await self._cleanup_core_services()

        self.logger.info("AgentLifecycleManager cleaned up")

    async def _health_check(self) -> Dict[str, bool]:
        """Perform health checks on all services."""
        from .lifecycle_health_checker import LifecycleHealthChecker

        checker = LifecycleHealthChecker(self)
        return await checker.perform_health_check()

    async def _initialize_core_services(self) -> None:
        """Initialize core external service dependencies."""
        try:
            # Initialize SharedPromptCache
            self.shared_cache = SharedPromptCache.get_instance()

            # Initialize AgentRegistry
            self.agent_registry = AgentRegistry(cache_service=self.shared_cache)

            # Initialize AgentModificationTracker
            self.modification_tracker = AgentModificationTracker()
            await self.modification_tracker.start()

            # Initialize AgentPersistenceService
            self.persistence_service = AgentPersistenceService()
            await self.persistence_service.start()

            # Initialize AgentManager
            self.agent_manager = AgentManager()

            self.logger.info("Core services initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize core services: {e}")
            raise

    async def _setup_service_integrations(self) -> None:
        """Set up integrations between services."""
        try:
            # Register modification callback
            if self.modification_tracker:
                self.modification_tracker.register_modification_callback(
                    self._handle_modification_event
                )

            self.logger.debug("Service integrations set up successfully")

        except Exception as e:
            self.logger.warning(f"Failed to setup some service integrations: {e}")

    async def _sync_with_registry(self) -> None:
        """Synchronize state with agent registry."""
        try:
            if not self.agent_registry:
                return

            # Discover all agents
            self.agent_registry.discover_agents()
            all_agents = self.agent_registry.list_agents()

            # Update state service with registry data
            for agent_metadata in all_agents:
                if not self.state_service.get_record(agent_metadata.name):
                    # Map tier strings to enums
                    tier_map = {
                        "project": ModificationTier.PROJECT,
                        "user": ModificationTier.USER,
                        "system": ModificationTier.SYSTEM,
                    }

                    # Create new record
                    self.state_service.create_record(
                        agent_name=agent_metadata.name,
                        tier=tier_map.get(agent_metadata.tier, ModificationTier.USER),
                        file_path=agent_metadata.path,
                        initial_state=LifecycleState.ACTIVE,
                        version="1.0.0",
                        type=agent_metadata.type,
                        description=agent_metadata.description,
                        capabilities=agent_metadata.capabilities,
                        validated=agent_metadata.validated,
                    )

            self.logger.info(f"Synchronized with registry: {len(all_agents)} agents")

        except Exception as e:
            self.logger.error(f"Failed to sync with registry: {e}")

    # Main lifecycle operations (orchestration layer)

    async def create_agent(
        self,
        agent_name: str,
        agent_content: str,
        tier: ModificationTier = ModificationTier.USER,
        agent_type: str = "custom",
        **kwargs,
    ) -> LifecycleOperationResult:
        """
        Create a new agent through orchestrated services.

        Orchestration flow:
        1. Check state service for existing agent
        2. Execute creation through operation service
        3. Update state service with new record
        4. Invalidate cache and update registry
        5. Track metrics
        """
        # Check if agent already exists
        if self.state_service.get_record(agent_name):
            return LifecycleOperationResult(
                operation=LifecycleOperation.CREATE,
                agent_name=agent_name,
                success=False,
                duration_ms=0,
                error_message="Agent already exists",
            )

        # Execute creation
        result = await self.operation_service.create_agent(
            agent_name=agent_name,
            agent_content=agent_content,
            tier=tier,
            agent_type=agent_type,
            **kwargs,
        )

        # Update state if successful
        if result.success:
            # Create state record
            self.state_service.create_record(
                agent_name=agent_name,
                tier=tier,
                file_path=result.metadata.get("file_path", ""),
                initial_state=LifecycleState.ACTIVE,
                version="1.0.0",
                agent_type=agent_type,
                **kwargs,
            )

            # Track modification
            if result.modification_id:
                self.state_service.add_modification(agent_name, result.modification_id)

            # Handle cache and registry
            result.cache_invalidated = await self._invalidate_agent_cache(agent_name)
            result.registry_updated = await self._update_registry(agent_name)

            # Update metrics
            await self._update_performance_metrics(result)

        return result

    async def update_agent(
        self, agent_name: str, agent_content: str, **kwargs
    ) -> LifecycleOperationResult:
        """
        Update an existing agent through orchestrated services.

        Orchestration flow:
        1. Verify agent exists in state service
        2. Execute update through operation service
        3. Update state and version
        4. Invalidate cache and update registry
        5. Track metrics
        """
        # Check if agent exists
        record = self.state_service.get_record(agent_name)
        if not record:
            return LifecycleOperationResult(
                operation=LifecycleOperation.UPDATE,
                agent_name=agent_name,
                success=False,
                duration_ms=0,
                error_message="Agent not found",
            )

        # Execute update
        result = await self.operation_service.update_agent(
            agent_name=agent_name,
            agent_content=agent_content,
            file_path=record.file_path,
            tier=record.tier,
            **kwargs,
        )

        # Update state if successful
        if result.success:
            # Update state
            self.state_service.update_state(
                agent_name, LifecycleState.MODIFIED, "Agent updated"
            )

            # Increment version
            new_version = self.state_service.increment_version(agent_name)
            result.metadata["new_version"] = new_version

            # Track modification
            if result.modification_id:
                self.state_service.add_modification(agent_name, result.modification_id)

            # Handle cache and registry
            result.cache_invalidated = await self._invalidate_agent_cache(agent_name)
            result.registry_updated = await self._update_registry(agent_name)

            # Update metrics
            await self._update_performance_metrics(result)

        return result

    async def delete_agent(self, agent_name: str, **kwargs) -> LifecycleOperationResult:
        """
        Delete an agent through orchestrated services.

        Orchestration flow:
        1. Verify agent exists in state service
        2. Create backup if enabled
        3. Execute deletion through operation service
        4. Update state to DELETED
        5. Invalidate cache and update registry
        6. Track metrics
        """
        # Check if agent exists
        record = self.state_service.get_record(agent_name)
        if not record:
            return LifecycleOperationResult(
                operation=LifecycleOperation.DELETE,
                agent_name=agent_name,
                success=False,
                duration_ms=0,
                error_message="Agent not found",
            )

        # Execute deletion
        result = await self.operation_service.delete_agent(
            agent_name=agent_name,
            file_path=record.file_path,
            tier=record.tier,
            create_backup=self.enable_auto_backup,
            **kwargs,
        )

        # Update state if successful
        if result.success:
            # Update state
            self.state_service.update_state(
                agent_name, LifecycleState.DELETED, "Agent deleted"
            )

            # Track backup path
            if result.metadata.get("backup_path"):
                self.state_service.add_backup_path(
                    agent_name, result.metadata["backup_path"]
                )

            # Track modification
            if result.modification_id:
                self.state_service.add_modification(agent_name, result.modification_id)

            # Handle cache and registry
            result.cache_invalidated = await self._invalidate_agent_cache(agent_name)
            result.registry_updated = await self._update_registry(agent_name)

            # Update metrics
            await self._update_performance_metrics(result)

        return result

    async def restore_agent(
        self, agent_name: str, backup_path: Optional[str] = None
    ) -> LifecycleOperationResult:
        """Restore an agent from backup."""
        from .agent_restore_handler import AgentRestoreHandler

        handler = AgentRestoreHandler(self)
        return await handler.restore_agent(agent_name, backup_path)

    # Query methods (delegated to services)

    async def get_agent_status(self, agent_name: str) -> Optional[AgentLifecycleRecord]:
        """Get current status of an agent."""
        return self.state_service.get_record(agent_name)

    async def list_agents(
        self, state_filter: Optional[LifecycleState] = None
    ) -> List[AgentLifecycleRecord]:
        """List agents with optional state filtering."""
        return self.state_service.list_agents_by_state(state_filter)

    async def get_operation_history(
        self, agent_name: Optional[str] = None, limit: int = 100
    ) -> List[LifecycleOperationResult]:
        """Get operation history with optional filtering."""
        return self.operation_service.get_operation_history(agent_name, limit)

    async def get_lifecycle_stats(self) -> Dict[str, Any]:
        """Get comprehensive lifecycle statistics."""
        # Combine statistics from all services
        stats = {
            "total_agents": len(self.state_service.agent_records),
            "active_operations": len(self.operation_service.active_operations),
            "performance_metrics": self.operation_service.get_metrics(),
            "agents_by_state": self.state_service.get_state_statistics(),
            "agents_by_tier": self.state_service.get_tier_statistics(),
        }

        # Add record service statistics
        record_stats = await self.record_service.get_statistics()
        stats.update(record_stats)

        return stats

    # Support methods

    async def _invalidate_agent_cache(self, agent_name: str) -> bool:
        """Invalidate cache entries for an agent."""
        if not self.enable_cache_invalidation or not self.shared_cache:
            return False

        try:
            patterns = [
                f"agent_profile:{agent_name}:*",
                f"task_prompt:{agent_name}:*",
                "agent_registry_discovery",
                f"agent_profile_enhanced:{agent_name}:*",
            ]

            for pattern in patterns:
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda p=pattern: self.shared_cache.invalidate(p)
                )

            return True

        except Exception as e:
            self.logger.warning(f"Failed to invalidate cache for {agent_name}: {e}")
            return False

    async def _update_registry(self, agent_name: str) -> bool:
        """Update agent registry after modification."""
        if not self.enable_registry_sync or not self.agent_registry:
            return False

        try:
            # Refresh registry
            self.agent_registry.discover_agents()
            return True

        except Exception as e:
            self.logger.warning(f"Failed to update registry for {agent_name}: {e}")
            return False

    async def _update_performance_metrics(
        self, result: LifecycleOperationResult
    ) -> None:
        """Update performance metrics with operation result."""
        from .lifecycle_performance_tracker import LifecyclePerformanceTracker

        tracker = LifecyclePerformanceTracker(self.performance_metrics)
        tracker.update_metrics(result)

    async def _handle_modification_event(self, modification: AgentModification) -> None:
        """Handle modification events from tracker."""
        try:
            agent_name = modification.agent_name

            # Update state based on modification
            if modification.modification_type == ModificationType.DELETE:
                self.state_service.update_state(
                    agent_name, LifecycleState.DELETED, "External deletion detected"
                )
            elif modification.modification_type in [
                ModificationType.CREATE,
                ModificationType.MODIFY,
            ]:
                self.state_service.update_state(
                    agent_name,
                    LifecycleState.MODIFIED,
                    "External modification detected",
                )

            # Track modification
            self.state_service.add_modification(
                agent_name, modification.modification_id
            )

            self.logger.debug(
                f"Handled {modification.modification_type.value} event for {agent_name}"
            )

        except Exception as e:
            self.logger.error(f"Error handling modification event: {e}")

    async def _cleanup_core_services(self) -> None:
        """Cleanup core services if we manage their lifecycle."""
        try:
            if self.modification_tracker:
                await self.modification_tracker.stop()

            if self.persistence_service:
                await self.persistence_service.stop()

        except Exception as e:
            self.logger.error(f"Error cleaning up core services: {e}")
