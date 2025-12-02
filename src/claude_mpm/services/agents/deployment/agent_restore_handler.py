"""Agent restore handler for lifecycle manager.

This module provides agent restoration functionality for the AgentLifecycleManager.
Extracted to reduce complexity and improve maintainability.
"""

import time
from typing import TYPE_CHECKING, Optional

from claude_mpm.core.path_ops import path_ops

if TYPE_CHECKING:
    from .agent_lifecycle_manager import AgentLifecycleManager, LifecycleOperationResult


class AgentRestoreHandler:
    """Handles agent restoration operations."""

    def __init__(self, lifecycle_manager: "AgentLifecycleManager"):
        """Initialize the restore handler."""
        self.lifecycle_manager = lifecycle_manager
        self.logger = lifecycle_manager.logger

    async def restore_agent(
        self, agent_name: str, backup_path: Optional[str] = None
    ) -> "LifecycleOperationResult":
        """Restore agent from backup."""
        from .agent_lifecycle_manager import (
            LifecycleOperation,
            LifecycleOperationResult,
        )

        start_time = time.time()

        try:
            record = self.lifecycle_manager.agent_records.get(agent_name)
            if not record:
                return LifecycleOperationResult(
                    operation=LifecycleOperation.RESTORE,
                    agent_name=agent_name,
                    success=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error_message="Agent record not found",
                )

            # Use latest backup if not specified
            if not backup_path and record.backup_paths:
                backup_path = record.backup_paths[-1]

            if not backup_path or not path_ops.validate_exists(backup_path):
                return LifecycleOperationResult(
                    operation=LifecycleOperation.RESTORE,
                    agent_name=agent_name,
                    success=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error_message="No valid backup found",
                )

            # Read backup content
            backup_content = path_ops.safe_read(backup_path)
            if not backup_content:
                return LifecycleOperationResult(
                    operation=LifecycleOperation.RESTORE,
                    agent_name=agent_name,
                    success=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error_message="Failed to read backup content",
                )

            # Restore via update operation
            return await self.lifecycle_manager.update_agent(
                agent_name=agent_name,
                agent_content=backup_content,
                restored_from=backup_path,
            )

        except Exception as e:
            return LifecycleOperationResult(
                operation=LifecycleOperation.RESTORE,
                agent_name=agent_name,
                success=False,
                duration_ms=(time.time() - start_time) * 1000,
                error_message=str(e),
            )
