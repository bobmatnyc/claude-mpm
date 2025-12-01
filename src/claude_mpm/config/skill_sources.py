"""Configuration for skill sources (Git repositories).

This module manages skill sources configuration, which defines Git repositories
containing skill files (Markdown with YAML frontmatter). It supports:
- System repository (bobmatnyc/claude-mpm-skills) with priority 0
- Official Anthropic repository (anthropics/skills) with priority 1
- Multiple custom repositories with priority-based resolution
- YAML persistence for configuration
- Source management (add, remove, enable, disable)

Design Decision: Skill-specific data model separate from agent sources

Rationale: While skills and agents both come from Git repositories, they have
different structures (YAML frontmatter vs. Markdown sections) and different
resolution requirements. Separating the configuration models allows for
skill-specific validation and future extensibility.

Trade-offs:
- Maintainability: Clear separation of concerns
- Code Duplication: Some overlap with agent_sources.py (acceptable for clarity)
- Flexibility: Easy to extend skills with unique features

Example:
    >>> config = SkillSourceConfiguration.load()
    >>> config.add_source(SkillSource(
    ...     id="custom",
    ...     type="git",
    ...     url="https://github.com/owner/skills",
    ...     priority=200
    ... ))
    >>> config.save()
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

import yaml

from claude_mpm.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class SkillSource:
    """Represents a single skill source (Git repository).

    Attributes:
        id: Unique identifier for this source (e.g., "system", "custom")
        type: Source type (currently only "git" supported)
        url: Full Git repository URL
        branch: Git branch to use (default: "main")
        priority: Priority for skill resolution (lower = higher precedence)
        enabled: Whether this source should be synced

    Priority System:
        - 0: Reserved for system repository (highest precedence)
        - 1-99: High priority custom sources
        - 100-999: Normal priority custom sources
        - 1000+: Low priority custom sources

    Example:
        >>> source = SkillSource(
        ...     id="system",
        ...     type="git",
        ...     url="https://github.com/bobmatnyc/claude-mpm-skills",
        ...     priority=0
        ... )
        >>> source.validate()
        []
    """

    id: str
    type: str
    url: str
    branch: str = "main"
    priority: int = 100
    enabled: bool = True

    def __post_init__(self):
        """Validate skill source configuration after initialization.

        Raises:
            ValueError: If validation fails
        """
        errors = self.validate()
        if errors:
            raise ValueError(f"Invalid skill source configuration: {', '.join(errors)}")

    def validate(self) -> List[str]:
        """Validate skill source configuration.

        Returns:
            List of validation error messages (empty if valid)

        Validation checks:
            - ID is not empty and follows naming rules
            - Type is supported (currently only "git")
            - URL is valid and points to a Git repository
            - Branch name is valid
            - Priority is in valid range (0-1000)
        """
        errors = []

        # Validate ID
        if not self.id or not self.id.strip():
            errors.append("Source ID cannot be empty")
        elif not self.id.replace("-", "").replace("_", "").isalnum():
            errors.append(
                f"Source ID must be alphanumeric (with hyphens/underscores), got: {self.id}"
            )

        # Validate type
        if self.type != "git":
            errors.append(f"Only 'git' type is currently supported, got: {self.type}")

        # Validate URL
        if not self.url or not self.url.strip():
            errors.append("URL cannot be empty")
        else:
            try:
                parsed = urlparse(self.url)
                if parsed.scheme not in ("http", "https"):
                    errors.append(
                        f"URL must use http:// or https:// protocol, got: {parsed.scheme}"
                    )
                if not parsed.netloc.endswith("github.com"):
                    errors.append(
                        f"URL must be a GitHub repository, got: {parsed.netloc}"
                    )
                path_parts = [p for p in parsed.path.strip("/").split("/") if p]
                if len(path_parts) < 2:
                    errors.append(
                        f"URL must include owner/repo path, got: {parsed.path}"
                    )
            except Exception as e:
                errors.append(f"Invalid URL format: {e}")

        # Validate branch
        if not self.branch or not self.branch.strip():
            errors.append("Branch name cannot be empty")

        # Validate priority
        if self.priority < 0:
            errors.append("Priority must be non-negative (0 or greater)")
        if self.priority > 1000:
            errors.append(
                f"Priority {self.priority} is unusually high (recommended: 0-1000)"
            )

        return errors

    def __repr__(self) -> str:
        """Return string representation of skill source."""
        return (
            f"SkillSource(id='{self.id}', url='{self.url}', "
            f"priority={self.priority}, enabled={self.enabled})"
        )


class SkillSourceConfiguration:
    """Manages skill sources configuration file.

    Configuration Location:
        ~/.claude-mpm/config/skill_sources.yaml

    Default Configuration:
        sources:
          - id: system
            type: git
            url: https://github.com/bobmatnyc/claude-mpm-skills
            branch: main
            priority: 0
            enabled: true
          - id: anthropic-official
            type: git
            url: https://github.com/anthropics/skills
            branch: main
            priority: 1
            enabled: true

    Design Pattern: Configuration as Code

    This class follows the "configuration as code" pattern, treating YAML files
    as the single source of truth. All modifications are persisted immediately
    to ensure consistency.

    Example:
        >>> config = SkillSourceConfiguration()
        >>> sources = config.load()
        >>> print(f"Loaded {len(sources)} skill sources")
    """

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration manager.

        Args:
            config_path: Path to config file (defaults to ~/.claude-mpm/config/skill_sources.yaml)
        """
        if config_path is None:
            config_path = Path.home() / ".claude-mpm" / "config" / "skill_sources.yaml"
        self.config_path = config_path
        self.logger = get_logger(__name__)

    @classmethod
    def from_file(cls, config_path: Path) -> "SkillSourceConfiguration":
        """Load configuration from file.

        Args:
            config_path: Path to configuration file

        Returns:
            SkillSourceConfiguration instance
        """
        return cls(config_path=config_path)

    def load(self) -> List[SkillSource]:
        """Load skill sources from configuration file.

        Returns:
            List of SkillSource instances

        Behavior:
            - If file doesn't exist, returns default system source
            - If file is empty or invalid, returns default system source
            - Validates all sources during loading
            - Logs warnings for invalid sources (skips them)

        Example:
            >>> config = SkillSourceConfiguration()
            >>> sources = config.load()
            >>> for source in sources:
            ...     print(f"{source.id}: {source.url}")
        """
        # If file doesn't exist, return default sources
        if not self.config_path.exists():
            self.logger.info(
                f"Configuration file not found at {self.config_path}, using defaults"
            )
            return self._get_default_sources()

        try:
            with open(self.config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data or "sources" not in data:
                self.logger.warning(
                    f"Empty or invalid configuration at {self.config_path}, using defaults"
                )
                return self._get_default_sources()

            # Parse sources
            sources = []
            for source_data in data["sources"]:
                try:
                    source = SkillSource(
                        id=source_data["id"],
                        type=source_data["type"],
                        url=source_data["url"],
                        branch=source_data.get("branch", "main"),
                        priority=source_data.get("priority", 100),
                        enabled=source_data.get("enabled", True),
                    )
                    sources.append(source)
                except (KeyError, ValueError) as e:
                    self.logger.warning(f"Skipping invalid source: {e}")
                    continue

            if not sources:
                self.logger.warning("No valid sources found, using defaults")
                return self._get_default_sources()

            return sources

        except Exception as e:
            self.logger.error(
                f"Failed to load configuration from {self.config_path}: {e}"
            )
            self.logger.info("Using default configuration")
            return self._get_default_sources()

    def save(self, sources: List[SkillSource]) -> None:
        """Save skill sources to configuration file.

        Args:
            sources: List of SkillSource instances to save

        Behavior:
            - Creates parent directory if needed
            - Writes YAML atomically
            - Validates sources before saving
            - Logs save operation

        Raises:
            ValueError: If sources list is empty
            Exception: If file write fails

        Example:
            >>> config = SkillSourceConfiguration()
            >>> sources = [SkillSource(id="custom", type="git", url="...")]
            >>> config.save(sources)
        """
        if not sources:
            raise ValueError("Cannot save empty sources list")

        # Validate all sources before saving
        for source in sources:
            errors = source.validate()
            if errors:
                raise ValueError(
                    f"Cannot save invalid source '{source.id}': {', '.join(errors)}"
                )

        # Ensure parent directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Build YAML data structure
        data = {
            "sources": [
                {
                    "id": source.id,
                    "type": source.type,
                    "url": source.url,
                    "branch": source.branch,
                    "priority": source.priority,
                    "enabled": source.enabled,
                }
                for source in sources
            ]
        }

        try:
            # Write atomically: write to temp file, then rename
            temp_path = self.config_path.with_suffix(".yaml.tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

            # Atomic rename
            temp_path.replace(self.config_path)

            self.logger.info(
                f"Configuration saved to {self.config_path} ({len(sources)} sources)"
            )

        except Exception as e:
            self.logger.error(
                f"Failed to save configuration to {self.config_path}: {e}"
            )
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            raise

    def add_source(self, source: SkillSource) -> None:
        """Add a new skill source.

        Args:
            source: SkillSource to add

        Raises:
            ValueError: If source ID already exists or priority conflicts

        Example:
            >>> config = SkillSourceConfiguration()
            >>> source = SkillSource(id="custom", type="git", url="...")
            >>> config.add_source(source)
        """
        sources = self.load()

        # Check for duplicate IDs
        if any(s.id == source.id for s in sources):
            raise ValueError(f"Source with ID '{source.id}' already exists")

        # Check for priority conflicts (warn, don't fail)
        conflicts = [s for s in sources if s.priority == source.priority and s.enabled]
        if conflicts:
            self.logger.warning(
                f"Priority {source.priority} conflicts with existing sources: "
                f"{', '.join(s.id for s in conflicts)}"
            )

        sources.append(source)
        self.save(sources)
        self.logger.info(f"Added skill source: {source.id}")

    def remove_source(self, source_id: str) -> bool:
        """Remove a skill source by ID.

        Args:
            source_id: ID of source to remove

        Returns:
            True if source was removed, False if not found

        Example:
            >>> config = SkillSourceConfiguration()
            >>> removed = config.remove_source("custom")
            >>> print(removed)
            True
        """
        sources = self.load()
        initial_count = len(sources)

        sources = [s for s in sources if s.id != source_id]

        if len(sources) == initial_count:
            self.logger.warning(f"Source not found: {source_id}")
            return False

        self.save(sources)
        self.logger.info(f"Removed skill source: {source_id}")
        return True

    def get_source(self, source_id: str) -> Optional[SkillSource]:
        """Get a specific skill source by ID.

        Args:
            source_id: ID of source to retrieve

        Returns:
            SkillSource if found, None otherwise

        Example:
            >>> config = SkillSourceConfiguration()
            >>> source = config.get_source("system")
            >>> if source:
            ...     print(source.url)
        """
        sources = self.load()
        for source in sources:
            if source.id == source_id:
                return source
        return None

    def update_source(self, source_id: str, **updates) -> None:
        """Update an existing skill source.

        Args:
            source_id: ID of source to update
            **updates: Fields to update (url, branch, priority, enabled)

        Raises:
            ValueError: If source not found or updates are invalid

        Example:
            >>> config = SkillSourceConfiguration()
            >>> config.update_source("custom", enabled=False, priority=200)
        """
        sources = self.load()

        # Find source to update
        source_index = None
        for i, source in enumerate(sources):
            if source.id == source_id:
                source_index = i
                break

        if source_index is None:
            raise ValueError(f"Source not found: {source_id}")

        # Apply updates
        source = sources[source_index]
        for key, value in updates.items():
            if hasattr(source, key):
                setattr(source, key, value)
            else:
                raise ValueError(f"Invalid update field: {key}")

        # Validate updated source
        errors = source.validate()
        if errors:
            raise ValueError(
                f"Invalid updates for source '{source_id}': {', '.join(errors)}"
            )

        self.save(sources)
        self.logger.info(f"Updated skill source: {source_id}")

    def get_enabled_sources(self) -> List[SkillSource]:
        """Get all enabled skill sources sorted by priority.

        Returns:
            List of enabled SkillSource instances, sorted by priority (ascending)

        Priority Order:
            Lower priority number = higher precedence
            Priority 0 (system) comes first

        Example:
            >>> config = SkillSourceConfiguration()
            >>> sources = config.get_enabled_sources()
            >>> for source in sources:
            ...     print(f"{source.id} (priority: {source.priority})")
        """
        sources = self.load()
        enabled = [s for s in sources if s.enabled]
        return sorted(enabled, key=lambda s: s.priority)

    def validate_priority_conflicts(self) -> List[str]:
        """Check for priority conflicts between sources.

        Returns:
            List of warning messages about priority conflicts

        Behavior:
            - Conflicts occur when multiple enabled sources have same priority
            - Returns warning messages, not errors (conflicts are allowed)

        Example:
            >>> config = SkillSourceConfiguration()
            >>> warnings = config.validate_priority_conflicts()
            >>> for warning in warnings:
            ...     print(warning)
        """
        sources = self.load()
        enabled = [s for s in sources if s.enabled]

        warnings = []
        priorities = {}

        for source in enabled:
            if source.priority in priorities:
                priorities[source.priority].append(source.id)
            else:
                priorities[source.priority] = [source.id]

        for priority, source_ids in priorities.items():
            if len(source_ids) > 1:
                warnings.append(
                    f"Priority {priority} used by multiple sources: {', '.join(source_ids)}"
                )

        return warnings

    def _get_default_sources(self) -> List[SkillSource]:
        """Get default skill sources (system + official Anthropic).

        Returns:
            List of default SkillSource instances

        Design Decision: Multiple default sources

        Rationale: Provide users with both curated system skills and official
        Anthropic skills out-of-the-box. System repo maintains highest priority
        for custom/override capabilities.

        Default Sources:
            1. System repo (priority 0): bobmatnyc/claude-mpm-skills
            2. Anthropic repo (priority 1): anthropics/skills
        """
        return [
            SkillSource(
                id="system",
                type="git",
                url="https://github.com/bobmatnyc/claude-mpm-skills",
                branch="main",
                priority=0,
                enabled=True,
            ),
            SkillSource(
                id="anthropic-official",
                type="git",
                url="https://github.com/anthropics/skills",
                branch="main",
                priority=1,
                enabled=True,
            ),
        ]

    def _get_default_system_source(self) -> SkillSource:
        """Get default system skill source (legacy method).

        Returns:
            SkillSource for system repository

        Note: Deprecated in favor of _get_default_sources() which includes
        both system and Anthropic sources. Kept for backward compatibility.
        """
        return self._get_default_sources()[0]

    def __repr__(self) -> str:
        """Return string representation of configuration."""
        sources = self.load()
        enabled_count = len([s for s in sources if s.enabled])
        return (
            f"SkillSourceConfiguration(path='{self.config_path}', "
            f"sources={len(sources)}, enabled={enabled_count})"
        )
