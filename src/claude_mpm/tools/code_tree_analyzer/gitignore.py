#!/usr/bin/env python3
"""
Gitignore Manager
=================

Manages .gitignore pattern matching for file filtering.

WHY: Properly respecting .gitignore patterns ensures we don't analyze
or display files that should be ignored in the repository.
"""

from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

try:
    import pathspec

    PATHSPEC_AVAILABLE = True
except ImportError:
    PATHSPEC_AVAILABLE = False
    pathspec = None

from ...core.logging_config import get_logger


class GitignoreManager:
    """Manages .gitignore pattern matching for file filtering."""

    # Default patterns that should always be ignored
    DEFAULT_PATTERNS: ClassVar[list] = [
        ".git/",
        "__pycache__/",
        "*.pyc",
        "*.pyo",
        ".DS_Store",
        ".pytest_cache/",
        ".mypy_cache/",
        "dist/",
        "build/",
        "*.egg-info/",
        ".coverage",
        ".tox/",
        "htmlcov/",
        ".idea/",
        ".vscode/",
        "*.swp",
        "*.swo",
        "*~",
        "Thumbs.db",
        "node_modules/",
        ".venv/",
        "venv/",
        "env/",
        ".env",
        "*.log",
        ".ipynb_checkpoints/",
        "__MACOSX/",
        ".Spotlight-V100/",
        ".Trashes/",
        "desktop.ini",
    ]

    # Additional patterns to hide dotfiles (when enabled)
    DOTFILE_PATTERNS: ClassVar[list] = [
        ".*",  # All dotfiles
        ".*/",  # All dot directories
    ]

    # Important files/directories to always show
    DOTFILE_EXCEPTIONS: ClassVar[set] = {
        # Removed .gitignore from exceptions - it should be hidden by default
        ".env.example",
        ".env.sample",
        ".gitlab-ci.yml",
        ".travis.yml",
        ".dockerignore",
        ".editorconfig",
        ".eslintrc",
        ".prettierrc",
        # Removed .github from exceptions - it should be hidden by default
    }

    def __init__(self):
        """Initialize the GitignoreManager."""
        self.logger = get_logger(__name__)
        self._pathspec_cache: Dict[str, Any] = {}
        self._gitignore_cache: Dict[str, List[str]] = {}
        self._use_pathspec = PATHSPEC_AVAILABLE

        if not self._use_pathspec:
            self.logger.warning(
                "pathspec library not available - using basic pattern matching"
            )

    def get_ignore_patterns(self, working_dir: Path) -> List[str]:
        """Get all ignore patterns for a directory.

        Args:
            working_dir: The working directory to search for .gitignore files

        Returns:
            Combined list of ignore patterns from all sources
        """
        # Always include default patterns
        patterns = self.DEFAULT_PATTERNS.copy()

        # Don't add dotfile patterns here - handle them separately in should_ignore
        # This prevents exceptions from being overridden by the .* pattern

        # Find and parse .gitignore files
        gitignore_files = self._find_gitignore_files(working_dir)
        for gitignore_file in gitignore_files:
            patterns.extend(self._parse_gitignore(gitignore_file))

        return patterns

    def should_ignore(self, path: Path, working_dir: Path) -> bool:
        """Check if a path should be ignored based on patterns.

        Args:
            path: The path to check
            working_dir: The working directory (for relative path calculation)

        Returns:
            True if the path should be ignored
        """
        # Get the filename
        filename = path.name

        # 1. ALWAYS hide system files regardless of settings
        ALWAYS_HIDE = {".DS_Store", "Thumbs.db", ".pyc", ".pyo", ".pyd"}
        if filename in ALWAYS_HIDE or filename.endswith((".pyc", ".pyo", ".pyd")):
            return True

        # 2. Check dotfiles - ALWAYS filter them out (except exceptions)
        if filename.startswith("."):
            # Hide all dotfiles except those in the exceptions list
            # This means: return True (ignore) if NOT in exceptions
            return filename not in self.DOTFILE_EXCEPTIONS

        # Get or create PathSpec for this working directory
        pathspec_obj = self._get_pathspec(working_dir)

        if pathspec_obj:
            # Use pathspec for accurate matching
            try:
                rel_path = path.relative_to(working_dir)
                rel_path_str = str(rel_path)

                # For directories, also check with trailing slash
                if path.is_dir():
                    return pathspec_obj.match_file(
                        rel_path_str
                    ) or pathspec_obj.match_file(rel_path_str + "/")
                return pathspec_obj.match_file(rel_path_str)
            except ValueError:
                # Path is outside working directory
                return False
        else:
            # Fallback to basic pattern matching
            return self._basic_should_ignore(path, working_dir)

    def _get_pathspec(self, working_dir: Path) -> Optional[Any]:
        """Get or create a PathSpec object for the working directory.

        Args:
            working_dir: The working directory

        Returns:
            PathSpec object or None if not available
        """
        if not self._use_pathspec:
            return None

        cache_key = str(working_dir)
        if cache_key not in self._pathspec_cache:
            patterns = self.get_ignore_patterns(working_dir)
            try:
                self._pathspec_cache[cache_key] = pathspec.PathSpec.from_lines(
                    "gitwildmatch", patterns
                )
            except Exception as e:
                self.logger.warning(f"Failed to create PathSpec: {e}")
                return None

        return self._pathspec_cache[cache_key]

    def _find_gitignore_files(self, working_dir: Path) -> List[Path]:
        """Find all .gitignore files in the directory tree.

        Args:
            working_dir: The directory to search

        Returns:
            List of .gitignore file paths
        """
        gitignore_files = []

        # Check for .gitignore in working directory
        main_gitignore = working_dir / ".gitignore"
        if main_gitignore.exists():
            gitignore_files.append(main_gitignore)

        # Also check parent directories up to repository root
        current = working_dir
        while current != current.parent:
            parent_gitignore = current.parent / ".gitignore"
            if parent_gitignore.exists():
                gitignore_files.append(parent_gitignore)

            # Stop if we find a .git directory (repository root)
            if (current / ".git").exists():
                break

            current = current.parent

        return gitignore_files

    def _parse_gitignore(self, gitignore_path: Path) -> List[str]:
        """Parse a .gitignore file and return patterns.

        Args:
            gitignore_path: Path to .gitignore file

        Returns:
            List of patterns from the file
        """
        cache_key = str(gitignore_path)

        # Check cache
        if cache_key in self._gitignore_cache:
            return self._gitignore_cache[cache_key]

        patterns = []
        try:
            with Path(gitignore_path).open(
                encoding="utf-8",
            ) as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith("#"):
                        patterns.append(line)

            self._gitignore_cache[cache_key] = patterns
        except Exception as e:
            self.logger.warning(f"Failed to parse {gitignore_path}: {e}")

        return patterns

    def _basic_should_ignore(self, path: Path, working_dir: Path) -> bool:
        """Basic pattern matching fallback when pathspec is not available.

        Args:
            path: The path to check
            working_dir: The working directory

        Returns:
            True if the path should be ignored
        """
        path_str = str(path)
        path_name = path.name

        # 1. ALWAYS hide system files regardless of settings
        ALWAYS_HIDE = {".DS_Store", "Thumbs.db", ".pyc", ".pyo", ".pyd"}
        if path_name in ALWAYS_HIDE or path_name.endswith((".pyc", ".pyo", ".pyd")):
            return True

        # 2. Check dotfiles - ALWAYS filter them out (except exceptions)
        if path_name.startswith("."):
            # Only show if in exceptions list
            return path_name not in self.DOTFILE_EXCEPTIONS

        patterns = self.get_ignore_patterns(working_dir)

        for pattern in patterns:
            # Skip dotfile patterns since we already handled them above
            if pattern in [".*", ".*/"]:
                continue

            # Simple pattern matching
            if pattern.endswith("/"):
                # Directory pattern
                if path.is_dir() and path_name == pattern[:-1]:
                    return True
            elif pattern.startswith("*."):
                # Extension pattern
                if path_name.endswith(pattern[1:]):
                    return True
            elif "*" in pattern:
                # Wildcard pattern (simplified)
                import fnmatch

                if fnmatch.fnmatch(path_name, pattern):
                    return True
            elif pattern in path_str:
                # Substring match
                return True
            elif path_name == pattern:
                # Exact match
                return True

        return False

    def clear_cache(self):
        """Clear all caches."""
        self._pathspec_cache.clear()
        self._gitignore_cache.clear()
