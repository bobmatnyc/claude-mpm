#!/usr/bin/env python3
"""
Agent Operation Service - Core Operations for Agent Lifecycle
=============================================================

Handles core agent operations (create, update, delete, restore).
Extracted from AgentLifecycleManager to follow Single Responsibility Principle.

Key Responsibilities:
- Execute agent CRUD operations
- Coordinate with AgentManager for file operations
- Track operation results and history
- Handle operation locking and concurrency
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.base_service import BaseService
from claude_mpm.core.unified_paths import get_path_manager
from claude_mpm.models.agent_definition import AgentDefinition
from claude_mpm.services.agents.management import AgentManager
from claude_mpm.services.agents.registry.modification_tracker import (
    AgentModificationTracker,
    ModificationTier,
    ModificationType,
)
from claude_mpm.utils.path_operations import path_ops


class LifecycleOperation(Enum):
    """Agent lifecycle operations."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"
    MIGRATE = "migrate"
    REPLICATE = "replicate"
    VALIDATE = "validate"


@dataclass
class LifecycleOperationResult:
    """Result of a lifecycle operation."""

    operation: LifecycleOperation
    agent_name: str
    success: bool
    duration_ms: float
    error_message: Optional[str] = None
    modification_id: Optional[str] = None
    persistence_id: Optional[str] = None
    cache_invalidated: bool = False
    registry_updated: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentOperationService(BaseService):
    """
    Service for executing agent lifecycle operations.

    Responsibilities:
    - Create, update, delete agents
    - Coordinate with AgentManager for file operations
    - Track operation history
    - Handle concurrency and locking
    """

    def __init__(self, agent_manager: Optional[AgentManager] = None):
        """Initialize the operation service."""
        super().__init__("agent_operation_service")

        # Dependencies
        self.agent_manager = agent_manager
        self.modification_tracker: Optional[AgentModificationTracker] = None

        # Operation tracking
        self.operation_history: List[LifecycleOperationResult] = []
        self.active_operations: Dict[str, LifecycleOperation] = {}

        # Operation lock for thread safety
        self._operation_lock = asyncio.Lock()

        # Performance metrics
        self.metrics = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "average_duration_ms": 0.0,
        }

        self.logger.info("AgentOperationService initialized")

    def set_modification_tracker(self, tracker: AgentModificationTracker):
        """Set the modification tracker dependency."""
        self.modification_tracker = tracker

    async def create_agent(
        self,
        agent_name: str,
        agent_content: str,
        tier: ModificationTier = ModificationTier.USER,
        agent_type: str = "custom",
        **kwargs,
    ) -> LifecycleOperationResult:
        """
        Create a new agent.

        Args:
            agent_name: Name of the agent
            agent_content: Content of the agent file
            tier: Target tier for creation
            agent_type: Type of agent
            **kwargs: Additional metadata

        Returns:
            LifecycleOperationResult with operation details
        """
        start_time = time.time()

        async with self._operation_lock:
            self.active_operations[agent_name] = LifecycleOperation.CREATE

            try:
                # Create agent definition
                agent_def = await self._create_agent_definition(
                    agent_name, agent_content, tier, agent_type, **kwargs
                )

                # Determine location
                location = (
                    "project" if tier == ModificationTier.PROJECT else "framework"
                )

                # Create agent using AgentManager
                file_path = await self._execute_agent_creation(
                    agent_name, agent_def, location, tier, agent_content
                )

                # Track modification if tracker available
                modification_id = None
                if self.modification_tracker:
                    modification = await self.modification_tracker.track_modification(
                        agent_name=agent_name,
                        modification_type=ModificationType.CREATE,
                        file_path=str(file_path),
                        tier=tier,
                        agent_type=agent_type,
                        **kwargs,
                    )
                    modification_id = modification.modification_id

                # Create result
                result = LifecycleOperationResult(
                    operation=LifecycleOperation.CREATE,
                    agent_name=agent_name,
                    success=True,
                    duration_ms=(time.time() - start_time) * 1000,
                    modification_id=modification_id,
                    metadata={"file_path": str(file_path), "tier": tier.value},
                )

                self._update_metrics(result)
                self.operation_history.append(result)

                self.logger.info(
                    f"Created agent '{agent_name}' in {result.duration_ms:.1f}ms"
                )

                return result

            except Exception as e:
                result = LifecycleOperationResult(
                    operation=LifecycleOperation.CREATE,
                    agent_name=agent_name,
                    success=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error_message=str(e),
                )

                self._update_metrics(result)
                self.operation_history.append(result)

                self.logger.error(f"Failed to create agent '{agent_name}': {e}")
                return result

            finally:
                self.active_operations.pop(agent_name, None)

    async def update_agent(
        self,
        agent_name: str,
        agent_content: str,
        file_path: str,
        tier: ModificationTier,
        **kwargs,
    ) -> LifecycleOperationResult:
        """
        Update an existing agent.

        Args:
            agent_name: Name of the agent
            agent_content: New content for the agent
            file_path: Current file path
            tier: Agent tier
            **kwargs: Additional metadata

        Returns:
            LifecycleOperationResult with operation details
        """
        start_time = time.time()

        async with self._operation_lock:
            self.active_operations[agent_name] = LifecycleOperation.UPDATE

            try:
                # Update agent using AgentManager
                await self._execute_agent_update(
                    agent_name, agent_content, file_path, **kwargs
                )

                # Track modification if tracker available
                modification_id = None
                if self.modification_tracker:
                    modification = await self.modification_tracker.track_modification(
                        agent_name=agent_name,
                        modification_type=ModificationType.MODIFY,
                        file_path=file_path,
                        tier=tier,
                        **kwargs,
                    )
                    modification_id = modification.modification_id

                # Create result
                result = LifecycleOperationResult(
                    operation=LifecycleOperation.UPDATE,
                    agent_name=agent_name,
                    success=True,
                    duration_ms=(time.time() - start_time) * 1000,
                    modification_id=modification_id,
                    metadata={"file_path": file_path},
                )

                self._update_metrics(result)
                self.operation_history.append(result)

                self.logger.info(
                    f"Updated agent '{agent_name}' in {result.duration_ms:.1f}ms"
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

                self._update_metrics(result)
                self.operation_history.append(result)

                self.logger.error(f"Failed to update agent '{agent_name}': {e}")
                return result

            finally:
                self.active_operations.pop(agent_name, None)

    async def delete_agent(
        self,
        agent_name: str,
        file_path: str,
        tier: ModificationTier,
        create_backup: bool = True,
        **kwargs,
    ) -> LifecycleOperationResult:
        """
        Delete an agent.

        Args:
            agent_name: Name of the agent
            file_path: Path to agent file
            tier: Agent tier
            create_backup: Whether to create backup before deletion
            **kwargs: Additional metadata

        Returns:
            LifecycleOperationResult with operation details
        """
        start_time = time.time()

        async with self._operation_lock:
            self.active_operations[agent_name] = LifecycleOperation.DELETE

            try:
                # Create backup if requested
                backup_path = None
                if create_backup:
                    backup_path = await self._create_deletion_backup(
                        agent_name, file_path
                    )

                # Track modification if tracker available
                modification_id = None
                if self.modification_tracker:
                    modification = await self.modification_tracker.track_modification(
                        agent_name=agent_name,
                        modification_type=ModificationType.DELETE,
                        file_path=file_path,
                        tier=tier,
                        backup_path=backup_path,
                        **kwargs,
                    )
                    modification_id = modification.modification_id

                # Delete agent
                await self._execute_agent_deletion(agent_name, file_path)

                # Create result
                result = LifecycleOperationResult(
                    operation=LifecycleOperation.DELETE,
                    agent_name=agent_name,
                    success=True,
                    duration_ms=(time.time() - start_time) * 1000,
                    modification_id=modification_id,
                    metadata={"backup_path": backup_path},
                )

                self._update_metrics(result)
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

                self._update_metrics(result)
                self.operation_history.append(result)

                self.logger.error(f"Failed to delete agent '{agent_name}': {e}")
                return result

            finally:
                self.active_operations.pop(agent_name, None)

    async def _execute_agent_creation(
        self,
        agent_name: str,
        agent_def: AgentDefinition,
        location: str,
        tier: ModificationTier,
        agent_content: str,
    ) -> Path:
        """Execute agent creation through AgentManager or fallback."""
        try:
            if self.agent_manager:
                file_path = await self._run_sync_in_executor(
                    self.agent_manager.create_agent,
                    agent_name,
                    agent_def,
                    location,
                )
                return Path(file_path)
            # Fallback to direct file creation
            file_path = await self._determine_agent_file_path(agent_name, tier)
            path_ops.ensure_dir(file_path.parent)
            path_ops.safe_write(file_path, agent_content)
            return file_path
        except Exception as e:
            self.logger.error(f"AgentManager failed to create agent: {e}")
            # Fallback to direct file creation
            file_path = await self._determine_agent_file_path(agent_name, tier)
            path_ops.ensure_dir(file_path.parent)
            path_ops.safe_write(file_path, agent_content)
            return file_path

    async def _execute_agent_update(
        self, agent_name: str, agent_content: str, file_path: str, **kwargs
    ):
        """Execute agent update through AgentManager or fallback."""
        try:
            if self.agent_manager:
                # Read current agent to get full definition
                current_def = await self._run_sync_in_executor(
                    self.agent_manager.read_agent, agent_name
                )

                if current_def:
                    # Update raw content
                    current_def.raw_content = agent_content

                    # Apply metadata updates
                    for key, value in kwargs.items():
                        if hasattr(current_def.metadata, key):
                            setattr(current_def.metadata, key, value)

                    # Update via AgentManager
                    await self._run_sync_in_executor(
                        self.agent_manager.update_agent,
                        agent_name,
                        {"raw_content": agent_content},
                        True,
                    )
                else:
                    raise Exception("Could not read current agent definition")
            else:
                # Fallback to direct file update
                path = Path(file_path)
                if path_ops.validate_exists(path):
                    path_ops.safe_write(path, agent_content)
        except Exception as e:
            self.logger.error(f"AgentManager failed to update agent: {e}")
            # Fallback to direct file update
            path = Path(file_path)
            if path_ops.validate_exists(path):
                path_ops.safe_write(path, agent_content)

    async def _execute_agent_deletion(self, agent_name: str, file_path: str):
        """Execute agent deletion through AgentManager or fallback."""
        try:
            if self.agent_manager:
                success = await self._run_sync_in_executor(
                    self.agent_manager.delete_agent, agent_name
                )
                if not success:
                    raise Exception("AgentManager delete failed")
            else:
                # Fallback to direct file deletion
                path = Path(file_path)
                if path_ops.validate_exists(path):
                    path_ops.safe_delete(path)
        except Exception as e:
            self.logger.error(f"AgentManager failed to delete agent: {e}")
            # Fallback to direct file deletion
            path = Path(file_path)
            if path_ops.validate_exists(path):
                path_ops.safe_delete(path)

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
        self, agent_name: str, file_path: str
    ) -> Optional[str]:
        """Create backup before agent deletion."""
        try:
            source_path = Path(file_path)
            if not path_ops.validate_exists(source_path):
                return None

            backup_dir = get_path_manager().get_tracking_dir() / "backups"
            path_ops.ensure_dir(backup_dir)

            from datetime import datetime, timezone

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

    async def _create_agent_definition(
        self,
        agent_name: str,
        agent_content: str,
        tier: ModificationTier,
        agent_type: str,
        **kwargs,
    ) -> AgentDefinition:
        """Create an AgentDefinition from parameters."""
        # Import here to avoid circular dependency
        from claude_mpm.services.agents.deployment.agent_definition_factory import (
            AgentDefinitionFactory,
        )

        factory = AgentDefinitionFactory()
        return factory.create_agent_definition(
            agent_name, agent_content, tier, agent_type, **kwargs
        )

    async def _run_sync_in_executor(self, func, *args, **kwargs):
        """Run a synchronous function in an executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)

    def _update_metrics(self, result: LifecycleOperationResult):
        """Update performance metrics."""
        self.metrics["total_operations"] += 1

        if result.success:
            self.metrics["successful_operations"] += 1
        else:
            self.metrics["failed_operations"] += 1

        # Update average duration
        current_avg = self.metrics["average_duration_ms"]
        total_ops = self.metrics["total_operations"]
        self.metrics["average_duration_ms"] = (
            current_avg * (total_ops - 1) + result.duration_ms
        ) / total_ops

    def get_operation_history(
        self, agent_name: Optional[str] = None, limit: int = 100
    ) -> List[LifecycleOperationResult]:
        """Get operation history with optional filtering."""
        history = self.operation_history

        if agent_name:
            history = [op for op in history if op.agent_name == agent_name]

        return sorted(history, key=lambda x: x.duration_ms, reverse=True)[:limit]

    def get_active_operations(self) -> Dict[str, LifecycleOperation]:
        """Get currently active operations."""
        return self.active_operations.copy()

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return self.metrics.copy()

    async def _initialize(self) -> None:
        """Initialize the operation service."""
        self.logger.info("AgentOperationService initialized")

    async def _cleanup(self) -> None:
        """Cleanup the operation service."""
        # Wait for active operations to complete
        while self.active_operations:
            await asyncio.sleep(0.1)

        self.logger.info("AgentOperationService cleaned up")

    async def _health_check(self) -> Dict[str, bool]:
        """Perform health check."""
        return {
            "agent_manager_available": self.agent_manager is not None,
            "no_stuck_operations": len(self.active_operations) == 0,
        }
