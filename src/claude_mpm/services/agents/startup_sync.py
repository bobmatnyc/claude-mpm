"""Agent Startup Synchronization Service.

Synchronizes agent templates from configured Git repositories on Claude MPM
startup using AgentSourceConfiguration and GitSourceManager.

Design Decision: Non-blocking startup integration

Rationale: Agent synchronization should not block Claude MPM startup.
Network failures or slow responses shouldn't prevent core functionality.
We log errors but continue with cached agents if sync fails.

Trade-offs:
- Reliability: Startup succeeds even if remote sync fails
- User Experience: No startup delays from network issues
- Freshness: May use stale agents if sync fails silently

Configuration Source:
- Reads from AgentSourceConfiguration (agent_sources.yaml)
- No longer depends on Config singleton or config["agent_sync"]
- GitSourceManager handles per-repository sync orchestration
"""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def sync_agents_on_startup(
    config: dict[str, Any] | None = None, force_refresh: bool = False
) -> dict[str, Any]:
    """Synchronize agents from remote Git sources on Claude MPM startup.

    Loads repository configuration from AgentSourceConfiguration and
    delegates multi-repository sync to GitSourceManager.

    Args:
        config: Deprecated. Kept for backward compatibility but ignored.
            Configuration is always loaded from AgentSourceConfiguration.
        force_refresh: Force download even if cache is fresh (bypasses ETag).

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

    if config is not None:
        import warnings

        warnings.warn(
            "The 'config' parameter to sync_agents_on_startup() is deprecated "
            "and will be removed in a future version. Configuration is now loaded "
            "from AgentSourceConfiguration (agent_sources.yaml).",
            DeprecationWarning,
            stacklevel=2,
        )

    start_time = time.time()

    result: dict[str, Any] = {
        "enabled": False,
        "sources_synced": 0,
        "total_downloaded": 0,
        "cache_hits": 0,
        "errors": [],
        "duration_ms": 0,
    }

    try:
        from claude_mpm.config.agent_sources import AgentSourceConfiguration
        from claude_mpm.services.agents.git_source_manager import GitSourceManager

        agent_config = AgentSourceConfiguration.load()
        enabled_repos = agent_config.get_enabled_repositories()

        if not enabled_repos:
            logger.debug("No enabled agent sources configured, skipping sync")
            return result

        result["enabled"] = True
        logger.info(f"Syncing {len(enabled_repos)} agent source(s)")

        manager = GitSourceManager()
        sync_results = manager.sync_all_repositories(
            repos=enabled_repos,
            force=force_refresh,
            show_progress=True,
        )

        # Aggregate per-repo results into return format
        for source_id, source_result in sync_results.items():
            if source_result.get("synced"):
                result["sources_synced"] += 1
                result["total_downloaded"] += source_result.get("files_updated", 0)
                result["cache_hits"] += source_result.get("files_cached", 0)
                logger.info(
                    f"Source {source_id}: "
                    f"{source_result.get('files_updated', 0)} downloaded, "
                    f"{source_result.get('files_cached', 0)} cached"
                )
            else:
                error = source_result.get("error", "Unknown error")
                result["errors"].append(f"Source {source_id}: {error}")
                logger.warning(f"Source {source_id}: sync failed - {error}")

    except Exception as e:
        error_msg = f"Agent sync failed: {e}"
        logger.error(error_msg)
        result["errors"].append(error_msg)

    finally:
        duration_ms = int((time.time() - start_time) * 1000)
        result["duration_ms"] = duration_ms

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


def get_sync_status() -> dict[str, Any]:
    """Get current agent synchronization status.

    Reads configuration from AgentSourceConfiguration to determine
    which repositories are enabled and their status.

    Returns:
        Dictionary with sync status:
        {
            "enabled": bool,
            "sources_configured": int,
            "cache_dir": str,
            "last_sync": Optional[str],  # ISO timestamp (placeholder)
        }

    Usage:
        Used by diagnostic tools and health checks to verify
        agent synchronization configuration.
    """
    try:
        from claude_mpm.config.agent_sources import AgentSourceConfiguration

        agent_config = AgentSourceConfiguration.load()
        enabled_repos = agent_config.get_enabled_repositories()

        return {
            "enabled": len(enabled_repos) > 0,
            "sources_configured": len(enabled_repos),
            "cache_dir": str(Path.home() / ".claude-mpm" / "cache" / "agents"),
            "last_sync": None,
        }

    except Exception as e:
        logger.error(f"Failed to get sync status: {e}")
        return {
            "enabled": False,
            "sources_configured": 0,
            "cache_dir": "~/.claude-mpm/cache/agents",
            "last_sync": None,
            "error": str(e),
        }
