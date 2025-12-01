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
from typing import Any, Dict, List, Optional, Tuple

import requests

from claude_mpm.core.file_utils import get_file_hash
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
            cache_dir: Local cache directory (defaults to ~/.claude-mpm/cache/remote-agents/)
            source_id: Unique identifier for this source (for multi-source support)
        """
        self.source_url = source_url.rstrip("/")
        self.source_id = source_id

        # Setup cache directory
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            # Default to ~/.claude-mpm/cache/remote-agents/
            home = Path.home()
            self.cache_dir = home / ".claude-mpm" / "cache" / "remote-agents"

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

        # Finish progress bar
        if progress_bar:
            success_count = results["total_downloaded"] + results["cache_hits"]
            failed_count = len(results["failed"])
            if failed_count > 0:
                progress_bar.finish(
                    message=f"Complete: {success_count} synced, {failed_count} failed"
                )
            else:
                progress_bar.finish(
                    message=f"Complete: {success_count} {progress_suffix} synced"
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
        """Save agent file to cache.

        Args:
            filename: Agent filename
            content: File content

        Error Handling:
        - PermissionError: Logs error but doesn't raise
        - IOError: Logs error but doesn't raise

        Failure Mode: If cache write fails, agent is still synced in memory
        but will need re-download on next sync (graceful degradation).
        """
        try:
            cache_file = self.cache_dir / filename
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
        """Get list of agent filenames to sync.

        Design Decision: Auto-discovery via GitHub API with fallback

        Rationale: GitHub API provides reliable directory listing. Rate limits
        are acceptable (60/hour unauthenticated, 5000/hour authenticated) for
        this operation. Using API allows discovering ALL agents automatically
        without manual maintenance of hardcoded list.

        Trade-offs:
        - Performance: One extra API call (~200-500ms) per sync operation
        - Rate Limits: Consumes 1 API call per sync (acceptable for infrequent syncs)
        - Reliability: Fallback to static list if API fails
        - Maintainability: No manual updates needed when agents are added/removed

        Alternatives Considered:
        1. Manifest file (agents.json): Requires repository write access
        2. Hardcoded list only: Misses new agents, requires code updates
        3. Web scraping HTML: Fragile, breaks when GitHub changes UI

        Error Handling:
        - Network errors: Falls back to static list
        - Rate limit exceeded: Falls back to static list
        - JSON parse errors: Falls back to static list

        Returns:
            List of agent filenames (e.g., ["research.md", "engineer.md", ...])
        """
        # Extract repository info from source URL
        # URL format: https://raw.githubusercontent.com/owner/repo/branch/path
        try:
            # Parse GitHub API URL from raw URL
            # raw.githubusercontent.com/owner/repo/branch/path -> api.github.com/repos/owner/repo/contents/path
            url_parts = self.source_url.replace(
                "https://raw.githubusercontent.com/", ""
            ).split("/")

            if len(url_parts) >= 3:
                owner = url_parts[0]
                repo = url_parts[1]
                branch = url_parts[2]
                path = "/".join(url_parts[3:]) if len(url_parts) > 3 else ""

                # Construct GitHub API URL
                api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
                if branch and branch != "main":
                    api_url += f"?ref={branch}"

                logger.debug(f"Fetching agent list from GitHub API: {api_url}")

                # Make API request with timeout
                # Override session's Accept header for API call (needs application/json)
                api_headers = {"Accept": "application/vnd.github+json"}
                response = self.session.get(api_url, headers=api_headers, timeout=10)

                if response.status_code == 200:
                    files = response.json()

                    # Filter for .md files, exclude README.md, only sync from /agents/ directory
                    agent_files = [
                        f["name"]
                        for f in files
                        if isinstance(f, dict)
                        and f.get("name", "").endswith(".md")
                        and f.get("name") != "README.md"
                        and f.get("type") == "file"
                        and f.get("path", "").startswith("agents/")
                    ]

                    if agent_files:
                        logger.info(
                            f"Discovered {len(agent_files)} agents via GitHub API"
                        )
                        # Sort for consistent ordering
                        return sorted(agent_files)
                    logger.warning("No agent files found via API, using fallback list")

                elif response.status_code == 403:
                    logger.warning(
                        "GitHub API rate limit exceeded (HTTP 403), using fallback list. "
                        "Consider setting GITHUB_TOKEN environment variable."
                    )
                else:
                    logger.warning(
                        f"GitHub API returned HTTP {response.status_code}, using fallback list"
                    )

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
