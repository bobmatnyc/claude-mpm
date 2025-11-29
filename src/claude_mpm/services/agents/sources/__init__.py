"""Git source sync services for agent templates.

This module provides services for syncing agent templates from remote
Git repositories, with ETag-based caching for efficient updates.
"""

from claude_mpm.services.agents.sources.git_source_sync_service import (
    GitSourceSyncService,
)

__all__ = ["GitSourceSyncService"]
