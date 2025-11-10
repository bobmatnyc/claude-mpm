#!/usr/bin/env python3
"""
Discovery Module
================

Handles directory traversal and file discovery for code analysis.

WHY: Separates file system operations from analysis logic,
providing efficient directory scanning with proper filtering.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar, Dict, List, Optional, Set

from ...core.logging_config import get_logger
from ..code_tree_events import CodeTreeEventEmitter
from .gitignore import GitignoreManager


class DiscoveryManager:
    """Manages file and directory discovery for code analysis."""

    # Define code file extensions at class level for directory filtering
    CODE_EXTENSIONS: ClassVar[Set[str]] = {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".mjs",
        ".cjs",
        ".java",
        ".cpp",
        ".c",
        ".h",
        ".hpp",
        ".cs",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".scala",
        ".r",
        ".m",
        ".mm",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".ps1",
        ".bat",
        ".cmd",
        ".sql",
        ".html",
        ".css",
        ".scss",
        ".sass",
        ".less",
        ".xml",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".md",
        ".rst",
        ".txt",
    }

    # File extensions to language mapping
    LANGUAGE_MAP: ClassVar[Dict[str, str]] = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".mjs": "javascript",
        ".cjs": "javascript",
    }

    def __init__(
        self,
        gitignore_manager: GitignoreManager,
        emitter: Optional[CodeTreeEventEmitter] = None,
    ):
        """Initialize discovery manager.

        Args:
            gitignore_manager: GitignoreManager instance for filtering
            emitter: Optional event emitter
        """
        self.logger = get_logger(__name__)
        self.gitignore_manager = gitignore_manager
        self.emitter = emitter
        self._last_working_dir = None

    def has_code_files(
        self, directory: Path, depth: int = 5, current_depth: int = 0
    ) -> bool:
        """Check if directory contains code files up to 5 levels deep.

        Args:
            directory: Directory to check
            depth: Maximum depth to search
            current_depth: Current recursion depth

        Returns:
            True if directory contains code files within depth levels
        """
        if current_depth >= depth:
            return False

        # Skip checking these directories entirely
        SKIP_DIRS = {
            "node_modules",
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "dist",
            "build",
            ".tox",
            "htmlcov",
            ".pytest_cache",
            ".mypy_cache",
            "coverage",
            ".idea",
            ".vscode",
            "env",
            ".coverage",
            "__MACOSX",
            ".ipynb_checkpoints",
        }
        # Skip directories in the skip list or egg-info directories
        if directory.name in SKIP_DIRS or directory.name.endswith(".egg-info"):
            return False

        try:
            for item in directory.iterdir():
                # Skip hidden items in scan
                if item.name.startswith("."):
                    continue

                if item.is_file():
                    # Check if it's a code file
                    ext = item.suffix.lower()
                    if ext in self.CODE_EXTENSIONS:
                        return True
                elif item.is_dir() and current_depth < depth - 1:
                    # Skip egg-info directories in the recursive check too
                    if item.name.endswith(".egg-info"):
                        continue
                    if self.has_code_files(item, depth, current_depth + 1):
                        return True

        except (PermissionError, OSError):
            pass

        return False

    def discover_top_level(
        self, directory: Path, ignore_patterns: Optional[List[str]] = None
    ) -> Dict[str, any]:
        """Discover only top-level directories and files for lazy loading.

        Args:
            directory: Root directory to discover
            ignore_patterns: Patterns to ignore

        Returns:
            Dictionary with top-level structure
        """
        # CRITICAL FIX: Use the directory parameter as the base for relative paths
        # NOT the current working directory. This ensures we only show items
        # within the requested directory, not parent directories.
        Path(directory).absolute()

        # Emit discovery start event
        if self.emitter:
            self.emitter.emit(
                "info",
                {
                    "type": "discovery.start",
                    "action": "scanning_directory",
                    "path": str(directory),
                    "message": f"Starting discovery of {directory.name}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        result = {
            "path": str(directory),
            "name": directory.name,
            "type": "directory",
            "children": [],
        }

        try:
            # Clear cache if working directory changed
            if self._last_working_dir != directory:
                self.gitignore_manager.clear_cache()
                self._last_working_dir = directory

            # Get immediate children only (no recursion)
            files_count = 0
            dirs_count = 0
            ignored_count = 0

            for item in directory.iterdir():
                # Use gitignore manager for filtering with the directory as working dir
                if self.gitignore_manager.should_ignore(item, directory):
                    if self.emitter:
                        self.emitter.emit(
                            "info",
                            {
                                "type": "filter.gitignore",
                                "path": str(item),
                                "reason": "gitignore pattern",
                                "message": f"Ignored by gitignore: {item.name}",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            },
                        )
                    ignored_count += 1
                    continue

                # Also check additional patterns if provided
                if ignore_patterns and any(p in str(item) for p in ignore_patterns):
                    if self.emitter:
                        self.emitter.emit(
                            "info",
                            {
                                "type": "filter.pattern",
                                "path": str(item),
                                "reason": "custom pattern",
                                "message": f"Ignored by pattern: {item.name}",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            },
                        )
                    ignored_count += 1
                    continue

                if item.is_dir():
                    # Check if directory contains code files (recursively checking subdirectories)
                    # Important: We want to include directories even if they only have code
                    # in subdirectories (like src/claude_mpm/*.py)
                    if not self.has_code_files(item, depth=5):
                        if self.emitter:
                            self.emitter.emit(
                                "info",
                                {
                                    "type": "filter.no_code",
                                    "path": str(item.name),
                                    "reason": "no code files",
                                    "message": f"Skipped directory without code: {item.name}",
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                },
                            )
                        ignored_count += 1
                        continue

                    # Directory - return just the item name
                    # The frontend will construct the full path by combining parent path with child name
                    path_str = item.name

                    # Emit directory found event
                    if self.emitter:
                        self.emitter.emit(
                            "info",
                            {
                                "type": "discovery.directory",
                                "path": str(item),
                                "message": f"Found directory: {item.name}",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            },
                        )
                    dirs_count += 1

                    child = {
                        "path": path_str,
                        "name": item.name,
                        "type": "directory",
                        "discovered": False,
                        "children": [],
                    }
                    result["children"].append(child)

                elif item.is_file():
                    # Check if it's a supported code file or a special file we want to show
                    supported_extensions = {
                        ".py",
                        ".js",
                        ".jsx",
                        ".ts",
                        ".tsx",
                        ".mjs",
                        ".cjs",
                    }
                    if item.suffix in supported_extensions or item.name in [
                        ".gitignore",
                        ".env.example",
                        ".env.sample",
                    ]:
                        # File - mark for lazy analysis
                        language = self.get_language(item)

                        # File path should be just the item name
                        # The frontend will construct the full path by combining parent path with child name
                        path_str = item.name

                        # Emit file found event
                        if self.emitter:
                            self.emitter.emit(
                                "info",
                                {
                                    "type": "discovery.file",
                                    "path": str(item),
                                    "language": language,
                                    "size": item.stat().st_size,
                                    "message": f"Found file: {item.name} ({language})",
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                },
                            )
                        files_count += 1

                        child = {
                            "path": path_str,
                            "name": item.name,
                            "type": "file",
                            "language": language,
                            "size": item.stat().st_size,
                            "analyzed": False,
                        }
                        result["children"].append(child)

                        if self.emitter:
                            self.emitter.emit_file_discovered(
                                path_str, language, item.stat().st_size
                            )

        except PermissionError as e:
            self.logger.warning(f"Permission denied accessing {directory}: {e}")
            if self.emitter:
                self.emitter.emit_error(str(directory), f"Permission denied: {e}")

        # Emit discovery complete event with stats
        if self.emitter:
            self.emitter.emit(
                "info",
                {
                    "type": "discovery.complete",
                    "path": str(directory),
                    "stats": {
                        "files": files_count,
                        "directories": dirs_count,
                        "ignored": ignored_count,
                    },
                    "message": f"Discovery complete: {files_count} files, {dirs_count} directories, {ignored_count} ignored",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        return result

    def discover_directory(
        self, dir_path: str, ignore_patterns: Optional[List[str]] = None
    ) -> Dict[str, any]:
        """Discover contents of a specific directory for lazy loading.

        Args:
            dir_path: Directory path to discover
            ignore_patterns: Patterns to ignore

        Returns:
            Dictionary with directory contents
        """
        directory = Path(dir_path)
        if not directory.exists() or not directory.is_dir():
            return {"error": f"Invalid directory: {dir_path}"}

        # Clear cache if working directory changed
        if self._last_working_dir != directory.parent:
            self.gitignore_manager.clear_cache()
            self._last_working_dir = directory.parent

        # The discover_top_level method will emit all the INFO events
        return self.discover_top_level(directory, ignore_patterns)

    def get_language(self, file_path: Path) -> str:
        """Determine language from file extension.

        Args:
            file_path: Path to file

        Returns:
            Language string
        """
        ext = file_path.suffix.lower()
        return self.LANGUAGE_MAP.get(ext, "unknown")
