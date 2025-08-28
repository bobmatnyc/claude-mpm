#!/usr/bin/env python3
"""
Code Tree Builder
=================

WHY: Builds hierarchical file system structure with intelligent filtering
and incremental processing support for large codebases.

DESIGN DECISIONS:
- Support .gitignore patterns for filtering
- Incremental processing with resume capability
- Efficient directory traversal with progress tracking
- Cache file metadata to detect changes
"""

import fnmatch
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ..core.logging_config import get_logger


@dataclass
class FileMetadata:
    """Metadata for a file in the tree."""

    path: str
    size: int
    modified: float
    hash: Optional[str] = None
    language: Optional[str] = None


@dataclass
class TreeNode:
    """Node in the file tree."""

    name: str
    path: str
    type: str  # 'file' or 'directory'
    children: List["TreeNode"] = field(default_factory=list)
    metadata: Optional[FileMetadata] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {"name": self.name, "path": self.path, "type": self.type}

        if self.metadata:
            result["metadata"] = {
                "size": self.metadata.size,
                "modified": self.metadata.modified,
                "language": self.metadata.language,
            }

        if self.children:
            result["children"] = [child.to_dict() for child in self.children]

        return result


class GitignoreParser:
    """Parser for .gitignore patterns.

    WHY: Respecting .gitignore patterns ensures we don't analyze files
    that shouldn't be included in the codebase analysis.
    """

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.patterns = []
        self.logger = get_logger(__name__)
        self._load_patterns()

    def _load_patterns(self):
        """Load .gitignore patterns from file."""
        gitignore_path = self.root_dir / ".gitignore"

        if gitignore_path.exists():
            try:
                with open(gitignore_path) as f:
                    for line in f:
                        line = line.strip()
                        # Skip comments and empty lines
                        if line and not line.startswith("#"):
                            self.patterns.append(line)

                self.logger.debug(f"Loaded {len(self.patterns)} .gitignore patterns")
            except Exception as e:
                self.logger.warning(f"Failed to load .gitignore: {e}")

    def should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored based on patterns.

        Args:
            path: Path to check

        Returns:
            True if path should be ignored
        """
        # Get relative path from root
        try:
            rel_path = path.relative_to(self.root_dir)
        except ValueError:
            return False

        rel_str = str(rel_path)

        for pattern in self.patterns:
            # Handle directory patterns
            if pattern.endswith("/"):
                if path.is_dir() and fnmatch.fnmatch(rel_str, pattern[:-1]):
                    return True
            # Handle negation patterns
            elif pattern.startswith("!"):
                if fnmatch.fnmatch(rel_str, pattern[1:]):
                    return False
            # Regular patterns
            else:
                if fnmatch.fnmatch(rel_str, pattern):
                    return True
                # Also check if any parent directory matches
                for parent in rel_path.parents:
                    if fnmatch.fnmatch(str(parent), pattern):
                        return True

        return False


class CodeTreeBuilder:
    """Builds hierarchical code tree with filtering and caching.

    WHY: Efficient tree building is crucial for large codebases. This class
    handles incremental processing, caching, and intelligent filtering.
    """

    # Default ignore patterns
    DEFAULT_IGNORE = [
        "__pycache__",
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "env",
        "dist",
        "build",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        ".eggs",
        "*.egg-info",
        ".coverage",
        "htmlcov",
        ".hypothesis",
        ".ruff_cache",
        ".DS_Store",
        "Thumbs.db",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".Python",
        "*.so",
        "*.dll",
        "*.dylib",
        ".idea",
        ".vscode",
        "*.swp",
        "*.swo",
        "*~",
        ".env",
        ".env.local",
    ]

    # Language detection by extension
    LANGUAGE_MAP = {
        ".py": "python",
        ".pyw": "python",
        ".pyx": "python",
        ".pxd": "python",
        ".pyi": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".java": "java",
        ".kt": "kotlin",
        ".scala": "scala",
        ".go": "go",
        ".rs": "rust",
        ".c": "c",
        ".h": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".hpp": "cpp",
        ".cs": "csharp",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".m": "objc",
        ".mm": "objc",
        ".r": "r",
        ".R": "r",
        ".lua": "lua",
        ".pl": "perl",
        ".pm": "perl",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "zsh",
        ".fish": "fish",
        ".ps1": "powershell",
        ".psm1": "powershell",
        ".vim": "vim",
        ".el": "elisp",
        ".clj": "clojure",
        ".cljs": "clojure",
        ".ex": "elixir",
        ".exs": "elixir",
        ".erl": "erlang",
        ".hrl": "erlang",
        ".fs": "fsharp",
        ".fsx": "fsharp",
        ".ml": "ocaml",
        ".mli": "ocaml",
        ".dart": "dart",
        ".nim": "nim",
        ".nims": "nim",
        ".zig": "zig",
        ".v": "v",
        ".vv": "v",
        ".sql": "sql",
        ".md": "markdown",
        ".rst": "restructuredtext",
        ".tex": "latex",
        ".json": "json",
        ".xml": "xml",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".ini": "ini",
        ".cfg": "ini",
        ".conf": "conf",
        ".dockerfile": "dockerfile",
        ".Dockerfile": "dockerfile",
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".scss": "scss",
        ".sass": "sass",
        ".less": "less",
    }

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize tree builder.

        Args:
            cache_dir: Directory for caching tree data
        """
        self.logger = get_logger(__name__)
        self.cache_dir = cache_dir or Path.home() / ".claude-mpm" / "tree-cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Statistics
        self.stats = {
            "directories_scanned": 0,
            "files_found": 0,
            "files_ignored": 0,
            "total_size": 0,
            "languages": set(),
        }

    def build_tree(
        self,
        root_path: Path,
        file_extensions: Optional[List[str]] = None,
        ignore_patterns: Optional[List[str]] = None,
        max_depth: Optional[int] = None,
        use_gitignore: bool = True,
        calculate_hashes: bool = False,
        progress_callback: Optional[callable] = None,
    ) -> TreeNode:
        """Build file tree from directory.

        Args:
            root_path: Root directory to scan
            file_extensions: File extensions to include (None for all)
            ignore_patterns: Additional ignore patterns
            max_depth: Maximum directory depth to traverse
            use_gitignore: Whether to use .gitignore patterns
            calculate_hashes: Whether to calculate file hashes
            progress_callback: Callback for progress updates

        Returns:
            Root TreeNode of the built tree
        """
        self.stats = {
            "directories_scanned": 0,
            "files_found": 0,
            "files_ignored": 0,
            "total_size": 0,
            "languages": set(),
        }

        # Load gitignore patterns if requested
        gitignore_parser = GitignoreParser(root_path) if use_gitignore else None

        # Combine ignore patterns
        all_ignore_patterns = set(self.DEFAULT_IGNORE)
        if ignore_patterns:
            all_ignore_patterns.update(ignore_patterns)

        # Build the tree
        return self._build_node(
            root_path,
            root_path,
            file_extensions,
            all_ignore_patterns,
            gitignore_parser,
            max_depth,
            0,
            calculate_hashes,
            progress_callback,
        )

    def _build_node(
        self,
        path: Path,
        root_path: Path,
        file_extensions: Optional[List[str]],
        ignore_patterns: Set[str],
        gitignore_parser: Optional[GitignoreParser],
        max_depth: Optional[int],
        current_depth: int,
        calculate_hashes: bool,
        progress_callback: Optional[callable],
    ) -> Optional[TreeNode]:
        """Recursively build tree node.

        Args:
            path: Current path to process
            root_path: Root directory of tree
            file_extensions: File extensions to include
            ignore_patterns: Patterns to ignore
            gitignore_parser: Gitignore parser instance
            max_depth: Maximum depth to traverse
            current_depth: Current depth in tree
            calculate_hashes: Whether to calculate file hashes
            progress_callback: Progress callback function

        Returns:
            TreeNode or None if path should be ignored
        """
        # Check if we should ignore this path
        if self._should_ignore(path, ignore_patterns):
            self.stats["files_ignored"] += 1
            return None

        # Check gitignore
        if gitignore_parser and gitignore_parser.should_ignore(path):
            self.stats["files_ignored"] += 1
            return None

        # Check depth limit
        if max_depth is not None and current_depth > max_depth:
            return None

        # Create node
        node = TreeNode(
            name=path.name,
            path=str(path),
            type="directory" if path.is_dir() else "file",
        )

        # Handle files
        if path.is_file():
            # Check file extension filter
            if file_extensions:
                if not any(path.suffix == ext for ext in file_extensions):
                    return None

            # Get file metadata
            stat = path.stat()
            metadata = FileMetadata(
                path=str(path),
                size=stat.st_size,
                modified=stat.st_mtime,
                language=self._detect_language(path),
            )

            # Calculate hash if requested
            if calculate_hashes:
                metadata.hash = self._calculate_file_hash(path)

            node.metadata = metadata

            # Update statistics
            self.stats["files_found"] += 1
            self.stats["total_size"] += stat.st_size
            if metadata.language:
                self.stats["languages"].add(metadata.language)

            # Progress callback
            if progress_callback:
                progress_callback(path, self.stats)

        # Handle directories
        elif path.is_dir():
            self.stats["directories_scanned"] += 1

            try:
                # Process children
                children = []
                for child_path in sorted(path.iterdir()):
                    child_node = self._build_node(
                        child_path,
                        root_path,
                        file_extensions,
                        ignore_patterns,
                        gitignore_parser,
                        max_depth,
                        current_depth + 1,
                        calculate_hashes,
                        progress_callback,
                    )

                    if child_node:
                        children.append(child_node)

                node.children = children

            except PermissionError:
                self.logger.warning(f"Permission denied: {path}")

        return node

    def _should_ignore(self, path: Path, ignore_patterns: Set[str]) -> bool:
        """Check if path matches any ignore pattern.

        Args:
            path: Path to check
            ignore_patterns: Set of ignore patterns

        Returns:
            True if path should be ignored
        """
        name = path.name

        return any(fnmatch.fnmatch(name, pattern) for pattern in ignore_patterns)

    def _detect_language(self, path: Path) -> Optional[str]:
        """Detect programming language from file extension.

        Args:
            path: File path

        Returns:
            Language name or None
        """
        suffix = path.suffix.lower()

        # Special case for Dockerfile
        if path.name.lower() in ("dockerfile", "dockerfile.*"):
            return "dockerfile"

        return self.LANGUAGE_MAP.get(suffix)

    def _calculate_file_hash(self, path: Path) -> str:
        """Calculate MD5 hash of file contents.

        Args:
            path: File path

        Returns:
            MD5 hash string
        """
        hasher = hashlib.md5()

        try:
            with open(path, "rb") as f:
                # Read in chunks for large files
                while chunk := f.read(8192):
                    hasher.update(chunk)
        except Exception as e:
            self.logger.warning(f"Failed to hash {path}: {e}")
            return ""

        return hasher.hexdigest()

    def save_tree(self, tree: TreeNode, output_path: Path):
        """Save tree to JSON file.

        Args:
            tree: Root tree node
            output_path: Output file path
        """
        tree_dict = tree.to_dict()
        tree_dict["stats"] = {
            "directories_scanned": self.stats["directories_scanned"],
            "files_found": self.stats["files_found"],
            "files_ignored": self.stats["files_ignored"],
            "total_size": self.stats["total_size"],
            "languages": list(self.stats["languages"]),
            "generated_at": datetime.utcnow().isoformat(),
        }

        with open(output_path, "w") as f:
            json.dump(tree_dict, f, indent=2)

        self.logger.info(f"Saved tree to {output_path}")

    def load_tree(self, input_path: Path) -> TreeNode:
        """Load tree from JSON file.

        Args:
            input_path: Input file path

        Returns:
            Root tree node
        """
        with open(input_path) as f:
            tree_dict = json.load(f)

        # Remove stats if present
        if "stats" in tree_dict:
            del tree_dict["stats"]

        return self._dict_to_node(tree_dict)

    def _dict_to_node(self, node_dict: Dict[str, Any]) -> TreeNode:
        """Convert dictionary to TreeNode.

        Args:
            node_dict: Node dictionary

        Returns:
            TreeNode instance
        """
        node = TreeNode(
            name=node_dict["name"], path=node_dict["path"], type=node_dict["type"]
        )

        if "metadata" in node_dict:
            meta = node_dict["metadata"]
            node.metadata = FileMetadata(
                path=node.path,
                size=meta.get("size", 0),
                modified=meta.get("modified", 0),
                hash=meta.get("hash"),
                language=meta.get("language"),
            )

        if "children" in node_dict:
            node.children = [
                self._dict_to_node(child_dict) for child_dict in node_dict["children"]
            ]

        return node

    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics.

        Returns:
            Statistics dictionary
        """
        return {**self.stats, "languages": list(self.stats["languages"])}

    def compare_trees(
        self, old_tree: TreeNode, new_tree: TreeNode
    ) -> Dict[str, List[str]]:
        """Compare two trees to find differences.

        Args:
            old_tree: Previous tree
            new_tree: Current tree

        Returns:
            Dictionary with added, removed, and modified files
        """
        old_files = self._get_all_files(old_tree)
        new_files = self._get_all_files(new_tree)

        old_paths = set(old_files.keys())
        new_paths = set(new_files.keys())

        added = list(new_paths - old_paths)
        removed = list(old_paths - new_paths)

        # Check for modifications
        modified = []
        for path in old_paths & new_paths:
            old_meta = old_files[path]
            new_meta = new_files[path]

            # Compare modification times or hashes
            if old_meta.hash and new_meta.hash:
                if old_meta.hash != new_meta.hash:
                    modified.append(path)
            elif old_meta.modified != new_meta.modified:
                modified.append(path)

        return {
            "added": sorted(added),
            "removed": sorted(removed),
            "modified": sorted(modified),
        }

    def _get_all_files(self, tree: TreeNode) -> Dict[str, FileMetadata]:
        """Get all files from tree.

        Args:
            tree: Root tree node

        Returns:
            Dictionary mapping file paths to metadata
        """
        files = {}

        def traverse(node: TreeNode):
            if node.type == "file" and node.metadata:
                files[node.path] = node.metadata
            elif node.children:
                for child in node.children:
                    traverse(child)

        traverse(tree)
        return files
