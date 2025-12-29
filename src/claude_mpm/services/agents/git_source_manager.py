"""Git source manager for multi-repository agent sync and discovery."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.models.git_repository import GitRepository
from claude_mpm.services.agents.deployment.remote_agent_discovery_service import (
    RemoteAgentDiscoveryService,
)
from claude_mpm.services.agents.sources.git_source_sync_service import (
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
                       Defaults to ~/.claude-mpm/cache/agents/
        """
        if cache_root is None:
            cache_root = Path.home() / ".claude-mpm" / "cache" / "agents"

        self.cache_root = cache_root
        self.cache_root.mkdir(parents=True, exist_ok=True)

        # Bug #2 fix: Store repository metadata for source attribution
        # Maps repo_identifier -> {priority, url, ...}
        self._repo_metadata: Dict[str, Dict[str, Any]] = {}

        logger.info(f"GitSourceManager initialized with cache: {self.cache_root}")

    def sync_repository(
        self, repo: GitRepository, force: bool = False, show_progress: bool = True
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
            show_progress: Show ASCII progress bar during sync (default: True)

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

        # Bug #2 fix: Store repository metadata for later source attribution
        self._repo_metadata[repo.identifier] = {
            "priority": repo.priority,
            "url": repo.url,
            "subdirectory": repo.subdirectory,
            "enabled": repo.enabled,
        }

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

            # Sync agents with progress bar
            sync_results = sync_service.sync_agents(
                force_refresh=force, show_progress=show_progress
            )

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
        self,
        repos: List[GitRepository],
        force: bool = False,
        show_progress: bool = True,
    ) -> Dict[str, Dict[str, Any]]:
        """Sync multiple repositories.

        Syncs repositories in priority order (lower priority first).
        Individual failures don't stop overall sync.

        Args:
            repos: List of repositories to sync
            force: Force sync even if cache is fresh
            show_progress: Show ASCII progress bar during sync (default: True)

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
                result = self.sync_repository(
                    repo, force=force, show_progress=show_progress
                )
                results[repo.identifier] = result

            except Exception as e:
                logger.error(f"Exception syncing {repo.identifier}: {e}")
                results[repo.identifier] = {"synced": False, "error": str(e)}

        logger.info(
            f"Sync complete: {sum(1 for r in results.values() if r.get('synced'))} "
            f"succeeded, {sum(1 for r in results.values() if not r.get('synced'))} failed"
        )

        return results

    def _ensure_metadata_loaded(self) -> None:
        """Load repository metadata from configuration if not already loaded.

        Bug #2 fix: Ensures repository metadata (priority, URL) is available
        for source attribution even when list_cached_agents() is called
        without prior sync_repository() calls.

        Attempts to load from AgentSourceConfiguration and populates
        _repo_metadata dictionary with priority and URL for each repository.
        """
        # Skip if metadata already populated
        if self._repo_metadata:
            return

        try:
            from ...config.agent_sources import AgentSourceConfiguration

            config = AgentSourceConfiguration()
            sources = config.list_sources()

            for source in sources:
                # Source dict has: identifier, url, subdirectory, enabled, priority
                self._repo_metadata[source["identifier"]] = {
                    "priority": source.get("priority", 100),
                    "url": source.get("url", ""),
                    "subdirectory": source.get("subdirectory"),
                    "enabled": source.get("enabled", True),
                }

            logger.debug(f"Loaded metadata for {len(self._repo_metadata)} repositories")

        except Exception as e:
            logger.warning(f"Failed to load repository metadata from config: {e}")
            # Continue with empty metadata - will use defaults in _discover_agents_in_directory

    def list_cached_agents(
        self, repo_identifier: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all cached agents, optionally filtered by repository.

        Scans cache directories for agent markdown files and returns
        metadata for each discovered agent with source attribution.

        Bug #2 fix: Enriches agents with repository metadata (priority, URL)
        from stored configuration or attempts to load from config file.

        Args:
            repo_identifier: Optional repository filter (e.g., "owner/repo/agents")

        Returns:
            List of agent metadata dictionaries:
            [
                {
                    "name": "engineer",
                    "version": "2.5.0",
                    "path": "/cache/owner/repo/agents/engineer.md",
                    "repository": "owner/repo/agents",
                    "source": {
                        "identifier": "owner/repo/agents",
                        "priority": 100,
                        "url": "https://github.com/owner/repo"
                    }
                }
            ]

        Example:
            >>> agents = manager.list_cached_agents()
            >>> for agent in agents:
            ...     print(f"{agent['name']} v{agent['version']} from {agent['repository']}")
        """
        logger.debug(
            f"[DEBUG] list_cached_agents START: repo_identifier={repo_identifier}"
        )

        # Bug #2 fix: Load metadata from config if not already loaded
        logger.debug("[DEBUG] Calling _ensure_metadata_loaded()")
        self._ensure_metadata_loaded()
        logger.debug("[DEBUG] Metadata loaded successfully")

        agents = []

        # If repo_identifier specified, only scan that repository
        if repo_identifier:
            # Parse identifier to find cache path
            parts = repo_identifier.split("/")
            if len(parts) >= 2:
                cache_path = self.cache_root / "/".join(parts)

                if cache_path.exists():
                    metadata = self._repo_metadata.get(repo_identifier, {})
                    agents.extend(
                        self._discover_agents_in_directory(
                            cache_path, repo_identifier, metadata
                        )
                    )
        else:
            # Scan all cached repositories
            logger.debug("[DEBUG] Scanning all cached repositories")
            if not self.cache_root.exists():
                logger.debug(f"[DEBUG] Cache root doesn't exist: {self.cache_root}")
                return []

            # Walk cache directory structure
            logger.debug(f"[DEBUG] Walking cache root: {self.cache_root}")

            # Known legacy category directories to skip (flat cache structure)
            LEGACY_CATEGORIES = {
                "universal",
                "engineer",
                "ops",
                "qa",
                "security",
                "documentation",
                "claude-mpm",
            }

            # Repositories that are NOT agent repositories (should be excluded from agent discovery)
            # These contain skills, documentation, or other non-agent content
            EXCLUDED_REPOSITORIES = {
                "claude-mpm-skills",  # Skills repository, not agents
            }

            for owner_dir in self.cache_root.iterdir():
                if not owner_dir.is_dir():
                    continue

                # Skip legacy category directories (they're not GitHub owners)
                if owner_dir.name.lower() in LEGACY_CATEGORIES:
                    logger.debug(
                        f"[DEBUG] Skipping legacy category directory: {owner_dir.name}"
                    )
                    continue

                logger.debug(f"[DEBUG] Processing owner_dir: {owner_dir.name}")

                for repo_dir in owner_dir.iterdir():
                    if not repo_dir.is_dir():
                        continue

                    # Skip excluded repositories (e.g., skills repos are not agent repos)
                    if repo_dir.name in EXCLUDED_REPOSITORIES:
                        logger.debug(
                            f"[DEBUG] Skipping excluded repository: {repo_dir.name}"
                        )
                        continue

                    logger.debug(f"[DEBUG] Processing repo_dir: {repo_dir.name}")

                    # Bug #5 fix: Don't iterate subdirectories - RemoteAgentDiscoveryService
                    # now handles the /agents/ subdirectory internally (Bug #4 fix).
                    # Iterating subdirectories caused it to treat /agents/ hierarchy as
                    # separate repositories (engineer/backend, ops/tooling, etc.)
                    repo_id = f"{owner_dir.name}/{repo_dir.name}"
                    metadata = self._repo_metadata.get(repo_id, {})
                    logger.debug(f"[DEBUG] Discovering agents in repo root: {repo_id}")
                    agents.extend(
                        self._discover_agents_in_directory(repo_dir, repo_id, metadata)
                    )
                    logger.debug(f"[DEBUG] Found {len(agents)} agents so far")

        logger.debug(f"[DEBUG] list_cached_agents COMPLETE: {len(agents)} total agents (before deduplication)")

        # Deduplicate agents by agent_id (Bug #2 fix)
        # When same agent exists in multiple locations, keep only first occurrence
        seen_ids = set()
        deduplicated_agents = []

        for agent in agents:
            agent_id = agent.get("agent_id") or agent.get("metadata", {}).get("name")
            if agent_id and agent_id not in seen_ids:
                seen_ids.add(agent_id)
                deduplicated_agents.append(agent)
            elif agent_id:
                logger.debug(f"[DEBUG] Skipping duplicate agent: {agent_id}")

        logger.debug(f"[DEBUG] After deduplication: {len(deduplicated_agents)} unique agents")
        return deduplicated_agents

    def _discover_agents_in_directory(
        self,
        directory: Path,
        repo_identifier: str,
        repo_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Discover agents in a specific directory with source attribution.

        Bug #2 fix: Enriches agent metadata with source information including
        repository identifier, priority, and URL for proper attribution.

        Args:
            directory: Directory to scan
            repo_identifier: Repository identifier for metadata
            repo_metadata: Optional repository metadata (priority, URL, etc.)

        Returns:
            List of agent metadata dictionaries with source attribution
        """
        try:
            discovery_service = RemoteAgentDiscoveryService(directory)
            discovered = discovery_service.discover_remote_agents()

            # Default metadata if not provided
            if repo_metadata is None:
                repo_metadata = {}

            # Bug #2 fix: Enrich each agent with proper source attribution
            for agent in discovered:
                agent["repository"] = repo_identifier

                # Add source attribution at root level for CLI compatibility
                # source: repository identifier string
                # priority: numeric priority from config
                # source_url: full GitHub URL for reference
                if "source" not in agent or agent["source"] == "remote":
                    agent["source"] = repo_identifier
                agent["priority"] = repo_metadata.get("priority", 100)
                agent["source_url"] = repo_metadata.get("url", "")

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

    def list_cached_agents_with_filters(
        self,
        repo_identifier: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """List cached agents with optional filters.

        This method extends list_cached_agents() by adding semantic filtering
        based on AUTO-DEPLOY-INDEX.md categories. Filters are applied using
        the AutoDeployIndexParser to match agents by category, language,
        framework, platform, or specialization.

        Design Decision: Filter at application layer, not database layer

        Rationale: Agent discovery is file-based (no database), so filtering
        happens in-memory after discovery. For the expected dataset size
        (100-1000 agents), this performs well (~10-50ms).

        Trade-offs:
        - Simplicity: No query optimization needed, straightforward logic
        - Performance: Fast enough for CLI use case (< 100ms)
        - Scalability: May need optimization for 10K+ agents

        Args:
            repo_identifier: Filter by specific repository
            filters: Dict with optional keys:
                - category: str (e.g., "engineer/backend", "qa")
                - language: str (e.g., "python", "javascript")
                - framework: str (e.g., "react", "nextjs")
                - platform: str (e.g., "vercel", "gcp")
                - specialization: str (e.g., "data", "security")

        Returns:
            List of agent definitions with metadata:
            [
                {
                    "agent_id": "engineer/backend/python-engineer",
                    "name": "Python Engineer",
                    "version": "1.2.0",
                    "description": "...",
                    "source": "bobmatnyc/claude-mpm-agents",
                    "priority": 100,
                    "category": "engineer/backend",
                    "metadata": {...}
                }
            ]

        Example:
            >>> # Filter by category
            >>> agents = manager.list_cached_agents_with_filters(
            ...     filters={"category": "engineer/backend"}
            ... )
            >>> for agent in agents:
            ...     print(f"{agent['agent_id']} from {agent['source']}")

            >>> # Filter by language
            >>> agents = manager.list_cached_agents_with_filters(
            ...     filters={"language": "python"}
            ... )

            >>> # Multiple filters
            >>> agents = manager.list_cached_agents_with_filters(
            ...     filters={"category": "engineer/frontend", "framework": "react"}
            ... )
        """
        # Get all cached agents
        all_agents = self.list_cached_agents(repo_identifier)

        # If no filters, return all agents
        if not filters:
            return all_agents

        # Load AUTO-DEPLOY-INDEX.md parser
        from .auto_deploy_index_parser import AutoDeployIndexParser

        # Find AUTO-DEPLOY-INDEX.md in bobmatnyc/claude-mpm-agents cache
        index_path = (
            self.cache_root / "bobmatnyc" / "claude-mpm-agents" / "AUTO-DEPLOY-INDEX.md"
        )

        if not index_path.exists():
            logger.warning(f"AUTO-DEPLOY-INDEX.md not found at: {index_path}")
            logger.warning("Filtering by category/language/framework unavailable")
            # Return all agents if index not found
            return all_agents

        parser = AutoDeployIndexParser(index_path)

        # Build set of matching agent IDs based on filters
        matching_agent_ids = set()

        # Filter by category
        if "category" in filters:
            category = filters["category"]
            category_agents = parser.get_agents_by_category(category)
            matching_agent_ids.update(category_agents)
            logger.debug(
                f"Category '{category}': {len(category_agents)} matching agents"
            )

        # Filter by language
        if "language" in filters:
            language = filters["language"]
            lang_agents = parser.get_agents_by_language(language)
            lang_agent_ids = lang_agents.get("core", []) + lang_agents.get(
                "optional", []
            )
            if matching_agent_ids:
                # Intersection with previous filters
                matching_agent_ids &= set(lang_agent_ids)
            else:
                matching_agent_ids.update(lang_agent_ids)
            logger.debug(
                f"Language '{language}': {len(lang_agent_ids)} matching agents"
            )

        # Filter by framework
        if "framework" in filters:
            framework = filters["framework"]
            framework_agents = parser.get_agents_by_framework(framework)
            if matching_agent_ids:
                # Intersection with previous filters
                matching_agent_ids &= set(framework_agents)
            else:
                matching_agent_ids.update(framework_agents)
            logger.debug(
                f"Framework '{framework}': {len(framework_agents)} matching agents"
            )

        # Filter by platform
        if "platform" in filters:
            platform = filters["platform"]
            platform_agents = parser.get_agents_by_platform(platform)
            if matching_agent_ids:
                # Intersection with previous filters
                matching_agent_ids &= set(platform_agents)
            else:
                matching_agent_ids.update(platform_agents)
            logger.debug(
                f"Platform '{platform}': {len(platform_agents)} matching agents"
            )

        # Filter by specialization
        if "specialization" in filters:
            specialization = filters["specialization"]
            spec_agents = parser.get_agents_by_specialization(specialization)
            if matching_agent_ids:
                # Intersection with previous filters
                matching_agent_ids &= set(spec_agents)
            else:
                matching_agent_ids.update(spec_agents)
            logger.debug(
                f"Specialization '{specialization}': {len(spec_agents)} matching agents"
            )

        # Filter all_agents to only include matching IDs
        filtered_agents = []

        for agent in all_agents:
            # Extract agent_id from metadata or infer from path
            agent_id = agent.get("agent_id")

            if not agent_id:
                # Try to infer from metadata.name or source_file
                name = agent.get("metadata", {}).get("name", "")
                if name:
                    agent_id = name.lower().replace(" ", "-")

            # Check if agent matches filter
            if agent_id in matching_agent_ids:
                # Add source attribution
                agent["source"] = agent.get("repository", "unknown")

                # Add category if not present
                if "category" not in agent and "/" in agent_id:
                    agent["category"] = agent_id.rsplit("/", 1)[0]

                filtered_agents.append(agent)

        logger.info(
            f"Filtered {len(filtered_agents)} agents from {len(all_agents)} total"
        )

        return filtered_agents

    def __repr__(self) -> str:
        """Return string representation."""
        return f"GitSourceManager(cache_root='{self.cache_root}')"
