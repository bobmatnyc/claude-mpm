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
    if config is not None:
        import warnings

        warnings.warn(
            "The 'config' parameter to sync_agents_on_startup() is deprecated "
            "and will be removed in a future version. Configuration is now loaded "
            "from AgentSourceConfiguration (agent_sources.yaml).",
            DeprecationWarning,
            stacklevel=2,
        )

    # Delegate to AgentSyncOrchestrator (Phase 3 unification)
    from claude_mpm.services.agents.sync_orchestrator import AgentSyncOrchestrator

    orchestrator = AgentSyncOrchestrator(show_progress=True)
    sync_result = orchestrator.sync(force=force_refresh)

    # Return backward-compatible dict for existing callers
    return {
        "enabled": sync_result.enabled,
        "sources_synced": sync_result.sources_synced,
        "sources_failed": sync_result.sources_failed,
        "total_downloaded": sync_result.total_downloaded,
        "cache_hits": sync_result.cache_hits,
        "errors": sync_result.errors,
        "duration_ms": sync_result.duration_ms,
    }


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
