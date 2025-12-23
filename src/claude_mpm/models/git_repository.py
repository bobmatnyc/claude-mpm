"""Git repository model for agent sources."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


@dataclass
class GitRepository:
    """Represents a Git repository configuration for agent sources.

    This model tracks Git repositories that contain agent markdown files.
    Repositories are cached locally and synced using ETag-based HTTP caching.

    Attributes:
        url: Full GitHub repository URL (e.g., https://github.com/owner/repo)
        subdirectory: Optional subdirectory within repository (e.g., "agents/backend")
        enabled: Whether this repository should be synced
        priority: Priority for agent resolution (lower = higher precedence)
        last_synced: Timestamp of last successful sync
        etag: HTTP ETag from last sync for incremental updates
    """

    url: str
    subdirectory: Optional[str] = None
    enabled: bool = True
    priority: int = 100
    last_synced: Optional[datetime] = None
    etag: Optional[str] = None

    @property
    def cache_path(self) -> Path:
        """Return cache directory path for this repository.

        Cache structure: ~/.claude-mpm/cache/agents/{owner}/{repo}/{subdirectory}/

        Returns:
            Absolute path to cache directory for this repository

        Example:
            >>> repo = GitRepository(
            ...     url="https://github.com/bobmatnyc/claude-mpm-agents",
            ...     subdirectory="agents"
            ... )
            >>> repo.cache_path
            Path('/Users/user/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents/agents')
        """
        home = Path.home()
        base_cache = home / ".claude-mpm" / "cache" / "agents"

        # Extract owner and repo from URL
        owner, repo = self._parse_github_url(self.url)

        # Build cache path: base/owner/repo/subdirectory
        cache_path = base_cache / owner / repo

        if self.subdirectory:
            # Normalize subdirectory path (remove leading/trailing slashes)
            normalized_subdir = self.subdirectory.strip("/")
            cache_path = cache_path / normalized_subdir

        return cache_path

    @property
    def identifier(self) -> str:
        """Return unique identifier for this repository.

        Format: {owner}/{repo}/{subdirectory} or {owner}/{repo}

        Returns:
            Unique identifier string

        Example:
            >>> repo = GitRepository(
            ...     url="https://github.com/owner/repo",
            ...     subdirectory="agents"
            ... )
            >>> repo.identifier
            'owner/repo/agents'
        """
        owner, repo = self._parse_github_url(self.url)
        base_id = f"{owner}/{repo}"

        if self.subdirectory:
            normalized_subdir = self.subdirectory.strip("/")
            return f"{base_id}/{normalized_subdir}"

        return base_id

    def validate(self) -> list[str]:
        """Validate repository configuration.

        Returns:
            List of validation error messages (empty if valid)

        Validation checks:
            - URL is not empty
            - URL is valid HTTP/HTTPS format
            - URL is a GitHub repository URL
            - Priority is non-negative
            - Priority is reasonable (<= 1000, warning only)
            - Subdirectory is relative path (not absolute)
        """
        errors = []

        # Validate URL
        if not self.url or not self.url.strip():
            errors.append("URL cannot be empty")
            return errors  # Can't continue validation without URL

        # Check URL format
        try:
            parsed = urlparse(self.url)

            # Must be HTTP or HTTPS
            if parsed.scheme not in ("http", "https"):
                errors.append(
                    f"URL must use http:// or https:// protocol, got: {parsed.scheme}"
                )

            # Must be GitHub (for now)
            if not parsed.netloc.endswith("github.com"):
                errors.append(f"URL must be a GitHub repository, got: {parsed.netloc}")

            # Should have owner/repo path structure
            path_parts = [p for p in parsed.path.strip("/").split("/") if p]
            if len(path_parts) < 2:
                errors.append(f"URL must include owner/repo path, got: {parsed.path}")

        except Exception as e:
            errors.append(f"Invalid URL format: {e}")

        # Validate priority
        if self.priority < 0:
            errors.append("Priority must be non-negative (0 or greater)")

        if self.priority > 1000:
            errors.append(
                f"Priority {self.priority} is unusually high (recommended: 0-1000). "
                "Lower priority numbers have higher precedence."
            )

        # Validate subdirectory
        if self.subdirectory:
            # Must be relative path
            if Path(self.subdirectory).is_absolute():
                errors.append(
                    f"Subdirectory must be a relative path, got absolute: {self.subdirectory}"
                )

            # Should not start with slash
            if self.subdirectory.startswith("/"):
                errors.append(
                    f"Subdirectory should not start with '/', got: {self.subdirectory}"
                )

        return errors

    def _parse_github_url(self, url: str) -> tuple[str, str]:
        """Parse GitHub URL to extract owner and repository name.

        Args:
            url: GitHub repository URL

        Returns:
            Tuple of (owner, repository_name)

        Example:
            >>> repo = GitRepository(url="https://github.com/owner/repo")
            >>> repo._parse_github_url(repo.url)
            ('owner', 'repo')
        """
        # Remove .git suffix if present
        url = url.rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]

        # Parse URL
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]

        if len(path_parts) >= 2:
            owner = path_parts[0]
            repo = path_parts[1]
            return owner, repo

        # Fallback: Use URL as-is if parsing fails
        # This will be caught by validation
        return "unknown", "unknown"

    def __repr__(self) -> str:
        """Return string representation of repository."""
        return (
            f"GitRepository(identifier='{self.identifier}', "
            f"priority={self.priority}, enabled={self.enabled})"
        )
