"""Git Source Sync Service for agent templates.

Syncs agent markdown files from remote Git repositories (GitHub) using
ETag-based caching and SQLite state tracking for efficient updates.
Implements Stage 1 of the three-stage sync algorithm:
- Check repository for updates using ETag headers
- Download agent files via raw.githubusercontent.com URLs
- Track content with SHA-256 hashes and sync history in SQLite
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

from claude_mpm.core.file_utils import get_file_hash

# Import normalize function for exclusion filtering
from claude_mpm.services.agents.deployment.multi_source_deployment_service import (
    _normalize_agent_name,
)
from claude_mpm.services.agents.sources.agent_sync_state import AgentSyncState
from claude_mpm.utils.progress import create_progress_bar

logger = logging.getLogger(__name__)


class GitSyncError(Exception):
    """Base exception for git sync errors."""


class NetworkError(GitSyncError):
    """Network/HTTP errors."""


class CacheError(GitSyncError):
    """Cache read/write errors."""


class ETagCache:
    """Manages ETag storage for efficient HTTP caching.

    Design Decision: Simple JSON file-based cache for ETag storage

    Rationale: ETags are small text strings that change infrequently.
    JSON provides human-readable format for debugging and is sufficient
    for this use case. Rejected SQLite as it adds complexity without
    significant benefits for this simple key-value storage.

    Trade-offs:
    - Simplicity: JSON is simple and debuggable
    - Performance: File I/O is fast enough for <100 ETags
    - Scalability: Limited to ~1000s of ETags before performance degrades

    Extension Points: Can be replaced with SQLite if ETag count exceeds
    performance threshold (>1000 agents syncing).
    """

    def __init__(self, cache_file: Path):
        """Initialize ETag cache.

        Args:
            cache_file: Path to JSON file storing ETags
        """
        self._cache_file = cache_file
        self._cache: Dict[str, Dict[str, Any]] = self._load_cache()

    def get_etag(self, url: str) -> Optional[str]:
        """Retrieve stored ETag for URL.

        Args:
            url: URL to look up ETag for

        Returns:
            ETag string or None if not found
        """
        entry = self._cache.get(url, {})
        return entry.get("etag")

    def set_etag(self, url: str, etag: str, file_size: Optional[int] = None):
        """Store ETag for URL.

        Args:
            url: URL to store ETag for
            etag: ETag value to store
            file_size: Optional file size in bytes
        """
        self._cache[url] = {
            "etag": etag,
            "last_modified": datetime.now(timezone.utc).isoformat(),
            "file_size": file_size,
        }
        self._save_cache()

    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        """Load ETag cache from JSON file.

        Returns:
            Dictionary mapping URLs to ETag metadata

        Error Handling:
        - FileNotFoundError: Returns empty dict (first run)
        - JSONDecodeError: Logs warning and returns empty dict
        - PermissionError: Logs error and returns empty dict
        """
        if not self._cache_file.exists():
            return {}

        try:
            with self._cache_file.open() as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"Invalid ETag cache file: {self._cache_file}, resetting")
            return {}
        except PermissionError as e:
            logger.error(f"Permission denied reading ETag cache: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error loading ETag cache: {e}")
            return {}

    def _save_cache(self):
        """Persist ETag cache to JSON file.

        Error Handling:
        - PermissionError: Logs error but doesn't raise (cache is optional)
        - IOError: Logs error but doesn't raise (graceful degradation)

        Failure Mode: If cache write fails, next sync will re-download
        all files (inefficient but correct behavior).
        """
        try:
            # Ensure parent directory exists
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)

            with self._cache_file.open("w") as f:
                json.dump(self._cache, f, indent=2)
        except PermissionError as e:
            logger.error(f"Permission denied writing ETag cache: {e}")
        except OSError as e:
            logger.error(f"IO error writing ETag cache: {e}")
        except Exception as e:
            logger.error(f"Error saving ETag cache: {e}")


class GitSourceSyncService:
    """Service for syncing agent templates from remote Git repositories.

    Design Decision: Use raw.githubusercontent.com URLs instead of Git API

    Rationale: Raw URLs bypass GitHub API rate limits (60/hour unauthenticated,
    5000/hour authenticated). For agent files, direct raw access is sufficient
    and more reliable. Rejected Git API because it requires base64 decoding
    and consumes rate limit unnecessarily.

    Trade-offs:
    - Performance: Raw URLs have no rate limit, instant access
    - Simplicity: Direct HTTP GET, no JSON parsing or base64 decoding
    - Discovery: Cannot auto-discover agent list (requires manifest or hardcoded)
    - Metadata: No commit info, file size, or last modified date

    Optimization Opportunities:
    1. Async Downloads: Use aiohttp for parallel agent downloads
       - Estimated speedup: 5-10x for initial sync (10 agents)
       - Effort: 4-6 hours, medium complexity
       - Threshold: Implement when agent count >20

    2. Manifest File: Add agents.json to repository for auto-discovery
       - Removes hardcoded agent list
       - Effort: 2 hours
       - Blocks: Requires repository write access

    Performance:
    - Time Complexity: O(n) where n = number of agents
    - Space Complexity: O(n) for in-memory agent content during sync
    - Expected Performance:
      * First sync (10 agents): ~5-10 seconds
      * Subsequent sync (no changes): ~1-2 seconds (ETag checks only)
      * Partial update (2 of 10 changed): ~2-3 seconds
    """

    def __init__(
        self,
        source_url: str = "https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main/agents",
        cache_dir: Optional[Path] = None,
        source_id: str = "github-remote",
    ):
        """Initialize Git source sync service.

        Args:
            source_url: Base URL for raw files (without trailing slash)
            cache_dir: Local cache directory (defaults to ~/.claude-mpm/cache/agents/)
            source_id: Unique identifier for this source (for multi-source support)

        Design Decision: Cache to ~/.claude-mpm/cache/agents/ (canonical location)

        Rationale: Separates cached repository structure from deployed agents.
        This allows preserving nested directory structure in cache while
        flattening for deployment. Enables multiple deployment targets
        (user, project) from single cache source.

        Trade-offs:
        - Storage: Uses 2x disk space (cache + deployment)
        - Performance: Copy operation on deployment (~10ms for 50 agents)
        - Flexibility: Supports project-specific deployments
        - Migration: Requires one-time migration from old cache location
        """
        self.source_url = source_url.rstrip("/")
        self.source_id = source_id

        # Setup cache directory (canonical: ~/.claude-mpm/cache/agents/)
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            # Default to ~/.claude-mpm/cache/agents/ (canonical cache location)
            home = Path.home()
            self.cache_dir = home / ".claude-mpm" / "cache" / "agents"

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Setup HTTP session with connection pooling
        self.session = requests.Session()
        self.session.headers["Accept"] = "text/plain"

        # Initialize SQLite state tracking (NEW)
        self.sync_state = AgentSyncState()

        # Register this source
        self.sync_state.register_source(
            source_id=self.source_id, url=self.source_url, enabled=True
        )

        # Initialize ETag cache (DEPRECATED - kept for backward compatibility)
        etag_cache_file = self.cache_dir / ".etag-cache.json"
        self.etag_cache = ETagCache(etag_cache_file)

        # Migrate old ETag cache to SQLite if it exists
        if etag_cache_file.exists():
            self._migrate_etag_cache(etag_cache_file)

        # NEW: Initialize git manager for cache (Phase 1 integration)
        from claude_mpm.services.agents.cache_git_manager import CacheGitManager

        self.git_manager = CacheGitManager(self.cache_dir)

    def sync_agents(
        self,
        force_refresh: bool = False,
        show_progress: bool = True,
        progress_prefix: str = "Syncing agents",
        progress_suffix: str = "agents",
    ) -> Dict[str, Any]:
        """Sync agents from remote Git repository with SQLite state tracking.

        Args:
            force_refresh: Force download even if cache is fresh (bypasses ETag)
            show_progress: Show ASCII progress bar during sync (default: True, auto-detects TTY)
            progress_prefix: Custom prefix for progress bar (default: "Syncing agents")
            progress_suffix: Custom suffix for completion message (default: "agents")

        Returns:
            Dictionary with sync results:
            {
                "synced": ["agent1.md", "agent2.md"],  # New downloads
                "cached": ["agent3.md"],                # ETag 304 responses
                "failed": [],                           # Failed downloads
                "total_downloaded": 2,
                "cache_hits": 1
            }

        Error Handling:
        - Network errors: Individual agent failures don't stop sync
        - Failed agents added to "failed" list
        - Returns partial success if some agents sync successfully
        """
        logger.info(f"Starting agent sync from {self.source_url}")
        logger.debug(f"Cache directory: {self.cache_dir}")
        logger.debug(f"Force refresh: {force_refresh}")

        start_time = time.time()

        # NEW: Pre-sync git operations (Phase 1 integration)
        if self.git_manager.is_git_repo():
            logger.debug("Cache is a git repository, checking for updates...")

            # Warn about uncommitted changes
            if self.git_manager.has_uncommitted_changes():
                uncommitted_count = len(
                    self.git_manager.get_status().get("uncommitted", [])
                )
                logger.warning(
                    f"Cache has {uncommitted_count} uncommitted change(s). "
                    "These will be preserved, but consider committing them."
                )

            # Pull latest if online (non-blocking)
            try:
                success, msg = self.git_manager.pull_latest()
                if success:
                    logger.info(f"✅ Git pull: {msg}")
                else:
                    logger.warning(f"⚠️  Git pull failed: {msg}")
                    logger.info("Continuing with HTTP sync as fallback")
            except Exception as e:
                logger.warning(f"Git pull error (continuing with HTTP sync): {e}")
        else:
            logger.debug("Cache is not a git repository, skipping git operations")

        results = {
            "synced": [],
            "cached": [],
            "failed": [],
            "total_downloaded": 0,
            "cache_hits": 0,
        }

        # Get list of agents to sync
        agent_list = self._get_agent_list()

        # Create progress bar if enabled
        progress_bar = None
        if show_progress:
            progress_bar = create_progress_bar(
                total=len(agent_list), prefix=progress_prefix
            )

        for idx, agent_filename in enumerate(agent_list, start=1):
            try:
                # Update progress bar with current file
                if progress_bar:
                    progress_bar.update(idx, message=agent_filename)

                url = f"{self.source_url}/{agent_filename}"
                content, status = self._fetch_with_etag(url, force_refresh)

                if status == 200:
                    # New content downloaded - save and track
                    self._save_to_cache(agent_filename, content)

                    # Track file with content hash in SQLite
                    cache_file = self.cache_dir / agent_filename
                    content_sha = get_file_hash(cache_file, algorithm="sha256")
                    if content_sha:
                        self.sync_state.track_file(
                            source_id=self.source_id,
                            file_path=agent_filename,
                            content_sha=content_sha,
                            local_path=str(cache_file),
                            file_size=len(content.encode("utf-8")),
                        )

                    results["synced"].append(agent_filename)
                    results["total_downloaded"] += 1
                    logger.debug(f"Downloaded: {agent_filename}")

                elif status == 304:
                    # Not modified - verify hash
                    cache_file = self.cache_dir / agent_filename
                    if cache_file.exists():
                        current_sha = get_file_hash(cache_file, algorithm="sha256")
                        if current_sha and self.sync_state.has_file_changed(
                            self.source_id, agent_filename, current_sha
                        ):
                            # Hash mismatch - re-download
                            logger.warning(
                                f"Hash mismatch for {agent_filename}, re-downloading"
                            )
                            content, _ = self._fetch_with_etag(url, force_refresh=True)
                            if content:
                                self._save_to_cache(agent_filename, content)
                                # Re-calculate and track hash
                                new_sha = get_file_hash(cache_file, algorithm="sha256")
                                if new_sha:
                                    self.sync_state.track_file(
                                        source_id=self.source_id,
                                        file_path=agent_filename,
                                        content_sha=new_sha,
                                        local_path=str(cache_file),
                                        file_size=len(content.encode("utf-8")),
                                    )
                                results["synced"].append(agent_filename)
                                results["total_downloaded"] += 1
                            else:
                                results["failed"].append(agent_filename)
                        else:
                            # Hash matches - true cache hit
                            results["cached"].append(agent_filename)
                            results["cache_hits"] += 1
                            logger.debug(f"Cache hit: {agent_filename}")
                    else:
                        # Cache file missing - re-download
                        logger.warning(
                            f"Cache file missing for {agent_filename}, re-downloading"
                        )
                        content, _ = self._fetch_with_etag(url, force_refresh=True)
                        if content:
                            self._save_to_cache(agent_filename, content)
                            # Track hash
                            current_sha = get_file_hash(cache_file, algorithm="sha256")
                            if current_sha:
                                self.sync_state.track_file(
                                    source_id=self.source_id,
                                    file_path=agent_filename,
                                    content_sha=current_sha,
                                    local_path=str(cache_file),
                                    file_size=len(content.encode("utf-8")),
                                )
                            results["synced"].append(agent_filename)
                            results["total_downloaded"] += 1
                        else:
                            results["failed"].append(agent_filename)

                else:
                    # Error status
                    logger.warning(f"Unexpected status {status} for {agent_filename}")
                    results["failed"].append(agent_filename)

            except requests.RequestException as e:
                logger.error(f"Network error downloading {agent_filename}: {e}")
                results["failed"].append(agent_filename)
                # Continue with other agents
            except Exception as e:
                logger.error(f"Unexpected error for {agent_filename}: {e}")
                results["failed"].append(agent_filename)

        # Record sync result in history
        duration_ms = int((time.time() - start_time) * 1000)
        status = (
            "success"
            if not results["failed"]
            else ("partial" if results["synced"] or results["cached"] else "error")
        )

        self.sync_state.record_sync_result(
            source_id=self.source_id,
            status=status,
            files_synced=results["total_downloaded"],
            files_cached=results["cache_hits"],
            files_failed=len(results["failed"]),
            duration_ms=duration_ms,
        )

        # Update source metadata
        self.sync_state.update_source_sync_metadata(source_id=self.source_id)

        # Finish progress bar with clear breakdown
        if progress_bar:
            downloaded = results["total_downloaded"]
            cached = results["cache_hits"]
            total = downloaded + cached
            failed_count = len(results["failed"])

            if failed_count > 0:
                progress_bar.finish(
                    message=f"Complete: {downloaded} downloaded, {cached} cached, {failed_count} failed ({total} total)"
                )
            # Show breakdown to clarify only changed files were downloaded
            elif cached > 0:
                progress_bar.finish(
                    message=f"Complete: {downloaded} downloaded, {cached} cached ({total} total)"
                )
            else:
                # All new downloads (first sync)
                progress_bar.finish(
                    message=f"Complete: {downloaded} {progress_suffix} downloaded"
                )

        # Log summary
        logger.info(
            f"Sync complete: {results['total_downloaded']} downloaded, "
            f"{results['cache_hits']} from cache, {len(results['failed'])} failed"
        )

        return results

    def check_for_updates(self) -> Dict[str, bool]:
        """Check if remote repository has updates using ETag.

        Uses HEAD requests to check ETags without downloading content.

        Returns:
            Dictionary mapping agent filenames to update status:
            {
                "research.md": True,   # Has updates
                "engineer.md": False,  # No updates (ETag matches)
            }

        Performance: ~1-2 seconds for 10 agents (HEAD requests only)
        """
        logger.info("Checking for agent updates")
        updates = {}

        agent_list = self._get_agent_list()

        for agent_filename in agent_list:
            try:
                url = f"{self.source_url}/{agent_filename}"
                cached_etag = self.etag_cache.get_etag(url)

                # Use HEAD request to check ETag without downloading
                response = self.session.head(url, timeout=30)

                if response.status_code == 200:
                    remote_etag = response.headers.get("ETag")
                    has_update = remote_etag != cached_etag
                    updates[agent_filename] = has_update

                    if has_update:
                        logger.info(f"Update available: {agent_filename}")
                else:
                    logger.warning(
                        f"Could not check {agent_filename}: HTTP {response.status_code}"
                    )
                    updates[agent_filename] = False

            except requests.RequestException as e:
                logger.error(f"Network error checking {agent_filename}: {e}")
                updates[agent_filename] = False

        return updates

    def download_agent_file(self, filename: str) -> Optional[str]:
        """Download single agent file with ETag caching.

        Args:
            filename: Agent filename (e.g., "research.md")

        Returns:
            Agent content as string, or None if download fails

        Error Handling:
        - Network errors: Returns None, logs error
        - 404 Not Found: Returns None, logs warning
        - Cache fallback: Attempts to load from cache on error
        """
        url = f"{self.source_url}/{filename}"

        try:
            content, status = self._fetch_with_etag(url)

            if status == 200:
                self._save_to_cache(filename, content)
                return content
            if status == 304:
                # Load from cache
                return self._load_from_cache(filename)
            logger.warning(f"HTTP {status} for {filename}")
            return None

        except requests.RequestException as e:
            logger.error(f"Network error downloading {filename}: {e}")
            # Try cache fallback
            return self._load_from_cache(filename)

    def _fetch_with_etag(
        self, url: str, force_refresh: bool = False
    ) -> Tuple[Optional[str], int]:
        """Fetch URL with ETag caching.

        Design Decision: Use If-None-Match header for conditional requests

        Rationale: ETag-based caching is standard HTTP pattern that GitHub
        supports. Reduces bandwidth by 95%+ for unchanged files. Alternative
        was Last-Modified timestamps, but ETags are more reliable for Git
        content (commit hash based).

        Args:
            url: URL to fetch
            force_refresh: Skip ETag check and force download

        Returns:
            Tuple of (content, status_code) where:
            - status_code 200: New content downloaded
            - status_code 304: Not modified (use cached)
            - content is None on 304

        Error Handling:
        - Timeout: 30 second timeout, raises requests.Timeout
        - Connection errors: Raises requests.ConnectionError
        - HTTP errors (4xx, 5xx): Returns (None, status_code)
        """
        headers = {}

        # Add ETag header if we have cached version and not forcing refresh
        if not force_refresh:
            cached_etag = self.etag_cache.get_etag(url)
            if cached_etag:
                headers["If-None-Match"] = cached_etag

        response = self.session.get(url, headers=headers, timeout=30)

        if response.status_code == 304:
            # Not modified - use cached version
            return None, 304

        if response.status_code == 200:
            # New content - update cache
            content = response.text
            etag = response.headers.get("ETag")
            if etag:
                file_size = len(content.encode("utf-8"))
                self.etag_cache.set_etag(url, etag, file_size)
            return content, 200

        # Error status
        return None, response.status_code

    def _save_to_cache(self, filename: str, content: str):
        """Save agent file to cache (Phase 1: preserves nested directory structure).

        Design Decision: Preserve nested directory structure in cache

        Rationale: Cache mirrors remote repository structure, allowing
        proper organization and future features (e.g., category browsing).
        Deployment layer flattens to .claude-mpm/agents/ for backward
        compatibility.

        Args:
            filename: Agent file path (may include directories, e.g., "engineer/core/engineer.md")
            content: File content

        Error Handling:
        - PermissionError: Logs error but doesn't raise
        - IOError: Logs error but doesn't raise

        Failure Mode: If cache write fails, agent is still synced in memory
        but will need re-download on next sync (graceful degradation).
        """
        try:
            cache_file = self.cache_dir / filename
            # Create parent directories for nested structure
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(content, encoding="utf-8")
            logger.debug(f"Saved to cache: {filename}")
        except PermissionError as e:
            logger.error(f"Permission denied writing {filename}: {e}")
        except OSError as e:
            logger.error(f"IO error writing {filename}: {e}")
        except Exception as e:
            logger.error(f"Error saving {filename} to cache: {e}")

    def _load_from_cache(self, filename: str) -> Optional[str]:
        """Load agent file from cache.

        Args:
            filename: Agent filename

        Returns:
            Cached content or None if not found

        Error Handling:
        - FileNotFoundError: Returns None (not in cache)
        - PermissionError: Logs error, returns None
        - IOError: Logs error, returns None
        """
        cache_file = self.cache_dir / filename

        if not cache_file.exists():
            logger.debug(f"No cached version of {filename}")
            return None

        try:
            content = cache_file.read_text(encoding="utf-8")
            logger.debug(f"Loaded from cache: {filename}")
            return content
        except PermissionError as e:
            logger.error(f"Permission denied reading {filename}: {e}")
            return None
        except OSError as e:
            logger.error(f"IO error reading {filename}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading {filename} from cache: {e}")
            return None

    def _get_agent_list(self) -> List[str]:
        """Get list of agent file paths to sync (including nested directories).

        Design Decision: Use Git Tree API instead of Contents API (Phase 1 fix)

        Rationale: Git Tree API with recursive=1 discovers entire repository
        structure in a single request, solving the "1 agent discovered" issue.
        Contents API only shows top-level files, missing nested directories.

        Trade-offs:
        - Performance: Single API call vs. 10-50+ recursive calls
        - Rate Limits: 1 request vs. dozens (avoids 403 errors)
        - Discovery: Finds ALL files in nested structure (50+ agents)
        - API Complexity: Requires commit SHA lookup before tree fetch

        Alternatives Considered:
        1. Contents API with recursion: 50+ API calls, hits rate limits
        2. Hardcoded nested paths: Misses new agents, unmaintainable
        3. Manifest file: Requires repository write access

        Error Handling:
        - Network errors: Falls back to static list
        - Rate limit exceeded: Falls back to static list
        - JSON parse errors: Falls back to static list

        Returns:
            List of agent file paths with directory structure
            (e.g., ["research.md", "engineer/core/engineer.md", ...])
        """
        # Extract repository info from source URL
        # URL format: https://raw.githubusercontent.com/owner/repo/branch/path
        try:
            # Parse GitHub URL to extract owner/repo/branch
            url_parts = self.source_url.replace(
                "https://raw.githubusercontent.com/", ""
            ).split("/")

            if len(url_parts) >= 3:
                owner = url_parts[0]
                repo = url_parts[1]
                branch = url_parts[2]
                base_path = "/".join(url_parts[3:]) if len(url_parts) > 3 else ""

                logger.debug(
                    f"Discovering agents from {owner}/{repo}/{branch} via Git Tree API"
                )

                # Use Git Tree API for recursive discovery
                agent_files = self._discover_agents_via_tree_api(
                    owner, repo, branch, base_path
                )

                if agent_files:
                    logger.info(
                        f"Discovered {len(agent_files)} agents via Git Tree API"
                    )
                    return sorted(agent_files)

                logger.warning("No agent files found via Tree API, using fallback list")

        except requests.RequestException as e:
            logger.warning(
                f"Network error fetching agent list from API: {e}, using fallback list"
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(
                f"Error parsing GitHub API response: {e}, using fallback list"
            )
        except Exception as e:
            logger.warning(
                f"Unexpected error fetching agent list: {e}, using fallback list"
            )

        # Fallback to known agent list if API fails
        logger.debug("Using fallback agent list")
        return [
            "research.md",
            "engineer.md",
            "qa.md",
            "documentation.md",
            "security.md",
            "ops.md",
            "ticketing.md",
            "product_owner.md",
            "version_control.md",
            "project_organizer.md",
        ]

    def _discover_agents_via_tree_api(
        self, owner: str, repo: str, branch: str, base_path: str = ""
    ) -> List[str]:
        """Discover all agent files using GitHub Git Tree API with recursion.

        Design Decision: Two-step Tree API pattern (commit SHA → tree)

        Rationale: Git Tree API requires commit SHA, not branch name.
        Step 1 resolves branch to SHA, Step 2 fetches recursive tree.
        This pattern is standard for GitHub API and handles branch
        references correctly.

        Algorithm:
        1. GET /repos/{owner}/{repo}/git/refs/heads/{branch} → commit SHA
        2. GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1 → all files
        3. Filter for .md/.json files in agents/ directory
        4. Exclude README.md and .gitignore

        Args:
            owner: GitHub owner (e.g., "bobmatnyc")
            repo: Repository name (e.g., "claude-mpm-agents")
            branch: Branch name (e.g., "main")
            base_path: Base path prefix to filter (e.g., "agents")

        Returns:
            List of agent file paths relative to base_path
            (e.g., ["research.md", "engineer/core/engineer.md"])

        Error Handling:
        - HTTP 404: Branch or repo not found, raises RequestException
        - HTTP 403: Rate limit exceeded, raises RequestException
        - Timeout: 30 second timeout, raises RequestException
        - Empty tree: Returns empty list (logged as warning)

        Performance:
        - Time: ~500-800ms for 50+ agents (2 API calls)
        - Rate Limit: Consumes 2 API calls per sync
        - Scalability: Handles repositories with 1000s of files
        """
        # Step 1: Get commit SHA for branch
        refs_url = (
            f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch}"
        )
        logger.debug(f"Fetching commit SHA from {refs_url}")

        refs_response = self.session.get(
            refs_url, headers={"Accept": "application/vnd.github+json"}, timeout=30
        )

        if refs_response.status_code == 403:
            logger.warning(
                "GitHub API rate limit exceeded (HTTP 403). "
                "Consider setting GITHUB_TOKEN environment variable."
            )
            raise requests.RequestException("Rate limit exceeded")

        refs_response.raise_for_status()
        commit_sha = refs_response.json()["object"]["sha"]
        logger.debug(f"Resolved {branch} to commit {commit_sha[:8]}")

        # Step 2: Get recursive tree for commit
        tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{commit_sha}"
        params = {"recursive": "1"}  # Recursively fetch all files

        logger.debug(f"Fetching recursive tree from {tree_url}")
        tree_response = self.session.get(
            tree_url,
            headers={"Accept": "application/vnd.github+json"},
            params=params,
            timeout=30,
        )
        tree_response.raise_for_status()

        tree_data = tree_response.json()
        all_items = tree_data.get("tree", [])

        logger.debug(f"Tree API returned {len(all_items)} total items")

        # Step 3: Filter for agent files
        agent_files = []
        for item in all_items:
            # Only process files (blobs), not directories (trees)
            if item["type"] != "blob":
                continue

            path = item["path"]

            # Filter for files in base_path (e.g., "agents/")
            if base_path and not path.startswith(base_path + "/"):
                continue

            # Exclude build/dist directories (prevents double-counting)
            # e.g., both "agents/engineer.md" and "dist/agents/engineer.md"
            path_parts = path.split("/")
            if any(excluded in path_parts for excluded in ["dist", "build", ".cache"]):
                continue

            # Remove base_path prefix for relative paths
            if base_path:
                relative_path = path[len(base_path) + 1 :]
            else:
                relative_path = path

            # Filter for .md or .json files, exclude README and .gitignore
            if (
                relative_path.endswith(".md") or relative_path.endswith(".json")
            ) and relative_path not in ["README.md", ".gitignore"]:
                agent_files.append(relative_path)

        logger.debug(f"Filtered to {len(agent_files)} agent files")
        return agent_files

    def _migrate_etag_cache(self, cache_file: Path):
        """Migrate old ETag cache to SQLite (one-time operation).

        Args:
            cache_file: Path to old JSON ETag cache file

        Error Handling:
        - Migration failures are logged but don't stop initialization
        - Old cache is renamed to .migrated to prevent re-migration
        """
        try:
            with cache_file.open() as f:
                old_cache = json.load(f)

            logger.info(f"Migrating {len(old_cache)} ETag entries to SQLite...")

            migrated = 0
            for url, metadata in old_cache.items():
                try:
                    etag = metadata.get("etag")
                    if etag:
                        # Store in new system
                        self.sync_state.update_source_sync_metadata(
                            source_id=self.source_id, etag=etag
                        )
                        migrated += 1
                except Exception as e:
                    logger.error(f"Failed to migrate {url}: {e}")

            # Rename old cache to prevent re-migration
            backup_file = cache_file.with_suffix(".json.migrated")
            cache_file.rename(backup_file)

            logger.info(
                f"ETag cache migration complete: {migrated} entries migrated, "
                f"old cache backed up to {backup_file.name}"
            )

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in ETag cache, skipping migration: {e}")
        except Exception as e:
            logger.error(f"Failed to migrate ETag cache: {e}")

    def get_cached_agents_dir(self) -> Path:
        """Get directory containing cached agent files.

        Returns:
            Path to cache directory for integration with MultiSourceAgentDeploymentService
        """
        return self.cache_dir

    def _cleanup_excluded_agents(
        self,
        deployment_dir: Path,
        excluded_set: Set[str],
    ) -> Dict[str, List[str]]:
        """Remove excluded agents from deployment directory.

        Removes any agents in the deployment directory whose normalized
        names match the exclusion list. This ensures that excluded agents
        are cleaned up from previous deployments.

        Args:
            deployment_dir: Directory containing deployed agents
            excluded_set: Set of normalized agent names to exclude

        Returns:
            Dictionary with cleanup results:
            - removed: List of agent names that were removed
        """
        cleanup_results: Dict[str, List[str]] = {"removed": []}

        if not deployment_dir.exists():
            logger.debug("Deployment directory does not exist, no cleanup needed")
            return cleanup_results

        for item in deployment_dir.iterdir():
            # Only process .md files
            if not item.is_file() or item.suffix != ".md":
                continue

            # Skip hidden files
            if item.name.startswith("."):
                continue

            # Normalize agent name for comparison
            agent_name = _normalize_agent_name(item.stem)

            # Check if this agent is excluded
            if agent_name in excluded_set:
                try:
                    item.unlink()
                    cleanup_results["removed"].append(item.stem)
                    logger.info(f"Removed excluded agent: {item.stem}")
                except PermissionError as e:
                    logger.error(f"Permission denied removing {item.stem}: {e}")
                except Exception as e:
                    logger.error(f"Failed to remove {item.stem}: {e}")

        # Log summary
        if cleanup_results["removed"]:
            logger.info(
                f"Cleanup complete: removed {len(cleanup_results['removed'])} excluded agents"
            )

        return cleanup_results

    def deploy_agents_to_project(
        self,
        project_dir: Path,
        agent_list: Optional[List[str]] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Deploy agents from cache to project directory (Phase 1 deployment).

        Design Decision: Copy from cache to project-specific deployment directory

        Rationale: Separates syncing (cache) from deployment (project-local).
        Allows multiple projects to use same cache with different agent
        configurations. Flattens nested structure for backward compatibility.

        Trade-offs:
        - Storage: 2x disk usage (cache + deployments)
        - Performance: Copy operation ~10ms for 50 agents
        - Isolation: Each project has independent agent set
        - Flexibility: Can deploy subset of cached agents per project

        Algorithm:
        1. Create deployment directory (.claude-mpm/agents/)
        2. Discover cached agents if list not provided
        3. For each agent, flatten path and copy to deployment
        4. Track deployment results (new, updated, skipped)

        Args:
            project_dir: Project root directory (e.g., /path/to/project)
            agent_list: Optional list of agent paths to deploy (uses all if None)
            force: Force redeployment even if up-to-date

        Returns:
            Dictionary with deployment results:
            {
                "deployed": ["engineer.md"],      # Newly deployed
                "updated": ["research.md"],       # Updated existing
                "skipped": ["qa.md"],             # Already up-to-date
                "failed": ["broken.md"],          # Copy failures
                "deployment_dir": "/path/.claude-mpm/agents"
            }

        Error Handling:
        - Missing cache files: Logged and added to "failed" list
        - Permission errors: Individual failures don't stop deployment
        - Directory creation: Creates deployment directory if missing

        Example:
            >>> service = GitSourceSyncService()
            >>> service.sync_agents()  # Sync to cache first
            >>> result = service.deploy_agents_to_project(Path("/my/project"))
            >>> print(f"Deployed {len(result['deployed'])} agents")
        """
        import shutil

        from claude_mpm.core.config import Config

        # Deploy to .claude/agents/ where Claude Code expects them
        deployment_dir = project_dir / ".claude" / "agents"
        deployment_dir.mkdir(parents=True, exist_ok=True)

        results = {
            "deployed": [],
            "updated": [],
            "skipped": [],
            "failed": [],
            "deployment_dir": str(deployment_dir),
        }

        # Load project config to get exclusion list
        config_file = project_dir / ".claude-mpm" / "configuration.yaml"
        if config_file.exists():
            config = Config(config_file=config_file)
            excluded_agents = config.get("excluded_agents", [])
        else:
            # No project config, no exclusions
            excluded_agents = []

        # Create normalized exclusion set
        excluded_set: Set[str] = (
            {_normalize_agent_name(name) for name in excluded_agents}
            if excluded_agents
            else set()
        )

        if excluded_set:
            logger.info(
                f"Applying exclusions: {', '.join(sorted(excluded_agents))} "
                f"(normalized: {', '.join(sorted(excluded_set))})"
            )

        # Get agents from cache or use provided list
        if agent_list is None:
            agent_list = self._discover_cached_agents()

        # Filter out excluded agents
        if excluded_set:
            original_count = len(agent_list)
            agent_list = [
                agent_path
                for agent_path in agent_list
                if _normalize_agent_name(Path(agent_path).stem) not in excluded_set
            ]
            filtered_count = original_count - len(agent_list)
            if filtered_count > 0:
                logger.info(f"Filtered out {filtered_count} excluded agents")

        # Clean up any previously deployed excluded agents
        if excluded_set:
            cleanup_results = self._cleanup_excluded_agents(
                deployment_dir, excluded_set
            )
            if cleanup_results["removed"]:
                logger.info(
                    f"Cleaned up {len(cleanup_results['removed'])} excluded agents: "
                    f"{', '.join(cleanup_results['removed'])}"
                )

        logger.info(
            f"Deploying {len(agent_list)} agents from cache to {deployment_dir}"
        )

        for agent_path in agent_list:
            try:
                cache_file = self.cache_dir / agent_path

                if not cache_file.exists():
                    logger.warning(f"Cache file not found: {agent_path}")
                    results["failed"].append(agent_path)
                    continue

                # Flatten nested path for deployment (engineer/core/engineer.md → engineer.md)
                deploy_filename = Path(agent_path).name
                deploy_file = deployment_dir / deploy_filename

                # Check if update needed (compare content, not just mtime)
                # DESIGN: Use content hash comparison for reliable change detection
                # Mtime comparison can fail when cache downloads have older timestamps
                should_deploy = force
                was_existing = deploy_file.exists()

                if not force and was_existing:
                    # Compare file contents using hash
                    cache_content = cache_file.read_bytes()
                    deploy_content = deploy_file.read_bytes()
                    should_deploy = cache_content != deploy_content

                if not should_deploy and was_existing:
                    results["skipped"].append(deploy_filename)
                    logger.debug(f"Skipped (up-to-date): {deploy_filename}")
                    continue

                # Copy from cache to deployment
                shutil.copy2(cache_file, deploy_file)

                # Track result
                if deploy_file.exists():
                    if was_existing:
                        results["updated"].append(deploy_filename)
                        logger.info(f"Updated: {deploy_filename}")
                    else:
                        results["deployed"].append(deploy_filename)
                        logger.info(f"Deployed: {deploy_filename}")
                else:
                    results["failed"].append(deploy_filename)
                    logger.error(f"Failed to deploy: {deploy_filename}")

            except PermissionError as e:
                logger.error(f"Permission denied deploying {agent_path}: {e}")
                results["failed"].append(Path(agent_path).name)
            except OSError as e:
                logger.error(f"IO error deploying {agent_path}: {e}")
                results["failed"].append(Path(agent_path).name)
            except Exception as e:
                logger.error(f"Unexpected error deploying {agent_path}: {e}")
                results["failed"].append(Path(agent_path).name)

        # Log summary
        total_success = len(results["deployed"]) + len(results["updated"])
        logger.info(
            f"Deployment complete: {total_success} deployed/updated, "
            f"{len(results['skipped'])} skipped, {len(results['failed'])} failed"
        )

        return results

    def _discover_cached_agents(self) -> List[str]:
        """Discover all agent files currently in cache.

        Scans cache directory for .md and .json files, preserving
        nested directory structure in returned paths.

        Returns:
            List of agent file paths relative to cache directory
            (e.g., ["research.md", "engineer/core/engineer.md"])

        Algorithm:
        1. Walk cache directory recursively
        2. Find all .md and .json files
        3. Convert to paths relative to cache root
        4. Filter out README.md and .gitignore
        """
        cached_agents = []

        if not self.cache_dir.exists():
            logger.warning(f"Cache directory does not exist: {self.cache_dir}")
            return []

        for file_path in self.cache_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in {".md", ".json"}:
                # Get relative path from cache directory
                relative_path = file_path.relative_to(self.cache_dir)
                relative_str = str(relative_path)

                # Exclude README and .gitignore
                if relative_str not in ["README.md", ".gitignore"]:
                    cached_agents.append(relative_str)

        logger.debug(f"Discovered {len(cached_agents)} cached agents")
        return sorted(cached_agents)
