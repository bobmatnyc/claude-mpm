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
from typing import Any, Dict, List, Optional

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

    def sync_all_sources(self, force: bool = False) -> Dict[str, Any]:
        """Sync all enabled skill sources.

        Syncs sources in priority order (lower priority first). Individual
        failures don't stop overall sync.

        Args:
            force: Force re-download even if cached

        Returns:
            Dict with sync results for each source:
            {
                "synced_count": int,
                "failed_count": int,
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
            "sources": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        for source in sources:
            try:
                result = self.sync_source(source.id, force=force)
                results["sources"][source.id] = result

                if result.get("synced"):
                    results["synced_count"] += 1
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

    def sync_source(self, source_id: str, force: bool = False) -> Dict[str, Any]:
        """Sync a specific skill source.

        Args:
            source_id: ID of source to sync
            force: Force re-download

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
            # Build source URL for raw GitHub content
            # Format: https://raw.githubusercontent.com/owner/repo/branch/
            source_url = self._build_raw_github_url(source)

            # Determine cache path for this source
            cache_path = self._get_source_cache_path(source)
            cache_path.mkdir(parents=True, exist_ok=True)

            # Initialize sync service (or use injected)
            if self.sync_service:
                sync_service = self.sync_service
            else:
                sync_service = GitSourceSyncService(
                    source_url=source_url,
                    cache_dir=cache_path,
                    source_id=source_id,
                )

            # Sync skills
            sync_results = sync_service.sync_agents(force_refresh=force)

            # Discover skills in cache
            discovery_service = SkillDiscoveryService(cache_path)
            discovered_skills = discovery_service.discover_skills()

            # Build result
            result = {
                "synced": True,
                "files_updated": sync_results.get("total_downloaded", 0),
                "files_cached": sync_results.get("cache_hits", 0),
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

    def __repr__(self) -> str:
        """Return string representation."""
        sources = self.config.load()
        enabled_count = len([s for s in sources if s.enabled])
        return (
            f"GitSkillSourceManager(cache='{self.cache_dir}', "
            f"sources={len(sources)}, enabled={enabled_count})"
        )
