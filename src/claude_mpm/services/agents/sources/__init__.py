"""Git source sync services for agent templates.

This module provides services for syncing agent templates from remote
Git repositories, with ETag-based caching for efficient updates and
SQLite-based state tracking.
"""

from claude_mpm.services.agents.sources.agent_sync_state import AgentSyncState
from claude_mpm.services.agents.sources.git_source_sync_service import (
    GitSourceSyncService,
)

__all__ = ["AgentSyncState", "GitSourceSyncService"]
