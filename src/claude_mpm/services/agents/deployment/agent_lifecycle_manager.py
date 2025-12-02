#!/usr/bin/env python3
"""
Agent Lifecycle Manager - ISS-0118 Integration Service (Refactored)
===================================================================

Comprehensive agent lifecycle management integrating modification tracking,
persistence, and registry services for complete agent management across
the three-tier hierarchy.

This refactored version delegates responsibilities to specialized services:
- AgentStateService: State tracking and transitions
- AgentOperationService: CRUD operations
- AgentRecordService: Persistence and history
- LifecycleHealthChecker: Health monitoring

Key Features:
- Unified agent lifecycle management (create, modify, delete, restore)
- Integrated modification tracking and persistence
- Automatic cache invalidation and registry updates
- Comprehensive backup and versioning system
- Conflict detection and resolution workflows
- Performance monitoring and optimization

Performance Impact:
- <100ms end-to-end agent operations
- Automatic cache coherency maintenance
- Intelligent persistence routing
- Real-time modification detection

Created for ISS-0118: Agent Registry and Hierarchical Discovery System
"""

import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.base_service import BaseService
from claude_mpm.core.unified_paths import get_path_manager
from claude_mpm.models.agent_definition import AgentDefinition
from claude_mpm.services.agents.management import AgentManager
from claude_mpm.services.agents.memory import (
    AgentPersistenceService,
    PersistenceOperation,
    PersistenceRecord,
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
from claude_mpm.utils.path_operations import path_ops

# Import extracted services
from .agent_operation_service import (
    AgentOperationService,
    LifecycleOperation,
    LifecycleOperationResult,
)
from .agent_record_service import AgentRecordService
from .agent_state_service import AgentLifecycleRecord, AgentStateService, LifecycleState

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
    Agent Lifecycle Manager - Unified agent management across hierarchy tiers.

    Refactored to use specialized services following SOLID principles:
    - AgentStateService handles state tracking
    - AgentOperationService handles CRUD operations
    - AgentRecordService handles persistence
    - LifecycleHealthChecker handles health monitoring

    Features:
    - Complete agent lifecycle management (CRUD operations)
    - Integrated modification tracking and persistence
    - Automatic cache invalidation and registry synchronization
    - Comprehensive backup and versioning system
    - Real-time conflict detection and resolution
    - Performance monitoring and optimization
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the agent lifecycle manager."""
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

        # Extracted internal services
        self.state_service = AgentStateService()
        self.operation_service = AgentOperationService()
        self.record_service = AgentRecordService()

        # Backward compatibility - expose service data through properties
        self._operation_lock = asyncio.Lock()

        # Performance metrics
        self.performance_metrics = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "average_duration_ms": 0.0,
            "cache_hit_rate": 0.0,
        }

        self.logger.info("AgentLifecycleManager initialized (refactored)")

    async def _initialize(self) -> None:
        """Initialize the lifecycle manager."""
        self.logger.info("Initializing AgentLifecycleManager...")

        # Initialize core services
        await self._initialize_core_services()

        # Initialize extracted services
        await self.state_service.start()
        await self.operation_service.start()
        await self.record_service.start()

        # Load existing agent records into state service
        records = await self.record_service.load_records()
        self.state_service.agent_records = records

        # Setup operation service dependencies
        self.operation_service.agent_manager = self.agent_manager
        self.operation_service.set_modification_tracker(self.modification_tracker)

        # Start service integrations
        await self._setup_service_integrations()

        # Perform initial registry sync
        if self.enable_registry_sync:
            await self._sync_with_registry()

        self.logger.info("AgentLifecycleManager initialized successfully")

    async def _cleanup(self) -> None:
        """Cleanup lifecycle manager resources."""
        self.logger.info("Cleaning up AgentLifecycleManager...")

        # Save agent records through record service
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
        """Perform lifecycle manager health checks."""
        from .lifecycle_health_checker import LifecycleHealthChecker

        checker = LifecycleHealthChecker(self)
        return await checker.perform_health_check()

    async def _initialize_core_services(self) -> None:
        """Initialize core service dependencies."""
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

    @property
    def agent_records(self) -> Dict[str, AgentLifecycleRecord]:
        """Get agent records from state service (backward compatibility)."""
        return self.state_service.agent_records

    @property
    def operation_history(self) -> List[LifecycleOperationResult]:
        """Get operation history from operation service (backward compatibility)."""
        return self.operation_service.operation_history

    @property
    def active_operations(self) -> Dict[str, LifecycleOperation]:
        """Get active operations from operation service (backward compatibility)."""
        return self.operation_service.active_operations

    async def _save_agent_records(self) -> None:
        """Save agent lifecycle records to disk."""
        try:
            records_file = (
                get_path_manager().get_tracking_dir() / "lifecycle_records.json"
            )
            path_ops.ensure_dir(records_file.parent)

            data = {}
            for agent_name, record in self.agent_records.items():
                record_dict = record.__dict__.copy()
                # Convert enums to strings for JSON serialization
                record_dict["current_state"] = record.current_state.value
                record_dict["tier"] = record.tier.value
                data[agent_name] = record_dict

            # Use save_json with custom encoder for datetime serialization
            import json

            # First convert to JSON string with custom encoder, then save
            json_str = json.dumps(data, indent=2, default=str)
            records_file.parent.mkdir(parents=True, exist_ok=True)
            with records_file.open("w", encoding="utf-8") as f:
                f.write(json_str)

            self.logger.debug(f"Saved {len(self.agent_records)} agent records")

        except Exception as e:
            self.logger.error(f"Failed to save agent records: {e}")

    async def _sync_with_registry(self) -> None:
        """Synchronize with agent registry."""
        try:
            if not self.agent_registry:
                return

            # Discover all agents via registry (sync methods)
            self.agent_registry.discover_agents()
            all_agents = self.agent_registry.list_agents()

            # Update lifecycle records with registry data
            for agent_metadata in all_agents:
                if agent_metadata.name not in self.agent_records:
                    # Create new lifecycle record
                    tier_map = {
                        "project": ModificationTier.PROJECT,
                        "user": ModificationTier.USER,
                        "system": ModificationTier.SYSTEM,
                    }

                    record = AgentLifecycleRecord(
                        agent_name=agent_metadata.name,
                        current_state=LifecycleState.ACTIVE,
                        tier=tier_map.get(agent_metadata.tier, ModificationTier.USER),
                        file_path=agent_metadata.path,
                        created_at=agent_metadata.last_modified or time.time(),
                        last_modified=agent_metadata.last_modified or time.time(),
                        version="1.0.0",
                        metadata={
                            "type": agent_metadata.type,
                            "description": agent_metadata.description,
                            "capabilities": agent_metadata.capabilities,
                            "validated": agent_metadata.validated,
                        },
                    )

                    self.agent_records[agent_metadata.name] = record

            self.logger.info(f"Synchronized with registry: {len(all_agents)} agents")

        except Exception as e:
            self.logger.error(f"Failed to sync with registry: {e}")

    async def create_agent(
        self,
        agent_name: str,
        agent_content: str,
        tier: ModificationTier = ModificationTier.USER,
        agent_type: str = "custom",
        **kwargs,
    ) -> LifecycleOperationResult:
        """
        Create a new agent with complete lifecycle tracking.

        Args:
            agent_name: Name of the agent to create
            agent_content: Content of the agent file
            tier: Target tier for creation
            agent_type: Type of agent (for classification)
            **kwargs: Additional metadata

        Returns:
            LifecycleOperationResult with operation details
        """
        start_time = time.time()

        # Check if agent already exists
        if self.state_service.get_record(agent_name):
            return LifecycleOperationResult(
                operation=LifecycleOperation.CREATE,
                agent_name=agent_name,
                success=False,
                duration_ms=0,
                error_message="Agent already exists",
            )

        # Create agent definition
        agent_def = await self._create_agent_definition(
            agent_name, agent_content, tier, agent_type, **kwargs
        )

        # Determine location based on tier
        location = "project" if tier == ModificationTier.PROJECT else "framework"

        # Create agent using AgentManager (sync call in executor)
        try:
            if self.agent_manager:
                file_path = await self._run_sync_in_executor(
                    self.agent_manager.create_agent,
                    agent_name,
                    agent_def,
                    location,
                )
            else:
                # Fallback to direct file creation if AgentManager not available
                file_path = await self._determine_agent_file_path(agent_name, tier)
                path_ops.ensure_dir(file_path.parent)
                path_ops.safe_write(file_path, agent_content)
        except Exception as e:
            self.logger.error(f"AgentManager failed to create agent: {e}")
            # Fallback to direct file creation
            file_path = await self._determine_agent_file_path(agent_name, tier)
            path_ops.ensure_dir(file_path.parent)
            path_ops.safe_write(file_path, agent_content)

        # Track modification
        modification = await self.modification_tracker.track_modification(
            agent_name=agent_name,
            modification_type=ModificationType.CREATE,
            file_path=str(file_path),
            tier=tier,
            agent_type=agent_type,
            **kwargs,
        )

        # Note: We don't use persistence_service for the actual write anymore
        # since AgentManager handles that. We create a synthetic record for compatibility.
        persistence_record = PersistenceRecord(
            operation_id=f"create_{agent_name}_{time.time()}",
            operation_type=PersistenceOperation.CREATE,
            agent_name=agent_name,
            source_tier=tier,
            target_tier=tier,
            strategy=self.default_persistence_strategy,
            success=True,
            timestamp=time.time(),
            file_path=str(file_path),
        )

        # Create lifecycle record
        lifecycle_record = AgentLifecycleRecord(
            agent_name=agent_name,
            current_state=LifecycleState.ACTIVE,
            tier=tier,
            file_path=str(file_path),
            created_at=time.time(),
            last_modified=time.time(),
            version="1.0.0",
            modifications=[modification.modification_id],
            persistence_operations=[persistence_record.operation_id],
            metadata={"agent_type": agent_type, **kwargs},
        )

        self.agent_records[agent_name] = lifecycle_record

        # Invalidate cache and update registry
        cache_invalidated = await self._invalidate_agent_cache(agent_name)
        registry_updated = await self._update_registry(agent_name)

        # Create result
        result = LifecycleOperationResult(
            operation=LifecycleOperation.CREATE,
            agent_name=agent_name,
            success=persistence_record.success,
            duration_ms=(time.time() - start_time) * 1000,
            modification_id=modification.modification_id,
            persistence_id=persistence_record.operation_id,
            cache_invalidated=cache_invalidated,
            registry_updated=registry_updated,
            metadata={"file_path": str(file_path)},
        )

        if not persistence_record.success:
            result.error_message = persistence_record.error_message
            lifecycle_record.current_state = LifecycleState.CONFLICTED

        # Update performance metrics
        await self._update_performance_metrics(result)

        self.operation_history.append(result)
        self.logger.info(f"Created agent '{agent_name}' in {result.duration_ms:.1f}ms")

        return result

    async def update_agent(
        self, agent_name: str, agent_content: str, **kwargs
    ) -> LifecycleOperationResult:
        """
        Update an existing agent with lifecycle tracking.

        Args:
            agent_name: Name of the agent to update
            agent_content: New content for the agent
            **kwargs: Additional metadata

        Returns:
            LifecycleOperationResult with operation details
        """
        start_time = time.time()

        async with self._operation_lock:
            self.active_operations[agent_name] = LifecycleOperation.UPDATE

            try:
                # Check if agent exists
                if agent_name not in self.agent_records:
                    return LifecycleOperationResult(
                        operation=LifecycleOperation.UPDATE,
                        agent_name=agent_name,
                        success=False,
                        duration_ms=(time.time() - start_time) * 1000,
                        error_message="Agent not found",
                    )

                record = self.agent_records[agent_name]

                # Update agent using AgentManager
                try:
                    if self.agent_manager:
                        # Read current agent to get full definition
                        current_def = await self._run_sync_in_executor(
                            self.agent_manager.read_agent, agent_name
                        )

                        if current_def:
                            # Update raw content
                            current_def.raw_content = agent_content

                            # Apply any metadata updates from kwargs
                            if "model_preference" in kwargs:
                                current_def.metadata.model_preference = kwargs[
                                    "model_preference"
                                ]
                            if "tags" in kwargs:
                                current_def.metadata.tags = kwargs["tags"]
                            if "specializations" in kwargs:
                                current_def.metadata.specializations = kwargs[
                                    "specializations"
                                ]

                            # Update via AgentManager
                            updated_def = await self._run_sync_in_executor(
                                self.agent_manager.update_agent,
                                agent_name,
                                {"raw_content": agent_content},
                                True,
                            )

                            if not updated_def:
                                raise Exception("AgentManager update failed")
                        else:
                            raise Exception("Could not read current agent definition")
                    else:
                        # Fallback to direct file update
                        file_path = Path(record.file_path)
                        if path_ops.validate_exists(file_path):
                            path_ops.safe_write(file_path, agent_content)
                except Exception as e:
                    self.logger.error(f"AgentManager failed to update agent: {e}")
                    # Fallback to direct file update
                    file_path = Path(record.file_path)
                    if path_ops.validate_exists(file_path):
                        path_ops.safe_write(file_path, agent_content)

                # Track modification
                modification = await self.modification_tracker.track_modification(
                    agent_name=agent_name,
                    modification_type=ModificationType.MODIFY,
                    file_path=record.file_path,
                    tier=record.tier,
                    **kwargs,
                )

                # Create synthetic persistence record for compatibility
                persistence_record = PersistenceRecord(
                    operation_id=f"update_{agent_name}_{time.time()}",
                    operation_type=PersistenceOperation.UPDATE,
                    agent_name=agent_name,
                    source_tier=record.tier,
                    target_tier=record.tier,
                    strategy=self.default_persistence_strategy,
                    success=True,
                    timestamp=time.time(),
                    file_path=record.file_path,
                )

                # Update lifecycle record
                record.current_state = LifecycleState.MODIFIED
                record.last_modified = time.time()
                record.modifications.append(modification.modification_id)
                record.persistence_operations.append(persistence_record.operation_id)

                # Increment version
                current_version = record.version.split(".")
                current_version[-1] = str(int(current_version[-1]) + 1)
                record.version = ".".join(current_version)

                # Invalidate cache and update registry
                cache_invalidated = await self._invalidate_agent_cache(agent_name)
                registry_updated = await self._update_registry(agent_name)

                # Create result
                result = LifecycleOperationResult(
                    operation=LifecycleOperation.UPDATE,
                    agent_name=agent_name,
                    success=persistence_record.success,
                    duration_ms=(time.time() - start_time) * 1000,
                    modification_id=modification.modification_id,
                    persistence_id=persistence_record.operation_id,
                    cache_invalidated=cache_invalidated,
                    registry_updated=registry_updated,
                    metadata={"new_version": record.version},
                )

                if not persistence_record.success:
                    result.error_message = persistence_record.error_message
                    record.current_state = LifecycleState.CONFLICTED

                # Update performance metrics
                await self._update_performance_metrics(result)

                self.operation_history.append(result)
                self.logger.info(
                    f"Updated agent '{agent_name}' to version {record.version} in {result.duration_ms:.1f}ms"
                )

                return result

            except Exception as e:
                result = LifecycleOperationResult(
                    operation=LifecycleOperation.UPDATE,
                    agent_name=agent_name,
                    success=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error_message=str(e),
                )

                self.operation_history.append(result)
                await self._update_performance_metrics(result)

                self.logger.error(f"Failed to update agent '{agent_name}': {e}")
                return result

            finally:
                self.active_operations.pop(agent_name, None)

    async def delete_agent(self, agent_name: str, **kwargs) -> LifecycleOperationResult:
        """
        Delete an agent with lifecycle tracking.

        Args:
            agent_name: Name of the agent to delete
            **kwargs: Additional metadata

        Returns:
            LifecycleOperationResult with operation details
        """
        start_time = time.time()

        async with self._operation_lock:
            self.active_operations[agent_name] = LifecycleOperation.DELETE

            try:
                # Check if agent exists
                if agent_name not in self.agent_records:
                    return LifecycleOperationResult(
                        operation=LifecycleOperation.DELETE,
                        agent_name=agent_name,
                        success=False,
                        duration_ms=(time.time() - start_time) * 1000,
                        error_message="Agent not found",
                    )

                record = self.agent_records[agent_name]

                # Create backup before deletion
                backup_path = None
                if self.enable_auto_backup:
                    backup_path = await self._create_deletion_backup(agent_name, record)

                # Track modification
                modification = await self.modification_tracker.track_modification(
                    agent_name=agent_name,
                    modification_type=ModificationType.DELETE,
                    file_path=record.file_path,
                    tier=record.tier,
                    backup_path=backup_path,
                    **kwargs,
                )

                # Delete agent using AgentManager
                deletion_success = False
                try:
                    if self.agent_manager:
                        deletion_success = await self._run_sync_in_executor(
                            self.agent_manager.delete_agent, agent_name
                        )
                        if not deletion_success:
                            raise Exception("AgentManager delete failed")
                    else:
                        # Fallback to direct file deletion
                        file_path = Path(record.file_path)
                        if path_ops.validate_exists(file_path):
                            path_ops.safe_delete(file_path)
                            deletion_success = True
                except Exception as e:
                    self.logger.error(f"AgentManager failed to delete agent: {e}")
                    # Fallback to direct file deletion
                    file_path = Path(record.file_path)
                    if path_ops.validate_exists(file_path):
                        path_ops.safe_delete(file_path)
                        deletion_success = True

                # Update lifecycle record
                record.current_state = LifecycleState.DELETED
                record.last_modified = time.time()
                record.modifications.append(modification.modification_id)
                if backup_path:
                    record.backup_paths.append(backup_path)

                # Invalidate cache and update registry
                cache_invalidated = await self._invalidate_agent_cache(agent_name)
                registry_updated = await self._update_registry(agent_name)

                # Create result
                result = LifecycleOperationResult(
                    operation=LifecycleOperation.DELETE,
                    agent_name=agent_name,
                    success=True,
                    duration_ms=(time.time() - start_time) * 1000,
                    modification_id=modification.modification_id,
                    cache_invalidated=cache_invalidated,
                    registry_updated=registry_updated,
                    metadata={"backup_path": backup_path},
                )

                # Update performance metrics
                await self._update_performance_metrics(result)

                self.operation_history.append(result)
                self.logger.info(
                    f"Deleted agent '{agent_name}' in {result.duration_ms:.1f}ms"
                )

                return result

            except Exception as e:
                result = LifecycleOperationResult(
                    operation=LifecycleOperation.DELETE,
                    agent_name=agent_name,
                    success=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error_message=str(e),
                )

                self.operation_history.append(result)
                await self._update_performance_metrics(result)

                self.logger.error(f"Failed to delete agent '{agent_name}': {e}")
                return result

            finally:
                self.active_operations.pop(agent_name, None)

    async def _determine_agent_file_path(
        self, agent_name: str, tier: ModificationTier
    ) -> Path:
        """Determine appropriate file path for agent."""
        if tier == ModificationTier.USER:
            base_path = get_path_manager().get_user_agents_dir()
        elif tier == ModificationTier.PROJECT:
            base_path = get_path_manager().get_project_agents_dir()
        else:  # SYSTEM
            base_path = Path.cwd() / "claude_pm" / "agents"

        path_ops.ensure_dir(base_path)
        return base_path / f"{agent_name}_agent.py"

    async def _create_deletion_backup(
        self, agent_name: str, record: AgentLifecycleRecord
    ) -> Optional[str]:
        """Create backup before agent deletion."""
        try:
            source_path = Path(record.file_path)
            if not path_ops.validate_exists(source_path):
                return None

            backup_dir = get_path_manager().get_tracking_dir() / "backups"
            path_ops.ensure_dir(backup_dir)

            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{agent_name}_deleted_{timestamp}{source_path.suffix}"
            backup_path = backup_dir / backup_filename

            path_ops.safe_copy(source_path, backup_path)
            return str(backup_path)

        except Exception as e:
            self.logger.warning(
                f"Failed to create deletion backup for {agent_name}: {e}"
            )
            return None

    async def _invalidate_agent_cache(self, agent_name: str) -> bool:
        """Invalidate cache entries for agent."""
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
            # Refresh registry (discover_agents is synchronous)
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

            # Update lifecycle record if exists
            if agent_name in self.agent_records:
                record = self.agent_records[agent_name]
                record.last_modified = modification.timestamp
                record.modifications.append(modification.modification_id)

                # Update state based on modification type
                if modification.modification_type == ModificationType.DELETE:
                    record.current_state = LifecycleState.DELETED
                elif modification.modification_type in [
                    ModificationType.CREATE,
                    ModificationType.MODIFY,
                ]:
                    record.current_state = LifecycleState.MODIFIED

                self.logger.debug(
                    f"Updated lifecycle record for {agent_name} due to {modification.modification_type.value}"
                )

        except Exception as e:
            self.logger.error(f"Error handling modification event: {e}")

    # Test capability methods moved to LifecycleHealthChecker

    async def _cleanup_core_services(self) -> None:
        """Cleanup core services if we manage their lifecycle."""
        try:
            if self.modification_tracker:
                await self.modification_tracker.stop()

            if self.persistence_service:
                await self.persistence_service.stop()

        except Exception as e:
            self.logger.error(f"Error cleaning up core services: {e}")

    # Public API Methods

    async def get_agent_status(self, agent_name: str) -> Optional[AgentLifecycleRecord]:
        """Get current status of an agent."""
        return self.agent_records.get(agent_name)

    async def list_agents(
        self, state_filter: Optional[LifecycleState] = None
    ) -> List[AgentLifecycleRecord]:
        """List agents with optional state filtering."""
        agents = list(self.agent_records.values())

        if state_filter:
            agents = [agent for agent in agents if agent.current_state == state_filter]

        return sorted(agents, key=lambda x: x.last_modified, reverse=True)

    async def get_operation_history(
        self, agent_name: Optional[str] = None, limit: int = 100
    ) -> List[LifecycleOperationResult]:
        """Get operation history with optional filtering."""
        history = self.operation_history

        if agent_name:
            history = [op for op in history if op.agent_name == agent_name]

        return sorted(history, key=lambda x: x.duration_ms, reverse=True)[:limit]

    async def get_lifecycle_stats(self) -> Dict[str, Any]:
        """Get comprehensive lifecycle statistics."""
        stats = {
            "total_agents": len(self.agent_records),
            "active_operations": len(self.active_operations),
            "performance_metrics": self.performance_metrics.copy(),
        }

        # State distribution
        state_counts = {}
        for record in self.agent_records.values():
            state_counts[record.current_state.value] = (
                state_counts.get(record.current_state.value, 0) + 1
            )

        stats["agents_by_state"] = state_counts

        # Tier distribution
        tier_counts = {}
        for record in self.agent_records.values():
            tier_counts[record.tier.value] = tier_counts.get(record.tier.value, 0) + 1

        stats["agents_by_tier"] = tier_counts

        # Recent activity
        recent_ops = [
            op
            for op in self.operation_history
            if (time.time() - (op.duration_ms / 1000)) < 3600  # Last hour
        ]
        stats["recent_operations"] = len(recent_ops)

        return stats

    async def _create_agent_definition(
        self,
        agent_name: str,
        agent_content: str,
        tier: ModificationTier,
        agent_type: str,
        **kwargs,
    ) -> AgentDefinition:
        """Create an AgentDefinition from lifecycle parameters."""
        from .agent_definition_factory import AgentDefinitionFactory

        factory = AgentDefinitionFactory()
        return factory.create_agent_definition(
            agent_name, agent_content, tier, agent_type, **kwargs
        )

    async def _run_sync_in_executor(self, func, *args, **kwargs):
        """
        Run a synchronous function in an executor to avoid blocking.

        WHY: AgentManager has synchronous methods but AgentLifecycleManager is async.
        This allows us to call sync methods without blocking the event loop.

        PERFORMANCE: Uses the default executor which manages a thread pool efficiently.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)

    async def restore_agent(
        self, agent_name: str, backup_path: Optional[str] = None
    ) -> LifecycleOperationResult:
        """Restore agent from backup."""
        from .agent_restore_handler import AgentRestoreHandler

        handler = AgentRestoreHandler(self)
        return await handler.restore_agent(agent_name, backup_path)
