#!/usr/bin/env python3
"""
Code Tree Analyzer Core
=======================

Main orchestrator that coordinates all code tree analysis operations.

WHY: Provides a unified interface for analyzing codebases with multiple
languages, handling caching and incremental processing.
"""

import time
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

from ...core.logging_config import get_logger
from ..code_tree_events import CodeTreeEventEmitter
from .analysis import FileAnalyzer
from .cache import CacheManager
from .discovery import DiscoveryManager
from .events import EventManager
from .gitignore import GitignoreManager
from .models import CodeNode
from .multilang_analyzer import MultiLanguageAnalyzer
from .python_analyzer import PythonAnalyzer


class CodeTreeAnalyzer:
    """Main analyzer that coordinates language-specific analyzers."""

    # Define code file extensions at class level for directory filtering
    CODE_EXTENSIONS: ClassVar[set] = {
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
    LANGUAGE_MAP: ClassVar[dict] = {
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
        emit_events: bool = True,
        cache_dir: Optional[Path] = None,
        emitter: Optional[CodeTreeEventEmitter] = None,
    ):
        """Initialize the code tree analyzer.

        Args:
            emit_events: Whether to emit Socket.IO events
            cache_dir: Directory for caching analysis results
            emitter: Optional event emitter to use (creates one if not provided)
        """
        self.logger = get_logger(__name__)
        self.emit_events = emit_events
        self.cache_dir = cache_dir or Path.home() / ".claude-mpm" / "code-cache"

        # Use provided emitter or create one
        if emitter:
            self.emitter = emitter
        elif emit_events:
            self.emitter = CodeTreeEventEmitter(use_stdout=True)
        else:
            self.emitter = None

        # Initialize managers
        self.gitignore_manager = GitignoreManager()
        self.cache_manager = CacheManager(self.cache_dir)
        self.event_manager = EventManager(self.emitter)

        # Initialize language analyzers
        self.python_analyzer = PythonAnalyzer(self.emitter)
        self.multi_lang_analyzer = MultiLanguageAnalyzer(self.emitter)

        # For JavaScript/TypeScript
        self.javascript_analyzer = self.multi_lang_analyzer
        self.generic_analyzer = self.multi_lang_analyzer

        # Initialize discovery and file analysis managers
        self.discovery_manager = DiscoveryManager(self.gitignore_manager, self.emitter)
        self.file_analyzer = FileAnalyzer(
            self.python_analyzer,
            self.multi_lang_analyzer,
            self.cache_manager,
            self.event_manager,
        )

        # Load cache
        self.cache_manager.load()

    def analyze_directory(
        self,
        directory: Path,
        languages: Optional[List[str]] = None,
        ignore_patterns: Optional[List[str]] = None,
        max_depth: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Analyze a directory and build code tree.

        Args:
            directory: Directory to analyze
            languages: Languages to include (None for all)
            ignore_patterns: Patterns to ignore
            max_depth: Maximum directory depth

        Returns:
            Dictionary containing the code tree and statistics
        """
        if self.emitter:
            self.emitter.start()

        start_time = time.time()
        all_nodes = []
        files_processed = 0
        total_files = 0

        # Collect files to process
        files_to_process = []
        for ext, lang in self.LANGUAGE_MAP.items():
            if languages and lang not in languages:
                continue

            for file_path in directory.rglob(f"*{ext}"):
                # Use gitignore manager for filtering with directory as working dir
                if self.gitignore_manager.should_ignore(file_path, directory):
                    continue

                # Also check additional patterns
                if ignore_patterns and any(
                    p in str(file_path) for p in ignore_patterns
                ):
                    continue

                # Check max depth
                if max_depth:
                    depth = len(file_path.relative_to(directory).parts) - 1
                    if depth > max_depth:
                        continue

                files_to_process.append((file_path, lang))

        total_files = len(files_to_process)

        # Process files
        for file_path, language in files_to_process:
            # Check cache
            cache_key = self.cache_manager.get_cache_key(file_path)

            if cached_nodes := self.cache_manager.get(cache_key):
                nodes = cached_nodes
                self.logger.debug(f"Using cached results for {file_path}")
            else:
                # Emit file start event
                if self.emitter:
                    self.emitter.emit_file_start(str(file_path), language)

                file_start = time.time()

                # Analyze based on language
                if language == "python":
                    nodes = self.python_analyzer.analyze_file(file_path)
                else:
                    nodes = self.multi_lang_analyzer.analyze_file(file_path, language)

                    # If no nodes found and we have a valid language, emit basic file info
                    if not nodes and language != "unknown":
                        self.logger.debug(
                            f"No AST nodes found for {file_path}, using basic discovery"
                        )

                # Cache results
                self.cache_manager.set(cache_key, nodes)

                # Emit file complete event
                if self.emitter:
                    self.emitter.emit_file_complete(
                        str(file_path), len(nodes), time.time() - file_start
                    )

            all_nodes.extend(nodes)
            files_processed += 1

            # Emit progress
            if self.emitter and files_processed % 10 == 0:
                self.emitter.emit_progress(
                    files_processed, total_files, f"Processing {file_path.name}"
                )

        # Build tree structure
        tree = self._build_tree(all_nodes, directory)

        # Calculate statistics
        duration = time.time() - start_time
        stats = {
            "files_processed": files_processed,
            "total_nodes": len(all_nodes),
            "duration": duration,
            "classes": sum(1 for n in all_nodes if n.node_type == "class"),
            "functions": sum(
                1 for n in all_nodes if n.node_type in ("function", "method")
            ),
            "imports": sum(1 for n in all_nodes if n.node_type == "import"),
            "languages": list(
                {n.language for n in all_nodes if hasattr(n, "language")}
            ),
            "avg_complexity": (
                sum(n.complexity for n in all_nodes) / len(all_nodes)
                if all_nodes
                else 0
            ),
        }

        # Save cache
        self.cache_manager.save()

        # Stop emitter
        if self.emitter:
            self.emitter.stop()

        return {"tree": tree, "nodes": all_nodes, "stats": stats}

    def _build_tree(self, nodes: List[CodeNode], root_dir: Path) -> Dict[str, Any]:
        """Build hierarchical tree structure from flat nodes list."""
        tree = {
            "name": root_dir.name,
            "type": "directory",
            "path": str(root_dir),
            "children": [],
        }

        # Group nodes by file
        files_map = {}
        for node in nodes:
            if node.file_path not in files_map:
                files_map[node.file_path] = {
                    "name": Path(node.file_path).name,
                    "type": "file",
                    "path": node.file_path,
                    "children": [],
                }

            # Add node to file
            node_dict = {
                "name": node.name,
                "type": node.node_type,
                "line_start": node.line_start,
                "line_end": node.line_end,
                "complexity": node.complexity,
                "has_docstring": node.has_docstring,
                "decorators": node.decorators,
                "signature": node.signature,
            }
            files_map[node.file_path]["children"].append(node_dict)

        # Build directory structure
        for file_path, file_node in files_map.items():
            rel_path = Path(file_path).relative_to(root_dir)
            parts = rel_path.parts

            current = tree
            for part in parts[:-1]:
                # Find or create directory
                dir_node = None
                for child in current["children"]:
                    if child["type"] == "directory" and child["name"] == part:
                        dir_node = child
                        break

                if not dir_node:
                    dir_node = {"name": part, "type": "directory", "children": []}
                    current["children"].append(dir_node)

                current = dir_node

            # Add file to current directory
            current["children"].append(file_node)

        return tree

    def discover_top_level(
        self, directory: Path, ignore_patterns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Discover only top-level directories and files for lazy loading.

        Args:
            directory: Root directory to discover
            ignore_patterns: Patterns to ignore

        Returns:
            Dictionary with top-level structure
        """
        return self.discovery_manager.discover_top_level(directory, ignore_patterns)

    def discover_directory(
        self, dir_path: str, ignore_patterns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Discover contents of a specific directory for lazy loading.

        Args:
            dir_path: Directory path to discover
            ignore_patterns: Patterns to ignore

        Returns:
            Dictionary with directory contents
        """
        return self.discovery_manager.discover_directory(dir_path, ignore_patterns)

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a specific file and return its AST structure.

        Args:
            file_path: Path to file to analyze

        Returns:
            Dictionary with file analysis results
        """
        return self.file_analyzer.analyze_file(file_path)

    @property
    def supported_extensions(self):
        """Get list of supported file extensions."""
        return {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}

    # Backward compatibility: Expose cache property
    @property
    def cache(self):
        """Get cache dictionary for backward compatibility."""
        return self.cache_manager.cache
