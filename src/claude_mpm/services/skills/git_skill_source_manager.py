"""Git source manager for multi-repository skill sync and discovery.

This module manages multiple Git-based skill sources with priority resolution.
It orchestrates syncing, caching, and discovery of skills from multiple repositories,
applying priority-based conflict resolution when skills have the same ID.

Design Decision: Reuse GitSourceSyncService for all Git operations

Rationale: The GitSourceSyncService provides robust ETag-based caching and
incremental updates for Git repositories. Rather than duplicating this logic,
we compose it and adapt for skills-specific discovery.

Trade-offs:
- Code Reuse: Leverage proven sync infrastructure
- Maintainability: Single source of truth for Git operations
- Flexibility: Easy to extend with skills-specific features
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Set, Tuple

from claude_mpm.config.skill_sources import SkillSource, SkillSourceConfiguration
from claude_mpm.core.logging_config import get_logger
from claude_mpm.services.agents.sources.git_source_sync_service import (
    GitSourceSyncService,
)
from claude_mpm.services.skills.skill_discovery_service import SkillDiscoveryService

logger = get_logger(__name__)


class GitSkillSourceManager:
    """Manages multiple Git-based skill sources with priority resolution.

    Responsibilities:
        - Coordinate syncing of multiple skill repositories
        - Apply priority-based resolution for duplicate skills
        - Provide unified catalog of available skills
        - Handle caching and updates

    Priority Resolution:
        - Lower priority number = higher precedence
        - Priority 0 reserved for system repository
        - Skills with same ID: lowest priority wins

    Design Pattern: Orchestrator with Dependency Injection

    This class orchestrates multiple services (sync, discovery) without
    reimplementing their logic. Services can be injected for testing.

    Example:
        >>> config = SkillSourceConfiguration()
        >>> manager = GitSkillSourceManager(config)
        >>> results = manager.sync_all_sources()
        >>> skills = manager.get_all_skills()
    """

    def __init__(
        self,
        config: SkillSourceConfiguration,
        cache_dir: Optional[Path] = None,
        sync_service: Optional[GitSourceSyncService] = None,
    ):
        """Initialize skill source manager.

        Args:
            config: Skill source configuration
            cache_dir: Cache directory (defaults to ~/.claude-mpm/cache/skills/)
            sync_service: Git sync service (injected for testing)
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".claude-mpm" / "cache" / "skills"

        self.config = config
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.sync_service = sync_service  # Use injected if provided
        self.logger = get_logger(__name__)
        self._etag_cache_lock = Lock()  # Thread-safe ETag cache operations

        self.logger.info(
            f"GitSkillSourceManager initialized with cache: {self.cache_dir}"
        )

    def sync_all_sources(
        self, force: bool = False, progress_callback=None
    ) -> Dict[str, Any]:
        """Sync all enabled skill sources.

        Syncs sources in priority order (lower priority first). Individual
        failures don't stop overall sync.

        Args:
            force: Force re-download even if cached
            progress_callback: Optional callback(increment: int) called for each file synced

        Returns:
            Dict with sync results for each source:
            {
                "synced_count": int,
                "failed_count": int,
                "total_files_updated": int,
                "total_files_cached": int,
                "sources": {
                    "source_id": {
                        "synced": bool,
                        "files_updated": int,
                        "skills_discovered": int,
                        "error": str (if failed)
                    }
                },
                "timestamp": str
            }

        Example:
            >>> manager = GitSkillSourceManager(config)
            >>> results = manager.sync_all_sources()
            >>> print(f"Synced {results['synced_count']} sources")
        """
        sources = self.config.get_enabled_sources()
        self.logger.info(f"Syncing {len(sources)} enabled skill sources")

        results = {
            "synced_count": 0,
            "failed_count": 0,
            "total_files_updated": 0,
            "total_files_cached": 0,
            "sources": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        for source in sources:
            try:
                result = self.sync_source(
                    source.id, force=force, progress_callback=progress_callback
                )
                results["sources"][source.id] = result

                if result.get("synced"):
                    results["synced_count"] += 1
                    results["total_files_updated"] += result.get("files_updated", 0)
                    results["total_files_cached"] += result.get("files_cached", 0)
                else:
                    results["failed_count"] += 1

            except Exception as e:
                self.logger.error(f"Exception syncing source {source.id}: {e}")
                results["sources"][source.id] = {"synced": False, "error": str(e)}
                results["failed_count"] += 1

        self.logger.info(
            f"Sync complete: {results['synced_count']} succeeded, "
            f"{results['failed_count']} failed"
        )

        return results

    def sync_source(
        self, source_id: str, force: bool = False, progress_callback=None
    ) -> Dict[str, Any]:
        """Sync a specific skill source.

        Design Decision: Recursive GitHub directory download for skills

        Rationale: Skills use nested directory structures (e.g., universal/collaboration/SKILL.md)
        unlike agents which are flat .md files. We need to recursively download the entire
        repository structure to discover all SKILL.md files.

        Approach: Use GitHub API to recursively discover all files, then download each via
        raw.githubusercontent.com with ETag caching for efficiency.

        Args:
            source_id: ID of source to sync
            force: Force re-download
            progress_callback: Optional callback(increment: int) called for each file synced

        Returns:
            Sync result dict:
            {
                "synced": bool,
                "files_updated": int,
                "files_cached": int,
                "skills_discovered": int,
                "timestamp": str,
                "error": str (if failed)
            }

        Raises:
            ValueError: If source_id not found

        Example:
            >>> manager = GitSkillSourceManager(config)
            >>> result = manager.sync_source("system")
            >>> print(f"Updated {result['files_updated']} files")
        """
        source = self.config.get_source(source_id)
        if not source:
            raise ValueError(f"Source not found: {source_id}")

        if not source.enabled:
            self.logger.warning(f"Source is disabled: {source_id}")
            return {"synced": False, "error": "Source is disabled"}

        self.logger.info(f"Syncing skill source: {source_id} ({source.url})")

        try:
            # Determine cache path for this source
            cache_path = self._get_source_cache_path(source)
            cache_path.mkdir(parents=True, exist_ok=True)

            # Recursively sync repository structure
            files_updated, files_cached = self._recursive_sync_repository(
                source, cache_path, force, progress_callback
            )

            # Discover skills in cache
            discovery_service = SkillDiscoveryService(cache_path)
            discovered_skills = discovery_service.discover_skills()

            # Build result
            result = {
                "synced": True,
                "files_updated": files_updated,
                "files_cached": files_cached,
                "skills_discovered": len(discovered_skills),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            self.logger.info(
                f"Sync complete for {source_id}: {result['files_updated']} updated, "
                f"{result['skills_discovered']} skills discovered"
            )

            return result

        except Exception as e:
            self.logger.error(f"Failed to sync source {source_id}: {e}")
            return {
                "synced": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def get_all_skills(self) -> List[Dict[str, Any]]:
        """Get all skills from all sources with priority resolution.

        Returns:
            List of resolved skill dicts, each containing:
            {
                "skill_id": str,
                "name": str,
                "description": str,
                "version": str,
                "tags": List[str],
                "agent_types": List[str],
                "content": str,
                "source_id": str,
                "source_priority": int,
                "source_file": str
            }

        Priority Resolution Algorithm:
            1. Load skills from all enabled sources
            2. Group by skill ID (name converted to ID)
            3. For each group, select skill with lowest priority
            4. Return deduplicated skill list

        Example:
            >>> manager = GitSkillSourceManager(config)
            >>> skills = manager.get_all_skills()
            >>> for skill in skills:
            ...     print(f"{skill['name']} from {skill['source_id']}")
        """
        sources = self.config.get_enabled_sources()

        if not sources:
            self.logger.warning("No enabled sources found")
            return []

        # Collect skills from all sources
        skills_by_source = {}

        for source in sources:
            try:
                cache_path = self._get_source_cache_path(source)
                if not cache_path.exists():
                    self.logger.debug(f"Cache not found for source: {source.id}")
                    continue

                discovery_service = SkillDiscoveryService(cache_path)
                source_skills = discovery_service.discover_skills()

                # Tag skills with source metadata
                for skill in source_skills:
                    skill["source_id"] = source.id
                    skill["source_priority"] = source.priority

                skills_by_source[source.id] = source_skills

            except Exception as e:
                self.logger.warning(f"Failed to discover skills from {source.id}: {e}")
                continue

        # Apply priority resolution
        resolved_skills = self._apply_priority_resolution(skills_by_source)

        self.logger.info(
            f"Discovered {len(resolved_skills)} skills from {len(skills_by_source)} sources"
        )

        return resolved_skills

    def get_skills_by_source(self, source_id: str) -> List[Dict[str, Any]]:
        """Get skills from a specific source.

        Args:
            source_id: ID of source to query

        Returns:
            List of skill dicts from that source

        Example:
            >>> manager = GitSkillSourceManager(config)
            >>> skills = manager.get_skills_by_source("system")
            >>> print(f"Found {len(skills)} system skills")
        """
        source = self.config.get_source(source_id)
        if not source:
            self.logger.warning(f"Source not found: {source_id}")
            return []

        cache_path = self._get_source_cache_path(source)
        if not cache_path.exists():
            self.logger.debug(f"Cache not found for source: {source_id}")
            return []

        try:
            discovery_service = SkillDiscoveryService(cache_path)
            skills = discovery_service.discover_skills()

            # Tag with source metadata
            for skill in skills:
                skill["source_id"] = source.id
                skill["source_priority"] = source.priority

            return skills

        except Exception as e:
            self.logger.error(f"Failed to discover skills from {source_id}: {e}")
            return []

    def _apply_priority_resolution(
        self, skills_by_source: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Apply priority resolution to skill list.

        Args:
            skills_by_source: Dict mapping source_id to skill list

        Returns:
            Deduplicated skill list with priority resolution applied

        Resolution Strategy:
            - Group skills by skill_id
            - For each group, select skill from source with lowest priority
            - If multiple skills have same priority, use first encountered

        Example:
            skills_by_source = {
                "system": [{"skill_id": "review", "source_priority": 0}],
                "custom": [{"skill_id": "review", "source_priority": 100}]
            }
            # Returns: skill from "system" (priority 0 < 100)
        """
        # Flatten skills from all sources
        all_skills = []
        for skills in skills_by_source.values():
            all_skills.extend(skills)

        if not all_skills:
            return []

        # Group by skill_id
        skills_by_id: Dict[str, List[Dict[str, Any]]] = {}
        for skill in all_skills:
            skill_id = skill.get("skill_id", skill.get("name", "unknown"))
            if skill_id not in skills_by_id:
                skills_by_id[skill_id] = []
            skills_by_id[skill_id].append(skill)

        # Select skill with lowest priority for each group
        resolved_skills = []
        for skill_id, skill_group in skills_by_id.items():
            # Sort by priority (ascending), take first
            skill_group_sorted = sorted(
                skill_group, key=lambda s: s.get("source_priority", 999)
            )
            selected_skill = skill_group_sorted[0]

            # Log if multiple versions exist
            if len(skill_group) > 1:
                sources = [s.get("source_id") for s in skill_group]
                self.logger.debug(
                    f"Skill '{skill_id}' found in multiple sources {sources}, "
                    f"using source '{selected_skill.get('source_id')}'"
                )

            resolved_skills.append(selected_skill)

        return resolved_skills

    def _recursive_sync_repository(
        self,
        source: SkillSource,
        cache_path: Path,
        force: bool = False,
        progress_callback=None,
    ) -> Tuple[int, int]:
        """Recursively sync entire GitHub repository structure to cache.

        Design Decision: Two-phase sync architecture (Phase 2 refactoring)

        Rationale: Separates syncing (to cache) from deployment (to project).
        Phase 1: Download ALL repository files to cache with Git Tree API
        Phase 2: Deploy selected skills from cache to project-specific locations

        This refactoring follows the agent sync pattern (git_source_sync_service.py)
        with cache-first architecture for multi-project support.

        Trade-offs:
        - Storage: 2x disk usage (cache + deployments) vs. direct deployment
        - Performance: Copy operation adds ~10ms, but enables offline deployment
        - Flexibility: Multiple projects can deploy from single cache
        - Isolation: Projects have independent skill sets from shared cache

        Args:
            source: SkillSource configuration
            cache_path: Local cache directory (structure preserved)
            force: Force re-download even if ETag cached
            progress_callback: Optional callback(absolute_position: int) for progress tracking

        Returns:
            Tuple of (files_updated, files_cached)

        Algorithm:
            1. Parse GitHub URL to extract owner/repo
            2. Discover ALL files via Git Tree API (recursive=1, single request)
            3. Filter for relevant files (.md, .json, .gitignore)
            4. Download each file to cache with ETag caching
            5. Call progress_callback with ABSOLUTE position (not increment)
            6. Preserve nested directory structure in cache

        Error Handling:
        - Invalid GitHub URL: Raises ValueError
        - Tree API failure: Returns 0, 0 (logged as warning)
        - Individual file failures: Logged but don't stop sync
        """
        # Parse GitHub URL
        url_parts = source.url.rstrip("/").replace(".git", "").split("github.com/")
        if len(url_parts) != 2:
            raise ValueError(f"Invalid GitHub URL: {source.url}")

        repo_path = url_parts[1].strip("/")
        owner_repo = "/".join(repo_path.split("/")[:2])

        # Step 1: Discover all files via GitHub Tree API (single request)
        # This discovers the COMPLETE repository structure (272 files for skills)
        all_files = self._discover_repository_files_via_tree_api(
            owner_repo, source.branch
        )

        if not all_files:
            self.logger.warning(f"No files discovered in repository: {source.url}")
            return 0, 0

        self.logger.info(
            f"Discovered {len(all_files)} files in {owner_repo}/{source.branch} via Tree API"
        )

        # Step 2: Filter to only download relevant files (markdown, JSON metadata)
        relevant_files = [
            f
            for f in all_files
            if f.endswith(".md") or f.endswith(".json") or f == ".gitignore"
        ]

        self.logger.info(
            f"Filtered to {len(relevant_files)} relevant files (.md, .json, .gitignore)"
        )

        # Step 3: Download files to cache with ETag caching (parallel)
        files_updated = 0
        files_cached = 0

        # Use ThreadPoolExecutor for parallel downloads (10 workers for optimal performance)
        # Trade-off: 10 workers balances speed (306 files in ~3-5s) vs. GitHub rate limits
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all download tasks
            future_to_file = {}
            for file_path in relevant_files:
                raw_url = f"https://raw.githubusercontent.com/{owner_repo}/{source.branch}/{file_path}"
                cache_file = cache_path / file_path
                future = executor.submit(
                    self._download_file_with_etag, raw_url, cache_file, force
                )
                future_to_file[future] = file_path

            # Process completed downloads as they finish
            completed = 0
            for future in as_completed(future_to_file):
                completed += 1
                try:
                    updated = future.result()
                    if updated:
                        files_updated += 1
                    else:
                        files_cached += 1
                except Exception as e:
                    file_path = future_to_file[future]
                    self.logger.warning(f"Failed to download {file_path}: {e}")

                # Call progress callback with ABSOLUTE position
                if progress_callback:
                    progress_callback(completed)

        self.logger.info(
            f"Repository sync complete: {files_updated} updated, "
            f"{files_cached} cached from {len(relevant_files)} files"
        )
        return files_updated, files_cached

    def _discover_repository_files_via_tree_api(
        self, owner_repo: str, branch: str
    ) -> List[str]:
        """Discover all files in repository using GitHub Git Tree API.

        Design Decision: Two-step Tree API pattern (Phase 2 refactoring)

        Rationale: Git Tree API with recursive=1 discovers entire repository
        structure in a SINGLE request, solving the "limited file discovery" issue.
        This is the same pattern used successfully in agent sync (Phase 1).

        Previous Issue: Contents API only showed top-level files, missing nested
        directories. This caused skills sync to discover only 1-2 files instead
        of 272 files in the repository.

        Trade-offs:
        - Performance: Single API call vs. 50+ recursive Contents API calls
        - Rate Limiting: 1 request vs. dozens (avoids 403 rate limit errors)
        - Discovery: Finds ALL 272 files in nested structure
        - API Complexity: Requires commit SHA lookup before tree fetch

        Algorithm (matches agents pattern from git_source_sync_service.py):
        1. GET /repos/{owner}/{repo}/git/refs/heads/{branch} → commit SHA
        2. GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1 → all files
        3. Filter for blobs (files), exclude trees (directories)
        4. Return complete file list

        Args:
            owner_repo: GitHub owner/repo (e.g., "bobmatnyc/claude-mpm-skills")
            branch: Branch name (e.g., "main")

        Returns:
            List of all file paths in repository
            (e.g., ["collections/toolchains/python/pytest.md", ...])

        Error Handling:
        - HTTP 404: Branch or repo not found, raises RequestException
        - HTTP 403: Rate limit exceeded (warns about GITHUB_TOKEN)
        - Timeout: 30 second timeout per request
        - Empty tree: Returns empty list (logged as warning)

        Performance:
        - Expected: ~500-800ms for 272 files (2 API calls)
        - Rate Limit: Consumes 2 API calls per sync
        - Scalability: Handles 1000s of files without truncation

        Example:
            >>> files = self._discover_repository_files_via_tree_api(
            ...     "bobmatnyc/claude-mpm-skills", "main"
            ... )
            >>> print(len(files))
            272  # Complete repository (not just top-level)
        """
        import requests

        all_files = []

        try:
            # Step 1: Get the latest commit SHA for the branch
            refs_url = (
                f"https://api.github.com/repos/{owner_repo}/git/refs/heads/{branch}"
            )
            self.logger.debug(f"Fetching commit SHA from {refs_url}")

            refs_response = requests.get(
                refs_url, headers={"Accept": "application/vnd.github+json"}, timeout=30
            )

            # Check for rate limiting
            if refs_response.status_code == 403:
                self.logger.warning(
                    "GitHub API rate limit exceeded (HTTP 403). "
                    "Consider setting GITHUB_TOKEN environment variable for higher limits."
                )
                raise requests.RequestException("Rate limit exceeded")

            refs_response.raise_for_status()
            commit_sha = refs_response.json()["object"]["sha"]
            self.logger.debug(f"Resolved {branch} to commit {commit_sha[:8]}")

            # Step 2: Get the tree for that commit (recursive=1 gets ALL files)
            tree_url = (
                f"https://api.github.com/repos/{owner_repo}/git/trees/{commit_sha}"
            )
            params = {"recursive": "1"}  # Recursively get entire tree

            self.logger.debug(f"Fetching recursive tree from {tree_url}")
            tree_response = requests.get(
                tree_url,
                headers={"Accept": "application/vnd.github+json"},
                params=params,
                timeout=30,
            )
            tree_response.raise_for_status()

            tree_data = tree_response.json()
            all_items = tree_data.get("tree", [])

            self.logger.debug(f"Tree API returned {len(all_items)} total items")

            # Step 3: Extract file paths (filter out directories)
            for item in all_items:
                if item["type"] == "blob":  # blob = file, tree = directory
                    all_files.append(item["path"])

            self.logger.info(
                f"Discovered {len(all_files)} files via Tree API in {owner_repo}/{branch}"
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to discover files via Tree API: {e}")
            # Fall back to empty list (sync will fail gracefully)
            return []
        except (KeyError, ValueError) as e:
            self.logger.error(f"Error parsing GitHub API response: {e}")
            return []

        return all_files

    def _download_file_with_etag(
        self, url: str, local_path: Path, force: bool = False
    ) -> bool:
        """Download file from URL with ETag caching (thread-safe).

        Args:
            url: Raw GitHub URL
            local_path: Local file path to save to
            force: Force download even if cached

        Returns:
            True if file was updated, False if cached
        """

        import json

        import requests

        # Create parent directory (thread-safe with exist_ok=True)
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Thread-safe ETag cache operations
        etag_cache_file = local_path.parent / ".etag_cache.json"

        # Read cached ETag (lock required for file read)
        with self._etag_cache_lock:
            etag_cache = {}
            if etag_cache_file.exists():
                try:
                    with open(etag_cache_file, encoding="utf-8") as f:
                        etag_cache = json.load(f)
                except Exception:
                    pass

            cached_etag = etag_cache.get(str(local_path))

        # Make conditional request (no lock needed - independent HTTP call)
        headers = {}
        if cached_etag and not force:
            headers["If-None-Match"] = cached_etag

        try:
            response = requests.get(url, headers=headers, timeout=30)

            # 304 Not Modified - use cached version
            if response.status_code == 304:
                self.logger.debug(f"Cache hit (ETag match): {local_path.name}")
                return False

            response.raise_for_status()

            # Download and save file (no lock needed - independent file write)
            local_path.write_bytes(response.content)

            # Save new ETag (lock required for cache file write)
            if "ETag" in response.headers:
                with self._etag_cache_lock:
                    # Re-read cache in case other threads updated it
                    if etag_cache_file.exists():
                        try:
                            with open(etag_cache_file, encoding="utf-8") as f:
                                etag_cache = json.load(f)
                        except Exception:
                            etag_cache = {}

                    etag_cache[str(local_path)] = response.headers["ETag"]
                    with open(etag_cache_file, "w", encoding="utf-8") as f:
                        json.dump(etag_cache, f, indent=2)

            self.logger.debug(f"Downloaded: {local_path.name}")
            return True

        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Failed to download {url}: {e}")
            return False

    def _build_raw_github_url(self, source: SkillSource) -> str:
        """Build raw GitHub URL for source.

        Args:
            source: SkillSource instance

        Returns:
            Raw GitHub content URL

        Example:
            >>> source = SkillSource(
            ...     id="system",
            ...     url="https://github.com/owner/repo",
            ...     branch="main"
            ... )
            >>> url = manager._build_raw_github_url(source)
            >>> print(url)
            'https://raw.githubusercontent.com/owner/repo/main'
        """
        # Parse GitHub URL to extract owner/repo
        url = source.url.rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]

        # Extract path components
        parts = url.split("github.com/")
        if len(parts) != 2:
            raise ValueError(f"Invalid GitHub URL: {source.url}")

        repo_path = parts[1].strip("/")
        owner_repo = "/".join(repo_path.split("/")[:2])

        return f"https://raw.githubusercontent.com/{owner_repo}/{source.branch}"

    def _get_source_cache_path(self, source: SkillSource) -> Path:
        """Get cache directory path for a source.

        Args:
            source: SkillSource instance

        Returns:
            Absolute path to cache directory

        Cache Structure:
            ~/.claude-mpm/cache/skills/{source_id}/

        Example:
            >>> source = SkillSource(id="system", ...)
            >>> path = manager._get_source_cache_path(source)
            >>> print(path)
            Path('/Users/user/.claude-mpm/cache/skills/system')
        """
        return self.cache_dir / source.id

    def deploy_skills_to_project(
        self,
        project_dir: Path,
        skill_list: Optional[List[str]] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Deploy skills from cache to project directory (Phase 2 deployment).

        Design Decision: Deploy from cache to project-specific directory

        Rationale: Follows agent deployment pattern (git_source_sync_service.py).
        Separates sync (cache) from deployment (project), enabling:
        - Multiple projects using same cached skills
        - Offline deployment from cache
        - Project-specific skill selection
        - Consistent two-phase architecture

        This complements deploy_skills() which deploys to global ~/.claude/skills/.
        This method deploys to project-local .claude-mpm/skills/ for project-specific
        skill management.

        Trade-offs:
        - Storage: 2x disk (cache + project deployments)
        - Performance: Copy ~10ms for 50 skills (negligible)
        - Flexibility: Project-specific skill sets from shared cache
        - Isolation: Projects don't affect each other

        Args:
            project_dir: Project root directory (e.g., /path/to/myproject)
            skill_list: Optional list of skill names to deploy (deploys all if None)
            force: Force redeployment even if up-to-date

        Returns:
            Dictionary with deployment results:
            {
                "deployed": ["skill1"],      # Newly deployed
                "updated": ["skill2"],        # Updated existing
                "skipped": ["skill3"],        # Already up-to-date
                "failed": [],                 # Copy failures
                "deployment_dir": "/path/.claude-mpm/skills"
            }

        Algorithm:
        1. Create .claude-mpm/skills/ in project directory
        2. Get all skills from cache (or use provided list)
        3. For each skill:
           a. Check if cache file exists
           b. Flatten nested path to deployment name
           c. Compare modification times (skip if up-to-date)
           d. Copy from cache to project
           e. Track result (deployed/updated/skipped/failed)
        4. Return deployment statistics

        Error Handling:
        - Missing cache files: Logged and added to "failed"
        - Permission errors: Individual failures don't stop deployment
        - Path validation: Security check prevents directory traversal

        Example:
            >>> manager = GitSkillSourceManager(config)
            >>> manager.sync_all_sources()  # Sync to cache first
            >>> result = manager.deploy_skills_to_project(Path("/my/project"))
            >>> print(f"Deployed {len(result['deployed'])} skills")
        """
        import shutil

        deployment_dir = project_dir / ".claude-mpm" / "skills"

        # Try to create deployment directory
        try:
            deployment_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            self.logger.error(f"Permission denied creating deployment directory: {e}")
            return {
                "deployed": [],
                "deployed_count": 0,
                "updated": [],
                "updated_count": 0,
                "skipped": [],
                "skipped_count": 0,
                "failed": [],
                "failed_count": 0,
                "deployment_dir": str(deployment_dir),
            }

        results = {
            "deployed": [],
            "updated": [],
            "skipped": [],
            "failed": [],
            "deployment_dir": str(deployment_dir),
        }

        # Get all skills from cache or use provided list
        if skill_list is None:
            all_skills = self.get_all_skills()
        else:
            # Filter skills by provided list
            all_skills = [
                s for s in self.get_all_skills() if s.get("name") in skill_list
            ]

        self.logger.info(
            f"Deploying {len(all_skills)} skills from cache to {deployment_dir}"
        )

        for skill in all_skills:
            skill_name = skill.get("name", "unknown")
            deployment_name = skill.get("deployment_name")
            source_file = skill.get("source_file")

            if not deployment_name or not source_file:
                self.logger.warning(
                    f"Skill {skill_name} missing deployment_name or source_file, skipping"
                )
                results["failed"].append(skill_name)
                continue

            try:
                source_path = Path(source_file)
                if not source_path.exists():
                    self.logger.warning(f"Cache file not found: {source_file}")
                    results["failed"].append(skill_name)
                    continue

                # Source is the entire skill directory (not just SKILL.md)
                source_dir = source_path.parent
                target_skill_dir = deployment_dir / deployment_name

                # Check if already deployed and up-to-date
                should_deploy = force
                was_existing = target_skill_dir.exists()

                if not force and was_existing:
                    # Compare modification times of SKILL.md files
                    source_mtime = source_path.stat().st_mtime
                    target_file = target_skill_dir / "SKILL.md"
                    if target_file.exists():
                        target_mtime = target_file.stat().st_mtime
                        should_deploy = source_mtime > target_mtime
                    else:
                        should_deploy = True

                if not should_deploy and was_existing:
                    results["skipped"].append(deployment_name)
                    self.logger.debug(f"Skipped (up-to-date): {deployment_name}")
                    continue

                # Security: Validate paths
                if not self._validate_safe_path(deployment_dir, target_skill_dir):
                    self.logger.error(f"Invalid target path: {target_skill_dir}")
                    results["failed"].append(skill_name)
                    continue

                # Remove existing if force or updating
                if target_skill_dir.exists():
                    if target_skill_dir.is_symlink():
                        self.logger.warning(f"Removing symlink: {target_skill_dir}")
                        target_skill_dir.unlink()
                    else:
                        shutil.rmtree(target_skill_dir)

                # Copy entire skill directory from cache
                shutil.copytree(source_dir, target_skill_dir)

                # Track result
                if was_existing:
                    results["updated"].append(deployment_name)
                    self.logger.info(f"Updated: {deployment_name}")
                else:
                    results["deployed"].append(deployment_name)
                    self.logger.info(f"Deployed: {deployment_name}")

            except PermissionError as e:
                self.logger.error(f"Permission denied deploying {skill_name}: {e}")
                results["failed"].append(skill_name)
            except OSError as e:
                self.logger.error(f"IO error deploying {skill_name}: {e}")
                results["failed"].append(skill_name)
            except Exception as e:
                self.logger.error(f"Unexpected error deploying {skill_name}: {e}")
                results["failed"].append(skill_name)

        # Log summary
        total_success = len(results["deployed"]) + len(results["updated"])
        self.logger.info(
            f"Deployment complete: {total_success} deployed/updated, "
            f"{len(results['skipped'])} skipped, {len(results['failed'])} failed"
        )

        # Return format matching agents deployment pattern
        return {
            "deployed": results["deployed"],
            "deployed_count": len(results["deployed"]),
            "updated": results["updated"],
            "updated_count": len(results["updated"]),
            "skipped": results["skipped"],
            "skipped_count": len(results["skipped"]),
            "failed": results["failed"],
            "failed_count": len(results["failed"]),
            "deployment_dir": results["deployment_dir"],
        }

    def deploy_skills(
        self,
        target_dir: Optional[Path] = None,
        force: bool = False,
        progress_callback=None,
        skill_filter: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:
        """Deploy skills from cache to target directory with flat structure.

        Flattens nested Git repository structure into Claude Code compatible
        flat directory structure. Each skill directory is copied with a
        hyphen-separated name derived from its path.

        Transformation Example:
            Cache: collaboration/dispatching-parallel-agents/SKILL.md
            Deploy: collaboration-dispatching-parallel-agents/SKILL.md

        Args:
            target_dir: Target deployment directory (default: ~/.claude/skills/)
            force: Overwrite existing skills
            progress_callback: Optional callback(increment: int) called for each skill deployed
            skill_filter: Optional set of skill names to deploy (selective deployment).
                         If None, deploys all skills. If provided, only deploys skills
                         whose name matches an entry in the filter set.

        Returns:
            Dict with deployment results:
            {
                "deployed_count": int,
                "skipped_count": int,
                "failed_count": int,
                "deployed_skills": List[str],
                "skipped_skills": List[str],
                "errors": List[str],
                "filtered_count": int  # Number of skills filtered out
            }

        Example:
            >>> manager = GitSkillSourceManager(config)
            >>> result = manager.deploy_skills()
            >>> print(f"Deployed {result['deployed_count']} skills")

            # Selective deployment based on agent requirements:
            >>> required = {"typescript-core", "react-patterns"}
            >>> result = manager.deploy_skills(skill_filter=required)
            >>> print(f"Deployed {result['deployed_count']} of {len(required)} required skills")
        """
        if target_dir is None:
            target_dir = Path.home() / ".claude" / "skills"

        target_dir.mkdir(parents=True, exist_ok=True)

        deployed = []
        skipped = []
        errors = []
        filtered_count = 0

        # Get all skills from all sources
        all_skills = self.get_all_skills()

        # Apply skill filter if provided (selective deployment)
        if skill_filter is not None:
            original_count = len(all_skills)
            # Normalize filter to lowercase for case-insensitive matching
            normalized_filter = {s.lower() for s in skill_filter}

            def matches_filter(deployment_name: str) -> bool:
                """Match using same fuzzy logic as ProfileManager.is_skill_enabled()"""
                deployment_lower = deployment_name.lower()

                # Exact match
                if deployment_lower in normalized_filter:
                    return True

                # Fuzzy match: check if deployment name ends with or contains short name
                # Example: "toolchains-python-frameworks-flask" matches "flask"
                for short_name in normalized_filter:
                    if deployment_lower.endswith(f"-{short_name}"):
                        return True
                    # Check if short name is contained as a segment
                    if f"-{short_name}-" in deployment_lower:
                        return True
                    if deployment_lower.startswith(f"{short_name}-"):
                        return True

                return False

            # Match against deployment_name using fuzzy matching
            all_skills = [
                s for s in all_skills if matches_filter(s.get("deployment_name", ""))
            ]
            filtered_count = original_count - len(all_skills)
            self.logger.info(
                f"Selective deployment: {len(all_skills)} of {original_count} skills "
                f"match agent requirements ({filtered_count} filtered out)"
            )

            # Cleanup: Remove skills from target directory that aren't in the filtered set
            # This ensures only the skills in the profile are deployed
            removed_skills = self._cleanup_unfiltered_skills(target_dir, all_skills)
            if removed_skills:
                self.logger.info(
                    f"Removed {len(removed_skills)} skills not in profile filter: {removed_skills}"
                )

        self.logger.info(
            f"Deploying {len(all_skills)} skills to {target_dir} (force={force})"
        )

        for idx, skill in enumerate(all_skills, start=1):
            skill_name = skill.get("name", "unknown")
            deployment_name = skill.get("deployment_name")

            if not deployment_name:
                self.logger.warning(
                    f"Skill {skill_name} missing deployment_name, skipping"
                )
                errors.append(f"{skill_name}: Missing deployment_name")
                if progress_callback:
                    progress_callback(idx)
                continue

            try:
                result = self._deploy_single_skill(
                    skill, target_dir, deployment_name, force
                )

                if result["deployed"]:
                    deployed.append(deployment_name)
                elif result["skipped"]:
                    skipped.append(deployment_name)

                if result["error"]:
                    errors.append(result["error"])

            except Exception as e:
                self.logger.error(f"Failed to deploy {skill_name}: {e}")
                errors.append(f"{skill_name}: {e}")

            # Call progress callback for each skill processed
            if progress_callback:
                progress_callback(idx)

        self.logger.info(
            f"Deployment complete: {len(deployed)} deployed, "
            f"{len(skipped)} skipped, {len(errors)} errors"
        )

        return {
            "deployed_count": len(deployed),
            "skipped_count": len(skipped),
            "failed_count": len(errors),
            "deployed_skills": deployed,
            "skipped_skills": skipped,
            "errors": errors,
            "filtered_count": filtered_count,
        }

    def _cleanup_unfiltered_skills(
        self, target_dir: Path, filtered_skills: List[Dict[str, Any]]
    ) -> List[str]:
        """Remove skills from target directory that aren't in the filtered skill list.

        Uses fuzzy matching to handle both exact deployment names and short skill names.
        For example:
        - "toolchains-python-frameworks-flask" (deployed dir) matches "flask" (filter)
        - "toolchains-elixir-frameworks-phoenix-liveview" matches "phoenix-liveview"

        Args:
            target_dir: Target deployment directory
            filtered_skills: List of skills that should remain deployed

        Returns:
            List of skill names that were removed
        """
        import shutil

        removed_skills = []

        # Build set of deployment names (exact matches)
        expected_deployments = {
            skill.get("deployment_name").lower()
            for skill in filtered_skills
            if skill.get("deployment_name")
        }

        # Build helper function for fuzzy matching (matches logic from deploy_skills)
        def should_keep_skill(deployed_dir_name: str) -> bool:
            """Check if deployed skill matches any expected deployment using fuzzy matching.

            Matches the same logic as matches_filter() in deploy_skills() at line 1053.
            """
            deployed_lower = deployed_dir_name.lower()

            # Exact match
            if deployed_lower in expected_deployments:
                return True

            # Fuzzy match: check if deployment name matches any short name pattern
            # Example: "toolchains-elixir-frameworks-phoenix-liveview" matches "phoenix-liveview"
            for expected_name in expected_deployments:
                # Suffix match: deployment ends with "-shortname"
                if deployed_lower.endswith(f"-{expected_name}"):
                    return True
                # Segment match: "-shortname-" appears in deployment
                if f"-{expected_name}-" in deployed_lower:
                    return True
                # Prefix match: deployment starts with "shortname-"
                if deployed_lower.startswith(f"{expected_name}-"):
                    return True

            return False

        # Check each directory in target_dir
        if not target_dir.exists():
            return removed_skills

        try:
            for item in target_dir.iterdir():
                # Skip files, only process directories
                if not item.is_dir():
                    continue

                # Skip hidden directories
                if item.name.startswith("."):
                    continue

                # Check if this skill directory should be kept (fuzzy matching)
                if not should_keep_skill(item.name):
                    try:
                        # Security: Validate path is within target_dir
                        if not self._validate_safe_path(target_dir, item):
                            self.logger.error(
                                f"Refusing to remove path outside target directory: {item}"
                            )
                            continue

                        # Remove the skill directory
                        if item.is_symlink():
                            item.unlink()
                        else:
                            shutil.rmtree(item)

                        removed_skills.append(item.name)
                        self.logger.info(f"Removed orphaned skill: {item.name}")

                    except Exception as e:
                        self.logger.warning(
                            f"Failed to remove skill directory {item.name}: {e}"
                        )

        except Exception as e:
            self.logger.error(f"Error during skill cleanup: {e}")

        return removed_skills

    def _deploy_single_skill(
        self, skill: Dict[str, Any], target_dir: Path, deployment_name: str, force: bool
    ) -> Dict[str, Any]:
        """Deploy a single skill with flattened directory name.

        Args:
            skill: Skill metadata dict
            target_dir: Target deployment directory
            deployment_name: Flattened deployment directory name
            force: Overwrite if exists

        Returns:
            Dict with deployed, skipped, error flags
        """
        import shutil

        source_file = Path(skill["source_file"])
        source_dir = source_file.parent

        target_skill_dir = target_dir / deployment_name

        # Check if already deployed
        if target_skill_dir.exists() and not force:
            self.logger.debug(f"Skipped {deployment_name} (already exists)")
            return {"deployed": False, "skipped": True, "error": None}

        # Security: Validate paths
        if not self._validate_safe_path(target_dir, target_skill_dir):
            return {
                "deployed": False,
                "skipped": False,
                "error": f"Invalid target path: {target_skill_dir}",
            }

        try:
            # Remove existing if force
            if target_skill_dir.exists():
                if target_skill_dir.is_symlink():
                    self.logger.warning(f"Removing symlink: {target_skill_dir}")
                    target_skill_dir.unlink()
                else:
                    shutil.rmtree(target_skill_dir)

            # Copy entire skill directory with all resources
            shutil.copytree(source_dir, target_skill_dir)

            self.logger.debug(
                f"Deployed {deployment_name} from {source_dir} to {target_skill_dir}"
            )
            return {"deployed": True, "skipped": False, "error": None}

        except Exception as e:
            return {
                "deployed": False,
                "skipped": False,
                "error": f"{deployment_name}: {e}",
            }

    def _validate_safe_path(self, base: Path, target: Path) -> bool:
        """Ensure target path is within base directory (security).

        Args:
            base: Base directory
            target: Target path to validate

        Returns:
            True if path is safe, False otherwise
        """
        try:
            target.resolve().relative_to(base.resolve())
            return True
        except ValueError:
            return False

    def __repr__(self) -> str:
        """Return string representation."""
        sources = self.config.load()
        enabled_count = len([s for s in sources if s.enabled])
        return (
            f"GitSkillSourceManager(cache='{self.cache_dir}', "
            f"sources={len(sources)}, enabled={enabled_count})"
        )
