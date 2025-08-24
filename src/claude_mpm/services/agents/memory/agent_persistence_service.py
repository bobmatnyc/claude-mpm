#!/usr/bin/env python3
"""
Agent Persistence Service (Stub)
================================

WHY: This is a stub implementation to support the AgentLifecycleManager integration.
The actual persistence is now handled by AgentManager, but we maintain this interface
for backward compatibility.

DESIGN DECISION: Creating a minimal stub because:
- AgentManager handles the actual file persistence
- This maintains the existing API contract
- Allows for future extension if needed
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class PersistenceStrategy(Enum):
    """Agent persistence strategies."""

    USER_OVERRIDE = "user_override"
    PROJECT_SPECIFIC = "project_specific"
    SYSTEM_DEFAULT = "system_default"


class PersistenceOperation(Enum):
    """Persistence operation types."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    BACKUP = "backup"
    RESTORE = "restore"


@dataclass
class PersistenceRecord:
    """Record of a persistence operation."""

    operation_id: str
    operation_type: PersistenceOperation
    agent_name: str
    source_tier: Any
    target_tier: Optional[Any] = None
    strategy: Optional[PersistenceStrategy] = None
    success: bool = True
    timestamp: float = 0.0
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None


class AgentPersistenceService:
    """
    Stub implementation for agent persistence service.

    WHY: Maintains compatibility with AgentLifecycleManager while
    actual persistence is delegated to AgentManager.
    """

    async def start(self) -> None:
        """Start the persistence service."""
        # No-op for stub

    async def stop(self) -> None:
        """Stop the persistence service."""
        # No-op for stub

    async def persist_agent(
        self,
        agent_name: str,
        agent_content: str,
        source_tier: Any,
        target_tier: Optional[Any] = None,
        strategy: Optional[PersistenceStrategy] = None,
    ) -> PersistenceRecord:
        """
        Create a persistence record (actual persistence handled by AgentManager).

        WHY: This method exists for API compatibility but doesn't perform
        actual file operations since AgentManager handles that.
        """
        return PersistenceRecord(
            operation_id=f"persist_{agent_name}_{time.time()}",
            operation_type=PersistenceOperation.UPDATE,
            agent_name=agent_name,
            source_tier=source_tier,
            target_tier=target_tier or source_tier,
            strategy=strategy or PersistenceStrategy.USER_OVERRIDE,
            success=True,
            timestamp=time.time(),
        )
