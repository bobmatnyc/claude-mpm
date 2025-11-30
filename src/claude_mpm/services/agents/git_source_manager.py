"""Git source manager for multi-repository agent sync and discovery."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.claude_mpm.models.git_repository import GitRepository
from src.claude_mpm.services.agents.deployment.remote_agent_discovery_service import (
    RemoteAgentDiscoveryService,
)
from src.claude_mpm.services.agents.sources.git_source_sync_service import (
    GitSourceSyncService,
)

logger = logging.getLogger(__name__)


class GitSourceManager:
    """Manages Git repository sources for agents.

    This service coordinates syncing and discovery across multiple Git repositories.
    It handles:
    - Multi-repository sync with priority resolution
    - ETag-based incremental updates
    - Agent discovery from cached repositories
    - Priority-based agent resolution (lower priority = higher precedence)

    Design Decision: Composition over inheritance

    Rationale: GitSourceManager composes GitSourceSyncService and
    RemoteAgentDiscoveryService rather than inheriting. This provides
    better separation of concerns and makes it easier to test each
    component independently.

    Trade-offs:
    - Flexibility: Easy to swap implementations or mock for testing
    - Complexity: Slightly more code than inheritance
    - Maintainability: Clear boundaries between sync and discovery

    Example:
        >>> manager = GitSourceManager()
        >>> repo = GitRepository(url="https://github.com/owner/repo")
        >>> result = manager.sync_repository(repo)
        >>> agents = manager.list_cached_agents()
    """

    def __init__(self, cache_root: Optional[Path] = None):
        """Initialize Git source manager.

        Args:
            cache_root: Root directory for repository caches.
                       Defaults to ~/.claude-mpm/cache/remote-agents/
        """
        if cache_root is None:
            cache_root = Path.home() / ".claude-mpm" / "cache" / "remote-agents"

        self.cache_root = cache_root
        self.cache_root.mkdir(parents=True, exist_ok=True)

        logger.info(f"GitSourceManager initialized with cache: {self.cache_root}")

    def sync_repository(
        self, repo: GitRepository, force: bool = False
    ) -> Dict[str, Any]:
        """
        Sync a single repository from Git.

        This method:
        1. Creates a GitSourceSyncService for the repository
        2. Syncs agents using ETag-based caching (unless force=True)
        3. Discovers agents in the cached directory
        4. Returns sync results with metadata

        Args:
            repo: GitRepository to sync
            force: Force sync even if cache is fresh (bypasses ETag)

        Returns:
            Dictionary with sync results:
            {
                "synced": bool,              # Overall success
                "etag": str,                 # HTTP ETag from sync
                "files_updated": int,        # Files downloaded
                "files_added": int,          # New files
                "files_removed": int,        # Deleted files
                "files_cached": int,         # Cache hits (304)
                "agents_discovered": List[str],  # Agent names found
                "timestamp": str,            # ISO timestamp
                "error": str                 # Error message (if failed)
            }

        Example:
            >>> repo = GitRepository(url="https://github.com/owner/repo")
            >>> result = manager.sync_repository(repo)
            >>> if result["synced"]:
            ...     print(f"Synced {result['files_updated']} files")
        """
        logger.info(f"Syncing repository: {repo.identifier}")

        try:
            # Build source URL for raw GitHub content
            # Format: https://raw.githubusercontent.com/owner/repo/main/subdirectory
            owner, repo_name = repo._parse_github_url(repo.url)
            branch = "main"  # TODO: Make configurable

            if repo.subdirectory:
                subdirectory = repo.subdirectory.strip("/")
                source_url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/{branch}/{subdirectory}"
            else:
                source_url = (
                    f"https://raw.githubusercontent.com/{owner}/{repo_name}/{branch}"
                )

            # Initialize sync service
            sync_service = GitSourceSyncService(
                source_url=source_url,
                cache_dir=repo.cache_path,
                source_id=repo.identifier,
            )

            # Sync agents
            sync_results = sync_service.sync_agents(force_refresh=force)

            # Discover agents in cache
            discovery_service = RemoteAgentDiscoveryService(repo.cache_path)
            discovered_agents = discovery_service.discover_remote_agents()

            # Build result
            result = {
                "synced": True,
                "files_updated": sync_results.get("total_downloaded", 0),
                "files_added": len(sync_results.get("synced", [])),
                "files_removed": 0,  # TODO: Track deletions
                "files_cached": sync_results.get("cache_hits", 0),
                "agents_discovered": [
                    agent.get("metadata", {}).get(
                        "name", agent.get("agent_id", "unknown")
                    )
                    for agent in discovered_agents
                ],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(
                f"Sync complete: {result['files_updated']} updated, "
                f"{result['files_cached']} cached, "
                f"{len(result['agents_discovered'])} agents"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to sync {repo.identifier}: {e}")
            return {
                "synced": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def sync_all_repositories(
        self, repos: List[GitRepository], force: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """Sync multiple repositories.

        Syncs repositories in priority order (lower priority first).
        Individual failures don't stop overall sync.

        Args:
            repos: List of repositories to sync
            force: Force sync even if cache is fresh

        Returns:
            Dictionary mapping repository identifier to sync results:
            {
                "owner/repo/subdir": {...},
                "owner/repo2": {...}
            }

        Example:
            >>> repos = [
            ...     GitRepository(url="https://github.com/owner/repo1", priority=100),
            ...     GitRepository(url="https://github.com/owner/repo2", priority=50)
            ... ]
            >>> results = manager.sync_all_repositories(repos)
            >>> for repo_id, result in results.items():
            ...     print(f"{repo_id}: {'✓' if result['synced'] else '✗'}")
        """
        logger.info(f"Syncing {len(repos)} repositories")

        # Sort by priority (lower = higher precedence)
        sorted_repos = sorted(repos, key=lambda r: r.priority)

        results = {}

        for repo in sorted_repos:
            # Skip disabled repositories
            if not repo.enabled:
                logger.debug(f"Skipping disabled repository: {repo.identifier}")
                continue

            try:
                result = self.sync_repository(repo, force=force)
                results[repo.identifier] = result

            except Exception as e:
                logger.error(f"Exception syncing {repo.identifier}: {e}")
                results[repo.identifier] = {"synced": False, "error": str(e)}

        logger.info(
            f"Sync complete: {sum(1 for r in results.values() if r.get('synced'))} "
            f"succeeded, {sum(1 for r in results.values() if not r.get('synced'))} failed"
        )

        return results

    def list_cached_agents(
        self, repo_identifier: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all cached agents, optionally filtered by repository.

        Scans cache directories for agent markdown files and returns
        metadata for each discovered agent.

        Args:
            repo_identifier: Optional repository filter (e.g., "owner/repo/agents")

        Returns:
            List of agent metadata dictionaries:
            [
                {
                    "name": "engineer",
                    "version": "2.5.0",
                    "path": "/cache/owner/repo/agents/engineer.md",
                    "repository": "owner/repo/agents"
                }
            ]

        Example:
            >>> agents = manager.list_cached_agents()
            >>> for agent in agents:
            ...     print(f"{agent['name']} v{agent['version']} from {agent['repository']}")
        """
        agents = []

        # If repo_identifier specified, only scan that repository
        if repo_identifier:
            # Parse identifier to find cache path
            parts = repo_identifier.split("/")
            if len(parts) >= 2:
                cache_path = self.cache_root / "/".join(parts)

                if cache_path.exists():
                    agents.extend(
                        self._discover_agents_in_directory(cache_path, repo_identifier)
                    )
        else:
            # Scan all cached repositories
            if not self.cache_root.exists():
                return []

            # Walk cache directory structure
            for owner_dir in self.cache_root.iterdir():
                if not owner_dir.is_dir():
                    continue

                for repo_dir in owner_dir.iterdir():
                    if not repo_dir.is_dir():
                        continue

                    # Check for agents in repo root
                    repo_id = f"{owner_dir.name}/{repo_dir.name}"
                    agents.extend(self._discover_agents_in_directory(repo_dir, repo_id))

                    # Check for subdirectories
                    for subdir in repo_dir.iterdir():
                        if subdir.is_dir():
                            sub_repo_id = f"{repo_id}/{subdir.name}"
                            agents.extend(
                                self._discover_agents_in_directory(subdir, sub_repo_id)
                            )

        return agents

    def _discover_agents_in_directory(
        self, directory: Path, repo_identifier: str
    ) -> List[Dict[str, Any]]:
        """Discover agents in a specific directory.

        Args:
            directory: Directory to scan
            repo_identifier: Repository identifier for metadata

        Returns:
            List of agent metadata dictionaries
        """
        try:
            discovery_service = RemoteAgentDiscoveryService(directory)
            discovered = discovery_service.discover_remote_agents()

            # Add repository identifier to each agent
            for agent in discovered:
                agent["repository"] = repo_identifier

            return discovered

        except Exception as e:
            logger.warning(f"Failed to discover agents in {directory}: {e}")
            return []

    def get_agent_path(
        self, agent_name: str, repo_identifier: Optional[str] = None
    ) -> Optional[Path]:
        """Get cached path for a specific agent.

        Args:
            agent_name: Agent name (without .md extension)
            repo_identifier: Optional repository filter

        Returns:
            Path to cached agent file, or None if not found

        Example:
            >>> path = manager.get_agent_path("engineer")
            >>> if path:
            ...     print(f"Found: {path}")
        """
        agents = self.list_cached_agents(repo_identifier)

        for agent in agents:
            # Agent dict has metadata.name or agent_id
            name = agent.get("metadata", {}).get("name", "")
            agent_id = agent.get("agent_id", "")

            if name.lower().replace(" ", "-") == agent_name or agent_id == agent_name:
                return Path(agent.get("source_file", ""))

        return None

    def __repr__(self) -> str:
        """Return string representation."""
        return f"GitSourceManager(cache_root='{self.cache_root}')"
