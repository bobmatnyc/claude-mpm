#!/usr/bin/env python3
"""
Agent State Service - State Management for Agent Lifecycle
===========================================================

Handles agent state tracking and transitions for the lifecycle manager.
Extracted from AgentLifecycleManager to follow Single Responsibility Principle.

Key Responsibilities:
- Track agent states (ACTIVE, MODIFIED, DELETED, etc.)
- Manage state transitions
- Validate state changes
- Maintain state history
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from claude_mpm.core.base_service import BaseService
from claude_mpm.services.agents.registry.modification_tracker import ModificationTier


class LifecycleState(Enum):
    """Agent lifecycle states."""

    ACTIVE = "active"
    MODIFIED = "modified"
    DELETED = "deleted"
    CONFLICTED = "conflicted"
    MIGRATING = "migrating"
    VALIDATING = "validating"


@dataclass
class AgentLifecycleRecord:
    """Complete lifecycle record for an agent."""

    agent_name: str
    current_state: LifecycleState
    tier: ModificationTier
    file_path: str
    created_at: float
    last_modified: float
    version: str
    modifications: List[str] = field(default_factory=list)  # Modification IDs
    persistence_operations: List[str] = field(default_factory=list)  # Operation IDs
    backup_paths: List[str] = field(default_factory=list)
    validation_status: str = "valid"
    validation_errors: List[str] = field(default_factory=list)
    metadata: Dict[str, any] = field(default_factory=dict)

    @property
    def age_days(self) -> float:
        """Get age in days."""
        return (time.time() - self.created_at) / (24 * 3600)

    @property
    def last_modified_datetime(self):
        """Get last modified as datetime."""
        from datetime import datetime

        return datetime.fromtimestamp(self.last_modified)


@dataclass
class StateTransition:
    """Record of a state transition."""

    agent_name: str
    from_state: LifecycleState
    to_state: LifecycleState
    timestamp: float
    reason: str
    metadata: Dict[str, any] = field(default_factory=dict)


class AgentStateService(BaseService):
    """
    Service for managing agent lifecycle states.

    Responsibilities:
    - Track current state of all agents
    - Validate and execute state transitions
    - Maintain state history
    - Query agents by state
    """

    def __init__(self):
        """Initialize the agent state service."""
        super().__init__("agent_state_service")

        # Agent records storage
        self.agent_records: Dict[str, AgentLifecycleRecord] = {}

        # State transition history
        self.transition_history: List[StateTransition] = []

        # Valid state transitions
        self.valid_transitions = {
            LifecycleState.ACTIVE: [
                LifecycleState.MODIFIED,
                LifecycleState.DELETED,
                LifecycleState.CONFLICTED,
                LifecycleState.MIGRATING,
                LifecycleState.VALIDATING,
            ],
            LifecycleState.MODIFIED: [
                LifecycleState.ACTIVE,
                LifecycleState.DELETED,
                LifecycleState.CONFLICTED,
                LifecycleState.VALIDATING,
            ],
            LifecycleState.DELETED: [
                LifecycleState.ACTIVE,  # For restoration
            ],
            LifecycleState.CONFLICTED: [
                LifecycleState.ACTIVE,
                LifecycleState.MODIFIED,
                LifecycleState.DELETED,
            ],
            LifecycleState.MIGRATING: [
                LifecycleState.ACTIVE,
                LifecycleState.MODIFIED,
                LifecycleState.CONFLICTED,
            ],
            LifecycleState.VALIDATING: [
                LifecycleState.ACTIVE,
                LifecycleState.MODIFIED,
                LifecycleState.CONFLICTED,
            ],
        }

        self.logger.info("AgentStateService initialized")

    def create_record(
        self,
        agent_name: str,
        tier: ModificationTier,
        file_path: str,
        initial_state: LifecycleState = LifecycleState.ACTIVE,
        version: str = "1.0.0",
        **metadata,
    ) -> AgentLifecycleRecord:
        """
        Create a new agent lifecycle record.

        Args:
            agent_name: Name of the agent
            tier: Agent tier (USER, PROJECT, SYSTEM)
            file_path: Path to agent file
            initial_state: Initial state (default: ACTIVE)
            version: Initial version
            **metadata: Additional metadata

        Returns:
            Created AgentLifecycleRecord
        """
        record = AgentLifecycleRecord(
            agent_name=agent_name,
            current_state=initial_state,
            tier=tier,
            file_path=file_path,
            created_at=time.time(),
            last_modified=time.time(),
            version=version,
            metadata=metadata,
        )

        self.agent_records[agent_name] = record
        self.logger.debug(f"Created lifecycle record for agent '{agent_name}'")

        return record

    def get_record(self, agent_name: str) -> Optional[AgentLifecycleRecord]:
        """Get lifecycle record for an agent."""
        return self.agent_records.get(agent_name)

    def update_state(
        self, agent_name: str, new_state: LifecycleState, reason: str = "", **metadata
    ) -> bool:
        """
        Update agent state with validation.

        Args:
            agent_name: Name of the agent
            new_state: Target state
            reason: Reason for transition
            **metadata: Additional metadata

        Returns:
            True if transition successful, False otherwise
        """
        record = self.agent_records.get(agent_name)
        if not record:
            self.logger.warning(f"Agent '{agent_name}' not found for state update")
            return False

        # Check if transition is valid
        if not self._is_valid_transition(record.current_state, new_state):
            self.logger.warning(
                f"Invalid state transition for '{agent_name}': "
                f"{record.current_state.value} -> {new_state.value}"
            )
            return False

        # Record transition
        transition = StateTransition(
            agent_name=agent_name,
            from_state=record.current_state,
            to_state=new_state,
            timestamp=time.time(),
            reason=reason,
            metadata=metadata,
        )
        self.transition_history.append(transition)

        # Update state
        old_state = record.current_state
        record.current_state = new_state
        record.last_modified = time.time()

        self.logger.info(
            f"Agent '{agent_name}' state changed: "
            f"{old_state.value} -> {new_state.value}"
        )

        return True

    def _is_valid_transition(
        self, from_state: LifecycleState, to_state: LifecycleState
    ) -> bool:
        """Check if a state transition is valid."""
        if from_state == to_state:
            return True  # Allow same state (no-op)

        valid_targets = self.valid_transitions.get(from_state, [])
        return to_state in valid_targets

    def list_agents_by_state(
        self, state: Optional[LifecycleState] = None
    ) -> List[AgentLifecycleRecord]:
        """
        List agents filtered by state.

        Args:
            state: State to filter by (None for all)

        Returns:
            List of matching agent records
        """
        agents = list(self.agent_records.values())

        if state:
            agents = [a for a in agents if a.current_state == state]

        return sorted(agents, key=lambda x: x.last_modified, reverse=True)

    def get_state_statistics(self) -> Dict[str, int]:
        """Get count of agents in each state."""
        stats = {}
        for record in self.agent_records.values():
            state_name = record.current_state.value
            stats[state_name] = stats.get(state_name, 0) + 1
        return stats

    def get_transition_history(
        self, agent_name: Optional[str] = None, limit: int = 100
    ) -> List[StateTransition]:
        """
        Get state transition history.

        Args:
            agent_name: Filter by agent name (None for all)
            limit: Maximum number of transitions to return

        Returns:
            List of state transitions
        """
        history = self.transition_history

        if agent_name:
            history = [t for t in history if t.agent_name == agent_name]

        # Return most recent first
        return sorted(history, key=lambda x: x.timestamp, reverse=True)[:limit]

    def update_record_metadata(self, agent_name: str, **metadata) -> bool:
        """
        Update metadata for an agent record.

        Args:
            agent_name: Name of the agent
            **metadata: Metadata to update

        Returns:
            True if successful, False if agent not found
        """
        record = self.agent_records.get(agent_name)
        if not record:
            return False

        record.metadata.update(metadata)
        record.last_modified = time.time()
        return True

    def increment_version(self, agent_name: str) -> Optional[str]:
        """
        Increment the patch version of an agent.

        Args:
            agent_name: Name of the agent

        Returns:
            New version string or None if agent not found
        """
        record = self.agent_records.get(agent_name)
        if not record:
            return None

        # Parse and increment version
        parts = record.version.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        record.version = ".".join(parts)
        record.last_modified = time.time()

        return record.version

    def add_modification(self, agent_name: str, modification_id: str) -> bool:
        """Add a modification ID to agent's history."""
        record = self.agent_records.get(agent_name)
        if not record:
            return False

        record.modifications.append(modification_id)
        record.last_modified = time.time()
        return True

    def add_persistence_operation(self, agent_name: str, operation_id: str) -> bool:
        """Add a persistence operation ID to agent's history."""
        record = self.agent_records.get(agent_name)
        if not record:
            return False

        record.persistence_operations.append(operation_id)
        record.last_modified = time.time()
        return True

    def add_backup_path(self, agent_name: str, backup_path: str) -> bool:
        """Add a backup path to agent's record."""
        record = self.agent_records.get(agent_name)
        if not record:
            return False

        record.backup_paths.append(backup_path)
        record.last_modified = time.time()
        return True

    def get_tier_statistics(self) -> Dict[str, int]:
        """Get count of agents in each tier."""
        stats = {}
        for record in self.agent_records.values():
            tier_name = record.tier.value
            stats[tier_name] = stats.get(tier_name, 0) + 1
        return stats

    async def _initialize(self) -> None:
        """Initialize the state service."""
        self.logger.info("AgentStateService initialized")

    async def _cleanup(self) -> None:
        """Cleanup the state service."""
        self.logger.info("AgentStateService cleaned up")

    async def _health_check(self) -> Dict[str, bool]:
        """Perform health check."""
        return {
            "records_loaded": len(self.agent_records) > 0,
            "transitions_valid": True,
        }
