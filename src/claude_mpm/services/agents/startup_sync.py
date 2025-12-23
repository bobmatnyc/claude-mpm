"""Agent Startup Synchronization Service.

Integrates GitSourceSyncService into Claude MPM's startup flow to ensure
agent templates are synchronized automatically on initialization.

Design Decision: Non-blocking startup integration

Rationale: Agent synchronization should not block Claude MPM startup.
Network failures or slow responses shouldn't prevent core functionality.
We log errors but continue with cached agents if sync fails.

Trade-offs:
- Reliability: Startup succeeds even if remote sync fails
- User Experience: No startup delays from network issues
- Freshness: May use stale agents if sync fails silently

Error Handling:
- Network errors: Logged as warnings, use cached agents
- Configuration errors: Logged and skipped
- Sync failures: Partial success is acceptable
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from claude_mpm.core.config import Config
from claude_mpm.services.agents.sources.git_source_sync_service import (
    GitSourceSyncService,
)

logger = logging.getLogger(__name__)


def sync_agents_on_startup(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Synchronize agents from remote sources on Claude MPM startup.

    Design Decision: Single-source support for Stage 1

    Rationale: Implementing multi-source support requires additional
    complexity (priority resolution, conflict handling, source management).
    Single-source (GitHub) is sufficient for initial deployment and
    provides immediate value. Multi-source support planned for ticket 1M-390.

    Args:
        config: Optional configuration dictionary. If None, loads from Config singleton.

    Returns:
        Dictionary with sync results:
        {
            "enabled": bool,           # Whether sync was enabled
            "sources_synced": int,     # Number of sources synced
            "total_downloaded": int,   # Total agents downloaded
            "cache_hits": int,         # Total cache hits
            "errors": [],              # List of error messages
            "duration_ms": int,        # Total sync duration
        }

    Error Handling:
    - Configuration errors: Returns error result, doesn't raise
    - Network errors: Logged, returns partial results
    - Source failures: Continue with other sources, log errors

    Performance:
    - Expected: 1-3 seconds for typical sync (10 agents, mostly cached)
    - First run: 5-10 seconds (download all agents)
    - All cached: <1 second (ETag checks only)
    """
    import time

    start_time = time.time()

    result = {
        "enabled": False,
        "sources_synced": 0,
        "total_downloaded": 0,
        "cache_hits": 0,
        "errors": [],
        "duration_ms": 0,
    }

    try:
        # Load configuration
        if config is None:
            config_obj = Config()
            config = config_obj.to_dict()

        # Get agent sync configuration
        agent_sync_config = config.get("agent_sync", {})

        # Check if agent sync is enabled
        if not agent_sync_config.get("enabled", True):
            logger.debug("Agent sync disabled in configuration")
            result["enabled"] = False
            return result

        result["enabled"] = True

        # Get sources list
        sources = agent_sync_config.get("sources", [])

        if not sources:
            logger.debug("No agent sources configured, skipping sync")
            return result

        # Get cache directory
        cache_dir = agent_sync_config.get("cache_dir")
        if cache_dir:
            cache_dir = Path(cache_dir).expanduser()
        else:
            cache_dir = None  # Will use default

        # Check for old cache directory names and provide migration guidance
        # This handles users upgrading from older versions
        old_cache_paths = [
            Path.home() / ".claude-mpm" / "cache" / "remote-agents",
        ]
        new_cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"

        for old_cache in old_cache_paths:
            if old_cache.exists() and not new_cache_dir.exists():
                logger.warning(f"Found old cache directory: {old_cache}")
                logger.warning(
                    "The cache directory location has changed to: ~/.claude-mpm/cache/agents"
                )
                logger.warning("To migrate your existing cache, run:")
                logger.warning(f"  mv {old_cache} {new_cache_dir}")
                logger.info(
                    "Agents will be re-synced to the new cache location automatically."
                )
                break  # Only show warning once

        # Sync each enabled source
        for source_config in sources:
            try:
                # Skip disabled sources
                if not source_config.get("enabled", True):
                    logger.debug(f"Skipping disabled source: {source_config.get('id')}")
                    continue

                source_id = source_config.get("id", "unknown")
                source_url = source_config.get("url")

                if not source_url:
                    logger.warning(f"Source {source_id} missing URL, skipping")
                    result["errors"].append(f"Source {source_id} missing URL")
                    continue

                logger.info(f"Syncing agents from source: {source_id}")

                # Create sync service for this source
                sync_service = GitSourceSyncService(
                    source_url=source_url,
                    cache_dir=cache_dir,
                    source_id=source_id,
                )

                # Perform sync
                sync_result = sync_service.sync_agents(force_refresh=False)

                # Aggregate results
                result["sources_synced"] += 1
                result["total_downloaded"] += sync_result.get("total_downloaded", 0)
                result["cache_hits"] += sync_result.get("cache_hits", 0)

                # Log any failures
                failed = sync_result.get("failed", [])
                if failed:
                    error_msg = (
                        f"Source {source_id} failed to sync {len(failed)} agents"
                    )
                    logger.warning(error_msg)
                    result["errors"].append(error_msg)

                logger.info(
                    f"Source {source_id}: {sync_result['total_downloaded']} downloaded, "
                    f"{sync_result['cache_hits']} cached"
                )

            except Exception as e:
                # Log error but continue with other sources
                error_msg = f"Failed to sync source {source_config.get('id')}: {e}"
                logger.error(error_msg)
                result["errors"].append(error_msg)
                continue

    except Exception as e:
        # Catch-all for unexpected errors
        error_msg = f"Agent sync failed: {e}"
        logger.error(error_msg)
        result["errors"].append(error_msg)

    finally:
        # Record duration
        duration_ms = int((time.time() - start_time) * 1000)
        result["duration_ms"] = duration_ms

        # Log summary
        if result["enabled"]:
            if result["sources_synced"] > 0:
                logger.info(
                    f"Agent sync complete: {result['total_downloaded']} downloaded, "
                    f"{result['cache_hits']} cached in {duration_ms}ms"
                )
                if result["errors"]:
                    logger.warning(f"Agent sync had {len(result['errors'])} errors")
            else:
                logger.debug("No agent sources synced")

    return result


def get_sync_status() -> Dict[str, Any]:
    """Get current agent synchronization status.

    Returns:
        Dictionary with sync status:
        {
            "enabled": bool,
            "sources_configured": int,
            "last_sync": Optional[str],  # ISO timestamp
            "cache_dir": str,
        }

    Usage:
        Used by diagnostic tools and health checks to verify
        agent synchronization configuration.
    """
    try:
        config = Config()
        agent_sync_config = config.get("agent_sync", {})

        sources = agent_sync_config.get("sources", [])
        enabled_sources = [s for s in sources if s.get("enabled", True)]

        status = {
            "enabled": agent_sync_config.get("enabled", True),
            "sources_configured": len(enabled_sources),
            "cache_dir": agent_sync_config.get(
                "cache_dir", "~/.claude-mpm/cache/agents"
            ),
        }

        # Try to get last sync timestamp from sync state
        # Future enhancement: Add get_last_sync_time() method to AgentSyncState
        # to retrieve most recent sync timestamp across all sources
        status["last_sync"] = None  # Placeholder for future implementation

        return status

    except Exception as e:
        logger.error(f"Failed to get sync status: {e}")
        return {
            "enabled": False,
            "sources_configured": 0,
            "cache_dir": "~/.claude-mpm/cache/agents",
            "last_sync": None,
            "error": str(e),
        }
