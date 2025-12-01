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

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
        """Recursively sync entire GitHub repository structure.

        Discovers all files in repository via GitHub API and downloads them
        via raw.githubusercontent.com with ETag caching.

        Args:
            source: SkillSource configuration
            cache_path: Local cache directory
            force: Force re-download even if cached
            progress_callback: Optional callback(increment: int) called for each file synced

        Returns:
            Tuple of (files_updated, files_cached)

        Algorithm:
            1. Discover all files recursively via GitHub API
            2. For each file, download if needed (check ETag)
            3. Call progress_callback for each file processed
            4. Return update statistics
        """
        # Parse GitHub URL
        url_parts = source.url.rstrip("/").replace(".git", "").split("github.com/")
        if len(url_parts) != 2:
            raise ValueError(f"Invalid GitHub URL: {source.url}")

        repo_path = url_parts[1].strip("/")
        owner_repo = "/".join(repo_path.split("/")[:2])

        # Step 1: Discover all files via GitHub Tree API (single request)
        # This avoids rate limiting issues with recursive Contents API calls
        all_files = self._discover_repository_files_via_tree_api(
            owner_repo, source.branch
        )

        if not all_files:
            self.logger.warning(f"No files discovered in repository: {source.url}")
            return 0, 0

        self.logger.info(
            f"Discovered {len(all_files)} files in {owner_repo}/{source.branch}"
        )

        # Step 2: Download files
        files_updated = 0
        files_cached = 0

        # Filter to only download relevant files (markdown, JSON metadata)
        relevant_files = [
            f
            for f in all_files
            if f.endswith(".md") or f.endswith(".json") or f == ".gitignore"
        ]

        for file_path in relevant_files:
            # Build raw GitHub URL
            raw_url = f"https://raw.githubusercontent.com/{owner_repo}/{source.branch}/{file_path}"

            # Download file with ETag caching
            updated = self._download_file_with_etag(
                raw_url, cache_path / file_path, force
            )

            if updated:
                files_updated += 1
            else:
                files_cached += 1

            # Call progress callback if provided
            if progress_callback:
                progress_callback(1)

        self.logger.info(
            f"Repository sync complete: {files_updated} updated, {files_cached} cached"
        )
        return files_updated, files_cached

    def _discover_repository_files_via_tree_api(
        self, owner_repo: str, branch: str
    ) -> List[str]:
        """Discover all files in repository using GitHub Tree API.

        Design Decision: Use Tree API instead of recursive Contents API

        Rationale: GitHub's Tree API returns the entire repository structure in a single
        request, avoiding rate limiting issues from making dozens of Contents API calls.
        For repositories with nested structures (like skills), this is much more efficient.

        Trade-offs:
        - Performance: Single API call vs. 10-50+ calls for nested repos
        - Rate Limiting: Avoids 403 errors from hitting 60 requests/hour limit
        - Completeness: Tree API may truncate for huge repos (>100k files), but skills repos are small

        Args:
            owner_repo: GitHub owner/repo (e.g., "bobmatnyc/claude-mpm-skills")
            branch: Branch name (e.g., "main")

        Returns:
            List of file paths (e.g., ["universal/collaboration/SKILL.md", ...])

        Example:
            >>> files = self._discover_repository_files_via_tree_api(
            ...     "bobmatnyc/claude-mpm-skills", "main"
            ... )
            >>> print(len(files))
            245  # All files in repository
        """
        import requests

        all_files = []

        try:
            # Step 1: Get the latest commit SHA for the branch
            refs_url = (
                f"https://api.github.com/repos/{owner_repo}/git/refs/heads/{branch}"
            )
            refs_response = requests.get(refs_url, timeout=30)
            refs_response.raise_for_status()
            commit_sha = refs_response.json()["object"]["sha"]

            # Step 2: Get the tree for that commit (recursive=1 gets all files)
            tree_url = (
                f"https://api.github.com/repos/{owner_repo}/git/trees/{commit_sha}"
            )
            params = {"recursive": "1"}  # Recursively get all files
            tree_response = requests.get(tree_url, params=params, timeout=30)
            tree_response.raise_for_status()

            tree_data = tree_response.json()

            # Step 3: Extract file paths (filter out directories)
            for item in tree_data.get("tree", []):
                if item["type"] == "blob":  # blob = file, tree = directory
                    all_files.append(item["path"])

            self.logger.info(
                f"Discovered {len(all_files)} files via Tree API in {owner_repo}/{branch}"
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to discover files via Tree API: {e}")
            # Fall back to empty list (sync will fail gracefully)
            return []

        return all_files

    def _download_file_with_etag(
        self, url: str, local_path: Path, force: bool = False
    ) -> bool:
        """Download file from URL with ETag caching.

        Args:
            url: Raw GitHub URL
            local_path: Local file path to save to
            force: Force download even if cached

        Returns:
            True if file was updated, False if cached
        """

        import requests

        # Create parent directory
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Load ETag cache
        etag_cache_file = local_path.parent / ".etag_cache.json"
        etag_cache = {}
        if etag_cache_file.exists():
            try:
                import json

                with open(etag_cache_file, encoding="utf-8") as f:
                    etag_cache = json.load(f)
            except Exception:
                pass

        # Get cached ETag
        cached_etag = etag_cache.get(str(local_path))

        # Make conditional request
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

            # Download and save file
            local_path.write_bytes(response.content)

            # Save new ETag
            if "ETag" in response.headers:
                etag_cache[str(local_path)] = response.headers["ETag"]
                with open(etag_cache_file, "w", encoding="utf-8") as f:
                    import json

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

    def deploy_skills(
        self,
        target_dir: Optional[Path] = None,
        force: bool = False,
        progress_callback=None,
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

        Returns:
            Dict with deployment results:
            {
                "deployed_count": int,
                "skipped_count": int,
                "failed_count": int,
                "deployed_skills": List[str],
                "skipped_skills": List[str],
                "errors": List[str]
            }

        Example:
            >>> manager = GitSkillSourceManager(config)
            >>> result = manager.deploy_skills()
            >>> print(f"Deployed {result['deployed_count']} skills")
        """
        if target_dir is None:
            target_dir = Path.home() / ".claude" / "skills"

        target_dir.mkdir(parents=True, exist_ok=True)

        deployed = []
        skipped = []
        errors = []

        # Get all skills from all sources
        all_skills = self.get_all_skills()

        self.logger.info(
            f"Deploying {len(all_skills)} skills to {target_dir} (force={force})"
        )

        for skill in all_skills:
            skill_name = skill.get("name", "unknown")
            deployment_name = skill.get("deployment_name")

            if not deployment_name:
                self.logger.warning(
                    f"Skill {skill_name} missing deployment_name, skipping"
                )
                errors.append(f"{skill_name}: Missing deployment_name")
                if progress_callback:
                    progress_callback(1)
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
                progress_callback(1)

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
        }

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
