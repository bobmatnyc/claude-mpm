"""Agent sync orchestrator -- single entry-point for all sync callers.

Wraps GitSourceManager with consistent config resolution, error handling,
and result aggregation so that every call-site (startup, deploy, CLI, auto-
configure) uses the same logic.

Design Decision: The TTL gate is NOT in this class.
  TTL gating is a startup-specific concern and stays in startup.py.
  This orchestrator only cares about "sync these repos, return a result".

Phase 3 of Agent Pipeline Unification (1M-486).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Unified result dataclass returned by AgentSyncOrchestrator.sync().

    Attributes:
        enabled:          Whether any repositories were available to sync.
        sources_synced:   Number of repositories that synced successfully.
        sources_failed:   Number of repositories that failed to sync.
        total_downloaded: Total files downloaded (across all repos).
        cache_hits:       Total cache hits / 304s (across all repos).
        errors:           List of human-readable error strings.
        duration_ms:      Wall-clock time for the entire sync, in milliseconds.
        raw_results:      Per-repo dicts straight from GitSourceManager (for
                          callers that need the full detail).
    """

    enabled: bool = False
    sources_synced: int = 0
    sources_failed: int = 0
    total_downloaded: int = 0
    cache_hits: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0
    raw_results: dict[str, dict[str, Any]] = field(default_factory=dict)


class AgentSyncOrchestrator:
    """Single entry-point for agent repository synchronization.

    Usage::

        orch = AgentSyncOrchestrator(show_progress=True)
        result = orch.sync(force=True)        # sync all configured repos
        result = orch.sync(repos=[my_repo])    # sync specific repos only

    The class never raises -- it always returns a SyncResult (possibly with
    errors populated).
    """

    def __init__(
        self,
        show_progress: bool = True,
        source_config: Any | None = None,
    ) -> None:
        """Initialise the orchestrator.

        Args:
            show_progress: Whether to show progress bars during sync.
            source_config: An AgentSourceConfiguration instance.  If *None*,
                one is loaded lazily on the first call to :meth:`sync`.
        """
        self._show_progress = show_progress
        self._source_config = source_config

    # ------------------------------------------------------------------ #
    # Public API                                                            #
    # ------------------------------------------------------------------ #

    def sync(
        self,
        force: bool = False,
        repos: list[Any] | None = None,
    ) -> SyncResult:
        """Synchronise agent repositories and return a SyncResult.

        Args:
            force:  Bypass ETag / cache freshness checks.
            repos:  Explicit list of ``GitRepository`` objects to sync.
                    When *None*, all enabled repos from the source config
                    are used.

        Returns:
            A :class:`SyncResult` that is *never* an exception -- errors are
            captured inside the dataclass.
        """
        start = time.time()
        result = SyncResult()

        try:
            # Lazy-import to avoid circular imports at module level
            from claude_mpm.config.agent_sources import AgentSourceConfiguration
            from claude_mpm.services.agents.git_source_manager import GitSourceManager

            # Resolve repos
            if repos is None:
                config = self._source_config
                if config is None:
                    config = AgentSourceConfiguration.load()
                    self._source_config = config
                repos = config.get_enabled_repositories()

            if not repos:
                logger.debug("No enabled agent sources configured, skipping sync")
                result.duration_ms = int((time.time() - start) * 1000)
                return result

            result.enabled = True
            logger.info("Syncing %d agent source(s)", len(repos))

            manager = GitSourceManager()
            raw = manager.sync_all_repositories(
                repos=repos,
                force=force,
                show_progress=self._show_progress,
            )

            result.raw_results = raw

            # Aggregate per-repo results
            for source_id, source_result in raw.items():
                if source_result.get("synced"):
                    result.sources_synced += 1
                    result.total_downloaded += source_result.get("files_updated", 0)
                    result.cache_hits += source_result.get("files_cached", 0)
                    logger.info(
                        "Source %s: %d downloaded, %d cached",
                        source_id,
                        source_result.get("files_updated", 0),
                        source_result.get("files_cached", 0),
                    )
                else:
                    result.sources_failed += 1
                    error = source_result.get("error", "Unknown error")
                    result.errors.append(f"Source {source_id}: {error}")
                    logger.warning("Source %s: sync failed - %s", source_id, error)

        except Exception as exc:
            error_msg = f"Agent sync failed: {exc}"
            logger.error(error_msg)
            result.errors.append(error_msg)

        result.duration_ms = int((time.time() - start) * 1000)

        if result.enabled:
            if result.sources_synced > 0:
                logger.info(
                    "Agent sync complete: %d downloaded, %d cached in %dms",
                    result.total_downloaded,
                    result.cache_hits,
                    result.duration_ms,
                )
                if result.errors:
                    logger.warning("Agent sync had %d error(s)", len(result.errors))
            else:
                logger.debug("No agent sources synced")

        return result
